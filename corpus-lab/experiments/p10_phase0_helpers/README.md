# p10_phase0_helpers — the instruments the rest of the night is measured with

Plan E (`plans_fable/E_TRUST_AND_REPRO/EXECUTE_2026-09-16_NIGHT.md`) Phase 0.
Branch `phase10-trust-and-repro`, off `phase9-production-hardening` at `1e7c7b3`.

## Purpose

Before anything is measured tonight, establish two things.

**First, that the lab still reads what it read yesterday.** Every number this plan
corrects or extends was produced by this code on this corpus. If the baselines no
longer reproduce, then something moved underneath the whole Phase 9 record, and the
right response is to stop rather than to publish corrections built on a shifted
foundation. That is the `BASELINE_BROKEN` stop condition.

**Second, that the documentation standard is enforced by a mechanism rather than by
an intention.** Ali's standard is that another competent person, handed the repo, the
portable package and a corpus, can reproduce the build and see where every headline
number came from — without this chat and without Ali's memory. A checklist in a plan
does not survive a tired night at 3 a.m.; a script that exits 1 does. So Phase 0 builds
the two scripts every later phase is required to run through: `run_record.py`, which
writes the provenance of a run, and `docs_check.py`, which refuses to certify a record
that is missing any of it.

Nothing in this phase measures retrieval, and nothing in it changes retrieval.

## Method

1. **Branch and baselines.** Created `phase10-trust-and-repro`. The pre-existing
   uncommitted work in the tree (the `00_archive/` reorganisation, `ENGINE.md`, and
   the `c_stack.py` deny-list entry that follows `ACCEPTANCE.md` into `00_archive/`)
   was committed as `WIP (resumed): …` rather than discarded, per the plan's resume
   rule. Then the four self-tests and the offline baselines were re-run.
2. **Checkpoint helper.** `p9_checkpoint.py` gained `--file <path>`. Its default is
   still `state/phase9_checkpoint.json`, so every Phase 9 command in the record
   reproduces unchanged; a filename containing `phase10` switches the run id, branch,
   heartbeat log and step headings to the Phase 10 set.
3. **`run_record.py`.** `start` / `note` / `finish` / `show`. `start` captures the
   section-D fields; `finish` refuses to close a record whose declared output already
   existed when `start` ran, unless `--supersedes <path>` is given — and then writes
   the `<old>.SUPERSEDED.md` sibling itself. That is rule 15 turned into a mechanism:
   the only way to replace a recorded number is to leave the old one in place and say
   so in writing.
4. **`docs_check.py`.** Five checks, described under *Gate* below. Gate D at the end
   of the night is this script's exit code.
5. **Pins.** `p10_pins.py` walks the real dependency closure of the four declared
   roots and pins each at the live venv's version, rather than copying `pip freeze`
   wholesale — the dev venv also carries `fastmcp`, `lancedb`, `keyring` and `pytest`,
   none of which the portable imports.
6. **Demo-path protection.** `checksums.py` gained an additive `--also-dir`, so one
   label covers both the planted corpus files and the built shelf Ali demos from.
   With no `--also-dir` the snapshot is byte-for-byte what it always was.
7. **Pre-existing file snapshot.** `p10_snapshot_files.py` lists what existed before
   tonight, scoped to the directories `docs_check` guards. It deliberately does *not*
   walk `_private/harness_keys`: a committed file listing 9,255 key filenames would
   breach the contamination rule for no benefit.

`pytest` was installed into the dev venv, which did not previously have it; Plan E
Phase 1.5 requires `python -m pytest corpus-lab/tests -q`. It is a dev dependency and
is excluded from `requirements-portable.txt`. `corpus-lab/tests/conftest.py` points
pytest's scratch space at `corpus-lab/99_scratch/pytest_tmp`, because the system temp
root is not writable for this account and a suite that cannot start looks exactly like
a suite that fails.

## Inputs

| path | sha256 |
|---|---|
| `corpus-lab/bin/p9_checkpoint.py` (after 0.2) | `92aa2ccb8c6f8255` |
| `corpus-lab/bin/checksums.py` (after 0.6) | `3485c8544b2d6f02` |
| `_private/canaries/canary_manifest_pass2.csv` | via `CANARY_MANIFEST`, scoring-only |
| `corpus-lab/02_stacks/s7_shelf/` | 8 artefacts, hashed into the snapshot below |

Baseline commands, exactly as run:

```
.venv/Scripts/python.exe corpus-lab/bin/c_stack.py selftest
.venv/Scripts/python.exe corpus-lab/bin/c_provenance_selftest.py
.venv/Scripts/python.exe corpus-lab/bin/c_stop_guard_selftest.py
cd harness/corpus_15000 && ../../.venv/Scripts/python.exe ../../corpus-lab/bin/c_selftest.py
.venv/Scripts/python.exe -u corpus-lab/bin/c_caption_gate.py --channel lex
.venv/Scripts/python.exe -u corpus-lab/bin/c_offline_gate.py --v2 --page-only --query-mode row --caption-channel dense_first
.venv/Scripts/python.exe -u corpus-lab/bin/c_route_gate.py
```

## Outputs

| path | sha256 |
|---|---|
| `corpus-lab/bin/run_record.py` | `d17f1f1a70c68db8` |
| `corpus-lab/bin/docs_check.py` | `d3233809e3b50e45` |
| `corpus-lab/bin/p10_pins.py` | `881b0155c3e6becf` |
| `corpus-lab/bin/p10_snapshot_files.py` | `479523f1c1056106` |
| `corpus-lab/requirements-portable.txt` | `eef6cf377a7e1556` |
| `corpus-lab/state/phase10_preexisting_files.txt` | `21eb36abf5c2acde` |
| `corpus-lab/state/checksums/s7_phase10_pre.json` | `f5fea41a25e25aaf` |
| `corpus-lab/tests/test_run_record.py`, `test_docs_check.py`, `conftest.py` | new |
| `corpus-lab/state/phase10_baseline_console.txt` | baseline console |
| `corpus-lab/state/phase10_checkpoint.json` | Phase 10 checkpoint |

(Short hashes above are the first 16 hex characters; the full values are in
`corpus-lab/state/phase10_helper_hashes.json`.)

## Gate

No pre-registered numeric gate governs Phase 0 itself. Two conditions applied:

- **`BASELINE_BROKEN`** — stop the night if any baseline misses its number. Spec:
  Plan E §0.1, which fixes them in advance at 25 / 10 / 24 / 18 for the self-tests
  and 10/17, 16/17, 52/57 for the offline baselines.
- **Both helper self-tests must pass.** `docs_check.py` is the eventual Gate D, so a
  `docs_check` that cannot detect a defect would certify a broken record as sound.
  Its suite therefore builds a temp tree with exactly one deliberate omission of each
  kind and asserts the run fails *and names that reason*, plus two negative controls
  proving the checks are not simply always-fail.

The five `docs_check` mechanisms: **A** every run record created during the run has
all its section-D fields and has been finished; **B** every experiment README carries
the nine fixed headings; **C** no run record cites a gate spec whose commit is dated
after the run started; **D** nothing written during the run overwrote a pre-existing
path; **E** every scorer output names its `scorer_version` and `key_sha256`.

## Result

**All baselines reproduced. No `BASELINE_BROKEN`.**

| baseline | expected | measured |
|---|---|---|
| `c_stack.py selftest` | 25 | **25/25** |
| `c_provenance_selftest.py` | 10 | **10/10** |
| `c_stop_guard_selftest.py` | 24 | **24/24** |
| `c_selftest.py` (in rung) | 18 | **18/18** |
| caption gate, document top-10 | 10/17 | **10/17** |
| caption gate, pool@100 | 16/17 | **16/17** |
| offline gate B2c (`row+caption_dense_first`) | 52/57 | **52/57** |
| route gate, document / identifier level | 11/11, 4/4 | **11/11, 4/4** |

The state files these gates rewrote were diffed line by line: every changed line is a
timestamp or a wall-clock timing. No recorded number moved.

Test suite: **67 passed** — 6 `run_record` self-tests, 14 `docs_check` self-tests, and
the 61 pre-existing `evidence_v1` tests, all green.

Pins: 36 packages in the runtime closure. The four roots are `fastembed==0.8.0`,
`onnxruntime==1.30.0`, `numpy==2.4.6`, `pdfplumber==0.11.10` on python 3.11.5 with
claude code 2.1.257 — the versions Plan E's header names.

Demo-path snapshot `s7_phase10_pre`: **26 files hashed, 0 missing**, and an immediate
`verify` reads **26 unchanged, 0 CHANGED, 0 MISSING**. `harness/corpus_15000` has
neither `CLAUDE.md` nor `.claude`.

## Adopted?

**Yes**, as infrastructure. `run_record.py` and `docs_check.py` are required by every
later phase; `requirements-portable.txt` ships in the Phase 3 package; the
`s7_phase10_pre` label is the demo-path guard that Phases 3 and 5 verify against.

The three additive edits to existing scripts are all default-preserving and are listed
in the handoff: `p9_checkpoint.py --file`, `checksums.py --also-dir`, and
`corpus-lab/tests/conftest.py` (new file, affects only the test suite).

## Run record

Phase 0 builds `run_record.py`; it does not yet run under it. Its provenance is this
README, the commit `Phase 10.0: …`, and `corpus-lab/state/phase10_checkpoint.json`
steps 0.1–0.7. Every phase from 1 onward runs under `run_record.py` and is checked by
`docs_check.py`.

## What this does not show

- **Nothing about retrieval quality.** No ranking, shelf, caption, prompt or guard
  behaviour was touched or measured. The baselines here prove only that the existing
  instruments still read what they read before.
- **Nothing about portability.** `requirements-portable.txt` was generated from this
  venv and has not yet been installed into a clean one. Whether it is sufficient is
  Gate R1's question, in Phase 3 — until that gate runs, this file is a hypothesis.
- **Nothing about whether the scorer is correct.** Phase 0's baselines were produced
  by the same v1/v2 scorers whose defects Plan E §1 diagnoses. Reproducing a number
  is not the same as the number being right; that is Phase 1's question.
- **`docs_check` checks mechanisms, not meaning.** It can prove a README has a
  *Result* heading; it cannot prove the result under it is true. It can prove a gate
  spec was committed before a run started; it cannot prove the gate was a sensible one.
