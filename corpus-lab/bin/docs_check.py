#!/usr/bin/env python
"""docs_check.py - Gate D is this script's exit code.

Plan E section D lists a documentation standard and, for each requirement, the
mechanism that enforces it. This script checks the mechanisms. It does not read
prose and it does not judge quality; it asks five questions that have yes/no
answers, and every one of them is a way the record could silently stop being
reproducible:

  A. every run record created during this run has all its section-D fields and
     has been `finish`ed;
  B. every experiment README carries the nine fixed headings;
  C. no run record cites a gate spec whose commit is dated AFTER the run started
     (that is what "gates are written before numbers exist" means mechanically);
  D. nothing written during this run overwrote a file that already existed
     (rule 15), judged against the Phase 0 snapshot;
  E. every scorer output names its scorer version and its key's sha256
     (rule 17).

  docs_check.py [--root <dir>] [--since <epoch>] [--snapshot <file>] [--quiet]

exit 0 = every mechanism holds; exit 1 = at least one does not, and each failure
is printed with the file and the reason named.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# --- what a complete run record looks like (section D, first row) ------------
RECORD_TOP_FIELDS = [
    "id", "started_at", "finished_at", "command", "cwd", "git", "env_overrides",
    "runtime", "models", "inputs", "declared_outputs", "outputs", "notes",
]
RECORD_GIT_FIELDS = ["head", "branch", "dirty"]
RECORD_RUNTIME_FIELDS = ["python", "packages", "workers",
                         "OMP_NUM_THREADS", "PYTHONHASHSEED"]

# --- the fixed experiment-README headings (section D, "one README per experiment")
README_HEADINGS = [
    "Purpose", "Method", "Inputs", "Outputs", "Gate", "Result", "Adopted?",
    "Run record", "What this does not show",
]

# Files whose whole job is to be appended to or updated in place. Rule 15 is
# about not overwriting a RECORDED RESULT; a checkpoint, a heartbeat and the
# progress log are logs, and the pre-existing snapshot is this check's own input.
APPEND_BY_DESIGN = {
    "corpus-lab/state/progress.jsonl",
    "corpus-lab/state/phase10_checkpoint.json",
    "corpus-lab/state/phase10_checkpoint.json.tmp",
    "corpus-lab/state/phase10_heartbeat.log",
    "corpus-lab/state/phase9_checkpoint.json",
    "corpus-lab/state/phase9_heartbeat.log",
    "corpus-lab/state/phase10_preexisting_files.txt",
    "corpus-lab/state/phase10_run_started.txt",
    "corpus-lab/state/phase10_baseline_console.txt",
    "corpus-lab/state/phase10_deadline_resolved.txt",
}

# Never scanned. 99_scratch holds the docs_check self-test's own fixtures --
# temp trees containing deliberately broken run records -- and a gate that fails
# on its own test data is a gate nobody can pass.
SKIP_PARTS = {".git", ".venv", "99_scratch", "node_modules", "__pycache__",
              ".pytest_cache", "dist"}

# Result files guarded by check D.
GUARDED_DIRS = ["corpus-lab/state", "_private/results/04_scores"]

# Scorer outputs guarded by check E.
SCORER_GLOBS = ["c_live_battery_v3__*.json", "live_v3__*.json",
                "c_rescore_v2_vs_v3.json"]


class Report:
    def __init__(self, quiet=False):
        self.fails = []
        self.oks = []
        self.quiet = quiet

    def ok(self, check, msg):
        self.oks.append((check, msg))

    def fail(self, check, path, reason):
        self.fails.append((check, str(path), reason))

    def render(self):
        for check, msg in self.oks:
            if not self.quiet:
                print("  [PASS] %s  %s" % (check, msg))
        for check, path, reason in self.fails:
            print("  [FAIL] %s  %s\n           reason: %s" % (check, path, reason))
        print()
        print("checks failed: %d" % len(self.fails))
        return 1 if self.fails else 0


def _skipped(path, root):
    try:
        parts = Path(path).relative_to(root).parts
    except ValueError:
        parts = Path(path).parts
    return any(x in SKIP_PARTS for x in parts)


def _load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception as e:
        return {"__error__": str(e)}


def _iso_to_epoch(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(s[:19], fmt))
        except Exception:
            pass
    # git's %aI is ISO-8601 with an offset
    try:
        from datetime import datetime
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


# --- check A + C -------------------------------------------------------------

def check_run_records(root, since, rep):
    found = 0
    for p in sorted(root.rglob("run_record.json")):
        if _skipped(p, root):
            continue
        if p.stat().st_mtime < since:
            continue
        found += 1
        d = _load_json(p)
        if "__error__" in d:
            rep.fail("A", p, "unreadable: %s" % d["__error__"])
            continue

        missing = [f for f in RECORD_TOP_FIELDS if f not in d]
        if missing:
            rep.fail("A", p, "missing section-D field(s): %s" % ", ".join(missing))
        for f in RECORD_GIT_FIELDS:
            if f not in (d.get("git") or {}):
                rep.fail("A", p, "missing git.%s" % f)
        for f in RECORD_RUNTIME_FIELDS:
            if f not in (d.get("runtime") or {}):
                rep.fail("A", p, "missing runtime.%s" % f)
        if not d.get("finished_at"):
            rep.fail("A", p, "record was never finished (rule 16: nothing is "
                             "reported without run_record.py finish)")

        spec = d.get("spec")
        if spec and spec.get("commit_author_date"):
            spec_t = _iso_to_epoch(spec["commit_author_date"])
            run_t = _iso_to_epoch(d.get("started_at"))
            if spec_t and run_t and spec_t > run_t:
                rep.fail("C", p, "gate spec %s was committed %s, AFTER the run "
                                 "started at %s -- the gate was not pre-registered"
                         % (spec.get("path"), spec["commit_author_date"],
                            d.get("started_at")))
    rep.ok("A/C", "%d run record(s) created during this run examined" % found)
    return found


# --- check B -----------------------------------------------------------------

def check_experiment_readmes(root, rep):
    exp = root / "corpus-lab" / "experiments"
    if not exp.exists():
        rep.ok("B", "no corpus-lab/experiments yet")
        return 0
    n = 0
    for d in sorted(x for x in exp.iterdir() if x.is_dir()):
        r = d / "README.md"
        if not r.exists():
            rep.fail("B", d, "experiment directory has no README.md")
            continue
        n += 1
        text = r.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        missing = [h for h in README_HEADINGS if h.lower() not in lowered]
        if missing:
            rep.fail("B", r, "README is missing the fixed heading(s): %s"
                     % ", ".join(missing))
    rep.ok("B", "%d experiment README(s) carry all nine fixed headings" % n)
    return n


# --- check D -----------------------------------------------------------------

def check_no_silent_overwrite(root, since, snapshot, rep):
    if not snapshot or not Path(snapshot).exists():
        rep.fail("D", snapshot or "(none)",
                 "the Phase 0 pre-existing file snapshot is missing; rule 15 "
                 "cannot be checked without it")
        return 0
    pre = set(x.strip() for x in Path(snapshot).read_text(
        encoding="utf-8").splitlines() if x.strip())
    n = 0
    for gd in GUARDED_DIRS:
        base = root / gd
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or _skipped(p, root):
                continue
            rel = p.relative_to(root).as_posix()
            if rel in APPEND_BY_DESIGN:
                continue
            if p.stat().st_mtime < since:
                continue
            n += 1
            if rel in pre:
                rep.fail("D", rel,
                         "a result file that already existed before this run was "
                         "written again. Rule 15: write a new file named for its "
                         "version and phase tag, and record `supersedes`")
    rep.ok("D", "%d result file(s) written during this run, none overwriting a "
                "pre-existing path" % n)
    return n


# --- check E -----------------------------------------------------------------

def check_scorer_outputs(root, since, rep):
    n = 0
    seen = set()
    for gd in GUARDED_DIRS:
        base = root / gd
        if not base.exists():
            continue
        for pat in SCORER_GLOBS:
            for p in sorted(base.rglob(pat)):
                if p in seen or _skipped(p, root) or p.stat().st_mtime < since:
                    continue
                seen.add(p)
                n += 1
                d = _load_json(p)
                if "__error__" in d:
                    rep.fail("E", p, "unreadable: %s" % d["__error__"])
                    continue
                for f in ("scorer_version", "key_sha256"):
                    if f not in d:
                        rep.fail("E", p, "scorer output does not name its %s "
                                         "(rule 17)" % f)
    rep.ok("E", "%d scorer output(s) name their version and key sha256" % n)
    return n


def main(argv):
    ap = argparse.ArgumentParser(prog="docs_check.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(L.RETRIEVAL_LAB))
    ap.add_argument("--since", type=float, default=None,
                    help="epoch seconds; default: corpus-lab/state/phase10_run_started.txt")
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv[1:])

    root = Path(a.root).resolve()
    since = a.since
    if since is None:
        marker = root / "corpus-lab" / "state" / "phase10_run_started.txt"
        if marker.exists():
            try:
                since = float(marker.read_text(encoding="utf-8").splitlines()[0])
            except Exception:
                since = 0.0
        else:
            since = 0.0
    snapshot = a.snapshot or str(
        root / "corpus-lab" / "state" / "phase10_preexisting_files.txt")

    print("=" * 72)
    print("docs_check  root=%s" % root)
    print("            since=%s" % time.strftime("%Y-%m-%dT%H:%M:%S",
                                                 time.localtime(since)))
    print("=" * 72)
    rep = Report(quiet=a.quiet)
    check_run_records(root, since, rep)
    check_experiment_readmes(root, rep)
    check_no_silent_overwrite(root, since, snapshot, rep)
    check_scorer_outputs(root, since, rep)
    rc = rep.render()
    print("GATE D:", "PASS" if rc == 0 else "FAIL")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
