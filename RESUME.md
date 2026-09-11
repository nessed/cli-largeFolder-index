# START HERE

If you are a fresh session picking this up, read this file top to bottom. It is enough
to continue without any prior context.

```
cd C:\Users\Ali\Desktop\corpus-lab
```

---

## 1. What this is

Building a retrieval layer so Claude Code can answer vague questions over sir's huge
Pakistan-economics document tree without missing material. Prompting has already failed
repeatedly; this is the infrastructure layer underneath it.

Night 1 ran 2026-09-10, 00:56 → 08:15. Laptop slept twice, so ~3 h of real compute.

## 2. The result so far, in one line

**Stock Claude Code finds 6/13 planted canaries on ra-ship. The index built here finds
12/13 — half the cost, 1–3 tool calls instead of up to 23, 17–35 s instead of up to 815 s.**

Root cause is **`.gitignore`**, not the ripgrep timeout bug: ra-ship ignores every document
directory, so gitignore-aware search sees 495 of 217,527 files (0.2%) and `Grep` returns
"No files found" for files that exist.

## 3. Read these, in this order

| file | what it gives you |
|---|---|
| `NIGHT1_FULL_WRITEUP.md` | **everything from night 1 in one self-contained document.** Written for a reader who knows only the ClickUp task. Start here if you have no context. |
| `05_findings/DECISION_MEMO.md` | **the deliverable.** Recommendation + every number. |
| `05_findings/OPEN_QUESTIONS.md` | ranked next actions + every trap that cost time |
| `05_findings/FINDINGS_LIVE.md` | raw measured findings as they landed |
| `01_reports/TOOL_MATRIX.md` | the 4 research passes distilled and filtered by what this machine can run |
| `state/run_state.json` | machine state: phase statuses, gotchas |

## 4. The two corpora — never merge them

| | ra-ship | harness |
|---|---|---|
| path | `C:\Users\Ali\Desktop\Projects\Code\ra-ship` | `C:\Users\Ali\Desktop\harness\corpus_{500,2000,5000,15000}` |
| size | 217,527 files / 17.85 GiB | 500 → 15,004 files |
| ground truth | 13 canaries, manifest at `C:\Users\Ali\Desktop\canary_manifest_pass1.csv` | 135-question answer key in `harness/keys/answer_key.json` |
| measures | **findability** at real scale and real mess | **retrieval quality** + degradation across rungs |

Merging destroys the rung ladder and breaks the 15 absence questions. They stay separate.

## 5. How to run things

```bash
# one headless session, captures every tool call -> 03_runs/<phase>/<stack>__<corpus>__<qid>.json
python bin/ask.py --phase P --stack S --corpus <root> --corpus-label L --qid Q --question "..."

# 13-canary battery on ra-ship
python bin/run_canaries.py --phase P5_s2_canaries --stack s2_hook --parallel 3 --timeout 300
python bin/run_canaries.py --stack s2_hook --score-only      # rescore without re-running

# 20 frozen harness questions (sample is frozen in 04_scores/question_sample.json - do not re-draw)
python bin/run_harness.py --phase P6 --stack s2_hook --rung 500 --parallel 3

# build an index over ANY tree (this is the portable bit)
python bin/index_build.py --corpus <root> --db 02_stacks/s2_fts5/<name>.db --workers 12

# query it
set CORPUS_DB=C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\raship.db
python bin/corpus_search.py "search terms"
python bin/corpus_search.py --exact "literal phrase"
python bin/corpus_search.py --coverage

# install / remove a delivery layer in a corpus root
python bin/stack.py setup --stack s2_hook --corpus <root>
python bin/stack.py teardown          # ALWAYS run this before you finish
```

## 6. Indexes — DELETED in the 2026-09-10 cleanup, rebuild before any retrieval work

Both were binned to reclaim 3.71 GB. They are fully regenerable; the measured results they
produced are preserved in `03_runs/` and `04_scores/`. See `CLEANUP_LOG.md`.

| db | corpus | what it held | rebuild |
|---|---|---|---|
| `02_stacks/s2_fts5/raship.db` (was 3.51 GB) | ra-ship | 3,872 files, **621,736 pages** | `python bin/index_build.py --corpus "C:\Users\Ali\Desktop\Projects\Code\ra-ship" --db 02_stacks/s2_fts5/raship.db --workers 12` — **~10 min** |
| `02_stacks/s2_fts5/harness_500.db` (was 203 MB) | corpus_500 | 489 files, 39,647 pages | same command against `harness\corpus_500` — **~25 s** |

## 7. Do this next (ranked)

1. **Fix stream-json capture, re-run the harness battery** (~1 h). Sessions answered
   correctly but returned plain text, so `files_opened[]` was empty and retrieval recall is
   unmeasured on the harness. Reproduce with a single `ask.py` call before re-running.
2. **S1 policy-only A/B** (~40 min). `python bin/stack.py setup --stack s1_policy` then the
   canary battery. This is the telling-vs-forcing question the whole delivery debate turns
   on, and the rig is ready.
3. Degradation curve at 500 / 2,000 / 5,000.
4. `SessionStart` incremental reconcile — the refresh story is unbuilt.
5. Plant harness canaries from `harness/keys/canary_slots.json` (**18 of 20 slots exist only
   at rung 15000**).

## 8. Safety rules — these are not optional

- **ra-ship and the harness rungs are READ-ONLY sources.** The only writes into ra-ship are
  `CLAUDE.md` and `.claude/settings.json`, both installed and removed by `bin/stack.py`.
- **Always `python bin/stack.py teardown` before finishing.** Verify with `git status` in
  ra-ship: it must show exactly **9** entries (the canaries). Anything else means teardown
  failed.
- **Never commit or push ra-ship.** Nothing has been committed.
- **Do not re-plant or disturb the 13 canaries.** Manifest, companion md and backups live on
  Desktop (`canary_manifest_pass1.csv`, `canary_companion_pass1.md`,
  `canary_backups_pass1\`). The `pass_fail` column is still blank by design.
- **No copies of the big corpora.** Indexes live here, in `02_stacks/`.

## 9. Traps that already cost real time — do not rediscover them

- `claude` on PATH is a shell wrapper. Python must call `C:\nvm4w\nodejs\claude.cmd`.
- `subprocess.run(timeout=)` kills `claude.cmd` but **not** its node grandchild, and
  `stderr=PIPE` then blocks forever. Use `Popen` + `taskkill /PID <pid> /T /F`, stderr to a
  file. This silently ate 45 minutes. `bin/ask.py` already does it correctly.
- `claude -p` waits 3 s for stdin unless given `</dev/null`.
- `--output-format stream-json` requires `--verbose`.
- **Hooks do not load from `--settings`.** Project `.claude/settings.json` only.
- `rg` in Git Bash is a Claude Code shim *function* using `ARGV0=`, which does not work on
  msys — it returns 0 results for everything. Real binary:
  `C:\Users\Ali\AppData\Local\OpenAI\Codex\bin\b91d382ea836415f\rg.exe`.
- Installing the hook in a corpus root intercepts **any** Claude Code session in that
  directory, including your own.
- Don't put Windows paths in bash heredocs feeding `python -c` — backslashes break
  `unicodeescape`. Use the Write/Edit tools.

## 10. When talking to sir

Lead with the `Grep → "No files found"` trace on his own repo
(`03_runs/P2_s0_baseline/s0_baseline__raship__doc_485988.jsonl`), then 6/13 → 12/13.

**Do not cite #16043, #12534, or the Read-truncation claim.** The timeout bug does not
reproduce here; #12534 is the VS Code extension, not his setup; #4486 is closed
`not_planned` by an inactivity bot with zero human triage and is labelled `platform:macos`.
The gitignore finding is stronger, is his actual problem, and reproduces in three seconds.
