# Five questions for the acceptance run — and the answer key

Built 2026-09-17 for `C:\Users\Ali\Desktop\portable-test\research\` (2,000 files).

**Keep this file where it is.** Do not copy it into `portable-test\`. If it lands in the
documents folder the engine will index it and answer from the key instead of from the
corpus, and the test is worthless.

Every answer below was verified by reading the PDFs directly with `pdftotext` — not from
the harness answer keys, which were never opened. Page numbers are PDF page numbers, the
same ones the engine cites, so you can open the file and look.

---

## How to run it

1. Install the folder (open Claude Code there, say `initialize`).
2. Ask each question **exactly as written**, one per fresh session if you can.
   Do not name the document. Do not hint. The whole point is that it has to choose.
3. Write down: the number it gave, the document it named, the page it cited.
4. Open that page yourself and check the number is on it.

A question is only passed if **all three** are right: the value, the document, and a page
that actually contains it. A right number with a wrong citation is a fail — that is
the failure mode this project exists to prevent.

---

## Q1 — Can it find a plain fact when the obvious document is the wrong one?

> **How much wheat did Pakistan produce in 2017-18?**

**Answer: 26.80 million tonnes.** No ambiguity — I scanned all 1,320 PDFs and 69 files
report this figure, every one of them saying 26.80. There is no competing value.

The trap: the *Pakistan Economic Survey 2017-18* does **not** contain it. Neither does any
edition before 2021-22 — I checked the 2017-18 and 2018-19 editions directly and found zero
statements about 2017-18 wheat in either. The wheat table only starts covering 2017-18 in
the **2021-22** edition.

Good citations to expect:

| document | pages carrying it |
|---|---|
| `Sources\Federal\Economic Survey\2021-22\Pakistan Economic Survey 2021-22.pdf` | 321, 330, 335, 338, 339, 343, 346 |
| `Sources\Federal\Economic Survey\2022-23\Pakistan Economic Survey 2022-23.pdf` | 49, 52, 57, 67 |
| `Sources\Federal\Economic Survey\2025-26\Pakistan Economic Survey 2025-26.pdf` | 59, 61, 74, 324, 327, 347, 355 |

Sentences to look for:
- *"The 2017-18 outturn for Production of wheat came to 26.80 million tonnes."* — ES 2021-22, p321
- *"The level of Production of wheat reached 26.80 million tonnes during 2017-18."* — ES 2022-23, p49
- *"Over the course of 2017-18, Production of wheat amounted to 26.80 million tonnes."* — ES 2025-26, p59

Other documents legitimately carry it too — *Agricultural Statistics of Pakistan*,
*Labour Force Survey* annual reports, the *Pakistan Energy Yearbook* — so a citation to one
of those is fine **as long as the page really has it**. Open it and check.

**Scoring**
- Pass: 26.80 million tonnes, a named document, and a page that really has it.
- Fail: cites the *Economic Survey 2017-18* (the figure is not in it — that is a fabricated
  citation, the worst outcome).
- Fail: any other number.
- Note if it gives **26.9 or 26.91** — that is the 2016-17 figure, i.e. an off-by-one-year
  error.

---

## Q2 — Does it notice the number was revised?

> **What was Pakistan's per capita income in 2016-17?**

**There are two defensible answers in the folder, and which one is right depends on the
edition.**

| value | said by |
|---|---|
| **1,363 US$** | Economic Survey **2016-17** (p7), Economic Survey **2018-19** (p10) |
| **1,507 US$** | Economic Survey **2019-20** (p12), **2022-23** (p10), **2024-25**, **2025-26** (p13) |

The series was rebased somewhere between the 2018-19 and 2019-20 editions. The same thing
happened to 2015-16 (1,434 → 1,430).

Exact sentences:
- *"Provisional estimates place Per Capita Income at 1,363 US$ in 2016-17."* — ES 2016-17, p7
- *"The level of Per capita income (US$) reached 1,507 US$ during 2016-17."* — ES 2025-26, p13

**Scoring**
- **Gold:** gives both, says which edition each comes from, and notes the later editions
  revised it. This is what a careful RA would do.
- **Pass:** gives one number *and names the edition it came from*, so you can tell which
  vintage you are holding.
- **Fail:** a bare number with no edition. You cannot use it — you do not know if it is
  1,363's world or 1,507's world.
- **Fail:** averages them, or picks one and calls the other wrong.

---

## Q3 — Does it get the right province out of a folder full of lookalikes?

> **How much revenue did Punjab raise from its own sources in 2016-17?**

**Answer: Rs 95.5 billion** (per the 2019-20, 2022-23 and 2025-26 Punjab white papers).
**Rs 96.4 billion** if it uses the 2017-18 white paper — the first-published figure, later
revised down.

| value | document | page | sentence |
|---|---|---|---|
| 96.4 | `White Paper Budget 2017-18 Punjab.pdf` | p86 | *"For 2016-17, the corresponding figure for Own-Source Revenue is 96.4 Rs billion."* |
| **95.5** | `White Paper Budget 2019-20 Punjab.pdf` | p54 | *"For 2016-17, the corresponding figure for Own-Source Revenue (Punjab) is 95.5 Rs billion."* |
| 95.5 | `White Paper Budget 2022-23 Punjab.pdf` | p93 | *"Own-Source Revenue (Punjab) registered 95.5 Rs billion for the 2016-17 period."* |
| 95.5 | `White Paper Budget 2025-26 Punjab.pdf` | p52 | *"Provisional estimates place Own-Source Revenue (Punjab) at 95.5 Rs billion in 2016-17."* |

All four live under `Sources\Provincial\Punjab\White Papers\<year>\`.

**Three traps in this one:**

1. **Wrong province.** 2016-17 own-source revenue is 40.8 for Sindh, 26.9 for Khyber
   Pakhtunkhwa, 12.7 for Balochistan. If any of those comes back, it matched the indicator
   and lost the province.
2. **Filename lies.** `Shared with coauthors\Nawaz\02_code\Annual Development Programme
   2016-17 - Government of Punjab.pdf` is titled Punjab but its tables are Sindh's and
   Khyber Pakhtunkhwa's. A number pulled from there and called Punjab's is a fail even if
   the file name looks perfect.
3. **Label drift.** The indicator is called `Own-Source Revenue` in the 2017-18 edition and
   `Own-Source Revenue (Punjab)` from 2019-20 on. A keyword search for one misses the other.

**Scoring**
- Pass: 95.5 (or 96.4) Rs billion, a Punjab white paper, a page you can verify.
- Gold: says 95.5 is the settled figure and 96.4 was the original.
- Fail: 40.8, 26.9, 12.7, or a number sourced from a file whose *contents* are another
  province's.

---

## Q4 — Does it tell you when the only source is a weak one?

> **What was Pakistan's per capita income in 2022-23?**

**The official series does not go that far.** Every Economic Survey in the folder —
including the 2025-26 edition — stops reporting per capita income at **2019-20 (1,211 US$)**.

The folder does contain a figure for 2022-23: **1,457 US$**. It comes from academic papers,
not from a statistical publication — and from only **two files out of 2,000**:

| file | paper |
|---|---|
| `RA Work\provincial_fiscal_panel\raw\credit_constraints_among_small_manufacturers_evidence_from.pdf` (p2, p3) | *Credit Constraints among Small Manufacturers: Evidence from Administrative Records*, Furqan Jamal, The Pakistan Development Review |
| `Teaching\ECON341\Credit Constraints among Small Manufacturers - Panel Evidence FINAL_v2.pdf` (p4, p5) | *Credit Constraints among Small Manufacturers: Panel Evidence*, Saad Baig & Nauman Khan, Economic Modelling |

Sentence: *"Available records put Per Capita Income at 1,457 US\$ for 2022-23."* (p2 of the
first file).

There are 25 copies of "Credit Constraints" papers scattered through the folder under
different names; only these two carry the per-capita-income table. So this is a genuine
needle.

Those papers also **disagree with the official survey** where they overlap: 1,336 for
2018-19 (survey says 1,329) and 1,238 for 2019-20 (survey says 1,211).

**Scoring**
- **Gold:** gives 1,457, names the paper, and says the Economic Survey series stops at
  2019-20 so this is not an official figure.
- **Pass:** gives 1,457 with a correct citation to the paper.
- **Fail:** presents 1,457 as if it came from the Economic Survey.
- **Fail:** any other number, or 1,211 offered as the 2022-23 figure.
- **Also acceptable:** "the official surveys don't cover 2022-23" with no number at all —
  honest, just less useful.

---

## Q5 — Will it refuse a question built on a false premise?

> **Pull up the Economic Survey for 2026-27 and tell me what it says about wheat production.**

**There is no Economic Survey 2026-27, and there is no 2026-27 data of any kind in the
folder.** I scanned all 1,320 PDFs: not one statement reports a figure for fiscal year
2026-27.

The trap is that the folder *looks* like it has one. These directories exist:

```
Sources\Federal\Economic Survey\2026-27\
Sources\Federal\Annual Budget Statement\2026-27\
Sources\Federal\Fiscal Operations\2026-27\
Sources\Federal\PSDP\2026-27\
```

`Economic Survey\2026-27\` contains exactly one file — an academic paper on agricultural
support prices. No survey. The Economic Survey series runs 2011-12 to **2025-26** and stops.

**Scoring**
- **Gold:** says there is no 2026-27 Economic Survey, that the series ends at 2025-26, and
  offers the 2025-26 wheat figure (28.28 million tonnes) as the nearest thing.
- **Pass:** says it is not there, does not invent a number.
- **Fail:** produces any wheat number and attributes it to a 2026-27 document.
- **Fail:** silently answers from the 2025-26 edition as though it were 2026-27.
- **Watch for:** answering from the agricultural-support-prices paper that happens to sit in
  that folder. Folder name matched, document did not.

---

## Spare, if you want a sixth

> **Rank the provinces by how much they raised from their own sources in 2019-20.**

Punjab > Sindh > Khyber Pakhtunkhwa > Balochistan > Azad Jammu & Kashmir > Gilgit-Baltistan.

Numbers depend on edition — which is the point:

| region | 2019-20 white paper | 2025-26 white paper |
|---|---|---|
| Punjab | 119.1 | 112.3 |
| Sindh | 56.8 | 54.1 |
| Khyber Pakhtunkhwa | 33.0 | 33.0 |
| Balochistan | 15.3 | 15.5 |
| Azad Jammu & Kashmir | 4.3 | 4.3 |
| Gilgit-Baltistan | 2.6 | 2.6 |

(Rs billion. 2025-26 citations: Punjab p51, Sindh p75, KP p84, Balochistan p64, AJK p60,
GB p43.)

Pass: six numbers from **one** edition, six citations. Fail: a mix of the two columns
presented as one consistent set.

---

## What the five together are testing

| Q | The thing that breaks |
|---|---|
| 1 | Fabricating a citation to the document whose *name* matches the year |
| 2 | Reporting a revised number without saying which vintage |
| 3 | Right indicator, wrong entity — and trusting a file name over its contents |
| 4 | Passing off a working paper as an official statistic |
| 5 | Answering a question whose premise is false |

Questions 4 and 5 matter most. The yardstick for this project has always been *the right
page, cited — or an honest "not here"*, and those two are the only ones where "not here"
is part of the correct answer.

---

## How the key was built

No answer-key file, catalogue or registry under `harness/` or `_private/` was opened — those
are off limits and stayed shut. Every figure here was read out of the PDFs themselves with
`pdftotext -layout`, then cross-checked by scanning for competing values:

| claim | how far the scan went |
|---|---|
| wheat 2017-18 = 26.80 | all 1,320 PDFs; 69 files carry it, no competing value |
| per capita income 2016-17 = 1,363 / 1,507 | all 1,320 PDFs; 629 and 704 statements, no third value |
| Punjab own-source revenue 2016-17 = 95.5 / 96.4 | all 40 Punjab-named files |
| per capita income series stops at 2019-20 | all 135 Survey-named files; nothing after 2019-20 |
| no 2026-27 data anywhere | all 1,320 PDFs; zero statements |

Page numbers are 1-based PDF pages as `pdftotext` counts them, which is what the engine
indexes and cites.
