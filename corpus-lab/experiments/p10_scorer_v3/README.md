# p10_scorer_v3 — a scorer you can trust, then frozen

Plan E Phase 1. Branch `phase10-trust-and-repro`.
Gate T verdict: **`GATE_T_STOP`** (rows T2, T3, T6, T7). v3 was **not** modified in
response — that is the rule, and it is the reason the result below is worth anything.

## Purpose

An independent audit of the 2026-09-15 night concluded that three of the four headline
defects in the Phase 9 report were defects in the **scorer**, not in the system it was
measuring. If that is true, then several sentences in the report are wrong about the
thing the whole project is for — whether the system cites pages it has actually read.

Phase 1 builds a third scorer that fixes exactly the four parsing defects the audit
names, re-scores the six recorded batteries with it, and puts v2 and v3 side by side
with a reason for every difference. Gate T asks a deliberately hostile question: does
v3, written independently from the audit's prose, reproduce the audit's own numeric
predictions?

It largely does not. That is the finding.

**No Phase 9 verdict changes.** Those were set by the pre-registered v2 scorer and they
stand as recorded, restated verbatim in the comparison file under
`historical_verdicts_unchanged`.

## Method

`c_score_live_v3.py` imports v2 for the placement registry and the value logic and
overrides four things and nothing else:

1. **Opens come from ground truth, not from the command string.** The union of every
   `OPENED <rel> p<N>` line in a tool result (what `c_shelf.py open` prints,
   `c_shelf.py:1262`), every `open "<rel>" <N>` v1's regex finds, and `files_opened`
   from the hook record. A command-derived "path" that is really a shell placeholder
   (`$f`, a glob) is dropped — v1's regex matched `open "$f" 12` and recorded a file
   named `$f`.
2. **A citation is a path with a page; a mention is not.** Either the `<path> | p<N>`
   Sources form, or a path with a `p<N>` / `page N` token within **40 characters**.
   Everything else path-shaped is a *mention*, reported separately and never counted as
   an open-before-cite violation. Leading markdown (bullets, backticks, emphasis) is
   stripped before the path is normalised.
3. **The complete answer across a guard interruption.** The harness keeps the last
   assistant message, so a session the guard challenged records only the confirmation
   reply. `reconstruct_full_answer()` returns the trailing assistant text plus the
   assistant text immediately preceding each Stop-hook block. A Stop-hook block is a
   synthetic `user` event carrying a text block — established by reading the event
   shapes, not by guessing (`p10_hook_probe.py`).
4. **Denominators.** `value_correct` is `k / n_keyed`, where `n_keyed` counts questions
   the key carries a numeric value for. Unkeyed questions get `value_scorable: false`
   and are in no value denominator.

Seven regression tests, one per audited bug, named for the transcript that exposed it,
plus seven supporting cases. Every fixture is synthetic — invented paths, invented
numbers — so running the suite reveals nothing about the answer key.

## Inputs

| path | sha256 / note |
|---|---|
| `_private/results/03_runs/{P5,P6,P7,P8,P9S,P9O}_live/*.jsonl` | 6 recordings, 102 sessions; read-only |
| `_private/harness_keys/answer_key.json` | key v1, unedited; sha256 in the run record |
| `_private/results/04_scores/question_sample.json` | frozen-20 group definition |
| `corpus-lab/bin/c_score_live.py`, `c_score_live_v2.py` | frozen; imported, not modified |
| `corpus-lab/state/phase10_gate_t_spec.md` | Gate T, committed `9da8744` at 20:56, **before** the re-score ran |

Commands:

```
.venv/Scripts/python.exe corpus-lab/bin/c_score_live_v3.py --phase P5_live --abs-phase P5_live_abs --max-turns 25
   (likewise P6_live, P7_live, P8_live at 25; P9S_live, P9O_live at 60)
.venv/Scripts/python.exe corpus-lab/bin/p10_rescore_compare.py
.venv/Scripts/python.exe corpus-lab/bin/p10_gate_t.py
```

## Outputs

| path | what |
|---|---|
| `corpus-lab/bin/c_score_live_v3.py` | sha256 `09f4105d81114dee…`, frozen at tag `scorer-v3-frozen-2026-09-16` |
| `corpus-lab/state/c_live_battery_v3__{P5,P6,P7,P8,P9S,P9O}_live.json` | aggregates, public |
| `_private/results/04_scores/live_v3__*.json` | per question |
| `corpus-lab/state/c_rescore_v2_vs_v3.json` | v2 beside v3, with a reason per difference |
| `corpus-lab/state/phase10_gate_t_result.json` | the gate, row by row |
| `corpus-lab/state/phase10_scorer_freeze.json` | the tag and the sha256 |
| `corpus-lab/tests/test_score_live_v3.py` | 14 tests |

Every scorer output carries `scorer_version`, `scorer_sha256`, `key_file`,
`key_sha256`, `group_definition_sha256` and its source recording paths.

## Gate

`corpus-lab/state/phase10_gate_t_spec.md`, commit `9da8744`, author date
2026-09-15T20:56:12+05:00 — **before** the re-score run record started. Eight rows.

| row | check | result |
|---|---|---|
| T1 | 7+ regression tests pass | **PASS** — 14 passed |
| T2 | v3 reproduces v2 `cited_right_page_equiv` on P8 exactly | **FAIL** — v2 4, v3 3 |
| T3 | v3 reproduces v2 `cited_unopened_total` on P8 exactly | **FAIL** — v2 0, v3 1 |
| T4 | P9S equivalence within ±1 of 13 | **PASS** — 13 |
| T5 | P9O equivalence within ±1 of 14 | **PASS** — 14 |
| T6 | `cited_unopened` reads Sonnet 0, Opus 2 | **FAIL** — Sonnet 1, Opus 4 |
| T7 | both Opus violations fall in `mb_04` | **FAIL** — they fall in `mb_07` and `pl_01` |
| T8 | `value_correct` 5/5 both, `n_keyed == 5` | **PASS** |

## Result

### The headline is robust

| battery | equivalence v2 | equivalence v3 |
|---|---|---|
| P9S (Sonnet) | 13/17 | **13/17** |
| P9O (Opus) | 14/17 | **14/17** |

Two scorers with materially different citation rules read the same recordings and agree
exactly. The 13 and 14 stand.

### `value_correct` was a denominator error, and the audit was right about it

12 of the 17 dev answerable questions carry no numeric value in the key, so
`value_correct` could never be true for them. Both models scored **5/5 on the 5 keyed
questions** (`n_keyed = 5`). The claims "reads the number wrong on 12 of 17" and "4 of 4
wrong totals on decade questions" are unsupported and are withdrawn.

### `cited_unopened` was mostly the scorer — but not in the way the audit said

| battery | v2 | audit predicted | **v3** |
|---|---|---|---|
| P9S (Sonnet) | 1, in `mb_07` | 0 | **1, in `rc_07`** |
| P9O (Opus) | 7, in `mb_04`(2) `pl_01`(3) `sd_05`(2) | 2, both in `mb_04` | **4, in `mb_07`(1) `pl_01`(3)** |

v3 confirms the audit on two cases and contradicts it on three:

- **`sd_05` (Opus, 2) — audit right.** Two CSV filenames named in prose, no page token
  anywhere near them. v3 classes both as mentions. Not violations.
- **`mb_07` (Sonnet, 1) — audit right.** 6 opens visible only in tool output, the
  citation is to a page among them. Not a violation.
- **`mb_04` (Opus, 2) — audit wrong.** The audit read this as two table lines quoted
  without opening, with "the session ended without opening it". The transcript says
  otherwise: the guard fired, and the model then opened the pages **inside a shell
  loop** (3 loop-only opens). In the reconstructed 8,233-character answer every one of
  its 4 citations is to a page it opened. **0 violations.**
- **`pl_01` (Opus, 3) — audit wrong.** The audit attributed these to loop opens. v3
  finds `n_opens_loop_only = 0` for this session and, checking all 14 paths it opened by
  any route, **no economic-survey document among them** — yet the answer cites four
  pages across three of them. These are **3 genuine open-before-cite violations**.
- **`rc_07` (Sonnet, 1) — both missed it.** The answer cites a survey edition at a page
  the session never opened, having opened four neighbouring editions. It appears only in
  the reconstructed 4,927-character answer, not in the 1,923-character fragment v2
  scored. **Fixing the fragment bug reveals violations as well as clearing them.**

So the corrected count is **Sonnet 1, Opus 4, zero fabricated** — lower than v2's 1 and
7, higher than the audit's 0 and 2. The STOP column was wrong; it was not wrong in the
direction the audit thought.

### Why P8 broke T2 and T3

The spec justified the exact-match bars by asserting "P8 has no loop opens and no
fragments". That premise is false: v3 finds **5 fragments and 11 loop-only opens** in
P8. P8 was never an inert control, so T2 and T3 were unpassable as written. The two
differences are both explained:

- equivalence 4 → 3: on three questions (`tr_10`, `tr_16`, `mb_05` in P5; `tr_10`,
  `tr_16` in P8) v3 finds **no page citation in the answer at all**. v2 credited them
  because the page *number* happened to appear somewhere in the answer text — often as a
  data value. v3 requires the page beside the path. One question (`rc_07`) moves the
  other way, gained because the fragment had hidden its citations.
- `cited_unopened` 0 → 1: `cd_04`, a fragment (1,166 → 2,725 chars) whose fuller answer
  contains a citation the fragment did not.

The same looseness explains P5's larger drop (6 → 3): the older batteries predate the
Sources-line discipline, so their answers name paths without page tokens beside them,
and v2's "page number anywhere" rule credited them. On P9, where CLAUDE.md v2 asks for
`<path> | pN` lines, the two scorers agree exactly.

## Adopted?

**Yes, with its Gate T failure on the record.** v3 is adopted as the analytical scorer
and is frozen at tag `scorer-v3-frozen-2026-09-16`, sha256 `09f4105d81114dee…`. Phase 4
scores every new recording with **four** scorers from one recording — v1 strict, v2, v3
with key v1, v3 with key v2 — and zero model calls.

Gate T stopping did **not** trigger the Phase 4 skip: that applies only if v3 moved the
headline equivalence by more than ±1 on a P9 battery, and it moved by **0**.

Per Plan E §1.8, any defect later found in v3 goes into the handoff for a v4. It is not
fixed tonight.

## Run record

`corpus-lab/experiments/p10_scorer_v3/run_record.json`, id `p10_rescore_v2_vs_v3`,
spec `corpus-lab/state/phase10_gate_t_spec.md` at commit `9da8744` (author date precedes
the run's `started_at`, which `docs_check.py` check C verifies).

## What this does not show

- **Nothing about retrieval quality.** v3 re-reads recordings. Not one model call was
  made to produce any number here, and no ranking, shelf, caption, prompt or guard
  behaviour was touched.
- **It does not prove v3 is correct in general** — only that it agrees with one
  independent reading on eight named quantities, four of which it disagreed with. The
  40-character citation window and the 1.25× fragment threshold are judgement calls
  fixed in advance; different values would move small counts.
- **It does not revisit any Phase 9 verdict.** All six batteries were STOP under v2's
  pre-registered Gate LIVE-5 and remain so. v3's numbers are *analytical corrections*,
  not re-adjudications.
- **It cannot tell a right answer from a wrong one** where the key carries no value.
  That is what Phase 2's key v2 is for, and even there the metric is reported, not gated.
- **The equivalence agreement at 13 and 14 is one sample per model.** Whether those
  numbers are stable is Phase 4's question, not this one's.
