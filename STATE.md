# STATE — read this first

*Last updated 2026-10-09. Update this at the end of every session. One page, no history.*

## Where everything is

Everything moved under `Desktop\Projects\Code\` when the Desktop was reorganised 2026-09-25.

| What | Path |
|---|---|
| This project | `C:\Users\Ali\Desktop\Projects\Code\retrieval-lab` |
| Test folder — **installed**, used for the acceptance run | `...\Code\portable-test` |
| Clean spare — **never installed**, the handover target | `...\Code\portable-test - Copy` |
| Documents (2,000 files) | `...\portable-test\research` |
| Built index (763 MB) | `...\portable-test\engine\artefacts\pages.db` |
| Corpora, generator, world | `retrieval-lab\harness\` |
| Answer keys | `retrieval-lab\_private\harness_keys\` |
| Gates, battery, scorer, 136 tests | `retrieval-lab\corpus-lab\` |
| Packages (9 builds) | `retrieval-lab\dist\` — current is `retrieval-portable-23ae9d3` |
| Ahmad's fork | `C:\Users\Ali\Downloads\ahmad-claude-rag-main\ahmad-claude-rag-main` (nested twice) |
| Engine's machine registry | `C:\Users\Ali\AppData\Local\retrieval-lab\roots.json` |

Branch `phase11-fresh-folder`, 17 commits ahead of `master`, **pushed** to
`nessed/cli-largeFolder-index`. `harness\` and `_private\` are gitignored, so they are **not**
backed up by that push — they exist only on this disk until copied to G Drive.

## What is done

- The package installs from one word. Recipient opens Claude Code in the folder, types
  `initialize`, and the folder's own documents carry the agent through it.
- F-01, F-02, F-17 fixed. 136 tests pass.
- Twelve acceptance questions written with a verified answer key, built by reading the PDFs
  rather than the answer keys — `ACCEPTANCE_QUESTIONS_2026-09-17.md` (five) and
  `ACCEPTANCE_QUESTIONS_HARD_2026-09-17.md` (seven).
- **The acceptance run happened** on 2026-09-17. Nine of twelve asked. Transcripts saved to
  `REPORT\08_what_next\RUN_2026-09-17\`; scoring in `SCORECARD_2026-10-09.md`.
  **Eight Gold, one Pass, no Fail on substance.**
- Ahmad's fork reviewed — `COWORKER_FORK_REVIEW_2026-10-09.md`. Verdict: keep it.

## What is open

| ID | Problem | Status |
|---|---|---|
| **F-23** | **Every cited page is one too low.** A bare `enumerate(pages)` in `index_build.py` stores a document's first page as page 0. Verified across 11 citations in 6 answers. No gate caught it because the v3 scorer compares a cited page against `OPENED` pages from the same index, so the offset cancels. | **Blocker.** Ahmad has the root fix — `labpaths.FIRST_PAGE_INDEX = 1`. Take his. Requires a re-index. |
| **F-24** | A **false absence**. H7 said Sindh has no own-source revenue before 2012-13 "anywhere in the folder"; every edition carries 2010-11 (23.9). Same for AJK (1.8). It read a table printing only its last eight columns and generalised. Cost Ali two years of panel. | Open. No quote check catches it — the quote was real. Planned fix is a template rule. |
| **F-25** | A portable install creates a folder called `_private` in the recipient's directory (the stop hook's log). Not a key leak, but it reads as one. | Open. One line at install time: set `RUNS_ROOT` into `engine\artefacts\`. |
| **F-03** | The interactive permission prompts are still unmeasured. The merge **adds a second Stop hook**, so this matters more now. | Open. |
| — | Ahmad reports that at the 6 workers `INITIALIZE.md` computes for an 8-core machine, large files hit a hardcoded 180s `pdftotext` timeout and are **dropped while `COVERAGE` prints `failed=0`**. | **Unverified here.** Outranks F-23 if it reproduces on 2,000 files. |

## What is next

1. **Reproduce the dropped-files claim** on `corpus_2000`. If real, every answer so far came
   from an incomplete index.
2. **Merge Ahmad's work** per `MERGE_PLAN_2026-10-09.md`. Snapshot the ranker *first* — that
   "before" expires the moment a file changes.
3. **Re-index**, then prove F-23 closed by pointing `verify` at the nine existing answers:
   all should fail on pages now and pass after.
4. **Ask the three unasked questions** — H5 first, because its answer depends on noticing the
   2022-23 Punjab edition stops six years early, the same trap F-24 fell into.
5. Hand-test, then send to the professor.

Do **not** gate the merge on a before/after live battery. Identical reruns swing 2–5 of 17,
which is why the Sonnet-vs-Opus gap of 1 was retired as noise. Use the identical-ranker diff
and `verify` instead — both deterministic.

## What has never been tested

Say these out loud in the handover note:

- **A second machine.** The F-01 tool-path fix has only ever run here.
- **A cold cache.** Every install measured ran warm, 0 bytes downloaded. The professor's
  first run downloads a 130MB embedding model. Testable via `FASTEMBED_CACHE_PATH`.
- **The permission prompts** (F-03).
- **This project's own gate on a corpus from another generator.** Partly closed by accident:
  Ahmad's 26 Punjab PDFs are the first non-generated corpus this project has touched, and
  three findings came out of it. Our gate has still never run on one.
- **Whether a genuinely fresh agent follows `INITIALIZE.md`** rather than improvising.

## Housekeeping still outstanding

- `harness\` + `_private\` to G Drive. ~580 MB for the irreplaceable core (`_private` 291 MB,
  `generator` 289 MB, `world` 1.3 MB, `seed_docs` 124 KB), plus `corpus_2000` 396 MB.
- `roots.json` has 6 entries; 4 point at folders that no longer exist.
- `REPORT\08_what_next\` holds 9 dated handoffs and 4 architecture docs. Move them to
  `archive\` — this file replaces them as the entry point.
- Delete the stray `portable-test\_private\`. The `- Copy` folder has never had one.
