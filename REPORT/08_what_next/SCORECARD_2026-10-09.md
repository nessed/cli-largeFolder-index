# Scorecard — Ali's acceptance run, reviewed 2026-10-09

The run happened on 2026-09-17 in `C:\Users\Ali\Desktop\Projects\Code\portable-test`
(the folder has since moved there from `Desktop\portable-test`). Three sessions, all
read-only questions against the installed shelf. Nine of the twelve questions were asked.
No engine or document was touched; the repo is still clean at `8d937cb`.

This file scores those nine answers against the two question files in this directory, and
records the two defects the review found.

---

## The headline

**The engine's reasoning is excellent and its page numbers are all wrong by one.**

On substance it scored Gold on eight of nine and found three things the answer key did not
know about. But every page number it emitted is **one less than the true page**. Under this
project's own yardstick — *the right page, cited* — that means every answer fails
verification as delivered, from a single off-by-one bug.

---

## F-23 — every cited page is one too low (BLOCKER)

The engine reports page *N* when the content is on page *N+1*. Verified against ten
citations drawn from six different answers and eight different documents:

| answer | document | cited | content actually on |
|---|---|---|---|
| Q1 wheat | ES 2020-21, Table A.43 "Wheat output" | p372 | **p373** |
| Q2 per capita | ES 2016-17 | p17 | **p18** |
| Q2 per capita | ES 2019-20 | p407 | **p408** |
| Q2 per capita | ES 2025-26 | p19 | **p20** |
| Q3 Punjab OSR | Punjab WP 2017-18 | p102 | **p103** |
| H1 PSDP | ES 2014-15 | p269 | **p270** |
| H1 PSDP | ES 2020-21 | p93 | **p94** |
| H6 Sindh OSR | Sindh WP 2025-26 | p89 | **p90** |
| H6 KP outlay | KP WP 2025-26 | p9 | **p10** |
| H6 Balochistan OSR | Balochistan WP 2025-26 | p76 | **p77** |
| H6 AJK OSR | AJK WP 2025-26 | p59 | **p60** |

In every case `cited + 1` is a page that genuinely contains the quoted sentence, and in
eight of the eleven the cited page does **not** contain it at all. Method: `pdftotext
-layout`, split on form feed, 1-based page index — the same counting the package's own
documentation promises ("page numbers are 1-based PDF pages as `pdftotext` counts them").

**The same offset shows up in page counts**, which is corroboration that this is one bug
and not eleven coincidences. In its H4 answer the engine reported the six
"Pakistan Economic Survey 2013-14" files as 344 / 43 / 42 / 50 / 46 / 38 pages. The true
counts are 345 / 44 / 43 / 51 / 47 / 39 — every one exactly one short.

**Diagnosis:** a 0-based page index is reaching the user-facing citation and the page-count
report, rather than being converted to the 1-based number a reader uses to open the file.

**Why it matters more than it looks.** Every gate this project has run scored citations with
the frozen v3 scorer, which checks a cited page against the pages the transcript shows as
`OPENED` — both sides of that comparison come from the same internal index, so an offset
applied to both cancels out and the scorer reports a clean pass. The offset is only visible
when a **human opens the PDF**, which is exactly what Ali's run did and what no gate ever
did. This is the same shape as the phase-11 finding: the harness measured the engine
against itself and never against the thing a real user does.

Do not fix this by changing the scorer. Fix the emitted citation, then re-run one live
answer and open the cited page by hand.

---

## F-24 — a false absence, asserted corpus-wide from one table

In H7 the engine told Ali:

> *"Sindh has no own-revenue figure before 2012-13 anywhere in the folder"*

and gave AJK's earliest year as 2012-13. Both are wrong.

| region | engine said series starts | actually starts |
|---|---|---|
| Sindh | 2012-13 (27.7) | **2010-11 (23.9)**, 2011-12 = 23.5 |
| AJK | 2012-13 (2.3) | **2010-11 (1.8)**, 2011-12 = 2.0 |

Verified in `White Paper Budget 2025-26 Sindh.pdf` — *"The 2010-11 outturn for Own-Source
Revenue came to 23.9 Rs billion"*, repeated in prose on many pages — and in
`White Paper Budget 2025-26 Azad Jammu & Kashmir.pdf` — *"Own-Source Revenue is reported at
1.8 Rs billion for 2010-11."* And it is not edition-specific: **every** Sindh white paper
(2013-14, 2015-16, 2017-18, 2019-20, 2022-23, 2025-26) carries 2010-11.

**How the error was made.** The engine cited Sindh WP 2019-20 p86, whose Table 3.1 prints
only the last eight columns, starting 2012-13. That citation is accurate about the table.
The failure is generalising a truncated table to "anywhere in the folder" without checking
the prose in the same document, or the 2025-26 edition it had already opened for other
figures in the same answer.

**It is load-bearing.** The engine's main recommendation was that Ali's usable window across
the four provinces is **2012-13 to 2019-20**. The correct window is **2010-11 to 2019-20** —
bounded by KP's series ending (which the engine got right) and not by Sindh's start. It cost
him two years of panel he actually has.

This is the project's yardstick failing in its less-discussed direction: not a fabricated
number, but a fabricated absence. The guard and the scorer both have no check for it.

---

## Scores

| Q | asked | verdict | note |
|---|---|---|---|
| Q1 wheat 2017-18 | yes | **Gold** | 26.80; flagged that the 2017-18 edition does not carry it, and that neighbouring years were revised. Cited ES 2020-21, an edition the key did not list — real, and legitimate. |
| Q2 per capita 2016-17 | yes | **Gold** | Both 1,363 and 1,507, each with its edition, and spotted that the two vintages point opposite directions on growth. |
| Q3 Punjab OSR 2016-17 | yes | **Gold** | 95.5 settled, 96.4 as first published, one compiler, one revision. Also volunteered that no 2016-17 Punjab edition exists. |
| Q4 per capita 2022-23 | yes | **Gold** | 1,457, sourced to an SBP EasyData extract and a WDI CSV, with the caveat that no publication in the folder prints it. **Better than the key** — which named two academic PDFs and missed the CSVs entirely, because the key's scan only covered PDFs. |
| Q5 Economic Survey 2026-27 | yes | **Gold** | Refused, listed the fifteen editions held, explained why a 2026-27 edition would not exist yet, and explicitly declined to substitute 2025-26. |
| H1 federal PSDP 2013-14 | yes | **Gold+** | Both figures, the conversion, a four-year ratio table showing a uniform ~18% wedge, and the correct conclusion that it is a **base change** (2005-06 vs 2015-16) rather than a data revision — a mechanism the key did not identify. Also found that 2013-14 has since dropped out of the published table entirely. |
| H2 Punjab vs Balochistan ADP | yes | **Gold** | Punjab, 8.2×, Rs 809bn gap, units flagged, and noted the trap would otherwise give Balochistan a hundredfold win. |
| H4 six "ES 2013-14" files | yes | **Gold** | Right file, reasons from contents, flagged the DO-NOT-CITE draft, and identified the "perturbed values" copy as genuinely altered (literacy 58.9 against 56.8) — which the key had not established, because the key's prose-only scan could not see it. |
| H6 own-revenue share, six regions | yes | **Gold** | KP 9.94 / Punjab 8.97 / Sindh 8.65 / GB 8.25 / AJK 8.10 / Balochistan 7.93 — identical to the key to two decimals. Added that the ranking is vintage-dependent and KP drops to fourth on the 2022-23 vintage, which the key had not spotted. |
| H7 open-ended scoping | yes | **Pass** | Outstanding on everything except F-24. Found `Sources\Provincial\SOURCE_SELECTION.md` is stale, that three Survey appendix tables carry no province in the title, and that table numbers move between editions — none of which the key knew. Marked down from Gold only because the headline recommendation rests on a false absence. |
| H3 per capita series + revisions | **no** | — | not yet asked |
| H5 Punjab OSR full run | **no** | — | not yet asked |
| spare: fiscal deficit series | **no** | — | not yet asked |

**Nine asked: eight Gold, one Pass, zero Fail on substance. Eleven of eleven citations one
page low.**

Four of the nine answers taught the answer key something it had got wrong or missed: the
CSV sources behind Q4, the base-change mechanism behind H1, the altered literacy figure in
H4, and the vintage-dependence of the H6 ranking. That is the first time an answer in this
project has been better-informed than the key it was scored against.

---

## What to do next, in order

1. **Fix F-23.** One off-by-one in the emitted citation and the page count. Add a test that
   asserts a cited page, opened with `pdftotext -f N -l N`, contains the quoted sentence —
   a check no existing test performs, because every existing test compares the index to
   itself.
2. **Ask the three unasked questions** (H3, H5, the fiscal-deficit spare). H5 is the one
   most likely to surface more of F-24's shape, because its correct answer depends on
   noticing that the 2022-23 Punjab edition stops early.
3. **Then F-24.** Harder: it needs the engine to distinguish "this table starts here" from
   "the series starts here" before asserting absence. Worth a finding in the guard, not a
   quick patch.
4. Still untested, unchanged from the 2026-09-18 handoff: a second machine, a cold cache,
   and a corpus from any generator other than this one.
