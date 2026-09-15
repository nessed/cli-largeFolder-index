#!/usr/bin/env python
"""p10_rescore_compare.py - v2 beside v3, with a reason for every difference.

Plan E §1.6. The point is not to replace v2's numbers. It is to put the two
readings of the SAME recordings next to each other so a reader can see which
differences are the four corrections v3 was built to make, and which are
something else that needs explaining.

Phase 9's verdicts were set by the pre-registered v2 scorer and stand unchanged;
they are restated verbatim in `historical_verdicts_unchanged`.

Writes corpus-lab/state/c_rescore_v2_vs_v3.json. Counts and q_ids only.

  python p10_rescore_compare.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
from c_score_live_v3 import CITATION_WINDOW as V3_WINDOW  # noqa: E402

PHASES = ["P5_live", "P6_live", "P7_live", "P8_live", "P9S_live", "P9O_live"]

AGG_FIELDS = [
    "cited_right_page_strict", "cited_right_page_equiv", "cited_unopened_total",
    "mentioned_unopened_total", "n_answer_fragments", "n_opens_loop_only_total",
    "surfaced", "opened_any", "opened_right_page", "absence_ok3_frozen3",
]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def why(field, v2r, v3r):
    """One line explaining ONE per-question difference.

    Attribution matters here: a reader has to be able to tell which of v3's four
    corrections moved a given number, and a catch-all reason would hide exactly
    the disagreements this file exists to surface.
    """
    frag = ("the recorded answer was a post-guard fragment (%d -> %d chars), so "
            "v2 scored only the confirmation reply"
            % (v3r.get("len_answer_recorded", 0), v3r.get("len_answer_full", 0))
            ) if v3r.get("answer_was_fragment") else None
    loop = ("%d open(s) are visible only in tool output (opened inside a shell "
            "loop), which v2 could not see"
            % v3r.get("n_opens_loop_only", 0)) if v3r.get("n_opens_loop_only") else None

    if field in ("cited_right_page_equiv", "cited_right_page_strict"):
        gained = bool(v3r.get(field)) and not bool(v2r.get(field))
        if gained:
            return ("; ".join(x for x in (frag, loop) if x)
                    or "v3 credits a citation v2 missed")
        # v3 withdrew the credit
        if not v3r.get("n_citations"):
            return ("v3 finds NO page citation in this answer at all (%d path "
                    "mention(s), no page token beside any of them). v2 credited "
                    "the pair because the page NUMBER appeared somewhere in the "
                    "answer text; v3 requires the page beside the path."
                    % v3r.get("n_mentions", 0))
        return ("v3 requires the cited page to sit within %d characters of the "
                "path (or in the `path | pN` form); v2 accepted the bare page "
                "number anywhere in the answer" % V3_WINDOW)

    if field == "cited_unopened":
        parts = []
        if (v3r.get("cited_unopened") or 0) < (v2r.get("cited_unopened") or 0):
            if v3r.get("mentioned_unopened"):
                parts.append("%d path(s) reclassified from citation to mention "
                             "(named in prose, no page)"
                             % v3r["mentioned_unopened"])
            if loop:
                parts.append(loop)
        else:
            if frag:
                parts.append(frag + " -- the fuller answer contains a citation "
                                    "the fragment did not")
        return "; ".join(parts) or "citation set changed under v3's parsing rules"

    if field == "value_correct":
        if not v3r.get("value_scorable"):
            return ("the key carries no numeric value for this question, so it "
                    "is in no value denominator under v3")
        return "value matched under v3's reading of the answer text"

    return "; ".join(x for x in (frag, loop) if x) or "difference not attributed"


def main():
    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "what_this_is": (
            "The same recordings read by two scorers. v2 is the pre-registered "
            "instrument that set every Phase 9 verdict; v3 corrects four parsing "
            "defects found by an independent audit. No verdict changes."),
        "phases": {},
        "historical_verdicts_unchanged": {},
    }

    for ph in PHASES:
        v2agg = load(L.STATE / ("c_live_battery_v2__%s.json" % ph))
        v3agg = load(L.STATE / ("c_live_battery_v3__%s.json" % ph))
        v2per = load(L.SCORES / ("live_v2__%s.json" % ph))
        v3per = load(L.SCORES / ("live_v3__%s.json" % ph))

        v2rows = {r["q_id"]: r for r in v2per["answerable"] if "status" not in r}
        v3rows = {r["q_id"]: r for r in v3per["answerable"] if "status" not in r}

        agg_cmp = {}
        for f in AGG_FIELDS:
            a, b = v2agg.get(f), v3agg.get(f)
            agg_cmp[f] = {"v2": a, "v3": b, "delta": (
                (b - a) if isinstance(a, (int, float)) and isinstance(b, (int, float))
                else None)}
        # value, with its denominator made explicit on both sides
        agg_cmp["value_correct"] = {
            "v2": "%s/17 (v2 used the wrong denominator)" % v2agg.get("value_correct"),
            "v3": v3agg.get("value_correct_of"),
            "n_keyed": v3agg.get("n_keyed"),
            "n_unscorable_value": v3agg.get("n_unscorable_value"),
        }

        diffs = []
        for qid in sorted(set(v2rows) | set(v3rows)):
            a, b = v2rows.get(qid, {}), v3rows.get(qid, {})
            fields = {}
            for f in ("cited_right_page_strict", "cited_right_page_equiv",
                      "cited_unopened", "value_correct"):
                if a.get(f) != b.get(f):
                    fields[f] = {"v2": a.get(f), "v3": b.get(f)}
            if fields:
                diffs.append({
                    "q_id": qid, "fields": fields,
                    "why": {f: why(f, a, b) for f in fields},
                    "v3_detail": {
                        "n_opens_from_output": b.get("n_opens_from_output"),
                        "n_opens_from_command": b.get("n_opens_from_command"),
                        "n_opens_loop_only": b.get("n_opens_loop_only"),
                        "n_citations": b.get("n_citations"),
                        "n_mentions": b.get("n_mentions"),
                        "mentioned_unopened": b.get("mentioned_unopened"),
                        "answer_was_fragment": b.get("answer_was_fragment"),
                        "value_scorable": b.get("value_scorable"),
                    }})

        out["phases"][ph] = {
            "aggregate": agg_cmp,
            "n_questions_with_a_difference": len(diffs),
            "per_question_differences": diffs,
            "cited_unopened_by_question_v3": {
                q: r["cited_unopened"] for q, r in sorted(v3rows.items())
                if r.get("cited_unopened")},
            "cited_unopened_by_question_v2": {
                q: r["cited_unopened"] for q, r in sorted(v2rows.items())
                if r.get("cited_unopened")},
            "scorer_v3_sha256": v3agg.get("scorer_sha256"),
            "key_file": v3agg.get("key_file"),
            "key_sha256": v3agg.get("key_sha256"),
            "group_definition_sha256": v3agg.get("group_definition_sha256"),
        }
        out["historical_verdicts_unchanged"][ph] = {
            "scorer": "v2 (pre-registered)",
            "gate_live5": v2agg.get("gate_live5"),
            "gate_live5_column": v2agg.get("gate_live5_column"),
            "note": "This verdict stands as recorded. v3 does not revisit it.",
        }

    dest = L.STATE / "c_rescore_v2_vs_v3.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s" % dest)
    for ph in PHASES:
        a = out["phases"][ph]["aggregate"]
        print("%-10s equiv %s->%s   unopened %s->%s   mentions_v3=%s   frags_v3=%s   loop_v3=%s"
              % (ph,
                 a["cited_right_page_equiv"]["v2"], a["cited_right_page_equiv"]["v3"],
                 a["cited_unopened_total"]["v2"], a["cited_unopened_total"]["v3"],
                 a["mentioned_unopened_total"]["v3"],
                 a["n_answer_fragments"]["v3"], a["n_opens_loop_only_total"]["v3"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
