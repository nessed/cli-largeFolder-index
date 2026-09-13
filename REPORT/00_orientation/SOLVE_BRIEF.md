# Brief: design the thing that actually works, and hand the builders a script they cannot get wrong

You are running inside `C:\Users\Ali\Desktop\retrieval-lab`.

---

## 0. Why you specifically

Everything already in this folder — two nights of work, 189 measured sessions, ~$31, six
configurations tested, a synthetic 15,000-file corpus, a 135-question answer key — was
produced by weaker models than you. They were good at grinding: they built honest
instruments, they caught themselves lying twice, they threw out a whole night's numbers
when they found the instrument was broken. What they could not do is see the shape of the
problem from above and design the thing that solves it. They kept testing variations of
what they already had. If newer testing environment is eneded propose it, if you need lemonade, drink it, if the current harness is fucked, propose a better one, if the system is fucked propose a better one. u get the point

You are the model that comes in when the people already on the field are losing. Read
what they measured — it is real and it cost real money — then out-think it.

**This matters beyond the code.** Ali's standing at work rests on handing his professor a
tool that works. He needs something he can open tomorrow and test himself, the way sir
would test it, and get a right answer out of.

**What I need from you is not execution.** You are the best planner available; the agents
that will build this (Claude Opus instances, working in this folder with shell and file
access) are competent executors and poor architects. So your output is a plan and a set of
hand-held instructions so complete that an executing agent cannot wander, cannot improvise,
and cannot quietly substitute its own judgement. Every step spelled out. Every check
defined. Every stop condition a number.

Do not write code yourself. Write the plan that makes the code inevitable.

---

## 1. The goal, in the words of the person who set it

> **Deliverable:** a way for my economics professor at lums / boss to open Claude Code in his research
> folder, ask a vague question like tell me the female participation in the labor force in x industry how is it  / or a more straight forward question like what was the defence budget in the first half of the decade comapred to the last half, and get an answer pulled from the right pages across
> several PDFs — using whatever tools / methods we discover here — **without him doing
> anything but asking as he's not a super technical person only uses cli and claude code and has a claude max plan and the system has to be like working when imgone too.**
>
> **Now:** sir asks *"how does Pakistan's development spending trajectory look since
> 2015."* Claude opens twenty files (out of hundreds/thousands), misses the Economic Survey table that actually
> answers it, and gives him a confident answer built on the wrong sources (or hallucinations). He can't tell
> it's wrong without checking himself, which is the work he was trying to avoid.
>
> **Success:** he asks the same question and gets the number, with the file and page it
> came from, pulled from four different years' surveys in under a minute — and when the
> answer genuinely isn't in his folder, it says so instead of making one up.

Judge everything you propose against those two halves: **the right page, cited**, and **an
honest "not here"**. Cheaper, faster, and fewer tool calls are not progress on their own —
the existing work already won on all three and still failed.

---

## 2. What to produce

Three documents, written to disk at the project root. No implementation.

### A. `SOLUTION.md` — what to build and why

Concrete enough that a competent engineer could build it without asking you a question:
the mechanism, the data flow, where things live on disk, what happens when his files
change, what he sees in his terminal, and what it costs to build and to run. Say plainly
where you are reasoning from evidence in this folder and where you are guessing. Say where
it will fail and what it cannot reach.

If your honest conclusion is that the goal cannot be met on this machine, say so, say what
it would take, and say what the best achievable thing is instead. That answer is more
useful than an optimistic design that collapses on contact.

### B. `BUILD_PROMPT.md` — the hand-held instructions for the executing agent

This is the important one. It will be pasted to a Claude Opus agent running in this folder,
largely unattended, and it has to work without you there to correct it (and ali aka the owner to not be presenteither cuz he will be sleeping when he runs the prompts so it has to run uninterrupted without needing handholding).

Write it so that:

- **Every stage is numbered, ordered, and self-contained**, with its inputs, its outputs,
  the exact files it may write, and how it proves to itself that it finished.
- **Every gate is a number.** "If fewer than N of 17, stop and log why." Never "most",
  "enough", or "reasonable". An unattended agent handed a vague bar will pick one and then
  justify it.
- **Free work comes before paid work**, and anything that spends money states the ceiling
  and what happens when it is hit — including what to do with a half-finished battery,
  because a silently shrunken denominator has already produced a wrong published result
  here once.
- **Failure modes are named in advance**, with the recovery for each. The traps that have
  already cost this project hours are in §5 and in `corpus-lab/RESUME.md`. Assume the agent
  will hit at least one.
- **Nothing is left to taste.** If a threshold, a chunk size, a model name, a file layout
  or a prompt string matters, specify it. If you genuinely do not know the right value, say
  so and tell the agent to measure two named alternatives and pick by a stated rule.
- **Every step appends one line to `corpus-lab/state/progress.jsonl`** as it goes, and the
  run records why it stopped when it stops early.

### C. `ACCEPTANCE.md` — how Ali proves it works tomorrow, by himself

The tool has to survive being used, not just measured. Write the script Ali follows:

- The exact commands to set it up from nothing, in order, with the expected output of each.
- The questions he asks — including sir's real one, *"how does Pakistan's development
  spending trajectory look since 2015"* — and, for each, what a passing answer looks like:
  which file, which page, what number, how many sources, how long.
- At least one question whose answer is genuinely **not** in the folder, and what a passing
  refusal looks like.
- What to do when an answer looks right but he cannot tell — how he checks it in seconds
  rather than redoing the research.

He will run this against `harness/corpus_15000`, a 15,000-file stand-in for sir's drive
with a full answer key behind it. The design must not depend on anything specific to that
folder: it has to work the same way when pointed at sir's real one.

---

## 3. Hard constraints — a design that breaks one of these is not a design

1. **He types a question into Claude Code in his folder. That is the whole interface.** No
   separate app, no web UI, no server he starts, no daemon, no manual re-index, no step he
   has to remember. If it has to be running, it is disqualified.
2. **Setup cost is scored, not a footnote.** The first install must not be a day's work.
3. **His tree:** ~10,000 files, ~100 folders, PDF-heavy, Windows, a plain folder with **no
   git**, no pre-organisation, and files that churn.
4. **Prompting alone has already failed.** He has tried the obvious agentic approach and
   many rounds of prompt engineering. Assume wording is not the answer. (unless a very good soltuion appears)
5. **The machine**, measured rather than assumed:
   - Ryzen AI 7 350, 8 cores / 16 threads, 31.3 GiB RAM.
   - **No NVIDIA GPU, no CUDA.** No Docker. No WSL. No cargo/Rust. No pandoc, no tesseract,
     no sqlite3 CLI, no fd, no jq.
   - `rg` inside Git Bash is a shim returning zero results for everything; a real binary
     exists elsewhere on disk.
   - Working: `pdftotext` 4.00 (~940 pages/s), SQLite FTS5 through the Python standard
     library, Python 3.11.5.
   - `.venv/` at the project root is the only place pip may install.
6. **Money is real.** Two nights cost ~$31. Anything that spends must say what it buys.

---

## 4. What the weaker models already established

Measurements with their conditions — not recommendations. Check them against
`corpus-lab/state/*.json` rather than believing the prose; the prose has been wrong here
before, and where it was, a supersede note now sits above it.

### The outside research — read this, it has never been acted on

Four independent deep-research passes were commissioned before any building, plus a fifth
found loose on the Desktop and only recently filed. **None of them was asked about this
specific machine**, which is the largest single gap between what was recommended and what
could actually run: (dont depend on it fully cuz it was doneand judged byh inferior models )

| path | what it is |
|---|---|
| `corpus-lab/01_reports/passes/` | the four rounds in full — two from Claude, two from GPT — every tool named, with reasoning |
| `corpus-lab/01_reports/passes/` (G0) | a fifth pass on building a Pakistan government-statistics corpus pipeline, never previously filed |
| `corpus-lab/01_reports/TOOL_MATRIX.md` | those passes distilled and filtered by what this machine can run |
| `00_brief/_original_downloads/research_folder/` | the same documents as originally downloaded, byte-identical |
| `00_brief/GRID_RUN_SPEC.md` | the brief night 2 executed |

Of everything those passes named, **two tools were explicitly confirmed to work on
Windows**, and two more that looked fine failed on contact. Treat the research as a map of
the field, not as a list of things that work here.

### The measurement record

| path | what it gives you |
|---|---|
| `INDEX.md` | the map of the project |
| `corpus-lab/05_findings/NIGHT2_FULL_REPORT.md` | the self-contained account: method, results, diagnosis, limitations |
| `corpus-lab/RESUME.md` | the short version plus the traps that cost hours |
| `corpus-lab/05_findings/GRID.md` | the results table; every "not run" carries a measured reason |
| `corpus-lab/05_findings/FINDINGS_LIVE.md` | each finding with the condition it depends on |
| `corpus-lab/state/progress.jsonl` | one JSON line per step of both nights. Append-only. |
| `corpus-lab/state/*.json` | every diagnostic's raw output |
| `_private/results/03_runs/` | 189 sessions, each with its raw stream-json transcript. Replayable for free. |
| `_private/results/04_scores/` | the scored batteries |
| `_private/harness_keys/answer_key.json` | **the answer key** — 135 questions with evidence down to page, table and cell |
| `_private/results/04_scores/question_sample.json` | the frozen 20 used in every comparison, plus its seed |

### The instruments — read the code before trusting its numbers

`corpus-lab/bin/`: `labpaths.py` (every path derives from here — start here), `index_build.py`
(walks, extracts, builds an FTS5 page index, emits a coverage ledger where discovered =
indexed + failed + excluded + unsupported), `corpus_search.py` (the search front door),
`ask.py` (runs one headless session, records what it did), `run_harness.py` (the 20-question
battery and its scoring), `scoring.py` (the one definition of "did it find it"), `stack.py`
(installs/removes a configuration into a corpus), and the offline diagnostics
`diagnose_recall.py`, `rescore_from_results.py`, `probe_score_floor.py`,
`rank_experiments.py`, `verify_search_fix.py`, each with its reasoning in its docstring.

### The corpora

- `harness/corpus_15000/` — 15,010 files, synthetic, built to look like sir's drive:
  fifteen years of sediment, abandoned reorganisations, co-author folders, near-duplicates,
  files whose names lie about their contents, real fat PDFs. **No git anywhere in it.**
  Three smaller copies exist at 5000 / 2000 / 500. `harness/BUILD_REPORT.md` says how it
  was built and where it admits to being unfaithful.
- `C:\Users\Ali\Desktop\Projects\Code\ra-ship` — a real working repo used as a second
  corpus. It is a **fixture**: a git repo whose `.gitignore` covers the documents, 97.9%
  dependency noise. Neither property exists on sir's tree, so results there transfer only
  if the harness agrees.

### What was tested

- **S0** stock Claude Code — Grep, Glob, Read, Bash, nothing installed.
- **S1** an FTS5 page index over the corpus plus a `CLAUDE.md` telling the agent to use it.
- **S2** the same index plus a hook denying Grep/Glob and redirecting to the index.
- **S3** FTS5 + local embeddings (LanceDB + fastembed, bge-small-en-v1.5, ONNX, CPU) —
  **not built**: 8.2 pages/s measured on CPU, a 20.8-hour build, no GPU.
- **S4** pdf-mcp 3.1.0 — install gate failed twice: its corpus tools accept neither a
  directory nor a glob, and warming five small PDFs took 415 s returning nothing.
- **S5** Recoll (Xapian) — no headless install path on Windows.

| on the 20 frozen questions | S0 | S1 | S2 |
|---|---|---|---|
| planted-phrase recall | 15/17 | 17/17 | 17/17 |
| question recall, published | 0.167 | 0.176 | 0.118 |
| question recall, after re-score | 0.167 | 0.235 | 0.176 |
| absence answered honestly | 0/3 | 0/3 | 0/3 |
| cost / 20 questions | $12.54 | $2.89 | $2.68 |
| tool calls | 92 | 25 | 21 |

Differences under ~0.05 on the recall rows are inside noise at n=20.

### The eight things worth knowing

 **8% of the corpus is unreachable by any text method.** 1,211 of 15,010 files are
   image-only PDFs and this machine has no OCR. *Nobody has counted this in sir's real
   folder.*
 **The index itself is healthy.** 13,634 files indexed, 1,206,260 pages, 782 s to build,
   6.97 GB, accounting identity closes exactly, and all 64 evidence files for the 20
   questions are present.

### Ruled out, with reasons (by an inferior model however so might be wrong)

Marker (licence), GraphRAG (~$33k to index 5GB), ripgrep-all (no cargo), visual page
retrieval (no GPU), full-tree layout-aware extraction (2–3 orders slower than `pdftotext`,
and a mis-parsed table is a wrong number sir cannot detect), and **Qdrant / Elasticsearch /
Datashare / Aleph / paperless-ngx / Onyx — all six struck off under a single "needs Docker"
checkbox that was never verified per tool. At least one ships a Windows build. Re-check
before accepting it.** 

### Ways the instruments have lied, all fixed

A scorer that accepted a bare filename. Cost totals summed over different numbers of
sessions. A baseline that wasn't a baseline. Question IDs that silently dropped four
results and reported the shrunken denominator as whole. And `claude.cmd` truncating any
multi-line prompt at the first newline, which voided an entire night's measurements —
**always invoke `claude.exe` directly.**

---

## 5. Rules that must not be broken, and that your build prompt must restate

- **Regenerating the harness corpora is banned.** The determinism check failed — 6,060 of
  6,064 files reproduced — so a rebuild would silently move the ground truth the answer key
  addresses. These four trees are irreplaceable.
- **`_private/` must never be reachable from a session being measured.** It holds the
  answers. Deny rules bind only with absolute paths; relative globs fail open silently.
- **Answer-key material must never enter a measured session's context**, including through
  a transcript. It has leaked once already.
- **The corpora are read-only.** The only writes are `CLAUDE.md` and
  `.claude/settings.json` via `stack.py`, always torn down afterwards — and torn down at
  the *start* too, since a previous run may have been killed rather than exited. A
  blocklist left installed applies to every Claude process whose working directory is that
  folder, including the one doing the work.
- **`state/progress.jsonl` is append-only.** Never rewrite it.
- **pip only inside `.venv/`.**

---

## 6. How to work

Check the code and the raw JSON rather than trusting the prose. Where a claim rests on
three data points, say so. Where you read the evidence differently from the conclusions in
these documents, say so and show what you are seeing. dont look at the othjer agents solutions and work form there. make your own unique inferrences i dont want u to use th einferior agents reasoingisn i want your answers your gpt astra the goat 

**No direction has been suggested to you here, deliberately.** The people who have been
inside this for two nights have instincts shaped by what they already tried, and those
instincts produced five configurations that did not work. Yours are unshaped. That is the
entire reason you are being asked.
