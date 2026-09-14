#!/usr/bin/env python
"""c_inside_equiv_check.py - does the stored-vector `inside` return the same pages?

Phase 9.1.3 stopped re-embedding a document's captions on every `inside` and reads
them out of captions.f16.npy instead. The vectors are stored in float16, so a tie
can move; the pre-registered gate is that the top-5 page set is IDENTICAL on at
least 54 of the 57 dev addresses' documents.

This is a gate script, so it may open the answer key (rule 4). It records counts
only -- no path, page label, title or value ever leaves here.

  python c_inside_equiv_check.py
Writes state/c_inside_equiv.json.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402


def top5_new(ctx, rel, terms):
    res = CSH.do_inside(ctx, rel, terms, k=20, caption_channel="dense_first")
    return [h["page_index"] for h in res["hits"][:5]]


def top5_old(ctx, rel, terms):
    """Force the pre-9.1.3 path by hiding the vector store from this ctx."""
    saved = getattr(ctx, "_capvec", None)
    ctx._capvec = (None, None)
    try:
        res = CSH.do_inside(ctx, rel, terms, k=20, caption_channel="dense_first")
        return [h["page_index"] for h in res["hits"][:5]]
    finally:
        if saved is None:
            if hasattr(ctx, "_capvec"):
                del ctx._capvec
        else:
            ctx._capvec = saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(L.STACKS / "s2_fts5" / "harness_15000.db"))
    ap.add_argument("--shelf-dir", dest="shelf_dir", default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--out", default=str(L.STATE / "c_inside_equiv.json"))
    a = ap.parse_args()

    ctx = CSH.get_ctx(a.db, str(Path(a.shelf_dir) / "shelf.db"), None)
    _qs, answerable_ids, per_q, _counts = G.load_frozen(ctx)

    n_addr = 0
    n_same_set = 0
    n_same_order = 0
    n_fell_back = 0
    for qid in answerable_ids:
        pq = per_q[qid]
        terms = G.row_words_from_question(pq["question"])
        for addr in pq["page_addresses"]:
            rel = addr["rel"]
            new = top5_new(ctx, rel, terms)
            old = top5_old(ctx, rel, terms)
            n_addr += 1
            if set(new) == set(old):
                n_same_set += 1
            if new == old:
                n_same_order += 1
            if CSH._stored_caption_vectors(
                    ctx, rel,
                    ctx.shelf.execute(
                        "SELECT page_index, caption FROM captions WHERE rel=? ORDER BY rowid",
                        (rel,)).fetchall()) is None:
                n_fell_back += 1

    out = {"n_addresses": n_addr,
           "top5_set_identical": n_same_set,
           "top5_order_identical": n_same_order,
           "n_documents_without_stored_vectors": n_fell_back,
           "gate_requires_set_identical_ge": 54,
           "shelf_dir": a.shelf_dir,
           "verdict": "SHIP" if n_same_set >= 54 else "REVERT_1.3"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0 if out["verdict"] == "SHIP" else 1


if __name__ == "__main__":
    sys.exit(main())
