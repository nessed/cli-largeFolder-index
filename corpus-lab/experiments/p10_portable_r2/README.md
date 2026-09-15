# p10_portable_r2 — the package against a folder it was not built around

Plan E Phase 3.4. Gate R2 verdict: **PASS** (all six rows).

## Purpose

Gate R1 proved the package installs twice and agrees with itself, but both installs used
`corpus_500` — the rung the installer has been run against before. R2 asks a slightly
harder question: point the same package at a **different** folder, four times the size,
and see whether it installs, self-tests, and answers a question with citations that hold up.

It is deliberately not a scoring run. Nothing is compared against an answer key, no
accuracy number comes out of it, and there is no second room to compare against. The
question is whether the thing works somewhere else at all.

## Method

Clean room C: a copy of `dist/retrieval-portable-02f53c8` under `%TEMP%`, its own venv from
the pinned requirements, all nine lab environment variables unset and asserted unset, and a
**copy** of `harness/corpus_2000` (the rung itself is never touched).

`install --artefacts <room>/artefacts --seed-env --workers 8`, then `c_selftest.py` with
explicit `--db`/`--shelf` and `--expect-pages 0`, then the same fixed probe list as R1
(**captured, not compared** — there is no B), then **one** headless Sonnet question, then
`uninstall`, with the project-key memory count asserted zero before and after.

The question was written for this folder and has no key:

> which years of budget documents does this folder hold, and what does the most recent one
> say about development spending

The citation check uses the **frozen v3 scorer's own functions**
(`reconstruct_full_answer`, `opened_pairs_v3`, `citations_and_mentions`), so it asks
exactly the question the rest of the night asks rather than a second, slightly different one.

## Inputs

| path | note |
|---|---|
| `dist/retrieval-portable-02f53c8/` | 20 files, `default_builder: v1` |
| `harness/corpus_2000` | 2,000 files; copied, never written to |
| `corpus-lab/state/phase10_gate_r_spec.md` | committed `c4dce54`, before any clean-room command |
| `corpus-lab/bin/c_score_live_v3.py` | frozen at `scorer-v3-frozen-2026-09-16` |

```
python corpus-lab/bin/p10_cleanroom.py build --room C --package dist/retrieval-portable-02f53c8 --corpus harness/corpus_2000 --workers 8
python corpus-lab/bin/p10_cleanroom.py probe --room C
<room>/package/.venv/Scripts/python.exe <room>/package/bin/setup_folder.py ask \
    --folder <room>/corpus --model claude-sonnet-5 --stream-json <room>/ask.jsonl "<question>"
python corpus-lab/bin/p10_check_ask.py --room C
python corpus-lab/bin/p10_cleanroom.py teardown --room C
python corpus-lab/bin/p10_gate_r.py r2 --room C
```

## Outputs

| path | what |
|---|---|
| `corpus-lab/state/phase10_gate_r2_result.json` | the six rows and the verdict |
| `%TEMP%/p10_clean_C/room.json` | provenance, timings, memory asserts, the ask check |
| `%TEMP%/p10_clean_C/artefacts/{build_manifest.json,BUILD_REPORT.md,canonical_export.json}` | the build, three ways |
| `%TEMP%/p10_clean_C/retrieval_outputs.json` | the 31 probe captures |
| `%TEMP%/p10_clean_C/ask.jsonl` | the one session's transcript |

## Gate

`corpus-lab/state/phase10_gate_r_spec.md`, commit `c4dce54`, author date
2026-09-15T21:17:53+05:00 — before the run record started.

| row | check | result |
|---|---|---|
| R2.1 | install exits 0 | **PASS** |
| R2.2 | wall ≤ 60 min | **PASS** — 375s |
| R2.3 | self-test passes its applicable checks | **PASS** — 18 checks, none failed |
| R2.4 | Sources block names only pages shown as `OPENED` | **PASS** — 1 citation, 0 unopened |
| R2.5 | guard block count recorded | **PASS** — 0 |
| R2.6 | memory files 0 before and after | **PASS** |

## Result

**The package installed 2,000 files in 6 minutes 15 seconds from a throwaway copy, and
the answer's citations held.**

All 18 self-test checks passed. The 31 retrieval probes returned output and were captured
for the record. The headless Sonnet question took 93.7 seconds, produced a 1,442-character
answer with a Sources block, and **the one page it cited is a page the transcript shows as
`OPENED`** — two pages were opened, one was cited, none was cited without opening. No path
was named in prose without a page. The citation guard **did not fire**, which is the right
outcome when nothing is cited unopened.

`uninstall` removed `CLAUDE.md` and `.claude`, and the project-key memory count was zero
both before and after, so the run left nothing behind and learned nothing between steps.

One incidental observation, recorded because it was not expected: the install creates an
empty `_private/` directory inside the room, because `labpaths.py` derives that path from
the package root. It is harmless and stays inside the room, but a package that creates a
directory named `_private` on a user's machine is untidy, and it is listed in the handoff.

## Adopted?

**Yes**, as evidence that the package installs and answers on a second folder. It is
**not** adopted as evidence of generalisation — see below.

## Run record

`corpus-lab/experiments/p10_portable_r2/run_record.json`, id `p10_gate_r2`,
spec `corpus-lab/state/phase10_gate_r_spec.md` at commit `c4dce54`.

## What this does not show

- **`corpus_2000` is another generated corpus from the same fixture ecosystem; this is not
  real-world validation; genuine cross-folder generalisation remains untested.** Every rung
  under `harness/` comes from one generator, with one naming scheme, one family structure
  and one table layout. A second rung from that generator tests that the code does not
  hard-code the first rung's size — nothing more.
- **One question, one model, one run.** It shows the citation discipline held once. It is
  not a measurement of accuracy, and no accuracy number was computed: there is no key for
  this folder and none was invented.
- **The guard not firing is not evidence the guard works.** It is evidence it was not
  needed. The guard's behaviour is covered by its own 24-check self-test.
- **The probe outputs were captured, not compared.** With no second room there is nothing
  to compare them to; they exist so a later run can be compared against them.
- **Nothing here tests a folder with different rules** — different filenames, different
  document families, a different language, real scanned publications. That is the next
  experiment, designed and pre-registered on its own, and it has not been run.
