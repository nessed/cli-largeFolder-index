#!/usr/bin/env python
"""plog.py - append ONE json line to state/progress.jsonl. Append mode only.
Usage: python bin/plog.py <phase> <step> <status> <note> [k=v ...]
Values that look numeric are coerced to int/float.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

ROOT = L.CORPUS_LAB

def main(argv):
    if len(argv) < 5:
        print("usage: plog.py <phase> <step> <status> <note> [k=v ...]", file=sys.stderr)
        return 2
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase": argv[1], "step": argv[2], "status": argv[3], "note": argv[4],
    }
    for kv in argv[5:]:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        try:
            rec[k] = int(v)
        except ValueError:
            try:
                rec[k] = float(v)
            except ValueError:
                rec[k] = v
    p = ROOT / "state" / "progress.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("LOGGED", rec["phase"], rec["step"], rec["status"])
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
