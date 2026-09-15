# ENGINE.md — how the thing actually works, step by step

Written 2026-09-15 against commit `1e7c7b3` on `phase9-production-hardening`, by reading the
production code rather than the design documents. Every claim here is either a line of code or a
number read off disk today; where a design document and the code disagree, the code wins and
§16 records the disagreement.

**What this covers.** The path a question actually travels in the shipped system: approach C,
the `s7_shelf` stack. Every step names its input, what it does to it, its output, and the file
and function that does it.

**What this does not cover.** The four abandoned or unbuilt lanes — `evidence_v1`
(`corpus-lab/evidence_v1/`, a typed evidence compiler, stopped at its Stage 2 gate), approach B
(hybrid multi-query, never built), the S0–S2 stacks from nights 1–3, and the ~40 `c_*_gate.py`
measurement scripts. None of them run when a question is asked. They are instruments and dead
ends, not the engine.

**One sentence.** A folder is turned into a page index and a shelf of one card per document;
a question picks documents off the shelf, then pages inside those documents, and nothing may be
cited until its page has been opened.

---

## 1. The map

There are two phases. The first runs once per folder and takes about half an hour for 15,000
files. The second runs on every question and takes seconds.

```
BUILD TIME (once per folder — setup_folder.py install)

  folder of files
    │  1. index_build.py          text extraction, one row per page
    ▼
  pages.db  ───────────────────────────────────────────┐
    │  2. c_shelf_build.py        one card per document │
    ▼                                                   │
  shelf.db (docs, captions, families, cards FTS)        │
  cards.f16.npy (document vectors)                      │
    │  3. c_caption_index.py      captions as their own FTS index
    ▼                                                   │
  captions_fts.db                                       │
    │  4. c_caption_embed.py      captions as their own vectors
    ▼                                                   │
  captions.f16.npy                                      │
    │  5. c_stack.py setup        writes CLAUDE.md + settings.json into the folder,
    ▼                              registers the folder → (pages.db, shelf.db)
  a folder you can ask questions in  ◄──────────────────┘


QUESTION TIME (every question — the model driving c_shelf.py from CLAUDE.md)

  question in ordinary language
    │  6.  find      → 40 one-line publication cards          (shelf.db + 4 ranked channels)
    │  7.  have      → is this publication / year held at all? (the honest-no path)
    │  8.  inside    → pages within one chosen document        (pages.db + caption vectors)
    │  9.  series    → the same row across every edition       (inside, looped)
    │  10. open      → the page text, and a record that it was opened
    │  11. note      → refuses any line whose page was not opened
    │  12. notes     → the evidence the answer must be built from
    ▼
  answer with a Sources block
    │  13. c_stop_guard.py --v2   Stop hook: blocks once if the answer cites what it never opened
    ▼
  answer, or one more turn
```

---

# Part A — build time

## Step 1. Page index — `corpus-lab/bin/index_build.py`

**In:** a folder path.
**Out:** `pages.db` — a SQLite file with two tables that matter.

It walks the tree, skipping dependency directories by name (`.git`, `node_modules`,
`site-packages`, `.venv`, …, the list is `EXCLUDE_DIRS`), and for each remaining file decides
what it is from the extension:

| kind | how the text comes out | what a "page" is |
|---|---|---|
| PDF | `pdftotext -layout` from Git for Windows, 180 s timeout | a real page, split on form feed |
| `.docx/.xlsx/.pptx` | unzip, strip XML tags | the whole file is page 0 |
| text-ish (`.md .csv .py .do .tex` …) | read as UTF-8 | a 400-line chunk |
| images, archives, binaries | not read | — |

Two design choices here carry through everything downstream:

- **The unit is a page, not a file.** A 500-page yearbook is 500 addressable rows. A citation is
  therefore always `(path, page_index)`, never just a filename.
- **Every file gets a status and nothing is silently dropped.** The enum is closed —
  `indexed`, `image_only_no_text`, `failed_encrypted`, `failed_parser`, `zero_byte`,
  `unsupported_type`, `skipped_too_large` — and the totals must add up. That accounting is what
  the `COVERAGE` line at the bottom of every `find` prints.

Files land in `files(rel, sha256, size, mtime, status, error_class, n_pages)`; page text lands in
an FTS5 table `pages(rel UNINDEXED, page_index UNINDEXED, body)`.

**Measured on the 15,000-file fixture** (read from `shelf.db`'s coverage cache today):
15,010 files discovered, 13,634 indexed, 1,211 image-only PDFs, 32 outright failures, 120
unsupported, 13 zero-byte, **1,206,260 pages**, 6.49 GiB, built in 782 s.

> **Known limit, and it is structural.** `index_build.py` skips any path already in `files`. It
> does not notice a changed file, and does not remove a deleted one. Re-running it after editing
> the folder adds new files and nothing else. There is no incremental refresh in the shipped
> system.

## Step 2. The shelf — `corpus-lab/bin/c_shelf_build.py`

**In:** `pages.db`, read-only.
**Out:** `shelf.db` and `cards.f16.npy`.

This is the idea the whole approach rests on: *before searching a million pages, decide which
documents you are searching.* So every indexed document gets one card.

It makes a single ordered pass over the page table (`ORDER BY id`, which groups a file's pages
into one contiguous run) and, per document, harvests five things:

1. **A title.** The first line of page 0 with at least three alphabetic words — rejecting lines
   that start with `[` or `{` (JSON blobs) or run past 25 tokens (CSV headers). Falls back to the
   filename stem. *11,737 of 12,760 titles came from page 0.*
2. **Fiscal years.** Every `20NN-NN` token in the title, path, and first three pages. The first
   one found becomes `fy_primary` — the edition. *8,002 of 12,760 documents have one.*
3. **A family key.** The title, lowercased, with its fiscal years replaced by `{fy}` and a fixed
   list of copy-markers removed (`copy`, `draft`, `final`, `v2`, `(3)`, `rev`, `backup`, …). So
   *Annual Budget Statement 2018-19* and *Annual Budget Statement 2019-20 (final)* both become
   `annual budget statement {fy}` — **one publication, two editions**. *1,618 families; 393 of
   them hold two or more editions.*
4. **Table captions.** Lines matching `Table <number>: <text>`, plus any of the first 15 pages
   containing "Contents" or "List of Tables". Capped at 400 per document, deduplicated.
   ***89,380 captions.***
5. **A catalog blob** — contents text plus caption text — and a `head` of the first two pages.

Then it clusters. Documents are grouped by `(family, fy_primary)`; identical SHA-256 hashes
collapse into one survivor with its duplicates listed; and among the survivors of one edition the
**largest by page count wins and becomes the primary** — the one `find` will offer. The rest stay
in the database but are hidden from results. *12,760 documents + 874 collapsed duplicates =
13,634, the exact indexed count.*

Finally it embeds each card — `title | family | catalog[:1200]` — with `BAAI/bge-small-en-v1.5`
via fastembed, on CPU, L2-normalised, stored as float16. *12,760 vectors at 7.6/s, 1,675 s,
which is 98% of the build's wall time.* Checkpointed every 10 batches, because an earlier run was
killed mid-embedding with nothing recoverable.

`shelf.db` ends up with `docs`, `captions`, `families`, `cards` (an FTS5 table over
`title, family, catalog, head`) and `meta`.

## Steps 3 and 4. The caption channels — `c_caption_index.py`, `c_caption_embed.py`

The shelf already stores every caption. These two scripts make captions *independently
searchable*, at corpus scale, as their own retrieval unit:

- **Step 3** copies the 89,380 captions into `captions_fts.db` as an FTS5 table
  `cap(rel, page_index, caption)`. Takes seconds.
- **Step 4** embeds all 89,380 with the same model into `captions.f16.npy`, with
  `captions_ids.jsonl` mapping each row back to `(rel, page_index)`. Alignment is *positional* —
  row `i` of the npy is row `i` of `captions ORDER BY rowid` — and §16.4 explains why that matters.

Both read `shelf.db` read-only and never write to it. The shelf is a frozen instrument; these sit
beside it.

The reasoning: a caption is the shortest honest description of what a table holds. A page-length
relevance score treats 400 words of prose and the one table you want as the same object; a
caption does not.

## Step 5. Install — `corpus-lab/bin/c_stack.py setup`

**In:** the folder, the shelf directory.
**Out:** exactly two files inside the folder, plus one registry entry.

1. **`CLAUDE.md`** — the operating instructions the model reads. This *is* the orchestration
   layer. There is no planner, no router, no agent framework: the policy is prose, and §6–§12
   below are its five numbered sections. It is generated from a template with the frozen flags
   substituted in, so what a live session runs is exactly what the offline gates measured.
2. **`.claude/settings.json`** — a deny list (built-in Grep/Glob and every private lab path) and
   one `Stop` hook running `c_stop_guard.py --v2`.
3. **A registry entry** in `%LOCALAPPDATA%\retrieval-lab\roots.json` mapping the folder to its
   `pages.db` and `shelf.db`. This is how `c_shelf.py` works with no arguments: it walks up from
   the working directory until it finds a registered root.

Install is transactional in the only way that matters: a state file listing the two files it will
create is written **before** either exists, so a teardown after a crash knows exactly what to
remove — and refuses to remove anything it did not create.

`setup_folder.py install` runs steps 1–5 in order, skipping any stage whose output already
exists, so an interrupted install resumes by re-running the same command.

---

# Part B — question time

Nothing is resident. Every command below is a fresh Python process that opens two SQLite files,
answers, and exits. That is why several caches (page ranges, coverage counts, caption-row maps)
are written *into* `shelf.db` rather than held in memory.

## Step 6. `find` — which publication?

```
c_shelf.py find "<question>" --fusion rrf --caption-channel lex --compact 40 \
    --q "<rewrite>" --q "<rewrite>" --q "<rewrite>"
```

**In:** the question as asked, plus three to five rewrites the model writes itself. CLAUDE.md
tells it how: the row name as a statistical publication would print it; the publication plus the
fiscal year; the two-to-four nouns naming subject, place and period.

**What happens** (`do_find`, `c_shelf.py:444`). For **each** query string, up to four ranked
lists of documents are produced:

| channel | function | mechanism |
|---|---|---|
| lexical cards | `_lex_search` | FTS5 `OR` over the card, `bm25` weighted title 3.0, family 3.0, catalog 2.0, head 1.0 — top 200 |
| dense cards | `_vec_search` | query embedded, cosine against all 12,760 card vectors — top 200 |
| lexical captions | `_cap_search` | FTS5 over 89,380 captions; **all** label words first, falling back to **any** if under 20 hits — top 200, mapped to the documents those captions sit in |
| dense captions | `_cap_vec_search` | same, cosine over caption vectors — only with `--caption-channel lex+vec` |

"Label words" are the query's content words minus fiscal-year tokens minus trajectory filler
("trend", "over time", …), because a year is printed in the table *body* as a column heading and
almost never in the caption.

All the lists — 3 queries × 3 channels = 9 of them, in the frozen configuration — go into one
**reciprocal rank fusion** at `k=60`: a document scores `Σ 1/(60 + rank)` over every list it
appeared in. Document scores then collapse to **family** scores — *a family scores whatever its
single best document scores* — and the families are sorted.

**Out:** with `--compact 40`, forty one-line cards:

```
#3  annual budget statement | 15 editions 2011-12-2025-26 | Receipts: Public Sector Development Programme (Federal)
```

then a `RECEIPT` line (how many queries, how deep each channel went, how many families and
documents were considered) and the `COVERAGE` line. `--show 3,7,9` reprints chosen ranks in full
with their editions, their evidence lines, and the exact `inside` command to run next.

**Why forty lines and not twelve full cards.** Offline, the right publication is in the fused top
10 on 10 of 17 dev questions but the top 50 on 14 of 17. Experiment H measured that a model shown
100 one-line cards re-ranks the right one into *its own* top 10 on 11–14 of 17 — better than any
statistical reranker tried. `--compact` is that mechanism at zero extra model calls: show more of
the list, one line each, in the session already running.

## Step 7. `have` — the honest no

```
c_shelf.py have "<publication words>" --fy 2012-13
```

A three-tier cascade (exact phrase in the title column → all words over title+family → any word),
then: does the best-matching family hold an edition for that year?

- `EDITION_PRESENT 2012-13 <path> (279p)`
- `NO_EDITION_FOR 1998-99 in "annual budget statement {fy}"; nearest: None, 2011-12; editions held: [...]`
- `NO_FAMILY_MATCHES "<words>"`

Every reply also prints `UNREADABLE_FILES_WITH_MATCHING_NAME=n` — files whose *name* matches but
whose text never extracted, so "we don't hold it" is never confused with "we hold it and couldn't
read it".

**This is the project's one solved headline.** It is a structural check — *do I hold any edition
of this publication for that year?* — not a confidence threshold, which is why it works where
every scoring approach scored 0 of 3. It measures 11/11 on absent editions and, via `exact`
returning `TOTAL_PAGES_MATCHING=0`, 4/4 on absent identifiers. The live battery scored it 11 of
15 after two measurement defects were repaired; the old 1-of-15 number is published alongside,
labelled superseded rather than deleted.

## Step 8. `inside` — which page?

```
c_shelf.py inside "<path>" "<subject in a few words>"
```

**In:** one document's path and a short subject phrase.

**What happens** (`do_inside`, `c_shelf.py:979`). The document's pages are pulled out of
`pages.db` and loaded into an **in-memory FTS5 table** — a 190-page document, not 1.2 M — then
ranked by `bm25` in tiers: exact phrase if ≤4 words, else all words, falling back to any word.
The tier used is printed, so a loose match is never mistaken for a precise one.

Then the caption channel reorders it. The default is **`dense_first` (B2c)**: this document's own
captions are scored by cosine against the query's label words, and pages above *the document's
own median caption score* (with a floor of the top 3) are promoted ahead of the body ranking. No
threshold is tuned against the questions — the cut is relative to the document itself.

B2c exists because of a measured vocabulary gap: on every year-asking question, **no caption in
the right document contains the question's subject words at all**. The tax is listed under its
statutory name, the series under its official title. A lexical matcher cannot cross that however
it is phrased; an embedding can. **82.7% on a page-level holdout** — the second solved
sub-problem.

**Out:** up to `k` lines of `p<page_index>  <bm25 score or None>  | <best matching line>`.
A `None` score means the page arrived via the caption channel and the body ranking never returned
it.

## Step 9. `series` — the same row across editions

```
c_shelf.py series "<row words>" --family "<publication>" --from 2015-16
```

Resolves the family (through `have`, or exactly if the caller already holds a real family key),
takes every primary edition in the year range in order, and runs `inside` on each. One line per
edition: the fiscal year, the page, and the matching line — or `NO_MATCH`.

It does **not** open pages. CLAUDE.md says so explicitly, because a `series` line is a search
result and the rule in §10 has no exceptions.

This is also where the vintage rule lives: a fiscal year's figure is usually reprinted, revised,
in the next one or two editions. Measured on the fixture, the edition that actually prints year
Y's row is Y itself only 4 times in 14 — it is Y+1 six times and Y+2 four times. **The year
narrows the row, not the edition.** CLAUDE.md therefore tells the model to check Y, Y+1 and Y+2
and to report which vintage each figure came from.

## Step 10. `open` — the only way text becomes evidence

```
c_shelf.py open "<path>" <page_index> --slug <slug>
```

Returns the page body, capped at 12,000 characters. With `--slug`, it appends
`{"rel", "page_index", "ts"}` to `<slug>_opened.jsonl` in a per-corpus notes directory under
`%LOCALAPPDATA%`.

That log is the whole provenance mechanism. Everything downstream checks against it.

## Steps 11–12. `note` and `notes` — provenance the tool enforces

```
c_shelf.py note --slug <slug> "<verbatim line> | <path> | p<page_index>"
```

`do_note` (`c_shelf.py:1270`) requires the `| <path> | p<n>` tail, then requires that
`(path, page)` to appear in *this slug's own* `_opened.jsonl`. Paths match on their last two
segments, lowercased — the same rule the scorer uses, because the model quotes the path as `find`
printed it and byte-identical comparison would reject honest notes over punctuation.

If it does not match, nothing is recorded and it exits 3 with `NOTE_REFUSED_PAGE_NOT_OPENED`.

The reasoning is written into the source, and it is the most transferable thing in this
repository: *an instruction the tool does not enforce is a suggestion.* The rule "open before you
cite" sat in CLAUDE.md the whole time two live batteries produced 5 and then 8 answers citing
files the session never opened.

`notes --slug <slug>` prints the opened log and the accepted notes. CLAUDE.md requires the answer
to be built from those and nothing else, ending in a `Sources` block, one line per figure:
`<figure> | <path> | p<page_index> | "<verbatim line>"`.

## Step 13. `c_stop_guard.py --v2` — the check at the answer boundary

A `Stop` hook. It reads the session transcript, collects every `open "<path>" <page>` the session
issued and the final assistant message, and applies four rules in order:

1. **v1** — a path-like string in the answer that no `open` matches → block.
2. **v2** — a `Sources` line naming a `(path, page)` that was never opened → block.
3. **v2** — a page number in prose (`"Title, p.239"`) that no opened page carries → block. This
   is the hole v1 had: prose citations name no path, so v1 never saw them.
4. **v2** — figures with units and *no* citation anywhere → block. This is the other half:
   an answer that cites nothing satisfies a guard that only inspects citations.

Its manners are deliberate and deliberately narrow: it asks **once** per session, writes a marker
file so it cannot ask twice, never edits text, and lets any second stop through unconditionally.
A session that disagrees, or genuinely cannot open the page, always terminates. It is a check at
a boundary, not a controller — explicitly unlike the earlier S2 hook, which denied the search
tools outright and scored *worse* than one line of prose in CLAUDE.md.

---

## 14. A real trace, end to end

Run today against the production shelf, 2026-09-15. Not a reconstruction.

**`find`** — 3 queries, 3.4 s cold:

```
#1  consolidated federal and provincial fiscal | 12 editions 2014-15-2025-26 | Table 1.1: Development Expenditure
#2  consolidated federal and provincial fiscal operations | 5 editions 2014-15-2025-26 | Table 1.1: Development Expenditure
#3  annual budget statement | 15 editions 2011-12-2025-26 | Receipts: Public Sector Development Programme (Federal)
#4  cite consolidated federal and provincial fiscal | 4 editions 2014-15-2025-26 | Table 1.1: Development Expenditure
#5  ite consolidated federal and provincial fiscal | 1 edition 2014-15 | Table 1.1: Development Expenditure
...
RECEIPT queries=3 lex=[200] vec=[200] families=122 docs_considered=937 shown=8
COVERAGE indexed=13634 image_only_no_text=1211 failed=32 unsupported=120 pages=1206260
```

937 documents were scored; they collapsed to 122 families; 8 were shown. Note ranks 4 and 5 —
`cite consolidated…` and `ite consolidated…` are the *same publication* as rank 1, split off as
fragment families. That is the defect §16.1 covers, visible in the first query I ran.

**`--show 3`** gives the full card and the next command:

```
#3  family: annual budget statement {fy}
    editions: 2011-12*(224p) 2012-13*(279p) 2013-14*(240p) … 2024-25*(184p) 2025-26*(191p)
              [15 editions, 64 copies not shown]
    open with: inside "Sources/Federal/Annual Budget Statement/2018-19/Annual Budget Statement 2018-19.pdf" ...
```

**`inside`** — 1.4 s:

```
INSIDE …/Annual Budget Statement 2018-19.pdf (190p) tier=all
  p25  -9.408  | Public Sector Development Programme (Federal) is reported at 414,045 Rs million for 2015-16.
  p60  None    | Table 2.1: Total domestic debt
  p95  None    | Table 3.1: Federal Excise Duty
```

p25 came from the body ranking. p60 and p95 are dense-caption promotions with no body hit — and
they are off-subject, which is the honest cost of a median cut inside a document whose captions
are all roughly equally unlike the query.

**`open` → `note`** — the enforcement, both directions:

```
$ open "…/Annual Budget Statement 2018-19.pdf" 25 --slug enginedoc
OPENED …/Annual Budget Statement 2018-19.pdf p25

$ note --slug enginedoc "made up line | …/Annual Budget Statement 2018-19.pdf | p999"
NOTE_REFUSED_PAGE_NOT_OPENED …/Annual Budget Statement 2018-19.pdf p999      (exit 3)

$ note --slug enginedoc "Public Sector Development Programme (Federal) is reported at
                         414,045 Rs million for 2015-16. | …2018-19.pdf | p25"
NOTED                                                                        (exit 0)
```

**The absence path**, same shelf:

```
$ have "annual budget statement" --fy 1998-99
NO_EDITION_FOR 1998-99 in "annual budget statement {fy}"; nearest: None, 2011-12;
  editions held: ['2011-12', …, '2025-26']

$ exact "SRO 9999(I)/2099"
TOTAL_PAGES_MATCHING=0
NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING
```

---

## 15. Every artefact, and who writes it

Production paths under `corpus-lab/02_stacks/`; a folder installed with `setup_folder.py` gets
the same set under `02_stacks/portable/<label>/`.

| file | written by | holds | size on the fixture |
|---|---|---|---|
| `s2_fts5/harness_15000.db` | `index_build.py` | 13,634 files, 1,206,260 pages | 6.49 GiB |
| `s7_shelf/shelf.db` | `c_shelf_build.py` | 12,760 docs, 1,618 families, 89,380 captions, cards FTS | 76 MB |
| `s7_shelf/cards.f16.npy` | `c_shelf_build.py` | 12,760 × 384 float16 | 9.3 MB |
| `s7_shelf/cards_ids.jsonl` | `c_shelf_build.py` | npy row → document path | 1.3 MB |
| `s7_shelf/captions_fts.db` | `c_caption_index.py` | 89,380 captions, FTS5 | 22 MB |
| `s7_shelf/captions.f16.npy` | `c_caption_embed.py` | 89,380 × 384 float16 | 65 MB |
| `s7_shelf/captions_ids.jsonl` | `c_caption_embed.py` | npy row → (path, page) | 10.6 MB |
| `s7_shelf/captions_by_rel.json` | `c_shelf.py`, lazily | path → npy rows, a startup cache | 1.4 MB |
| `shelf.db: page_ranges` | `c_shelf.py`, lazily | path → contiguous page rowid block | in shelf.db |
| `shelf.db: meta.coverage_cache` | `c_shelf.py`, lazily | the COVERAGE line, keyed to the index's size+mtime | in shelf.db |
| `%LOCALAPPDATA%/retrieval-lab/roots.json` | `c_shelf.py register` | folder → (pages.db, shelf.db) | — |
| `%LOCALAPPDATA%/retrieval-lab/notes/<key>/` | `open`, `note` | per-slug opened log and notes | — |
| `<folder>/CLAUDE.md`, `<folder>/.claude/settings.json` | `c_stack.py setup` | the policy and the hook | — |

The three lazy caches deserve a note, because they are the reason the system is usable at all.
Every shelf command is a fresh process, and `rel` is `UNINDEXED` in both FTS5 tables — so a
`WHERE rel=?` lookup is a full scan of 1.2 M rows, about 7.5 s, on *every* `open`. The page-range
cache turns that into a rowid lookup. All three were verified rank-preserving: `open` was checked
byte-identical on 300 pages by `c_open_equiv_check.py`.

---

## 16. Couplings and inconsistencies, found by reading the code

These are not in any design document. Four of the five I found while writing this and verified
today; the first is known and recorded as F66.

### 16.1 Edition assignment and copy visibility are the same `None` branch

In `c_shelf_build.py`, a cluster with `fy_primary is None` makes **every survivor a primary**
(visible in `find`); a cluster with a year makes **one primary and hides the rest**. So any change
to how editions are assigned silently changes how many files `find` will offer.

Shelf v2 learned this the expensive way: normalising bare years gave 4,333 previously year-less
documents an edition, which flipped their clusters from "all visible" to "one visible", dropped
primaries from 7,694 to 4,198, and raised gold evidence files hidden as non-primary from 20 to
31. That one row failed its pre-registered gate and v2 was rejected. Production stays on v1.

The related defect is visible in §14's trace and in `have "annual budget statement"`, which
returns **seven** families for one publication — `annual budget statement {fy}`,
`… {fy} cite`, `text … front matter`, `notes ran the full pipeline against …`. Title extraction
takes the first plausible line of page 0, and when that line is a fragment the family key is a
fragment too. Shelf v2's family merge fixed exactly this (35 duplicate slots in a dev `find` → 0)
and is the change H5 recommends rebuilding on its own.

### 16.2 The installer builds a shelf that production rejected

`setup_folder.py:164` runs **`c_shelf_build_v2.py`** for every new folder. The 15,000-file
production rung runs v1, because v2 was rejected by Gate S.

So there are two different shelf builders in the shipped system, and which one you get depends on
whether you are the frozen fixture or a folder someone installs today. The v2 defect is a
*visibility* regression — fewer files offered as primary — which is invisible in a `find` listing
and shows up only as an evidence file the model is never shown.

This may well be deliberate (v2's family merge genuinely fixes the fragment problem, and a fresh
folder has no gate history to protect), but it is written down nowhere, and the handoff's
"production stays on v1" is true only of the fixture.

### 16.3 The recorded "frozen page caption" value is not what runs

`c_stack.py` defines `FROZEN_PAGE_CAPTION = "first"` and writes it into the install state file as
part of the frozen configuration. But `{PAGECAP}` never appears in the CLAUDE.md template — the
substitution at `c_stack.py:156` is a no-op — and there is a self-test
(`claude_md_inside_no_stale_caption_flag`) asserting the `inside` example carries **no**
`--caption` flag at all.

So `inside` runs the CLI default, which is **`dense_first`** (B2c, adopted as F55), not `first`
(B2). The behaviour is the intended one; the recorded frozen value is stale. Anyone reading the
state file to reproduce a run would reproduce the wrong page channel.

### 16.4 Caption vectors are aligned by position, and re-embed silently if they drift

`_stored_caption_vectors` (`c_shelf.py:882`) matches a document's stored vectors to its caption
rows by requiring an identical `page_index` sequence in rowid order. If that check fails — a
rebuilt shelf, a partially written npy — it returns `None` and `inside` **re-embeds the
document's captions on the fly**. Correct, and about 1.3 s slower per call on a 500-page
document, with nothing printed to say it happened.

### 16.5 Two state files were overwritten by a test build

`corpus-lab/state/c_caption_index.json` and `c_caption_embed.json` currently read **4,483
captions**. That is the Phase 6 cold test on a 500-file folder, not the production shelf, which
holds 89,380 (verified by counting rows in `captions_fts.db` today). `c_shelf_build_v2.json` has
the same problem and the orchestrator brief flags it; these two are not flagged anywhere. The
artefacts on disk are correct — only the state files lie.

---

## 17. What this engine is measured to do, and what it is not

Stated plainly, because the pipeline above describes a mechanism, not a result.

**Works, measured:**
- Honest "we don't hold that" — 11/11 absent editions, 4/4 absent identifiers, 11/15 live.
- The right page inside a document already known to be right — 82.7% on a holdout.
- Not citing a file path the session never opened — 10 → 0.
- Coverage accounting, content hashing, safe install and teardown.

**Does not work yet:** picking the right document from a vague question. Across four live
batteries the right publication did not surface on 9 to 11 of 17 questions. Offline document
recall has moved by five questions over the project; the live outcome has not moved at all.

**The reason, measured rather than assumed:** this corpus republishes the same fiscal tables
every year across dozens of near-identical editions, and restates each year's figure in prose on
many pages within each edition. A vague question's words match hundreds of candidates about
equally. It is a **disambiguation** problem, not an indexing or vocabulary one — which is why
better word matching, query rewrites, wider aliases, deeper candidate pools, and two rerankers
all measured out to approximately zero.

---

## 18. Where to go next

- **The record of every experiment:** [`REPORT/README.md`](REPORT/README.md), then
  [`REPORT/08_what_next/SESSION_LOG_2026-09-13_to_09-14.md`](REPORT/08_what_next/SESSION_LOG_2026-09-13_to_09-14.md).
- **The current state of each box, with numbers:**
  [`REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md`](REPORT/08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md)
  and its 09-16 addendum.
- **The build contract these scripts implement:**
  [`REPORT/06_approach_c_shelf/C_SHELF_FIRST_BUILD.md`](REPORT/06_approach_c_shelf/C_SHELF_FIRST_BUILD.md).
- **How to use it as a person:** [`INSTALL_FOR_SIR.md`](INSTALL_FOR_SIR.md).
- **Every number's source file and checksum:** [`REPORT/MANIFEST.md`](REPORT/MANIFEST.md).
