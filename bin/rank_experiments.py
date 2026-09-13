#!/usr/bin/env python
"""rank_experiments.py - the gate failed, so try to fix ranking before paying.

verify_search_fix.py showed the sentence-capable front door removes every empty
result (17/17 -> 0/17) and still puts the correct evidence file in the top 50
ZERO times. A search that returns 50 wrong pages instead of nothing has moved the
failure, not fixed it.

So: try several ways of turning a question into a query, and measure where the
correct evidence file actually lands. All offline, read-only, no sessions, free.

  legacy_and   every word of the question, ANDed          (what shipped before)
  or_all       every content word, ORed, bm25             (today's fix)
  and_rare_K   the K rarest content words, ANDed          (K = 2, 3, 4)
  or_rare_K    the K rarest content words, ORed           (K = 3, 5)
  rerank       top N by OR/bm25, re-sorted by how many distinct query terms the
               page actually contains, then by bm25

"Rarest" is measured against this index: a term matching few pages carries more
signal than one matching half the corpus. That is the cheapest possible version
of "narrow the candidate set before ranking", which the night-2 report listed as
untested.

DEEP RANK is also reported: if the right page sits at rank 3,000 then reranking a
large top-k can reach it and is worth building; if it sits at rank 400,000 then
nothing downstream of this query can recover it and the query itself is wrong.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import corpus_search as CS  # noqa: E402

DB = L.STACKS / "s2_fts5" / "harness_15000.db"
DEEP = 5000        # how far down to look for the right page
RERANK_POOL = 2000  # candidates pulled before reranking


def norm(p):
    return str(p).replace("\\", "/").lower().lstrip("./")


def df(db, term, cache):
    """How many pages contain this term (document frequency)."""
    if term not in cache:
        try:
            cache[term] = db.execute(
                "SELECT COUNT(*) FROM pages WHERE pages MATCH ?",
                (f'"{term}"',)).fetchone()[0]
        except sqlite3.OperationalError:
            cache[term] = 0
    return cache[term]


def run(db, match, limit):
    try:
        return db.execute(
            "SELECT rel, page_index, bm25(pages) FROM pages WHERE pages MATCH ? "
            "ORDER BY bm25(pages) LIMIT ?", (match, limit)).fetchall()
    except sqlite3.OperationalError:
        return []


def rank_of(rows, ev):
    for i, r in enumerate(rows, 1):
        if norm(r[0]) in ev:
            return i
    return None


def rerank(db, words, ev):
    """Pull a pool by OR/bm25, then re-sort by how much of the question each page
    actually contains. Cheap: one pool query, one body fetch, counting in Python.

    Score per page = distinct query terms present. bm25 breaks ties. This is the
    minimum viable "narrow, then rank on coverage" and needs no model.
    """
    m = CS.fts_any(words)
    if not m:
        return None, 0
    try:
        pool = db.execute(
            "SELECT rowid, rel, page_index, bm25(pages) FROM pages WHERE pages MATCH ? "
            "ORDER BY bm25(pages) LIMIT ?", (m, RERANK_POOL)).fetchall()
    except sqlite3.OperationalError:
        return None, 0
    if not pool:
        return None, 0
    ids = [str(r[0]) for r in pool]
    bodies = dict(db.execute(
        f"SELECT rowid, lower(body) FROM pages WHERE rowid IN ({','.join(ids)})"
    ).fetchall())
    scored = []
    for rid, rel, pi, score in pool:
        b = bodies.get(rid, "")
        n = sum(1 for w in words if w in b)
        scored.append((n, score, rel))
    scored.sort(key=lambda t: (-t[0], t[1]))
    for i, (n, score, rel) in enumerate(scored, 1):
        if norm(rel) in ev:
            return i, len(scored)
    return None, len(scored)


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    samp = set(json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))["q_ids"])
    qs = [q for q in key["questions"] if q["q_id"] in samp and q.get("evidence_addresses")]
    qs.sort(key=lambda q: q["q_id"])
    cache = {}

    strategies = ["legacy_and", "or_all", "and_rare_2", "and_rare_3", "and_rare_4",
                  "or_rare_3", "or_rare_5"]
    if "--rerank" in sys.argv:
        strategies.append("rerank")
    results = {s: [] for s in strategies}
    per_q = []

    t0 = time.time()
    for q in qs:
        ev = {norm(a["path"]) for a in q.get("evidence_addresses", [])}
        words = CS.content_words(q["question"])
        rare = sorted(words, key=lambda w: df(db, w, cache))
        row = {"q_id": q["q_id"], "type": q["type"], "n_words": len(words),
               "rarest": [(w, cache[w]) for w in rare[:4]]}

        m = CS.fts_quote(q["question"])
        r = rank_of(run(db, m, DEEP), ev) if m else None
        row["legacy_and"] = r

        r = rank_of(run(db, CS.fts_any(words), DEEP), ev)
        row["or_all"] = r

        for k in (2, 3, 4):
            r = rank_of(run(db, CS.fts_all(rare[:k]), DEEP), ev)
            row[f"and_rare_{k}"] = r
        for k in (3, 5):
            r = rank_of(run(db, CS.fts_any(rare[:k]), DEEP), ev)
            row[f"or_rare_{k}"] = r

        if "rerank" in strategies:
            rr, _ = rerank(db, words, ev)
            row["rerank"] = rr

        for s in strategies:
            results[s].append(row.get(s))
        per_q.append(row)
        print(f"  {q['q_id']:<7} done ({time.time() - t0:.0f}s)", flush=True)

    print("\nWHERE DOES THE CORRECT PAGE LAND?  (rank, '-' = not in top "
          f"{DEEP})\n")
    hdr = f"{'q_id':<7}{'type':<20}" + "".join(f"{s:>13}" for s in strategies)
    print(hdr)
    print("-" * len(hdr))
    for row in per_q:
        print(f"{row['q_id']:<7}{row['type']:<20}" +
              "".join(f"{str(row.get(s) or '-'):>13}" for s in strategies))

    print("\nSCOREBOARD - how many of the 17 put the right page this high\n")
    print(f"{'strategy':<14}{'top 1':>8}{'top 5':>8}{'top 15':>8}{'top 50':>8}"
          f"{'top 500':>9}{'found at all':>14}")
    print("-" * 69)
    for s in strategies:
        v = results[s]
        row = [sum(1 for x in v if x and x <= d) for d in (1, 5, 15, 50, 500)]
        print(f"{s:<14}" + "".join(f"{x:>8}" for x in row[:4]) +
              f"{row[4]:>9}{sum(1 for x in v if x):>14}")

    print(f"\n  'found at all' means inside the top {DEEP} of that query.")
    print("  top 15 is what the agent actually sees by default.")

    out = L.STATE / "rank_experiments.json"
    out.write_text(json.dumps({"deep": DEEP, "per_q": per_q}, indent=1),
                   encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
