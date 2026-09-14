#!/usr/bin/env python
"""c_shelf_v2_gate.py - Gate S: did shelf v2 fix the structure without costing recall?

Phase 9.2.3. Runs the two structural counters that the three offline gates cannot
see, and collects their numbers into one verdict. The offline gates themselves are
run separately, with --shelf-dir, and their results read from their own state files
-- this script never re-implements a measurement that already has an instrument.

The pre-registered readings, written before the v2 build existed:

  document top-10, E1 config, dev        v1 10/17   requires >= 10/17
  document pool@100, dev                 v1 16/17   requires >= 16/17
  B2c pages, dev                         v1 52/57   requires >= 52/57
  ROUTE absence                          v1 11/11, 4/4   requires 11/11, 4/4
  gold evidence files hidden as non-primary copies   must NOT increase
  gold families that are fragments of a larger family  must FALL

Any improvement on the top-10 row is RECORDED, NOT CLAIMED: one dev set carries
+/-3 noise (F63).

This is a gate script: it may open the answer key, and it writes counts only.
Writes state/c_shelf_v2_gate.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_shelf as CSH  # noqa: E402
import c_offline_gate as G  # noqa: E402


def structural_counters(shelf_dir, db):
    """The two counts the recall gates cannot see, measured on one shelf.

    hidden_gold: a gold evidence file that the shelf collapsed into some other
    file's duplicate list, or marked non-primary, is a file `find` will not put
    in front of the model -- the (c) defect, counted on the questions that matter.

    fragment_gold_families: a gold family whose token list is a longer form of
    another family's is the (b) defect, counted the same way."""
    ctx = CSH.get_ctx(db, str(Path(shelf_dir) / "shelf.db"), None)
    _qs, answerable_ids, per_q, _counts = G.load_frozen(ctx)

    fam_count = {}
    for (fam,) in ctx.shelf.execute("SELECT family FROM docs"):
        fam_count[fam] = fam_count.get(fam, 0) + 1

    hidden_gold = 0
    n_gold_files = 0
    fragment_gold_fams = 0
    gold_fams = set()
    for qid in answerable_ids:
        for rel in per_q[qid]["resolved_rels"]:
            row = ctx.rel_to_row.get(rel)
            if row is None:
                continue
            n_gold_files += 1
            if not row["is_primary"]:
                hidden_gold += 1
            gold_fams.add(row["family"])

    for fam in gold_fams:
        toks = fam.split()
        if len(toks) < 4:
            continue
        for k in (1, 2, 3):
            if len(toks) - k < 3:
                break
            g = " ".join(toks[k:])
            if g in fam_count and g != fam and fam_count[g] >= fam_count.get(fam, 0):
                fragment_gold_fams += 1
                break

    # The crowding counter. The two gated counters above ask whether the GOLD
    # family is itself a fragment; on this dev set it never is. But section 1.3's
    # actual complaint is that fragments of OTHER publications occupy the top ten
    # -- the same fiscal-operations publication sitting at ranks 4, 5, 6 and 11 --
    # so the slots the model reads are spent on one publication four times over.
    # This measures that directly: of the top 40 families a dev `find` returns,
    # how many are a longer form of another family already in the same list.
    # RECORDED, NOT GATED.
    queries, _n = G.build_rewrites(answerable_ids, {qid: {"question": per_q[qid]["question"]}
                                                    for qid in answerable_ids}, L.STATE)
    dup_slots_top40 = 0
    n_lists = 0
    for qid in answerable_ids:
        res = CSH.do_find(ctx, queries[qid]["queries"], fusion="rrf",
                          caption_channel="lex")
        top = [f["family"] for f in res["families"][:40]]
        n_lists += 1
        seen = set(top)
        for fam in top:
            toks = fam.split()
            if len(toks) < 4:
                continue
            for k in (1, 2, 3):
                if len(toks) - k < 3:
                    break
                if " ".join(toks[k:]) in seen:
                    dup_slots_top40 += 1
                    break

    return {"n_gold_files_on_shelf": n_gold_files,
            "gold_files_hidden_as_non_primary": hidden_gold,
            "n_gold_families": len(gold_fams),
            "gold_families_that_are_fragments": fragment_gold_fams,
            "n_families_total": len(fam_count),
            "fragment_slots_in_top40_over_%d_dev_lists" % n_lists: dup_slots_top40}


def read_gate_outputs():
    """The three offline gates' own state files, as they stand right now."""
    out = {}
    try:
        d = json.loads((L.STATE / "c_caption_family_gate.json").read_text(encoding="utf-8"))
        out["caption_family_gate"] = d
    except Exception as e:
        out["caption_family_gate"] = {"error": str(e)[:120]}
    try:
        d = json.loads((L.STATE / "c_page_gate.json").read_text(encoding="utf-8"))
        cfg = d.get("row+caption_dense_first", {})
        out["b2c_pages"] = {"micro_hits": cfg.get("micro_hits"),
                            "micro_n": cfg.get("micro_n")}
    except Exception as e:
        out["b2c_pages"] = {"error": str(e)[:120]}
    try:
        d = json.loads((L.STATE / "c_route_gate.json").read_text(encoding="utf-8"))
        out["route"] = {"document_level": d.get("document_level"),
                        "identifier_level": d.get("identifier_level")}
    except Exception as e:
        out["route"] = {"error": str(e)[:120]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(L.STACKS / "s2_fts5" / "harness_15000.db"))
    ap.add_argument("--v1-shelf-dir", dest="v1", default=str(L.STACKS / "s7_shelf"))
    ap.add_argument("--v2-shelf-dir", dest="v2", default=str(L.STACKS / "s7_shelf_v2"))
    ap.add_argument("--stage", choices=["structure", "verdict"], default="verdict")
    ap.add_argument("--doc-top10", type=int, default=None,
                    help="v2 document top-10 from c_caption_gate.py --shelf-dir <v2>")
    ap.add_argument("--doc-pool100", type=int, default=None)
    ap.add_argument("--b2c", type=int, default=None)
    ap.add_argument("--route-doc", type=int, default=None)
    ap.add_argument("--route-ident", type=int, default=None)
    ap.add_argument("--out", default=str(L.STATE / "c_shelf_v2_gate.json"))
    a = ap.parse_args()

    rec = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "v1_shelf_dir": a.v1, "v2_shelf_dir": a.v2}
    rec["v1_structure"] = structural_counters(a.v1, a.db)
    rec["v2_structure"] = structural_counters(a.v2, a.db)

    if a.stage == "structure":
        Path(a.out).write_text(json.dumps(rec, indent=1), encoding="utf-8")
        print(json.dumps(rec, indent=1))
        return 0

    v1s, v2s = rec["v1_structure"], rec["v2_structure"]
    rows = [
        ("document_top10_dev", a.doc_top10, 10, "ge"),
        ("document_pool100_dev", a.doc_pool100, 16, "ge"),
        ("b2c_pages_dev", a.b2c, 52, "ge"),
        ("route_document_level", a.route_doc, 11, "eq"),
        ("route_identifier_level", a.route_ident, 4, "eq"),
    ]
    gate = {}
    for name, got, bar, how in rows:
        if got is None:
            gate[name] = {"got": None, "bar": bar, "pass": None,
                          "note": "not supplied -- run the gate with --shelf-dir and pass its number"}
            continue
        ok = (got >= bar) if how == "ge" else (got == bar)
        gate[name] = {"got": got, "bar": bar, "pass": ok}

    gate["gold_files_hidden_as_non_primary"] = {
        "v1": v1s["gold_files_hidden_as_non_primary"],
        "v2": v2s["gold_files_hidden_as_non_primary"],
        "rule": "must not increase",
        "pass": v2s["gold_files_hidden_as_non_primary"]
                <= v1s["gold_files_hidden_as_non_primary"]}
    gate["gold_families_that_are_fragments"] = {
        "v1": v1s["gold_families_that_are_fragments"],
        "v2": v2s["gold_families_that_are_fragments"],
        "rule": "must fall",
        "pass": v2s["gold_families_that_are_fragments"]
                < v1s["gold_families_that_are_fragments"]
                or v1s["gold_families_that_are_fragments"] == 0}

    decided = [v["pass"] for v in gate.values() if isinstance(v, dict) and v.get("pass") is not None]
    missing = [k for k, v in gate.items() if isinstance(v, dict) and v.get("pass") is None]
    rec["gate_s"] = gate
    rec["verdict"] = ("INCOMPLETE" if missing else ("PASS" if all(decided) else "STOP"))
    rec["rows_not_supplied"] = missing
    rec["note"] = ("Any improvement on the top-10 row is recorded, not claimed: "
                   "one dev set carries +/-3 noise (F63).")

    Path(a.out).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
