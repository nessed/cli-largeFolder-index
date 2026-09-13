#!/usr/bin/env python
"""c_offline_gate.py - build C, Stage 3. The free offline gate.

Imports c_shelf.py in-process (never shells out per question). Reads
_private/harness_keys/answer_key.json for evidence paths and decoys -- the
one place besides c_score_extra.py (Stage 5, not built here) allowed to.
Prints and records COUNTS ONLY: no evidence path, row label or expected
value from the key is ever written to progress.jsonl, FINDINGS_LIVE.md, or
any file under corpus-lab/bin/.

See plans_fable/C_SHELF_FIRST_BUILD.md Stage 3.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
from corpus_search import content_words  # noqa: E402

FY_RE = re.compile(r"\b(20[0-3]\d-\d\d)\b")

# 2026-09-13 series_ok rerun: passing the FULL question as `series`'s row-words
# argument overflows `inside`'s 4-content-word exact-phrase tier, falling to a
# loose any-word match that rarely lands on the right page at k=1. Extracted
# instead: a short row phrase, from the QUESTION TEXT ONLY (no key content).
# Generic pattern, not fit to any one question: these questions are phrased
# either as "<region> -- <row phrase> <verb...>" (the row phrase sits between
# an em/en-dash-style separator and the next transitional verb) or, lacking
# that separator, as ordinary prose where corpus_search.content_words()'s
# existing English stopword list already strips most of the frame, leaving a
# small residue of trajectory-question scaffolding words to drop too.
_ROW_SEP_RE = re.compile(
    r"--\s*(.+?)(?:\s+(?:look|looks|across|over|since|through|trend|trends)\b|$)",
    re.IGNORECASE)
_TRAJECTORY_FILLER = set("""
    has have gone period much decade so trajectory years we me give
""".split())


def row_words_from_question(question):
    m = _ROW_SEP_RE.search(question)
    candidate = m.group(1) if m else question
    words = [w for w in content_words(candidate) if w not in _TRAJECTORY_FILLER]
    if not words:
        words = [w for w in content_words(question) if w not in _TRAJECTORY_FILLER]
    return " ".join(words[:4])

REWRITE_INSTRUCTION = """Write 6 search queries for the question, one per line, numbered 1-6, nothing else.
1. the question itself, word for word
2. the name a Pakistani government statistical publication would print for this series or table row (a noun phrase, no verbs)
3. the same concept using an alternative official term, spelling or acronym (for example defence/defense, labour/labor, receipts/revenue, expenditure/spending, programme/program)
4. the publication most likely to carry the table, plus the fiscal year or years involved, written like 2015-16
5. only the two to four nouns that name the subject, the place and the period - drop every question word and every conversational filler word
6. how the subject would appear in a memo, a note or a spreadsheet file name"""


def norm_path(p):
    return str(p or "").replace("\\", "/")


def _parse_numbered(text):
    out = []
    for line in text.splitlines():
        m = re.match(r"^\s*[1-6][.)]\s*(.+)$", line.strip())
        if m:
            out.append(m.group(1).strip())
    return out


def _haiku_rewrite(question, cwd, err_path):
    cmd = [L.CLAUDE, "-p", REWRITE_INSTRUCTION + "\n\nQuestion: " + question,
           "--model", "claude-haiku-4-5-20251001", "--output-format", "text",
           "--max-turns", "1", "--disallowedTools",
           "Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch",
           "Agent", "NotebookEdit"]
    for attempt in range(2):
        try:
            with open(err_path, "ab") as errf:
                r = subprocess.run(cmd, cwd=str(cwd), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=errf, timeout=120)
        except subprocess.TimeoutExpired:
            continue
        text = (r.stdout or b"").decode("utf-8", errors="replace")
        lines = _parse_numbered(text)
        if len(lines) >= 4:
            return lines, False
    return None, True


def build_rewrites(q_ids, questions_by_id, state_dir):
    cache_path = state_dir / "c_queries.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if all(qid in cached for qid in q_ids):
                return cached, 0
        except Exception:
            pass
    cwd = L.SCRATCH / "c_llm_cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    if (cwd / "CLAUDE.md").exists():
        (cwd / "CLAUDE.md").unlink()
    err_path = L.SCRATCH / "c_queries_stderr.log"
    out = {}
    n_calls = 0
    for qid in q_ids:
        q = questions_by_id[qid]["question"]
        lines, failed = _haiku_rewrite(q, cwd, err_path)
        n_calls += 1
        if failed:
            out[qid] = {"q_id": qid, "queries": [q], "rewrite_failed": True}
        else:
            out[qid] = {"q_id": qid, "queries": [q] + lines[:5], "rewrite_failed": False}
    cache_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out, n_calls


def find_doc_rank(ctx, queries, evidence_rels, decoy_rels):
    res = CSH.do_find(ctx, queries, pool=200)
    fams = res["families"]
    ev_families = {ctx.rel_to_family.get(r) for r in evidence_rels if ctx.rel_to_family.get(r)}
    decoy_families_only = set()
    for r in decoy_rels:
        fam = ctx.rel_to_family.get(r)
        if fam and fam not in ev_families:
            decoy_families_only.add(fam)

    doc_rank = None
    top1_hit = False
    decoy_rank = None
    for i, f in enumerate(fams, start=1):
        if f["family"] in ev_families and doc_rank is None:
            doc_rank = i
            top1_hit = (i == 1)
        if f["family"] in decoy_families_only and decoy_rank is None:
            decoy_rank = i
        if doc_rank is not None and decoy_rank is not None:
            break
    decoy_first = bool(decoy_rank is not None and (doc_rank is None or decoy_rank < doc_rank))
    return {"doc_rank": doc_rank, "top1_hit": top1_hit, "decoy_first": decoy_first,
            "n_families_considered": len(fams)}


def page_rank_for(ctx, question_text, rel, page_index):
    res = CSH.do_inside(ctx, rel, question_text, k=20)
    for i, h in enumerate(res["hits"], start=1):
        if h["page_index"] == page_index:
            return i
    return None


def series_ok_for(ctx, question_text, family_of_evidence, evidence_pages_by_fy, k=5):
    row_words = row_words_from_question(question_text)
    res = CSH.do_series(ctx, row_words, family_of_evidence, k=k, exact_family=True)
    hit = 0
    per_edition_rank = []  # (fy, rank-within-k or None)
    for e in res.get("editions", []):
        want = evidence_pages_by_fy.get(e["fy"])
        rank = None
        if want is not None:
            for i, h in enumerate(e.get("hits", []), start=1):
                if h["page_index"] == want:
                    rank = i
                    break
        if rank is not None:
            hit += 1
        per_edition_rank.append((e["fy"], rank))
    return hit, res.get("n", 0), row_words, per_edition_rank


def run_series_measurement(ctx, qs_by_id, trajectory_ids):
    series_results = {}
    for qid in trajectory_ids:
        q = qs_by_id[qid]
        ev = q["evidence_addresses"]
        fam_counts = {}
        for e in ev:
            fam = ctx.rel_to_family.get(norm_path(e["path"]))
            if fam:
                fam_counts[fam] = fam_counts.get(fam, 0) + 1
        if not fam_counts:
            series_results[qid] = {"hit_editions": 0, "n_editions": 0, "skipped": True}
            continue
        # the family holding the MOST of this question's evidence editions, not an
        # arbitrary one -- messy real titles can split one publication across a
        # couple of family spellings (see c_shelf_build.py's docstring on this).
        family = max(fam_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
        pages_by_fy = {}
        for e in ev:
            if e.get("fy") and e.get("page_index") is not None:
                pages_by_fy[e["fy"]] = e["page_index"]
        hit, n_ed, row_words, per_edition_rank = series_ok_for(ctx, q["question"], family, pages_by_fy)
        series_results[qid] = {"hit_editions": hit, "n_editions": n_ed,
                               "ok": hit >= 2, "skipped": False,
                               "row_words_word_count": len(row_words.split()),
                               "per_edition_rank": per_edition_rank}
    return series_results


def run_series_only():
    """2026-09-13: rerun ONLY series_ok, row term extracted from question text
    (no key content) via row_words_from_question(), k=5 not k=1. Everything
    else (rewrites, doc_rank, page_rank, absence) is untouched from the prior
    Stage 3 run. Key access stays confined to this file, per the build rules."""
    ak = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in ak["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sample["q_ids"]
    trajectory_ids = [qid for qid in frozen_ids if qs_by_id[qid]["type"] == "trajectory"]

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                       str(L.STACKS / "s7_shelf" / "shelf.db"))
    series_results = run_series_measurement(ctx, qs_by_id, trajectory_ids)
    hits = sum(1 for v in series_results.values() if v.get("ok"))
    n = len(trajectory_ids)
    report = {"series_ok": f"{hits}/{n}", "per_question": series_results}
    out = L.STATE / "c_series_rerun.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return report


def main():
    t0 = time.time()
    ak = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in ak["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sample["q_ids"]

    answerable_ids = [qid for qid in frozen_ids if qs_by_id[qid]["type"] != "absence"]
    absence_frozen_ids = [qid for qid in frozen_ids if qs_by_id[qid]["type"] == "absence"]
    all_absence = [q for q in ak["questions"] if q["type"] == "absence"]
    assert len(answerable_ids) == 17, f"expected 17 answerable, got {len(answerable_ids)}"

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                       str(L.STACKS / "s7_shelf" / "shelf.db"))

    rewrites, n_calls = build_rewrites(answerable_ids, qs_by_id, L.STATE)

    per_q = {}
    excluded_not_on_shelf = 0
    for qid in answerable_ids:
        q = qs_by_id[qid]
        ev_rels = [norm_path(e["path"]) for e in q["evidence_addresses"]]
        decoy_rels = [norm_path(m["path"]) for m in q["must_not_cite"]]
        on_shelf = [r for r in ev_rels if r in ctx.rel_to_row]
        if not on_shelf:
            excluded_not_on_shelf += 1
        per_q[qid] = {"type": q["type"], "ev_rels": ev_rels, "decoy_rels": decoy_rels,
                      "on_shelf": on_shelf, "question": q["question"],
                      "evidence_addresses": q["evidence_addresses"]}

    configs = {"C1": {}, "C2": {}}
    for qid in answerable_ids:
        pq = per_q[qid]
        c1_queries = [pq["question"]]
        c2_queries = rewrites[qid]["queries"] if qid in rewrites else [pq["question"]]
        for cfg_name, queries in (("C1", c1_queries), ("C2", c2_queries)):
            if not pq["on_shelf"]:
                configs[cfg_name][qid] = {"skipped": "evidence_not_on_shelf"}
                continue
            dr = find_doc_rank(ctx, queries, pq["ev_rels"], pq["decoy_rels"])
            entry = dict(dr)
            if cfg_name == "C1":
                pr_list = []
                for e in pq["evidence_addresses"]:
                    if e.get("page_index") is not None and norm_path(e["path"]) in ctx.rel_to_row:
                        r = page_rank_for(ctx, pq["question"], norm_path(e["path"]), e["page_index"])
                        pr_list.append(r)
                entry["page_ranks"] = pr_list
            configs[cfg_name][qid] = entry

    # series_ok: 4 trajectory questions, C1 only
    trajectory_ids = [qid for qid in answerable_ids if qs_by_id[qid]["type"] == "trajectory"]
    series_results = run_series_measurement(ctx, qs_by_id, trajectory_ids)

    # --- 3.3 absence enumeration -----------------------------------------
    doclevel, idlevel = [], []
    for q in all_absence:
        if FY_RE.search(q["question"]):
            doclevel.append(q)
        else:
            idlevel.append(q)

    doclevel_results = []
    for q in doclevel:
        m = FY_RE.search(q["question"])
        fy = m.group(1)
        words = FY_RE.sub(" ", q["question"])
        res = CSH.do_have(ctx, words, fy=fy)
        status = res.get("fy_check", {}).get("status") if not res["no_family_matches"] else "NO_FAMILY_MATCHES"
        hit = status in ("NO_EDITION_FOR", "NO_FAMILY_MATCHES")
        doclevel_results.append({"q_id": q["q_id"], "hit": hit, "status": status})

    # One entry per answerable question (denominator = 17, matching the gate
    # table's "of 17"), not one entry only when a usable edition happens to
    # exist -- a question with no on-shelf fy-bearing evidence is a genuine
    # miss for this control, not a question that never happened.
    control_results = []
    for qid in answerable_ids:
        q = qs_by_id[qid]
        checked = False
        for e in q["evidence_addresses"]:
            rel = norm_path(e["path"])
            if rel not in ctx.rel_to_row:
                continue
            fy = ctx.rel_to_row[rel]["fy_primary"]
            if not fy:
                continue
            fam = ctx.rel_to_row[rel]["family"]
            fam_words = CSH._family_words(fam)
            res = CSH.do_have(ctx, fam_words, fy=fy)
            status = res.get("fy_check", {}).get("status") if not res["no_family_matches"] else "NO_FAMILY_MATCHES"
            control_results.append({"q_id": qid, "hit": status == "EDITION_PRESENT", "status": status})
            checked = True
            break  # one control check per question, using its first fy-bearing evidence edition (our shelf's own fy_primary)
        if not checked:
            control_results.append({"q_id": qid, "hit": False, "status": "no_fy_bearing_evidence_on_shelf"})

    idlevel_results = []
    for q in idlevel:
        toks = re.findall(r"[A-Za-z0-9/().\-]*\d[A-Za-z0-9/().\-]*", q["question"])
        longest = max(toks, key=len) if toks else ""
        res = CSH.do_exact(ctx, longest, k=1) if longest else {"total": None}
        hit = res.get("total") == 0
        idlevel_results.append({"q_id": q["q_id"], "hit": hit, "total": res.get("total")})

    # --- gate 3 aggregation ------------------------------------------------
    def band(pct, pass_n, weak_lo, n):
        if pct is None:
            return "n/a"
        if pct >= pass_n:
            return "PASS"
        if pct >= weak_lo:
            return "PASS-WEAK"
        return "FAIL"

    c1_doc_hits = sum(1 for v in configs["C1"].values() if v.get("doc_rank") and v["doc_rank"] <= 10)
    c1_doc_n = len(answerable_ids)
    c2_doc_hits = sum(1 for v in configs["C2"].values() if v.get("doc_rank") and v["doc_rank"] <= 10)

    pr_hits = pr_n = 0
    for v in configs["C1"].values():
        for r in v.get("page_ranks", []):
            pr_n += 1
            if r is not None and r <= 5:
                pr_hits += 1
    pr_pct = round(100.0 * pr_hits / pr_n, 1) if pr_n else None

    series_hits = sum(1 for v in series_results.values() if v.get("ok"))
    series_n = len(trajectory_ids)

    doc_absence_hits = sum(1 for r in doclevel_results if r["hit"])
    doc_absence_n = len(doclevel_results)
    control_hits = sum(1 for r in control_results if r["hit"])
    control_n = len(control_results)
    id_absence_hits = sum(1 for r in idlevel_results if r["hit"])
    id_absence_n = len(idlevel_results)

    gate_rows = {
        "C1_doc_rank_le_10": {"hits": c1_doc_hits, "n": c1_doc_n,
                               "band": band(c1_doc_hits, 12, 8, c1_doc_n)},
        "C2_doc_rank_le_10": {"hits": c2_doc_hits, "n": c1_doc_n},
        "C1_page_rank_le_5": {"hits": pr_hits, "n": pr_n, "pct": pr_pct,
                               "band": band(pr_pct, 60, 40, pr_n)},
        "series_ok": {"hits": series_hits, "n": series_n,
                      "band": band(series_hits, 3, 2, series_n)},
        "doc_level_absence_NO_EDITION": {"hits": doc_absence_hits, "n": doc_absence_n,
                                          "band": band(doc_absence_hits, 9, 7, doc_absence_n)},
        "control_EDITION_PRESENT": {"hits": control_hits, "n": control_n,
                                     "band": band(control_hits, 15, 13, control_n)},
        "identifier_level_absence_zero_hits": {"hits": id_absence_hits, "n": id_absence_n},
    }
    bands = [v.get("band") for v in gate_rows.values() if "band" in v]
    if all(b == "PASS" for b in bands):
        overall = "PASS"
    elif any(b == "FAIL" for b in bands):
        overall = "FAIL"
    else:
        overall = "PASS-WEAK"

    report = {
        "n_answerable": len(answerable_ids),
        "excluded_not_on_shelf": excluded_not_on_shelf,
        "absence_split": {"document_level_n": len(doclevel), "identifier_level_n": len(idlevel)},
        "n_haiku_calls": n_calls,
        "gate_rows": gate_rows,
        "overall": overall,
        "wall_s": round(time.time() - t0, 1),
    }
    out_path = L.STATE / "c_offline_gate.json"
    out_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return report


# ===================================================================== #
# 2026-09-14 corrected gate (v2). Everything above this line is the
# historical Stage 3 gate and is left alone so its numbers stay
# reproducible; `main()` still writes c_offline_gate.json and is the
# HISTORICAL record. Everything below is the corrected measurement, and
# writes only to c_gate_v2.json and its siblings.
#
# It fixes four defects found by the 2026-09-13 adversarial review:
#   D1  page_rank_for fed `inside` the WHOLE question, overflowing the
#       4-content-word exact-phrase tier -- the same defect already found
#       and fixed for the series walk (see run_series_only above), never
#       carried across to the page row.            -> F6, --query-mode
#   D2  evidence whose path the shelf hash-collapsed into another file's
#       `dupes` list was not in rel_to_row, so the question was scored an
#       automatic miss rather than resolved to the surviving twin. -> F1
#   D3  the present-edition control queried with the SHELF's own family
#       words, so it tested the shelf against itself, and it counted
#       NO_FAMILY_MATCHES as an absence hit.                        -> F5
#   D4  per-question family ranks were computed and thrown away, so
#       recall past top-10 was unknown.                        -> F2, F7
# ===================================================================== #

RECALL_DEPTHS = (10, 20, 50, 100, 200)

# The frozen 30-question confirmation set. Read ONLY inside this file, and
# only ever reduced to aggregate counts before anything is written out.
HOLDOUT_FROZEN = L.PRIVATE / "evidence_v1" / "holdout_frozen.json"


def build_rel_to_survivor(ctx):
    """F1. docs.dupes maps a surviving rel -> the byte-identical paths that
    were collapsed into it. Invert it. Byte-identical files share page
    indices, so the survivor's rel is a sound stand-in for family lookup
    AND for page lookup."""
    out = {}
    for rel, row in ctx.rel_to_row.items():
        for d in row.get("dupes") or []:
            out[norm_path(d)] = rel
    return out


def resolve_rel(ctx, rel, rel_to_survivor):
    """rel if the shelf holds it; else its surviving twin; else None."""
    if rel in ctx.rel_to_row:
        return rel
    return rel_to_survivor.get(rel)


def family_rank_full(ctx, queries, ev_families, pool=200):
    """F2. Rank of the gold family in the full fused ranking (do_find
    returns every fused family, not a slice)."""
    res = CSH.do_find(ctx, queries, pool=pool)
    fams = res["families"]
    for i, f in enumerate(fams, start=1):
        if f["family"] in ev_families:
            return i, len(fams)
    return None, len(fams)


def recall_at(ranks, depth):
    return sum(1 for r in ranks if r is not None and r <= depth)


def _ev_families(ctx, rels):
    return {ctx.rel_to_family[r] for r in rels if r in ctx.rel_to_family}


def load_frozen(ctx):
    """The 17 answerable frozen questions, with evidence resolved through
    the duplicate map."""
    ak = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in ak["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sample["q_ids"]
    answerable_ids = [qid for qid in frozen_ids if qs_by_id[qid]["type"] != "absence"]
    r2s = build_rel_to_survivor(ctx)

    per_q = {}
    n_mapped = 0
    rescued = 0
    for qid in answerable_ids:
        q = qs_by_id[qid]
        raw = [norm_path(e["path"]) for e in q["evidence_addresses"]]
        direct = [r for r in raw if r in ctx.rel_to_row]
        resolved, mapped_here = [], 0
        for r in raw:
            rr = resolve_rel(ctx, r, r2s)
            if rr is not None:
                resolved.append(rr)
                if rr != r:
                    mapped_here += 1
        n_mapped += mapped_here
        if not direct and resolved:
            rescued += 1
        addrs = []
        for e in q["evidence_addresses"]:
            rr = resolve_rel(ctx, norm_path(e["path"]), r2s)
            if rr is not None and e.get("page_index") is not None:
                addrs.append({"rel": rr, "page_index": e["page_index"], "fy": e.get("fy")})
        per_q[qid] = {
            "type": q["type"], "question": q["question"],
            "raw_rels": raw, "direct_rels": direct, "resolved_rels": resolved,
            "decoy_rels": [norm_path(m["path"]) for m in q["must_not_cite"]],
            "page_addresses": addrs,
        }
    counts = {"n_evidence_mapped_via_dupes": n_mapped,
              "n_questions_rescued": rescued,
              "n_excluded_legacy": sum(1 for v in per_q.values() if not v["direct_rels"]),
              "n_excluded_corrected": sum(1 for v in per_q.values() if not v["resolved_rels"])}
    return qs_by_id, answerable_ids, per_q, counts


def doc_ranks_for_config(ctx, answerable_ids, per_q, queries_by_qid, legacy_exclusion):
    """F2/D2. Per-question gold-family rank at full depth, under either the
    legacy exclusion rule (a hash-collapsed evidence path is a miss) or the
    corrected one (resolve it to its surviving twin)."""
    out = {}
    for qid in answerable_ids:
        pq = per_q[qid]
        rels = pq["direct_rels"] if legacy_exclusion else pq["resolved_rels"]
        if not rels:
            out[qid] = {"type": pq["type"], "family_rank": None,
                        "skipped": "evidence_not_on_shelf"}
            continue
        fams = _ev_families(ctx, rels)
        rank, n_ranked = family_rank_full(ctx, queries_by_qid[qid], fams)
        out[qid] = {"type": pq["type"], "family_rank": rank, "n_families_ranked": n_ranked}
    return out


def recall_curve(rank_map):
    ranks = [v.get("family_rank") for v in rank_map.values()]
    return {"recall_at_%d" % d: recall_at(ranks, d) for d in RECALL_DEPTHS}


# --------------------------------------------------------------------- #
# F6. page rank, with the query-mode defect isolated
# --------------------------------------------------------------------- #
def page_rank_measure(ctx, answerable_ids, per_q, query_mode="row",
                      caption_channel=None, k=20, le=5, legacy_exclusion=False):
    """legacy_exclusion=True reproduces the historical denominator: a question
    whose evidence path was hash-collapsed contributed no addresses at all."""
    per_question = {}
    micro_hits = micro_n = 0
    macro_fracs = []
    by_type = {}
    n_no_caption_cover = 0
    for qid in answerable_ids:
        pq = per_q[qid]
        if legacy_exclusion and not pq["direct_rels"]:
            continue
        addrs = [a for a in pq["page_addresses"]
                 if not legacy_exclusion or a["rel"] in pq["direct_rels"]]
        if not addrs:
            continue
        terms = pq["question"] if query_mode == "full" else row_words_from_question(pq["question"])
        ranks = []
        caption_covered = False
        for a in addrs:
            if caption_channel is not None:
                res = CSH.do_inside(ctx, a["rel"], terms, k=k,
                                    caption_channel=caption_channel)
            else:
                res = CSH.do_inside(ctx, a["rel"], terms, k=k)
            r = None
            for i, h in enumerate(res["hits"], start=1):
                if h["page_index"] == a["page_index"]:
                    r = i
                    break
            ranks.append(r)
            if caption_channel is not None and res.get("n_caption_hits"):
                caption_covered = True
        if caption_channel is not None and not caption_covered:
            n_no_caption_cover += 1
        hits = sum(1 for r in ranks if r is not None and r <= le)
        micro_hits += hits
        micro_n += len(ranks)
        macro_fracs.append(hits / float(len(ranks)))
        t = pq["type"]
        bt = by_type.setdefault(t, {"hits": 0, "n": 0, "questions": 0})
        bt["hits"] += hits
        bt["n"] += len(ranks)
        bt["questions"] += 1
        per_question[qid] = {"type": t, "page_ranks": ranks,
                             "n_addresses": len(ranks), "hits_le_5": hits}
    macro = round(100.0 * sum(macro_fracs) / len(macro_fracs), 1) if macro_fracs else None
    return {
        "query_mode": query_mode,
        "caption_channel": caption_channel or "off",
        "micro_hits": micro_hits, "micro_n": micro_n,
        "micro_pct": round(100.0 * micro_hits / micro_n, 1) if micro_n else None,
        "macro_pct": macro, "n_questions_with_pdf_addresses": len(macro_fracs),
        "by_type": by_type,
        "n_questions_no_caption_covers_all_query_words": n_no_caption_cover,
        "per_question": per_question,
    }


# --------------------------------------------------------------------- #
# F5. symmetric absence control
# --------------------------------------------------------------------- #
def absence_and_symmetric_control(ctx):
    ak = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    all_absence = [q for q in ak["questions"] if q["type"] == "absence"]
    doclevel = [q for q in all_absence if FY_RE.search(q["question"])]
    idlevel = [q for q in all_absence if not FY_RE.search(q["question"])]

    n_no_edition = n_no_family = 0
    n_symmetric_present = n_unresolvable = 0
    per_q = {}
    for q in doclevel:
        m = FY_RE.search(q["question"])
        fy = m.group(1)
        words = FY_RE.sub(" ", q["question"])
        res = CSH.do_have(ctx, words, fy=fy)
        if res["no_family_matches"]:
            status = "NO_FAMILY_MATCHES"
        else:
            status = res.get("fy_check", {}).get("status")
        if status == "NO_EDITION_FOR":
            n_no_edition += 1
        elif status == "NO_FAMILY_MATCHES":
            n_no_family += 1

        # D3's fix: the control now asks the SAME question words, swapping only
        # the asked year for a year that family actually holds. If presence
        # detection is sound, the identical phrasing must now say PRESENT.
        sym = None
        if status == "NO_EDITION_FOR":
            fy_list = res["fy_check"].get("fy_list") or []
            if fy_list:
                def _dist(y):
                    try:
                        return abs(int(y[:4]) - int(fy[:4]))
                    except Exception:
                        return 10 ** 6
                held = min(fy_list, key=_dist)
                sres = CSH.do_have(ctx, words, fy=held)
                sstat = ("NO_FAMILY_MATCHES" if sres["no_family_matches"]
                         else sres.get("fy_check", {}).get("status"))
                sym = sstat
                if sstat == "EDITION_PRESENT":
                    n_symmetric_present += 1
            else:
                n_unresolvable += 1
        else:
            n_unresolvable += 1
        per_q[q["q_id"]] = {"absence_status": status, "symmetric_status": sym}

    id_hits = 0
    for q in idlevel:
        toks = re.findall(r"[A-Za-z0-9/().\-]*\d[A-Za-z0-9/().\-]*", q["question"])
        longest = max(toks, key=len) if toks else ""
        res = CSH.do_exact(ctx, longest, k=1) if longest else {"total": None}
        if res.get("total") == 0:
            id_hits += 1

    n = len(doclevel)
    sym_band = ("PASS" if n_symmetric_present >= 9
                else "WEAK" if n_symmetric_present >= 7 else "FAIL")
    return {
        "document_level_n": n, "identifier_level_n": len(idlevel),
        "doc_absence_hits": n_no_edition + n_no_family,
        "n_no_edition": n_no_edition, "n_no_family": n_no_family,
        "n_symmetric_present": n_symmetric_present,
        "n_unresolvable": n_unresolvable,
        "symmetric_band": sym_band,
        "identifier_absence_hits": id_hits,
        "per_question": per_q,
    }


# --------------------------------------------------------------------- #
# F7. per-rewrite diagnostic
# --------------------------------------------------------------------- #
def per_rewrite_diagnostic(ctx, answerable_ids, per_q, rewrites):
    per_index_hits = {}
    any_single_le10 = 0
    unique_contrib = {}
    per_question = {}
    for qid in answerable_ids:
        pq = per_q[qid]
        if not pq["resolved_rels"]:
            continue
        fams = _ev_families(ctx, pq["resolved_rels"])
        qs = rewrites.get(qid, {}).get("queries") or [pq["question"]]
        ranks = []
        for i, q in enumerate(qs):
            r, _ = family_rank_full(ctx, [q], fams)
            ranks.append(r)
            if r is not None and r <= 10:
                per_index_hits[i] = per_index_hits.get(i, 0) + 1
        if any(r is not None and r <= 10 for r in ranks):
            any_single_le10 += 1
        found = [i for i, r in enumerate(ranks) if r is not None]
        if len(found) == 1:
            unique_contrib[found[0]] = unique_contrib.get(found[0], 0) + 1
        per_question[qid] = {"ranks_by_rewrite_index": ranks}
    return {"recall_at_10_by_rewrite_index": per_index_hits,
            "any_single_rewrite_le_10": any_single_le10,
            "sole_contributor_count_by_rewrite_index": unique_contrib,
            "per_question": per_question}


# --------------------------------------------------------------------- #
# F3. holdout (aggregate counts only, never per-question ranks)
# --------------------------------------------------------------------- #
def build_holdout_rewrites(q_ids, questions_by_id, state_dir, budget):
    cache_path = state_dir / "c_queries_holdout.json"
    cached = {}
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cached = {}
    todo = [q for q in q_ids if q not in cached]
    if len(todo) > budget:
        raise SystemExit("HAIKU_BUDGET: need %d calls, budget %d" % (len(todo), budget))
    cwd = L.SCRATCH / "c_llm_cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    if (cwd / "CLAUDE.md").exists():
        (cwd / "CLAUDE.md").unlink()
    err_path = L.SCRATCH / "c_queries_holdout_stderr.log"
    n_calls = 0
    for qid in todo:
        q = questions_by_id[qid]["question"]
        lines, failed = _haiku_rewrite(q, cwd, err_path)
        n_calls += 1
        if failed:
            cached[qid] = {"q_id": qid, "queries": [q], "rewrite_failed": True}
        else:
            cached[qid] = {"q_id": qid, "queries": [q] + lines[:5], "rewrite_failed": False}
        cache_path.write_text(json.dumps(cached, indent=1), encoding="utf-8")
    return cached, n_calls


def holdout_rank_inputs(ctx, budget=40):
    """Returns (list of (queries_c1, queries_c2, gold_families), counts).
    Deliberately returns no question ids alongside ranks: the caller may
    only aggregate."""
    hold = json.loads(HOLDOUT_FROZEN.read_text(encoding="utf-8"))
    ak = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in ak["questions"]}
    ids = [q for q in hold["holdout_q_ids"] if q in qs_by_id]
    answerable = [q for q in ids if qs_by_id[q]["type"] != "absence"]
    rewrites, n_calls = build_holdout_rewrites(answerable, qs_by_id, L.STATE, budget)
    r2s = build_rel_to_survivor(ctx)
    items = []
    n_excluded = 0
    for qid in answerable:
        q = qs_by_id[qid]
        rels = [r for r in (resolve_rel(ctx, norm_path(e["path"]), r2s)
                            for e in q["evidence_addresses"]) if r]
        if not rels:
            n_excluded += 1
            continue
        items.append(([q["question"]], rewrites[qid]["queries"], _ev_families(ctx, rels)))
    return items, {"n_holdout": len(ids), "n_answerable": len(answerable),
                   "n_measurable": len(items), "n_excluded": n_excluded,
                   "n_haiku_calls": n_calls}


def holdout_recall(ctx, budget=40):
    items, counts = holdout_rank_inputs(ctx, budget)
    c1 = [family_rank_full(ctx, q1, f)[0] for q1, _, f in items]
    c2 = [family_rank_full(ctx, q2, f)[0] for _, q2, f in items]
    out = dict(counts)
    out["C1"] = {"recall_at_%d" % d: recall_at(c1, d) for d in RECALL_DEPTHS}
    out["C2"] = {"recall_at_%d" % d: recall_at(c2, d) for d in RECALL_DEPTHS}
    return out


# --------------------------------------------------------------------- #
# legacy reproduction: the historical gate rows, recomputed
# --------------------------------------------------------------------- #
def legacy_reproduction(ctx, answerable_ids, per_q, rewrites):
    c1 = doc_ranks_for_config(ctx, answerable_ids, per_q,
                              {q: [per_q[q]["question"]] for q in answerable_ids},
                              legacy_exclusion=True)
    c2 = doc_ranks_for_config(ctx, answerable_ids, per_q,
                              {q: rewrites.get(q, {}).get("queries") or [per_q[q]["question"]]
                               for q in answerable_ids},
                              legacy_exclusion=True)
    return {
        "C1_family_le_10": recall_at([v.get("family_rank") for v in c1.values()], 10),
        "C2_family_le_10": recall_at([v.get("family_rank") for v in c2.values()], 10),
        "n": len(answerable_ids),
    }


def run_gate_v2(argv):
    t0 = time.time()
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    qs_by_id, answerable_ids, per_q, dupe_counts = load_frozen(ctx)
    rewrites, _ = build_rewrites(answerable_ids, qs_by_id, L.STATE)

    report = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "n_answerable": len(answerable_ids),
              "dupe_mapping": dupe_counts}

    def want(flag):
        return (flag in argv) or ("--all" in argv)

    if want("--doc"):
        c1q = {q: [per_q[q]["question"]] for q in answerable_ids}
        c2q = {q: rewrites.get(q, {}).get("queries") or [per_q[q]["question"]]
               for q in answerable_ids}
        c1 = doc_ranks_for_config(ctx, answerable_ids, per_q, c1q, legacy_exclusion=False)
        c2 = doc_ranks_for_config(ctx, answerable_ids, per_q, c2q, legacy_exclusion=False)
        report["CORRECTED"] = {
            "C1": {"per_question": c1, "curve": recall_curve(c1),
                   "family_le_10": recall_at([v.get("family_rank") for v in c1.values()], 10)},
            "C2": {"per_question": c2, "curve": recall_curve(c2),
                   "family_le_10": recall_at([v.get("family_rank") for v in c2.values()], 10)},
        }
        report["HISTORICAL_reproduction"] = legacy_reproduction(
            ctx, answerable_ids, per_q, rewrites)
        (L.STATE / "c_recall_curve.json").write_text(json.dumps(
            {"n": len(answerable_ids),
             "C1": report["CORRECTED"]["C1"]["curve"],
             "C2": report["CORRECTED"]["C2"]["curve"]}, indent=1), encoding="utf-8")

    if want("--per-rewrite"):
        report["per_rewrite"] = per_rewrite_diagnostic(ctx, answerable_ids, per_q, rewrites)

    if want("--page-only"):
        if "--query-mode" in argv:
            modes = [argv[argv.index("--query-mode") + 1]]
        else:
            modes = ["full", "row"]
        chan = None
        if "--caption-channel" in argv:
            c = argv[argv.index("--caption-channel") + 1]
            chan = None if c == "off" else c
        page = {}
        prev_page = {}
        pg_path = L.STATE / "c_page_gate.json"
        if pg_path.exists():
            try:
                prev_page = json.loads(pg_path.read_text(encoding="utf-8"))
            except Exception:
                prev_page = {}
        legacy = "--legacy-exclusion" in argv
        for m in modes:
            key = m if chan is None else "%s+caption_%s" % (m, chan)
            if legacy:
                key += "+legacy_exclusion"
            page[key] = page_rank_measure(ctx, answerable_ids, per_q,
                                          query_mode=m, caption_channel=chan,
                                          legacy_exclusion=legacy)
        report["page"] = page
        prev_page.update(page)
        pg_path.write_text(json.dumps(prev_page, indent=1), encoding="utf-8")

    if want("--absence"):
        report["absence"] = absence_and_symmetric_control(ctx)
        (L.STATE / "c_absence_control_v2.json").write_text(
            json.dumps(report["absence"], indent=1), encoding="utf-8")

    if want("--series"):
        trajectory_ids = [q for q in answerable_ids if per_q[q]["type"] == "trajectory"]
        sr = run_series_measurement(ctx, qs_by_id, trajectory_ids)
        report["series_ok_rerun"] = {
            "hits": sum(1 for v in sr.values() if v.get("ok")), "n": len(trajectory_ids),
            "per_question": {k: {kk: vv for kk, vv in v.items() if kk != "per_edition_rank"}
                             for k, v in sr.items()}}
        (L.STATE / "c_series_v2.json").write_text(
            json.dumps(report["series_ok_rerun"], indent=1), encoding="utf-8")

    if want("--holdout"):
        report["holdout"] = holdout_recall(ctx)

    report["wall_s"] = round(time.time() - t0, 1)
    out = L.STATE / "c_gate_v2.json"
    prev = {}
    if out.exists() and "--fresh" not in argv:
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    prev.update(report)
    out.write_text(json.dumps(prev, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("CORRECTED", "per_rewrite", "page", "absence")},
                     indent=1))
    return prev


if __name__ == "__main__":
    if "--series-only" in sys.argv:
        run_series_only()
    elif "--v2" in sys.argv:
        run_gate_v2(sys.argv[1:])
    else:
        main()
