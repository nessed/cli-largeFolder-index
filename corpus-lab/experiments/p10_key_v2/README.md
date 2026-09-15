# p10_key_v2 — a versioned key for the questions that had none

Plan E Phase 2. **Reported, not gated.**

## Purpose

`value_correct` read 5/17 for both models on the 2026-09-15 night, and the report
turned that into "reads the number wrong on 12 of 17". It was never a measurement of
the models. 12 of the 17 dev answerable questions carry no numeric
`expected_answer.value` and no alternate with a value, so `accepted_values()` returns
an empty list and `value_correct` cannot be true for them whatever the model writes.
The split is a property of the key.

But those 12 are not unanswerable. They are questions whose right answer is a *series*:
"how has development spending changed over the last decade" has ten right numbers, not
one. So Phase 2 builds a second key carrying, for each such question, the vector of
values the generator actually printed — and measures whether the answer carried them.

This is **the project's first measurement of table reading**. There is no earlier
number to compare it with, and it gates nothing.

## Method

`c_key_v2_build.py`, a scoring script under rule 4. **No value was written by hand**
(Plan E decision 6): the script reads the generator's own per-document placement
records, `_private/harness_keys/pdf_index/*.json`, each of which lists its tables with
`series_id`, `vintage_id`, `page_index` and `cells: {fiscal_year: value}`.

For every question the base key carries no value for:

- **trajectory** and **multi-branch** — for each evidence address, take its `series_id`
  and fiscal year and collect every distinct value any vintage of that series prints
  for that cell. Keyed `<series_id>|<fy>`, so a multi-branch question gets one entry
  per branch and per year instead of colliding on the year.
- **reconciliation** — the same, which naturally yields the several competing values
  the two documents print for one cell.
- **relationship** and **stale-document** — `value_scorable: false`, reason
  `"text question"`. A key cannot score prose by value, and manufacturing a denominator
  for it would be the same mistake this phase exists to correct.

`answer_key.json` is **never edited** (rule 17). The builder writes a new dated file and
refuses to overwrite it if it already exists. The base key's sha256 is recorded inside
the new key, and `answer_key.json`'s hash after the build is byte-identical to the one
recorded — checked and reported below.

Scoring uses the already-frozen v3 with `--key <file> --tag keyv2`. `--key` was part of
v3's interface before the freeze, not a change after it.

## Inputs

| path | sha256 |
|---|---|
| `_private/harness_keys/answer_key.json` (base, unedited) | `8282da8668299011…` |
| `_private/harness_keys/pdf_index/*.json` | 9,240 files, 86,361 tables with cells |
| `_private/results/03_runs/{P9S,P9O}_live/*.jsonl` | the same recordings as Phase 1 |
| `corpus-lab/bin/c_score_live_v3.py` | `09f4105d81114dee…`, frozen at `scorer-v3-frozen-2026-09-16` |

```
.venv/Scripts/python.exe corpus-lab/bin/c_key_v2_build.py
.venv/Scripts/python.exe corpus-lab/bin/c_score_live_v3.py --phase P9S_live \
    --abs-phase P5_live_abs --max-turns 60 --key <key v2> --tag keyv2
   (likewise P9O_live)
```

## Outputs

| path | sha256 / note |
|---|---|
| `_private/harness_keys/answer_key_v2_2026-09-16.json` | `773ab75e5018ec58…` |
| `corpus-lab/bin/c_key_v2_build.py` | the only thing that read the key |
| `corpus-lab/state/c_live_battery_v3__P9S_live__keyv2.json` | aggregate |
| `corpus-lab/state/c_live_battery_v3__P9O_live__keyv2.json` | aggregate |
| `_private/results/04_scores/live_v3__P9{S,O}_live__keyv2.json` | per question |

Key v2 covers 135 questions: 45 already keyed, 50 given a vector, 25 text questions,
15 unkeyed and underivable. In the frozen 20: 4 trajectory, 3 multi-branch and 2
reconciliation get vectors; 2 stale-document, 1 relationship and 3 absence do not.

## Gate

**None.** Plan E §2.3 fixes this as reported, not gated, and fixes the wording. No
pre-registered bar exists because there is no prior measurement to set one against.

## Result

The sentence Plan E §2.3 permits, filled in:

> On the 7 trajectory and multi-branch questions, the answer carried every expected
> year's value on **4 of 7** (Sonnet) and **4 of 7** (Opus), scored by v3 against key v2
> (sha `773ab75e5018ec58…`). This is the project's first measurement of table reading;
> there is no earlier number to compare it with.

Including the 2 reconciliation questions, both models read **6 of 9** complete, with a
mean per-question coverage of **0.741** each.

| question | cells | Sonnet coverage | Opus coverage |
|---|---|---|---|
| `tr_04` | 8 years | **1.000** | **1.000** |
| `tr_07` | 4 years | **1.000** | **1.000** |
| `tr_10` | 6 years | **1.000** | 0.333 |
| `tr_16` | 6 years | **1.000** | **1.000** |
| `mb_04` | 3 branches | 0.333 | 0.333 |
| `mb_05` | 3 branches | 0.000 | 0.000 |
| `mb_07` | 3 branches | 0.333 | **1.000** |
| `rc_05` | 1 cell | **1.000** | **1.000** |
| `rc_07` | 1 cell | **1.000** | **1.000** |

The two models' aggregates are identical (6/9, 0.7407) but their answers are not: they
differ on `mb_07` and `tr_10`, one swap each way, which is why the means coincide. That
is arithmetic, not a bug — it was checked because identical figures to four decimals
across two models is exactly the shape a degenerate metric makes.

**The signal is in the split.** Trajectory questions — read one table, carry eight or
six years across — come back complete. Multi-branch questions — gather one cell from
each of three different series in three different documents — come back at a third or
at nothing, for both models. Whatever the weakness is, it is not "reads numbers wrong";
it is assembling one answer from several places.

**How permissive this metric is, stated plainly.** A cell accepts any value any vintage
of that series prints, per Plan E §2.1. For the multi-branch cells that is **up to 16
accepted values** (11 even when restricted to the vintage the key's own address names);
for trajectory cells, up to 10. So a hit is cheap — which makes the trajectory result
weaker evidence than it looks, and the multi-branch failures *stronger*: those questions
scored 0 and 0.333 against 16 chances per cell. Both the permissive vector and the
vintage-restricted one are recorded per question in the key
(`expected_vector` and `expected_vector_cited_vintages`), so a future scorer can use the
tighter one without rebuilding anything.

## Adopted?

**Yes as a recorded measurement, no as a gate.** Key v2 is a new file with a date in its
name; `answer_key.json` is unchanged and its sha256 after the build is
`8282da86682990112f66d86ea7235491efccfe6b52963b99377ec62aef7273bb`, identical to the
`base_key_sha256` the new key records. Phase 4 scores every new recording against both
keys.

No sentence of the form "reads the number wrong on N of 17" is written anywhere. The
corrected `value_correct` is **5/5 with `n_keyed = 5`** for both models.

## Run record

`corpus-lab/experiments/p10_key_v2/run_record.json`, id `p10_key_v2`.

## What this does not show

- **Nothing about retrieval.** No model call was made; these are the Phase 9 recordings
  re-read against a different key.
- **It is not a hard test of table reading.** The metric asks whether the expected
  numbers *appear somewhere in the answer text*, within ±0.5%. It does not check that
  they are attached to the right year, the right series, or the right claim. An answer
  reciting a whole table scores 1.000 whether or not it says anything true about it.
- **The values are the generator's, not the world's.** They are right by construction
  for this fixture corpus and say nothing about reading a real document.
- **9 questions, one run each.** `mb_07` and `tr_10` each moved a full step between two
  models; nothing here separates a model difference from run-to-run noise. Phase 4
  measures the noise band, and these vector numbers are computed for every battery there
  so a later reader can see how much they wander.
- **The two stale-document and one relationship question remain unmeasured by value**,
  by design. They are marked `value_scorable: false` with the reason recorded, rather
  than being silently counted as failures — which is what produced the 5/17 error in the
  first place.
