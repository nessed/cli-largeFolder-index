#!/usr/bin/env python
"""c_page_holdout.py -- one holdout page evaluation, 2026-09-15 pm.

B2c cleared its development gate, and its gate made one holdout page look
conditional on that. This is that look: the same page measurement the
development gate runs, on the 30-question frozen holdout, for the three page
methods side by side so the comparison is like for like.

**Aggregate micro/macro only.** No per-question rank, no question id, and no
evidence path ever leaves this function -- the holdout is worth only what it is
unseen.

  python -u corpus-lab/bin/c_page_holdout.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

METHODS = [("row", None), ("row+caption_first", "first"),
           ("row+caption_dense_first", "dense_first")]
TOPK = 20
LE = 5


def main():
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    hold = json.loads(G.HOLDOUT_FROZEN.read_text(encoding="utf-8"))
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    r2s = G.build_rel_to_survivor(ctx)

    items = []          # (terms, [(rel, page_index), ...]) -- no ids kept
    for qid in hold["holdout_q_ids"]:
        q = qs_by_id.get(qid)
        if not q or q["type"] == "absence":
            continue
        addrs = []
        for e in q.get("evidence_addresses", []):
            rr = G.resolve_rel(ctx, G.norm_path(e["path"]), r2s)
            if rr is not None and e.get("page_index") is not None:
                addrs.append((rr, e["page_index"]))
        if addrs:
            items.append((G.row_words_from_question(q["question"]), addrs))

    report = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "n_questions_with_addresses": len(items),
              "n_addresses": sum(len(a) for _t, a in items),
              "holdout_look": "4 of 5", "methods": {}}

    for name, chan in METHODS:
        micro_hits = micro_n = 0
        fracs = []
        for terms, addrs in items:
            hits = 0
            for rel, page in addrs:
                res = CSH.do_inside(ctx, rel, terms, k=TOPK, caption_channel=chan)
                r = None
                for i, h in enumerate(res["hits"], start=1):
                    if h["page_index"] == page:
                        r = i
                        break
                if r is not None and r <= LE:
                    hits += 1
            micro_hits += hits
            micro_n += len(addrs)
            fracs.append(hits / float(len(addrs)))
        report["methods"][name] = {
            "micro_hits": micro_hits, "micro_n": micro_n,
            "micro_pct": round(100.0 * micro_hits / micro_n, 1) if micro_n else None,
            "macro_pct": round(100.0 * sum(fracs) / len(fracs), 1) if fracs else None,
        }
        print("%-26s %d/%d micro=%s macro=%s" % (
            name, micro_hits, micro_n, report["methods"][name]["micro_pct"],
            report["methods"][name]["macro_pct"]), flush=True)

    report["wall_s"] = round(time.time() - t0, 1)
    (L.STATE / "c_page_holdout.json").write_text(json.dumps(report, indent=1),
                                                 encoding="utf-8")
    print("WROTE state/c_page_holdout.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
