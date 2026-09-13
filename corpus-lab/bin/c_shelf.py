#!/usr/bin/env python
"""c_shelf.py - build C, Stage 2. The front door onto the shelf built by
c_shelf_build.py: find, have, inside, tables, series, copies, exact, open,
note, notes, coverage, register.

Every subcommand accepts --db PATH --shelf DIR; otherwise the corpus root is
resolved by walking up from the cwd to a key in the shared registry
(%LOCALAPPDATA%\\retrieval-lab\\roots.json). See plans_fable/C_SHELF_FIRST_BUILD.md
Stage 2 for the exact command grammar and output format.

Importable in-process (c_offline_gate.py does this): every subcommand has a
`do_*` function returning a plain dict; the CLI's `main()` only formats and
prints. DB is opened read-only; shelf.db is ours and opened read-write so a
one-time page-range cache can be built into it on first use.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
from corpus_search import content_words, coverage as _cs_coverage  # noqa: E402

REG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home())) ) / "retrieval-lab" / "roots.json"
FY_RE = re.compile(r"\b(20[0-3]\d-\d\d)\b")

_MODEL = None  # module-level singleton; loaded only when `find` needs vectors


def _model():
    global _MODEL
    if _MODEL is None:
        from fastembed import TextEmbedding
        _MODEL = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _MODEL


# --------------------------------------------------------------------- #
# registry / root resolution
# --------------------------------------------------------------------- #
def _norm_root_key(p):
    return str(Path(p).resolve()).replace("\\", "/").lower()


def _load_registry():
    if REG_PATH.exists():
        try:
            return json.loads(REG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_registry(reg):
    REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    REG_PATH.write_text(json.dumps(reg, indent=1), encoding="utf-8")


def do_register(root, db, shelf):
    reg = _load_registry()
    key = _norm_root_key(root)
    entry = dict(reg.get(key, {}))
    entry["root"] = str(Path(root).resolve()).replace("\\", "/")
    entry["db"] = str(Path(db).resolve())
    entry["shelf"] = str(Path(shelf).resolve())
    reg[key] = entry
    _save_registry(reg)
    return {"ok": True, "key": key, "entry": entry}


def _resolve(explicit_db, explicit_shelf):
    if explicit_db and explicit_shelf:
        return None, explicit_db, explicit_shelf
    reg = _load_registry()
    cur = Path.cwd().resolve()
    while True:
        key = _norm_root_key(cur)
        if key in reg:
            e = reg[key]
            return cur, explicit_db or e.get("db"), explicit_shelf or e.get("shelf")
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    print("NO_REGISTERED_ROOT", file=sys.stderr)
    sys.exit(2)


def _corpus_key(root_key_str):
    return hashlib.sha256(root_key_str.encode("utf-8")).hexdigest()[:12]


def _notes_dir(root):
    key = _norm_root_key(root) if root else "no-root"
    ck = _corpus_key(key)
    d = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "retrieval-lab" / "notes" / ck
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------- #
# context: open connections once per process
# --------------------------------------------------------------------- #
class Ctx:
    def __init__(self, db_path, shelf_path, root=None):
        self.db_path = db_path
        self.shelf_path = shelf_path
        self.root = root
        self.db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.shelf = sqlite3.connect(str(shelf_path))
        self.rel_to_family = {}
        self.rel_to_row = {}
        for row in self.shelf.execute(
            "SELECT rel, title, family, fy_primary, n_pages, size, sha256, "
            "is_primary, edition_key, n_dupes, dupes FROM docs"
        ):
            (rel, title, family, fy_primary, n_pages, size, sha256,
             is_primary, edition_key, n_dupes, dupes) = row
            self.rel_to_family[rel] = family
            self.rel_to_row[rel] = {
                "rel": rel, "title": title, "family": family, "fy_primary": fy_primary,
                "n_pages": n_pages, "size": size, "sha256": sha256,
                "is_primary": is_primary, "edition_key": edition_key,
                "n_dupes": n_dupes, "dupes": json.loads(dupes) if dupes else [],
            }
        # `cards.rel` is FTS5 UNINDEXED -- a `WHERE rel=?` lookup is a full-table
        # scan every time. `find` used to do one such lookup per ranked family
        # (up to a couple hundred), which measured at ~14s warm on "budget".
        # Load once instead, and precompute the two other per-family/per-edition
        # groupings `find` needs so it never does an O(n_docs) scan per family.
        self.rel_to_catalog = dict(self.shelf.execute("SELECT rel, catalog FROM cards"))
        self.family_to_rels = {}
        self.edition_primary = {}  # edition_key -> primary rel
        for rel, row in self.rel_to_row.items():
            self.family_to_rels.setdefault(row["family"], []).append(rel)
            if row["is_primary"]:
                self.edition_primary[row["edition_key"]] = rel

    def coverage(self):
        # corpus_search.coverage() does SELECT COUNT(*) FROM pages -- a full
        # scan of the 1.2M-row FTS5 table every call. The corpus is read-only
        # for the life of this process, so compute it once.
        if not hasattr(self, "_coverage_cache"):
            self._coverage_cache = _cs_coverage(self.db)
        return self._coverage_cache


_ctx_cache = {}


def get_ctx(db_path, shelf_path, root=None):
    key = (str(db_path), str(shelf_path))
    if key not in _ctx_cache:
        _ctx_cache[key] = Ctx(db_path, shelf_path, root)
    return _ctx_cache[key]


# --------------------------------------------------------------------- #
# page-range cache, built once into shelf.db, so `inside`/`series` never
# need a full scan of the 1.2M-row page table (that scan costs ~4-5s per
# lookup without it -- see corpus_search.py; the pages_content shadow
# table stores one file's pages as a contiguous rowid block, so a single
# one-time sequential pass records (rel -> start_id, end_id) once).
# --------------------------------------------------------------------- #
def _ensure_page_ranges(ctx):
    has = ctx.shelf.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='page_ranges'"
    ).fetchone()
    if has:
        return
    print("(building page-range cache, one-time, ~1 min)", file=sys.stderr)
    ctx.shelf.execute("CREATE TABLE page_ranges(rel TEXT PRIMARY KEY, start_id INTEGER, end_id INTEGER)")
    cur_rel, start_id, last_id = None, None, None
    rows_out = []
    for id_, c0 in ctx.db.execute("SELECT id, c0 FROM pages_content ORDER BY id"):
        if c0 != cur_rel:
            if cur_rel is not None:
                rows_out.append((cur_rel, start_id, last_id))
            cur_rel, start_id = c0, id_
        last_id = id_
    if cur_rel is not None:
        rows_out.append((cur_rel, start_id, last_id))
    ctx.shelf.executemany("INSERT INTO page_ranges VALUES (?,?,?)", rows_out)
    ctx.shelf.commit()


def _load_doc_pages(ctx, rel):
    _ensure_page_ranges(ctx)
    row = ctx.shelf.execute("SELECT start_id, end_id FROM page_ranges WHERE rel=?", (rel,)).fetchone()
    if not row:
        return []
    start_id, end_id = row
    return ctx.db.execute(
        "SELECT c1, c2 FROM pages_content WHERE id BETWEEN ? AND ? ORDER BY id",
        (start_id, end_id)).fetchall()


# --------------------------------------------------------------------- #
# find
# --------------------------------------------------------------------- #
def _lex_search(ctx, query, limit):
    words = content_words(query)
    if not words:
        return []
    m = " OR ".join(f'"{w}"' for w in words)
    try:
        rows = ctx.shelf.execute(
            "SELECT rel FROM cards WHERE cards MATCH ? "
            "ORDER BY bm25(cards, 3.0, 3.0, 2.0, 1.0) LIMIT ?", (m, limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


def _vec_search(ctx, query, limit):
    import numpy as np
    if not hasattr(ctx, "_vecs"):
        ctx._vecs = np.load(Path(ctx.shelf_path).parent / "cards.f16.npy").astype("float32")
        ctx._vec_ids = [json.loads(l)["rel"] for l in
                        (Path(ctx.shelf_path).parent / "cards_ids.jsonl").read_text(encoding="utf-8").splitlines()]
    qv = np.asarray(next(iter(_model().embed([query]))), dtype="float32")
    n = np.linalg.norm(qv)
    if n > 0:
        qv = qv / n
    scores = ctx._vecs @ qv
    top = np.argsort(-scores)[:limit]
    return [ctx._vec_ids[i] for i in top]


def _rrf_fuse(rank_lists, k=60):
    from collections import defaultdict
    scores = defaultdict(float)
    for lst in rank_lists:
        for rank, rel in enumerate(lst, start=1):
            scores[rel] += 1.0 / (k + rank)
    return scores


def _family_words(family):
    return re.sub(r"\s+", " ", family.replace("{fy}", " ")).strip()


def _why_lines(catalog, title, qwords):
    lines = [l.strip() for l in (catalog or "").splitlines() if l.strip()]
    qw = set(qwords)
    scored = []
    for l in lines:
        overlap = len(set(content_words(l)) & qw)
        if overlap > 0:
            scored.append((overlap, l))
    scored.sort(key=lambda x: -x[0])
    top = [l for _, l in scored[:2]]
    return top if top else [title]


def _editions_for_family(ctx, family):
    rows = [ctx.rel_to_row[rel] for rel in ctx.family_to_rels.get(family, ())]
    primaries_fy = sorted([r for r in rows if r["is_primary"] and r["fy_primary"]],
                           key=lambda r: r["fy_primary"])
    n_copies = sum(1 for r in rows if not r["is_primary"])
    if primaries_fy:
        return primaries_fy, n_copies, "fy"
    singletons = [r for r in rows if r["is_primary"]]
    return singletons, n_copies, "singleton"


def do_find(ctx, queries, pool=200):
    """Returns ALL fused families, ranked best-first (not sliced to any k) --
    the CLI printer shows the top --k, the offline gate checks rank within
    whatever depth it needs (measurement uses 50)."""
    all_lists = []
    for q in queries:
        all_lists.append(_lex_search(ctx, q, pool))
        all_lists.append(_vec_search(ctx, q, pool))
    doc_scores = _rrf_fuse(all_lists, k=60)

    fam_scores, fam_best_doc = {}, {}
    for rel, score in doc_scores.items():
        fam = ctx.rel_to_family.get(rel)
        if not fam:
            continue
        if fam not in fam_scores or score > fam_scores[fam]:
            fam_scores[fam] = score
            fam_best_doc[fam] = rel

    ranked = sorted(fam_scores.items(), key=lambda x: -x[1])
    qwords = []
    for q in queries:
        qwords.extend(content_words(q))

    families_out = []
    for fam, score in ranked:
        best_rel = fam_best_doc[fam]
        best_row = ctx.rel_to_row[best_rel]
        catalog = ctx.rel_to_catalog.get(best_rel, "")
        editions, n_copies, kind = _editions_for_family(ctx, fam)
        ek = best_row["edition_key"]
        primary_rel = best_rel if best_row["is_primary"] else ctx.edition_primary.get(ek, best_rel)
        families_out.append({
            "family": fam, "score": score,
            "editions": [{"fy": r.get("fy_primary"), "rel": r["rel"], "n_pages": r["n_pages"]}
                         for r in editions],
            "n_editions": len(editions), "n_copies_hidden": n_copies, "kind": kind,
            "why": _why_lines(catalog, best_row["title"], qwords),
            "best_rel": best_rel, "primary_rel": primary_rel,
            "evidence_rels": [r["rel"] for r in editions] + [best_rel],
        })

    return {
        "families": families_out,
        "receipt": {"queries": len(queries), "lex": pool, "vec": pool,
                    "families": len(fam_scores), "docs_considered": len(doc_scores)},
        "coverage": ctx.coverage(),
        "qwords": qwords,
    }


def _print_find(res, k):
    for i, f in enumerate(res["families"][:k], start=1):
        print(f"#{i}  family: {f['family']}")
        eds = f["editions"]
        parts = [f"{e['fy'] or Path(e['rel']).name}*({e['n_pages']}p)" for e in eds]
        if len(parts) > 6:
            shown = parts[:3] + ["…"] + parts[-2:]
        else:
            shown = parts
        print(f"    editions: {' '.join(shown)}   "
              f"[{f['n_editions']} editions, {f['n_copies_hidden']} copies not shown]")
        why = " | ".join(f'"{w}"' for w in f["why"])
        print(f"    why: {why}")
        terms = " ".join(res["qwords"][:6])
        fam_words = _family_words(f["family"])
        print(f'    open with: inside "{f["primary_rel"]}" "{terms}"   or   '
              f'series "<row words>" --family "{fam_words}"')
    r = res["receipt"]
    print(f"RECEIPT queries={r['queries']} lex=[{r['lex']}] vec=[{r['vec']}] "
          f"families={r['families']} docs_considered={r['docs_considered']}")
    _print_coverage(res["coverage"])


def _print_coverage(cov):
    by = cov["by_status"]
    failed = by.get("failed_encrypted", 0) + by.get("failed_parser", 0)
    print(f"COVERAGE indexed={by.get('indexed', 0)} "
          f"image_only_no_text={by.get('image_only_no_text', 0)} "
          f"failed={failed} unsupported={by.get('unsupported_type', 0)} "
          f"pages={cov['addressable_pages']}")


# --------------------------------------------------------------------- #
# have
# --------------------------------------------------------------------- #
def _unreadable_matching_name(ctx, words):
    if not words:
        return 0
    lw = [w.lower() for w in words]
    n = 0
    for (rel,) in ctx.db.execute(
        "SELECT rel FROM files WHERE status='image_only_no_text' OR status LIKE 'failed_%'"
    ):
        name = Path(rel).name.lower()
        if all(w in name for w in lw):
            n += 1
    return n


def do_have(ctx, words_str, fy=None):
    words = content_words(words_str)
    unreadable = _unreadable_matching_name(ctx, words)
    if not words:
        return {"families": [], "no_family_matches": True, "words": words_str,
                "unreadable": unreadable}

    # Tiered, most-precise-first (same cascade shape as corpus_search.py):
    # a "have" lookup is a catalog lookup for a NAMED publication, so an exact
    # phrase match confined to the title column is tried before falling back
    # to a bag-of-words score across title+family. Restricting the phrase tier
    # to title-only matters: this corpus also holds audit/log files whose body
    # is a JSON blob echoing a real file's path (e.g. a "profile" record
    # naming the path it processed), and those get long, noisy `family` text
    # that out-scores a real short title on raw bm25 term frequency if
    # `family` is included in this first tier.
    rows = []
    phrase = words_str.strip().replace('"', '""')
    if phrase:
        m_phrase = '{title} : "' + phrase + '"'
        try:
            rows = ctx.shelf.execute(
                "SELECT rel FROM cards WHERE cards MATCH ? "
                "ORDER BY bm25(cards, 3.0, 0, 0, 0) LIMIT 200", (m_phrase,)).fetchall()
        except sqlite3.OperationalError:
            rows = []
    if not rows:
        m_and = "{title family} : (" + " ".join(f'"{w}"' for w in words) + ")"
        try:
            rows = ctx.shelf.execute(
                "SELECT rel FROM cards WHERE cards MATCH ? "
                "ORDER BY bm25(cards, 3.0, 3.0, 2.0, 1.0) LIMIT 200", (m_and,)).fetchall()
        except sqlite3.OperationalError:
            rows = []
    if not rows:
        m_or = "{title family} : (" + " OR ".join(f'"{w}"' for w in words) + ")"
        try:
            rows = ctx.shelf.execute(
                "SELECT rel FROM cards WHERE cards MATCH ? "
                "ORDER BY bm25(cards, 3.0, 3.0, 2.0, 1.0) LIMIT 200", (m_or,)).fetchall()
        except sqlite3.OperationalError:
            rows = []
    fam_order = []
    seen = set()
    for (rel,) in rows:
        fam = ctx.rel_to_family.get(rel)
        if fam and fam not in seen:
            seen.add(fam)
            fam_order.append(fam)
    if not fam_order:
        return {"families": [], "no_family_matches": True, "words": words_str,
                "unreadable": unreadable}

    families_out = []
    for fam in fam_order[:8]:
        fy_list = sorted({r["fy_primary"] for r in ctx.rel_to_row.values()
                           if r["family"] == fam and r["is_primary"] and r["fy_primary"]})
        families_out.append({"family": fam, "fy_list": fy_list})

    result = {"families": families_out, "no_family_matches": False,
              "words": words_str, "unreadable": unreadable}

    if fy is not None:
        best = families_out[0]
        fy_list = best["fy_list"]
        if fy in fy_list:
            row = next(r for r in ctx.rel_to_row.values()
                       if r["family"] == best["family"] and r["fy_primary"] == fy and r["is_primary"])
            result["fy_check"] = {"status": "EDITION_PRESENT", "fy": fy,
                                   "rel": row["rel"], "n_pages": row["n_pages"]}
        else:
            before = max((f for f in fy_list if f < fy), default=None)
            after = min((f for f in fy_list if f > fy), default=None)
            result["fy_check"] = {"status": "NO_EDITION_FOR", "fy": fy,
                                   "family": best["family"],
                                   "nearest_before": before, "nearest_after": after,
                                   "fy_list": fy_list}
    return result


def _print_have(res):
    if res["no_family_matches"]:
        print(f'NO_FAMILY_MATCHES "{res["words"]}"')
        print(f"UNREADABLE_FILES_WITH_MATCHING_NAME={res['unreadable']}")
        return
    for f in res["families"]:
        print(f"family: {f['family']}   fy_list: {f['fy_list']}")
    if "fy_check" in res:
        c = res["fy_check"]
        if c["status"] == "EDITION_PRESENT":
            print(f"EDITION_PRESENT {c['fy']} {c['rel']} ({c['n_pages']}p)")
        else:
            print(f'NO_EDITION_FOR {c["fy"]} in "{c["family"]}"; '
                  f'nearest: {c["nearest_before"]}, {c["nearest_after"]}; '
                  f'editions held: {c["fy_list"]}')
    print(f"UNREADABLE_FILES_WITH_MATCHING_NAME={res['unreadable']}")


# --------------------------------------------------------------------- #
# inside
# --------------------------------------------------------------------- #
def _best_line(body, words):
    lines = body.splitlines()
    best_line, best_n = "", -1
    lw = [w.lower() for w in words]
    for line in lines:
        low = line.lower()
        n = sum(1 for w in lw if w in low)
        if n > best_n:
            best_n, best_line = n, line
    return " ".join(best_line.split())[:200]


def do_inside(ctx, rel, terms, k=8):
    row = ctx.rel_to_row.get(rel)
    n_pages = row["n_pages"] if row else None
    pages = _load_doc_pages(ctx, rel)
    if not pages:
        return {"rel": rel, "n_pages": n_pages, "tier": "none", "hits": []}

    mem = sqlite3.connect(":memory:")
    mem.execute("CREATE VIRTUAL TABLE p USING fts5(page_index UNINDEXED, body)")
    mem.executemany("INSERT INTO p VALUES (?,?)", pages)
    mem.commit()

    words = content_words(terms)
    tier = "any"
    rows = []
    if words:
        if len(words) <= 4:
            m = '"' + terms.replace('"', '""') + '"'
            tier = "phrase"
        else:
            m = " ".join(f'"{w}"' for w in words)
            tier = "all"
        try:
            rows = mem.execute(
                "SELECT page_index, body, bm25(p) FROM p WHERE p MATCH ? ORDER BY bm25(p) LIMIT ?",
                (m, k)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows and words:
            m2 = " OR ".join(f'"{w}"' for w in words)
            try:
                rows = mem.execute(
                    "SELECT page_index, body, bm25(p) FROM p WHERE p MATCH ? ORDER BY bm25(p) LIMIT ?",
                    (m2, k)).fetchall()
            except sqlite3.OperationalError:
                rows = []
            tier = "any"
    hits = []
    for page_index, body, score in rows:
        hits.append({"page_index": page_index, "score": round(score, 3),
                     "line": _best_line(body, words)})
    return {"rel": rel, "n_pages": n_pages, "tier": tier if words else "none", "hits": hits}


def _print_inside(res):
    print(f"INSIDE {res['rel']} ({res['n_pages']}p) tier={res['tier']}")
    for h in res["hits"]:
        print(f"  p{h['page_index']}  {h['score']}  | {h['line']}")


# --------------------------------------------------------------------- #
# tables
# --------------------------------------------------------------------- #
def do_tables(ctx, rel, grep=None):
    rows = ctx.shelf.execute(
        "SELECT page_index, caption FROM captions WHERE rel=? ORDER BY page_index", (rel,)).fetchall()
    if grep:
        g = grep.lower()
        rows = [r for r in rows if g in r[1].lower()]
    return {"rel": rel, "captions": [{"page_index": p, "caption": c} for p, c in rows]}


def _print_tables(res):
    for c in res["captions"]:
        print(f"  p{c['page_index']}  {c['caption']}")


# --------------------------------------------------------------------- #
# series
# --------------------------------------------------------------------- #
def do_series(ctx, row_words, family_words, fy_from=None, fy_to=None, k=1, exact_family=False):
    """exact_family=True: `family_words` IS already a real docs.family key (the
    caller resolved it directly from ctx.rel_to_family, not from user text) --
    use it as-is instead of re-resolving through do_have's fuzzy search. That
    fuzzy search is for a human's --family "some words"; a family KEY strings
    like "...{fy}" as a literal query (the placeholder brace text matches no
    real title), so it falls through to a bag-of-words tier where a noisy
    same-topic family can out-score the real one on raw term frequency -- the
    exact key is right there, searching for it again can only make it worse."""
    if exact_family:
        family = family_words
        if family not in ctx.family_to_rels:
            return {"editions": [], "matched": 0, "family": None, "error": "NO_FAMILY_MATCHES"}
    else:
        have_res = do_have(ctx, family_words)
        if have_res["no_family_matches"]:
            return {"editions": [], "matched": 0, "family": None, "error": "NO_FAMILY_MATCHES"}
        family = have_res["families"][0]["family"]
    members = [r for r in ctx.rel_to_row.values()
               if r["family"] == family and r["is_primary"] and r["fy_primary"]]
    if fy_from:
        members = [r for r in members if r["fy_primary"] >= fy_from]
    if fy_to:
        members = [r for r in members if r["fy_primary"] <= fy_to]
    members.sort(key=lambda r: r["fy_primary"])

    out, matched = [], 0
    for r in members:
        ins = do_inside(ctx, r["rel"], row_words, k=k)
        if ins["hits"]:
            matched += 1
            h = ins["hits"][0]
            out.append({"fy": r["fy_primary"], "rel": r["rel"],
                        "page_index": h["page_index"], "line": h["line"],
                        "hits": ins["hits"]})
        else:
            out.append({"fy": r["fy_primary"], "rel": r["rel"], "page_index": None,
                        "line": None, "hits": []})
    return {"editions": out, "matched": matched, "family": family, "n": len(out)}


def _print_series(res):
    if res.get("error"):
        print(res["error"])
        return
    for e in res["editions"]:
        if e["page_index"] is not None:
            print(f"{e['fy']}  p{e['page_index']}  {e['rel']}  | {e['line']}")
        else:
            print(f"{e['fy']}  NO_MATCH  {e['rel']}")
    print(f'SERIES_RECEIPT editions={res["n"]} matched={res["matched"]} family="{res["family"]}"')


# --------------------------------------------------------------------- #
# copies
# --------------------------------------------------------------------- #
def do_copies(ctx, rel):
    row = ctx.rel_to_row.get(rel)
    if not row:
        return {"rel": rel, "members": []}
    ek = row["edition_key"]
    primary = next((r for r in ctx.rel_to_row.values()
                     if r["edition_key"] == ek and r["is_primary"]), row)
    members = []
    for r in ctx.rel_to_row.values():
        if r["edition_key"] == ek:
            members.append({"rel": r["rel"], "n_pages": r["n_pages"],
                             "is_primary": bool(r["is_primary"]),
                             "same_hash_as_primary": r["sha256"] == primary["sha256"]})
    for d in row["dupes"]:
        members.append({"rel": d, "n_pages": row["n_pages"], "is_primary": False,
                         "same_hash_as_primary": row["sha256"] == primary["sha256"],
                         "collapsed_duplicate": True})
    return {"rel": rel, "members": members}


def _print_copies(res):
    for m in res["members"]:
        print(f"  {m['rel']}  ({m['n_pages']}p)  is_primary={m['is_primary']}  "
              f"same_hash_as_primary={'yes' if m['same_hash_as_primary'] else 'no'}")


# --------------------------------------------------------------------- #
# exact / open / note / notes / coverage
# --------------------------------------------------------------------- #
def do_exact(ctx, phrase, k=50):
    m = '"' + phrase.replace('"', '""') + '"'
    total = ctx.db.execute("SELECT COUNT(*) FROM pages WHERE pages MATCH ?", (m,)).fetchone()[0]
    rows = ctx.db.execute(
        "SELECT rel, page_index FROM pages WHERE pages MATCH ? LIMIT ?", (m, k)).fetchall()
    grouped = {}
    for rel, pi in rows:
        grouped.setdefault(rel, []).append(pi)
    return {"phrase": phrase, "total": total, "grouped": grouped}


def _print_exact(res):
    print(f"TOTAL_PAGES_MATCHING={res['total']}")
    if res["total"] == 0:
        print("NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING")
    else:
        for rel, pages in res["grouped"].items():
            print(f"  {rel}  pages={pages}")


def do_open(ctx, rel, page_index, slug=None):
    row = ctx.db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?",
                          (rel, page_index)).fetchone()
    if not row:
        return {"rel": rel, "page_index": page_index, "found": False}
    body = row[0][:12000]
    if slug:
        nd = _notes_dir(ctx.root)
        log = nd / f"{slug}_opened.jsonl"
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rel": rel, "page_index": page_index,
                                  "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
    return {"rel": rel, "page_index": page_index, "found": True, "body": body}


def _print_open(res):
    if not res["found"]:
        print(f"NO SUCH PAGE: {res['rel']} page {res['page_index']}")
        return
    print(f"OPENED {res['rel']} p{res['page_index']}")
    print(res["body"])


def do_note(ctx, slug, text):
    nd = _notes_dir(ctx.root)
    log = nd / f"{slug}_notes.jsonl"
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"text": text, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")
    return {"ok": True}


def do_notes(ctx, slug):
    nd = _notes_dir(ctx.root)
    opened_log = nd / f"{slug}_opened.jsonl"
    notes_log = nd / f"{slug}_notes.jsonl"
    opened = [json.loads(l) for l in opened_log.read_text(encoding="utf-8").splitlines()] \
        if opened_log.exists() else []
    notes = [json.loads(l) for l in notes_log.read_text(encoding="utf-8").splitlines()] \
        if notes_log.exists() else []
    return {"slug": slug, "opened": opened, "notes": notes}


def _print_notes(res):
    print(f"NOTES for slug={res['slug']}")
    print(f"opened ({len(res['opened'])}):")
    for o in res["opened"]:
        print(f"  {o['rel']} p{o['page_index']}  ({o['ts']})")
    print(f"notes ({len(res['notes'])}):")
    for n in res["notes"]:
        print(f"  {n['text']}  ({n['ts']})")


def do_coverage(ctx):
    return ctx.coverage()


# --------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(prog="c_shelf.py")
    ap.add_argument("--db")
    ap.add_argument("--shelf")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("find"); p.add_argument("question"); p.add_argument("--q", action="append", default=[])
    p.add_argument("--k", type=int, default=12); p.add_argument("--slug")

    p = sub.add_parser("have"); p.add_argument("words"); p.add_argument("--fy")

    p = sub.add_parser("inside"); p.add_argument("rel"); p.add_argument("terms")
    p.add_argument("--k", type=int, default=8)

    p = sub.add_parser("tables"); p.add_argument("rel"); p.add_argument("--grep")

    p = sub.add_parser("series"); p.add_argument("row_words"); p.add_argument("--family", required=True)
    p.add_argument("--from", dest="fy_from"); p.add_argument("--to", dest="fy_to"); p.add_argument("--slug")

    p = sub.add_parser("copies"); p.add_argument("rel")

    p = sub.add_parser("exact"); p.add_argument("phrase"); p.add_argument("--k", type=int, default=50)

    p = sub.add_parser("open"); p.add_argument("rel"); p.add_argument("page_index", type=int)
    p.add_argument("--slug")

    p = sub.add_parser("note"); p.add_argument("--slug", required=True); p.add_argument("text")

    p = sub.add_parser("notes"); p.add_argument("--slug", required=True)

    sub.add_parser("coverage")

    p = sub.add_parser("register"); p.add_argument("--root", required=True)
    p.add_argument("--db", dest="reg_db", required=True); p.add_argument("--shelf", dest="reg_shelf", required=True)

    a = ap.parse_args()
    if not a.cmd:
        ap.print_usage(); sys.exit(2)

    if a.cmd == "register":
        r = do_register(a.root, a.reg_db, a.reg_shelf)
        print(json.dumps(r, indent=1)); return

    root, db, shelf = _resolve(a.db, a.shelf)
    if not db or not shelf:
        print("NO_REGISTERED_ROOT", file=sys.stderr); sys.exit(2)
    ctx = get_ctx(db, shelf, root)

    if a.cmd == "find":
        queries = [a.question] + list(a.q)
        res = do_find(ctx, queries)
        _print_find(res, a.k)
    elif a.cmd == "have":
        res = do_have(ctx, a.words, fy=a.fy)
        _print_have(res)
    elif a.cmd == "inside":
        res = do_inside(ctx, a.rel, a.terms, k=a.k)
        _print_inside(res)
    elif a.cmd == "tables":
        res = do_tables(ctx, a.rel, grep=a.grep)
        _print_tables(res)
    elif a.cmd == "series":
        res = do_series(ctx, a.row_words, a.family, fy_from=a.fy_from, fy_to=a.fy_to)
        _print_series(res)
    elif a.cmd == "copies":
        res = do_copies(ctx, a.rel)
        _print_copies(res)
    elif a.cmd == "exact":
        res = do_exact(ctx, a.phrase, k=a.k)
        _print_exact(res)
    elif a.cmd == "open":
        res = do_open(ctx, a.rel, a.page_index, slug=a.slug)
        _print_open(res)
    elif a.cmd == "note":
        do_note(ctx, a.slug, a.text)
        print("NOTED")
    elif a.cmd == "notes":
        res = do_notes(ctx, a.slug)
        _print_notes(res)
    elif a.cmd == "coverage":
        _print_coverage(do_coverage(ctx))
    else:
        ap.print_usage(); sys.exit(2)


if __name__ == "__main__":
    main()
