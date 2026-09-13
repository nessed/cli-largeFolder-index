# Approach B — the brother's suggestion, examined and turned into a design

> "This is a search problem. Use a combination of embedding and keyword searches across
> all the documents. Elasticsearch maybe. Transform the initial query into 5–6 queries,
> summarise the results and feed them back into the model for ranking."
>
> "Or be very naive: load each document into the context window one at a time, save the
> important pieces to a file, do that for all docs, then answer from the file you built."

Both messages are right about the shape of the problem and both need adjusting to fit
what this lab has measured. This document says what survives, what does not, and what to
build. The executor prompt is `B_HYBRID_MULTIQUERY_BUILD.md`.

---

## 1. The short version

- **Keyword search already exists and already fails alone.** SQLite FTS5 over 1,206,260
  pages is BM25, the same ranking family Elasticsearch would give. Eight mechanical ways
  of turning a question into a BM25 query put the right file in the top 50 zero times out
  of 17 (`state/rank_experiments.json`). So the keyword half is built; it is the other
  three pieces of the suggestion that are new here: **query rewriting into several
  queries, a semantic channel, and reranking**.
- **Query rewriting is the most promising piece, and it has quiet evidence behind it.**
  The mechanical strategies used the question's own words ("compare", "released",
  "decade"). When the *agent* wrote its own short queries in the S1 sessions, the search
  surfaced a correct file on 5 of 17 questions (F21). Nobody has yet measured what happens
  when 5–6 deliberately different rewrites are fused. That is the first free experiment.
- **The semantic channel is the expensive piece and cannot be "all pages" on this
  machine.** Measured today, 13 Sep, on real pages from the index: bge-small-en-v1.5
  (quantized ONNX, fastembed) embeds 7.0–7.3 pages/s at 2,000 characters whether it is
  given 16 threads or the default. That is **46 hours** for the harness. At 300
  characters it does 28–35/s, still 10 hours, and page heads miss the captions that sit
  mid-page. So the vector half must run on a **smaller denominator**: the ~88,700 table
  caption lines in the corpus (estimated from a 1-in-25 page sample), and document
  titles, and optionally a much faster static embedding model measured on the spot.
- **Elasticsearch is out**, not for quality but for the interface constraint: it is a
  JVM server that takes 20+ seconds and 1 GB+ to start and has to be running. Nothing it
  adds over FTS5 + a vector file pays for that.
- **The naive "read every document" idea is out at corpus scale by arithmetic, and in at
  candidate scale.** 1.2 million pages × ~3,770 characters ≈ 1.1 billion tokens per full
  pass: about $1,100 on Haiku 4.5, $2,200 on Sonnet 5, and it would have to be redone as
  the folder churns. But the same loop over the **top 20 candidate pages** for one
  question is ~20,000 tokens, and "save the important pieces to a file, then answer from
  the file" is exactly the discipline that fixes F21 (the agent citing pages it never
  opened). So B keeps the naive loop as its answering procedure, scoped to what the
  search returns.

## 2. What the evidence in this folder says about each piece

### 2.1 Keyword search: present, healthy, and the wrong ranker on its own

- Index: 13,634 files, 1,206,260 pages, 782 s to build, accounting identity closes
  (`corpus_search.py --coverage`). All 64 evidence references for the frozen 20 are
  indexed (`state/diagnose_recall.json`).
- Ranking: the correct evidence file sits at rank 62–2,917 when it appears at all under
  the best mechanical query (OR of all content words); under AND of the rarest terms it
  never appears (`state/rank_experiments.json`). The rarest terms are question words like
  "compare", "spreadsheet", "somewhere" with document frequency 0 to 200 — a human would
  never search on them, which is the point: the failure is *query formation*, not BM25.
- Vocabulary gaps exist and are not exotic: `pl_14` asks for "sales tax", the table says
  "GST collection" ("sales tax" is on 39,304 pages, "gst collection" on 21,210);
  `pl_21` asks for "direct taxes", the table row is "Income and Corporation Tax". An
  embedding bridges these; a synonym list would too, but a synonym list written by hand
  after reading the answer key is contamination, so B does not allow one.

### 2.2 Multi-query rewriting: unmeasured, with a favourable hint

F21: with an FTS5 front door and no query help, the model's own short queries surfaced a
correct file on 5/17 questions. The lab has never fused several rewrites. In the
literature this (query expansion + reciprocal-rank fusion) is the cheapest known lift for
vague questions, and it needs no model at query time beyond the one already answering.

Design decision: **the agent writes the rewrites itself** (the search command accepts
several `--q` arguments and fuses them). No nested LLM call inside the tool. For the
offline gate the executor produces rewrites with a headless Haiku call using the *same*
instruction text that goes into `CLAUDE.md`, so the free measurement approximates
production behaviour.

### 2.3 Semantic channel: what fits in the setup budget

| unit | count | seconds at measured rate | verdict |
|---|---|---|---|
| every page, 2,000 chars, bge-small | 1,206,260 | 46 h (7.3/s) | no |
| every page head, 300 chars, bge-small | 1,206,260 | 9.6 h (35/s) | no, and misses mid-page captions |
| table caption lines (`Table X.Y: …`) | ≈ 88,700 | ≈ 25–40 min at 40–60/s (short strings) | **yes** |
| document title cards | 13,634 | ≈ 30 min at 2,000 chars, 7 min at 300 | **yes** |
| every page with a static embedding model (model2vec / potion-retrieval-32M) | 1,206,260 | unknown here; vendor claims "up to 500× faster on CPU" than the transformer it distils; MTEB retrieval 35.1 vs bge-small 51.7 | **measure once, decide by rule** |

Rule for the executor: embed captions and titles unconditionally. Embed pages with the
static model only if it measures ≥ 250 pages/s on 512 real pages (≤ 80 minutes for the
harness) *and* its offline gate is not worse than the captions-only configuration.

Storage: a float16 numpy memmap plus an id table, brute-force cosine in numpy. 88,700 ×
384 × 2 bytes = 68 MB; even 1.2 M rows is 926 MB and a dot product over it is well under
a second on this CPU. No vector database. `lancedb` is installed and would also work, but
it is one more moving part with nothing to add at this size.

### 2.4 Reranking: cheap on CPU at a 200-candidate pool

fastembed 0.8 ships ONNX cross-encoders with no torch: `Xenova/ms-marco-MiniLM-L-6-v2`
(80 MB) and larger ones. Published CPU throughput at long passages was not found; the
order of magnitude is tens of pairs per second at 512 tokens on 8 cores. The executor
measures it; the pool size is chosen so reranking finishes in ≤ 8 s.

The lab's own crude reranker (re-sort a 2,000-page pool by how many query terms a page
contains) moved one question into the top 50 and nothing else (F23), so reranking alone
over a bad pool does not save it. Reranking is here to sort a **fused** pool that
multi-query and the semantic channel have already made better, not to rescue BM25.

### 2.5 Reading and note-taking: the second half of the brother's message, scoped

F21 is the finding this addresses: S1 surfaced the right file five times and the model
opened it zero times, citing three of them from the snippet. The `CLAUDE.md` for B
therefore prescribes the naive loop over the candidate list:

1. search (several `--q`) → candidate pages grouped by document;
2. **open** each candidate page you intend to use;
3. **note** the exact line or table cell, with path and page, into a notes file the tool
   keeps outside the corpus;
4. when done, print the notes and answer **only** from them, citing path + page for
   every number;
5. if the notes are empty after the candidates are exhausted, say what was searched and
   that nothing supporting was found.

The notes file lives in `%LOCALAPPDATA%\retrieval-lab\notes\<corpus-key>\<slug>.md`, so
the agent never needs the Write tool, which measurement sessions disallow.

### 2.6 Honest absence

A score floor cannot do it (F22: absence questions score inside the answerable range).
B's mechanism is different: the reranked top-k is small enough that the model actually
reads it, and the rule is "no note, no number". For exact identifiers (SRO numbers,
demand numbers) the `exact` command reports the total number of matching pages in the
whole index, which for a literal string is a strong negative when it is zero. The 15
absence questions in the key are run through the offline pipeline to see whether the top
20 contains anything the model could mistake for an answer; that is a diagnostic, not a
gate, because the true test is what the model does with it.

## 3. What gets built

```
corpus-lab/bin/b_embed_build.py    builds the caption / title (and optionally page) vectors from the existing FTS index
corpus-lab/bin/b_search.py         the front door: search (multi --q, fused, reranked), exact, page, note, notes, coverage
corpus-lab/bin/b_stack.py          installs / removes CLAUDE.md + settings.json for stack s6_hybrid (imports the backstop deny from stack.py)
corpus-lab/bin/b_offline_gate.py   the free measurement: rank of the evidence file/page under four ablations
corpus-lab/bin/b_queries.py        headless Haiku rewrites for the offline gate, same instruction text as CLAUDE.md
corpus-lab/02_stacks/s6_hybrid/    vectors + id tables + models cache (gitignored)
```

The search pipeline, fixed:

1. For each `--q`: FTS5 phrase-or-AND top 300, FTS5 OR/bm25 top 300, vector top 300
   (captions → their page; titles → the document's first page; pages if built).
2. Reciprocal-rank fusion, k = 60, over every list of every query → top 200 pages.
3. Cross-encoder rerank of those 200 against the first `--q` (which by instruction is
   the user's question verbatim), passage = a 900-character window around the first
   query term on the page.
4. Group by document, show at most 3 pages per document, top 20 pages total, each line
   marked `not opened` until `page` is called on it in the same session slug.
5. Print a receipt: per query per channel the number of hits, the fused pool size,
   the rerank time, and the coverage line (indexed / image-only / failed counts).

## 4. What it costs

| item | cost |
|---|---|
| build vectors (captions + titles) | ~1 hour of CPU once, incremental afterwards by content hash |
| model downloads | bge-small already cached; MiniLM reranker 80 MB; potion ~130 MB if tried |
| offline gate | free: 35 headless Haiku calls for rewrites (Max quota), the rest is local |
| canary battery | ~$1–2 equivalent, 17 sessions |
| question battery | ~$3–6 equivalent, 20 Sonnet sessions, ~25 min at 2 in parallel |
| per question in production | 1–3 s search + rerank, plus the model's reading |

`claude -p` sessions draw from the Max subscription's rolling limits rather than API
dollars (Anthropic help centre, checked today); `cost_usd` is still recorded because it is
the comparability number against S0–S2.

## 5. Where it will fail

- **Scanned PDFs.** 1,211 of 15,010 harness files are image-only. No text method reaches
  them; B reports them in every receipt and nothing more.
- **Setup time scales with pages if the static-model page embedding is chosen.** The
  captions+titles configuration scales with documents, which is the safe default.
- **Questions with no lexical or semantic handle** ("is the reorganisation finished")
  depend on the rewrites guessing the right nouns. C handles these better because notes
  and memos are small distinctive documents at document level.
- **Many near-identical copies.** The harness has 25+ partial copies of the 2015-16
  Economic Survey ("perturbed values", "DRAFT", "old tables"). Fusion will return several
  of them; the reranker cannot tell a perturbed copy from the real one. B's grouping shows
  the copies side by side with page counts, and the answering rule prefers the copy it
  actually opened and quotes; whether that is the canonical one is left to the model.
  C attacks this directly.

## 6. What "worked" means for B

Offline, before spending anything, on the 17 answerable frozen questions:

| configuration | evidence file in top 20 |
|---|---|
| single BM25 query, question words (today) | 0/17 |
| multi-query lexical, fused | must reach ≥ 6/17 to justify the vector build |
| + captions/titles vectors | measured |
| + rerank | **≥ 9/17 to unlock the paid battery** |

Then the paid battery must beat the best published cell on the two halves that matter:
evidence opened (not merely surfaced) on ≥ 6 of 17, and honest handling on ≥ 10 of 15
absence questions under the corrected absence rule (declines, and asserts no figure that
is not a year or an identifier). Precise definitions are in the BUILD file.
