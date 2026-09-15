#!/usr/bin/env python
"""p10_cleanroom.py - install the portable package somewhere it cannot cheat.

Plan E Phase 3.3-3.5, governed by corpus-lab/state/phase10_gate_r_spec.md.

One clean room is: a copy of the package under %TEMP%, its own venv built from
`requirements-portable.txt`, every `*_ROOT` / `LAB_PRIVATE` environment variable
unset AND asserted unset, a COPY of the corpus (the rung is never touched), and
its own artefacts directory. Nothing in room A is reachable from room B.

  python p10_cleanroom.py build   --room A --package <dir> --corpus <rung>
  python p10_cleanroom.py probe   --room A
  python p10_cleanroom.py compare --a A --b B
  python p10_cleanroom.py trace   --room A --package <dir> --corpus <rung>
  python p10_cleanroom.py teardown --room A

Every step prints what it did and writes JSON beside the room, so a failed gate
names the first thing that differed rather than "the gate failed".
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# Unset in every clean room, then asserted unset: if any of these leaked, the
# "portable" install would quietly resolve back into the development lab and the
# gate would pass for the wrong reason.
LAB_ENV = ["CORPUS_LAB_ROOT", "RETRIEVAL_LAB_ROOT", "LAB_PRIVATE", "HARNESS_ROOT",
           "RUNS_ROOT", "SCORES_ROOT", "HARNESS_KEYS", "RASHIP_ROOT",
           "CANARY_MANIFEST"]

FIND_QUERIES = [
    "development spending by year",
    "tax revenue table",
    "which years does the folder cover",
    "production of a major crop over time",
    "total expenditure summary",
    "provincial budget allocation",
    "public debt outstanding",
    "import and export values",
    "inflation rate by month",
    "population estimates by province",
    "education sector spending",
    "health sector allocation",
    "energy generation capacity",
    "agricultural output by crop",
    "employment and labour force",
    "foreign exchange reserves",
    "subsidy payments",
    "development programme releases",
    "revenue collection target versus actual",
    "summary table of key indicators",
]
SERIES_QUERIES = ["development expenditure", "tax revenue", "total expenditure"]


def room_dir(room):
    return Path(os.environ.get("TEMP", "/tmp")) / ("p10_clean_%s" % room)


def clean_env():
    env = dict(os.environ)
    for k in LAB_ENV:
        env.pop(k, None)
    env["PYTHONHASHSEED"] = "0"
    env["OMP_NUM_THREADS"] = "4"
    return env


def _run(cmd, cwd, env, log=None, timeout=4800):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                       text=True, errors="replace", timeout=timeout)
    wall = time.time() - t0
    if log:
        Path(log).write_text((p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""),
                             encoding="utf-8")
    return p.returncode, wall, (p.stdout or ""), (p.stderr or "")


def project_key_memory_count(folder):
    """How many auto-memory files exist for this folder's project key.

    A clean room that accumulates memory is a clean room that is learning the
    corpus between runs, which would make every later number meaningless.
    """
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return 0, []
    key = str(Path(folder).resolve()).replace(":", "-").replace("\\", "-").replace("/", "-")
    key = key.lstrip("-")
    hits = []
    for d in base.iterdir():
        if not d.is_dir():
            continue
        if key.lower().endswith(d.name.lower().lstrip("-")) or \
           d.name.lower().lstrip("-") in key.lower():
            for f in d.rglob("*"):
                if f.is_file() and f.suffix in (".md", ".json") and "memory" in str(f).lower():
                    hits.append(str(f))
    return len(hits), hits


def cmd_build(a):
    room = room_dir(a.room)
    if room.exists():
        shutil.rmtree(room, ignore_errors=True)
    room.mkdir(parents=True)
    rec = {"room": a.room, "root": str(room), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # 1. copy the package
    pkg_src = Path(a.package).resolve()
    pkg = room / "package"
    shutil.copytree(pkg_src, pkg)
    rec["package_src"] = str(pkg_src)
    print("[1/6] package copied -> %s" % pkg, flush=True)

    # 2. venv from the pinned requirements
    venv = pkg / ".venv"
    rc, w, _o, e = _run([sys.executable, "-m", "venv", str(venv)], pkg, clean_env())
    if rc != 0:
        print("VENV_FAILED %s" % e[-400:], file=sys.stderr)
        return 4
    pip = venv / "Scripts" / "pip.exe"
    py = venv / "Scripts" / "python.exe"
    rc, w, _o, e = _run([str(pip), "install", "-q", "-r",
                         str(pkg / "requirements-portable.txt")], pkg, clean_env(),
                        log=room / "pip.log")
    rec["venv_s"] = round(w, 1)
    if rc != 0:
        print("PIP_FAILED rc=%d %s" % (rc, e[-600:]), file=sys.stderr)
        return 4
    print("[2/6] venv built and requirements installed (%.0fs)" % w, flush=True)

    # 3. assert the lab env vars are unset INSIDE the clean interpreter
    env = clean_env()
    rc, _w, out, _e = _run([str(py), "-c",
                            "import os,json;print(json.dumps({k:os.environ.get(k) "
                            "for k in %r}))" % LAB_ENV], pkg, env)
    leaked = {k: v for k, v in json.loads(out.strip().splitlines()[-1]).items() if v}
    rec["env_asserted_unset"] = LAB_ENV
    rec["env_leaked"] = leaked
    if leaked:
        print("ENV_LEAKED %s" % leaked, file=sys.stderr)
        return 4
    print("[3/6] %d lab env vars asserted unset" % len(LAB_ENV), flush=True)

    # 4. copy the corpus; the rung itself is never touched
    corpus = room / "corpus"
    src = Path(a.corpus).resolve()
    shutil.copytree(src, corpus)
    n_files = sum(1 for x in corpus.rglob("*") if x.is_file())
    rec["corpus_src"] = str(src)
    rec["corpus_n_files"] = n_files
    n_mem, _ = project_key_memory_count(corpus)
    rec["memory_files_before"] = n_mem
    if n_mem:
        print("MEMORY_PRESENT_BEFORE %d" % n_mem, file=sys.stderr)
        return 4
    print("[4/6] corpus copied (%d files), 0 memory files" % n_files, flush=True)

    # 5. doctor, then install
    rc, w, out, _e = _run([str(py), str(pkg / "bin" / "setup_folder.py"), "doctor"],
                          pkg, env, log=room / "doctor.log")
    rec["doctor_rc"] = rc
    print("[5/6] doctor rc=%d" % rc, flush=True)

    art = room / "artefacts"
    rc, w, out, e = _run([str(py), "-u", str(pkg / "bin" / "setup_folder.py"), "install",
                          "--folder", str(corpus), "--artefacts", str(art),
                          "--seed-env", "--workers", str(a.workers)],
                         pkg, env, log=room / "install.log")
    rec["install_rc"] = rc
    rec["install_s"] = round(w, 1)
    rec["artefacts"] = str(art)
    print("[6/6] install rc=%d in %.0fs" % (rc, w), flush=True)
    if rc != 0:
        print("INSTALL_FAILED rc=%d\n%s" % (rc, e[-1200:]), file=sys.stderr)
        rec["install_stderr_tail"] = e[-2000:]
        (room / "room.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return 4

    # self-test with explicit paths
    rc, w, out, _e = _run([str(py), str(pkg / "bin" / "c_selftest.py"),
                           "--db", str(art / "pages.db"),
                           "--shelf", str(art / "shelf" / "shelf.db"),
                           "--out", str(room / "selftest.json")],
                          corpus, env, log=room / "selftest.log")
    rec["selftest_rc"] = rc
    try:
        st = json.loads((room / "selftest.json").read_text(encoding="utf-8"))
        rec["selftest_checks"] = sorted(k for k in st if not k.startswith("_"))
        rec["selftest_failed"] = sorted(
            k for k in st if not k.startswith("_")
            and isinstance(st[k], dict) and st[k].get("pass") is False)
        rec["selftest_pass"] = st.get("_overall", {}).get("pass")
    except Exception as ex:
        rec["selftest_parse_error"] = str(ex)
    print("      selftest rc=%d pass=%s" % (rc, rec.get("selftest_pass")), flush=True)

    (room / "room.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("\nroom %s ready: %s" % (a.room, room))
    return 0


def cmd_probe(a):
    """Run the fixed probe list from the gate spec and capture ranked output."""
    room = room_dir(a.room)
    rec = json.loads((room / "room.json").read_text(encoding="utf-8"))
    pkg = room / "package"
    py = pkg / ".venv" / "Scripts" / "python.exe"
    art = Path(rec["artefacts"])
    corpus = room / "corpus"
    env = clean_env()
    shelf_py = pkg / "bin" / "c_shelf.py"
    # c_shelf takes --db and --shelf globally; the corpus root comes from the
    # registry entry `install` made, so the probes run with cwd inside the copy.
    base = [str(py), str(shelf_py), "--db", str(art / "pages.db"),
            "--shelf", str(art / "shelf" / "shelf.db")]

    def call(*args, timeout=600):
        rc, w, out, e = _run(base + list(args), corpus, env, timeout=timeout)
        return {"args": list(args), "rc": rc, "stdout": out.strip(),
                "stderr": e.strip()[-300:]}

    out = {"room": a.room, "find": [], "inside": [], "series": [],
           "coverage": None, "have": []}
    for q in FIND_QUERIES:
        out["find"].append(call("find", q))
    print("  %d find queries done" % len(out["find"]), flush=True)

    # five largest families, by the spec's rule
    import sqlite3
    fams = []
    try:
        con = sqlite3.connect("file:%s?mode=ro"
                              % (art / "shelf" / "shelf.db").as_posix(), uri=True)
        try:
            fams = [r[0] for r in con.execute(
                "SELECT family_id FROM families ORDER BY n_members DESC, family_id "
                "LIMIT 5").fetchall()]
        except sqlite3.Error:
            fams = [r[0] for r in con.execute(
                "SELECT family_id FROM families ORDER BY family_id LIMIT 5").fetchall()]
        finally:
            con.close()
    except Exception as e:
        out["family_error"] = str(e)
    out["families_probed"] = fams

    for f in fams:
        out["inside"].append(call("have", f))
    for q in SERIES_QUERIES:
        out["series"].append(call("series", q))
    out["coverage"] = call("coverage")
    for f in fams[:2]:
        out["have"].append(call("have", f))

    (room / "retrieval_outputs.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s" % (room / "retrieval_outputs.json"))
    return 0


def cmd_teardown(a):
    room = room_dir(a.room)
    rec_p = room / "room.json"
    if rec_p.exists():
        rec = json.loads(rec_p.read_text(encoding="utf-8"))
        pkg, corpus = room / "package", room / "corpus"
        py = pkg / ".venv" / "Scripts" / "python.exe"
        if py.exists() and corpus.exists():
            rc, _w, _o, _e = _run([str(py), str(pkg / "bin" / "setup_folder.py"),
                                   "uninstall", "--folder", str(corpus)],
                                  pkg, clean_env(), log=room / "uninstall.log")
            print("uninstall rc=%d" % rc)
            n_mem, hits = project_key_memory_count(corpus)
            print("memory files after: %d" % n_mem)
            rec["memory_files_after"] = n_mem
            rec["uninstall_rc"] = rc
            rec["claude_md_removed"] = not (corpus / "CLAUDE.md").exists()
            rec["dot_claude_removed"] = not (corpus / ".claude").exists()
            rec_p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    if a.purge:
        keep = room.parent / ("p10_clean_%s_record" % a.room)
        keep.mkdir(exist_ok=True)
        for f in ("room.json", "retrieval_outputs.json", "selftest.json",
                  "install.log", "doctor.log", "reads.log", "trace.json"):
            if (room / f).exists():
                shutil.copy2(room / f, keep / f)
        art = room / "artefacts"
        for f in ("build_manifest.json", "BUILD_REPORT.md", "canonical_export.json"):
            if (art / f).exists():
                shutil.copy2(art / f, keep / f)
        shutil.rmtree(room, ignore_errors=True)
        print("purged %s; records kept in %s" % (room, keep))
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build")
    b.add_argument("--room", required=True)
    b.add_argument("--package", required=True)
    b.add_argument("--corpus", required=True)
    b.add_argument("--workers", type=int, default=8)
    b.set_defaults(fn=cmd_build)

    p = sub.add_parser("probe")
    p.add_argument("--room", required=True)
    p.set_defaults(fn=cmd_probe)

    t = sub.add_parser("teardown")
    t.add_argument("--room", required=True)
    t.add_argument("--purge", action="store_true")
    t.set_defaults(fn=cmd_teardown)

    a = ap.parse_args(argv[1:])
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
