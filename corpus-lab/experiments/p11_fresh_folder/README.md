# P11 — the fresh-folder acceptance stage

Plan F, `plans_fable/F_FRESH_FOLDER_ACCEPTANCE/EXECUTE_2026-09-17.md`, run 2026-09-17 on
branch `phase11-fresh-folder`.

## Purpose

Every install this project has ever measured was driven by
`corpus-lab/bin/p10_cleanroom.py`, a harness that knows the engine inside out. Nobody had
followed the package's own `INSTALL.md` as a stranger would. Ali's professor will be a
stranger. This phase builds the stage for that test — a Desktop folder Ali can open cold,
holding only raw documents and the portable package — and rehearses the run first, so that
he does not spend an evening on a failure findable in ten minutes.

The rule for the test: *if you need knowledge that is not in the package's `INSTALL.md` to
make it work, that is a usability bug.*

This phase builds the stage. Ali runs the play.

## Method

Four phases, each with its own run record.

**A — build.** Test suite, then `make_portable.py --out dist` from a clean HEAD; manifest
checks (`package_commit` equals HEAD, `package_dirty` false, `default_builder` v1, `refused`
empty); `bin/` compared file-by-file against the `02f53c8` package; the whole package
grepped for `C:\Users`, `Desktop`, `C:\Program Files`, `nvm4w`, `retrieval-lab\` and
`_private`.

**B — stage.** `C:\Users\Ali\Desktop\portable-test\` with `engine\` (the package, every
sha256 in `PACKAGE_MANIFEST.json` verified against the copy), `research\` (a copy of
`harness/corpus_2000` exactly as it is, odd folder names and non-PDF files included), and
`ACCEPTANCE_TEST.md`, a scorecard carrying no commands, no paths beyond `engine\INSTALL.md`
and no expected answers. Nothing else written there; no `install`, `doctor`, `ask`,
`claude`, `pip` or `venv` ever run inside it.

**C — dress rehearsal.** In a throwaway temp copy with `harness/corpus_500`, following
`INSTALL.md` literally, in PowerShell, in the order and with the words it uses, consulting
nothing else. Every step timed and logged. Then the commands the installed `CLAUDE.md`
prints, run by hand from inside the research folder **with no `--db`/`--shelf` flags**,
because that is how the model runs them. Then one live Sonnet answer through
`setup_folder.py ask --stream-json`, its `Sources` block checked against the pages the
transcript shows as `OPENED` using the frozen v3 scorer's own parsing. Then the
moved-folder probe, then `uninstall` and a full residue check.

Three rehearsals were needed: each of the first two hit a blocker, which was recorded,
fixed with tests, the package rebuilt, and the rehearsal restarted from a **new** temp
directory.

**D — blockers only.** Two fixes, each with a failing-then-passing test, each its own
commit. Friction was never fixed; it is the material for the next plan.

## Inputs

- HEAD at start `a9ab77a` (branch `phase11-fresh-folder`, from `phase10-trust-and-repro`)
- `harness/corpus_2000` — 2,000 files, 390 MB, staged for Ali, never written to
- `harness/corpus_500` — 500 files, the rehearsal rung, never written to
- `dist/retrieval-portable-02f53c8` — the previous package, read only for comparison
- machine: Python 3.11.5, 16 logical processors, no lab environment variable set

## Outputs

- `C:\Users\Ali\Desktop\portable-test\` — `engine\` (package `retrieval-portable-43ed356`),
  `research\` (2,000 files), `ACCEPTANCE_TEST.md`
- `dist/retrieval-portable-43ed356/` — the package, built from a clean HEAD
- `FINDINGS.md` — 10 predictions adjudicated, 9 further findings, Ali's column left empty
- `A_package/`, `B_stage/`, `C_rehearsal/` — run records and every rehearsal log, including
  the live transcript `r3_09_ask1.jsonl` and the answer `r3_09_answer.md`
- `corpus-lab/tests/test_install_registers_artefacts_db.py` (5 cases)
- `corpus-lab/tests/test_install_md_selftest_command.py` (4 cases)

## Gate

**No numeric gate.** The pass condition for this phase is: Ali's folder is staged, the
rehearsal completed every `INSTALL.md` step, and every finding is on file.

All three hold. Every `INSTALL.md` step in rehearsal 3 exited 0.

## Result

**Two blockers, both fixed, both the same shape.**

**F-02.** `c_stack.do_setup` registered the pages database as a hardcoded development-rung
constant, `<L.STACKS>/s2_fts5/harness_15000.db`, which does not exist in a portable install.
The machine-global registry is the only thing standing between the model and the engine —
every command `CLAUDE.md` prints carries no `--db` and no `--shelf` — so the first command a
stranger reaches died with `sqlite3.OperationalError: unable to open database file`. Fixed
in `c0442de` by plumbing `--db` through exactly as `--shelf-dir` already was.

**F-17.** `INSTALL.md`'s "Check the build" command exits 1 on any folder that is not the
15,000-file rung, because `--expect-pages` defaults to that rung's page count. Fixed in
`43ed356`, document only: the command now prints `--expect-pages 0` and says what it means.

Both were invisible to seven nights of gates for the same reason: `p10_cleanroom.py` passes
`--db`, `--shelf` and `--expect-pages 0` on every call, so no gate ever ran the commands a
reader of `INSTALL.md` would run. The harness measured the engine and never the plumbing a
real user depends on. **That is the finding of this phase**, and it is larger than either
bug.

Of the ten predictions: six confirmed (F-01, F-02, F-04, F-07, F-08, F-09), one denied
(F-05 — no stray `_private\` appears), one half-confirmed (F-06 — undocumented, but the
timing is fine on 16 cores), one satisfied (F-10 — `uninstall` touched no other registry
entry), one untestable here and passed to Ali (F-03, the permission prompts). Nine further
findings, F-11 to F-19, were added; the three most likely to bite are F-03, F-16 (a routine
progress message renders as a red PowerShell error and looks exactly like a crash) and F-09.

The one live answer: 149 s, rc 0, four `Sources` lines, every one of them a page the
transcript shows as `OPENED`, guard never triggered, and the answer volunteered where its
series stopped instead of inventing the missing years.

## Adopted?

Yes. The two fixes are on `phase11-fresh-folder` with tests; the suite goes 106 → 115, all
passing. Ali's folder is staged with the fixed package and is waiting for him. Nothing
pushed.

## Run record

- `A_package/run_record.json` — id `P11A_package`
- `B_stage/run_record.json` — id `P11B_stage`
- `C_rehearsal/run_record.json` — id `P11C_rehearsal`
- `E_trail/run_record.json` — id `P11E_trail`

## What this does not show

- **Not retrieval quality.** One live answer, no answer key, no score. It shows citation
  discipline held on one question, nothing about whether the answer is right.
- **Not sir's machine.** The package still hardcodes this machine's `pdftotext.exe` and
  `claude.exe` paths (F-01); `doctor` passes on them here precisely because this is the
  machine they came from. Ali's instruction on 2026-09-17 was to cover that with a
  `SETUP.md` rather than fix it in the engine, so it stays open.
- **Not the interactive experience.** Rule 7 forbade an interactive `claude` session, so
  the permission prompts of F-03 — predicted to be the loudest friction — are unmeasured.
  Only Ali's run will show them.
- **Not a fresh install.** Every Python wheel and the 130 MB embedding model came from
  cache; 0 bytes were downloaded. A stranger's first run does both, and F-15 shows `doctor`
  cannot be made to simulate that.
- **Not a new corpus.** `corpus_500` and `corpus_2000` come from the same generator as every
  other gate this project has run. Cross-folder generalisation remains untested; the
  adversarial professor folder is still the next experiment.
- **Not the 2,000-file path.** The rehearsal used the 500-file rung. Ali's install is the
  first 2,000-file run through this package.
