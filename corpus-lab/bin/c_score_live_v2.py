#!/usr/bin/env python
"""c_score_live_v2.py -- the live scorer, measuring what the professor cares about.

c_score_live.py is frozen and stays the strict reference. This file imports it,
reports its number as `cited_right_page_strict` alongside everything below, and
never deletes it.

WHY (Session Log A.2.4, F62, and section 1.5 of the Phase 9 plan): the strict
rule marks an answer right only if it cites the ONE address the key names. Two
models across four sessions reported the same figure from four different
official publications and every one scored 0. The answer key itself disagrees
with that rule -- it carries `acceptable_alternates` on 45 of 135 questions, and
a series_id/vintage_id/fy on every evidence address -- and the generator's own
placement records know every page that prints a given cell. Meanwhile 1-5 of
every 17 sessions per battery ended with NO ANSWER TEXT AT ALL because the
harness capped them, and each was scored a miss, so part of the measured loss
was never the system's.

So v2 adds five columns, all side by side with the strict one:

  cited_right_page_equiv   a cited (file, page) also counts if that page prints
                           the SAME CELL -- same series_id, vintage_id and fy --
                           as a gold evidence address, per the generator's
                           per-document table placement records.
  value_correct            the answer states the key's value, or any acceptable
                           alternate's value, as a number within +/-0.5%.
  value_wrong_confident    the answer states some other number with the right
                           unit beside the row's own words, and no correct value.
  no_answer_cause          per session: max_turns | timeout | other_empty | answered.
  cited_no_path            answers carrying figures and no citation at all
                           (F62's "guard satisfied by silence").

Also reported: `answered_within_300s`, so a like-for-like row against P5-P8
(which ran at 25 turns / 300 s) exists whatever limits the battery used.

This is a scoring script, so it may open the answer key and the generator's
placement records. It writes COUNTS ONLY to the public copy -- never a path,
value, title or row label.

  python c_score_live_v2.py --phase P9S_live --abs-phase P5_live_abs
  python c_score_live_v2.py --selftest

Writes:
  corpus-lab/state/c_live_battery_v2__<phase>.json   aggregate only, public
  _private/results/04_scores/live_v2__<phase>.json   per-question booleans, ids only
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import scoring as SC  # noqa: E402
import c_score_live as V1  # noqa: E402

STACK = V1.STACK
CORPUS_LABEL = V1.CORPUS_LABEL

UNIT_WORDS = ("billion", "million", "percent", "%", "rs", "rupees", "tonnes",
              "thousand", "trillion", "crore", "lakh", "kg", "mt")
VALUE_TOLERANCE = 0.005          # +/- 0.5%, pre-registered
NUM_IN_TEXT = re.compile(r"(?<![A-Za-z0-9.])(\d[\d,]*(?:\.\d+)?)(?![A-Za-z0-9])")


# --------------------------------------------------------------------- #
# the placement registry: which page prints which cell
# --------------------------------------------------------------------- #
def build_placement_registry(verbose=True):
    """{(norm_path, page_index): {(series_id, vintage_id, fy), ...}}

    Source, in the order section 4.1 of the plan gives: the generator's
    per-document table index under _private/harness_keys/pdf_index/. Each file
    is one document and lists its tables with page_index, series_id, vintage_id
    and the fiscal years its columns carry -- which is exactly "this page prints
    this cell"."""
    d = L.HARNESS_KEYS / "pdf_index"
    reg = {}
    n_files = n_tables = 0
    if not d.is_dir():
        return reg, {"source": "MISSING", "n_files": 0, "n_tables": 0, "n_pages": 0}
    for f in d.glob("*.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        path = SC.norm_path(rec.get("path") or "")
        if not path:
            continue
        n_files += 1
        for t in rec.get("tables") or []:
            n_tables += 1
            pi = t.get("page_index")
            if pi is None:
                continue
            sid, vid = t.get("series_id"), t.get("vintage_id")
            fys = list((t.get("cells") or t.get("cols") or {}).keys())
            if not fys:
                fys = [None]
            cell = reg.setdefault((path, int(pi)), set())
            for fy in fys:
                cell.add((sid, vid, fy))
    if verbose:
        print("placement registry: %d documents, %d tables, %d pages"
              % (n_files, n_tables, len(reg)), file=sys.stderr)
    return reg, {"source": "pdf_index", "n_files": n_files,
                 "n_tables": n_tables, "n_pages": len(reg)}


def validate_registry(reg, qs_by_id):
    """Every gold evidence address must itself be reproduced by the registry, or
    the registry is not describing the same world and equivalence does not ship.
    Pre-registered bar: >= 0.95."""
    n_total = n_ok = 0
    for q in qs_by_id.values():
        for e in q.get("evidence_addresses") or []:
            if e.get("page_index") is None:
                continue
            n_total += 1
            key = (SC.norm_path(e.get("path") or ""), int(e["page_index"]))
            cells = reg.get(key)
            if not cells:
                continue
            want = (e.get("series_id"), e.get("vintage_id"), e.get("fy"))
            if want in cells or any(c[0] == want[0] and c[2] == want[2] for c in cells):
                n_ok += 1
    frac = (n_ok / n_total) if n_total else 0.0
    return {"n_gold_addresses": n_total, "n_gold_addresses_reproduced": n_ok,
            "fraction": round(frac, 4), "bar": 0.95, "usable": frac >= 0.95}


# --------------------------------------------------------------------- #
# the answer's own citations
# --------------------------------------------------------------------- #
def cited_pairs(answer, opened_pairs):
    """The (path, page) pairs the ANSWER actually cites, drawn from what the
    session opened. Same test the strict scorer applies, minus the requirement
    that the pair be a gold address -- which is the whole point: a page that
    prints the same cell from a different publication is still a right answer."""
    out = set()
    stripped = V1.strip_addressy(answer)
    for rel, pg in opened_pairs:
        if pg is None:
            continue
        named, _ = SC.answer_names_path(answer, rel)
        if not named:
            continue
        if re.search(r"\bp\.?\s?%d\b" % pg, answer, re.I) or \
           re.search(r"\bpage\s+%d\b" % pg, answer, re.I) or \
           re.search(r"\b%d\b" % pg, stripped):
            out.add((rel, pg))
    return out


def gold_cells(q):
    """{(series_id, vintage_id, fy)} the question's gold addresses print."""
    out = set()
    for e in q.get("evidence_addresses") or []:
        out.add((e.get("series_id"), e.get("vintage_id"), e.get("fy")))
    return out


# --------------------------------------------------------------------- #
# the value
# --------------------------------------------------------------------- #
def _as_float(v):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.replace(",", "").strip()
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
    return None


def accepted_values(q):
    """[(value, vintage_id_or_None), ...] -- the key's own answer plus every
    alternate the key itself declares acceptable."""
    out = []
    ea = q.get("expected_answer") or {}
    v = _as_float(ea.get("value"))
    if v is not None:
        out.append((v, ea.get("vintage_id")))
    for alt in q.get("acceptable_alternates") or []:
        av = _as_float(alt.get("value"))
        if av is not None:
            out.append((av, alt.get("vintage_id")))
    return out


def answer_numbers(answer):
    out = []
    for m in NUM_IN_TEXT.finditer(answer or ""):
        try:
            out.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass
    return out


def score_value(q, answer):
    """value_correct / which vintage matched / value_wrong_confident."""
    accepted = accepted_values(q)
    nums = answer_numbers(answer)
    matched_vintage = None
    correct = False
    for want, vintage in accepted:
        tol = abs(want) * VALUE_TOLERANCE
        for n in nums:
            if abs(n - want) <= max(tol, 1e-9):
                correct = True
                matched_vintage = vintage
                break
        if correct:
            break

    wrong_confident = False
    if not correct and accepted:
        # a number carrying the right unit, beside the row's own words
        row_label = ((q.get("expected_answer") or {}).get("row_label") or "")
        row_words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", row_label)]
        toks = re.findall(r"\S+", answer or "")
        low = [t.lower() for t in toks]
        for i, t in enumerate(toks):
            if not NUM_IN_TEXT.search(t):
                continue
            window = low[max(0, i - 3):i + 4]
            if not any(any(u == w.strip(".,;:()") for u in UNIT_WORDS) for w in window):
                continue
            if row_words and not any(rw in " ".join(low) for rw in row_words):
                continue
            wrong_confident = True
            break

    return {"value_correct": correct,
            "value_matched_vintage": matched_vintage,
            "value_wrong_confident": wrong_confident,
            "n_accepted_values": len(accepted),
            "n_alternates": len(q.get("acceptable_alternates") or [])}


# --------------------------------------------------------------------- #
# why a session produced nothing
# --------------------------------------------------------------------- #
def no_answer_cause(rec, max_turns):
    answer = (rec or {}).get("answer_text") or ""
    if answer.strip():
        return "answered"
    if (rec or {}).get("timed_out"):
        return "timeout"
    turns = (rec or {}).get("turns")
    if turns is not None and max_turns and turns >= max_turns:
        return "max_turns"
    return "other_empty"


def has_any_citation(answer):
    return bool(V1.answer_paths(answer)) or bool(
        re.search(r"(?<![A-Za-z0-9])p\.?\s?\d{1,4}(?![0-9-])", answer or "", re.I))


# --------------------------------------------------------------------- #
# per question
# --------------------------------------------------------------------- #
def score_answerable_v2(q, rec, raw_path, notes_texts, reg, reg_usable, max_turns):
    strict = V1.score_answerable(q, rec, raw_path, notes_texts)
    answer = (rec or {}).get("answer_text") or ""

    _results, bash_cmds, _t = V1.read_transcript(raw_path)
    opens = V1.opens_from_bash(bash_cmds)
    for f in (rec or {}).get("files_opened", []) or []:
        if f.get("path"):
            opens.append((SC.norm_path(f["path"]), None))
    pairs = {(rel, pg) for rel, pg in opens if pg is not None}

    cited = cited_pairs(answer, pairs)
    want_cells = gold_cells(q)
    equiv = bool(strict["cited_right_page"])
    equiv_via_other_publication = False
    if reg_usable and not equiv:
        for rel, pg in cited:
            cells = reg.get((SC.norm_path(rel), int(pg)))
            if not cells:
                continue
            for c in cells:
                if c in want_cells or any(
                        c[0] == w[0] and c[0] is not None and c[2] == w[2]
                        for w in want_cells):
                    equiv = True
                    equiv_via_other_publication = True
                    break
            if equiv:
                break

    figures = V1.answer_figures(answer)
    out = dict(strict)
    out.update(score_value(q, answer))
    out.update({
        "cited_right_page_strict": bool(strict["cited_right_page"]),
        "cited_right_page_equiv": bool(equiv),
        "equiv_via_other_publication": equiv_via_other_publication,
        "n_cited_pairs": len(cited),
        "cited_no_path": bool(figures) and not has_any_citation(answer),
        "no_answer_cause": no_answer_cause(rec, max_turns),
        "answered_within_300s": (rec or {}).get("wall_s") is not None
                                and (rec or {}).get("wall_s") <= 300
                                and bool(answer.strip()),
        "turns": (rec or {}).get("turns"),
        "suspended": bool((rec or {}).get("suspended")),
    })
    return out


def score_absence_v2(q, rec, raw_path, max_turns):
    out = dict(V1.score_absence(q, rec, raw_path))
    answer = (rec or {}).get("answer_text") or ""
    out.update({
        "no_answer_cause": no_answer_cause(rec, max_turns),
        "answered_within_300s": (rec or {}).get("wall_s") is not None
                                and (rec or {}).get("wall_s") <= 300
                                and bool(answer.strip()),
        "turns": (rec or {}).get("turns"),
        "suspended": bool((rec or {}).get("suspended")),
    })
    return out


# --------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------- #
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P5_live")
    ap.add_argument("--abs-phase", dest="abs_phase", default="P5_live_abs")
    ap.add_argument("--max-turns", dest="max_turns", type=int, default=25,
                    help="the cap the battery ran under, for no_answer_cause")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    import c_shelf as CSH
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sorted(sample["q_ids"])
    answerable = [i for i in frozen_ids if qs_by_id[i]["type"] != "absence"]
    frozen_abs = [i for i in frozen_ids if qs_by_id[i]["type"] == "absence"]
    extra_abs = sorted(q["q_id"] for q in key["questions"]
                       if q["type"] == "absence" and q["q_id"] not in set(frozen_ids))[:12]

    reg, reg_meta = build_placement_registry()
    reg_val = validate_registry(reg, qs_by_id)
    reg_usable = bool(reg_val["usable"])
    if not reg_usable:
        print("EQUIV_REGISTRY_NOT_FOUND fraction=%.3f (bar 0.95) -- shipping "
              "value/no-answer columns only" % reg_val["fraction"], file=sys.stderr)

    notes_dir = CSH._notes_dir(str((L.HARNESS / "corpus_15000").resolve()))
    ntexts = V1.notes_texts_for(notes_dir)

    per_q, per_abs = [], []
    for qid in answerable:
        rec, raw = V1.load_rec(a.phase, qid)
        if rec is None:
            per_q.append({"q_id": qid, "type": qs_by_id[qid]["type"], "status": "no_result"})
            continue
        per_q.append(score_answerable_v2(qs_by_id[qid], rec, raw, ntexts,
                                         reg, reg_usable, a.max_turns))
    for qid, ph in [(i, a.phase) for i in frozen_abs] + [(i, a.abs_phase) for i in extra_abs]:
        rec, raw = V1.load_rec(ph, qid)
        if rec is None:
            per_abs.append({"q_id": qid, "type": "absence", "status": "no_result"})
            continue
        per_abs.append(score_absence_v2(qs_by_id[qid], rec, raw, a.max_turns))

    done = [r for r in per_q if "status" not in r]
    absdone = [r for r in per_abs if "status" not in r]
    frozen_abs_done = [r for r in absdone if r["q_id"] in set(frozen_abs)]
    walls = sorted(r["wall_s"] for r in per_q + per_abs
                   if r.get("wall_s") is not None and not r.get("timed_out"))
    costs = [r["cost_usd"] for r in per_q + per_abs if r.get("cost_usd") is not None]

    def cause(rows, name):
        return sum(1 for r in rows if r.get("no_answer_cause") == name)

    agg = {
        "scorer": "v2", "phase": a.phase, "abs_phase": a.abs_phase,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_turns_assumed": a.max_turns,
        "n_answerable_denominator": 17, "n_answerable_done": len(done),
        "n_absence_frozen_denominator": 3, "n_absence_frozen_done": len(frozen_abs_done),
        "n_absence_all_denominator": 15, "n_absence_all_done": len(absdone),

        # the strict column, unchanged and never deleted
        "cited_right_page_strict": sum(1 for r in done if r["cited_right_page_strict"]),
        "cited_unopened_total": sum(r["cited_unopened"] for r in done),
        "surfaced": sum(1 for r in done if r["surfaced"]),
        "opened_any": sum(1 for r in done if r["opened_any_evidence_file"]),
        "opened_right_page": sum(1 for r in done if r["opened_right_page"]),
        "figures_ungrounded_total": sum(r["figures_ungrounded"] for r in done),
        "forbidden_total": sum(r["forbidden"] for r in done),

        # v2
        "cited_right_page_equiv": sum(1 for r in done if r["cited_right_page_equiv"]),
        "equiv_via_other_publication": sum(1 for r in done
                                           if r["equiv_via_other_publication"]),
        "value_correct": sum(1 for r in done if r["value_correct"]),
        "value_wrong_confident": sum(1 for r in done if r["value_wrong_confident"]),
        "cited_no_path": sum(1 for r in done if r["cited_no_path"]),
        "no_answer_answered": cause(done + absdone, "answered"),
        "no_answer_max_turns": cause(done + absdone, "max_turns"),
        "no_answer_timeout": cause(done + absdone, "timeout"),
        "no_answer_other_empty": cause(done + absdone, "other_empty"),
        "answered_within_300s": sum(1 for r in done + absdone
                                    if r.get("answered_within_300s")),
        "n_suspended": sum(1 for r in done + absdone if r.get("suspended")),

        # absence, from the frozen v2 rule
        "absence_ok3_frozen3": sum(1 for r in frozen_abs_done if r.get("absence_ok3")),
        "absence_ok3_all15": sum(1 for r in absdone if r.get("absence_ok3")),
        "absence_ok2_frozen3": sum(1 for r in frozen_abs_done if r.get("absence_ok2")),
        "absence_ok2_all15": sum(1 for r in absdone if r.get("absence_ok2")),

        "median_wall_s": walls[len(walls) // 2] if walls else None,
        "p90_wall_s": walls[int(len(walls) * 0.9)] if walls else None,
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "cost_n_of_m": "%d/%d" % (len(costs), len(per_q) + len(per_abs)),
        "timeouts": sum(1 for r in per_q + per_abs if r.get("timed_out")),

        "equivalence_registry": dict(reg_meta, **reg_val),
        "equivalence_shipped": reg_usable,
    }

    # Gate LIVE-5, pre-registered in state/phase9_live_spec.md before any session.
    no_answer_cap_hits = agg["no_answer_max_turns"] + agg["no_answer_timeout"]
    if reg_usable:
        hits, pass_bar, weak_lo = agg["cited_right_page_equiv"], 5, 3
    else:
        hits, pass_bar, weak_lo = agg["cited_right_page_strict"], 4, 2
    others_ok = (agg["cited_unopened_total"] == 0
                 and agg["absence_ok3_frozen3"] >= 2
                 and no_answer_cap_hits <= 1)
    agg["gate_live5_column"] = "equiv" if reg_usable else "strict"
    agg["gate_live5"] = ("PASS" if (hits >= pass_bar and others_ok)
                         else "WEAK" if (weak_lo <= hits < pass_bar and others_ok)
                         else "STOP")

    L.SCORES.mkdir(parents=True, exist_ok=True)
    (L.SCORES / ("live_v2__%s.json" % a.phase)).write_text(
        json.dumps({"aggregate": agg, "answerable": per_q, "absence": per_abs},
                   indent=1), encoding="utf-8")
    (L.STATE / ("c_live_battery_v2__%s.json" % a.phase)).write_text(
        json.dumps(agg, indent=1), encoding="utf-8")
    print(json.dumps(agg, indent=1))
    return 0


# --------------------------------------------------------------------- #
# regression self-test: v2 must reproduce the frozen scorer on P8_live
# --------------------------------------------------------------------- #
def selftest():
    """Section 4.2: on P8_live, cited_right_page_strict, cited_unopened_total and
    absence_ok3 must equal the recorded 1 / 0 / 2-of-3. Any difference is a bug in
    v2, never a correction to the record."""
    import c_shelf as CSH
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sorted(sample["q_ids"])
    answerable = [i for i in frozen_ids if qs_by_id[i]["type"] != "absence"]
    frozen_abs = [i for i in frozen_ids if qs_by_id[i]["type"] == "absence"]

    reg, _ = build_placement_registry(verbose=False)
    reg_val = validate_registry(reg, qs_by_id)
    notes_dir = CSH._notes_dir(str((L.HARNESS / "corpus_15000").resolve()))
    ntexts = V1.notes_texts_for(notes_dir)

    strict_hits = unopened = 0
    for qid in answerable:
        rec, raw = V1.load_rec("P8_live", qid)
        if rec is None:
            continue
        r = score_answerable_v2(qs_by_id[qid], rec, raw, ntexts, reg,
                                reg_val["usable"], 25)
        strict_hits += 1 if r["cited_right_page_strict"] else 0
        unopened += r["cited_unopened"]
    abs_ok = 0
    n_abs = 0
    for qid in frozen_abs:
        rec, raw = V1.load_rec("P8_live", qid)
        if rec is None:
            continue
        n_abs += 1
        abs_ok += 1 if score_absence_v2(qs_by_id[qid], rec, raw, 25)["absence_ok3"] else 0

    checks = [
        ("p8_cited_right_page_strict_is_1", strict_hits == 1, strict_hits),
        ("p8_cited_unopened_total_is_0", unopened == 0, unopened),
        ("p8_absence_ok3_is_2_of_3", (abs_ok, n_abs) == (2, 3), "%d/%d" % (abs_ok, n_abs)),
        ("registry_reproduces_gold_addresses", reg_val["usable"], reg_val["fraction"]),
    ]
    rec = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_checks": len(checks), "n_passed": sum(1 for c in checks if c[1]),
           "all_pass": all(c[1] for c in checks),
           "checks": [{"check": c[0], "pass": bool(c[1]), "got": c[2]} for c in checks],
           "registry": reg_val}
    (L.STATE / "c_score_live_v2_selftest.json").write_text(
        json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    return 0 if rec["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
