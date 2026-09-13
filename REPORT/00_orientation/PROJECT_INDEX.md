# retrieval-lab — INDEX

## 0. THE GOAL — read this before any finding in here

> **Deliverable:** a way for sir to open Claude Code in his research folder, ask a vague
> question, and get an answer pulled from the right pages across several PDFs — using
> whatever tools/methods we discover here — **without him doing anything but asking.**
> Right now we can tell him which setups work, which don't, and that one is worth
> adopting today.
>
> **The failure:** he asks *"how does Pakistan's development spending trajectory look
> since 2015."* Claude opens twenty files, misses the Economic Survey table that actually
> answers it, and gives a confident answer built on the wrong sources. He can't tell it's
> wrong without checking himself — which is the work he was trying to avoid.
>
> **Success:** the same question returns the number, with the file and page it came from,
> pulled from four different years' surveys, in under a minute — and when the answer
> genuinely isn't in his folder, it **says so** instead of making one up.

Every result in this tree is scored against those two halves: **right page + citation**,
and **honest abstention**. Cheaper and fewer tool calls are not progress on their own.
Measured against this goal as of 2026-09-12: question recall 0.118–0.176 on every stack
(the right page never surfaces) and absence 0/3 on every stack (it invents instead of
abstaining). The one thing adoptable today is the `CLAUDE.md` line — §1.

---

**This directory is the project root.** Everything belonging to the corpus-retrieval
bake-off lives under it. Nothing outside it is needed to read, re-run or continue the
work — with one deliberate exception, noted in §5.

```
ROOT = C:\Users\Ali\Desktop\retrieval-lab\
```

Scripts derive every path from this root via `corpus-lab/bin/labpaths.py`. No script
hardcodes a location. Override any of it with env vars (§6) if the tree ever moves.

---

## 1. Start here, depending on what you want

| I want to… | read |
|---|---|
| **understand the whole thing** | `corpus-lab/05_findings/NIGHT2_FULL_REPORT.md` ← self-contained |
| see just the results table | `corpus-lab/05_findings/GRID.md` |
| continue the work | `corpus-lab/RESUME.md` |
| know what was asked for | `00_brief/GRID_RUN_SPEC.md` |
| **design the solution from scratch** | `00_brief/SOLVE_BRIEF.md` ← brief for an outside model: the goal, the constraints, everything measured, and deliberately no suggestions |
| audit what happened, step by step | `corpus-lab/state/progress.jsonl` |

---

## 2. The layout

```
retrieval-lab\                        <- ROOT
│
├─ INDEX.md                           <- you are here
│
├─ 00_brief\                          the task as given
│   ├─ GRID_RUN_SPEC.md               the night-2 brief that was executed
│   └─ _original_downloads\           the research passes as originally downloaded,
│       └─ research_folder\           byte-identical to corpus-lab/01_reports/passes/
│
├─ corpus-lab\                        ALL scripts, findings and run state  [git repo]
│   ├─ bin\                           the instruments (see §3)
│   ├─ 01_reports\                    research inputs, filed
│   │   ├─ TOOL_MATRIX.md             the 4 passes distilled, filtered by what runs here
│   │   └─ passes\                    C1, C2 (Claude) and G1, G2 (GPT) research rounds,
│   │                                 plus G0 on building a PK gov-statistics corpus
│   │                                 pipeline (found loose, never previously filed)
│   ├─ 02_stacks\s2_fts5\             the FTS5 indexes (gitignored - large)
│   │   ├─ raship.db                  3.41 GB,   614,150 pages
│   │   └─ harness_15000.db           6.97 GB, 1,206,260 pages
│   ├─ 05_findings\                   THE OUTPUT
│   │   ├─ NIGHT2_FULL_REPORT.md      task + method + results + diagnosis + limits
│   │   ├─ GRID.md                    the grid table, auto-generated, + prose
│   │   ├─ FINDINGS_LIVE.md           findings as they landed, each with its condition
│   │   ├─ DECISION_MEMO.md           night 1's deliverable (superseded)
│   │   └─ OPEN_QUESTIONS.md          night 1's ranked next actions
│   ├─ state\                         machine-readable run state
│   │   ├─ progress.jsonl             ONE JSON LINE PER STEP - the audit trail
│   │   ├─ cells\                     per (stack, tree) cell records
│   │   ├─ checksums\                 planted-file sha256 snapshots
│   │   ├─ diagnose_recall.json       the ranking diagnosis, raw
│   │   ├─ bench_embed__raship.json   why S3 was not built
│   │   └─ phase2_6_closure_proof.json the sandbox proof, verbatim refusals
│   ├─ 99_scratch\                    logs, backups, install transcripts
│   ├─ RESUME.md                      how to continue from cold
│   ├─ NIGHT1_FULL_WRITEUP.md         night 1, for context
│   ├─ INVENTORY.md / CLEANUP_LOG.md / 00_RUNBOOK.md   night-1 housekeeping
│   └─ .git\                          full history of both nights
│
├─ harness\                           the synthetic corpora (the TARGET-shaped tree)
│   ├─ corpus_500 / _2000 / _5000 / _15000      independent hard copies, not linked
│   ├─ generator\                     how they were built (regeneration is BANNED)
│   ├─ world\  seed_docs\  logs\
│   └─ BUILD_REPORT.md
│
├─ _private\                          ANSWER KEYS - never reachable from a test session
│   ├─ harness_keys\                  answer_key.json, canary_slots.json
│   ├─ canaries\                      manifests, companions, plant backups (pass 1 + 2)
│   └─ results\                       03_runs\ (189 sessions), 04_scores\,
│                                     _transcript_quarantine\, _memory_quarantine\
│
└─ .venv\                             the ONLY place pip may install
```

---

## 3. The instruments (`corpus-lab/bin/`)

| script | what it does |
|---|---|
| `labpaths.py` | **every path in the project derives from here.** Start reading here. |
| `ask.py` | runs ONE headless session and records what it did. The measurement primitive. |
| `run_canaries.py` | the canary battery for a (stack, corpus) |
| `run_harness.py` | the 20-question battery; `--only` fills gaps without re-paying |
| `run_grid.py` | drives one full cell: the 11 steps of spec 7.2, with a gate after each |
| `stack.py` | installs / removes a stack in a corpus. **Always teardown.** |
| `index_build.py` | builds an FTS5 page index over any tree |
| `corpus_search.py` | the front door the stacks point at |
| `hook_frontdoor.py` | the S2 PreToolUse hook |
| `scoring.py` | the ONE definition of "did it find it" |
| `checksums.py` | planted-file integrity, before and after every battery |
| `build_grid.py` | regenerates the table in `GRID.md` from summaries on disk |
| `diagnose_recall.py` | the ranking diagnosis |
| `bench_embed.py` | the S3 feasibility measurement |
| `smoke_index.py` | proves an index can actually find the canaries |
| `prove_closed.py` | the phase-2.6 sandbox proof |
| `quarantine_transcripts.py` | removes leaked phrases from `.claude/projects` |
| `plog.py` | appends to `progress.jsonl`; takes `@file` for the note |
| `peek.py` | safe progress view of a running battery |
| `diag_streamjson.py` / `diag_quotes.py` / `diag_denyform.py` | the three bug hunts |
| `rescore_night1.py` | night 1 re-scored under the fixed scorer |
| `rescore_from_results.py` | **night 3.** Rebuilds evidence contact from tool RESULTS, which `ask.py` never recorded. Free, replays saved transcripts. |
| `probe_score_floor.py` | **night 3.** Can a relevance score tell "answer is here" from "answer isn't"? No. |
| `rank_experiments.py` | **night 3.** Eight ways of turning a question into a query, scored against the key. |
| `verify_search_fix.py` | **night 3.** The gate on the sentence-mode search: empties fixed, finding not. |

---

## 4. Rules that still apply

- **`_private/` must never be reachable from a measurement session.** It holds the
  answers. The deny rules are in `stack.py:BACKSTOP_DENY`, and they only work with
  **absolute** paths — relative globs fail open silently.
- **`ra-ship` and the harness rungs are read-only sources.** The only writes are
  `CLAUDE.md` and `.claude/settings.json`, both via `stack.py`. Never commit ra-ship.
- **Always `stack.py teardown`** before finishing. A deny list left installed in a corpus
  applies to every Claude Code process whose cwd is that corpus — including your own.
- **Regeneration of the harness is banned.** Its determinism check failed (6,060 of 6,064
  files reproduced), so rebuilding it would silently change the ground truth.
- **Canary phrases must never enter an orchestrating session's context.** Verify
  manifests with the scripts, which print counts only.

---

## 5. The one thing outside this root

`C:\Users\Ali\Desktop\Projects\Code\ra-ship` — the second corpus. It is **not** moved
here deliberately: it is a real working repository whose git state is the baseline, and
relocating it would change what is being measured. It is a *fixture*, not the target;
see the full report §8 for why its results do not transfer.

Also outside, and deliberately so: `C:\Users\Ali\Desktop\_unrelated\agent-harness\` —
an unrelated repo whose installer merges hooks into any target's `.claude/settings.json`.
Quarantined. **Never run it near a corpus.**

---

## 6. Environment

```
CORPUS_LAB_ROOT    corpus-lab             (default: parent of bin/)
RETRIEVAL_LAB_ROOT this directory         (default: parent of corpus-lab)
LAB_PRIVATE        _private
HARNESS_ROOT       harness
RASHIP_ROOT        the ra-ship fixture
RUNS_ROOT / SCORES_ROOT   under _private/results
CANARY_MANIFEST    scoring only - NEVER defaulted, never given to a test session
CLAUDE_CMD         claude.exe - NOT claude.cmd, see the full report §3.1 bug 1
```

None are required if the tree sits where it does now; all are overridable.

---

## 7. State as of 2026-09-13

Nothing running. No stack installed in any corpus (verified, not assumed). All 31 planted
files verified unchanged. 189 measurement sessions on disk. **~$31 spent — night 3 added
nothing to that: it was entirely offline.**

Three stacks measured end to end, three not run with measured reasons. Night 3's four
findings are F20–F24 in `corpus-lab/05_findings/FINDINGS_LIVE.md`; the short version is
`corpus-lab/RESUME.md` §0.

Two things a fresh session must know before trusting anything here:

1. **The published recall numbers are superseded.** See
   `corpus-lab/state/rescore_from_results.json`. `GRID.md` carries the note, but
   `build_grid.py` regenerates that file and will drop it.
2. **`corpus_search.py` behaves differently than it did on night 2.** It takes a whole
   sentence now; `--legacy-and` reproduces the night-2 behaviour if you need to compare
   against those numbers.

Night 1 and 2 are committed in `corpus-lab/.git`. **Night 3's changes are not committed.**
