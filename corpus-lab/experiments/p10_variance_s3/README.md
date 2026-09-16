# p10_variance_s3 — Sonnet repeat 3 of 3

One battery of Plan E Phase 4. Pre-registered in
[`corpus-lab/state/phase10_variance_spec.md`](../../state/phase10_variance_spec.md), committed
`d5849bb` at 2026-09-15T21:33:16+05:00, **before any battery ran**. The reading of all six
batteries together is [`../p10_variance/README.md`](../p10_variance/README.md); this file
records only what this one run did.

## Purpose

The third and last Sonnet repeat. The spec barred it from starting if the first two
together exceeded $30; they came to **$21.12**, so it ran. Four points is the minimum at which
a sample standard deviation is worth printing at all, and the spec permits one only at n >= 3.

## Method

Plan D section 5.2 verbatim: exclusivity check, checksum snapshot, memory
count, install into `harness/corpus_15000`, three isolation probes on a fresh 16-hex token,
the battery in the foreground, verify, quarantine, **unconditional teardown**, then scoring.

Frozen: shelf `corpus-lab/02_stacks/s7_shelf` (**v1**), the `CLAUDE_MD_TEMPLATE` in
`c_stack.py`, the citation guard with `--v2`, and the flags
`--group frozen20 --parallel 2 --max-turns 60 --timeout 900 --capture full`.
Nothing was changed from the battery before it. That is the entire point.

## Inputs

- corpus `harness/corpus_15000`, question group `frozen20`
  (group definition sha256 `6bbe137e076030c3...`)
- scorer `c_score_live_v3.py` sha256 `09f4105d81114dee...`, frozen at tag
  `scorer-v3-frozen-2026-09-16`; scored beside `c_score_live_v2.py`
- key v1 `_private/harness_keys/answer_key.json` sha256 `8282da8668299011...`;
  key v2 `answer_key_v2_2026-09-16.json` sha256 `773ab75e5018ec58...`

## Outputs

- `_private/results/03_runs/P10S3_live/` — the recording, made once
- `corpus-lab/state/c_live_battery_v2__P10S3_live.json`
- `corpus-lab/state/c_live_battery_v3__P10S3_live.json`
- `corpus-lab/state/c_live_battery_v3__P10S3_live__keyv2.json`
- `corpus-lab/state/phase9_probes__P10S3.json` — the three isolation probes

Scored by four scorers from that one recording. **No model call was made to score anything**
(rule 18).

## Gate

No pass/fail gate. Per-battery assertions only, all of which held:
`checksums.py verify --against s7_phase10_live_pre` read **26 unchanged, 0 changed**; the rung
was clean before and after; all three isolation probes passed; 0 memory files under the corpus
project key; quarantine moved 0 transcripts.

## Result

`cited_right_page_equiv` **11 of 17** under v3, **9 of 17** under v2. Strict 1.
`cited_unopened` 3, `mentioned_unopened` 14, answer fragments 9, loop-only opens 0.
Absence 3 of 3. `value_correct` 4 of 5 keyed; `vector_full` 6 of 9 against key v2.
Median wall 81.8s, p90 303.6s. Driver cost **$10.7911**.

With this run the four Sonnet points are 13, 13, 11, 11 under v3 and 13, 14, 10, 9 under v2 —
**range 2 and range 5**. The v2 figure is the one that matters most, because v2 is the scorer
every Phase 9 gate verdict was adjudicated with.

## Adopted?

Not a result to adopt — a data point, and the one that completes the Sonnet range.

## Run record

`run_record.json` in this directory — id `p10_P10S3`. The phase-level record is
`../p10_variance_table/run_record.json`.

## What this does not show

- Nothing about whether the system is any good. One battery is one point.
- Nothing on its own. A single battery's number is only interpretable **against the range in
  the variance table**, which is what this run exists to help build.
- Nothing about a different corpus, a different question set, or a different day's serving.
