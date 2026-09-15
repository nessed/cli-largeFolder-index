# Handoff — production hardening night, 2026-09-15 → 09-16

One agent, one night, running `plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md`
top to bottom. Branch `phase9-production-hardening`, off `master` at `12de91b`. Nothing pushed.

Plain English first, numbers after. Everything here is measured; where something was not
measured it says so.

---

## What actually changed tonight

**The tool got fast.** Opening a page took three seconds and now takes two tenths of one.
Every command the model runs is a fresh process, and two of them were scanning all 1.2 million
pages on every single call — `open`, because the file column has no index, and `coverage`,
which counts them. A trajectory question used to spend about 52 seconds of its life waiting for
tools on a warm machine, and over two minutes on a cold one. It now spends about 18.

**Not one rank moved, and that is proved rather than claimed.** 300 sampled pages come back
byte-identical through the old and new code paths. The stored caption vectors match freshly
computed ones on 200 of 200 at cosine 1.0. `inside` returns the identical top-5 page set *and
order* on all 57 dev addresses. All three offline baselines and all four self-tests reproduce
exactly.

**The model now sees forty candidate publications instead of twelve.** Offline, the right
publication is in the top 12 on 11 of 17 questions but in the top 40 on 14 of 17 — so the old
display was capping everything downstream at 11 before the model read a word. This is
Experiment H's mechanism (F60, F63), which measured better than any statistical reranker tried
here, finally shipped where it costs nothing: inside the session that is already running.

**Two measurement instruments were wrong, both in the direction of flattering nobody.** The
harness was killing 1 to 5 sessions per battery before they produced any answer, and scoring
each as a miss. And the scorer was stricter than its own answer key — which carries acceptable
alternates on 45 of 135 questions — so an answer that found the right figure in a different
official publication scored zero. Fixing the scorer moves the recorded history from 0–2 of 17
to 4–9 of 17 on transcripts nobody re-ran.

**One planned change was rejected by its own gate.** See F66 and the STOP box below.

---

## The boxes

### Keep (measured, shipped, in production)

- `open` 2.95 s → **0.18 s**, `coverage` 2.89 s → **0.17 s**, `find` 4.14 → **1.15 s**,
  `series` 4.52 → **1.22 s**, `inside` 1.69 → **1.14 s**. Warm-vs-warm, old code restored from
  git for the baseline. Gate 1 PASS every row. (F64)
- `find --compact N` / `--show i,j,k`, and CLAUDE.md v2 built on them. (F67)
- Citation guard v2: prose page numbers, `Sources` lines, and answers that state figures and
  cite nothing. Behind `--v2`, which the installer passes. (F67)
- Scorer v2: equivalence, value-vs-alternates, no-answer cause, `cited_no_path`. The frozen
  strict scorer is untouched and still reported. (F68)
- `c_live_battery.py --max-turns/--timeout`, defaults unchanged. (F65)
- `setup_folder.py`: doctor / install / status / ask / uninstall for any folder.

### Adopted, then blocked by its own pre-registered gate

- **Shelf v2. Gate S reads STOP.** Five recall rows held exactly; the fragment-family merge
  took duplicate slots in the top 40 from 35 to 0 across 17 lists; and one structural row
  failed — gold evidence files hidden as non-primary rose 20 → 31, because the bare-year change
  gave an edition to 4,333 documents that had none, flipping their clusters from "show every
  copy" to "one primary, hide the rest". **Production stays on v1.** Not tuned. The v2 shelf is
  kept on disk so the next session can pre-register **(b) alone**. (F66)

### Weak / unresolved

- **LIVE-5 reads STOP on both models**, each on one condition: a citation of a file the session
  never opened (Sonnet 1, Opus 7). Everything else on the gate passed, and the citation column
  itself came in at 13 and 14 of 17 against a bar of 5. (F69)
- **Finding the page is not reading it.** Both models: 13–14 of 17 on citation, **5 of 17 on the
  number**. On decade-long trajectory questions Sonnet opened the right page 4 times of 4 and got
  the figure wrong 4 times of 4. Largest open gap in the system, and not a retrieval problem.
- **Opus cites carelessly.** 7 unopened citations to Sonnet's 1, 4 decoy citations to Sonnet's 1,
  and the only ungrounded figure in either battery. It writes the better answer and is the looser
  about provenance.
- **No variance measurement.** Phase 5b was skipped on the clock, so every live number here is a
  single sample and the project's own ±3 on 17 questions (F63) applies to all of it.

### Failed or not attempted tonight

- **Shelf v2 rejected by Gate S** (above, F66). Built, measured, not shipped, not tuned.
- **Phase 5b, the variance battery: skipped.** Budget allowed it — cumulative live spend was
  $37.83 against a $40 threshold — the clock did not, and the plan ranks it first to sacrifice.
  It remains the cheapest unspent measurement in the project.
- **Holdout-2: untouched.** One look remains.

### Untested

- Everything in this handoff is measured on **one synthetic corpus**. The figures in it were
  generated, not published.
- The dev set is 17 questions and carries **±3 noise** (F63). Any single-battery difference
  smaller than that is not a result.
- Nothing here has been confirmed on holdout-2. **Holdout looks spent tonight: zero.**

---

## The numbers

### Offline, before and after (all on the v1 production shelf)

| measure | before tonight | after tonight |
|---|---|---|
| document top-10, dev | 10 / 17 | 10 / 17 |
| document pool@100, dev | 16 / 17 | 16 / 17 |
| B2c page retrieval, dev | 52 / 57 | 52 / 57 |
| ROUTE absence | 11/11, 4/4 | 11/11, 4/4 |
| gold publication within what the model is shown | 11 / 17 (top 12) | **14 / 17 (top 40)** |
| self-tests | 22, 10, 9, 16 | **25, 10, 24, 18** |

Retrieval did not move tonight, and was not expected to. What moved is latency, what the model
is shown, what the guard catches, and what the scorer can see.

### Live

Both batteries: the frozen 20, v1 shelf, CLAUDE.md v2, guard v2, `--max-turns 60 --timeout 900`,
`--parallel 2`. Both models resolved to the exact id requested; all six probes passed.

| | claude-sonnet-5 | claude-opus-5 | gate |
|---|---|---|---|
| cited_right_page_equiv | **13 / 17** | **14 / 17** | PASS ≥ 5 |
| cited_right_page_strict | 1 / 17 | 3 / 17 | project record was 2/17 |
| value_correct | 5 / 17 | 5 / 17 | reported |
| value_wrong_confident | 0 | 0 | reported |
| absence, frozen 3 | 3 / 3 | 2 / 3 | needs ≥ 2 |
| sessions lost to caps | 0 | 0 | needs ≤ 1 |
| **cited_unopened_total** | **1** | **7** | **needs 0 — the STOP** |
| median / p90 wall | 99 s / 311 s | 118 s / 308 s | |
| cost | $11.01 | $23.35 | caps $20 / $80 |

**Verdict: STOP on both**, each on one unopened citation. 13–14 of 17 is nonetheless the best live
citation reading the project has taken; the previous best was 9/17, itself a re-score of old
transcripts performed tonight.

Three changes could each explain it and this battery cannot separate them: the harness stopped
killing sessions, the scorer stopped being stricter than its key, and the model started seeing 40
candidates instead of 12. Two of those are measurement repairs, so part of the gain is removal of
error rather than new capability.

**The harness fix paid on the first run:** 6 of 20 Sonnet sessions and 5 of 20 Opus sessions ran
past 25 turns or 300 seconds. All 11 produced full cited answers; all 11 would have been killed
and scored as misses under the old limits.

### Rehearsal, the professor's way (5c)

Three questions, plain `claude.exe -p` from inside the rung, Opus, no harness, no caps:

| question | wall | page citations | Sources block |
|---|---|---|---|
| wheat in Punjab 2015-16 (honest negative) | 181 s | 4 | yes |
| tax-to-GDP over a decade (comparability) | 234 s | 9 | yes |
| federal development spending 2019-20 (reconciliation) | 235 s | 10 | yes |

Read by hand against the opened pages, no key involved: Q1 correctly refuses the Punjab
breakdown, offers the national figure, catches two publications disagreeing (23.63 vs 23.29) and
confirms the revised value is stable across three editions. Q2 states plainly that **no page in
the folder prints a tax-to-GDP ratio**, that the division is its own work, and flags a
Survey-vs-working-CSV conflict worth a quarter of a point. Q3 separates two different tables from
two vintages of one table and quotes the reclassification note that explains the gap.

Files: `corpus-lab/99_scratch/asks/professor_rehearsal/`.

---

## Run record

- **Sessions:** 46 live. 40 battery (20 Sonnet + 20 Opus), 6 probes, plus 3 rehearsal and 2
  portable cold-test sessions run outside the battery driver. Against a budget of 95.
- **Reported cost:** $11.01 Sonnet battery (cap $20), $23.35 Opus battery (cap $80), $37.83
  cumulative including probes. Rule-12 projection at 11 Opus sessions read $24.24 — CONTINUE.
- **Holdout looks spent: 0.** Nothing ran with `--holdout`, `--holdout2` or `c_page_holdout.py`.
- **Contamination events: 0.** Both isolation probes passed for both models with a freshly minted
  16-hex token; neither model revealed the decoy or the private tree.
- **Checksums:** `s7_phase9_pre` and `s7_phase9_live_pre`, 18 files each. Verified after the
  batteries: **18 unchanged, 0 changed, 0 missing.**
- **Transcripts:** 9 canary-bearing transcripts quarantined, 0 left in place.
- **Memory files under the corpus project key: 0**, before and after.
- **Rungs:** `corpus_15000` and `corpus_500` both clean at the start and at the end — neither
  `CLAUDE.md` nor `.claude` present.
- **Timeouts: 0. Suspended sessions: 0. Results discarded: 0.**
- **Branch:** `phase9-production-hardening`, from `12de91b`. Nothing pushed.

---

## Deviations from the plan, recorded rather than resolved

1. **The guard v2 switch is an argument, not an environment prefix.** The plan specified
   `STOP_GUARD_V2=1` set in the hook command. A hook command runs under whichever shell the host
   picks, and `set VAR=1 &&` means different things to cmd.exe and to bash, so that prefix could
   have switched the guard off silently and left a passing self-test. It is `--v2` instead; the
   env var still works, and both forms are tested.

2. **Gate S's "gold families that are fragments" counter reads 0 on v1**, so it could not show
   the defect it was written for. It is reported as it stands (0 → 0) and a second counter was
   added alongside it — fragment slots inside the top 40 of a dev `find`, 35 → 0 — which measures
   the harm section 1.3 actually described. The added counter is **recorded, not gated**; it had
   no influence on the STOP.

3. **The first two `after_phase1` benchmarks were contaminated** — one by a cold disk cache on
   the baseline side, one by the Phase 2 embedding job holding the CPU — and both overstated the
   speedup. Both are kept in `c_shelf_bench.json` under their own labels rather than deleted, and
   the reported figures come from a third run with the pre-Phase-1 code restored from git so both
   sides share a cache state.

4. **`n_primary_changed` (306) counts more than the plan's estimate of 150–170** because it
   counts every cluster where the v1 and v2 sort keys disagree, including marker-penalty moves,
   rather than only clusters where the sibling count differs. The definition is stated with the
   number.

5. **A `git add -A` briefly tracked 12,809 fixture paths** (`cards_ids.jsonl` for the v2 shelf);
   the ignore rule named `s7_shelf` but not `s7_shelf_v2`. Untracked in the following commit and
   the rule extended to `s7_shelf_v2/` and `portable/`.

---

## What I wanted to change and did not

Per the plan's standing rule, these are written down instead of acted on:

- **The bare-year fallback in shelf v2 (change a).** The obvious repair is to keep a cluster's
  "every survivor is primary" behaviour when its edition came from a bare year rather than a
  fiscal year. That would very likely turn Gate S green. It is a change made *after seeing the
  gate fail*, which is exactly what the rule forbids, so it is an experiment for the next
  session to pre-register — not a fix for tonight.
- **The `inside` 2.5 s bar.** On a cold cache `inside` misses it. The floor is a fresh Python
  process plus the model load, and the only way under it is a resident process, which is a
  different architecture, not a tuning change.
