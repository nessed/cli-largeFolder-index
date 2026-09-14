#!/usr/bin/env python
"""c_edition_gate.py - 2026-09-14, phase "corrected continuation", Phase 6.

Measures ONE thing: given the right publication family, can the shelf's own
structural metadata narrow it to the right edition(s) without reading a page?

This isolates edition selection the same way the series gate isolates the walk
-- the gold family is handed in, so nothing here is a statement about family
retrieval. It exists because F42 found that the trajectory walk's failure was
not page retrieval at all: the years lined up, the files did not.

Key access is confined to this file and to c_offline_gate.py. Prints and
persists COUNTS, question ids and booleans only: never a path, a title, a
family name, a caption, a row label or an expected value.

The three branch rules below are structural and come from the question TEXT
plus the shelf's own metadata. No hand-written year rule, title list or
synonym list -- the fiscal-year regex and the series-cue regex are the ones
that already exist in c_offline_gate.py.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

# the generic trajectory scaffolding already used by row_words_from_question
_SERIES_FILLER = ("decade", "trajectory", "across", "years")


def branch_for(question, qtype):
    """Which structural narrowing applies. Question text only."""
    m = G.FY_RE.search(question)
    if m:
        return "fy_token", m.group(1)
    low = question.lower()
    if (qtype == "trajectory" or G._ROW_SEP_RE.search(question)
            or any(w in low for w in _SERIES_FILLER)):
        return "series", None
    return "all_primaries", None


def _fy_all(row_fy_all):
    try:
        v = json.loads(row_fy_all) if row_fy_all else []
        return v if isinstance(v, list) else []
    except Exception:
        return []


def main():
    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    fy_all_by_rel = dict(ctx.shelf.execute("SELECT rel, fy_all FROM docs"))

    qs_by_id, answerable_ids, per_q, _ = G.load_frozen(ctx)

    per_question = {}
    set_sizes = []
    n_recall = 0
    n_all_primaries = 0
    branch_fail = {}
    n_primary_is_the_cited_file = 0
    n_editions_checked = 0

    for qid in answerable_ids:
        pq = per_q[qid]
        rels = pq["resolved_rels"]
        if not rels:
            per_question[qid] = {"skipped": "evidence_not_on_shelf"}
            continue

        # gold family: the one holding the most of this question's evidence,
        # same tie-break the series measurement already uses.
        fam_counts = {}
        for r in rels:
            f = ctx.rel_to_family.get(r)
            if f:
                fam_counts[f] = fam_counts.get(f, 0) + 1
        if not fam_counts:
            per_question[qid] = {"skipped": "no_family"}
            continue
        family = max(fam_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]

        members = [ctx.rel_to_row[r] for r in ctx.family_to_rels.get(family, ())]
        primaries = [r for r in members if r["is_primary"]]
        family_size = len(primaries)

        branch, fy = branch_for(pq["question"], pq["type"])
        if branch == "fy_token":
            sel = [r for r in primaries if fy in _fy_all(fy_all_by_rel.get(r["rel"]))]
            if not sel:
                # the year is asked for but no primary declares it: the rule
                # gives an empty set, which is a failure of the rule, not a
                # licence to fall back to everything.
                sel = []
        else:
            sel = list(primaries)
            if branch == "all_primaries":
                n_all_primaries += 1

        sel_keys = {r["edition_key"] for r in sel}
        sel_rels = {r["rel"] for r in sel}

        # An evidence address is covered when the SET CONTAINS ITS EDITION.
        # Tracked separately: whether the selected primary is the very file the
        # key cites, because F42 showed a page index does not carry from one
        # copy of an edition to another.
        covered = []
        for r in rels:
            row = ctx.rel_to_row.get(r)
            if not row:
                continue
            n_editions_checked += 1
            covered.append(row["edition_key"] in sel_keys)
            if r in sel_rels:
                n_primary_is_the_cited_file += 1
        all_in = bool(covered) and all(covered)
        if all_in:
            n_recall += 1
        else:
            branch_fail[branch] = branch_fail.get(branch, 0) + 1
        set_sizes.append(len(sel))

        per_question[qid] = {
            "type": pq["type"], "branch": branch,
            "all_evidence_editions_in_set": all_in,
            "set_size": len(sel), "family_size": family_size,
            "n_evidence_editions": len(covered),
            "n_evidence_editions_in_set": sum(covered),
        }

    n = len(answerable_ids)
    mean_set = round(sum(set_sizes) / float(len(set_sizes)), 2) if set_sizes else None
    report = {
        "n_answerable": n,
        "set_recall_questions": n_recall,
        "mean_set_size": mean_set,
        "max_set_size": max(set_sizes) if set_sizes else None,
        "n_questions_rule_was_all_primaries": n_all_primaries,
        "failures_by_branch": branch_fail,
        "n_evidence_editions_checked": n_editions_checked,
        "n_selected_primary_is_the_cited_file": n_primary_is_the_cited_file,
        "per_question": per_question,
    }
    out = L.STATE / "c_edition_set.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_question"}, indent=1))
    return report


if __name__ == "__main__":
    main()
