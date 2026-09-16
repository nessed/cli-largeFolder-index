# p10_variance — how much does the number move when nothing changes?

Plan E Phase 4. Pre-registered in
[`corpus-lab/state/phase10_variance_spec.md`](../../state/phase10_variance_spec.md),
committed `d5849bb` at 2026-09-15T21:33:16+05:00 — **before the first battery ran**.

## Purpose

Every headline this project has published is one run of one battery. "Sonnet 13 of 17,
Opus 14 of 17" has been quoted, in the brief and in the demo pack, as though the gap of
one meant something about the two models.

Nobody had ever run the same thing twice.

This phase runs the **same stack, the same twenty questions, the same flags**, four times
on Sonnet and twice on Opus, changes nothing between runs, tunes nothing, and reports the
spread. It is not an attempt to improve a score. It exists to find out whether the
differences already published are larger than the instrument's own noise.

## Method

Four Sonnet batteries (`P9S`, `P10S1`, `P10S2`, `P10S3`) and two Opus (`P9O`, `P10O1`).
`P9S` and `P9O` were recorded last night and are re-scored here, not re-run — rule 18, one
recording, many scorers.

Frozen for all six: shelf `corpus-lab/02_stacks/s7_shelf` (**v1**), the `CLAUDE_MD_TEMPLATE`
in `c_stack.py`, the citation guard with `--v2`, and the flags
`--group frozen20 --parallel 2 --max-turns 60 --timeout 900 --capture full`.

Each battery ran Plan D §5.2 in full: exclusivity check, checksum snapshot, memory count,
install, three probes on a fresh token, battery in the foreground, verify, quarantine,
**unconditional teardown**, then scoring. Each has its own run record
(`p10_variance`, `p10_variance_s2`, `p10_variance_s3`, `p10_variance_o1`).
`checksums.py verify --against s7_phase10_live_pre` read **26 unchanged, 0 changed** after
every one of them, and the rung was clean before and after each.

Scoring is by four scorers from each single recording, with **zero model calls**.

## Inputs

- `_private/results/03_runs/{P9S,P9O,P10S1,P10S2,P10S3,P10O1}_live/` — the recordings
- scorer `c_score_live_v3.py`, sha256 `09f4105d81114dee…`, frozen at tag
  `scorer-v3-frozen-2026-09-16`
- key `_private/harness_keys/answer_key.json`, sha256 `8282da8668299011…`;
  key v2 `answer_key_v2_2026-09-16.json` for `vector_full`
- group definition sha256 `6bbe137e076030c3…`

## Outputs

- [`corpus-lab/state/c_variance_2026-09-16.json`](../../state/c_variance_2026-09-16.json)
- `corpus-lab/bin/p10_variance.py` — the reader that builds it

## Gate

There is no pass/fail gate here. The spec registered a **decision rule** instead, and the
rule binds whatever the numbers turn out to be:

> A difference between two single Sonnet batteries on `cited_right_page_equiv` smaller than
> the observed Sonnet range is within measured noise and **may not be used to prefer a
> configuration.** The Opus range from n = 2 is a **lower bound**, not a band.
> Sonnet-versus-Opus differences are not interpreted beyond one sentence.

## Result

### The noise is bigger than every difference we have published

Sonnet `cited_right_page_equiv`, four identical runs:

| scorer | P9S | P10S1 | P10S2 | P10S3 | mean | range |
|---|---|---|---|---|---|---|
| v3 | 13 | 13 | 11 | 11 | 12.0 | **2** |
| v2 (the pre-registered instrument every Phase 9 verdict came from) | 13 | 14 | 10 | 9 | 11.5 | **5** |

**The published Sonnet-versus-Opus gap is 1.** It is inside the noise under v3 and well
inside it under v2. So are the gaps between stacks that earlier phases reported. Under the
pre-registered rule, none of them may be used to prefer anything.

The v2 range of 5 is worth sitting with: the instrument that produced every Phase 9 gate
verdict swings by five questions out of seventeen when absolutely nothing changes.

### A steady total can hide questions that flip

Only **10 of the 17** answerable questions received the same v3 verdict in all four Sonnet
runs. Seven changed: `cd_04`, `mb_05`, `mb_07`, `pl_14`, `rc_05`, `rl_05`, `tr_04`. The
aggregate looks calmer than the thing it aggregates, and any claim about a *specific*
question from a *single* battery is weaker still than the headline.

### Opus's range is mostly a quota, not a model

Opus reads 14 then 12 — but **P10O1 is a partial battery**. Three of its twenty sessions
(`tr_07`, `tr_10`, `tr_16`) were cut off by the operating account's own session limit, and
all three are inside the answerable seventeen. Of the four questions whose verdict changed
between the two Opus runs, **three are exactly those three**. Only `rc_07` changed for a
reason that has anything to do with the model.

So the Opus range of 2 is not a measurement of Opus. **Opus variance is still essentially
unmeasured**, and it is reported here as unmeasured rather than dressed up as a band.

### The scorer cannot see a lost session

`sessions_lost` reads **0** for P10O1, in the same table as session accounting that reads
**17 of 20 completed**. `c_score_live_v3.py` recognises a lost session only as max-turns,
timeout, or empty output; a quota kill arrives as returncode 1 carrying ordinary-looking
assistant text, so all three were silently scored as wrong answers.

v3 is frozen and §7 forbids changing it for any reason, so it was not touched. The
denominator is reported beside it instead, from the driver records, by
`p10_variance.session_accounting()`. The contradiction is left visible on purpose: it is
the clearest evidence of the defect, and a reader can check it.

### Cross-model, the one permitted sentence

Both fall inside each other's observed range.

## Adopted?

**Yes, as a constraint, not as a result.** From here no configuration, model, or stack may
be preferred over another on a `cited_right_page_equiv` difference smaller than the
observed range, and the range is to be quoted next to any such number. This retires the
"Opus is better at citation than Sonnet" reading of the Phase 9 batteries. It does not
replace it with the opposite reading; it says the experiment could not tell.

## Run record

- `corpus-lab/experiments/p10_variance/run_record.json` — `p10_P10S1`
- `corpus-lab/experiments/p10_variance_s2/run_record.json` — `p10_P10S2`
- `corpus-lab/experiments/p10_variance_s3/run_record.json` — `p10_P10S3`
- `corpus-lab/experiments/p10_variance_o1/run_record.json` — `p10_P10O1`, partial
- `corpus-lab/experiments/p10_variance_table/run_record.json` — `p10_variance_table`

## What this does not show

- **Nothing about whether the system is any good.** Only how much its measured number
  moves when nothing changes.
- Four Sonnet points and two Opus points is a small sample. A range from n = 4 is a
  **lower bound** on the true spread, not a confidence interval, and it is deliberately
  reported as a range for that reason.
- Nothing about variance on a different corpus, a different question set, a different
  question count, or a different day's model serving.
- Nothing about why individual questions flip. Seven Sonnet questions changed verdict and
  this phase did not look into any of them.
- `P10O2`, a second Opus battery, was **not run**. See the cut recorded in
  `p10_variance_o1` and in the handoff: the account had already hit its session limit
  during `P10O1`, and a second partial Opus battery would have added a contaminated row to
  the one table whose entire purpose is to be trustworthy.
