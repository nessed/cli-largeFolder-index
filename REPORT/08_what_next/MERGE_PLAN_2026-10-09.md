# Merge plan — the handover baseline

Goal: one portable package that is **the** baseline, carrying the parts of Ahmad's
`local/reliability` work that earn their place, verified by deterministic evidence rather
than by a noisy live battery, and ready for Ali to hand-test once and send to his professor.

Target folder for the result: `Desktop\Projects\Code\portable-test - Copy` — the only clean
2,000-file folder left (no index, no `CLAUDE.md`, never installed). `portable-test` stays as
it is so the old index survives for comparison.

---

## The constraint that shapes every decision

**Ahmad ran Claude Code the program, but with DeepSeek v4 Pro behind it**, routed through a
local LiteLLM proxy because his CommandCode plan returned `MODEL_NOT_IN_PLAN` on every
`claude-*` model. The professor will run Claude on a Max plan.

So his work splits in two, and the two halves need completely different treatment:

**Enforcement in Python — model-blind.** A script that exits non-zero behaves identically
whoever drives it. His page fix, the quote check, `verify`, coverage counting, timeout
retry, `--adopt`. The model he used is *irrelevant* to this half, and it is where almost all
the value is. Take it on code review.

**The `CLAUDE.md` template — model-tuned.** Wording he shaped against DeepSeek's mistakes.
Mostly it just documents the new commands, which Claude needs too, but it carries at least
one hedge that is wrong for us. Must be edited deliberately and then driven once by Claude.

---

## What goes in

Verified present in his code, not merely claimed in his `RUN.md`.

### 1. The page fix — `FIRST_PAGE_INDEX = 1`

Closes **F-23**, the blocker. Ours stores a document's first page as page 0 via a bare
`enumerate(pages)` in `index_build.py`; his puts the numbering in one constant in
`labpaths.py`, with `pdf_page_number()` as the single place the two numberings meet, and both
shelf builders read it instead of hardcoding.

Take his version, not a patch of our own — two independent diagnoses agreeing is the
strongest evidence this project has produced, and his is the root fix.

**Changing it is a re-index.** The old numbers are stored in `pages`, in the shelf's
`captions`, and inside every written note.

### 2. The citation-integrity group — the reason the project exists

| change | token |
|---|---|
| `note` refuses a quote not on the page it cites | `NOTE_REFUSED_QUOTE_NOT_ON_PAGE` |
| `verify --slug` re-derives every note from the index, exit 1 on any failure | — |
| `verify --answer <file>` checks the prose's figures against the notes | `ANSWER_UNSUPPORTED_FIGURES` |
| a note records the page SHA it was written against | `PAGE_CHANGED_SINCE_NOTE` |
| second Stop hook runs verify at answer time | `c_verify_guard.py` |

`c_verify_guard.py` follows the existing guard's discipline deliberately: never blocks an
answer that cited nothing, asks at most once per session, never on the re-entry it caused
(so a disagreeing session still terminates), prints the hook contract's JSON and exits 0. It
reuses `c_stop_guard`'s transcript reader rather than adding a second parser, and ships a
`--selftest` for the decision logic that needs no corpus.

This group is what would have caught F-23. Our v3 scorer compares a cited page against
`OPENED` pages drawn from the same internal index, so a uniform offset cancels and the gate
reports a clean pass. `verify` re-derives the quote from the page text, which does not cancel.

### 3. Coverage honesty

`failed_by={failed_timeout:4}` when non-zero, `pages_with_no_readable_text=N`, and
`coverage --json` naming every unreadable file. Turns silent loss into visible loss. For a
stranger installing on an unknown machine this is worth more than any retrieval improvement.

### 4. `index_build` timeout scaling and retry

He reports that at the 6 workers `INITIALIZE.md` computes for an 8-core machine, four large
volumes hit a hardcoded 180-second `pdftotext` timeout and are **dropped while `COVERAGE`
still prints `failed=0`**. He also found that an install only re-runs stages whose output is
missing, so a failed file is never retried without `--purge`.

Take the root fixes: budget scales with file size, previously-failed files are retried.

**Do not take his worker advice.** "Use 3, not 6" was measured on 26 very large PDFs on an
8-core host. Our 2,000 files are small and installed fine. Fixing the timeout fixes the
cause; hardcoding a worker count would pessimise every other machine.

### 5. The moved-folder fixes

`uninstall`/`install` key ownership and registry state on the **absolute** corpus path, so
after a move the tool refuses. **This already bit Ali** when the Desktop was reorganised on
25 September and `portable-test` moved into `Projects\Code\`. His fixes:
`FOREIGN_INDEX_PRESENT` with exit 3, `install --adopt` to repoint deliberately,
`ADOPTED_MOVED_INSTALL` so teardown of a moved install still works, and excluding the pack's
own `CLAUDE.md`/`.claude` from the corpus (`excluded_dependency=2`).

A professor who drags the folder from Downloads to Documents hits this on day one.

### 6. Shelf update atomicity

`UPDATE_IN_PROGRESS` makes readers exit 3 mid-update; `SHELF_REBUILD_PREFERRED` exits 6 on an
update that is really a rebuild.

### 7. `table <rel> --page N`

Reads the real grid with `pdfplumber` cells rather than the text layer. **No new
dependency** — `pdfplumber==0.11.10` is already a declared root in
`requirements-portable.txt`, and he guards the import with a useful hint anyway. Worth having:
in a budget corpus the numbers live in tables, and `pdftotext -layout` mangles them. The
entire answer key for Ali's twelve questions had to be built from prose for exactly this
reason.

### 8. The selftests that were never packaged

`c_index_selftest.py`, `c_setup_selftest.py`, `c_note_quote_selftest.py`,
`c_dupe_audit_selftest.py`, `c_shelf_update_selftest.py`, plus `c_shelf_update.py` and
`c_dupe_audit.py` which the features need. These already exist in `corpus-lab/bin/`; they
were simply never on the package allowlist. A package that can check itself on a stranger's
machine is worth more than one that cannot.

All eight were checked for answer-key access — `answer_key`, `placed_catalogue`,
`series_registry`, `rung_membership`, `_private`, `harness/keys`. **Zero hits.** None is on
`make_portable.py`'s `NEVER` list.

---

## What stays out

**`make_fixture_index.py` and `c_retrieval_eval.py`.** Development tools with no user-facing
role. Every shipped script is surface area on a machine we cannot debug.

**His `RUN.md`.** 17KB, and most of it is his machine: `C:\Users\Ahmad Karim\...`, the
LiteLLM router, the CommandCode yaml, `deepseek/deepseek-v4-pro`, `ask.cmd`, his
`fetch_punjab_budget.py`. Shipping it to a professor on a Max plan would actively mislead.
Mine its three durable findings into `INITIALIZE.md` — the timeout behaviour, the
moved-folder behaviour, and that an install does not retry a failed file — and keep the file
here as reference.

**OCR on by default.** Keep the code, keep it gated behind `PCR_OCR=1`. `tesseract` and
`pdftoppm` are external binaries resolved through `_find_exe` with env override; the
professor will not have tesseract. **Add one `doctor` line**: OCR unavailable, scanned files
will be reported as image-only rather than silently empty. That is the honest default — our
own run already had 124 image-only files.

---

## One of ours to fix while we are in here — F-25

A portable install creates a directory called **`_private`** in the recipient's folder.

`portable-test\_private\results\03_runs\hooks\stop_guard__unlabelled.log` — one 2.4KB file,
written by the stop hook on first run. `labpaths.RUNS` defaults to
`PRIVATE / "results" / "03_runs"`, and `PRIVATE` defaults to `RETRIEVAL_LAB / "_private"`,
which in a portable layout resolves to the package's parent. So the hook creates it.

It is **not** a key leak — the answer keys are in this repo at `_private\harness_keys\`, and
nothing of the sort is in the handover folder. But a folder named `_private` appearing
unbidden in a professor's directory looks exactly like something he was not meant to see, and
it is the only place the lab's internal naming reaches a handover install.

Merging Ahmad's work makes it slightly worse, not better: `c_verify_guard.py` defaults
`VERIFY_GUARD_LOG` to the same `L.RUNS / "hooks"`, so a second log lands beside the first.

Fix: have `install` set `RUNS_ROOT` (the env var already exists, `labpaths.py:70`) to
somewhere inside `engine\artefacts\`, so hook logs go where every other build artefact goes.
Delete the stray directory from `portable-test` by hand; `portable-test - Copy` has never
been installed and does not have one.

---

## Template changes — the half that needs Claude

**Strip** the 0-based hedge. His template says, in effect, *"if the index you were given was
built with numbering from 0 instead, `open` prints the PDF page beside the index number."*
That is a compatibility note for a state that will not exist after the re-index, and cruft
in the one document the model always reads.

**Keep** the documentation of `table` and `verify`, the note quote-refusal rule, and "do not
hand over an answer whose notes fail."

**Add one rule, for F-24.** The single wrong answer in Ali's run was a *fabricated absence*:
the engine said Sindh has no own-source revenue before 2012-13 "anywhere in the folder" when
every edition carries 2010-11 in prose. It had read a Table 3.1 that prints only its last
eight columns and generalised from the table to the corpus. It cost Ali two years of panel he
actually has.

No quote check catches this — the quote was real. The cheap, proportionate fix is a template
rule: *before reporting that a series starts later than asked, or is absent, check the prose
and another edition, not only the columns a table happens to print.* It costs one paragraph
and it is the difference between an honest "not here" and a false one.

---

## Build order

```
cd C:\Users\Ali\Desktop\Projects\Code\retrieval-lab
git checkout -b merge-ahmad-reliability
```

1. **Snapshot the ranker first, before touching anything.** Run `c_shelf.py find` for a fixed
   question set against the existing `portable-test` index and save the output. This is the
   only clean "before" available, and it expires the moment a file changes.
2. Copy his nine changed engine files into `corpus-lab/bin/`, plus the eight new scripts.
3. Add the eight new scripts to `ALLOWLIST` in `corpus-lab/bin/make_portable.py:42`. Without
   this a rebuild silently drops them.
4. Apply the template edits above to `CLAUDE_MD_TEMPLATE` in `c_stack.py`.
5. Fold the three durable `RUN.md` findings into `INITIALIZE.md`; add the OCR `doctor` line.
6. `.venv\Scripts\python.exe -m pytest corpus-lab\tests -q` — 136 collected today. The
   fifteen `test_initialize_md.py` cases check every flag and subcommand the runbook prints
   against `setup_folder.py`'s argparse, so step 5 will fail them until it is done properly.
   That is the point of them.
7. Re-run the step-1 ranker snapshot and diff. **Expect byte-identical.** If it differs, he
   changed the ranker without saying so and the merge stops here.
8. `.venv\Scripts\python.exe corpus-lab\bin\make_portable.py --out dist` — this is what fixes
   the stale-manifest problem. It computes every hash itself, runs the forbidden-string grep,
   and refuses on a dirty tree. His engine files contain **zero** `C:\Users` or `Desktop`
   hits, so the grep will pass.

---

## The acceptance gate

"Flawlessly" needs evidence. Four deterministic checks and one judged one — deliberately
**not** a before/after on the live battery.

### Why not the live battery

Identical reruns of the frozen battery swing by **2 to 5 of 17**. That variance is why the
published Sonnet-vs-Opus gap of 1 was retired as noise. A before/after on twenty questions
cannot resolve a change of this size, and reporting one would mean disowning it later. Use
the battery to *get answers*, not to *score the merge*.

### Check 1 — the ranker did not move

Step 7 above. Byte-identical `find` output on a fixed question set. Deterministic, free,
and a stronger retrieval regression test than any live run.

### Check 2 — `verify` turns red to green on answers we already have

Point `verify` at the nine answers from 17 September. Every one should **fail** on page
numbers now, and **pass** after the re-index. That is the before/after, and it is exact
rather than noisy. It is also the only direct proof that F-23 is actually closed rather than
relocated.

### Check 3 — the clean-room install, with a cold model cache

In a throwaway temp directory, not `portable-test`:

- fresh `venv`, `pip install -r requirements-portable.txt`
- `PDFTOTEXT_EXE` and `CLAUDE_CMD` pointed at invented paths first, to confirm `doctor`
  names the fix rather than printing a stranger's directory (the F-01 fix has only ever been
  exercised on this machine)
- **`FASTEMBED_CACHE_PATH` pointed at an empty directory**, so the 130MB embedding model
  actually downloads. Every install this project has measured ran from a warm cache with
  0 bytes downloaded; the professor's first run will not. The code honours this variable in
  `build_manifest.py`, `run_record.py` and `setup_folder.py`, so this finally closes a gap
  open since phase 11.
- then `install`, `doctor`, `c_selftest`, and each of the new selftests

### Check 4 — the move

Install, move the folder, confirm `FOREIGN_INDEX_PRESENT` and exit 3, then `install --adopt`
and confirm `ADOPTED_MOVED_INSTALL` and a working query. This is the path that broke Ali's
own folder, and it is the single most likely thing a professor does on day one.

### Check 5 — the twelve questions, judged

Install into `portable-test - Copy`, then ask all twelve: the five from
`ACCEPTANCE_QUESTIONS_2026-09-17.md` and the seven from
`ACCEPTANCE_QUESTIONS_HARD_2026-09-17.md`. Nine have scored answers already, so they are a
regression check; three — H3, H5 and the fiscal-deficit spare — have never been asked.

Score citations by **opening the page**, not by trusting the transcript. That is the one
thing no gate has ever done and the only reason F-23 was ever found.

Ask **H5 first**. Its correct answer depends on noticing that the 2022-23 Punjab edition
stops six years early — the same trap F-24 fell into. If it passes, F-24 was a one-off; if
it fails, the template rule did not take and the problem is structural.

Watch the install's `indexed=` count. The old one reported `indexed=1850`. If his build
reports **more**, his dropped-files finding reproduces here and every answer in Ali's run
came from an incomplete index.

---

## What this still cannot certify

Unchanged from the 2026-09-18 handoff, and no amount of local work closes them:

- **A second machine.** The F-01 tool-path fix has only ever run here, where the historical
  locations still win. Check 3's env-var probe is a proxy, not proof.
- **The interactive permission prompts (F-03).** Rule 7 forbade an interactive `claude`
  session, so the loudest predicted friction is still unmeasured — and this merge *adds a
  second Stop hook*, which makes it more relevant, not less.
- **A corpus from another generator.** Partly closed by accident: Ahmad's 26 Punjab FY2026-27
  PDFs are the first non-generated corpus this project has touched, and the findings above
  came out of it. But our own gate has still never run on one.
- **Whether a genuinely fresh agent follows `INITIALIZE.md`** rather than improvising. Only
  the professor's run answers that.

Say these four out loud in the handover note. A package that names what it has not been
tested on is worth more than one that implies it has been tested on everything.
