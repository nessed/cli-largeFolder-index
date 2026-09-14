#!/usr/bin/env python
"""c_holdout2.py -- freeze a second confirmation set, 2026-09-15 evening.

Holdout-1 (`_private/evidence_v1/holdout_frozen.json`) has one look left and is
retired for this branch after Experiment G spends it. Everything measured after
that needs a confirmation set that has never been looked at, or the branch has
no way to tell a real improvement from one fitted to 17 questions.

Sampled from the answerable questions in the key that are in NEITHER the frozen
20 NOR holdout-1, with a fixed seed, inside this script. Only question ids are
written out, and the rewrite cache is gitignored -- a confirmation set is worth
exactly what it is unseen, and `corpus-lab/state/` is published.

  python -u corpus-lab/bin/c_holdout2.py [--budget 30]

Never inspects a question. Prints counts only.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_offline_gate as G  # noqa: E402

SEED = 20260915
N = 30
OUT = L.PRIVATE / "evidence_v1" / "holdout2_frozen.json"
CACHE = L.STATE / "c_queries_holdout2.json"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=30)
    a = ap.parse_args(argv)

    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    qs_by_id = {q["q_id"]: q for q in key["questions"]}
    frozen20 = set(json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))["q_ids"])
    h1 = set(json.loads(G.HOLDOUT_FROZEN.read_text(encoding="utf-8"))["holdout_q_ids"])

    eligible = sorted(q["q_id"] for q in key["questions"]
                      if q["type"] != "absence"
                      and q["q_id"] not in frozen20 and q["q_id"] not in h1)
    print("eligible (answerable, not in frozen 20, not in holdout-1): %d" % len(eligible))

    if OUT.exists():
        chosen = json.loads(OUT.read_text(encoding="utf-8"))["holdout_q_ids"]
        print("holdout-2 already frozen: %d ids (not re-sampled)" % len(chosen))
    else:
        rng = random.Random(SEED)
        chosen = sorted(rng.sample(eligible, min(N, len(eligible))))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"seed": SEED, "n": len(chosen),
                                   "holdout_q_ids": chosen}, indent=1), encoding="utf-8")
        print("froze holdout-2: %d ids, seed %d" % (len(chosen), SEED))

    cached = {}
    if CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cached = {}
    todo = [q for q in chosen if q not in cached]
    if len(todo) > a.budget:
        raise SystemExit("HAIKU_BUDGET: need %d calls, budget %d" % (len(todo), a.budget))

    cwd = L.SCRATCH / "c_llm_cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    if (cwd / "CLAUDE.md").exists():
        (cwd / "CLAUDE.md").unlink()
    err_path = L.SCRATCH / "c_queries_holdout2_stderr.log"

    n_calls = n_failed = 0
    for qid in todo:
        lines, failed = G._haiku_rewrite(qs_by_id[qid]["question"], cwd, err_path)
        n_calls += 1
        if failed:
            n_failed += 1
            cached[qid] = {"q_id": qid, "queries": [qs_by_id[qid]["question"]],
                           "rewrite_failed": True}
        else:
            cached[qid] = {"q_id": qid,
                           "queries": [qs_by_id[qid]["question"]] + lines[:5],
                           "rewrite_failed": False}
        CACHE.write_text(json.dumps(cached, indent=1), encoding="utf-8")
        if n_calls % 10 == 0:
            print("  rewrites %d/%d" % (n_calls, len(todo)), flush=True)

    rec = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "seed": SEED, "n_eligible": len(eligible), "n_frozen": len(chosen),
           "n_haiku_calls": n_calls, "n_rewrite_failed": n_failed,
           "n_cached": len(cached),
           "n_with_6_queries": sum(1 for v in cached.values() if len(v["queries"]) == 6),
           "looks_used": 0, "looks_allowed_today": 2}
    (L.STATE / "c_holdout2.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
