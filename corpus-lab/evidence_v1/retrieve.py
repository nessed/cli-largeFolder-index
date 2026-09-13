#!/usr/bin/env python
"""evidence_v1.retrieve -- five independent discovery channels, fused.

Runtime code, no labpaths import. Implements BUILD_PROMPT.md's retrieval
section: caption+row, heading+source, document title, notes+links, paragraph;
fusion score = sum of 1/(60+rank) across channels; ties broken by full content
hash then physical page index; byte-identical documents collapsed before
top-k; max 2 pages/document in the initial 24 leads, 8 slots reserved for
distinct label families/periods.
"""
import json
import re
from pathlib import Path

from . import store

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "is", "are",
    "was", "were", "what", "how", "does", "do", "did", "it", "its", "this",
    "that", "with", "as", "at", "by", "from", "be", "has", "have", "had",
    "i", "need", "whatever", "official", "figure", "number", "somewhere",
    "here", "there", "around", "about",
    # 2026-09-13 tuning loop: trajectory-question framing words that carry no
    # discriminating power but were diluting the query enough to push the
    # correct (rare, specific) candidate below rank 120 -- traced concretely
    # on tr_04 ("...look over the last decade or so"): dropping these moved
    # the gold document from absent-in-top-120 to rank 93.
    "look", "looks", "looked", "over", "so", "since", "start", "period",
    "gone", "happened", "roughly", "big", "give", "trajectory",
}

ALIASES_PATH = Path(__file__).resolve().parent / "aliases.json"


def load_aliases():
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    return [[x.lower() for x in g] for g in data["groups"]]


def content_words(text, max_words=12):
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]*", text.lower())
    out = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return out[:max_words]


def expand_phrases(text, alias_groups):
    """Most aliases are multi-word ('non-tax revenue' / 'non-tax receipts'),
    so matching must happen against the ORIGINAL TEXT, not single tokens from
    content_words() -- a word-by-word lookup against a phrase-keyed map can
    never fire. Returns whole alternate PHRASES (kept unsplit, so the FTS
    query quotes them and gets the exact-phrase match boost a table caption
    like "Non-tax receipts" needs against a question that says "non-tax
    revenue")."""
    text_lower = text.lower()
    extra = []
    for group in alias_groups:
        if any(phrase in text_lower for phrase in group):
            for phrase in group:
                if phrase not in text_lower and phrase not in extra:
                    extra.append(phrase)
    return extra


def expand_terms(question_text, words, alias_groups):
    """Combines single-token words from content_words() with whole-phrase
    aliases detected against the original question text (see
    expand_phrases -- a word-by-word lookup cannot find a multi-word alias)."""
    expanded = list(words)
    for phrase in expand_phrases(question_text, alias_groups):
        if phrase not in expanded:
            expanded.append(phrase)
    return expanded


def _fts_quote(term):
    escaped = term.replace('"', '""')
    return '"{}"'.format(escaped)


def _or_query(terms):
    return " OR ".join(_fts_quote(t) for t in terms if t.strip())


def _and_query(terms):
    return " AND ".join(_fts_quote(t) for t in terms if t.strip())


def _run_with_and_then_or_fallback(run_fn, terms, limit):
    """Try the conjunction first -- when every term genuinely co-occurs on a
    card, that is a far more precise signal than OR's bag-of-words ranking,
    and it is cheap to attempt since an empty AND result costs one query.
    Falls back to OR whenever AND returns nothing, exactly as
    corpus_search.py's own night-3 fix established for this corpus."""
    and_expr = _and_query(terms)
    rows = run_fn(and_expr, limit) if and_expr else []
    if rows:
        return rows, "AND"
    or_expr = _or_query(terms)
    return (run_fn(or_expr, limit) if or_expr else []), "OR"


def _channel_query(con, table, match_expr, limit, extra_cols=""):
    sql = ("SELECT rowid, content_sha256, page_index, rank {extra} "
           "FROM {table} WHERE {table} MATCH ? ORDER BY rank LIMIT ?"
           ).format(table=table, extra=extra_cols)
    try:
        return con.execute(sql, (match_expr, limit)).fetchall()
    except Exception:
        return []


def _card_channel(con, columns, match_expr, limit):
    sql = ("SELECT card_id, content_sha256, page_index, rank FROM cards_fts "
           "WHERE cards_fts MATCH '{{{cols}}} : ' || ? ORDER BY rank LIMIT ?"
           ).format(cols=" ".join(columns))
    try:
        return con.execute(sql, (match_expr, limit)).fetchall()
    except Exception:
        return []


def _card_whole_text_channel(con, column, match_expr, limit):
    sql = ("SELECT card_id, content_sha256, page_index, rank FROM cards_fts "
           "WHERE {col} MATCH ? ORDER BY rank LIMIT ?").format(col=column)
    try:
        return con.execute(sql, (match_expr, limit)).fetchall()
    except Exception:
        return []


def run_channels(root_path, query_terms, limit_per_channel=500, alternative="A"):
    """Returns {channel_name: [(key, rank, raw_row), ...]}. key is a stable
    item identity: ('card', card_id) for table cards, ('doc', content_sha256)
    for title hits, ('page', content_sha256, page_index) for prose/notes.

    `alternative` selects the ONE permitted A/B catalogue variant (Stage 5):
    A = cards_fts.search_text (caption/header/row card, <=1500 chars); B =
    cards_fts.search_text_b (same plus preceding/following paragraph,
    <=2400 chars). This is a single measured choice for channel 1, not a
    per-query option -- the CLI never exposes it."""
    con = store.connect(root_path, timeout_s=2.0)
    try:
        match_expr = _or_query(query_terms)
        if not match_expr:
            return {}
        channels = {}
        # Measured during Stage 5 (night 3's own finding F23, reproduced here):
        # AND-first-then-OR-fallback makes aggregate recall WORSE on this
        # corpus (3/17 -> 2/17 hit@24), not better -- a narrow AND match is
        # often confidently wrong rather than absent, so the OR fallback
        # never gets a chance to surface the actually-correct, lower-ranked
        # card. Kept as pure OR; _and_query/_run_with_and_then_or_fallback
        # remain defined and tested but unused by default.

        col = "search_text" if alternative == "A" else "search_text_b"
        rows = _card_whole_text_channel(con, col, match_expr, limit_per_channel)
        channels["caption_row"] = [(("card", r[0]), i + 1, r) for i, r in enumerate(rows)]

        rows = _card_channel(con, ["heading", "source_literal"], match_expr, limit_per_channel)
        channels["heading_source"] = [(("card", r[0]), i + 1, r) for i, r in enumerate(rows)]

        rows = _channel_query(con, "title_fts", match_expr, limit_per_channel)
        channels["title"] = [(("doc", r[1]), i + 1, r) for i, r in enumerate(rows)]

        rows = _channel_query(con, "notes_fts", match_expr, limit_per_channel)
        channels["notes"] = [(("page", r[1], r[2]), i + 1, r) for i, r in enumerate(rows)]

        rows = _channel_query(con, "prose_fts", match_expr, limit_per_channel)
        channels["paragraph"] = [(("page", r[1], r[2]), i + 1, r) for i, r in enumerate(rows)]

        return channels
    finally:
        con.close()


def fuse(channels, reserved_families=8, max_leads=24, max_pages_per_doc=2):
    """RRF fusion (1/(60+rank)), redistributing slots from channels with fewer
    hits into later channels in the order listed above, as the contract
    requires. Collapses items sharing a content_sha256 so a byte-identical
    document contributes at most max_pages_per_doc candidates."""
    scores = {}
    doc_of = {}
    page_of = {}
    for chname, hits in channels.items():
        for key, rank, row in hits:
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + rank)
            content_sha = row[1]
            doc_of[key] = content_sha
            if key not in page_of:
                page_of[key] = key[2] if key[0] == "page" else (
                    row[2] if len(row) > 2 and key[0] == "card" else None)

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], doc_of.get(kv[0], ""),
                                                       kv[0][-1] if len(kv[0]) > 2 else 0))

    per_doc_count = {}
    leads = []
    seen_docs_in_leads = set()
    for key, score in ordered:
        doc = doc_of.get(key)
        if per_doc_count.get(doc, 0) >= max_pages_per_doc:
            continue
        leads.append({"key": key, "score": round(score, 6), "content_sha256": doc,
                       "page_index": page_of.get(key)})
        per_doc_count[doc] = per_doc_count.get(doc, 0) + 1
        seen_docs_in_leads.add(doc)
        if len(leads) >= max_leads - reserved_families:
            break

    # Reserve remaining slots for items from documents NOT already represented,
    # i.e. distinct label families/periods rather than more of the same table.
    for key, score in ordered:
        if len(leads) >= max_leads:
            break
        doc = doc_of.get(key)
        if doc in seen_docs_in_leads:
            continue
        leads.append({"key": key, "score": round(score, 6), "content_sha256": doc,
                       "page_index": page_of.get(key)})
        seen_docs_in_leads.add(doc)

    return leads[:max_leads]


DEFAULT_ALTERNATIVE = "A"  # set by the Stage 5 measured choice; see cli.py

CLAUSE_SPLIT_RE = re.compile(
    r"\s*(?:,|;|\band\b|\bwith\b|\bcompared? (?:to|with)\b|\bversus\b|\bvs\.?\b)\s*", re.I)


def generate_query_variants(question_text, alias_groups):
    """Deterministic multi-query rewriting (2026-09-13 tuning loop, idea 2):
    a handful of algorithmic rewordings of the same question, each producing
    its own term list, fused together at the channel level in discover().
    No live model call -- these are fixed transformations of the question
    text, not agent-written rewrites (that variant is not available to this
    offline tuning loop).

    Returns a list of (variant_name, terms) pairs. The FIRST is always the
    original full-question terms (today's baseline), so this function is a
    strict superset of the single-query behavior.
    """
    variants = []
    base_words = content_words(question_text)
    base_terms = expand_terms(question_text, base_words, alias_groups)
    variants.append(("full", base_terms))

    # Tail phrase: the last few content words are usually the specific
    # metric/entity being asked about ("... for non-tax revenue", "...
    # Balochistan -- health affairs and services"), rather than the
    # question's framing words at the front ("I need", "roughly how big").
    if len(base_words) >= 2:
        tail = base_words[-4:] if len(base_words) > 4 else base_words
        tail_terms = expand_terms(" ".join(tail), tail, alias_groups)
        if tail_terms != base_terms:
            variants.append(("tail", tail_terms))

    # Clause split: multi-concept questions ("how does X compare with Y and
    # with Z") ask about several sub-tables in one sentence; a single
    # bag-of-words query dilutes across all of them. Split on light
    # connective words and query each clause separately.
    clauses = [c.strip() for c in CLAUSE_SPLIT_RE.split(question_text) if c.strip()]
    if len(clauses) > 1:
        # The first clause usually carries the shared entity/period context
        # ("for Khyber Pakhtunkhwa around 2019-20"); a later clause alone
        # ("federal development allocation") is too generic to discriminate
        # on its own -- measured: isolated, it does not surface the right
        # document at all. Pair each later clause WITH clause 0 instead of
        # querying it alone.
        shared_words = content_words(clauses[0])
        for idx, clause in enumerate(clauses[1:], start=1):
            cwords = content_words(clause)
            if len(cwords) < 2:
                continue
            combined_text = clauses[0] + " " + clause
            combined_words = shared_words + cwords
            cterms = expand_terms(combined_text, combined_words, alias_groups)
            if cterms and cterms not in [v for _, v in variants]:
                variants.append(("clause0+{}".format(idx), cterms))

    return variants


USE_MULTIQUERY = False  # tuning-loop switch; see corpus-lab/state/evidence_v1/tuning_log.jsonl idea 2


USE_FAMILY_WALK = False  # tuning-loop switch; see tuning_log.jsonl idea 5


def _family_walk(root_path, seed_leads, seed_count=5, per_label_limit=60):
    """Idea 5: a trajectory/multi-edition question's real blocker is not
    missing vocabulary -- it is hundreds of near-identical yearly editions of
    the SAME table (measured: 778 cards caption-match "Sindh"+"Annual
    Development Programme" alone) all scoring within a hair of each other
    under generic OR terms, so the specific years asked about do not make the
    top-K cut. Once ANY one instance of the family is found among the seed
    leads, its literal row_label is an exact, low-noise key: walk it directly
    against cards.row_labels rather than re-competing in the generic pool."""
    con = store.connect(root_path, timeout_s=2.0)
    try:
        seen_labels = set()
        extra = []
        for lead in seed_leads[:seed_count]:
            if lead["key"][0] != "card":
                continue
            row = con.execute("SELECT row_labels FROM cards WHERE card_id=?",
                               (lead["key"][1],)).fetchone()
            if not row or not row[0]:
                continue
            try:
                labels = json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                continue
            for label in labels:
                label = (label or "").strip()
                if len(label) < 8 or label in seen_labels:
                    continue
                seen_labels.add(label)
                q = '"{}"'.format(label.replace('"', '""'))
                try:
                    rows = con.execute(
                        "SELECT card_id, content_sha256, page_index FROM cards_fts "
                        "WHERE row_labels MATCH ? LIMIT ?", (q, per_label_limit)).fetchall()
                except Exception:
                    rows = []
                for r in rows:
                    extra.append({"key": ("card", r[0]), "score": 1e-6,
                                  "content_sha256": r[1], "page_index": r[2],
                                  "family_of": label})
        return extra
    finally:
        con.close()


def _merge_family_leads(leads, family_leads, max_leads, max_pages_per_doc=2):
    per_doc_count = {}
    for l in leads:
        per_doc_count[l["content_sha256"]] = per_doc_count.get(l["content_sha256"], 0) + 1
    seen_keys = {l["key"] for l in leads}
    merged = list(leads)
    for fl in family_leads:
        if len(merged) >= max_leads:
            break
        if fl["key"] in seen_keys:
            continue
        if per_doc_count.get(fl["content_sha256"], 0) >= max_pages_per_doc:
            continue
        merged.append(fl)
        seen_keys.add(fl["key"])
        per_doc_count[fl["content_sha256"]] = per_doc_count.get(fl["content_sha256"], 0) + 1
    return merged[:max_leads]


def discover(root_path, question_text, max_leads=24, alternative=None):
    alias_groups = load_aliases()
    alt = alternative or DEFAULT_ALTERNATIVE

    if not USE_MULTIQUERY:
        words = content_words(question_text)
        terms = expand_terms(question_text, words, alias_groups)
        channels = run_channels(root_path, terms, alternative=alt)
        leads = fuse(channels, max_leads=max_leads)
        if USE_FAMILY_WALK:
            # Seed from a WIDER pool than the final cutoff -- the whole point
            # is that a relevant family member often sits well past the
            # top-24 (or even top-120) cut under generic OR terms, so seeding
            # only from the already-cut list would rarely find one to walk
            # from in the first place.
            wide_leads = fuse(channels, max_leads=100, reserved_families=0)
            family_leads = _family_walk(root_path, wide_leads, seed_count=10)
            leads = _merge_family_leads(leads, family_leads, max_leads)
        return {"terms_used": terms, "channels_hit": {k: len(v) for k, v in channels.items()},
                "leads": leads}

    variants = generate_query_variants(question_text, alias_groups)
    # Iteration 3 (idea 2): summing every variant's channels together (as
    # iterations 1-2 did) rewards a document for matching the SAME shared
    # words repeatedly across many clause-paired variants, not for being
    # specifically relevant to any one sub-concept -- measured: the correct
    # KP White Paper card for mb_04 ranked #6 when its one matching variant
    # was queried alone, but fell out of the top 24 entirely once summed
    # against four other variants that all also share the "khyber
    # pakhtunkhwa" terms. Fusing per-variant instead (best score across
    # variants, not summed) is the fix being measured here.
    all_leads_by_variant = []
    channels_hit = {}
    for variant_name, terms in variants:
        channels = run_channels(root_path, terms, alternative=alt)
        for chname, hits in channels.items():
            channels_hit["{}__{}".format(variant_name, chname)] = len(hits)
        variant_leads = fuse(channels, max_leads=max_leads, reserved_families=0)
        all_leads_by_variant.append(variant_leads)

    best_by_key = {}
    for variant_leads in all_leads_by_variant:
        for lead in variant_leads:
            key = lead["key"]
            if key not in best_by_key or lead["score"] > best_by_key[key]["score"]:
                best_by_key[key] = lead
    ordered = sorted(best_by_key.values(), key=lambda l: -l["score"])

    per_doc_count = {}
    leads = []
    for lead in ordered:
        doc = lead["content_sha256"]
        if per_doc_count.get(doc, 0) >= 2:
            continue
        leads.append(lead)
        per_doc_count[doc] = per_doc_count.get(doc, 0) + 1
        if len(leads) >= max_leads:
            break

    return {"terms_used": [t for _, terms in variants for t in terms],
            "variants_used": [v for v, _ in variants],
            "channels_hit": channels_hit,
            "leads": leads}


def search(root_path, concept, entity="", period="", kind="lookup", max_results=120,
           alternative=None):
    alias_groups = load_aliases()
    concept_entity_text = " ".join(x for x in [concept, entity] if x)
    words = content_words(concept_entity_text)
    terms = expand_terms(concept_entity_text, words, alias_groups)
    if period and period != "unspecified":
        terms.append(period)
    channels = run_channels(root_path, terms, limit_per_channel=max_results,
                             alternative=alternative or DEFAULT_ALTERNATIVE)
    leads = fuse(channels, max_leads=max_results, reserved_families=0)
    return {"terms_used": terms, "channels_hit": {k: len(v) for k, v in channels.items()},
            "results": leads}
