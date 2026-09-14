#!/usr/bin/env python
"""c_route_gate.py -- 2026-09-15 pm, Phase 1.3.

Settles a dispute between two numbers this repository publishes. The shelf's
absence control has said 11/11 and 4/4 since it was built. The end-to-end chain
routed 1 of 3 frozen absence questions correctly (F52). Both cannot be right
unless they are measuring different things -- and they are.

This runs ROUTE **alone**, through the chain's own `route_absent`, over every
absence question in the key, split by kind:

  document level   the question names a fiscal year  -> `have`
  identifier level it names a literal identifier only -> `exact`

The overnight chain implemented only the first, so every identifier-level
question was silently routed "present" without being looked at. The exact path
is now added; this measures both, and re-derives the published 11/11 from the
chain's code path rather than from the control's.

  python -u corpus-lab/bin/c_route_gate.py

Counts, ids and booleans only.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402
import c_chain_gate as CH  # noqa: E402


def main():
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen = set(sample["q_ids"])

    absence = [q for q in key["questions"] if q["type"] == "absence"]
    per_q = {}
    for q in absence:
        doc_level = bool(G.FY_RE.search(q["question"]))
        absent, why = CH.route_absent(ctx, q["question"])
        per_q[q["q_id"]] = {
            "kind": "document_level" if doc_level else "identifier_level",
            "in_frozen_sample": q["q_id"] in frozen,
            "routed_absent": bool(absent), "reason": why,
        }

    def count(pred):
        sel = [v for v in per_q.values() if pred(v)]
        return sum(1 for v in sel if v["routed_absent"]), len(sel)

    doc_ok, doc_n = count(lambda v: v["kind"] == "document_level")
    id_ok, id_n = count(lambda v: v["kind"] == "identifier_level")
    fro_ok, fro_n = count(lambda v: v["in_frozen_sample"])
    all_ok, all_n = count(lambda v: True)

    # What the overnight chain would have scored: identifier-level questions
    # were never routed, so they could only ever come out "present".
    old_fro = sum(1 for v in per_q.values()
                  if v["in_frozen_sample"] and v["kind"] == "document_level"
                  and v["routed_absent"])

    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "document_level": {"routed_absent": doc_ok, "n": doc_n},
        "identifier_level": {"routed_absent": id_ok, "n": id_n},
        "frozen_sample": {"routed_absent": fro_ok, "n": fro_n},
        "all_absence": {"routed_absent": all_ok, "n": all_n},
        "overnight_chain_equivalent_on_frozen": {"routed_absent": old_fro, "n": fro_n},
        "note": ("The overnight chain (F52) scored 1 of 3 because 2 of the 3 frozen absence "
                 "questions are identifier level and its ROUTE had no exact path. That is a "
                 "chain implementation gap, not a ROUTE failure."),
        "per_question": per_q,
        "wall_s": round(time.time() - t0, 1),
    }
    (L.STATE / "c_route_gate.json").write_text(json.dumps(report, indent=1),
                                               encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_question"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
