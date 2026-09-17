# Plan F / Phase 11 — findings

Fresh-folder acceptance stage. The package staged for Ali is
`retrieval-portable-43ed356`, built from HEAD `43ed356` on branch
`phase11-fresh-folder`, after two blocker fixes found by the dress rehearsal.

The ten predictions below were copied verbatim from
`plans_fable/F_FRESH_FOLDER_ACCEPTANCE/EXECUTE_2026-09-17.md` section 3 **before** the
first rehearsal command ran. The *observed in rehearsal* and *class* columns were filled
afterwards. The *observed by Ali* column is left empty for him.

**Classes.** *blocker* — a step in `INSTALL.md`, followed exactly as printed, that exits
non-zero or leaves the next step impossible; or a command in the installed folder's
`CLAUDE.md`, run from inside that folder with no extra flags, that prints
`NO_REGISTERED_ROOT`, `unable to open database file`, a traceback, or nothing where output
is documented. *friction* — everything else a stranger had to know, guess, wait for or
tolerate that `INSTALL.md` did not say. *not a bug* — it worked and the document was enough.

**Three rehearsals were run**, each from a new temp directory, each deleted afterwards:

| | package | purpose | outcome |
|---|---|---|---|
| R1 | `a9ab77a` | first pass | died at the first `CLAUDE.md` command (F-02) |
| R2 | `c0442de` | after the F-02 fix | shelf commands all work; died at "Check the build" (F-17) |
| R3 | `43ed356` | after the F-17 fix | every `INSTALL.md` step exits 0; live answer produced |

---

## Summary

**Two blockers, both fixed.** Both were the same shape, and it is worth naming that shape
because it is likely to recur: *the clean-room harness passed a flag that the document does
not print*. `p10_cleanroom.py` supplies `--db`/`--shelf` on every shelf call and
`--expect-pages 0` on the self-test. Gate R1, R2 and R3 therefore measured the engine and
never once ran the commands a reader of `INSTALL.md` would run. Seven nights of green gates
sat on top of a package whose first user-facing command raised a traceback.

**Predictions:** 6 confirmed (F-01, F-02, F-04, F-06 partially, F-07, F-08, F-09),
1 denied (F-05), 2 could not be tested here and pass to Ali (F-03, and the interactive half
of F-09), 1 satisfied (F-10). Nine further findings, F-11 to F-19, were added.

---

## Pre-registered predictions

### F-01 — hardcoded development-machine paths

**Prediction.** The package hard-codes two development-machine paths that happen to exist
on this machine and will not on sir's: `pdftotext.exe` at `C:\Program Files\Git\mingw64\bin\`
(`setup_folder.py` `PDFTOTEXT`) and `claude.exe` under `C:\nvm4w\nodejs\` (`labpaths.py`
`_CLAUDE_EXE`, fallback `claude.cmd`, override env `CLAUDE_CMD`). Neither is looked up on
PATH. `INSTALL.md` says "Claude Code on the PATH", which the code does not honour. Gate
R3's absolute-path grep only looks for `C:\Users` and `Desktop`, so it passed.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED, and wider than predicted.** The grep of the built package finds the pdftotext path in **two** files, not one: `setup_folder.py:56` and `index_build.py:26`. The claude path is at `labpaths.py:104` and `:107`. As predicted, `doctor` reports `[PASS] pdftotext C:\Program Files\Git\mingw64\bin\pdftotext.exe` and `[PASS] claude_exe C:\nvm4w\nodejs\...\claude.exe` — both pass here precisely because this is the machine they were hardcoded from, so the rehearsal cannot show the failure. Gate R3's rule still holds honestly: `C:\Users` and `Desktop` are zero hits. |
| observed by Ali | |
| class | **friction here, blocker on sir's machine.** Not fixed, by Ali's instruction. |

**Ali's decision, 2026-09-17.** Asked mid-run to treat this as out of scope: *"forget the
little parts like reproducing claude.exe install and pdf to text install that can honestly
just be setup.md the bot has to follow when u open Claude code in a new folder"*. So the
intended remedy is a `SETUP.md` that an agent follows on a new machine, not PATH lookup in
the engine. Recorded here as the first item that document has to cover.

### F-02 — registered pages-database path

**Prediction.** `c_stack.py do_setup` registers `<package>\02_stacks\s2_fts5\harness_15000.db`
as `db`, not the `--artefacts` `pages.db`; `02_stacks` is excluded from the package. Yet
Gate R2's one live answer opened two pages successfully. The planning session could not
reconcile these; the rehearsal must. If `open` or `inside` prints `unable to open database
file` or `NO_REGISTERED_ROOT`, this is a **blocker**.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED, and it is a blocker.** After a clean install, the registry entry read `"db": "<R>\engine\02_stacks\s2_fts5\harness_15000.db"` — a path that does not exist (`02_stacks` is on the package's excluded-dirs list). `"shelf"` was correct, because `--shelf-dir` is already plumbed through. The very first command `CLAUDE.md` tells the model to run, executed from inside the research folder with no `--db`/`--shelf`, died: `sqlite3.OperationalError: unable to open database file`, raised at `c_shelf.py:115` in `Ctx.__init__` via `get_ctx` at `c_shelf.py:199`, exit 1, traceback on stderr. `find`, `have`, `inside`, `open`, `note` and `notes` all route through the same `get_ctx`, so none of them could work. Log: `C_rehearsal/08a_find.log`. |
| observed by Ali | |
| class | **blocker — fixed**, commit `c0442de`. |

**Why Gate R2 passed anyway.** The clean-room harness never used the registry:
`corpus-lab\bin\p10_cleanroom.py:243` builds every shelf invocation as
`[python, c_shelf.py, "--db", <artefacts>\pages.db, "--shelf", ...]`, passing both paths
explicitly. `--db` short-circuits the registry lookup. R2 measured the engine and never the
one line of plumbing a real user depends on.

**The fix.** `c_stack.do_setup` gains `db_path=None`, `c_stack.py setup` gains `--db`, and
`setup_folder.py` passes `art["db"]` — the value it already computes at line 154 and
already hands to every other stage. The default is unchanged, so nothing outside a portable
install behaves differently. Tests:
`corpus-lab/tests/test_install_registers_artefacts_db.py`, five cases, all five failing
before and passing after; `test_04` drives `c_shelf._resolve` from inside the folder with no
flags, which is exactly what the model does.

**Verified in R2/R3.** All seven commands now run from inside the research folder with no
flags: `find` (40 families), `have` (`EDITION_PRESENT 2021-22 ... (165p)`), `inside`,
`open` (printed the page text), `note` (`NOTED`), `notes`, `coverage`. Logs `r2_08*`.

### F-03 — a permission prompt on every engine command

**Prediction.** Interactive Claude Code in the installed folder will ask permission for
every engine command, because `.claude\settings.json` carries only a deny list and a Stop
hook, no allow rules. The `ask` subcommand avoids this with `--permission-mode
bypassPermissions`, but `INSTALL.md` leads with the interactive route.

| column | value |
|---|---|
| observed in rehearsal | **Not testable here** — rule 7 forbids an interactive session, and the one live call went through `ask`, which passes `--permission-mode bypassPermissions` (`setup_folder.py:338`) and so sees no prompts at all. The static half is confirmed by reading the installed `.claude\settings.json`: it contains `permissions.deny` and a `hooks.Stop` entry, and **no allow list**. |
| observed by Ali | |
| class | **friction — passes to Ali.** Predicted to be the loudest thing he meets. |

### F-04 — moving the engine folder breaks every command

**Prediction.** `CLAUDE.md` and the Stop hook embed the absolute path of
`engine\.venv\Scripts\python.exe` and `engine\bin\c_shelf.py`. Moving or renaming the
engine folder after install breaks every command silently. `INSTALL.md` does not say
"do not move it".

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED.** The installed `CLAUDE.md` embeds the absolute interpreter and script paths in all fourteen commands it prints. After renaming the rehearsal root, the command `CLAUDE.md` prints fails with `The term '...\engine\.venv\Scripts\python.exe' is not recognized as the name of a cmdlet, function, script file, or operable program.` The failure is loud rather than silent, which is better than predicted — but it names a missing interpreter, not a moved folder, so the reader is not told what to do. Log: `C_rehearsal/r3_10_moved.log`. |
| observed by Ali | |
| class | **friction (documentation).** `INSTALL.md` should say: do not move or rename the engine folder after installing; if you do, uninstall and install again. |

### F-05 — an empty `_private\` appears next to the package

**Prediction.** `install` creates an empty `_private\` next to the package because
`labpaths.PRIVATE` defaults to `<package parent>\_private` and something calls `mkdir`.

| column | value |
|---|---|
| observed in rehearsal | **DENIED.** After a full install the rehearsal root held exactly `engine\` and `research\`. The only `_private` anywhere under it was `engine\.venv\Lib\site-packages\numpy\testing\_private`, which is numpy's. The engine directory gained `.venv\`, `artefacts\`, `99_scratch\` and `state\` — all expected, none of them `_private`. |
| observed by Ali | |
| class | **not a bug.** The 2026-09-17 handoff's note about this no longer reproduces. |

### F-06 — undocumented default `--workers 12`

**Prediction.** The default `--workers 12` is not mentioned in `INSTALL.md`; the R2 install
used `--workers 8`. On a laptop 12 pdftotext processes may thrash.

| column | value |
|---|---|
| observed in rehearsal | **Half confirmed.** `INSTALL.md` indeed never mentions `--workers`. No thrashing: this machine reports 16 logical processors, and the 500-file install took **139-140 s** across three runs, against the ≈2 min in `INSTALL_FOR_SIR.md`'s table. Stage timings were stable to within 0.5 s across all three (`index_s` 25.8-26.4, `shelf_s` 67.7-68.0, `caption_embed_s` 42.3-42.7). |
| observed by Ali | |
| class | **not a bug** on a 16-core machine. Unknown on sir's; the 2,000-file folder Ali is about to install is the real test of the published ≈6 min. |

### F-07 — the embedding-model download is never exercised here

**Prediction.** `BAAI/bge-small-en-v1.5` (~130 MB) is already cached on this machine, so
neither the rehearsal nor Ali's run exercises sir's first-run download.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED.** `doctor` prints, verbatim: `[PASS] embedding_model_bge-small-en-v1.5   cached at C:\Users\Ali\AppData\Local\temp\fastembed_cache\models--qdrant--bge-small-en-v1.5-onnx-q`. `pip install` also downloaded nothing at all — 72 wheels came from cache, 0 downloaded, in 73-89 s. A stranger's first run does both: ~130 MB of model and a full wheel download. Neither this rehearsal nor Ali's run will measure that. See also F-15 on the attempted probe. |
| observed by Ali | |
| class | **test-coverage gap, not a bug.** Also worth noting the cache lives under a directory named `temp`; a disk cleaner could delete it and force a silent re-download. |

### F-08 — "Python 3.11" with no way to check it

**Prediction.** `INSTALL.md` says Python 3.11 but does not say how to check, and
`python -m venv` picks whichever `python` is first on PATH. `doctor`'s first check only
verifies the interpreter is inside `.venv`.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED.** `python -m venv .venv` picked `C:\Users\Ali\AppData\Local\Programs\Python\Python311\python.exe` and the venv reports `3.11.5`, so it worked here by luck of PATH order. `doctor`'s first line is `[PASS] python_is_the_venv <path>` — it asserts the interpreter is the venv's and never looks at the version. Nothing in the install path would catch a 3.12 or a Microsoft Store stub. |
| observed by Ali | |
| class | **friction (documentation).** One line — `python --version` should print 3.11.x — would close it. |

### F-09 — "Ask it something" stops where the hard part starts

**Prediction.** `INSTALL.md` tells the user to `cd <your folder>` and run
`claude --model claude-opus-5`, but says nothing about what happens next, what a good
answer looks like, what a `Sources` block is, or that a `COVERAGE` line exists.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED by reading both documents.** `INSTALL.md`'s "Ask it something" is six lines: two commands and nothing else. It never explains what a `Sources` block is, that a `COVERAGE` line will appear, that the first `inside` call pauses to build a page-range cache, what "not here" looks like, or that answers take one to three minutes. A stranger reaching this section has a working index and no idea what success looks like. |
| observed by Ali | |
| class | **friction (documentation), the largest one.** |

**Which paragraphs of `INSTALL_FOR_SIR.md` a stranger would have needed** — read only after
the rehearsal's stranger-steps were finished, per rule: the wall-time table (to know a
2,000-file install is ≈6 minutes and not hung), the description of the `COVERAGE` line, the
worked example of a `Sources` block, and the paragraph on what an honest "not here" reads
like. Those four are what the package is missing.

### F-10 — one machine-global registry shared by every install

**Prediction.** `%LOCALAPPDATA%\retrieval-lab\roots.json` is keyed by folder path. Two
installs cannot collide, but `uninstall` of one must not remove another's entry, and a
stale entry from a deleted folder lingers forever.

| column | value |
|---|---|
| observed in rehearsal | **SATISFIED.** The registry held 4 entries before the rehearsal (`corpus_15000`, two scratchpad `hooktest` folders, and a stale `p10_clean_a\corpus_trace` from Plan E). Install added a 5th; `uninstall` removed exactly that one and left the other four byte-identical. Snapshots: `roots_before.json`, `roots_after_install.json`, `roots_after_uninstall.json`. The stale-entry half of the prediction is visible in the data: `p10_clean_a\corpus_trace` names a temp folder deleted weeks ago and still sits in the registry, pointing at a db that no longer exists. |
| observed by Ali | |
| class | **not a bug** for the acceptance test — no other entry changed. The lingering stale entry is untidiness, not a defect anyone will hit. |

---

## Findings added during execution

### F-11 — the packaged `bin/` differs from the 02f53c8 package by line endings only

The plan predicted an empty `diff -r` between the two packages' `bin/`. By sha256 it is not
empty: `c_stack.py`, `c_caption_embed.py` and `c_caption_index.py` differ. Line-by-line
comparison of all three shows **zero** differing lines and `git diff 02f53c8 HEAD --stat`
for them is empty. The delta is CRLF in the older package against LF in the new one, from
git's end-of-line normalization. Package content equals HEAD, which is what the plan's
claim was actually asserting.

**Class:** not a bug. Recorded so the next reader is not alarmed by a non-empty diff.

### F-12 — one flaky test in the suite

The first run of `.venv\Scripts\python.exe -m pytest corpus-lab\tests -q` in this session
gave **105 passed, 1 failed**:
`corpus-lab/tests/evidence_v1/test_inventory.py::TestInventory::test_08_partially_readable_pdf`
— a PDF with one unreadable page classified `parser_failed` where the test expects
`partially_readable`. It was first recorded as a standing pre-existing failure. That was
wrong: it has not reproduced in any of the six subsequent runs on the same unchanged code.
It is **flaky**, most likely sensitive to leftover state in
`corpus-lab/99_scratch/pytest_tmp`, which `conftest.py` pins as the suite's temp root and
which the first run of a session inherits from whatever ran last.

The true baseline is **106 collected, 106 passing**; after both fixes the suite is **115
collected, 115 passing** — the old count plus exactly the nine new tests.

**Confirmed again at the end of the phase.** The final verification run reported
`1 failed, 114 passed`; an immediate rerun of the same suite on the same code gave
`115 passed`. The flake is real and recurs on the first suite run inside a fresh shell.
It is worth someone's attention on its own, and it means any single green run of this
suite should be read with that in mind.

**Class:** not a bug for this plan. The flake is in the test's temp-directory hygiene, not
in the engine.

### F-13 — `make_portable.py` calls an untracked file "dirty"

`make_portable.py:261` derives `package_dirty` from `git status --short`, which lists
untracked files. Creating the experiment directory this plan itself mandates therefore
stamps the package dirty. The package was built only after committing the plan file and the
opened run record.

**Class:** friction, on the builder's side rather than the stranger's.

### F-14 — the research corpus itself ships `CLAUDE.md` files and a `.claude\` directory

The plan's section 5 asks me to verify there is "no `CLAUDE.md`, no `.claude\` anywhere
inside" `research\`. There is: `harness\corpus_2000` contains **9** `CLAUDE.md` files and a
`.claude\` directory holding 5 json files under `agent_workspace\`. They are generated
corpus content — a synthetic messy academic's drive, complete with an agent's working notes
— present at source, not install residue. Per the plan's own rule, the corpus wins and the
contradiction is recorded here.

It does not spoil the test. There is **no** `CLAUDE.md` and **no** `.claude\` at the
research **root**, which is where `install` writes its two files, so `uninstall`'s "removes
exactly those" claim stays testable — and was verified: after uninstall the research tree
was byte-identical to `harness\corpus_500`, 500 files, zero sha256 mismatches in a 50-file
sweep.

One thing to watch: Claude Code reads `CLAUDE.md` files from subdirectories it works in, so
a session that reads deep into `agent_workspace\` may pick up that file's conventions
(fiscal-year formatting, "values are Rs billion unless…"). The content is benign and
plausible; nothing in it is adversarial. Worth knowing before reading too much into one
answer's phrasing.

**Class:** not a bug. A contradiction between plan and corpus, resolved in the corpus's
favour.

### F-15 — `doctor`'s embedding-model check cannot fail

Two things, found while probing F-07.

First, `setup_folder.py:128` calls `chk("embedding_model_...", True, ...)` — the pass flag
is the literal `True`. The check reports where the model is, or that the first run will
download it, but it is counted as a PASS either way. "9 checks, 0 failed" therefore
overstates what has been verified by one.

Second, the F-07 probe could not be run as the plan described. Pointing
`FASTEMBED_CACHE_PATH` at an empty directory still printed
`[PASS] embedding_model_... cached at ...AppData\Local\temp\fastembed_cache\...`, because
`find_model_cache` (`setup_folder.py:87-107`) treats the env var as the first of five
candidate locations and falls through to the machine default when it misses. So the probe
tells you nothing about a fresh machine, and `doctor` cannot be made to simulate one.

**Class:** friction. Not fixed — it is not a blocker, and this plan fixes only blockers.

### F-16 — a routine progress message renders as a red PowerShell error

The first `inside` call on a new install prints `(building page-range cache, one-time,
~1 min)` to **stderr**. PowerShell renders native-command stderr as a `NativeCommandError`
record: red text, a `+ CategoryInfo : NotSpecified` block, and the offending command echoed
with a squiggly underline. It looks exactly like a crash. The command then succeeds and
prints its hits normally.

Sir will see this. It is the single most alarming-looking thing in an otherwise quiet run,
and it is not a failure at all.

**Class:** friction. Worth fixing later by printing progress to stdout.

### F-17 — `INSTALL.md`'s self-test command exits 1 on any real folder

"Check the build" printed
`bin\c_selftest.py --db .\artefacts\pages.db --shelf .\artefacts\shelf\shelf.db`.
`--expect-pages` defaults to **1,206,260** — the page count of the frozen 15,000-file
development rung. Run as printed against a user's own folder, the `coverage` check compares
that constant against their page count, fails, and `_overall` goes false, so the command
exits 1. In R2: `coverage pass=false, pages=39647`, with every other one of the fourteen
checks passing. Nothing was wrong with the build; the document asked the wrong question.

The same blind spot as F-02: `p10_cleanroom.py:205-212` already passes `--expect-pages 0`,
with a comment reading *"the flag exists for exactly this case"*, so Gate R1 never ran the
command a reader of `INSTALL.md` would run.

**Class:** **blocker — fixed**, commit `43ed356`. Document only: `INSTALL_MD` in
`make_portable.py` now prints `--expect-pages 0` plus one short paragraph saying what it
means and why to leave it in. No engine code, no default, no check changed. Tests:
`corpus-lab/tests/test_install_md_selftest_command.py`, four cases; `test_02` failed before
and passes after, `test_01` pins the default so a future change to it cannot silently
invalidate the reason for the flag. Verified in R3: `_overall pass=true`, exit 0.

### F-18 — the frozen scorer does not recognise a bold `Sources` heading

Checking R3's live answer the way `p10_check_ask.py` does gave
`has_sources_block: false` — yet the answer plainly ends with a `**Sources**` heading and
four citation lines. `c_score_live_v3`'s test is a regex for a bare `Sources` line or the
string `Sources:`; the model wrote `**Sources**` in bold, which matches neither. Separately,
`citations_and_mentions` returned `n_sources: 2` where the prose carries four lines —
correct behaviour, since two pairs are repeated, but easy to misread as two lines lost.

Checked by hand: **all four** `Sources` lines name pages the transcript shows as `OPENED`.

Scorer v3 is frozen at `scorer-v3-frozen-2026-09-16` and rule 4 forbids touching it, so
this is recorded and not fixed. It matters for anyone reading a `has_sources_block` field:
false does not mean the answer lacked sources.

**Class:** not a bug in the engine; a parsing limitation in the measurement code, and a live
caution for reading any future scorer output.

### F-19 — `uninstall` leaves the Claude Code session directory behind

After `uninstall --folder <R>\research`, `CLAUDE.md` and `.claude\` were gone and the
registry entry was removed, but
`%USERPROFILE%\.claude\projects\C--Users-Ali-AppData-Local-Temp-portable-rehearsal3-...-research\`
remained, holding the session transcript. `uninstall` prints "index artefacts kept (pass
`--purge` to delete them)" and says nothing about this. The rehearsal deleted it by hand.

It is small, but it is the one piece of residue that contains the content of what was
asked, and a user who uninstalls to "remove it" will reasonably think it is gone.

**Class:** friction. Not fixed — not a blocker.

---

## The one live answer (R3)

One Sonnet call, 149 s, rc=0, transcript at `C_rehearsal/r3_09_ask1.jsonl`, answer at
`C_rehearsal/r3_09_answer.md`. Question, written from the folder listing alone:
*"How has federal development spending changed over the last ten years?"*

| field | value |
|---|---|
| `n_sources` (unique path,page pairs the frozen parser found) | 2 |
| `Sources` lines in the prose | 4 |
| `n_opened` | 4 |
| `sources_unopened` | none |
| `sources_all_opened` | **true** — verified by hand for all four lines, see F-18 |
| `guard_blocks` | 0 |
| `has_sources_block` (frozen parser) | false — a parser artefact, see F-18 |
| answer length | 2,940 chars |

There is no key and this is not a score. What it shows is that the citation discipline held:
every page cited was a page opened, the Stop guard never had to intervene, and the answer
volunteered its own limits (it said the series stops at 2021-22 and named the families it
had not checked) rather than inventing the missing years.

---

# Phase 11.F — the "initialize" route

Ali's instruction after reading the Phase 11 report: the recipient should not have
to follow INSTALL.md at all. They open Claude Code in the folder, say
`initialize`, and the folder's own documents are enough for the agent to install
everything. That made F-01 a blocker rather than a deferred item, and it added a
document — `INITIALIZE.md`, the same procedure addressed to the agent — plus
`CLAUDE_ROOT.md`, copied to the distribution root as `CLAUDE.md` so a session
opened there reads it unprompted.

**Numbering note.** The commit "Phase 11.F: two findings from rehearsing the
initialize flow" labels the red-text and timing findings F-18 and F-19. Those
IDs were already taken above. They are **F-20** and **F-21** here; the commit
message is wrong and is left as written rather than rewritten.

### F-01 — `pdftotext` and `claude.exe` were this machine's paths — FIXED

`setup_folder.py` and `index_build.py` carried `C:\Program Files\Git\mingw64\bin\
pdftotext.exe`; `labpaths.py` carried `C:\nvm4w\...\claude.exe`. Neither was ever
looked up on PATH, and `INSTALL.md` promises "Claude Code on the PATH". Gate R3's
grep covered `C:\Users` and `Desktop` only, so both walked through it. On any
second machine `doctor` printed FAIL beside a directory the reader does not have
and no document mentions.

Resolution order now: env var (`PDFTOTEXT_EXE`, `CLAUDE_CMD`), then this machine's
historical location so no recorded run changes, then PATH, then the ordinary
install locations, then a bare name that fails with "not found" rather than with
a stranger's directory. `doctor` names the fix instead of a path.

Verified: on this machine both still resolve to exactly what they always did;
with the env vars set to invented paths, `doctor` reports those paths and exits 1.
Seven tests.

**Class:** blocker. Fixed, commit `d9931b3`.

### F-20 — the red `NativeCommandError` block appears at the pip step

Filed in Phase 11.C against the index pass. The rehearsal saw it first at step 2,
wrapped around pip's own "a new release of pip is available" notice — the second
command anyone runs, before anything interesting has happened. A person watching
their first install sees a red error block and stops.

The warning has been promoted out of step 4 into a standing section before
step 1, naming all three sources: progress messages, the pip notice, and
*building page-range cache, one-time*.

**Class:** friction in the engine, blocker in the document. Documented.

### F-21 — the time estimate was optimistic

500 documents at 12 workers: 133 s wall — index 24 s, shelf 67 s, caption index
0.2 s, caption vectors 40 s. That is 4.4 minutes per thousand. The runbook said
three. An estimate someone watches a progress bar against must not be optimistic;
it now says three to six.

**Class:** friction. Fixed in the document.

### F-22 — `REFUSED ... already has a CLAUDE.md` reads as a failure

Re-running `install` on an installed folder exits 3 with
`REFUSED <folder> already has a CLAUDE.md. Run uninstall first`. The refusal is
right — but `INSTALL.md` also says "an interrupted install is resumed by
re-running the identical command", and writing `CLAUDE.md` is the *last* thing
install does. An agent that reads exit 3 as failure, and takes the message's own
advice, will run `uninstall` and throw away a completed index.

`INITIALIZE.md` now says: exit 3 with that message is a finished install, not a
failed one; go to step 5, and do not uninstall to clean up first.

**Class:** blocker for the agent route. Documented; the engine is unchanged.

### What the rehearsal proved

A fresh temp folder, the package copied in, `CLAUDE.md` at the root, 500 documents
beside it. Following `INITIALIZE.md` literally:

| step | result |
|---|---|
| 1 python | 3.11.5 |
| 2 venv + pip | 35 packages, clean |
| 3 doctor | 9 checks, 0 failed |
| 4 install | indexed=489 image_only=9 failed=1 unsupported=1, 39,647 pages, 146 families, 472 documents, 133 s |
| 5 self-test | `_overall` pass |
| the model's first command | `c_shelf.py find --fusion rrf --caption-channel lex --compact 8` run from the documents folder with no `--db` and no `--shelf`: eight ranked publications, exit 0 |

That last row is the one F-02 used to kill. The registry entry names
`engine\artefacts\pages.db`, which is the file that exists.

**Still untested:** a machine that is not this one, a genuinely cold model cache,
the 2,000-document path, the interactive permission prompts, and whether a fresh
agent actually follows `INITIALIZE.md` rather than improvising. That last one is
what Ali's run tests.
