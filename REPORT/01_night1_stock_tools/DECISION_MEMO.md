# Decision memo — corpus retrieval layer

**Run:** night01, 2026-09-10, 00:56 → 08:15. **Machine:** the target machine itself.
**Every number below came from a run in `03_runs/`; nothing here is from the research reports.**

Real compute was about three hours, not seven — the laptop slept twice mid-run. The
headline comparison completed anyway. What did not is listed in §8.

---

## 1. Bottom line

**Build the index. It works, it is free, it took ten minutes to build over the whole
17.85 GiB tree, and it more than doubles retrieval on sir's real corpus.**

| | S0 — stock Claude Code | S2 — index + front-door hook |
|---|---|---|
| **Canaries found (ra-ship, 13 planted)** | **6 / 13 — 46%** | **12 / 13 — 92%** |
| Cost for the battery | $1.80 | **$0.98** |
| Tool calls per canary | 1 – 23 | **1 – 3** |
| Wall-clock per canary | 10 – 815 s | **17 – 35 s** |
| Worst case | 23 calls, no answer, session died | 3 calls, 35 s |

The single miss is the canary deliberately planted inside `site-packages`. The index
excludes dependency directories, and the coverage report **names it as excluded** rather
than dropping it silently. That is the intended behaviour, and it is the difference
between a known gap and an invisible one.

---

## 2. The root cause is not the bug we were going to cite

The plan was to show sir Claude Code issue #16043 — ripgrep times out on a large
directory, gets SIGTERM'd, returns "0 results" silently.

**That does not reproduce on this machine.** Measured:

| ripgrep invocation over ra-ship | files seen | wall |
|---|---|---|
| `--files --no-ignore --hidden` (what Glob uses) | **217,681** | **3.05 s** |
| `--files --hidden` (respects `.gitignore`) | **495** | 0.03 s |

3.05 s is nowhere near the ~10 s timeout. The tree is on a fast SSD and is only 17.85 GiB.

**The actual cause is `.gitignore`.** ra-ship's `.gitignore` excludes every document
directory by design — `Source Documents Organized/`, `Arsalan Archive/`, `Budget EDA/`,
`ABS_PES_PBS_Extraction_Test/`, `02_Source_Documents_Read_Only/`,
`Agent Files/budget-eda-briefing/`. 94 files are tracked out of 217,527. So a
gitignore-aware search sees **495 files — 0.2% of the tree**, and the entire research
corpus is invisible to it.

Measured directly against the 13 canaries:

| search | found |
|---|---|
| grep, default (gitignore-aware) | **3 / 13 (23%)** |
| grep, `--no-ignore` | **10 / 13 (77%)** |
| index | **12 / 13 (92%)** |

Two independent, stacking causes. `.gitignore` costs 8 canaries and is fixed by one flag.
Binary formats — one DOCX, two PDFs — cost 3 more, and no flag fixes those; they need a
text-extraction layer.

### 2a. What the failure actually looks like

Verbatim from `03_runs/P2_s0_baseline/s0_baseline__raship__doc_485988.jsonl`:

```
CALL  : Grep {"pattern": "doc-f806356a-485988"}
RESULT: No files found          <-- the file exists. Silent, confident, wrong.
CALL  : Bash grep -rl ...       -> "did not complete within its 120s timeout"
CALL  : Bash grep -a -r -l ...  -> moved to background
CALL  : Bash du -sh . ; find .  -> timed out at 60s
SAY   : "Let me check on these background searches instead of piling up more slow commands."
CALL  : TaskStop                -> the agent killing its own runaway search
CALL  : Glob **/*.{pdf,docx,…}  -> dumps a wall of paths into context
… 23 calls, no answer, session dies at the cap
```

`Grep` returned **"No files found"** — not an error. The agent believed it and burned the
rest of its window. **This is exactly the reported failure, and it is now reproducible on
demand.** It is the single most useful thing to put in front of sir, because it is his own
repo, and because the fix is demonstrable in the same breath.

---

## 3. What was built and measured

**`bin/index_build.py`** — walks any tree, extracts text, writes page-level rows to SQLite
FTS5, and keeps a closed coverage ledger.

| ra-ship index | |
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

`discovered = excluded + indexed + failed + unsupported`, exactly. There is no "unknown"
state. That is the number sir can be handed: *everything is in the index, and here are the
777 exceptions with reasons.*

**`bin/corpus_search.py`** — the front door. Returns `path + page_index + snippet`, and
prints a **retrieval receipt** on every query saying how many pages were searched and what
was not searched, so a nil result reads as "no indexed page matched" rather than "it isn't
there."

**`bin/hook_frontdoor.py`** — `PreToolUse` hook that denies `Grep`, `Glob`, and Bash
crawls (`grep`/`rg`/`find`/`ls -R`/`Select-String`), and redirects to the index.

---

## 4. Delivery mechanism — settled by test, not by report

Both round-two research passes recommended "MCP server + PreToolUse deny" and **neither
tested it**. Tested here:

| question | measured answer |
|---|---|
| Do hooks load from `--settings <file>`? | **No.** Hook never fired; Grep ran unimpeded. |
| Do hooks load from project `.claude/settings.json`? | **Yes.** Fires reliably. |
| Is denying `Grep`/`Glob` enough? | **No.** The model fell through to `Bash: grep -rl` and succeeded anyway, *in the same turn*. |
| Does denying Bash crawls too work? | **Yes** — and the agent adapts immediately, going to the index on its next call. |

**Consequences for the build:**
1. The enforcement layer must be written into the target repo's `.claude/settings.json`.
   A portable installer therefore has to write one file into the repo — which is fine, and
   is what makes the config "live inside the folder" as required.
2. `Bash(grep:*)`, `Bash(rg:*)`, `Bash(find:*)` must be denied alongside the built-ins.
   This kills the round-one recommendation to "just install rga and grep from Bash" — that
   path is exactly the hole the model escapes through.
3. Denying built-ins and letting the model fall through to the index is the **only**
   workable direction, which also happens to sidestep issue #33106 (a deny is not enforced
   against MCP tools).

---

## 5. Environment constraints that eliminate most of the researched stack

Measured on this machine (AMD Ryzen AI 7 350, 8C/16T, 31.3 GiB RAM):

| | status | what it rules out |
|---|---|---|
| NVIDIA GPU / CUDA | **absent** (AMD 860M integrated) | ColQwen2.5 / visual page retrieval — the GPT round-two centrepiece |
| Docker | **not installed** | Qdrant, Elasticsearch, Datashare, Aleph, paperless-ngx |
| WSL | **not installed** | no Linux fallback at all |
| cargo / Rust | **absent** | **ripgrep-all is not installable** — the round-one "do this first" pick |
| `rg` binary | **does not exist**; `rg` in Git Bash is a Claude Code shim function that returns 0 results | anything shelling to `rg` breaks outside a Claude Bash call |
| pandoc / tesseract / sqlite3 CLI / fd / jq | **not installed** | no OCR path |
| `pdftotext` 4.00 | **present** (Git for Windows) | the one working PDF text path |
| **SQLite FTS5** | **present and verified** via Python stdlib | **the only zero-install index available** |

**This is what actually decided the build.** Of everything four research passes named, the
intersection of *free* + *installs on Windows with no GPU/Docker/WSL* + *already present*
is: **SQLite FTS5 + pdftotext + Python stdlib.** Everything else needed a toolchain this
machine does not have. The research was not wrong; it simply was never asked about Windows.

---

## 6. Extraction cost — an open question in both round-two reports, now answered

Neither report gave a single pages/sec figure. Measured, `pdftotext` with 12 workers:

| corpus | files | pages | wall | rate |
|---|---|---|---|---|
| harness_500 | 500 | 39,647 | 25 s | ~1,590 pages/s |
| **ra-ship (17.85 GiB)** | **3,899** | **555,549** | **589 s** | **~940 pages/s** |

**Extrapolated to sir's real tree (~10k files, his stated ceiling): well under 30 minutes
for a full build, and seconds for an incremental one.** Deep layout-aware extraction
(Docling/MinerU) runs 2–3 orders of magnitude slower and is not needed to locate material —
it would only be needed if we later want table structure rather than table text.

---

## 7. A control worth noting

On the **harness** corpus (clean tree, no gitignore problem, 500 files), the *baseline*
agent performed well — it correctly declined all 3 absence questions rather than inventing
numbers, and reasoned correctly about which of four duplicate copies was current.

**So the failure is not "agents are bad at this."** It is specific to the conditions of the
real tree: gitignored documents, 217k files, and binary formats. That is a much more
tractable problem, and it is the one the index solves.

---

## 8. What did not finish

| | why | cost to finish |
|---|---|---|
| Harness retrieval scoring | Sessions ran and answered correctly, but returned plain text instead of stream-json, so tool calls were not captured. **Instrumentation gap on my side, not an agent failure.** Answers salvaged to `04_scores/harness_s0_salvaged.json`. | ~30 min to fix + 40 min to re-run |
| S1 policy-only A/B (CLAUDE.md, no hook) | Ran out of clock. This is the test of whether *telling* the agent is enough, or whether *forcing* is required. | ~40 min |
| Degradation curve across 500/2k/5k rungs | Depends on the above | ~1.5 h |
| MCP variant vs Bash-CLI variant | Not attempted; the CLI works and was faster to prove | ~1 h |
| Semantic layer | No torch on the machine; CPU-only inference | deferred deliberately |
| Same-series-across-years | Untouched. Still the hardest open problem and nothing off the shelf solves it. | days, not hours |

---

## 9. Recommendation

1. **Ship the index as the front door.** FTS5 + pdftotext + the PreToolUse hook. Zero cost,
   zero install beyond what is already on the machine, ~10 min to build, 3.3 GB on disk.
2. **Make the install one command that writes `.claude/settings.json` + `CLAUDE.md` into the
   target folder**, so each repo carries its own index config — which satisfies the
   portability requirement.
3. **Add `SessionStart` incremental reconcile** so the index refreshes with no step anyone
   has to remember. Hash-keyed, so a moved file is a path update rather than a silent miss.
4. **Do not chase the vector layer yet.** Lexical + page addressing got 92% on the real
   corpus. Establish the degradation curve first, and only add semantic retrieval where the
   measurement shows lexical failing — which will be the vague trajectory questions, not
   findability.
5. **When showing sir:** lead with the `Grep → "No files found"` trace on his own repo, then
   the 6/13 → 12/13. Do not mention #16043 or #12534 — the timeout bug does not reproduce
   here, #12534 is the VS Code extension, and #4486 is closed `not_planned` by an inactivity
   bot with no human triage. The gitignore finding is stronger, is his actual problem, and
   is reproducible in three seconds.

---

## 10. Honesty notes

- The 12/13 is one battery of one run per canary, not a repeated measurement.
- Canaries measure **findability**, not answer quality. The harness measures answer quality
  and that scoring did not complete.
- The index was built once on a warm cache; a cold-cache build will be slower.
- `total_cost_usd` for the harness battery reads $0 because cost is carried in the
  stream-json result event, which those runs did not emit. It is not free; it is unmeasured.
- ra-ship was restored after the run. `git status` matches the pre-run canary-only baseline
  exactly, and nothing was committed or pushed.
