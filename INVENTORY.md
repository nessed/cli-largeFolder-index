# Inventory — everything the overnight run put on this machine

**Generated:** 2026-09-10, read-only pass. **Nothing was deleted, moved, renamed or cleaned.**

**Run window:** 2026-09-10 00:56 → 08:15 local. Anything with an mtime before 00:56 on
2026-09-10 was **not** created by this run and is marked as such.

**Grand total attributable to the run: ~3.74 GB across ~280 files.**
Of that, **3.71 GB is two SQLite index files**, both regenerable. Everything else is ~25 MB.

---

## 0. Summary — where the GB actually are

| location | size | files | attributable to the run? |
|---|---|---|---|
| `C:\Users\Ali\Desktop\corpus-lab\` | **3.716 GB** | 173 | **Yes — created entirely by the run** |
| `C:\Users\Ali\.claude\` (session state) | **~19.9 MB** | ~67 | **Yes — written by the run's headless sessions** |
| `C:\Users\Ali\AppData\Local\Temp\claude\` | **~0.8 MB** | 41 | **Yes — background task stdout** |
| `C:\Users\Ali\Desktop\harness\` | 6.093 GB | 46,710 | **No — pre-existing (built 2026-09-09). Zero files touched by this run.** |
| `C:\Users\Ali\Desktop\Projects\Code\ra-ship\` | 17.85 GiB | 217,527 | **No net change. 0 files modified after midnight.** |

---

## 1. corpus-lab — full inventory

`C:\Users\Ali\Desktop\corpus-lab` — **173 files, 3.716 GB.** Created 00:57, entirely by the run.

### 1a. Per-folder totals

| folder | files | size | notes |
|---|---|---|---|
| `02_stacks\s2_fts5\` | 7 | **3,714.47 MB** | **99.9% of the lab's disk footprint** |
| `03_runs\` | 136 | 1.37 MB | raw session transcripts |
| `bin\` | 8 | 0.05 MB | all the code |
| `04_scores\` | 8 | 0.03 MB | scored results |
| `05_findings\` | 3 | 0.03 MB | the write-ups |
| `99_scratch\` | 5 | 0.02 MB | probe fixture |
| `01_reports\` | 1 | 0.01 MB | research distillation |
| `state\` | 1 | <0.01 MB | phase status |
| `02_stacks\s0_baseline,s1_rga,s3_hybrid,s4_stretch` | 0 | 0 | **empty dirs, created but never used** |
| root `.md` files | 4 | 0.07 MB | RESUME, NIGHT1 write-up, 2× RUNBOOK |

### 1b. The big files — call-outs

| path | size | what it is | regenerable |
|---|---|---|---|
| `02_stacks\s2_fts5\raship.db` | **3,510,956,032 B (3.51 GB)** | SQLite FTS5 page-level index over the whole ra-ship tree. 3,872 files indexed, 621,736 pages. Built in 589 s. | **Y** — `python bin\index_build.py --corpus <ra-ship> --db raship.db --workers 12`, ~10 min |
| `02_stacks\s2_fts5\harness_500.db` | **203,444,224 B (203 MB)** | Same index over `harness\corpus_500`. 489 files, 39,647 pages. Built in 25 s. | **Y** — same command, ~25 s |
| `raship.db-shm` / `harness_500.db-shm` | 32,768 B each | SQLite shared-memory sidecar | **Y** — regenerated on open |
| `raship.db-wal` / `harness_500.db-wal` | **0 B each** | Write-ahead log, empty = **cleanly checkpointed, no pending writes** | **Y** |

> **These two DBs are the entire storage question.** Delete them and you free 3.71 GB and lose
> ~10 minutes of rebuild time. Nothing else in the lab is bigger than 200 KB.

### 1c. Code — `bin\` (8 files, all regenerable only by re-authoring; treat as source)

| path | size | what it is | regenerable |
|---|---|---|---|
| `bin\index_build.py` | 10,903 | The indexer. Walks any tree, extracts text (pdftotext / zipfile / plain), writes page-level FTS5 rows + coverage ledger. | **N — source code** |
| `bin\corpus_search.py` | 5,332 | The front door. Page-level search + retrieval receipt + `--coverage`. | **N — source code** |
| `bin\ask.py` | 7,080 | The instrument. Runs one headless `claude -p` session, captures every tool call. | **N — source code** |
| `bin\run_harness.py` | 7,765 | Runs + scores the 20 frozen harness questions. | **N — source code** |
| `bin\run_canaries.py` | 5,353 | Runs + scores the 13-canary ra-ship battery. | **N — source code** |
| `bin\stack.py` | 4,227 | Installs/removes a delivery layer in a corpus root, with exact restore. | **N — source code** |
| `bin\hook_frontdoor.py` | 3,214 | PreToolUse hook: denies Grep/Glob/Bash-crawl, redirects to the index. | **N — source code** |
| `bin\hook_deny.py` | 1,359 | **Superseded** first-draft hook from the M1 probe. Kept only as the artefact that proved `--settings` doesn't load hooks. | **N — but obsolete** |

### 1d. Measured results — `03_runs\` (136 files, 1.37 MB) — **ALL ONE-TIME**

These are the raw evidence. Every number in the memo traces back here. **They cannot be
regenerated** — re-running produces different sessions, and costs money.

| path | files | size | what it is | regenerable |
|---|---|---|---|---|
| `03_runs\P2_s0_baseline\` | 27 | 0.77 MB | **S0 baseline, 13 canaries on ra-ship (the 6/13 result).** 13 × `.jsonl` transcript + `.json` parsed + `.err` | **N — one-time** |
| `03_runs\P5_s2_canaries\` | 39 | 0.42 MB | **S2 index+hook, 13 canaries (the 12/13 result).** | **N — one-time** |
| `03_runs\P2_s0_harness\` | 60 | 0.06 MB | S0 on 20 harness questions. Answers present, tool calls NOT captured (the stream-json gap). | **N — one-time** |
| `03_runs\M1_deny\` | 6 | 0.09 MB | The three hook-enforcement probes that established `--settings` doesn't load hooks. | **N — one-time** |
| `03_runs\hooks\frontdoor.log` | 1 | 9,006 B | Every hook decision logged — this is the proof the deny fired. | **N — one-time** |
| `03_runs\P4_index_raship.log` | 1 | 1,084 B | Index build log (throughput numbers). | **N — one-time** |
| `03_runs\T\` | 2 | 0.02 MB | **Throwaway smoke test** of `ask.py`. No value. | **Y — junk** |

**Single most valuable file:** `03_runs\P2_s0_baseline\s0_baseline__raship__doc_485988.jsonl`
(191,961 B) — the verbatim 23-call failure trace where Grep returned "No files found". This is
the artefact to show sir.

### 1e. Scores — `04_scores\` (8 files) — **ONE-TIME except where noted**

| path | size | what it is | regenerable |
|---|---|---|---|
| `04_scores\canaries__s0_baseline.json` | 7,950 | Scored 6/13 baseline, per-canary | **Y** — from `03_runs`, via `--score-only` |
| `04_scores\canaries__s2_hook.json` | 7,913 | Scored 12/13 result, per-canary | **Y** — same |
| `04_scores\harness__s0_baseline__rung500.json` | 7,393 | Harness scoring (recall all zero — instrumentation gap) | **Y** — same |
| `04_scores\harness_s0_salvaged.json` | 3,283 | Answers salvaged from the plain-text harness runs | **Y** — from `03_runs` |
| `04_scores\summary__s0_baseline__rung500.json` | 297 | Summary of above | **Y** |
| `04_scores\question_sample.json` | 280 | **The frozen 20-question sample + seed. Do not delete — re-drawing breaks comparability with every future run.** | **N — must persist** |
| `04_scores\harness__x__rung500.json` | 1,614 | **Junk** — from a `--stack x` smoke test | **Y — junk** |
| `04_scores\summary__x__rung500.json` | 285 | **Junk** — same | **Y — junk** |

### 1f. Write-ups — root + `05_findings\` + `01_reports\` — **ONE-TIME (authored)**

| path | size | what it is | regenerable |
|---|---|---|---|
| `NIGHT1_FULL_WRITEUP.md` | 24,115 | Complete self-contained account of the night | **N — authored** |
| `RESUME.md` | 6,892 | Entry point for a fresh session | **N — authored** |
| `05_findings\DECISION_MEMO.md` | 11,839 | The deliverable: recommendation + numbers | **N — authored** |
| `05_findings\FINDINGS_LIVE.md` | 8,908 | Raw findings as measured | **N — authored** |
| `05_findings\OPEN_QUESTIONS.md` | 4,264 | Ranked next actions + traps | **N — authored** |
| `01_reports\TOOL_MATRIX.md` | 7,877 | 4 research passes distilled, filtered by machine constraints | **N — authored** |
| `00_RUNBOOK.md` | 23,874 | Copy of the original plan file | **Y — dup of `~\.claude\plans\majestic-finding-swan.md`** |
| `00_RUNBOOK_RESULTS.md` | 11,839 | **Byte-identical duplicate of `DECISION_MEMO.md`** | **Y — redundant copy** |
| `state\run_state.json` | 4,671 | Machine-readable phase status + gotchas | **N — authored** |

### 1g. Scratch — `99_scratch\` (5 files, 0.02 MB)

| path | size | what it is | regenerable |
|---|---|---|---|
| `99_scratch\m0_fixture\readme.md` | 13 | Tiny fixture for the M0/M1 probes | **Y — trivial** |
| `99_scratch\m0_fixture\deep\a\b\c\notes_2019.md` | 36 | Fixture file holding the probe string `zz-m0probe-9931` | **Y — trivial** |
| `99_scratch\m0_fixture\.claude\settings.json` | 266 | **Hook config left in the fixture dir.** Harmless (fixture is mine) but it is a live hook config. | **Y** |
| `99_scratch\m0_out.jsonl` | 21,294 | M0 probe raw output | **Y — junk** |
| `99_scratch\m0_err.txt` | 157 | M0 probe stderr | **Y — junk** |
| `02_stacks\s2_fts5\settings_deny.json` | 266 | First-draft hook settings from M1 | **Y — superseded** |

---

## 2. Harness — `C:\Users\Ali\Desktop\harness`

**PRE-EXISTING. Built 2026-09-09 by the Codex generator run, not by last night.**

**Verified: 0 files in the entire harness tree have an mtime after 2026-09-10 00:00.** The
overnight run read from it and wrote nothing into it.

**Total: 46,710 files, 6.093 GB.**

### 2a. Which rungs actually got generated — all four

| rung | files | size | regenerable |
|---|---|---|---|
| `corpus_15000` | **15,004** | 4.071 GB | **Y** — but ~2 h + rebuild cycles |
| `corpus_5000` | **5,000** | 1.144 GB | **Y** |
| `corpus_2000` | **2,000** | 0.409 GB | **Y** |
| `corpus_500` | **500** | 0.088 GB | **Y** |
| **corpus total** | **22,504** | **5.712 GB** | |

The rungs are **independent hard copies, not links** — distinct inodes, `nlink == 1`, identical
bytes and mtimes. 500 ⊂ 2000 ⊂ 5000 ⊂ 15000 by path.

Top-level branches at rung 15000: `Sources` (4,095 files / 1.236 GB), `Papers` (2,011), `RA Work`
(1,670), `Shared with coauthors` (1,159), `Downloads` (785), `Teaching`, `Grants` (289),
`Dissertation` (226), `Conferences` (169), `.old_backup` (130), `New folder (3)` (62), `Admin` (38).

### 2b. Other harness folders

| folder | files | size | what it is | regenerable |
|---|---|---|---|---|
| `generator\.venv` | 9,094 | 0.280 GB | Python 3.11.5 venv with pypdf/pandas/numpy/reportlab/openpyxl. **Part of the reproducibility story — do not pip-install into it.** | **Y** — but recreating changes versions |
| `generator\` (code) | ~35 | small | 22 `.py` files + `config.yaml` + `exclusion_list.json` | **N — source** |
| `keys\pdf_index\` | **9,240** | 0.054 GB | One JSON sidecar per PDF: page index, printed page label, table titles, cell values. Filename = `sha256(rel_path)[:32]`. **9,240 tiny files — will hurt any tar/rsync.** | **Y** — only by full regen |
| `keys\` (rest) | 9 | 0.043 GB | see 2c | **Y** — only by full regen |
| `logs\progress\` | 5,772 | ~0 | Per-file factory progress markers | **Y — junk** |
| `world\` | 9 | 0.001 GB | Series registry, vintages, breaks, document catalogue | **Y** — only by full regen |
| `seed_docs\` | 27 | ~0 | Authored style seeds | **N — authored** |
| `BUILD_REPORT.md` | 1 | 28,433 B | 453-line build narrative | **N — authored** |

### 2c. `keys\` contents (exact)

| file | size | what it is |
|---|---|---|
| `answer_key.json` | 2,144,895 | **135 questions**, 9 types, with evidence addresses down to page + table + cell, `must_not_cite` traps, acceptable alternates |
| `rung_membership.json` | 1,897,353 | Which files exist at each rung |
| `skeleton_manifest.json` | 19,366,522 | Full file plan (only `verify.py` needs it) |
| `mtimes.parquet` | 681,162 | 22,504 rows — per-file era/role/mtime. Tamper-detection baseline |
| `placed_catalogue.json` | 18,238 | `doc_id → relative path` for 190 catalogued docs |
| `canary_slots.json` | 7,900 | 20 recommended canary placements |
| `rung_report.json` | 1,675 | Per-rung format/role breakdown |
| `extra_damaged.json` | 123 | Deliberately-unreadable file list |
| `skeleton_dirs.json` | 118,633 | Directory plan |
| `pdf_index\` | 9,240 files | see above |
| `work\` | 6 files | 0.019 GB intermediate |

### 2d. Was `canary_slots.json` ever executed? — **NO**

- `keys\plant_backups\` **does not exist** (that directory is what `plant_canaries.py` creates).
- `canary_slots.json` still carries its own note: *"Recommended placements only. Nothing has
  been planted."*
- Its mtime is **2026-09-09 11:19:45** — untouched by last night's run.
- Its `corpus_root` is hard-coded to `C:\Users\Ali\Desktop\harness\corpus_15000`.

**Nothing has been planted into any harness rung.** Note for later: 18 of the 20 slots exist
only at rung 15000.

### 2e. `BUILD_REPORT.md` — exists, 28,433 B. Verification section verbatim:

| check | result |
|---|---|
| 1. file counts per rung within 3% of ladder | PASS |
| 2. format mix per rung within 3 points of config | PASS |
| 3. fat-PDF share and page ranges | PASS |
| 4. every evidence address resolves | PASS |
| 5. every shadow file named by a question exists | PASS |
| 6. absence probes genuinely absent | PASS |
| 7. no experiment vocabulary in any path or content | PASS |
| 8. mtime distribution plausible, none on the build date | PASS |
| **9. determinism: same config reproduces the same bytes** | **FAIL** |
| 10. source exclusion list honoured | PASS |
| 11. unreadable files present and genuinely unreadable | PASS |
| 12. at least 8 duplicate clusters spanning 2+ branches | PASS |
| 13. every script input exists or is intentionally broken | PASS |

**12 of 13 PASS. Check 9 fails only because the regeneration was stopped part-way by the
operator** — the planning layer reproduced 6/6 byte-identical and the content layer 6,060 of
6,064. `logs\verify_last.json` (mtime 2026-09-09 14:59:32) holds the full output.

**Caution:** `verify.py` unconditionally writes `logs\verify_last.json` on every run, even a
single-check run. Running it mutates the harness.

---

## 3. Config / state written into directories that aren't mine

| path | what was written | still there? | how verified |
|---|---|---|---|
| `ra-ship\CLAUDE.md` | 12-line corpus policy, written by `stack.py setup` at 03:25 | **REMOVED** | `ls` returns "No such file"; `git status` shows no such untracked file; 0 files in ra-ship modified after midnight |
| `ra-ship\.claude\settings.json` | PreToolUse hook config (`matcher: Grep\|Glob\|Bash`) | **REMOVED** | `ls` returns "No such file"; directory listing of `.claude\` shows only the two pre-existing files |
| `ra-ship\.claude\` (the directory) | `stack.py` called `mkdir(exist_ok=True)` | **Pre-existed** — contains `settings.local.json` dated 2026-08-15 | directory listing |
| `ra-ship\.mcp.json` | never written | n/a | absent |
| `corpus-lab\99_scratch\m0_fixture\.claude\settings.json` | hook config for the M0/M1 probe | **STILL PRESENT** | intentional — the fixture is mine, inside corpus-lab. Harmless, but it is a live hook config in a directory a session could be launched from. |

**Current `ra-ship\.claude\` contents:**

| file | size | mtime | mine? |
|---|---|---|---|
| `settings.local.json` | 228 | 2026-08-15 13:03 | **No — pre-existing** |
| `scheduled_tasks.lock` | 124 | 2026-09-09 04:07 | **No — pre-existing** (stale lock from session `5da79a64…`) |

**No other repo was written to.** `clickup-mcp\.claude\settings.json` (2026-08-14) and
`portable-claims-extractor-main\.claude\settings.local.json` (2026-06-11) are both untouched.

---

## 4. ra-ship Desktop copy — current state

### 4a. `git status` verbatim

```
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   00_Workspace_Guide/WORKSPACE_STRUCTURE.md
	modified:   04_Research_Outputs/Deliverables/PORTAL_AUDIT_FINDINGS.html
	modified:   DOCUMENTATION_RECON.md

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	04_Research_Outputs/Deliverables/PAKISTAN_ECONOMIC_SURVEY_COMPREHENSIVE_ANNEX.pdf
	04_Research_Outputs/Deliverables/RESEARCH_MEMORANDUM_STYLE_GUIDE.docx
	LOCAL_ENVIRONMENT_SETUP.md
	harness_generator_plan.md
	portable-claims-extractor-main/
	portable_budget_extraction_pilot/

no changes added to commit (use "git add" and/or "git commit -a")
```

**This is identical to the pre-run baseline.** Nothing committed, nothing pushed.

### 4b. Files created by the run vs injected into — **NONE. Zero.**

**The overnight run created and injected nothing into ra-ship.** It only read.
Confirmed by an mtime sweep: **0 files under ra-ship modified after 2026-09-10 00:00**
(walk excluded `02_tool_runs`, `node_modules`, `site-packages`, `.envs`, `.venv`).

The 9 entries in `git status` are all from the **canary plant of 2026-09-09**, which predates
this run:

| file | canary action | date |
|---|---|---|
| `00_Workspace_Guide/WORKSPACE_STRUCTURE.md` | injected `rev-85eb12c9-531683` | 2026-09-09 |
| `04_Research_Outputs/Deliverables/PORTAL_AUDIT_FINDINGS.html` | injected `audit-a6fb5003-851804` | 2026-09-09 |
| `04_.../PAKISTAN_ECONOMIC_SURVEY_COMPREHENSIVE_ANNEX.pdf` | **created** (250 pp, canary at p.222) | 2026-09-09 |
| `04_.../RESEARCH_MEMORANDUM_STYLE_GUIDE.docx` | **created**, canary `idx-15206252-141322` | 2026-09-09 |
| `LOCAL_ENVIRONMENT_SETUP.md` | **created**, canary `env-prod-471176-x88` | 2026-09-09 |
| `DOCUMENTATION_RECON.md` | modified — **not a canary**, pre-existing edit | earlier |
| `harness_generator_plan.md` | the generator brief — **not a canary** | 2026-09-09 |
| `portable-claims-extractor-main/`, `portable_budget_extraction_pilot/` | nested repos, **not canaries**, not gitignored | earlier |

8 further canaries sit in gitignored paths and therefore do not appear in `git status`.

### 4c. Canary manifest, companion and backups — locations confirmed

| item | path | size |
|---|---|---|
| Manifest | `C:\Users\Ali\Desktop\canary_manifest_pass1.csv` | 4,897 B |
| Companion md | `C:\Users\Ali\Desktop\canary_companion_pass1.md` | 7,187 B |
| Backups of injected originals | `C:\Users\Ali\Desktop\canary_backups_pass1\` | directory, 5 backups |

All three are on **Desktop root, outside the repo** — deliberate, so the answer key can't be
found by an agent searching the tree. The manifest's `pass_fail` column is **still blank**;
last night's results were written to `corpus-lab\04_scores\`, not back into the manifest.

---

## 5. Claude Code session state written by the run

`C:\Users\Ali\.claude\` — **~19.9 MB across ~67 files** modified after midnight.

| path | size | what it is | regenerable |
|---|---|---|---|
| `.claude\projects\C--Users-Ali-desktop-projects-code-ra-ship\*.jsonl` | ~13 MB across ~14 files (01:43–08:13) | **Full transcripts of the headless canary sessions.** Duplicates what's in `03_runs`, but richer. | **N — one-time** |
| `.claude\projects\C--Users-Ali-Desktop-harness-corpus-500\` | **9.04 MB, 27 files** | Transcripts of the 20 harness question sessions | **N — one-time** |
| `.claude\projects\C--Users-Ali-Desktop-corpus-lab-99-scratch-m0-fixture\` | 0.80 MB, 5 files | M0/M1 probe sessions | **N — one-time, low value** |
| `.claude\file-history\9937661a-…\` | 18 files, 0.14 MB | Backups of files I edited this session | **Y** |
| `.claude\backups\.claude.json.backup.*` | 5 files, 0.72 MB | Claude Code's own config backups | **Y — Claude Code housekeeping** |
| `.claude\shell-snapshots\` | 11 files, 0.04 MB | Bash env snapshots | **Y — housekeeping** |
| `.claude\plans\majestic-finding-swan.md` | ~24 KB | The overnight plan file | **N — authored** (duplicated at `corpus-lab\00_RUNBOOK.md`) |
| `.claude\history.jsonl`, `sessions\`, `paste-cache\` | small | Claude Code state | **Y — housekeeping** |

### 5a. ⚠️ MEMORY FILES — the one genuinely unexpected side effect

The headless harness sessions **wrote persistent memory files** into:

`C:\Users\Ali\.claude\projects\C--Users-Ali-Desktop-harness-corpus-500\memory\`

| file | size | content |
|---|---|---|
| `MEMORY.md` | 355 B | Index pointing at the two below |
| `perturbed-values-pdfs-are-not-sources.md` | 1,230 B | "Corpus PDFs with `- perturbed values` in the filename hold deliberately altered numbers… canonical copies live under `Sources/`" |
| `survey-appendix-restates-earlier-years.md` | 1,548 B | "…a spreadsheet/document number mismatch is usually a publication-vintage difference…" |

**Why this matters:** these are memories about the **synthetic** harness corpus, written as
though they were real project knowledge — they cite `RA Work/tax_effort/PLAN.md` and an
"HEC NRPU 2019 proposal" that exist only inside the generated tree. Any future Claude Code
session launched in `harness\corpus_500` will load them as background context.

They are also, on their own terms, **correct and rather good** — the agent worked out the
perturbed-values trap and the vintage convention unaided, which is itself a finding. But they
are scoped to a disposable test corpus.

**Recommendation: delete them before any future harness measurement run**, because they give
later runs prior knowledge the baseline run did not have, which breaks comparability.
**One-time / not regenerable, but should be binned.** I have not touched them.

---

## 6. Temp

`C:\Users\Ali\AppData\Local\Temp\claude\` — **41 files, ~0.8 MB**, all background-task stdout
captures from the run (`tasks\*.output`). Largest is `a59b9ec6932d23066.output` at 598,534 B
(the toolchain survey agent's transcript).

**Regenerable: N/A — pure junk, safe to bin.** Content is duplicated in `03_runs` and in the
`.claude\projects` transcripts.

---

## 7. Anything still running or scheduled

| check | result |
|---|---|
| node / claude / python / rg / pdftotext processes | **One only:** `claude` PID 12312, started 11:41 — **this session.** No orphans. |
| Background bash tasks from the run | All completed; none live |
| File handles on the index DBs | `-wal` files are **0 bytes** = cleanly checkpointed. `-shm` present but no writer. **Safe to move or delete the DBs.** |
| Scheduled tasks | Only `IndexerAutomaticMaintenance` (State: Ready) — **this is the built-in Windows Search indexer, not created by the run** |
| Watchers / file monitors | None. No watcher was ever installed. |
| MCP servers | None started. The MCP variant was never built. |

**Nothing is running. Nothing is scheduled. Nothing holds a lock.**

---

## 8. Machine-level changes

**Nothing was installed and nothing was changed at machine level.** Verified:

| check | before (survey, 01:15) | now | changed? |
|---|---|---|---|
| pip packages in default Python 3.11.5 | 12 | **12** (certifi, charset-normalizer, defusedxml, idna, lxml, pip, python-docx, requests, setuptools, typing_extensions, urllib3, youtube-transcript-api) | **No** |
| npm globals | 7 | **7** (`@anthropic-ai/claude-code@2.1.257`, `@openai/codex`, `@shopify/cli`, `corepack`, `n8n`, `npm`, `openclaw`) | **No** |
| venvs created | — | **none in corpus-lab** | **No** |
| PATH / env vars | — | no persistent edits; `CORPUS_DB` was only ever set per-command | **No** |
| Anything installed (rga, cargo, tesseract, Docker, WSL) | absent | **still absent** | **No** |

The whole stack ran on Python stdlib plus `pdftotext`, which already shipped with Git for
Windows. **This was a design constraint, and it held.**

---

## 9. Things I am not certain about

1. **`C:\Users\Ali\Desktop\Diagnostics\Battery\battery\lag-watch.csv`** — 337,613 B, modified
   **11:59 today**. Almost certainly a separate battery-diagnostic job of yours, not mine. I
   never wrote to `Desktop\Diagnostics`. **Flagging because it is inside today's window.**

2. **`C:\Users\Ali\Downloads\Todaro_-_Smith__2015_...[69-147].pdf`** — 1,833,488 B, modified
   **00:04**, which is **52 minutes before my run started**. Not mine.

3. **The two `compass_artifact_wf-*.md` on Desktop** — modified **00:31**, 25 minutes before my
   run. These are the round-one/round-two Claude research reports. Not written by me; I only
   read them.

4. **`Temp\claude\...\5da79a64-9bd1-498e-955d-c08df8a46284\tasks\*`** — a session directory
   holding several MB of task output (largest 2,276,134 B). That session ID also appears in
   `ra-ship\.claude\scheduled_tasks.lock` dated **2026-09-09 04:07**, so it **predates** my
   run — it looks like the canary-planting or generator session. **Not mine, but I can't prove
   it definitively.**

5. **`03_runs\P2_s0_harness\` has 60 files for 20 questions but only 19–20 completed** — some
   `.jsonl` are 0 bytes (`mb_07`, `rl_05`, `tr_04`) and `rc_05.jsonl` is 19 bytes. These are
   **partial writes from sessions killed when the laptop slept.** Harmless, but they are why
   the harness scoring shows gaps.

6. **RESOLVED (checked while writing this):** `03_runs\P5_s2_canaries\s2_hook__raship__sig_328120`
   — the 13th canary, the `site-packages` one. Its record shows `wall_s = 23,492` (**6.5
   hours**), `timed_out: true`, `returncode: -1`, no answer. It made 5 Bash + 1 PowerShell +
   ToolSearch + TaskOutput calls, so it was actively working, then was **suspended by the
   laptop sleep and killed by the timeout on wake.**

   So the honest phrasing of the headline is **"12 confirmed hits, 1 indeterminate"**, not
   "12 hits and 1 miss." Separately and independently, the *mechanical* index test (querying
   the DB directly, no agent involved) also returns MISS for this canary — because it lives
   under `site-packages`, which the indexer excludes by design and reports as excluded. So
   **12/13 is the right score, but the 13th is a by-design exclusion rather than an agent
   failure**, and the agent session that would have confirmed it never finished.
   `DECISION_MEMO.md` and `NIGHT1_FULL_WRITEUP.md` describe the exclusion correctly but do not
   mention that this particular session was also sleep-killed. Minor, but worth knowing.

7. **`.claude\projects\` contains many large pre-existing directories** — `jarvis` (98 MB),
   `Desktop-bs` (83 MB), `page-read-task` (76 MB), `Downloads-ra-ship` (20 MB). **None of
   these are mine.** Only the three listed in §5 were written last night.

8. **`00_RUNBOOK_RESULTS.md` is a byte-identical copy of `DECISION_MEMO.md`** — I made it as a
   convenience and it is pure redundancy.

---

## 10. If you want the short version of what to bin

| candidate | frees | risk |
|---|---|---|
| `02_stacks\s2_fts5\*.db` (both) | **3.71 GB** | none — 10 min to rebuild |
| `harness\logs\progress\` (5,772 markers) | ~0 | none |
| `03_runs\T\`, `04_scores\*__x__*` | ~20 KB | none — smoke-test junk |
| `99_scratch\m0_*` | ~21 KB | none |
| `00_RUNBOOK_RESULTS.md` | 12 KB | none — exact duplicate |
| `bin\hook_deny.py`, `02_stacks\s2_fts5\settings_deny.json` | 2 KB | none — superseded |
| `Temp\claude\...\tasks\*.output` (this run's 41) | ~0.8 MB | none |
| `.claude\projects\...harness-corpus-500\memory\` | 3 KB | **should be binned** — contaminates future harness runs |
| **Keep no matter what** | | `03_runs\` (one-time evidence), `04_scores\question_sample.json` (frozen sample), `bin\` (source), `05_findings\` + `01_reports\` + `NIGHT1_FULL_WRITEUP.md` (authored), the whole `harness\keys\` tree |
