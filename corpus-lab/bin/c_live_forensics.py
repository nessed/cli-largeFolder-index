#!/usr/bin/env python
"""c_live_forensics.py -- 2026-09-15 pm, Phase 2.

The overnight battery established that the agent opened pages diligently and
opened the wrong ones: an evidence path was printed to 8 of 17 sessions and
only 2 of those opened an evidence file. This asks the next question: **when
the right file was on screen, where did it go instead?**

Six mutually exclusive classes, tested in order, first match wins:

  L0_family_not_surfaced            no find output contained the gold family
  L1_surfaced_opened_other_family   gold family surfaced; every open was elsewhere
  L2_opened_same_family_other_edition  opened in the gold family, never a gold file
  L3_opened_gold_file_wrong_page    opened a gold file, never at a gold page
  L4_opened_right_page_not_cited    opened a gold (file, page), did not cite it
  L5_cited_right_page

Each class names a different repair, which is why the decision table that reads
this output was written before the counts existed.

  python -u corpus-lab/bin/c_live_forensics.py [--phase P5_live]

Reads the answer key inside this script. Output is counts, ranks and question
ids only -- no path, title, family or label string is ever written out.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import scoring as SC  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_score_live as SL  # noqa: E402
from corpus_search import content_words  # noqa: E402

CLASSES = ["L0_family_not_surfaced", "L1_surfaced_opened_other_family",
           "L2_opened_same_family_other_edition", "L3_opened_gold_file_wrong_page",
           "L4_opened_right_page_not_cited", "L5_cited_right_page"]

FIND_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+find\b")
HAVE_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+have\b")
TABLES_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+tables\b")
SERIES_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+series\b")
INSIDE_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+inside\b")
Q_FLAG = re.compile(r"--q\s+")
# the free-text terms argument of inside/series, or the --grep value of tables
TERMS_RE = re.compile(r"(?:inside|series)\s+(?:\"[^\"]*\"|\S+)\s+\"([^\"]*)\"|--grep\s+\"([^\"]*)\"")


_FAM_LC = {}


def family_of(ctx, rel):
    """Shelf rels preserve their original case; scoring.norm_path lowercases.
    Looking one up in the other silently returns None for EVERY path, which is
    not "the agent opened a different publication" -- it is the classifier
    going blind. Build a lowercased index once and match on it, falling back to
    the last two path segments the way scoring.py does."""
    if not _FAM_LC:
        for r, f in ctx.rel_to_family.items():
            n = SC.norm_path(r)
            _FAM_LC[n] = f
            _FAM_LC.setdefault(SC.path_tail(n, 2), f)
    n = SC.norm_path(rel)
    return _FAM_LC.get(n) or _FAM_LC.get(SC.path_tail(n, 2))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P5_live")
    ap.add_argument("--out", default="c_live_forensics.json")
    a = ap.parse_args(argv)

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    answerable = [i for i in sorted(sample["q_ids"]) if qs_by_id[i]["type"] != "absence"]

    per_q, totals = {}, {c: 0 for c in CLASSES}
    n_rewrote_subject = 0
    n_l1_with_no_opens = 0
    n_opens_no_family_resolved = 0
    l2_ranks = []
    counters = {"find_calls": 0, "find_with_q": 0, "have_called": 0, "tables_called": 0,
                "inside_calls": 0, "series_on_trajectory": 0, "n_trajectory": 0}

    for qid in answerable:
        q = qs_by_id[qid]
        rec, raw = SL.load_rec(a.phase, qid)
        if rec is None:
            per_q[qid] = {"status": "no_result"}
            continue
        results, cmds, _ = SL.read_transcript(raw)
        blob_n = SC.norm_text("\n".join(results))
        answer = rec.get("answer_text") or ""

        gold_addrs = {(SC.norm_path(e["path"]), e.get("page_index"))
                      for e in q["evidence_addresses"]}
        gold_paths = {p for p, _ in gold_addrs}
        gold_fams = {f for f in (family_of(ctx, p) for p in gold_paths) if f}

        surfaced = any(SC.norm_path(p) in blob_n or SC.path_tail(p, 2) in blob_n
                       for p in gold_paths)

        opens = SL.opens_from_bash(cmds)
        opened_paths = {rel for rel, _ in opens}
        opened_fams = {f for f in (family_of(ctx, r) for r in opened_paths) if f}
        if opened_paths and not opened_fams:
            n_opens_no_family_resolved += 1

        opened_gold_file = any(SL._same_path(r, p) for r in opened_paths for p in gold_paths)
        opened_gold_page = any(pg is not None and (p, pg) in gold_addrs
                               for r, pg in opens for p in gold_paths
                               if SL._same_path(r, p))
        cited = any(r.get("cited_right_page") for r in [])  # placeholder, see below

        scored = SL.score_answerable(q, rec, raw, [])
        cited = scored["cited_right_page"]

        if not surfaced:
            cls = "L0_family_not_surfaced"
        elif cited:
            cls = "L5_cited_right_page"
        elif opened_gold_page:
            cls = "L4_opened_right_page_not_cited"
        elif opened_gold_file:
            cls = "L3_opened_gold_file_wrong_page"
        elif opened_fams & gold_fams:
            cls = "L2_opened_same_family_other_edition"
        else:
            cls = "L1_surfaced_opened_other_family"
        totals[cls] += 1
        if cls == "L1_surfaced_opened_other_family" and not opens:
            n_l1_with_no_opens += 1

        # --- per-session command counters (counts only) -------------------
        fc = sum(1 for c in cmds if FIND_CMD.search(c))
        fq = sum(1 for c in cmds if FIND_CMD.search(c) and Q_FLAG.search(c))
        ic = sum(1 for c in cmds if INSIDE_CMD.search(c))
        counters["find_calls"] += fc
        counters["find_with_q"] += fq
        counters["inside_calls"] += ic
        if any(HAVE_CMD.search(c) for c in cmds):
            counters["have_called"] += 1
        if any(TABLES_CMD.search(c) for c in cmds):
            counters["tables_called"] += 1
        if q["type"] == "trajectory":
            counters["n_trajectory"] += 1
            if any(SERIES_CMD.search(c) for c in cmds):
                counters["series_on_trajectory"] += 1

        # --- vocabulary bridge: did the model search in its OWN words? ----
        qwords = set(content_words(q["question"]))
        rewrote = False
        for c in cmds:
            for m in TERMS_RE.finditer(c):
                terms = m.group(1) or m.group(2) or ""
                tw = set(content_words(terms))
                if tw - qwords:
                    rewrote = True
        if rewrote:
            n_rewrote_subject += 1

        # --- for L2: where the gold edition sat vs what was opened --------
        rank_gold = rank_opened = None
        if cls == "L2_opened_same_family_other_edition":
            for fam in (opened_fams & gold_fams):
                eds, _n, _k = CSH._editions_for_family(ctx, fam)
                order = [e["rel"] for e in eds]
                for i, rel in enumerate(order, start=1):
                    if rank_gold is None and any(SL._same_path(rel, p) for p in gold_paths):
                        rank_gold = i
                    if rank_opened is None and any(SL._same_path(rel, o) for o in opened_paths):
                        rank_opened = i
                break
            l2_ranks.append({"q_id": qid, "gold_edition_rank": rank_gold,
                             "opened_edition_rank": rank_opened,
                             "n_editions": len(order) if 'order' in dir() else None})

        per_q[qid] = {"type": q["type"], "class": cls, "surfaced": surfaced,
                      "n_find": fc, "n_find_with_q": fq, "n_inside": ic,
                      "rewrote_subject_in_own_words": rewrote,
                      "n_opens": len(opens)}

    n = len([v for v in per_q.values() if "class" in v])
    surfaced_n = sum(1 for v in per_q.values() if v.get("surfaced"))
    mid = {c: totals[c] for c in CLASSES[1:5]}
    top = max(mid.values()) if mid else 0
    dominant = [c for c, v in mid.items() if v == top and v > 0]
    dominant_class = dominant[0] if len(dominant) == 1 else None

    report = {
        "phase": a.phase, "n_answerable_scored": n,
        "n_surfaced": surfaced_n,
        "class_totals": totals,
        "dominant_class_L1_L4": dominant_class,
        "dominant_class_count": top,
        "dominant_qualifies_ge4_of_surfaced": bool(dominant_class and top >= 4),
        "counters": counters,
        "n_sessions_rewrote_subject_in_own_words": n_rewrote_subject,
        "n_L1_sessions_that_opened_nothing_at_all": n_l1_with_no_opens,
        "n_sessions_where_no_open_resolved_to_a_family": n_opens_no_family_resolved,
        "l2_edition_ranks": l2_ranks,
        "per_question": per_q,
    }
    (L.STATE / a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_question"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
