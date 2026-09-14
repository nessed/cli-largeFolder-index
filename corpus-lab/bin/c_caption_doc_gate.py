#!/usr/bin/env python
"""c_caption_doc_gate.py -- Experiment G and ED3, 2026-09-15 evening.

Mechanism and gate are specified in state/experiment_g_spec.md, committed
before this was run. Reranks the frozen configuration's top-100 pool by the
maximum cosine between the query's label words and any caption in a family.

  python -u corpus-lab/bin/c_caption_doc_gate.py [--holdout1] [--ed3]

Counts, ranks and question ids only.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

POOL = 100
FROZEN_FUSION = "rrf"
FROZEN_CAPTION_CHANNEL = "lex"
TOPK_PAGE = 5


# ------------------------------------------------------------------ #
# caption vectors, grouped by family once per process
# ------------------------------------------------------------------ #
_CAP = {}


def _cap_index(ctx):
    """family -> row indices into captions.f16.npy."""
    if _CAP:
        return _CAP
    import numpy as np
    base = Path(ctx.shelf_path).parent
    vecs = np.load(base / "captions.f16.npy").astype("float32")
    fam_rows = {}
    for i, line in enumerate((base / "captions_ids.jsonl").read_text(
            encoding="utf-8").splitlines()):
        rec = json.loads(line)
        fam = ctx.rel_to_family.get(rec["rel"])
        if fam:
            fam_rows.setdefault(fam, []).append(i)
    _CAP["vecs"] = vecs
    _CAP["fam_rows"] = {f: np.asarray(r, dtype="int64") for f, r in fam_rows.items()}
    return _CAP


def label_vec(query):
    import numpy as np
    words = CSH._label_words(query)
    if not words:
        return None
    v = np.asarray(next(iter(CSH._model().embed([" ".join(words)]))), dtype="float32")
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def caption_scores(ctx, queries, families):
    """family -> max cosine over queries and over that family's captions."""
    import numpy as np
    idx = _cap_index(ctx)
    vecs, fam_rows = idx["vecs"], idx["fam_rows"]
    qvs = [v for v in (label_vec(q) for q in queries) if v is not None]
    out = {}
    if not qvs:
        return out
    Q = np.vstack(qvs)
    for fam in families:
        rows = fam_rows.get(fam)
        if rows is None or len(rows) == 0:
            continue
        sims = vecs[rows] @ Q.T          # (n_captions, n_queries)
        out[fam] = float(sims.max())
    return out


def table_like(question):
    """The three generic signals already in c_offline_gate. Question text only."""
    if G.FY_RE.search(question):
        return True
    if G._ROW_SEP_RE.search(question):
        return True
    low = set(question.lower().split())
    return bool(low & G._TRAJECTORY_FILLER)


def ranked_families(ctx, queries, mode, question):
    """Returns the family ranking under 'frozen', 'G1' or 'G2'."""
    res = CSH.do_find(ctx, queries, fusion=FROZEN_FUSION,
                      caption_channel=FROZEN_CAPTION_CHANNEL)
    fused = [f["family"] for f in res["families"]]
    if mode == "frozen":
        return fused
    if mode == "G2" and not table_like(question):
        return fused

    pool = fused[:POOL]
    cs = caption_scores(ctx, queries, pool)
    cap_rank = sorted(cs, key=lambda f: -cs[f])

    scores = {}
    for r, fam in enumerate(pool, start=1):
        scores[fam] = scores.get(fam, 0.0) + 1.0 / (60 + r)
    for r, fam in enumerate(cap_rank, start=1):
        scores[fam] = scores.get(fam, 0.0) + 1.0 / (60 + r)
    reranked = sorted(pool, key=lambda f: (-scores[f], fused.index(f)))
    return reranked + fused[POOL:]


def rank_of(ranking, gold):
    for i, f in enumerate(ranking, start=1):
        if f in gold:
            return i
    return None


def dev_ranks(ctx, ids, per_q, queries_by_qid, mode):
    out = {}
    for qid in ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            out[qid] = None
            continue
        gold = G._ev_families(ctx, pq["resolved_rels"])
        out[qid] = rank_of(ranked_families(ctx, queries_by_qid[qid], mode,
                                           pq["question"]), gold)
    return out


def above_gold_kinds(ctx, ids, per_q, queries_by_qid, mode):
    totals = {"singleton": 0, "fy": 0}
    for qid in ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            continue
        gold = G._ev_families(ctx, pq["resolved_rels"])
        for fam in ranked_families(ctx, queries_by_qid[qid], mode, pq["question"]):
            if fam in gold:
                break
            _e, _n, kind = CSH._editions_for_family(ctx, fam)
            totals[kind] = totals.get(kind, 0) + 1
    return totals


def holdout1_ranks(ctx, mode):
    """ONE aggregate look. Returns counts only; no ids, no per-question rank."""
    items, counts = G.holdout_rank_inputs(ctx, budget=0)
    ranks = []
    for _q1, q2, fams in items:
        # holdout_rank_inputs hands back no question text beyond the queries;
        # q2[0] is the verbatim question, which is what table_like needs.
        ranks.append(rank_of(ranked_families(ctx, q2, mode, q2[0]), fams))
    return {"n_measurable": counts["n_measurable"],
            "curve": {"recall_at_%d" % d: G.recall_at(ranks, d) for d in G.RECALL_DEPTHS}}


def run_ed3(ctx, per_q, ids):
    n_hit, sizes = 0, []
    per_question = {}
    year_ids = []
    for qid in ids:
        pq = per_q[qid]
        m = G.FY_RE.search(pq["question"])
        if not m:
            continue
        year_ids.append(qid)
        fy = m.group(1)
        rels = pq["resolved_rels"]
        counts = {}
        for r in rels:
            f = ctx.rel_to_family.get(r)
            if f:
                counts[f] = counts.get(f, 0) + 1
        if not counts:
            continue
        fam = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        row_words = G.row_words_from_question(pq["question"])
        primaries = [ctx.rel_to_row[r] for r in ctx.family_to_rels.get(fam, ())
                     if ctx.rel_to_row[r]["is_primary"]]
        sel = []
        for r in primaries:
            ins = CSH.do_inside(ctx, r["rel"], row_words, k=TOPK_PAGE,
                                caption_channel="dense_first")
            for h in ins["hits"][:TOPK_PAGE]:
                row = ctx.db.execute(
                    "SELECT body FROM pages WHERE rel=? AND page_index=?",
                    (r["rel"], h["page_index"])).fetchone()
                if row and fy in (row[0] or ""):
                    sel.append(r)
                    break
        sel_keys = {r["edition_key"] for r in sel}
        ev_keys = [ctx.rel_to_row[r]["edition_key"] for r in rels if r in ctx.rel_to_row]
        all_in = bool(ev_keys) and all(k in sel_keys for k in ev_keys)
        if all_in:
            n_hit += 1
        sizes.append(len(sel))
        per_question[qid] = {"set_size": len(sel), "all_evidence_editions_in_set": all_in,
                             "family_primaries": len(primaries)}
    return {"page_method": "B2c dense_first", "n_year_bearing_questions": len(year_ids),
            "set_recall_questions": n_hit,
            "mean_set_size": round(sum(sizes) / float(len(sizes)), 2) if sizes else None,
            "max_set_size": max(sizes) if sizes else None,
            "per_question": per_question}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout1", action="store_true")
    ap.add_argument("--ed3", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, ids, per_q, _ = G.load_frozen(ctx)
    rewrites, _ = G.build_rewrites(ids, qs_by_id, L.STATE)
    c2q = {q: rewrites.get(q, {}).get("queries") or [per_q[q]["question"]] for q in ids}

    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "pool": POOL, "n": len(ids), "dev": {}}

    for mode in ("frozen", "G1", "G2"):
        r = dev_ranks(ctx, ids, per_q, c2q, mode)
        vals = list(r.values())
        out["dev"][mode] = {
            "curve": {"recall_at_%d" % d: G.recall_at(vals, d) for d in G.RECALL_DEPTHS},
            "family_le_10": G.recall_at(vals, 10),
            "per_question_rank": r,
        }
        print("dev %-6s le10=%d curve=%s" % (mode, out["dev"][mode]["family_le_10"],
                                             out["dev"][mode]["curve"]), flush=True)

    g1, g2 = out["dev"]["G1"]["family_le_10"], out["dev"]["G2"]["family_le_10"]
    chosen = "G2" if g2 > g1 else "G1"          # ties -> G1, the simpler rule
    out["chosen_on_dev"] = chosen
    out["n_table_like"] = sum(1 for q in ids if table_like(per_q[q]["question"]))

    out["diagnostic_above_gold"] = above_gold_kinds(ctx, ids, per_q, c2q, chosen)

    # how many of the live battery's 9 L0 questions now reach the top 10
    try:
        fr = json.loads((L.STATE / "c_live_forensics.json").read_text(encoding="utf-8"))
        l0 = [q for q, v in fr["per_question"].items()
              if v.get("class") == "L0_family_not_surfaced"]
        ranks = out["dev"][chosen]["per_question_rank"]
        out["live_L0_questions"] = len(l0)
        out["live_L0_now_in_top10"] = sum(
            1 for q in l0 if ranks.get(q) is not None and ranks[q] <= 10)
    except Exception as e:
        out["live_L0_diagnostic_error"] = str(e)

    if a.holdout1:
        out["holdout1"] = holdout1_ranks(ctx, chosen)
        out["holdout1_look"] = "5 of 5 -- holdout-1 retired for this branch"
        print("holdout1 (%s): %s" % (chosen, json.dumps(out["holdout1"]["curve"])), flush=True)

    out["wall_s"] = round(time.time() - t0, 1)
    (L.STATE / "c_caption_doc_gate.json").write_text(json.dumps(out, indent=1),
                                                     encoding="utf-8")
    print("chosen=%s dev_le10=%d  L0_recovered=%s/%s"
          % (chosen, out["dev"][chosen]["family_le_10"],
             out.get("live_L0_now_in_top10"), out.get("live_L0_questions")))

    if a.ed3:
        ed3 = run_ed3(ctx, per_q, ids)
        (L.STATE / "c_edition_set_v3.json").write_text(json.dumps(ed3, indent=1),
                                                       encoding="utf-8")
        print("ED3 set_recall=%d of %d mean_set=%s max=%s"
              % (ed3["set_recall_questions"], ed3["n_year_bearing_questions"],
                 ed3["mean_set_size"], ed3["max_set_size"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
