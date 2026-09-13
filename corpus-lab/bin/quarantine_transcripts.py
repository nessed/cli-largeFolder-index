#!/usr/bin/env python
"""quarantine_transcripts.py - grid-run phase 2, the route the spec did not list.

Phase 1.4 assumes moving the lab changes the `.claude/projects/` key and so puts
old transcripts out of a test session's reach. That is true for the harness --
its cwd moved. It is NOT true for ra-ship, which deliberately does not move. Every
ra-ship measurement session runs with cwd = the ra-ship root, so it runs under
exactly the project key whose transcript directory already contains night-1
sessions that quote all 13 canary phrases and their planted paths.

A deny rule alone is not enough here: under S0 there is no hook, Bash is
unrestricted, and the transcript store sits outside every path pattern the phase
2.5 backstop covers. So the files are physically moved into the private tree.

This session's own transcript is left alone -- it is open, and moving it would
break the run. Files are selected by mtime older than --since, which is the start
of this orchestration session.

  python bin\\quarantine_transcripts.py --since 2026-09-12T01:33 --apply
"""
import argparse
import csv
import datetime as dt
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

PROJECTS = Path.home() / ".claude" / "projects"


def load_phrases():
    phrases = []
    with open(L.canary_manifest(), newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            p = (r.get("canary_phrase") or r.get("phrase") or "").strip()
            if p:
                phrases.append(p)
    return phrases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True,
                    help="ISO timestamp; files modified AFTER this are left alone")
    ap.add_argument("--apply", action="store_true", help="actually move (default: dry run)")
    a = ap.parse_args()
    cutoff = dt.datetime.fromisoformat(a.since).timestamp()

    phrases = load_phrases()
    dest = L.PRIVATE / "results" / "_transcript_quarantine"
    report = {"cutoff": a.since, "n_phrases": len(phrases), "moved": [],
              "left_open": [], "scanned": 0}

    for f in sorted(PROJECTS.rglob("*.jsonl")):
        report["scanned"] += 1
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        n = sum(1 for p in phrases if p in t)
        if not n:
            continue
        rec = {"file": str(f), "project_key": f.parent.name, "phrases": n,
               "mtime": dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")}
        if f.stat().st_mtime > cutoff:
            # This session's own live transcript. Cannot be moved while open.
            report["left_open"].append(rec)
            continue
        if a.apply:
            tgt = dest / f.parent.name / f.name
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(tgt))
            rec["moved_to"] = str(tgt)
        report["moved"].append(rec)

    out = L.STATE / "transcript_quarantine.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    verb = "MOVED" if a.apply else "would move (dry run)"
    print(f"scanned {report['scanned']} transcripts")
    print(f"{verb}: {len(report['moved'])} containing canary phrases")
    for r in report["moved"][:5]:
        print(f"   {r['project_key']}/{Path(r['file']).name}  ({r['phrases']} phrases)")
    if len(report["moved"]) > 5:
        print(f"   ... and {len(report['moved']) - 5} more")
    print(f"left open (this session, newer than cutoff): {len(report['left_open'])}")
    for r in report["left_open"]:
        print(f"   {r['project_key']}/{Path(r['file']).name}  mtime={r['mtime']}")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
