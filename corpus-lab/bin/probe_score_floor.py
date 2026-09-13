#!/usr/bin/env python
"""probe_score_floor.py - can a retrieval score floor tell "it's in there" from "it isn't"?

THE QUESTION THIS ANSWERS
-------------------------
Absence questions scored 0/3 in all three stacks: when the honest answer was "not in
the corpus", every stack invented one. The cheapest conceivable fix is a floor - the
front door refuses to answer when its best hit scores below some threshold. That only
works if the score distribution for questions whose answer IS present separates from
the distribution for questions whose answer is ABSENT.

This measures that separation before anyone pays for a session. It runs the 20 frozen
questions' own words against the FTS5 index read-only, records candidate discriminators,
and reports whether any single threshold splits the two groups. No sessions, no cost.

TWO QUERY SHAPES, because the front door and the earlier probe disagree
----------------------------------------------------------------------
  AND  what corpus_search.py actually builds: fts_quote() joins every token as a
       quoted term, and FTS5's implicit operator is AND. A 15-token question is a
       15-way conjunction, which usually matches nothing.
  OR   what diagnose_recall.py used for finding B - an OR over content words,
       capped at 12. More forgiving, and not what the front door does.

Both are reported because a floor has to live on whichever one the agent's queries
actually resemble, and neither is the agent's real query. The agent issues SHORT
phrases it invents from the question; these two shapes bracket that behaviour rather
than reproducing it.

WHY bm25 NUMBERS LOOK ODD
-------------------------
SQLite FTS5 bm25() returns NEGATIVE values and ORDER BY bm25 ASC puts the best match
first, so **more negative is a better match**. Magnitude also scales with how many
query terms are present, so a score from a 4-token query is not comparable with one
from a 14-token query. That is the central threat to a fixed floor and it is measured
here as score_per_token.
"""
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
from diagnose_recall import toks  # one definition of "content word"  # noqa: E402

DB = L.STACKS / "s2_fts5" / "harness_15000.db"
OR_CAP = 12          # diagnose_recall.py's cap, kept identical for comparability
DEEP_RANK = 10       # for the top1-vs-deeper gap


# An IDENTIFIER is the part of a question that names a specific thing rather than a
# topic: a fiscal year, a four-digit year, a notification number, an acronym. Derived
# from the question text ONLY - never from the key's absence_probe, which would be
# reading the answer.
RE_IDENT = [
    re.compile(r"\b\d{4}-\d{2,4}\b"),      # 2008-09, 2021-2022
    re.compile(r"\b(?:19|20)\d{2}\b"),     # 2024
    re.compile(r"\b\d{3,}\b"),             # 1500, 1502
    re.compile(r"\b[A-Z]{3,6}\b"),         # SRO, PSDP, ADP
]


def identifiers(raw):
    """Identifier-ish tokens from the raw question, de-duplicated, order kept."""
    out = []
    for rx in RE_IDENT:
        for m in rx.findall(raw or ""):
            t = m if isinstance(m, str) else m[0]
            for piece in re.findall(r"[A-Za-z0-9]{3,}", t):
                if piece.lower() not in [o.lower() for o in out]:
                    out.append(piece)
    return out


def q_and(tokens):
    return " ".join(f'"{t}"' for t in tokens) or None


def q_or(tokens):
    tokens = tokens[:OR_CAP]
    return " OR ".join(f'"{t}"' for t in tokens) or None


def probe(db, match):
    """-> total matching pages, top-1 score, score at DEEP_RANK, top-1 path."""
    if not match:
        return {"total": 0, "top1": None, "deep": None, "top1_path": None}
    try:
        total = db.execute("SELECT COUNT(*) FROM pages WHERE pages MATCH ?",
                           (match,)).fetchone()[0]
        rows = db.execute(
            "SELECT rel, bm25(pages) FROM pages WHERE pages MATCH ? "
            "ORDER BY bm25(pages) LIMIT ?", (match, DEEP_RANK)).fetchall()
    except sqlite3.OperationalError as e:
        return {"total": 0, "top1": None, "deep": None, "top1_path": f"ERROR {e}"}
    if not rows:
        return {"total": total, "top1": None, "deep": None, "top1_path": None}
    return {"total": total,
            "top1": round(rows[0][1], 3),
            "deep": round(rows[-1][1], 3) if len(rows) == DEEP_RANK else None,
            "top1_path": rows[0][0]}


def fmt(v, w=9, nd=2):
    if v is None:
        return " " * (w - 1) + "-"
    if isinstance(v, float):
        return f"{v:>{w}.{nd}f}"
    return f"{v:>{w}}"


def dist(label, vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return f"{label:<22}  (no values)"
    return (f"{label:<22}  n={len(vals):<3} min={min(vals):>10.2f} "
            f"med={statistics.median(vals):>10.2f} max={max(vals):>10.2f}")


def separable(present, absent, higher_is_present):
    """Does ANY single threshold split the two groups? -> (bool, margin, threshold).

    margin is the gap between the groups; <=0 means the ranges overlap and no floor
    on this metric can work, however it is tuned.
    """
    p = [v for v in present if v is not None]
    a = [v for v in absent if v is not None]
    cov = (len(p), len(present), len(a), len(absent))
    if not p or not a:
        return None, None, None, cov
    if higher_is_present:
        margin = min(p) - max(a)
        thr = (min(p) + max(a)) / 2
    else:
        margin = min(a) - max(p)
        thr = (min(a) + max(p)) / 2
    return margin > 0, round(margin, 3), round(thr, 3), cov


def main():
    if not DB.exists():
        raise SystemExit(f"no index at {DB}")
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    samp = set(json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))["q_ids"])
    qs = [q for q in key["questions"] if q["q_id"] in samp]
    qs.sort(key=lambda q: (q["type"] != "absence", q["q_id"]))

    rows = []
    for q in qs:
        t = toks(q["question"])
        present = bool(q.get("evidence_addresses"))
        a = probe(db, q_and(t))
        o = probe(db, q_or(t))
        ids = identifiers(q["question"])
        # per-identifier page counts, and the AND over all of them
        id_counts = {i: probe(db, q_and([i]))["total"] for i in ids}
        idp = probe(db, q_and(ids)) if ids else {"total": 0, "top1": None,
                                                 "deep": None, "top1_path": None}
        rows.append({
            "q_id": q["q_id"], "type": q["type"], "present": present,
            "n_tokens": len(t), "n_tokens_or": min(len(t), OR_CAP),
            "and": a, "or": o,
            "identifiers": ids, "ident_counts": id_counts, "ident_and": idp,
            "ident_min_count": min(id_counts.values()) if id_counts else None,
            "or_top1_per_token": (round(o["top1"] / min(len(t), OR_CAP), 3)
                                  if o["top1"] is not None and t else None),
            "or_gap_top1_deep": (round(o["deep"] - o["top1"], 3)
                                 if o["top1"] is not None and o["deep"] is not None
                                 else None),
        })

    pres = [r for r in rows if r["present"]]
    absent = [r for r in rows if not r["present"]]

    print(f"index: {DB.name}   questions: {len(rows)}  "
          f"(evidence {len(pres)}, absence {len(absent)})")
    print("bm25: MORE NEGATIVE = BETTER MATCH. 'and' is what corpus_search.py builds;")
    print(f"'or' is diagnose_recall.py's proxy, capped at {OR_CAP} tokens.\n")

    hdr = (f"{'q_id':<7}{'type':<20}{'ev':>3}{'ntok':>6}"
           f"{'AND pages':>11}{'AND top1':>10}"
           f"{'OR pages':>10}{'OR top1':>10}{'OR/tok':>9}{'gap1-10':>9}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r is absent[0]:
            print("-" * len(hdr) + "   <- absence questions below")
        print(f"{r['q_id']:<7}{r['type']:<20}{'Y' if r['present'] else 'N':>3}"
              f"{r['n_tokens']:>6}"
              f"{fmt(r['and']['total'], 11)}{fmt(r['and']['top1'], 10)}"
              f"{fmt(r['or']['total'], 10)}{fmt(r['or']['top1'], 10)}"
              f"{fmt(r['or_top1_per_token'], 9)}{fmt(r['or_gap_top1_deep'], 9)}")

    print("\nDISTRIBUTIONS")
    print("-" * 70)
    for label, grp in (("evidence (n=17)", pres), ("absence  (n=3)", absent)):
        print(f"\n{label}")
        print("  " + dist("AND matching pages", [r["and"]["total"] for r in grp]))
        print("  " + dist("AND top1 bm25", [r["and"]["top1"] for r in grp]))
        print("  " + dist("OR matching pages", [r["or"]["total"] for r in grp]))
        print("  " + dist("OR top1 bm25", [r["or"]["top1"] for r in grp]))
        print("  " + dist("OR top1 per token", [r["or_top1_per_token"] for r in grp]))
        print("  " + dist("OR gap top1->top10", [r["or_gap_top1_deep"] for r in grp]))

    print("\nIDENTIFIER PROBE - does the specific thing named in the question exist?")
    print("-" * 70)
    print("  A bag-of-words score asks 'is this topic in the corpus'. Every question's")
    print("  topic is. These three absence questions each name a SPECIFIC item - a")
    print("  fiscal year, a notification number - so the answerable question is whether")
    print("  that item appears at all. Identifiers are taken from the question text only.\n")
    print(f"{'q_id':<7}{'ev':>3}  {'and-pages':>10}{'rarest':>9}   identifiers")
    print("-" * 78)
    for r in rows:
        if r is absent[0]:
            print("-" * 78 + "   <- absence below")
        ids = ",".join(f"{k}:{v}" for k, v in r["ident_counts"].items())
        print(f"{r['q_id']:<7}{'Y' if r['present'] else 'N':>3}  "
              f"{fmt(r['ident_and']['total'], 10)}{fmt(r['ident_min_count'], 9)}   {ids[:70]}")

    print("\nSEPARABILITY - can ANY single threshold split present from absent?")
    print("-" * 70)
    metrics = [
        ("AND matching pages", lambda r: r["and"]["total"], True),
        ("AND top1 bm25", lambda r: r["and"]["top1"], False),
        ("OR matching pages", lambda r: r["or"]["total"], True),
        ("OR top1 bm25", lambda r: r["or"]["top1"], False),
        ("OR top1 per token", lambda r: r["or_top1_per_token"], False),
        ("OR gap top1->top10", lambda r: r["or_gap_top1_deep"], True),
        ("IDENT and-pages", lambda r: r["ident_and"]["total"], True),
        ("IDENT rarest token", lambda r: r["ident_min_count"], True),
    ]
    verdicts = {}
    for name, f, hi in metrics:
        ok, margin, thr, cov = separable([f(r) for r in pres],
                                         [f(r) for r in absent], hi)
        verdicts[name] = (ok, margin, thr, cov)
        scored = f"scored {cov[0]}/{cov[1]} ev, {cov[2]}/{cov[3]} ab"
        if ok is None:
            print(f"  {name:<22} UNTESTABLE  a group has no values   ({scored})")
        elif ok:
            print(f"  {name:<22} SEPARATES   margin={margin:<10} thr={thr:<12} ({scored})")
        else:
            print(f"  {name:<22} overlaps    margin={margin:<10} "
                  f"{'':<16} ({scored})")

    print("\n  READ THE 'scored' COLUMN BEFORE BELIEVING A 'SEPARATES'. A metric that")
    print("  cannot be computed for some questions is compared on a SUBSET, and a rule")
    print("  that cannot fire is not a rule that works. Every verdict also rests on")
    print("  THREE absence questions: three points cannot establish a threshold, they")
    print("  can only fail to rule one out.")

    out = L.STATE / "probe_score_floor.json"
    out.write_text(json.dumps(
        {"db": DB.name, "or_cap": OR_CAP, "deep_rank": DEEP_RANK,
         "rows": rows,
         "verdicts": {k: {"separates": v[0], "margin": v[1], "threshold": v[2]}
                      for k, v in verdicts.items()}},
        indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
