#!/usr/bin/env python
"""c_llm_select_gate.py -- Experiment H, 2026-09-16.

Mechanism and gate in state/experiment_h_spec.md, committed before any call.
The frozen configuration's top-100 families are rendered as compact cards and
handed to the answering model in one headless single-turn call; it returns the
indices it would look in.

  python -u corpus-lab/bin/c_llm_select_gate.py --dev
  python -u corpus-lab/bin/c_llm_select_gate.py --holdout2      # look 1 of 2

Cards are built from shelf fields only -- no path, no page index, nothing from
the answer key. The key is read only to score indices after a call returns.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from pathlib import Path as pathlib_Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402

POOL = 100
FROZEN_FUSION = "rrf"
FROZEN_CAPTION_CHANNEL = "lex"
CACHE = L.PRIVATE / "results" / "h_cache"
# The cwd must be OUTSIDE the repository tree. A headless call made from
# inside it resolves to this project's own Claude Code project key and loads
# the project auto-memory -- the architecture review, the goal, the plans --
# so the selector was reading this project's notes while judging. Measured,
# not theorised: a first-run response quoted the memory back. Under a
# TEMP-tree cwd the key has no memory directory at all.
CWD = (pathlib_Path(tempfile.gettempdir()) / "c_h_select_cwd")
MAX_CALLS = 50

INSTRUCTION = (
    'Below are 100 publications held in a research folder, each with the years held '
    'and two lines from its table of contents. Which of them most likely print the '
    'table or figure that answers the question? Reply with JSON: '
    '{"picks": [up to 10 indices, most likely first], "publication_guess": "the name '
    'a Pakistani government publication would have for the document you would look '
    'in"}. Judge by what kind of publication would carry this series, not by word '
    'overlap.'
)


# ------------------------------------------------------------------ #
# cards -- shelf fields only
# ------------------------------------------------------------------ #
def build_cards(ctx, res):
    """One line per family, in the fused order do_find returned."""
    lines = []
    for i, f in enumerate(res["families"][:POOL], start=1):
        eds = f["editions"]
        fys = [e["fy"] for e in eds if e.get("fy")]
        if fys:
            span = ("%d editions, %s to %s" % (len(fys), min(fys), max(fys))
                    if len(fys) > 1 else "1 edition, %s" % fys[0])
        else:
            rel = f.get("primary_rel") or f.get("best_rel") or ""
            ext = Path(rel).suffix.lower().lstrip(".") or "file"
            span = "single file, %s" % ext
        why = " | ".join(w.strip() for w in (f.get("why") or [])[:2] if w and w.strip())
        why = re.sub(r"\s+", " ", why)[:220]
        lines.append("%d. %s (%s) -- %s" % (i, CSH._family_words(f["family"]), span, why))
    return "\n".join(lines)


def build_prompt(question, cards):
    return "%s\n\n%s\n\n%s" % (question, INSTRUCTION, cards)


# ------------------------------------------------------------------ #
# the call
# ------------------------------------------------------------------ #
DISALLOW = ("Bash,Read,Write,Edit,NotebookEdit,Glob,Grep,Task,Agent,WebFetch,"
            "WebSearch,TodoWrite")


def assert_clean_cwd():
    """A guard, because this failed silently once. Walks up from the cwd looking
    for a CLAUDE.md, and checks the project key that cwd resolves to has no
    auto-memory directory."""
    d = CWD.resolve()
    for p in [d] + list(d.parents):
        if (p / "CLAUDE.md").exists():
            raise SystemExit("H_CWD_NOT_CLEAN: CLAUDE.md at %s" % p)
    key = "C--" + str(d).replace(":", "").replace("\\", "-")
    mem = Path.home() / ".claude" / "projects" / key / "memory"
    if mem.is_dir() and any(mem.iterdir()):
        raise SystemExit("H_CWD_NOT_CLEAN: project memory at %s" % mem)


def call_model(prompt, timeout=180):
    CWD.mkdir(parents=True, exist_ok=True)
    assert_clean_cwd()
    md = CWD / "CLAUDE.md"
    if md.exists():
        md.unlink()
    env = dict(os.environ)
    env.pop("CANARY_MANIFEST", None)
    cmd = [L.CLAUDE, "-p", prompt, "--model", "claude-sonnet-5",
           "--max-turns", "2", "--output-format", "text",
           "--disallowedTools"] + DISALLOW.split(",")
    try:
        p = subprocess.run(cmd, cwd=str(CWD), capture_output=True, text=True,
                           errors="replace", env=env, timeout=timeout)
        return (p.stdout or "").strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "", -1


JSON_RE = re.compile(r"\{.*?\"picks\".*?\}", re.S)


def parse(text):
    m = JSON_RE.search(text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        try:
            d = json.loads(m.group(0).replace("'", '"'))
        except Exception:
            return None
    picks = d.get("picks")
    if not isinstance(picks, list):
        return None
    out = []
    for x in picks:
        try:
            out.append(int(x))
        except Exception:
            pass
    return {"picks": out[:10], "publication_guess": str(d.get("publication_guess") or "")}


# ------------------------------------------------------------------ #
# one question
# ------------------------------------------------------------------ #
def run_one(ctx, qid, question, queries, budget):
    CACHE.mkdir(parents=True, exist_ok=True)
    cpath = CACHE / ("%s.json" % qid)
    if cpath.exists():
        try:
            c = json.loads(cpath.read_text(encoding="utf-8"))
            if c.get("parsed"):
                return c, 0
        except Exception:
            pass

    res = CSH.do_find(ctx, queries, fusion=FROZEN_FUSION,
                      caption_channel=FROZEN_CAPTION_CHANNEL)
    fams = [f["family"] for f in res["families"][:POOL]]
    cards = build_cards(ctx, res)
    prompt = build_prompt(question, cards)

    used = 0
    parsed = None
    raw = ""
    for attempt in (1, 2):
        if used >= budget:
            break
        raw, rc = call_model(prompt)
        used += 1
        parsed = parse(raw)
        if parsed:
            break
    rec = {"q_id": qid, "n_pool": len(fams), "parsed": parsed,
           "raw_tail": (raw or "")[-1200:], "calls": used,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    cpath.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    rec["_fams"] = fams
    return rec, used


def score(rec, fams, gold):
    """Rank of the gold family within the model's picks (1-based), or None."""
    p = rec.get("parsed")
    if not p:
        return None, None
    guess = p.get("publication_guess") or ""
    for r, idx in enumerate(p["picks"], start=1):
        if 1 <= idx <= len(fams) and fams[idx - 1] in gold:
            return r, guess
    return None, guess


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--holdout2", action="store_true")
    ap.add_argument("--budget", type=int, default=MAX_CALLS)
    a = ap.parse_args(argv)

    ctx = CSH.get_ctx(str(L.STACKS / "s2_fts5" / "harness_15000.db"),
                      str(L.STACKS / "s7_shelf" / "shelf.db"))
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}

    path = L.STATE / "c_llm_select_gate.json"
    out = {}
    if path.exists():
        try:
            out = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            out = {}
    out.setdefault("generated_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    budget = a.budget - int(out.get("total_calls", 0))

    if a.dev:
        _qs, ids, per_q, _ = G.load_frozen(ctx)
        rewrites, _ = G.build_rewrites(ids, qs_by_id, L.STATE)
        ranks, guesses, calls = {}, 0, 0
        have_top3 = 0
        for qid in ids:
            pq = per_q[qid]
            queries = rewrites.get(qid, {}).get("queries") or [pq["question"]]
            rec, used = run_one(ctx, qid, pq["question"], queries, budget - calls)
            calls += used
            fams = rec.get("_fams")
            if fams is None:
                res = CSH.do_find(ctx, queries, fusion=FROZEN_FUSION,
                                  caption_channel=FROZEN_CAPTION_CHANNEL)
                fams = [f["family"] for f in res["families"][:POOL]]
            gold = G._ev_families(ctx, pq["resolved_rels"])
            r, guess = score(rec, fams, gold)
            ranks[qid] = r
            if guess:
                guesses += 1
                hv = CSH.do_have(ctx, guess)
                top3 = [f["family"] for f in hv.get("families", [])[:3]]
                if any(f in gold for f in top3):
                    have_top3 += 1
            print("  [%s] rank=%s calls=%d" % (qid, r, used), flush=True)
        vals = list(ranks.values())
        out["dev"] = {
            "n": len(ids),
            "top_1": sum(1 for v in vals if v == 1),
            "top_3": sum(1 for v in vals if v is not None and v <= 3),
            "top_10": sum(1 for v in vals if v is not None and v <= 10),
            "n_no_answer": sum(1 for v in vals if v is None),
            "per_question_rank": ranks,
            "publication_guess_have_top3": have_top3,
            "n_guesses": guesses,
        }
        out["total_calls"] = int(out.get("total_calls", 0)) + calls
        print("DEV top1=%d top3=%d top10=%d no_answer=%d  have(guess) top3=%d/%d"
              % (out["dev"]["top_1"], out["dev"]["top_3"], out["dev"]["top_10"],
                 out["dev"]["n_no_answer"], have_top3, len(ids)))

    if a.holdout2:
        h2 = json.loads((L.PRIVATE / "evidence_v1" / "holdout2_frozen.json")
                        .read_text(encoding="utf-8"))["holdout_q_ids"]
        cache = json.loads((L.STATE / "c_queries_holdout2.json").read_text(encoding="utf-8"))
        r2s = G.build_rel_to_survivor(ctx)
        ranks, calls = [], 0
        for qid in h2:
            q = qs_by_id[qid]
            rels = [r for r in (G.resolve_rel(ctx, G.norm_path(e["path"]), r2s)
                                for e in q["evidence_addresses"]) if r]
            if not rels:
                continue
            queries = cache.get(qid, {}).get("queries") or [q["question"]]
            rec, used = run_one(ctx, qid, q["question"], queries, budget - calls)
            calls += used
            fams = rec.get("_fams")
            if fams is None:
                res = CSH.do_find(ctx, queries, fusion=FROZEN_FUSION,
                                  caption_channel=FROZEN_CAPTION_CHANNEL)
                fams = [f["family"] for f in res["families"][:POOL]]
            r, _g = score(rec, fams, G._ev_families(ctx, rels))
            ranks.append(r)
            print("  [holdout2 %d/%d] calls=%d" % (len(ranks), len(h2), used), flush=True)
        out["holdout2"] = {
            "n_measurable": len(ranks),
            "top_3": sum(1 for v in ranks if v is not None and v <= 3),
            "top_10": sum(1 for v in ranks if v is not None and v <= 10),
            "n_no_answer": sum(1 for v in ranks if v is None),
            "look": "1 of 2",
        }
        out["total_calls"] = int(out.get("total_calls", 0)) + calls
        print("HOLDOUT-2 top3=%d top10=%d of %d"
              % (out["holdout2"]["top_3"], out["holdout2"]["top_10"], len(ranks)))

    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("total_calls=%s" % out.get("total_calls"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
