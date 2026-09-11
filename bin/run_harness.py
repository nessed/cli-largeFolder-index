#!/usr/bin/env python
"""run_harness.py - run the frozen question sample against a corpus rung and score it.

Scoring deliberately leads with the MECHANICAL metrics, because they are
unambiguous and they are the ones that expose silent omission:

  retrieval_recall     evidence files the agent actually opened / evidence files
  retrieval_precision  correct evidence opened / all files opened
  forbidden_cited      files opened that the key marks must_not_cite  <-- the trap metric
  absence_ok           on absence questions, did it decline instead of inventing

Answer-text correctness for trajectory is scored on DIRECTION + MAGNITUDE, never on
exact values: the key's trajectory values are the canonical registry series while the
cited PDFs print earlier vintages, so exact matching would fail 23 of 25 correct answers.
"""
import argparse, json, os, random, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# Phase 1.1: every path derived from one root. Phase 2.1: the answer key lives in
# the private tree, not one `..` above a session's cwd.
LAB = L.CORPUS_LAB
HARNESS = L.HARNESS
SAMPLE = L.QUESTION_SAMPLE

STRATA = {"trajectory": 4, "point_lookup": 3, "absence": 3, "multi_branch": 3,
          "reconciliation": 2, "stale_doc": 2, "name_content_mismatch": 1,
          "canonical_duplicate": 1, "relationship": 1}


def load_key():
    return json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))


def freeze_sample(seed=20260910):
    if SAMPLE.exists():
        return json.loads(SAMPLE.read_text(encoding="utf-8"))
    key = load_key()
    by_type = {}
    for q in key["questions"]:
        by_type.setdefault(q["type"], []).append(q["q_id"])
    rng = random.Random(seed)
    chosen = []
    for t, n in STRATA.items():
        ids = sorted(by_type.get(t, []))
        rng.shuffle(ids)
        chosen += ids[:n]
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text(json.dumps({"seed": seed, "q_ids": sorted(chosen)}, indent=1),
                      encoding="utf-8")
    return {"seed": seed, "q_ids": sorted(chosen)}


def one(q, args):
    cmd = [sys.executable, str(L.ASK),
           "--phase", args.phase, "--stack", args.stack,
           "--corpus", str(L.rung(args.rung)),
           "--corpus-label", f"harness{args.rung}",
           "--qid", q["q_id"],
           "--question", q["question"] +
           "\n\nCite the exact file paths (and page numbers for PDFs) you used.",
           "--model", args.model, "--max-turns", str(args.max_turns),
           "--timeout", str(args.timeout)]
    if args.settings:
        cmd += ["--settings", args.settings]
    if args.force:
        cmd += ["--force"]
    env = dict(os.environ)
    env.pop("CANARY_MANIFEST", None)   # never hand a session the manifest location
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env)
    return q["q_id"], p.returncode, (p.stdout or "").strip()[-200:]


NUM = re.compile(r"-?\d[\d,]*\.?\d*")
DECLINE = re.compile(
    r"\b(not (present|in the corpus|available|found|here)|no (such|evidence|record|"
    r"file|document|data)|does not (appear|exist)|could not find|couldn'?t find|"
    r"isn'?t (in|here|present)|no supporting evidence|not_found|unable to find)\b", re.I)


def norm(p):
    return str(p).replace("\\", "/").lower().lstrip("./")


def score(args, qs):
    outdir = L.RUNS / args.phase
    rows = []
    for q in qs:
        f = outdir / f"{args.stack}__harness{args.rung}__{q['q_id']}.json"
        if not f.exists():
            rows.append({"q_id": q["q_id"], "type": q["type"], "status": "no_result"})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        ans = d.get("answer_text") or ""
        opened = {norm(x["path"]) for x in d.get("files_opened", []) if x.get("path")}
        ev = {norm(a["path"]) for a in q.get("evidence_addresses", [])}
        bad = {norm(m["path"]) for m in q.get("must_not_cite", [])}
        # a path also counts as "reached" if the agent cited it in its answer text
        ans_n = norm(ans)
        cited = {p for p in ev if p in ans_n or p.split("/")[-1] in ans_n}
        reached = (opened | cited) & ev
        recall = len(reached) / len(ev) if ev else None
        forbidden = sorted((opened | {p for p in bad if p.split("/")[-1] in ans_n}) & bad)
        prec = len(reached) / len(opened) if opened else None

        r = {"q_id": q["q_id"], "type": q["type"],
             "n_evidence": len(ev), "n_reached": len(reached),
             "retrieval_recall": None if recall is None else round(recall, 3),
             "retrieval_precision": None if prec is None else round(prec, 3),
             "n_files_opened": len(opened), "forbidden_cited": len(forbidden),
             "forbidden_examples": forbidden[:3],
             "wall_s": d.get("wall_s"), "cost_usd": d.get("cost_usd"),
             "suspended": d.get("suspended"),
             "stream_json_ok": d.get("stream_json_ok"),
             "timed_out": d.get("timed_out"), "n_tool_calls": d.get("n_tool_calls"),
             "tools": d.get("tool_histogram"), "answer_head": ans[:200]}

        if q["type"] == "absence":
            declined = bool(DECLINE.search(ans))
            nums = NUM.findall(ans)
            r["absence_ok"] = bool(declined and len(nums) <= 2)
            r["absence_declined"] = declined
            r["absence_numbers_emitted"] = len(nums)
        rows.append(r)

    out = L.SCORES / f"harness__{args.stack}__rung{args.rung}.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")

    with_ev = [r for r in rows if r.get("retrieval_recall") is not None]
    ab = [r for r in rows if r.get("type") == "absence"]
    with_cost = [r for r in rows if r.get("cost_usd") is not None]
    timed = [r for r in rows if not r.get("suspended") and not r.get("timed_out")]
    summary = {
        "stack": args.stack, "rung": args.rung, "n_questions": len(rows),
        "mean_retrieval_recall": round(sum(r["retrieval_recall"] for r in with_ev)
                                       / len(with_ev), 3) if with_ev else None,
        "mean_retrieval_precision": round(
            sum(r["retrieval_precision"] or 0 for r in with_ev) / len(with_ev), 3)
            if with_ev else None,
        "questions_with_zero_recall": sum(1 for r in with_ev if r["retrieval_recall"] == 0),
        "total_forbidden_citations": sum(r.get("forbidden_cited", 0) for r in rows),
        "absence_correct": f"{sum(1 for r in ab if r.get('absence_ok'))}/{len(ab)}",
        "timeouts": sum(1 for r in rows if r.get("timed_out")),
        # 0.7 - a bare total silently favours whichever stack flailed more, because
        # a timed-out session reports no cost and drops out of the sum.
        "total_cost_usd": round(sum(r["cost_usd"] for r in with_cost), 4),
        "cost_n_of_m": f"{len(with_cost)}/{len(rows)}",
        "cost_warning": (None if len(with_cost) == len(rows) else
                         f"{len(rows) - len(with_cost)} session(s) reported no cost; "
                         f"NOT comparable to a total with a different n"),
        # 0.6 - suspended sessions measured laptop sleep, not the stack.
        "mean_wall_s_excl_suspended": (
            round(sum(r["wall_s"] or 0 for r in timed) / len(timed), 1) if timed else None),
        "n_suspended_excluded_from_timing": sum(1 for r in rows if r.get("suspended")),
        # 0.10 - a battery that reused results is stale and must say so itself.
        "n_skipped_stale": args.n_skipped,
        "battery_is_stale": args.n_skipped > 0,
        "not_stream_json": sum(1 for r in rows if r.get("stream_json_ok") is False),
    }
    (L.SCORES / f"summary__{args.stack}__rung{args.rung}.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--stack", required=True)
    ap.add_argument("--rung", default="500")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--settings", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args()
    a.n_skipped = 0

    samp = freeze_sample()
    key = load_key()
    qs = [q for q in key["questions"] if q["q_id"] in set(samp["q_ids"])]
    print(f"{len(qs)} questions (seed {samp['seed']}): "
          f"{sorted(set(q['type'] for q in qs))}")
    if not a.score_only:
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=a.parallel) as ex:
            for qid, rc, so in ex.map(lambda q: one(q, a), qs):
                if rc == 3:
                    a.n_skipped += 1
                    print(f"\033[1;31m[{qid}] SKIPPED-STALE\033[0m", file=sys.stderr)
                print(f"[{qid}] rc={rc} {so}")
        print(f"battery wall {time.monotonic()-t0:.0f}s")
        if a.n_skipped:
            print(f"\033[1;31m### {a.n_skipped} question(s) reused an existing result. "
                  f"THIS BATTERY IS STALE.\033[0m", file=sys.stderr)
    score(a, qs)
