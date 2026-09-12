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

---

# GRID RUN — night 2, 2026-09-12

## Phase 0 — instruments (complete, 01:35–02:00)

**The night-1 headline survives the scorer fix, but for a reason worth stating.**
The old rule scored a hit when the answer contained the bare filename and that
filename was longer than 8 characters. `02_Source_Documents_Read_Only/README.md`
has basename `readme.md`, nine characters, so any answer mentioning any README in
a 217k-file tree would have scored as a find. That loophole was real but **never
fired**: re-scoring both night-1 batteries with a rule that requires the full
relative path or its last two segments returns **6/13 and 12/13 unchanged**, and
every single hit matched on `full_path`. Zero false hits. *Condition: holds for
these 13 pass-1 canaries and these two batteries only — it says the bug was
latent here, not that the bug was harmless in general. Pass-2 phrases are placed
in files with far more generic basenames, where it would have fired.*

**Two corrections that do change the numbers.** Neither is a scorer bug; both are
accounting.

1. **The site-packages canary must come out of the headline** (spec 7.4).
   `sig-328120` lives under `ABS_PES_PBS_Extraction_Test/02_tool_runs/.envs/mineru/
   Lib/site-packages/`, which `index_build.py` excludes by design. Stock Claude
   Code **found it**; the index stack **structurally cannot**. Scored as its own
   row, night 1 reads **S0 5/12, S2 12/12**, with S0 taking the excluded row 1/1
   and S2 taking it 0/1. The honest sentence is not "6 versus 12" but "5 versus 12
   on indexable material, and the one file the index is blind to is the one file
   grep got and the index missed."
   *Condition: depends on a tree containing dependency directories the indexer
   excludes. The target — a plain PDF-heavy folder — has no venvs, so this row
   is expected to be empty there. **Fixture-specific.***

2. **The cost totals were never comparable.** A timed-out session reports
   `cost_usd: null` and silently drops out of the sum. S0 timed out 4 times and
   reported cost for **8 of 13** sessions ($1.80); S2 timed out once and reported
   **12 of 13** ($0.98). Night 1's "half the cost" compared a sum over 8 sessions
   to a sum over 12. Every cost cell from here carries an explicit n-of-m and
   refuses to be compared across different n.
   *Condition: applies wherever any session times out — i.e. everywhere. Transfers.*

**Retrieval is now scored separately from answer text, and the two diverge hard.**
Sessions that *named* the right path having never *opened* it: S0 answered 5 but
opened 2; S2 answered 12 but opened 2. For S2 this is mostly real behaviour — the
agent answers from `corpus_search` snippets without ever reading the page — but it
is partly a measurement limit: `files_opened[]` is built from tool-call *inputs*,
so a path that only ever appears in a tool *result* is invisible to it. Recorded
as a caveat on the retrieval column, not as a finding about the stacks.

**Instrument change that breaks strict comparability with night 1.** The
front-door hook's redirect text asserted ra-ship's gitignore numbers verbatim
("495 of 217,527 files"). That claim is a property of one fixture, and injecting
it into a harness session tells the agent something false about the tree it is
searching. The redirect and `CLAUDE.md` are now corpus-neutral. S2 tonight is
therefore not the byte-identical instrument S2 was on night 1.

Also done: `--disallowedTools Write,Edit,NotebookEdit` on every measurement
session plus a sha256 manifest either side of each battery (all 13 pass-1 canaries
verified unchanged, so night 1 did not corrupt the tree); timing moved to
`time.monotonic()` with suspend detected by divergence between the wall clock and
`perf_counter` — the spec's literal "wall minus summed inter-event time" rule
cannot fire, because the gaps are measured live and sum to the wall by
construction, so a sleep lands *inside* one gap rather than vanishing from the
sum; `stack.py` state written before mutation and backups keyed per corpus;
per-(stack, corpus) hook logs; and a skipped question now prints in red and marks
its whole battery stale.

## Phases 1–2 — move, and close every route (complete, 02:00–02:40)

**The harness has no git and no `.gitignore` anywhere in it — checked, 0 hits at
any depth.** That is the condition night 1's headline finding depends on, absent
in the tree built to resemble the target. It is now confirmed rather than assumed.

### Night 1's undiagnosed stream-json break, root-caused

Not the corpus root. `claude.cmd` is a cmd.exe batch wrapper whose operative line
is `"...\bin\claude.exe" %*`, and **cmd.exe's `%*` expansion truncates at the
first newline inside an argument**. Any prompt containing `\n` therefore loses
every argument after it — including `--output-format stream-json`. The session
falls back to text mode and returns prose with returncode 0 and empty stderr,
which is precisely the reported symptom.

The apparent correlation with the corpus root was an artifact of which question
builder each root used: `run_canaries.py` asks a single-line question (worked on
ra-ship), while `run_harness.py` appends `"\n\nCite the exact file paths..."` to
every question (broke on corpus_500). Verified across 8 prompt shapes — via the
`.cmd`, the 2 containing newlines return prose and the other 6 are fine; via
`claude.exe` directly, all 8 return valid stream-json. Fix: never go through
cmd.exe. *Condition: Windows, Claude Code invoked as a subprocess through the
npm `.cmd` shim, prompt containing a newline. This is an **instrument** bug —
sir drives Claude Code interactively in a terminal and is unaffected.
**Fixture-specific; it does not transfer to the target**, but it invalidated
every harness cell night 1 produced.*

### The phase-2.5 deny pattern in the spec does not work

Worth stating plainly because it failed silently and would have been believed.
`Read(**/_private/**)` **provides no protection at all**. Measured across seven
pattern forms under `--permission-mode bypassPermissions`:

| pattern | result |
|---|---|
| `Read(**/_private/**)` — the spec's | **LEAKS** |
| `Read(*_private*)` | **LEAKS** |
| `Read(**/canary_manifest*)` | **LEAKS** |
| `Read(//C:/.../_private/**)` | **LEAKS** |
| `Read(C:\...\_private\**)` | BINDS |
| `Read(C:/.../_private/**)` | BINDS |
| `Read(C:/.../_private/**/*)` | BINDS |

A `Read()` deny binds **only** with an absolute path prefix; every relative glob
fails open and says nothing. `Bash()` patterns are matched against the command
string, so relative forms there do bind — which is why the first closure proof
showed Bash refusals alongside successful Reads and looked partially secure.
The first run of 2.6 read the manifest and the companion in full **on both
corpora**, and the transcript store on ra-ship. After switching to absolute-path
denies: **7 of 7 routes blocked on both trees**, refusals captured verbatim.
*Condition: Claude Code's settings.json permission layer, bypassPermissions,
protecting a path outside the project root. Transfers to anyone using a deny
rule this way.*

### A route the spec did not enumerate

Spec 1.4 assumes relocating the lab changes the `.claude/projects` key and so
puts night-1 transcripts out of reach. True for the harness, whose cwd moved.
**False for ra-ship, which deliberately does not move** — so every ra-ship
measurement session runs under exactly the key whose transcript directory held
**30 sessions quoting all 13 canary phrases**. Those are now moved into the
private tree, and the store is denied by absolute path. The orchestrator's own
still-open transcript cannot be moved while the run is live, which is why the
deny matters rather than being belt-and-braces.

**Instrument-integrity check:** all 13 pass-1 canary files verified byte-identical
by sha256, so nothing in night 1 or in this phase altered the corpus under test.

## Phases 3–6 — planting, indexes, feasibility (02:15–03:00)

### The backstop deny bit the experiment, not just the test sessions

The phase-3 planting agent **planted nothing**, and the cause was mine. A subagent
inherits the parent session's working directory, and this orchestration session's
cwd is ra-ship — so while the phase-2.5 backstop was installed there, the planting
agent inherited that corpus's deny list. Those patterns block the quarantine tree
by absolute path *and* block any Bash command whose text contains the marker word,
which also blocks naming the planting script itself. Every backup write was
refused. Because the brief requires backing up each file **before** modifying it,
the agent refused to plant rather than plant without backups — the right call, and
rung 15000 is byte-for-byte untouched.

The general lesson is worth keeping: **a deny list scoped to a corpus root applies
to every Claude Code process whose cwd is that root, including the orchestrator and
anything it spawns.** Planting cannot run while any stack is installed in ra-ship.
*Condition: Claude Code, project-level settings.json, subagents inheriting cwd.
Transfers to anyone using deny rules to sandbox a corpus they also work in.*

What survives from the attempt: all three specified bugs in `plant_canaries.py` are
fixed and verified against throwaway files — the inverted newline condition, the
whole-file JSON re-serialisation (replaced with in-place single-line key insertion
plus an `assert_one_hunk` check), and the missing `.html` in `TEXTY`. The agent
also found a fourth the brief did not name: reading JSON in universal-newline mode
silently converted CRLF to LF, which would have rewritten every line of a CRLF file
and defeated the single-hunk fix.

Two facts from its survey change the plan. **No directory in rung 15000 has 300+
direct children** — the largest flat directory holds 163 — so mandatory coverage
case 10 cannot be met as written and will be satisfied on a subtree count with the
shortfall stated rather than papered over. And a 760-page document exists whose
physical page index and printed page label genuinely differ, so case 1 is viable.

### S3 is not buildable tonight, measured rather than assumed

`fastembed` with `BAAI/bge-small-en-v1.5` (ONNX, CPU, no torch) runs at **8.2
pages/s** on real pages from the ra-ship index, after a 20.8 s model load. The
ra-ship index holds **614,150 pages**, which projects to a **20.8-hour** embedding
build; the rung-15000 index will be larger still, since corpus_500 alone held
39,647 pages across 489 files. There is no GPU on this machine, so this is not a
tuning problem. S3 as specified — *embed every page* — therefore gets a `not run`
cell carrying that measured rate, not a guess and not a quietly reduced scope.
*Condition: CPU-only embedding of a page-level index of this size. Transfers to
the target only if the target's page count is comparable; at ~10k PDF-heavy files
it plausibly is, which makes this a real finding about local embedding on this
class of machine rather than a lab artifact.*

### Index (4.2–4.4)

ra-ship rebuilt: 217,681 discovered, 4,649 candidates, **3,872 indexed**, 4 failed,
773 unsupported/empty, 213,032 excluded as dependency material, **614,150 pages**,
481 s, 3.41 GB. The accounting identity closes exactly. Smoke query: **12 of 13
pass-1 canaries resolve to the correct file**, 0 wrong-file, 1 absent — and the
absent one is the `site-packages` canary the indexer excludes by design, so the
7.4 ceiling is now confirmed structurally rather than inferred. The fat-PDF canary
returns physical `page_index` 221 against a printed label of 222, confirming the
two genuinely differ.

### A cross-session channel that `--disallowedTools` does not close

Checking memory dirs found `memory/sandbox-probe.md` under ra-ship's project key,
written by the phase-2.6 probe session at 01:58 — **despite `ask.py` passing
`--disallowedTools Write,Edit,NotebookEdit`**. Memory persistence does not go
through those tools, so disallowing them does not close it. One measurement session
can leave notes the next session on the same corpus reads, which would quietly
inflate recall for whichever stack ran second. The grid driver now *moves* anything
it finds into quarantine before and after every battery rather than merely checking.
This was nearly missed: the first implementation derived the project-key name from
the corpus path, got the drive-letter separator wrong, matched nothing, and returned
a confident all-clear. *Condition: any two Claude Code sessions sharing a cwd.
Transfers directly.*

## Phase 4 + first real comparison (resumed 06:50)

### The result that overturns night 1's framing

Stock Claude Code — no index, no policy, no hook — hunting exact planted strings:

| tree | canary recall | mean wall | cost |
|---|---|---|---|
| **harness rung 15000** (no git anywhere) | **15 / 17** | 29.6 s | $1.82 over 17 of 18 |
| **ra-ship** (git repo, documents gitignored) | **4 / 12** | 153.1 s | $1.43 over 9 of 13 |

Same stack, same scorer, same night. The gap is the fixture, not retrieval.
ra-ship's `.gitignore` hides every document directory from gitignore-aware search;
the harness has no `.git` at any depth, so `grep` simply works. Night 1 read the
ra-ship gap as evidence that stock search is broken and an index is required. On a
plain folder — **which is what the target actually is** — stock search finds 15 of
17 exact strings in under half a minute each. The index's apparent 3× advantage on
ra-ship is mostly the gitignore artifact.

**But the same tree tells the opposite story for real questions.** On these same
15,010 files, the S0 question battery scored **0.167** mean retrieval recall, with
**12 of 20** questions reaching zero evidence, **21** forbidden citations, and
**0 of 3** absence questions answered honestly.

So the honest two-line summary, which night 1 could not have reached because it
measured only the first capability:

> Stock tooling is **good at finding a string you can already quote**, and **bad at
> answering a question you cannot**.

Those are different capabilities. A canary battery measures the first. Sir's
problem is the second.

### A ceiling larger than every canary effect measured tonight

The rung-15000 index: 15,010 discovered, **13,634 indexed**, 32 failed (18
encrypted, 14 parser), 1,344 unsupported or empty — **of which 1,211 are
image-only PDFs with no text layer** — 0 excluded as dependency material,
**1,206,260 pages**, 782 s, 6.97 GB. Identity closes exactly.

1,211 scanned PDFs is **8% of the tree that no text index and no grep can reach
without OCR**. That is a larger hole than any difference between stacks measured
so far. *Condition: the tree contains scanned documents. The target is described as
PDF-heavy, so this very likely transfers and should be checked against sir's actual
folder before any stack is chosen.*

### An instrument bug the pass-2 design caught

`run_canaries` derived a question id as `phrase.split("-")[0] + "_" + phrase[-6:]`.
Safe for pass 1 *only* because all 13 phrases shared the shape
`prefix-8hex-6digits`. Pass 2 deliberately mixes shapes — that is spec rule 3.3,
so no single regex sweeps the set — and four of the 18 produced an id containing
`/`. The id becomes part of the result filename, `Path` read the slash as a
subdirectory that did not exist, and those four results were never written.

The battery reported **12/14**. The denominator had silently fallen from 18 to 14
and nothing said so. That is the exact silent-partial-completion failure this run
exists to measure, occurring inside the measuring instrument, and it surfaced only
because the phrase design was adversarial enough to trigger it. Fixed by
sanitising the id with a digest suffix so ids stay injective; pass-1 ids are
byte-identical, so earlier results still resolve.

### Second excluded-by-design row

The pass-2 ZIP canary is `unsupported_type` — `index_build.py` does not descend
into archives, and a grep cannot read a compressed member either. Unlike the
site-packages case this is **not** an index-only ceiling: no stack in this grid can
reach it. Scored as its own row so it neither flatters a grep-based stack nor
penalises an index-based one. Both PDF canaries returned page indices matching the
manifest exactly (734 and 200), confirming physical index and printed label are
tracked separately and correctly.
