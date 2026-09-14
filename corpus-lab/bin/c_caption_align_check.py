#!/usr/bin/env python
"""c_caption_align_check.py - prove captions.f16.npy lines up with the captions table.

Phase 9.1.3 reads a document's caption vectors straight out of the npy instead of
re-embedding them. That is only safe if npy row i really is the i-th caption in
rowid order. This re-embeds 200 randomly chosen caption texts and checks cosine
against their stored rows.

Gate: >= 198 of 200 at cosine >= 0.98, else 1.3 does not ship.
Writes state/c_caption_align.json.
"""
import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shelf-dir", dest="shelf_dir", default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260915)
    ap.add_argument("--out", default=str(L.STATE / "c_caption_align.json"))
    a = ap.parse_args()

    import numpy as np
    from fastembed import TextEmbedding

    d = Path(a.shelf_dir)
    shelf = d / "shelf.db"
    npy = d / "captions.f16.npy"
    ids = d / "captions_ids.jsonl"
    for p in (shelf, npy, ids):
        if not p.exists():
            raise SystemExit("MISSING %s" % p)

    db = sqlite3.connect("file:%s?mode=ro" % shelf, uri=True)
    rows = db.execute(
        "SELECT rel, page_index, caption FROM captions ORDER BY rowid").fetchall()
    db.close()

    id_rows = []
    with open(ids, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                id_rows.append(json.loads(line))

    n_rows_match = len(rows) == len(id_rows)
    n_id_mismatch = 0
    if n_rows_match:
        for r, j in zip(rows, id_rows):
            if r[0] != j["rel"] or r[1] != j["page_index"]:
                n_id_mismatch += 1

    mat = np.load(str(npy), mmap_mode="r")
    rng = random.Random(a.seed)
    cand = [i for i, r in enumerate(rows) if (r[2] or "").strip()]
    rng.shuffle(cand)
    pick = cand[:a.n]

    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    texts = [rows[i][2] for i in pick]
    fresh = np.asarray(list(model.embed(texts)), dtype="float32")
    fn = np.linalg.norm(fresh, axis=1, keepdims=True)
    fn[fn == 0] = 1.0
    fresh = fresh / fn

    stored = np.asarray(mat[pick, :], dtype="float32")
    sn = np.linalg.norm(stored, axis=1, keepdims=True)
    sn[sn == 0] = 1.0
    stored = stored / sn

    cos = (fresh * stored).sum(axis=1)
    n_aligned = int((cos >= 0.98).sum())

    out = {"n": len(pick), "aligned_ge_0.98": n_aligned,
           "min_cosine": round(float(cos.min()), 4),
           "median_cosine": round(float(np.median(cos)), 4),
           "n_caption_rows": len(rows), "n_npy_id_rows": len(id_rows),
           "row_counts_match": n_rows_match,
           "n_id_position_mismatch": n_id_mismatch,
           "shelf_dir": a.shelf_dir,
           "verdict": "SHIP" if (n_aligned >= 198 and n_rows_match and n_id_mismatch == 0)
                      else "DO_NOT_SHIP"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0 if out["verdict"] == "SHIP" else 1


if __name__ == "__main__":
    sys.exit(main())
