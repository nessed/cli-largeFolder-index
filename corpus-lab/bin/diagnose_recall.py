#!/usr/bin/env python
"""diagnose_recall.py - why is question recall stuck at ~0.15 across every stack?

Three stacks with very different plumbing (no index, index-by-instruction,
index-by-enforcement) all land in the same narrow band on the 20 frozen
questions, while the same stacks separate cleanly on canaries. So the bottleneck
is not which search tool gets used. This splits the failure into the three places
it can live, using only data already on disk plus direct queries against the FTS5
index. It runs no sessions and costs nothing.

  A. IS IT IN THE INDEX AT ALL?
     For each question's evidence files, is the file indexed? If the evidence is
     not in the index, no index-based stack can ever reach it and the ceiling is
     ingestion, not retrieval.

  B. CAN LEXICAL SEARCH FIND IT FROM THE QUESTION'S OWN WORDS?
     Run the question text as an FTS5 query. Does the correct evidence file come
     back at all, and at what rank? This is the "vague question" hypothesis
     stated precisely: the words in the question do not appear in the document.

  C. DID THE AGENT REACH IT AND STILL FAIL?
     Compare what the session actually opened against the evidence set. If the
     agent opened the right file and still scored zero, the failure is downstream
     of retrieval entirely.

Prints aggregate counts only.
"""
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

STOP = set("""a an the of in on at to for and or is are was were be been being with by from
as that this these those it its which what when where who whom how why does do did doing
than then there their them they he she his her you your we our us i me my if but not no
nor so such only own same too very can will just should now over under between into
through during before after above below up down out off again further once here both each
few more most other some any all no""".split())


def toks(s):
    return [t for t in re.findall(r"[A-Za-z0-9]{3,}", (s or "").lower()) if t not in STOP]


def norm(p):
    return str(p).replace("\\", "/").lower().lstrip("./")


def main():
    db = sqlite3.connect(
        "file:" + str(L.STACKS / "s2_fts5" / "harness_15000.db") + "?mode=ro", uri=True)
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    samp = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    qs = [q for q in key["questions"] if q["q_id"] in set(samp["q_ids"])]

    indexed = {norm(r[0]) for r in db.execute(
        "SELECT rel FROM files WHERE status='indexed'").fetchall()}
    status = {norm(r[0]): r[1] for r in db.execute("SELECT rel, status FROM files").fetchall()}

    stacks = {
        "s0_baseline": ("P7_s0_baseline_h15000", "harness15000"),
        "s1_policy":   ("P7_s1_policy_h15000",   "harness15000"),
        "s2_hook":     ("P7_s2_hook_h15000",     "harness15000"),
    }
    opened = {}
    for st, (ph, lbl) in stacks.items():
        d = L.RUNS / ph
        for f in d.glob(f"{st}__{lbl}__*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            opened[(st, r["qid"])] = {norm(x["path"]) for x in r.get("files_opened", [])
                                      if x.get("path")}

    A = Counter()
    B = Counter()
    C = Counter()
    rank_hist = Counter()
    per_q = []

    for q in qs:
        ev = [norm(a["path"]) for a in q.get("evidence_addresses", [])]
        if not ev:
            continue
        # --- A. ingestion ---
        n_idx = sum(1 for e in ev if e in indexed)
        A["evidence_files_total"] += len(ev)
        A["evidence_files_indexed"] += n_idx
        for e in ev:
            if e not in indexed:
                A["missing_status_" + str(status.get(e, "NOT_IN_FILES_TABLE"))] += 1
        all_idx = (n_idx == len(ev))

        # --- B. lexical reachability from the question's own words ---
        t = toks(q["question"])[:12]
        best = None
        if t:
            m = " OR ".join(f'"{x}"' for x in t)
            try:
                hits = db.execute(
                    "SELECT rel FROM pages WHERE pages MATCH ? ORDER BY bm25(pages) LIMIT 50",
                    (m,)).fetchall()
            except sqlite3.OperationalError:
                hits = []
            seen = []
            for h in hits:
                r = norm(h[0])
                if r not in seen:
                    seen.append(r)
            for e in ev:
                if e in seen:
                    rk = seen.index(e) + 1
                    best = rk if best is None else min(best, rk)
        if all_idx:
            B["questions_with_all_evidence_indexed"] += 1
            if best is None:
                B["evidence_NOT_in_top50_by_question_words"] += 1
                rank_hist["not_found"] += 1
            else:
                B["evidence_in_top50"] += 1
                rank_hist["top1" if best == 1 else
                          "top5" if best <= 5 else
                          "top10" if best <= 10 else "top50"] += 1

        # --- C. did any stack actually open the evidence ---
        for st in stacks:
            op = opened.get((st, q["q_id"]))
            if op is None:
                C[f"{st}__no_result"] += 1
                continue
            if set(ev) & op:
                C[f"{st}__opened_evidence"] += 1
            else:
                C[f"{st}__never_opened_evidence"] += 1

        per_q.append({"q_id": q["q_id"], "type": q["type"], "n_evidence": len(ev),
                      "all_indexed": all_idx, "best_rank_by_question_words": best})

    print("=" * 72)
    print("A. INGESTION - is the evidence even in the index?")
    print("=" * 72)
    tot, idx = A["evidence_files_total"], A["evidence_files_indexed"]
    print(f"  evidence files referenced by the 20 questions : {tot}")
    print(f"  of those, indexed                             : {idx}  ({idx/tot:.0%})")
    for k, v in sorted(A.items()):
        if k.startswith("missing_status_"):
            print(f"     NOT indexed, status={k[len('missing_status_'):]:<22} {v}")

    print()
    print("=" * 72)
    print("B. LEXICAL REACH - can the question's own words retrieve its evidence?")
    print("=" * 72)
    print(f"  questions whose evidence is fully indexed      : "
          f"{B['questions_with_all_evidence_indexed']}")
    print(f"    evidence appears in top-50 BM25 hits         : {B['evidence_in_top50']}")
    print(f"    evidence NOT in top 50                       : "
          f"{B['evidence_NOT_in_top50_by_question_words']}")
    print(f"  best-rank distribution: {dict(rank_hist)}")

    print()
    print("=" * 72)
    print("C. DOWNSTREAM - did the agent open the evidence and still fail?")
    print("=" * 72)
    for st in stacks:
        print(f"  {st:<14} opened evidence {C[st+'__opened_evidence']:>3}   "
              f"never opened {C[st+'__never_opened_evidence']:>3}   "
              f"no result {C[st+'__no_result']:>3}")

    out = L.STATE / "diagnose_recall.json"
    out.write_text(json.dumps({"A": dict(A), "B": dict(B), "ranks": dict(rank_hist),
                               "C": dict(C), "per_question": per_q}, indent=1),
                   encoding="utf-8")
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
