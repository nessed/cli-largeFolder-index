# Review — Ahmad's fork, 2026-10-09

Folder: `C:\Users\Ali\Downloads\ahmad-claude-rag-main\ahmad-claude-rag-main`
(note the doubled directory — the zip has a nested root).

Branch he calls `local/reliability`. Dated 2026-10-01. 38 files; it is the **portable
package only**, not the full project — no `corpus-lab`, no `harness`, no tests directory.

## Base

Forked from **exactly `23ae9d3`** — `package_commit
23ae9d34509c4d9f228ec8ea54bc962881116b49`, `package_dirty: false`, the same package staged
for Ali's acceptance run. A clean base, so this is a strict superset of what we shipped and
merges without archaeology.

He ran it against a different corpus: 26 Punjab budget PDFs for FY2026-27, ~34,400 pages.
Not our synthetic folder. **That makes this the first evidence this project has from a
corpus outside its own generator** — the gap named as the next experiment in every handoff
since 2026-09-13.

## Verdict

**Keep it.** The engineering is sound, it is additive rather than destructive, and it
independently found and fixed the blocker filed this morning as F-23. Two things need doing
before it can be merged, and one measurement claim has to be retired.

---

## He found F-23 independently, and fixed it properly

This is the headline. `SCORECARD_2026-10-09.md` filed F-23 — every cited page one too low —
after checking eleven citations by hand. Ahmad diagnosed the same bug from the other end and
fixed it at the root.

Ours, `bin/index_build.py`:

```python
return "indexed", "", [(i, t) for i, t in enumerate(pages) if t.strip()]
```

`enumerate` with no `start`, so the first page of every document is stored as page 0. That
single line is F-23.

His, in `bin/labpaths.py`:

```python
FIRST_PAGE_INDEX = 1

def pdf_page_number(page_index):
    return page_index - FIRST_PAGE_INDEX + 1
```

with `index_build.py` calling `_page_index(position) = position + L.FIRST_PAGE_INDEX`. The
numbering now lives in one constant, both shelf builders read it rather than hardcoding, and
his own comment states the diagnosis exactly:

> *"0 is how this package's first index was built, which is why every citation used to need a
> mental +1 (the reader-side fix that printed "(PDF page N+1)" alongside was a patch for
> that, not a fix)."*

Two people arriving at the same defect from opposite directions is about as confirmed as a
finding gets. **Take his fix, not a patch of our own.** He also correctly notes that changing
the constant is a re-index, because the old numbers are baked into `pages`, the shelf's
`captions`, and every written note.

---

## What else he built

Verified as present in code, not just claimed in his `RUN.md`:

**Citation integrity — the most valuable group**

| change | token |
|---|---|
| `note` refuses a quote that is not on the page it cites | `NOTE_REFUSED_QUOTE_NOT_ON_PAGE` |
| `verify --slug` re-derives every note from the index; exit 1 if any fails | — |
| `verify --answer <file>` checks the figures in the prose against the notes | `ANSWER_UNSUPPORTED_FIGURES` |
| a note records the page SHA it was written against | `PAGE_CHANGED_SINCE_NOTE` |
| a second Stop hook runs verify at answer time | `c_verify_guard.py` |

This closes the hole that made F-23 invisible to seven nights of gates. Our v3 scorer
compares a cited page against `OPENED` pages from the same internal index, so a uniform
offset cancels and the gate passes. His `verify` re-derives the quote from the page text,
which would have caught it.

**Silent data loss — a bug we never found**

He reports that on his 8-core machine `INITIALIZE.md` computes 6 workers, and at 6 workers
the four largest volumes hit a hardcoded 180-second `pdftotext` timeout and are **dropped
while `COVERAGE` still prints `failed=0`**. At 3 workers the same corpus builds in 107s.

If that reproduces, it is worse than F-23: the index silently omits whole documents and the
coverage line says everything is fine. His fixes:

- `COVERAGE` counts every `failed_*` status — `failed_by={failed_timeout:4}`
- `COVERAGE` reports `pages_with_no_readable_text=N`
- `index_build` scales the timeout with file size and retries instead of dropping
- `index_build` retries previously-failed files without needing `--purge`
- `coverage --json` names every unreadable file

He also found that an install only re-runs stages whose output is missing, so a failed file
is never retried unless you delete that stage's output. That is a real design flaw.

**The portability claim**

> *"The folder claims to be portable; it is not, quite."*

`uninstall`/`install` key ownership and registry state on the **absolute** corpus path, so
after a move the tool reports `FOREIGN_FILES_PRESENT` and refuses. **This is exactly what
happened to Ali's own folder** when the Desktop was reorganised on 25 September and
`portable-test` moved into `Projects\Code\`. His fixes: `FOREIGN_INDEX_PRESENT` with exit 3,
`install --adopt` to repoint deliberately, `ADOPTED_MOVED_INSTALL` so teardown of a moved
install still works, and excluding the pack's own `CLAUDE.md`/`.claude` from the corpus
(`excluded_dependency=2`).

**Other additions**

- `table <rel> --page N` reads the real grid with `pdfplumber` cells rather than the text
  layer. Worth having — our whole key was built from prose because tables do not survive
  `pdftotext -layout`.
- OCR for text-less files via `tesseract` + `pdftoppm`, **off unless `PCR_OCR=1`**. He OCR'd
  two scanned documents in his corpus, including one with a CID-obfuscated text layer.
- Shelf update atomicity: `UPDATE_IN_PROGRESS` makes readers exit 3 mid-update, and
  `SHELF_REBUILD_PREFERRED` exit 6 refuses an update that is really a rebuild.
- Ten engine scripts that exist in our repo but were never included in the portable package
  (`c_dupe_audit`, `c_index_selftest`, `c_retrieval_eval`, `c_setup_selftest`,
  `c_shelf_update`, `make_fixture_index`, and their selftests).

---

## What is safe

- **The ranker is untouched.** Diffing `c_shelf.py` for weights, scores, BM25 terms and
  ranking produced no hits beyond a reflowed comment. No function was removed from any file —
  the diff is purely additive (17 new functions in `c_shelf.py`, 0 deletions).
- **`scoring.py` and `c_stop_guard.py` are byte-identical.** The frozen v3 scorer and the
  stop guard were not edited. His verify hook is a *second* hook, not a replacement.
- He deliberately kept the `COVERAGE` token and field order stable because `c_selftest`
  greps for them.

## What is not safe, and must be dealt with

**1. His package fails its own integrity check.** `PACKAGE_MANIFEST.json` still carries
`23ae9d3`'s hashes:

```
manifest lists 22 files; package contains 33
  verify OK : 10
  MISMATCH  : 12   (c_shelf, c_stack, index_build, labpaths, setup_folder,
                    corpus_search, c_selftest, c_shelf_build, c_shelf_build_v2,
                    CLAUDE_ROOT.md, INITIALIZE.md, INSTALL.md)
```

Eleven new files are not listed at all. This is a working copy, not a releasable package —
the fix is to rebuild the manifest from his branch with `make_portable.py`. Until then the
forbidden-string grep and sha verification in gate R3 cannot run against it.

**2. He changed `CLAUDE_MD_TEMPLATE`** in `c_stack.py` — the explicitly frozen thing under
test. The changes are *necessary* (the model cannot use `table` or `verify` if it is not told
they exist, and the page-numbering line now substitutes `{FIRST}`), but they are still
changes to the prompt.

**Consequence: our measured answer-quality numbers through F63 are no longer comparable.**
The ranker is identical, so retrieval ranking should reproduce exactly; what moves is model
behaviour, because the model is now instructed to verify before answering. That is the point
of his work, and it means the gate has to be re-run to re-baseline rather than compared
against the old figures. Do not quote a before/after improvement off the existing numbers.

**3. Nothing here has been run.** I read the diffs; I did not build his venv or execute his
selftests. The 180s-timeout claim, the OCR path and `--adopt` are all unverified by me and
rest on his `RUN.md`. His corpus is also 26 documents against our 2,000, so his timings and
worker advice do not transfer.

---

## Recommended order

1. **Take `FIRST_PAGE_INDEX` now.** It closes F-23 at the root and it is one constant plus
   two call sites. Re-index afterwards — the old page numbers are stored.
2. **Take the citation-integrity group** (`note` quote check, `verify --slug`,
   `verify --answer`, page SHA). This is the part that would have caught F-23 and it defends
   the project's actual yardstick. It is also what makes F-24 harder to repeat.
3. **Reproduce the worker/timeout claim on our 2,000-file corpus** before taking the
   `index_build` changes. If documents really are dropped with `failed=0`, that outranks
   everything else on this list.
4. **Take the moved-folder fixes** (`FOREIGN_INDEX_PRESENT`, `--adopt`). Ali has already been
   bitten by this once.
5. **Rebuild the manifest and re-run gate R3** before any of it is packaged for handover.
6. **Re-baseline.** Run the gate on our corpus with his template, and treat the result as a
   new series rather than a comparison.
7. `table` and OCR last — useful, no urgency, and OCR is opt-in anyway.

## Also worth telling him

- F-24 from the scorecard, because his `verify` does not catch it: the engine asserted that
  Sindh has no own-source revenue before 2012-13 "anywhere in the folder" when every edition
  carries 2010-11 in prose. It had read a table that prints only its last eight columns. A
  quote check cannot catch a fabricated *absence*.
- His corpus is 26 documents of FY2026-27 plus 2025-26 revised estimates, so his own note is
  right that "how has X changed over ten years" is unanswerable there. Our 2,000-file folder
  is the one that exercises the edition/vintage machinery.
