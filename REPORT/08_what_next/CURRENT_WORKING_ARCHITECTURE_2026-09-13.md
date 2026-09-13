# Current working architecture — 2026-09-13

> **This is not a proven design. It is a synthesis, for review, not a conclusion.**
> It is the best picture we can currently draw by putting a proposed pipeline shape
> next to the numbers this repository has actually measured. Two of its boxes are
> untested combinations of ideas that were each tested separately. It exists so the
> next Fable agent has one concrete claim to try to break, not because the pipeline
> below is believed to work end to end. See §6 for exactly what should be attacked.

## 1. The pipeline

```
15,000 messy files
      ↓
   SHELF
      ↓
   ROUTE
      ↓
RETRIEVE DOCUMENT
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

The feedback edge matters: today a failed verification just stops the run. Nothing
in this repository has tested going back for a second candidate page or a second
extraction method instead of giving up.

## 2. What each box means

**SHELF** — one card per document (not per page): publication family, edition /
fiscal year, duplicate/copy grouping, explicit table captions, and a structural
inventory of what exists. Answers "what do I hold?", not "what does this say?".

**ROUTE** — decide how a question should be answered *before* running a fuzzy
search:
- exact identifier (SRO number, report number, literal phrase) → exhaustive literal
  search, never a similarity score;
- named publication + year → shelf presence/absence lookup;
- series / trajectory ("since", "over the years") → enumerate the family's editions
  first, then search each one;
- vague semantic question → falls through to the retrieval path below.

The reason this is its own box: absence must stay a structural yes/no
("do I hold an edition for that year?"), never a side effect of a retrieval score
being low. A retrieval score cannot tell "the answer is here" from "it isn't" —
that was measured directly and failed (`corpus-lab/state/probe_score_floor.json`,
finding F22 in `corpus-lab/05_findings/FINDINGS_LIVE.md`). If ROUTE is removed and
absence is inferred from RETRIEVE DOCUMENT scoring low, the one part of this project
that currently works stops working.

**RETRIEVE DOCUMENT** — of everything on the shelf, pick the one publication/edition
that answers the question. **This is the current bottleneck** (§3).

**RETRIEVE PAGE / TABLE** — once the document is known, find the specific evidence
page inside it, and tell an actual table apart from a paragraph that happens to
restate the same figure in prose.

**EXTRACT** — get literal values off the selected page: existing fast extraction for
normal text PDFs; a structure-aware table parser where the layout demands it; OCR/
vision for image-only pages; native readers for structured files (CSV/XLSX/DOCX)
that don't need extraction at all.

**VERIFY** — build one evidence record per claim: source, page, row/column where
relevant, literal value, period, unit. Ambiguous evidence abstains rather than
guessing. No fuzzy acceptance of a numeric cell.

**CLAUDE ANSWERS** — a numeric or factual claim may only come from a record that was
actually opened and verified. A search-result snippet is not evidence and may not be
cited as if it were.

## 3. Measured state, box by box

| box | measured result | bar | source |
|---|---|---|---|
| SHELF | 12,760 document cards, 1,618 families, 393 with 2+ editions, 89,380 explicit table captions; 13/13 self-tests pass | — | `corpus-lab/state/c_shelf_build.json`, `corpus-lab/state/c_shelf_selftest.json` |
| ROUTE — missing edition | 11/11 correctly say absent | 9/10 | `STAGE3_OFFLINE_GATE_REPORT.md` §2 |
| ROUTE — absent identifier | 4/4 correct zero-hit | — | `STAGE3_OFFLINE_GATE_REPORT.md` §2 |
| ROUTE — present-edition control | 14/17 correctly say present (weak pass) | 15/17 clean, 13/17 weak | `STAGE3_OFFLINE_GATE_REPORT.md` §2 |
| RETRIEVE DOCUMENT | 6/17 correct family in top 10, verbatim question; 8/17 with 5 paraphrases | 12/17 | `STAGE3_OFFLINE_GATE_REPORT.md` §2 |
| RETRIEVE PAGE / TABLE | 25/57 correct page in top 5, given the correct document (43.9%) | 60% clean, 40% floor | `STAGE3_OFFLINE_GATE_REPORT.md` §2 |
| RETRIEVE PAGE — trajectory walk | 1/4 editions landed correctly | 3/4 clean, 2/4 weak | `STAGE3_OFFLINE_GATE_REPORT.md` §3 |
| VERIFY | 30 cells: 27 correct, **0 incorrect accepted**, 3 honest abstentions | — | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/stage6_2_thirty_cells.json` |
| CLAUDE ANSWERS (behaviour) | correct document surfaced on 5/17 questions, opened on **0/5** — three of those five were cited off the preview without opening the page | — | finding F21, `corpus-lab/05_findings/FINDINGS_LIVE.md` |
| COVERAGE | 1,211 image-only PDFs (8% of the fixture) unreachable by text extraction today | — | `README.md` §"Coverage nobody has measured" |

## 4. Built and keep / bottleneck / untested

**Built and keep** — SHELF; ROUTE's absence handling (both directions); VERIFY.
These are measured, and two of them (absence, verify) clear their bars.

**Current bottleneck** — RETRIEVE DOCUMENT (6/17 against 12/17) and, one level down,
RETRIEVE PAGE / TABLE (43.9% against a 60% clean bar, 1/4 on trajectories).
Everything after these two boxes is conditional on them: EXTRACT, VERIFY, and
CLAUDE ANSWERS cannot do better than the document and page they are handed.

**Untested / provisional** — the ROUTE/RETRIEVE-DOCUMENT/RETRIEVE-PAGE split as
drawn above has never been run as one system. The caption channel as a fix for
RETRIEVE PAGE (§5, Experiment B) has never been measured. The EXTRACT router
("normal PDF vs. difficult table vs. image-only vs. native file") does not exist as
code — today there is dual-method extraction, not a router. The VERIFY → retry
feedback edge has never been built or run. CLAUDE ANSWERS' "must open before citing"
rule is written policy, never tested — it was held behind a retrieval gate that
never passed.

**Do not read this as one integrated production system.** Every arrow above
connects boxes that were, at best, measured in isolation.

## 5. Next falsifiable experiments

**Experiment A — document retrieval.** Use the existing Approach C shelf as-is; no
rebuild. Test whether the one genuinely untested idea — a compact reranker over the
fused FTS5 + semantic top-100 candidates — moves the 8/17 (paraphrased) result.
Fable must review the exact design (candidate pool size, reranker choice, what
counts as an improvement) before it runs.

**Experiment B — page/table retrieval.** Deliberately supply the *correct* document
(bypass Experiment A) and test whether caption-aware retrieval — favoring a
harvested `Table N.N: ...` caption line over a prose sentence mentioning the same
subject — improves on the current 43.9%.

Keep A and B separate. If they ran together and the result changed, it would be
impossible to tell whether document selection or page selection was responsible.

## 6. This document should be attacked, specifically on:

- whether the ROUTE / RETRIEVE-DOCUMENT / RETRIEVE-PAGE split is the right cut, or
  whether it hides a different real bottleneck;
- whether "correct document in top 10" is even the right intermediate objective to
  optimize, as opposed to some end-to-end measure;
- possible benchmark leakage between the frozen dev/holdout questions and anything
  used to tune the shelf or the retrieval route;
- whether Experiment A or B is a previously-tried idea being re-proposed under a new
  name (check `corpus-lab/state/evidence_v1/TUNING_SUMMARY_2026-09-13.md` and
  `RESEARCH_2026-09-13.md` before running either);
- whether the metrics here (top-10 family recall, top-5 page recall, cell
  verification) actually represent how a person doing this research would judge the
  system, or whether they reward something narrower.

If Fable finds a real flaw in this document, amend it before running either
experiment.

## 7. Related reports (not duplicated here)

- [`STAGE3_OFFLINE_GATE_REPORT.md`](../06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md) — full gate detail and the two test-harness bugs fixed mid-review.
- [`CORRECTION_2026-09-13.md`](CORRECTION_2026-09-13.md) — why the earlier Shelf V2 recommendation was withdrawn.
- [`C_SHELF_FIRST_PLAN.md`](../06_approach_c_shelf/C_SHELF_FIRST_PLAN.md) / [`C_SHELF_FIRST_BUILD.md`](../06_approach_c_shelf/C_SHELF_FIRST_BUILD.md) — what Approach C actually built.
- `corpus-lab/state/evidence_v1/TUNING_SUMMARY_2026-09-13.md` — eleven prior tuning attempts against a frozen holdout; read before proposing a retrieval change.
- `corpus-lab/05_findings/FINDINGS_LIVE.md` (F20-F22) — the agent-behaviour and score-floor findings behind §2's ROUTE reasoning and §3's CLAUDE ANSWERS row.
