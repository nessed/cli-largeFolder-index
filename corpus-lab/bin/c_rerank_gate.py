#!/usr/bin/env python
"""c_rerank_gate.py - 2026-09-14, phase "corrected continuation", Phase 5 (A1).

Experiment A1: does a compact cross-encoder over Approach C's fused family
pool move the gold family into the top 10?

Authorised by A0 (finding F41): C2 gold-family recall@100 is 16/17 on the dev
set and 28/30 on the holdout, so the pool holds the answer and the loss is in
ranking. Pool depth is fixed at 100 -- depth 200 added nothing in either set.

Candidate generation is FROZEN: the existing do_find, the existing C2 rewrites
with rewrite index 4 dropped (A0 measured that no question is found by exactly
one rewrite index, so rewrite 4 never uniquely contributes), RRF k=60, family
fold by max, top 100 families.

The passage shown to the reranker is built from shelf metadata only: the
family's best-scoring document's title, its fiscal year, and up to 8 catalog
lines picked by content-word overlap with the query -- the existing _why_lines
rule at n=8 instead of n=2. No hand-written string of any kind. The query is
the verbatim question.

Two configurations only, no weight sweeps:
  A1   order by cross-encoder score alone
  A1b  RRF(k=60) of the A1 rank and the fused rank

Key access is confined to this file and c_offline_gate.py. Persists COUNTS and
question ids only for the dev set, and AGGREGATE COUNTS ONLY for the holdout.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402
from corpus_search import content_words  # noqa: E402

MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"
POOL = 100
DROP_REWRITE_INDEX = 4
PASSAGE_WORD_CAP = 350
CATALOG_LINES = 8
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _MODEL = TextCrossEncoder(model_name=MODEL_NAME)
    return _MODEL


def drop_rewrite_4(queries):
    if len(queries) > DROP_REWRITE_INDEX:
        return [q for i, q in enumerate(queries) if i != DROP_REWRITE_INDEX]
    return list(queries)


def catalog_lines(catalog, title, qwords, n=CATALOG_LINES):
    """_why_lines generalised to n. Same rule, same tie-break."""
    lines = [l.strip() for l in (catalog or "").splitlines() if l.strip()]
    qw = set(qwords)
    scored = []
    for l in lines:
        overlap = len(set(content_words(l)) & qw)
        if overlap > 0:
            scored.append((overlap, l))
    scored.sort(key=lambda x: -x[0])
    top = [l for _, l in scored[:n]]
    return top if top else [title]


def passage_for(ctx, fam_entry, qwords):
    best_rel = fam_entry["best_rel"]
    row = ctx.rel_to_row[best_rel]
    parts = [row["title"] or ""]
    if row["fy_primary"]:
        parts.append(row["fy_primary"])
    parts.extend(catalog_lines(ctx.rel_to_catalog.get(best_rel, ""),
                               row["title"] or "", qwords))
    text = " ".join(p for p in parts if p)
    return " ".join(text.split()[:PASSAGE_WORD_CAP])


def rerank_ranks(ctx, question, queries, gold_families):
    """Returns (fused_rank, a1_rank, a1b_rank, pool_contains_gold)."""
    res = CSH.do_find(ctx, queries, pool=200)
    pool = res["families"][:POOL]
    qwords = res["qwords"]

    fused_rank = None
    for i, f in enumerate(pool, start=1):
        if f["family"] in gold_families:
            fused_rank = i
            break
    if fused_rank is None:
        return None, None, None, False

    passages = [passage_for(ctx, f, qwords) for f in pool]
    scores = list(model().rerank(question, passages))

    order = sorted(range(len(pool)), key=lambda i: -scores[i])
    a1_rank_of = {idx: r for r, idx in enumerate(order, start=1)}

    rrf = {}
    for idx in range(len(pool)):
        rrf[idx] = 1.0 / (60 + a1_rank_of[idx]) + 1.0 / (60 + idx + 1)
    b_order = sorted(range(len(pool)), key=lambda i: (-rrf[i], i))
    a1b_rank_of = {idx: r for r, idx in enumerate(b_order, start=1)}

    gold_idx = [i for i, f in enumerate(pool) if f["family"] in gold_families]
    a1 = min(a1_rank_of[i] for i in gold_idx)
    a1b = min(a1b_rank_of[i] for i in gold_idx)
    return fused_rank, a1, a1b, True


def main():
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, answerable_ids, per_q, _ = G.load_frozen(ctx)
    rewrites, _ = G.build_rewrites(answerable_ids, qs_by_id, L.STATE)

    dev = {}
    for qid in answerable_ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            dev[qid] = {"skipped": "evidence_not_on_shelf"}
            continue
        gold = G._ev_families(ctx, pq["resolved_rels"])
        qs = rewrites.get(qid, {}).get("queries") or [pq["question"]]
        fused, a1, a1b, in_pool = rerank_ranks(ctx, pq["question"],
                                               drop_rewrite_4(qs), gold)
        dev[qid] = {"type": pq["type"], "pool_contains_gold": in_pool,
                    "fused_rank": fused, "A1_rank": a1, "A1b_rank": a1b}

    def curve(key):
        ranks = [v.get(key) for v in dev.values()]
        return {"recall_at_%d" % d: G.recall_at(ranks, d) for d in (10, 20, 50)}

    dev_report = {
        "n": len(answerable_ids),
        "pool_depth": POOL,
        "rewrite_4_dropped": True,
        "pool_recall_at_100": sum(1 for v in dev.values() if v.get("pool_contains_gold")),
        "fused_baseline": curve("fused_rank"),
        "A1": curve("A1_rank"),
        "A1b": curve("A1b_rank"),
        "per_question": dev,
    }

    # --- holdout: aggregate counts only, never a per-question rank ---------
    items, hcounts = G.holdout_rank_inputs(ctx, budget=0)
    h_fused, h_a1, h_a1b = [], [], []
    for q1, q2, gold in items:
        question = q1[0]
        fused, a1, a1b, _ = rerank_ranks(ctx, question, drop_rewrite_4(q2), gold)
        h_fused.append(fused)
        h_a1.append(a1)
        h_a1b.append(a1b)
    hold_report = dict(hcounts)
    for name, ranks in (("fused_baseline", h_fused), ("A1", h_a1), ("A1b", h_a1b)):
        hold_report[name] = {"recall_at_%d" % d: G.recall_at(ranks, d)
                             for d in (10, 20, 50)}

    report = {"model": MODEL_NAME,
              "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "dev": dev_report, "holdout": hold_report,
              "wall_s": round(time.time() - t0, 1)}
    out = L.STATE / "c_rerank_gate.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    printable = dict(report)
    printable["dev"] = {k: v for k, v in dev_report.items() if k != "per_question"}
    print(json.dumps(printable, indent=1))
    return report


if __name__ == "__main__":
    main()
