#!/usr/bin/env python
"""p10_score_all.py - one recording, four scorers, zero model calls.

Plan E rule 18. A live session is run once and recorded once; every scorer
derives from that recording. No model call is ever made to score.

  v1 strict   the frozen reference (its number is read out of v2's copy, since
              c_score_live.py overwrites state/c_live_battery.json -- Plan D's
              trap list says to restore that file afterwards, so this script
              never runs v1 directly)
  v2          the pre-registered instrument every Phase 9 verdict came from
  v3 key v1   tonight's corrected scorer
  v3 key v2   the same, against the versioned key with expected vectors

  python p10_score_all.py --phase P10S1_live [--max-turns 60]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

KEY_V2 = L.HARNESS_KEYS / "answer_key_v2_2026-09-16.json"


def run(cmd):
    print("  $ %s" % " ".join(Path(c).name if "/" in str(c) or "\\" in str(c)
                              else str(c) for c in cmd), flush=True)
    p = subprocess.run([str(c) for c in cmd], cwd=str(L.RETRIEVAL_LAB),
                       capture_output=True, text=True, errors="replace",
                       timeout=3600)
    if p.returncode != 0:
        print("    rc=%d\n%s" % (p.returncode, (p.stderr or "")[-800:]),
              file=sys.stderr)
    return p.returncode


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--abs-phase", dest="abs_phase", default="P5_live_abs")
    ap.add_argument("--max-turns", dest="max_turns", type=int, default=60)
    a = ap.parse_args(argv[1:])

    py = sys.executable
    bin_ = L.BIN
    rcs = {}

    print("scoring %s -- four scorers, one recording" % a.phase)
    rcs["v2"] = run([py, bin_ / "c_score_live_v2.py", "--phase", a.phase,
                     "--abs-phase", a.abs_phase, "--max-turns", a.max_turns])
    rcs["v3_keyv1"] = run([py, bin_ / "c_score_live_v3.py", "--phase", a.phase,
                           "--abs-phase", a.abs_phase,
                           "--max-turns", a.max_turns])
    if KEY_V2.exists():
        rcs["v3_keyv2"] = run([py, bin_ / "c_score_live_v3.py", "--phase", a.phase,
                               "--abs-phase", a.abs_phase,
                               "--max-turns", a.max_turns,
                               "--key", KEY_V2, "--tag", "keyv2"])
    else:
        print("  key v2 absent -- skipping the keyv2 pass", file=sys.stderr)

    # v1 strict: read out of v2's own copy rather than re-running the frozen
    # scorer, which would overwrite state/c_live_battery.json.
    v2 = json.loads((L.STATE / ("c_live_battery_v2__%s.json" % a.phase)
                     ).read_text(encoding="utf-8"))
    v3 = json.loads((L.STATE / ("c_live_battery_v3__%s.json" % a.phase)
                     ).read_text(encoding="utf-8"))
    print("\n%-28s v2      v3" % a.phase)
    for k in ("cited_right_page_strict", "cited_right_page_equiv",
              "cited_unopened_total", "mentioned_unopened_total",
              "n_answer_fragments", "n_opens_loop_only_total",
              "absence_ok3_frozen3", "total_cost_usd"):
        print("  %-26s %-7s %s" % (k, v2.get(k, "-"), v3.get(k, "-")))
    print("  %-26s %-7s %s" % ("value_correct",
                               "%s/17" % v2.get("value_correct"),
                               v3.get("value_correct_of")))
    if KEY_V2.exists():
        kv = json.loads((L.STATE / ("c_live_battery_v3__%s__keyv2.json" % a.phase)
                         ).read_text(encoding="utf-8"))
        print("  %-26s %-7s %s" % ("vector_full", "-", kv.get("vector_full_of")))
    print("\nreturn codes: %s" % json.dumps(rcs))
    return 0 if all(v == 0 for v in rcs.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
