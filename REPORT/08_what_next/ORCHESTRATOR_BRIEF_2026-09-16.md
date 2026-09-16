# Orchestrator brief — what the 2026-09-15 night run did, and what is now decidable

> **Corrected 2026-09-16.** Some numbers below were withdrawn or restated after three faults were found in the scoring program. See [`REPORT/08_what_next/CORRECTION_2026-09-16.md`](CORRECTION_2026-09-16.md). The gate verdicts are unchanged.

For a planning agent deciding the next session. This is the complete account, not the demo
version. Everything below is measured unless it says otherwise; where a number is soft it
says so.

Source plan: `plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md`, 981 lines,
phases 0–7, gates pre-registered before any number existed.
Branch `phase9-production-hardening`, 9 commits off `master` at `12de91b`. **Nothing pushed.**
Step-level audit trail: `corpus-lab/state/phase9_checkpoint.json` (every step start/end/result).

---

## 1. Execution status

| phase | what it was | status |
|---|---|---|
| 0 | reproduce baselines, checksum, branch | done |
| 1 | latency, rank-preserving | done, **Gate 1 PASS every row** |
| 2 | shelf v2 (3 changes) | done, **Gate S STOP** — not shipped |
| 3 | `find --compact`, CLAUDE.md v2, guard v2, battery limit flags | done |
| 4 | scorer v2 (equivalence) | done, registry validated 0.970 vs bar 0.95 |
| 5 / 5c | live battery both models + professor rehearsal | done, **Gate LIVE-5 STOP on both** |
| 5b | variance battery (3× same config) | **skipped** — plan's own first-to-sacrifice |
| 6 | one-command installer, cold test | done, **Gate P PASS** |
| 7 | findings, handoff, demo, README, manifest | done |

Every checkpoint row reads `done` except `5b` (`skipped`). Plan step 1.4 (the "never import
fastembed" tripwire) has no checkpoint row because it was implemented as an assertion inside
`c_shelf_bench.py` and verified as part of 1.5 — `fastembed_loaded: false` is recorded for
every NO_MODEL command in `c_shelf_bench.json`.

Closing checks: both rungs clean (no `CLAUDE.md`, no `.claude`), 0 memory files under either
corpus project key, checksums **18 unchanged / 0 changed / 0 missing**, 9 canary transcripts
quarantined and 0 left in place, self-tests **25 / 10 / 24 / 18**, working tree clean,
**0 holdout looks spent**, 0 contamination events.

---

## 2. What changed, with the evidence

### Shipped to production (v1 shelf)

**Latency.** Warm-vs-warm, old code restored from git for the baseline, 3 repeats, medians,
fresh subprocess per call (`corpus-lab/state/c_shelf_bench.json`, label pair
`baseline_v1_warm` → `after_phase1`):

| command | before | after | Gate 1 bar |
|---|---|---|---|
| `open` | 2.95 s | **0.18 s** | ≤ 0.5 |
| `coverage` | 2.89 s | **0.17 s** | ≤ 0.8 |
| `find` | 4.14 s | **1.15 s** | ≤ 3.5 |
| `series` | 4.52 s | **1.22 s** | ≤ 5.0 |
| `inside` | 1.69 s | **1.14 s** | ≤ 2.5 |

Three mechanisms: a page-range cache so `open` stops scanning 1.2 M rows for an unindexed
column; a persisted coverage count keyed on db size+mtime; caption vectors read from a mmapped
float16 store instead of re-embedding per call.

**Rank preservation is proved, not asserted** — this is the part that makes the speedup free:
300/300 sampled pages byte-identical old vs new (`c_open_equiv.json`); stored caption vectors
match fresh ones 200/200 at cosine 1.0 (`c_caption_align.json`); `inside` returns the identical
top-5 **set and order** on 57/57 dev addresses (`c_inside_equiv.json`). All three offline
baselines and all four self-tests reproduce exactly.

**Display depth.** `find --compact N` / `--show i,j,k`. Offline the gold publication is in the
top 12 on **11/17** and in the top 40 on **14/17** (`c_compact_depth.json`) — the old
twelve-item display was capping the whole chain at 11 before the model read a word. This is
Experiment H's mechanism (F60/F63) shipped at zero extra model calls.

**Citation guard v2** (behind `--v2`, which the installer passes): catches prose page numbers,
`Sources` lines naming files the session never opened, and answers stating figures with no
citation at all. Self-test 9 → 24 checks.

**Scorer v2** (`c_score_live_v2.py`): equivalence against a generator placement registry, value
comparison against the key's alternates, no-answer cause attribution, `cited_no_path`. The
frozen strict scorer is untouched and still reported alongside.

**Harness limits**: `c_live_battery.py --max-turns/--timeout`, defaults unchanged.

**Installer**: `setup_folder.py` doctor / install / status / ask / uninstall, for any folder.

### Built, measured, rejected by its own gate

**Shelf v2 — Gate S STOP.** Three pre-registered changes: (a) bare-year edition fallback,
(b) fragment-family merge, (c) consensus primary. `c_shelf_v2_gate.json`:

- all five recall rows held exactly (10/17, 16/17, 52/57, 11/11, 4/4)
- duplicate publications occupying top-40 slots across 17 dev lists: **35 → 0** (change b)
- **gold evidence files hidden as non-primary: 20 → 31** ← the STOP

Diagnosed, not tuned: change (a) gave `fy_primary` to 4,333 documents that had `None`. The
builder reads `fy_primary=None` as "no edition, every survivor is a primary", so those clusters
flipped to "one primary, hide the rest". Primaries fell 7,694 → 4,198 and 11 more gold files
landed on the hidden side. **Production stays on v1.** The v2 shelf is kept on disk so the next
session can take the three changes apart without rebuilding.

### Two measurement instruments were found to be wrong

Both were inflating the failure rate, i.e. the project had been underselling itself:

1. **The harness was killing sessions and scoring them as misses.** 1–5 per battery produced no
   answer text at all under a 25-turn / 300 s cap. Raised to 60/900: **0 of 40** lost, with 11
   sessions running past the old limits and all 11 producing full cited answers.
2. **The scorer was stricter than its own answer key,** which carries acceptable alternates on
   45 of 135 questions. Re-scoring P5–P8 on unchanged recorded transcripts: strict 0/2/1/1 →
   equivalence 6/4/9/4 of 17.

**An orchestrator should treat this as the load-bearing caveat on the Phase 5 result.** Three
changes landed at once — harness limits, scorer, display depth — and this battery cannot
separate them. Two of the three are error removal rather than new capability.

---

## 3. Live result (Phase 5, LIVE-5)

Frozen 20 questions, v1 shelf, CLAUDE.md v2, guard v2, `--max-turns 60 --timeout 900`,
`--parallel 2`. Both model ids resolved exactly as requested; all six isolation probes passed.

| | claude-sonnet-5 | claude-opus-5 | gate |
|---|---|---|---|
| cited_right_page_equiv | **13 / 17** | **14 / 17** | PASS ≥ 5 |
| cited_right_page_strict | 1 / 17 | 3 / 17 | previous project record 2/17 |
| value_correct | 5 / 17 | 5 / 17 | reported |
| value_wrong_confident | 0 | 0 | reported |
| figures_ungrounded | 0 | 1 | reported |
| forbidden (decoy) citations | 1 | 4 | reported |
| absence, frozen 3 | 3 / 3 | 2 / 3 | needs ≥ 2 |
| sessions lost to caps | 0 | 0 | needs ≤ 1 |
| **cited_unopened_total** | **1** | **7** | **needs 0 — the STOP** |
| median / p90 wall | 99 s / 311 s | 118 s / 308 s | |

**Verdict STOP on both**, each on the unopened-citation row alone. 13–14 of 17 is the best live
citation reading the project has taken; the previous best was 9/17, itself a re-score of old
transcripts performed the same night.

Two structural facts worth carrying forward:

- **Retrieval is no longer the bottleneck; reading is.** 13–14 of 17 on finding the page,
  **5 of 17 on the number**. On decade-long trajectory questions Sonnet opened the right page
  4 of 4 times and got the total wrong 4 of 4 times. That is arithmetic and table-reading, not
  search.
- **The system routinely answers from a different official publication than the key
  anticipated** — `equiv_via_other_publication` is 12 (Sonnet) and 11 (Opus) of the equivalence
  hits. This is why strict and equivalence disagree so widely, and why forensics' L0 count and
  the equivalence count tell different stories. Both readings are reported; neither is hidden.
- **Model split:** Opus writes the better answer and is looser about provenance (7 unopened
  citations vs 1, 4 decoy citations vs 1, the only ungrounded figure). Sonnet cites better.

---

## 4. Run record and budget

- **Live sessions:** 46 charged this night — 34 new battery sessions plus 6 probes, 3 rehearsal
  and 2 portable cold-test, against a budget of 95. (The absence half of each battery was scored
  from earlier recorded transcripts, not re-run.)
- **Cost:** $37.83 cumulative. Per-battery figures differ slightly between the driver
  ($11.01 / $23.35) and the v2 scorer files ($12.74 / $25.09) because the scorer totals include
  the reused absence sessions. **Unreconciled bookkeeping, flagged rather than papered over.**
  Caps were $20 Sonnet / $80 Opus / $10 other — all respected. Rule-12 projection at 11 Opus
  sessions read $24.24 → CONTINUE.
- **Holdout looks spent: 0.** Holdout-2 still has its one look.
- **Contamination: 0.** Fresh 16-hex canary; neither model revealed the decoy or the private
  tree.

---

## 5. Deviations from the plan, recorded rather than resolved

1. **Guard v2 switched by `--v2` argument, not a `set STOP_GUARD_V2=1 &&` hook prefix.** A hook
   command runs under whichever shell the host picks and that prefix means different things to
   cmd.exe and bash — it could have silently disabled the guard while the self-test still
   passed. Both forms work and both are tested; the installed hook was verified to end `--v2`.
2. **Gate S's "gold families that are fragments" counter reads 0 on v1,** so it could not fire
   for the defect it was written for. Reported as it stands (0 → 0); a second counter measuring
   the harm §1.3 actually described (fragment slots in the top 40, 35 → 0) was added alongside,
   **recorded not gated**, with no influence on the STOP.
3. **Two contaminated benchmarks, both kept under their own labels rather than deleted.** One
   ran under the Phase 2 embedding load; the more serious one compared a cold baseline to a warm
   after-run and roughly doubled the apparent win. Corrected by restoring the pre-Phase-1 code
   from git and re-benching both sides warm. The correction moved Gate 1 from SHORTFALL to PASS
   and was reported to the user unprompted.
4. **`n_primary_changed` = 306 exceeds the plan's 150–170 estimate** because it counts every
   cluster where the v1 and v2 sort keys disagree, not only clusters where the sibling count
   changes. Definition stated with the number.
5. **A `git add -A` briefly tracked 12,809 fixture paths** (the ignore rule named `s7_shelf` but
   not `s7_shelf_v2`). Untracked in the next commit, rule extended.
6. **`corpus-lab/state/c_shelf_build_v2.json` now holds the Phase 6 portable 500-file build,**
   not the 15,000-file v2 build — the later run overwrote it. The 15,000-file v2 figures survive
   in `c_shelf_v2_gate.json` and in the checkpoint's step 2.2 row. Cosmetic, but a reader of
   that one file alone would be misled.

---

## 6. What was deliberately not done

Per the plan's standing rule — no change may be made after seeing a gate fail — these were
written down instead of acted on:

- **Shelf v2 change (b) alone, pre-registered.** (b) is the change that did the good (35 → 0
  duplicate slots); (a) is the change that caused the STOP. Splitting them is the obvious next
  experiment and needs no rebuild. **Cheapest high-value item on the list.**
- **The `fy_primary=None` repair** — keep a cluster's "every survivor is primary" behaviour when
  its edition came from a bare year. Would very likely turn Gate S green. Forbidden tonight
  because it is a fix invented after seeing the gate fail; legitimate the moment it is
  pre-registered.
- **Phase 5b, the variance battery.** 3 runs of one config to measure the noise band directly.
  Budget allowed it, the clock did not. **Every live number in this brief is a single sample
  against a ±3-on-17 noise band (F63); the 13-vs-14 model gap is inside the noise and means
  nothing.** This is the cheapest unspent measurement in the project and everything downstream
  is weaker without it.
- **Holdout-2.** One look remains, deliberately unspent.

---

## 7. Candidate next moves, ranked by value per dollar

Offered as input to a planner, not as a decision:

1. **Shelf v2 (b) alone** — offline only, no model calls, hours not dollars. Resolves a STOP
   that is currently blocking a change already shown to help.
2. **The reading gap: 5/17 on the number against 13–14/17 on the page.** Largest open defect in
   the system and the one a professor will ask about. Not a retrieval problem — it is table
   reading and multi-year arithmetic. Needs a diagnosis pass over the 12 transcripts that found
   the page and missed the figure before any fix is designed.
3. **The unopened-citation STOP** — Opus 7, Sonnet 1. The guard catches it after the fact; the
   question is whether CLAUDE.md can prevent it. Cheap to test, and it is the single condition
   standing between the current result and a PASS.
4. **Phase 5b variance** — ~$12 and one night's clock. Until it runs, no single-battery
   comparison in this project is defensible.
5. **Holdout-2 confirmation** — only worth its one remaining look once 1–4 have settled and
   there is a configuration worth confirming.

The honest summary for a planner: **the night made the tool fast, made two broken instruments
honest, and produced the project's best live citation numbers — while both of the gates that
mattered read STOP, one on a defect the system has (unopened citations) and one on a change
that made things worse (shelf v2). Nothing was tuned to pass. The biggest remaining problem is
not finding pages; it is reading them.**
