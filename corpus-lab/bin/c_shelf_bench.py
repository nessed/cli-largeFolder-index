#!/usr/bin/env python
"""c_shelf_bench.py - wall-clock benchmark of the shelf CLI, as the professor runs it.

Every shelf command in a real session is a FRESH python process: import cost,
model load, and any full-table scan are paid on every call. So the benchmark
launches a fresh subprocess per measurement, exactly as CLAUDE.md tells the model
to. Three runs per command, median reported.

  python c_shelf_bench.py --label baseline_v1
  python c_shelf_bench.py --label after_phase1 --shelf-dir corpus-lab/02_stacks/s7_shelf_v2

Writes state/c_shelf_bench.json as {label: {command: {...}}}, keeping every
previously recorded label.

The strings below are generic English benchmark inputs. They are not drawn from
the answer key and they do not enter retrieval logic (rule 4).
"""
import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

SHELF_CLI = L.BIN / "c_shelf.py"

BENCH_DOC = "Sources/Federal/Economic Survey/2018-19/Pakistan Economic Survey 2018-19.pdf"
BENCH_PAGE = "5"
BENCH_ROW = "development expenditure"
BENCH_QUESTION = "how has development spending changed over the last decade"
BENCH_REWRITES = ["development expenditure",
                  "public sector development programme",
                  "annual development programme"]

# Commands that must never pay the embedding-model load (Phase 1.4).
NO_MODEL = {"have", "tables", "open", "exact", "copies", "note", "notes", "coverage"}

# Gate 1, written into the executor plan before any of these numbers existed.
GATE_1 = {"open": 0.5, "find": 3.5, "inside": 2.5, "series": 5.0,
          "have": 0.8, "tables": 0.8, "exact": 0.8, "coverage": 0.8}


def commands():
    q = ["--q", BENCH_REWRITES[0], "--q", BENCH_REWRITES[1], "--q", BENCH_REWRITES[2]]
    return {
        "find":     ["find", BENCH_QUESTION] + q + ["--caption-channel", "lex"],
        "open":     ["open", BENCH_DOC, BENCH_PAGE],
        "coverage": ["coverage"],
        "inside":   ["inside", BENCH_DOC, BENCH_ROW, "--caption", "dense_first"],
        "series":   ["series", BENCH_ROW, "--family", "economic survey",
                     "--from", "2014-15", "--to", "2018-19"],
        "have":     ["have", "economic survey"],
        "tables":   ["tables", BENCH_DOC],
        "exact":    ["exact", "development expenditure"],
        "copies":   ["copies", BENCH_DOC],
        # `notes` reads one slug's log; `note` refuses (rc 3) without an opened
        # page and writes nothing. Both are here only to prove the cheap commands
        # never pay the embedding-model load (Phase 1.4).
        "notes":    ["notes", "--slug", "c_shelf_bench_probe"],
        "note":     ["note", "--slug", "c_shelf_bench_probe", "a benchmark probe with no citation"],
        "import_floor": None,   # bare import + context build, measured specially
    }


# `note` deliberately exits 3 here: refusing an uncited note is its correct behaviour.
EXPECTED_RC = {"note": (0, 3)}


def run_once(db, shelf, argv, cwd):
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, str(SHELF_CLI), "--db", db, "--shelf", shelf] + argv,
                       capture_output=True, text=True, cwd=cwd, timeout=600)
    dt = time.perf_counter() - t0
    return dt, r.returncode, (r.stdout or ""), (r.stderr or "")


def run_import_floor(db, shelf, cwd):
    """Bare `import c_shelf` + get_ctx, no command: the per-call floor."""
    src = (
        "import sys,time\n"
        "sys.path.insert(0, r'%s')\n"
        "import c_shelf as S\n"
        "ctx = S.get_ctx(r'%s', r'%s', None)\n"
        "print('OK')\n" % (str(L.BIN), db, shelf)
    )
    f = L.SCRATCH / "_bench_import_floor.py"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(src, encoding="utf-8")
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True,
                       cwd=cwd, timeout=600)
    return time.perf_counter() - t0, r.returncode, (r.stdout or ""), (r.stderr or "")


def loaded_fastembed(db, shelf, argv, cwd):
    """Re-run the command in-process with an import tripwire and report whether
    fastembed was imported. Rule: the cheap commands must never load the model."""
    src = (
        "import sys, json\n"
        "sys.path.insert(0, r'%s')\n"
        "sys.argv = %r\n"
        "import c_shelf as S\n"
        "try:\n"
        "    S.main()\n"
        "except SystemExit:\n"
        "    pass\n"
        "except Exception:\n"
        "    pass\n"
        "print('FASTEMBED_LOADED=' + str('fastembed' in sys.modules), file=sys.stderr)\n"
        % (str(L.BIN),
           ["c_shelf.py", "--db", db, "--shelf", shelf] + list(argv))
    )
    f = L.SCRATCH / "_bench_tripwire.py"
    f.write_text(src, encoding="utf-8")
    r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True,
                       cwd=cwd, timeout=600)
    return "FASTEMBED_LOADED=True" in (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--db", default=str(L.STACKS / "s2_fts5" / "harness_15000.db"))
    ap.add_argument("--shelf-dir", dest="shelf_dir",
                    default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--only", default=None, help="comma-separated subset of command names")
    a = ap.parse_args()

    shelf = str(Path(a.shelf_dir) / "shelf.db")
    cwd = str(L.RETRIEVAL_LAB)
    cmds = commands()
    if a.only:
        want = set(a.only.split(","))
        cmds = {k: v for k, v in cmds.items() if k in want}

    out = {}
    for name, argv in cmds.items():
        times, rcs = [], []
        stdout_last = ""
        for _ in range(a.repeats):
            if name == "import_floor":
                dt, rc, so, se = run_import_floor(a.db, shelf, cwd)
            else:
                dt, rc, so, se = run_once(a.db, shelf, argv, cwd)
            times.append(dt)
            rcs.append(rc)
            stdout_last = so
            if rc not in EXPECTED_RC.get(name, (0,)):
                print("  !! %s rc=%d  %s" % (name, rc, (se or "")[:300]))
        rec = {"median_s": round(statistics.median(times), 3),
               "min_s": round(min(times), 3),
               "max_s": round(max(times), 3),
               "runs": [round(t, 3) for t in times],
               "rc": rcs}
        if name in NO_MODEL and argv:
            rec["fastembed_loaded"] = loaded_fastembed(a.db, shelf, argv, cwd)
        if name == "coverage":
            for line in stdout_last.splitlines():
                if line.startswith("COVERAGE"):
                    rec["coverage_line"] = line.strip()
        out[name] = rec
        print("%-14s median=%6.2fs  min=%6.2fs  max=%6.2fs %s"
              % (name, rec["median_s"], rec["min_s"], rec["max_s"],
                 ("fastembed=%s" % rec["fastembed_loaded"]) if "fastembed_loaded" in rec else ""))

    # Gate 1, pre-registered in the executor file before any of these numbers
    # existed. Reported here so the verdict is read off the same artefact as the
    # measurement rather than by eye.
    gate = {}
    for name, bar in GATE_1.items():
        if name not in out:
            continue
        gate[name] = {"median_s": out[name]["median_s"], "bar_s": bar,
                      "pass": out[name]["median_s"] <= bar}
    for name in NO_MODEL:
        if name in out and out[name].get("fastembed_loaded"):
            gate.setdefault("_model_load_violations", []).append(name)
    gate["_all_pass"] = all(v["pass"] for k, v in gate.items()
                            if isinstance(v, dict) and "pass" in v)
    print("GATE 1:", "PASS" if gate["_all_pass"] else "SHORTFALL",
          " ".join("%s=%s" % (k, "ok" if v.get("pass") else "MISS")
                   for k, v in gate.items() if isinstance(v, dict) and "pass" in v))

    path = L.STATE / "c_shelf_bench.json"
    all_labels = {}
    if path.exists():
        try:
            all_labels = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            all_labels = {}
    all_labels[a.label] = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "shelf_dir": a.shelf_dir, "db": a.db,
                           "repeats": a.repeats, "commands": out, "gate_1": gate}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(all_labels, indent=1), encoding="utf-8")
    print("WROTE", path, "label=%s" % a.label)


if __name__ == "__main__":
    main()
