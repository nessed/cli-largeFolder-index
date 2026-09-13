#!/usr/bin/env python
"""verify_search_fix.py - does the sentence-capable front door actually help?

Gate before spending. The old front door required every word of a question on one
page, so it returned nothing on 16 of the frozen 20 - and on 13 of the 17 whose
evidence is in the index. This asks two things of the new one, offline and free:

  1. does it still come back empty?
  2. does the CORRECT evidence file appear, and at what rank?

Question 2 is the one that matters. A search that returns 15 wrong pages instead
of zero pages is not an improvement; it just moves the failure downstream.

No sessions, no cost. Read-only against the harness index.
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import corpus_search as CS  # noqa: E402

DB = L.STACKS / "s2_fts5" / "harness_15000.db"
DEPTHS = (15, 50)


def norm(p):
    return str(p).replace("\\", "/").lower().lstrip("./")


def rank_of(rows, ev):
    """1-based rank of the first correct evidence file, or None."""
    for i, r in enumerate(rows, 1):
        if norm(r[0]) in ev:
            return i
    return None


def main():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    samp = set(json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))["q_ids"])
    qs = [q for q in key["questions"] if q["q_id"] in samp]
    qs.sort(key=lambda q: (q["type"] != "absence", q["q_id"]))

    maxd = max(DEPTHS)
    rows_out = []
    for q in qs:
        ev = {norm(a["path"]) for a in q.get("evidence_addresses", [])}
        old_rows, old_total, _ = CS.search(db, q["question"], maxd, False, legacy=True)
        new_rows, new_total, tier = CS.search(db, q["question"], maxd, False)
        rows_out.append({
            "q_id": q["q_id"], "type": q["type"], "has_evidence": bool(ev),
            "old_hits": len(old_rows), "old_total": old_total,
            "old_rank": rank_of(old_rows, ev) if ev else None,
            "new_hits": len(new_rows), "new_total": new_total, "tier": tier,
            "new_rank": rank_of(new_rows, ev) if ev else None,
        })

    hdr = (f"{'q_id':<7}{'type':<20}{'ev':>3}{'OLD hits':>10}{'OLD rank':>10}"
           f"{'NEW hits':>10}{'tier':>6}{'NEW rank':>10}")
    print(f"index: {DB.name}   depth searched: top {maxd}\n")
    print(hdr)
    print("-" * len(hdr))
    for r in rows_out:
        print(f"{r['q_id']:<7}{r['type']:<20}{'Y' if r['has_evidence'] else 'N':>3}"
              f"{r['old_hits']:>10}{str(r['old_rank'] or '-'):>10}"
              f"{r['new_hits']:>10}{r['tier']:>6}{str(r['new_rank'] or '-'):>10}")

    ev_rows = [r for r in rows_out if r["has_evidence"]]
    print("\nTHE GATE")
    print("-" * 60)
    old_empty = sum(1 for r in ev_rows if r["old_hits"] == 0)
    new_empty = sum(1 for r in ev_rows if r["new_hits"] == 0)
    print(f"  answerable questions returning NOTHING:   old {old_empty}/{len(ev_rows)}"
          f"   ->   new {new_empty}/{len(ev_rows)}")
    for d in DEPTHS:
        o = sum(1 for r in ev_rows if r["old_rank"] and r["old_rank"] <= d)
        n = sum(1 for r in ev_rows if r["new_rank"] and r["new_rank"] <= d)
        print(f"  correct evidence inside top {d:<3}:            old {o}/{len(ev_rows)}"
              f"   ->   new {n}/{len(ev_rows)}")
    print("\n  The first line is plumbing. The rest is whether it FINDS anything.")
    print("  If the top-15 number does not move, the agent still gets 15 wrong pages")
    print("  and paying for a battery buys nothing.")

    out = L.STATE / "verify_search_fix.json"
    out.write_text(json.dumps(rows_out, indent=1), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
