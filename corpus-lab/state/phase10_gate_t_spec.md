# Gate T — pre-registered, 2026-09-16

**Written and committed before `c_score_live_v3.py` was run against any recorded
battery.** Plan E §1.6 / §1, and Plan D §0 rule 3: a gate is a number written before
the number exists. `docs_check.py` check C fails any run record whose spec commit is
dated after the run started, which is what makes this file's commit time load-bearing.

## What Gate T is for

Gate T does **not** ask whether v3 scores higher. It asks whether v3 reproduces the
*independent audit's own predictions* — predictions made by a different reader, from
the same transcripts, before v3 existed. If v3 agrees, the corrected numbers rest on
two independent derivations. If it disagrees, that is a finding to record, not
something to tune away (Plan E decision 1).

## The bars

| # | check | bar |
|---|---|---|
| T1 | all seven regression tests in `corpus-lab/tests/test_score_live_v3.py` pass | all pass |
| T2 | v3 on `P8_live` reproduces v2's `cited_right_page_equiv` **exactly** | equal |
| T3 | v3 on `P8_live` reproduces v2's `cited_unopened_total` **exactly** | equal |
| T4 | v3 `cited_right_page_equiv` on `P9S_live` is within **±1** of v2's **13** | 12–14 |
| T5 | v3 `cited_right_page_equiv` on `P9O_live` is within **±1** of v2's **14** | 13–15 |
| T6 | v3 `cited_unopened_total` reads **Sonnet 0, Opus 2** | exactly 0 and 2 |
| T7 | both Opus `cited_unopened` counts fall in `mb_04` | both in `mb_04` |
| T8 | `value_correct` reads **5/5** for both P9 batteries, with `n_keyed == 5` | 5/5, n=5 |

T2 and T3 are exact because P8 has no loop opens and no fragments — every v3 change is
inert there, so any difference on P8 is a bug in v3 rather than a correction.

## Fixed parameters (registered here so they cannot be chosen after seeing results)

- **Citation window: 40 characters.** A path counts as a citation if a `p<N>` / `page N`
  token lies within 40 characters of it, or if it appears in the `<path> | p<N>` form.
- **Value tolerance: ±0.5%**, inherited unchanged from v2.
- **`n_keyed`** = questions with `n_accepted_values > 0`. Unkeyed questions are in no
  value denominator.
- **A page named in `series` / `tables` / `inside` output is not an open.** Only an
  `OPENED <rel> p<N>` line in a tool result, or an `open "<rel>" <N>` command whose path
  is not a shell placeholder, or a `files_opened` hook record, counts.
- **Fragment rule:** a recorded answer is a fragment when the session contains at least
  one Stop-hook block and the reconstructed full answer is more than 1.25× its length.

## Verdict rule

Every row must hold. Any row missed → **`GATE_T_STOP`**: record which row and the
actual values, **do not touch v3**, and continue the night. v3 is then reported as
"diverges from the independent audit on \<row\>", and Phase 4 scores with both v2 and v3
regardless.

**Additional stop condition (Plan E §7):** if Gate T reads STOP *and* v3's equivalence
count differs from v2 by more than ±1 on either P9 battery, Phase 4 is skipped
entirely — a scorer that moved the headline is not the instrument to measure variance
with. Phases 3 and 5 still run, and the morning note says so.

## What Gate T does not establish

It does not establish that v3 is correct in general — only that it agrees with one
independent reading of six recorded batteries on eight named quantities. It says
nothing about retrieval quality, and it does not revisit any Phase 9 verdict: those
were set by the pre-registered v2 scorer and stand as recorded.
