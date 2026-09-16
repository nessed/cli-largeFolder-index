# p10_variance_o1 — Opus repeat 1 — partial

One battery of Plan E Phase 4. Pre-registered in
[`corpus-lab/state/phase10_variance_spec.md`](../../state/phase10_variance_spec.md), committed
`d5849bb` at 2026-09-15T21:33:16+05:00, **before any battery ran**. The reading of all six
batteries together is [`../p10_variance/README.md`](../p10_variance/README.md); this file
records only what this one run did.

## Purpose

A second Opus point, to put some kind of bound on Opus noise where previously there was
one battery and a confident sentence.

It did not get there. **This battery is partial and must be read as partial.**

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

- `_private/results/03_runs/P10O1_live/` — the recording, made once
- `corpus-lab/state/c_live_battery_v2__P10O1_live.json`
- `corpus-lab/state/c_live_battery_v3__P10O1_live.json`
- `corpus-lab/state/c_live_battery_v3__P10O1_live__keyv2.json`
- `corpus-lab/state/phase9_probes__P10O1.json` — the three isolation probes

Scored by four scorers from that one recording. **No model call was made to score anything**
(rule 18).

## Gate

No pass/fail gate. Per-battery assertions only, all of which held even though the battery
did not complete: checksums **26 unchanged, 0 changed**; rung clean before and after; three
isolation probes passed; 0 memory files under the corpus project key; quarantine scanned and
moved 0 transcripts. **Nothing about the harness failed here. The account ran out of quota.**

## Result

`cited_right_page_equiv` **12 of 17** under v3, **11 of 17** under v2. Strict 3.
`cited_unopened` 5, `mentioned_unopened` 5, answer fragments 8, loop-only opens 23.
Absence 3 of 3. `value_correct` 5 of 5 keyed; `vector_full` 3 of 9 against key v2.
Median wall 96.1s, p90 372.0s. Driver cost **$20.5743**, battery wall 1978s.

**3 of the 20 sessions never answered.** `tr_07`, `tr_10` and `tr_16` ended with returncode 1
and the assistant text *"You've hit your session limit - resets 3:20am (Asia/Karachi)"* — the
operating **account's** own quota, not a harness fault, not a timeout, not a refusal. `tr_07`
had already made 22 tool calls and spent $1.28 when it was cut; `tr_10` 7 calls and $0.46;
`tr_16` 0 calls and $0. All three are trajectory questions, which this group runs last.

All three sit inside the answerable 17, and **all three were scored as misses**, so 12 of 17 is
really 12 of the 14 questions that were allowed to finish. Both numbers are recorded; neither is
adjusted by hand.

`c_score_live_v3.py` reports `sessions_lost` as **0** for this battery. It recognises a lost
session only as max-turns, timeout, or empty output, and a quota kill arrives looking like an
ordinary answer. v3 is frozen at its tag and section 7 forbids changing it for any reason, so it
was **not** touched; the denominator is reported beside it from the driver records instead, by
`p10_variance.session_accounting()`.

The consequence for the phase: of the 4 questions whose verdict differs between P9O and P10O1,
**3 are exactly these 3**. Only `rc_07` moved for a reason involving the model. The apparent
Opus range of 2 is mostly a measurement of a quota, and **Opus variance remains unmeasured**.

## Adopted?

**No.** This battery is recorded, not adopted. It contributes a caveat to the variance
table rather than a bound. `P10O2`, the optional second Opus battery, was **cut** as a direct
result: all four section 4.4 conditions held, but running another Opus battery under the same
quota would most likely have produced a second partial row, and a second contaminated row makes
the one table whose purpose is trustworthiness worse rather than better.

## Run record

`run_record.json` in this directory — id `p10_P10O1`. The phase-level record is
`../p10_variance_table/run_record.json`.

## What this does not show

- Nothing about whether the system is any good. One battery is one point.
- Nothing on its own. A single battery's number is only interpretable **against the range in
  the variance table**, which is what this run exists to help build.
- Nothing about a different corpus, a different question set, or a different day's serving.
