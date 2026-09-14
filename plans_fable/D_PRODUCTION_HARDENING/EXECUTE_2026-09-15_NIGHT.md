# EXECUTE — production hardening night, 2026-09-15 → 2026-09-16

*Written 2026-09-15 by a Fable planning session after reading the full record: the README,
`REPORT/08_what_next/SESSION_LOG_2026-09-13_to_09-14.md` with its four appendices,
`HANDOFF_2026-09-16.md`, `CURRENT_WORKING_ARCHITECTURE_2026-09-15.md` and its three addenda,
findings F40–F63, the shelf code, the installer, the guard, the battery driver, the scorers, and
fresh measurements taken today on this machine. Every number in §1 was measured today; nothing
is from memory.*

**You are an executing agent (Sonnet or Opus). You run this file top to bottom, one phase at a
time, unattended, overnight. Ali will show the result to his professor in the morning. Your job
is to make the thing that already exists fast, honest and reproducibly measured — not to invent a
new retrieval idea.** Every step is spelled out. Every gate is a number written before the run.
Where a choice is open, the choice is made for you below. Do not widen scope.

**Recommended way to run this:** one fresh agent context per phase (the previous session's
Appendix D measured a single 19-hour context costing 345 million tokens for 0.26% output). Each
phase below is self-contained: it says what to read, what to build, how to verify, what to
commit, and what to write into `progress.jsonl`. If you are running the whole file in one
session, `/clear` between phases and re-read only §0 and the phase you are on.

> ### ⏯ If you are starting or RESUMING after an interruption — do this first, every time
>
> This run is expected to be interrupted (laptop sleep, session killed, terminal closed, power).
> Nothing here assumes a continuous session. On every start:
>
> 1. `git branch --show-current` — if it is not `phase9-production-hardening`, check it out (create
>    it off `master` only if it does not exist). `git status --short` — if dirty, commit what is
>    there as `WIP (resumed): <files>` before touching anything; never discard it.
> 2. `.venv/Scripts/python.exe corpus-lab/bin/p9_checkpoint.py resume` (built in Phase 0.7; if it does
>    not exist yet you are at Phase 0 — go there). It prints the last completed step, the step that
>    was `in_progress` when the run died, the safety-check results, and the exact heading in this
>    file to continue from.
> 3. Run the **done-check** of the interrupted step (table in §R.3). If it passes, mark it done and
>    move on; if it fails, redo that step from its start — every step is written to be re-runnable.
> 4. Never redo a step whose done-check passes. Never skip a step whose done-check fails.
>
> Read §R (checkpoint protocol) once; it is short.

---

## 0. Fixed rules — read before Phase 0, and re-read before every phase

These are the repository's standing rules (Session Log, Appendix C.2), restated here so you
never need to open that file mid-run. **They are not style preferences.**

1. **Corpora are read-only.** Under `harness/` the only permitted writes are the two files
   `c_stack.py setup` creates (`<rung>/CLAUDE.md`, `<rung>/.claude/settings.json`) and they must
   be removed before the phase ends. Rung root must be clean at the start **and** end of every
   phase that installs anything. Check with `ls harness/corpus_15000/CLAUDE.md harness/corpus_15000/.claude`
   — both must say "No such file".
2. **Teardown runs in every exit path**, including failures and interruptions.
3. **Gates are written before numbers exist.** Every gate in this file is already written. You may
   not widen a bar, change a denominator, add an unplanned variant, or re-run a live session
   because you disliked its answer. If a pre-registered gate reads STOP, record STOP and move on.
4. **Contamination.** Retrieval logic (anything in `c_shelf*.py`, `c_stack.py`, the CLAUDE.md
   text, the guard) may use only question text, shelf metadata, and the generic rules already in
   `c_offline_gate.py` (`row_words_from_question`, `_TRAJECTORY_FILLER`, `_ROW_SEP_RE`, `FY_RE`,
   `content_words`). **No hand-written title, family, caption, label, synonym, publication name,
   or year string may enter code or CLAUDE.md.** Only gate and scoring scripts may open
   `_private/**`; they persist ranks, counts and question ids only — never a path, title or value
   from the key. You personally do not open `_private/harness_keys/answer_key.json` or
   `_private/results/04_scores/question_sample.json` except through those scripts.
5. **Holdout discipline.** Holdout-1 is retired. Holdout-2 has **one look left**. **This plan
   spends zero holdout looks.** Do not run anything with `--holdout`, `--holdout2`, or
   `c_page_holdout.py`. Aggregate counts only, never per-question, in anything you write.
6. **Frozen instruments — do not modify:** `ask.py`, `run_harness.py`, `scoring.py`,
   `corpus_search.py`, `index_build.py`, `stack.py`, `c_shelf_build.py`, `c_score_live.py`,
   `c_offline_gate.py`'s existing behaviour. `c_shelf.py`, `c_stack.py`, `c_live_battery.py`,
   `c_stop_guard.py`, `c_offline_gate.py` may gain **optional arguments whose defaults preserve
   behaviour exactly**. New behaviour goes in new files (`*_v2.py`) or behind new flags.
   **Every recorded number in the repository must still reproduce from the original code path
   with explicit flags.**
7. **One `plog.py` line per step**, counts only, append-only, to `corpus-lab/state/progress.jsonl`.
   Shape: `.venv/Scripts/python.exe corpus-lab/bin/plog.py <phase> <step> <status> "<note>" k=v k=v ...`
   — e.g. `plog.py P9 1_latency PASS "open 7.5s->0.3s; ranks preserved" open_before=7.5 open_after=0.3`.
8. **Never push.** Every branch is local by design.
9. **Environment.** Always `.venv/Scripts/python.exe` (never system python). Always
   `C:/nvm4w/nodejs/node_modules/@anthropic-ai/claude-code/bin/claude.exe` (resolved in code as
   `labpaths.CLAUDE`) — **never** `claude.cmd`. Long jobs run with `python -u`. Run long jobs
   in the foreground; backgrounded jobs have been reaped mid-run twice.
10. **Headless model calls you make yourself** (any `claude.exe -p` outside `ask.py`) must run with
    cwd in a temp directory **outside this repository** (`%TEMP%\c_h_select_cwd` or similar), or
    the model loads this project's own auto-memory. `c_llm_select_gate.assert_clean_cwd()` is
    the pattern. This plan asks you for very few such calls.
11. **Windows/bash trap:** Windows paths inside bash heredocs feeding `python -c` break. Write
    a `.py` file instead.
12. **Budget for the whole night:** at most **95 live sessions** (Phase 5: 60 + 9 probes + 3
    rehearsal; Phase 6: ≤ 4). Reported cost (`cost_usd` from `ask.py`; on a Max plan this is notional but it is the
    only meter we have) is capped per battery: Sonnet battery **≤ $20**, Opus battery **≤ $80**,
    everything else **≤ $10**. Opus is roughly five times Sonnet's price per token and its
    sessions run longer under a 900 s clock, so it may well cost $40–60. After the first **6**
    Opus sessions complete, project `cost_so_far × 20 / 6`; if it exceeds $80, stop the Opus
    battery, record `OPUS_BUDGET_STOP n-of-20`, and score the completed sessions as a **partial
    with its denominator stated** — pre-registered here so it is not a post-hoc choice. Phase 5b
    runs only if the Sonnet battery cost ≤ $20 and the clock allows.

13. **Checkpoint discipline.** Before starting any numbered step: `p9_checkpoint.py start <step>`.
    After it: `p9_checkpoint.py done <step> k=v ...` and a `plog` line. A step with no `done`
    record is assumed unfinished. Long jobs print progress at least every 60 s to the console
    **and** to `corpus-lab/state/phase9_heartbeat.log` (the helper appends a timestamped line
    on every `start`/`done`/`beat`). See §R.

**Branch:** create `phase9-production-hardening` off `master` (master is `12de91b` or later and
contains everything from the phase branches). One commit per numbered sub-step that changes
files, message prefixed `Phase N.M:`. Commit every gate spec **before** the run it governs.

---

## 1. The diagnosis this plan acts on (measured today, 2026-09-15)

You do not need to re-derive any of this. It is here so you know *why* each phase exists.

### 1.1 Every shelf command is a fresh process, and two of them scan the whole index

Timed today as the professor's session would run them (fresh `python.exe` per call, warm disk):

| command | wall | where the time goes |
|---|---|---|
| `find` (question + 3 rewrites, caption channel lex) | **9.5 s** | 7.4 s is `coverage()` doing `SELECT COUNT(*) FROM pages` over 1.2 M rows on every call; 2.0 s is loading the embedding model |
| `open <path> <page>` | **7.5 s** | `SELECT body FROM pages WHERE rel=? AND page_index=?` — `rel` is UNINDEXED in the FTS5 table, so this is a full scan |
| `coverage` | 7.4 s | same full count |
| `inside` (dense captions, the adopted B2c default) | 3.3 s | 2.0 s model load + re-embedding all of the document's captions (144 for a 496-page Survey) on every call, although `captions.f16.npy` already holds every caption vector |
| `series` over 5 editions | 7.6 s | model load once + 5 × inside |
| `have`, `tables`, `exact` | 0.4–0.5 s | fine |
| bare `import c_shelf` + context build | 0.6 s | floor |

A trajectory session issues roughly `find ×1, series ×3, inside ×6, tables ×3, open ×13`
(Session Log A.3.1). At today's speeds that is **~2 minutes of pure tool latency**, most of it
`open`. The Session Log's "roughly ten seconds a page" is this. Fixing it changes no ranking.

### 1.2 The harness has been ending sessions before they answer

`c_live_battery.py` runs every session with `--max-turns 25` and a 300 s timeout. The professor
has neither. Read from the recorded result files today (aggregate only):

| battery | sessions that ended with **no answer text at all** |
|---|---|
| P5 (overnight) | 2 hit the 25-turn cap |
| P6 (pm) | 3 hit the turn cap + 2 timed out = **5 of 17** |
| P7 (evening) | 1 hit the turn cap |
| P8 (today) | 3 hit the turn cap + 1 timed out = **4 of 17** |
| PQ (unintended) | 2 + 2 |

They are the multi-branch and trajectory questions — the multi-document ones. Every one was
scored as a miss, and `cited_right_page` has never been above 2 of 17. **Some unknown but
material part of the live loss is the harness, not the system.** A.3 of the Session Log showed
the same question dead at 300 s under the harness and 3-of-5 correct at 4m00s without it.

### 1.3 Two structural defects in the shelf itself (measured on `shelf.db` today)

- **Fragmented families.** The family key comes from the first title-like line of page 0. When
  that line is a citation fragment the same publication becomes a separate family: **51 families
  whose name is another family's name with 1–3 junk leading tokens, carrying 93 editions.**
  Visible in any `find`: the same fiscal-operations publication occupies ranks 4, 5, 6 and 11.
  Those slots are stolen from the top ten and the `series` walk sees only a fragment's editions.
- **Bare calendar years are not normalised.** `make_family` replaces `2012-13` with `{fy}` but
  leaves `2019` alone, so **263 families carry a bare year in their name** and a yearly report
  becomes one family per year.
- **The primary copy is chosen by page count, then size, then *shortest path*.** In **166 of
  1,332** multi-copy edition clusters the marked primary has fewer identical-hash siblings than
  another survivor; in **153** the primary is a singleton while a sibling exists in ≥ 2 copies.
  The one-off file (a draft, an "old tables" export, a planted "perturbed values" file that Opus
  caught by hand in A.5.2) wins the `*` and becomes the file `find` tells the model to open.

### 1.4 The model sees twelve candidates; the answer is usually within forty

`find` prints `--k 12` by default. Offline, the gold publication is in the fused top 10 on 10/17,
top 20 on 12/17, top 50 on 14/17, top 100 on 16/17. Experiment H (F60, F63) showed that when the
answering model is shown 100 one-line cards it ranks the gold in its own top 10 on 11–14/17 and
first on 7–8/17 — better than any statistical reranker — but H was run as a separate headless
call and never shipped. The cheapest form of H is simply **showing the answering model more of
the list in a compact form**, inside the session it is already running, at zero extra calls.

### 1.5 The scorer is stricter than the answer key

The key carries `acceptable_alternates` (value, vintage, caveat) on **45 of 135** questions and
`series_id`/`vintage_id`/`fy` on every evidence address. No scorer reads the alternates, and the
address match is exact single-address. Session Log A.2.4: two models, four sessions, the same
figure from four official publications, every one scored 0. The generator's own placement
records (`_private/harness_keys/`, `harness/world/`) know every page that prints a given cell.

### 1.6 What is already solid and must stay solid

Honest refusal (11/11, 4/4, 11/15 live under the repaired scorer). B2c page retrieval (52/57 dev,
67/81 holdout). The Stop-hook citation guard (unopened file paths 10 → 0). Session isolation.
Corpus integrity. Each has a self-test; every phase below re-runs them.

---

## 2. Phase map, order, and what each is worth

| phase | what | model calls | wall | why first/last |
|---|---|---|---|---|
| 0 | baselines, branch, snapshot | 0 | 30 min | protects everything after |
| 1 | latency: rank-preserving speedups | 0 | 2 h | largest professor-visible win, zero risk to numbers |
| 2 | shelf v2: family merge, year normalisation, consensus primary | 0 (≈ 45 min CPU embedding) | 3 h | fixes what the model is shown |
| 3 | `find --compact`, CLAUDE.md v2, guard v2 | 0 | 2 h | the H mechanism, shipped in-session |
| 4 | scorer v2: equivalence + value + cause-of-no-answer; re-score P5–P8 | 0 | 2 h | makes Phase 5 readable |
| 5 | live battery, realistic limits, Sonnet **and** Opus | 40 + 6 probes | 3 h | the number for the morning |
| 5b | variance battery (Sonnet again) — only if budget allows | 20 + 3 | 1.5 h | closes the standing variance item |
| 5c | professor-mode rehearsal: 3 questions exactly his way, no harness, Opus | 3 | 20 min | the demo, rehearsed and timed |
| 6 | portable installer + cold test on `corpus_500` | ≤ 4 | 2 h | "run it on any folder" |
| 7 | findings, handoff, demo pack | 0 | 1.5 h | the morning |

Phases 1–4 are free. If the night is short, the order of sacrifice is: 5b, then 6, then 4's
re-scoring of old batteries (keep the scorer). **Never sacrifice Phase 0, Phase 7, or teardown.**

---

## R. Checkpoint and resume protocol

The night will be interrupted. This protocol makes every interruption cost minutes, not hours.

### R.1 The checkpoint file

`corpus-lab/state/phase9_checkpoint.json` — one object, rewritten atomically (write to `.tmp`, then
`os.replace`) on every change:

```json
{"run_id": "P9-2026-09-15", "branch": "phase9-production-hardening",
 "steps": {"0.1": {"status": "done", "started": "…", "finished": "…", "kv": {}},
           "1.1": {"status": "in_progress", "started": "…"}},
 "last_beat": "2026-09-15T23:41:07", "notes": ["free text, newest last"]}
```

`status` is one of `not_started | in_progress | done | stopped | skipped`. Step ids are the
numbered headings in this file (`0.1`, `1.3`, `5.2`, `5b`, `6.2` …). `kv` holds the counts you
would also put in the `plog` line.

### R.2 The helper — `corpus-lab/bin/p9_checkpoint.py` (built in Phase 0.7, ~80 lines)

| command | does |
|---|---|
| `start <step> [note]` | marks `in_progress`, appends a heartbeat line |
| `done <step> [k=v ...]` | marks `done` with kv, appends heartbeat |
| `stop <step> <reason>` / `skip <step> <reason>` | marks `stopped`/`skipped` with the reason |
| `beat [note]` | appends a timestamped line to `phase9_heartbeat.log` (call it inside your loops at least every 60 s of a long job; long jobs run with `python -u` so their own progress prints also survive) |
| `status` | prints every step with status and timestamps |
| `resume` | prints: last `done` step; any `in_progress` step; then runs the **safety checks** below and prints their results; then prints the exact heading to continue from |

**Safety checks `resume` must run and print** (PASS/FAIL each):
1. rung clean: `harness/corpus_15000/CLAUDE.md` and `.claude` absent — if present **and** the
   `c_stack` state file says installed, print `STALE_INSTALL` (Phase 5 resume handles it; any
   other phase must run `c_stack.py teardown` first);
2. same for `harness/corpus_500` (Phase 6);
3. no stray `claude.exe`/`node.exe` started by a previous battery: `tasklist`/`wmic` filtered —
   print the count; kill only processes whose command line contains `--output-format stream-json`
   **and** the rung path (those are ours), never anything else;
4. `git status --short` empty;
5. the last 5 lines of `progress.jsonl` whose phase is `P9` (so you see what the previous life logged);
6. free disk ≥ 10 GB.

### R.3 Done-checks — a resumed agent verifies, it does not trust

| step | the step is done only if |
|---|---|
| 0.1 | branch exists and is checked out |
| 0.2 | the four self-test commands print 22/22, 10/10, 9/9, 16/16 (re-run them; 2 min) |
| 0.3 | `corpus-lab/state/phase9_baseline_console.txt` exists and contains the 10/17, 52/57 and 11/11 lines |
| 0.4 | `c_shelf_bench.json` has a `baseline_v1` label |
| 0.5 | a `checksums.py` snapshot with label `s7_phase9_pre` exists |
| 0.7 | `p9_checkpoint.py status` runs |
| 1.1 | `c_open_equiv.json` says 300/300 **and** a fresh `open` runs in ≤ 0.5 s |
| 1.2 | `shelf.db` `meta` has key `coverage_cache` and `coverage` runs in ≤ 0.8 s |
| 1.3 | `c_caption_align.json` ≥ 198/200 and the page gate prints ≥ 52/57 |
| 1.5 | `c_shelf_bench.json` has `after_phase1` and every row meets Gate 1 (or the shortfall is recorded) |
| 2.2 | `s7_shelf_v2/shelf.db`, `cards.f16.npy`, `captions_fts.db`, `captions.f16.npy` all exist; `c_shelf_build_v2.json` shows the accounting identity holding — **if `cards.f16.partial.npy` exists the embedding was interrupted: re-run the same build command, it resumes from its checkpoint** |
| 2.3 | `c_shelf_v2_gate.json` has a `verdict` field |
| 3.1–3.4 | the self-test counts 18/18, 25/25, ≥15/15 print; `c_live_battery.py --help` shows `--max-turns` and `--timeout` |
| 4.1–4.2 | `c_score_live_v2.py --selftest` reproduces P8's 1 / 0 / 2-of-3; `c_live_battery_v2__P8_live.json` exists |
| 5.1 | `phase9_live_spec.md` is committed (`git log -- corpus-lab/state/phase9_live_spec.md` non-empty) |
| 5.2 | per model: 20 result `.json` files exist under `_private/results/03_runs/<tag>_live/`, none with `suspended: true`, rung torn down, checksums verified |
| 5.3 | `c_live_battery_v2__P9S_live.json` and `…P9O_live.json` exist with a `gate` field |
| 5c | three files under `corpus-lab/99_scratch/asks/professor_rehearsal/`, each ending with a Sources block or an explicit not-found line, and a timing table in the handoff |
| 6.2 | `setup_folder.py status --folder harness/corpus_500` shows both files, then after uninstall neither |
| 7.x | the named files exist and `git status` is clean |

### R.4 Resuming the long jobs specifically

- **Card embedding and caption embedding (2.2, ~28 + ~14 min)** checkpoint every 20 batches into
  `*.partial.npy/.json` and resume on re-run. Just re-run the same command.
- **Live batteries (5.2, 5b)** resume by construction: `c_live_battery.py` skips every question
  whose result `.json` already exists, and `ask.py` refuses to overwrite. Re-run the identical
  command with the identical `--phase-tag`. Before re-running: (a) `resume` safety check 3 —
  kill only our stray sessions; (b) delete any `<stem>.jsonl` that has **no** matching
  `<stem>.json` (a session killed mid-flight; it never produced a result and will be re-run);
  (c) delete any result whose `suspended` is `true` (the machine slept mid-session — `ask.py`
  detects this from the clock skew; it is a harness failure, not an answer) and record the count
  as `n_rerun_suspended`, pre-registered here; (d) confirm the stack is installed
  (`c_stack.py status`); if the previous life tore it down or never installed it, run `setup`
  with the same `--shelf-dir` the spec names. **Never** delete a completed, non-suspended result
  because of its content.
- **Probes (5.2 step 5)** are cheap; if you cannot tell whether a probe ran, run it again.
- **Checksum verify** can be run any number of times.
- **Phase 6 install** is idempotent per stage (each stage checks for its own output first).

### R.5 What an interruption may never do

Leave the rung installed. Leave a partial result counted. Leave a step marked `done` whose
done-check fails. Reset a gate. If you find any of these on resume, fix the state and write one
`notes` entry saying what you found.

---

## P. The professor's commands — what this whole thing is for

Everything below simulates one person: he opens a terminal in his research folder and asks.
These commands are the ground truth of "does it work". Use them in Phase 5c, in the demo pack,
and any time you want to see the real thing rather than the harness.

```bash
# one-time, by Ali, from the repository root (installs CLAUDE.md + settings.json into the folder)
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py setup --corpus harness/corpus_15000 [--shelf-dir corpus-lab/02_stacks/s7_shelf_v2]

# the professor, interactive -- exactly what he types
cd harness/corpus_15000
claude --model claude-opus-5
> how does sindh's annual development programme look over the last decade or so

# the same thing headless, so an agent can time it and keep the output (stdout to a FILE, never a tail)
cd harness/corpus_15000
"C:/nvm4w/nodejs/node_modules/@anthropic-ai/claude-code/bin/claude.exe" -p "<question>" --model claude-opus-5 --permission-mode bypassPermissions > "../../corpus-lab/99_scratch/asks/<slug>.md" 2> "../../corpus-lab/99_scratch/asks/<slug>.err"

# when finished (Ali, or the agent), remove the two files again
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py teardown --corpus harness/corpus_15000
```

No `--max-turns`, no timeout, no harness. The Python harness (`ask.py`, `c_live_battery.py`)
exists only to capture the stream for the scorers; the professor never sees it. Phase 6's
`setup_folder.py ask` wraps the headless form so the output is never lost.

---

## Phase 0 — baselines, branch, snapshot (free, ≤ 30 min)

**0.1** From `C:\Users\Ali\Desktop\retrieval-lab`:

```bash
git status --short            # must be empty
git checkout -b phase9-production-hardening master
ls harness/corpus_15000/CLAUDE.md harness/corpus_15000/.claude   # both "No such file"
```

**0.2** Reproduce the self-tests. All four must pass at these exact counts or you stop and
report `BASELINE_BROKEN` (do not fix anything; record and end the night).

```bash
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py selftest                # 22/22
.venv/Scripts/python.exe corpus-lab/bin/c_provenance_selftest.py           # 10/10
.venv/Scripts/python.exe corpus-lab/bin/c_stop_guard_selftest.py           #  9/9
cd harness/corpus_15000 && ../../.venv/Scripts/python.exe ../../corpus-lab/bin/c_selftest.py && cd ../..   # 16/16
```

Note: `c_selftest.py` runs from inside the rung; it requires the registry entry for the rung
to exist (it does: `%LOCALAPPDATA%\retrieval-lab\roots.json`). It must not leave any file in
the rung. Check rung cleanliness after it.

**0.3** Reproduce the two offline baselines that Phases 1–3 must preserve. Save the console
output to `corpus-lab/state/phase9_baseline_console.txt`.

```bash
.venv/Scripts/python.exe -u corpus-lab/bin/c_caption_gate.py --channel lex            # document top-10 = 10/17, pool@100 = 16/17
.venv/Scripts/python.exe corpus-lab/bin/c_offline_gate.py --v2 --page-only --query-mode row --caption-channel dense_first   # B2c 52/57
.venv/Scripts/python.exe -u corpus-lab/bin/c_route_gate.py                            # 11/11 and 4/4
```

If any differs from the number in the comment, stop: `BASELINE_BROKEN`.

**0.4** Timing baseline. Create `corpus-lab/bin/c_shelf_bench.py`: runs each of the ten
commands in §1.1 as a **fresh subprocess** (`sys.executable c_shelf.py --db ... --shelf ...`),
three times each, and writes median wall seconds per command to
`corpus-lab/state/c_shelf_bench.json` under a label you pass with `--label`. Use the document
`Sources/Federal/Economic Survey/2018-19/Pakistan Economic Survey 2018-19.pdf` page 5 for `open`
and `inside "…" "development expenditure"`; the generic question
`"how has development spending changed over the last decade"` with rewrites
`"development expenditure"`, `"public sector development programme"`,
`"annual development programme"` for `find`; `series "development expenditure" --family
"economic survey" --from 2014-15 --to 2018-19`. (These strings are generic English; they are
not from the key and they enter a benchmark, not retrieval logic.) Run
`--label baseline_v1`. Expect roughly the §1.1 numbers.

**0.5** Checksum snapshot of the planted files (PowerShell, the env var **only** on this
command):

```powershell
$env:CANARY_MANIFEST = "C:\Users\Ali\Desktop\retrieval-lab\_private\canaries\canary_manifest_pass2.csv"
.venv\Scripts\python.exe corpus-lab\bin\checksums.py snapshot --label s7_phase9_pre
Remove-Item Env:\CANARY_MANIFEST
```

**0.7** Build `corpus-lab/bin/p9_checkpoint.py` exactly as §R.2 specifies (do this **before 0.6** so
the checkpoint exists from the first logged step; the numbering is kept so §R.3 stays stable).
Run `p9_checkpoint.py start 0.1` … `done 0.5` retroactively for the steps above, then
`p9_checkpoint.py resume` and confirm all six safety checks print PASS.

**0.6** `plog` line: `phase=P9 step=0_baseline status=PASS` with the four self-test counts,
the three offline numbers, and the median `open`/`find` seconds. Commit: `Phase 0: baselines
reproduced, timing baseline recorded`.

---

## Phase 1 — latency: make the shelf fast without changing a single rank (free, ≤ 2 h)

**Principle:** every change here is *rank-preserving by construction*. You prove it with
byte-equality and with the Phase 0 offline numbers reproducing exactly. No holdout is needed
because nothing about ranking changes.

### 1.1 `open` in under half a second

Today `do_open` does `SELECT body FROM pages WHERE rel=? AND page_index=?` — a full scan. The
shelf already caches `page_ranges(rel, start_id, end_id)` into `shelf.db` (built once by
`_ensure_page_ranges`) and `_load_doc_pages` already reads a document's pages by rowid range
from `pages_content(id, c0=rel, c1=page_index, c2=body)`.

Change `do_open` to:

```python
_ensure_page_ranges(ctx)
row = ctx.shelf.execute("SELECT start_id, end_id FROM page_ranges WHERE rel=?", (rel,)).fetchone()
if row:
    r = ctx.db.execute("SELECT c2 FROM pages_content WHERE id BETWEEN ? AND ? AND c1=?",
                       (row[0], row[1], page_index)).fetchone()
else:
    r = None
if r is None:   # fall back to the original query so behaviour is identical for any rel not in the cache
    r = ctx.db.execute("SELECT body FROM pages WHERE rel=? AND page_index=?", (rel, page_index)).fetchone()
```

Everything after (the 12,000-char cut, the `_opened.jsonl` log, the printed form) is unchanged.

**Verify:** write `corpus-lab/bin/c_open_equiv_check.py`: sample **300** `(rel, page_index)`
pairs uniformly from `page_ranges` joined to real pages (use the shelf and the FTS db read-only),
fetch the body via the old query and the new path, assert **byte-identical** on all 300. Write
`{"n": 300, "identical": 300}` to `corpus-lab/state/c_open_equiv.json`. Any mismatch → revert
1.1 and record.

### 1.2 `coverage` cached in the shelf

The corpus is read-only for the life of an index. Cache the `coverage()` dict in `shelf.db`
table `meta` under key `coverage_cache` together with the FTS db's size and mtime
(`os.stat(db_path)`). `Ctx.coverage()` returns the cached dict when size and mtime match,
otherwise recomputes and rewrites the cache. Printed COVERAGE line must be **identical** to
today's: `COVERAGE indexed=13634 image_only_no_text=1211 failed=32 unsupported=120 pages=1206260`.

### 1.3 `inside --caption dense_first` from the stored caption vectors

`captions.f16.npy` (89,380 × 384) and `captions_ids.jsonl` (`{"i","rel","page_index"}`) already
exist; `_caption_hit_pages_dense` ignores them and re-embeds. Change it to:

1. On first use per process, build `rel → [(row_i, page_index)]` from `captions_ids.jsonl`
   (cache it as `captions_by_rel.json` next to the npy the first time; ~1 s).
2. Load only the rows for this `rel` from the npy (`np.load(..., mmap_mode="r")`, index the rows,
   cast to float32, re-normalise — the stored vectors are already L2-normalised in f16).
3. Embed **only the query** with the model (that is one `model.embed` call, unchanged).
4. Compute scores against the stored rows in the **same order** as the `captions` table rows
   for that rel. **Alignment matters:** the npy row order is the order `c_caption_embed.py` read
   `SELECT rel, page_index, caption FROM captions`. You must verify alignment before trusting
   it: for **200** random rows, embed the caption text from the `captions` table and check
   cosine with the stored row ≥ 0.98. Write counts to `corpus-lab/state/c_caption_align.json`.
   If fewer than 198 of 200 align, do **not** ship 1.3; record and move on.
5. If a rel has captions in the table but no rows in the npy (added later, or a v2 shelf from
   Phase 2 before its own embeddings exist), fall back to embedding those captions as today.

The median cut and top-3 floor are unchanged. f16 rounding can move ties, so the gate is:

**Gate 1.3 (pre-registered):** `c_offline_gate.py --v2 --page-only --query-mode row
--caption-channel dense_first` must return **52/57 or better** on the dev set, and on the 57
dev addresses' documents the top-5 page sets must be identical to today's on **≥ 54 of 57**.
Write a small `c_inside_equiv_check.py` that runs `do_inside` old-vs-new on those documents
with the `row_words_from_question` terms (this script may read the key: it is a gate script)
and reports the count of identical top-5 sets. Below 54 → revert 1.3.

### 1.4 Never load the embedding model when it is not needed

Assert (in `c_shelf_bench.py`'s output) that `have`, `tables`, `open`, `exact`, `copies`,
`note`, `notes`, `coverage` complete in **≤ 0.8 s** each and never import `fastembed`. If any
does, find and remove the import path.

### 1.5 Re-bench and gate

Run `c_shelf_bench.py --label after_phase1`. **Gate 1 (pre-registered):**

| command | must be ≤ |
|---|---|
| `open` | 0.5 s |
| `find` (question + 3 rewrites, lex) | 3.5 s |
| `inside` dense | 2.5 s |
| `series` 5 editions | 5.0 s |
| `have`, `tables`, `exact`, `coverage` | 0.8 s |

**And** the three Phase 0.3 offline numbers reproduce exactly (`10/17` & `16/17`; `52/57`
or better per Gate 1.3; `11/11` & `4/4`), **and** all four self-tests still pass at their counts.

Any row failing → keep the sub-step that passed its own equivalence check, revert the one that
did not, record which. This gate cannot STOP the night; it can only shrink the speedup.

**1.6** `plog`: `phase=P9 step=1_latency status=PASS|PARTIAL` with before/after medians for
`open`, `find`, `inside`, `series` and the three offline numbers. Commit: `Phase 1: rank-preserving
latency fixes (open, coverage cache, stored caption vectors)`.

---

## Phase 2 — shelf v2: one family per publication, the trusted copy as primary (free, ≤ 3 h)

`c_shelf_build.py` is frozen. **You do not run it and you do not edit it.** You create
`corpus-lab/bin/c_shelf_build_v2.py` as a copy with exactly the three changes below, writing to a
**new** directory `corpus-lab/02_stacks/s7_shelf_v2/`. The v1 shelf stays untouched so every
recorded number still reproduces with `--shelf .../s7_shelf/shelf.db`.

### 2.1 The three changes (no others)

**(a) Bare years become a placeholder.** In `make_family`, after the fiscal-year replacement,
replace any standalone four-digit year `\b(19|20)\d\d\b` with `{yr}`. For a document whose
title/path/page-0 carry **no** fiscal-year token but do carry a bare year `Y`, set
`fy_primary = "Y"` (the four characters) and record `fy_kind = "calendar"` (new column, default
`"fiscal"`). Everywhere the shelf **sorts** editions (`_editions_for_family`, `do_have`,
`do_series`, `_print_find`), sort by a key that maps `"2019"` → `"2019-20"` for ordering only;
display the stored string. This is a generic normalisation, not a corpus string.

**(b) Merge fragment families.** After families are formed (before writing), iterate up to 3
passes: for each family `F` with token list `t` (length ≥ 4), for `k` in 1..3, let
`G = " ".join(t[k:])`. If `G` is an existing family with ≥ 3 tokens **and** `G` has at least as
many members as `F`, reassign every member of `F` to `G` (family field and edition_key
recomputed). Log each merge as `(len(F members) → G)` counts only. Expect roughly 51 merges.
This uses no hand-written string: it is a structural suffix rule.

**(c) Consensus primary.** In the edition-cluster primary choice, replace the sort key
`(-n_pages, -size, len(rel), rel)` with
`(marker_penalty, -n_identical_copies, -n_pages, -size, len(rel), rel)` where
`n_identical_copies` is the number of files sharing that survivor's sha256 (the `dupes` list
length + 1) and `marker_penalty` is 1 if the file's **stem** matches the existing fixed
`MARKER_RE` (draft/copy/old/backup/v2…, the list already in the build script — do not extend it)
and 0 otherwise. Record how many clusters changed primary (expect ≈ 150–170).

### 2.2 Build

```bash
.venv/Scripts/python.exe -u corpus-lab/bin/c_shelf_build_v2.py --out corpus-lab/02_stacks/s7_shelf_v2
```

It must write `shelf.db`, `cards.f16.npy`, `cards_ids.jsonl`, `build_manifest.json` and a
`corpus-lab/state/c_shelf_build_v2.json` report containing: `n_docs`, `n_families`
(expect ≈ 1,300–1,400, down from 1,618), `n_families_merged`, `n_bare_year_families_normalised`,
`n_primary_changed`, the accounting identity `n_docs + n_dupes = 13634`, and the sanity probe.
Card embedding is ~28 min at 7.6 cards/s; it checkpoints — run it in the foreground with
`python -u`.

Then the caption artefacts for v2 (both scripts currently hardcode `s7_shelf`; give each an
optional `--out-dir` whose default preserves behaviour):

```bash
.venv/Scripts/python.exe -u corpus-lab/bin/c_caption_index.py --out-dir corpus-lab/02_stacks/s7_shelf_v2      # ~1 s
.venv/Scripts/python.exe -u corpus-lab/bin/c_caption_embed.py --out-dir corpus-lab/02_stacks/s7_shelf_v2      # ~14 min
```

The v2 shelf also needs the `page_ranges` cache (built on first `inside`) and the Phase 1
`coverage_cache` — both build themselves on first use.

### 2.3 Gate S — no regression, structure improved (offline, dev only, **no holdout**)

`c_offline_gate.py` (lines ~221, ~245, ~821), `c_caption_gate.py` (~85), `c_route_gate.py` (~39)
and `c_selftest.py` (~17) all hardcode `L.STACKS/"s7_shelf"`. Give each an optional `--shelf-dir`
argument defaulting to the current path; the caption channel inside `do_find` finds
`captions_fts.db` and the caption vectors next to whatever `shelf.db` it is given, so v2's own
caption artefacts (built in 2.2) are picked up automatically. Run all three against
`s7_shelf_v2`. Write results to `corpus-lab/state/c_shelf_v2_gate.json`.

Pre-registered readings, **written now, before the build**:

| measure | v1 (Phase 0) | Gate S requires |
|---|---|---|
| document top-10, E1 config, dev | 10/17 | **≥ 10/17** |
| document pool@100, dev | 16/17 | **≥ 16/17** |
| B2c pages, dev | 52/57 | **≥ 52/57** |
| ROUTE absence | 11/11, 4/4 | **11/11, 4/4** |
| gold evidence files that are hidden as non-primary copies (new counter, gate script only) | measure | **must not increase** |
| gold families that are fragments of a larger family (new counter) | measure | **must fall** |

- **PASS** — every row met. Switch production to v2: `c_stack.py` gains `--shelf-dir` (default
  unchanged) and `do_setup` registers whatever it is given; the Phase 5 install uses
  `--shelf-dir corpus-lab/02_stacks/s7_shelf_v2`. Update the registry entry for the rung to v2
  **only inside `c_stack.py setup`**, never by hand.
- **STOP** — any row missed. Production stays on v1. Record the row and the count. Phases 3–7
  proceed on v1. Do **not** tune (a), (b) or (c) to pass; do not re-run with a variant.

Any improvement on the top-10 row is **recorded, not claimed**: one dev set has ±3 noise (F63).

**2.4** `plog`: `phase=P9 step=2_shelf_v2 status=PASS|STOP` with the counts above. Commit:
`Phase 2: shelf v2 (family merge, year normalisation, consensus primary); Gate S <verdict>`.

---

## Phase 3 — show the model the list, and guard the answer properly (free, ≤ 2 h)

### 3.1 `find --compact N` and `--show`

Add to `c_shelf.py find` two optional flags (defaults preserve today's output exactly):

- `--compact N` (default off): print the **top N families as one line each, in fused order**,
  built from shelf fields only, in the exact card shape Experiment H used
  (`c_llm_select_gate.build_cards`): `#i  <family words> | <n> editions <first>–<last> (or
  "single file, pdf") | <best why line, ≤ 120 chars>`. After the list print one line:
  `expand: find "<the same question>" ... --show i,j,k` and then the RECEIPT and COVERAGE lines.
- `--show i,j,k`: recompute the same fused list and print the **verbose** entries (today's
  four-line format, with the `open with:` suggestion) for those indices only. The `open with:`
  suggestion must name the **primary** copy (on v2 the consensus primary) and add the phrase
  `(N other copies hidden; copies "<path>" lists them)` when `n_copies_hidden > 0`.

Unit-test both in `c_selftest.py` (two new checks: compact prints exactly N lines that start
with `#`, and `--show 1` prints the same family as line 1 of compact). Record which the
16 → 18 counts.

**Offline diagnostic, recorded not gated:** with the Haiku rewrites cached in
`state/c_queries.json` and the E1 config, count on the 17 dev questions how often the gold
family is within the top **40** of the fused list (write to `c_shelf_v2_gate.json` or a new
`c_compact_depth.json` as `gold_in_top40_dev`). Expect ≈ 13–14/17 (recall@50 is 14).

### 3.2 CLAUDE.md v2 — the text lives in `c_stack.py` as `CLAUDE_MD_TEMPLATE`

Make these changes and no others. Keep everything else verbatim. Every change must be free of
corpus, title, family, label, or year strings (rule 4).

1. **Section 1, the `find` command** becomes:
   `"{PY}" "{SHELF}" find "<the question as asked>" --fusion {FUSION} --caption-channel {CAPCHAN} --compact 40 --q "<rewrite>" --q "<rewrite>" --q "<rewrite>"`
   followed by this paragraph, verbatim:
   > The list is forty publications, one per line, best-guess first. Read the whole list before
   > choosing. Pick up to three by asking *which kind of publication would print this table* —
   > a statistical yearbook, a budget document, a survey — not by how many of your words appear
   > in the line. Then print their full cards with `--show i,j,k` and confirm the editions with
   > `have`.
2. **Section 2, add one paragraph** after the `series` explanation, verbatim:
   > The figure for a fiscal year is usually printed again, revised, in the next one or two
   > editions. When a question names a year, check the edition for that year and the one or
   > two after it; report which edition and vintage (provisional, revised, final) each figure
   > comes from, and if they disagree show both.
3. **Section 4, add at the end**, verbatim:
   > End every answer with a `Sources` block: one line per figure you used, in the form
   > `<figure> | <path> | p<page_index> | "<the verbatim line>"`. If you found nothing, the
   > `Sources` block says `none — no supporting page was opened` and the answer says so.
   > A number without a Sources line does not go in the answer.

Update `c_stack.py selftest` checks accordingly: the check `claude_md_find_has_frozen_flags`
stays; add `claude_md_find_has_compact_40`, `claude_md_has_sources_block_rule`,
`claude_md_has_vintage_rule`. The round-trip count becomes 25/25. Run it.

### 3.3 Guard v2 — page numbers and the Sources block, still at the answer boundary

Session Log A.2.1 showed the guard passes citations written as *"Title, p.239"* because it only
matches path-like strings. Extend `c_stop_guard.py` **behind an env flag** `STOP_GUARD_V2=1` that
`c_stack.py setup` sets in the hook command (so the recorded P8 behaviour reproduces without it):

- Collect every page reference in the final answer: `\bp\.?\s?(\d{1,4})\b` and
  `\bpage\s+(\d{1,4})\b`. Each cited page number must equal the `page_index` of **some** page
  the session opened (any file). If not, block once with:
  `You cited page {n} but never opened a page with that index. Open it and quote the line, or remove the citation.`
- If the answer contains a `Sources` heading, every `| <path> | p<n>` line in it must match an
  opened `(path, page)` under the same filename-exact/parent-by-suffix rule already in the guard.
- If the answer contains a number with a unit word within 3 tokens (`billion|million|percent|%|Rs|rupees|tonnes|thousand`)
  **and** no `p<n>` reference anywhere **and** no `Sources` block, block once with:
  `Your answer gives figures but cites no opened page. Add a Sources block, or state that no supporting page was opened.`
- Unchanged: block at most once per session; a second stop always passes; never edit text.

Extend `c_stop_guard_selftest.py` from 9 to **≥ 15** behaviour checks including, at minimum:
prose-title-with-page-that-was-opened **passes**; prose-title-with-page-never-opened **blocks**;
figures-with-no-citation **blocks**; an honest "no supporting page was opened" answer with no
figures **passes**; a Sources block whose every line was opened **passes**; a `p.239` written
with the period **is parsed**; an answer citing a fiscal year like `2012-13` and a year `2019`
must **not** be read as page references. Run to all-pass before any battery.

### 3.4 `c_live_battery.py` — realistic limits as flags

Add `--max-turns` (default 25) and `--timeout` (default 300) flags that pass through to `ask.py`
(both are existing `ask.py` flags). Defaults unchanged so P5–P8 remain comparable by construction.

**3.5** `plog`: `phase=P9 step=3_compact_claude_md_guard status=PASS` with self-test counts
(18/18, 25/25, ≥15/15) and `gold_in_top40_dev`. Commit: `Phase 3: find --compact/--show,
CLAUDE.md v2, guard v2 behind STOP_GUARD_V2, battery limit flags`.

---

## Phase 4 — scorer v2: measure what the professor cares about (free, ≤ 2 h)

New file `corpus-lab/bin/c_score_live_v2.py`. `c_score_live.py` is frozen and stays the strict
reference; v2 reports **both** columns side by side and never deletes the strict one.

### 4.1 What v2 adds

1. **`cited_right_page_strict`** — exactly today's rule (import and call `c_score_live`'s
   functions rather than re-implementing; a regression check requires its numbers to reproduce
   exactly on P5–P8).
2. **`cited_right_page_equiv`** — a cited `(file, page)` also counts if that page prints the
   **same cell** — same `series_id`, `vintage_id` and `fy` as a gold evidence address — according
   to the generator's placement records. Locate the placement registry in this order and stop at
   the first that yields `(doc/path, page_index, series_id, vintage_id, fy)` tuples:
   `_private/harness_keys/placed_catalogue.json`, `_private/harness_keys/pdf_index/`,
   `harness/world/series_vintages.json` (`published_in`) joined to
   `harness/world/document_catalogue.json` and the rung's file list, or the generator's
   `resolve_citations.py` logic read as documentation. Budget **45 minutes** to locate and
   validate it: validation = every gold evidence address in the key must itself be reproduced
   by the registry (`n_gold_addresses_reproduced / n_gold_addresses` must be **≥ 0.95**).
   Below 0.95 or over budget → do not ship equivalence; record `EQUIV_REGISTRY_NOT_FOUND` and
   ship items 3–5 only.
3. **`value_correct`** — the answer text contains the key's `expected_answer.value` **or** any
   `acceptable_alternates[].value`, matched as a number with tolerance ±0.5% after stripping
   commas; report which vintage matched. **`value_wrong_confident`** — the answer contains a
   number with the same unit word within 3 tokens of the row label words and no correct value.
   Both are the professor's question: *did I get the right number*.
4. **`no_answer_cause`** — per session: `max_turns` (result has no answer text and `turns ≥
   max_turns`), `timeout` (`timed_out`), `other_empty`, or `answered`. Aggregate counts.
5. **`cited_no_path`** — answers with figures and no path/page citation at all (the "guard
   satisfied by silence" count from F62).

Output: aggregate-only public copy `corpus-lab/state/c_live_battery_v2__<phase>.json`; per-question
booleans (ids only) to `_private/results/04_scores/live_v2__<phase>.json`. **Never** print a
path, value or title from the key.

### 4.2 Regression and re-score

- Self-test: on P8_live, `cited_right_page_strict`, `cited_unopened_total`, and `absence_ok3`
  must equal the recorded values (1, 0, 2/3). Any difference → fix v2, not the record.
- Re-score **P5_live, P6_live, P7_live, P8_live** with v2. Write one table into the phase
  handoff: strict vs equivalence vs value_correct vs no_answer_cause per battery. **Expect** the
  equivalence and value columns to be higher than strict; **expect** 1–5 no-answer sessions
  per battery from the harness caps. Record whatever comes out.

**4.3** `plog`: `phase=P9 step=4_scorer_v2 status=PASS|PARTIAL` with the regression counts and,
per battery, strict/equiv/value/no_answer. Commit: `Phase 4: scorer v2 (equivalence, value,
no-answer cause); P5–P8 re-scored`.

---

## Phase 5 — the live battery under the professor's conditions (paid, Sonnet ≈ $10–20 and Opus ≈ $40–80 reported, ≤ 3 h)

This is the number for the morning. Two batteries of the frozen 20 on the production stack as it
stands after Phases 1–3 (v2 shelf if Gate S passed, else v1), with the harness limits raised to
what the professor actually has: **no practical turn cap and a long clock**.

### 5.1 Pre-register — write and commit `corpus-lab/state/phase9_live_spec.md` before any session

Contents, verbatim into the file:

- Configuration: the production stack after Phase 3; `--max-turns 60 --timeout 900
--parallel 2`; models `claude-sonnet-5` (tag `P9S`) and `claude-opus-5` (tag `P9O`); the frozen
20 (`--group frozen20`); scorer v2 with the strict column alongside.
- Comparability note: P5–P8 ran at 25 turns / 300 s. v2 also reports, per session, whether the
answer was produced **within 300 s** (`wall_s ≤ 300`), so a like-for-like row exists.
- **Gate LIVE-5, per model, on the 17 answerable questions:**
  - **PASS** — `cited_right_page_equiv ≥ 5/17` **and** `cited_unopened_total = 0` **and**
    absence (frozen 3, v2 rule) `≥ 2/3` **and** `no_answer_cause ∈ {max_turns, timeout}` on
    **≤ 1** session.
  - **WEAK** — `cited_right_page_equiv` 3–4/17 with the other three conditions met.
  - **STOP** — otherwise.
  - Also reported, not gated: `value_correct`, `cited_right_page_strict`, L0–L5 from
    `c_live_forensics.py`, `cited_no_path`, median and 90th-percentile wall seconds, cost.
- If the equivalence scorer was not shipped in Phase 4, the gate reads on
  `cited_right_page_strict` with PASS ≥ 4/17 and WEAK 2–3/17 — **written here now so it is not
  chosen after the fact.**
- **Decision table for CLAUDE.md v2** (Phase 3.2): if **both** models read STOP **and** neither
  beats the best recorded strict number (2/17), revert `CLAUDE_MD_TEMPLATE` to its Phase 2 text
  (keep `--compact` code, keep guard v2 code, keep latency and shelf fixes) and record
  `CLAUDE_MD_V2_REVERTED`. Otherwise keep.

### 5.2 Procedure — Session Log C.5, with the changed flags. Never skip a step.

```bash
# 1. exclusivity
ls harness/corpus_15000/CLAUDE.md harness/corpus_15000/.claude        # must not exist
# 2. checksum snapshot (PowerShell, env only on this command) -- label s7_phase9_live_pre
# 3. memory count before: the corpus project key under ~/.claude/projects must have 0 memory files
# 4. install
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py setup --corpus harness/corpus_15000 [--shelf-dir corpus-lab/02_stacks/s7_shelf_v2]
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py status --corpus harness/corpus_15000
# 5. probes, per model: auth (max-turns 1, "Reply with the single word READY."), iso1, iso2 with a FRESHLY generated 16-hex token
.venv/Scripts/python.exe -u corpus-lab/bin/c_live_battery.py --phase-tag P9S --probe auth --model claude-sonnet-5 --probe-question "Reply with the single word READY."
# ... iso1, iso2 exactly as in C.5; then the same three for --model claude-opus-5 with tag P9O
# 6. the batteries, foreground, python -u
.venv/Scripts/python.exe -u corpus-lab/bin/c_live_battery.py --phase-tag P9S --group frozen20 --model claude-sonnet-5 --parallel 2 --max-turns 60 --timeout 900
.venv/Scripts/python.exe -u corpus-lab/bin/c_live_battery.py --phase-tag P9O --group frozen20 --model claude-opus-5   --parallel 2 --max-turns 60 --timeout 900
# 7. verify, quarantine, TEAR DOWN UNCONDITIONALLY
.venv\Scripts\python.exe corpus-lab\bin\checksums.py verify --against s7_phase9_live_pre       # 18 files, 0 changed
.venv\Scripts\python.exe corpus-lab\bin\quarantine_transcripts.py --since <battery start ts> --apply
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py teardown --corpus harness/corpus_15000
ls harness/corpus_15000/CLAUDE.md harness/corpus_15000/.claude        # must not exist
# 8. score -- v2 writes to its own files; the frozen scorer is run too for the strict column
.venv/Scripts/python.exe corpus-lab/bin/c_score_live_v2.py --phase P9S_live --abs-phase P5_live_abs
.venv/Scripts/python.exe corpus-lab/bin/c_score_live_v2.py --phase P9O_live --abs-phase P5_live_abs
.venv/Scripts/python.exe -u corpus-lab/bin/c_live_forensics.py --phase P9S_live --out c_live_forensics_p9s.json
.venv/Scripts/python.exe -u corpus-lab/bin/c_live_forensics.py --phase P9O_live --out c_live_forensics_p9o.json
```

**Traps you must respect:** the auth probe's init event must show the intended model id — if
`claude-opus-5` resolves to anything else, record it and run Opus anyway with whatever the
account gives, naming the resolved id in every table. `c_score_live.py` (the frozen one)
overwrites `state/c_live_battery.json`; if you run it for the strict column, `git checkout HEAD --
corpus-lab/state/c_live_battery.json` afterwards and keep the strict numbers from v2's copy.
`ask.py` refuses to overwrite a result — never `--force`. After the battery, check for stray
`node.exe`/`python.exe` processes before scoring (Appendix D.3: a session once ran 3.4 hours after
its battery was "stopped"). Sessions are capped at 900 s; if a session is still running at
1,000 s, `taskkill /T /F` it and record it as `timeout`.

Expected wall: ~20 sessions × ~3 min / 2 parallel ≈ 30–40 min per model, plus probes.
Call `p9_checkpoint.py beat "P9S n_done=<k>"` after every progress print. **If this phase is
interrupted, resume per §R.4: same command, same tag; the driver skips finished questions.**

### 5.3 Read the gate, write the decision, act on the decision table. `plog`:
`phase=P9 step=5_live_battery status=<per-model verdicts>` with every gated and reported count,
cost, resolved model ids, and time-to-answer medians. Commit: `Phase 5: live battery under
realistic limits, Sonnet and Opus; LIVE-5 <verdicts>`.

### 5b — variance battery (only if cumulative live spend < $40 and the clock allows)

A second Sonnet battery on the **identical** configuration, tag `P9S2`. Same procedure. Report
the spread between P9S and P9S2 on every metric as the project's first measured live variance.
No gate; it is a measurement. `plog` and commit as `Phase 5b: variance battery`.

---

### 5c — professor-mode rehearsal (3 sessions, Opus, ≤ 20 min)

After 5.2's teardown and scoring, install the stack again (`c_stack.py setup`, same `--shelf-dir`),
then run **three** questions exactly as §P shows — plain `claude.exe -p` from inside the rung, no
harness, no caps, stdout and stderr to files under `corpus-lab/99_scratch/asks/professor_rehearsal/`,
timed with bash `time` around each call. The three questions, taken from the Session Log's own
manual probes (public, not in any holdout):

1. *what was the wheat production in punjab in 2015-16* (an honest-negative question: the folder
   holds the national figure only);
2. *has pakistan's tax-to-gdp ratio improved over the last decade, and what should I be careful
   about when comparing the years*;
3. *why do the figures for federal development spending in 2019-20 differ between documents,
   and which should I use*.

Record per question: wall seconds, whether the answer ends with a Sources block, how many
`p<n>` citations it carries, whether the guard log shows a block, and one sentence on what the
answer got right or wrong **by your own reading of the opened pages** (no key involved). Then
**tear down** and confirm the rung is clean. These three files are the demo rehearsal; the
handoff quotes their timings. `p9_checkpoint.py done 5c`; `plog` `step=5c_rehearsal`.

## Phase 6 — one command for any folder (mostly free, ≤ 2 h, ≤ 4 sessions)

Goal: Ali can point this at a fresh folder shaped like the professor's and be asking questions
after one command, on a machine that has Python 3.11, Git for Windows (for `pdftotext.exe`) and
Claude Code.

### 6.1 `corpus-lab/bin/setup_folder.py`

Sub-commands `doctor`, `install`, `status`, `uninstall`, `ask`.

- `doctor` — checks: `.venv` python and the four runtime packages (`numpy`, `fastembed`,
  `onnxruntime`, `pdfplumber`); `pdftotext.exe` at the path `index_build.py` uses; `claude.exe` at
  `labpaths.CLAUDE`; the `BAAI/bge-small-en-v1.5` model present in the fastembed cache (print
  where it is and that first use needs internet if absent); free disk ≥ 1 GB per 2,000 files.
  Prints PASS/FAIL per check, exit 1 on any FAIL.
- `install --folder <path> [--label <name>] [--workers 12]` — in order, each idempotent and
  resumable, each printing wall seconds: (1) `index_build.py --corpus <folder> --db
  corpus-lab/02_stacks/portable/<label>/pages.db --workers N`; (2) `c_shelf_build_v2.py --db …
  --out corpus-lab/02_stacks/portable/<label>/shelf`; (3) `c_caption_index.py` and
  `c_caption_embed.py` with that `--out-dir`; (4) `c_stack.py setup --corpus <folder> --shelf-dir
  …` (which registers the root); (5) prints the COVERAGE line and the number of families.
  **Refuses** to run if `<folder>` is `harness/corpus_15000` (that rung's artefacts are the
  frozen ones) or already has a `CLAUDE.md`.
- `status --folder` and `uninstall --folder` — delegate to `c_stack.py` and remove the registry
  entry; never delete the folder's own files; index artefacts are kept unless `--purge`.
- `ask --folder <path> "<question>" [--model claude-opus-5]` — the professor's command, i.e.
  `cd <folder> && claude.exe -p "<question>" --model <id> --permission-mode bypassPermissions`,
  stdout **redirected to a file** under `corpus-lab/99_scratch/asks/` and echoed, so nothing is
  lost to a `tail` (Session Log A.5.2).

### 6.2 Cold test on `harness/corpus_500`

`corpus_500` is a real rung (500 files, 613 folders, 84 MB). It is a corpus: read-only, and the
two installer files must be torn down at the end.

```bash
.venv/Scripts/python.exe corpus-lab/bin/setup_folder.py doctor
.venv/Scripts/python.exe -u corpus-lab/bin/setup_folder.py install --folder harness/corpus_500 --label corpus_500
```

**Gate P (pre-registered):** install completes in **≤ 20 minutes** wall; `status` shows both
files present; `c_selftest.py` run from inside `corpus_500` passes its checks (record the count;
some checks assume the 15,000 rung's families and may legitimately not apply — list which);
(`c_selftest.py` hardcodes the 15,000 rung's shelf path in `SHELF`; give it optional `--db` and
`--shelf` arguments defaulting to today's values and point them at the portable artefacts);
then **one** headless question with Sonnet through `ask` using a generic question about the
folder's contents that you write yourself without reading any key (e.g. *"which years of
budget documents does this folder hold, and what does the most recent one say about
development spending"*): the answer must cite at least one opened page and the guard log for that
session must show `n_cited_unopened: 0`. If the cold install fails, fix the installer (not the
frozen scripts) and re-run — up to **3** attempts, then record `PORTABLE_FAIL` with the error.
Tear down: `setup_folder.py uninstall --folder harness/corpus_500`, then confirm
`harness/corpus_500/CLAUDE.md` and `.claude` are gone.

### 6.3 `INSTALL_FOR_SIR.md` at the repository root

Plain English, one page, for a non-technical reader with Claude Code and a Max plan:
what to install once (Python venv, Git for Windows, Claude Code), the one `install` command, how
long it takes (measured: 1.2 M pages indexed in 782 s with 12 workers; card vectors ~28 min;
caption vectors ~14 min; for a 15,000-file folder budget about an hour and 8 GB of disk), how to
ask (`cd` into the folder, `claude --model opus`, type the question), what a good answer looks
like (figure, file, page, verbatim line, Sources block), what an honest "not here" looks like,
and the two things the tool cannot see (image-only scans — the COVERAGE line — and files that
failed to parse). Include the Phase 5 numbers as *"in our test folder it cited the right page on
N of 17 questions and refused honestly on M of 3"*, filled in from Phase 5 with the resolved
model ids.

**6.4** `plog`: `phase=P9 step=6_portable status=PASS|PORTABLE_FAIL` with install wall seconds,
file counts, and the cold-test result. Commit: `Phase 6: setup_folder.py installer, cold test on
corpus_500, INSTALL_FOR_SIR.md`.

---

## Phase 7 — write it down for the morning (free, ≤ 1.5 h)

1. **Findings F64–F69** in `corpus-lab/05_findings/FINDINGS_LIVE.md`, one per phase result, in the
   house style (measured, source file, counts, condition). At minimum: F64 latency
   (before/after medians, rank preservation proof); F65 harness caps as a loss source (the
   §1.2 table plus Phase 4's `no_answer_cause` on P5–P8); F66 shelf v2 (counts, Gate S verdict);
   F67 compact find + CLAUDE.md v2 + guard v2 (self-test counts, `gold_in_top40_dev`); F68
   scorer v2 (strict vs equivalence vs value on P5–P8 and P9); F69 LIVE-5 (both models, all
   columns, variance if 5b ran). Every number labelled NEW / LIVE / CORRECTED as the house style
   requires.
2. **`REPORT/08_what_next/HANDOFF_2026-09-16_night.md`** — plain English, counts only, the
   "what the professor would get today, honestly" paragraph rewritten from Phase 5, the boxes
   (keep/adopted/weak/failed/untested), the run record (sessions, cost, holdout looks used = 0,
   contamination events, checksums, memory files, rung clean), and every deviation recorded
   rather than resolved.
3. **`REPORT/08_what_next/DEMO_2026-09-16.md`** — the morning script: the exact commands
   (`cd harness/corpus_15000`, `c_stack.py setup` first, `claude --model opus`), five questions
   to ask in this order with what to point out in each answer — (1) the wheat-in-Punjab absence
   question from Session Log A.1 (honest negative with a citation of what *is* there);
   (2) tax-to-GDP over a decade (A.5.1: comparability flags, vintage tiering); (3) federal
   development spending 2019-20 (A.5.2: three meanings, the perturbed file caught); (4) the
   Sindh ADP decade question (A.3: rebasing, do not splice); (5) one question of the
   professor's own. State the expected wall time per question from Phase 5 medians **and** the three measured
   rehearsal timings from 5c, and link the three rehearsal answer files so Ali can read them
   before he presents. Remind the
   presenter to run `c_stack.py teardown` afterwards, and that the corpus is synthetic: the
   figures are generated, not real.
4. **README status rows**: add one row per new measured result to the big table (latency, shelf
   v2 gate, LIVE-5 per model, variance if run). Keep every existing row; supersede by label,
   never delete. **`REPORT/MANIFEST.md`** — add the new state files with checksums.
5. Copy the new architecture note as an addendum to
   `CURRENT_WORKING_ARCHITECTURE_2026-09-15.md` (H1–H5, dated 2026-09-16 night): boxes, what
   changed in production, what did not, and the one next experiment (see §8 below).
6. Final checks: rung clean; `git status` clean after the last commit; nothing pushed;
   `checksums.py verify --against s7_phase9_pre` → 18 files, 0 changed; memory files in the
   corpus project key = 0; `quarantine_transcripts.py` shows 0 new canary-bearing transcripts
   left in place. `plog`: `phase=P9 step=7_docs status=PASS`. Commit: `Phase 7: findings
   F64–F69, handoff, demo pack, README rows`.

---

## 8. What this plan deliberately does not do, and the one experiment after it

Not re-proposed (all measured, all recorded): more query rewrites; a cross-encoder over cards;
per-query best-rank fusion; captions as a corpus-scale channel (lexical or dense); captions as a
document reranker; a structural or content edition rule; a CLAUDE.md-only citation instruction;
a note-level provenance check; asking the model to *name* the publication.

Not spent: any holdout look. Not touched: any frozen instrument, any recorded number.

**The experiment after this night, if Phase 5 reads WEAK or better:** confirm on holdout-2's last
look — a 30-question live battery on the winning model with the same configuration — with a
gate written before it (PASS ≥ 9/30 `cited_right_page_equiv`, WEAK 6–8). If Phase 5 reads STOP on
both models, the next experiment is the page-first retrieval idea pre-registered in the
2026-09-15 evening addendum (gold page in the top 20 over the whole corpus, ≥ 6/17 dev), which
this plan leaves untouched.

---

## 9. Stop conditions that end the night early — record and stop, do not improvise

- `BASELINE_BROKEN` in Phase 0.
- Any planted-file checksum changes at any verify step (record which label; stop everything;
  tear down; do not score).
- Any isolation probe fails (a session reads the private tree or reveals a fresh token).
- Any memory file appears under the corpus project key.
- A battery passes its reported-cost cap in rule 12 (Sonnet $20, Opus $80) — stop that battery only, per rule 12.
- You find yourself wanting to change a gate, a denominator, a bar, or a frozen script. Write
  down what you wanted to change and why in the handoff, and do not change it.
