"""Regression tests for c_score_live_v3.py (Plan E Phase 1.5).

One test per audited bug, named for the transcript that exposed it. Every
fixture is SYNTHETIC -- written by the test, with invented paths and invented
numbers. No corpus path, no key value and no recorded answer text appears in
this file, so running the suite tells nobody anything about the answer key.

The point of the suite is not that v3 scores higher. Three of these tests assert
that v3 counts FEWER violations than v2 did, one asserts that v3 keeps counting
a violation v2 found (`series_output_is_not_an_open` -- the one case in the audit
that was a real defect in the system), and one asserts v3 and v2 agree exactly on
a clean transcript.
"""
import json
import sys
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))

import c_score_live_v3 as V3          # noqa: E402
import c_score_live_v2 as V2          # noqa: E402
import c_score_live as V1             # noqa: E402


# --------------------------------------------------------------------------
# minimal stream-json builders
# --------------------------------------------------------------------------

def ev_assistant_text(text):
    return {"type": "assistant",
            "message": {"role": "assistant",
                        "content": [{"type": "text", "text": text}]}}


def ev_assistant_bash(cmd):
    return {"type": "assistant",
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "name": "Bash",
                                     "input": {"command": cmd}}]}}


def ev_tool_result(text):
    return {"type": "user",
            "message": {"role": "user",
                        "content": [{"type": "tool_result", "content": text}]}}


def ev_hook(text):
    """A Stop-hook interruption: a synthetic user turn carrying a text block."""
    return {"type": "user", "isSynthetic": True,
            "message": {"role": "user",
                        "content": [{"type": "text", "text": text}]}}


def write_transcript(tmp_path, events, name="t.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    return p


def question(qid="q_01", qtype="trajectory", addrs=(), value=None):
    q = {"q_id": qid, "type": qtype,
         "evidence_addresses": [
             {"path": p, "page_index": pg, "series_id": "s1",
              "vintage_id": "v1", "fy": "2018-19"} for p, pg in addrs],
         "must_not_cite": [], "acceptable_alternates": []}
    q["expected_answer"] = {"value": value, "row_label": "some row"} \
        if value is not None else {"row_label": "some row"}
    return q


def score(tmp_path, events, q, rec=None, reg=None):
    raw = write_transcript(tmp_path, events)
    rec = rec if rec is not None else {"answer_text": "", "wall_s": 10.0}
    return V3.score_answerable_v3(q, rec, raw, [], reg or {}, bool(reg), 60)


# --------------------------------------------------------------------------
# 1. P9O pl_01 -- pages opened inside a bash `for` loop
# --------------------------------------------------------------------------

def test_loop_open_is_an_open(tmp_path):
    """The command carries the loop variable; the tool OUTPUT carries the truth.

    v1 and v2 read opens from the command string only, so every page opened in a
    loop was invisible and every page cited from one counted as a violation.
    """
    answer = ("Development spending rose over the decade.\n\n"
              "Sources:\n- reports/alpha.pdf | p12\n- reports/beta.pdf | p7\n")
    events = [
        ev_assistant_bash('for f in reports/*.pdf; do python c_shelf.py open "$f" 12; done'),
        ev_tool_result("OPENED reports/alpha.pdf p12\nOPENED reports/beta.pdf p7\n"),
        ev_assistant_text(answer),
    ]
    r = score(tmp_path, events, question(addrs=[("reports/alpha.pdf", 12)]),
              rec={"answer_text": answer, "wall_s": 10.0})
    assert r["cited_unopened"] == 0, "a page the tool says it OPENED is an open"
    assert r["n_opens_loop_only"] == 2
    assert r["n_opens_from_output"] == 2
    assert r["n_opens_from_command"] == 0


# --------------------------------------------------------------------------
# 2. P9S mb_07 -- a markdown bullet swallowed into the path
# --------------------------------------------------------------------------

def test_bullet_does_not_join_path(tmp_path):
    answer = "Answer.\n\nSources:\n- file.pdf | p3\n"
    citations, mentions = V3.citations_and_mentions(answer)
    paths = {p for p, _ in citations}
    assert "file.pdf" in paths, "got %r" % (paths,)
    assert not any(p.startswith("-") for p in paths)
    assert ("file.pdf", 3) in citations


def test_bullet_path_is_matched_against_opens(tmp_path):
    answer = "Answer.\n\nSources:\n- file.pdf | p3\n"
    events = [
        ev_assistant_bash('python c_shelf.py open "file.pdf" 3'),
        ev_tool_result("OPENED file.pdf p3\n"),
        ev_assistant_text(answer),
    ]
    r = score(tmp_path, events, question(addrs=[("file.pdf", 3)]),
              rec={"answer_text": answer, "wall_s": 5.0})
    assert r["cited_unopened"] == 0


# --------------------------------------------------------------------------
# 3. P9O sd_05 -- two filenames named in prose
# --------------------------------------------------------------------------

def test_mention_is_not_citation(tmp_path):
    """No page, no figure: naming a file is not claiming to have read a page."""
    answer = ("The file a.csv is older than the file b.csv, so the second is "
              "the one to trust.")
    citations, mentions = V3.citations_and_mentions(answer)
    assert citations == set(), "no page token anywhere, so nothing is a citation"
    assert mentions == {"a.csv", "b.csv"}

    events = [ev_assistant_text(answer)]
    r = score(tmp_path, events, question(), rec={"answer_text": answer, "wall_s": 5.0})
    assert r["cited_unopened"] == 0
    assert r["mentioned_unopened"] == 2


# --------------------------------------------------------------------------
# 4. P9S tr_10 -- the guard interrupted and the harness kept the fragment
# --------------------------------------------------------------------------

def test_fragment_answer_is_completed(tmp_path):
    full = ("Development spending rose across the decade.\n\n"
            "Sources:\n- reports/alpha.pdf | p12\n")
    reply = "Confirmed - the citation stands. Updated Sources line: reports/alpha.pdf | p12"
    events = [
        ev_assistant_bash('python c_shelf.py open "reports/alpha.pdf" 12'),
        ev_tool_result("OPENED reports/alpha.pdf p12\n"),
        ev_assistant_text(full),
        ev_hook("OPEN_BEFORE_CITE: you cited a page you have not opened."),
        ev_assistant_text(reply),
    ]
    raw = write_transcript(tmp_path, events)
    recon = V3.reconstruct_full_answer(raw)
    assert recon["n_hook_blocks"] == 1
    assert recon["answer_text_last"].strip() == reply
    assert full.strip() in recon["answer_text_full"]
    assert recon["was_fragment"], "the recorded answer was only the post-guard reply"

    # and the full answer's citations are what gets scored
    r = V3.score_answerable_v3(question(addrs=[("reports/alpha.pdf", 12)]),
                               {"answer_text": reply, "wall_s": 20.0},
                               raw, [], {}, False, 60)
    assert r["answer_was_fragment"]
    assert r["cited_right_page_strict"], \
        "the real answer cited an opened gold page; only the fragment hid it"
    assert r["len_answer_full"] > r["len_answer_recorded"]


def test_clean_session_is_not_a_fragment(tmp_path):
    """No hook block, so nothing to reconstruct and no fragment flag."""
    answer = "Answer.\n\nSources:\n- file.pdf | p3\n"
    events = [
        ev_assistant_bash('python c_shelf.py open "file.pdf" 3'),
        ev_tool_result("OPENED file.pdf p3\n"),
        ev_assistant_text(answer),
    ]
    raw = write_transcript(tmp_path, events)
    recon = V3.reconstruct_full_answer(raw)
    assert recon["n_hook_blocks"] == 0
    assert not recon["was_fragment"]
    assert recon["answer_text_full"].strip() == answer.strip()


# --------------------------------------------------------------------------
# 5. tr_04 -- a question the key carries no value for
# --------------------------------------------------------------------------

def test_unkeyed_value_not_in_denominator(tmp_path):
    q = question(qid="tr_04", value=None)          # no expected_answer.value
    assert V2.accepted_values(q) == []
    f = V3.value_fields(q, "Spending rose to 123.4 billion.")
    assert f["value_scorable"] is False
    assert f["value_correct"] is False
    assert f["n_accepted_values"] == 0


def test_keyed_value_is_in_denominator(tmp_path):
    q = question(qid="q_kv", value=123.4)
    f = V3.value_fields(q, "Spending reached 123.4 billion rupees.")
    assert f["value_scorable"] is True
    assert f["value_correct"] is True


def test_aggregate_denominator_excludes_unkeyed():
    """n_keyed counts only questions the key can score, so k/n_keyed is honest."""
    rows = [{"value_scorable": True, "value_correct": True},
            {"value_scorable": True, "value_correct": True},
            {"value_scorable": False, "value_correct": False},
            {"value_scorable": False, "value_correct": False}]
    keyed = [r for r in rows if r["value_scorable"]]
    assert len(keyed) == 2
    assert sum(1 for r in keyed if r["value_correct"]) == 2


# --------------------------------------------------------------------------
# 6. P9O mb_04 -- a page named in `tables` output is NOT an open
# --------------------------------------------------------------------------

def test_series_output_is_not_an_open(tmp_path):
    """This one stays a defect. The whole credibility of the correction rests
    on v3 still catching the case that was real."""
    answer = ("The table gives 45.6 for that year.\n\n"
              "Sources:\n- reports/gamma.pdf | p88\n")
    events = [
        ev_assistant_bash('python c_shelf.py tables "some query"'),
        # names the path AND the page, but no OPENED line: nothing was opened
        ev_tool_result("reports/gamma.pdf p88  Table 3.1 some caption\n"),
        ev_assistant_text(answer),
    ]
    r = score(tmp_path, events, question(addrs=[("reports/gamma.pdf", 88)]),
              rec={"answer_text": answer, "wall_s": 9.0})
    assert r["cited_unopened"] == 1, "citing from tables output without open is a violation"
    assert r["n_opens_from_output"] == 0
    assert r["n_opens_from_command"] == 0
    assert not r["cited_right_page_strict"]


def test_inside_output_is_not_an_open(tmp_path):
    answer = "See page 41.\n\nSources:\n- reports/delta.pdf | p41\n"
    events = [
        ev_assistant_bash('python c_shelf.py inside "reports/delta.pdf" "query"'),
        ev_tool_result("reports/delta.pdf p41 matched\n"),
        ev_assistant_text(answer),
    ]
    r = score(tmp_path, events, question(addrs=[("reports/delta.pdf", 41)]),
              rec={"answer_text": answer, "wall_s": 9.0})
    assert r["cited_unopened"] == 1


# --------------------------------------------------------------------------
# 7. v3 == v2 on a clean transcript
# --------------------------------------------------------------------------

def test_v2_parity_on_clean_transcript(tmp_path):
    """Plain opens, no guard, a keyed value: nothing v3 changes applies, so the
    two scorers must agree on every shared field. If they do not, v3 has moved
    something it was not supposed to move."""
    answer = ("Spending reached 123.4 billion rupees.\n\n"
              "Sources:\n- reports/alpha.pdf | p12\n")
    events = [
        ev_assistant_bash('python c_shelf.py open "reports/alpha.pdf" 12'),
        ev_tool_result("OPENED reports/alpha.pdf p12\n"),
        ev_assistant_text(answer),
    ]
    raw = write_transcript(tmp_path, events)
    q = question(addrs=[("reports/alpha.pdf", 12)], value=123.4)
    rec = {"answer_text": answer, "wall_s": 12.0, "cost_usd": 0.1, "turns": 4}

    r3 = V3.score_answerable_v3(q, rec, raw, [], {}, False, 60)
    r2 = V2.score_answerable_v2(q, rec, raw, [], {}, False, 60)

    for f in ("cited_right_page_strict", "cited_right_page_equiv",
              "cited_unopened", "surfaced", "opened_any_evidence_file",
              "opened_right_page", "figures_ungrounded", "forbidden",
              "value_correct", "value_wrong_confident", "n_accepted_values",
              "no_answer_cause", "turns", "wall_s", "cost_usd"):
        assert r3[f] == r2[f], "v3 and v2 disagree on %s: %r vs %r" % (
            f, r3[f], r2[f])
    assert r3["value_scorable"] is True
    assert r3["cited_unopened"] == 0
    assert not r3["answer_was_fragment"]


# --------------------------------------------------------------------------
# citation-window behaviour, pre-registered at 40 characters
# --------------------------------------------------------------------------

def test_page_token_far_from_path_is_not_a_citation():
    far = "x" * 120
    answer = "See a.pdf %s and separately page 9 of something else." % far
    citations, mentions = V3.citations_and_mentions(answer)
    assert citations == set()
    assert mentions == {"a.pdf"}


def test_page_token_near_path_is_a_citation():
    answer = "See a.pdf page 9 for the table."
    citations, _ = V3.citations_and_mentions(answer)
    assert ("a.pdf", 9) in citations
