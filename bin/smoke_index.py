#!/usr/bin/env python
"""smoke_index.py - grid-run phase 4.4. Does the index actually find the canaries?

If a canary is missing from the index, that is a broken INSTRUMENT, not a stack
result -- every index-based stack would score a miss and the grid would read as
though retrieval failed. So this is checked once, up front.

Reads phrases from the manifest and queries the index for each. Prints ONLY
pass/fail plus the file and page that matched, never the phrase itself, so the
orchestrator can run it without loading the answer key into its own context.

  set CANARY_MANIFEST=<manifest.csv>
  set CORPUS_DB=<index.db>
  python bin\\smoke_index.py --corpus-root <root>
"""
import argparse
import csv
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L
import scoring


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.environ.get("CORPUS_DB"))
    ap.add_argument("--corpus-root", default=None)
    ap.add_argument("--show-paths", action="store_true",
                    help="print matched paths (only safe in a session that may see them)")
    a = ap.parse_args()
    if not a.db:
        sys.exit("no --db and no CORPUS_DB")
    db = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    rows = []
    with open(L.canary_manifest(), newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            p = (r.get("canary_phrase") or r.get("phrase") or "").strip()
            if not p:
                continue
            rel = (r.get("relative_path") or "").strip()
            if not rel and r.get("absolute_path") and a.corpus_root:
                try:
                    rel = str(Path(r["absolute_path"]).relative_to(Path(a.corpus_root)))
                except Exception:
                    rel = Path(r["absolute_path"]).name
            rows.append((p, scoring.norm_path(rel), r.get("format", ""),
                         r.get("page_index", "")))

    ok = miss = wrong = 0
    detail = []
    for phrase, rel, fmt, want_page in rows:
        hits = db.execute(
            "SELECT rel, page_index FROM pages WHERE pages MATCH ? "
            "ORDER BY bm25(pages) LIMIT 5", (f'"{phrase}"',)).fetchall()
        got = [(scoring.norm_path(h[0]), h[1]) for h in hits]
        if not got:
            miss += 1
            status = "NOT-IN-INDEX"
        elif any(g[0] == rel or g[0].endswith(rel) or rel.endswith(g[0]) for g in got):
            ok += 1
            status = "ok"
        else:
            wrong += 1
            status = "WRONG-FILE"
        page = got[0][1] if got else None
        detail.append({"format": fmt, "status": status, "n_hits": len(got),
                       "page_returned": page, "page_expected": want_page,
                       **({"rel": rel, "got": got[:2]} if a.show_paths else {})})
        line = f"  {status:<13} fmt={str(fmt)[:20]:<20} hits={len(got)} page={page}"
        if want_page not in ("", None):
            line += f" (manifest page_index={want_page})"
        print(line)

    print(f"\n{ok} found in the right file, {wrong} matched the wrong file, "
          f"{miss} absent from the index, of {len(rows)}")
    dest = L.STATE / f"smoke_index__{Path(a.db).stem}.json"
    dest.write_text(json.dumps(
        {"db": a.db, "ok": ok, "wrong_file": wrong, "missing": miss,
         "n": len(rows), "detail": detail}, indent=1), encoding="utf-8")
    print(f"written: {dest}")
    return 0 if (miss == 0 and wrong == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
