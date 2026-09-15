# p10_portable_r1 — two clean builds of the same folder

Plan E Phase 3.3. Gate R1 verdict: **`GATE_R1_STOP`** on one row of eight (R1.3).
The stop is recorded under the gate line as written. The cause is fully diagnosed
below, and it is not a difference in what was built.

## Purpose

Plan E §1.4 found that the "portable" installer had never been run from a copy. It ran
scripts out of the development repo, wrote its artefacts into the development repo, and
built the shelf with the experimental v2 builder — the one that failed Gate S — while
production and the demo ran v1. So the portable was not portable, and what it built was
not what had been measured.

Gate R1 asks the narrowest useful version of "is it portable": install the packaged
thing twice, from scratch, in two rooms that cannot see each other or the development
lab, and ask whether the two builds are the same build.

## Method

`p10_cleanroom.py`. One room is: a copy of `dist/retrieval-portable-02f53c8` under
`%TEMP%`, its own venv built from `requirements-portable.txt`, all nine `*_ROOT` /
`LAB_PRIVATE` / `HARNESS_KEYS` variables unset **and asserted unset from inside the clean
interpreter**, a **copy** of `harness/corpus_500` (the rung is never touched), and its own
artefacts directory. Rooms A and B use distinct paths for package, venv, corpus and
artefacts; nothing in A is reachable from B.

Per room: `doctor`, then
`install --folder <copy> --artefacts <room>/artefacts --seed-env --workers 8`, then
`c_selftest.py --db … --shelf … --expect-pages 0`, then the fixed 20-query probe list
from the gate spec, then `uninstall`, with the project-key memory count asserted zero
before and after.

**"Matching artefact hashes" means the canonical export**, not the raw files: sorted
logical rows with `built_at`, `indexed_at` and every timing column removed, and the
vector stores hashed after rounding to 3 decimal places. Raw SQLite files carry
timestamps and filesystem walk order and can never match; comparing them would fail every
time and prove nothing.

## Inputs

| path | note |
|---|---|
| `dist/retrieval-portable-02f53c8/` | 20 files, `PACKAGE_MANIFEST.json`, `default_builder: v1` |
| `harness/corpus_500` | 500 files; copied, never written to |
| `corpus-lab/state/phase10_gate_r_spec.md` | committed `c4dce54`, **before** any clean-room command |

```
python corpus-lab/bin/make_portable.py
python corpus-lab/bin/p10_cleanroom.py build --room A --package dist/retrieval-portable-02f53c8 --corpus harness/corpus_500 --workers 8
python corpus-lab/bin/p10_cleanroom.py probe --room A
   (likewise room B)
python corpus-lab/bin/p10_cleanroom.py teardown --room A   (and B)
python corpus-lab/bin/p10_gate_r.py r1 --a A --b B
```

## Outputs

| path | what |
|---|---|
| `corpus-lab/state/phase10_gate_r1_result.json` | the eight rows, the verdict, the diagnosis |
| `%TEMP%/p10_clean_{A,B}/room.json` | per-room provenance, timings, memory asserts |
| `%TEMP%/p10_clean_{A,B}/artefacts/build_manifest.json` | counts, versions, hashes |
| `%TEMP%/p10_clean_{A,B}/artefacts/BUILD_REPORT.md` | the same in one page |
| `%TEMP%/p10_clean_{A,B}/artefacts/canonical_export.json` | the compared object |
| `%TEMP%/p10_clean_{A,B}/retrieval_outputs.json` | the 20 + 5 + 3 + 1 + 2 probe captures |

## Gate

`corpus-lab/state/phase10_gate_r_spec.md`, commit `c4dce54`, author date
2026-09-15T21:17:53+05:00 — before the run record started.

| row | check | result |
|---|---|---|
| R1.1 | both installs exit 0 | **PASS** — A rc=0, B rc=0 |
| R1.2 | each install ≤ 20 min | **PASS** — 118s and 118s |
| R1.3 | `canonical_export.json` sha256 A == B | **FAIL** — `pages.files` differs |
| R1.4 | manifest counts A == B | **PASS** — every count equal |
| R1.5 | vectors deterministic | **PASS** — *bit-identical*, both stores |
| R1.6 | retrieval outputs A == B | **PASS** — all 31 probes identical |
| R1.7 | same self-test check set, passing in both | **PASS** — 18 checks, both pass, symmetric difference empty |
| R1.8 | memory files 0 before and after in both | **PASS** |

## Result

**The package installs from a copy, and the two builds are logically identical.**

Both rooms indexed 500 files in **118 seconds**, produced **472 documents, 146 families,
4,483 captions, 472 card vectors**, and the identical status split — 489 indexed, 9
image-only, 1 encrypted, 1 unsupported type. All 18 self-test checks passed in both.

Three results are stronger than the gate required:

- **The vectors are bit-identical**, not merely equal to 3 decimal places. The spec
  allowed a "deterministic up to float noise" class; it was not needed.
- **All 31 retrieval probes returned identical ranked output** — 20 `find`, 5 `have` on
  the five largest families, 3 `series`, `coverage`, and 2 `have`. The tie-noise
  allowance the spec provided was not needed either.
- **Four of the five canonical tables — `shelf.docs`, `shelf.families`, `shelf.cards`,
  `shelf.captions` — are byte-identical**, all 5,573 rows.

### Why R1.3 failed, exactly

The sole difference is in `pages.files`, and it is the `file_id` column:

- 255 of 500 rows differ; every one of them has the **same `rel`, `sha256`, `size`,
  `n_pages`, `status` and `error_class`** and a different `file_id`;
- dropping `file_id` alone makes the two tables **identical as sets**;
- `file_id` is a surrogate key assigned in insertion order, i.e. filesystem walk order;
- **nothing downstream references it.** The shelf tables key on `rel`, which is why all
  four of them matched before any adjustment.

So this is the "directory walk order" non-determinism that `BUILD_REPORT.md` names, and
that the canonical export exists to neutralise. The export drops wall-clock columns but
not surrogate row ids, and that is a gap in the **comparison method**, not a difference
between the builds.

**The gate is still recorded as STOP.** The R1 line says *any* canonical difference
fails, and relaxing a rule after seeing which way it went is how a gate stops meaning
anything. The fix — dropping surrogate ids in the canonical export — goes to the handoff
as a method change for next time, pre-registered before it is used. Had it been in place
tonight, R1 would have passed all eight rows.

### Two real portability defects Gate R1 found before it could run

Both were invisible in the development repo, where the missing pieces are always present:

1. **`c_stop_guard_selftest.py` was not in the package.** `c_selftest.py` shells out to
   it, so the clean room returned `stop_guard_behaviour: {pass: false, n_checks: null}` —
   the check had not run at all. Added to the allowlist.
2. **The clean room asserted the 15,000 rung's page count** (1,206,260) against a
   500-file corpus. `c_selftest.py` already has `--expect-pages 0` for exactly this case.

A third defect was in the harness rather than the package: the clean room's memory check
matched project keys by substring and reported 3 memory files for a brand-new temporary
folder, having matched `C--Users-Ali` — a prefix of every path on this machine. It now
matches the derived key exactly, and was verified to read 0 for a fresh folder and 7 for
the development repo, so it can detect the thing it is checking for.

## Adopted?

**Yes.** The package is the artefact Phase 3.4 and 3.5 test and the one
`INSTALL_FOR_SIR.md` now describes. `default_builder: v1` is in `PACKAGE_MANIFEST.json`
and in every `build_manifest.json` the installs wrote.

## Run record

`corpus-lab/experiments/p10_portable_r1/run_record.json`, id `p10_gate_r1`,
spec `corpus-lab/state/phase10_gate_r_spec.md` at commit `c4dce54`.

## What this does not show

- **Nothing about retrieval quality.** R1 asks whether two builds agree, not whether
  either is any good. Identical output from both rooms would be just as identical if the
  ranking were useless.
- **One corpus, 500 files, one machine, one OS, twice, minutes apart.** It does not show
  that a build on a different machine, a different Python patch version, or a different
  CPU would match — and the bit-identical vectors in particular are the kind of result
  that can depend on the CPU's instruction set.
- **It does not test the v2 builder.** Both rooms used v1, which is the default and the
  point. The v2 shelf remains experimental and Gate-S-failed.
- **It says nothing about a folder the tool has not seen.** `corpus_500` comes from the
  same generator as every other rung. Gate R2 uses a second rung from that same
  generator, which is not real-world validation either; **genuine cross-folder
  generalisation remains untested.**
- **`uninstall` was verified to remove `CLAUDE.md` and `.claude`**, but no test here
  covers a partially-completed or interrupted install.
