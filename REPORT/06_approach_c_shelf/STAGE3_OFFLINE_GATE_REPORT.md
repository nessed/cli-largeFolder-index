# Approach C, Stage 3 — the offline gate, in full

> ## Correction — 2026-09-14
>
> **The body of this report is left exactly as written on 2026-09-13. Four of its
> numbers were measured by a defective harness. This block says which, and what they
> are once the harness is fixed. Every historical number below still reproduces
> exactly from the same code path, so nothing here is a retraction of a measurement —
> it is a correction of what the measurement was of.** Full detail in findings
> F41–F44 and in [`../08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](../08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md).
>
> **1. The page row was measured with the whole question (defect D1).** §2's
> `page_rank ≤ 5` row fed the in-document search the entire question text, which
> overflows its four-content-word exact-phrase tier — the same defect that had
> already been found and fixed for the series walk, never carried across. The
> corrected baseline, using the short row phrase, is **24 of 57 addresses (42.1%
> micro, 27.9% macro)**, against the historical 25 of 57 (43.9%). The defect was
> real; it was not costing anything. The corrected 24/57 is the baseline any page
> change must now beat, not the 43.9%.
>
> **2. The document denominator excluded two questions (defect D2).** Two of the 17
> answerable questions were scored an automatic miss because the shelf had
> hash-collapsed their evidence path into another file's duplicate list. Resolving
> those paths to their surviving twin — byte-identical files share page indices —
> rescues both and leaves **0 of 17 excluded**. Corrected counts: **C1 stays 6/17**,
> **C2 moves 8/17 → 9/17**. That is a scorer correction, not a retrieval improvement.
>
> **3. The present-edition control was circular (defect D3).** §2's 14/17 control
> queried the shelf with the shelf's own family words, so it asked the shelf about
> itself. The corrected control asks the *question's* own words with a year the
> family actually holds swapped in: **8 of 11 say EDITION_PRESENT**, 3 unresolvable
> because the matched family holds no dated primary. That is a weak pass, not the
> clean 14/17. The absence result itself survives intact — all 11 document-level
> hits are `NO_EDITION_FOR`, none is `NO_FAMILY_MATCHES`, so the circularity the
> review feared did not bite.
>
> **4. Per-question ranks were never persisted (defect D4), so §2's headline hid the
> real result.** Recall past the top 10 was unknown. It is now: **C2 gold-family
> recall@100 is 16 of 17** on this set and 28 of 30 on the frozen holdout. The
> candidate pool nearly always holds the answer. This report's document failure is a
> ranking failure, not a retrieval-coverage failure — and a compact cross-encoder
> over that pool was then built, measured and **failed its gate** (F44).
>
> **5. §3's series result does not mean what this report reads it as.** `series_ok`
> stays 1 of 4 even with the best available page method. The reason is not page
> retrieval: across the four trajectory questions the fiscal years line up on 21 of
> 24 evidence years, but the file the walk opens at that year is the file the key
> cites on only **3** of those 21. The walk has been measuring which copy the shelf
> calls primary. Handed the correct document, the same trajectory pages are found in
> the top 5 on **40 of 42** addresses (F42).


*Written 2026-09-13. This is the detailed report behind the summary table in the
project's main [`README.md`](../README.md) §7. It covers only Stage 3 — measuring
the shelf that Stage 1 built — and it updates two numbers from what that summary
currently shows: the series-walk result changed after a bug was found and fixed
while writing this up (see §3). Nothing from `_private/` (the answer key) appears
below — only counts, and the public text of the questions themselves.*

## 1. What this stage is measuring, and why it's free

Approach C's idea (full plan in this folder's `C_SHELF_FIRST_PLAN.md`) is: instead
of ranking 1.2 million individual pages against a question, first figure out **which
document** answers it — the way a person pulls a specific year's report off a shelf —
then search inside just that one document. Stage 1 built the shelf: a card for every
document, showing what publication it is, which year's edition, how many pages, and
which tables it lists. Stage 3 is the free, no-cost check of whether that idea
actually works, run against 17 real questions with a known answer key, before any
money is spent on a live model session.

Every row below is a **yes/no bar measured against 17 questions** (or a related count
for a subset of them), not a vague impression. "Passed" and "failed" are stated
exactly as the build's own spec defined them going in.

## 2. Every gate row, with its number and its bar

| what's being checked | result | bar to clear | outcome |
|---|---|---|---|
| Does the shelf rank the *correct document* in its top 10, asking the question exactly as written? | 6 of 17 | needed 12 of 17 | **failed** |
| Same thing, but first paraphrasing the question five different ways and combining all six searches | 8 of 17 | informational only | still short |
| Once the correct document is found, is the correct *page inside it* in the top 5 results? | 25 of 57 checks (43.9%) | 60% for a clean pass, 40% floor for a weak pass | weak pass |
| For a question asking "how did this number change over several years," does the shelf correctly walk from edition to edition and land on the right page in at least 2 of the years asked about? | 1 of 4 | needed 3 of 4 for a pass, 2 for a weak pass | **failed** (see §3 — this number moved during review) |
| When a document genuinely isn't on the shelf for the year asked, does the shelf correctly say so instead of guessing? | 11 of 11 | needed 9 of 10 | **passed** |
| As a control: for years the shelf *does* hold, does it correctly say so (not falsely claim absence)? | 14 of 17 | needed 15 of 17 for a clean pass, 13 for a weak pass | weak pass |
| For a question naming a specific document number (like a notification or reference number) that isn't in the corpus, does an exact search correctly return zero hits? | 4 of 4 | — | passed |

**In plain terms:** the shelf is reliably honest about what it does and doesn't hold —
both flavors of "we don't have that" work well. What it is *not* yet reliable at is
the first, most basic step: given a plainly-worded question, correctly picking out
which document answers it. That's failing on more than half the questions, and it's
the thing everything else in the pipeline depends on — if the wrong document is
picked, no amount of in-document search recovers the answer.

Two of the 17 questions couldn't be measured on document-ranking at all, because
their evidence documents were among the ones the shelf's own duplicate-collapsing
legitimately merged away (see the shelf-build report in this folder for that
accounting — it closes exactly, nothing was silently lost).

## 3. The series-walk number: a bug in the test, found and fixed mid-review

The fourth row above — "walk the editions and find the row in at least 2 years" — is
the specific test for questions like *"has cotton production gone up or down over the
period, and by how much"* or *"how does [a province]'s development programme look over
the last decade"*: four such questions are in the frozen sample. The first run of this
gate measured **0 of 4**, which on its face reads as a complete failure of the whole
"search inside one document" idea. On closer inspection it was measuring something
narrower and fixable.

**Defect one — the wrong search term.** The build's own instructions had the
series-walk step search *inside* each year's edition using the entire question as
the search phrase. A trajectory question is a full sentence — "how does sindh --
annual development programme look over the last decade or so" — and a full sentence
is far more words than the in-document search's exact-match mode will take (its
cutoff is 4 words). Past that cutoff it falls back to matching *any single word*,
which on a document where every subject gets mentioned dozens of times in different
paragraphs is nearly useless for picking out the one specific page wanted, and the
first run only kept a single best guess per year. **Fix:** pull out just the 2-4
words that actually name the row being asked about — "annual development programme,"
"cotton production," "total budget outlay" — using a small, general rule (not
anything specific to these four questions: look for text set off by a dash before a
transition word like "look" or "across," and otherwise strip the standard sentence
scaffolding), and check the top 5 results per year instead of only the top 1.

**Defect two, found while fixing the first — the walk was quietly checking the wrong
document.** Each year's edition belongs to a named "family" (e.g., "Annual
Development Programme" for a given province). The series-walk step was re-finding
that family by *searching for its own internal name*, the way a person would type a
publication title into a search box. But a family's internal name isn't natural
text — it's a template like `annual development programme {fy}`, with a literal
placeholder where the year goes. Searching for that literal placeholder text doesn't
match any real document title, so the lookup fell back to a loose, one-word-at-a-time
match — and on at least one of the four questions, that loose match landed on an
unrelated document that happened to share generic wording, not the real 15-edition
publication. The walk was checking the right *years* but the wrong *document* for
some of its four cases. **Fix:** when the caller already knows exactly which document
family it means (which is always true here — it comes straight from the shelf's own
index, not from typing a search query), use it directly instead of re-searching for
it.

**Result after both fixes: 1 of 4**, not 4 of 4 — this remains a failing result
against the stated bar (needs 3 of 4), but it is now a measurement of the actual
approach rather than of a defect in how the test was run. The one success: for the
Sindh development-programme question, the walk correctly landed on the right page
for 2 of that publication's 15 editions (the two most recent). The other three
questions still found nothing in the top 5 for any of their editions. §4 is about
why.

## 4. Why in-document search still misses 3 of 4 trajectories, even now that the document is right

This is the part worth understanding, because it's the same underlying problem the
whole project has been running into for four nights, just showing up one level down.

Once the correct document is identified, searching inside it means searching a few
hundred pages instead of 1.2 million — which should be an easy problem. It mostly
isn't, for a specific, checkable reason: **this corpus doesn't state each year's
number once, in one table. It restates it many times, in prose, on many different
pages.** A single 500-page publication doesn't just have "Table 2.3: Cotton
Production" with the row of numbers — it also has paragraphs scattered through later
chapters, each one restating a single year's figure in a full sentence ("Cotton
production registered 10.03 million bales for the 2013-14 period...").

Measured directly on one real document: searching that single publication for
"cotton production" returns eight matching pages. The actual table is one of them —
and it ranks **sixth**, behind five prose restatements, because a word-frequency
search can't tell "the canonical table for this row" apart from "a sentence that
mentions the same two words." Widening the check from the top 1 result to the top 5
(the fix in §3) helps, but with eight or more competing pages inside a single
document, top 5 isn't always wide enough — and the pattern repeats across every one
of the 15 editions being walked, not just once.

This is the same failure mode documented earlier in the project at the scale of the
whole corpus (Night 3: the right page sits at rank 500–3,000 out of 1.2 million when
matched on words alone) — it just turns out the corpus's habit of restating every
number in prose operates *within* a document almost as much as it does *across*
documents. Picking the right book off the shelf cuts the haystack from 1.2 million
pages to a few hundred. It does not remove the haystack. The one question that did
succeed (Sindh) most likely had less of this restatement competing for its specific
row in its most recent editions — not evidence the mechanism is reliable, just that
it isn't guaranteed to fail every time.

The practical implication: the fix in §3 (a short, well-chosen search phrase, and
checking more than the top result) is necessary but not sufficient on its own.
What would actually close this gap is a way to tell "this is the table itself" apart
from "this mentions the table's subject" — which the shelf's own harvested table
captions (the "Table N.N: ..." lines already extracted in Stage 1) are well placed to
do, since they're a *label*, not a restatement, and the caption channel already
covers essentially all of this corpus's large statistical publications. That's not
built into `series` yet; the gate above shows what happens without it.

## 5. What Stage 3 does and doesn't tell you

**Solid:** the shelf is honest about absence, both when a year's edition genuinely
isn't held (11/11) and, as a control, when it is (14/17). That's a real result — every
earlier approach in this project scored 0 out of 3 on honest refusal, and this one
doesn't.

**Not solid:** picking the right document from a plain question (6/17, or 8/17 with
paraphrased retries) and, even once the document is right, landing on the right page
inside it for a multi-year question (1/4). Both numbers are well short of their bars,
and both point at the same root cause the whole project keeps finding: this corpus
repeats itself, at every scale, and matching on words alone can't tell a real answer
apart from a lookalike.

**Not run:** the paid, live-model battery. With document-finding at 6/17 and the
series walk at 1/4, a live session would mostly be asked to answer using a document
that doesn't contain the answer — that tests the model's behavior under a bad hand,
not the retrieval design. It was deliberately not run, and no stack was installed
in the test corpus at any point during this stage.
