# p10_variance_table — reading the six batteries together

The arithmetic step of Plan E Phase 4: no model call, no session, no corpus touched. It reads
the six scored batteries off disk and writes the variance table. The interpretation lives in
[`../p10_variance/README.md`](../p10_variance/README.md); this file records the build.

## Purpose

Six batteries had been scored and nobody had put them side by side. Until they are, "Sonnet
13 of 17" reads like a property of Sonnet rather than one draw from a distribution nobody had
sampled. This produces the table that makes the distinction visible, and does it with a script
rather than by hand, so it can be re-run when a seventh battery exists.

## Method

`p10_variance.py` reads the v2, v3 and v3-with-key-v2 score files for each phase tag and
reports, per metric: **every individual value, n, the denominator, mean, min, max and range**.
A sample standard deviation is printed **only at n >= 3**, because at n = 2 it is arithmetic
theatre. It also computes per-question agreement — how many of the 17 answerable questions got
the same v3 equivalence verdict in every repeat — because an aggregate can hold still while the
questions underneath it churn.

One addition was made to the script during this step: `session_accounting()`, which reads the
**driver** records to report how many sessions in each battery actually completed. It exists
because P10O1 is partial, because the spec's own instruction for a partial battery is to score
it *"with its denominator stated"*, and because the frozen scorer cannot supply that
denominator. It adds a block; it changes no metric value.

## Inputs

- `corpus-lab/state/c_live_battery_{v2,v3}__{P9S,P9O,P10S1,P10S2,P10S3,P10O1}_live.json`
  and the `__keyv2` variants
- `_private/results/04_scores/live_v3__*.json` for per-question agreement
- `_private/results/03_runs/*/` for session accounting
- scorer v3 sha256 `09f4105d81114dee...`, key v1 sha256 `8282da8668299011...`,
  group definition sha256 `6bbe137e076030c3...`

## Outputs

- `corpus-lab/state/c_variance_2026-09-16.json`

## Gate

No gate. The spec registered a **decision rule** instead, and the rule binds whatever the
numbers turned out to be: a difference smaller than the observed range may not be used to prefer
a configuration; the Opus range is a lower bound, not a band; Sonnet-versus-Opus is not
interpreted beyond one sentence.

## Result

Sonnet `cited_right_page_equiv` over four identical runs: **13, 13, 11, 11** under v3 (range 2)
and **13, 14, 10, 9** under v2 (range 5). Only **10 of 17** questions held the same verdict in
all four. Opus: 14 then 12, with P10O1 partial and 3 of its 4 changed questions being exactly
the 3 sessions a quota cut off. Cross-model: both fall inside each other's observed range.

`sessions_lost` reads 0 for P10O1 in the same table as accounting that reads 17 of 20. That
contradiction is left standing on purpose — it is the clearest evidence of the v3 blind spot,
and a reader can check it.

## Adopted?

**Yes, as a constraint rather than a result.** No configuration, model or stack may be preferred
on an equivalence difference smaller than the observed range, and the range is quoted next to
any such number from here on.

## Run record

`run_record.json` in this directory — id `p10_variance_table`, five notes including the
deviation for a deleted untracked dry-run file.

## What this does not show

- Nothing about whether the system is any good — only how much its number moves when nothing
  changes.
- Four Sonnet points and two Opus points is a small sample. A range from n = 4 is a **lower
  bound** on the true spread, not a confidence interval, and is reported as a range for exactly
  that reason.
- Nothing about **why** seven Sonnet questions flipped. This step did not look at one of them.
- Nothing about variance on another corpus, another question set, or another day's serving.
