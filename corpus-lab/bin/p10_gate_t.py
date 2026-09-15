#!/usr/bin/env python
"""p10_gate_t.py - read Gate T against its pre-registered spec.

corpus-lab/state/phase10_gate_t_spec.md was committed before v3 was run against
any recorded battery. This script evaluates its eight rows and writes the verdict
to corpus-lab/state/phase10_gate_t_result.json. It does not modify v3 and it does
not modify any recorded number; a failed row is recorded with its actual value.

  python p10_gate_t.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

SPEC = L.STATE / "phase10_gate_t_spec.md"
OUT = L.STATE / "phase10_gate_t_result.json"


def agg(scorer, phase):
    return json.loads((L.STATE / ("c_live_battery_%s__%s.json" % (scorer, phase))
                       ).read_text(encoding="utf-8"))


def per_q(phase):
    d = json.loads((L.SCORES / ("live_v3__%s.json" % phase)).read_text(encoding="utf-8"))
    return {r["q_id"]: r for r in d["answerable"] if "status" not in r}


def main():
    tests = subprocess.run(
        [sys.executable, "-m", "pytest",
         str(L.CORPUS_LAB / "tests" / "test_score_live_v3.py"), "-q"],
        capture_output=True, text=True, cwd=str(L.RETRIEVAL_LAB), timeout=900)
    tests_pass = tests.returncode == 0
    tests_line = (tests.stdout or "").strip().splitlines()[-1:] or [""]

    v2 = {p: agg("v2", p) for p in ("P8_live", "P9S_live", "P9O_live")}
    v3 = {p: agg("v3", p) for p in ("P8_live", "P9S_live", "P9O_live")}
    opus_rows = per_q("P9O_live")
    opus_unopened_qs = sorted(q for q, r in opus_rows.items() if r.get("cited_unopened"))

    rows = [
        ("T1", "all regression tests in test_score_live_v3.py pass",
         tests_pass, tests_line[0]),
        ("T2", "v3 on P8_live reproduces v2 cited_right_page_equiv exactly",
         v3["P8_live"]["cited_right_page_equiv"] == v2["P8_live"]["cited_right_page_equiv"],
         "v2=%s v3=%s" % (v2["P8_live"]["cited_right_page_equiv"],
                          v3["P8_live"]["cited_right_page_equiv"])),
        ("T3", "v3 on P8_live reproduces v2 cited_unopened_total exactly",
         v3["P8_live"]["cited_unopened_total"] == v2["P8_live"]["cited_unopened_total"],
         "v2=%s v3=%s" % (v2["P8_live"]["cited_unopened_total"],
                          v3["P8_live"]["cited_unopened_total"])),
        ("T4", "v3 P9S_live cited_right_page_equiv within +/-1 of v2's 13",
         abs(v3["P9S_live"]["cited_right_page_equiv"] - 13) <= 1,
         "v2=13 v3=%s" % v3["P9S_live"]["cited_right_page_equiv"]),
        ("T5", "v3 P9O_live cited_right_page_equiv within +/-1 of v2's 14",
         abs(v3["P9O_live"]["cited_right_page_equiv"] - 14) <= 1,
         "v2=14 v3=%s" % v3["P9O_live"]["cited_right_page_equiv"]),
        ("T6", "v3 cited_unopened_total reads Sonnet 0, Opus 2",
         (v3["P9S_live"]["cited_unopened_total"] == 0
          and v3["P9O_live"]["cited_unopened_total"] == 2),
         "Sonnet=%s Opus=%s" % (v3["P9S_live"]["cited_unopened_total"],
                                v3["P9O_live"]["cited_unopened_total"])),
        ("T7", "both Opus cited_unopened counts fall in mb_04",
         opus_unopened_qs == ["mb_04"],
         "Opus violations in: %s" % (opus_unopened_qs or "(none)")),
        ("T8", "value_correct reads 5/5 for both P9 batteries, n_keyed == 5",
         (v3["P9S_live"]["value_correct_of"] == "5/5"
          and v3["P9O_live"]["value_correct_of"] == "5/5"
          and v3["P9S_live"]["n_keyed"] == 5 and v3["P9O_live"]["n_keyed"] == 5),
         "Sonnet=%s Opus=%s n_keyed=%s/%s" % (
             v3["P9S_live"]["value_correct_of"], v3["P9O_live"]["value_correct_of"],
             v3["P9S_live"]["n_keyed"], v3["P9O_live"]["n_keyed"])),
    ]

    failed = [r[0] for r in rows if not r[2]]
    verdict = "PASS" if not failed else "GATE_T_STOP"

    # Plan E section 7: skip Phase 4 only if Gate T stops AND v3 moved the
    # headline equivalence count by more than +/-1 on either P9 battery.
    moved = max(abs(v3["P9S_live"]["cited_right_page_equiv"] - 13),
                abs(v3["P9O_live"]["cited_right_page_equiv"] - 14))
    skip_phase4 = (verdict != "PASS") and moved > 1

    rec = {
        "gate": "T",
        "spec": str(SPEC.relative_to(L.RETRIEVAL_LAB)).replace("\\", "/"),
        "spec_commit": subprocess.run(
            ["git", "-C", str(L.RETRIEVAL_LAB), "log", "-1", "--format=%H", "--",
             "corpus-lab/state/phase10_gate_t_spec.md"],
            capture_output=True, text=True).stdout.strip(),
        "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": verdict,
        "rows_failed": failed,
        "rows": [{"id": r[0], "check": r[1], "pass": bool(r[2]), "actual": r[3]}
                 for r in rows],
        "headline_equivalence_moved_by": moved,
        "skip_phase4": skip_phase4,
        "phase4_rule": ("Plan E section 7: Phase 4 is skipped only if Gate T stops AND "
                        "v3's equivalence count differs from v2 by more than +/-1 on "
                        "either P9 battery. It moved by %d, so Phase 4 proceeds and "
                        "scores with BOTH v2 and v3." % moved),
        "v3_is_not_modified": ("Plan E section 1.6 and section 7: a failed Gate T row is "
                               "recorded, not repaired. v3 is frozen as it stands."),
    }
    OUT.write_text(json.dumps(rec, indent=1), encoding="utf-8")

    print("=" * 72)
    print("GATE T: %s" % verdict)
    print("=" * 72)
    for r in rows:
        print("  [%s] %-4s %s" % ("PASS" if r[2] else "FAIL", r[0], r[1]))
        print("          actual: %s" % r[3])
    print()
    print("headline equivalence moved by: %d (bar for skipping Phase 4: > 1)" % moved)
    print("skip Phase 4: %s" % skip_phase4)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
