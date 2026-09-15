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

<!-- PHASE5_BOXES -->

### Failed or not attempted tonight

<!-- PHASE67_BOXES -->

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

<!-- PHASE5_TABLE -->

---

## Run record

<!-- RUN_RECORD -->

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
