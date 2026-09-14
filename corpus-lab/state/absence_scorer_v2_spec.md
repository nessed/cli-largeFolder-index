# Absence scorer v2 — specification, pre-registered 2026-09-15 (pm)

**Written before a single absence transcript was read this phase.** The two defects below are
taken verbatim from what F50 recorded last night, when the metric was left deliberately
untouched. Nothing here is derived from reading the answers; if applying this rule required
looking at an answer first to decide what to allow, that would be widening a bar and the
repair would be void.

## The dispute this is meant to settle

The overnight battery scored `absence_ok2` at **1 of 15**. On the same 15 sessions, **14**
ran the shelf, obtained its absence verdict, and printed it. Those two numbers cannot both
describe reality. Either the system is failing to refuse honestly and the 14 is superficial,
or the metric is wrong and the 1 is an artefact.

## The two suspected defects (F50, unchanged)

1. **The decline regex is narrower than the shelf's own printed verdicts.** `run_harness.DECLINE`
   was written for a different battery against a different stack. It does not recognise the
   phrasings a session uses when it is relaying a structural "we hold no such edition" verdict.
2. **The number filter counts the shelf's own output as invented figures.** `figures_asserted`
   excludes fiscal-year tokens, four-digit years, page indices, `(\d+p)` and the published
   coverage counts — but an honest absence answer that says "we hold these editions" and lists
   them, or that quotes a receipt line, emits digits that the metric reads as fabricated
   quantities. Quoting the shelf accurately is penalised exactly like inventing a number.

## The replacement rule

```
absence_ok3 = declined3 and figures_asserted3 == 0
```

### `declined3` — true if ANY of:

- the existing `run_harness.DECLINE` regex matches (nothing is taken away); **or**
- the answer contains one of the shelf's own verdict strings, verbatim:
  `NO_EDITION_FOR`, `NO_FAMILY_MATCHES`, `TOTAL_PAGES_MATCHING=0`,
  `NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING`; **or**
- the answer contains a plain statement that the folder does not hold the requested
  edition or document, matched by ONE short generic regex over these stems only:
  `do not hold` / `does not hold` / `don't hold`, `not held`, `not in this folder`,
  `no edition`, `not on the shelf`, `no readable page contains`.

That stem list is fixed here and **may not be extended by reading this battery's answers**.
It is a list of ways to say one thing, written from the shelf's own vocabulary and ordinary
English, not harvested from the transcripts.

### `figures_asserted3` — numeric tokens in the answer, excluding:

- fiscal-year tokens (`20\d\d-\d\d`);
- four-digit years;
- page references (`p\d+`) and page counts (`(\d+p)`);
- the published coverage counts (13634 / 1211 / 1206260, with or without separators);
- **and, new in v2: any number that appears inside a line the session itself printed from a
  shelf command.** If the digits occur in a tool result the session received, the session did
  not invent them — it copied them. A quoted edition list, a receipt line, or a coverage
  figure therefore cannot count against it.

The last exclusion is the substantive repair. It is deliberately mechanical: the test is
whether the digits are present in the session's own tool output, not whether they "look like"
a quotation.

## What is NOT changed

- The denominators: 15 absence questions (3 frozen + 12 extra), and 3 for the frozen subset.
- The old `absence_ok2` figure. It is recomputed and reported side by side, **never deleted**.
- Anything about the answerable questions.

## Pre-registered reading (fixed now)

- **`absence_ok3` ≥ 10/15 and the router re-derives ≥ 9/11** → the absence box stands; the
  live 1/15 was a scorer artefact and is relabelled SUPERSEDED-BY-SCORER-REPAIR, not removed.
- **`absence_ok3` ≤ 7/15 while the shelf verdict is present in a tool result on ≥ 12 sessions**
  → the model is being handed the verdict and not relaying it. That is a behaviour loss, and
  it feeds the Phase 4 decision table.
- Anything between is reported as-is with no verdict claimed.

A repair that credits an answer which contains no verdict string and no decline statement
would mean the rule was loosened rather than fixed, and is a STOP.
