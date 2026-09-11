---
name: survey-appendix-restates-earlier-years
description: "In this corpus a spreadsheet/document number mismatch is usually a publication-vintage difference, not an extraction error; the convention is to keep both, not pick one."
metadata: 
  node_type: memory
  type: project
  originSessionId: 9e9d316d-bc6a-4d06-80e6-61ddd786db40
  modified: 2026-09-09T20:46:13.299Z
---

The cleaned CSVs under `RA Work/*/clean/` stamp one `source_doc` per file and re-extract every
fiscal year from a single recent publication, because the Economic Survey's statistical appendix
reprints earlier years with revisions. So a cleaned series is a *latest-vintage* restatement,
while the figure printed in a contemporaneous survey is a *first-publication* vintage. The two
legitimately differ.

`source_doc` is named by publication year, not fiscal year: `economic_survey_2026` = Pakistan
Economic Survey 2025-26; `economic_survey_2022` = 2021-22.

**Why:** The project's stated method (HEC NRPU 2019 proposal; `RA Work/tax_effort/PLAN.md`) is to
record the publication vintage alongside every observation "rather than by choosing a single
figure." Asking which of two vintages is correct is the wrong question by design.

**How to apply:** On a mismatch, identify the vintage on each side before treating either as an
error. Check units too — `RA Work/auto_sector_protection/notes/MEMO_auto_sector_protection.md`
records a chart that was wrong by three orders of magnitude from reading thousands as units.
Related: [[perturbed-values-pdfs-are-not-sources]].
