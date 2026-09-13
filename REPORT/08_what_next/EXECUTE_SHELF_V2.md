# Shelf V2 execution contract

> **Superseded — 2026-09-13. Do not execute this contract as written.** It implements the
> Shelf V2 recommendation in `RESEARCH_2026-09-13.md`, which rested on the premise that
> semantic retrieval over the small card pool was untested. Approach C had already built and
> measured that route (BGE-small vectors over 12,760 document cards, fused with FTS5 by
> reciprocal-rank fusion) and it failed its offline gate — 6/17 documents in the top 10
> against a 12/17 bar. See
> [`CORRECTION_2026-09-13.md`](CORRECTION_2026-09-13.md)
> and [`STAGE3_OFFLINE_GATE_REPORT.md`](../06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md).
> Kept for its staging, gating and verification design, which remain sound. Future work
> should be a separately specified, offline-gated ablation on the shelf that already exists.

## Purpose and scope

Build and evaluate the Shelf V2 discovery layer described in `RESEARCH_2026-09-13.md`.
This is an offline-first experiment. Do not run a Claude question battery or install a
stack until all free gates pass. The corpus is read-only. Never regenerate any harness,
read answer-key text in a measurement session, or expose `_private` to one.

## Files that may change

Create only these new paths:

```text
corpus-lab/shelf_v2/
corpus-lab/bin/shelf_v2.py
corpus-lab/bin/shelf_v2_offline.py
corpus-lab/bin/shelf_v2_stack.py
corpus-lab/tests/shelf_v2/
corpus-lab/state/shelf_v2/
corpus-lab/02_stacks/shelf_v2/       # derived data, gitignored
_private/results/03_runs/PSV2_*/     # only after a paid gate passes
_private/results/04_scores/*shelf_v2* # only after a paid gate passes
```

Do not modify `ask.py`, `run_harness.py`, `scoring.py`, `corpus_search.py`,
`index_build.py`, or the existing `evidence_v1` runtime. Reuse public read-only helpers
where safe. Append state records; never rewrite `progress.jsonl`.

## Stage 0 — preflight and isolation

1. Run `stack.py status` against the rung. Require no `CLAUDE.md` or `.claude` owned by a
   live stack.
2. Snapshot the planted-file checksum using the existing script and pass-2 manifest.
3. Read the last 20 `progress.jsonl` lines. If another run has a live status, stop with
   `RUNG_BUSY`; do not install or mutate the rung.
4. Record `state/shelf_v2/preflight.json`: timestamp, source DB identity, checksum label,
   corpus path, and existing-stack status.

Gate 0: all four checks pass. Otherwise append one progress record and stop.

## Stage 1 — strict representation build

Build `shelf.sqlite` from the existing FTS index plus source files. It has `documents`,
`families`, `family_members`, `cards`, `captions`, `aliases`, and `build_receipts` tables.

For every indexed source file, create one document card. Detect publication family and FY
only from front-matter/page-zero text and deterministic filename tokens; retain raw values
and confidence. Build cards only from explicit caption/list-of-tables text or native
Office/CSV structure. Do **not** invoke any captionless numeric-window detector.

Cards must store source hash/path, physical page, kind, extraction rule, and contextual
fields. Build duplicate groups by exact content hash first. For near copies, produce
candidates with normalized title/FY plus first-page and caption-token Jaccard similarity;
verify similarity before assigning a family. Within an edition mark the longest readable
primary, but keep all members.

Output:

* `02_stacks/shelf_v2/shelf.sqlite`
* `state/shelf_v2/build.json` with file accounting, document/card/family counts, timings,
  detector counts, and 100 deterministic card sample IDs for audit.

Gate 1:

* exactly 13,634 indexed documents represented, or an explained count matching the source DB;
* document-card count equals document count;
* strict-card count is at most 150,000;
* no captionless heuristic cards exist;
* source accounting identity closes.

On failure: log `REPRESENTATION_BUILD_FAILED`, fix once, rebuild from derived Shelf V2 data
only, then stop if it fails again.

## Stage 2 — representation precision audit

Without reading answer-key content, inspect the deterministic 100-card sample from each
table-oriented source type. A card is valid only when its cited source page visibly contains
the claimed caption/list entry/native table. Classify it `valid_table`, `valid_navigation`,
`ordinary_prose`, or `malformed`.

Write `state/shelf_v2/card_precision.json`, including sample seed, sample IDs, labels, and
per-type precision. This is a human/visual verification task; do not claim a parser's own
output validates it.

Gate 2:

* explicit-caption and contents/list cards: at least 95% valid;
* native structured-file cards: at least 98% valid;
* any geometry cards, if introduced: at least 85% valid;
* ordinary prose: at most 5% in every table-oriented set.

If a source type fails, remove it from discovery and rebuild. Never loosen its detector.

## Stage 3 — shelf-only offline retrieval gate

Implement CLI commands:

```text
find <question> [--q <rewrite> ...]
have <publication> --fy <YYYY-YY>
inside <relative-path> <terms>
series <terms> --family <family> --from <FY> --to <FY>
exact <literal>
open <relative-path> <page>
coverage
```

`find` runs field-weighted FTS5 over document/family cards and strict navigation cards,
groups by family, and prints up to eight families with edition/primary/copy information.
`inside` ranks only pages belonging to the named file. `series` enumerates primaries by FY
and reports one local page lead per edition. `exact` reports a corpus-wide literal count.
Every command prints a structured receipt and coverage line.

Run `shelf_v2_offline.py` against the private frozen key in the orchestrator only. It must
measure the actual route, not one bag of words:

| Category | Measurement | Passing threshold |
|---|---|---:|
| 10 single-source positives | required evidence family in `find` top-8, then page in `inside` top-5 | 8/10 |
| 7 comparison/trajectory positives | all required families recovered through no more than four atomic searches | 5/7 |
| all 17 positives | required address recall after the bounded route | at least 0.65 |
| document-level absence | `have` emits correct inventory-negative | 9/10 |
| present-edition controls | `have` emits edition-present | 15/17 |

Record every query, route, hit ranks, excluded evidence, candidate counts, and latency in
`state/shelf_v2/offline_baseline.json`. Do not put answer text, row labels, or gold paths
in source code, prompts, aliases, or a Claude session.

Gate 3: every row passes. If it fails, write a miss taxonomy (`family_missing`,
`family_misclustered`, `vocabulary_gap`, `inside_document_failure`, `bad_oracle`, or
`multi-source_route_failure`) and stop. Do not download a model or launch paid sessions.

## Stage 4 — conditional semantic and reranker ablations

Only if Gate 3 passes, benchmark a static embedding candidate on 1,000 card texts:
throughput, peak memory, cold/warm timing, and deterministic checksum of vectors. Permit a
full card-vector build only if projected build time is 20 minutes or less and RAM stays
below 8 GiB. Use float16 vectors and local NumPy cosine; no server or daemon.

Run these offline ablations in this order:

1. shelf FTS only;
2. shelf FTS + contextual fields;
3. FTS + semantic card vectors fused by RRF (`k=60`);
4. fused candidates plus compact reranker over the top 50 and top 100 separately;
5. the winning retrieval stack with predeclared routed subqueries.

For each, record family recall, page recall, all-address recall, p50/p95 latency, and the
candidate pool before/after reranking. Keep a layer only if it adds at least two positive
questions to family top-8 **or** raises all-address recall by at least 0.10 without adding
more than 10 seconds p95 latency. If neither condition holds, delete only its derived
vectors/models and retain the stronger prior configuration.

Gate 4: winning configuration must exceed the Gate-3 baseline and reach at least 12/17
family recovery after the bounded route. Otherwise stop as `SEMANTIC_LAYER_NOT_JUSTIFIED`.

## Stage 5 — selected-page verification

For leads returned by the winning route, implement `verify` on an already selected page.
Try PyMuPDF `find_tables()` using `lines_strict`, then `text`; use the returned bounding box
to extract rows/headers. Cross-check a chosen numeric cell against PDF text coordinates or
pdfplumber. Do not run geometry extraction corpus-wide.

An evidence record is valid only with all of: source hash, path, physical page, page crop or
bbox, literal row label, complete column/header path, literal value, unit, period, and
verbatim caption/source text. Record uncertainty explicitly. Reuse the `evidence_v1`
compiler/compatibility concepts rather than inventing a free-form final-answer path.

Run an offline 30-address audit, stratified across PDF tables, CSV, XLSX, DOCX, and prose.

Gate 5: at least 24/30 records have a complete valid address; zero records may contain a
model-invented value; every failed record has a machine-readable reason. Below this, stop
before Claude sessions and repair selected-page extraction only.

## Stage 6 — install and paid evaluation

Only after Gates 1-5 pass, add `shelf_v2_stack.py`. It must use absolute deny paths,
record all owned files before writing them, refuse a pre-existing foreign stack, and remove
only its own files on teardown. The `CLAUDE.md` must require: route -> find/inside/series ->
open -> verify/note -> answer from evidence receipt. It must state that listing/snippets are
not evidence.

Run stack round-trip tests twice, including foreign-file refusal. Then execute canaries
with a ceiling of $3/40 minutes. Require at least 15/17 reachable canaries. If it passes,
run the 20-question battery with a $12/60-minute ceiling, at parallelism two. Run the 12
extra absence questions only if the 20 complete.

Report separately: family surfaced, page opened, valid evidence address, compatible
calculation, claim supported, forbidden citation, and scoped absence. The success target is
at least 10/17 opened valid evidence addresses and at least 10/15 safe absence outcomes.
Always verify checksum, quarantine new memory, and teardown before reporting results.

## OCR branch (separate, optional)

After Shelf V2 is measured, sample 30 image-only/complex pages across document types. Test
Docling CPU or PaddleOCR against rendered pages for character accuracy, table boundary
accuracy, numeric-cell accuracy, runtime, memory, and installation reproducibility. OCR may
be added only if at least 27/30 sampled pages preserve requested labels and at least 24/30
numeric cells are visually correct. OCR-derived numbers still require visual confirmation.
