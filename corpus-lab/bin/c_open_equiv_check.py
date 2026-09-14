#!/usr/bin/env python
"""c_open_equiv_check.py - prove the Phase 9.1.1 `open` speedup changed no bytes.

The old path scans `pages` by (rel, page_index). The new path looks the document's
contiguous rowid block up in the shelf's page_ranges cache and reads the row out of
the pages_content shadow table. Same row or the change is reverted.

Samples 300 (rel, page_index) pairs uniformly from page_ranges joined to real pages,
fetches the body both ways, and asserts byte-identical. Read-only on both databases.
Writes state/c_open_equiv.json.
"""
import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(L.STACKS / "s2_fts5" / "harness_15000.db"))
    ap.add_argument("--shelf-dir", dest="shelf_dir", default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20260915)
    ap.add_argument("--out", default=str(L.STATE / "c_open_equiv.json"))
    a = ap.parse_args()

    shelf_path = str(Path(a.shelf_dir) / "shelf.db")
    ctx = S.get_ctx(a.db, shelf_path, None)
    S._ensure_page_ranges(ctx)

    rows = ctx.shelf.execute(
        "SELECT rel, start_id, end_id FROM page_ranges").fetchall()
    rng = random.Random(a.seed)
    rng.shuffle(rows)

    n_checked = 0
    n_identical = 0
    n_old_missing = 0
    n_new_missing = 0
    mismatches = 0
    i = 0
    while n_checked < a.n and i < len(rows):
        rel, start_id, end_id = rows[i]
        i += 1
        # pick one real page of this document
        pick = ctx.db.execute(
            "SELECT c1 FROM pages_content WHERE id BETWEEN ? AND ? ORDER BY id",
            (start_id, end_id)).fetchall()
        if not pick:
            continue
        page_index = pick[rng.randrange(len(pick))][0]

        old = ctx.db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?",
                             (rel, page_index)).fetchone()
        new = ctx.db.execute(
            "SELECT c2 FROM pages_content WHERE id BETWEEN ? AND ? AND c1=?",
            (start_id, end_id, page_index)).fetchone()

        n_checked += 1
        if old is None:
            n_old_missing += 1
        if new is None:
            n_new_missing += 1
        if old is not None and new is not None and old[0] == new[0]:
            n_identical += 1
        else:
            mismatches += 1

    out = {"n": n_checked, "identical": n_identical,
           "old_missing": n_old_missing, "new_missing": n_new_missing,
           "mismatches": mismatches,
           "shelf_dir": a.shelf_dir, "seed": a.seed}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0 if (n_checked == a.n and n_identical == n_checked) else 1


if __name__ == "__main__":
    sys.exit(main())
