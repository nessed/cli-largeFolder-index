#!/usr/bin/env python
"""c_fusion_gate.py -- Experiment C, 2026-09-15.

Per-query selection ("best") against reciprocal-rank summation ("rrf") for the
document channel. Reads the answer key and the frozen question sample only
through c_offline_gate's existing loaders, and writes nothing but ranks,
counts and question ids.

  python -u corpus-lab/bin/c_fusion_gate.py [--holdout]

Pre-registered gate (fixed before measuring, see the 2026-09-15 master prompt):
  PASS  >=12/17 and holdout >=17/30
  WEAK  10-11/17 and holdout >=16/30
  STOP  <=9/17 or holdout <16/30
The rule with the higher development count (ties -> rrf) is the fusion rule for
the rest of the run.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

RULES = ("rrf", "best")
BASELINE_HOLDOUT_RRF_LE10 = 14  # F41, already measured; costs no new look


def dev_ranks(ctx, answerable_ids, per_q, queries_by_qid, fusion):
    ranks = {}
    for qid in answerable_ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            ranks[qid] = None
            continue
        fams = G._ev_families(ctx, pq["resolved_rels"])
        r, _ = G.family_rank_full(ctx, queries_by_qid[qid], fams, fusion=fusion)
        ranks[qid] = r
    return ranks


def above_gold_kinds(ctx, answerable_ids, per_q, queries_by_qid, fusion):
    """Aggregate only: across all questions, what KIND of family outranks the
    gold one. 'fy' families carry dated primaries, 'singleton' ones do not --
    the question is whether per-query selection is being crowded out by dated
    editions or by undated one-offs."""
    totals = {"singleton": 0, "fy": 0}
    n_q = 0
    for qid in answerable_ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            continue
        fams = G._ev_families(ctx, pq["resolved_rels"])
        res = CSH.do_find(ctx, queries_by_qid[qid], fusion=fusion)
        for f in res["families"]:
            if f["family"] in fams:
                n_q += 1
                break
            totals[f["kind"]] = totals.get(f["kind"], 0) + 1
    return {"n_questions_gold_found": n_q,
            "families_above_gold_kind_singleton": totals["singleton"],
            "families_above_gold_kind_fy": totals["fy"]}


def main(argv):
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, answerable_ids, per_q, _ = G.load_frozen(ctx)
    rewrites, _ = G.build_rewrites(answerable_ids, qs_by_id, L.STATE)
    c2q = {q: rewrites.get(q, {}).get("queries") or [per_q[q]["question"]]
           for q in answerable_ids}

    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n": len(answerable_ids), "queries": "C2", "dev": {}}

    for rule in RULES:
        ranks = dev_ranks(ctx, answerable_ids, per_q, c2q, rule)
        vals = list(ranks.values())
        out["dev"][rule] = {
            "curve": {"recall_at_%d" % d: G.recall_at(vals, d) for d in G.RECALL_DEPTHS},
            "family_le_10": G.recall_at(vals, 10),
            "per_question_rank": ranks,
        }
        print("dev %-5s le10=%d curve=%s" % (
            rule, out["dev"][rule]["family_le_10"], out["dev"][rule]["curve"]))

    le10 = {r: out["dev"][r]["family_le_10"] for r in RULES}
    better = "best" if le10["best"] > le10["rrf"] else "rrf"   # ties -> rrf
    out["better_rule_dev"] = better
    out["dev_family_le_10"] = le10

    out["diagnostic_above_gold"] = above_gold_kinds(
        ctx, answerable_ids, per_q, c2q, better)
    print("diagnostic(%s): %s" % (better, out["diagnostic_above_gold"]))

    if "--holdout" in argv:
        if better == "rrf":
            out["holdout"] = {"fusion": "rrf", "recall_at_10": BASELINE_HOLDOUT_RRF_LE10,
                              "source": "F41, already measured; no new look spent"}
            out["holdout_look_spent"] = 0
        else:
            h = G.holdout_curve_for_config(ctx, fusion=better, budget=0)
            out["holdout"] = h
            out["holdout_look_spent"] = 1
        print("holdout: %s" % json.dumps(out["holdout"]))

    out["wall_s"] = round(time.time() - t0, 1)
    (L.STATE / "c_fusion_gate.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("WROTE state/c_fusion_gate.json  wall=%ss" % out["wall_s"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
