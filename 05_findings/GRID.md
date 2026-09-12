<!-- TABLE:AUTO -->
# GRID — night 2, 2026-09-12

Every cell is a number, `not run — <reason>`, or `install failed — <error>`. No empty cells.

`canary recall` is **answer recall**: the answer named enough of the path to address the file. `retrieval` is the stricter question of whether the session actually opened it — see the caveat below the table, it is not comparable across stacks.

| stack | harness-15k canary | harness-15k question | ra-ship canary | ra-ship retrieval | cost (n/m) | tool calls | wall (excl. suspended) | setup | excluded-by-design |
|---|---|---|---|---|---|---|---|---|---|
| **s0_baseline** | 15/17 | 0.167 (12/20 zero, 21 forbidden, absence 0/3) | 4/12 | 0/12 | $1.4275 (9/13) | 119 | 153.1s | 0s (installs nothing but the backstop deny) | h15k 0/1 / ra-ship 0/1 |
| **s1_policy** | 17/17 | 0.176 (13/20 zero, 19 forbidden, absence 0/3) | not run[^s1_policy] — no result on disk | - | - | - | - | 0s beyond the shared index | h15k 0/1 / ra-ship - |
| **s2_hook** | 17/17 | 0.118 (14/20 zero, 16 forbidden, absence 0/3) | 12/12 **[night 1]** | 2/12 | $0.9847 (12/13) | 28 | 20.6s | rung-15000 index 782s / 1,206,260 pages / 6.97 GB (built once, shared with s1_policy) | h15k 0/1 / ra-ship 0/1 |
| **s3_hybrid** | not run[^s3_hybrid] — embedding build exceeds the night's budget | not run[^s3_hybrid] — embedding build exceeds the night's budget | not run[^s3_hybrid] — embedding build exceeds the night's budget | - | - | - | - | not built - 8.2 pages/s measured, 20.8 h projected for ra-ship alone | h15k - / ra-ship - |
| **s4_pdfmcp** | not run[^s4_pdfmcp] — install gate FAILED on this corpus | not run[^s4_pdfmcp] — install gate FAILED on this corpus | not run[^s4_pdfmcp] — install gate FAILED on this corpus | - | - | - | - | pip install clean; warm UNUSABLE - 415s for 5 small PDFs | h15k - / ra-ship - |
| **s5_recoll** | not run[^s5_recoll] — no headless install path | not run[^s5_recoll] — no headless install path | not run[^s5_recoll] — no headless install path | - | - | - | - | not attempted | h15k - / ra-ship - |

**Why a cell was not run:**

[^s1_policy]: **s1_policy** — not run - no result on disk
[^s3_hybrid]: **s3_hybrid** — not run - embedding build exceeds the night's budget. Measured 8.2 pages/s with fastembed BAAI/bge-small-en-v1.5 (ONNX, CPU, no torch) on real pages from the ra-ship index; that index holds 614,150 pages, projecting a 20.8-hour build. No GPU on this machine, so this is not a tuning problem. See state/bench_embed__raship.json.
[^s4_pdfmcp]: **s4_pdfmcp** — not run - install gate FAILED on this corpus. pdf-mcp 3.1.0 installs and its server exposes 13 tools, but pdf_corpus_warm/pdf_corpus_search accept neither a directory nor a glob (root -> "not a .pdf file: no extension"; root/**/*.pdf -> "file not found"), so a caller must enumerate all 9,942 PDFs explicitly - which the S4 hook also forbids the agent from doing. And warming FIVE small PDFs took 415s and returned docs:[] with 3 of 5 unprocessed, ~200s per small PDF, projecting ~23 days for the rung. pytesseract is a dependency and the rung holds 1,211 image-only PDFs, so OCR is the likely cause.
[^s5_recoll]: **s5_recoll** — not run - no headless install path. Not on PATH or in Program Files; winget has nothing under the winget or msstore sources, nor for xapian; the vendor Windows page carries no .exe/.msi/.msix link; the only linked downloads dir is GPL source-compliance tarballs. Distribution is an interactive install, which the spec rules dead.

A cell marked **[night 1]** is a re-scored night-1 battery, not a measurement taken tonight. It is shown so the row is not empty, and it must not be compared against a night-2 cell as though the instrument were the same — it was not.

<!-- TABLE:AUTO -->

## How to read this grid

`canary recall` is **answer recall**: did the answer name enough of the path to
*address* the file — the full relative path, or its last two segments. Night 1
scored a hit when the answer merely contained the bare filename and that filename
was over 8 characters, which meant any answer mentioning any README scored as
finding `02_Source_Documents_Read_Only/README.md`. That loophole never actually
fired on the pass-1 set (every night-1 hit matched on full path), but it would
have on pass 2, whose target files have far more generic names.

`retrieval` is the stricter question of whether the session actually *opened* the
file. **It is not comparable across stacks** and must not be read as a quality
ranking. `files_opened[]` is reconstructed from tool-call *inputs*, so a path that
only ever appears in a tool *result* — which is the normal case for an index stack
answering from search snippets — is invisible to it. It is reported because a
large gap between answer recall and retrieval tells you the stack is answering
from snippets rather than from the document, which is a real and relevant
behaviour, not because a low number means a bad stack.

`cost` always carries an explicit **n-of-m**. A timed-out session reports no cost
and silently drops out of the sum, so a stack that flails more looks cheaper.
**Two totals with different n are not comparable** and are never presented as if
they were.

`excluded-by-design` is its own column rather than part of the headline. One
pass-1 canary lives under `site-packages`, which the indexer excludes deliberately.
Every index-based stack has a hard ceiling there that grep-based S0 does not, so
folding it into the main number would penalise the index for a design decision
rather than a failure.

---

## Fixture-specific — does not transfer

Findings whose enabling condition is **absent** on the target. The target is: a
plain folder tree, no git, roughly 100 folders and 10k files, PDF-heavy, Windows,
terminal Claude Code. Nothing in this section may appear in the headline or in a
recommendation.

**1. The `.gitignore` root cause — night 1's entire thesis.** ra-ship is a git
repository whose `.gitignore` excludes every document directory, so gitignore-aware
search sees 495 of 217,527 files and `Grep` returns "No files found" for material
that is present. *Condition: the tree is a git repo with a `.gitignore` covering
the documents.* **Checked against the target-shaped tree: the harness has no `.git`
and no `.gitignore` at any depth — zero hits.** On a plain folder, `grep` and
`grep --no-ignore` are the same command and this finding describes nothing. It is
a property of one test fixture. It is also why ra-ship numbers are evidence about
the stacks, not about the problem being solved.

**2. The venv/model-cache bulk.** 213,032 of ra-ship's 217,681 files are dependency
material that the indexer excludes, i.e. 97.9% of the tree is noise no researcher
put there. *Condition: the tree contains Python venvs and model caches.* A document
folder has none, so both the "0.2% visible" figure and the exclusion ratio are
artifacts. The excluded-by-design column exists only because of this and is
expected to be empty on the target.

**3. The `claude.cmd` newline bug.** `claude.cmd` is a cmd.exe wrapper and `%*`
truncates at the first newline in an argument, so a multi-line prompt silently
loses `--output-format stream-json` and the session returns prose with exit 0 and
empty stderr. *Condition: Windows, Claude Code driven as a subprocess through the
npm `.cmd` shim, prompt containing a newline.* Sir drives Claude Code
interactively in a terminal and never hits this. It is an **instrument** bug — but
it invalidated every harness cell night 1 produced, which is why it is recorded
rather than quietly fixed.

**4. Everything about the deny-rule and transcript work.** The `Read(**/...)`
pattern failing open, the `.claude/projects` transcript route, the memory-dir
channel: these are properties of *running a blind measurement*, not of retrieval.
They matter for trusting these numbers and for anyone else building a rig like
this. They say nothing about whether an index helps sir find a table.

---
