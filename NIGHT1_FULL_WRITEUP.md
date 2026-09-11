# Night 1 — full write-up

**Date:** 2026-09-10, 00:56 → 08:15 local. **Machine:** the target Windows 11 laptop itself.
**Everything here was measured on this machine.** Nothing is quoted from the research reports
as fact; where a report is mentioned it is labelled as a claim, and separately noted whether
we verified it.

---

## 0. How to read this document

You know the ClickUp task ("corpus index from datalab"). You do not know anything about what
happened last night. This document is the bridge. It is self-contained — you should not need
any other file to follow it.

The short version is in §2. If you only read one section, read §2 and §4.

Sections §3 and §4 contain **corrections to premises stated in the ClickUp task itself**.
Those matter more than the rest, because acting on the task as written would send you at the
wrong problem.

---

## 1. What the task asked for, and what last night was actually for

The ClickUp task describes sir's problem: he `cd`s into a very large research folder, runs
Claude Code in the terminal, asks a vague question, and the agent silently misses material.
It skips files, drops the connections between documents, and degrades further the deeper it
goes. Prompt engineering has failed repeatedly. The task's conclusion — correct — is that the
fix is a retrieval layer, not a better prompt.

The task also lists a long queue of prior work: four deep-research passes, a canary suite
planted in a disposable copy of the ra-ship workspace, and a generated test corpus with an
answer key. All of that was already done before last night.

**What last night was for:** converting research into evidence. Four research passes had
named dozens of tools and nothing had been tested on our own setup. The instruction was to
experiment autonomously overnight and produce a recommendation backed by numbers.

**What last night was not:** the build. It was the experiment that decides the build.

**Time actually available:** the laptop slept twice, so roughly 3 hours of real compute out
of a 7-hour window. The headline comparison completed; several secondary measurements did
not. §11 lists exactly what.

---

## 2. TL;DR — the result

**On sir's real tree, stock Claude Code finds 6 of 13 planted test strings. A page-level
index built last night finds 12 of 13 — at half the cost, in 1–3 tool calls instead of up to
23, in 17–35 seconds instead of up to 815 seconds.**

| | S0 — stock Claude Code | S2 — index + front-door hook |
|---|---|---|
| Canaries found (13 planted in ra-ship) | **6 / 13 — 46%** | **12 / 13 — 92%** |
| Cost for the whole battery | $1.80 | **$0.98** |
| Tool calls per canary | 1 – 23 | **1 – 3** |
| Wall-clock per canary | 10 – 815 s | **17 – 35 s** |
| Worst single case | 23 calls, no answer, session died | 3 calls, 35 s |

The single miss is a canary deliberately planted inside a Python `site-packages` folder. The
index excludes dependency directories, and its coverage report **names that file as
excluded** rather than dropping it silently. That is the intended behaviour and it is the
whole point: a known gap instead of an invisible one.

**And the root cause turned out to be different from what the task assumed.** See §3.

---

## 3. CORRECTION 1 — the cause is `.gitignore`, not the ripgrep timeout bug

The ClickUp task builds a case around Claude Code issue **#16043**: ripgrep hits a timeout on
a large directory, gets SIGTERM'd, and returns "0 results" silently, so the agent believes
nothing is there. The plan was to show sir this bug.

**Measured last night on ra-ship — it does not reproduce here:**

| ripgrep invocation over ra-ship | files seen | wall-clock |
|---|---|---|
| `--files --no-ignore --hidden` (what Glob uses) | **217,681** | **3.05 s** |
| `--files --hidden` (respects `.gitignore`) | **495** | 0.03 s |

3.05 seconds is nowhere near the ~10 second timeout threshold. The tree sits on a fast SSD
and is only 17.85 GiB. The timeout bug is real in the reported environment (a 107 GB ignored
directory) but is not what is happening to sir.

**The real cause is `.gitignore` visibility.** ra-ship's `.gitignore` deliberately excludes
every document directory:

```
/02_Source_Documents_Read_Only/
/Source Documents Organized/
/Arsalan Archive/
/Budget EDA/
/ABS_PES_PBS_Extraction_Test/
/Agent Files/budget-eda-briefing/
...
```

94 files are tracked out of 217,527. So any gitignore-aware search sees **495 files — 0.2% of
the tree** — and the entire research corpus is invisible to it.

Verified directly against all 13 canaries (`git check-ignore` plus ripgrep both ways):

| search method | canaries found |
|---|---|
| grep, default (gitignore-aware) | **3 / 13 (23%)** |
| grep, `--no-ignore` | **10 / 13 (77%)** |
| the index built last night | **12 / 13 (92%)** |

**Two independent, stacking causes:**
1. **`.gitignore` invisibility** — costs 8 canaries. Fixed by one flag.
2. **Binary formats** — costs 3 more (1 DOCX, 2 PDFs). grep cannot read them at all. No flag
   fixes this; it needs a text-extraction layer.

This is a *better* finding than the bug. It is deterministic, reproduces in three seconds,
and it is his actual problem.

### 3a. What the failure looks like in the transcript

This is the single most useful artefact for showing sir. Verbatim from
`03_runs/P2_s0_baseline/s0_baseline__raship__doc_485988.jsonl`, a stock Claude Code session
asked to find one canary string:

```
CALL  : Grep {"pattern": "doc-f806356a-485988", "output_mode": "files_with_matches"}
RESULT: No files found            <-- THE FILE EXISTS. Silent, confident, and wrong.
CALL  : Bash grep -rl ...         -> "did not complete within its 120s timeout"
CALL  : Bash grep -a -r -l ...    -> moved to background
CALL  : Bash du -sh . ; find .    -> timed out at 60s
SAY   : "Let me check on these background searches instead of piling up more slow commands."
CALL  : ToolSearch select:Monitor
CALL  : Bash git ls-files | wc -l -> 94
CALL  : Bash du -sh --max-depth=1 -> error
CALL  : Bash ls -la
CALL  : Bash find . -type d -name node_modules  -> timeout
CALL  : TaskStop                  -> the agent killing its own runaway search
CALL  : Glob **/*.{pdf,docx,...}  -> dumps a wall of paths into its own context
... 23 tool calls total, no answer, session dies at the cap
```

`Grep` returned **"No files found"** — not an error, not a warning. The agent had no way to
know it had been lied to, believed it, and burned the rest of its window flailing. That is
precisely the failure sir reports: *"it skips stuff and doesn't link connections… misses more
detail the further it goes."*

---

## 4. CORRECTION 2 — other premises in the task that need updating

The ClickUp task already flags that its bug framing is "partly wrong" and points to a
round-two review. Consolidating, with what we can now confirm:

| claim in the task | status |
|---|---|
| #16043 — Glob silent 0-results from ripgrep timeout | **Does not reproduce on this machine** (§3). Ticket is closed as a duplicate of #4486. |
| #4486 — the ticket to actually cite | **Checked directly last night.** Closed `not_planned` on 2026-01-03, auto-locked 2026-01-10. Four comments, **all bots**, zero human triage. Labelled `platform:macos`; sir is on Windows. Honest claim: *the class of defect is filed and unfixed* — never *his exact bug is filed*. |
| #12534 — subdirectory contents invisible | **VS Code extension, not the terminal CLI.** The reporter explicitly says the CLI saw all files. Not sir's setup. |
| Read-tool silent truncation at 2000 lines | Still unreconciled across four research passes with non-overlapping issue numbers. **Not tested last night.** Do not assert it. |
| "Claude Code reaches for its own glob and grep first, so an index sitting there unused solves nothing" | **Confirmed and measured.** See §7 — and it is worse than stated: denying Grep/Glob alone is not enough, the model escapes via Bash in the same turn. |
| `deep-research-report (4).md` is one of the four research passes | **It is not.** It is a Bluetooth earbuds buying guide that got swept into the folder. There are four passes, not five. Do not read it. |

**Nothing from the bug paragraph should go in front of sir as originally written.** The
gitignore finding replaces it entirely and is stronger.

---

## 5. What happened, in order

| time | what |
|---|---|
| 00:56 | Created the lab folder `C:\Users\Ali\Desktop\corpus-lab`. Launched three parallel research agents (map the research reports; map the harness answer-key schema; survey the ra-ship tree and the local toolchain). |
| 01:00 | **M0 probe** — proved `claude -p --output-format stream-json --verbose` works headlessly and captures every tool call with its arguments, plus cost and turn count. This is the whole measurement rig; everything depended on it. |
| 01:05 | Wrote `bin/ask.py`, the instrument: one headless session per question → one `run.json` recording `files_opened[]`, `tool_calls[]`, wall-clock, cost. |
| 01:10 | **M2 probe** — ripgrep timing on ra-ship. Found the timeout bug does not reproduce, and found the 495-of-217,681 gitignore result (§3). |
| 01:18 | First S0 baseline battery launched. **It hung.** Diagnosed as a Windows process-tree bug in my own harness (see §12), fixed, relaunched. Cost ~45 minutes. |
| 01:35 | **M1 probe** — PreToolUse hook enforcement. Found hooks do not load from `--settings`, and found the model routes around a Grep-only deny via Bash grep within one turn (§7). |
| 02:05 | S0 baseline completed: **6/13**. |
| 02:20 | Wrote `bin/index_build.py`. Smoke-tested on the generated harness corpus: 500 files → 39,647 pages in 25 s. |
| 02:32 | Launched the ra-ship index build in the background. |
| 02:45 | Wrote `bin/corpus_search.py` (the front door) and `bin/hook_frontdoor.py` (the enforcement layer). |
| 02:53 | Launched the S0 baseline on the generated harness corpus, 20 frozen questions. |
| 03:20 | ra-ship index finished: **3,899 files, 555,549 pages, 589 s**. Verified 12/13 canaries resolve through it mechanically. |
| 03:25 | Installed the S2 stack into ra-ship and launched the end-to-end agent battery. |
| ~03:40 | **Laptop slept.** Runs stalled. |
| 08:14 | Woke. Scored everything, tore the stack down, verified ra-ship restored, wrote the deliverables. |

---

## 6. What was built

All of it is in `C:\Users\Ali\Desktop\corpus-lab\bin\`. Pure Python standard library plus
`pdftotext`, which ships with Git for Windows. **No pip installs, no services, no Docker.**

### `index_build.py` — the index
Walks any directory tree, extracts text, and writes **page-level** rows into a SQLite FTS5
database, plus a coverage ledger.

Four design decisions that matter:
- **Page-level rows, not file-level.** "Pakistan's X trajectory" is answered by one table on
  page 340, so the retrieval unit has to be a page. Finding the right 600-page PDF still
  leaves you 600 pages.
- **Coverage accounting with a closed status enum and no "unknown" state.** The identity
  `discovered = indexed + failed + excluded + unsupported` must always hold.
- **Content hash is identity; path is a mutable alias.** A moved file becomes a path update,
  not a silent miss. (This is the round-two consensus; the round-one Claude report said
  staleness wouldn't matter and was overturned by both round-two passes.)
- **Exclusions are recorded, not dropped.** 213,032 venv/cache files stay auditable as
  intentionally excluded rather than vanishing from the numbers.

Extraction: PDFs via `pdftotext -layout` split on form-feed for page boundaries; DOCX/XLSX/
PPTX by unzipping and stripping XML tags; text formats chunked at 400 lines so a hit points
at a region rather than a 100k-line file.

**Result on ra-ship:**

| | |
|---|---|
| discovered on disk | 217,681 |
| intentionally excluded (venvs, node_modules, caches) | 213,032 |
| **indexed OK** | **3,872** |
| failed extraction | 4 |
| unsupported / empty | 773 |
| **addressable pages** | **621,736** |
| **build wall-clock** | **589 s (~10 min)** |
| index size on disk | 3.3 GB |
| accounting identity closes | **yes** |

That last row is what sir can be handed: *everything is in the index, and here are the 777
exceptions with reasons.* This is the honest version of "98% scanned" that the task asks for.

### `corpus_search.py` — the front door
Queries the index. Returns `path + page_index + snippet + score`, and prints a **retrieval
receipt** on every single query saying how many pages were searched and what was *not*
searched. So a nil result reads as *"no indexed page matched"* rather than *"it isn't there"*
— which is the wording rule the research converged on and the thing that makes the system
trustworthy.

Verified working: querying the fat-PDF canary returned
`04_Research_Outputs/Deliverables/PAKISTAN_ECONOMIC_SURVEY_COMPREHENSIVE_ANNEX.pdf
[page_index=221]` — which is printed page **222**, exactly where it was planted in a
250-page PDF. Page-level addressing works, and note the physical-vs-printed offset the
research warned about is real and visible.

### `hook_frontdoor.py` — the enforcement layer
A `PreToolUse` hook that denies `Grep`, `Glob`, **and** Bash crawls (`grep`, `rg`, `find`,
`ls -R`, `Select-String`), returning a message that redirects the agent to `corpus_search.py`
and explains why. Allows `corpus_search.py` itself through, and logs every decision so
enforcement is provable rather than assumed.

### `ask.py` / `run_canaries.py` / `run_harness.py` / `stack.py`
The measurement rig: run one headless session; run the 13-canary battery; run the 20 frozen
harness questions; install/remove a delivery layer in a corpus root with exact restore.

---

## 7. Delivery mechanism — settled by test, not by report

This was listed in the ClickUp task as the biggest open decision ("MCP server, a skill, hooks,
or just CLAUDE.md plus scripts… that choice probably determines the whole shape of the
build"). Both round-two research passes recommended "MCP server + PreToolUse deny on
Grep/Glob" and **neither tested it.** Tested last night:

| question | measured answer |
|---|---|
| Do hooks load from `--settings <file>`? | **No.** The hook never fired; Grep ran unimpeded. |
| Do hooks load from the project's `.claude/settings.json`? | **Yes.** Fires reliably. |
| Is denying `Grep`/`Glob` enough? | **No.** The agent fell straight through to `Bash: grep -rl …` and succeeded anyway, *within the same turn.* |
| Does also denying Bash crawls work? | **Yes** — and the agent adapts immediately, going to the index on its next call. |

**Three consequences for the build:**

1. **The enforcement layer has to be written into the target repo's `.claude/settings.json`.**
   It cannot be passed as a flag. This means a portable installer writes one file into the
   repo — which is fine, and is exactly what "config living inside the target folder" in the
   task requires.
2. **`Bash(grep:*)`, `Bash(rg:*)`, `Bash(find:*)` must be denied alongside the built-ins.**
   This kills the round-one research recommendation to "install rga and grep from Bash" —
   that path is precisely the hole the model escapes through.
3. **Deny the built-ins and let the model fall through to the index** — never the reverse.
   This is also the only direction that works given issue #33106 (a `deny` decision is not
   enforced against MCP tool calls, but is enforced against built-ins).

One side observation: installing the hook in a corpus root intercepts **any** Claude Code
session running in that directory, including your own working session. Expected, but worth
knowing.

---

## 8. Environment constraints — this is what actually decided the build

Surveyed on the target machine (HP OmniBook X Flip, AMD Ryzen AI 7 350, 8 cores / 16 threads,
31.3 GiB RAM):

| | status | what it eliminates |
|---|---|---|
| NVIDIA GPU / CUDA | **absent** (AMD 860M integrated only) | ColQwen2.5 / visual page retrieval — the GPT round-two centrepiece |
| Docker | **not installed** | Qdrant, Elasticsearch, Datashare, Aleph, paperless-ngx, Onyx |
| WSL | **not installed** | no Linux fallback path at all |
| cargo / Rust toolchain | **absent** | **ripgrep-all is not installable** — the round-one Claude report's #1 "do this first" pick |
| `rg` binary | **does not exist.** `rg` in Git Bash is a Claude Code shim *function* that returns 0 results for everything | anything shelling out to `rg` breaks outside a Claude Bash call |
| pandoc / tesseract / sqlite3 CLI / fd / jq | **not installed** | no OCR path at all |
| `pdftotext` 4.00 | **present** (Git for Windows) | the one working PDF text path |
| **SQLite FTS5** | **present and verified working** via Python stdlib | **the only zero-install index available** |
| default `python` 3.11.5 | 12 packages; no pypdf, pandas, numpy | needs its own venv for anything heavier |

**Of everything four research passes named, the intersection of *free* + *installs on Windows
with no GPU, Docker or WSL* + *already present* is: SQLite FTS5 + pdftotext + Python stdlib.**

The research was not wrong. It was simply never asked about Windows — across all four passes,
exactly two tools are explicitly confirmed Windows-compatible. That is the largest gap between
the commissioned research and the actual machine, and it is why the built solution looks
much plainer than the reports suggest.

---

## 9. Extraction cost — an open question in both round-two reports, now answered

The ClickUp task lists this as unaddressed: *"the cost of running deep extraction across a
full tree is unaddressed in both round-two reports."* Neither gave a single pages-per-second
figure; every estimate was in engineer-hours.

Measured, `pdftotext` with 12 worker processes:

| corpus | files | pages | wall | rate |
|---|---|---|---|---|
| generated harness, 500 files | 500 | 39,647 | 25 s | ~1,590 pages/s |
| **ra-ship, 17.85 GiB** | **3,899** | **555,549** | **589 s** | **~940 pages/s** |

**Extrapolated to sir's real tree (~10k files, his stated ceiling): well under 30 minutes for
a full build, and seconds for an incremental one.** Layout-aware extraction (Docling, MinerU)
runs two to three orders of magnitude slower and is not needed to *locate* material — only if
we later want machine-readable table structure rather than table text.

---

## 10. A control worth noting

On the **generated harness corpus** (clean tree, no gitignore problem, 500 files), the
*baseline* agent performed well. It correctly declined all 3 absence questions rather than
inventing numbers — e.g. *"Nothing in the corpus contains SRO 1500(I)/2024. I searched
filenames and the text of every…"* — and reasoned correctly about which of four duplicate
copies was current.

**So the failure is not "agents are bad at this."** It is specific to the conditions of the
real tree: gitignored documents, 217k files, and binary formats. That is a far more tractable
problem, and it is exactly the one the index solves.

---

## 11. What did not finish, and why

| | why | cost to finish |
|---|---|---|
| **Harness retrieval scoring** | The 20 sessions ran and answered correctly, but returned plain text instead of stream-json, so `files_opened[]` was empty and retrieval recall is unmeasured. **This is an instrumentation gap in my harness, not an agent failure.** Answers salvaged to `04_scores/harness_s0_salvaged.json`. | ~1 h |
| **S1 policy-only A/B** | Ran out of clock. This is the test of whether *telling* the agent the index exists is enough, or whether *forcing* is required. The rig is built and ready. | ~40 min |
| Degradation curve across 500 / 2k / 5k rungs | Depends on the above | ~1.5 h |
| MCP variant vs the Bash-CLI variant | Not attempted; the CLI worked and was faster to prove | ~1 h |
| Semantic / vector layer | No torch on the machine, CPU-only inference | deliberately deferred |
| Same-series-across-years | Untouched. Still the hardest open problem; nothing off the shelf solves it. | days, not hours |

---

## 12. Traps that cost real time — do not rediscover these

- **`claude` on PATH is a shell wrapper.** Python's `subprocess` must call
  `C:\nvm4w\nodejs\claude.cmd` explicitly or you get `FileNotFoundError`.
- **`subprocess.run(timeout=)` kills `claude.cmd` but not its node grandchild**, and
  `stderr=PIPE` then blocks forever waiting on a pipe the orphan still holds. Use `Popen` +
  `taskkill /PID <pid> /T /F`, with stderr going to a file. **This silently ate 45 minutes**
  — five sessions sat at 11 CPU-seconds over 45 wall-clock minutes before I noticed.
- **`claude -p` waits 3 seconds for stdin** unless given `</dev/null`.
- **`--output-format stream-json` requires `--verbose`.**
- **Hooks do not load from `--settings`.** Project `.claude/settings.json` only.
- **`rg` in Git Bash is a shim function**, not a binary; it uses `ARGV0=`, which does not work
  on msys, and returns 0 results for everything. The real binary is at
  `C:\Users\Ali\AppData\Local\OpenAI\Codex\bin\b91d382ea836415f\rg.exe`.
- **Don't put Windows paths in bash heredocs feeding `python -c`** — backslashes break
  `unicodeescape` parsing.

---

## 13. Recommendation

1. **Ship the index as the front door.** FTS5 + pdftotext + the PreToolUse hook. Zero cost,
   nothing to install beyond what is already on the machine, ~10 minutes to build over 17.85
   GiB, 3.3 GB on disk.
2. **Make the install one command that writes `.claude/settings.json` and `CLAUDE.md` into
   the target folder**, so each repo carries its own index config. This satisfies the
   portability requirement in the task.
3. **Add a `SessionStart` incremental reconcile** so the index refreshes with no step anyone
   has to remember. Hash-keyed, so a moved file is a path update rather than a silent miss.
4. **Do not buy the vector layer yet.** Lexical plus page addressing got 92% on the real
   corpus. Establish the degradation curve first and add semantic retrieval only where the
   measurement shows lexical failing — which will be the vague trajectory questions, not
   findability.
5. **When showing sir:** lead with the `Grep → "No files found"` trace on his own repo, then
   6/13 → 12/13. Do not mention #16043, #12534 or the Read-truncation claim (§4).

---

## 14. Where everything lives

```
C:\Users\Ali\Desktop\corpus-lab\
  RESUME.md                     entry point for a fresh session
  NIGHT1_FULL_WRITEUP.md        this file
  bin\                          all the code (8 scripts)
  01_reports\TOOL_MATRIX.md     4 research passes distilled + filtered by what this machine runs
  02_stacks\s2_fts5\raship.db   the ra-ship index, 3.3 GB, 621,736 pages
  03_runs\                      raw session transcripts + per-run JSON
  04_scores\                    scored batteries
  05_findings\DECISION_MEMO.md  the deliverable
  05_findings\FINDINGS_LIVE.md  raw findings as measured
  05_findings\OPEN_QUESTIONS.md ranked next actions
  state\run_state.json          machine-readable phase status
```

**Safety state:** ra-ship was restored after the run. `git status` shows exactly 9 entries —
the canaries and pre-existing edits — matching the pre-run baseline. The `CLAUDE.md` and
`.claude/settings.json` installed for the test were removed and verified gone. **Nothing was
committed or pushed.** The 13 canaries are untouched and their `pass_fail` column is still
blank by design.

---

## 15. Next session — start here

1. **Fix the stream-json capture and re-run the harness battery** (~1 h). Unlocks every
   answer-quality number. Reproduce with a single `ask.py` call before re-running the battery.
2. **Run the S1 policy-only A/B** (~40 min): `python bin/stack.py setup --stack s1_policy`,
   then the canary battery. This answers the telling-vs-forcing question the whole delivery
   debate turns on.
3. Degradation curve at 500 / 2,000 / 5,000.
4. `SessionStart` incremental reconcile — the refresh story is unbuilt.
5. Plant the harness canaries from `harness/keys/canary_slots.json` (**18 of the 20 slots
   exist only at rung 15000** — plant at the top rung only).
