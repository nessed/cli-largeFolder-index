# Current working architecture — 2026-09-15

> Supersedes [`CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](CURRENT_WORKING_ARCHITECTURE_2026-09-14.md).
> That document named Experiment C — per-query selection instead of rank fusion — as the one
> justified next step, and proposed a caption-based retrieval channel as the idea behind it.
> Both were run tonight, along with a year-aware page rule, a vintage-tolerant trajectory
> metric, a content-based edition rule, **the first live Claude Code battery on a frozen
> configuration**, and **the first end-to-end run of the whole pipeline**.
>
> Every number carries one of four labels: **HISTORICAL** (as measured 2026-09-13,
> reproduced exactly), **CORRECTED** (the same thing measured properly), **NEW** (measured
> for the first time tonight), **LIVE** (measured with real Claude Code sessions).
>
> **Six pre-registered adoption gates were read tonight. Every one of them STOPped or
> FAILED.** No bar was moved, no denominator was changed to rescue a result, and no gate was
> re-read after seeing the number. What changed is not the score; it is that three separate
> beliefs about *where* the loss lives are now measured rather than assumed.

## 1. The pipeline

```
15,000 messy files
      ↓
   SHELF
      ↓
   ROUTE
      ↓
RETRIEVE DOCUMENT            ← still one box; see §2
      ↓
RETRIEVE PAGE / TABLE
      ↓
  EXTRACT
      ↓
  VERIFY  ──── failure / AMBIGUOUS_EXTRACTION ────┐
      ↓                                            │
CLAUDE ANSWERS                    try another candidate or another
                                   extraction path — do not dead-end
```

**The shape has not changed, and tonight that is a measured decision rather than inertia.**
The 2026-09-14 note left a standing condition: redraw RETRIEVE DOCUMENT → RETRIEVE PAGE as
**RETRIEVE FAMILY → LOCATE TABLE**, with the edition falling out of locating the table, if
the caption channel reached WEAK *and* content-based edition selection reached 8 of 10. The
caption channel reached WEAK on the development set only (F47) and **ED2 scored 3 of 10**
(F51). The condition is not met. The boxes stay, and §2 records why in one sentence.

## 2. Why the boxes were not redrawn, and what is now known instead

Three findings from tonight converge on one fact, and it is the most useful thing measured
all night:

1. **F47** — the caption channel finds *publications* better (holdout recall@20 16 → 20,
   @50 24 → 28, @100 28 → 29, the first movement of recall@100 in the project) but a gold
   evidence *address* appears in the union of a question's top-20 caption hits on **1 of 13**
   questions. Captions do not locate pages.
2. **F48** — on all **6** year-asking questions, **no caption in the gold document contains
   the question's subject words at all**, with or without the year removed. The year was
   never the binding constraint; caption coverage is.
3. **F51** — with the gold family handed in, the edition that actually prints year Y's row is
   Y itself only 4 times in 14; it is **Y+1 six times and Y+2 four times**, and for 10 of 24
   year-addresses no edition within two years carries the row at all.

So "locate the table and the edition follows" is false here in both directions: the caption
does not locate the table for the questions that name a year, and locating a table would not
determine the edition anyway, because the table that prints a year lives in an edition the
year does not name. **The year narrows the row, not the edition** — now measured twice, from
the structural side (F43) and the content side (F51).

## 3. Measured state, box by box

| box | HISTORICAL (09-13) | CORRECTED (09-14) | NEW (09-15) | LIVE (09-15) | source |
|---|---|---|---|---|---|
| SHELF | 12,760 cards, 1,618 families, 89,380 captions | unchanged | **+ a caption FTS index (89,380 rows) and caption embeddings (89,380 × 384)** | — | `c_caption_index.json`, `c_caption_embed.json` |
| ROUTE — missing edition | 11/11 | 11/11, all `NO_EDITION_FOR` | **chain router: 1/3 (F52)** | **14/15 quoted the shelf's absence verdict; `absence_ok2` 1/15. FAIL** | `c_live_battery.json`, F50, F52 |
| ROUTE — absent identifier | 4/4 | 4/4 | — | — | `c_absence_control_v2.json` |
| ROUTE — present control | 14/17 (circular) | 8/11 | — | — | same |
| RETRIEVE DOCUMENT — top 10 | 6/17, 8/17, 2 excluded | **6/17 and 9/17, 0 excluded** | **10/17 with the caption channel (E1). Gate STOP on the holdout** | **surfaced 8/17** | `c_caption_family_gate.json`, F47 |
| RETRIEVE DOCUMENT — pool @100 | never measured | — | 16/17; **holdout 28 → 29 of 30 with captions** | — | F47 |
| RETRIEVE DOCUMENT — reranker | — | — | A1 4/17, A1b 9/17. STOP | — | F44 |
| RETRIEVE DOCUMENT — per-query selection | — | — | **5/17 against rrf's 9/17. STOP** | — | `c_fusion_gate.json`, F46 |
| RETRIEVE PAGE — baseline | 25/57 = 43.9% | **24/57 = 42.1% micro, 27.9% macro** | — | — | `c_page_gate.json`, F42 |
| RETRIEVE PAGE — caption (B2) | — | **42/57 = 73.7% micro, 39.7% macro**, all gain on trajectory | — | — | same |
| RETRIEVE PAGE — year-aware (B2b) | — | — | **42/57, 39.7% — identical to B2 at every address. STOP** | — | F48 |
| SELECT EDITION(S) — structural | — | — | 3/17 (F43) | — | `c_edition_set.json` |
| SELECT EDITION(S) — content (ED2) | — | — | **3/10, mean set size 2.0. FAIL** | — | `c_edition_set_v2.json`, F51 |
| TRAJECTORY walk | 1/4 (measured copy choice) | 1/4 | **S2: strict 12/24, tolerant 14/24. WEAK** | `series` used on 2/4 | `c_series_v3.json`, F51 |
| EXTRACT | no router | unchanged | — | — | — |
| VERIFY | 30 cells: 27 correct, 0 wrong accepted | unchanged | — | — | `stage6_2_thirty_cells.json` |
| CLAUDE ANSWERS (behaviour) | surfaced 5/17, opened 0/5 | unchanged | — | **opened_any 2/17, opened_right_page 1/17, cited_right_page 0/17, cited_unopened 5, figures_ungrounded 1. FAIL** | `c_live_battery.json`, F50 |
| end-to-end chain | never run | — | **RUN for the first time: family top-5 8 → address 4 → **verified 3 of 17**; absence 1/3; 478 verifier calls** | — | `c_chain_gate.json`, F52 |
| COVERAGE | 1,211 image-only PDFs, 8% | unchanged | — | — | `README.md` |

## 4. Keep / weak / failed / still untested

**Proven enough to keep.**
SHELF — and it grew two new indexes tonight that work as artefacts even though the retrieval
built on them did not clear its gate. VERIFY. **Session isolation**: the installed deny list
refused a planted 16-hex token and a listing of the private tree in two live probes, 18
planted files came through the battery with 0 changed, and 0 memory files were written.

**Weak.**
The caption channel — a real, holdout-confirmed gain below the top ten and nothing at the top
ten. The trajectory walk, at S2 strict 12/24, the bottom of its band. ROUTE's presence half,
still 8/11. **The open-before-cite rule, in an unexpected way**: it was followed — all 17
sessions issued `open` commands, 12 of 17 wrote notes, and only 2 questions named an unopened
file — and following it bought almost nothing, because the agent opened the wrong pages.

**Failed.**
RETRIEVE DOCUMENT, now a fourth time: rewrites (9/17), a reranker (9/17), per-query selection
(5/17), the caption channel (10/17 dev, 14/30 holdout) — against a 12/17 bar. Edition
selection, now twice: structural 3/17 and content-based 3/10. The year-aware page rule, which
was a measured no-op. **CLAUDE ANSWERS under the live gate, and ROUTE's absence half under the
live scorer** — with the caveat in F50 that the absence scorer conflates two failures and is
itself a candidate defect.

**Still untested.**
The EXTRACT router. The VERIFY → retry feedback edge. Whether a caption harvest that captured
more than the printed caption line would fix F48's coverage problem. Whether the absence
scorer, repaired, would move 1/15 towards 14/15.

## 5. What should be attacked in this document

- **The absence scorer, before anything else.** F50 records 14 of 15 sessions correctly
  quoting the shelf's own absence verdict and the metric crediting 1. One of those two numbers
  is wrong about reality and the repository currently publishes both.
- Whether "gold family in the top 10" is still the right intermediate objective, given that
  the live battery surfaced 8 of 17 and converted 2 — the intermediate measure and the thing
  we care about are now visibly decoupled.
- Whether the caption harvest, not the caption *matcher*, is the limiting artefact (F48).
- Whether a wider vintage window than [Y, Y+2] is justified — noting that it was forbidden
  tonight precisely because widening it after seeing the offsets is the move that has quietly
  widened a bar before.

## 6. The next experiment

**One is justified, and for the first time in four nights it is not a retrieval idea.**

Every retrieval lever has now been pulled and measured: more rewrites, a reranker, a
different fusion rule, a second retrieval channel lexical, that channel dense, a page-level
caption rule, a year-aware page rule, two edition rules. The best of them moves the document
top ten from 9 to 10 of 17 and does not survive the holdout. Meanwhile the live battery shows
the agent opening pages diligently and choosing wrong, and the absence half of the system
scoring 1 of 15 on a metric that its own transcripts suggest should be much higher.

**And the chain agrees with the live battery about absence, which the scorer defects cannot
explain.** F52's deterministic router — pure code, no scorer anywhere in it — routes **1 of
3** absence questions correctly. Two independent measurements now disagree with the 11/11
this repository has published since the shelf was built. So the experiment below has a
second half that does not depend on the scorer at all.

**Experiment F — repair the live scorer, then re-read the battery already on disk.** The 32
transcripts are recorded. Fix the two defects F50 names — a decline regex written for a
different battery, and counting a figure quoted *from the shelf's own output* as an invented
figure — and re-score the existing sessions. No new model calls, no new index, no retrieval
change.

**Pre-registered gate, fixed before measuring:**

- **PASS** — the repaired `absence_ok2` is ≥ 10/15 **and** every one of the 15 answers it now
  credits contains the shelf's own absence verdict string. The absence box is then genuinely
  working and the 1/15 was a measurement artefact.
- **WEAK** — 8–9/15 on the same condition.
- **STOP** — ≤ 7/15, or any answer credited without the verdict string, which would mean the
  repair loosened the metric rather than fixing it.

**Second half, and it is not optional:** re-derive the published 11/11 with the same
`do_have` call the chain router uses, on the same 3 frozen absence questions the chain
scored 1 of 3. Either the 11/11 and the 1/3 are measuring different question sets — in
which case say so on the status line — or one of them is wrong. This costs nothing and
settles whether the project's one solved box is solved.

The rule that makes this honest: **the repair must be specified in full, and the gate written,
before the re-score is run** — and it must be written from the two defects F50 already names,
not from reading the answers. If the repaired metric passes, absence moves back to *keep*. If
it stops, then 1/15 stands and the absence box has quietly been failing since it was declared
solved, which would be the single most important correction this project has made.

**Do not**, to get past this gate: widen the decline regex by reading tonight's answers and
adding their phrases one at a time; count a non-declining answer as a decline because it
"clearly means it"; or re-run the battery with a different prompt.

## 7. Related

- [`HANDOFF_2026-09-15.md`](HANDOFF_2026-09-15.md) — tonight in thirteen plain answers.
- [`CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](CURRENT_WORKING_ARCHITECTURE_2026-09-14.md) — the document this supersedes.
- [`ARCHITECTURE_REVIEW_2026-09-13.md`](ARCHITECTURE_REVIEW_2026-09-13.md) — the review that produced the corrected harness.
- `corpus-lab/05_findings/FINDINGS_LIVE.md` F46–F52.
