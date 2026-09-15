# retrieval-lab

**The question:** can you point Claude Code at a folder of ~15,000 research PDFs, ask a
vague question in ordinary language, and get back the actual number with the file and page
it came from — and an honest "not in here" when the answer genuinely isn't?

**Answer so far: structural honest refusal works, and B2c can find the right page once the
right document is known. The unresolved end-to-end problem is selecting that document from a
vague question.** Six nights, twelve pre-registered gates, and five live Claude Code batteries
produced one full holdout-confirmed pass (B2c), a passing citation-guard sub-arm, and a WEAK
Experiment H result; timeout, evaluator, and variance findings qualify the live headline metrics.
This repository is the full record — code, measurements, failures, and the diagnosis.

> ### 👉 New here? Start at [`REPORT/README.md`](REPORT/README.md)
>
> ### 👉 Picking up the work? Start at [`REPORT/08_what_next/SESSION_LOG_2026-09-13_to_09-14.md`](REPORT/08_what_next/SESSION_LOG_2026-09-13_to_09-14.md)
>
> That file is the full handover: six execution phases, twelve pre-registered gates, the
> Claude session transcripts verbatim with timings and accuracy, the current state of every
> box, and an operating manual (Appendix C) with a runnable command for every number below.
>
> It walks the whole project start to finish in plain English, written for someone who has
> never seen this repo. Everything else here is supporting evidence.
>
> Every number on this page is traceable: [`REPORT/MANIFEST.md`](REPORT/MANIFEST.md) maps
> each report to its source file and checksum, and
> [`corpus-lab/state/progress.jsonl`](corpus-lab/state/progress.jsonl) is an append-only
> log with one line per step across all four nights.

---

## Status

| | |
|---|---|
| ✅ **Solved** | Getting the model to *use* a tool you give it. One line in `CLAUDE.md` moved index adoption from 0 of 38 sessions to 38 of 38. A hook that *forced* the same thing scored slightly worse. |
| ✅ **Solved** (disputed 2026-09-15 am, **restored the same day** — see F53) | Knowing when material genuinely isn't there — **11/11** on absent editions and **4/4** on absent identifiers, via a structural check ("do I hold any edition of this publication for that year?"). Every earlier approach scored **0/3**. Note this is a property of approach C's shelf, not of a shipped system. **2026-09-15, and this is the useful part of the story:** an overnight live battery scored this 1 of 15 and the deterministic chain 1 of 3, putting the whole claim in doubt. Both were measurement defects. The scorer counted the shelf's own quoted edition lists as invented figures — no absence session invented a number, not once in fifteen — and the chain had no path for identifier-level absence, which is 2 of the 3 questions it scored. Repaired: **11 of 15 live**, and ROUTE re-derives **11/11 and 4/4** from a second implementation. Both numbers are published; the old one is labelled SUPERSEDED-BY-SCORER-REPAIR, not deleted (F53). |
| 🟡 **Built, trustworthy, retrieval-independent** | Coverage accounting over 15,010 files, content hashing, provenance records, geometry-aware table-cell verification, a typed evidence compiler, safe install/teardown, and test suites. None of it depends on which retrieval idea eventually wins. |
| ❌ **Not solved** | Putting the right page in front of the model for a vague question. The primary retrieval loss is still document selection: across four Sonnet live batteries, the right publication did not surface on **9 to 11 of 17** questions and the right page was cited on **0 to 2**. Those live headline metrics need qualification: the 300-second harness cap can turn a found answer into a miss, strict single-gold-address scoring can reject credible official alternatives, and direct Sonnet/Opus probes were qualitatively stronger. Two sub-problems are solved — the right *page* inside a known-right document (82.7% on a holdout) and preventing citations of unopened **file paths** (10 → 0) — and neither has yet moved the measured live outcome. Experiment H's clean confirmation is a **WEAK** document-selection gain: **11/17** dev and **17/30** holdout-2, against frozen **10/17** and **14/30**; it is not adopted. |

### The primary open retrieval problem

This corpus republishes the same fiscal tables every year across dozens of near-identical
editions, *and* restates each year's figure in prose on many pages inside each edition. A
vague question's words match hundreds of candidates about equally, and the question usually
doesn't name the year it wants ("over the last decade or so").

That makes this a **disambiguation** problem, not an indexing or vocabulary problem — which
is why better word matching, query rewrites, wider aliases and deeper candidate pools all
measured out to approximately zero. It shows up at both scales: across the corpus (the right
page sits at rank ~500–3,000 of 1.2 million) and *within* a single correct document (the
canonical table ranks 6th behind five prose restatements of its own subject).

It is not the only open problem in the project. Evaluator completeness for alternate official
sources, the 300-second live timeout, citation validation for prose title/page citations, and
run-to-run variance all now limit how confidently the measured live numbers can be read.

| approach | best measured result | bar |
|---|---|---|
| stock tools / index / index+hook | 0.167 / 0.235 / 0.176 question recall — all inside noise | — |
| eight lexical query strategies | right file in global top-50: **1 of 17** (the term-coverage rerank; 0 for the other seven) | — |
| `evidence_v1` table catalogue | **3/17**, then **2/17** after 13 measured tuning iterations | 10/17 |
| approach C "shelf" (document-first) | right *document* in top-10: **6/17** (**9/17** with 5 paraphrases) — CORRECTED 2026-09-14, was 8/17 with 2 questions wrongly excluded | 12/17 |
| approach C, the same pool at depth 100 | right document **in the pool on 16 of 17** — NEW; the loss is ranking, not coverage | — |
| approach C + a compact cross-encoder reranker | **9/17** — NEW, gate STOP: it recovers what it cost and nothing more | 12/17 |
| approach C, multi-year trajectory walk | **1/4** editions-walk correct — and the metric measures which *copy* the shelf calls primary, not page retrieval | 3/4 |
| approach C, right *page* once document is right | **52 of 57 (91.2% by address, 82.1% by question) dev and 67 of 81 (82.7%) on the holdout** — NEW 2026-09-15 pm, **gate PASS and adopted into production**; was 24 of 57 with lexical matching | 60% + 60% |
| approach C + caption-aware page retrieval | **42 of 57 (73.7%)** — NEW, but *all* of the gain is on trajectory questions and none elsewhere | 60% |
| approach C, structural edition selection | **3/17** — NEW; the year a question asks for is usually not the year on the document that answers it | 15/17 |
| approach C + per-query selection instead of rank fusion | **5/17** — NEW 2026-09-15, gate STOP: the best-supported untried idea in the repo, and it is worse than the fusion it replaced | 12/17 |
| approach C + a caption-line retrieval channel (89,380 captions) | **10/17** dev, **14/30** holdout — NEW 2026-09-15, gate STOP. Below the top ten it is the biggest document-channel gain yet measured (holdout recall@100 28 → 29) | 12/17 |
| the same caption channel, plus caption embeddings | **9/17** dev, **13/30** holdout — NEW 2026-09-15, gate STOP: dense dilutes a short table title | 12/17 |
| approach C, year-aware caption page rule | **42/57, 39.7%** — NEW 2026-09-15, identical to the plain caption rule at every address; on all 6 year-asking questions *no caption matches the subject words at all* | 60% + 60% |
| approach C, vintage-tolerant trajectory walk | **strict 12/24, tolerant 14/24** — NEW 2026-09-15, WEAK. 10 of the 14 hits come from a *later* edition than the year asked about | 16/24 |
| approach C, content-based edition selection | **3/10**, mean set size 2.0 — NEW 2026-09-15; a small, confident, wrong set | 8/10 |
| **approach C, live Claude Code battery on the frozen configuration** | **surfaced 8/17, opened the right page 1/17, cited the right page 0/17, cited a file it never opened 5 times, honest-refusal 1/15** — LIVE 2026-09-15, both gates FAIL. All 17 sessions *did* open pages; they opened the wrong ones | see F50 |
| approach C, dense caption ranking **inside** the right document (B2c) | **52 of 57 (91.2%) dev, 67 of 81 (82.7%) holdout** — NEW 2026-09-15 pm, **gate PASS**, the first holdout-confirmed pass in the project; gain spread across question types, not trajectory-only | 60% + 60% |
| approach C, live re-battery with one instruction changed | L1 loss class 4 → 2 and **cited-the-right-page 0 → 2**, the first ever; but cited-a-file-never-opened 5 → 8, so **gate STOP** and the change is kept unadopted | see F56 |
| approach C, caption similarity as a **document** reranker (G) | **9 of 17** against the frozen 10 — NEW 2026-09-15 evening, gate STOP; improves 4 questions and worsens 11. Fourth result showing captions discriminate *within* a document and dilute *across* the corpus | 13/17 |
| approach C, edition selection using the better pages (ED3) | **3 of 10**, mean set 2.0 — identical to the previous rule despite page retrieval going 42 → 52 of 57; the pages found are the right kind in the wrong edition | 8/10 |
| approach C, whole pipeline end to end (chain v2) | **8 → 5 → 3 of 17 verified**, absence **3/3** — NEW 2026-09-15 evening; a page fix worth +10 of 57 in isolation is worth +1 of 17 in the chain | — |
| approach C, third live battery (tool-enforced citation) | `note` now refuses a page you did not open — and **answers citing an unopened file rose 8 → 10**, because the gate guards the note and the answer does not pass through it. Gate STOP | see F59 |
| **approach C, the model picks the publication from the top-100 pool (H)** | clean confirmation: **11/17** dev, **17/30** holdout-2 against frozen **10/17**, **14/30** — **WEAK**, not adopted. The earlier clean dev sample was 14/17, so identical runs spread by 3/17; this is a modest gain, not a breakthrough | 13/17 + holdout |
| approach C, asking the model to *name* the publication instead | **1 of 17** — selecting from a list works, generating a title does not | — |
| approach C, fourth live battery (citation guard on the answer) | citations of **unopened file paths**: **10 → 0**, six blocks in six of twenty sessions — the third attempt and first mechanical pass. Title/page-style citations can bypass the path matcher. **Right page still cited on 1 of 17** | see F62 + session-log Appendix A |
| approach C, shelf latency (Phase 9.1) | `open` **2.95 s → 0.18 s**, `coverage` **2.89 → 0.17 s**, `find` 4.14 → 1.15 s, `series` 4.52 → 1.22 s — warm-vs-warm, old code restored from git. Rank-preserving and proved: 300/300 pages byte-identical, caption vectors 200/200 at cosine 1.0, `inside` top-5 identical on 57/57. NEW 2026-09-16 | Gate 1 PASS |
| approach C, shelf v2 (family merge, year normalisation, consensus primary) | families 1,618 → 1,512; duplicate publications occupying top-40 slots **35 → 0** across 17 dev lists; every recall row held exactly. **Gate S STOP** on one structural row — gold files hidden as non-primary **20 → 31**, because giving 4,333 documents an edition flipped their clusters from “show every copy” to “one primary, hide the rest”. Not tuned; production stays on v1. NEW 2026-09-16 | see F66 |
| approach C, showing the model 40 candidates instead of 12 (`find --compact`) | the gold publication is inside the list shown on **11/17 at depth 12** and **14/17 at depth 40** — the old display capped the whole chain at 11 before the model read a word. Experiment H's mechanism, shipped in-session at zero extra model calls. NEW 2026-09-16 | recorded, not gated |
| approach C, the harness itself as a loss source | **1–5 sessions per battery produced no answer text at all** because a 25-turn cap or 300 s clock fired, and every one was scored a miss. Raised to 60/900: **0 of 40** sessions lost across both Phase 9 batteries, with 11 of them running past the old limits. CORRECTED 2026-09-16 | see F65 |
| approach C, scorer v2 (equivalence to the same cell) | the key lists acceptable alternates on **45 of 135** questions and the scorer read none of them. Re-scoring P5–P8 on the same recorded transcripts: strict **0/2/1/1** → equivalence **6/4/9/4** of 17. Registry validated at 322/332 gold addresses (0.970). CORRECTED 2026-09-16 | see F68 |
| **approach C, fifth live battery — realistic limits, both models (LIVE-5)** | **cited_right_page_equiv 13/17 (Sonnet) and 14/17 (Opus)**, the best live citation reading the project has taken; strict 1/17 and **3/17**, beating the old record of 2/17. But **value_correct is 5/17 for both** — it finds the page far better than it reads the number, and on decade-long questions it opened 4 of 4 right pages and got 0 of 4 totals right. **Gate STOP on both**, each on one condition: citing a file never opened (Sonnet 1, Opus 7). NEW 2026-09-16 | PASS ≥ 5 equiv **and** 0 unopened |
| approach C, one-command installer on a fresh folder | cold install of a 500-file folder in **141 s** (bar 20 min); self-test **18/18** from inside it; one live question cited two pages it had opened, guard `n_cited_unopened=0`. **Gate P PASS**. NEW 2026-09-16 | see F64–F69 |

> **Extended 2026-09-16 — production hardening night.** The tool got between 3 and 17 times
> faster with every rank proved unchanged; two *measurement* defects were found and fixed (the
> harness was killing 1–5 sessions a battery before they answered, and the scorer was stricter
> than its own answer key); and the model is now shown 40 candidate publications instead of 12.
> Under those conditions the fifth live battery reads **13 and 14 of 17** on cited-right-page
> equivalence — the best the project has measured — while **both gates still STOP**, each on a
> single citation of a file the session never opened, and the right *number* is still only
> **5 of 17**. One planned change, shelf v2, was rejected by its own pre-registered gate and not
> tuned. See
> [`REPORT/08_what_next/HANDOFF_2026-09-16_night.md`](REPORT/08_what_next/HANDOFF_2026-09-16_night.md),
> [`REPORT/08_what_next/DEMO_2026-09-16.md`](REPORT/08_what_next/DEMO_2026-09-16.md) and
> [`INSTALL_FOR_SIR.md`](INSTALL_FOR_SIR.md).

> **Extended 2026-09-15 — the first live battery, and the first end-to-end run.**
> Six more pre-registered gates were read and **all six STOPped or FAILED**; no bar was moved.
> The headline change is not a score, it is a diagnosis: 32 real Claude Code sessions show the
> agent *following* the open-before-cite rule and still opening the wrong pages, and the
> honest-refusal number — long the one solved thing here — scores 1 of 15 under a scorer whose
> own transcripts say 14 of 15 found the right verdict. Which of those is true is the next
> experiment. See
> [`REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md`](REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md)
> and [`REPORT/08_what_next/HANDOFF_2026-09-15.md`](REPORT/08_what_next/HANDOFF_2026-09-15.md).

> **Corrected and extended 2026-09-14.** An adversarial review found four defects in the
> harness behind the approach-C rows; every historical number still reproduces exactly from
> the original code path, but several were measurements of something other than what they
> were read as. The review is at
> [`REPORT/08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md`](REPORT/08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md),
> what replaced it at
> [`REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md),
> and the phase in twelve plain answers at
> [`REPORT/08_what_next/HANDOFF_2026-09-14.md`](REPORT/08_what_next/HANDOFF_2026-09-14.md).

---

## Where independent review would help most

If you are here to suggest improvements, these are the live questions, in rough order of
how much they matter. **Arguments that the framing itself is wrong are as welcome as
arguments within it.**

**1. Establish whether the measurements can be trusted.** The next work should first measure
run-to-run variance, inspect all timed-out sessions, audit strict-gold scoring against credible
alternate official sources, and run one comparable longer-cap battery on Opus. The current
headline live metrics partly measure the harness and an incomplete evaluator, not just retrieval.

**2. The disambiguation problem above.** Given hundreds of near-identical yearly editions
and a question that doesn't name a year, how do you pick the right one? Every lexical idea
tried has failed, each with a traced reason rather than a shrug. See
[`REPORT/README.md`](REPORT/README.md) §6–7.

**3. Transfer the solved page signal to document selection.** B2c now uses dense caption ranking
inside a known-right document, passed its holdout gate (**52/57** dev; **67/81**, 82.7%, holdout),
and is adopted. The unresolved question is why captions distinguish the right table *within* a
document but dilute across the corpus: Experiment G's document-level caption reranker stopped at
9/17. Stage 1 harvested **89,380 explicit `Table N.N:` caption lines**, with 100% coverage of
PDFs ≥100 pages (1,895/1,895).

**4. Grounding and citation validation.** The live `note`-requires-`open` check stopped because
the answer bypassed the note; the later answer-boundary guard eliminated citations of unopened
*file paths* (10 → 0). Quote-before-cite validation and coverage of prose title/page citations
remain untested.

**5. Is the table-card framing wrong at the root?** Honest self-assessment at the end of
[`REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md`](REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md).

**6. Coverage nobody has measured.** 1,211 files (8% of the fixture) are image-only PDFs
unreachable without OCR. Nobody has checked the equivalent share in the real target folder,
and bulk OCR over numeric tables is unmeasured here.

### What has already been tried — please don't re-propose these

Each was measured, and the reasons are written up:

- **Dense/semantic embedding over the small card pool.** Approach C built it: BGE-small
  vectors over 12,760 document cards (28 minutes, 7.6 cards/s), fused with FTS5 top-200 by
  reciprocal-rank fusion, plus query rewrites. **It is inside the 6/17 and 9/17 numbers
  above.** Semantic retrieval at card scale is tested, not untried. A compact cross-encoder
  reranked on top of it on 2026-09-14 and failed its gate — see
  [`REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md)
  and [`REPORT/08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md`](REPORT/08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md).
- **Full-page dense embedding** — 8.2 pages/s measured, **40.9–46 hours** for this harness's
  1,206,260 pages, no GPU. (The 20.8-hour figure quoted here until 2026-09-14 was the
  projection for the smaller ra-ship fixture, not for this corpus.)
- **A relevance-score threshold for absence** — disproven; absent and answerable questions
  score in the same range ([`probe_score_floor.json`](REPORT/03_night3_rescore_and_rank/probe_score_floor.json)).
- **Multi-query fusion by summation** — rewards documents for repeating shared generic
  words; traced concretely on one question.
- **Forcing tool use with a hook** rather than asking in `CLAUDE.md` — measured slightly worse.
- **A PDF MCP server** (415 s for five small PDFs), **Recoll** (no headless installer),
  and **swapping in a search server** (does not repair candidate representation).

> ⚠️ **The `Shelf V2` recommendation in
> [`RESEARCH_2026-09-13.md`](REPORT/08_what_next/RESEARCH_2026-09-13.md) is superseded.**
> It named semantic retrieval over the card pool as the main untested lever; approach C had
> already measured that route and failed its gate. The correction is
> [`REPORT/08_what_next/CORRECTION_2026-09-13.md`](REPORT/08_what_next/CORRECTION_2026-09-13.md).
> The research body is kept unchanged as the historical recommendation. Future work should
> be a separately specified, offline-gated ablation on the existing shelf — not a rebuild
> of the same architecture.

---

## Layout

```
REPORT/              the walkthrough + copies of every report, in reading order. START HERE.
  00_orientation/      what the project is, the brief, the tool matrix
  01..03/              nights 1-3: stock tools, the six-approach bake-off, offline re-scoring
  04..05/              evidence_v1: the build, its honest stop, and the tuning loop
  06_approach_c_shelf/ the document-first shelf: build, self-test, full Stage 3 gate report
  07_approach_b_planned/  hybrid multi-query — specified, never built
  08_what_next/        the research pass AND the correction that supersedes it
  09_ledgers/          every finding, every step, and the cold-start guide
INDEX.md             the original repo map and ground rules
SOLUTION.md          the evidence_v1 design rationale
BUILD_PROMPT.md      the staged contract evidence_v1 was executed against
RESEARCH_2026-09-13.md   the research pass (recommendation superseded — see above)
EXECUTE_SHELF_V2.md  its build contract (likewise superseded; kept for the reasoning)
00_brief/            the task as given, incl. SOLVE_BRIEF.md for an outside designer
plans_fable/         two further approaches; C was built, B never was
corpus-lab/          all code, findings and run state
  bin/                 the instruments (measurement primitives, index builder, scorers)
  evidence_v1/         the table-catalogue engine runtime
  tests/               its test suites
  05_findings/         FINDINGS_LIVE.md — every finding with the condition it holds under
  state/               machine-readable run state; progress.jsonl is the audit trail
```

## What is deliberately not in this repository

- **`_private/`** — answer keys, canary manifests, and 189 recorded measurement sessions.
- **`harness/`** — the four generated fixture corpora *and* their generator. The generator
  (`finalize_key.py`, `canary_slots.py`, `plant_canaries.py`, `plan.py`) manufactures the
  answer key, so shipping it ships the key.
- **`ACCEPTANCE.md`** — an oracle in prose: gold source paths, literal cell values, page
  indices. Its *criteria* are fully described in `BUILD_PROMPT.md` and `SOLUTION.md`, both
  published here; only the expected answers are withheld.
- **Derived indexes** — a ~7 GB FTS5 page index, the shelf database, card vectors. All
  rebuildable from code that *is* here.

> ⚠️ **If you intend to re-run the benchmark, read this first.** Some answer-derived
> material was published in earlier commits and is still present: 13 canary phrases quoted
> as evidence in `FINDINGS_LIVE.md`, 21 gold evidence paths in `state/c_card_sample_100.csv`,
> and a handful in `probe_score_floor.json` and `rescore_from_results.json`. They were left
> in place because scrubbing them means rewriting public history and stripping verbatim
> evidence out of the night-1 findings. **Reading this repository therefore contaminates
> you — or an agent you point at it — for re-running the measurement.** Reviewing the
> design and the reasoning is unaffected.

## Reproducing anything

Every path derives from `corpus-lab/bin/labpaths.py`; no script hardcodes a location.
`corpus-lab/RESUME.md` is the cold-start guide, including the traps worth not
rediscovering (several cost a full night to find).

The fixture corpora are not here, and regeneration is **banned**: the generator's own
determinism check failed — 6,060 of 6,064 files reproduced — so rebuilding would silently
change the ground truth. Results here are reproducible in reasoning and in code, but not
bit-for-bit re-runnable without the archived corpora.

**A note on how results are reported.** Findings carry the condition they hold under, gates
state their bar before the number, and several headline figures in this repo were revised
*downward* on review — the night-1 conclusion was overturned, the night-2 recall numbers
were superseded by a re-score, and approach C's trajectory result moved after a bug was
found in the test itself. Where a number is contested or superseded, both versions are kept.
