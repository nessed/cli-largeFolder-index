# Current working architecture — 2026-09-14

> **SUPERSEDED 2026-09-15** by [`CURRENT_WORKING_ARCHITECTURE_2026-09-15.md`](CURRENT_WORKING_ARCHITECTURE_2026-09-15.md).
> The experiment this document proposed (Experiment C, per-query selection) was run and
> **STOPped at 5/17 against RRF's 9/17** (F46). The numbers below are still correct as
> measured; the recommendation in §5 is not.

> Supersedes [`CURRENT_WORKING_ARCHITECTURE_2026-09-13.md`](CURRENT_WORKING_ARCHITECTURE_2026-09-13.md),
> which proposed experiments A and B. Both were run, after the
> [2026-09-13 adversarial review](ARCHITECTURE_REVIEW_2026-09-13.md) found four defects in
> the harness that produced the numbers they were aimed at. This document reports what the
> corrected harness measures. Every number below carries one of three labels:
> **HISTORICAL** (as measured 2026-09-13, reproduced exactly), **CORRECTED** (the same thing
> measured properly), **NEW** (measured for the first time this phase).
>
> The pipeline shape has not changed. What changed is our knowledge of which box is losing.

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

Unchanged from the 2026-09-13 draft. The feedback edge is still untested.

## 2. Why RETRIEVE DOCUMENT was *not* split into FAMILY → EDITION

The 2026-09-13 review proposed replacing RETRIEVE DOCUMENT with
RETRIEVE FAMILY → SELECT EDITION(S), on the theory that once the right publication family is
known, the shelf's own structural metadata can name the right edition without reading a page.
That was measured (F43) and it does not work: with the gold family handed in, a structural
rule built from fiscal-year tokens and the shelf's `fy_all` selects a set containing all of a
question's evidence on **3 of 17** questions, against a pre-registered bar of 15 of 17.

The reason is worth stating plainly, because it is a fact about this kind of research rather
than a defect in the shelf. **The year a question asks about is usually not the year printed
on the document that answers it.** Of the 18 evidence documents behind the ten year-asking
questions, 7 carry the asked year anywhere in their metadata, 1 carries it as its primary
year, and on 4 of the 10 questions no evidence document carries it at all. A question about a
fiscal year is answered by whichever edition happens to print that year's row — usually a
later one carrying a historical series. The year narrows the *row*, not the *edition*.

So the box stays as it is, and "which edition, and which copy of it" is recorded as a real
unsolved sub-problem rather than a solved routing rule.

## 3. Measured state, box by box

| box | HISTORICAL (2026-09-13) | CORRECTED | NEW | source |
|---|---|---|---|---|
| SHELF | 12,760 cards, 1,618 families, 89,380 captions, 13/13 self-tests | unchanged | — | `state/c_shelf_build.json`, `state/c_shelf_selftest.json` |
| ROUTE — missing edition | 11/11 say absent | 11/11, and all 11 are `NO_EDITION_FOR`, none `NO_FAMILY_MATCHES` | — | `state/c_absence_control_v2.json` |
| ROUTE — absent identifier | 4/4 zero-hit | 4/4 | — | same |
| ROUTE — present-edition control | 14/17 (circular: queried with the shelf's own words) | **8/11** with the question's own words and a held year swapped in; 3 unresolvable | — | same, F41 block in the Stage 3 correction |
| RETRIEVE DOCUMENT — top 10 | 6/17 verbatim, 8/17 with rewrites, 2 questions excluded | **6/17 and 9/17, 0 excluded** | — | `state/c_gate_v2.json` |
| RETRIEVE DOCUMENT — pool recall | never measured | — | **recall@100 = 16/17 (C2); 28/30 on the holdout** | `state/c_recall_curve.json`, F41 |
| RETRIEVE DOCUMENT — reranker | — | — | **A1 4/17, A1b 9/17; holdout 12/30 and 16/30. Gate: STOP** | `state/c_rerank_gate.json`, F44 |
| RETRIEVE PAGE — baseline | 25/57 = 43.9% micro | **24/57 = 42.1% micro, 27.9% macro** (corrected short query) | — | `state/c_page_gate.json`, F42 |
| RETRIEVE PAGE — caption channel | — | — | **42/57 = 73.7% micro, 39.7% macro; all of the gain on trajectory questions (22/42 → 40/42), none elsewhere** | same |
| RETRIEVE PAGE — trajectory walk | 1/4 editions landed | 1/4 with the best page method; the metric measures copy choice, not page retrieval — the walk opens the cited file on 3 of 21 aligned years | — | `state/c_series_v2.json`, F42 |
| SELECT EDITION(S) | — | — | **structural set recall 3/17, mean set size 7.06. Not adopted** | `state/c_edition_set.json`, F43 |
| EXTRACT | no router exists; dual-method extraction only | unchanged | — | — |
| VERIFY | 30 cells: 27 correct, 0 incorrect accepted, 3 abstentions | unchanged | — | `state/evidence_v1/…/stage6_2_thirty_cells.json` |
| CLAUDE ANSWERS (behaviour) | right document surfaced on 5/17, opened on 0/5 | unchanged | — | F21 |
| end-to-end chain | never run | — | **still never run** — its pre-registered condition (gold family in top 3 on ≥8/17) was not met; the best configuration does it on 5 | `state/progress.jsonl`, P7 |
| COVERAGE | 1,211 image-only PDFs, 8% of the fixture | unchanged | — | `README.md` |

## 4. Keep / weak / failed / still untested

**Proven enough to keep.**
SHELF. ROUTE's absence handling, in both directions — and it is now the only box that
survived a deliberate attempt to break its measurement: all 11 document-level absence hits
are genuine `NO_EDITION_FOR`, not the `NO_FAMILY_MATCHES` fallback the review suspected.
VERIFY.

**Weak.**
ROUTE's *presence* half: 8 of 11 under the honest symmetric control, against 9 for a clean
pass. The caption channel for page retrieval: a large, clean win on one question type and
exactly nothing on the other four, so it is a keeper for trajectory work and not a general
page fix.

**Failed.**
RETRIEVE DOCUMENT, still, at 9/17 against a 12/17 bar — and now failed a second way, because
the reranker that was the one genuinely untested idea for it did not work. The
FAMILY → EDITION structural split, at 3/17 against 15/17. `series_ok` as a metric: it has
been measuring which copy the shelf calls primary.

**Still untested.**
The pipeline as one system — the chain test's condition was not met, so nothing here has been
run end to end. The EXTRACT router. The VERIFY → retry feedback edge. The "must open before
citing" rule. Per-query max fusion (F41 recorded that some single rewrite alone reaches the
top 10 on 12 of 17 against 9 for all six fused — this is the best-supported untried idea in
the repository and it was deliberately not built this phase).

## 5. The next experiment

**One is justified, and it is not a new approach.** F41 measured that on **12 of 17**
questions some single query rewrite, on its own, already puts the gold family in its own top
10 — while RRF over all six rewrites together manages 9. Fusion is losing questions that its
own inputs had. F44 then confirmed the same thing from the other side: dropping one rewrite
cost two questions out of the fused top 10 even though that rewrite was never the sole finder
of anything. Both point at the fusion step, which is the one part of candidate generation
nobody has varied.

**Experiment C — per-query selection instead of rank fusion.** For each rewrite, take its own
ranked family list; score each family by its *best* rank across rewrites rather than by summed
reciprocal rank; break ties by how many rewrites found it. No model calls, no new index, no
new metadata. Roughly an hour.

**Pre-registered gate, fixed before measuring:** gold family in the top 10 on the 17, with the
corrected denominator, compared against C2's 9/17, then confirmed on the frozen holdout
against its 14/30.

- **PASS** — ≥12/17 **and** holdout ≥17/30.
- **WEAK** — 10–11/17 **and** holdout ≥16/30.
- **STOP** — ≤9/17, or the holdout does not improve by at least 2.

If it stops, the honest conclusion is that no reweighting of these six rewrites over this
shelf reaches the bar, and the next thing to attack is what the cards are made of rather than
how they are ranked. **Do not** tune the fusion constant, add a seventh rewrite, or vary the
pool depth to get past this gate; each of those is the move that has quietly widened a bar
before.

## 6. What should be attacked in this document

- Whether "gold family in the top 10" is still the right intermediate objective, given that
  F43 showed the family is not the unit that holds the answer — the *copy* is.
- Whether the caption channel's trajectory win survives more than four trajectory questions.
- Whether the symmetric presence control at 8/11 is a real weakness or an artefact of three
  families that hold no dated primary.
- Whether Experiment C is a previously-tried idea under a new name: check
  `state/evidence_v1/TUNING_SUMMARY_2026-09-13.md` and `RESEARCH_2026-09-13.md` first.

## 7. Related

- [`ARCHITECTURE_REVIEW_2026-09-13.md`](ARCHITECTURE_REVIEW_2026-09-13.md) — the review this phase executed.
- [`HANDOFF_2026-09-14.md`](HANDOFF_2026-09-14.md) — this phase in twelve answers.
- [`../06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md`](../06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md) — historical body, with a dated correction block on top.
- `corpus-lab/05_findings/FINDINGS_LIVE.md` F40–F44.
