# EXECUTE — trust and reproducibility night, 2026-09-16 → 2026-09-17

*Written 2026-09-15/16 by a Fable planning session after an independent audit of the 2026-09-15
night run: the orchestrator brief, both live scorer files and their per-question rows, all 34
live transcripts, the guard log, the answer key (through the scoring scripts only), the
installer, the builders, and `labpaths.py`. Every number in §1 was recomputed from disk.
Finalised after Ali's review; his decisions are folded into §2.*

**You are an executing agent (Sonnet or Opus). You run this file top to bottom, one phase at a
time, unattended, overnight. The priority order is fixed and is the tie-breaker for every
judgement call:**

> **trustworthy measurement → production-aligned portable → reproducibility →
> documentation and auditability → variance testing.** Not higher retrieval scores.

You do not change retrieval, ranking, the shelf, the captions, the prompt, or the guard's
behaviour. You do not tune anything. Every gate is a number written before the run. Where a
choice is open, it is made for you. **If the clock runs short, optional model calls are cut
first (§3 clock rule); documentation is never cut.**

**Run one fresh agent context per phase.** `/clear` between phases; re-read only §0, §D and the
phase you are on.

> ### ⏯ Starting or RESUMING — do this first, every time
>
> 1. `git branch --show-current` must be `phase10-trust-and-repro`; create it off
>    `phase9-production-hardening` (head `1e7c7b3` or later) only if it does not exist. If
>    `git status --short` is dirty, commit as `WIP (resumed): <files>`; never discard.
> 2. `.venv/Scripts/python.exe corpus-lab/bin/p9_checkpoint.py resume --file corpus-lab/state/phase10_checkpoint.json`
>    (Phase 0.2 gives the helper a `--file` argument; its default stays the old file so every
>    Phase 9 command still reproduces). It prints the last completed step and where to continue.
> 3. Run the done-check of the interrupted step. Pass → mark done, move on. Fail → redo from its
>    start. Never redo a step whose done-check passes; never skip one that fails.
> 4. If the interrupted step was a live battery, re-run the same command with the same tag; the
>    driver skips finished questions. Teardown first if the rung is not clean.

---

## 0. Fixed rules — read before Phase 0 and before every phase

Rules 1–13 of `plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md` §0 apply
unchanged: read-only corpora; teardown on every exit path; gates written before numbers exist;
the contamination rule (no hand-written title, family, caption, label, synonym, publication
name or year string enters code or CLAUDE.md; only gate and scoring scripts open `_private/**`);
zero holdout looks; frozen instruments; one `plog` line per step; never push; `.venv` python and
`claude.exe` only; headless calls from a cwd outside the repo; no Windows paths in bash
heredocs; checkpoint discipline. Five rules are added:

14. **The production and demo path is frozen for the whole run.** Ali demos in about two days
    with `c_stack.py setup --corpus harness/corpus_15000`, the v1 shelf at
    `corpus-lab/02_stacks/s7_shelf`, `CLAUDE_MD_TEMPLATE` in `c_stack.py`, and the guard with
    `--v2`. None of these may change behaviour. Phase 0 checksums the s7_shelf artefacts; Phase 5
    verifies them. Any diff is a stop condition. Additive, default-preserving flags are the only
    permitted edits to `c_stack.py`, `c_stop_guard.py`, `c_shelf.py`, `c_live_battery.py`,
    `setup_folder.py`, `c_selftest.py`, and each is listed in the handoff.
15. **Nothing recorded is overwritten.** Every scorer, builder and battery writes to a new file
    named for its version and phase tag. When a new number replaces an old one, the old file
    stays untouched and the new file carries `supersedes: <path>`; a sibling
    `<old>.SUPERSEDED.md` (one paragraph: by what, why, where) is added next to the old file.
    Corrections are appended to `REPORT/08_what_next/CORRECTION_2026-09-16.md`; no earlier
    report body is edited — a one-line pointer at its top is the only permitted change.
16. **Every important run carries a run record** (§D). No battery, build, gate or re-score
    starts without `run_record.py start`; none is reported without `run_record.py finish`.
17. **Answer-key, scorer and benchmark changes are versioned.** `answer_key.json` is never
    edited. New keys are new files with a date in the name. Every scorer output names its
    scorer version, key file and key sha256, and the frozen-20 group definition it used.
18. **One recording, many scorers.** A live session is run once and recorded once. Every scorer
    (v1 strict, v2, v3 with either key) derives from that recording. No model call is ever made
    to score.

**Branch:** `phase10-trust-and-repro` off `phase9-production-hardening`. One commit per numbered
sub-step, message prefixed `Phase 10.N.M:`. Commit every gate spec before the run it governs.

**Frozen for this run, beyond rule 6:** `c_score_live_v2.py`, `c_shelf_build_v2.py`,
`c_stop_guard.py` behaviour, and — from the moment it is tagged in Phase 1.8 —
`c_score_live_v3.py`.

---

## 1. The diagnosis this plan acts on (recomputed 2026-09-15 from the recorded transcripts)

### 1.1 `value_correct` 5/17 was a denominator error

12 of the 17 dev answerable questions carry no numeric `expected_answer.value` and no
alternate with a value (all `tr_*`, `mb_*`, `rc_*`, `rl_*`, `sd_*`). `accepted_values()` returns
an empty list, so `value_correct` can never be true for them. Both models scored the same 5
right and the same 12 "wrong" because the split is a property of the key. On the 5 keyed
questions both models were 5/5. The claims "reads the number wrong on 12 of 17" and "4 of 4
wrong totals on decade questions" are unsupported. They appear in
`ORCHESTRATOR_BRIEF_2026-09-16.md` §3 and §7, `DEMO_2026-09-16.md`, `HANDOFF_2026-09-16_night.md`.

### 1.2 `cited_unopened_total` (Sonnet 1, Opus 7) was mostly the scorer

| counted case | what the transcript shows |
|---|---|
| Opus `pl_01`, 3 | pages opened inside a bash `for spec in ...` loop; `opens_from_bash` captures the loop variable `$f` as the path; the tool output carries `OPENED <path> p<N>` for each |
| Sonnet `mb_07`, 1 | same loop blindness, plus `answer_paths` swallows a markdown bullet (`- file.pdf`) into the path |
| Opus `sd_05`, 2 | two CSV filenames mentioned in prose ("this file is older than that one"), no page, no figure: mentions, not citations |
| Opus `mb_04`, 2 | **real**: two table lines quoted from `tables`/`inside` output without `open`; the guard challenged one; the session ended without opening it |

Corrected: Sonnet 0, Opus 2 (one session), zero fabricated. Recomputing the equivalence column
with loop opens credited leaves it at 13 and 14. The headline is robust; the STOP column was not.

### 1.3 The guard was right every time, and it shapes what gets scored

The guard blocked once in 20 of 34 sessions (Sonnet 11, Opus 9). Each challenge was checked
against the opens preceding it in the transcript: all 20 were genuine (a path cited from
`series`/`inside`/`tables` output before `open`). In every case but Opus `mb_04` the model then
opened the page and confirmed. **In 5 Sonnet sessions the recorded `answer_text` is only the
post-guard reply** ("Confirmed — the citation stands. Updated Sources line: …") because the
harness keeps the last assistant message. The scorer scored the fragment.

### 1.4 The portable is not portable, and ships the wrong builder

`setup_folder.py install` runs scripts from `labpaths.BIN` (the dev repo), writes artefacts to
`corpus-lab/02_stacks/portable/<label>/` (the dev repo), and builds the shelf with
`c_shelf_build_v2.py` — the builder that failed Gate S — while production and the demo run the
v1 shelf. There is no requirements file. `labpaths.py` resolves its root from `__file__`, so a
copied `bin/` would work, but it has never been run that way. `c_selftest.py` hardcodes the
15,000 rung's shelf path. Structural outputs carry wall-clock fields (`indexed_at`, `built_at`,
`timing_s`), so raw artefact hashes never match between two installs. **Last night's Phase 6
cold test on corpus_500 therefore validated the experimental v2 shelf, not production, and is
superseded for any production-portability claim.**

### 1.5 What is solid and must stay solid

Latency rows, rank preservation (300/300, 200/200, 57/57), shelf v2 gate numbers, equivalence
registry validation (0.970), the 13/17 and 14/17 equivalence hits, the checkpoint log, the clean
corpus, and the three rehearsal answers. Reproduced from disk; not to be touched.

---

## 2. Decisions already taken (do not reopen them)

1. **Scorer v3 changes no recorded verdict.** Phase 9's gates were scored by the pre-registered
   v2 scorer and stay STOP. v3 re-scores the same recordings into new files; the report shows
   v2 and v3 side by side with the reason for each difference. The audit's predictions (§1.2)
   are v3's regression gate. **If v3 disagrees with the audit, that is a finding to record, not
   something to tune away.**
2. **"Matching artefact hashes" is defined on canonical logical exports, not raw files.** SQLite
   files carry timestamps and walk order. Gate R1 hashes a canonical export (sorted rows,
   wall-clock fields removed), compares vectors numerically, and compares retrieval outputs on a
   fixed query list. Any unexplained difference fails; explained differences are reported.
3. **There is no genuine independent economics folder tonight, and none is manufactured.**
   Every rung under `harness/` comes from the same generator. `corpus_2000` is the second
   portability rung and is described everywhere as *another generated corpus from the same
   fixture ecosystem, not real-world validation.* **Genuine real-world cross-folder
   generalisation remains untested after this run**, and that sentence goes verbatim into the
   correction note, `INSTALL_FOR_SIR.md`, the morning note and the handoff. The independently
   designed adversarial synthetic "professor folder" test is the next experiment, to be designed
   and pre-registered on its own (§6).
4. **The portable ships the v1 builder by default.** `setup_folder.py install` gains
   `--builder v1|v2`, default `v1`; `v2` prints `EXPERIMENTAL SHELF V2 — failed Gate S
   2026-09-15; not production` and writes `builder: v2 (experimental)` into the manifest, so it
   can never be used silently.
5. **Variance is Sonnet ×3 and Opus ×1, optional second Opus under §4.4 only.** No tuning
   between runs. Tiny Sonnet-versus-Opus differences are not interpreted.
6. **Keys for the 12 unkeyed questions are derived from the generator's placement registry by a
   scoring script, never by hand.** Graded as vectors, reported not gated. No "reads numbers
   wrong" sentence is written anywhere until that measurement exists, and then only in the fixed
   wording of Phase 2.3.
7. **No retrieval work.** No new ranker, no B2c change, no shelf v2 experimentation, no prompt
   change from live results, no holdout look.
8. **Documentation is done inside each phase, not at the end.** `run_record.py` and
   `docs_check.py` are built in Phase 0; each phase writes its own experiment README before its
   commit. Phase 5 only assembles the morning note and the handoff.

---

## 3. Phase map, order, budget, clock

| phase | what | cost | clock | gate |
|---|---|---|---|---|
| 0 | branch, baselines, checksums, run-record + docs-check helpers, pins | free | ≤ 1 h | `BASELINE_BROKEN` stops |
| 1 | scorer v3 + full-answer capture + regression tests + re-score P5–P9; **freeze and tag** | free | ≤ 3 h | **Gate T** |
| 2 | versioned key v2 for unkeyed questions + vector value metric | free | ≤ 1.5 h | reported |
| 3 | portable package, manifest, two clean-room builds, corpus_2000 rung | free + 1 ask | ≤ 3.5 h | **Gates R1, R2, R3** |
| 4 | variance batteries on the frozen stack | Sonnet ≤ $45, Opus ≤ $40 | ≤ 4.5 h | none; pre-registered decision rule |
| 5 | morning note, handoff, final checks | free | ≤ 1 h | **Gate D** |

Order is fixed. **v3 is committed and tagged before any Phase 4 probe runs**, so every new
battery is scored by v2 (continuity) and v3 (trust) from one recording, and v3 cannot be changed
by anything Phase 4 shows.

**Live budget:** ≤ 94 sessions (4 batteries × 20 + 12 probes + 1 cold-test ask + optional
20 + 3). Reported cost caps (`cost_usd` from `ask.py`): Sonnet **≤ $45** across its three
batteries (do not start the third if the first two exceed $30); Opus **≤ $40** for P10O1 (after
6 sessions project `cost × 20 / 6`; if > $40 stop and score the partial with its denominator);
everything else **≤ $10**; **$95 total, hard.** Holdout looks: **0.**

**Clock rule.** Phase 5 needs one hour and must run. Before launching any battery, compute
`remaining = deadline − now − 1 h`; a Sonnet battery needs 50 min, Opus 60 min, each including
probes, verify and teardown. Do not launch a battery that does not fit. Cut in this order:
optional P10O2, then P10O1, then P10S3, then P10S2. Never cut Phase 5, never cut a README, never
cut a run record. Record every cut with `run_record.py note` and in the handoff. Deadline: the
time Ali wrote into `corpus-lab/state/phase10_deadline.txt` (Phase 0.1 reads it; if absent, 08:00
local on 2026-09-17).

---

## R. Checkpoint and resume

Same protocol as Plan D §R, with `corpus-lab/state/phase10_checkpoint.json` and heartbeat
`corpus-lab/state/phase10_heartbeat.log`. Done-checks are listed inside each phase. Long jobs
(`index_build.py`, the builders, the batteries) are resumable by re-running the same command.

---

## D. The documentation standard — mechanisms, not intentions

Ali's standard: *if the repo, the portable package and a corpus are handed to another competent
person, they can reproduce the build and see exactly where every headline number came from,
without this chat or Ali's memory.* Each requirement names the mechanism that enforces it;
`docs_check.py` (Phase 0.4) verifies the mechanisms and Gate D is its exit code.

| requirement | mechanism |
|---|---|
| branch + exact commit, dirty/clean, exact commands, configs, dependency and runtime versions, model ids, embedding model, seeds, corpus identity and counts, artefact and canonical hashes, start/finish, retries/timeouts/errors/contamination/manual steps, conclusion and adoption | `corpus-lab/bin/run_record.py` writes `run_record.json` beside each run's outputs: `git rev-parse HEAD`, branch, dirty flag, full `argv` and working directory, env overrides in force, `python -V`, versions of `fastembed onnxruntime numpy pdfplumber`, `claude.exe --version`, resolved model ids from the auth probe, `BAAI/bge-small-en-v1.5` and the sha256 of its cached model file, `--workers`, `OMP_NUM_THREADS`, `PYTHONHASHSEED`, rung name + file count + checksum label, sha256 of every declared input and output, `notes[]` (appended by `run_record.py note`), and `conclusion` / `adopted` set by `finish` |
| pre-registered gates before results are read | every gate spec is a committed file `corpus-lab/state/phase10_*_spec.md`; the run record stores the spec's commit hash and `docs_check.py` fails if that commit's author date is later than the run's `started_at` |
| raw kept, derived separate | raw transcripts stay in `_private/results/03_runs/<tag>/`; per-question scores in `04_scores/`; aggregates in `corpus-lab/state/`; no script writes derived numbers into a raw directory |
| nothing silently overwritten | rule 15; `run_record.py finish` refuses if a declared output already existed at `start` unless `--supersedes <path>` was given, and then writes the `.SUPERSEDED.md` sibling itself |
| scorer / key / benchmark versioning | rule 17; every scorer output carries `scorer_version`, `key_file`, `key_sha256`, `group_definition_sha256` |
| machine-readable manifest + plain-English build report | `build_manifest.json` and `BUILD_REPORT.md` written by `setup_folder.py install` (Phase 3.2) |
| one README per experiment | `corpus-lab/experiments/<id>/README.md` with fixed headings *Purpose, Method, Inputs (paths + sha256), Outputs (paths + sha256), Gate (spec + commit), Result, Adopted?, Run record, What this does not show* |
| deterministic defaults, explicit non-determinism | portable install defaults `--workers 8`, `OMP_NUM_THREADS=4`, `PYTHONHASHSEED=0`, all recorded; `BUILD_REPORT.md` names the known non-deterministic fields (directory walk order, timestamps, float embeddings) and how R1 neutralises each |
| clean-room reproduction | Gate R1: two installs from `%TEMP%` copies of the package, fresh venvs, all `*_ROOT`/`LAB_PRIVATE` env vars unset and asserted unset, corpus project key with 0 memory files before and after, and an open/scandir trace proving no read from the dev repo (R3) |

---

## Phase 0 — branch, baselines, protection, helpers (free, ≤ 1 h)

**0.1 Branch, deadline, baseline.** Create the branch. Read `phase10_deadline.txt` (§3). Run the
four self-tests and the three offline baselines exactly as Plan D Phase 0.4 lists them; they must
reproduce (25 / 10 / 24 / 18 and 10/17, 16/17, 52/57). Any miss → `BASELINE_BROKEN`, stop.

**0.2 Checkpoint helper.** `p9_checkpoint.py --file` (default: old path). Start the new file.

**0.3 `corpus-lab/bin/run_record.py`** (~150 lines): `start --id <id> --out <dir> [--reads
<path>...] [--writes <path>...] [--spec <spec file>]`, `note <id> "<text>"`, `finish <id>
[--supersedes <path>] [--conclusion "<text>"] [--adopted yes|no|n/a]`. Writes the §D fields.
Self-test on a temp dir: every field present; `finish` refuses to clobber; `--supersedes` writes
the sibling.

**0.4 `corpus-lab/bin/docs_check.py`** — exit 1 if any of: a `run_record.json` created after
Phase 0's start lacks a §D field or has no `finish`; an experiment README under
`corpus-lab/experiments/` lacks a fixed heading; a run record's spec commit is dated after the
run's start; a state or score file written tonight shares a path with a pre-existing file
(compares against a file list snapshot taken now, `corpus-lab/state/phase10_preexisting_files.txt`);
a scorer output lacks `scorer_version` or `key_sha256`. Self-test: a temp tree with one
deliberate omission of each kind must fail with the reason named.

**0.5 Pins.** `corpus-lab/requirements-portable.txt` from the live venv: `fastembed==0.8.0`,
`onnxruntime==1.30.0`, `numpy==2.4.6`, `pdfplumber==0.11.10`, plus their `pip freeze`
dependencies; header comment `# python 3.11.5, claude code 2.1.257`.

**0.6 Protect the demo path.** `checksums.py snapshot` over `corpus-lab/02_stacks/s7_shelf/*`
and the planted files in `harness/corpus_15000`, label `s7_phase10_pre`. Confirm
`harness/corpus_15000/CLAUDE.md` and `.claude` do not exist.

**0.7** README `corpus-lab/experiments/p10_phase0_helpers/README.md`. `plog P10 0_baseline
PASS`; commit `Phase 10.0: baselines, run_record, docs_check, pins, snapshot`.

**done-check:** branch exists; both helper self-tests pass; requirements file present; snapshot
label present; pre-existing file list present.

---

## Phase 1 — a scorer you can trust, then freeze it (free, ≤ 3 h)

New file `corpus-lab/bin/c_score_live_v3.py`. v1 and v2 untouched. v3 imports v2 for the registry
and value logic and overrides exactly the four things below. Outputs:
`corpus-lab/state/c_live_battery_v3__<phase>[__keyv2].json` (aggregate) and
`_private/results/04_scores/live_v3__<phase>[__keyv2].json` (per question). Every output carries
`scorer_version: "v3"`, the v3 file's own sha256, `key_file`, `key_sha256`,
`group_definition_sha256`, and the source recording paths.

### 1.1 Opens from ground truth, not from the command string

`opened_pairs(transcript)` = union of: every `OPENED <rel> p<N>` line in any tool result (what
`c_shelf.py open` prints, `c_shelf.py:1262`); every `open "<rel>" <N>` the v1 regex finds (kept so
old transcripts score); and `files_opened` from the hook record. Report `n_opens_from_output`,
`n_opens_from_command`, `n_opens_loop_only` (in output, in no command string).

### 1.2 A citation is a path with a page; a mention is not

`citations(answer)` = every `<path> | p<N>` Sources-line pair plus every path within 40
characters of a `p<N>` / `page N` token. `mentions(answer)` = path-like strings that are not
citations. Path extraction strips leading markdown bullets, backticks, quotes, asterisks.
`cited_unopened` counts citations only; `mentioned_unopened` is a separate reported field.

### 1.3 The complete answer across a guard interruption

`c_live_battery.py` gains `--capture full` (default `last`, unchanged). With `full` the record
stores `answer_text_last` (today's field) and `answer_text_full`: the assistant text blocks after
the last tool result **plus**, when a Stop-hook block occurred, the assistant text blocks
immediately preceding that block, in order. One function `reconstruct_full_answer(raw_path)` in
v3 derives the same thing from any jsonl, and is used for both live and recorded sessions so the
two paths cannot diverge. v3 scores the full text and reports `answer_was_fragment`.

### 1.4 Denominators

`value_correct` is reported as `k / n_keyed`, `n_keyed` = questions with `n_accepted_values > 0`.
Unkeyed questions get `value_scorable: false` and are in no value denominator. Same for
`value_wrong_confident`. Every count in every aggregate names its denominator explicitly.

### 1.5 Regression tests — `corpus-lab/tests/test_score_live_v3.py`

Synthetic minimal transcripts written by the test (invented paths, no private data). One test
per audited bug, named for the transcript that exposed it:

| test | fixture | expected |
|---|---|---|
| `loop_open_is_an_open` (P9O pl_01) | bash `for` loop whose tool result carries two `OPENED` lines | `cited_unopened == 0`, `n_opens_loop_only == 2` |
| `bullet_does_not_join_path` (P9S mb_07) | Sources line beginning `- file.pdf \| p3` | path parsed as `file.pdf` |
| `mention_is_not_citation` (P9O sd_05) | prose "`a.csv` is older than `b.csv`" | `cited_unopened == 0`, `mentioned_unopened == 2` |
| `fragment_answer_is_completed` (P9S tr_10) | full answer, guard block, "Confirmed — the citation stands" reply | `answer_was_fragment`; full-answer citations scored |
| `unkeyed_value_not_in_denominator` (tr_04) | question with `value: None` | `value_scorable == False`, absent from `n_keyed` |
| `series_output_is_not_an_open` (P9O mb_04) | `series`/`tables` output naming a page, no `OPENED`, answer cites it | `cited_unopened == 1` — this stays a defect |
| `v2_parity_on_clean_transcript` | plain opens, no guard, keyed value | v3 == v2 on every shared field |

`.venv/Scripts/python.exe -m pytest corpus-lab/tests -q`. All pass before 1.6.

### 1.6 Re-score every recorded battery, v2 and v3 side by side

For `P5_live`, `P6_live`, `P7_live`, `P8_live`, `P9S_live`, `P9O_live` (abs-phase as recorded):
run v3, then write `corpus-lab/state/c_rescore_v2_vs_v3.json` with, per phase, v2 and v3 values
of `cited_right_page_strict`, `cited_right_page_equiv`, `cited_unopened_total`,
`mentioned_unopened_total`, `value_correct` as `k/n_keyed`, `n_answer_fragments`,
`n_opens_loop_only`, and for every per-question difference a one-line `why`. Under
`run_record.py` with `--reads` the six recordings and the key, `--spec` the Gate T spec.
**These are corrected analytical metrics. The Phase 9 verdicts (STOP under v2) are restated as
they stand in the same file, under `historical_verdicts_unchanged`.**

### Gate T (pre-registered; commit `corpus-lab/state/phase10_gate_t_spec.md` before 1.6)

- all seven regression tests pass;
- v3 on `P8_live` reproduces v2's `cited_right_page_equiv` and `cited_unopened_total` exactly
  (P8 has no loop opens and no fragments);
- on `P9S_live` and `P9O_live`, v3 `cited_right_page_equiv` is within **±1** of v2 (13, 14);
- v3 `cited_unopened_total` reads **Sonnet 0, Opus 2**, both Opus counts in `mb_04`;
- `value_correct` reads **5/5** for both P9 batteries, `n_keyed == 5`.

Any row missed → `GATE_T_STOP`, record which row and the actual values, **do not touch v3**,
continue. v3 is then reported as "diverges from the independent audit on <row>" and Phase 4
scores with both v2 and v3 regardless.

### 1.7 README `corpus-lab/experiments/p10_scorer_v3/README.md` (§D headings).

### 1.8 Freeze

Commit `Phase 10.1: scorer v3, full-answer capture, regression tests, re-score; Gate T
<verdict>`. Then `git tag scorer-v3-frozen-2026-09-16` on that commit and record the tag and the
v3 sha256 in `corpus-lab/state/phase10_scorer_freeze.json`. **From this point `c_score_live_v3.py`
is a frozen instrument (rule 6).** Any later defect found in it is recorded in the handoff for a
v4; it is not fixed tonight.

**done-check:** tests pass; six `live_v3__*.json` exist; `c_rescore_v2_vs_v3.json` exists; tag
exists; spec commit precedes the re-score run record.

---

## Phase 2 — a versioned key for the questions that have none (free, ≤ 1.5 h)

Only `c_key_v2_build.py` (new; a scoring script under rule 4) opens the key and the registry.
You do not read either by hand.

**2.1** For every dev question with `n_accepted_values == 0`, derive `expected_vector` from the
generator's `pdf_index` cells at the question's `evidence_addresses`: trajectories → `fy →
[values across vintages]` for the named `series_id`; multi-branch → one entry per branch
`series_id` and `fy`; reconciliation → both printed values, and which the key marks correct;
relationship and stale-document questions → `value_scorable: false` with the reason "text
question". Write `_private/harness_keys/answer_key_v2_2026-09-16.json`: the original questions
byte-for-byte plus the new fields, a `derived_from` block naming the pdf_index files, and
`base_key_sha256`. **Never edit `answer_key.json`.**

**2.2** v3 (frozen) already accepts `--key <file>` (build it in 1.x — it is part of v3's
interface, not a change after freezing). With key v2 it reports `vector_coverage` per scorable
vector question (fraction of expected years whose value, any listed vintage, ±0.5%, appears in
the answer) and `vector_full` (fraction == 1.0); aggregate `vector_full k/n_vector`.

**2.3** Re-score `P9S_live` and `P9O_live` with key v2 into `__keyv2` files. **Reported, not
gated.** The only permitted sentence about it, anywhere: *"On the N trajectory and multi-branch
questions, the answer carried every expected year's value on k of N (Sonnet) and m of N
(Opus), scored by v3 against key v2 (sha …). This is the project's first measurement of table
reading; there is no earlier number to compare it with."*

**2.4** README `p10_key_v2`. `plog`; commit `Phase 10.2: versioned key v2, vector value metric`.

**done-check:** key v2 exists, sha256 in the run record; both `__keyv2` score files exist.

---

## Phase 3 — the portable: production-aligned, then proven (free + 1 ask, ≤ 3.5 h)

### 3.1 The package — `corpus-lab/bin/make_portable.py`

Writes `dist/retrieval-portable-<commit7>/`: `bin/` from an explicit allowlist (`labpaths.py`,
`scoring.py`, `index_build.py`, `c_shelf.py`, `c_shelf_build.py`, `c_shelf_build_v2.py`,
`c_caption_index.py`, `c_caption_embed.py`, `c_stack.py`, `c_stop_guard.py`, `c_selftest.py`,
`setup_folder.py`, `run_record.py`, and whatever they import — verified by running the install in
the clean room, not by guessing); `requirements-portable.txt`; `INSTALL.md` (from
`INSTALL_FOR_SIR.md`, path-free); `PACKAGE_MANIFEST.json` (commit, branch, build time, sha256 per
file, the allowlist, `default_builder: v1`). No `02_stacks`, `_private`, `state`, `99_scratch`.
`grep -rn "C:\\\\Users\|Desktop" dist/` returns nothing; `labpaths.py`'s hard-coded RASHIP
default becomes `None` when the env var is absent.

`setup_folder.py` gains: `--builder v1|v2` (default **`v1`**, §2.4 message for v2);
`--artefacts <dir>` (default: old location); `--seed-env` (sets and records `PYTHONHASHSEED=0`,
`OMP_NUM_THREADS=4`); `--workers` default unchanged. `c_selftest.py` gains `--db`, `--shelf`.
`c_stack.py setup` is unchanged.

### 3.2 Manifest, build report, canonical export

At the end of `install`, into the artefacts dir: `build_manifest.json` (package commit,
`builder`, dependency versions, embedding model id + cached-file sha256, workers, seeds, corpus
root, file count, per-status counts, families / editions / duplicates / captions / card-vector
rows, sha256 of every artefact, warnings, per-step and total wall); `BUILD_REPORT.md` (same, plain
English, one page, naming the non-deterministic fields); `canonical_export.json` — the `docs`,
`families`, `editions`, `dupes`/duplicate groups, `captions` tables and the page-index status
table as **sorted rows with `built_at`, `indexed_at` and every timing field removed**, plus
`vectors_card.sha256` and `vectors_caption.sha256` over the stores rounded to 3 decimals.

### 3.3 Gate R1 — two genuinely clean builds, same corpus, same logical result

Pre-register `corpus-lab/state/phase10_gate_r_spec.md` (all three R gates, including the fixed
query list below) and commit it before any clean-room command.

Twice, A then B, each from scratch in its own `%TEMP%\p10_clean_<X>`:

```
copy dist\retrieval-portable-<commit7>\  →  here
python -m venv .venv  &&  .venv\Scripts\pip install -r requirements-portable.txt
unset CORPUS_LAB_ROOT RETRIEVAL_LAB_ROOT LAB_PRIVATE HARNESS_ROOT RUNS_ROOT SCORES_ROOT HARNESS_KEYS  (assert, log)
copy harness\corpus_500  →  .\corpus   (a copy; the rung is never touched)
memory files under the copy's project key: assert 0
.venv\Scripts\python.exe bin\setup_folder.py doctor
.venv\Scripts\python.exe -u bin\setup_folder.py install --folder .\corpus --artefacts .\artefacts --seed-env --workers 8
.venv\Scripts\python.exe bin\c_selftest.py --db .\artefacts\pages.db --shelf .\artefacts\shelf\shelf.db
.venv\Scripts\python.exe bin\c_shelf.py <fixed query list, §3.3a>  → .\retrieval_outputs.json
.venv\Scripts\python.exe bin\setup_folder.py uninstall --folder .\corpus
memory files under the copy's project key: assert 0
```

Both under `run_record.py`. **The A and B artefact directories, venvs and corpus copies are
distinct paths; nothing from A is readable by B** (delete A's venv and artefacts only after both
comparisons are written).

**3.3a Fixed retrieval probe list** (written into the spec before the builds; generic wording,
no publication names): 20 `find` queries such as *"development spending by year"*, *"tax
revenue table"*, *"which years does the folder cover"*, *"production of a major crop over
time"*; 5 `inside` calls on the first primary document of the five largest families (chosen by
a rule, `ORDER BY n_members DESC, family_id`); 3 `series` calls; `coverage`; `have` on the two
largest families. Outputs captured as JSON (rank lists of `rel, page_index, score`).

**Gate R1 PASS** iff every line holds:

| check | rule |
|---|---|
| both installs exit 0, each ≤ 20 min | fail otherwise |
| `canonical_export.json` sha256 A == B | **any** difference fails; the first differing table and row is named |
| `build_manifest.json` counts (files, statuses, families, editions, duplicates, captions, card rows) A == B | fail otherwise |
| vectors A vs B | sha256 equal → "deterministic"; else per-row cosine mean ≥ 0.9999 and min ≥ 0.999 → "deterministic up to float noise", **reported**; else fail |
| retrieval outputs A == B | rank lists identical → pass; a swap only between rows whose A-scores differ by < 1e-6 **and** vectors were "float noise" → reported as tie noise, pass; anything else fails |
| `c_selftest.py` same check set passes in A and B | list checks that do not apply to 500 files; fail if the two lists differ |
| memory files 0 before and after in both | fail otherwise |

Else `GATE_R1_STOP` with the first failing line. Unexplained differences are never smoothed
over; every explained one is in the README's *Result*.

### 3.4 Gate R2 — the second portability rung, corpus_2000

Clean room C, same package, copy of `harness/corpus_2000`, `--workers 8 --seed-env`, then
`install`, `c_selftest.py`, the same retrieval probe list (captured, not compared — there is no
B), **one** headless Sonnet question via `setup_folder.py ask` (a question you write about the
folder's contents, no key, e.g. *"which years of budget documents does this folder hold, and
what does the most recent one say about development spending"*), teardown, memory assert.
**PASS** iff install exits 0, self-test passes its applicable checks, the answer ends with a
Sources block whose every line names a page the transcript shows as `OPENED`, the guard log
shows its block count, wall ≤ 60 min. Nothing is scored against a key. The README's *What this
does not show* says: *corpus_2000 is another generated corpus from the same fixture ecosystem;
this is not real-world validation; genuine cross-folder generalisation remains untested.*

### 3.5 Gate R3 — no dependency on the dev repo, proven by trace

In clean room A's layout, on a fresh corpus copy, run `install` again with a `sitecustomize.py`
placed in the clean venv that hooks `builtins.open`, `io.open`, `sqlite3.connect`, `os.scandir`,
`os.listdir` and appends every absolute path to `reads.log` (child processes inherit it via the
venv). **PASS** iff `reads.log` contains no path under `C:\Users\Ali\Desktop\retrieval-lab`, none
under `~/.claude/projects/<dev repo key>`, and the package grep (3.1) is empty. Else
`GATE_R3_STOP` naming the first offending path.

**3.6 Supersede and document.** `corpus-lab/state/c_shelf_build_v2.json.SUPERSEDED.md` and a
sibling for the Phase 6 cold-test record: *built with the experimental v2 builder; superseded
for production-portability claims by Gate R1 (v1 builder); v2 remains experimental.* Rewrite
`INSTALL_FOR_SIR.md`: the package, the one install command, the manifest and build report, the
builder line (*"builds the same shelf that was measured; the experimental v2 shelf is behind a
flag and prints a warning"*), the Phase 5 numbers with the v2/v3 note, and the untested-
generalisation sentence from §2.3. READMEs `p10_portable_r1`, `p10_portable_r2`, `p10_portable_r3`.

**3.7** `plog P10 3_portable <R1 R2 R3 verdicts>`; commit `Phase 10.3: portable package (v1
default), manifest, clean-room gates R1/R2/R3 <verdicts>`.

**done-check:** `dist/` with `PACKAGE_MANIFEST.json`; run records A, B, C, R3; every clean-room
corpus copy removed; `checksums.py verify --against s7_phase10_pre` reads 0 changed.

---

## Phase 4 — the noise band of the frozen stack (paid, ≤ 4.5 h)

**Nothing in the stack changes.** Same shelf (`s7_shelf`, v1), same `CLAUDE_MD_TEMPLATE`, same
guard `--v2`, same flags as P9: `--group frozen20 --parallel 2 --max-turns 60 --timeout 900`,
plus `--capture full` (adds a field only). Assert `git tag --points-at HEAD~N` includes
`scorer-v3-frozen-2026-09-16` in history and `c_score_live_v3.py`'s sha256 equals
`phase10_scorer_freeze.json` before the first probe; else stop. Pre-register
`corpus-lab/state/phase10_variance_spec.md` (this section, with the decision rule) and commit it.

**4.1 Procedure** — Plan D §5.2 verbatim (exclusivity, checksum snapshot `s7_phase10_live_pre`,
memory count, install, three probes per model with a fresh 16-hex token, battery in the
foreground with `python -u`, verify, quarantine, unconditional teardown, score), each battery
under its own `run_record.py`. Tags `P10S1`, `P10S2`, `P10S3` (`claude-sonnet-5`), then `P10O1`
(`claude-opus-5`). Sequential. Teardown and a clean-rung check between every battery. After each
recording: score with v1 strict (into v2's copy), v2, v3 (key v1), v3 (key v2) — **four scorers,
one recording, zero model calls** (rule 18).

**4.2 Budget and clock** — §3. A stopped battery is scored as a partial with its denominator.

**4.3 The variance report** — `corpus-lab/state/c_variance_2026-09-16.json` and a table in the
handoff. For Sonnet over {P9S, P10S1, P10S2, P10S3} and Opus over {P9O, P10O1[, P10O2]}, per
metric (`cited_right_page_equiv` v2 and v3, `cited_right_page_strict`, `cited_unopened_total` v3,
`mentioned_unopened` v3, `value_correct` k/5, `vector_full` k/n, absence frozen 3, sessions
lost, median and p90 wall, cost): **each individual value, n, denominator, mean, min, max,
range**, sample standard deviation only where n ≥ 3, and the per-question agreement count (how
many of the 17 received the same v3 equiv verdict in every repeat). Every table names
`scorer_version`, `key_file`, resolved model id, group definition sha256.

**Pre-registered decision rule:** a difference between two single Sonnet batteries on
`cited_right_page_equiv` smaller than the observed Sonnet range is "within measured noise" and
may not be used to prefer a configuration. The Opus range from n=2 (or 3) is a lower bound on
Opus noise, not a band. **Sonnet-versus-Opus differences are not interpreted in this report
beyond the sentence "both fall inside each other's observed range" or its negation.**

**4.4 Optional `P10O2`** only if Sonnet's three batteries total ≤ $36 **and** P10O1 ≤ $25
**and** the clock rule allows it **and** the $95 total holds.

**4.5** README `p10_variance`. `plog P10 4_variance DONE ...`; commit `Phase 10.4: variance
batteries P10S1-3, P10O1[, P10O2]`.

**done-check:** all score files for every completed tag exist under all four scorers;
`c_variance_*.json`; rung clean; `checksums.py verify --against s7_phase10_live_pre` reads 0
changed; quarantine applied; no stray `node.exe`/`python.exe`.

---

## Phase 5 — the morning note, the handoff, the final checks (free, ≤ 1 h)

**5.1 The morning note first** — `REPORT/08_what_next/MORNING_2026-09-17.md`, one screen,
in this order, one line each, numbers with denominators, no adjectives:

1. scorer v3: Gate T verdict, and the row that failed if any;
2. corrected Phase 9 analytical results (v2 → v3, both models) with the historical STOP verdicts
   restated as unchanged;
3. answer-key status: key v2 file, sha256, what it covers, what stays unscorable;
4. portable default builder: v1 — yes/no, with the manifest line quoted;
5. clean-build A vs B: R1 verdict and the vector determinism class;
6. corpus_2000: R2 verdict, and the sentence that it is the same fixture ecosystem;
7. every failed gate or unexplained mismatch, one line each;
8. Sonnet ×3: each battery's v3 equiv, range, cost;
9. Opus: each battery's v3 equiv, cost;
10. total cost, total sessions, against the caps;
11. retries, timeouts, kills, contamination events, manual interventions (counts, then list);
12. branch, every commit hash tonight, the v3 tag;
13. working-tree status;
14. exactly what changed (files, flags added, defaults preserved);
15. exactly what did not change (shelf, template, guard, ranking, key v1, Phase 9 verdicts);
16. what Ali must know or do before the demo, including: *real-world cross-folder
    generalisation remains untested; the next experiment is the pre-registered adversarial
    synthetic professor folder.*

**5.2 Correction note** — `REPORT/08_what_next/CORRECTION_2026-09-16.md`: §1.1 and §1.2 with the
per-case table, the v2/v3 side-by-side, the portable-builder mismatch, and every sentence in
`ORCHESTRATOR_BRIEF_2026-09-16.md`, `DEMO_2026-09-16.md`, `HANDOFF_2026-09-16_night.md`,
`INSTALL_FOR_SIR.md` (old text) and `README.md` that it supersedes, each with its replacement
wording. One-line pointer at the top of each of those files; bodies untouched.

**5.3 Handoff** — `REPORT/08_what_next/HANDOFF_2026-09-17.md`: phase status table; every gate with
verdict and spec commit; the variance table; budget reconciled line by line (driver figure vs
scorer figure per battery, or flagged unreconciled with the candidate cause); deviations; cuts
made under the clock rule; what was not done; the next moves re-ranked, first among them the
adversarial synthetic professor-folder test with its own pre-registration, and shelf v2 change
(b) alone after it.

**5.4 Final checks.** `docs_check.py` — **Gate D is its exit code.** `checksums.py verify
--against s7_phase10_pre` on the demo path: 0 changed. `git diff phase9-production-hardening --
corpus-lab/bin/c_stack.py corpus-lab/bin/c_stop_guard.py corpus-lab/bin/c_shelf.py
corpus-lab/bin/c_live_battery.py corpus-lab/bin/setup_folder.py corpus-lab/bin/c_selftest.py`
shows only additive, default-preserving changes; list them in the morning note item 14. Rung
clean. No stray processes. Working tree clean after the commit.

**5.5** `plog P10 5_trail <Gate D>`; commit `Phase 10.5: morning note, correction, handoff,
docs_check <verdict>`.

---

## 6. What this plan deliberately does not do, and the experiment after it

- No retrieval, ranking, B2c, shelf, caption, CLAUDE.md or guard-behaviour change.
- No re-run of Phase 9's batteries to revisit their STOP. Their verdicts stand under v2.
- No holdout look. No hand-written key values. No demo-path change.
- **No genuine real-world corpus.** None exists tonight and none is manufactured. Every gate in
  this plan runs on corpora from one generator. **Genuine real-world cross-folder
  generalisation remains untested.**

**Next experiment (not tonight; to be designed and pre-registered on its own):** an
independently designed adversarial synthetic "professor folder" — built by a different
generator or by hand from a different document family, with its own answer key, its own
contamination rule, its own frozen questions, and a pre-registered gate — so the portable is
tested against a folder its rules have never seen. Its README must exist before its first build.

---

## 7. Stop conditions — record and stop, do not improvise

- `BASELINE_BROKEN` in Phase 0.
- Any checksum change on `s7_phase10_pre` (demo path or planted files) or `s7_phase10_live_pre`.
- Any isolation probe fails; any memory file under a corpus project key; any dev-repo read in
  the R3 trace (stops R3 only).
- A battery passes its cost cap (stop that battery only); the $95 total is reached (stop all
  model calls; Phase 5 still runs).
- Gate T reads STOP **and** v3's equivalence count differs from v2 by more than ±1 on either P9
  battery: skip Phase 4 (a scorer that moved the headline is not the instrument to measure
  variance with); do Phases 3 and 5; say so in the morning note.
- `c_score_live_v3.py` changes after its tag: not permitted for any reason; if you believe it
  must, write why in the handoff and leave it.
- You want to change a gate, a bar, a denominator, a frozen script, or a recorded file. Write
  what and why in the handoff; do not do it.
