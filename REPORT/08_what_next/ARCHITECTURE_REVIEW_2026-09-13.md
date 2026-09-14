# Adversarial review of CURRENT_WORKING_ARCHITECTURE_2026-09-13.md

Reviewer: fresh Fable agent, 2026-09-13. Nothing in the repository was modified. No experiment was run. I did run read-only reads: Python over the public JSON state files, and one read-only SQLite count over the local shelf database (captions per page range). Both are disclosed where used.

## Contamination disclosure

Reading this repository contaminates an agent for running the benchmark, and it contaminated me. Beyond the items README.md already lists, I saw:

- `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/stage6_2_thirty_cells.json`: gold paths, pages, row and column labels for the 20 frozen questions. Gitignored, but present locally and cited by the architecture document.
- `corpus-lab/99_scratch/evidence_v1/frozen20_key.json`: a local copy of the frozen-20 answer key. Gitignored, but sitting in a scratch folder any local agent can grep. A grep for "cotton production" returned table titles from it before I could stop.
- `corpus-lab/state/c_card_sample_100.csv` is tracked in git and holds 21 gold paths.

Every design recommendation below is derived from code structure, public aggregate counts, and the plans. Where a recommendation could have been shaped by a gold path, I say so and cite the public source I am relying on instead.

---

## 1. Current state

What is built and measured, verified against the files, not the prose.

| box | measured | verified where | verification note |
|---|---|---|---|
| SHELF | 12,760 docs, 1,618 families, 393 with 2+ editions, 89,380 captions; 13/13 self-tests | `corpus-lab/state/c_shelf_build.json`, `c_shelf_selftest.json` | Confirmed. Flagged `GATE1_FAILED_STRUCTURAL` (family clustering defect). |
| ROUTE, missing edition | 11/11 | `corpus-lab/state/c_offline_gate.json` | Confirmed. A hit is `NO_EDITION_FOR` **or** `NO_FAMILY_MATCHES` (`c_offline_gate.py:298`); the split between the two is not recorded. |
| ROUTE, absent identifier | 4/4 | same | Confirmed. F22 notes the token `sro` appears on zero pages of the fixture, so this is fixture-easy. |
| ROUTE, present-edition control | 14/17 | same | Confirmed, but circular: the control queries `have` with the shelf's own family words (`c_offline_gate.py:317`), not question text. |
| RETRIEVE DOCUMENT | 6/17 verbatim, 8/17 with rewrites | same | Confirmed. Measures **family** rank, not document (`c_offline_gate.py:127`, `c_shelf.py:288`). 2 of 17 are automatic misses: evidence collapsed as a hash-duplicate is not mapped to its surviving twin (`c_offline_gate.py:266`). Measurable denominator is 15. |
| RETRIEVE PAGE | 25/57 = 43.9% | same | Confirmed. Measured with the **entire question text** as the in-document query (`c_offline_gate.py:150-151`), the same defect later fixed for the series walk and never re-run here. |
| Series walk | 1/4 | `corpus-lab/state/c_series_rerun.json` | Confirmed there. `c_offline_gate.json` and its REPORT copy still say 0/4; the two state files disagree. Sindh landed 2 of 15 editions at ranks 3 and 5; the other three landed none. |
| VERIFY | 27 correct, 0 wrong accepted, 3 abstain | `corpus-lab/state/evidence_v1/.../stage6_2_thirty_cells.json` | Confirmed. The file is gitignored, so the public architecture document cites an unpublished source. 12 of the 27 carry `KEY_VALUE_CONFLICTS_WITH_SOURCE`; the oracle audit (`stage2_2_oracle_audit.json`) resolves all 40/40 trajectory addresses as key-vs-printed-cell vintage divergence. |
| CLAUDE ANSWERS | 5/17 surfaced, 0/5 opened, 3 cited unopened | `corpus-lab/05_findings/FINDINGS_LIVE.md` F21 | Confirmed. |
| COVERAGE | 1,211 image-only | README.md, SOLUTION.md §2 | Confirmed. |
| evidence_v1 | 3/17 then 2/17 | `corpus-lab/state/evidence_v1/tuning_log.jsonl` | Confirmed. The 3→2 drop happened at the baseline re-verify (card regeneration nondeterminism), not from a tuning change. The log itself declares ±1 hit as noise. |
| corpus-wide page ranking | 0/17 in top-50 | `corpus-lab/state/rank_experiments.json` | Nearly. The term-coverage rerank strategy put rl_05 at rank 39; F23 reports that as 1/17. "0/17 across all 8" is slightly wrong. |
| full-page embedding | 8.2 pages/s | SOLUTION.md §2 | README.md:99 says "20.8 hours projected" for the harness. That is the ra-ship projection (614k pages). The harness figure is 40.9–46 h (SOLUTION.md; `plans_fable/B_HYBRID_MULTIQUERY_PLAN.md` §2.3). |

Additional facts established from code that the architecture document does not state:

- `find` fuses 2 lists per query (FTS5 top-200, vector top-200) by reciprocal-rank fusion and folds documents into families by max (`c_shelf.py:236-241, 273-288`). With 6 queries that is 12 lists, and the verbatim question appears twice in C2 (`c_queries.json`: `queries[0]` and rewrite 1 are identical), so it carries double weight.
- The card **embedding** text is `title | family | catalog[:1200]`, where `catalog` is contents text (up to 6,000 chars) followed by caption lines (`c_shelf_build.py:149, 315`). For any large publication with a contents page, the dense channel never saw a single caption. The lexical channel did (full `catalog` column).
- `inside` uses an exact phrase of the raw query string when it has ≤4 content words, AND of words when more, then OR fallback (`c_shelf.py:502-515`). A query like "sales tax 2023-24" as a literal phrase will not match a table where the label and the year are in different cells.
- Caption harvesting keeps the first occurrence of each caption text per document (`c_shelf_build.py:181`). Read-only count on the local shelf: 904 of 89,380 captions sit on pages < 15 (contents region), so contents-page pollution of the caption table is about 1%. 17,495 captions end in a digit because the regex ran into the year-header row on the same line; that is a fixture layout property.
- Per-question document ranks are computed but not persisted; only counts reach `c_offline_gate.json`. Family recall at 20/50/100/200 is therefore unknown.
- Of the 57 page-rank addresses, 40 belong to the four trajectory questions (`stage2_2_oracle_audit.json`: 40/40 trajectory addresses). The 43.9% is roughly 70% weighted to four questions.

## 2. What the current architecture gets right

- **Structural absence in ROUTE.** The only mechanism in four nights that answers "not here" correctly, and the reason is sound: it asks a yes/no inventory question rather than thresholding a score, which F22 disproved. Preserve it.
- **Document-first before page-first.** Empirically the better cut: family-level hybrid retrieval reaches 8/17 in the top 10, page-level lexical retrieval reaches 0/17 (or 1/17) in the top 50 of 1.2M. The hierarchy is justified by measurement, not elegance.
- **VERIFY with abstention.** 0 incorrect cells accepted on 30 is the right property. It is also the only box whose result is independent of retrieval.
- **Keeping A and B separate.** Correct, and the report already understood why. Supplying the gold document to B is the right confound control.
- **The caption hypothesis is the right kind of lead.** It is a label-versus-mention distinction, which is exactly what word frequency cannot make. The motivating "rank 6 of 8" observation is prose-only (no state file records it), but the direction is consistent with the series rerun.
- **The retry edge from VERIFY.** Untested, but cheap and clearly missing.
- **The refusal to run the paid battery** while the document box is at 8/17. Right call.

## 3. What we are wrong about

Ordered by how much each changes the experiments.

1. **Experiment B's baseline is not a measurement of the approach.** The 43.9% was produced by handing `inside` the whole question as its query (`c_offline_gate.py:150-151`). That is the exact defect the gate report §3 calls "defect one" for the series walk. The fix (`row_words_from_question`, `c_offline_gate.py:46`) was applied only to `run_series_only` (`:206`). The page-rank row was never re-run. A caption-channel gain measured against 43.9% would be confounded with the query fix.

2. **"Correct document" is measured as "correct family", and edition selection is not measured anywhere.** `find_doc_rank` maps evidence paths to families (`:127`); `page_rank_for` is then handed the gold file. The step between them, picking which of 15 editions to open, is skipped by the harness. For trajectory questions the series walk covers it. For point lookups with a year, it is untested, and it is not a single-target problem: a 2023-24 figure is printed in the 2023-24, 2024-25 and 2025-26 editions as budget, revised and actual. STOP_REASON.md states 7 of 17 questions need multiple documents; the oracle audit shows 16 distinct source documents across the four trajectory questions. The key names one address; a person would accept several.

3. **The absence control is circular, so the false-absence rate is unknown.** Absence questions are routed with question text minus the year; the control is routed with the shelf's own family string (`:317`). A question about a held publication phrased in the user's words can fall to `have`'s OR tier (`c_shelf.py:408`), land on the wrong family, and return `NO_EDITION_FOR` spuriously. Nothing measures that. Also, `NO_FAMILY_MATCHES` counts as an absence hit (`:298`), so part of the 11/11 may be "the search found nothing", which is not the structural check the document describes.

4. **Experiment A's "5–6 genuinely different rewrites" is not new.** That is configuration C2: five Haiku rewrites plus the verbatim question, fused by RRF. RRF is rank-normalised summation across lists (`c_shelf.py:241`); it rewards a document for appearing in every rewrite's list, the same consensus mechanism §3 warns about, bounded rather than absent. The rewrites also drift: rewrite 4 invents publication names ("Federal Board of Revenue Annual Report 2012-13", "Agricultural Statistics of Pakistan 2015-16 to 2023-24", "Administrative Reorganisation Report 2025-26", "Large Scale Manufacturing Industries Survey 2016-17", all in `corpus-lab/state/c_queries.json`). Whether they exist on the shelf is unknown; each injects generic words. The only new component in A is the reranker.

5. **A reranker experiment without a pool-recall pre-test repeats F23's mistake.** The lab's distinction ("a bad pool can't be rescued, a good pool might be") is correct in principle, but whether the fused pool is good is a number nobody has: family recall at 100 is not recorded. If the gold family is inside the top 100 for fewer than 12 questions, no reranker can reach 12/17 and the experiment is decided before it runs.

6. **The 17-question battery cannot support a 2-question conclusion.** The tuning log records that regenerating cards flipped the dev count by one with no code change. A move from 8 to 10 is inside that noise. Approach C was never run on the frozen 30-question holdout that evidence_v1 built (`_private/evidence_v1/holdout_frozen.json`, referenced in `REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md`). Any A result must be confirmed there, counts only.

7. **The semantic channel is weaker than the retraction implies, but that does not reopen the question.** The correction is right that card-scale embeddings were built and measured. What was embedded was title plus the head of the contents page; captions were truncated off for every large publication (`c_shelf_build.py:315`). So the honest statement is "title-plus-contents embeddings were measured", not "caption-aware embeddings were measured". Caption-line vectors (Plan B §2.3) remain untested. I list this in §5, below the reranker, not as a reason to re-run the same thing.

8. **The page metric rewards four questions.** 40 of 57 addresses are trajectory addresses. Report a per-question macro average alongside the micro rate, or B can pass by fixing one publication.

9. **Any future end-to-end value scoring will fail every trajectory question by construction.** The key's expected numbers for trajectories are later-vintage registry values; the printed cells differ on 40/40 addresses. Score the printed cell at the cited address, never the key's number.

10. **Smaller factual defects in the public record.** README.md:99 uses the ra-ship embedding projection for the harness. "0/17 across all 8 strategies" should be 0/17 for seven and 1/17 for the rerank strategy. The VERIFY row and §6's tuning-summary pointer cite gitignored files. The two gate state files disagree on the series number.

11. **Fixture-only properties presented as corpus properties.** 100% caption coverage on PDFs ≥100 pages, captions sharing a line with the year header, and `sro` appearing on zero pages are all properties of the generator. Real Pakistani publications often split "Table 2.4" and its title across lines, or print captions inside images. None of this invalidates the experiments; it bounds what a pass means.

What holds up on scrutiny: the ROUTE box and its reason for existing; the document-first cut; the separation of A and B; the caption hypothesis; the VERIFY contract; the decision not to spend money yet.

## 4. Already tested, do not repeat

Extends the prompt's §3. Items marked ★ are additions.

| idea | where tested | result | would repeating add information? |
|---|---|---|---|
| Dense embedding over document cards, fused with FTS5 by RRF | Approach C `find` | inside 6/17 and 8/17 | No. Only a different **unit** (caption lines) would be new. |
| Full-page dense embedding | `bench_embed.py`, Plan B §2.3 | 41–46 h CPU | No. Arithmetic. |
| Score threshold for absence | `probe_score_floor.json`, F22 | ranges overlap | No. |
| Identifier page-count as absence signal ★ | F22 | separates on n=3, fixture-specific, disqualified | No, unless on a corpus where the identifiers actually occur. |
| Multi-query, summed scores, card scale | tuning idea 2, iters 1–2 | worse | No. |
| Multi-query, max-not-sum, card scale | tuning idea 2, iter 3 | flat | No. |
| Multi-query rewrites, RRF, family scale ★ | Approach C config C2 | +2 (6→8) | Only as a per-rewrite diagnostic (which rewrite helps), not as a lever. |
| Alias widening | tuning idea 3 | 0 change | No. |
| Tightening the captionless detector | tuning idea 1, 3 variants | worse ×3 | No. |
| Caption-only lexical catalogue at corpus scale ★ | tuning idea 1 iter 1 (88,041 cards, row-label bug still live) | 2/17 dev, 1/30 holdout, address-level hit@24 | Not in that form. Its metric was stricter (path+page) and the label bug was live, so it neither proves nor rules out caption-unit retrieval at family scale. |
| Family walk without a query fix | tuning idea 5 | 0 gain | No. |
| Series walk with query fix | gate §3 rerun | 1/4 | No; only with a caption channel (Experiment B). |
| AND-first, OR-fallback query on the card catalogue ★ | STOP_REASON.md | 3/17→2/17 | No. |
| Candidate depth 100→500→1000 ★ | tuning idea 6 | 500 helped recall@120, 1000 added nothing | No. |
| Family-diversity slots, 3 pages/doc ★ | tuning idea 6 iter 4 | 0 change | No. |
| Crude page-level rerank by term count | F23 | 1/17 into top-50 | No. Different from a cross-encoder over a family pool, but only after the pool is shown to contain the answer. |
| Hook enforcement vs CLAUDE.md | night 2 | hook worse | No. |
| PDF MCP server, Recoll, search-server swap | night 2 | ruled out | No. |
| Stock tools on a plain folder ★ | night 2 s0 | 15/17 canaries, 0.167 questions | No. |
| Docling as bulk indexer | never run; rejected on the no-GPU and setup constraints | — | Not as bulk. See §10. |

## 5. Genuinely untested levers

**New components**

- Cross-encoder reranker over the fused family pool. New. Conditional on pool recall (§6).
- Caption channel inside a document: captions treated as a separate, higher-trust field in `inside`. New. Experiment B.
- Caption-line vectors as the dense unit (one vector per `Table N.N:` line, mapped to document and page). New representation, same model. Lower priority than the two above because it changes candidate generation, which needs the recall curve first.
- Structural edition selection: given a family and a year in the question, return the set of editions whose `fy_all` covers that year. New, tiny, uses only shelf fields. Fills the unmeasured gap in §3 item 2.
- VERIFY → retry edge. New.
- Extraction router by file type. New code, but not a retrieval lever.
- The live open-before-cite rule. Never run.

**New combinations of tested parts**

- Fused pool + reranker. The fused pool is C2; only the reranker is new.
- Caption channel + series walk. The walk is measured; the channel is new.
- The whole chain run as one deterministic pipeline offline. Every box measured alone; never chained.

**Not new, despite the label**: rewrites + RRF at family scale (that is C2); embeddings over cards (that is C1).

## 6. Experiment A: document retrieval

**Hypothesis.** A cross-encoder reranker over the already-fused family pool moves gold-family-in-top-10 materially, because the pool contains the gold family but ranks it below near-topic families.

**Baseline.** C2 as recorded: 8/17. Before any reranking, fix two scorer defects and re-record the baseline:

- Map an evidence path that was collapsed as a hash duplicate to its surviving twin using `docs.dupes` (the data is already stored). This turns the 2 automatic misses into measured questions.
- Persist per-question family rank for C1 and C2 (rank only, no path) so recall@k is a number.

**Pre-test A0 (decides whether A1 runs).** From the persisted ranks: gold family recall at 10, 20, 50, 100, 200 for C1 and C2, on the 17 and on the frozen 30-question holdout. Also per-rewrite recall@10 (each of the 6 queries alone, 2 lists each) and the "any single rewrite" ceiling. Cost: 30 Haiku rewrite calls for the holdout (Max quota), a few minutes of CPU. Decision rule: if C2 recall@100 on the 17 is below 12, a perfect reranker cannot clear the bar; do not build A1, record the recall curve as the finding, and the lever is candidate generation, not ranking.

**Candidate generation and pool.** Unchanged: existing `find` with the C2 queries, RRF k=60, family fold by max. Pool = top-100 families. 200 only if recall@100 < recall@200 by ≥2 questions.

**Reranker.** ONNX cross-encoder on CPU via fastembed, pinned: `Xenova/ms-marco-MiniLM-L-6-v2` (~80 MB). Preflight: it must order five hand-made unrelated pairs correctly and run ≥10 pairs/s; if not, `BAAI/bge-reranker-base` as the one alternative. Query = the verbatim question only. Passage per family = title of the best-scoring document, its fiscal year, and up to 8 catalog lines chosen by content-word overlap with the query (the same rule `_why_lines` already uses), capped at 350 words. Rerank score replaces the fused score for the clean test (A1). One optional blend (A1b): RRF of reranker rank and fused rank. No other variants.

**Query rewrites.** Not a new arm. Keep C2's rewrites for candidate generation only, because that is the measured baseline. If A0's per-rewrite diagnostic shows rewrite 4 (publication guess) never contributes a gold family, drop it in A1 and say so.

**Frozen metric.** Gold family in top-10, denominator 17 after the scorer fix, plus the same on the holdout 30. Report recall@10/20/50/100 for every configuration.

**Criteria.** Pass: ≥12/17 and holdout count ≥ C2 holdout + 3. Weak pass: 10–11/17 and holdout ≥ C2 holdout + 2. Stop: ≤9/17, or holdout does not improve, or A0 recall@100 < 12.

**Runtime.** 17 × 100 + 30 × 100 = 4,700 pairs; at 20–50 pairs/s, 2–4 minutes per configuration. Whole experiment including code: 2–3 hours.

**Contamination.** Ranks and counts only in any written output. The passage builder must contain no literal strings; review the diff for any title, label or year that is not derived from the question or the shelf. The executor should be an agent that has not read `stage6_2_thirty_cells.json`, `c_card_sample_100.csv`, `frozen20_key.json` or FINDINGS_LIVE.md's canary quotes; in this repository that is not achievable for any agent that has read the reports, so the mitigation is the diff review plus the holdout.

**Files.** New `corpus-lab/bin/c_rerank_gate.py` importing `c_shelf` and reusing `c_offline_gate`'s key access. `c_offline_gate.py`: dupe mapping in the on-shelf check, rank persistence, holdout run. `c_shelf.py` production path untouched until A passes.

**Is the 12/17 bar still right?** Yes as the clean bar; it was the pre-registered number. What changes is the denominator (17 measurable after the fix) and the added holdout condition. Without the holdout, 12/17 can be reached by noise plus overfitting to seventeen questions.

**Redundant or flawed parts of the proposal as written.** The rewrites arm is redundant (it is C2). Reranking whole cards is flawed (a 512-token model sees the contents page head, not the captions). Reranking before A0 is flawed (F23's lesson). "Compact reranker over top-100" is otherwise the right minimum.

## 7. Experiment B: page and table retrieval

**Hypothesis.** Inside the correct document, a page whose harvested caption matches the question's label words is the canonical table; pages that only mention the label in prose are restatements. Ranking caption-matched pages first raises the gold page into the top 5.

**Correct-document bypass.** As today: `page_rank_for` receives the key's evidence file. Unchanged.

**Baseline, three runs of one script.**

- B0: current code, full question as query. Must reproduce 25/57. Kept only to show the harness defect.
- B1: same code, query = `row_words_from_question(question)` (exists at `c_offline_gate.py:46`). This is the clean baseline. Nothing else changes.
- B2: B1 plus the caption channel. For the document, load its `captions` rows. A caption is a hit when it contains every label word (after the same `content_words` normalisation). Final ranking: caption-hit pages first, ordered by body BM25 among themselves, then the remaining body-ranked pages. Optional B3 only if B2 is worse than B1: RRF over the caption list and the body list.

That is the minimum clean ablation: B0→B1 measures the query fix, B1→B2 measures the hypothesis.

**Frozen metric.** Gold page rank ≤5 over the same 57 addresses (micro) and the per-question mean of hit rates (macro, over questions with PDF evidence). k=20 as today.

**Criteria.** Pass: B2 ≥60% micro and ≥60% macro. Weak: 50–59% on both. Stop: B2 ≤ B1 + 1 address, or macro falls while micro rises.

**Secondary, not gated.** Re-run `series` with the B2 ranking on the 4 trajectory questions and report editions landed, since `series` calls `inside`.

**Runtime.** Seconds per configuration; under an hour with code.

**Contamination.** The query rule is the existing generic regex; the caption match uses question words only; no label strings in code; outputs are ranks and counts. Preflight report: share of captions on pages <15 (1.0% by my read-only count), and the count of evidence documents that have zero captions (count only).

**Files.** `c_shelf.py`: `do_inside` gains an optional caption-channel argument, default off. `c_offline_gate.py`: a `--page-only` rerun with a query-mode switch and the caption flag.

**Known bound.** Where the question's words are not the caption's words (the public example from Plan B §2.1: "sales tax" versus "GST collection"), the channel cannot fire. That is expected and should be reported as the number of questions where no caption in the gold document matches the label words at all.

## 8. What each possible result means

**Experiment A**

- A0 recall@100 < 12: the pool does not contain the answer often enough. Stop the reranker. The lever moves to candidate generation: caption-line vectors or structural routing. This is a decisive, useful result.
- 8/17: reranker adds nothing to this pool. Abandon the reranker hypothesis. Do not try a bigger reranker.
- 10/17 with holdout up ≥2: weak. Keep the code behind a flag; do not build on it; run B and the chain metric before deciding.
- 10/17 with holdout flat: noise. Treat as 8/17.
- 12/17 with holdout up ≥3: pass. Combine with B in the offline chain (§9).
- 14+/17: check for leakage first (literal strings in the passage builder, rewrite cache contents), then proceed to the chain and, only after it, a paid battery.

**Experiment B**

- B1 ≈ B0 ≈ 44%: query formation was not the page problem; the restatement problem is real. Then B2 decides.
- B2 ≈ 44%: captions do not separate on this fixture. Abandon the hypothesis; the page problem needs table geometry or year-column matching, not labels.
- 50%: weak. Check macro. Likely a subset of publications benefit; report which count, not which names.
- 60%: pass. Wire into `series`, re-run the 4 trajectories; the series bar (3/4) becomes testable.
- 70%+: pass, and it says page selection is solvable once the document is right. Priority shifts entirely to A and edition selection.

**Combine A+B** only when both pass, via the chain metric. If A stops and B passes, the system is "right page given right book"; the open problem is unchanged and correctly located. If A passes and B stops, the next lever is EXTRACT-side table detection on the top-5 pages, which is where Docling enters (§10).

## 9. End-to-end metric check

The three proxies are necessary and not sufficient. They miss: edition selection (nobody measures it), the printed-versus-key vintage issue, and whether a chain of top-k choices actually lands on a verified cell. They also reward family rank for questions whose answer legitimately lives in several editions.

Add exactly one: **offline chain hit**. For each of the 20 frozen questions, run deterministically with no model: `find` → top-3 families → structural edition set by year (all editions if the question names none) → `inside` top-5 pages per edition → VERIFY on those pages with the question's label words. A hit is any verified record whose address is a key address and whose value equals the **printed** cell. For the 3 absence questions, a hit is ROUTE saying no edition and the chain producing zero verified records. One count out of 20, free, and it measures the arrow the document says was never run. Keep the diagnostic metrics; they say which box broke.

The paid version ("opened before cited", Plan B §6) stays the live metric for later.

## 10. Docling and OCR decision

**Not yet for retrieval; a 30-page EXTRACT benchmark after A and B.**

Reasons. Perfect extraction of the wrong document is worthless, and the document box is at 8/17. The one place Docling has a measured target today is VERIFY's 3 abstentions, where the oracle audit found the row label's glyphs overlapping the first data column in the text layer. That is a table-structure problem, exactly Docling's job, and it is independent of retrieval. The right test is: run Docling on the 30 audited pages (3 abstained plus 27 verified), CPU, single pages, and count agreement with the verified cells and whether the 3 abstentions resolve. About an hour, no corpus pass, no model download beyond Docling's own weights. Do it after A and B so it does not consume the free hours that decide the retrieval question.

Rejecting Docling as the bulk indexer stands: setup time and the no-service constraint, not quality. Not reconsidering it once the failure became table geometry was a gap; the benchmark above closes it cheaply.

OCR: do not build. First count the image-only share of the real folder with one `pdftotext` pass. That is a coverage measurement the project has said for four nights nobody has taken.

## 11. Architecture amendments

**Amendment 1**
CURRENT: one box, RETRIEVE DOCUMENT, "pick the one publication/edition".
CHANGE TO: two steps. RETRIEVE FAMILY (fuzzy, what `find` does) then SELECT EDITIONS (structural: the set of editions whose `fy_all` covers the question's year, all editions for a series question, primaries only). The output is a set, not a winner.
WHY: the gate already measures family, not document (`c_offline_gate.py:127`); edition choice is measured nowhere; 7 of 17 questions need several documents (STOP_REASON.md); a year's figure is printed in several editions with different vintages, so a single "correct document" is the wrong target for point lookups.
DECISIVE TEST: for the 17, is the gold edition inside the structural edition set (set recall, counts only), and what is the set's mean size. If set recall is high and the set is small, the box is replaced; if the set is large, edition ranking is a real sub-problem and needs its own experiment.

**Amendment 2**
CURRENT: ROUTE absence measured with a control that uses shelf-internal family names.
CHANGE TO: no box change; a symmetric control. For each doc-level absence question, replace the year with one the best-matching family holds (from the shelf's own `fy_list`) and require `EDITION_PRESENT`. Also record the `NO_EDITION_FOR` versus `NO_FAMILY_MATCHES` split.
WHY: the current control cannot detect a false absence caused by `have`'s OR tier resolving the wrong family; `NO_FAMILY_MATCHES` currently counts as success.
DECISIVE TEST: the symmetric control count, 11 questions, free.

**Amendment 3**
CURRENT: RETRIEVE PAGE baseline of 43.9%.
CHANGE TO: no box change; re-baseline with the short query (B1) before any caption work.
WHY: the recorded number was measured under a query-formation defect the report itself identified and fixed elsewhere.
DECISIVE TEST: B0 versus B1.

**Amendment 4**
CURRENT: 2 of 17 questions excluded from document ranking because their evidence was hash-collapsed.
CHANGE TO: map collapsed paths to their surviving twin in the scorer.
WHY: the data exists in `docs.dupes`; the exclusion is a scorer defect that hides two measurable questions.
DECISIVE TEST: re-run C1/C2 with the mapping; the counts move or they do not.

No other box or arrow changes are justified before the experiments. The ROUTE box, the document-first cut, VERIFY, and the retry edge stay as drawn.

## 12. Execution order

1. Scorer fixes: dupe mapping, per-question rank persistence, holdout support. ~30 min.
2. A0: recall curves for C1 and C2 on 17 and holdout; per-rewrite diagnostic; edition-set recall (Amendment 1's test); symmetric absence control (Amendment 2). ~45 min. Everything here is decisive on its own.
3. B0, B1, B2 on the 57 addresses, micro and macro. ~1 h.
4. A1 only if A0 recall@100 ≥ 12. ~1–2 h including the reranker preflight.
5. `series` rerun with B's winner. ~10 min.
6. Offline chain hit on the 20, if A and B both at least weak-pass. ~1 h.
7. Write F41 and F42 with counts only, and correct the four factual defects in §3 item 10.

Docling's 30-page benchmark and the real-folder image-only count come after, in either order. No paid session in this sequence.

## 13. Final verdict

**RUN THEM WITH THESE SPECIFIC AMENDMENTS.**

Both experiments test the right things, but as written each would produce an uninterpretable number: A's rewrites arm is a re-run of C2 and its reranker has no pool-recall pre-test; B's baseline was measured under the query defect the report itself fixed for the series walk. Fix the scorer, measure the recall curve, re-baseline B with the short query, then run the reranker and the caption channel. Confirm anything that moves on the frozen holdout, because seventeen questions cannot carry a two-question conclusion.

---

## Educational appendix: what this system is in established terms

*Not part of the verdict. This does not change the recommendations above.*

**The whole thing.** You have built a two-stage, hierarchical retrieval-augmented question answering system over a versioned document collection, with a grounded-generation policy and selective abstention. Each of those phrases has a literature.

**Your boxes, by their usual names.**

- SHELF: a *bibliographic catalogue* or *document-level index*. Your family / edition / copy structure is close to the library world's FRBR model (IFLA, 1998): Work (the publication), Expression or Manifestation (the yearly edition), Item (each file copy). Grouping copies by hash is *exact deduplication*; grouping editions by normalised title is *near-duplicate detection* or *record linkage* (Broder's shingling, 1997; Charikar's SimHash, 2002, are the classic tools you did not need because titles were enough).
- ROUTE: *query intent classification* and *query routing*. The exact-identifier path is *known-item search*; the named-publication-plus-year path is an *inventory lookup*; the series path is *implicit temporal query* handling. Your discovery that a score cannot signal absence is a known hard problem called *query performance prediction* (Carmel and Yom-Tov's 2010 survey), and the QA version is *answerability detection* (SQuAD 2.0, Rajpurkar et al., 2018).
- RETRIEVE DOCUMENT: *first-stage retrieval* or *candidate generation*, specifically *hybrid retrieval*: sparse BM25 plus a dense bi-encoder (bge-small) fused by *reciprocal rank fusion* (Cormack, Clarke and Buettcher, 2009). Your column weights `bm25(cards, 3, 3, 2, 1)` are a hand-rolled *BM25F* (Robertson, Zaragoza and Taylor, 2004). Folding documents into families by taking the best member is the *MaxP* aggregation rule (Dai and Callan, 2019). The "reserved family slots" in evidence_v1 are *result diversification*, first formalised as Maximal Marginal Relevance (Carbonell and Goldstein, 1998).
- RETRIEVE PAGE: *passage retrieval* and, with a reranker, *retrieve-then-rerank* (Nogueira and Cho, 2019). Treating captions as a trusted field is *field boosting*, and the specific task of finding a table by its caption and headers is *ad hoc table retrieval* (Zhang and Balog, 2018). Deciding whether to return the document, the section, or the table is what the XML retrieval community called *element retrieval* (the INEX evaluations, 2002 onward).
- EXTRACT: *document layout analysis* and *table structure recognition*. Docling, Camelot and pdfplumber are all tools in that field.
- VERIFY and CLAUDE ANSWERS: *attributed question answering* (Bohnet et al., 2022) with *citation verification* (Gao et al., ALCE, 2023); abstaining on ambiguous cells is *selective prediction*. The evidence record with hash, page, bbox and unit is *provenance*.

**Your measurement apparatus.** Frozen questions with judged evidence addresses is a *test collection* in the Cranfield tradition; the key is the *qrels*; decoys in `must_not_cite` are *hard negatives*; canaries are *needle-in-a-haystack* probes; the frozen 30 is a *held-out set*; stating gates before numbers is *pre-registration*; what you keep flagging is *test-set leakage*.

**Where you match convention.** Hybrid sparse-plus-dense with RRF, hierarchical document-then-passage retrieval, a cross-encoder only over a small pool, grounded answering with abstention, and a frozen holdout. All standard, all arrived at from first principles. The Anthropic contextual-retrieval note the research pass cited is the same idea as your cards carrying family and year.

**Where you depart, and it is a defensible departure.** Standard RAG chunks pages and ranks chunks. You concluded from measurement that for this corpus the right unit is the document, then the table. That matches a smaller literature on *dense hierarchical retrieval* and is the better fit for a collection where the same text recurs across editions.

**The technique you were missing by name: temporal information retrieval over versioned collections.** Your central problem, near-identical yearly editions and questions with implicit time ("over the last decade"), is a well-studied one. The survey to read is Campos, Dias, Jorge and Jatowt, "Survey of Temporal Information Retrieval and Related Applications", ACM Computing Surveys, 2014. The ideas that map directly:

- *Temporal query intent*: classify whether a question carries an explicit time, an implicit one, or none, and resolve it to a year range before ranking. Your ROUTE box is halfway there.
- *Time-aware ranking*: rank with a time prior, not only text similarity (Berberich, Bedathur, Alonso and Weikum, "A Language Modeling Approach for Temporal Information Needs", ECIR 2010). This is the formal version of "the question names no year, so rank by structure, not similarity".
- *Versioned document indexing*: index the collection as one document with many versions, not many documents (Anand, Bedathur, Berberich and Schenkel's work on temporal indexes for web archives and Wikipedia revisions, SIGIR 2011 and after). Your family-plus-fiscal-year key is exactly a version key.
- *Data vintages*: economists already have the concept you kept rediscovering, that a 2016-17 figure exists as budget, revised and actual across three editions. The St. Louis Fed's ALFRED archive is the reference implementation: every series is stored with the date each value was published. Your oracle audit's "printed cell versus registry value" is a vintage mismatch, and the right answer to a series question is a vintage-labelled table, which is what Amendment 1 turns RETRIEVE DOCUMENT into.
- *Dataset search*: retrieving statistical tables by what series they hold rather than by prose is its own field (Chapman et al., "Dataset search: a survey", VLDB Journal, 2020).

**What you learned without knowing you had.** That rank fusion beats score summation; that field weighting matters more than vocabulary; that diversification is needed when a corpus repeats itself; that a reranker cannot fix recall; that answerability cannot be read off a score; that document-level retrieval can succeed where passage-level fails; that vintages are a first-class dimension of the data; and that a test collection with pre-registered gates is the only thing that stopped four nights of plausible ideas from being reported as progress.
