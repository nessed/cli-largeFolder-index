# Handoff — forensics, the absence dispute, dense captions, and one live re-battery, 2026-09-15 (pm)

Four questions, in order. Counts only; no paths, no titles, nothing from the answer key.

---

## 1. Is absence solved, disputed, or broken?

**Solved.** Both numbers that disputed it were broken instruments, and they were broken in two
different ways.

| | number | status |
|---|---|---|
| live battery, v1 scorer | **1 / 15** | SUPERSEDED-BY-SCORER-REPAIR — published, not deleted |
| live battery, v2 scorer | **11 / 15** (2/3 frozen) | gate PASS |
| chain ROUTE, frozen three | 1 / 3 | superseded as a statement about ROUTE |
| ROUTE, repaired, frozen three | **3 / 3** | |
| ROUTE, document-level absence | **11 / 11** | re-derives the published figure |
| ROUTE, identifier-level absence | **4 / 4** | re-derives the published figure |

**I believe the 11 of 15, and the reason is a single statistic that does not depend on the
repair being reasonable:** `figures_asserted3` is **zero on all fifteen sessions**. Not one
absence answer contains a number the session had not been shown in its own tool output. No
absence session invented anything. The v1 rule demanded "declined **and** asserted no figures",
and an honest answer that says *we hold these editions, not the one you asked for* and then
lists them was scored as asserting fabricated quantities. It was penalising accurate quotation.

The router was a separate and simpler fault. This corpus has **two kinds of absence** — a
missing edition (the question names a fiscal year, answered by `have`) and a missing identifier
(a literal code, no year, answered by `exact`) — and the overnight chain implemented only the
first, returning "present" for the second without looking. The three frozen absence questions
are **one of the first kind and two of the second**, so the chain could score at most 1 and
scored exactly 1; re-running the old logic reproduces that 1 exactly. With the `exact` path
added it is 3 of 3, and across the whole key 11/11 and 4/4 — **re-derived by a second
implementation, not by the control that produced them originally**.

The repair was specified and committed **before any transcript was read** (`d093729`), and the
spec's own STOP condition was checked rather than assumed: **0 answers are credited without a
verdict string or a decline statement**.

One residue, recorded and not acted on: the shelf verdict reached a tool result on **15 of 15**
sessions and the final answer on **5**; four sessions received it and did not relay it. The
pre-registered trigger for treating that as a behaviour loss required `absence_ok3` ≤ 7/15, and
it is 11, so no instruction change was claimed on it.

## 2. Where did the agent go when the right file was on screen?

| class | count | one sentence |
|---|---|---|
| **L0** the right publication never appeared | **9 / 17** | The session never had the chance to choose it. |
| **L1** it appeared, session opened another publication | 4 | It went to a different publication — though 2 of the 4 opened nothing at all, so only 2 actively chose elsewhere. |
| **L2** right publication, wrong edition | 2 | It reached the right publication and opened the wrong year's volume. |
| **L3** right file, wrong page | 1 | It opened the correct document and never reached the cited page. |
| **L4** right page open, not cited | 1 | It had the page open and its answer did not cite it. |
| **L5** cited the right page | 0 | — |

**The loss is top-heavy: more than half of it happens before the agent makes a choice at all,
and everything downstream of choosing the publication is four questions in total.**

**Yes, it rewrote the subject in its own words — on 8 of 17 questions.** And the tooling was
used as instructed: all **26** `find` calls carried `--q` rewrites, `have` on 14 of 17,
`tables` on 10 of 17. Neither tool use nor paraphrasing is the loss.

The two L2 sessions are the only direct evidence of how edition choice fails: in one the right
edition was listed **first** of 15 and the session opened the **third**; in the other it was
**third** of 15 and the session opened the **fifteenth** — consistent with the offline finding
that the agent matches the printed year to the asked year while the row it wants is in a later
volume.

*One classifier defect caught before the counts were read: shelf paths preserve their case and
the scorer's normaliser lowercases, so every family lookup silently missed and the first run
reported L1 = 6, L2 = 0. Zero of 14 opens resolved to any family — the signature of a blind
classifier. Fixed, with a permanent guard that is now 0.*

## 3. Do dense captions bridge the vocabulary gap?

**Yes, decisively, and it is the first pre-registered gate this project has passed.**

| right page in the top 5, given the right document | B1 | B2 | **B2c** |
|---|---|---|---|
| dev addresses | 24/57 | 42/57 | **52/57 (91.2%)** |
| dev macro | 27.9% | 39.7% | **82.1%** |
| **holdout** addresses | 23/81 | 35/81 | **67/81 (82.7%)** |
| **holdout** macro | 27.0% | 40.0% | **77.7%** |

**Of the six year-asking questions that had no lexical caption match at all — the group whose
existence proved the failure was vocabulary and not matching — five now have a gold page in the
top five.** The gain is also the first that is not trajectory-only: point_lookup 0/3 → 3/3,
multi_branch 1/9 → 5/9.

Yesterday's conclusion that this "cannot be fixed by another matching rule" was right about
matching rules and wrong about the remedy: the fix was to stop matching words and start
measuring similarity. And it does not contradict the morning's finding that dense captions
*hurt* at corpus scale — across 89,380 captions an embedding dilutes a precise hit with
plausible neighbours; across one document's few dozen there is nothing to confuse it with.

**The frozen production page method was deliberately not changed on this result.**

## 4. Did the re-battery run, what changed, and what moved?

It ran: 23 of 23 permitted sessions, `claude-sonnet-5`, **one sentence** added to section 1 of
`CLAUDE.md` from the decision table written before the counts existed — *prefer families with
several dated editions over single files, notes or spreadsheets when the question asks for an
official published figure*. Committed before any session started. Nothing else changed.

| | overnight | re-battery |
|---|---|---|
| L1, the targeted class | 4 | **2** |
| L3 | 1 | **0** |
| **L5 cited the right page** | **0** | **2** |
| opened the right page | 1 | **3** |
| `series` on trajectory | 2/4 | **4/4** |
| **cited a file never opened** | **5** | **8** |
| ungrounded figures | 1 | 2 |
| surfaced | 8 | 7 |
| timeouts | 0 | 2 |

**Gate LIVE-2: STOP.** PASS needed the dominant class to fall by ≥3 and correct citations to
rise by ≥3; WEAK needed a fall of ≥2 **and nothing else to worsen**. The fall was 2, the rise
was 2, and citations to unopened files rose by 3. The WEAK band was not claimed on the strength
of its first half.

The change is kept on the branch **measured-and-not-adopted**; no second wording was tried.

**What moved is nevertheless the project's first correctly cited pages in a live session** —
`cited_right_page` had been 0 in every battery across four nights. **And the caveat is as
important as the result:** retrieval did not change at all, yet `surfaced` still moved by one
and two sessions timed out where none had before. A ±2 movement on a base of 17 is inside this
battery's own run-to-run variation. The gains are consistent with the instruction working and
equally consistent with noise, and one battery cannot separate them. Re-running the same
wording to see whether the number firms up would be the same error as trying a second wording.

## 5. The single biggest bottleneck

**Retrieval — specifically finding the right document, and nothing else is close.** On 9 of 17
questions overnight and 10 of 17 in the re-battery, the right publication never appeared on the
agent's screen. Page choice, given the right document, is now largely solved (82.7% on the
holdout). Vocabulary is solved inside a document. Edition choice is a real but small term at 2
questions. Behaviour is a small term at 2. The document box is the whole game.

## 6. The one next experiment

**Experiment G — carry B2c's mechanism up to the document channel, as a reranker over the pool
that already exists rather than as a new retrieval channel.**

The three facts it stands on are each already measured: the right document is in the top-100
pool on 16 of 17 and 28 of 30 (F41); a cross-encoder over *catalog cards* cannot reorder that
pool (F44); and embedding a document's *captions* cleanly separates the right table from its
neighbours (F55). G scores each of the top-100 candidates by the **maximum cosine between the
query's label words and any caption in that document**, and fuses that with the existing rank.

**Pre-registered gate**, against the frozen configuration's 10/17 and 14/30:
- **PASS** — ≥13/17 **and** holdout ≥17/30
- **WEAK** — 11–12/17 **and** holdout ≥16/30
- **STOP** — ≤10/17, or the holdout does not improve by at least 2

This spends the **fifth and last** holdout look. Do not, to get past it: tune the fusion weight,
change the pool depth, lower the caption cut, or add a seventh rewrite.

## 7. Run record

Branch `phase4-forensics-live` off `d9e186f`, one commit per phase plus the pre-registration
commit, **nothing pushed**.

**Sessions: 23 of 23 permitted** — 1 auth probe, 2 isolation probes, 20 questions. **$7.58**,
cost recorded for 18 of 20 (the two timeouts report none). Model `claude-sonnet-5`, matching
overnight. **Holdout looks: 4 of 5** — the B2c page look was the only one spent today, earned
by B2c clearing its gate; Phase 1 and Phase 2 read no holdout at all.

**Isolation probes: both PASS** with a freshly generated token. **Checksums: 18 files, 0
changed, 0 missing.** **Memory files: 0 before, 0 after.** **Transcript quarantine: 0 new
canary-bearing transcripts** (531 scanned). **Rung root: clean**, teardown ran and `status`
confirms both files absent. **Contamination events: 0.**

**Four deviations, recorded rather than silently resolved.**

1. **A classifier defect that would have pointed the phase at the wrong repair.** The first
   forensics run reported L1 = 6 and L2 = 0 because shelf paths keep their case and the
   scorer's normaliser lowercases, so every family lookup missed. It was caught by checking
   whether the opens resolved at all — 0 of 14 did — and fixed before the counts were read. A
   permanent guard now reports 0.
2. **The re-battery overwrote the overnight aggregate.** `c_score_live.py` writes to a fixed
   path, so scoring the new battery destroyed the numbers it was to be compared against.
   Recovered from commit `538d7eb`; the two batteries now live in separate, labelled files.
3. **The battery needed a new phase tag.** `ask.py` correctly refuses to overwrite an existing
   result, which the re-battery would have required. Rather than force it, the driver gained a
   `--phase-tag` so the overnight results are preserved intact and the stale-result guard is
   respected instead of bypassed.
4. **Two sessions timed out** at the 300 s limit where none did overnight, with no configuration
   change. They are counted in the denominator of 17 as fixed, not excluded.

**One thing to carry forward about method, not results.** Two of this project's headline numbers
turned out to be broken instruments within eighteen hours of being published, and both were
caught only because they were written down precisely enough to be attacked, and because the
repair was specified before the data was re-read. Neither the 1/15 nor the 1/3 was deleted.
