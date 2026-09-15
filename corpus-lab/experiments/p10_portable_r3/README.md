# p10_portable_r3 — proving the package does not read the lab

Plan E Phase 3.5. Gate R3 verdict: **PASS** (all four rows).

## Purpose

`labpaths.py` resolves every path from `__file__`, so a copied `bin/` *should* work
standalone. "Should" is the word that made this gate necessary: the installer had never
once been run from a copy, and a single stray absolute path — a default, a fallback, a
cached registry entry — would mean the package works **only** on the machine that built it,
and works there for the wrong reason.

Reasoning about the code cannot settle this, because the failure mode is a path taken at
run time under conditions that only arise elsewhere. So: record every file the install
opens, and look.

## Method

`p10_trace.py` writes a `sitecustomize.py` into the clean venv. Python imports
`sitecustomize` automatically at interpreter start-up, so **every process launched from
that venv inherits the hooks before any lab code runs** — including the children the
installer spawns, which is where the reads that matter happen.

It wraps `builtins.open`, `io.open`, `sqlite3.connect`, `os.scandir` and `os.listdir`, and
appends every absolute path to `reads.log`. The install then runs against a **fresh** copy
of the corpus and a fresh artefacts directory, so the trace covers a real first install
rather than a resumed one.

Afterwards every logged path is checked against two roots: the development repository, and
the development repository's own Claude project key under `~/.claude/projects`.

## Inputs

| path | note |
|---|---|
| `%TEMP%/p10_clean_A/package/` | the packaged copy, with its own venv |
| `harness/corpus_500` | copied fresh for the traced install |
| `corpus-lab/state/phase10_gate_r_spec.md` | committed `c4dce54`, before any clean-room command |

```
python corpus-lab/bin/p10_trace.py --room A --corpus harness/corpus_500 --workers 8
python corpus-lab/bin/p10_gate_r.py r3 --room A
```

## Outputs

| path | what |
|---|---|
| `corpus-lab/state/phase10_gate_r3_result.json` | the four rows and the verdict |
| `%TEMP%/p10_clean_A/reads.log` | every traced path, one per line, with its kind |
| `%TEMP%/p10_clean_A/trace.json` | the counts and any offending paths |
| `corpus-lab/tests/test_trace_hook.py` | four tests proving the tracer itself works |

## Gate

`corpus-lab/state/phase10_gate_r_spec.md`, commit `c4dce54`.

| row | check | result |
|---|---|---|
| R3.1 | no read under the development repo | **PASS** — 891 reads traced, none |
| R3.2 | no read under the dev repo's Claude project key | **PASS** — none |
| R3.3 | package grep for `C:\Users` and `Desktop` is empty | **PASS** — 0 hits |
| R3.4 | the traced install actually ran | **PASS** — rc=0, 112s |

## Result

**891 distinct paths were read across the install and every child process it spawned.
None of them is under the development repository, and none is under its Claude project
key.** The traced install completed normally (rc 0, 112 seconds — the same as the untraced
one, 118 seconds), so the trace did not distort what it measured.

Two absolute development-machine paths were removed from `labpaths.py` to get here: the
pre-move `harness` sibling fallback and the hard-coded `RASHIP_ROOT` default. Neither had
been taken since the phase 1/2 moves completed, but both would have shipped in the package.
With the env var absent there is now simply no RASHIP root.

### The tracer failed twice before it could be trusted, and that is the finding

Both failures produced an **empty log**, which this gate would have read as *"no reads
happened"* — a pass. That is the worst available failure mode for a check, and it is worth
recording how close it came:

1. **`_note` opened the log through the traced `open`.** The first traced call recursed
   into `_note`, which tried to take a non-reentrant lock it was already holding. The
   install hung indefinitely and wrote nothing.
2. **The tracer's source is built as a string literal**, so `\t` in it was interpreted when
   `p10_trace.py` was parsed. The generated `sitecustomize.py` contained a real tab inside
   a string literal, never loaded, and wrote nothing.

`corpus-lab/tests/test_trace_hook.py` now proves, before the tracer is trusted, that the
generated source parses, that it keeps its escapes, that a traced process records all four
hook kinds and **terminates**, and that it is a clean no-op when the log variable is unset.
A check that cannot fail is not a check, and an empty log must never again be mistaken for
a clean one.

## Adopted?

**Yes.** The package is independent of the development repository on the evidence of this
trace, and the tracer is kept, with its tests, for re-running R3 after any future change to
`labpaths.py` or the package allowlist.

## Run record

`corpus-lab/experiments/p10_portable_r3/run_record.json`, id `p10_gate_r3`,
spec `corpus-lab/state/phase10_gate_r_spec.md` at commit `c4dce54`.

## What this does not show

- **A trace proves no dev-repo read on THIS run**, on this OS, for this corpus, with this
  package. It is a trace, not a proof about all inputs. A code path taken only for a file
  type absent from `corpus_500`, or only on a second install, is not covered.
- **It traces Python-level file access only.** A subprocess that is not Python — and the
  install shells out to `pdftotext.exe` — is invisible to these hooks. What that binary
  reads was not traced.
- **It says nothing about network access.** No socket was hooked; the claim that nothing is
  uploaded rests on the code, not on this trace.
- **It says nothing about correctness.** An install that reads only its own files can still
  build a useless index, and R3 would still pass.
- **The grep is a text search**, so it proves no absolute user path appears in the package's
  source — not that none could be constructed at run time.
