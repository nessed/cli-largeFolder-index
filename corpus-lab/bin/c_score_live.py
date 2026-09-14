#!/usr/bin/env python
"""c_score_live.py -- the scorer for the 2026-09-15 live battery.

The offline gates measure retrieval with the agent taken out of the loop. This
scorer measures the agent, and the whole point of it is to separate the two:

  surfaced             the shelf put an evidence path in front of the session
  opened_right_page    the session opened that path at the page the key cites
  cited_right_page     the answer cites a page the session had actually opened
  cited_unopened       paths the answer names that were never opened  <-- the
                       open-before-cite violation count
  figures_ungrounded   numbers in the answer that appear on no opened page

A session can surface everything and open nothing (a behaviour loss), or open
the right page and still cite the wrong one (an answering loss), or surface
nothing at all (a retrieval loss). Those three readings were fixed before any
session ran; this file only counts.

  python corpus-lab/bin/c_score_live.py --phase P5_live --abs-phase P5_live_abs
  python corpus-lab/bin/c_score_live.py --selftest

Writes per-question booleans and counts (ids only, never key content) to
_private/results/04_scores/live__s7_shelf__rung15000.json and an
aggregate-only public copy to corpus-lab/state/c_live_battery.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import scoring as SC  # noqa: E402
import run_harness as RH  # noqa: E402

STACK = "s7_shelf"
CORPUS_LABEL = "h15000"

# Figures that are addresses or published coverage counts, not claims about the
# world, and so are not "ungrounded" when they appear in an answer.
FY_TOKEN = re.compile(r"\b20[0-3]\d-\d\d\b")
YEAR4 = re.compile(r"\b(?:19|20)\d\d\b")
PAGE_REF = re.compile(r"\bp\d+\b", re.I)
PAGE_COUNT = re.compile(r"\(\d+p\)")
COVERAGE_COUNTS = {"13634", "1211", "1206260", "13,634", "1,211", "1,206,260"}
NUMTOK = re.compile(r"\d[\d,]*\.?\d*")

# --- absence scorer v2 (2026-09-15 pm), specified in
# state/absence_scorer_v2_spec.md BEFORE any transcript was read this phase.
# The shelf's own structural verdicts. A session that prints one of these has
# relayed the shelf's answer verbatim; the v1 decline regex did not know them.
SHELF_VERDICTS = ("NO_EDITION_FOR", "NO_FAMILY_MATCHES", "TOTAL_PAGES_MATCHING=0",
                  "NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING")
# One short generic regex over ways of saying "the folder does not hold it".
# Fixed in the spec; deliberately NOT extended by reading this battery.
DECLINE_PLAIN = re.compile(
    r"(do(es)?\s+not\s+hold|don'?t\s+hold|not\s+held|not\s+in\s+this\s+folder"
    r"|no\s+edition|not\s+on\s+the\s+shelf|no\s+readable\s+page\s+contains)", re.I)


# A path-ish token in free answer text: something with a corpus file extension.
ANSWER_PATH = re.compile(
    r"[A-Za-z0-9_\-./\\()\[\] ]{0,180}?\.(?:pdf|xlsx|xls|docx|doc|csv|txt|md)\b",
    re.I)

# `... c_shelf.py open "<rel>" <page_index>` inside a Bash command string.
OPEN_CMD = re.compile(
    r"open\s+(?P<q>[\"'])(?P<rel>.+?)(?P=q)\s+(?P<page>\d+)", re.S)
OPEN_CMD_BARE = re.compile(r"open\s+(?P<rel>\S+\.(?:pdf|xlsx|xls|docx|doc|csv|txt|md))\s+(?P<page>\d+)", re.I)
NOTE_CMD = re.compile(r"\bnote\s+--slug\b")
SERIES_CMD = re.compile(r"\bc_shelf\.py[\"']?\s+series\b")


# --------------------------------------------------------------------- #
# transcript reading
# --------------------------------------------------------------------- #
def read_transcript(raw_path):
    """Returns (tool_result_texts, bash_commands, assistant_text_blocks).

    rescore_from_results.py reads the same stream-json shape: `assistant`
    events carry tool_use blocks, `user` events carry tool_result blocks.
    """
    results, bash_cmds, texts = [], [], []
    if not Path(raw_path).exists():
        return results, bash_cmds, texts
    for line in Path(raw_path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        if t == "assistant":
            for c in d.get("message", {}).get("content", []) or []:
                if c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    if c.get("name") == "Bash" and inp.get("command"):
                        bash_cmds.append(inp["command"])
                elif c.get("type") == "text":
                    texts.append(c.get("text") or "")
        elif t == "user":
            content = d.get("message", {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "tool_result":
                        cc = c.get("content")
                        if isinstance(cc, str):
                            results.append(cc)
                        elif isinstance(cc, list):
                            for part in cc:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    results.append(part.get("text") or "")
    return results, bash_cmds, texts


def opens_from_bash(cmds):
    """[(rel_norm, page_index), ...] -- every `open` the session issued."""
    out = []
    for c in cmds:
        if "open" not in c:
            continue
        for rx in (OPEN_CMD, OPEN_CMD_BARE):
            for m in rx.finditer(c):
                rel = SC.norm_path(m.group("rel"))
                try:
                    out.append((rel, int(m.group("page"))))
                except ValueError:
                    pass
    return out


def _same_path(a, b):
    """Path equality under the tail-2 rule scoring.py already uses, with one
    relaxation this corpus forces: directory names here contain spaces, so a
    path lifted out of free answer text keeps whatever prose word preceded it
    ("from some_dir/a_report.pdf"). The leading segment is therefore matched by
    suffix rather than by equality -- conservative, because the filename and the
    tail of the parent directory must still agree exactly."""
    a, b = SC.norm_path(a), SC.norm_path(b)
    if not a or not b:
        return False
    if a == b or a.endswith("/" + b) or b.endswith("/" + a):
        return True
    sa = [s for s in a.split("/") if s]
    sb = [s for s in b.split("/") if s]
    if not sa or not sb or sa[-1] != sb[-1]:
        return False
    if len(sa) >= 2 and len(sb) >= 2:
        return sa[-2].endswith(sb[-2]) or sb[-2].endswith(sa[-2])
    return len(sa[-1]) >= SC.DISTINCTIVE_BASENAME_MIN


def answer_paths(answer):
    out = []
    for m in ANSWER_PATH.finditer(answer or ""):
        tok = m.group(0).strip().strip("`'\"()[],")
        if len(tok) > 4:
            out.append(SC.norm_path(tok))
    return out


def strip_addressy(text):
    t = FY_TOKEN.sub(" ", text or "")
    t = PAGE_COUNT.sub(" ", t)
    t = PAGE_REF.sub(" ", t)
    t = YEAR4.sub(" ", t)
    return t


def answer_figures(answer):
    """Numeric figures an answer asserts, excluding addresses and the published
    coverage counts."""
    out = []
    for m in NUMTOK.finditer(strip_addressy(answer)):
        tok = m.group(0).strip(".,")
        if not tok or tok in COVERAGE_COUNTS:
            continue
        if tok.replace(",", "") in {c.replace(",", "") for c in COVERAGE_COUNTS}:
            continue
        out.append(tok)
    return out


# --------------------------------------------------------------------- #
# per-question scoring
# --------------------------------------------------------------------- #
def score_answerable(q, rec, raw_path, notes_texts):
    ev_addrs = [(SC.norm_path(a["path"]), a.get("page_index"))
                for a in q.get("evidence_addresses", [])]
    ev_paths = {p for p, _ in ev_addrs}
    bad_paths = {SC.norm_path(m["path"]) for m in q.get("must_not_cite", [])}
    answer = (rec or {}).get("answer_text") or ""

    results, bash_cmds, _ = read_transcript(raw_path)
    blob = "\n".join(results)
    blob_n = SC.norm_text(blob)

    surfaced = any(SC.norm_path(p) in blob_n or SC.path_tail(p, 2) in blob_n
                   for p in ev_paths)

    opens = opens_from_bash(bash_cmds)
    for f in (rec or {}).get("files_opened", []) or []:
        if f.get("path"):
            opens.append((SC.norm_path(f["path"]), None))

    opened_any = any(_same_path(rel, p) for rel, _ in opens for p in ev_paths)
    opened_right_page = any(
        pg is not None and pg == page and _same_path(rel, p)
        for rel, pg in opens for p, page in ev_addrs if page is not None)

    opened_pairs = {(rel, pg) for rel, pg in opens if pg is not None}
    cited_right_page = False
    for p, page in ev_addrs:
        if page is None:
            continue
        named, _ = SC.answer_names_path(answer, p)
        if not named:
            continue
        if re.search(r"\b%d\b" % page, strip_addressy(answer)) or \
           re.search(r"\bp%d\b" % page, answer, re.I):
            if any(pg == page and _same_path(rel, p) for rel, pg in opened_pairs):
                cited_right_page = True
                break

    noted = any(NOTE_CMD.search(c) for c in bash_cmds)
    opened_paths = {rel for rel, _ in opens}
    cited_unopened = 0
    for ap in set(answer_paths(answer)):
        if not any(_same_path(ap, op) for op in opened_paths):
            cited_unopened += 1

    grounding = "\n".join(results) + "\n" + "\n".join(notes_texts)
    grounding_n = grounding.replace(",", "")
    figures_ungrounded = 0
    for fig in set(answer_figures(answer)):
        if fig in grounding or fig.replace(",", "") in grounding_n:
            continue
        figures_ungrounded += 1

    forbidden = sorted(p for p in bad_paths
                       if SC.answer_names_path(answer, p)[0])

    return {
        "q_id": q["q_id"], "type": q["type"],
        "surfaced": bool(surfaced),
        "opened_any_evidence_file": bool(opened_any),
        "opened_right_page": bool(opened_right_page),
        "cited_right_page": bool(cited_right_page),
        "noted": bool(noted),
        "cited_unopened": cited_unopened,
        "figures_ungrounded": figures_ungrounded,
        "series_used": any(SERIES_CMD.search(c) for c in bash_cmds),
        "forbidden": len(forbidden),
        "n_opens": len(opens),
        "timed_out": bool((rec or {}).get("timed_out")),
        "cost_usd": (rec or {}).get("cost_usd"),
        "wall_s": (rec or {}).get("wall_s"),
    }


def score_absence(q, rec, raw_path=None):
    """Both rules at once. v1 (`absence_ok2`) is computed exactly as it was
    overnight and is never removed; v2 (`absence_ok3`) applies the repair
    pre-registered in state/absence_scorer_v2_spec.md."""
    answer = (rec or {}).get("answer_text") or ""
    results, _bash, _t = read_transcript(raw_path) if raw_path else ([], [], [])
    tool_blob = "\n".join(results)

    # ---- v1, unchanged ---------------------------------------------------
    declined = bool(RH.DECLINE.search(answer))
    figures_asserted = len(answer_figures(answer))
    edition_list = bool(
        "NO_EDITION_FOR" in answer or "NO_FAMILY_MATCHES" in answer
        or "TOTAL_PAGES_MATCHING=0" in answer
        or len(set(FY_TOKEN.findall(answer))) >= 3)

    # ---- v2 --------------------------------------------------------------
    verdict_in_answer = any(v in answer for v in SHELF_VERDICTS)
    verdict_in_tool_result = any(v in tool_blob for v in SHELF_VERDICTS)
    declined3 = bool(declined or verdict_in_answer or DECLINE_PLAIN.search(answer))

    # A number the session was SHOWN is a number it copied, not one it invented.
    tool_digits = tool_blob.replace(",", "")
    figs3 = [f for f in answer_figures(answer)
             if f not in tool_blob and f.replace(",", "") not in tool_digits]
    figures_asserted3 = len(figs3)

    return {
        "q_id": q["q_id"], "type": q["type"],
        "declined": declined,
        "figures_asserted": figures_asserted,
        "absence_ok2": bool(declined and figures_asserted == 0),
        "edition_list_quoted": edition_list,
        "declined3": declined3,
        "figures_asserted3": figures_asserted3,
        "absence_ok3": bool(declined3 and figures_asserted3 == 0),
        "shelf_verdict_in_tool_result": verdict_in_tool_result,
        "shelf_verdict_in_answer": verdict_in_answer,
        "timed_out": bool((rec or {}).get("timed_out")),
        "cost_usd": (rec or {}).get("cost_usd"),
        "wall_s": (rec or {}).get("wall_s"),
    }


# --------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------- #
def notes_texts_for(slugless_dir):
    out = []
    d = Path(slugless_dir)
    if not d.exists():
        return out
    for f in d.glob("*_notes.jsonl"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                out.append(json.loads(line).get("text") or "")
            except Exception:
                pass
    return out


def load_rec(phase, qid):
    p = L.RUNS / phase / ("%s__%s__%s.json" % (STACK, CORPUS_LABEL, qid))
    raw = L.RUNS / phase / ("%s__%s__%s.jsonl" % (STACK, CORPUS_LABEL, qid))
    rec = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    return rec, raw


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P5_live")
    ap.add_argument("--abs-phase", dest="abs_phase", default="P5_live_abs")
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

    notes_dir = CSH._notes_dir(str((L.HARNESS / "corpus_15000").resolve()))
    ntexts = notes_texts_for(notes_dir)

    per_q, per_abs = [], []
    for qid in answerable:
        rec, raw = load_rec(a.phase, qid)
        if rec is None:
            per_q.append({"q_id": qid, "type": qs_by_id[qid]["type"], "status": "no_result"})
            continue
        per_q.append(score_answerable(qs_by_id[qid], rec, raw, ntexts))
    for qid, ph in [(i, a.phase) for i in frozen_abs] + [(i, a.abs_phase) for i in extra_abs]:
        rec, raw = load_rec(ph, qid)
        if rec is None:
            per_abs.append({"q_id": qid, "type": "absence", "status": "no_result"})
            continue
        per_abs.append(score_absence(qs_by_id[qid], rec, raw))

    done = [r for r in per_q if "status" not in r]
    absdone = [r for r in per_abs if "status" not in r]
    frozen_abs_done = [r for r in absdone if r["q_id"] in set(frozen_abs)]
    traj = [r for r in done if r["type"] == "trajectory"]
    costs = [r["cost_usd"] for r in per_q + per_abs
             if r.get("cost_usd") is not None]
    walls = [r["wall_s"] for r in per_q + per_abs
             if r.get("wall_s") is not None and not r.get("timed_out")]

    agg = {
        "stack": STACK, "rung": 15000,
        "n_answerable_denominator": 17, "n_answerable_done": len(done),
        "n_absence_frozen_denominator": 3, "n_absence_frozen_done": len(frozen_abs_done),
        "n_absence_all_denominator": 15, "n_absence_all_done": len(absdone),
        "surfaced": sum(1 for r in done if r["surfaced"]),
        "opened_any": sum(1 for r in done if r["opened_any_evidence_file"]),
        "opened_right_page": sum(1 for r in done if r["opened_right_page"]),
        "cited_right_page": sum(1 for r in done if r["cited_right_page"]),
        "noted": sum(1 for r in done if r["noted"]),
        "cited_unopened_total": sum(r["cited_unopened"] for r in done),
        "figures_ungrounded_total": sum(r["figures_ungrounded"] for r in done),
        "series_used": sum(1 for r in traj if r["series_used"]),
        "n_trajectory": len(traj),
        "forbidden_total": sum(r["forbidden"] for r in done),
        "absence_ok2_frozen3": sum(1 for r in frozen_abs_done if r["absence_ok2"]),
        "absence_ok2_all15": sum(1 for r in absdone if r["absence_ok2"]),
        "absence_ok3_frozen3": sum(1 for r in frozen_abs_done if r.get("absence_ok3")),
        "absence_ok3_all15": sum(1 for r in absdone if r.get("absence_ok3")),
        "declined3": sum(1 for r in absdone if r.get("declined3")),
        "shelf_verdict_in_tool_result": sum(1 for r in absdone
                                            if r.get("shelf_verdict_in_tool_result")),
        "shelf_verdict_in_answer": sum(1 for r in absdone
                                       if r.get("shelf_verdict_in_answer")),
        "edition_list_quoted": sum(1 for r in absdone if r["edition_list_quoted"]),
        "total_cost_usd": round(sum(costs), 4) if costs else None,
        "cost_n_of_m": "%d/%d" % (len(costs), len(per_q) + len(per_abs)),
        "mean_wall_s": round(sum(walls) / len(walls), 1) if walls else None,
        "timeouts": sum(1 for r in per_q + per_abs if r.get("timed_out")),
    }
    agg["gate_behaviour"] = (
        "PASS" if (agg["cited_unopened_total"] <= 2 and agg["figures_ungrounded_total"] <= 2
                   and agg["opened_right_page"] >= 6)
        else "WEAK" if (agg["cited_unopened_total"] <= 4 and agg["opened_right_page"] >= 4)
        else "FAIL")
    agg["gate_absence"] = (
        "PASS" if (agg["absence_ok2_all15"] >= 10 and agg["absence_ok2_frozen3"] >= 2)
        else "WEAK" if 8 <= agg["absence_ok2_all15"] <= 9
        else "FAIL")
    agg["gate_absence_v1_label"] = "SUPERSEDED-BY-SCORER-REPAIR (see F53); retained, not deleted"
    agg["gate_absence_v2"] = (
        "PASS" if (agg["absence_ok3_all15"] >= 10 and agg["absence_ok3_frozen3"] >= 2)
        else "WEAK" if 8 <= agg["absence_ok3_all15"] <= 9
        else "FAIL")

    L.SCORES.mkdir(parents=True, exist_ok=True)
    (L.SCORES / "live__s7_shelf__rung15000.json").write_text(
        json.dumps({"aggregate": agg, "answerable": per_q, "absence": per_abs},
                   indent=1), encoding="utf-8")
    (L.STATE / "c_live_battery.json").write_text(
        json.dumps(agg, indent=1), encoding="utf-8")
    print(json.dumps(agg, indent=1))
    return 0


# --------------------------------------------------------------------- #
# self test on two hand-written transcripts
# --------------------------------------------------------------------- #
def _synth(tmp, stem, bash_cmds, results, answer):
    lines = []
    for c in bash_cmds:
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": c}}]}}))
    for r in results:
        lines.append(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "content": r}]}}))
    lines.append(json.dumps({"type": "result", "result": answer,
                             "total_cost_usd": 0.1, "num_turns": 3}))
    raw = tmp / (stem + ".jsonl")
    raw.write_text("\n".join(lines), encoding="utf-8")
    return raw


def selftest():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="c_score_live_"))
    q = {"q_id": "SYN1", "type": "point_lookup",
         "evidence_addresses": [{"path": "some_dir/a_report.pdf", "page_index": 7}],
         "must_not_cite": [{"path": "other_dir/decoy.pdf"}]}

    clean_cmds = [
        'py c_shelf.py find "x" --fusion rrf',
        'py c_shelf.py open "some_dir/a_report.pdf" 7 --slug s1',
        'py c_shelf.py note --slug s1 "the row reads 4321 | some_dir/a_report.pdf | p7"',
    ]
    clean_results = ["#1 family: ... some_dir/a_report.pdf",
                     "OPENED some_dir/a_report.pdf p7\nTotal outlay 4321 million"]
    clean_ans = "The figure is 4321 million, from some_dir/a_report.pdf page 7 (p7)."
    raw1 = _synth(tmp, "clean", clean_cmds, clean_results, clean_ans)
    r1 = score_answerable(q, {"answer_text": clean_ans, "files_opened": []}, raw1, [])

    dirty_cmds = ['py c_shelf.py find "x" --fusion rrf']
    dirty_results = ["#1 family: ... some_dir/a_report.pdf"]
    dirty_ans = ("The figure is 9999 million, from some_dir/a_report.pdf page 7, "
                 "see also other_dir/decoy.pdf.")
    raw2 = _synth(tmp, "dirty", dirty_cmds, dirty_results, dirty_ans)
    r2 = score_answerable(q, {"answer_text": dirty_ans, "files_opened": []}, raw2, [])

    checks = [
        ("clean.surfaced", r1["surfaced"] is True),
        ("clean.opened_right_page", r1["opened_right_page"] is True),
        ("clean.cited_right_page", r1["cited_right_page"] is True),
        ("clean.noted", r1["noted"] is True),
        ("clean.cited_unopened_is_0", r1["cited_unopened"] == 0),
        ("clean.figures_grounded", r1["figures_ungrounded"] == 0),
        ("clean.no_forbidden", r1["forbidden"] == 0),
        ("dirty.surfaced", r2["surfaced"] is True),
        ("dirty.opened_right_page_false", r2["opened_right_page"] is False),
        ("dirty.cited_right_page_false", r2["cited_right_page"] is False),
        ("dirty.cited_unopened_ge_1", r2["cited_unopened"] >= 1),
        ("dirty.figure_ungrounded_ge_1", r2["figures_ungrounded"] >= 1),
        ("dirty.forbidden_counted", r2["forbidden"] == 1),
    ]
    ok = all(c for _, c in checks)
    rec = {"n_checks": len(checks), "n_passed": sum(1 for _, c in checks if c),
           "all_pass": ok,
           "checks": [{"check": n, "pass": bool(c)} for n, c in checks],
           "clean": r1, "dirty": r2}
    (L.STATE / "c_score_live_selftest.json").write_text(
        json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items()
                      if k not in ("checks", "clean", "dirty")}, indent=1))
    for n, c in checks:
        if not c:
            print("FAILED: %s" % n)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
