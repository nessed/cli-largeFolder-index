#!/usr/bin/env python
"""c_series_gate_v3.py -- S2 and ED2, 2026-09-15.

F42 showed `series_ok` was never measuring page retrieval: the years lined up on
21 of 24 addresses but the file the walk opened was the one the key cites on
only 3 of them. It was measuring which copy the shelf calls canonical. Both
measurements here replace that with something that can actually move.

S2 -- vintage-tolerant series.  A question about fiscal year Y is answered by
whichever edition happens to PRINT year Y's row, and F43 measured that this is
"usually a later one". So for each key year Y the candidate editions are the
family's primaries with fy_primary in [Y, Y+2] -- a window fixed in advance from
F43 and deliberately not widened -- and a hit is the key's (file, page) turning
up in the top 5 pages of any candidate whose body carries Y.

  strict   the returned page IS the key's (file, page)
  tolerant the returned page is in a file sharing the cited file's edition_key
           AND its page text is byte-identical -- i.e. the same page of the same
           edition, a different copy. F42's whole point was that the strict
           number punishes copy choice; this separates the two.

ED2 -- content-based edition selection.  F43's structural rule (does a primary
DECLARE the asked year in its metadata) scored 3/17. ED2 asks the same question
from the content side: does the primary's caption-matched top-5 contain a page
whose body holds the asked year?

Gold family handed in for both, as in F42/F43, so neither is a statement about
family retrieval. Counts, ids and booleans only.

  python -u corpus-lab/bin/c_series_gate_v3.py

Pre-registered gate S2 (strict, 24 year-addresses):
  PASS >=16   WEAK 12-15   STOP <12
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

PAGE_CAPTION = "first"     # the frozen page method (F48/F49)
TOPK = 5
WINDOW = 2                 # candidate editions: fy_primary in [Y, Y+2]


def fy_int(fy):
    """'2015-16' -> 2015. The shelf's own fiscal-year spelling, nothing else."""
    try:
        return int(str(fy).split("-")[0])
    except Exception:
        return None


def gold_family(ctx, rels):
    counts = {}
    for r in rels:
        f = ctx.rel_to_family.get(r)
        if f:
            counts[f] = counts.get(f, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def page_text(ctx, rel, page_index):
    row = ctx.db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?",
                         (rel, page_index)).fetchone()
    return row[0] if row else None


def run_s2(ctx, qs_by_id, per_q, trajectory_ids):
    strict = tolerant = 0
    n_addr = 0
    cand_sizes = []
    offsets = {"Y": 0, "Y+1": 0, "Y+2": 0, "none": 0}
    per_question = {}

    for qid in trajectory_ids:
        pq = per_q[qid]
        rels = pq["resolved_rels"]
        fam = gold_family(ctx, rels)
        if not fam:
            per_question[qid] = {"skipped": "no_family"}
            continue
        row_words = G.row_words_from_question(pq["question"])
        primaries = [ctx.rel_to_row[r] for r in ctx.family_to_rels.get(fam, ())
                     if ctx.rel_to_row[r]["is_primary"] and ctx.rel_to_row[r]["fy_primary"]]

        # A "year address" is one (question, fiscal year) pair -- the unit F42's
        # 24 was counted in. Several evidence files can carry the same year, and
        # finding any one of them answers that year, so they are grouped rather
        # than counted separately.
        by_fy = {}
        for a in pq["page_addresses"]:
            if a.get("fy"):
                by_fy.setdefault(a["fy"], []).append(a)

        q_strict = q_tol = q_n = 0
        for fy in sorted(by_fy):
            Y = fy_int(fy)
            if Y is None:
                continue
            addrs = by_fy[fy]
            n_addr += 1
            q_n += 1
            cands = [r for r in primaries
                     if fy_int(r["fy_primary"]) is not None
                     and Y <= fy_int(r["fy_primary"]) <= Y + WINDOW]
            cand_sizes.append(len(cands))

            wants = {(a["rel"], a["page_index"]) for a in addrs}
            want_eks = {}
            want_texts = {}
            for a in addrs:
                row = ctx.rel_to_row.get(a["rel"]) or {}
                if row.get("edition_key"):
                    want_eks[row["edition_key"]] = a
                want_texts[(a["rel"], a["page_index"])] = page_text(
                    ctx, a["rel"], a["page_index"])

            got_strict = got_tol = False
            hit_offset = None
            for r in cands:
                ins = CSH.do_inside(ctx, r["rel"], row_words, k=TOPK,
                                    caption_channel=PAGE_CAPTION)
                for h in ins["hits"][:TOPK]:
                    body = page_text(ctx, r["rel"], h["page_index"])
                    if not body or fy not in body:
                        continue
                    if (r["rel"], h["page_index"]) in wants:
                        got_strict = True
                    else:
                        ek = ctx.rel_to_row.get(r["rel"], {}).get("edition_key")
                        if ek in want_eks and body in [t for t in want_texts.values()
                                                       if t is not None]:
                            got_tol = True
                    if got_strict or got_tol:
                        off = fy_int(r["fy_primary"]) - Y
                        hit_offset = {0: "Y", 1: "Y+1", 2: "Y+2"}.get(off)
                        break
                if got_strict:
                    break
            if got_strict:
                strict += 1
                q_strict += 1
            if got_strict or got_tol:
                tolerant += 1
                q_tol += 1
            offsets[hit_offset or "none"] = offsets.get(hit_offset or "none", 0) + 1

        per_question[qid] = {"type": pq["type"], "n_year_addresses": q_n,
                             "strict_hits": q_strict, "tolerant_hits": q_tol}

    return {
        "page_method": "row+caption_%s" % PAGE_CAPTION,
        "window": "[Y, Y+%d]" % WINDOW, "topk": TOPK,
        "n_year_addresses": n_addr,
        "unit": "distinct (question, fiscal year) pairs",
        "strict_hits": strict, "tolerant_hits": tolerant,
        "mean_candidate_set_size": round(sum(cand_sizes) / float(len(cand_sizes)), 2)
                                   if cand_sizes else None,
        "offset_distribution": offsets,
        "per_question": per_question,
    }


def run_ed2(ctx, per_q, answerable_ids):
    """Edition set = primaries in the gold family whose caption-matched inside
    top-5 contains a page whose body holds the asked fiscal year."""
    n_hit = 0
    sizes = []
    per_question = {}
    year_ids = []
    for qid in answerable_ids:
        pq = per_q[qid]
        m = G.FY_RE.search(pq["question"])
        if not m:
            continue
        year_ids.append(qid)
        fy = m.group(1)
        rels = pq["resolved_rels"]
        fam = gold_family(ctx, rels)
        if not fam:
            per_question[qid] = {"skipped": "no_family"}
            continue
        row_words = G.row_words_from_question(pq["question"])
        primaries = [ctx.rel_to_row[r] for r in ctx.family_to_rels.get(fam, ())
                     if ctx.rel_to_row[r]["is_primary"]]
        sel = []
        for r in primaries:
            ins = CSH.do_inside(ctx, r["rel"], row_words, k=TOPK,
                                caption_channel=PAGE_CAPTION)
            for h in ins["hits"][:TOPK]:
                body = page_text(ctx, r["rel"], h["page_index"])
                if body and fy in body:
                    sel.append(r)
                    break
        sel_keys = {r["edition_key"] for r in sel}
        ev_keys = [ctx.rel_to_row[r]["edition_key"] for r in rels
                   if r in ctx.rel_to_row]
        all_in = bool(ev_keys) and all(k in sel_keys for k in ev_keys)
        if all_in:
            n_hit += 1
        sizes.append(len(sel))
        per_question[qid] = {"type": pq["type"], "set_size": len(sel),
                             "family_primaries": len(primaries),
                             "all_evidence_editions_in_set": all_in,
                             "n_evidence_editions": len(ev_keys)}
    return {
        "n_year_bearing_questions": len(year_ids),
        "set_recall_questions": n_hit,
        "mean_set_size": round(sum(sizes) / float(len(sizes)), 2) if sizes else None,
        "max_set_size": max(sizes) if sizes else None,
        "per_question": per_question,
    }


def main():
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, answerable_ids, per_q, _ = G.load_frozen(ctx)
    traj = [q for q in answerable_ids if per_q[q]["type"] == "trajectory"]

    s2 = run_s2(ctx, qs_by_id, per_q, traj)
    s2["gate"] = ("PASS" if s2["strict_hits"] >= 16
                  else "WEAK" if s2["strict_hits"] >= 12 else "STOP")
    s2["wall_s"] = round(time.time() - t0, 1)
    (L.STATE / "c_series_v3.json").write_text(json.dumps(s2, indent=1), encoding="utf-8")
    print("S2 strict=%d tolerant=%d of %d  gate=%s  mean_candidates=%s  offsets=%s"
          % (s2["strict_hits"], s2["tolerant_hits"], s2["n_year_addresses"],
             s2["gate"], s2["mean_candidate_set_size"], s2["offset_distribution"]))

    t1 = time.time()
    ed2 = run_ed2(ctx, per_q, answerable_ids)
    ed2["wall_s"] = round(time.time() - t1, 1)
    (L.STATE / "c_edition_set_v2.json").write_text(json.dumps(ed2, indent=1),
                                                   encoding="utf-8")
    print("ED2 set_recall=%d of %d  mean_set=%s  max_set=%s"
          % (ed2["set_recall_questions"], ed2["n_year_bearing_questions"],
             ed2["mean_set_size"], ed2["max_set_size"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
