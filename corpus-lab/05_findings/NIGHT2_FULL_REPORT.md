# Night 2 — full report

**Run date:** 2026-09-12, 01:35 → 08:15 (paused 03:50–06:50 at the user's request).
**Deliverable:** this document. The auto-generated grid table lives in `GRID.md`;
everything else needed to understand it is here.
**Written for:** a reader who knows only that we are trying to make Claude Code find
things in a large document folder.

---

## 1. The problem this exists to solve

Sir has a large research folder — roughly 10,000 files, mostly PDFs, on Windows, no git,
driven through terminal Claude Code. When he asks a question about it, Claude misses
material that is demonstrably there, and does so *silently*: it answers confidently
rather than saying it could not find anything. Prompting has been tried and has failed
repeatedly. The question is whether an infrastructure layer underneath the prompting —
an index, a search tool, a policy, an enforcement hook — fixes it.

Night 1 (2026-09-10) produced an answer that turned out to be wrong in an instructive
way. It found that the test repository's `.gitignore` excluded every document directory,
so built-in search saw 495 of 217,527 files and returned "No files found" for material
that existed. It built an index, measured 6/13 canaries found without it versus 12/13
with it, and organised its entire write-up around that.

**That finding does not transfer.** Sir's tree is a plain folder with no git and no
`.gitignore`, so on his machine `grep` and `grep --no-ignore` are the same command and
the finding describes nothing. A root cause had been promoted to a thesis without anyone
checking whether its enabling condition existed on the target.

Night 2's brief was therefore: fix the instruments, build a tree that actually resembles
the target, measure several retrieval stacks against it, and make every claim carry the
condition it depends on.

---

## 2. What was tested, and how

### 2.1 Two corpora — and only one of them speaks to the problem

| | `harness/corpus_15000` | `ra-ship` |
|---|---|---|
| files | 15,010 | 217,681 |
| git | **none at any depth** | git repo, documents `.gitignore`d |
| dependency noise | **0 files excluded** | 213,032 excluded (97.9%) |
| built to represent | **the target** | nothing — it is a convenience fixture |

The harness is a synthetic tree built to resemble sir's drive. Its lack of git was
verified, not assumed: zero `.git` and zero `.gitignore` at any depth. **ra-ship is a
fixture.** Results measured there are evidence about the stacks, not about the problem,
unless the harness agrees.

### 2.2 Two tests per stack

**Canaries** — 18 marker phrases planted in the harness (13 already existed in ra-ship),
each in a known file. The session is given the exact string and asked which file contains
it. This measures *can the tool find something you can already quote*.

The pass-2 phrases were deliberately built with **no shared token and no shared
structural shape** — a regulatory notification number, a statistical series ID, a
person's name, a mistyped acronym, a value-plus-unit, a lowercase slug, an office code
with slashes, a DOI, and so on. Pass 1 had failed this: 11 of its 13 phrases matched
`prefix-8hex-6digits`, so one regex swept the whole set. Coverage was mandated across 12
cases — deep inside a 200+ page PDF (recording physical page index *and* printed page
label separately), a DOCX, an XLSX cell, a CSV row, a JSON, a stale README, inside a ZIP,
depth 6+, top level, a large folder, a file whose name lies about its content, and a
near-duplicate pair where only one copy carries the phrase. All 12 were covered.

**Questions** — a frozen sample of 20 from a 135-question answer key, spanning
trajectory, point lookup, absence, multi-branch, reconciliation, stale-doc,
name/content-mismatch, canonical-duplicate and relationship types. Scored on which
*evidence files* the session actually reached, against the key. This measures the real
job.

Every question ran in its **own headless session**. Sessions are never batched: if they
shared context, question 5 would benefit from what question 2 found and recall would mean
nothing. 189 sessions were run in total.

### 2.3 The six stacks

| stack | what it actually is |
|---|---|
| **S0** | stock Claude Code — `Grep` (ripgrep), `Glob`, `Read`, `Bash`. Nothing installed. |
| **S1** | SQLite **FTS5** page index (`index_build.py`), queried via `corpus_search.py`. A `CLAUDE.md` tells the agent it exists and to use it first. **Nothing enforced.** |
| **S2** | The same index, plus `hook_frontdoor.py` — a `PreToolUse` hook that denies `Grep`/`Glob` and Bash `grep\|rg\|find\|fd`, redirecting to the index. |
| **S3** | FTS5 + local embeddings: **LanceDB** + **fastembed** running `BAAI/bge-small-en-v1.5` (ONNX, CPU), hybrid BM25+vector with RRF. |
| **S4** | **pdf-mcp 3.1.0** — an off-the-shelf MCP server (fastmcp, pdfplumber, pypdfium2) exposing `pdf_corpus_warm`, `pdf_corpus_search`, `pdf_read_pages`. |
| **S5** | **Recoll** — a desktop search application over Xapian BM25. |

S1 vs S2 is the designed experiment: **is telling the agent enough, or does it have to be
forced?**

---

## 3. Fixing the instruments first

Night 1's numbers were untrustworthy for reasons that had nothing to do with retrieval.
Ten instrument defects were fixed before any measurement. Five of them mattered:

**The scorer accepted a bare filename.** A hit was scored if the answer contained the
filename and it was over 8 characters. One canary lives in `README.md` — 9 characters —
so any answer mentioning any README in a 217,527-file tree scored as finding it. Fixed to
require the full relative path or its last two segments. Re-scoring night 1 showed the
loophole **never actually fired** (every hit matched on full path), but it would have on
pass 2, whose targets have far more generic names.

**Cost totals were never comparable.** A timed-out session reports `cost_usd: null` and
silently drops out of the sum, so whichever stack flailed more looked cheaper. Night 1's
"half the cost" compared a sum over 8 sessions to a sum over 12. Every cost figure now
carries an explicit **n-of-m** and refuses comparison across different n.

**The baseline was not a baseline.** `stack.py setup --stack s0_baseline` wrote a
`CLAUDE.md`, so night 1's S0 and S2 differed by two things at once. S0 now installs
nothing.

**Sessions could silently edit the corpus.** They run under `bypassPermissions`. Now
every measurement session passes `--disallowedTools Write,Edit,NotebookEdit`, and a
sha256 manifest of every planted file is verified before *and* after every battery.
Verify, never restore — a restore would hide the thing the check exists to catch.

**Timing counted laptop sleep.** `wall_s` used `time.time()`. Now `time.monotonic()`,
with suspend detected by divergence between the wall clock and `perf_counter` (the
spec's literal rule — wall minus summed inter-event gaps — can never fire, because the
gaps are measured live and sum to the wall by construction).

### 3.1 Five bugs found during the run that invalidated earlier work

1. **`claude.cmd` truncates multi-line prompts.** It is a cmd.exe wrapper whose `%*`
   expansion stops at the first newline in an argument, so any prompt containing `\n`
   silently lost `--output-format stream-json`. The session then ran in text mode and
   returned prose with **exit code 0 and empty stderr**. This was night 1's undiagnosed
   failure. It was never the corpus root: ra-ship ran single-line canary questions and
   worked; `run_harness.py` appends `"\n\nCite the exact file paths…"` to every question,
   so 100% of harness questions broke and 0% of ra-ship canary questions did. Verified
   across 8 prompt shapes — 8/8 clean via `claude.exe`, 2/8 broken via the `.cmd`.
   **Every harness cell night 1 produced was void because of this.**

2. **`Read(**/_private/**)` provides no protection at all.** Under `bypassPermissions` a
   `Read()` deny binds **only** with an absolute path prefix; relative globs fail open
   silently. The first sandbox proof read the answer key manifest in full on *both*
   corpora. `Bash()` patterns match the command string, so relative forms do bind there —
   which is why the first proof showed Bash refusals alongside successful Reads and
   looked partially secure.

3. **Sessions write `memory/` despite `--disallowedTools Write`.** Memory persistence
   does not go through those tools. One battery could hand notes to the next, inflating
   whichever ran second. The driver now quarantines memory files either side of every
   cell.

4. **The question-id derivation silently lost results.** Ids were built from the phrase;
   pass 2's deliberately mixed phrase shapes produced ids containing `/`, which `Path`
   read as a non-existent subdirectory. Four results were never written and the battery
   reported **12/14** — the denominator had fallen from 18 to 14 and nothing said so.
   This is exactly the silent-partial-completion failure the run exists to measure,
   occurring inside the measuring instrument, and it surfaced only because the phrase
   design was adversarial enough to trigger it.

5. **The answer key was reachable from a test session.** 30 night-1 transcripts under
   ra-ship's `.claude/projects` key quoted all 13 canary phrases — and that is precisely
   the key every ra-ship measurement session runs under, because ra-ship does not move.
   Quarantined, and the store denied by absolute path. Final proof: **7 of 7 escape
   routes blocked on both corpora**, refusals captured verbatim.

---

## 4. Results

### 4.1 The grid

| stack | harness canary | harness questions | ra-ship canary | question cost (n/m) | tool calls (canary) |
|---|---|---|---|---|---|
| **S0** baseline | **15/17** | **0.167** (12/20 zero, 21 forbidden, absence 0/3) | **4/12** | $12.5381 (14/20) | 92 |
| **S1** policy | **17/17** | **0.176** (13/20 zero, 19 forbidden, absence 0/3) | not run | $2.8934 (15/20) | 25 |
| **S2** hook | **17/17** | **0.118** (14/20 zero, 16 forbidden, absence 0/3) | not run | $2.6832 (16/20) | 21 |
| **S3** hybrid | — | — | — | not built | — |
| **S4** pdf-mcp | — | — | — | install gate failed | — |
| **S5** Recoll | — | — | — | no headless installer | — |

Two canaries are excluded from the headline as structurally unreachable: one under
`site-packages` (the indexer excludes dependency directories by design — grep reaches it,
an index cannot) and one inside a ZIP (the indexer does not descend into archives, and
grep cannot read a compressed member either, so **no stack here can reach it**).

### 4.2 Finding one — stock search is fine on a plain folder

Stock Claude Code, hunting exact planted strings:

- **harness (no git): 15 of 17**, 29.6 s mean
- **ra-ship (documents gitignored): 4 of 12**, 153.1 s mean

Same stack, same scorer, same night. The gap is the fixture. Night 1 read the ra-ship
number as proof that built-in search is broken; on a plain folder — which is what the
target is — it already finds 15 of 17 in under half a minute each.

### 4.3 Finding two — telling works, forcing adds nothing

A single line in `CLAUDE.md` moved index adoption from **0 of 38 sessions to 38 of 38**.

| | S0 (nothing) | S1 (told) |
|---|---|---|
| sessions using `corpus_search` | 0 / 38 | **38 / 38** |
| `Grep` calls | 79 | **0** |
| `Read` calls | 145 | **0** |
| `Glob` calls | 80 | 6 |
| canary recall | 15/17, 92 calls | **17/17, 25 calls** |
| question cost | $12.54 | **$2.89** |

S2's hook then enforced a behaviour the agent had already adopted voluntarily. Canary
recall identical (17/17), evidence contact identical (0 of 17), cost differs by 7%, tool
calls by four. S2's question recall reads lower (0.118 vs 0.176), but on n=20 that gap is
**not safely outside sampling noise and I am not claiming S2 is worse.**

The one real difference: S2 removes a fallback. S0, unrestricted, made the *most*
evidence contact of the three by ignoring rankers and crawling. S2 forecloses that.

*Condition: one model (claude-sonnet-5), one prompt shape, 38 sessions per stack. A
different model, or one under heavier task pressure, may not comply as readily. The
concern that motivated the hook is not disproven in general, only unobserved here.*

### 4.4 Finding three — none of it moved question recall

0.167 → 0.176 → 0.118. All three inside noise of each other. Absence questions **0 of 3
in every stack**: when the honest answer was "not in the corpus", every stack invented
one instead. Adding the index made the work five times cheaper and four times fewer tool
calls, and made the actual job no better.

S0's $12.54 is worth explaining: across 20 questions it issued 200 Bash, 145 Read, 80
Glob and 44 Grep calls — and also `Agent` (11), `ScheduleWakeup`, `SendMessage`,
`ListAgents` and `Monitor`. The unguided baseline began spawning subagents and scheduling
wakeups instead of reading documents.

---

## 5. Why recall is stuck — the diagnosis

Run against data already on disk. No sessions, no cost. Three places the failure could
live:

**A. Ingestion — not the problem.** All **64 of 64** evidence files referenced by the 20
questions are in the index with status `indexed`.

> **SUPERSEDED 2026-09-12 (P9).** Recall numbers and this finding's strength are
> superseded by the re-score from tool results — see `state/rescore_from_results.json`.

**B. Lexical ranking — this is the failure.** For the 17 questions whose evidence is
fully indexed, running the question's own content words as a BM25 query returns the
correct evidence file in the top 50 hits **zero times**. Not once.

**B2. And it is ranking, not vocabulary.** The evidence files *do* contain the question's
words — mean **38.9%** of the question's content words appear in the evidence file,
median 33.3%, only 1 of 27 sampled files contains none. The words are there, and BM25
ranks thousands of the other 1.2 million pages above the right one.

**C. The agents corroborate it independently.** S1 and S2, which route every question
through the index, opened a correct evidence file on **0 of 17** questions. S0, which
wanders instead of searching, managed **4 of 17**. Worse tooling, better evidence
contact — which only makes sense if the ranker is the bottleneck.

**Consequence.** S4 (pdfplumber text search) and S5 (Xapian BM25) are both lexical and
share the failing component, so neither would have moved this number. That is now
evidence rather than an assumption. The stack that attacks this directly is S3,
embeddings — and S3 is the one that cannot be built on this machine.

*Caveat: the probe in B used an OR of up to 12 content words, cruder than an agent's
query. It is a proxy. Finding C is not a proxy — it is what real sessions did — and the
two agree.*

---

## 6. A ceiling no stack here can clear

The rung-15000 index: 15,010 discovered, **13,634 indexed**, 32 failed (18 encrypted, 14
parser), 1,344 unsupported or empty — **of which 1,211 are image-only PDFs with no text
layer** — 1,206,260 pages, 782 s, 6.97 GB. The accounting identity closes exactly.

**1,211 scanned PDFs is 8% of the tree that no text index and no grep can reach without
OCR.** That hole is larger than every difference between stacks measured here. *Condition:
the tree contains scanned documents. The target is PDF-heavy, so this very likely
transfers and should be checked against the real folder before any stack is chosen.*

---

## 7. Why three stacks did not run

**S3 — not built.** fastembed `bge-small-en-v1.5` measured at **8.2 pages/s** on CPU
against 614,150 ra-ship pages and 1,206,260 harness pages: a 20.8-hour build for the
smaller of the two, with no GPU available. Not a tuning problem.

**S4 — install gate failed, on two independent grounds.** `pdf_corpus_warm` and
`pdf_corpus_search` accept neither a directory nor a glob (root → `"not a .pdf file: no
extension"`; `root/**/*.pdf` → `"file not found"`), so a caller must enumerate all **9,942
PDFs** explicitly — which the S4 hook forbids the agent from doing, so the front door
cannot be opened from inside a session. And warming **five small PDFs** (32 KB–1.6 MB)
took **415 seconds** and returned `docs:[]` with three still unprocessed: ~200 s per small
PDF, ~23 days for the rung. `pytesseract` is a dependency and the rung holds 1,211
image-only PDFs, so OCR is the likely cause.

**S5 — no headless install path exists.** Absent from PATH and Program Files; absent from
winget and msstore, and from a search for xapian; the vendor's Windows page carries no
`.exe`, `.msi` or `.msix` link at all, and the only linked downloads directory holds GPL
source tarballs. Distribution is an interactive install, which the brief rules dead.
Nothing was downloaded or installed.

---

## 8. Fixture-specific — does not transfer

Findings whose enabling condition is **absent** on the target. None of these may appear in
a headline or a recommendation.

1. **The `.gitignore` root cause** — night 1's entire thesis. *Condition: the tree is a
   git repo with a `.gitignore` covering the documents.* The harness has neither, and the
   direct measurement is 15/17 vs 4/12.
2. **The venv/model-cache bulk** — 97.9% of ra-ship is dependency noise; the harness walk
   excluded **0 of 15,010**. So ra-ship's "3,872 indexed files" is not the corpus, it is
   the 1.8% left after the noise filter.
3. **The `claude.cmd` newline bug** — an *instrument* bug. Sir drives Claude Code
   interactively and never hits it. Recorded because it voided night 1's harness half.
4. **The deny-rule, transcript and memory work** — properties of running a blind
   measurement, not of retrieval. They matter for trusting these numbers and for anyone
   building a rig like this; they say nothing about whether an index helps find a table.

---

## 9. Limitations — what would make me doubt this

- **n=20 questions.** The S1/S2 gap (0.176 vs 0.118) is not outside noise. Differences
  below roughly 0.05 in these tables should not be read as real.
- **One model, one prompt shape.** Everything about the telling-vs-forcing result is
  conditional on claude-sonnet-5 complying with a `CLAUDE.md` instruction.
- **S1 and S2 were never run on ra-ship** (~$4 of work). Two grid cells read "not run".
  My judgement, not the brief's: ra-ship is a fixture whose defining property is absent
  on the target.
- **The `retrieval` column is not comparable across stacks.** `files_opened[]` is
  reconstructed from tool-call *inputs*, so a path appearing only in a tool *result* —
  normal for an index stack answering from snippets — is invisible to it.
- **The harness is synthetic.** It was built to resemble the target; it is not the target.
  Its determinism check had already failed (6,060 of 6,064 files reproduced), which is why
  regeneration was banned for this run.

---

## 10. State and cost

Nothing is running. No stack is installed in either corpus. All 31 planted files verified
unchanged by sha256 before and after every battery. 189 measurement sessions on disk.

**~$31 total, ~$28 of it night 2.** Canary batteries $1–2 each; question batteries
$2.68–$12.54.

Everything is committed. `state/progress.jsonl` holds one JSON line per step of the whole
run; `RESUME.md` is enough for a fresh session to continue from.

---

## 11. What I'd look at first

1. **Ranking, not the engine.** The right words are in the right files and BM25 still
   buries them under 1.2M pages. Swapping one lexical engine for another cannot fix that —
   two such swaps already failed for unrelated reasons. What is unmeasured: shrinking the
   candidate set before ranking using structure or metadata, reranking a large top-k, or
   indexing at a coarser unit than a single page so each unit carries more signal.
2. **Count the scanned PDFs in the real folder.** 8% of the harness is image-only and
   unreachable by anything tested here. If the real tree is similar, that hole outranks
   every stack choice on this page.
3. **The absence failure is not a retrieval problem.** 0 of 3 in all three stacks: when
   the honest answer was "not in the corpus", every stack invented one instead. Nothing
   measured here addresses it, and it is the failure mode that makes silent omission
   dangerous rather than merely annoying.
