# Live findings — night01

Appended as measured. Every number here came from a run in `03_runs/`.

---

## F1. The failure reproduces on sir's own data — but the cause is NOT the timeout bug

**Measured:** real ripgrep 15.2.0 over ra-ship (217,681 files, 17.85 GiB):

| invocation | files seen | wall |
|---|---|---|
| `rg --files --no-ignore --hidden` | **217,681** | **3.05 s** |
| `rg --files --hidden` (respects .gitignore) | **495** | 0.03 s |

3.05 s is far under the ~10 s SIGTERM threshold in #16043/#4486. **The timeout bug does not
reproduce on this machine.** The tree is on a fast SSD and is only 17.85 GiB.

**The actual cause is `.gitignore` visibility.** ra-ship's `.gitignore` excludes every
document directory by design (`/Source Documents Organized/`, `/Arsalan Archive/`,
`/ABS_PES_PBS_Extraction_Test/`, `/Budget EDA/`, `/02_Source_Documents_Read_Only/`,
`/Agent Files/budget-eda-briefing/`, …). 94 files are tracked out of 217,527.
A gitignore-respecting walk therefore sees **495 files = 0.2% of the tree**, and the entire
research corpus is invisible to it.

**This matters more than the bug we were going to cite.** It is deterministic, it is
reproducible in 3 seconds, and it is happening on his real repo right now.

---

## F2. Canary visibility, measured mechanically (13/13)

`git check-ignore` + ripgrep with and without `--no-ignore`:

| canary | gitignored | grep default | grep --no-ignore | format |
|---|---|---|---|---|
| env-prod-471176-x88 | no | **HIT** | HIT | markdown |
| rev-85eb12c9-531683 | no | **HIT** | HIT | markdown |
| cfg-04b00a77-646234 | YES | MISS | HIT | markdown |
| audit-a6fb5003-851804 | no | **HIT** | HIT | HTML |
| idx-15206252-141322 | no | MISS | MISS | **DOCX** |
| sec-53a9e0be-660385 | no | MISS | MISS | **PDF (fat, p.222)** |
| pt-7fb11c5e-424362 | YES | MISS | HIT | JSON |
| tag-a0d0599a-463051 | YES | MISS | HIT | JSON |
| ref-0f1a6531-587770 | YES | MISS | MISS | **PDF (small)** |
| tbl-a6b21810-644646 | YES | MISS | HIT | markdown |
| xr-ff8c5491-746864 | YES | MISS | HIT | CSV |
| sig-de8a5936-328120 | YES | MISS | HIT | Python |
| doc-f806356a-485988 | YES | MISS | HIT | markdown |

**Default lexical search: 3/13 (23%). With `--no-ignore`: 10/13 (77%).**

Two independent, stacking causes:
1. **gitignore invisibility** — costs 8 canaries. Fixed by one flag.
2. **binary formats** — costs 3 canaries (1 DOCX, 2 PDFs). grep cannot read them at all;
   needs a text-extraction layer. No flag fixes this.

---

## F3. S0 baseline — stock Claude Code, 13 canary sessions on ra-ship

**6/13 found (46%). $1.80. 1,043 s wall at parallel-5.**

| result | canary | tool calls | wall |
|---|---|---|---|
| HIT | env_76-x88 (not gitignored) | **1** | **10.7 s** |
| HIT | rev_531683 (tracked) | **1** | **10.8 s** |
| HIT | idx_141322 (DOCX) | 7 | 162.8 s |
| HIT | tbl_644646 | 15 | 815.0 s |
| HIT | xr_746864 | 17 | 804.3 s |
| HIT | sig_328120 | 10 | 782.4 s |
| MISS | cfg_646234 | 9 | 228.2 s |
| MISS | audit_851804 (tracked!) | 4 | 228.5 s |
| MISS | sec_660385 (fat PDF) | 3 | 217.1 s |
| MISS | pt_424362 | 8 | 170.2 s |
| MISS | tag_463051 | 2 | 65.8 s |
| MISS | ref_587770 (PDF) | 1 | 46.4 s |
| MISS | doc_485988 | 23 | 549.8 s |

**The shape of the failure is the story.** The two non-gitignored canaries were found in
**one tool call and ~10 seconds**. Everything else either failed, or was brute-forced after
10-23 tool calls and 13 minutes. That is a **75× time penalty and 15× tool-call penalty** for
the same task — and it still fails more often than it succeeds.

### F3a. The verbatim failure trace (canary `doc-f806356a-485988`)

This is the single most useful artefact for showing sir. Full trace in
`03_runs/P2_s0_baseline/s0_baseline__raship__doc_485988.jsonl`:

```
CALL  : Grep {"pattern": "doc-f806356a-485988", "output_mode": "files_with_matches"}
RESULT: No files found                      <-- THE FILE EXISTS. Silent, confident, wrong.
CALL  : Bash grep -rl ...                   -> "did not complete within its 120s timeout"
CALL  : Bash grep -a -r -l ...              -> moved to background
CALL  : Bash du -sh . ; find . -maxdepth 2  -> timed out at 60s
SAY   : "Let me check on these background searches instead of piling up more slow commands."
CALL  : ToolSearch select:Monitor
CALL  : Bash git ls-files | wc -l           -> 94
CALL  : Bash du -sh --max-depth=1           -> error
CALL  : Bash ls -la
CALL  : Bash find . -type d -name node_modules -> timeout
CALL  : TaskStop                            -> agent killing its own runaway search
CALL  : Glob **/*.{pdf,docx,...}            -> dumps a wall of paths into context
... 23 calls total, no answer, session dies at the 300 s cap
```

`Grep` returned **"No files found"** rather than an error. The agent believed it, then spent
the rest of its window flailing. **This is exactly the reported failure mode**: it does not
know it missed anything.

---

## F4. Delivery mechanism — measured, not assumed

Both round-two research passes recommend "MCP server + PreToolUse deny on Grep|Glob" and
**neither tested it**. Tested here:

| finding | result |
|---|---|
| Hooks passed via `--settings <file>` | **DO NOT FIRE.** Grep ran unimpeded, hook log never written. |
| Hooks in project `.claude/settings.json` | **FIRE correctly.** |
| Agent behaviour when Grep is denied | **Falls straight through to `Bash: grep -rl ...` and succeeds anyway.** |

**Consequence for the build:** the enforcement layer must live in the project's
`.claude/settings.json`, not in a `--settings` file — which also means the portable
install has to write into the target repo. And denying `Grep|Glob` alone accomplishes
nothing: the model routes around it via Bash within one turn. `Bash(grep:*)`, `Bash(rg:*)`,
`Bash(find:*)` must be denied too, exactly as the round-two Claude report warned and the
round-one reports' "just use rga from Bash" advice would have broken.

---

## F5. Environment constraints that eliminate most of the researched stack

Measured on this machine (HP OmniBook X Flip, AMD Ryzen AI 7 350, 8C/16T, 31.3 GiB RAM):

| | status | consequence |
|---|---|---|
| NVIDIA GPU / CUDA | **absent** (AMD 860M integrated only) | ColQwen2.5 / MultiVectorEncoder visual-page retrieval is off the table |
| Docker | **not installed** | Qdrant, Elasticsearch, Datashare, Aleph, paperless-ngx all out |
| WSL | **not installed** | no Linux fallback path at all |
| `rg` binary | **does not exist** — `rg` in Git Bash is a Claude Code shim function that execs `claude.exe` with `ARGV0=rg`, which does not work on msys and returns 0 results | anything shelling out to `rg` breaks outside a Claude Bash call |
| `rga` (ripgrep-all) | **not installed**, no cargo/Rust toolchain | the round-one "do this first" recommendation is not installable here as-is |
| pandoc / tesseract / sqlite3 CLI / jq / fd | **not installed** | no OCR path; no CLI sqlite |
| `pdftotext` | **present, 4.00 (Xpdf)**, Git-Bash-only | the one working PDF text path |
| **SQLite FTS5** | **PRESENT and verified working** from Python 3.11 stdlib (SQLite 3.42.0) | **the only zero-install retrieval index available** |
| default `python` 3.11.5 | 12 packages, no pypdf/pandas/numpy | needs its own venv |
| `harness/generator/.venv` | pypdf 6.18, pandas, numpy, reportlab, openpyxl | usable for PDF work, but has no embedding stack |

**This is the finding that actually decides the build.** Of everything the four research
passes named, the intersection of *free*, *installs on Windows with no GPU/Docker/WSL*, and
*already present* is very small: **SQLite FTS5 + pdftotext + Python stdlib**. Anything
vector-based requires a ~2 GB torch CPU download and would run inference on 16 CPU threads.

---

## F6. Corpus shape — where the retrieval budget actually goes

| | files | size |
|---|---|---|
| ra-ship total | 217,527 | 17.85 GiB |
| `ABS_PES_PBS_Extraction_Test/02_tool_runs/` (venvs + model caches) | **136,569** | 6.7 GB |
| all venv / node_modules / site-packages / __pycache__ | **211,456** | 5.31 GiB |
| **actual research signal** | **~4,563** | **12.24 GiB** |
| `__MACOSX` 276-byte resource-fork shadows | 1,048 | ~0 |

**97% of the file count is reinstallable dependency material.** An indexer that does not
exclude it spends 97% of its budget on libraries. Note the deliberate tension: canary
`sig-de8a5936-328120` is planted *inside* `site-packages` precisely to test whether the
exclusion rule is overbroad.

Duplication: **885 excess copies across 393 groups.** Only 8 distinct PDFs exceed 40 MiB but
they occupy 20 file slots — dedup by hash cuts heavy-PDF ingest ~60% before parsing a page.

Page counts are badly decorrelated from file size: the fattest PDF is **4,354 pages / 57 MiB**
(ABS 2026-27), while the 56 MiB Economic Survey is only 376 pages. Nine KP `Demands for
Grants` PDFs in one folder total ~13,000 pages in ~150 MiB.
