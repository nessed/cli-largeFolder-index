# Approach C — "shelf first": find the book, then the page

A third approach, distinct from the page-ranking family (S1/S2, approach B) and from the
table-cell catalogue the other agent is building. The executor prompt is
`C_SHELF_FIRST_BUILD.md`.

---

## 1. The idea in one paragraph

Every stack so far asks one question of 1.2 million pages at once: "which page answers
this?" That is not how an economist finds a number. They think "that's in the Economic
Survey, statistical appendix, the provincial ADP table — I need the 2015-16 through
2018-19 editions", pull those four volumes off the shelf, and turn to the table. The
document is chosen by *what publication it is and which year*, and the page is found
inside a few hundred pages, where plain keyword search works fine. C builds that shelf:
one card per document, saying what publication it is, which edition, how many pages,
what tables it lists, and which other files are copies of it. Questions are answered in
two moves — pick the documents (13,634 cards, not 1.2 M pages), then search inside them —
and the two things the lab could not get, honest absence and multi-year trajectories,
fall out of the shelf's structure rather than out of a relevance score.

## 2. Why the lab's own evidence points this way

- **The failure is at page scale.** The correct page ranks 62–2,917 among 1.2 M when the
  question's words are used (`state/rank_experiments.json`), yet the exact row label
  appears on 13,909 pages ("sindh -- annual development programme") because the corpus
  repeats every series across prose restatements, copies and drafts. Ranking pages will
  always face that repetition. Ranking *documents* does not: there are 15 editions of the
  Economic Survey under `Sources/Federal/Economic Survey/`, one per year, 331–530 pages
  each, and every trajectory question in the frozen 20 is answered inside them.
- **The documents describe themselves.** Page 0 of each publication carries its title
  and fiscal year; pages 2–3 carry a Contents page and a **List of Tables** with the row
  labels ("Agriculture: Cotton Production", "Fiscal Development: Sales Tax"); body pages
  carry `Table A.22: …` captions (≈ 88,700 in the corpus by sampling). A card built from
  those is small, distinctive, and speaks the vocabulary the questions use. Real Pakistani
  publications have the same front matter.
- **Copies are a document-level problem.** The 2015-16 Economic Survey exists as one
  530-page file plus 25+ partial copies of 7–53 pages named "(2)", "copy", "DRAFT",
  "old tables", "rebased", "perturbed values", spread across `Downloads`, `Papers`,
  `Teaching`, `archive`. Their page-0 titles are identical to the original's. Clustering
  cards by title makes the original the obvious primary (most pages), and shows the
  copies as copies instead of as 25 competing search hits.
- **Absence is a shelf question.** Of the key's 15 absence questions, 10 are of the form
  "do we have the Gilgit-Baltistan white paper for 2012-13" / "the 2026-27 survey" / "the
  budget statement for 2008-09". The shelf holds GB white papers for 2013-14, 2015-16,
  2017-18, 2019-20, 2022-23, 2025-26 — so "2012-13 is not on the shelf; nearest editions
  2013-14" is a fact the tool can state, not a threshold guess. F22 showed a score floor
  cannot do this; an edition list can. The other 5 (SRO and demand numbers) are literal
  identifiers, where an exhaustive exact search with a zero count is already a strong
  negative.
- **Trajectories are a shelf walk.** "Development spending since 2015 across four
  years' surveys" is: take the Economic Survey family, for each edition from 2015-16 on
  find the page with the row, return the line. One command, one table of (edition, page,
  line). That is the success criterion in sir's own words.
- **F21 still applies** (the model cites what it never opened), so C keeps the same
  open-then-note-then-answer discipline as B.

## 3. What gets built

```
corpus-lab/bin/c_shelf_build.py   builds shelf.db + card vectors from the existing FTS index (read-only)
corpus-lab/bin/c_shelf.py         the front door: find, have, inside, tables, series, copies, exact, open, note, notes, coverage
corpus-lab/bin/c_stack.py         installs / removes CLAUDE.md + settings.json for stack s7_shelf
corpus-lab/bin/c_offline_gate.py  the free measurement (document rank, in-document page rank, series walk, absence enumeration)
corpus-lab/02_stacks/s7_shelf/    shelf.db, cards.f16.npy (small)
```

### The card

For each indexed file: `title` (first non-empty line of page 0, or filename stem when
page 0 has no title-like line), `family` (title with fiscal-year tokens replaced by `{FY}`
and generic version markers — `(2)`, `copy`, `draft`, `final`, `new`, `old`, `v2` —
stripped), `fy_primary` and every fiscal year seen in the first three pages, `catalog`
(Contents + List of Tables pages from the first 15 pages, plus every `Table X: …` caption
line with its page index), `head` (first 1,500 characters), `n_pages`, `sha256`, `ext`.
Cards go into an FTS5 table with column weights title 3, family 3, catalog 2, head 1, and
into a bge-small vector file (13,634 × 384, ~10 MB; roughly 20–40 minutes to embed at the
measured 7–12 strings/s for ~1,200-character inputs). No page vectors.

Families are clustered on `family`; within a family and fiscal year the member with the
most pages is the **primary**, identical hashes collapse to one entry, and everything else
is a **copy**.

### The commands

| command | what it returns |
|---|---|
| `find "<question>" [--q …]` | up to 12 families ranked by their best card (BM25 + vector, fused), each with its editions (fiscal years, primary marked, page counts), copy count, and the two catalog lines that matched |
| `have "<publication words>" [--fy 2012-13]` | matching families and their editions; with `--fy`, an explicit `EDITION_PRESENT` or `NO_EDITION_FOR 2012-13, nearest: 2013-14`, plus the count of unreadable files whose names match |
| `inside "<rel>" "<terms>"` | top pages *within one document* (an on-demand in-memory FTS5 over its pages), each with the matching line |
| `tables "<rel>"` | the document's caption lines with page indexes |
| `series "<row words>" --family "<publication words>" [--from 2015-16]` | one row per edition of the family: fiscal year, page index, the matching line — the trajectory command |
| `copies "<rel>"` | the other members of its family/edition with pages, hash equality and paths |
| `exact "<literal>"` | corpus-wide phrase count and grouped hits |
| `open "<rel>" <page>` / `note` / `notes` / `coverage` | as in approach B |

## 4. What it costs

| item | cost |
|---|---|
| shelf build | one pass over the index's first pages plus caption lines: minutes; card embedding 20–40 min once; incremental by content hash afterwards |
| per question | `find` ≈ 1–2 s, `inside` < 1 s, `series` ≈ 0.3 s × editions |
| offline gate | free (local); 20 optional Haiku rewrites on Max quota if B's are not already on disk |
| paid battery | same as B: ~$1–2 canaries, ~$3–6 questions, ~$1–2 extra absence |

Setup scales with the number of documents, not pages, which is the property that matters
on a 10,000-file drive of unknown page count.

## 5. Where it will fail

- **Documents without a self-description.** Scanned PDFs (1,211 here) have no card
  beyond the filename; papers and notes get a filename-plus-head card, which is weaker.
  The build reports the fraction of cards with a detected family and fiscal year; on
  sir's real drive that fraction is the first thing to look at.
- **Questions with no publication handle at all** ("has cotton production gone up") lean
  on the catalog text and the card vectors finding "Agriculture: Cotton Production" in a
  List of Tables. This is the case the offline gate tests hardest.
- **Family detection on messy real titles.** Two spellings of the same publication
  ("White Paper Budget 2022-23 Gilgit-Baltistan" vs "White Paper on the Budget 2022-23 -
  Government of Gilgit-Baltistan") become two families. `find` still shows both; `series`
  walks one. A later merge step by List-of-Tables similarity is the obvious fix, not in v1.
- **Notes, memos and spreadsheets** are single-edition "families" of one; the shelf gives
  them no special power beyond being small distinctive cards, which is already better than
  page ranking for them.
- **It does not read tables for you.** C finds the page and quotes the line; unit and
  vintage interpretation stay with the model, as in every other stack here.

## 6. What "worked" means for C

Offline, free, on the frozen 20 plus the key's 15 absence questions:

| measure | gate |
|---|---|
| evidence document's family in `find` top-10 (question verbatim, no rewrites) | **≥ 12 of 17** |
| evidence page in `inside` top-5 for PDF evidence | ≥ 10 of those with a page index |
| `series` finds the row's page in ≥ 2 editions for ≥ 3 of the 4 trajectory questions | yes/no |
| `have --fy` says NO_EDITION for the 10 document-level absence questions | ≥ 9 of 10 |
| `have --fy` says EDITION_PRESENT for the 17 evidence editions (control) | ≥ 15 of 17 |

Then the paid battery on the same terms as B: evidence opened on ≥ 6 of 17, honest on
≥ 10 of 15 absence questions under the corrected rule, forbidden citations ≤ 8.
