#!/usr/bin/env python
"""c_key_v2_build.py - a versioned key for the questions that have none.

Plan E Phase 2. `value_correct` read 5/17 for both models on the 2026-09-15
night. That was never a measurement of the models: 12 of the 17 dev answerable
questions carry no numeric `expected_answer.value` and no alternate with a
value, so `accepted_values()` returns an empty list and `value_correct` can
never be true for them. The split is a property of the key.

Those 12 are not unanswerable -- they are questions whose answer is a SERIES,
not a scalar. "How has development spending changed over the last decade" has
ten right numbers, not one. So this builds a second key that carries, for each
such question, the vector of values the generator actually printed at the pages
the key cites.

**Rule 4 and Plan E decision 6: the values are derived by this script from the
generator's own placement registry, never written by hand.** The author of this
file did not read a single value; the script reads `pdf_index/*.json`, matches
on `series_id` and fiscal year, and writes what it finds.

**`answer_key.json` is never edited** (rule 17). This writes a NEW file with a
date in its name and records the base key's sha256, so any number scored against
it can be traced to exactly this derivation.

  python c_key_v2_build.py [--out <path>] [--dry-run]

Writes _private/harness_keys/answer_key_v2_2026-09-16.json
"""
import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import scoring as SC  # noqa: E402
import c_score_live_v2 as V2  # noqa: E402

DEFAULT_OUT = "answer_key_v2_2026-09-16.json"

# Question families whose answer is prose, not a number or a series. A key
# cannot score these by value and pretending otherwise would manufacture a
# denominator -- they are marked unscorable WITH THE REASON, which is the honest
# form of "we did not measure this".
TEXT_QUESTION_TYPES = {"relationship", "stale_document", "stale_doc",
                       "stale", "absence"}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_placement_tables():
    """{series_id: [table, ...]} and {(norm_path, page_index): [table, ...]}.

    One pass over the generator's per-document table index. Each table carries
    `cells`: {fiscal_year: value} -- the generator's record of what it printed.
    """
    by_series = defaultdict(list)
    by_page = defaultdict(list)
    files = sorted((L.HARNESS_KEYS / "pdf_index").glob("*.json"))
    n_tables = 0
    for f in files:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        path = SC.norm_path(rec.get("path") or "")
        for t in rec.get("tables") or []:
            if not isinstance(t.get("cells"), dict):
                continue
            n_tables += 1
            t = dict(t)
            t["_path"] = path
            t["_source_file"] = f.name
            if t.get("series_id"):
                by_series[t["series_id"]].append(t)
            if t.get("page_index") is not None:
                by_page[(path, int(t["page_index"]))].append(t)
    return by_series, by_page, {"n_index_files": len(files), "n_tables": n_tables}


def _num(v):
    return V2._as_float(v)


def derive_vector(q, by_series, by_page):
    """The values the generator printed for this question's cited cells.

    Keyed `<series_id>|<fy>` so a multi-branch question, which names several
    series, gets one entry per branch and per year rather than colliding on the
    year alone. Each entry is the list of DISTINCT values any vintage prints for
    that cell, so an answer quoting a revised figure is not marked wrong for
    quoting a different edition -- the same principle as the equivalence column.
    """
    vector = {}
    tight_vector = {}
    provenance = []
    for e in q.get("evidence_addresses") or []:
        sid, fy = e.get("series_id"), e.get("fy")
        path = SC.norm_path(e.get("path") or "")
        page = e.get("page_index")

        cands = []
        if sid:
            cands = by_series.get(sid, [])
        elif page is not None:
            cands = by_page.get((path, int(page)), [])
        if not cands:
            continue
        # The permissive set is every vintage of the series anywhere in the
        # corpus, which is what Plan E 2.1 specifies. It is worth knowing how
        # much that costs: a cell with 16 accepted values is close to free to
        # satisfy. So the tighter set -- only the vintages this question's own
        # evidence addresses name -- is recorded beside it.
        tight = [t for t in cands
                 if e.get("vintage_id") and t.get("vintage_id") == e.get("vintage_id")]
        if not tight and page is not None:
            tight = [t for t in cands
                     if t.get("_path") == path and t.get("page_index") == page]

        if fy:
            wanted = [fy]
        else:
            # no year named: take every year the cited page's table prints
            wanted = sorted({k for t in by_page.get((path, int(page)), [])
                             for k in (t.get("cells") or {})}) if page is not None else []

        for y in wanted:
            vals = []
            srcs = set()
            for t in cands:
                v = _num((t.get("cells") or {}).get(y))
                if v is None:
                    continue
                if v not in vals:
                    vals.append(v)
                srcs.add(t["_source_file"])
            if not vals:
                continue
            tvals = []
            for t in tight:
                v = _num((t.get("cells") or {}).get(y))
                if v is not None and v not in tvals:
                    tvals.append(v)

            k = "%s|%s" % (sid or "page%s" % page, y)
            if k in vector:
                for v in vals:
                    if v not in vector[k]:
                        vector[k].append(v)
                for v in tvals:
                    if v not in tight_vector.setdefault(k, []):
                        tight_vector[k].append(v)
            else:
                vector[k] = vals
                tight_vector[k] = tvals
            provenance.append({"cell": k, "n_values_any_vintage": len(vals),
                               "n_values_cited_vintage": len(tvals),
                               "n_source_index_files": len(srcs)})
    return vector, tight_vector, provenance


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv[1:])

    base_path = L.ANSWER_KEY
    base_sha = sha256(base_path)
    key = json.loads(base_path.read_text(encoding="utf-8"))
    qs = key["questions"]
    qs_by_id = {q["q_id"]: q for q in qs}

    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    frozen = set(sample["q_ids"])

    by_series, by_page, meta = load_placement_tables()

    type_counts = defaultdict(int)
    n_unkeyed = n_vectored = n_text = n_empty = 0
    out_questions = []
    audit = []

    for q in qs:
        q2 = dict(q)                       # original fields, byte-for-byte
        accepted = V2.accepted_values(q)
        if accepted:
            q2["value_scorable"] = True
            q2["value_source"] = "expected_answer.value (key v1)"
            out_questions.append(q2)
            continue

        n_unkeyed += 1
        qtype = (q.get("type") or "").lower()
        if q["q_id"] in frozen:
            type_counts[qtype] += 1

        if qtype in TEXT_QUESTION_TYPES:
            q2["value_scorable"] = False
            q2["value_unscorable_reason"] = "text question"
            n_text += 1
            out_questions.append(q2)
            continue

        vector, tight, prov = derive_vector(q, by_series, by_page)
        if vector:
            q2["expected_vector"] = vector
            q2["expected_vector_cited_vintages"] = tight
            q2["n_values_per_cell_any_vintage"] = sorted(
                len(v) for v in vector.values())
            q2["n_values_per_cell_cited_vintage"] = sorted(
                len(v) for v in tight.values())
            q2["expected_vector_keying"] = "<series_id>|<fiscal_year>"
            q2["expected_vector_derivation"] = (
                "values read from the generator's pdf_index `cells` for the "
                "series_id and fiscal year of each evidence address; every "
                "distinct value any vintage prints is accepted")
            q2["value_scorable"] = False        # still not a SCALAR question
            q2["vector_scorable"] = True
            n_vectored += 1
            if q["q_id"] in frozen:
                audit.append({"q_id": q["q_id"], "type": qtype,
                              "n_cells": len(vector),
                              "max_values_any": max(len(v) for v in vector.values()),
                              "max_values_cited": max([len(v) for v in tight.values()]
                                                      or [0]),
                              "provenance": prov})
        else:
            q2["value_scorable"] = False
            q2["value_unscorable_reason"] = (
                "no numeric value in the key and no generator cell matched this "
                "question's evidence addresses")
            n_empty += 1
        out_questions.append(q2)

    out = {
        "key_version": "v2",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_key": str(base_path.name),
        "base_key_sha256": base_sha,
        "derived_from": {
            "source": "harness_keys/pdf_index/*.json (the generator's "
                      "per-document table placement records)",
            "n_index_files": meta["n_index_files"],
            "n_tables_with_cells": meta["n_tables"],
            "builder": "corpus-lab/bin/c_key_v2_build.py",
            "builder_sha256": sha256(__file__),
        },
        "what_changed": (
            "Every question from the base key, unchanged, plus three new fields: "
            "value_scorable, and for series questions expected_vector and "
            "vector_scorable. No value was written by hand; no question text, "
            "evidence address or existing expected_answer was altered."),
        "counts": {
            "n_questions": len(out_questions),
            "n_unkeyed_in_base": n_unkeyed,
            "n_given_a_vector": n_vectored,
            "n_text_questions": n_text,
            "n_unkeyed_and_underivable": n_empty,
        },
        "frozen20_unkeyed_by_type": dict(type_counts),
        "questions": out_questions,
    }

    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("questions",)}, indent=1))
    print("frozen-20 audit (cell counts only):")
    for r in audit:
        print("  %-8s %-16s %2d cells, up to %2d accepted values/cell (%d at the cited vintage)"
              % (r["q_id"], r["type"], r["n_cells"], r["max_values_any"],
                 r["max_values_cited"]))

    if a.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    dest = Path(a.out) if a.out else (L.HARNESS_KEYS / DEFAULT_OUT)
    if dest.exists():
        raise SystemExit("REFUSED: %s already exists. Rule 17: a new key is a new "
                         "file; keys are never edited in place." % dest)
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote %s" % dest)
    print("key v2 sha256: %s" % sha256(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
