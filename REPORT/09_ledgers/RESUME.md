# START HERE

A fresh session can continue from this file alone.

```
cd C:\Users\Ali\Desktop\retrieval-lab\corpus-lab
```

## Night 4 (evidence_v1), 2026-09-13 — read this first

A full build of BUILD_PROMPT.md's evidence engine ran unattended overnight. It got
further than any prior night: Stages 1-4 genuinely passed (corpus integrity,
scorer/oracle audit on the 20 frozen dev questions, the full runtime
store/inventory/extract/catalogue/retrieve/verify/compile/hooks/install stack built
and unit-tested, a cold catalogue build on corpus_15000 -- 15010/15010 files,
1109s/1800s). It stopped honestly at **Stage 5, RETRIEVAL_GATE_FAILED**: 3/17 of the
positive frozen questions found a correct address in the top 24 leads, far under
both the strict gate (15/17) and Ali's authorized 10/17 amendment. $0 spent, 0/175
sessions used, 0 corpus changes (independently re-hashed and confirmed
byte-identical to the Stage 1 baseline). Nothing is running; no stack is installed
in any corpus.

**Read `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/STOP_REASON.md`
first.** It has the full diagnosis, including the concrete root cause found right
after the stop: 92.5% of the 1.2M-card catalogue came from BUILD_PROMPT.md's own
captionless-table heuristic misfiring on ordinary prose sentences (two years, two
numbers, one sentence -- no table), so the catalogue never got meaningfully smaller
than the old full-page index the whole design was meant to beat. A real alias bug
was also found and fixed along the way (moved hit-rate 0/17 -> 3/17); an AND-first
query strategy was tried and measured WORSE, then reverted. All of `corpus-lab/
evidence_v1/` (the runtime) and its test suites in `corpus-lab/tests/evidence_v1/`
are real, working code, independent of whether the retrieval gate ever passes.

**Night 2 complete, 2026-09-12.** Nothing is running. No stack is installed in any
corpus. All 31 planted files verified unchanged. **The deliverable is
`05_findings/GRID.md`.**

> **SUPERSEDED 2026-09-12 (P9).** The recall numbers below are superseded by the
> re-score from tool results — see `state/rescore_from_results.json`.

---

## 0. STATE AS OF 2026-09-13 — read this before §1

Night 3 was **offline only. No sessions run, nothing spent.** Four new findings, F20–F24 in
`05_findings/FINDINGS_LIVE.md`, and two new entries in `state/progress.jsonl` (P9, P10).

**What changed on disk**

| | |
|---|---|
| `bin/corpus_search.py` | **now takes a sentence.** It used to AND every token, so a nine-word question matched nothing. Tries the conjunction first, falls back to any-word ranked by bm25, labels the loose tier. `--legacy-and` reproduces the old behaviour exactly. |
| `bin/stack.py` | `CLAUDE_MD` gained a **quote-before-cite** rule: open the page, quote the line verbatim, cite path + page_index; if you did not open it you may not cite it. `s0_baseline` still installs no `CLAUDE.md`. |
| new instruments | `rescore_from_results.py`, `probe_score_floor.py`, `rank_experiments.py`, `verify_search_fix.py` — all offline, all free to re-run |

**What was learned**

1. The scorer was blind to files the agent learned about from tool *results*, which
   undercounted the index stacks by construction. Re-scored: S1 0.176 → 0.235, S2 0.118 →
   0.176, S0 unchanged. Still inside noise. (F20)
2. **The search handed S1 a correct document on 5 of 17 questions and it opened 0 of them**
   — three were cited without ever being opened. A second failure, downstream of retrieval,
   that no retrieval change fixes. (F21)
3. **A score floor cannot power abstention.** Absence questions score inside the answerable
   range. (F22)
4. **Fixing the sentence bug removed every empty result and improved finding by nothing:**
   top-15 hit rate 0/17 → 0/17 across eight query strategies. The correct page sits at rank
   ~500–3,000 of 1.2M. Lexical retrieval is finished here; what is untested is matching on
   meaning. (F23)

**What is built but unproven:** the search fix and the quote-before-cite rule. Neither has
ever been run in a session. The paid battery was **held deliberately** at the F23 gate,
because it would test the quote rule against a search that cannot put the right page in the
agent's window on 17 of 17 questions. (F24)

**Open, free, and worth doing first:** pull every absence-type question out of the
135-question key — the abstention result currently rests on three. And count image-only
PDFs in sir's real folder; 8% of the harness is unreachable without OCR and nobody has
checked the target.

**A brief for an outside model** to design the solution from scratch, pointed at all the
evidence and deliberately not at anyone's suggestions, is at `00_brief/SOLVE_BRIEF.md`.

**Uncommitted:** night 3's changes are on disk but not committed. `git status` in
`corpus-lab/` shows them.

---

## 1. The answer, in four lines

1. **Stock search is fine on a plain folder.** S0 found 15/17 planted strings on the
   harness (no git) versus 4/12 on ra-ship (documents gitignored). Night 1 read that
   ra-ship gap as proof an index was needed; it is mostly a fixture artifact.
2. **Telling is enough; forcing adds nothing.** A line in `CLAUDE.md` moved index
   adoption from 0 of 38 sessions to 38 of 38. The S2 hook enforced what S1 had
   already achieved.
3. **None of it moved question recall** — 0.167 / 0.176 / 0.118, all inside noise.
4. **Because the failure is lexical ranking, not tooling.** The evidence is indexed
   (64/64) and contains the question's words (mean 38.9%), yet BM25 on the question's
   own words returns it in the top 50 **zero times out of 17**.

## 2. Where everything lives

```
C:\Users\Ali\Desktop\retrieval-lab\
  corpus-lab\      scripts, findings, state   <- git repo, cd here
  harness\         corpus_{500,2000,5000,15000}, generator
  _private\        NEVER reachable from a test session
    harness_keys\    answer_key.json, canary_slots.json
    canaries\        pass-1 and pass-2 manifests, companions, backups
    results\         03_runs\, 04_scores\, quarantined transcripts + memory
  .venv\           pip lives here only, never system python
```

`Desktop\_unrelated\agent-harness\` is quarantined — never run it near a corpus.
Every path derives from `bin/labpaths.py`. No script hardcodes a location.

## 3. Read these

| file | what it gives you |
|---|---|
| `05_findings/GRID.md` | **the deliverable.** Table + per-stack prose + diagnosis. |
| `state/progress.jsonl` | the full run record, one JSON line per step |
| `05_findings/FINDINGS_LIVE.md` | findings as they landed, each with its condition |
| `state/diagnose_recall.json` | the ranking diagnosis, raw |

## 4. What ran, what didn't

| stack | harness canary | harness questions | status |
|---|---|---|---|
| s0_baseline | 15/17 | 0.167 | complete (+ ra-ship 4/12) |
| s1_policy | 17/17 | 0.176 | complete on harness |
| s2_hook | 17/17 | 0.118 | complete on harness |
| s3_hybrid | — | — | not built: 8.2 pages/s, 20.8 h, no GPU |
| s4_pdfmcp | — | — | install gate failed: no dir/glob input; 415 s for 5 PDFs |
| s5_recoll | — | — | no headless installer exists |

**Not done, if anyone wants to continue:** S1 and S2 on ra-ship (2 cells, ~$4). Low
value — ra-ship is a fixture whose defining property does not exist on the target.

**Held, not skipped (2026-09-13):** the 20 questions on s1_policy and s2_hook with the
search fix and quote-before-cite installed, ~$6–12. Held at the F23 gate. Expect it to
measure honesty (does it refuse on the absence questions) rather than finding, since the
right page is still not in the agent's window.

## 5. How to run a cell

```bash
set CANARY_MANIFEST_PASS1=C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass1.csv
set CANARY_MANIFEST_PASS2=C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass2.csv
python -u bin/run_grid.py --stack s1_policy --tree raship      # all 11 steps of spec 7.2
python -u bin/run_harness.py --phase P --stack S --rung 15000 --only q1,q2   # fill gaps
python bin/build_grid.py                                        # rebuild the table
python bin/diagnose_recall.py                                   # re-run the diagnosis
```

## 6. Bugs found on night 2 that invalidated earlier work

1. **`claude.cmd` truncates multi-line prompts.** cmd.exe's `%*` stops at the first
   newline, so any prompt containing `\n` silently lost `--output-format stream-json`
   and the session returned prose, rc 0, empty stderr. That was night 1's undiagnosed
   break — never the corpus root. **Fix: invoke `claude.exe` directly**
   (`labpaths.CLAUDE`).
2. **`Read(**/_private/**)` does nothing.** Under `bypassPermissions` a `Read()` deny
   binds **only** with an absolute path prefix; relative globs fail open silently.
   `Bash()` patterns match the command string, so relative forms do bind there.
3. **Sessions write `memory/` despite `--disallowedTools Write`.** One battery could
   hand notes to the next. `run_grid.py` quarantines memory files either side of a cell.
4. **The qid derivation lost results.** Ids were built from the phrase, and pass-2's
   deliberately mixed phrase shapes produced ids containing `/`, so four results were
   never written and the battery reported 12/14 with a silently shrunk denominator.
   Fixed and made injective; pass-1 ids unchanged.
5. **The question scorer crashed on a battery with missing results**, and would have
   averaged a missing session in as 0 s. Now excluded explicitly.

## 7. Traps — do not rediscover these

- A deny list installed in a corpus applies to **every** Claude Code process whose cwd
  is that root, including the orchestrator and any subagent it spawns. That is why the
  first planting attempt failed. **Do not install a stack in ra-ship while a subagent
  needs to work.**
- `plog.py` accepts `@file` for the note, so a progress line mentioning a denied word
  is not refused while a stack is installed.
- **Run long jobs with `python -u`.** Buffered stdout meant an 18-minute battery left
  no trace in its log when the process was killed.
- Background jobs launched with `nohup ... &` have twice been reaped mid-run. For
  anything that must finish, run it in the foreground or re-check it afterwards.
- `subprocess.run(timeout=)` does not kill node grandchildren; `ask.py` uses `Popen` +
  `taskkill /T /F` with stderr to a file, never a pipe.
- Don't put Windows paths in bash heredocs feeding `python -c` — use the Write tool.
- Index DBs are gitignored. `git add -A` with a 7 GB db will hang the commit.

## 8. Safety rules

- ra-ship and the rungs are **read-only sources**. The only writes are `CLAUDE.md` and
  `.claude/settings.json` via `bin/stack.py`. Never commit ra-ship.
- **Always** `stack.py teardown` before finishing; verify with `stack.py status`.
- Canary phrases must never enter the orchestrator's context — verify manifests with
  the scripts, which print counts only.
- `checksums.py verify` before and after every battery. **Verify, never restore.**

## 9. Cost

**~$31 total on disk**, ~$28 of it night 2, across 189 measurement sessions. Canary
batteries run $1–2 each; question batteries $2.70–$12.54, the outlier being S0, which
spawned subagents instead of reading documents.
