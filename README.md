# retrieval-lab

**The question:** can you point Claude Code at a folder of ~15,000 research PDFs, ask a
vague question in ordinary language, and get back the actual number with the file and page
it came from — and an honest "not in here" when the answer genuinely isn't?

**The answer so far: no, and we now know fairly precisely why.** Four nights of measured
experiments, five distinct approaches, about $31 spent. This repository is the full record:
the code, the measurements, the failures, and the diagnosis.

> ### 👉 Start at [`REPORT/README.md`](REPORT/README.md)
>
> It walks the entire project start to finish in plain English — the problem, every
> approach tried, what each one measured, and what is and isn't solved. Written for
> someone who has never seen this repo. Everything else here is supporting evidence.

---

## Status in one table

| | |
|---|---|
| **Solved** | Getting the model to *use* a tool you give it — one line in `CLAUDE.md` moved adoption from 0/38 sessions to 38/38 |
| **Solved** | Knowing when material genuinely isn't there — 11/11 and 4/4 via a structural edition check (not a score threshold, which was disproven) |
| **Built and trustworthy** | Extraction and coverage accounting over 15,010 files, content hashing, provenance records, table-cell verification, typed evidence compiler, safe install/teardown, test suites |
| **NOT solved** | Putting the right page in front of the model for a vague question. Every approach has failed this. |

The open problem, stated precisely: this corpus republishes the same fiscal tables every
year across dozens of near-identical editions. A vague question's words match hundreds of
them about equally, and the question usually doesn't name the year it wants. That makes it
a **disambiguation** problem, not an indexing or vocabulary problem — which is why better
word matching, query rewrites, wider aliases and deeper candidate pools all measured out to
approximately zero.

| approach | best result | bar it needed to clear |
|---|---|---|
| stock tools / index / enforced index | 0.167 / 0.235 / 0.176 recall | — |
| eight lexical query strategies | right file in global top-50: **0/17** | — |
| `evidence_v1` table catalogue | 3/17, then 2/17 after 13 tuning iterations | 10/17 |
| approach C "shelf" (document-first) | right document in top-10: 6/17 (8/17 with rewrites) | 12/17 |

---

## Where independent review would help most

If you are reading this to suggest improvements, these are the live questions — roughly in
order of how much they matter:

1. **The disambiguation problem above.** Given hundreds of near-identical yearly editions
   and a question that doesn't name a year, how do you pick the right edition? Every
   lexical idea tried has failed. See [`REPORT/README.md`](REPORT/README.md) §6–7.
2. **Semantic matching over *cards*, not pages — the one substantial untried lever.** Dense
   embedding was ruled out early on a full-page estimate of 20.8 hours on this CPU-only
   machine. That number no longer applies at card scale: approach C measured the equivalent
   embedding work at 28 minutes for 12,760 cards. Nobody has tested whether it helps.
3. **A second failure that no retrieval fix addresses.** On 5 of 17 questions the right
   document *was* handed to the agent and it opened none of them, citing search snippets
   instead. A "quote the line before you cite it" rule was written for this and has never
   been run.
4. **Is the whole table-card framing wrong?** See the honest assessment at the end of
   [`REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md`](REPORT/05_evidence_v1_tuning/TUNING_SUMMARY.md).
5. **Coverage.** 8% of the fixture is image-only PDFs unreachable without OCR, and nobody
   has checked the equivalent share in the real target folder.

The recommended next build is specified in
[`REPORT/08_what_next/RESEARCH_2026-09-13.md`](REPORT/08_what_next/RESEARCH_2026-09-13.md).
Arguments against it are as welcome as arguments for it.

---

## Layout

```
REPORT/          ← the walkthrough + copies of every report, in reading order. START HERE.
INDEX.md         the original repo map and the ground rules
SOLUTION.md      the evidence_v1 design rationale
BUILD_PROMPT.md  the staged build contract evidence_v1 was executed against
RESEARCH_*.md    the research pass that reads all the evidence and recommends what's next
EXECUTE_SHELF_V2.md  the build contract for that recommendation
00_brief/        the task as originally given, incl. SOLVE_BRIEF.md for an outside designer
plans_fable/     two further approaches, planned; C was built, B never was
corpus-lab/      all code, findings and run state
  bin/             the instruments (measurement primitives, index builder, scorers)
  evidence_v1/     the table-catalogue engine runtime
  tests/           its test suites
  01_reports/      the original research passes
  05_findings/     FINDINGS_LIVE.md — every finding with the condition it holds under
  state/           machine-readable run state; progress.jsonl is the step-by-step audit trail
```

## What is deliberately not in this repository

- **`_private/`** — the answer keys, canary manifests, and 189 recorded measurement
  sessions. Publishing them would make an honest re-run of the benchmark impossible.
- **`harness/`** — the four generated fixture corpora *and* their generator. The generator
  (`finalize_key.py`, `canary_slots.py`, `plant_canaries.py`, `plan.py`) is the machinery
  that manufactures the answer key, so it is equivalent to the key itself.
- **`ACCEPTANCE.md`** — an oracle in prose: gold source paths, literal cell values and page
  indices. Referenced by the reports but not published.
- **Derived indexes** — a ~7 GB FTS5 page index, the shelf database, card vectors. All
  rebuildable from code that *is* here.

> ⚠️ **A caveat if you intend to re-run the benchmark.** Some answer-derived material was
> published in earlier commits and is still present: 13 canary phrases quoted as evidence
> in `FINDINGS_LIVE.md`, 21 gold evidence paths in `state/c_card_sample_100.csv`, and a
> handful in `probe_score_floor.json` and `rescore_from_results.json`. They were left in
> place because scrubbing them means rewriting public history and stripping verbatim
> evidence out of the night-1 findings. **Reading this repository therefore contaminates
> you (or an agent) for re-running the measurement.** Reviewing the design and the
> reasoning is unaffected.

## Reproducing anything

Every path derives from `corpus-lab/bin/labpaths.py`; no script hardcodes a location.
`corpus-lab/RESUME.md` is the cold-start guide, including the traps worth not
rediscovering. `corpus-lab/state/progress.jsonl` is the append-only audit trail — one JSON
line per step across all four nights.

Note that the fixture corpora are not in this repository and regeneration is banned: the
generator's own determinism check failed (6,060 of 6,064 files reproduced), so rebuilding
would silently change the ground truth. Results here are reproducible in reasoning and in
code, but not bit-for-bit re-runnable without the archived corpora.
