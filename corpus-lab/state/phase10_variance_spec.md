# Phase 4 variance spec — pre-registered, 2026-09-16

**Written and committed before any Phase 4 probe or battery ran.** Plan E §4.

## The question

Every headline in this project is one run of one battery. "Sonnet 13/17, Opus 14/17"
has been quoted as though the gap between them meant something. Nobody has ever
measured how much a single battery's number moves when nothing changes at all.

Phase 4 runs the **same stack, same questions, same flags**, several times, and reports
the band. It is not an experiment to improve anything, and **no configuration may be
preferred on the basis of a difference smaller than that band.**

## What is frozen

Nothing in the stack changes. Same shelf (`corpus-lab/02_stacks/s7_shelf`, **v1**),
same `CLAUDE_MD_TEMPLATE` in `c_stack.py`, same guard with `--v2`, and the P9 flags:

```
--group frozen20 --parallel 2 --max-turns 60 --timeout 900 --capture full
```

`--capture full` adds fields to the record and changes no behaviour.

**Asserted before the first probe**, else stop:

- `c_score_live_v3.py`'s sha256 equals the value in `corpus-lab/state/phase10_scorer_freeze.json`;
- the tag `scorer-v3-frozen-2026-09-16` is in this branch's history;
- `checksums.py verify --against s7_phase10_live_pre` reads 0 changed;
- the rung is clean (no `CLAUDE.md`, no `.claude`) at the start and end of every battery.

## Tags and order

Sequential, with teardown and a clean-rung check between every battery:

| tag | model | note |
|---|---|---|
| `P10S1` | `claude-sonnet-5` | |
| `P10S2` | `claude-sonnet-5` | do not start if P10S1 exceeded its share |
| `P10S3` | `claude-sonnet-5` | **do not start if P10S1 + P10S2 together exceed $30** |
| `P10O1` | `claude-opus-5` | after 6 sessions project `cost × 20 / 6`; if > $40, stop and score the partial **with its denominator stated** |
| `P10O2` | `claude-opus-5` | **optional**, only under §4.4 below |

Procedure per battery: Plan D §5.2 verbatim — exclusivity check, checksum snapshot
`s7_phase10_live_pre`, memory count, install, three probes with a fresh 16-hex token,
battery in the foreground with `python -u`, verify, quarantine, **unconditional
teardown**, score. Each battery runs under its own `run_record.py`.

## Scoring: one recording, four scorers, zero model calls

Rule 18. After each recording, score with **v1 strict**, **v2**, **v3 with key v1**, and
**v3 with key v2**. No model call is ever made to score anything.

## Budget and clock

- Sonnet **≤ $45** across its three batteries; do not start the third if the first two
  exceed **$30**.
- Opus **≤ $40** for `P10O1`.
- Everything else **≤ $10**. **Total $95, hard.**
- Holdout looks: **0**.
- Before launching any battery: `remaining = deadline − now − 1 h`. A Sonnet battery
  needs 50 min, Opus 60 min, each including probes, verify and teardown. **Do not launch
  a battery that does not fit.** Cut in this order: `P10O2`, `P10O1`, `P10S3`, `P10S2`.
  Never cut Phase 5, a README, or a run record. Every cut is recorded with
  `run_record.py note` and in the handoff.

## What the report must contain

`corpus-lab/state/c_variance_2026-09-16.json` and a table in the handoff. For Sonnet over
{P9S, P10S1, P10S2, P10S3} and Opus over {P9O, P10O1[, P10O2]}, per metric:

`cited_right_page_equiv` (v2 **and** v3), `cited_right_page_strict`, `cited_unopened_total`
(v3), `mentioned_unopened` (v3), `value_correct` k/5, `vector_full` k/n, absence frozen 3,
sessions lost, median and p90 wall, cost.

For each: **every individual value, n, the denominator, mean, min, max, range**; sample
standard deviation **only where n ≥ 3**; and the **per-question agreement count** — how
many of the 17 received the same v3 equivalence verdict in every repeat.

Every table names `scorer_version`, `key_file`, the resolved model id, and the group
definition sha256.

## Pre-registered decision rule

- A difference between two single Sonnet batteries on `cited_right_page_equiv` **smaller
  than the observed Sonnet range** is *within measured noise* and **may not be used to
  prefer a configuration**.
- The Opus range from n = 2 (or 3) is a **lower bound** on Opus noise, not a band.
- **Sonnet-versus-Opus differences are not interpreted in this report** beyond the
  sentence *"both fall inside each other's observed range"* or its negation.

## §4.4 — when the optional second Opus battery may run

`P10O2` runs **only** if all four hold: Sonnet's three batteries total **≤ $36**; `P10O1`
**≤ $25**; the clock rule allows it; and the **$95 total** still holds.

## What this will not establish

- Nothing about whether the system is good — only how much its measured number moves when
  nothing changes.
- Four Sonnet points and two Opus points are a small sample. The range is a lower bound on
  the true spread, not a confidence interval, and it is reported as a range for that reason.
- It says nothing about variance on a different corpus, a different question set, or a
  different day's model serving.
