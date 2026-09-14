# retrieval-lab

**The question:** can you point Claude Code at a folder of ~15,000 research PDFs, ask a
vague question in ordinary language, and get back the actual number with the file and page
it came from — and an honest "not in here" when the answer genuinely isn't?

**Answer so far: the honest-refusal half works. The find-the-right-page half does not,
and we now know fairly precisely why.** Four nights, five approaches measured end to end,
three more ruled out on measurements rather than opinion, about $31 spent. This repository
is the full record — code, measurements, failures, and the diagnosis.

> ### 👉 Start at [`REPORT/README.md`](REPORT/README.md)
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
| ❌ **Not solved** | Putting the right page in front of the model for a vague question. **Every approach has failed this**, and the numbers have barely moved in four nights. |

### The one open problem

This corpus republishes the same fiscal tables every year across dozens of near-identical
editions, *and* restates each year's figure in prose on many pages inside each edition. A
vague question's words match hundreds of candidates about equally, and the question usually
doesn't name the year it wants ("over the last decade or so").

That makes this a **disambiguation** problem, not an indexing or vocabulary problem — which
is why better word matching, query rewrites, wider aliases and deeper candidate pools all
measured out to approximately zero. It shows up at both scales: across the corpus (the right
page sits at rank ~500–3,000 of 1.2 million) and *within* a single correct document (the
canonical table ranks 6th behind five prose restatements of its own subject).

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

**1. The disambiguation problem above.** Given hundreds of near-identical yearly editions
and a question that doesn't name a year, how do you pick the right one? Every lexical idea
tried has failed, each with a traced reason rather than a shrug. See
[`REPORT/README.md`](REPORT/README.md) §6–7.

**2. Telling "this IS the table" apart from "this mentions the table's subject."** This is
the most concrete lead in the repo and it is *not* yet built. Stage 1 of approach C already
harvested **89,380 explicit `Table N.N:` caption lines**, and caption coverage is **100% of
every PDF ≥100 pages (1,895 of 1,895)** — i.e. essentially complete over the large
statistical publications, and legitimately absent only on short notes and non-PDF formats.
A caption is a *label*, not a restatement, so it is exactly the signal that should separate
a canonical table from prose that happens to share its words. The in-document search does
not use that channel yet. See
[`REPORT/06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md`](REPORT/06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md) §4.

**3. A second failure that no retrieval fix addresses.** On 5 of 17 questions the right
document *was* handed to the agent and it opened **none** of them — three were cited without
ever being opened. A "quote the line before you cite it" rule was written for this and has
**never been run**, because it was deliberately held behind a retrieval gate that never
passed. That hold may itself be the wrong call; it is arguable.

**4. Is the table-card framing wrong at the root?** Honest self-assessment at the end of
[`REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md`](REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md).

**5. Coverage nobody has measured.** 1,211 files (8% of the fixture) are image-only PDFs
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
