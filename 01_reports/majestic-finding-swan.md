# Overnight Retrieval-Stack Bake-Off — Executable Runbook

> **This document is the source of truth for the run.** It is written to be picked up
> cold by a fresh context at any hour of the night. If you are a new session reading
> this: go to §4 "How to resume", read `corpus-lab/state/run_state.json`, and continue
> from the first phase whose `status` is not `done`.

---

## 1. Context

**The problem.** Sir (econ professor) `cd`s into a very large research folder, runs Claude
Code in the terminal, and asks vague questions ("how does Pakistan's X trajectory look").
On big corpora the agent silently misses material — it skips files, drops the links between
documents, and degrades further the deeper it goes. He has hit this 4-5 times, most recently
on the Pakistan auto-policy work. Straightforward agentic use and many rounds of prompt
engineering both hit the same wall, so **prompting is not the answer**. What is missing is a
retrieval layer that lets an agent survive a large corpus.

**The end state we are building toward.** Point it at any folder — hundreds of folders,
thousands of files, no pre-organisation, a layout nobody has seen. Ask something vague and
niche. The agent goes straight to the exact material wherever it is buried, pulls from
several sources at once, and answers — including the page and table inside a 600-page PDF,
not just the filename. Portable to any repo. Lives entirely inside Claude Code: no separate
app, no server started by hand, no step anyone has to remember.

**What tonight is for.** Four deep-research passes are done and reviewed. They name many
candidate tools but **nothing has been tested on our own setup**. Tonight converts research
into evidence: build the measurement rig, run a bake-off of candidate stacks against two
corpora with ground truth, and produce a decision memo that says which stack to build, with
numbers behind it.

**Tonight is not the build.** It is the experiment that decides the build.

---

## 2. Success criteria for the morning

The run has succeeded if, at 08:00, `corpus-lab/05_findings/DECISION_MEMO.md` answers all
five of these with numbers, not opinions:

1. **Does the failure reproduce here?** Do Claude Code's built-in Glob/Grep actually miss
   material on a 217k-file tree on this machine — and by how much? (This is what justifies
   building anything, and it is the single most valuable thing to be able to show sir.)
2. **Which delivery mechanism holds?** Does a `PreToolUse` deny on Grep|Glob actually fire
   and redirect in this Claude Code version, headless and interactive? MCP vs hook vs
   CLAUDE.md, settled by test rather than by report.
3. **Which stack wins?** Ranked, on recall / precision / answer correctness / wall-clock /
   disk, over both corpora, at multiple corpus sizes.
4. **Where does it break?** The degradation curve across the 500 → 2k → 5k (→ 15k) rungs.
   Not pass/fail — the size at which each stack starts losing material.
5. **What does deep extraction cost?** Measured pages/sec for the extraction options, and
   the extrapolated hours to process sir's real tree. (Listed as unaddressed by both
   round-two reports.)

Secondary, if time allows: how each stack handles the hardest question classes —
`trajectory` (same series across ten years of differently-formatted PDFs), `reconciliation`,
and `absence` (the correct answer is "not in the corpus", which catches invention).

---

## 3. Hard constraints

| # | Constraint | Consequence for the design |
|---|---|---|
| C1 | **Hard stop 08:00.** Whatever is unfinished is deferred to another session. | Every phase has a timeout. Orchestrator checks the clock before starting any phase and skips ahead rather than overrunning. |
| C2 | **No questions.** Operator is asleep and unavailable. | Every ambiguity is resolved by a documented default in §9. Never block on input. Log the decision and continue. |
| C3 | **No copies of the big corpora.** SSD space is not to be wasted. | ra-ship and the harness rungs are **read-only sources**. Every index, cache and artifact is written to `corpus-lab/`. Nothing is duplicated. (428 GB free, so this is a discipline rule, not a capacity one.) |
| C4 | **Do not modify the source trees.** | The only writes into `ra-ship` are `.claude/settings.json` and `CLAUDE.md` — a few KB, git-revertible, and reverted by teardown after every stack. Nothing at all is written into `harness/corpus_*`. See §7.3. |
| C5 | **Zero cost.** Free/open tools only. | Anything with a paid tier, API cost, or revenue-threshold licence is excluded (kills LlamaParse, GraphRAG, Marker). Model spend on scored runs is capped in §8.4. |
| C6 | **Windows 11 native.** | Anything Linux-only or WSL-dependent is a fallback, not a primary. Path length ≤ 260 chars. Watch for colon-in-filename and case-insensitivity traps. |
| C7 | **Must survive context loss.** | State lives in files, not in conversation. §4. |
| C8 | **Canaries must not be invalidated.** | The 13 planted canaries in ra-ship stay exactly as they are. No re-planting, no mtime changes, no commits. Harness canaries get planted once, before any harness measurement. |

---

## 4. How to resume (read this first if you are a fresh context)

1. Read `C:\Users\Ali\Desktop\corpus-lab\state\run_state.json`. It is the machine state:
   every phase with `status` ∈ `pending | running | done | failed | skipped`, timings, and
   artifact paths.
2. Read `C:\Users\Ali\Desktop\corpus-lab\00_RUNBOOK.md` — a copy of this file, plus an
   appended **RUN LOG** section that every phase writes one line to as it completes.
3. Any phase marked `running` whose process is dead = crashed. Mark it `failed`, read its
   `03_runs/<phase>/log.txt` for the reason, and either retry once or skip per §10.
4. Continue from the first phase whose deps are `done` and whose own status is not `done`.
5. **Check the clock against the 08:00 hard stop before starting anything.** If a phase's
   budgeted time would overrun the cap, skip it and record `skipped:out_of_time`.
6. Every phase script is **idempotent** — safe to re-run; it checks its own completion
   marker (`03_runs/<phase>/result.json`) and exits early if already done.

---

## 5. Lab folder layout

Everything the run produces lives in one tree, outside both corpora:

```
C:\Users\Ali\Desktop\corpus-lab\
  00_RUNBOOK.md              # this file + appended RUN LOG
  state\
    run_state.json           # machine state: phase statuses, timings, artifacts
    schedule.json            # phase budgets and the 08:00 cap
  bin\                       # every phase is a script here; all idempotent
    orchestrate.py           # the runner (see §6)
    probe_*.py               # mechanism probes M1-M5
    stack_*.py               # per-stack build + teardown
    ask.py                   # runs one headless Claude Code session, captures transcript
    score.py                 # scores a run against canaries or the answer key
    report.py                # renders findings
  01_reports\                # tool matrix extracted from the 5 research MDs
  02_stacks\                 # ONE DIR PER STACK: its index, config, build log, disk usage
    s0_baseline\  s1_rga\  s2_fts5\  s3_hybrid\  s4_*\
  03_runs\                   # ONE DIR PER PHASE: raw transcripts, tool-call logs, result.json
  04_scores\                 # scoring output: per-run CSV/JSON + the combined matrix
  05_findings\
    DECISION_MEMO.md         # THE MORNING DELIVERABLE
    GLOB_BUG_EVIDENCE.md     # reproduction writeup for sir (see §11.2)
    OPEN_QUESTIONS.md        # what tonight did not settle
  99_scratch\
```

**Rule:** no experiment artifact is ever written inside `ra-ship` or `harness/corpus_*`.
A stack that cannot put its index elsewhere is disqualified and recorded as such.

---

## 6. Orchestration model

**Three layers, deliberately.** The heavy, boring work is deterministic; only the judgment
is agentic. This is what makes it survive both context loss and a hung tool.

- **Layer 1 — `bin/orchestrate.py`, the runner.** A single long-lived background process.
  Reads `run_state.json`, picks the next runnable phase, executes it with a hard timeout,
  writes the result, updates state, repeats. Enforces the 08:00 cap. Knows nothing about
  models or judgment. This is what actually guarantees the night runs unattended.
- **Layer 2 — me, the orchestrator.** Launched as a background Bash task, the runner
  re-invokes this session when it exits or when a phase completes. On each wake: read the
  new results, decide whether to adapt the queue (drop a stack, promote a rung, retry a
  probe), and spawn judgment subagents. A long fallback `ScheduleWakeup` (1800s) keeps the
  loop alive if the runner hangs and never notifies.
- **Layer 3 — subagents.** Bounded, parallel, each with a single deliverable and a time
  cap: building one stack's indexer to a fixed contract, analysing one stack's transcripts,
  writing one section of the memo. Used wherever work is independent. Never given the whole
  problem.

**Concurrency rule.** Index builds are CPU-heavy and scored sessions are wall-clock-measured,
so the runner holds a `quiet` lock: no background index build runs while a *scored* Claude
session is being timed. Unscored work may overlap freely.

---

## 7. The measurement rig

This is the foundation — nothing else means anything without it. Build it first, in P0/P1.

### 7.1 Two corpora, two different jobs

| | **Corpus A — ra-ship** | **Corpus B — harness** |
|---|---|---|
| Path | `Desktop\Projects\Code\ra-ship` | `Desktop\harness\corpus_{500,2000,5000,15000}` |
| Size | 17.85 GiB, ~217k files (~175k of them venv/model-cache noise under `02_tool_runs`) | 83.6 MB → 3.8 GB, 500 → 15,004 files |
| Ground truth | 13 planted canary strings | 135-question answer key, 9 types, with evidence addresses down to page |
| What it measures | **Findability at real scale and real mess.** Binary: found or not. | **Retrieval quality.** Recall, precision, correctness, degradation across rungs. |
| Its limitation | No recall scoring — nobody has ground truth for "all 12 files mentioning X" | Synthetic — cannot prove behaviour on a real 17 GB drive |

They are complementary and are **not merged**. Merging would destroy the rung ladder (the
degradation curve is the most valuable output) and break the 15 absence questions, which are
verified absent across 14,670 files and would silently become answerable.

### 7.2 Instrumentation — how a "run" is measured

`bin/ask.py` runs **one headless Claude Code session** per question:

- `claude -p "<question>"` with `--output-format stream-json`, cwd set to the corpus root,
  a per-stack settings file, and a per-run timeout.
- Captures: the full JSONL transcript, **every tool call with its arguments and result
  size**, wall-clock, and token counts.
- Emits one `run.json` per question: `{question_id, stack, corpus, rung, answer_text,
  files_opened[], tool_calls[], wall_s, tokens_in, tokens_out, timed_out}`.

`files_opened[]` is the whole point — it is how silent misses become visible. An agent that
opened 40 wrong files and guessed right does not score the same as one that opened three
correct ones.

> **Verify before relying on it (P1/M0):** the exact flag names, whether `stream-json`
> includes tool arguments, where transcripts land, and how to point a session at an isolated
> settings/MCP config. If headless mode cannot be made to work, fall back to scripted
> interactive sessions and parse `~/.claude/projects/<slug>/*.jsonl`. **This is the single
> highest-risk dependency of the night — it is probed first and everything else waits on it.**

### 7.3 Stack isolation

Each stack defines `setup()` and `teardown()`:
- `setup()` writes its `.claude/settings.json`, `CLAUDE.md` and `.mcp.json` into the corpus
  root, and starts nothing that needs manual attention.
- `teardown()` restores the corpus root to its exact prior state (`git checkout` /
  `git clean` for the tracked config files; the 13 canaries and all other untracked working
  files are left untouched).
- A snapshot of ra-ship's pre-existing `.claude/` state and `git status` is taken in P0 and
  is the reference for "clean". **Verified after every teardown**, and the run halts if a
  teardown leaves the tree dirty in any way other than the known canaries.

### 7.4 Scoring

**Corpus A (canaries) — `direct findability`.** For each of the 13 phrases: "Find the file
containing the string `<phrase>` and tell me its path." Binary hit/miss + files opened +
wall-clock + how many `02_tool_runs` files were opened before the first relevant one
(*venv-noise*, the context-rot proxy). This is deliberately a findability test, not a
semantic one — the canaries are nonsense strings and asking a semantic question of them
would measure nothing.

**Corpus B (answer key) — `retrieval quality`.** Per question:
- **Retrieval recall** — fraction of the key's evidence files the agent actually opened.
- **Retrieval precision** — correct evidence opened ÷ total files opened.
- **Answer correctness** — scored by type: numeric with tolerance and *vintage-aware*
  (two documents can give different numbers for the same series-year and both be correct);
  exact-match where the key allows; and an **LLM judge** for the open types, run against the
  key's expected answer, its acceptable-alternatives, and its must-not-cite list.
- **Absence behaviour** — for the 15 absence questions, did it correctly decline, or invent?
  Cheapest and most damning signal in the set; scored separately and reported on its own.

### 7.5 Question sampling

135 questions × N stacks × M rungs is far too many sessions for one night. Use a **fixed
stratified subset of 20**, identical across every stack and rung so results are comparable,
drawn to cover all 9 types with the hard classes weighted:

`trajectory 4 · point_lookup 3 · absence 3 · multi_branch 3 · reconciliation 2 ·
stale_doc 2 · name_content_mismatch 1 · canonical_duplicate 1 · relationship 1`

Frozen to `04_scores/question_sample.json` in P0 with the selection seed recorded, so any
later session extends rather than re-draws it. If a stack finishes early, extend the sample
rather than adding a rung.

---

## 8. The stacks

Ordered by cost. Each is a real candidate for the final build, not a strawman. **S0 and S1
must complete**; later stacks are cut first when time runs short (§10).

| id | Stack | What it tests | Index cost |
|---|---|---|---|
| **S0** | **Baseline — stock Claude Code.** No index, no hooks, no config. Glob/Grep/Read only. | The number that justifies the whole project. Run first, on both corpora. | zero |
| **S1** | **rga + policy.** `ripgrep-all` so grep reaches inside PDFs/Office docs, plus a CLAUDE.md policy and venv exclusion. | The cheapest possible intervention. If this alone fixes canary recall, that is a major finding and changes the recommendation. | zero (no index) |
| **S2** | **SQLite FTS5 page-level index + MCP + PreToolUse deny.** Walk → hash → per-page text extract → FTS5 rows at page granularity → coverage table with the status enum → exposed as MCP tools, with built-in Grep/Glob denied and redirected. | The likeliest thing to actually ship. Gives page addressing, the coverage exception list, and full control. | text only; small |
| **S3** | **S2 + semantic.** Embeddings over the page/chunk text into an embedded vector store, hybrid lexical+vector fused with RRF. | Whether semantic adds anything over FTS5 **for vague questions** — the professor's actual use case. | + vectors |
| **S4** | **Conditional / stretch.** Best remaining candidate from the tool matrix that installs cleanly on Windows and is free. Chosen at P1 from the research findings, not pre-committed. | Off-the-shelf vs hand-rolled. | TBD |

**Micro-benchmark (not a stack): deep-extraction cost.** Measure pages/sec for each viable
extraction path (fast text vs. layout-aware) on a fixed sample of fat PDFs, and extrapolate
to sir's real tree. Answers a question both round-two reports left open, in ~25 minutes.

### 8.4 Model policy

One model, fixed across every scored run, so stacks are comparable. Use the cheaper fast
model for the 20-question sweep; **re-run the winner and S0 on the larger model** to confirm
the finding holds and is not an artefact of model size. Record model + version in every
`run.json`. Hard cap on total scored sessions recorded in `schedule.json`; the orchestrator
stops scheduling new sessions when it is hit.

---

## 9. Mechanism probes (P1) — cheap, decisive, run before the stacks

These are minutes each and several of them determine the shape of the final build. They run
before any stack because a negative result changes what gets built.

| id | Probe | Why it matters |
|---|---|---|
| **M0** | **Headless harness works.** `claude -p`, stream-json, tool args captured, isolated settings honoured. | Everything depends on it. Blocking — if it fails, fall back to transcript parsing before continuing. |
| **M1** | **Does `PreToolUse` deny on `Grep\|Glob` hold?** Interactive and headless; does the model fall through to the MCP tool; does it survive `--dangerously-skip-permissions`. Also measure hook latency. | Both round-two reports recommend deny-and-redirect as the only available route, and **neither tested it**. If it does not hold, the whole delivery design changes. |
| **M2** | **Does the Glob silent-zero-results bug reproduce here?** Time raw ripgrep across ra-ship's 217k tree; compare against what Claude Code's Glob returns for the same pattern; look for `0 results` where the file demonstrably exists. | The most valuable single measurement for sir — it converts "prompting isn't working" into a demonstrated tool defect on his own data. Ticket trail (#16043 → dup of #4486, closed `not_planned` by an inactivity bot, never triaged by a human) is confirmed but **unverified on this machine**. |
| **M3** | **Read-tool truncation.** What actually happens past the default line limit, and is the model told? | Four research passes disagree; issue numbers do not overlap. Settle it locally instead of citing. |
| **M4** | **Do deny rules cover Bash-invoked `rg`/`grep`/`find`?** | If not, the enforcement layer has a hole big enough to walk the whole corpus through. |
| **M5** | **Does an index survive a moved file?** Move a file inside a scratch copy, re-run, see whether the stack reports a stale path or self-heals. | "A stale index silently points at files that moved" is the stated worst case. Content-hash-as-primary-key is the proposed answer; test it cheaply. |

M2, M3 and M5 run against scratch fixtures or read-only queries — none of them modify
ra-ship.

---

## 10. Schedule, timeouts and degradation rules

Start ≈ 01:30. Hard stop **08:00**. Budgets are ceilings, not targets.

| Phase | Work | Budget | Depends on |
|---|---|---|---|
| P0 | Lab scaffold, state file, snapshot ra-ship clean state, freeze question sample, plant harness canaries from `keys/canary_slots.json` | 25 min | — |
| P1 | Mechanism probes M0–M5 | 50 min | P0 |
| P2 | S0 baseline: 13 canaries on ra-ship + 20 questions on `corpus_500` | 50 min | P1(M0) |
| P3 | S1 rga: same battery | 40 min | P2 |
| P4 | S2 index build — ra-ship + rungs 500/2000/5000 *(background, overlaps P3/P5)* | 90 min | P1 |
| P5 | S2 eval: canaries + 20 questions at 500 and 5000 | 45 min | P4 |
| P6 | S3 semantic build + eval | 80 min | P5 |
| P7 | Deep-extraction cost micro-benchmark | 25 min | P1 |
| P8 | Analysis, scoring matrix, decision memo, glob-bug writeup | 45 min | all |
| — | Buffer | 40 min | — |

**Degradation order when behind schedule** — drop in this order, recording each as
`skipped:out_of_time` with what it would have told us:
1. S4 (stretch stack)
2. S3 semantic layer
3. The 5000 rung (keep 500 + 2000 for a two-point curve)
4. Extended question sample beyond the frozen 20
5. **Never cut:** M0, M1, M2, S0, and P8. Without S0 there is no baseline and the night
   produces nothing usable; without P8 the results are unread.

**Failure rule:** any phase that fails gets **one** retry with a fresh log. Second failure →
`failed`, move on, and record it in `OPEN_QUESTIONS.md`. Never retry a third time and never
let one broken tool consume the night. If a stack cannot be built in its budget, record what
blocked it — a stack that will not install cleanly on Windows unattended has told us
something real about whether it belongs in the final design.

**Checkpoint at 05:00:** stop starting new stacks. Whatever is running finishes; everything
after that is scoring, analysis and the memo. Better a complete memo on three stacks than a
half-scored fourth.

---

## 11. Morning deliverables

### 11.1 `05_findings/DECISION_MEMO.md` — the one that matters
Ranked recommendation with the numbers behind it: the scoring matrix (stack × corpus × rung
× metric), the degradation curve, what each stack costs in disk and build time, which
delivery mechanism actually held under test, and a specific recommendation for what to build
next with its measured basis. Written for sir's decision, but with the raw numbers attached.

### 11.2 `05_findings/GLOB_BUG_EVIDENCE.md` — the thing to show sir
If M2 reproduces: a clean, self-contained reproduction on his own corpus, with timings, the
exact query, what Claude Code returned, what ripgrep returned, and the ticket trail. **Framed
carefully** — the earlier framing of this was partly wrong and must not be repeated: #12534
is the VS Code extension and not his setup; #16043 is closed as a duplicate; the Read-tool
claim does not hold in the form previously written; #4486 is closed `not_planned` by an
inactivity bot with four bot comments and no human triage, and is labelled `platform:macos`
while sir is on Windows — so the honest claim is *the class of defect is filed and unfixed*,
not *his exact bug is filed*. Nothing goes in front of sir that has not been reproduced here.

### 11.3 `05_findings/OPEN_QUESTIONS.md`
What tonight did not settle, what got cut for time and what it would have told us, and the
ranked next actions for the following session.

### 11.4 Raw evidence
`03_runs/` transcripts and `04_scores/` matrices, kept so any claim in the memo can be traced
back to the session that produced it.

---

## 12. Verification — how we know the night's results are trustworthy

1. **Teardown check after every stack:** `git status` on ra-ship matches the P0 snapshot
   exactly, modulo the 13 known canaries. Run halts if not.
2. **Canary integrity at the end:** all 13 phrases still present at their recorded paths with
   unchanged mtimes; harness canaries verified planted and findable-in-principle.
3. **No writes into the source trees:** assert nothing under `harness/corpus_*` was modified
   (mtime sweep against the pre-run baseline), and nothing new under `ra-ship` beyond the
   stack config files.
4. **Comparability:** every scored run recorded the same model, the same frozen 20 questions,
   and the same corpus paths. Any run where this is not true is excluded from the matrix and
   listed as excluded.
5. **Traceability:** every number in the memo cites the `run.json` it came from.
6. **Space:** total `corpus-lab/` disk usage reported in the memo, with per-stack breakdown,
   so the space cost of each option is a known quantity rather than a guess.

---

## 13. Status

**Phase 1 exploration in progress.** Three parallel Explore agents are reading (a) the five
research reports to build the tool matrix, (b) the harness answer-key schema and scoring
surface, (c) the ra-ship tree, canary state, and the local toolchain inventory. §8 (final
stack list, esp. S4), §7.2 (exact headless flags) and §9 (probe specifics) are filled in from
their findings before execution begins.
