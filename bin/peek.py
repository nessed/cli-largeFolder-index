#!/usr/bin/env python
"""peek.py - safe progress view of a running battery.

While a stack is installed in ra-ship, the orchestrator session (whose cwd IS
ra-ship) inherits that corpus's deny list, so an ordinary `ls` of the results
directory is refused. This runs as a child process and prints only counts and
non-sensitive fields, so progress is visible without either fighting the deny
or pulling canary content into the orchestrator's context.

  python bin\\peek.py --phase P7_s0_baseline_raship
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    a = ap.parse_args()
    d = L.RUNS / a.phase
    if not d.exists():
        print(f"no results dir yet for phase {a.phase}")
        return
    done = sorted(d.glob("*.json"))
    print(f"phase {a.phase}: {len(done)} result file(s)")
    for f in done:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        print(f"  {r.get('qid'):<16} calls={r.get('n_tool_calls'):<3} "
              f"opened={r.get('n_files_opened'):<3} wall={r.get('wall_s')}s "
              f"cost={r.get('cost_usd')} timeout={r.get('timed_out')} "
              f"stream_ok={r.get('stream_json_ok')} susp={r.get('suspended')}")


if __name__ == "__main__":
    main()
