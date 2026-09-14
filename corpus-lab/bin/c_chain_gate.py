#!/usr/bin/env python
"""c_chain_gate.py -- CHAIN, 2026-09-15. The first end-to-end deterministic run.

Every box in the architecture has been measured alone, with the previous box's
output handed in. Nothing has ever been run as one system, so nothing has ever
paid the compounding cost. This does, on all 20 frozen questions, with no model
calls anywhere:

  ROUTE            fiscal-year token present and `have` on the words minus the
                   year returns NO_EDITION_FOR / NO_FAMILY_MATCHES -> ABSENT
  RETRIEVE FAMILY  the frozen document configuration, top 5 families
  SELECT EDITIONS  ED2's content rule for year questions; all primaries for
                   series questions; otherwise all primaries, 15 most recent
  RETRIEVE PAGE    the frozen page method, top 5 per edition
  VERIFY           evidence_v1/verify.py on PDF pages, row label from the
                   question text, column label from the question's year

The verifier is what makes this a chain rather than a fourth lookup measurement:
a page counts as VERIFIED only when the row and column are actually found and
read off the printed table. Values are compared to the printed cell through the
verifier and never to the key's number.

  python -u corpus-lab/bin/c_chain_gate.py

Counts, ids and booleans only.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

# evidence_v1 is a PACKAGE (its modules use relative imports) and it contains a
# logging.py. Putting that directory on sys.path shadows the standard library
# logging for everything imported afterwards, pdfplumber included. Add its
# PARENT and import it as a package instead.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FROZEN_FUSION = "rrf"
FROZEN_CAPTION_CHANNEL = "lex"
FROZEN_PAGE_CAPTION = "first"
TOP_FAMILIES = 5
TOP_PAGES = 5
MAX_EDITIONS = 15
VERIFY_CAP = 40


# do_inside is a deterministic function of (rel, terms, k, caption_channel) and
# the chain calls it twice on the same arguments for every year question -- once
# to select editions and once to retrieve pages. Each call reloads a whole
# document's pages and rebuilds an in-memory FTS index over them, which is the
# dominant cost of this measurement. Memoised here, in the driver, so c_shelf
# keeps its measured behaviour exactly; the cached value is the same object the
# uncached call would have returned.
_INSIDE_CACHE = {}


def inside_cached(ctx, rel, terms, k, caption_channel):
    key = (rel, terms, k, caption_channel)
    if key not in _INSIDE_CACHE:
        _INSIDE_CACHE[key] = CSH.do_inside(ctx, rel, terms, k=k,
                                           caption_channel=caption_channel)
    return _INSIDE_CACHE[key]


def page_text(ctx, rel, page_index):
    row = ctx.db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?",
                         (rel, page_index)).fetchone()
    return row[0] if row else None


# A literal identifier: the longest digit-bearing token in the question. Generic
# -- "the longest run of non-space characters that contains a digit" -- and
# derived from the question text alone, never from the key.
_ID_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9()/._-]*\d[A-Za-z0-9()/._-]*")


def longest_identifier(question):
    cands = [t.strip(".,;:)") for t in _ID_TOKEN_RE.findall(question or "")]
    cands = [t for t in cands if not G.FY_RE.fullmatch(t) and not re.fullmatch(r"\d{4}", t)]
    if not cands:
        return None
    return max(cands, key=len)


def route_absent(ctx, question):
    """Two absence routes, because this corpus has two kinds of absence and the
    2026-09-15 overnight chain only implemented one.

    DOCUMENT level -- the question names a fiscal year: ask the shelf whether it
    holds any edition of that publication for that year.

    IDENTIFIER level -- the question names a literal identifier and no fiscal
    year (a notification number, a demand number, a code). There is nothing for
    `have` to check, and the overnight chain returned "not absent" for every one
    of these without looking, which is why it scored 1 of 3 on the frozen
    absence questions: 1 of those 3 is document level and 2 are identifier
    level. `exact` is the path that was missing -- zero matching pages anywhere
    in the index is the shelf's own evidence of absence.
    """
    m = G.FY_RE.search(question)
    if not m:
        tok = longest_identifier(question)
        if not tok or len(tok) < 3:
            return False, None
        res = CSH.do_exact(ctx, tok, k=1)
        if res.get("total", 0) == 0:
            return True, "TOTAL_PAGES_MATCHING=0"
        return False, None
    fy = m.group(1)
    words = G.FY_RE.sub(" ", question)
    res = CSH.do_have(ctx, words, fy=fy)
    if res.get("no_family_matches"):
        return True, "NO_FAMILY_MATCHES"
    if (res.get("fy_check") or {}).get("status") == "NO_EDITION_FOR":
        return True, "NO_EDITION_FOR"
    return False, None


def select_editions(ctx, family, question, qtype, row_words):
    """ED2's rule for year questions, all primaries otherwise."""
    primaries = [ctx.rel_to_row[r] for r in ctx.family_to_rels.get(family, ())
                 if ctx.rel_to_row[r]["is_primary"]]
    m = G.FY_RE.search(question)
    if m and qtype != "trajectory":
        fy = m.group(1)
        sel = []
        for r in primaries:
            ins = inside_cached(ctx, r["rel"], row_words, TOP_PAGES,
                                FROZEN_PAGE_CAPTION)
            for h in ins["hits"][:TOP_PAGES]:
                body = page_text(ctx, r["rel"], h["page_index"])
                if body and fy in body:
                    sel.append(r)
                    break
        if sel:
            return sel, "ed2_year"
        return primaries[:MAX_EDITIONS], "ed2_year_empty_fallback"
    if qtype == "trajectory":
        return primaries, "all_primaries_series"
    dated = sorted([r for r in primaries if r["fy_primary"]],
                   key=lambda r: r["fy_primary"], reverse=True)
    undated = [r for r in primaries if not r["fy_primary"]]
    return (dated + undated)[:MAX_EDITIONS], "all_primaries_capped"


def main():
    t0 = time.time()
    from evidence_v1.verify import verify_pdf_cell

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sorted(sample["q_ids"])
    _, answerable_ids, per_q, _ = G.load_frozen(ctx)
    rewrites, _ = G.build_rewrites(answerable_ids, qs_by_id, L.STATE)
    root = (L.HARNESS / "corpus_15000").resolve()

    per_question = {}
    n_family_top5 = n_addr_hit = n_verified = n_absence_ok = 0
    n_absence = 0

    for qid in frozen_ids:
        print("  -> %s" % qid, flush=True)
        q = qs_by_id[qid]
        qtype = q["type"]
        rec = {"type": qtype}

        absent, why = route_absent(ctx, q["question"])
        rec["routed_absent"] = absent
        rec["route_reason"] = why

        if qtype == "absence":
            n_absence += 1
            rec["absence_correct"] = bool(absent)
            if absent:
                n_absence_ok += 1
            per_question[qid] = rec
            continue

        if qid not in per_q or not per_q[qid]["resolved_rels"]:
            rec["skipped"] = "evidence_not_on_shelf"
            per_question[qid] = rec
            continue
        pq = per_q[qid]
        ev_addrs = {(a["rel"], a["page_index"]) for a in pq["page_addresses"]}
        ev_fams = G._ev_families(ctx, pq["resolved_rels"])
        row_words = G.row_words_from_question(pq["question"])

        queries = rewrites.get(qid, {}).get("queries") or [pq["question"]]
        res = CSH.do_find(ctx, queries, fusion=FROZEN_FUSION,
                          caption_channel=FROZEN_CAPTION_CHANNEL)
        top = [f["family"] for f in res["families"][:TOP_FAMILIES]]
        fam_hit = any(f in ev_fams for f in top)
        rec["family_in_top5"] = fam_hit
        if fam_hit:
            n_family_top5 += 1

        pages_opened, verify_calls, cap_hit = [], 0, False
        addr_hit = verified_hit = False
        for fam in top:
            eds, rule = select_editions(ctx, fam, pq["question"], qtype, row_words)
            rec.setdefault("edition_rule", rule)
            for r in eds:
                ins = inside_cached(ctx, r["rel"], row_words, TOP_PAGES,
                                    FROZEN_PAGE_CAPTION)
                for h in ins["hits"][:TOP_PAGES]:
                    pages_opened.append((r["rel"], h["page_index"]))
                    if (r["rel"], h["page_index"]) in ev_addrs:
                        addr_hit = True
                    if not r["rel"].lower().endswith(".pdf"):
                        continue
                    if verify_calls >= VERIFY_CAP:
                        cap_hit = True
                        continue
                    col = None
                    m = G.FY_RE.search(pq["question"])
                    if qtype == "trajectory":
                        col = r["fy_primary"]
                    elif m:
                        col = m.group(1)
                    if not col:
                        continue
                    verify_calls += 1
                    try:
                        v = verify_pdf_cell(str(root / r["rel"]), h["page_index"],
                                            row_words, col)
                    except Exception:
                        continue
                    if v.get("verification_status") == "verified":
                        if (r["rel"], h["page_index"]) in ev_addrs:
                            verified_hit = True
                if verify_calls >= VERIFY_CAP:
                    cap_hit = True
                    break
            if verify_calls >= VERIFY_CAP:
                break

        if addr_hit:
            n_addr_hit += 1
        if verified_hit:
            n_verified += 1
        rec.update({"chain_address_hit": addr_hit, "chain_verified_hit": verified_hit,
                    "n_pages_opened": len(pages_opened),
                    "n_verify_calls": verify_calls, "cap_hit": cap_hit})
        per_question[qid] = rec
        print("  [%s] fam_top5=%s addr=%s verified=%s pages=%d verify=%d%s"
              % (qid, fam_hit, addr_hit, verified_hit, len(pages_opened),
                 verify_calls, " CAP" if cap_hit else ""), flush=True)

    n_answerable = len([i for i in frozen_ids if qs_by_id[i]["type"] != "absence"])
    report = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frozen_configuration": {"fusion": FROZEN_FUSION,
                                 "caption_channel": FROZEN_CAPTION_CHANNEL,
                                 "page_caption": FROZEN_PAGE_CAPTION,
                                 "top_families": TOP_FAMILIES, "top_pages": TOP_PAGES,
                                 "verify_cap": VERIFY_CAP},
        "n_answerable": n_answerable, "n_absence": n_absence,
        "family_top5": n_family_top5,
        "address_hits": n_addr_hit,
        "verified_hits": n_verified,
        "absence_correct": n_absence_ok,
        "decomposition": "family_top5=%d -> address_hit=%d -> verified_hit=%d (of %d)"
                         % (n_family_top5, n_addr_hit, n_verified, n_answerable),
        "total_verify_calls": sum(v.get("n_verify_calls", 0) for v in per_question.values()),
        "n_questions_hit_verify_cap": sum(1 for v in per_question.values() if v.get("cap_hit")),
        "wall_s": round(time.time() - t0, 1),
        "per_question": per_question,
    }
    (L.STATE / "c_chain_gate.json").write_text(json.dumps(report, indent=1),
                                               encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_question"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
