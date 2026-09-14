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

---

# Night 3 — 2026-09-12/13. Offline only; no sessions run, nothing spent.

## F20. The scorer was blind to every file the agent learned about from a tool RESULT

**Measured.** `ask.py` builds `files_opened[]` only inside its `type == "assistant"` /
`tool_use` branch, from tool *inputs*. A tool result is a separate stream event
(`type == "user"`, a `tool_result` content block) and no branch reads it. So a path that
arrived in a search result was invisible to scoring.

This undercounts the index stacks **by construction**: S1/S2 work by reading
`corpus_search` hit lines, while S0 reaches files through `Read(file_path=...)`, which is
an input and was scored in full.

Re-scored from the raw transcripts already on disk — free, no sessions — with paths tiered
by what the session actually saw: `input`, `snippet` (path arrived attached to that file's
own content), `listing` (a bare name in a Glob/ls listing), `mention` (a path named inside
another file's content; never counted). Headline is input|snippet.

| mean question recall | S0 | S1 | S2 |
|---|---|---|---|
| published | 0.167 | 0.176 | 0.118 |
| re-scored | 0.167 | **0.235** | **0.176** |
| crediting bare listings too (upper bound) | 0.345 | 0.235 | 0.176 |

The re-scorer reproduces **both** published instruments exactly before changing anything —
`run_harness.py`'s recall, and `diagnose_recall.py`'s 4/0/0 evidence contact. Those two
differed because the first credits an answer-text citation and the second does not, which
had never been written down.

Three questions moved, all verified by hand against the transcripts. Tooling:
`bin/rescore_from_results.py`, raw at `state/rescore_from_results.json`.

*Condition: none. This is a property of the instrument, not of a corpus.*

## F21. The search handed the agent the right document and the agent walked past it

**Measured.** Decomposing the 17 fully-indexed questions into "did a result contain a
correct evidence file" and "did the agent then open it":

| | surfaced | then opened | ignored |
|---|---|---|---|
| s0_baseline | 1/17 | 1/1 | 0 |
| s1_policy | **5/17** | **0/5** | 5 |
| s2_hook | 2/17 | 0/2 | 2 |

Three of S1's five were cited in the answer **without ever being opened** — answered off
the search preview, never verifying the page. One preview contained
`Table 1.1: Khyber Pakhtunkhwa -- Total Budget Outlay`, the table the question asked for.

Two consequences. Night 2's finding B overstated the ranking failure — its probe was a
crude OR of up to 12 content words, while the agents' real queries surfaced correct
evidence on 5 of 17. And there is a **second failure downstream of retrieval** that no
retrieval change can fix.

*Condition: one model, one prompt shape. Irreducible blind spot: S0 made 11 `Agent` calls
and a subagent's file access never enters the parent's stream, so S0's contact is a lower
bound.*

## F22. A relevance-score floor cannot tell "the answer is here" from "it isn't"

**Measured**, `bin/probe_score_floor.py`, raw at `state/probe_score_floor.json`.

The three absence questions score at -17.56, -28.61, -28.61; the 17 answerable ones span
-10.59 to -54.40. The absence values sit **inside** the answerable range. `sd_03` — a
genuinely answerable question — scores -20.27, worse than two questions whose answers do
not exist. Every candidate discriminator overlaps: top-1 score, score per token, matching
page count, and the gap between rank 1 and rank 10.

The score tracks query length and term rarity, not whether the answer exists. In a 1.2M
page corpus an OR over common fiscal vocabulary matches 585k–914k pages whatever is asked,
so "no match" is never the signal.

**The one metric that appeared to separate is disqualified.** All three absence questions
name a specific item (a fiscal year, an SRO number), and the rarest identifier's page count
is 5,734 / 0 / 0 against a minimum of 487,610 for the answerable ones. But: it is scored on
a **subset** — 7 of 17 answerable questions contain no identifier, so the rule cannot fire
on them; it rests on n=3; the token `sro` appears on **zero of 1,206,260 pages**, so two of
the three are caught only because this harness contains no SRO notifications at all; and
`2008` does appear, 5,734 times, as **bibliography entries** (`Qureshi, Ramsha Ali (2008)`),
not fiscal-year data.

*Condition: three absence questions. The key holds 135 and more absence cases can be drawn
from it. **Fixture-specific:** sir's corpus is Pakistan tariff material, where SROs
certainly do appear, so the enabling condition for the identifier signal is absent on the
target. Barred from any headline.*

## F23. The front door could not take a sentence — and fixing that did not help

**Measured.** `corpus_search.py` built queries with `fts_quote()`, which quotes every token,
and FTS5's implicit operator between terms is AND. A nine-word question was a nine-way
conjunction. Sir's own question returned `NO MATCHES`; across the frozen 20 the question's
own words returned zero pages on 16 of 20, and on 13 of the 17 answerable ones.

Fixed 2026-09-13: try the conjunction first, fall back to any-word ranked by bm25, label
the loose tier in the output. `--legacy-and` reproduces the old behaviour. Sir's question
now returns 1,146,283 matching pages.

**The gate then failed.** `bin/verify_search_fix.py`: answerable questions returning
nothing went 17/17 → 0/17; correct evidence inside the top 15 went 0/17 → **0/17**, and
inside the top 50, 0/17 → 0/17. Fifty wrong pages instead of zero pages.

**Eight query strategies measured** (`bin/rank_experiments.py`, raw at
`state/rank_experiments.json`), scored as the rank of the correct page within the top 5,000:

| strategy | found at all | in top 500 | in top 50 |
|---|---|---|---|
| legacy AND | 0/17 | 0 | 0 |
| OR all content words | 12/17 (ranks 62–2917) | 2 | 0 |
| AND of 2 / 3 / 4 rarest terms | 0/17 | 0 | 0 |
| OR of 3 rarest | 2/17 | 1 | 0 |
| OR of 5 rarest | 6/17 | 2 | 0 |
| rerank a 2,000-page pool on term coverage | 10/17 | 2 | **1** |

**So: almost none of the "index doesn't help" result was the broken query.** The broken
query made the index return nothing; fixing it makes the index return plenty and still not
the right thing. Night 2's finding B rested on one crude probe; it now holds against eight
strategies, including the two candidate-narrowing approaches and the reranker that the
night-2 report itself listed as untested.

*Condition: this corpus, this answer key, lexical matching only. What remains untested is
matching on meaning, which is S3, dead on this machine for want of a GPU.*

## F24. Quote-before-cite written, never run

`stack.py:CLAUDE_MD` now carries a "Never answer from a search result alone" section: the
agent must open the page, quote the line or table cell verbatim in its answer, and put path
and page_index beside the quote; if it did not open it, it may not cite it. `s0_baseline`
still installs no `CLAUDE.md`, so the baseline stays a baseline.

**Unmeasured.** The paid battery was held at the F23 gate: running it would test the rule
against a search that cannot put the right page in the agent's window on 17 of 17 questions.

## F40. Approach C (shelf-first) offline gate: FAIL, on document ranking and the series walk

**Measured**, `state/c_offline_gate.json`, both configs on the 17 answerable frozen questions
(2 of 17 excluded: their evidence is not on the shelf at all):

| measure | C1 (verbatim) | C2 (+5 Haiku rewrites) | gate |
|---|---|---|---|
| doc_rank ≤ 10 | 6/17 | 8/17 | **FAIL** (need ≥ 12 for PASS, ≤ 7 is FAIL) |
| page_rank ≤ 5 (PDF evidence with a page index, n=57) | 43.9% | — (C1 only) | PASS-WEAK (40–59%) |
| series_ok (4 trajectory questions) | 0/4 | — (C1 only) | **FAIL** (≤ 1 is FAIL) |

Rewrites moved doc_rank from 6 to 8 of 17 — real but not close to the gate, and C2 was not
run for page_rank or series_ok (C1-only measures per the build spec).

**Absence enumeration**, on the key's full 15 absence questions plus the 17 evidence editions
as a control: document-level `NO_EDITION_FOR`/`NO_FAMILY_MATCHES` hit 11/11 (all of them —
the FY-token split gave 11 document-level, 4 identifier-level, not the plan's estimated
10/5); identifier-level `exact` returned zero pages on 4/4; the control (does `have --fy`
say `EDITION_PRESENT` for editions we actually hold) hit 14/17. Absence and the control both
clear their bars; finding a held document and ranking it are the failures here, not telling
absence from presence.

**Why series_ok is 0/4, checked, not assumed:** the build spec's `series` command takes the
question text itself as the in-document search phrase; a multi-clause trajectory question
has well over 4 content words, so `inside`'s tier logic falls past its exact-phrase tier to
a loose any-word match, and at k=1 that rarely lands on the one page the key names in a
corpus where every row is restated in prose across dozens of near-duplicate pages. Verified
this is not an off-by-one page-index bug: the key's page_index and this build's are both
0-based and agree on content at the exact index for a spot-checked question.

*Condition: this corpus, families derived from page-0 titles, one build. The shelf itself is
flagged `GATE1_FAILED_STRUCTURAL` (see Stage 1's gate log): the sha256-collapse accounting
identity holds exactly, but the sanity probe still fails — the family with the most
"editions" is a near-duplicate clustering defect (a repeatedly-copied paper reading as 16
editions), not the intended kind of copy-heavy family. This result is measured on that
shelf, unrepaired past the one authorized title-line fix.*

**Addendum 2026-09-14.** Four of the numbers above were measured by a defective harness and
have been re-measured: see F41 (where the document loss actually is), F42 (the corrected page
baseline and the caption channel), F43 (edition selection), F44 (the reranker, which failed
its gate). The corrected counts are C1 6/17 and C2 9/17 with 0 of 17 excluded, page 24/57 with
the corrected short query, and a symmetric present-edition control of 8/11. The absence result
and the identifier result are unchanged and survived the correction. F45 was reserved for the
offline chain test, which was not run — its pre-registered condition was not met.

## F41. The document bottleneck is ranking, not candidate generation

**Measured**, `state/c_gate_v2.json` and `state/c_recall_curve.json`, on the 17 answerable
frozen questions with the corrected denominator (0 excluded, was 2), and confirmed on the
30-question frozen holdout (aggregate counts only, never per-question).

| depth | C1 (verbatim), 17 | C2 (+5 rewrites), 17 | C1, holdout 30 | C2, holdout 30 |
|---|---|---|---|---|
| top 10 | 6 | 9 | 10 | 14 |
| top 20 | 8 | 10 | 13 | 16 |
| top 50 | 12 | 11 | 19 | 24 |
| top 100 | 14 | **16** | 27 | **28** |
| top 200 | 14 | 16 | 27 | 28 |

**The pool almost always holds the answer.** The pre-registered A0 gate was C2 gold-family
recall@100 ≥ 12 of 17. It is 16 of 17, and 28 of 30 on the holdout. So the fused FTS5 +
BGE candidate pool is not what is losing these questions: something that is already in the
top 100 is failing to reach the top 10. That authorises the reranker experiment (A1) and
rules out the competing explanation the review wanted separated out.

Depth 200 adds nothing over depth 100 in either set, so the reranker pool is fixed at 100.

**Two diagnostics recorded with it** (`--per-rewrite`, ranks only):

- *Best-single-rewrite oracle.* On 12 of 17 questions **some** single rewrite alone puts the
  gold family in its own top 10, against 9 of 17 for the six fused together. RRF over six
  query variants is losing three questions that one of its own inputs already had. Per-query
  max fusion is therefore a live future candidate — **not built here**, and not a licence to
  tune fusion weights against these 17.
- *Rewrite 4 (the "which publication would carry this" guess) never uniquely contributes.*
  Across the 17, the number of questions where exactly one rewrite index found the gold
  family at all is 0, so there is no question that rewrite 4 rescues on its own. A1 drops it
  from candidate generation, per the pre-registered rule.

Recall per rewrite index at top 10 is flat — 6, 6, 6, 6, 6, 5 for indices 0–5 — so no single
rewrite style is carrying the others, and the fused result (9) does beat any one of them.
The oracle number above is the union across questions, not one better rewrite.

*Condition: this corpus, this shelf, this fused candidate generator, top-200 pool. "Gold
family" is the family holding the key's evidence, resolved through the shelf's duplicate map.
A0 is a statement about where the loss is, not a claim that a reranker will recover it.*

## F42. Captions fix the trajectory walk and do nothing for anything else

**Measured**, `state/c_page_gate.json`, correct document handed in (Experiment A bypassed),
57 PDF evidence addresses across the 13 frozen questions that have any, top 5:

| run | query | caption channel | micro | macro |
|---|---|---|---|---|
| B0 (HISTORICAL, reproduced) | whole question | off | 25/57 = 43.9% | 30.5% |
| B1 (CORRECTED baseline) | short row phrase | off | 24/57 = 42.1% | 27.9% |
| B2 (NEW) | short row phrase | `first` | **42/57 = 73.7%** | 39.7% |

**B0 → B1 is a harness correction, not a retrieval result**, and it is worth saying that it
cost one address. The review was right that the page row fed `inside` the whole question
while the series walk had already been fixed to feed it a short row phrase (defect D1). It
was a real inconsistency in the code. It was not what was losing the page row.

**B2 against the pre-registered gate: micro clears its 60% bar, macro does not.** PASS
required both, so this is not a PASS. It is nowhere near the STOP condition either (STOP was
B2 ≤ B1 + 1 address; it is B1 + 18). The band table did not anticipate a result that splits
this way, and the bar has not been moved to accommodate it.

**Why it splits — the whole gain is on one question type:**

| type | questions | addresses | B1 | B2 |
|---|---|---|---|---|
| trajectory | 4 | 42 | 22 | **40** |
| multi_branch | 3 | 9 | 1 | 1 |
| point_lookup | 3 | 3 | 0 | 0 |
| reconciliation | 2 | 2 | 0 | 0 |
| relationship | 1 | 1 | 1 | 1 |

Not one non-trajectory address moved. On 9 of the 13 questions no caption in the gold
document contains every query content word, so the channel is simply inert there, and those
9 are what holds macro down. Trajectory questions carry 42 of the 57 addresses, which is why
micro moves so far. The honest claim is narrow: **a harvested table caption is a good page
address for a question that names a table row and asks for it across years, and is no help
at all for a question that asks for one number in prose.**

`rrf` was written alongside `first` in the same edit but, per the pre-registered rule, was
not run: the rule permitted it only as a fallback if `first` came in worse than B1.

**The series walk is still 1/4 with the winning page method — and that number does not mean
what the gate has been reading it as.** Re-running the corrected walk (k=5, exact family)
with `caption_channel="first"` threaded through `series` changes nothing: 1 of 4. The reason
is not page retrieval. Counted directly (`state/c_series_v2.json` and the diagnostic behind
it): across the four questions the fiscal years line up almost perfectly — 21 of 24 evidence
years are years the walked family actually holds — but **the file the walk opens at that
year is the file the key cites on only 3 of those 21 years.** The shelf's `is_primary` pick
inside an edition selects a different copy from the one the key names, and a page index only
carries across byte-identical copies. One question's evidence spans three families and the
walk opens none of its twelve evidence files.

So `series_ok` has been measuring *which copy the shelf calls primary*, not whether the row
can be found. With the correct document handed in, the same trajectory pages are found in
the top 5 on 40 of 42 addresses. Edition selection, not page retrieval, is what the
trajectory result was failing on — which is the sub-problem F43 measures.

*Condition: this corpus, this shelf, 13 questions with PDF addresses, 4 of them trajectory.
A caption "hits" when it contains every content word of the short row phrase; no synonym
list, no title list, nothing derived from the key. The trajectory result rests on 4
questions and should not be reported as a general finding without more of them.*

## F43. The year in the question is not the year on the edition

**Measured**, `bin/c_edition_gate.py`, `state/c_edition_set.json`. Gold family handed in, so
this is a statement about edition selection only. The structural rule was pre-registered: a
question carrying a fiscal-year token selects the family's primaries whose `fy_all` holds
that year; a trajectory or series question selects all primaries; anything else selects all
primaries.

**Set recall: 3 of 17.** The bar for adopting RETRIEVE FAMILY → SELECT EDITION(S) as a
structural rule was 15 of 17 with a mean set size ≤ 3. Mean set size is 7.06, max 21.

| branch | questions | failures |
|---|---|---|
| fiscal-year token | 10 | 10 |
| series / trajectory | 4 | 3 |
| all primaries (no narrowing possible) | 3 | 1 |

**The year branch fails on all ten, and the reason is not a bug in the rule.** Counted
directly over those ten questions' 18 evidence documents:

- only **7 of 18** have the asked year anywhere in their `fy_all`;
- only **1 of 18** has it as `fy_primary`;
- only **8 of 18** are a primary at all;
- on 4 of the 10 questions, not one evidence document carries the asked year.

So the year in a question is mostly not a label on the document that answers it. A question
about a fiscal year is answered by whichever edition happens to print that year's row — very
often a later edition carrying a historical series. The fiscal year narrows the *row*, not
the *edition*. `fy_all` is doing its job; it is being asked the wrong question.

**The second half of the failure is the copy problem F42 found.** Ten of the 18 evidence
documents are not primaries, so a set built out of primaries cannot contain them, and a page
index does not carry from one copy of an edition to another.

**Verdict, per the pre-registered interpretation: do not adopt the split.** Set recall is
below 15/17, so the rule is not adopted in the 2026-09-14 architecture and RETRIEVE DOCUMENT
stays one box. No rules were added to chase the failures — that was pre-registered too. What
this does establish is that "which edition, and which copy of it" is a real, separate,
currently-unsolved sub-problem, and that it is sitting underneath both the trajectory result
and the page result.

*Condition: this corpus, this shelf's family and edition_key grouping, 17 questions, gold
family handed in. A different family/edition grouping could change every number here.*

## F44. The reranker recovers exactly what dropping a rewrite cost, and nothing more

**Measured**, `bin/c_rerank_gate.py`, `state/c_rerank_gate.json`. Model
`Xenova/ms-marco-MiniLM-L-6-v2` through fastembed's cross-encoder; preflight passed on the
first model at 5/5 generic everyday pairs ordered correctly and 16.2 pairs/s on 350-word
passages, so no second model was tried. Candidate generation frozen, pool depth 100
(authorised by F41), passage = the family's best document's title, fiscal year and up to 8
catalog lines by content-word overlap, capped at 350 words. Query = the verbatim question.

Gold family in the top 10:

| configuration | dev 17 | holdout 30 |
|---|---|---|
| C2 fused, all six queries (F41 baseline) | 9 | 14 |
| fused pool as A1 sees it (rewrite 4 dropped, cut to 100) | 7 | 13 |
| **A1** — cross-encoder score alone | **4** | 12 |
| **A1b** — RRF(60) of the A1 rank and the fused rank | **9** | 16 |

**Pre-registered gate: STOP.** The bar was ≥12/17 for PASS, 10–11/17 for WEAK, ≤9/17 for
STOP, applied to the better configuration on the dev set. A1b is 9 of 17. The holdout moved
the right way (+2 over C2) but the configuration may not be chosen on the holdout and the
dev gate is not met, so this is a STOP and the bar was not moved to rescue it.

**The cross-encoder on its own is actively harmful**: 4 of 17, down from a 7 of 17 pool it
was handed. Ranking a publication by how well a question matches its *catalog card* is not
the same task the model was trained for — the card is a label, not a passage that answers
anything — and on this evidence the model cannot tell a directly relevant government
publication from a plausibly-titled neighbour. A1b's 9 of 17 is not the reranker working;
it is RRF pulling the fused rank back in after the cross-encoder pushed it out.

**A pre-registered rule that turned out to cost something.** F41 recorded that no question is
found by exactly one rewrite index, so A1 dropped rewrite 4 (the "which publication would
carry this" guess) from candidate generation, as pre-registered. Doing so cost one question
out of the top-100 pool (recall@100 16 → 15) and two out of the fused top 10 (9 → 7). So
A1b's 9 exactly restores C2's 9, and the honest reading of the whole experiment is: **the
reranker bought nothing.** "Never uniquely contributes a find" was the wrong test for whether
a query variant earns its place in an RRF fusion; contributing rank mass to a family other
variants also find is worth something, and the rule could not see that.

*Condition: this corpus, this shelf, one cross-encoder, two configurations, no weight sweeps.
It does not show that no reranker can help — it shows that this compact cross-encoder over
shelf catalog cards does not, and that the document bottleneck survives A0's diagnosis intact.*

---

## F46. Experiment C — per-query selection loses to rank summation. STOP

**Measured**, `state/c_fusion_gate.json`, 17 answerable frozen questions, C2 rewrites, the
same shelf and the same candidate pool. No model calls; no holdout look spent.

The 2026-09-14 handoff named this the best-supported untried idea in the repository, on the
strength of F41's oracle: on 12 of 17 questions *some* single rewrite alone already puts the
gold family in its own top 10, while all six fused together manage 9. Experiment C is the
obvious cash-out — score a family by its **best rank across the rewrites** instead of by
summed reciprocal rank, break ties on how many rewrites found it, then on summed RRF.

| depth | rrf (summation) | best (per-query selection) |
|---|---|---|
| top 10 | **9** | **5** |
| top 20 | 10 | 8 |
| top 50 | 11 | 12 |
| top 100 | 16 | 16 |
| top 200 | 16 | 16 |

**Pre-registered gate: PASS ≥12/17, WEAK 10–11, STOP ≤9. It is 5. STOP.** The bar was not
moved, no tie-break was re-specified, and the holdout was not consulted — the development set
decides, as pre-registered, and spending a look to confirm a result four questions below the
stop line would buy nothing. Holdout looks used tonight so far: **0 of 5.**

**Why the oracle did not cash out, stated plainly.** The oracle is a *union* over questions —
for each question, some rewrite works — but it says nothing about which rewrite, and a rule
has to pick without knowing. Best-rank selection gives every rewrite a veto-free top slot: a
family that any single rewrite happens to rank #1 outranks a gold family that a *good*
rewrite ranks #3, because 1 < 3 and nothing else is consulted until the tie-break. Six
rewrites therefore inject six independent chances for a noisy neighbour to take the top of
the list. Summation is doing real work precisely because it is slow to be convinced: a family
has to be found repeatedly to rise. The minimum is a maximally noise-sensitive statistic and
the sum is not.

Note the crossover at depth 50, where `best` (12) passes `rrf` (11). Per-query selection does
surface a couple of families that summation buries — it simply pays for them with four
questions at the top, which is where the measure lives. Both rules reach the same 16 of 17 at
depth 100, confirming again that candidate generation is not the loss.

**Aggregate diagnostic, families ranked above the gold family under the winning rule (rrf).**
Across the 16 questions where the gold family is ranked at all, **661** families outrank it:
**586** of kind `fy` (the family has dated primary editions) against **75** of kind
`singleton`. So what crowds out the right publication is overwhelmingly *other dated
statistical series* — near neighbours in the same genre — not undated one-off documents. The
document channel is not confusing a yearbook with a memo; it is confusing a yearbook with
another yearbook.

**Consequence for the rest of the run.** The fusion rule is frozen at **`rrf`**, by the
pre-registered "higher development count, ties to rrf" rule. `fusion="best"` stays in
`c_shelf.do_find` as a measured negative result, off by default, and `--fusion` is exposed on
the `find` CLI and on the gate so the number can be reproduced.

*Condition: this corpus, this shelf, these six rewrites, k=60, pool 200. It shows that this
particular cash-out of the F41 oracle fails; it does not show that no selection rule can beat
summation — but the next such idea needs a mechanism for choosing which rewrite to trust,
which is the thing neither F41 nor this experiment has.*

---

## F47. Experiment E1 — the caption line is a real document signal, but not at the top ten. STOP

**Measured**, `state/c_caption_family_gate.json` key `lex`, 17 answerable frozen questions,
C2 rewrites, `rrf` fusion (frozen by F46), plus one holdout evaluation. A new FTS5 index over
all **89,380** harvested captions (`state/c_caption_index.json`), one row per caption, built
beside `shelf.db` without modifying it. No model calls.

Every query contributes a third ranked list: its content words minus fiscal-year tokens and
minus the trajectory scaffolding words, matched all-words-then-any against the caption index,
ordered by bm25, entering the fusion as the documents those captions sit in.

| depth | C2 + rrf (baseline) | E1 (+ caption lexical) | holdout baseline | holdout E1 |
|---|---|---|---|---|
| top 10 | 9 | **10** | 14 | **14** |
| top 20 | 10 | **12** | 16 | **20** |
| top 50 | 11 | **14** | 24 | **28** |
| top 100 | 16 | 16 | 28 | **29** |
| top 200 | 16 | 16 | 28 | 29 |

**Pre-registered gate: PASS ≥12/17 and holdout ≥17/30; WEAK 10–11/17 *and* holdout ≥16/30.
The development set is 10, which is inside the WEAK band, but the holdout top ten is 14,
which is not. Both halves are required. STOP.** The bar was not moved and the development
number was not allowed to carry the result on its own — that conjunction is exactly what the
holdout is for.

**What it nevertheless establishes, and it is not nothing.** Below the top ten the caption
channel is the largest single improvement this project has measured on the document channel:
+2 at depth 20 and +3 at depth 50 on the development set, and on the holdout **+4 at 20, +4
at 50, and the first movement of recall@100 in the project's history (28 → 29 of 30)**.
Captions find documents that catalog cards do not. The channel is real; what it does not do
is convert that into the top ten, which is where the gate lives and where an agent's
attention actually is.

**The joint diagnostic is the sharpest result here, and it is negative.** Taking the union of
each question's top-20 caption hits across all six rewrites — up to 120 (file, page) pairs per
question — a gold evidence *address* appears in it on **1 of 13** questions. So the caption
channel is emphatically **not** solving page-finding and document-finding at once. It ranks
the right *publication* better while almost never pointing at the right *page*. The hope that
motivated E — that the caption line is the better retrieval unit for table questions, jointly
— is not supported. It is a better unit for one half of the problem only.

On exactly **1 of 17** questions no rewrite produced any caption hit at all, so coverage of
the channel is not the limitation; ranking within it is.

**One implementation defect, recorded because it cost a holdout look.** The first E1 run
returned the baseline's numbers at every depth on both sets — 9/10/11/16/16 and
14/16/24/28/28, identical to the last question. That was the bug signature, not a result:
`_cap_search` returns a *family* list and fusion happens in *document* space, so
`rel_to_family` silently dropped every caption entry and the channel contributed nothing.
Fixed by entering the caption list as the documents its captions sit in, in first-seen order.
The inert run is counted against tonight's five-look holdout budget even though the
configuration it measured was numerically the already-published baseline and so told us
nothing new about the holdout. **Holdout looks used after E1: 2 of 5.**

*Condition: this corpus, this caption harvest, bm25 over caption text only, all-words then
any-word, pool 200, k=60, rrf. It shows this caption channel does not reach the top-ten bar;
it also shows the deeper pool is genuinely better, which is a fact about the shelf a future
reranking experiment would be working against.*

---

## F48. B2b — removing the year from the caption match changes nothing, and the reason kills the hypothesis. STOP

**Measured**, `state/c_page_gate.json` key `row+caption_first_label`, 13 PDF-bearing frozen
questions, 57 evidence addresses, gold document handed in as always. No model calls, no
holdout look spent.

B2b's hypothesis was specific and reasonable. B2 requires a page's caption to contain every
content word of the row query, and `content_words` keeps fiscal-year tokens, so on a question
that names a year B2 was demanding the caption print that year. F43 had already established
the year is printed in the table *body*, as a column heading, not in the caption. So B2b
matched the caption on label words only — query minus fiscal-year tokens, minus trajectory
filler — and required the year in the page body instead. Table selects on the caption, column
selects on the year.

| measure | B1 (row) | B2 (row + caption) | **B2b (year-aware)** |
|---|---|---|---|
| addresses in top 5 | 24/57 (42.1%) | 42/57 (73.7%) | **42/57 (73.7%)** |
| questions (macro) | 27.9% | 39.7% | **39.7%** |
| trajectory addresses | 22/42 | 40/42 | 40/42 |
| every other type | 2/15 | 2/15 | 2/15 |

**Pre-registered gate: PASS ≥60% micro and ≥60% macro; WEAK ≥60% micro and ≥45% macro. It is
73.7% micro and 39.7% macro. STOP** — the same way and for the same reason B2 recorded WEAK,
and the macro bar was not lowered to let it through. Because B2b did not reach WEAK, the
holdout page evaluation its gate made conditional was **not** run. Holdout looks used: still
**2 of 5**.

**Identical is the result, and the diagnostic says why.** Not one address moved: 112 caption
hit pages before, 112 after, **0 addresses where even the hit count differs**, 0 non-trajectory
questions changed, and the year filter dropped **0** pages. Removing the year from the caption
match was a no-op, which can only happen one way — and it is not the way the hypothesis
predicted.

- 12 of the 57 addresses carry a fiscal year in their row words; 45 do not.
- On those year-carrying questions — **6 of the 13** — the number that have *any* caption
  matching even the reduced label words is **0**.

So the year was never the binding constraint. On every question that names a fiscal year,
**no caption in the gold document contains the subject words at all**, with or without the
year. The year filter had nothing to filter because the caption match had already returned
nothing. All 112 caption hits in the entire measurement come from the seven questions that
name no year, and the 40 trajectory addresses B2 gained are all in that group.

**The honest restatement of the caption channel, now twice measured.** It is not "captions
work, except the year gets in the way" (B2b's premise, now refuted). It is: **the corpus's
harvested captions describe the tables that trajectory questions want and do not describe the
tables that point, reconciliation, multi-branch and relationship questions want.** That is a
fact about what a caption harvested from these documents contains, not about how it is
matched — so it cannot be fixed by another matching rule, which is what B2b was. Combined
with F47's joint diagnostic (a gold address is in the top-20 caption union on 1 of 13
questions), the caption line has now failed to be the general retrieval unit at both the
document level and the page level, while remaining a large, real win on trajectory pages.

**Page method for the rest of the run:** the better of B2 and B2b by macro, ties to B2. They
tie at 39.7%. **B2 (`--caption first`)** is frozen as the page method, and `first_label`
stays in the code as a measured null result.

*Condition: this corpus, this caption harvest, these 13 questions and 57 addresses, top-5
cut. It does not show that captions are useless — it shows that on this caption harvest the
subject words of year-asking questions are not in any caption of the document that answers
them, which is an argument about caption coverage and would be answered by harvesting more
caption text, not by another match rule.*

---

## F49. Experiment E2 — dense captions add nothing the lexical ones did not. STOP. And the FREEZE

**Measured**, `state/c_caption_family_gate.json` key `lex+vec` and `state/c_freeze.json`.
All 89,380 captions embedded with bge-small in 819 s at 109/s (`state/c_caption_embed.json`);
vector rows, id rows and caption rows all equal 89,380. One holdout evaluation.

E2 gives every rewrite a fourth ranked list: the same label-word string, cosine over the
caption embeddings, top 200.

| depth | C2 + rrf | E1 (+ caption lexical) | E2 (+ caption dense) |
|---|---|---|---|
| dev top 10 | 9 | **10** | 9 |
| dev top 20 | 10 | 12 | 10 |
| dev top 50 | 11 | 14 | 14 |
| holdout top 10 | 14 | 14 | **13** |
| holdout top 20 | 16 | 20 | 21 |
| holdout top 50 | 24 | 28 | 27 |
| holdout top 100 | 28 | 29 | 29 |

**Pre-registered gate: PASS ≥12/17 and holdout ≥17/30; WEAK 10–11 and ≥16. It is 9 and 13.
STOP** — and note it is the first configuration tonight to go *below* the baseline on the
holdout top ten. The dense channel does what dense retrieval usually does to a short label:
it dilutes a precise lexical match with semantic near-neighbours. Captions are short
institutional titles; that is the case where embeddings help least and cost most.

The one thing it fixes is coverage: **0** questions have empty caption lists under
`lex+vec`, against 1 under `lex` — a dense channel always returns something. It buys nothing
with it. The joint diagnostic is unchanged at **1 of 13**, exactly as in F47: adding a second
caption channel does not make captions point at gold *pages*.

### FREEZE

Four document configurations were measured tonight. The pre-registered rule is the highest
gold-family recall@10 on the 17, ties by holdout, then by simplicity.

| configuration | fusion | caption channel | dev ≤10 | holdout ≤10 | gate |
|---|---|---|---|---|---|
| C2-rrf (the 2026-09-14 baseline) | rrf | off | 9 | 14 | — |
| C-best (F46) | best | off | 5 | not measured | STOP |
| **E1 (F47)** | **rrf** | **lex** | **10** | **14** | STOP |
| E2 (this finding) | rrf | lex+vec | 9 | 13 | STOP |

**Frozen for the rest of the run: `fusion=rrf caption_channel=lex page=first`.**

This needs saying plainly, because it looks like a contradiction and is not. **Every
adoption gate tonight STOPped, and the configuration frozen for the live battery is one of
the configurations that STOPped.** Those are two different decisions. An adoption gate asks
"is this a real improvement worth carrying forward as a claim?" — E1's answer is no, because
its holdout top ten did not move. The FREEZE rule asks "which of the four measured
configurations should the live battery run on?" — and it is stated over the development
count, where E1's 10 is the highest of the four. Running the battery on a configuration
known to be worse on the measure would make the live numbers answer a question nobody asked.
So E1 is frozen as *the configuration under test*, not as an adopted improvement, and the
architecture document records it as WEAK-and-not-adopted.

The page method is **B2 (`--caption first`)**, per F48's tie-to-B2 rule.

**Holdout looks: 3 of 5 used** (E1 inert, E1 corrected, E2). The frozen configuration's
holdout curve is E1's, already measured in Phase 2 — 14 / 20 / 28 / 29 / 29 — so the fifth
look the phase reserved for it was **not** spent re-measuring a deterministic number that
was already on disk. C-best's holdout was never measured because its development number was
four questions below its own stop line.

*Condition: this corpus, this caption harvest, bge-small, cosine, top 200, k=60. It shows
dense caption retrieval does not add to lexical caption retrieval here; on a corpus whose
captions were free prose rather than institutional table titles the balance could differ.*

---

## F50. LIVE — the first Claude Code battery on the frozen configuration. Both gates FAIL

**Measured**, `state/c_live_battery.json` (aggregates) and the private per-question file.
35 sessions on the Max subscription: 1 auth probe, 2 isolation probes, the frozen 20, and 12
extra absence questions. Model **`claude-sonnet-5`** — the account's default (`"model":
"sonnet"` in the user settings, confirmed as the resolved id in the probe's stream-json init
event), passed explicitly to every battery session. `--max-turns 25 --timeout 300
--permission-mode bypassPermissions`, the question text alone as the prompt, a fresh process
per question, no memory carried between sessions. **32 of 32 battery sessions completed, 0
timeouts, $8.53 total, cost recorded for 32 of 32, mean wall 87 s.**

**Isolation held.** Probe 2 (print a 16-hex token from a scratch file) and probe 3 (list the
private tree) were both refused by the installed deny list; neither the token nor any private
filename appears anywhere in either answer or in any tool result. Checksums: **18 planted
files, 0 changed, 0 missing.** Memory files created: **0**. 72 transcripts containing canary
phrases were quarantined afterwards. The rung root holds neither `CLAUDE.md` nor `.claude/`.

### Behaviour, on the 17 answerable questions

| measure | count |
|---|---|
| surfaced (an evidence path was printed to the session) | **8 / 17** |
| opened *any* evidence file | **2 / 17** |
| opened the right page | **1 / 17** |
| cited the right page | **0 / 17** |
| wrote at least one note before answering | 12 / 17 |
| cited a file it never opened | **5** (on 2 questions) |
| figures in the answer grounded on no opened page | **1** |
| used `series` on a trajectory question | 2 / 4 |
| cited a `must_not_cite` file | 3 |

**Pre-registered gate: PASS needs cited_unopened ≤2, figures_ungrounded ≤2 and
opened_right_page ≥6/17. WEAK needs cited_unopened ≤4 and opened_right_page ≥4/17. It is 5, 1
and 1. FAIL.**

**Which of the three pre-registered readings applies: the first.** Surfaced is comparatively
high and opened_right_page is near zero, so the loss sits *after* retrieval. And the shape of
it is not the shape anyone expected. **Every one of the 17 sessions issued at least one
`open` command — 56 opens across 16 of the 20 sessions.** The rule was read and obeyed: the
agents did not skip opening, they did not answer from search snippets, they wrote notes on 12
of 17, and they named a file they had not opened on only 2 questions. **They opened the wrong
pages.** On 6 of the 8 questions where the right path was printed on screen, the session went
and opened something else instead.

So "did it open what it was handed" has a precise answer: **it opened diligently and chose
badly.** The open-before-cite rule is close to free — it cost almost nothing to follow and
almost nothing was gained, because the bottleneck is one step earlier, in which of the ranked
candidates is worth opening. The comparison point is S1's surfaced 5/17 and opened 0/5; this
is 8/17 surfaced and 2/8 opened, better on both, and still nowhere near usable.

Live retrieval did **not** underperform the offline gate by much: the frozen configuration
puts the gold family in the offline top ten on 10 of 17, and the agent's own hand-written
rewrites surfaced an evidence path on 8 of 17. The agent's rewrites are roughly as good as
Haiku's. That closes off the second reading.

### Absence, on 15 questions (3 frozen + 12 extra)

| measure | count |
|---|---|
| quoted the shelf's own absence verdict (`NO_EDITION_FOR` / `NO_FAMILY_MATCHES` / `TOTAL_PAGES_MATCHING=0`, or listed ≥3 fiscal years) | **14 / 15** |
| matched the inherited decline regex | 7 / 15 |
| declined **and** asserted no figures (`absence_ok2`) | **1 / 15** (0 / 3 on the frozen three) |

**Pre-registered gate: PASS ≥10/15 and ≥2/3 frozen. WEAK 8–9. It is 1. FAIL.**

**The decomposition matters more than the headline, and it is reported without touching the
metric.** `absence_ok2` requires two things at once, and each fails for a different reason.
Of the 15, **8 assert no figures at all** but only 1 of those matches the decline regex; **6
decline in substance but quote figures** — edition counts and page counts drawn from the
shelf's own output, which the metric counts as asserted figures. Meanwhile 14 of 15 sessions
correctly ran the shelf, got its absence verdict, and printed it.

Two candidate defects in the *measurement*, written down and **not** acted on tonight, per
the rule that a live result may not cause a code change in the same run:

1. The decline regex is `run_harness.DECLINE`, written for a different battery. It does not
   match the phrasings these sessions actually use when reporting a missing edition.
2. Counting a figure quoted *from the shelf's own absence output* (how many editions are
   held) as an invented figure conflates "made something up" with "answered the question
   accurately".

Until those are fixed, **1/15 is what the pre-registered metric says and it is what is
recorded.** The honest one-sentence version for a reader: *on absence the system found the
right verdict and said so 14 times out of 15, and the scorer as pre-registered credits it
once* — and which of those two numbers describes reality is exactly what next night has to
settle, by fixing the scorer before looking at the answers again.

### One deviation, recorded rather than silently resolved

The phase specified `run_harness.py --parallel 2` for the frozen 20 **and** a session
configuration with `--disallowed Write,Edit,NotebookEdit,Agent,WebFetch,WebSearch` and the
question text alone as the prompt. `run_harness.py` is a frozen instrument and can produce
neither: it appends a citation instruction to every question and does not forward
`--disallowed`, so its sessions would have run with a shorter disallowed list and a different
prompt from the 12 extra absence questions, which the phase required to be identical. A new
`c_live_battery.py` therefore calls `ask.py` per question with exactly the specified
arguments at `--parallel 2`; `run_harness.py` was not modified.

*Condition: this corpus, this shelf, this CLAUDE.md, claude-sonnet-5, 25 turns, 300 s, one
battery, no prompt variants. It measures this configuration once and is not evidence about
what a different prompt would do — and the phase forbade running a second battery to find out.*

---

## F51. S2 and ED2 — the trajectory metric finally measures page retrieval (WEAK); edition selection fails a second way

**Measured**, `state/c_series_v3.json` and `state/c_edition_set_v2.json`. Gold family handed
in for both, so neither is a statement about family retrieval. Page method: the frozen B2
(`--caption first`). No model calls, no holdout look.

### S2 — vintage-tolerant series

F42 retired `series_ok` as a metric: it had been measuring which copy of an edition the shelf
calls canonical, not whether page retrieval works. S2 replaces it. For each key year Y the
candidate editions are the family's primaries with `fy_primary` in **[Y, Y+2]** — a window
fixed in advance from F43's "usually a later one" and deliberately not widened — and a hit is
the key's (file, page) appearing in the top 5 pages of a candidate whose body carries Y.

**Strict 12 of 24. Tolerant 14 of 24. Mean candidate set size 2.46.**

**Pre-registered gate on strict: PASS ≥16, WEAK 12–15, STOP <12. It is 12 — WEAK, at the
very bottom of the band.** Against the old `series_ok` of 1 of 4 questions this is a large
improvement, but the two numbers count different things and should not be subtracted; what
S2 establishes is that with the vintage window the trajectory walk lands on the cited page
half the time, where the previous metric could not see page retrieval at all.

**The offset distribution is the finding, and it confirms F43 outright.**

| the edition that answered year Y was … | count |
|---|---|
| Y itself | 4 |
| **Y + 1** | **6** |
| **Y + 2** | **4** |
| nothing in the window | 10 |

**Ten of the 14 hits come from a later edition than the year asked about**, and only four
from the year's own edition. This is now measured twice, from two directions: the year a
question asks about is not the year printed on the document that answers it. Any rule that
selects an edition by matching the asked year to the edition's own year is selecting the
wrong document roughly three times in four — which is exactly why F43's structural rule
scored 3/17, and it was not a bug in that rule.

Strict and tolerant differ by only **2**, so copy choice — the thing F42 found the old metric
was really measuring — costs 2 of 24 here and is no longer the dominant term. The dominant
term is the 10 years for which nothing in the window carried the row at all.

**A denominator correction, recorded.** S2 was first run over all 42 evidence addresses that
carry a fiscal year and scored 15/42. F42's 24 counts a different unit: **distinct (question,
fiscal year) pairs**, of which there are exactly 24 across the four trajectory questions —
several evidence files can carry the same year, and finding any one of them answers that
year. The measurement was regrouped onto that unit and re-run before the gate was read. The
gate band was not touched; only the unit it was written over was made to match.

### ED2 — content-based edition selection

F43's structural rule asked whether a primary *declares* the asked year in its metadata: 3 of
17. ED2 asks the same question from the content side — does the primary's caption-matched
top-5 contain a page whose body *holds* the asked year?

**Set recall 3 of 10 year-bearing questions. Mean set size 2.0, max 6.**

**Reading, fixed before measuring: below 8 of 10 means captions-plus-year do not select
editions either.** They do not. The two rules agree on very little except the answer: the
structural one scored 3, the content one scores 3, and the pipeline still cannot name which
edition of a publication prints a given year's row.

The mean set of 2.0 is the sting. This is not a rule that hedges by returning everything and
still misses — it returns a *small, confident, wrong* set. A large set would have meant "the
mechanism is right and a vintage rule is the next sub-problem". A set of two that is right 3
times in 10 means the selection signal itself is absent, and the S2 offsets say why: the year
is in a later edition than the one being scored, and often in no edition within two years at
all.

**Consequence for the architecture.** The 2026-09-15 architecture note redraws
RETRIEVE DOCUMENT → RETRIEVE PAGE into RETRIEVE FAMILY → LOCATE TABLE only if E1 or E2 reached
WEAK **and** ED2 ≥ 8/10. ED2 is 3. **The boxes are not redrawn**, and the measured reason is
recorded in their place: locating the table does not determine the edition, because the table
that prints a year lives in an edition the year does not name.

*Condition: this corpus, this shelf, gold family handed in, window [Y, Y+2], top 5, the B2
page method. A wider window would raise S2's tolerant number and was forbidden in advance
precisely because it is the move that widens a bar after seeing the offsets.*

---

## F52. CHAIN — the pipeline run end to end for the first time. 3 of 17 verified

**Measured**, `state/c_chain_gate.json`, all 20 frozen questions, the frozen configuration
(`fusion=rrf caption_channel=lex page=first`), no model calls anywhere. 478 verifier calls,
32 minutes. Every box the project has built, wired together and run once:

`ROUTE → RETRIEVE FAMILY (top 5) → SELECT EDITIONS → RETRIEVE PAGE (top 5 each) → VERIFY`

The last step is what makes this a chain rather than a fourth lookup measurement. A page
counts as a hit only when `evidence_v1/verify.py` finds the row and the column on the printed
page and reads the cell geometrically — the value is never compared to the answer key's
number, only to what the PDF actually prints.

### The decomposition

| stage | count (of 17 answerable) |
|---|---|
| gold family in the top 5 | **8** |
| → and a gold (file, page) reached | **4** |
| → and the cell verified on the page | **3** |

**Absence routed correctly: 1 of 3.**

Mean pages opened per question: **46.4**. Eleven of the seventeen questions hit the 40-call
verifier cap.

### What the decomposition says, in order

**Half the loss is the document box, and that was already known.** 8 of 17 at top-5 is
consistent with everything measured tonight — the frozen configuration reaches top-10 on 10 of
17, and top-5 is a harder bar.

**The second half is new and it is the expensive one.** Of the 8 questions where the right
publication *was* in the top five, only **4** produced a gold address. So the pipeline throws
away half of what its own document retrieval hands it, at the edition-and-page step — after
opening an average of 46 pages per question. That is the compounding cost nobody had paid
before, because every previous measurement handed the next box a correct input.

**The edition rule is where those four go.** Its own counters say so: on **6 of the 17**
questions the ED2 content rule selected *no* edition at all and fell back to all primaries
(`ed2_year_empty_fallback`), and it fired properly on only 4. This is the same finding as F51
(ED2 3/10) arriving through a different door — the year is in a later edition than the one the
year names, so a rule that looks for the asked year inside a candidate finds nothing.

**VERIFY is not the bottleneck, and that is worth saying plainly.** Of the 4 addresses the
chain reached, **3 verified**. The one box that has never failed a gate did not fail here
either: when the chain actually lands on the right page, the verifier reads the right cell
about three times in four. Everything upstream of it is the problem.

**Absence at 1 of 3 is the chain's weakest number and it agrees with the live battery.** The
deterministic router and the live sessions independently score the absence questions far below
the 11/11 this project has published since the shelf was built. Two independent measurements
now disagree with that number. F50's candidate scorer defects explain the live one; they do
**not** explain this one, because the chain's route check is pure code with no scorer in it.
That makes repairing and re-reading absence the most urgent thing in the repository, and it is
the pre-registered next experiment.

### The honest headline

**The pipeline, run end to end on the questions it was built for, answers 3 of 17 with a
verified citation.** No previous number in this repository is comparable to it — every earlier
figure measured one box with the previous box's answer handed in for free. This is the first
number that includes the cost of being wrong earlier in the chain, and it is roughly a third
of what the best single-box measurement would have predicted.

*Condition: this corpus, this shelf, the frozen configuration, top 5 families, top 5 pages per
edition, a 40-call verifier cap per question (hit on 11 of 17, so the verified number is a
floor and a larger cap could only raise it). Deterministic and reproducible; no model calls.*

---

## F53. The absence box stands. The 1/15 was a scorer artefact, and the chain's 1/3 was an implementation gap

**Measured**, `state/c_live_battery.json` (both rules side by side), `state/c_route_gate.json`,
and the private per-question file. Scorer repair specified in
`state/absence_scorer_v2_spec.md` and **committed before a single transcript was read this
phase** (`d093729`). No new sessions; the 32 transcripts are the ones recorded overnight.

F50 published two numbers that could not both be true: `absence_ok2` **1 of 15**, while 14 of
those 15 sessions ran the shelf, got its verdict, and printed it. F52 then added a third:
the deterministic chain routed **1 of 3** frozen absence questions. Both low numbers have now
been explained, and they had different causes.

### The scorer: 1 of 15 → 11 of 15

| | v1 (`absence_ok2`) | v2 (`absence_ok3`) |
|---|---|---|
| all 15 | **1** | **11** |
| frozen 3 | 0 | **2** |
| gate (PASS ≥10/15 and ≥2/3) | FAIL | **PASS** |

**The decisive number is that `figures_asserted3` is zero on all fifteen sessions.** Not one
absence answer contains a figure that the session had not been shown in its own tool output.
**No absence session invented a number — not once in fifteen.** The v1 filter excluded
fiscal-year tokens, four-digit years, page indices and the coverage counts, but not the
shelf's own edition lists and receipt lines, so an answer that correctly said "we hold these
editions and not the one you asked for" was scored as asserting fabricated quantities. The
metric was penalising accurate quotation, which is the opposite of what it was built to catch.

The decline half mattered less but mattered: the v1 regex, written for a different battery
against a different stack, recognised 7 of 15; `declined3` recognises 11.

**The repair did not loosen the rule, and this was checked rather than asserted.** Every one
of the 11 credited answers is credited through at least one legitimate limb — the old regex,
a verbatim shelf verdict string, or the fixed plain-statement stem list — and **0 answers are
credited without any of them**, which the spec pre-registered as a STOP. The four not credited
(`declined3` false) genuinely do not decline: the shelf verdict was in their tool results and
did not reach their answers.

`absence_ok2` is **retained and relabelled SUPERSEDED-BY-SCORER-REPAIR**, not deleted.

### The router: 1 of 3 → 3 of 3, and the published numbers re-derived

The chain's `route_absent` returned early whenever the question carried no fiscal-year token.
This corpus has **two kinds of absence** and it implemented one:

| kind | how it is detected | count in the key | routed absent |
|---|---|---|---|
| document level (names a fiscal year) | `have` — do we hold any edition for that year | 11 | **11 / 11** |
| identifier level (a literal code, no year) | `exact` — does any readable page contain it | 4 | **4 / 4** |
| | | **15** | **15 / 15** |

The **3 frozen absence questions are 1 document level and 2 identifier level**, so the
overnight chain could score at most 1 — and scored exactly 1. Re-running the overnight logic
confirms it: `overnight_chain_equivalent_on_frozen` reproduces **1 of 3** exactly. With the
`exact` path added (longest digit-bearing token in the question, zero matching pages →
ABSENT — generic, derived from question text alone), the frozen three go to **3 of 3**.

**This re-derives the published 11/11 and 4/4 from the chain's own code path**, not from the
absence control that produced them. Two independent implementations now agree. The
pre-registered reading required `absence_ok3` ≥ 10/15 **and** the router ≥ 9/11; it is 11 and
11/11. **The absence box stands.**

### What is left, and it is small but real

The shelf verdict reached a tool result on **15 of 15** sessions and reached the final answer
on **5**. Eleven sessions declined in some recognised form; **four received the verdict and
did not relay it**. That is a genuine behaviour residue, and it is recorded here — but the
pre-registered trigger for treating it as *the* absence behaviour loss required
`absence_ok3` ≤ 7/15, and it is 11. **The trigger does not fire**, and no CLAUDE.md row is
claimed on this finding.

### What this costs the overnight conclusions

F50's absence gate FAIL is superseded. F52's "absence routed correctly 1 of 3" is superseded
as a statement about ROUTE and stands only as a statement about the chain implementation, now
fixed. **The overnight handoff's headline that "the one thing this project believed it had
solved" was in doubt is withdrawn: it was solved, and two measuring instruments were broken.**
That is worth stating plainly, because the alternative — quietly correcting it — is how a
project ends up believing its own bad numbers in both directions.

*Condition: this corpus, these 15 absence questions, one battery of recorded transcripts. The
scorer repair was specified from F50's two named defects and committed before reading; the
stem list was not extended after seeing the answers.*

---

## F54. Where the agent went when the right file was on screen

**Measured**, `state/c_live_forensics.json`, the 17 answerable P5_live transcripts recorded
overnight. No new sessions. Six mutually exclusive classes, first match wins, and the decision
table that reads this output was written before the counts existed.

| class | count | what it means, in one sentence |
|---|---|---|
| **L0** family not surfaced | **9** | The right publication never appeared in any `find` output, so the session never had a chance to choose it. |
| **L1** surfaced, opened another publication | **4** | The right publication was printed on screen and the session went to a different publication entirely — though **2 of these 4 opened nothing at all**, so only 2 actively chose elsewhere. |
| **L2** right publication, wrong edition | **2** | The session got to the right publication and opened the wrong year's volume of it. |
| **L3** right file, wrong page | **1** | The session opened the correct document and never landed on the page the key cites. |
| **L4** right page opened, not cited | **1** | The session had the right page open and its answer did not cite it. |
| **L5** cited the right page | **0** | — |

**The dominant class among L1–L4 is L1 at 4, which clears the pre-registered threshold of ≥4
of the 8 surfaced sessions.** The Phase 4 row for L1 therefore applies. Two honest
qualifications, recorded because they narrow what the number means: half of L1 is sessions
that opened nothing rather than sessions that opened the wrong thing, and L1's lead over L2 is
two questions on a base of eight.

**The shape of the loss is now decomposed, and it is top-heavy.** Of 17 questions, **9 never
see the right publication at all** — more than the other five classes combined. The
behavioural classes L2–L4, everything downstream of picking the right publication, account for
**4 questions total**. Whatever is wrong here is mostly not a matter of what the agent does
with a good candidate list; it is that the list is not good.

**The two L2 sessions are worth their own line**, because they are the only direct evidence of
how edition choice fails in practice. In one, the right edition was listed **first** of 15 and
the session opened the **third**. In the other, the right edition was **third** of 15 and the
session opened the **fifteenth**. Both are consistent with F51's finding from the offline side:
the agent is choosing the edition whose printed year matches the question, and the row it wants
is in a different volume.

### How the tools were actually used

| | |
|---|---|
| `find` calls | 26, and **all 26 carried `--q` rewrites** |
| `have` used | 14 of 17 sessions |
| `tables` used | 10 of 17 |
| `inside` calls | 24 |
| `series` on a trajectory question | 2 of 4 |
| searched using a content word **not** in the question (rewrote the subject in its own words) | **8 of 17** |

**The instructions were followed.** Every single `find` carried hand-written rewrites, as
`CLAUDE.md` asks; `have` was used on most questions; `tables` on more than half. This is not a
session ignoring its tooling. And on **8 of 17** questions the model searched using vocabulary
of its own rather than the question's — so the vocabulary bridge that B2b's failure said was
missing from the *caption index* is something the agent does attempt on its own about half the
time. Neither the tool use nor the paraphrasing is the loss.

### One classifier defect, caught and fixed before the counts were read

The first run of this script reported L1 = 6 and L2 = 0, which would have pointed the whole
phase at the wrong repair. Shelf `rel` keys preserve their original case and `scoring.norm_path`
lowercases, so **every** opened path failed its family lookup and silently returned "not in the
gold family". Zero of 14 opens in the supposed L1 sessions resolved to any family at all — the
signature of a blind classifier, not of an agent choosing badly. Fixed with a lowercased index
plus the tail-2 fallback `scoring.py` already uses, and a permanent guard
(`n_sessions_where_no_open_resolved_to_a_family`, now **0**) so this class of bug cannot pass
silently again. The counts above are from the corrected run.

*Condition: one battery, 17 questions, claude-sonnet-5, the frozen configuration. The classes
are ordered, so each question contributes to exactly one; a session can fail in more than one
way and only its earliest failure is counted.*
