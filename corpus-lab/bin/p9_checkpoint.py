#!/usr/bin/env python
"""p9_checkpoint.py - resume protocol for the Phase 9 production-hardening night.

The night is expected to be interrupted (sleep, killed terminal, power). This
helper is the only durable record of where the run is. It writes ONE object,
atomically, to state/phase9_checkpoint.json, and appends a timestamped line to
state/phase9_heartbeat.log on every start/done/beat.

Spec: plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md section R.

  start <step> [note]        mark in_progress
  done  <step> [k=v ...]     mark done, with counts
  stop  <step> <reason>      mark stopped
  skip  <step> <reason>      mark skipped
  beat  [note]               heartbeat only
  note  <text>               append a free-text note
  status                     print every step
  resume                     last done / in_progress + six safety checks + where to go

Every command accepts `--file <path>` anywhere on the command line. The default
is state/phase9_checkpoint.json, so every Phase 9 command still reproduces
byte-for-byte. Pointing --file at a name containing "phase10" switches the run
id, the branch, the heartbeat log and the step headings to the Phase 10 set
(plans_fable/E_TRUST_AND_REPRO/EXECUTE_2026-09-16_NIGHT.md).
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# --- Phase 9 (the default run) ------------------------------------------------
P9_RUN_ID = "P9-2026-09-15"
P9_BRANCH = "phase9-production-hardening"
P9_CKPT = L.STATE / "phase9_checkpoint.json"
P9_BEAT = L.STATE / "phase9_heartbeat.log"
P9_TAG = "P9"

# Step id -> the heading in the executor file to continue from.
P9_HEADINGS = {
    "0.1": "Phase 0 / 0.1 branch",
    "0.2": "Phase 0 / 0.2 self-tests",
    "0.3": "Phase 0 / 0.3 offline baselines",
    "0.4": "Phase 0 / 0.4 timing baseline",
    "0.5": "Phase 0 / 0.5 checksum snapshot",
    "0.6": "Phase 0 / 0.6 plog + commit",
    "0.7": "Phase 0 / 0.7 build p9_checkpoint.py",
    "1.1": "Phase 1 / 1.1 open in under half a second",
    "1.2": "Phase 1 / 1.2 coverage cached in the shelf",
    "1.3": "Phase 1 / 1.3 inside from stored caption vectors",
    "1.4": "Phase 1 / 1.4 never load the model when not needed",
    "1.5": "Phase 1 / 1.5 re-bench and gate",
    "1.6": "Phase 1 / 1.6 plog + commit",
    "2.1": "Phase 2 / 2.1 the three changes",
    "2.2": "Phase 2 / 2.2 build",
    "2.3": "Phase 2 / 2.3 Gate S",
    "2.4": "Phase 2 / 2.4 plog + commit",
    "3.1": "Phase 3 / 3.1 find --compact/--show",
    "3.2": "Phase 3 / 3.2 CLAUDE.md v2",
    "3.3": "Phase 3 / 3.3 guard v2",
    "3.4": "Phase 3 / 3.4 battery limit flags",
    "3.5": "Phase 3 / 3.5 plog + commit",
    "4.1": "Phase 4 / 4.1 what v2 adds",
    "4.2": "Phase 4 / 4.2 regression and re-score",
    "4.3": "Phase 4 / 4.3 plog + commit",
    "5.1": "Phase 5 / 5.1 pre-register the live spec",
    "5.2": "Phase 5 / 5.2 procedure",
    "5.3": "Phase 5 / 5.3 read the gate",
    "5b": "Phase 5b variance battery",
    "5c": "Phase 5c professor-mode rehearsal",
    "6.1": "Phase 6 / 6.1 setup_folder.py",
    "6.2": "Phase 6 / 6.2 cold test on corpus_500",
    "6.3": "Phase 6 / 6.3 INSTALL_FOR_SIR.md",
    "6.4": "Phase 6 / 6.4 plog + commit",
    "7.1": "Phase 7 / findings F64-F69",
    "7.2": "Phase 7 / handoff",
    "7.3": "Phase 7 / demo pack",
    "7.4": "Phase 7 / README rows + MANIFEST",
    "7.5": "Phase 7 / architecture addendum",
    "7.6": "Phase 7 / final checks",
}

# --- Phase 10 (selected with --file ...phase10...) ----------------------------
P10_RUN_ID = "P10-2026-09-16"
P10_BRANCH = "phase10-trust-and-repro"
P10_BEAT = L.STATE / "phase10_heartbeat.log"
P10_TAG = "P10"
P10_HEADINGS = {
    "0.1": "Phase 0 / 0.1 branch, deadline, baselines",
    "0.2": "Phase 0 / 0.2 checkpoint helper --file",
    "0.3": "Phase 0 / 0.3 run_record.py",
    "0.4": "Phase 0 / 0.4 docs_check.py",
    "0.5": "Phase 0 / 0.5 requirements-portable.txt",
    "0.6": "Phase 0 / 0.6 protect the demo path (s7_phase10_pre)",
    "0.7": "Phase 0 / 0.7 README + plog + commit",
    "1.1": "Phase 1 / 1.1 opens from ground truth",
    "1.2": "Phase 1 / 1.2 citation vs mention",
    "1.3": "Phase 1 / 1.3 full answer across a guard interruption",
    "1.4": "Phase 1 / 1.4 denominators",
    "1.5": "Phase 1 / 1.5 regression tests",
    "1.6": "Phase 1 / 1.6 re-score P5-P9, v2 vs v3; Gate T",
    "1.7": "Phase 1 / 1.7 README p10_scorer_v3",
    "1.8": "Phase 1 / 1.8 freeze and tag scorer v3",
    "2.1": "Phase 2 / 2.1 c_key_v2_build.py",
    "2.2": "Phase 2 / 2.2 vector value metric in v3",
    "2.3": "Phase 2 / 2.3 re-score P9 with key v2",
    "2.4": "Phase 2 / 2.4 README p10_key_v2 + commit",
    "3.1": "Phase 3 / 3.1 make_portable.py",
    "3.2": "Phase 3 / 3.2 manifest, build report, canonical export",
    "3.3": "Phase 3 / 3.3 Gate R1 clean rooms A and B",
    "3.4": "Phase 3 / 3.4 Gate R2 corpus_2000",
    "3.5": "Phase 3 / 3.5 Gate R3 read trace",
    "3.6": "Phase 3 / 3.6 supersede and document",
    "3.7": "Phase 3 / 3.7 plog + commit",
    "4.1": "Phase 4 / 4.1 variance batteries P10S1-3, P10O1",
    "4.2": "Phase 4 / 4.2 budget and clock",
    "4.3": "Phase 4 / 4.3 variance report",
    "4.4": "Phase 4 / 4.4 optional P10O2",
    "4.5": "Phase 4 / 4.5 README p10_variance + commit",
    "5.1": "Phase 5 / 5.1 morning note",
    "5.2": "Phase 5 / 5.2 correction note",
    "5.3": "Phase 5 / 5.3 handoff",
    "5.4": "Phase 5 / 5.4 final checks, Gate D",
    "5.5": "Phase 5 / 5.5 plog + commit",
}

# Selected by _select_run() from --file; the defaults are the Phase 9 set so
# every Phase 9 command reproduces unchanged.
RUN_ID = P9_RUN_ID
BRANCH = P9_BRANCH
CKPT = P9_CKPT
BEAT = P9_BEAT
TAG = P9_TAG
HEADINGS = dict(P9_HEADINGS)
ORDER = list(HEADINGS.keys())


def _select_run(argv):
    """Pull `--file <path>` out of argv and point the module at that run.

    Returns argv with the flag removed. Absent --file leaves every Phase 9
    default in place.
    """
    global RUN_ID, BRANCH, CKPT, BEAT, TAG, HEADINGS, ORDER
    rest, path = [], None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--file" and i + 1 < len(argv):
            path = argv[i + 1]
            i += 2
            continue
        if a.startswith("--file="):
            path = a.split("=", 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    if path is None:
        return rest
    CKPT = Path(path)
    if not CKPT.is_absolute():
        CKPT = (Path.cwd() / CKPT).resolve()
    if "phase10" in CKPT.name.lower():
        RUN_ID, BRANCH, BEAT, TAG = P10_RUN_ID, P10_BRANCH, P10_BEAT, P10_TAG
        HEADINGS = dict(P10_HEADINGS)
        ORDER = list(HEADINGS.keys())
    return rest


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def load():
    if CKPT.exists():
        try:
            return json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"run_id": RUN_ID, "branch": BRANCH, "steps": {},
            "last_beat": _now(), "notes": []}


def save(d):
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    tmp = CKPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, CKPT)


def beat(line):
    BEAT.parent.mkdir(parents=True, exist_ok=True)
    with open(BEAT, "a", encoding="utf-8") as fh:
        fh.write("%s  %s\n" % (_now(), line))


def _kv(args):
    out = {}
    for a in args:
        if "=" not in a:
            continue
        k, v = a.split("=", 1)
        try:
            out[k] = int(v)
        except ValueError:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def cmd_start(step, rest):
    d = load()
    s = d["steps"].setdefault(step, {})
    s["status"] = "in_progress"
    s["started"] = _now()
    s.pop("finished", None)
    if rest:
        s["note"] = " ".join(rest)
    d["last_beat"] = _now()
    save(d)
    beat("START %s %s" % (step, " ".join(rest)))
    print("START", step)


def cmd_done(step, rest):
    d = load()
    s = d["steps"].setdefault(step, {})
    s["status"] = "done"
    s.setdefault("started", _now())
    s["finished"] = _now()
    kv = _kv(rest)
    if kv:
        s.setdefault("kv", {}).update(kv)
    d["last_beat"] = _now()
    save(d)
    beat("DONE %s %s" % (step, json.dumps(kv)))
    print("DONE", step, json.dumps(kv))


def cmd_mark(status, step, rest):
    d = load()
    s = d["steps"].setdefault(step, {})
    s["status"] = status
    s["finished"] = _now()
    s["reason"] = " ".join(rest)
    d["last_beat"] = _now()
    save(d)
    beat("%s %s %s" % (status.upper(), step, s["reason"]))
    print(status.upper(), step, s["reason"])


def cmd_note(rest):
    d = load()
    d["notes"].append("%s  %s" % (_now(), " ".join(rest)))
    save(d)
    beat("NOTE " + " ".join(rest))
    print("NOTE recorded")


def cmd_status():
    d = load()
    print("run_id   ", d["run_id"])
    print("branch   ", d["branch"])
    print("last_beat", d["last_beat"])
    for k in ORDER:
        s = d["steps"].get(k)
        if not s:
            continue
        print("  %-5s %-12s %s -> %s %s" % (
            k, s.get("status", "?"), s.get("started", ""), s.get("finished", ""),
            json.dumps(s.get("kv", {})) if s.get("kv") else ""))
    unknown = [k for k in d["steps"] if k not in HEADINGS]
    for k in unknown:
        print("  %-5s %-12s (unlisted step)" % (k, d["steps"][k].get("status", "?")))
    if d["notes"]:
        print("notes:")
        for n in d["notes"][-10:]:
            print("  ", n)


# --- safety checks -----------------------------------------------------------

def _rung_clean(rung_path, label, out):
    cm = rung_path / "CLAUDE.md"
    cd = rung_path / ".claude"
    present = cm.exists() or cd.exists()
    if not present:
        out.append(("PASS", "%s clean (no CLAUDE.md, no .claude)" % label))
        return
    # is c_stack's own per-corpus state file claiming an install?
    installed = False
    try:
        sys.path.insert(0, str(L.BIN))
        import stack as STACK  # noqa: E402
        st = L.SCRATCH / ("c_stack_state__%s.json" % STACK.corpus_key(rung_path))
        if st.exists():
            j = json.loads(st.read_text(encoding="utf-8"))
            installed = j.get("status") == "installed"
    except Exception:
        pass
    out.append(("FAIL", "%s DIRTY%s -- CLAUDE.md=%s .claude=%s" % (
        label, " STALE_INSTALL" if installed else "", cm.exists(), cd.exists())))


def _stray_sessions(out):
    """Count claude.exe/node.exe processes whose command line is one of ours."""
    n_ours = 0
    n_total = 0
    try:
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='node.exe' or Name='claude.exe'\" "
              "| Select-Object -ExpandProperty CommandLine")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=90)
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            n_total += 1
            if "--output-format stream-json" in line and "corpus_" in line:
                n_ours += 1
    except Exception as e:
        out.append(("FAIL", "process scan failed: %s" % e))
        return
    status = "PASS" if n_ours == 0 else "FAIL"
    out.append((status, "stray sessions: ours=%d (kill these only), node/claude total=%d"
                % (n_ours, n_total)))


def _git_clean(out):
    try:
        r = subprocess.run(["git", "status", "--short"], cwd=str(L.RETRIEVAL_LAB),
                           capture_output=True, text=True, timeout=120)
        dirty = [x for x in (r.stdout or "").splitlines() if x.strip()]
        out.append(("PASS" if not dirty else "FAIL",
                    "git status: %d modified/untracked" % len(dirty)))
        for x in dirty[:10]:
            out.append(("", "    " + x))
    except Exception as e:
        out.append(("FAIL", "git status failed: %s" % e))


def _progress_tail(out):
    p = L.STATE / "progress.jsonl"
    lines = []
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                j = json.loads(line)
            except Exception:
                continue
            if j.get("phase") == TAG:
                lines.append(j)
    out.append(("", "last %d %s progress lines:" % (min(5, len(lines)), TAG)))
    for j in lines[-5:]:
        note = str(j.get("note", ""))
        if len(note) > 160:
            note = note[:160] + " ...[%d chars]" % len(note)
        out.append(("", "    %s %s %s %s" % (j.get("ts"), j.get("step"),
                                             j.get("status"), note)))


def _disk(out):
    try:
        free_gb = shutil.disk_usage(str(L.RETRIEVAL_LAB)).free / 1e9
        out.append(("PASS" if free_gb >= 10 else "FAIL", "free disk %.1f GB (need >= 10)" % free_gb))
    except Exception as e:
        out.append(("FAIL", "disk check failed: %s" % e))


def cmd_resume():
    d = load()
    done = [k for k in ORDER if d["steps"].get(k, {}).get("status") == "done"]
    inprog = [k for k, v in d["steps"].items() if v.get("status") == "in_progress"]
    print("=" * 72)
    print("%s RESUME   run_id=%s  last_beat=%s  file=%s"
          % (RUN_ID.split("-")[0], d["run_id"], d["last_beat"], CKPT.name))
    print("=" * 72)
    print("last completed step :", done[-1] if done else "(none)")
    print("in_progress         :", ", ".join(inprog) if inprog else "(none)")
    print()
    print("-- safety checks --")
    out = []
    _rung_clean(L.HARNESS / "corpus_15000", "corpus_15000", out)
    _rung_clean(L.HARNESS / "corpus_500", "corpus_500", out)
    _stray_sessions(out)
    _git_clean(out)
    _progress_tail(out)
    _disk(out)
    n_fail = 0
    for status, msg in out:
        if status:
            print("  [%s] %s" % (status, msg))
            if status == "FAIL":
                n_fail += 1
        else:
            print("  " + msg)
    print()
    if inprog:
        nxt = inprog[0]
        print("CONTINUE FROM: %s  -- %s" % (nxt, HEADINGS.get(nxt, "?")))
        print("  (run its done-check in section R.3 first; if it passes, mark done and move on)")
    else:
        nxt = None
        for k in ORDER:
            st = d["steps"].get(k, {}).get("status")
            if st not in ("done", "skipped", "stopped"):
                nxt = k
                break
        if nxt:
            print("CONTINUE FROM: %s  -- %s" % (nxt, HEADINGS[nxt]))
        else:
            print("CONTINUE FROM: (all listed steps closed)")
    print("safety check failures:", n_fail)
    return 0


def main(argv):
    argv = _select_run(list(argv))
    if len(argv) < 2:
        print(__doc__)
        return 2
    c = argv[1]
    rest = argv[3:] if len(argv) > 3 else []
    if c == "start":
        cmd_start(argv[2], rest)
    elif c == "done":
        cmd_done(argv[2], rest)
    elif c == "stop":
        cmd_mark("stopped", argv[2], rest)
    elif c == "skip":
        cmd_mark("skipped", argv[2], rest)
    elif c == "beat":
        note = " ".join(argv[2:])
        d = load()
        d["last_beat"] = _now()
        save(d)
        beat("BEAT " + note)
        print("BEAT", note)
    elif c == "note":
        cmd_note(argv[2:])
    elif c == "status":
        cmd_status()
    elif c == "resume":
        return cmd_resume()
    else:
        print("unknown command:", c)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
