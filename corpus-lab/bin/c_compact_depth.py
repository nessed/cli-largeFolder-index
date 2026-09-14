#!/usr/bin/env python
"""c_compact_depth.py - how often is the gold publication inside a compact list?

Phase 9.3.1 ships `find --compact 40`: the model is shown forty one-line cards
instead of twelve verbose ones, because offline the gold publication sits in the
fused top 10 on 10/17 but the top 50 on 14/17, and Experiment H (F60, F63)
measured that a model handed the longer list picks better than any statistical
reranker we tried. This records the ceiling that mechanism is working against --
if the gold family is not in the forty, no amount of reading them helps.

RECORDED, NOT GATED. One dev set carries +/-3 noise (F63).

This is a gate script: it may open the answer key, and it writes counts only.
Writes state/c_compact_depth.json.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

DEPTHS = (10, 12, 20, 40, 50, 100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(L.STACKS / "s2_fts5" / "harness_15000.db"))
    ap.add_argument("--shelf-dir", dest="shelf_dir", default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--fusion", default="rrf")
    ap.add_argument("--caption-channel", dest="caption_channel", default="lex")
    ap.add_argument("--out", default=str(L.STATE / "c_compact_depth.json"))
    a = ap.parse_args()

    ctx = CSH.get_ctx(a.db, str(Path(a.shelf_dir) / "shelf.db"), None)
    qs_by_id, answerable_ids, per_q, _counts = G.load_frozen(ctx)
    queries, n_calls = G.build_rewrites(answerable_ids, qs_by_id, L.STATE)
    if n_calls:
        print("WARNING: %d Haiku rewrite calls were made (the cache was incomplete)"
              % n_calls, file=sys.stderr)

    ranks = []
    for qid in answerable_ids:
        pq = per_q[qid]
        rels = pq["resolved_rels"]
        if not rels:
            ranks.append(None)
            continue
        fams = G._ev_families(ctx, rels)
        r, _n = G.family_rank_full(ctx, queries[qid]["queries"], fams,
                                   fusion=a.fusion,
                                   caption_channel=a.caption_channel)
        ranks.append(r)

    out = {"n_questions": len(answerable_ids),
           "shelf_dir": a.shelf_dir, "fusion": a.fusion,
           "caption_channel": a.caption_channel}
    for d in DEPTHS:
        out["gold_in_top%d_dev" % d] = G.recall_at(ranks, d)
    out["n_not_ranked_at_all"] = sum(1 for r in ranks if r is None)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
