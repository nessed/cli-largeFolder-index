# BUILD C — shelf first: document cards, then search inside the document (stack `s7_shelf`)

You are an executing agent with shell and file access, running unattended in
`C:\Users\Ali\Desktop\retrieval-lab`. Ali is asleep. Follow this file in order. Do not
improvise past a failed gate, do not narrow a task to make a gate pass, and do not
substitute your own judgement where a number is given. When something is impossible as
written, stop that stage, log why, and continue with the next stage that does not depend
on it.

Read `plans_fable/C_SHELF_FIRST_PLAN.md` once for context. Skim `corpus-lab/RESUME.md` §7
for traps that have already cost hours here.

---

## 0. Fixed rules — restate them to yourself before Stage 1

1. **Never regenerate any harness corpus.** `harness/corpus_*` are irreplaceable. The
   only files you may create under `harness/corpus_15000` are `CLAUDE.md` and
   `.claude/settings.json`, via `c_stack.py`, removed at the end of Stage 5 whatever
   happened. Always pass `--corpus` to any teardown; never run `stack.py teardown` bare.
2. **`_private/` must never be reachable from a measured session.** You read
   `_private/harness_keys/answer_key.json` only inside `c_offline_gate.py` (Stage 3) and
   `c_score_extra.py` (Stage 5). Never print an evidence path, row label or expected value
   into `progress.jsonl`, `FINDINGS_LIVE.md`, `CLAUDE.md`, a prompt, or any file under
   `corpus-lab/bin/`. Counts only.
3. **No hand-written synonym tables, alias lists, family name lists or example strings
   derived from the corpus or the key.** Families are derived by rule from the documents'
   own front pages. The generic version-marker list in Stage 1 is the only word list
   allowed and it is fixed here. If you catch yourself typing a title or row label you saw
   in the key into code or prompt, delete it and log `contamination_averted=1`.
4. **Do not modify existing instruments.** `ask.py`, `run_harness.py`, `run_canaries.py`,
   `scoring.py`, `corpus_search.py`, `index_build.py`, `stack.py`, `labpaths.py`,
   `checksums.py` are read-only for you. New files only, named `c_*.py`. If a change to an
   existing instrument looks necessary, log `blocked_needs_instrument_change` and stop
   that stage.
5. **Do not touch another agent's work.** `corpus-lab/evidence_v1/`,
   `corpus-lab/bin/evidence.py`, `corpus-lab/tests/`, `_private/evidence_v1/`,
   `corpus-lab/state/evidence_v1/`, root `SOLUTION.md`, `BUILD_PROMPT.md`, `ACCEPTANCE.md`,
   and approach B's `b_*.py` / `02_stacks/s6_hybrid/` are not yours. You **may read**
   `state/b_queries.json` if it exists (Stage 3).
6. **Open the index read-only**: `sqlite3.connect(f"file:{db}?mode=ro", uri=True)`.
7. **pip installs go into `.venv` only.** Nothing new should be needed; fastembed, numpy
   and onnxruntime are installed.
8. **Invoke `claude.exe`, never `claude.cmd`** — `labpaths.CLAUDE`.
9. **Every step appends one line to `corpus-lab/state/progress.jsonl`** via
   `python corpus-lab/bin/plog.py C <step> <status> <note> k=v …`. Append only. Status is
   one of `started`, `PASS`, `FAIL`, `skipped`, `stopped`. An early stop says why in one
   sentence.
10. **Free before paid.** Stages 0–4 spend nothing. Stage 5 only runs if Gate 3 passed.
11. **`python -u`, foreground, for anything long.** No `nohup … &`.
12. **No Windows paths inside bash heredocs feeding `python -c`.** Write script files.

Constants:

```
ROOT   = C:\Users\Ali\Desktop\retrieval-lab
PY     = C:\Users\Ali\Desktop\retrieval-lab\.venv\Scripts\python.exe
LAB    = C:\Users\Ali\Desktop\retrieval-lab\corpus-lab
BIN    = LAB\bin
DB     = LAB\02_stacks\s2_fts5\harness_15000.db      (read-only)
OUT    = LAB\02_stacks\s7_shelf\                      (create; append `02_stacks/s7_shelf/` to corpus-lab/.gitignore in Stage 1)
RUNG   = C:\Users\Ali\Desktop\retrieval-lab\harness\corpus_15000
STATE  = LAB\state
PLOG   = PY BIN\plog.py C
REG    = %LOCALAPPDATA%\retrieval-lab\roots.json      (shared registry with approach B; key = lowercased resolved root, forward slashes; C adds its own field "shelf")
NOTES  = %LOCALAPPDATA%\retrieval-lab\notes\<corpus-key>\  (corpus-key = first 12 hex of sha256 of the registry key)
STACK  = s7_shelf
PHASE  = PC_s7_shelf
MODEL  = claude-sonnet-5
```

---

## Stage 0 — preflight (free, ≤ 10 min)

Same checks as approach B's Stage 0 (Python 3.11, `fastembed`/`numpy` import, `DB`
present and ≥ 6.9 GB, `corpus_search.py --coverage` reporting `indexed_ok=13634`,
`addressable_pages=1206260`, `accounting_identity_holds=true`, `claude.exe --version`
prints, free disk ≥ 5 GB, and — informational — whether `RUNG\CLAUDE.md` / `RUNG\.claude\`
exist). Write `STATE\c_preflight.json`. `PLOG 0.2 PASS|FAIL`. On FAIL stop the build.

---

## Stage 1 — build the shelf (free, ≤ 90 min CPU)

Inputs: `DB`. Outputs: `OUT\shelf.db`, `OUT\cards.f16.npy`, `OUT\cards_ids.jsonl`,
`OUT\build_manifest.json`, `STATE\c_shelf_build.json`.

1.1 Write `BIN\c_shelf_build.py`. Rules, fixed:

**Per indexed file** (`files.status='indexed'`, joined to its pages):

- `p0`, `p1`, `p2` = bodies of page_index 0, 1, 2 (empty string if absent).
- `title`: the first line of `p0` that has ≥ 3 alphabetic words after stripping; cut at
  160 characters. If no such line in `p0`, use the filename stem with `_` and `-` turned
  into spaces. Record `title_source` = `page0` or `filename`.
- `FY` regex = `\b(20[0-3]\d)-(\d\d)\b`. `fy_all` = the ordered unique FY tokens found in
  `title`, filename, `p0`, `p1`, `p2` (in that order). `fy_primary` = the first FY in
  `title`, else the first in the filename, else the first in `p0`, else `null`.
- `family`: `title` lowercased, every FY token replaced by `{fy}`, then these generic
  version markers removed as whole tokens (this list is final; do not extend it):
  `(1)…(9)`, `copy`, `draft`, `final`, `new`, `old`, `v1…v9`, `rev`, `revised`,
  `updated`, `use this one`, `backup`; then punctuation collapsed to single spaces and
  trimmed. If the result is shorter than 4 characters, `family` = filename stem cleaned
  the same way.
- `catalog`: (a) the text of any page among the first 15 whose body contains the word
  `Contents` or the phrase `List of Tables` (case-insensitive), capped at 6,000 chars
  total; plus (b) every line in the whole document matching
  `^\s*Table\s+[A-Za-z]?\.?\d+(\.\d+)*\s*[:.\-–]\s*(.{3,160})$`, deduplicated, capped at
  400 lines, each stored with its page_index in a separate table `captions(rel, page_index,
  caption)`. `catalog` text = (a) + the caption texts joined by newlines.
- `head`: first 1,500 characters of `p0 + "\n" + p1`.
- `n_pages`, `sha256`, `size`, `ext` from `files`.

**Clustering.** `edition_key = (family, fy_primary)`. Within an edition key, members with
identical `sha256` collapse to one row (keep the shortest path, list the others in
`dupes`). Among the remaining members, `is_primary = 1` for the one with the largest
`n_pages` (ties: largest `size`, then shortest path). Members with `fy_primary = null`
form editions keyed `(family, null)` and are all primaries of their own singletons unless
their `sha256` matches.

**Tables in `shelf.db`:**

```
docs(rel PRIMARY KEY, title, title_source, family, fy_primary, fy_all, n_pages, size, sha256, ext, is_primary, edition_key, n_dupes, dupes)
captions(rel, page_index, caption)
families(family PRIMARY KEY, n_editions, n_members, fy_list)         -- fy_list = sorted distinct fy_primary of primaries
cards  FTS5(rel UNINDEXED, title, family, catalog, head)             -- one row per PRIMARY doc AND per non-primary doc (copies are searchable too, flagged by docs.is_primary)
meta(k, v)                                                           -- built_at, db_sha_or_size, counts
```

**Vectors:** `cards.f16.npy` over primaries and copies alike, text =
`f"{title} | {family} | {catalog[:1200]}"`, `fastembed.TextEmbedding("BAAI/bge-small-en-v1.5")`,
batch 128, L2-normalised float16 memmap, ids in `cards_ids.jsonl` (`{"i","rel"}`).
Expected 13,634 rows. Expected wall 20–40 minutes (measured today: 7 strings/s at 2,000
chars, 35/s at 300 chars).

**Report** to `STATE\c_shelf_build.json`: `n_docs`, `n_title_from_page0`,
`n_with_fy`, `n_families`, `n_families_with_2plus_editions`, `n_captions`, `n_dupes`,
build seconds per phase, embed rate.

1.2 Run `PY -u BIN\c_shelf_build.py --db DB --out OUT`. Budget 90 minutes; the card
extraction should take under 15 minutes, the embedding the rest.

1.3 Gate 1: `n_docs = 13634`; `n_title_from_page0 ≥ 8000`; `n_with_fy ≥ 8000`;
`n_families_with_2plus_editions ≥ 30`; `n_captions ≥ 20000`; `cards.f16.npy` has 13,634
rows. A sanity probe, printed and recorded (counts only): the family with the most
editions must have ≥ 10 editions and its primaries must average ≥ 200 pages. If
`n_families_with_2plus_editions < 30`, the family rule is mis-firing on real titles:
print 30 random `(title, family)` pairs, fix the rule **once** within the constraints of
1.1 (you may adjust how the title line is chosen; you may not add words to the marker
list), rebuild, and re-gate. `PLOG 1.3 PASS|FAIL` with the numbers. FAIL stops the build.

---

## Stage 2 — the front door `c_shelf.py` (free, ≤ 2 h)

Inputs: `DB`, `OUT`. Outputs: `BIN\c_shelf.py`, `REG` entry, `STATE\c_shelf_selftest.json`.

2.1 Write `BIN\c_shelf.py`. Every subcommand accepts `--db PATH --shelf DIR`; otherwise
the corpus root is resolved by walking up from the cwd to a `REG` key; exit 2 with
`NO_REGISTERED_ROOT` if none. Command grammar, fixed:

```
c_shelf.py find "<question>" [--q "<more>" …] [--k 12] [--slug NAME]
c_shelf.py have "<publication words>" [--fy 2012-13]
c_shelf.py inside "<rel>" "<terms>" [--k 8]
c_shelf.py tables "<rel>" [--grep "<word>"]
c_shelf.py series "<row words>" --family "<publication words>" [--from 2010-11] [--to 2030-31] [--slug NAME]
c_shelf.py copies "<rel>"
c_shelf.py exact "<literal phrase>" [--k 50]
c_shelf.py open "<rel>" <page_index> [--slug NAME]
c_shelf.py note --slug NAME "text"
c_shelf.py notes --slug NAME
c_shelf.py coverage
c_shelf.py register --root DIR --db PATH --shelf DIR
```

**`find`.** For each query string (the question plus any `--q`): FTS5 over `cards` with
`bm25(cards, 3.0, 3.0, 2.0, 1.0)` using the OR of content words (import
`corpus_search.content_words`), LIMIT 200; and cosine of the bge-small query vector
against `cards.f16.npy`, top 200. Reciprocal-rank fusion (k = 60) over all lists → doc
scores. Fold docs into families (a family's score = its best doc's fused score). Print
the top `--k` families in this fixed format:

```
#1  family: pakistan economic survey {fy}
    editions: 2011-12*(383p) 2012-13*(408p) … 2025-26*(385p)   [15 editions, 26 copies not shown]
    why: "Agriculture: Cotton Production" | "Table 2.4: Cotton Production"
    open with: inside "<primary rel of the best-scoring edition>" "<terms>"   or   series "<row words>" --family "<family words>"
#2  …
RECEIPT queries=1 lex=[n] vec=[200] families=12 docs_considered=…
COVERAGE indexed=13634 image_only_no_text=1211 failed=32 unsupported=120 pages=1206260
```

`*` marks a primary. `why` = the two catalog lines from the best card that share the
most content words with the query (or the title if none). Singleton families (notes,
CSVs, papers) print their one member's path as the edition. Copies are never listed in
`find`; their count is.

**`have`.** BM25 over `title` and `family` columns only for the words given; print up to
8 families with their `fy_list`. With `--fy X`: for the best family print exactly one of
`EDITION_PRESENT <fy> <primary rel> (<n>p)` or `NO_EDITION_FOR <fy> in "<family>";
nearest: <fy_before>, <fy_after>; editions held: <fy_list>`. Then print
`UNREADABLE_FILES_WITH_MATCHING_NAME=<n>` = count of `files` rows with status
`image_only_no_text` or `failed_*` whose filename contains all the given words
(case-insensitive). If no family matches at all: `NO_FAMILY_MATCHES "<words>"` and the
same unreadable count.

**`inside`.** Load that document's pages from `DB` into an in-memory FTS5 table (`CREATE
VIRTUAL TABLE p USING fts5(page_index UNINDEXED, body)`), then: quoted phrase if ≤ 4
content words, else AND of content words; if empty, OR of content words; order by bm25;
top `--k`. Each line: `p<page_index>  <score>  | <the first line on the page containing
the most query words, 200 chars>`. Print `INSIDE <rel> (<n_pages>p) tier=phrase|all|any`
first. This should run in under 1 s for a 700-page document.

**`tables`.** Print `captions` rows for the document, optionally filtered by `--grep`
substring (case-insensitive): `p<page_index>  <caption>`.

**`series`.** Resolve `--family` with the same matcher as `have`; take its primaries with
`fy_primary` in `[--from, --to]`, sorted by fiscal year. For each, run `inside` with the
row words and `--k 1`. Print one line per edition:
`<fy>  p<page_index>  <rel>  | <matching line 200 chars>` or `<fy>  NO_MATCH  <rel>`.
Then `SERIES_RECEIPT editions=<n> matched=<m> family="<family>"`. With `--slug`, nothing
is recorded as opened — `series` shows lines, it does not open pages; the `CLAUDE.md`
says so.

**`copies`.** All `docs` rows sharing the edition key with `<rel>`, plus its `dupes`:
path, pages, `is_primary`, `same_hash_as_primary` yes/no.

**`exact`, `open`, `note`, `notes`, `coverage`, `register`.** Same behaviour and output
lines as approach B's `b_search.py` (`TOTAL_PAGES_MATCHING=`, `NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING`,
`OPENED <rel> p<n>`, 12,000-char cap, notes header lines). Implement them independently;
do not import `b_search.py`.

2.2 Register: `PY BIN\c_shelf.py register --root RUNG --db DB --shelf OUT`.

2.3 Self-test from cwd `RUNG` (read-only use; nothing installed). Record each in
`STATE\c_shelf_selftest.json`:

| test | pass condition |
|---|---|
| `coverage` | COVERAGE line with pages=1206260 |
| `find "budget"` | ≥ 3 families printed, a RECEIPT and COVERAGE line, wall ≤ 5 s after the first (warm) call |
| `have "economic survey"` | at least one family with ≥ 10 editions |
| `have "economic survey" --fy 2029-30` | prints `NO_EDITION_FOR 2029-30` with a nearest year |
| `have "economic survey" --fy <a year from that fy_list>` | prints `EDITION_PRESENT` |
| `have "zqxv nonexistent publication"` | `NO_FAMILY_MATCHES` |
| `inside "<the primary rel of the largest family's latest edition>" "contents"` | ≥ 1 page line, wall ≤ 2 s |
| `tables` on the same rel | ≥ 20 caption lines |
| `series "production" --family "economic survey"` | ≥ 10 edition lines, SERIES_RECEIPT printed |
| `copies` on the same rel | ≥ 1 line |
| `exact "zqxv-nonexistent-string-9931"` | TOTAL_PAGES_MATCHING=0 |
| `open` on a page from `inside` with `--slug selftest`, then `notes --slug selftest` | OPENED printed; notes show the opened header |
| bogus subcommand | exit 2 and usage |

Gate 2: all pass. `PLOG 2.3 PASS` with `find_wall_s`, `inside_wall_s`. After two failed
fix attempts, `PLOG 2.3 FAIL` and stop. Delete the `selftest` notes file.

---

## Stage 3 — the offline gate (free, ≤ 60 min)

Inputs: the frozen 20, the key, `c_shelf.py`. Outputs: `STATE\c_offline_gate.json`,
finding F40. Import `c_shelf.py`'s functions in-process; do not shell out per question.

3.1 For each of the **17 answerable** frozen questions build the evidence set (paths from
`evidence_addresses`, normalised as `corpus_search` does) and the decoy set
(`must_not_cite`). Look each evidence path up in `docs` to get its `family` and
`edition_key`; if a path is not in `docs` (non-indexed), record `evidence_not_on_shelf=1`
for that question and exclude it from the doc-level rate (report the exclusion count).

3.2 Configurations:

| config | queries |
|---|---|
| C1 `verbatim` | the question text only |
| C2 `rewrites` | the question plus the five rewrites from `STATE\b_queries.json` if that file exists; otherwise generate them exactly as approach B's Stage 3.1 describes (same `claude.exe -p` call, same cwd rules, Haiku, `--max-turns 1`, tools disallowed) and save to `STATE\c_queries.json` |

Measures, per question and config:

- `doc_rank`: rank of the first family in `find` output (k = 50 for measurement) that
  contains an evidence path — hit if ≤ 10; also record whether the top-1 family is it.
- `decoy_first`: a family whose only matching member is a decoy ranks above every
  evidence family.
- `page_rank` (C1 only, PDF evidence with a `page_index`): rank of the evidence
  `page_index` in `inside <evidence rel> "<question>"` with k = 20 — hit if ≤ 5.
- `series_ok` (the 4 `trajectory` questions, C1): run `series "<question>" --family
  "<family of the evidence docs>"`; hit if the evidence `page_index` is returned for ≥ 2
  of the editions named in the key's evidence. (Using the family from the key here is
  allowed: this measures the walk, not the family choice, which `doc_rank` measures.)

3.3 Absence enumeration, on the key's 15 `absence` questions:

- Split them by rule: a question containing an FY token is **document-level** (expected
  10); otherwise **identifier-level** (expected 5). Record the split.
- Document-level: `have "<question content words minus FY tokens>" --fy <the FY in the
  question>` → hit if the output contains `NO_EDITION_FOR` **or** `NO_FAMILY_MATCHES`.
- Control: for each of the 17 answerable questions' evidence editions, `have "<family
  words of the evidence family>" --fy <evidence fy_primary>` → hit if `EDITION_PRESENT`.
- Identifier-level: `exact` on the longest token run containing a digit in the question
  (e.g. the SRO number as written) → record `TOTAL_PAGES_MATCHING`; hit if 0.

3.4 **Gate 3:**

| measure | PASS | PASS-WEAK | FAIL |
|---|---|---|---|
| C1 `doc_rank ≤ 10` | **≥ 12 of 17** | 8–11 | ≤ 7 |
| C1 `page_rank ≤ 5` (denominator = PDF evidence with page index) | ≥ 60 % | 40–59 % | < 40 % |
| `series_ok` | ≥ 3 of 4 | 2 of 4 | ≤ 1 |
| document-level absence `NO_EDITION` | ≥ 9 of 10 | 7–8 | ≤ 6 |
| control `EDITION_PRESENT` | ≥ 15 of 17 | 13–14 | ≤ 12 |

Overall: PASS if every row is PASS; PASS-WEAK if no row is FAIL; otherwise FAIL. FAIL →
skip Stage 5, still do Stage 4 (free) and Stage 6. PASS-WEAK → Stage 5 with the question
battery ceiling at $8. `PLOG 3.4 PASS|PASS-WEAK|FAIL` with every number, both configs.

3.5 Append **F40** to `FINDINGS_LIVE.md`: the table above with C1 and C2 side by side,
one sentence on whether rewrites changed the doc rank, the absence and control results,
and the condition line ("this corpus, families derived from page-0 titles, one build").
Counts only.

---

## Stage 4 — installer and `CLAUDE.md` for `s7_shelf` (free, ≤ 30 min)

4.1 Write `BIN\c_stack.py` with the same contract as approach B's `b_stack.py` (read that
section if it exists; the contract is restated here so you do not depend on it):
`setup` refuses with exit 3 `ANOTHER_STACK_PRESENT` if `CLAUDE.md` or `.claude\` exists;
writes its state file `LAB\99_scratch\c_stack_state__<corpus-key>.json` **before**
creating `.claude\settings.json` (`{"permissions": {"deny": BACKSTOP_DENY}}`, imported
from `stack.py`) and `CLAUDE.md`; `teardown` removes exactly what its state file lists,
refuses to delete files it did not create (`FOREIGN_FILES_PRESENT`, exit 3); `status`
prints what exists.

4.2 `CLAUDE.md` text, verbatim, `{PY}` and `{SHELF}` (= `BIN\c_shelf.py`) substituted
with absolute paths:

```
# How to answer questions from this research folder

Built-in Grep and Glob miss most of this tree (PDFs, spreadsheets, scanned files). Do
not rely on them. This folder has a shelf: one card per document saying what
publication it is, which year's edition, and which tables it lists. Work in two moves:
choose the documents from the shelf, then search inside them. Never search all pages at
once.

## 1. Find the publication on the shelf

    "{PY}" "{SHELF}" find "<the question as asked>"

Read the families it returns: each is a publication with the editions (fiscal years)
held. Decide which publication and which year(s) answer the question. If the question
names a publication or a year, confirm it is held:

    "{PY}" "{SHELF}" have "<publication words>" --fy <year like 2012-13>

If it prints NO_EDITION_FOR or NO_FAMILY_MATCHES, the answer is that we do not hold
that document; report the editions that are held and stop. Do not substitute another
year's edition without saying so.

## 2. Find the page inside the document

    "{PY}" "{SHELF}" inside "<path exactly as printed>" "<the subject in a few words>"
    "{PY}" "{SHELF}" tables "<path>" --grep "<word>"

For a question about how something changed over years, walk the editions in one go:

    "{PY}" "{SHELF}" series "<the table row in a few words>" --family "<publication words>" --from 2015-16

series shows you the matching line per edition. It does not open pages; you still must
open the page in each edition you use.

## 3. Open before you trust — a listed line is not evidence

    "{PY}" "{SHELF}" open "<path>" <page_index> --slug <slug>

Pick a short slug (letters and digits) for this question and reuse it in every open,
note and notes command. You may not cite, quote or take a number from a page you have
not opened. For a literal identifier (an SRO number, a demand number, a code) run
exact and, if TOTAL_PAGES_MATCHING=0, say that no readable page contains it:

    "{PY}" "{SHELF}" exact "<the literal string>"

## 4. Save what you find, then answer only from the notes

After opening a useful page:

    "{PY}" "{SHELF}" note --slug <slug> "<the exact line or table cell, verbatim> | <path> | p<page_index>"

Then print and answer from them:

    "{PY}" "{SHELF}" notes --slug <slug>

Every number in the answer carries its file path, page_index and the verbatim line. If
two editions or two copies disagree, show both with citations. If the notes are empty
after you have looked, say no supporting evidence was found, list the families and
pages you checked, and quote the COVERAGE line so the reader knows how many files could
not be read. Never supply a figure from memory or from a listing.

## 5. Copies

The folder holds partial copies, drafts and older versions of the same publications; the
shelf marks the complete one with * and hides the rest from find. Use the complete one
unless the question is about the copies, in which case run:

    "{PY}" "{SHELF}" copies "<path>"

Do not name copies you did not open.
```

4.3 Round-trip test on `LAB\99_scratch\c_roundtrip\` exactly as approach B's 4.3 (install,
assert, teardown, assert clean, stray-file refusal). Record `STATE\c_stack_roundtrip.json`.
Gate 4: all assertions hold. `PLOG 4.3 PASS`.

---

## Stage 5 — paid measurement (only if Gate 3 was PASS or PASS-WEAK)

Ceilings: canary battery ≤ $3 / 40 min; question battery ≤ $12 ($8 on PASS-WEAK) / 60
min; extra absence battery ≤ $4 / 30 min. Sum `cost_usd` after every 5 completed sessions.
At a ceiling: stop launching, let running sessions finish, record **partial n-of-m**.
These sessions draw on the Max subscription; the dollar figure is for comparability.

5.1 **Exclusivity.** `RUNG\CLAUDE.md` and `RUNG\.claude\` must be absent, and the last 20
lines of `progress.jsonl` must show no other run's `started` within 30 minutes without a
terminal status. Otherwise wait 5 minutes and re-check, up to 12 times, then
`PLOG 5.1 stopped "rung busy"` → Stage 6.

5.2 With env `CANARY_MANIFEST=ROOT\_private\canaries\canary_manifest_pass2.csv` for this
command only: `PY BIN\checksums.py snapshot --label s7_pre`. Record `mem_before` = number
of files under `%USERPROFILE%\.claude\projects\C--Users-Ali-Desktop-retrieval-lab-harness-corpus-15000\memory\`
(0 if absent). `PLOG 5.2 PASS`.

5.3 `PY BIN\c_stack.py setup --corpus RUNG`; `status` shows both files. `PLOG 5.3 PASS`.

5.4 **Canary battery**, env `CANARY_MANIFEST=<pass-2 manifest>` and `CORPUS_DB=DB` for this
command only:

```
PY -u BIN\run_canaries.py --phase PHASE --stack s7_shelf --corpus-kind rung --rung 15000 --corpus-label h15000 --timeout 420 --parallel 3
```

Gate: **≥ 15 of 17**. Below → `PLOG 5.4 FAIL`, teardown (5.8), skip 5.5–5.6, go to 5.9.

5.5 **Question battery:**

```
PY -u BIN\run_harness.py --phase PHASE --stack s7_shelf --rung 15000 --model MODEL --max-turns 25 --timeout 300 --parallel 2
```

No `--settings`. Apply the ceiling rule. `PLOG 5.5 PASS|stopped` with `n_done`,
`cost_usd`, `cost_n_of_m`, `timeouts`.

5.6 **Extra absence battery** (only if 5.5 completed all 20): the 12 absence questions
not in the frozen sample, via `ask.py` with the arguments `run_harness.one()` builds,
phase `PHASE_abs`. Ceiling $4 / 30 min. `PLOG 5.6 PASS|stopped` n-of-m.

5.7 `PY BIN\checksums.py verify --against s7_pre` (same env as 5.2). Mismatch →
`PLOG 5.7 FAIL "planted file changed"`; **verify, never restore.** Memory files: if more
than `mem_before`, move the new ones to `ROOT\_private\results\_memory_quarantine\PHASE\`.

5.8 **Teardown, unconditionally:** `PY BIN\c_stack.py teardown --corpus RUNG`; `status`
must show both absent. `PLOG 5.8 PASS`. On failure retry once, then put both paths in
capitals in the progress note and continue.

5.9 Scoring. `run_harness.py` wrote `harness__s7_shelf__rung15000.json` and its summary.
Write `BIN\c_score_extra.py` computing from the raw `.jsonl` streams in
`_private/results/03_runs/PHASE/` (and `PHASE_abs`), per question:

- `surfaced`: an evidence path appears in any `tool_result` text (from `find`, `inside`,
  `series` or `have` output);
- `opened`: an evidence path appears in an `open` command's arguments or in `files_opened`;
- `quoted`: the answer names the evidence path (tail-2 rule from `scoring.py`) and at least
  one `note` was issued;
- `series_used`: a `series` command was issued (trajectory questions);
- `forbidden`: as `run_harness.py`;
- absence (3 frozen + 12 extra): `declined` by `run_harness.DECLINE`; `figures_asserted` =
  numeric tokens in the answer that are not FY-shaped, not four-digit years, not inside
  an identifier, not page counts printed by the shelf (`(\d+p)`), and not the coverage
  counts (13634, 1211, 1206260, with or without commas); `absence_ok2 = declined and
  figures_asserted == 0`; plus `edition_list_quoted` = the answer contains `NO_EDITION_FOR`
  or lists ≥ 3 FY tokens (evidence that it answered from the shelf, not from a feeling).

Write `extra__s7_shelf__rung15000.json` and a summary: `n_surfaced/17`, `n_opened/17`,
`n_quoted/17`, `n_series_used/4`, `mean_recall`, `forbidden_total`, `absence_ok2 = a/15`
(or `/3`), `edition_list_quoted`, cost n-of-m, mean wall excluding suspended.
`PLOG 5.9 PASS` with those numbers.

**Gate 5 (reported, not enforced):** `n_opened ≥ 6 of 17` (published best 1) **and**
`absence_ok2 ≥ 10 of 15` **and** `forbidden_total ≤ 8`.

---

## Stage 6 — write-up and handoff (free, ≤ 30 min)

6.1 Append **F41** (canary), **F42** (question battery: harness summary beside S0/S1/S2,
the `extra` numbers, whether the two-move procedure was actually followed — `find` then
`inside`/`series` then `open` — counted from the tool-call sequences), **F43** (absence:
the 15-question result under `absence_ok2` and `edition_list_quoted`; the 3 frozen under
the old rule for comparability). Each with its condition line. Counts only.

6.2 `STATE\c_summary.json`: every gate's status and numbers, ceilings and spend,
`stopped_reason` if any.

6.3 A dated note at the top of `GRID.md` under the existing SUPERSEDED note:
"s7_shelf measured YYYY-MM-DD, see FINDINGS_LIVE F40–F43 and state/c_summary.json."
**Do not run `build_grid.py`.**

6.4 Three lines in `corpus-lab/RESUME.md` §0 pointing at `plans_fable/` and
`state/c_summary.json`.

6.5 `PLOG 6.5 PASS "build C complete"` with `total_cost_usd`, `stages_passed`,
`stages_stopped`. Print the summary. Do not commit; Ali commits.

---

## Named recoveries

| symptom | do this |
|---|---|
| `claude.exe -p` returns nothing / rc≠0 for rewrites | read the stderr file; if login/trust, run C1 only and mark C2 `not_run`; Stage 5 needs sessions — if login is the cause, `PLOG 5.1 stopped "claude needs interactive login"` |
| Family rule yields thousands of singleton families for real publications | see 1.3: print 30 samples, fix the title-line choice once, rebuild; do not add words to the marker list; report the before/after counts |
| `find` is slow (> 5 s warm) | the culprit is almost always re-loading the ONNX model per call; keep it in a module global; if still slow, reduce vector top-k to 100 |
| In-memory FTS5 build for a 700-page document exceeds 2 s | insert in one transaction with `executemany`; if still slow, cap body per page at 20,000 chars for the in-memory copy (record the cap) |
| A caption regex match explodes on prose lines starting with "Table" | the `\d` group is mandatory; if a document has > 400 captions they are capped and the count is recorded — that is fine |
| `TOTAL_PAGES_MATCHING` raises an FTS5 syntax error | double embedded quotes; never silently strip the string |
| Deny list blocks your own command | your cwd is `ROOT`, not the rung; fix the cwd |
| `SKIPPED-STALE` from a battery | you reused a phase label; use `PHASE_r2`; never `--force` |
| Ceiling hit | stop launching; n-of-m; summary says `partial`; `--only` later only with a fresh progress line |
| `checksums.py verify` fails | never restore; flag `corpus_mutated=true` in every summary |
| Another agent's files appear in the rung mid-battery | teardown yours; `PLOG … FAIL "concurrent install detected"`; the battery is void |
| `memory` dir gained files | quarantine; do not read them |
| A title or row label from the key ended up in code or prompt | delete it, `PLOG … PASS "contamination_averted" contamination_averted=1`, rerun that stage from scratch |
