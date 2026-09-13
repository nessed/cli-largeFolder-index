#!/usr/bin/env python
"""c_card_sample.py - build a 100-card sample of shelf.db for human visual
review, per Ali's explicit request after Gate 1 came back GATE1_FAILED_STRUCTURAL:
- the flagged 16-"edition" paper ("effective protection in the automobile
  sector...", the sanity-probe failure) must be represented,
- copy-heavy families must be covered (both the intended kind -- one real
  publication with many partial-copy duplicates, e.g. Pakistan Economic
  Survey -- and the defect kind -- a paper replicated under many locations
  with little/no fiscal-year structure, inflating "editions"/primaries),
- plus a broad stratified sample for general coverage.

Writes state/c_card_sample_100.csv (one row per sampled doc, with a
`sample_reason` column) and prints a short summary. Read-only against shelf.db.
"""
import csv
import json
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

SHELF = L.STACKS / "s7_shelf" / "shelf.db"
OUT = L.STATE / "c_card_sample_100.csv"

TARGET_FAMILY = "effective protection in the automobile sector a"  # the sanity-probe failure
COPY_HEAVY_GOOD = ["pakistan economic survey {fy}", "household integrated economic survey {fy}"]
COPY_HEAVY_DEFECT = [
    "series id label fiscal year value unit vintage label obs status source doc",
    "education expenditure and learning outcomes",
    "public debt sustainability under exchange rate",
    "agricultural support prices and cropping",
]


def fetch(db, family, limit=None, seed=None):
    rows = db.execute(
        "SELECT rel, title, title_source, family, fy_primary, n_pages, is_primary, sha256 "
        "FROM docs WHERE family=? ORDER BY fy_primary IS NULL, fy_primary, is_primary DESC, rel",
        (family,)).fetchall()
    if limit and len(rows) > limit:
        if seed is not None:
            rng = random.Random(seed)
            primaries = [r for r in rows if r[6]]
            copies = [r for r in rows if not r[6]]
            keep = primaries[:max(1, limit // 2)]
            remaining = limit - len(keep)
            keep += rng.sample(copies, min(remaining, len(copies)))
            rows = keep
        else:
            rows = rows[:limit]
    return rows


def main():
    db = sqlite3.connect(f"file:{SHELF}?mode=ro", uri=True)
    picked = {}  # rel -> (row, reason)

    for rel, title, tsrc, fam, fy, npages, isp, sha in fetch(db, TARGET_FAMILY, limit=20, seed=1):
        picked[rel] = ((rel, title, tsrc, fam, fy, npages, isp, sha), "target_family_16ed_sanity_fail")

    for fam in COPY_HEAVY_GOOD:
        for rel, title, tsrc, f, fy, npages, isp, sha in fetch(db, fam, limit=8, seed=2):
            if rel not in picked:
                picked[rel] = ((rel, title, tsrc, f, fy, npages, isp, sha), f"copy_heavy_good:{fam}")

    for fam in COPY_HEAVY_DEFECT:
        for rel, title, tsrc, f, fy, npages, isp, sha in fetch(db, fam, limit=8, seed=3):
            if rel not in picked:
                picked[rel] = ((rel, title, tsrc, f, fy, npages, isp, sha), f"copy_heavy_defect:{fam}")

    all_rels = [r[0] for r in db.execute("SELECT rel FROM docs")]
    rng = random.Random(42)
    rng.shuffle(all_rels)
    for rel in all_rels:
        if len(picked) >= 100:
            break
        if rel in picked:
            continue
        row = db.execute(
            "SELECT rel, title, title_source, family, fy_primary, n_pages, is_primary, sha256 "
            "FROM docs WHERE rel=?", (rel,)).fetchone()
        picked[rel] = (row, "stratified_random")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rel", "title", "title_source", "family", "fy_primary",
                    "n_pages", "is_primary", "sha256_short", "sample_reason"])
        for row, reason in picked.values():
            rel, title, tsrc, fam, fy, npages, isp, sha = row
            w.writerow([rel, title, tsrc, fam, fy, npages, isp, (sha or "")[:12], reason])

    by_reason = {}
    for _row, reason in picked.values():
        key = reason.split(":")[0]
        by_reason[key] = by_reason.get(key, 0) + 1
    print(f"wrote {len(picked)} rows to {OUT}")
    print(json.dumps(by_reason, indent=1))


if __name__ == "__main__":
    main()
