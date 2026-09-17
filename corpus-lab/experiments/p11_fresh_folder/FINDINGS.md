# Plan F / Phase 11 — findings

Fresh-folder acceptance stage. Package `retrieval-portable-a9ab77a`, built from HEAD
`a9ab77ada990c24993134a27012bcc09aceed6dc` on branch `phase11-fresh-folder`.

The predictions below were copied verbatim from
`plans_fable/F_FRESH_FOLDER_ACCEPTANCE/EXECUTE_2026-09-17.md` section 3 **before** the
first rehearsal command was run. The *observed in rehearsal* and *class* columns were
filled afterwards. The *observed by Ali* column is left empty for him.

**Classes.** *blocker* — an `INSTALL.md` step followed exactly as printed that exits
non-zero or leaves the next step impossible, or a `CLAUDE.md` command run from inside the
installed folder with no extra flags that prints `NO_REGISTERED_ROOT`, `unable to open
database file`, a traceback, or nothing where output is documented. *friction* —
everything else a stranger had to know, guess, wait for or tolerate that `INSTALL.md` did
not say. *not a bug* — it worked and the document was enough.

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
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-02 — registered pages-database path

**Prediction.** `c_stack.py do_setup` registers `<package>\02_stacks\s2_fts5\harness_15000.db`
as `db`, not the `--artefacts` `pages.db`; `02_stacks` is excluded from the package. Yet
Gate R2's one live answer opened two pages successfully. The planning session could not
reconcile these; the rehearsal must. If `open` or `inside` prints `unable to open database
file` or `NO_REGISTERED_ROOT`, this is a **blocker**.

| column | value |
|---|---|
| observed in rehearsal | **CONFIRMED, and it is a blocker.** After a clean `install --folder $R
esearch --artefacts .rtefacts --seed-env`, the registry entry written for the folder is `"db": "<R>\engine_stacks\s2_fts5\harness_15000.db"` — a path that **does not exist** (`Test-Path` false; `02_stacks` is on the package's excluded-dirs list). `"shelf"` is correct, `<artefacts>\shelf\shelf.db`, because `--shelf-dir` is already plumbed through. The very first command `CLAUDE.md` tells the model to run, executed from inside `$R
esearch` with no `--db`/`--shelf`, dies: `sqlite3.OperationalError: unable to open database file`, raised at `c_shelf.py:115` in `Ctx.__init__` via `get_ctx` at `c_shelf.py:199`, exit code 1, full traceback on stderr. `find`, `have`, `inside`, `open`, `note`, `notes` all route through the same `get_ctx`, so none of them can work. See `C_rehearsal/08a_find.log`. |
| observed by Ali | |
| class | **blocker** — fixed in Phase D, see below. |

**Why Gate R2 passed anyway.** The planning session could not reconcile the broken
registration with R2's successful two-page answer. The answer is that the clean-room
harness never used the registry: `corpus-labin\p10_cleanroom.py:243` builds every shelf
invocation as `[python, c_shelf.py, "--db", <artefacts>\pages.db, "--shelf", ...]`, passing
both paths explicitly on the command line. `--db` overrides the registry lookup entirely.
So R2 measured the engine, and never the one line of plumbing that a real user depends on.
This is the exact failure mode the plan was written to catch: *"every one of those installs
was driven by a harness script that knows the engine inside out"*.

**Responsible line.** `c_stack.py:280-282`, in `do_setup`:

```python
CSH.do_register(str(root),
                str(L.STACKS / "s2_fts5" / "harness_15000.db"),   # <- hardcoded
                str(sd / "shelf.db"))                             # <- parameterised
```

`shelf_dir` is a `do_setup` parameter fed by `setup_folder.py:257`'s `--shelf-dir`. The db
argument beside it is a frozen development-rung constant. `setup_folder.py:154` already
computes the right value as `art["db"] = <artefacts>/pages.db` and passes it to every other
stage; it simply never reaches `c_stack setup`.

### F-03 — a permission prompt on every engine command

**Prediction.** Interactive Claude Code in the installed folder will ask permission for
every engine command, because `.claude\settings.json` carries only a deny list and a Stop
hook, no allow rules. The `ask` subcommand avoids this with `--permission-mode
bypassPermissions`, but `INSTALL.md` leads with the interactive route.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-04 — moving the engine folder breaks every command

**Prediction.** `CLAUDE.md` and the Stop hook embed the absolute path of
`engine\.venv\Scripts\python.exe` and `engine\bin\c_shelf.py`. Moving or renaming the
engine folder after install breaks every command silently. `INSTALL.md` does not say
"do not move it".

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-05 — an empty `_private\` appears next to the package

**Prediction.** `install` creates an empty `_private\` next to the package because
`labpaths.PRIVATE` defaults to `<package parent>\_private` and something calls `mkdir`.
Untidy, and it invites the wrong assumption.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-06 — undocumented default `--workers 12`

**Prediction.** The default `--workers 12` is not mentioned in `INSTALL.md`; the R2
install used `--workers 8`. On a laptop 12 pdftotext processes may thrash.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-07 — the embedding-model download is never exercised here

**Prediction.** `BAAI/bge-small-en-v1.5` (~130 MB) is already cached on this machine, so
neither the rehearsal nor Ali's run exercises sir's first-run download.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-08 — "Python 3.11" with no way to check it

**Prediction.** `INSTALL.md` says Python 3.11 but does not say how to check, and
`python -m venv` picks whichever `python` is first on PATH. `doctor`'s first check only
verifies the interpreter is inside `.venv`.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-09 — "Ask it something" stops where the hard part starts

**Prediction.** `INSTALL.md` tells the user to `cd <your folder>` and run
`claude --model claude-opus-5`, but says nothing about what happens next, what a good
answer looks like, what a `Sources` block is, or that a `COVERAGE` line exists.
`INSTALL_FOR_SIR.md` has all of that and is not in the package.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

### F-10 — one machine-global registry shared by every install

**Prediction.** `%LOCALAPPDATA%\retrieval-lab\roots.json` is keyed by folder path. Two
installs cannot collide, but `uninstall` of one must not remove another's entry, and a
stale entry from a deleted folder lingers forever.

| column | value |
|---|---|
| observed in rehearsal | _pending_ |
| observed by Ali | |
| class | _pending_ |

---

## Findings added during execution

### F-11 — the packaged `bin/` differs from the 02f53c8 package by line endings only

**Observed in Phase A.** The plan predicted
`diff -r dist\retrieval-portable-02f53c8\bin dist\retrieval-portable-<HEAD7>\bin` would be
empty. By sha256 it is not: `c_stack.py`, `c_caption_embed.py` and `c_caption_index.py`
differ. Line-by-line comparison of all three shows **zero** differing lines, and
`git diff 02f53c8 HEAD --stat` for them is empty. The delta is CRLF in the older package
against LF in the new one, from git's end-of-line normalization. Package content equals
HEAD, which is what the plan's claim was actually asserting.

**Class:** not a bug. Recorded so the next reader is not alarmed by a non-empty diff.

### F-12 — one flaky test in the suite

**Observed in Phase A, then corrected.** The first run of
`.venv\Scripts\python.exe -m pytest corpus-lab	ests -q` in this session gave **105 passed,
1 failed**:
`corpus-lab/tests/evidence_v1/test_inventory.py::TestInventory::test_08_partially_readable_pdf`
— a PDF with one unreadable page classified `parser_failed` where the test expects
`partially_readable`. It was recorded as a standing pre-existing failure.

That was wrong. The failure has not reproduced in four subsequent runs (three of the file
alone, one of the whole suite), all on the same unchanged code. It is **flaky**, most
likely sensitive to leftover state in `corpus-lab/99_scratch/pytest_tmp`, which `conftest.py`
pins as the suite's temp root and which the first run of a session inherits from whatever
ran last.

The practical consequence for this plan: the true baseline is **106 collected, 106
passing**, and after the F-02 fix the suite is **111 collected, 111 passing** — the old
count plus exactly the five new tests, as Phase D requires.

**Class:** not a bug for this plan. A flaky test is worth someone's attention, but the
flake is in the test's temp-directory hygiene, not in the engine.

### F-13 — `make_portable.py` calls an untracked file "dirty"

**Observed in Phase A.** `make_portable.py:261` derives `package_dirty` from
`git status --short`, which lists untracked files. Creating the experiment directory the
plan itself mandates therefore stamps the package dirty. The package was built only after
committing the plan file and the opened run record.

**Class:** friction, on the builder's side rather than the stranger's.
