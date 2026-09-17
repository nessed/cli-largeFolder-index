# Seven harder questions for the acceptance run — and the answer key

Built 2026-09-17 for `C:\Users\Ali\Desktop\portable-test\research\` (2,000 files).
Companion to `ACCEPTANCE_QUESTIONS_2026-09-17.md`, which is the first, easier battery.

**Keep this file where it is.** Do not copy it into `portable-test\`. If it lands in the
documents folder the engine indexes it and answers from the key.

## Why this battery exists

The first five questions tested *retrieval integrity*: find a fact, handle a revision,
pick the right province, judge a source, refuse a false premise. Every one of them has a
single lookup at its centre.

A professor does not ask lookups. He asks for a series, a comparison, a table, a
judgement about which source to trust — questions where the engine has to open several
documents, notice that they disagree, reconcile units, and do arithmetic. These seven are
that. Each needs **at least two documents**, and five of the seven need arithmetic or an
explicit reconciliation before an answer exists at all.

They are harder in a specific way: on most of them the engine can produce a confident,
fluent, **wrong** answer by doing exactly what a keyword search would do.

---

## How to run it

1. Ask each question **exactly as written**. Do not name a document. Do not hint.
2. Record: every number it gave, every document it named, every page it cited.
3. Open one or two of the cited pages and check the number is there.
4. Score against the rubric. Most of these have a **Gold / Pass / Fail** ladder rather
   than a right answer, because a bare number is not a useful answer to any of them.

Budget roughly 10 minutes per question if you are checking pages properly.

---

## H1 — The same number, three names, two units, and a real disagreement

> **How much did the federal government spend on its Public Sector Development Programme in 2013-14?**

**This is the hardest question in the folder, and the one I would weight highest.**

There are **two irreconcilable answers**, and the split is by publication vintage:

| value | which documents say it | count |
|---|---|---|
| **414 Rs billion** | everything published **2015-16 or earlier** | 62 files |
| **349,274 Rs million** (= 349.3 Rs billion) | everything published **2016-17 or later** | 110 files |

Note they are not the same number in different units. 414 billion against 349.3 billion is
an 18 percent gap. Something was re-defined or re-based between the 2015-16 and 2016-17
publishing rounds, and no document in the folder explains it.

On top of that the indicator carries **three different labels**:

| label | editions |
|---|---|
| `Federal PSDP` | Economic Survey 2012-13, 2014-15, 2015-16 |
| `Public Sector Development Programme (Federal)` | Economic Survey 2016-17 through 2020-21 |
| `PSDP -- Federal` | Economic Survey 2021-22, 2024-25, 2025-26 |

A keyword search for any one of the three finds at most half the evidence.

Exact sentences, all verified:

| document | page | sentence |
|---|---|---|
| `Sources\Federal\Economic Survey\2012-13\Pakistan Economic Survey 2012-13.pdf` | 230 | *"Federal PSDP is reported at 414 Rs billion for 2013-14."* |
| `Sources\Federal\Economic Survey\2015-16\Pakistan Economic Survey 2015-16.pdf` | 117 | *"In 2013-14, Federal PSDP stood at 414 Rs billion."* |
| `Sources\Federal\PSDP\2013-14\PSDP 2013-14.pdf` | 10 | *"The 2013-14 outturn for Federal PSDP came to 414 Rs billion."* |
| `Sources\Federal\Economic Survey\2016-17\Pakistan Economic Survey 2016-17.pdf` | 213 | *"Provisional estimates place Public Sector Development Programme (Federal) at 349,274 Rs million in 2013-14."* |
| `Sources\Federal\PSDP\2016-17\PSDP 2016-17.pdf` | 7 | *"Public Sector Development Programme (Federal) is reported at 349,274 Rs million for 2013-14."* |
| `Sources\Federal\Economic Survey\2025-26\Pakistan Economic Survey 2025-26.pdf` | 218 | *"For 2013-14, the corresponding figure for PSDP -- Federal is 349,274 Rs million."* |

There is also a third value, **413 Rs billion**, in five academic working papers only. It is
nobody's official figure. Mentioning it is fine; leading with it is not.

**Scoring**

- **Gold:** gives both figures, converts 349,274 Rs million to about 349 Rs billion so they
  can be compared, says the newer series is the one to use, and says plainly that the two do
  **not** reconcile. Bonus if it notices the label changed.
- **Pass:** gives one figure with a named document and a real page, and flags that other
  documents in the folder disagree.
- **Fail:** a bare number with no vintage.
- **Fail:** reports `349,274` as billions. That is a 349-trillion-rupee PSDP and it should
  be obvious. Watch for this one specifically — it is the most likely silent error.
- **Fail:** claims 414 and 349,274 are the same number in different units.

---

## H2 — Two documents, two units, and the comparison flips if you skip the conversion

> **Which government budgets more for its annual development programme in 2025-26, Punjab or Balochistan, and by how much?**

**Answer: Punjab, by roughly eight to one.**

- Punjab: **921.1 Rs billion** — `Sources\Provincial\Punjab\White Papers\2025-26\White Paper Budget 2025-26 Punjab.pdf` p29
  *"The 2025-26 outturn for Annual Development Programme (Punjab) came to 921.1 Rs billion."*
- Balochistan: **112,240.0 Rs million** — `Sources\Provincial\Balochistan\White Papers\2025-26\White Paper Budget 2025-26 Balochistan.pdf` p43
  *"2025-26 data put Annual Development Programme (Balochistan) at 112,240.0 Rs million."*

112,240 Rs million is **112.2 Rs billion**. So Punjab is about **8.2 times** Balochistan, a
gap of roughly **809 Rs billion**.

**The trap.** Balochistan's 2025-26 white paper is the **only** cell in the entire
six-region by four-indicator by six-edition grid that reports in **Rs million** instead of
Rs billion. I checked all of them. Every other regional figure in the folder, including
Balochistan's own earlier editions, is in Rs billion — the 2022-23 Balochistan white paper
gives the same series rounded to whole billions (2019-20 = 36, against 35,387 Rs million in
the 2025-26 edition, which is the same number).

So the naive comparison reads 112,240 against 921.1 and concludes Balochistan spends more.
It does not. It spends an eighth as much.

**Scoring**

- **Gold:** Punjab, both figures quoted with their units, the conversion shown, and a ratio
  or difference.
- **Pass:** Punjab, both figures, units handled correctly, no arithmetic.
- **Fail:** **Balochistan.** This is the whole question.
- **Fail:** quotes 112,240 without a unit, or silently calls it billions.
- Note if it uses **941.8** (Punjab) or **134.4** (Balochistan): those come from academic
  working papers, not the white papers. The conclusion survives — Punjab is still about
  seven times bigger — but the citation is to the wrong kind of document.

---

## H3 — Build a series across ten editions and spot what moved

> **Trace Pakistan's per capita income year by year for as long as the folder covers it, and tell me whether any of those figures were ever revised.**

**The series, per the latest edition (Economic Survey 2025-26):**

| year | US$ | | year | US$ |
|---|---|---|---|---|
| 2010-11 | 1,151 | | 2015-16 | **1,430** |
| 2011-12 | 1,239 | | 2016-17 | **1,507** |
| 2012-13 | 1,260 | | 2017-18 | 1,558 |
| 2013-14 | 1,311 | | 2018-19 | 1,329 |
| 2014-15 | 1,417 | | 2019-20 | 1,211 |

**It stops at 2019-20.** Every Economic Survey in the folder, including the 2025-26 edition,
ends this table at 2019-20. There is no official per capita income for 2020-21 onwards.

**Exactly two figures were revised**, both between the 2018-19 and 2019-20 editions:

| year | old | new |
|---|---|---|
| 2015-16 | 1,434 | **1,430** |
| 2016-17 | 1,363 | **1,507** |

- *"According to the latest compilation, Per Capita Income was 1,434 US$ in 2015-16."* — ES 2018-19 p9
- *"Over the course of 2015-16, Per capita income (US$) amounted to 1,430 US$."* — ES 2019-20 p12
- *"Per Capita Income was recorded at 1,363 US$ in 2016-17."* — ES 2018-19 p10
- *"Per capita income (US$) registered 1,507 US$ for the 2016-17 period."* — ES 2019-20 p12

The other eight years are **identical in every edition** — 2010-11 is 1,151 in the 2012-13
edition and 1,151 in the 2025-26 edition. So "the series was rebased" is too strong; two
numbers moved and eight did not.

The label also changed: `Per Capita Income` up to the 2018-19 edition,
`Per capita income (US$)` from 2019-20 on.

**Scoring**

- **Gold:** the full ten-year series, says it ends at 2019-20, names both revisions with
  both values, and says the rest are unchanged.
- **Pass:** the series from one named edition, plus at least one revision spotted.
- **Fail:** silently splices old and new editions into one table — for instance 1,363 for
  2016-17 next to 1,558 for 2017-18. Those come from different vintages and the jump between
  them is an artefact.
- **Fail:** invents years after 2019-20.
- **Fail:** a series with no edition named. You cannot tell which vintage you are holding.

---

## H4 — Six files, one title, and only one worth citing

> **There are several files in this folder called "Pakistan Economic Survey 2013-14". Which one should I actually cite, and what are the others?**

**Cite:** `Sources\Federal\Economic Survey\2013-14\Pakistan Economic Survey 2013-14.pdf`

It is the only one of the six whose **internal front-page header matches its filename**, and
it is seven times longer than any other:

| file | pages | header says | indicators |
|---|---|---|---|
| **`Sources\Federal\Economic Survey\2013-14\...`** | **345** | **Fiscal Year 2013-14** | **62** |
| `Downloads\reports\adb\... - perturbed values.pdf` | 44 | Fiscal Year 2010-11 | 2 |
| `Downloads\reports\adb\... old tables.pdf` | 43 | Fiscal Year 2010-11 | few |
| `Downloads\reports\local think tanks\... DRAFT.pdf` | 51 | Fiscal Year 2010-11 | 19 |
| `Papers\ADP execution\replication\data\raw\... (2).pdf` | 39 | Fiscal Year **2015-16** | 3 |
| `Papers\Tax effort\replication\data\raw\... copy.pdf` | 47 | Fiscal Year 2010-11 | few |

Every decoy's own title page contradicts its filename. The `DRAFT` copy additionally carries
**"PRELIMINARY — DO NOT CITE"** on page 1.

The canonical file covers 2010-11 through 2023-24 across 62 indicators. The excerpts cover
four to seven years across two to nineteen indicators — so they are not just riskier, they
mostly do not contain what you would go looking for.

**Scoring**

- **Gold:** names the `Sources\Federal\Economic Survey\2013-14\` copy, gives a reason based
  on the **contents** (header matches, 345 pages, full indicator coverage) rather than on the
  folder name, and flags the do-not-cite draft.
- **Pass:** names the right file and says the others are short excerpts.
- **Fail:** picks a file because its path looks tidy, without opening it.
- **Fail:** says they are all copies of the same thing. They are not — five of the six are
  excerpts of a *different fiscal year*.

---

## H5 — Which single document can actually answer the question

> **I need Punjab's own-source revenue for every year from 2010-11 to 2025-26. Can this folder give me the full run, and where from?**

**Yes — from exactly one document.**
`Sources\Provincial\Punjab\White Papers\2025-26\White Paper Budget 2025-26 Punjab.pdf`,
table on pp. 51–67.

| year | Rs bn | | year | Rs bn |
|---|---|---|---|---|
| 2010-11 | 48.8 | | 2018-19 | 104.7 |
| 2011-12 | 53.1 | | 2019-20 | 112.3 |
| 2012-13 | 63.3 | | 2020-21 | 129.2 |
| 2013-14 | 66.3 | | 2021-22 | 171.5 |
| 2014-15 | 73.6 | | 2022-23 | 218.7 |
| 2015-16 | 82.8 | | 2023-24 | 278.9 |
| 2016-17 | 95.5 | | 2024-25 | 302.8 |
| 2017-18 | 99.3 | | 2025-26 | 349.0 |

- *"According to the latest compilation, Own-Source Revenue (Punjab) was 48.8 Rs billion in 2010-11."* — p51
- *"For 2025-26, the corresponding figure for Own-Source Revenue (Punjab) is 349.0 Rs billion."* — p52

**The reasoning this question is testing.** The folder holds six Punjab white papers —
2013-14, 2015-16, 2017-18, 2019-20, 2022-23, 2025-26. Five of them cannot answer it:

- 2013-14 and 2015-16 stop at 2013-14.
- 2017-18 stops at 2016-17.
- 2019-20 stops at 2019-20.
- **2022-23 also stops at 2019-20** — despite its title. This is the surprise. An engine
  that reasons "I need recent years, so I will take the second-newest edition" lands on a
  table that ends six years early.

Only the 2025-26 edition runs the full sixteen years.

**Scoring**

- **Gold:** the full sixteen-year series from the 2025-26 white paper, with pages, and says
  why the earlier editions cannot supply it.
- **Pass:** the full series from the right document.
- **Fail:** stitches years together from several editions without saying so. The joins are
  real: 2012-13 is 62.9 in the 2015-16 edition and 63.3 from 2017-18 on; 2013-14 is 68.3
  then 66.3; 2016-17 is 96.4 then 95.5; 2018-19 is 103.8 then 104.7; 2019-20 is 119.1 then
  112.3. A spliced series has five invisible seams in it.
- **Fail:** says the folder cannot cover 2020-21 onwards. It can.

---

## H6 — Twelve numbers, six divisions, six documents

> **For 2019-20, work out what share of each region's total budget came from its own revenue, and rank them.**

**Answer, all from the 2025-26 white papers:**

| region | own-source rev. | total outlay | share | pages |
|---|---|---|---|---|
| **Khyber Pakhtunkhwa** | 33.0 | 332.0 | **9.9%** | OSR p84, outlay p8 |
| **Punjab** | 112.3 | 1,252.0 | **9.0%** | OSR p51, outlay p10 |
| **Sindh** | 54.1 | 625.7 | **8.6%** | OSR p75, outlay p14 |
| **Gilgit-Baltistan** | 2.6 | 31.5 | **8.3%** | OSR p43, outlay p12 |
| **Azad Jammu & Kashmir** | 4.3 | 53.1 | **8.1%** | OSR p60, outlay p12 |
| **Balochistan** | 15.5 | 195.5 | **7.9%** | OSR p64, outlay p9 |

(Rs billion. Each region's figures come from
`Sources\Provincial\<region>\White Papers\2025-26\White Paper Budget 2025-26 <region>.pdf`.)

Everything sits between 7.9% and 9.9%, so the headline is that **they are all much alike** —
no region funds much more than a tenth of itself. KP top and Balochistan bottom are the only
two positions that are comfortably separated; the middle four are within 0.9 points and
GB and AJK are 0.2 apart.

**If it uses the 2019-20 editions instead**, that is also defensible, and the answer moves:
Punjab 119.1 / 1,277.0 = 9.3%, Sindh 56.8, Balochistan 15.3. What is **not** defensible is
mixing the two.

**Scoring**

- **Gold:** six ratios, twelve source numbers, six documents cited, one consistent edition,
  and a sentence saying the regions are close rather than presenting a dramatic league table.
- **Pass:** six ratios from one edition with citations, KP at the top and Balochistan at the
  bottom, even if the middle order wobbles.
- **Fail:** mixes editions — for instance Punjab's 119.1 (2019-20 edition) against Sindh's
  54.1 (2025-26 edition).
- **Fail:** ranks by own-source revenue in rupees instead of by share. That is a different
  question and gives Punjab first by a mile.
- **Fail:** any region missing, with no statement that it is missing.

---

## H7 — The open-ended one

> **I'm writing a short section on how much of their own money Pakistan's provinces raise, from 2010-11 onwards. What can this folder give me, which documents should I use, and what should I watch out for?**

No single right answer. This is the closest thing here to what your professor will actually
type, and it is scored on judgement, not on a number.

**What a good answer contains:**

1. **The right shelf.** Six regions times six editions of white papers under
   `Sources\Provincial\<region>\White Papers\<year>\`, 2013-14 through 2025-26.
2. **The right edition.** The 2025-26 white papers, because only they run past 2019-20 —
   and Punjab's 2025-26 edition is the only one reaching 2025-26 itself. Coverage of the
   later years is uneven: KP's own-source table stops at 2019-20 even in the 2025-26
   edition, Sindh's at 2021-22, Balochistan's and GB's at 2023-24.
3. **At least one real warning.** Any of: figures get revised between editions (Punjab
   2019-20 moved 119.1 to 112.3, Sindh 56.8 to 54.1); the indicator is named three different
   ways (`Own-Source Revenue`, `Own-Source Revenue (Punjab)`, `Punjab -- Own-Source
   Revenue`); Balochistan's 2025-26 white paper reports its development programme in Rs
   million while everyone else uses Rs billion; there are about a hundred lookalike
   white-paper files outside `Sources\` with names like *DRAFT*, *rebased*, *old tables*,
   *perturbed values*.
4. **Honesty about the gaps.** There is no white paper for 2011-12, 2012-13, 2014-15,
   2016-17, 2018-19, 2020-21, 2021-22, 2023-24 or 2024-25. The editions are every other year.

**Scoring**

- **Gold:** names the family and the specific edition to use, gives at least two of the four
  warnings, and says what is *not* available.
- **Pass:** points at the white papers, names real files, offers one caveat.
- **Fail:** recommends a document that does not exist, or a decoy from `Downloads\` or
  `archive\` as the primary source.
- **Fail:** answers as if the folder covers every year.
- **Fail:** produces a confident essay with no file names in it at all.

---

## Spare, if you want an eighth

> **What has Pakistan's fiscal deficit been as a share of GDP, for as many years as the folder covers?**

Per the Economic Survey 2025-26 (pp. 217–239), 2010-11 through 2025-26:

`5.2, 6.0, 5.7, 5.8, 6.1, 5.9, 6.9, 7.1, 7.1, 6.8, 6.8, 7.1, 7.7, 6.8, 8.0, 6.2`

Three labels again — `Fiscal Deficit` (editions 2013-14 to 2019-20),
`Overall fiscal deficit` (2021-22, 2022-23), `Budget deficit (% of GDP)` (2025-26) — and two
revisions: 2015-16 went 5.8 to 5.9, and 2021-22 went 7.4 to 7.1. The table is absent
entirely from the 2011-12, 2012-13, 2014-15, 2016-17, 2020-21, 2023-24 and 2024-25 editions,
so "which edition do I open" is itself part of the work.

---

## What the seven together are testing

| Q | The thing that breaks |
|---|---|
| H1 | Two official series that genuinely disagree, under three names and two units |
| H2 | A unit conversion that reverses the answer |
| H3 | Assembling a series across ten editions without splicing vintages |
| H4 | Choosing a document by its contents rather than its filename |
| H5 | Knowing which edition can answer the question at all |
| H6 | Twelve retrievals, six divisions, one consistent vintage |
| H7 | Judgement: what exists, what to use, what to warn about |

H1 and H2 are the two to watch. Both have a fluent, confident wrong answer sitting right
where a keyword search lands, and on H2 the wrong answer is the *opposite* of the truth.

---

## How the key was built

No answer-key file, catalogue or registry under `harness/` or `_private/` was opened — those
stayed shut. Every figure was extracted from the PDFs with `pdftotext -layout`, page by page,
and cross-checked against the whole corpus for competing values.

Scan coverage: all **1,320 PDFs**, yielding **1,654,027** anchored statements binding an
indicator, a fiscal year, a value, a unit and a 1-based page number.

| claim | how far the check went |
|---|---|
| PSDP 2013-14 splits 414 / 349,274 | all 1,320 PDFs; 62 files against 110 files, plus 5 papers at 413 |
| Balochistan ADP is the only Rs-million cell | all 6 regions, 4 indicators, 6 editions |
| per capita income revised in exactly two years | all 10 Economic Survey editions carrying the table |
| six "Economic Survey 2013-14" files, one canonical | filename search corpus-wide, headers read from page 1 |
| only the 2025-26 Punjab white paper spans 2010-11 to 2025-26 | all 6 Punjab editions |
| 2019-20 outlay shares for six regions | all 6 regions, 2019-20 and 2025-26 editions |

Page numbers are 1-based PDF pages as `pdftotext` counts them, which is what the engine
indexes and cites.
