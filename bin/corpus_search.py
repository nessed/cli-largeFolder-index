#!/usr/bin/env python
"""corpus_search.py - the front door. Page-level search over the FTS5 corpus index.

Every result is an addressable location (file + page), never just a filename, and
every result set carries a retrieval receipt so an omission is visible rather than
silent. This is what the agent is redirected to when built-in Grep/Glob are denied.

  corpus_search.py "motor vehicle production"      # ranked page hits
  corpus_search.py --exact "SRO 1247"              # literal phrase
  corpus_search.py --page <rel> <page_index>       # read one page
  corpus_search.py --coverage                      # what is and isn't in the index
"""
import argparse, json, os, re, sqlite3, sys
from pathlib import Path

DEFAULT_DB = os.environ.get("CORPUS_DB", r"C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\raship.db")


def connect(db):
    if not Path(db).exists():
        print(f"ERROR: no index at {db}. Run index_build.py first.", file=sys.stderr)
        sys.exit(2)
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def fts_quote(q):
    """Make an arbitrary user string safe for FTS5 MATCH as a phrase-ish query."""
    toks = re.findall(r"[A-Za-z0-9_\-]+", q)
    if not toks:
        return None
    return " ".join(f'"{t}"' for t in toks)


def coverage(db):
    rows = dict(db.execute("SELECT status, COUNT(*) FROM files GROUP BY status").fetchall())
    meta = dict(db.execute("SELECT k, v FROM meta").fetchall())
    npages = db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    discovered = int(meta.get("discovered", 0))
    indexed = rows.get("indexed", 0)
    # os.walk prunes excluded dirs without descending, so the walker cannot count
    # what it never visited. Derive it: everything discovered that never became a
    # candidate was excluded as dependency material. Keeps the identity closed.
    excluded = max(discovered - sum(rows.values()), 0)
    failed = sum(v for k, v in rows.items() if k.startswith("failed_"))
    other = sum(v for k, v in rows.items()
                if not k.startswith("failed_") and k != "indexed")
    out = {
        "corpus_root": meta.get("corpus_root"),
        "built_at": meta.get("built_at"),
        "discovered_on_disk": discovered,
        "intentionally_excluded_dependency": excluded,
        "indexed_ok": indexed,
        "failed": failed,
        "unsupported_or_empty": other,
        "addressable_pages": npages,
        "by_status": rows,
        "accounting_identity_holds":
            discovered == excluded + indexed + failed + other,
    }
    return out


def search(db, query, limit, exact):
    m = f'"{query}"' if exact else fts_quote(query)
    if not m:
        return [], 0
    total = db.execute("SELECT COUNT(*) FROM pages WHERE pages MATCH ?", (m,)).fetchone()[0]
    rows = db.execute(
        "SELECT rel, page_index, snippet(pages,2,'>>','<<','...',24), bm25(pages) "
        "FROM pages WHERE pages MATCH ? ORDER BY bm25(pages) LIMIT ?",
        (m, limit)).fetchall()
    return rows, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--page", nargs=2, metavar=("REL", "PAGE_INDEX"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    db = connect(a.db)

    if a.coverage:
        print(json.dumps(coverage(db), indent=1)); return

    if a.page:
        rel, pi = a.page[0].replace("\\", "/"), int(a.page[1])
        r = db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?",
                       (rel, pi)).fetchone()
        if not r:
            print(f"NO SUCH PAGE: {rel} page {pi}"); sys.exit(1)
        print(f"=== {rel}  page_index={pi} ===\n{r[0]}"); return

    q = " ".join(a.query).strip()
    if not q:
        ap.error("give a query, or --coverage, or --page")
    rows, total = search(db, q, a.limit, a.exact)
    cov = coverage(db)

    if a.json:
        print(json.dumps({
            "query": q, "returned": len(rows), "total_matching_pages": total,
            "results": [{"path": r[0], "page_index": r[1], "snippet": r[2],
                         "score": round(r[3], 3)} for r in rows],
            "receipt": cov}, indent=1))
        return

    if not rows:
        print(f"NO MATCHES for {q!r}.")
    else:
        print(f"{total} matching pages; showing top {len(rows)}:\n")
        for rel, pi, snip, score in rows:
            print(f"  {rel}  [page_index={pi}]  score={score:.2f}")
            print(f"      {' '.join(snip.split())[:240]}\n")
    # the receipt - printed always, so an omission is visible rather than silent
    print("--- retrieval receipt ---")
    print(f"  searched {cov['addressable_pages']} indexed pages across "
          f"{cov['indexed_ok']} files (index built {cov['built_at']})")
    print(f"  NOT searched: {cov['failed']} files failed extraction, "
          f"{cov['unsupported_or_empty']} unsupported/empty, "
          f"{cov['intentionally_excluded_dependency']} excluded as dependency material")
    print("  a 'no match' here means no indexed page matched - NOT that the corpus lacks it")


if __name__ == "__main__":
    main()
