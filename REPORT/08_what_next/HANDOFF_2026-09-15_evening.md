# Handoff — Experiment G, B2c adopted, tool-enforced provenance, chain v2, third live battery, 2026-09-15 evening

Counts only; no paths, no titles, nothing from the answer key.

---

## 1. Did Experiment G move document retrieval, and was it adopted?

**No, and no.**

| depth | frozen configuration | G1 | G2 |
|---|---|---|---|
| **top 10** | **10 / 17** | **9** | **9** |
| top 20 | 12 | 13 | 13 |
| top 100 | 16 | 16 | 16 |

**Gate: PASS ≥13/17, WEAK 11–12, STOP ≤10. It is 9. STOP. The frozen configuration stands
unchanged.**

**The holdout was not consulted.** The gate's stop condition is "≤10/17 *or* holdout <16/30", so
the development number alone decides. Spending the branch's last holdout-1 look to confirm a
configuration four questions below the pass bar would tell us nothing — the same call made for
Experiment C overnight. **Holdout-1 retires with its final look unused; holdout-2 stands at 0 of
its 2 looks.**

G2 is not a separate result: 14 of the 17 questions are table-like by the existing generic
signals, so it reproduces G1 exactly. The hypothesis that the harm concentrates on non-table
questions and could be switched off by question type is **not supported** — the harm is spread
across the questions the signal was meant to help. Per question, G improves **4** and worsens
**11**.

This is the fourth result with one shape: **captions discriminate within a document and dilute
across the corpus.** Inside a document the competitors are a few dozen tables of the same
publication; across 1,618 families every dated series holds some caption plausibly about any
fiscal subject, and a maximum over a family's captions is the statistic most exposed to that.

**ED3**, same phase: **3 of 10**, mean set size 2.0 — *identical* to ED2, despite page retrieval
improving from 42 to 52 of 57 addresses. That is only consistent with B2c finding the right kind
of page in the wrong edition, which is F51's offset result for the third time. **The architecture
boxes were not redrawn**, because the condition needed both G and ED3 and both failed.

## 2. The chain, before and after

- **Before (B2 pages):** 8 of 17 reach the right publication → 4 reach a right page → **3 verify**; absence 1/3.
- **After (B2c pages, identifier-level routing):** 8 → **5** → **3**; absence **3/3**.

Neither pre-registered reading fires (address hits reached 5, not ≥6; verified hits lag address
hits by 2, not ≥3). The number worth carrying: **a page fix worth +10 of 57 addresses in
isolation is worth +1 of 17 questions in the chain** — the arithmetic of a pipeline whose loss is
upstream of the box that improved.

## 3. The live battery — the three metrics, separated because they test different changes

| | tests | pm | evening | prior |
|---|---|---|---|---|
| **L0** right publication never surfaced | document retrieval | 10 | **10** | flat, as expected — G was not adopted |
| **L2+L3** edition and page choice | B2c in production | 2 | **2** | flat |
| **cited a file never opened** | the `note` enforcement | 8 | **10** | **rose** |

Also: cited the right page 2 → 1, opened the right page 3 → 2, notes written 11 → 13, absence
(frozen 3, repaired scorer) **3/3 → 3/3**, timeouts 2 → **0**, $6.65, 20 of 20 completed.

**Gate LIVE-3: PASS needs cited_right_page ≥5/17, cited_unopened ≤3, absence ≥2/3. It is 1, 10
and 3/3. STOP.**

**The useful result is why the enforcement failed.** It works — it fired 4 times across 19 note
commands in 2 of 20 sessions and recorded nothing it shouldn't have. But **the gate guards the
note, and the answer does not pass through the note.** The model notes the pages it opened, then
names extra paths from a `find` listing in its answer, where no check exists. Two nights and two
mechanisms — an instruction, then a tool check — have now failed to move this number for the same
structural reason.

**What the professor would experience now versus last night:** almost exactly the same thing. He
would ask a question; on roughly ten questions in seventeen the publication he needs would never
appear in the shelf's output at all, and he would get an answer assembled from whatever did. On
the questions where it does appear, the system is meaningfully better at finding the right *page*
inside it than it was yesterday — but he would rarely get that far. The one thing he would
reliably get right is a refusal: when the folder genuinely does not hold something, it says so,
3 times in 3.

## 4. Each box

**Keep:** SHELF; VERIFY — 3 of 4 then 3 of 5 in the chain, still never the bottleneck; session
isolation; **ROUTE/absence, now with the identifier path — 3/3 in the chain and 3/3 live, twice.**
**Adopted this phase:** B2c as the production page method (F55, holdout-confirmed).
**Weak:** the trajectory walk; ROUTE's presence half at 8/11.
**Failed:** RETRIEVE DOCUMENT, now **five** ways; edition selection, now **three** ways (3/17,
3/10, 3/10); citation discipline, now **two** ways.
**Untested:** the EXTRACT router; the VERIFY → retry edge.

## 5. The single biggest bottleneck

**Finding the right document — and it is no longer one bottleneck among several, it is the
system.** Across three live batteries with three different configurations, the right publication
never reaches the agent's screen on **9, 10 and 10 of 17** questions. Every downstream class is
four to six questions and moves by one or two between runs that changed nothing relevant.

## 6. The next experiment

**None is justified on the retrieval side**, and that is a measured position rather than a pause.
Five mechanisms have been tried on the document box — more rewrites, a cross-encoder, per-query
selection, captions as a channel (lexical and dense), captions as a reranker. The best moves the
top ten from 9 to 10 of 17 and does not survive a holdout. The answer is in the top hundred on 16
of 17; nothing reorders it.

Two things should happen before a sixth mechanism, neither of them a retrieval idea:

1. **Establish the variance.** Every live conclusion here rests on single batteries whose ±1–2
   movements are indistinguishable from noise — this phase's included. Run one configuration
   three times and report the spread. 3 × 20 sessions, no new code. Until it exists, no live gate
   band is trustworthy.
2. **Question the intermediate objective.** "Gold family in the top 10" has been the target for
   five nights, and it is visibly decoupling: the frozen configuration scores 10/17 on it while
   the live agent surfaces 7/17 and cites 1. A target you can hit without the outcome moving is
   the wrong target.

**If a sixth mechanism is attempted anyway**, the evidence points the opposite way from everything
tried so far: stop reranking documents and **retrieve pages directly, letting the document
follow** — B2c works at page level and the 1.2M-page index already exists. Pre-registered gate,
fixed now: gold **page** in the top 20 across the whole corpus on **≥6/17** dev and **≥10/30** on
holdout-2. Below that, stop.

## 7. Run record

Branch `phase5-caption-document` off `d9e186f`'s successor `fab9494`, 7 commits including the two
pre-registration commits, **nothing pushed**.

**Sessions: 23 of 23 permitted** — 1 auth probe, 2 isolation probes, 20 questions. **$6.65**, cost
recorded for 20 of 20, 0 timeouts. Model `claude-sonnet-5`, confirmed from the probe's init event.

**Holdout looks: holdout-1 0 of its last 1 (retired unused); holdout-2 0 of 2.** Holdout-2 was
frozen this phase: 30 questions sampled with seed 20260915 from the 73 answerable questions in
neither the frozen 20 nor holdout-1 (73 eligible, exactly as expected), ids in `_private`, 30
Haiku rewrites into a gitignored cache, 0 failures. **Offline model calls: 30**, all of them that.

**Isolation probes: both PASS** with a fresh token. **Checksums: 18 files, 0 changed, 0 missing.**
**Memory: 0 before, 0 after.** **Transcript quarantine: 0 new canary-bearing transcripts** (584
scanned). **Rung root: clean**, teardown ran, status confirms. **Contamination events: 0.**

**Production changes shipped this phase**, both on gates already passed and both self-tested:
B2c as the `inside`/`series` CLI default (Python defaults left as `None` so every recorded number
still reproduces with explicit flags — B2 re-runs at 42/57 and 39.7% unchanged), and `note`
refusing a citation whose page was not opened. `c_provenance_selftest.py` 10/10; `c_selftest.py`
extended and passing.

**Three deviations, recorded rather than silently resolved.**

1. **The pm run's `CLAUDE.md` sentence was removed.** Its gate STOPped (F56), so it does not ship;
   it was inherited by branching from that head and had to be taken out deliberately. The
   installer's self-test assertions that referenced the old flag text were updated with it, and
   one of those assertions was initially written so loosely it would have matched
   `--caption-channel` on the `find` example; tightened before it could pass for the wrong reason.
2. **The battery needed a new phase tag again** (`P7`). `ask.py` refuses to overwrite an existing
   result, which is correct; the driver's `--phase-tag` preserves the earlier batteries intact
   rather than forcing past the guard.
3. **Scoring the new battery overwrites the shared aggregate file**, as it did in the pm run. The
   overnight file was restored from `HEAD` immediately and the new battery written to its own
   labelled file. The three batteries now live in `c_live_battery.json`, `_p6` and `_p7`, each
   carrying a `battery` field naming itself.

**One thing to carry forward.** This phase shipped two changes that passed their own gates and
neither moved the live system — B2c because the loss is upstream of the page, the note
enforcement because it guards a surface the failure does not cross. Both were worth doing and both
are worth knowing about; neither is progress on the one box that matters.
