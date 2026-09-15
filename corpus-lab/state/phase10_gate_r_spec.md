# Gates R1, R2, R3 — pre-registered, 2026-09-16

**Written and committed before any clean-room command was run.** Plan E §3.3.
`docs_check.py` check C fails any run record whose spec commit is dated after the run
started, which is what makes this file's commit time load-bearing.

## What these gates are for

Plan E §1.4: the "portable" installer ran scripts out of the development repo, wrote its
artefacts into the development repo, and built the shelf with the experimental v2
builder while production ran v1. It had never once been run from a copy. So three
separate claims need proving, and each gets its own gate:

- **R1** — two clean installs of the same corpus produce the same build.
- **R2** — the package works on a corpus it has not been tuned against.
- **R3** — the package does not secretly read the development repo.

## Definition: "matching artefact hashes"

Plan E decision 2. Raw SQLite files **never** match between two builds: they carry
creation timestamps, their row order depends on the filesystem walk, and float
embeddings differ in their last bits. Comparing raw hashes would fail every time and
prove nothing about the build.

So a build is identified by its **canonical export**: every logical table as sorted
rows with `built_at`, `indexed_at` and every timing field removed, plus the vector
stores hashed after rounding to 3 decimal places. Raw file hashes are recorded for
completeness and are **expected to differ**.

## Gate R1 — two genuinely clean builds, same corpus, same logical result

Twice, A then B, each from scratch in its own `%TEMP%\p10_clean_<X>`: copy the package,
fresh venv from `requirements-portable.txt`, all `*_ROOT` / `LAB_PRIVATE` env vars unset
**and asserted unset**, a *copy* of `harness/corpus_500` (the rung itself is never
touched), 0 memory files under the copy's project key before and after, then `doctor`,
`install --artefacts .\artefacts --seed-env --workers 8`, `c_selftest.py --db --shelf`,
the fixed probe list below, `uninstall`.

A and B use distinct paths for artefacts, venv and corpus copy; nothing from A is
readable by B. A's venv and artefacts are deleted only after both comparisons are
written.

**PASS iff every line holds:**

| check | rule |
|---|---|
| both installs exit 0, each ≤ 20 min | fail otherwise |
| `canonical_export.json` sha256 A == B | **any** difference fails; the first differing table and row is named |
| `build_manifest.json` counts (files, statuses, families, editions, duplicates, captions, card rows) A == B | fail otherwise |
| vectors A vs B | sha256 equal → "deterministic"; else per-row cosine mean ≥ 0.9999 **and** min ≥ 0.999 → "deterministic up to float noise", **reported**; else fail |
| retrieval outputs A == B | rank lists identical → pass; a swap only between rows whose A-scores differ by < 1e-6 **and** vectors were "float noise" → reported as tie noise, pass; anything else fails |
| `c_selftest.py` same check set passes in A and B | list checks that do not apply to 500 files; fail if the two lists differ |
| memory files 0 before and after in both | fail otherwise |

Else `GATE_R1_STOP` with the first failing line. Unexplained differences are never
smoothed over; every explained one goes in the README's *Result*.

### R1a — the fixed retrieval probe list

Fixed here, before any build. Generic English wording; no publication name, no year
string, no title from the corpus (contamination rule).

**20 `find` queries:**

1. development spending by year
2. tax revenue table
3. which years does the folder cover
4. production of a major crop over time
5. total expenditure summary
6. provincial budget allocation
7. public debt outstanding
8. import and export values
9. inflation rate by month
10. population estimates by province
11. education sector spending
12. health sector allocation
13. energy generation capacity
14. agricultural output by crop
15. employment and labour force
16. foreign exchange reserves
17. subsidy payments
18. development programme releases
19. revenue collection target versus actual
20. summary table of key indicators

**5 `inside` calls** on the first primary document of the five largest families, chosen
by the rule `ORDER BY n_members DESC, family_id`, query `summary table`.

**3 `series` calls**: `development expenditure`, `tax revenue`, `total expenditure`.

**1 `coverage` call.** **`have`** on the two largest families by the same rule.

Outputs captured as JSON: ranked lists of `(rel, page_index, score)`.

## Gate R2 — the second portability rung, corpus_2000

Clean room C, same package, a copy of `harness/corpus_2000`, `--workers 8 --seed-env`,
then `install`, `c_selftest.py`, the same probe list (**captured, not compared** — there
is no B), **one** headless Sonnet question via `setup_folder.py ask`, teardown, memory
assert.

**PASS iff:** install exits 0; the self-test passes its applicable checks; the answer
ends with a Sources block **every line of which names a page the transcript shows as
`OPENED`**; the guard log shows its block count; wall ≤ 60 min. Nothing is scored
against a key.

**Recorded verbatim in the README's *What this does not show*:** *corpus_2000 is another
generated corpus from the same fixture ecosystem; this is not real-world validation;
genuine cross-folder generalisation remains untested.*

## Gate R3 — no dependency on the dev repo, proven by trace

In clean room A's layout, on a fresh corpus copy, run `install` again with a
`sitecustomize.py` in the clean venv hooking `builtins.open`, `io.open`,
`sqlite3.connect`, `os.scandir` and `os.listdir`, appending every absolute path to
`reads.log` (child processes inherit it via the venv).

**PASS iff** `reads.log` contains no path under the development repo, none under
`~/.claude/projects/<dev repo key>`, and the package grep for `C:\Users` and `Desktop`
is empty. Else `GATE_R3_STOP` naming the first offending path.

## What these gates do not establish

- Nothing about retrieval quality. R1 asks whether two builds agree, not whether either
  is any good.
- R2 is **not** real-world validation. Every rung under `harness/` comes from one
  generator, and a corpus from the same generator cannot test generalisation to a folder
  the rules have never seen.
- R3 proves no dev-repo read **on the traced run**, on this OS, for this corpus. It is a
  trace, not a proof about all inputs.
- None of them says anything about whether the install is fast enough, cheap enough, or
  usable by someone who has not read `INSTALL.md`.
