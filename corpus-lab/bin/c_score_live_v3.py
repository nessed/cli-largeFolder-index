#!/usr/bin/env python
"""c_score_live_v3.py -- the scorer corrected against its own transcripts.

v1 is the frozen strict reference. v2 added equivalence, value and no-answer
columns. Both stay untouched, and every verdict they produced stands: Plan E
decision 1 says v3 changes no recorded verdict, it re-scores the same recordings
into new files and reports the two side by side with a reason for each
difference.

WHY (Plan E section 1, recomputed from the recordings 2026-09-15): an independent
audit of the 2026-09-15 night found that three of the four headline defects in
the Phase 9 report were defects in the SCORER, not in the system it measured.

  1. Opens were read from the COMMAND STRING only. A session that opened pages
     inside a bash `for spec in ...` loop had every one of those opens missed,
     because the command carries the loop variable `$f` where a path should be.
     The pages were opened; the tool output says so. 28 opens across 7 Opus
     sessions and 6 in 1 Sonnet session were invisible to v1 and v2, and every
     page cited from them was counted as "cited without opening".
  2. Any path-shaped string in an answer counted as a CITATION. Two CSV
     filenames named in prose -- "this file is older than that one", no page,
     no figure -- scored as two open-before-cite violations. A mention is not a
     citation.
  3. The harness keeps the LAST assistant message. In 5 Sonnet sessions the
     guard challenged a citation, the model answered "Confirmed -- the citation
     stands", and THAT four-line reply is what got scored. The real answer was
     the 2,344-character block immediately before the guard's interruption.
  4. `value_correct` read 5/17 for both models. 12 of the 17 dev answerable
     questions carry no numeric value in the key at all, so `value_correct`
     could never be true for them. The split is a property of the key, not of
     the models. On the 5 keyed questions both models were 5/5.

v3 overrides exactly those four things and nothing else. It is deliberately NOT
a better scorer in any other respect: everything else is inherited from v2 so
the two numbers are comparable.

  cited_unopened          citations only (a path WITH a page), against opens
                          read from tool OUTPUT as well as from commands
  mentioned_unopened      separately reported; not a violation
  answer_was_fragment     the recorded answer_text was a post-guard reply
  value_correct           reported as k / n_keyed, never k / 17

**A page named in `series`/`tables`/`inside` output is still not an open.** That
is the one case in the audit that was a real defect in the system, and v3 keeps
counting it -- see the `series_output_is_not_an_open` regression test.

This is a scoring script (rule 4), so it may open the answer key and the
generator's placement records. It writes COUNTS ONLY to the public copy.

  python c_score_live_v3.py --phase P9S_live --abs-phase P5_live_abs
  python c_score_live_v3.py --phase P9S_live --key <key_v2.json> --tag keyv2

Writes:
  corpus-lab/state/c_live_battery_v3__<phase>[__<tag>].json   aggregate, public
  _private/results/04_scores/live_v3__<phase>[__<tag>].json   per question
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import scoring as SC  # noqa: E402
import c_score_live as V1  # noqa: E402
import c_score_live_v2 as V2  # noqa: E402

SCORER_VERSION = "v3"

# --- 1.1 opens from ground truth ---------------------------------------------
# What `c_shelf.py open` prints on success (c_shelf.py:1262). This is the
# system's own record that a page was opened, and it is true whether the command
# that produced it named the path literally or through a shell variable.
OPENED_LINE = re.compile(r"^OPENED\s+(?P<rel>.+?)\s+p(?P<page>\d+)\s*$", re.M)

# --- 1.2 a citation is a path with a page ------------------------------------
# Same file-extension anchor v1 uses, so the two scorers see the same universe
# of path-shaped strings and only the CLASSIFICATION differs.
PATH_TOKEN = re.compile(
    r"[A-Za-z0-9_\-./\\()\[\] ]{0,180}?\.(?:pdf|xlsx|xls|docx|doc|csv|txt|md)\b",
    re.I)
PAGE_TOKEN = re.compile(r"(?<![A-Za-z0-9])(?:p\.?\s?|page\s+)(\d{1,4})(?![0-9-])", re.I)
# `<path> | p12` -- the Sources-line form CLAUDE.md asks for.
SOURCES_PAIR = re.compile(
    r"(?P<path>[^\s|][^|\n]*?\.(?:pdf|xlsx|xls|docx|doc|csv|txt|md))"
    r"\s*\|\s*p\.?\s?(?P<page>\d{1,4})\b", re.I)

CITATION_WINDOW = 40          # characters, pre-registered in the Gate T spec

# Leading noise a path picks up from markdown: bullets, quotes, emphasis.
LEADING_JUNK = " \t`'\"*_>-[(••"


def _clean_path_token(tok):
    """Strip the markdown a path collects on a Sources line.

    v1 let a leading `- ` join the path, so `- file.pdf` normalised to a path
    whose first segment was the bullet. That is the `bullet_does_not_join_path`
    regression.
    """
    tok = (tok or "").strip()
    while tok and tok[0] in LEADING_JUNK:
        tok = tok[1:]
    tok = tok.strip().strip("`'\"()[],*")
    # A path lifted from prose keeps the word before it ("from some/file.pdf").
    # Drop leading whitespace-separated words that carry no path separator and
    # no extension -- the filename and its parent survive, which is all
    # _same_path's tail-2 rule needs.
    while " " in tok:
        head, rest = tok.split(" ", 1)
        if "/" in head or "\\" in head or "." in head:
            break
        tok = rest
    return tok.strip()


def _iter_path_spans(answer):
    """[(normalised_path, start, end)] for every path-shaped string."""
    out = []
    for m in PATH_TOKEN.finditer(answer or ""):
        raw = m.group(0)
        cleaned = _clean_path_token(raw)
        if len(cleaned) <= 4:
            continue
        # the cleaned token starts later in the string than the raw match did
        start = m.start() + raw.find(cleaned) if cleaned in raw else m.start()
        out.append((SC.norm_path(cleaned), start, m.end()))
    return out


SHELL_META = re.compile(r"[$*?{}`]|\$\{|%\w+%")


def _is_shell_placeholder(rel):
    """True for a `path` that is really a shell variable or a glob."""
    return bool(SHELL_META.search(rel or ""))


def opened_pairs_v3(raw_path, rec):
    """Every page this session actually opened, and where we learned it.

    Union of three sources:
      * `OPENED <rel> p<N>` in any tool result -- the system's own confirmation;
      * `open "<rel>" <N>` in a command string -- v1's rule, kept so that older
        transcripts still score identically;
      * `files_opened` from the hook record (no page).
    """
    results, bash_cmds, _texts = V1.read_transcript(raw_path)
    blob = "\n".join(results)

    from_output = set()
    for m in OPENED_LINE.finditer(blob):
        try:
            from_output.add((SC.norm_path(m.group("rel").strip()),
                             int(m.group("page"))))
        except ValueError:
            pass

    # v1's regex happily matches `open "$f" 12` and records a path literally
    # named `$f`. That is the loop-blindness bug wearing a disguise: it is not a
    # path, it never matches a real one, and counting it would overstate how
    # many opens the command strings actually named.
    from_command = {(rel, pg) for rel, pg in V1.opens_from_bash(bash_cmds)
                    if pg is not None and not _is_shell_placeholder(rel)}

    hook_paths = set()
    for f in (rec or {}).get("files_opened", []) or []:
        if f.get("path"):
            hook_paths.add(SC.norm_path(f["path"]))

    pairs = from_output | from_command
    return {
        "pairs": pairs,
        "paths": {rel for rel, _ in pairs} | hook_paths,
        "n_opens_from_output": len(from_output),
        "n_opens_from_command": len(from_command),
        "n_opens_loop_only": len(from_output - from_command),
        "bash_cmds": bash_cmds,
        "results": results,
    }


def citations_and_mentions(answer):
    """Split the answer's path-shaped strings into citations and mentions.

    A CITATION is a path with a page: either the `<path> | p<N>` Sources form,
    or a path within CITATION_WINDOW characters of a `p<N>` / `page N` token.
    A MENTION is a path-shaped string with no page anywhere near it -- naming a
    file in prose is not claiming to have read a page of it.
    """
    answer = answer or ""
    citations = set()          # (path, page)
    cited_paths = set()

    for m in SOURCES_PAIR.finditer(answer):
        p = SC.norm_path(_clean_path_token(m.group("path")))
        if len(p) > 4:
            try:
                citations.add((p, int(m.group("page"))))
                cited_paths.add(p)
            except ValueError:
                pass

    pages = [(int(m.group(1)), m.start(), m.end())
             for m in PAGE_TOKEN.finditer(answer)]
    spans = _iter_path_spans(answer)
    for path, s, e in spans:
        for pg, ps, pe in pages:
            near = (ps - e <= CITATION_WINDOW) and (s - pe <= CITATION_WINDOW)
            if near:
                citations.add((path, pg))
                cited_paths.add(path)

    mentions = {p for p, _s, _e in spans if p not in cited_paths}
    return citations, mentions


# --- 1.3 the complete answer across a guard interruption ----------------------

def reconstruct_full_answer(raw_path):
    """The answer the model actually gave, not the fragment the harness kept.

    The harness records the LAST assistant message. When the Stop hook fires,
    the model's real answer is followed by a synthetic `user` turn carrying the
    guard's challenge and then a short confirmation -- so `answer_text` becomes
    "Confirmed -- the citation stands." and the answer itself is lost.

    This returns the trailing assistant text PLUS, when a Stop-hook block
    occurred, the assistant text immediately preceding that block, in order.
    Both the live battery (`--capture full`) and this scorer call this one
    function, so the two paths cannot diverge.
    """
    p = Path(raw_path)
    if not p.exists():
        return {"answer_text_last": "", "answer_text_full": "",
                "n_hook_blocks": 0, "was_fragment": False}

    events = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            continue

    def assistant_texts(d):
        if d.get("type") != "assistant":
            return []
        out = []
        for c in (d.get("message", {}) or {}).get("content", []) or []:
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text"):
                out.append(c["text"])
        return out

    def is_hook_block(d):
        """A synthetic user turn injected by a hook -- not a tool result and not
        anything the model or the harness's own prompt produced."""
        if d.get("type") != "user" or not d.get("isSynthetic"):
            return False
        content = (d.get("message", {}) or {}).get("content")
        if not isinstance(content, list):
            return False
        return any(isinstance(c, dict) and c.get("type") == "text"
                   for c in content)

    def is_tool_result(d):
        if d.get("type") != "user":
            return False
        content = (d.get("message", {}) or {}).get("content")
        return isinstance(content, list) and any(
            isinstance(c, dict) and c.get("type") == "tool_result"
            for c in content)

    hook_idx = [i for i, d in enumerate(events) if is_hook_block(d)]

    # the trailing answer: assistant text after the last tool result / hook
    last_break = -1
    for i, d in enumerate(events):
        if is_tool_result(d) or is_hook_block(d):
            last_break = i
    tail = []
    for d in events[last_break + 1:]:
        tail.extend(assistant_texts(d))

    # the pre-hook answer: assistant text immediately before each hook block
    pre = []
    for i in hook_idx:
        j = i - 1
        block = []
        while j >= 0 and events[j].get("type") == "assistant":
            block = assistant_texts(events[j]) + block
            j -= 1
        pre.extend(block)

    last = "\n\n".join(tail).strip()
    full_parts = [x for x in (pre + tail) if x and x.strip()]
    # de-duplicate while preserving order: the tail can repeat a pre-hook block
    seen, ordered = set(), []
    for x in full_parts:
        if x not in seen:
            seen.add(x)
            ordered.append(x)
    full = "\n\n".join(ordered).strip()

    return {
        "answer_text_last": last,
        "answer_text_full": full or last,
        "n_hook_blocks": len(hook_idx),
        # a fragment is a recorded answer that the full reconstruction grows
        "was_fragment": bool(hook_idx) and len(full) > len(last) * 1.25,
    }


# --- 1.4 denominators ---------------------------------------------------------

def value_fields(q, answer):
    """v2's value logic, with the denominator made explicit.

    A question with no numeric value in the key is not a question the model got
    wrong; it is a question the key cannot score. It gets value_scorable=False
    and is in NO value denominator.
    """
    out = V2.score_value(q, answer)
    scorable = out["n_accepted_values"] > 0
    out["value_scorable"] = scorable
    if not scorable:
        out["value_correct"] = False
        out["value_wrong_confident"] = False
    return out


def vector_fields(q, answer):
    """Key-v2 vector coverage (Plan E Phase 2.2).

    Only meaningful with a key that carries `expected_vector`; with key v1 every
    question reports vector_scorable=False and nothing enters a denominator.
    """
    vec = q.get("expected_vector")
    if not vec or not isinstance(vec, dict):
        return {"vector_scorable": False, "vector_coverage": None,
                "vector_full": False, "n_vector_years": 0}
    nums = V2.answer_numbers(answer)
    hit = 0
    total = 0
    for _fy, vals in sorted(vec.items()):
        cands = [v for v in (vals if isinstance(vals, list) else [vals])
                 if V2._as_float(v) is not None]
        if not cands:
            continue
        total += 1
        for c in cands:
            want = V2._as_float(c)
            tol = max(abs(want) * V2.VALUE_TOLERANCE, 1e-9)
            if any(abs(n - want) <= tol for n in nums):
                hit += 1
                break
    if not total:
        return {"vector_scorable": False, "vector_coverage": None,
                "vector_full": False, "n_vector_years": 0}
    cov = hit / total
    return {"vector_scorable": True, "vector_coverage": round(cov, 4),
            "vector_full": cov >= 1.0, "n_vector_years": total}


# --- per question -------------------------------------------------------------

def score_answerable_v3(q, rec, raw_path, notes_texts, reg, reg_usable, max_turns):
    opens = opened_pairs_v3(raw_path, rec)
    recon = reconstruct_full_answer(raw_path)
    recorded = (rec or {}).get("answer_text") or ""
    # score the fullest text available: the reconstruction, or the recorded
    # answer when there is no transcript to reconstruct from
    answer = recon["answer_text_full"] or recorded

    citations, mentions = citations_and_mentions(answer)
    opened_paths = opens["paths"]
    opened_pairs = opens["pairs"]

    cited_unopened = sum(
        1 for p in {c[0] for c in citations}
        if not any(V1._same_path(p, op) for op in opened_paths))
    mentioned_unopened = sum(
        1 for p in mentions
        if not any(V1._same_path(p, op) for op in opened_paths))

    # --- strict: a gold address, cited with its page, and actually opened -----
    ev_addrs = [(SC.norm_path(a["path"]), a.get("page_index"))
                for a in q.get("evidence_addresses", [])]
    strict = False
    for p, page in ev_addrs:
        if page is None:
            continue
        if not any(V1._same_path(cp, p) and cpg == page for cp, cpg in citations):
            continue
        if any(pg == page and V1._same_path(rel, p) for rel, pg in opened_pairs):
            strict = True
            break

    # --- equivalence: a page that prints the same cell ------------------------
    want_cells = V2.gold_cells(q)
    equiv = strict
    equiv_via_other = False
    if reg_usable and not equiv:
        for cp, cpg in citations:
            if not any(pg == cpg and V1._same_path(rel, cp)
                       for rel, pg in opened_pairs):
                continue        # still must have opened what it cites
            cells = reg.get((SC.norm_path(cp), int(cpg)))
            if not cells:
                continue
            for c in cells:
                if c in want_cells or any(
                        c[0] == w[0] and c[0] is not None and c[2] == w[2]
                        for w in want_cells):
                    equiv = True
                    equiv_via_other = True
                    break
            if equiv:
                break

    # --- inherited, unchanged -------------------------------------------------
    blob_n = SC.norm_text("\n".join(opens["results"]))
    ev_paths = {p for p, _ in ev_addrs}
    surfaced = any(SC.norm_path(p) in blob_n or SC.path_tail(p, 2) in blob_n
                   for p in ev_paths)
    opened_any = any(V1._same_path(rel, p) for rel in opened_paths for p in ev_paths)
    opened_right_page = any(
        pg == page and V1._same_path(rel, p)
        for rel, pg in opened_pairs for p, page in ev_addrs if page is not None)

    grounding = "\n".join(opens["results"]) + "\n" + "\n".join(notes_texts)
    grounding_n = grounding.replace(",", "")
    figures_ungrounded = sum(
        1 for fig in set(V1.answer_figures(answer))
        if fig not in grounding and fig.replace(",", "") not in grounding_n)

    bad_paths = {SC.norm_path(m["path"]) for m in q.get("must_not_cite", [])}
    forbidden = sorted(p for p in bad_paths if SC.answer_names_path(answer, p)[0])

    out = {
        "q_id": q["q_id"], "type": q["type"],
        "surfaced": bool(surfaced),
        "opened_any_evidence_file": bool(opened_any),
        "opened_right_page": bool(opened_right_page),
        "cited_right_page_strict": bool(strict),
        "cited_right_page_equiv": bool(equiv),
        "equiv_via_other_publication": bool(equiv_via_other),
        "cited_unopened": cited_unopened,
        "mentioned_unopened": mentioned_unopened,
        "n_citations": len(citations),
        "n_mentions": len(mentions),
        "n_opens": len(opened_pairs),
        "n_opens_from_output": opens["n_opens_from_output"],
        "n_opens_from_command": opens["n_opens_from_command"],
        "n_opens_loop_only": opens["n_opens_loop_only"],
        "answer_was_fragment": bool(recon["was_fragment"]),
        "n_hook_blocks": recon["n_hook_blocks"],
        "len_answer_recorded": len(recorded),
        "len_answer_full": len(answer),
        "figures_ungrounded": figures_ungrounded,
        "forbidden": len(forbidden),
        "noted": any(V1.NOTE_CMD.search(c) for c in opens["bash_cmds"]),
        "series_used": any(V1.SERIES_CMD.search(c) for c in opens["bash_cmds"]),
        "cited_no_path": bool(V1.answer_figures(answer)) and not citations,
        "no_answer_cause": V2.no_answer_cause(rec, max_turns),
        "answered_within_300s": ((rec or {}).get("wall_s") is not None
                                 and (rec or {}).get("wall_s") <= 300
                                 and bool(answer.strip())),
        "turns": (rec or {}).get("turns"),
        "suspended": bool((rec or {}).get("suspended")),
        "timed_out": bool((rec or {}).get("timed_out")),
        "cost_usd": (rec or {}).get("cost_usd"),
        "wall_s": (rec or {}).get("wall_s"),
    }
    out.update(value_fields(q, answer))
    out.update(vector_fields(q, answer))
    return out


def score_absence_v3(q, rec, raw_path, max_turns):
    """Absence is scored by the frozen v2 rule, on the reconstructed answer.

    The absence rule itself is NOT changed -- only which text it reads, and for
    the same reason: a guard interruption must not turn a correct decline into
    an empty string.
    """
    recon = reconstruct_full_answer(raw_path)
    recorded = (rec or {}).get("answer_text") or ""
    answer = recon["answer_text_full"] or recorded

    shim = dict(rec or {})
    shim["answer_text"] = answer
    out = dict(V2.score_absence_v2(q, shim, raw_path, max_turns))
    out["answer_was_fragment"] = bool(recon["was_fragment"])
    out["len_answer_recorded"] = len(recorded)
    out["len_answer_full"] = len(answer)
    return out


# --- driver -------------------------------------------------------------------

def _sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P5_live")
    ap.add_argument("--abs-phase", dest="abs_phase", default="P5_live_abs")
    ap.add_argument("--max-turns", dest="max_turns", type=int, default=25)
    ap.add_argument("--key", default=None,
                    help="answer key file (default: the frozen answer_key.json)")
    ap.add_argument("--tag", default=None,
                    help="output filename suffix, e.g. keyv2")
    a = ap.parse_args(argv)

    import c_shelf as CSH
    key_file = Path(a.key) if a.key else L.ANSWER_KEY
    key = json.loads(key_file.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen_ids = sorted(sample["q_ids"])
    answerable = [i for i in frozen_ids if qs_by_id[i]["type"] != "absence"]
    frozen_abs = [i for i in frozen_ids if qs_by_id[i]["type"] == "absence"]
    extra_abs = sorted(q["q_id"] for q in key["questions"]
                       if q["type"] == "absence" and q["q_id"] not in set(frozen_ids))[:12]

    reg, reg_meta = V2.build_placement_registry()
    reg_val = V2.validate_registry(reg, qs_by_id)
    reg_usable = bool(reg_val["usable"])

    notes_dir = CSH._notes_dir(str((L.HARNESS / "corpus_15000").resolve()))
    ntexts = V1.notes_texts_for(notes_dir)

    per_q, per_abs, sources = [], [], []
    for qid in answerable:
        rec, raw = V1.load_rec(a.phase, qid)
        if rec is None:
            per_q.append({"q_id": qid, "type": qs_by_id[qid]["type"],
                          "status": "no_result"})
            continue
        sources.append(str(raw))
        per_q.append(score_answerable_v3(qs_by_id[qid], rec, raw, ntexts,
                                         reg, reg_usable, a.max_turns))
    for qid, ph in [(i, a.phase) for i in frozen_abs] + \
                   [(i, a.abs_phase) for i in extra_abs]:
        rec, raw = V1.load_rec(ph, qid)
        if rec is None:
            per_abs.append({"q_id": qid, "type": "absence", "status": "no_result"})
            continue
        sources.append(str(raw))
        per_abs.append(score_absence_v3(qs_by_id[qid], rec, raw, a.max_turns))

    done = [r for r in per_q if "status" not in r]
    absdone = [r for r in per_abs if "status" not in r]
    frozen_abs_done = [r for r in absdone if r["q_id"] in set(frozen_abs)]
    walls = sorted(r["wall_s"] for r in per_q + per_abs
                   if r.get("wall_s") is not None and not r.get("timed_out"))
    costs = [r["cost_usd"] for r in per_q + per_abs if r.get("cost_usd") is not None]
    keyed = [r for r in done if r.get("value_scorable")]
    vecd = [r for r in done if r.get("vector_scorable")]

    def cause(rows, name):
        return sum(1 for r in rows if r.get("no_answer_cause") == name)

    agg = {
        "scorer_version": SCORER_VERSION,
        "scorer_sha256": _sha256(__file__),
        "key_file": str(key_file),
        "key_sha256": _sha256(key_file),
        "group_definition": str(L.QUESTION_SAMPLE),
        "group_definition_sha256": _sha256(L.QUESTION_SAMPLE),
        "phase": a.phase, "abs_phase": a.abs_phase,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "max_turns_assumed": a.max_turns,
        "n_source_recordings": len(sources),

        "n_answerable_denominator": 17, "n_answerable_done": len(done),
        "n_absence_frozen_denominator": 3,
        "n_absence_frozen_done": len(frozen_abs_done),
        "n_absence_all_denominator": 15, "n_absence_all_done": len(absdone),

        "cited_right_page_strict": sum(1 for r in done if r["cited_right_page_strict"]),
        "cited_right_page_equiv": sum(1 for r in done if r["cited_right_page_equiv"]),
        "equiv_via_other_publication": sum(1 for r in done
                                           if r["equiv_via_other_publication"]),
        "cited_unopened_total": sum(r["cited_unopened"] for r in done),
        "mentioned_unopened_total": sum(r["mentioned_unopened"] for r in done),
        "surfaced": sum(1 for r in done if r["surfaced"]),
        "opened_any": sum(1 for r in done if r["opened_any_evidence_file"]),
        "opened_right_page": sum(1 for r in done if r["opened_right_page"]),
        "figures_ungrounded_total": sum(r["figures_ungrounded"] for r in done),
        "forbidden_total": sum(r["forbidden"] for r in done),
        "cited_no_path": sum(1 for r in done if r["cited_no_path"]),

        "n_opens_from_output_total": sum(r["n_opens_from_output"] for r in done),
        "n_opens_from_command_total": sum(r["n_opens_from_command"] for r in done),
        "n_opens_loop_only_total": sum(r["n_opens_loop_only"] for r in done),
        "n_answer_fragments": sum(1 for r in done + absdone
                                  if r.get("answer_was_fragment")),

        # --- denominators, always explicit -----------------------------------
        "n_keyed": len(keyed),
        "value_correct": sum(1 for r in keyed if r["value_correct"]),
        "value_correct_of": "%d/%d" % (sum(1 for r in keyed if r["value_correct"]),
                                       len(keyed)),
        "value_wrong_confident": sum(1 for r in keyed if r["value_wrong_confident"]),
        "value_wrong_confident_of": "%d/%d" % (
            sum(1 for r in keyed if r["value_wrong_confident"]), len(keyed)),
        "n_unscorable_value": sum(1 for r in done if not r.get("value_scorable")),

        "n_vector": len(vecd),
        "vector_full": sum(1 for r in vecd if r["vector_full"]),
        "vector_full_of": "%d/%d" % (sum(1 for r in vecd if r["vector_full"]),
                                     len(vecd)),
        "vector_coverage_mean": (round(sum(r["vector_coverage"] for r in vecd)
                                       / len(vecd), 4) if vecd else None),

        "no_answer_answered": cause(done + absdone, "answered"),
        "no_answer_max_turns": cause(done + absdone, "max_turns"),
        "no_answer_timeout": cause(done + absdone, "timeout"),
        "no_answer_other_empty": cause(done + absdone, "other_empty"),
        "answered_within_300s": sum(1 for r in done + absdone
                                    if r.get("answered_within_300s")),
        "n_suspended": sum(1 for r in done + absdone if r.get("suspended")),

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
        "citation_window_chars": CITATION_WINDOW,
        "note": ("v3 re-scores recordings only. It changes no Phase 9 verdict; "
                 "those were set by the pre-registered v2 scorer and stand."),
    }

    suffix = "%s__%s" % (a.phase, a.tag) if a.tag else a.phase
    L.SCORES.mkdir(parents=True, exist_ok=True)
    (L.SCORES / ("live_v3__%s.json" % suffix)).write_text(
        json.dumps({"aggregate": agg, "answerable": per_q, "absence": per_abs,
                    "source_recordings": sorted(set(sources))},
                   indent=1), encoding="utf-8")
    (L.STATE / ("c_live_battery_v3__%s.json" % suffix)).write_text(
        json.dumps(agg, indent=1), encoding="utf-8")
    print(json.dumps(agg, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
