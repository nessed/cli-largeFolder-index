#!/usr/bin/env python
"""c_caption_gate.py -- Experiments E1 and E2, 2026-09-15.

Does the caption line work as a DOCUMENT-level retrieval channel at corpus
scale? E1 adds a lexical caption list to every query's fusion inputs; E2 adds
a dense one as well. Both are measured against the frozen document baseline
(C2 + rrf: 9/17 on the development set, 14/30 on the holdout).

  python -u corpus-lab/bin/c_caption_gate.py --channel lex [--holdout]
  python -u corpus-lab/bin/c_caption_gate.py --channel lex+vec [--holdout]

Pre-registered gate, identical for E1 and E2, against the best configuration so
far:  PASS >=12/17 and holdout >=17/30;  WEAK 10-11/17 and holdout >=16/30;
STOP otherwise.

Writes ranks, counts and question ids only.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

STATE_FILE = "c_caption_family_gate.json"
JOINT_DEPTH = 20


def measure(ctx, answerable_ids, per_q, queries_by_qid, channel, fusion="rrf"):
    ranks = {}
    n_empty_all_queries = 0
    joint_hits = 0
    n_joint_measurable = 0
    for qid in answerable_ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            ranks[qid] = None
            continue
        fams = G._ev_families(ctx, pq["resolved_rels"])
        qs = queries_by_qid[qid]
        r, _ = G.family_rank_full(ctx, qs, fams, fusion=fusion,
                                  caption_channel=channel)
        ranks[qid] = r

        # --- caption-channel diagnostics, aggregate only ------------------
        union_pages, any_caption = set(), False
        for q in qs:
            _, pages = CSH._cap_search(ctx, q, 200)
            if channel == "lex+vec":
                _, vpages = CSH._cap_vec_search(ctx, q, 200)
                pages = list(pages) + list(vpages)
            if pages:
                any_caption = True
            union_pages.update(pages[:JOINT_DEPTH])
        if not any_caption:
            n_empty_all_queries += 1
        gold_addrs = {(a["rel"], a["page_index"]) for a in pq["page_addresses"]}
        if gold_addrs:
            n_joint_measurable += 1
            if gold_addrs & union_pages:
                joint_hits += 1

    vals = list(ranks.values())
    return {
        "caption_channel": channel, "fusion": fusion,
        "curve": {"recall_at_%d" % d: G.recall_at(vals, d) for d in G.RECALL_DEPTHS},
        "family_le_10": G.recall_at(vals, 10),
        "n_questions_caption_lists_empty_for_every_query": n_empty_all_queries,
        "joint_diagnostic_gold_page_in_top%d_caption_union" % JOINT_DEPTH: joint_hits,
        "n_joint_measurable": n_joint_measurable,
        "per_question_rank": ranks,
    }


def main(argv):
    t0 = time.time()
    channel = argv[argv.index("--channel") + 1] if "--channel" in argv else "lex"
    if channel not in ("lex", "lex+vec"):
        raise SystemExit("--channel must be lex or lex+vec")

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, answerable_ids, per_q, _ = G.load_frozen(ctx)
    rewrites, _ = G.build_rewrites(answerable_ids, qs_by_id, L.STATE)
    c2q = {q: rewrites.get(q, {}).get("queries") or [per_q[q]["question"]]
           for q in answerable_ids}

    res = measure(ctx, answerable_ids, per_q, c2q, channel)
    res["n"] = len(answerable_ids)
    print("dev %-8s le10=%d curve=%s" % (channel, res["family_le_10"], res["curve"]))
    print("  caption lists empty for every query on %d question(s)"
          % res["n_questions_caption_lists_empty_for_every_query"])
    print("  joint: gold (file,page) in top-%d caption union on %d of %d"
          % (JOINT_DEPTH,
             res["joint_diagnostic_gold_page_in_top%d_caption_union" % JOINT_DEPTH],
             res["n_joint_measurable"]))

    if "--holdout" in argv:
        res["holdout"] = G.holdout_curve_for_config(
            ctx, fusion="rrf", caption_channel=channel, budget=0)
        res["holdout_look_spent"] = 1
        print("  holdout: %s" % json.dumps(res["holdout"]["curve"]))

    res["wall_s"] = round(time.time() - t0, 1)
    path = L.STATE / STATE_FILE
    prev = {}
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    prev[channel] = res
    path.write_text(json.dumps(prev, indent=1), encoding="utf-8")
    print("WROTE state/%s [%s]  wall=%ss" % (STATE_FILE, channel, res["wall_s"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
