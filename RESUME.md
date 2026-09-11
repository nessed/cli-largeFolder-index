# START HERE

A fresh session can continue from this file alone.

```
cd C:\Users\Ali\Desktop\retrieval-lab\corpus-lab
```

**Paused 2026-09-12 ~03:50, resuming 06:50.** Nothing is running. No stack is
installed in any corpus. All 31 planted files verified unchanged by sha256.

---

## 1. Where everything lives (moved on night 2)

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

## 2. Read these first

| file | what it gives you |
|---|---|
| `state/progress.jsonl` | **the record of the whole run.** `tail` it. |
| `05_findings/FINDINGS_LIVE.md` | findings as they landed, each with its condition |
| `05_findings/GRID.md` | the deliverable; the table is auto-generated |
| `Desktop\GRID_RUN_SPEC.md` | the spec being executed |

## 3. Resume here, in this order

```bash
# 1. rebuild the rung-15000 index (~10 min; killed at 2750/15010 when paused)
python bin/index_build.py --corpus "C:\Users\Ali\Desktop\retrieval-lab\harness\corpus_15000" --db 02_stacks/s2_fts5/harness_15000.db --workers 10

# 2. smoke-test the pass-2 canaries against it (prints counts only, no phrases)
set CANARY_MANIFEST=C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass2.csv
set CORPUS_DB=C:\Users\Ali\Desktop\retrieval-lab\corpus-lab\02_stacks\s2_fts5\harness_15000.db
python bin/smoke_index.py --corpus-root "C:\Users\Ali\Desktop\retrieval-lab\harness\corpus_15000"

# 3. then one cell per (stack, tree). run_grid does all 11 steps of spec 7.2.
set CANARY_MANIFEST_PASS1=C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass1.csv
set CANARY_MANIFEST_PASS2=C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass2.csv
python bin/run_grid.py --stack s0_baseline --tree h15000 --skip-questions
python bin/run_grid.py --stack s1_policy   --tree h15000
python bin/run_grid.py --stack s2_hook     --tree h15000
python bin/run_grid.py --stack s1_policy   --tree raship
python bin/run_grid.py --stack s2_hook     --tree raship
python bin/run_grid.py --stack s4_pdfmcp   --tree h15000

# 4. rebuild the deliverable table at any point
python bin/build_grid.py
```

## 4. Results so far

| cell | result |
|---|---|
| s0_baseline / ra-ship canaries | **4/12** answer, 0/12 retrieval, 5 timeouts, $1.43 over 9 of 13 |
| s0_baseline / h15000 questions | **0.167** mean recall, **12/20** zero-recall, **21** forbidden citations, **absence 0/3**, 6 timeouts, $12.54 over 14 of 20 |

By question type the baseline scored **0.000 on point_lookup** (all 3 reached zero
evidence) and **0.000 on multi_branch** (all 3 timed out). So this is not only a
vague-question problem — stock tooling missed the evidence on the most concrete
question type in the set.

Night 1 re-scored with the fixed scorer: 6/13 and 12/13 both survive, but the
honest split is **S0 5/12, S2 12/12** once the `site-packages` canary is scored as
its own excluded-by-design row — and that is the one file grep found and the index
structurally cannot.

## 5. Three bugs found on night 2 that invalidated earlier work

1. **`claude.cmd` truncates multi-line prompts.** It is a cmd.exe wrapper and `%*`
   stops at the first newline, so any prompt containing `\n` silently lost
   `--output-format stream-json`; the session returned prose, rc 0, empty stderr.
   That is night 1's undiagnosed break — never the corpus root. **Fix: invoke
   `claude.exe` directly** (`labpaths.CLAUDE`). Confirmed: harness questions now
   record 17–18 files opened where night 1 recorded zero.
2. **`Read(**/_private/**)` does nothing.** Under `bypassPermissions` a `Read()`
   deny binds **only** with an absolute path prefix; relative globs fail open
   silently. The first closure proof read the manifest in full on both corpora.
   `Bash()` patterns match the command string, so relative forms do bind there.
3. **Sessions write `memory/` despite `--disallowedTools Write`.** Memory
   persistence does not go through those tools, so one battery could hand notes to
   the next. `run_grid.py` now quarantines memory files either side of every cell.

## 6. Traps — do not rediscover these

- A deny list installed in a corpus applies to **every** Claude Code process whose
  cwd is that root, including this orchestrator and any subagent it spawns. That is
  why phase-3 planting failed the first time. **Do not install a stack in ra-ship
  while a subagent needs to work.**
- `plog.py` accepts `@file` for the note, so a progress line that mentions a denied
  word is not refused while a stack is installed.
- `subprocess.run(timeout=)` does not kill node grandchildren; `ask.py` uses
  `Popen` + `taskkill /T /F` with stderr to a file, never a pipe. Keep it.
- Don't put Windows paths in bash heredocs feeding `python -c` — use the Write tool.
- The index DBs are gitignored. `git add -A` with a 3.4 GB db will hang the commit.
- `"canaries"` does not contain the substring `"canary"`, so a `Bash(*canary*)`
  deny does not block it. Don't rely on that either way.

## 7. Safety rules

- ra-ship and the rungs are **read-only sources**. The only writes are `CLAUDE.md`
  and `.claude/settings.json` via `bin/stack.py`. Never commit ra-ship.
- **Always** `stack.py teardown` before finishing; verify with `stack.py status`.
- Canary phrases must never enter the orchestrator's context — verify manifests
  with the scripts, which print counts only.
- `checksums.py verify` before and after every battery. **Verify, never restore.**

## 8. Budget — decide before resuming

~$14 spent. Question batteries cost $12–13 each, because they now actually
retrieve; night 1's were cheap only because the cmd.exe bug made them fail
instantly. Six or seven batteries remain, so the full grid plausibly lands at
**$60–90**. No budget was set in the spec.
