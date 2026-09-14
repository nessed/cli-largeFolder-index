# plans_fable — two more ways to attack the retrieval problem, planned, not built

Written 2026-09-13 by a planning session. Nothing in this folder has been executed.
Everything here is evidence-checked against the lab's own state files, and the numbers
quoted are the lab's numbers (with two fresh measurements taken today, marked as such).

## What is in here

| file | what it is | who reads it |
|---|---|---|
| `B_HYBRID_MULTIQUERY_PLAN.md` | Ali's brother's suggestion (hybrid keyword + embedding search, 5–6 query rewrites, fused and reranked; plus the "read each document and save notes to a file" idea) examined against what the lab measured, with the design that survives that examination | Ali, then the executor for context |
| `B_HYBRID_MULTIQUERY_BUILD.md` | the hand-held executor prompt that builds and measures approach B, stack label `s6_hybrid` | paste to an executing agent |
| `C_SHELF_FIRST_PLAN.md` | a third approach, mine: stop ranking 1.2 million pages and instead find the **document** first, the way an economist finds a table — a "shelf" of publications × editions, then search inside the one book | Ali, then the executor for context |
| `C_SHELF_FIRST_BUILD.md` | the executor prompt for approach C, stack label `s7_shelf` | paste to an executing agent |

Both BUILD files are self-contained: rules, stages, gates as numbers, ceilings, recoveries.
Each stage appends to `corpus-lab/state/progress.jsonl`. Free work comes before paid work,
and each paid step states what it buys and what happens when the ceiling is hit.

## Run order and what not to collide with

1. **Another agent is mid-build on a third approach (`evidence_v1`).** Its files live in
   `corpus-lab/evidence_v1/`, `corpus-lab/bin/evidence.py`, `corpus-lab/tests/`,
   `_private/evidence_v1/`, and it edits `corpus-lab/bin/stack.py`. Neither BUILD here
   touches any of those, and both refuse to install into `harness/corpus_15000` while
   another stack is installed there (a `CLAUDE.md` or `.claude/` present at the rung root).
   The offline stages of B and C can run at any time. The paid stages need the rung to
   themselves. Run B's and C's paid stage after `evidence_v1` has torn down, and never both
   at once.
2. **B and C are independent.** Their offline stages can run in parallel in two terminals
   (they only read the shared index and write to their own directories). Their paid
   stages must be sequential.
3. Suggested order if you have one evening: C's offline gate first (it is the cheaper
   build, under an hour), then B's offline gate (its embedding build is the long pole),
   then whichever cleared its gate by more gets the paid battery first.

## Where each approach writes

| | B (`s6_hybrid`) | C (`s7_shelf`) |
|---|---|---|
| code | `corpus-lab/bin/b_*.py` | `corpus-lab/bin/c_*.py` |
| data | `corpus-lab/02_stacks/s6_hybrid/` (gitignored, large) | `corpus-lab/02_stacks/s7_shelf/` |
| run records | `_private/results/03_runs/PB_*` | `_private/results/03_runs/PC_*` |
| scores | `_private/results/04_scores/*s6_hybrid*` | `_private/results/04_scores/*s7_shelf*` |
| state json | `corpus-lab/state/b_*.json` | `corpus-lab/state/c_*.json` |
| findings | appended to `corpus-lab/05_findings/FINDINGS_LIVE.md` as F30+ | as F40+ |

Neither modifies an existing instrument (`ask.py`, `run_harness.py`, `scoring.py`,
`corpus_search.py`, `index_build.py`, `stack.py`). Each has its own small installer that
imports the backstop deny list from `stack.py` rather than editing it.

## The yardstick, restated

Right page, cited, opened and quoted — and an honest "not here" when it is not here.
The frozen 20 questions and their published numbers are the comparison point:

| on the frozen 20 | S0 stock | S1 index+policy | S2 index+hook |
|---|---|---|---|
| mean question recall (re-scored) | 0.167 | 0.235 | 0.176 |
| evidence surfaced by search → then opened | 1 → 1 | 5 → 0 | 2 → 0 |
| absence answered honestly (old scorer) | 0/3 | 0/3 | 0/3 |
| right file in top-50 by any lexical query strategy | 0/17 across eight strategies | | |

A new approach earns a paid battery only after a free, offline gate shows it puts the
right file in front of the model far more often than that. The exact gate numbers are in
each BUILD file.

## D — production hardening (written 2026-09-15, not yet executed)

`D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md` is the executor prompt for the night of
2026-09-15: approach C is built and measured; this plan makes it fast (two full-index scans
removed from `open` and `find`), repairs the shelf's family clustering and primary-copy choice,
shows the answering model a compact top-40 instead of twelve, guards page citations at the
answer boundary, adds a scorer that credits legitimate alternative sources, and re-runs the live
battery under the professor's real limits on Sonnet and Opus. Zero holdout looks. Approach B
remains unbuilt.
