# Phase 9 live battery — pre-registration

Written and committed **before any session of this battery ran**. Nothing in this file
may be widened, re-denominated or re-read after the numbers exist. It is the plan's
section 5.1, transcribed here so the gate lives beside the result.

## Configuration

- The production stack as it stands after Phases 1–3 of
  `plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md`:
  the latency fixes, the shelf that Gate S selected, `find --compact 40`,
  CLAUDE.md v2, and the citation guard v2 behind `STOP_GUARD_V2=1`.
- Harness limits: `--max-turns 60 --timeout 900 --parallel 2`.
  P5–P8 ran at 25 turns / 300 s. The professor has neither, and 1–5 of every 17
  sessions per battery ended with **no answer text at all** because one of those
  two limits fired; every one was scored a miss. Raising them measures the system
  rather than the harness.
- Models and tags: `claude-sonnet-5` → `P9S`, `claude-opus-5` → `P9O`.
  If the auth probe's init event reports a different resolved model id, the battery
  still runs and every table names the id the account actually gave.
- Questions: the frozen 20 (`--group frozen20`) — 17 answerable, 3 absence.
- Scoring: `c_score_live_v2.py`, which reports the strict column beside the new ones.
  The frozen `c_score_live.py` is unchanged and remains the strict reference.

## Comparability

v2 records, per session, whether the answer was produced within 300 s
(`answered_within_300s`), so a like-for-like row against P5–P8 exists even though
this battery runs under a longer clock.

## Gate LIVE-5 — per model, on the 17 answerable questions

The equivalence scorer **did ship**: the generator's placement records reproduce
322 of 332 gold evidence addresses (0.970, bar 0.95), recorded in
`state/c_score_live_v2_selftest.json`. So the gate reads on the equivalence column:

- **PASS** — `cited_right_page_equiv ≥ 5/17`
  **and** `cited_unopened_total = 0`
  **and** absence (frozen 3, the v2 rule `absence_ok3`) `≥ 2/3`
  **and** `no_answer_cause ∈ {max_turns, timeout}` on **≤ 1** session.
- **WEAK** — `cited_right_page_equiv` 3–4/17 with the other three conditions met.
- **STOP** — otherwise.

Had equivalence not shipped, the gate would have read on `cited_right_page_strict`
with PASS ≥ 4/17 and WEAK 2–3/17. That fallback is written here for the record; it
does not apply.

Reported, **not gated**: `value_correct`, `value_wrong_confident`,
`cited_right_page_strict`, L0–L5 from `c_live_forensics.py`, `cited_no_path`,
median and 90th-percentile wall seconds, and cost.

## Decision table for CLAUDE.md v2

If **both** models read STOP **and** neither beats the best recorded strict number
(2/17), revert `CLAUDE_MD_TEMPLATE` to its Phase 2 text — keeping the `--compact`
code, the guard v2 code, and the latency and shelf fixes — and record
`CLAUDE_MD_V2_REVERTED`. Otherwise keep it.

## Budget and stop conditions

- Sonnet battery ≤ $20 reported, Opus battery ≤ $80 reported (`cost_usd` from
  `ask.py`; notional on a Max plan, but it is the only meter there is).
- After the first **6** Opus sessions complete, project `cost_so_far × 20 / 6`.
  If that exceeds $80: stop the Opus battery, record `OPUS_BUDGET_STOP n-of-20`,
  and score the completed sessions as a **partial with its denominator stated**.
- Phase 5b (a second Sonnet battery, tag `P9S2`, identical configuration) runs only
  if cumulative live spend is under $40 and the clock allows. It has no gate; it is
  the project's first measured live variance.
- Holdout looks spent by this battery: **zero**. Nothing here runs with `--holdout`,
  `--holdout2`, or `c_page_holdout.py`.

## Procedure

Exactly Session Log C.5 with the changed flags: confirm the rung is clean, take a
checksum snapshot labelled `s7_phase9_live_pre`, confirm zero memory files under the
corpus project key, install the stack, run the three probes per model (auth, iso1,
iso2 with a freshly generated 16-hex token), run the battery in the foreground under
`python -u`, then verify checksums, quarantine transcripts and **tear down
unconditionally**, in every exit path including failure.
