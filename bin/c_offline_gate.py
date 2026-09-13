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

FY_RE = re.compile(r"\b(20[0-3]\d-\d\d)\b")

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


def series_ok_for(ctx, question_text, family_of_evidence, evidence_pages_by_fy):
    res = CSH.do_series(ctx, question_text, family_of_evidence)
    hit = 0
    for e in res.get("editions", []):
        want = evidence_pages_by_fy.get(e["fy"])
        if want is not None and e["page_index"] == want:
            hit += 1
    return hit, res.get("n", 0)


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
        hit, n_ed = series_ok_for(ctx, q["question"], family, pages_by_fy)
        series_results[qid] = {"hit_editions": hit, "n_editions": n_ed,
                               "ok": hit >= 2, "skipped": False}

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

    control_results = []
    for qid in answerable_ids:
        q = qs_by_id[qid]
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
            break  # one control check per question, using its first fy-bearing evidence edition (our shelf's own fy_primary)

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


if __name__ == "__main__":
    main()
