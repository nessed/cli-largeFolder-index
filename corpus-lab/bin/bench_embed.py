#!/usr/bin/env python
"""bench_embed.py - is S3 (FTS5 + local embeddings) actually buildable tonight?

S3's setup cost is a scored dimension, and it is also a feasibility gate: the
spec says to embed EVERY page from the FTS5 index with bge-small via fastembed
on CPU. The ra-ship index holds 614,150 pages. If the throughput implies a
multi-hour build, S3 cannot be built inside the night's budget and the honest
grid cell is "not run" WITH the measured rate behind it -- not a guess, and not
a quietly reduced scope.

Measures real pages from the real index, including the model download (which is
part of the setup cost the first time).

  python bin\\bench_embed.py --db <index.db> --n 512
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--n", type=int, default=512)
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--max-chars", type=int, default=2000)
    a = ap.parse_args()

    db = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    total_pages = db.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    rows = db.execute("SELECT body FROM pages LIMIT ?", (a.n,)).fetchall()
    texts = [(r[0] or "")[:a.max_chars] for r in rows]
    texts = [t for t in texts if t.strip()]
    print(f"index holds {total_pages:,} pages; benchmarking on {len(texts)}")

    t0 = time.monotonic()
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name=a.model)
    load_s = time.monotonic() - t0
    print(f"model load (incl. download if first run): {load_s:.1f}s")

    t1 = time.monotonic()
    n = sum(1 for _ in model.embed(texts, batch_size=32))
    embed_s = time.monotonic() - t1
    rate = n / embed_s if embed_s else 0
    eta_h = (total_pages / rate / 3600) if rate else None

    out = {
        "db": a.db, "model": a.model,
        "total_pages_in_index": total_pages,
        "benchmarked_pages": n,
        "model_load_s": round(load_s, 1),
        "embed_s": round(embed_s, 2),
        "pages_per_s": round(rate, 1),
        "projected_full_build_hours": round(eta_h, 2) if eta_h else None,
        "max_chars_per_page": a.max_chars,
    }
    print(json.dumps(out, indent=1))
    dest = L.STATE / f"bench_embed__{Path(a.db).stem}.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"written: {dest}")


if __name__ == "__main__":
    main()
