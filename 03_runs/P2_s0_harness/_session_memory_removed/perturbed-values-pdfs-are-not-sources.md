---
name: perturbed-values-pdfs-are-not-sources
description: "Corpus PDFs with \"- perturbed values\" in the filename hold deliberately altered numbers and must never be cited as sources; canonical copies live under Sources/."
metadata: 
  node_type: memory
  type: project
  originSessionId: 9e9d316d-bc6a-4d06-80e6-61ddd786db40
  modified: 2026-09-09T20:46:05.765Z
---

In `C:\Users\Ali\Desktop\harness\corpus_500`, many PDFs are duplicated with `- perturbed values`
in the filename (e.g. `Pakistan Economic Survey 2016-17 - perturbed values.pdf` under
`archive/`, `Downloads/`, `Grants/`, `Papers/*/replication/data/raw/`). These carry altered
figures. The canonical, citable copies are the unsuffixed ones under
`Sources/Federal/Economic Survey/<fiscal-year>/`.

**Why:** This is not written down in any CLAUDE.md or README in the corpus, and the perturbed
copies sit in the same folders as working data, so a reconciliation can silently be run against
a doctored document.

**How to apply:** When resolving a number-vs-number discrepancy, first confirm which physical file
each side came from, and re-source anything traced to a `- perturbed values` copy from
`Sources/`. Related: [[survey-appendix-restates-earlier-years]].
