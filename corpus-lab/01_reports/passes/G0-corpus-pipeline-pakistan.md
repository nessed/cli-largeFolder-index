# Building a Reliable Government-Statistics Corpus + Report Pipeline in Pakistan: What Exists, What Works, and What Your Real Problem Is

## TL;DR
- Your four symptoms are really **two** underlying problems: (1) the agent has no *machine-checkable model of what is true* about your data (identity, state, vintage), and (2) the agent's retrieval over a growing file tree silently degrades. Problem 1 is load-bearing — until "per capita income," "this month's inflation," and "the value as published on date X" each resolve to exactly one addressable cell with a defined identity, no amount of retrieval fixing will stop the confident-but-wrong sentences.
- Your working assumption is **mostly right**: verification must be code-and-data, not a second model. The strongest production evidence (Statistics Netherlands' `validate`, ALFRED vintages, semantic layers, literate reporting) is all deterministic. Model-based cross-checking fails in correlated ways, which is exactly what you observed and what the numerical-claim-verification literature (best QuanTemp baseline of 58.32 macro-F1, and CheckThat! 2025 systems only ~0.57) confirms. But one model-shaped thing does work: **agentic search + subagents with isolated context**, which is Anthropic's own published fix for symptom 1.
- The highest-leverage build is **not more tooling** — it is to stop the agent browsing files and make it query a **Postgres + a metric/metadata catalog** where series identity, release state, and vintage are first-class columns, and to generate the report with **literate programming (Quarto)** so no number can be typed by hand. Adopt `validate`-style rule checking, a bitemporal schema, and a release calendar table. Most named "products" in this space are either enterprise-heavy or research artifacts unsuitable for a 1–3 person team; I say so per item below.

## Key Findings

### Your problem has two load-bearing cores, not four symptoms
1. **Symptom 1 (retrieval collapse)** is a genuine, separate engineering problem — and it is well-documented, not unique to you.
2. **Symptoms 2 and 3 (nonexistent/wrong datapoints; conceptual imprecision) collapse into one problem**: the absence of a machine-enforced *identity and state model* for every series. "This month's inflation doesn't exist yet" and "per capita income is five different series" are the same failure — a word in prose is not bound to one addressable, state-tagged cell.
3. **Symptom 4 (crawl freshness)** is a specialization of that same identity/state problem — it is "what is the transaction-time state of this cell relative to upstream."

So: **one retrieval problem, one identity/state problem.** The identity/state problem is load-bearing. If you fix retrieval but not identity, the agent retrieves the wrong-but-real series and still writes an unfalsifiable sentence. If you fix identity but not retrieval, the agent writes correct sentences about the subset of the corpus it can still see. But identity is the one that makes the errors *invisible and unfalsifiable*, which is what makes them dangerous, so build it first.

### Testing your assumption: code-and-data vs model-based verification
- **Evidence for code-and-data (strong):** Statistics Netherlands (CBS) has run rule-based validation of official statistics in production for years via the R `validate` package — validation rules as first-class, versionable objects, confronted against data, funded partly by an EU grant (88287–NL-VALIDATION). ALFRED at the St. Louis Fed has preserved data *vintages* deterministically since 2006. Central banks and the AEA generate reports where prose numbers come from code, not typing.
- **Evidence against model-based verification (strong):** The best published baseline on QuanTemp, the real-world numerical-claim-verification benchmark of 15,514 claims (Venktesh et al., SIGIR 2024), reaches only 58.32 macro-F1; subsequent CheckThat! 2025 systems reached only ~0.57 macro-F1, confirming the ceiling. Text-to-SQL on the BIRD benchmark tops out at published SOTA of 71.83% execution accuracy (Snowflake Arctic-Text2SQL-R1-32B, May 2025; the earlier CHASE-SQL reached 73.01% at ICLR 2025) — and a 2025 FLEX-metric analysis found BIRD's own execution-accuracy scoring agrees with human experts only 62% of the time, with "nearly 4 in 10 judgments … wrong, mostly false negatives." A model checking a model is two unreliable systems, and they fail in correlated ways — which you already observed.
- **The one model-shaped thing that works:** Anthropic reports that agentic search (grep/glob/read over the filesystem, no vector index) outperformed their own RAG+vector-DB implementation for Claude Code, and that **subagents with isolated context windows** materially improved their multi-agent research system. This is model-based, but it is architecture, not a second model grading the first. Use it for symptom 1.

---

## Details: candidates by the specific part of your problem they address

### A. Series identity — making "per capita income" resolve to one series

**Semantic layer / metric store (dbt MetricFlow / dbt Semantic Layer)** — *addresses symptom 3 directly.*
- **What:** Define each metric once in YAML (measures, dimensions, joins, grain), and every consumer queries the *metric*, not the table; MetricFlow compiles to SQL. This is the mechanism that makes "per capita income" a single defined object with one definition rather than five defensible sentences.
- **Maturity:** MetricFlow is Apache-2.0, maintained by dbt Labs, installable from PyPI, works with Postgres in dbt Core. Actively developed; part of the Open Semantic Interchange initiative.
- **Cost for 1–3 people:** Moderate — you already run Postgres. Expect a few engineer-days to stand up dbt Core + MetricFlow and encode your first ~20 contested metrics; ongoing cost is one PR per metric definition.
- **How it fails / what it doesn't do:** It does not *extract* data, does not manage vintages, and does not know release state. It governs definitions only. MetricFlow's richest features are tuned to cloud warehouses (Snowflake/BigQuery/Databricks); Postgres is supported in dbt Core but is a second-class citizen for some features. It will not stop the agent from *choosing* the wrong metric unless the metric names are unambiguous and the agent is forced to query through it.
- **Link:** https://github.com/dbt-labs/metricflow

**SDMX 3.0 / SDMX-ML / `sdmx1` (khaeru) and pandaSDMX (Python)** — *addresses symptom 3, the statistical-standards way.*
- **What:** SDMX is the ISO 17369 standard for statistical data + metadata exchange; Data Structure Definitions (DSDs) and code lists give every series an unambiguous identity. `sdmx1` is the maintained Python library (fork of pandaSDMX); it reads data from 20+ providers (World Bank, ECB, Eurostat, BIS, ILO, OECD, UN).
- **Maturity:** `sdmx1` is actively maintained (releases through 2025; v2.21.0 dated 2025-01-13). The original pandaSDMX (dr-leo) is effectively superseded — it implements SDMX 2.1 only. Neither fully implements SDMX 3.0/3.1 yet (open issues track it as of Aug 2025).
- **Cost:** High if you try to *model your whole corpus in SDMX* — the information model is famously complex. Low-to-moderate if you only use it to *consume* World Bank/IMF Pakistan series and to borrow its code-list discipline for your own DSDs.
- **How it fails:** SDMX is heavy; building DSDs for hundreds of PBS tables by hand is a multi-month undertaking that a 3-person team should not attempt wholesale. There is no Pakistani SDMX endpoint to consume (see section L). Use it as a *design vocabulary* for identity, not as a full implementation target.
- **Link:** https://sdmx1.readthedocs.io/

**Verdict on A:** Build a semantic/metric layer (dbt MetricFlow, or even a hand-rolled Postgres view catalog with a `metrics` registry table) as the load-bearing fix. Borrow SDMX/DDI concepts (code lists, DSDs) for your identity columns; do not adopt full SDMX.

### B. Vintage / point-in-time / revision management — "what was believed on date X"

**ALFRED (Archival FRED) + `fredapi`** — *addresses symptom 2 (wrong-value) and symptom 4.*
- **What:** ALFRED stores every *vintage* of a series — the value as it was published on each historical date, with `realtime_start`/`realtime_end`. This is the canonical reference implementation of the concept you need. `fredapi` (Python) exposes `get_series_vintage_dates` etc.
- **Maturity:** Production since 2006; 350,000+ series. `fredapi` is a mature community wrapper.
- **Cost:** You are not adopting ALFRED; you are copying its *data model* into your own Postgres. That's the work.
- **How it fails:** ALFRED itself has no Pakistani data. It's a model to imitate, not a service to use.
- **Link:** https://alfred.stlouisfed.org/

**Bitemporal Postgres: `temporal_tables` extension, `pg_bitemporal`, and native SQL:2011 temporal tables (PG 18/19)** — *the mechanism for storing vintages.*
- **What:** Two time axes — *valid time* (which period the figure describes) and *transaction time* (when your store believed it). This is exactly "this number was published on date X, revised on date Y." `temporal_tables` (PGXN) automates system-period history tables via triggers. `pg_bitemporal` (scalegenius, since 2015) does full bitemporal with `EXCLUDE USING gist` constraints. PostgreSQL 18/19 are adding native application-time temporal tables (`WITHOUT OVERLAPS`, `PERIOD`), though with limitations (temporal FKs only `NO ACTION`).
- **Maturity:** `temporal_tables` works but is lightly maintained (a well-known Clark Dave tutorial underpins most usage; the original extension is old). `pg_bitemporal` is niche. Native temporal support is the future but only partially landed and not yet in a version you'd deploy for production today without care.
- **Cost:** Moderate. The cheapest robust option for a small team is often *not* an extension: model it explicitly with `valid_from/valid_to` and `published_at/superseded_at` columns plus a uniqueness/exclusion constraint, and never `UPDATE` in place — only insert new vintages. A few engineer-days plus discipline.
- **How it fails:** `temporal_tables` triggers add write overhead and the history table grows unbounded (you prune manually). Bitemporal queries are genuinely hard to write and reason about; your agent will get them wrong unless you wrap them in views/functions. Native PG temporal is incomplete.
- **Links:** https://pgxn.org/dist/temporal_tables/ ; https://github.com/scalegenius/pg_bitemporal

**Verdict on B:** Model bitemporality explicitly in your schema (append-only vintages). Do not depend on an extension. This is what turns "the agent got a value wrong" into a bounded, checkable question: *which vintage did you cite?*

### C. Release-state awareness — "the figure doesn't exist yet"

**IMF SDDS/e-GDDS Advance Release Calendar** — *addresses the confident-nonexistent-datapoint failure directly.*
- **What:** IMF data standards *require* subscribers to publish an Advance Release Calendar (ARC) with release dates for the current month plus at least the next three, per data category. Pakistan participates in **e-GDDS** (via the IMF DSBB), which is the lower tier — the one that supports a National Summary Data Page but does *not* impose SDDS's strict ARC discipline.
- **Maturity:** Production; the DSBB is queryable per country.
- **Cost:** Low to *consume*: you build a `release_calendar` table (series, expected_release_date, actual_release_date, status) and refuse to let the agent state a figure whose `actual_release_date` is null. This single table + a guard is the cheapest, highest-value fix for symptom 2's "nonexistent datapoint" half.
- **How it fails:** Pakistan is e-GDDS, not SDDS, so upstream calendars are less rigorous/machine-readable than for SDDS countries. You will likely have to maintain the calendar yourself from PBS/SBP practice. There is no clean ICS/SDMX calendar feed to rely on.
- **Link:** https://dsbb.imf.org/egdds/country/PAK/category

**Verdict on C:** A release-state column/table is non-negotiable and cheap. It is the deterministic answer to "this figure hasn't been published." Treat "does this cell exist and is it released?" as a query, never an inference.

### D. PDF table extraction + validation

**Docling (IBM Research)** — *best current open-source extractor; addresses extraction-quality/provenance.*
- **What:** Open-source (Apache-2.0) document converter with a deep-learning layout model (DocLayNet-trained) and TableFormer table-structure model; outputs structured JSON preserving hierarchy; has an MCP server (`docling-mcp`). Granite-Docling 258M VLM released 2025-09-17.
- **Maturity:** Very active (IBM Research, multiple repos, 2025 releases). IBM's published table-extraction accuracy is ~97.9% on their benchmark; an independent test reproduced ~97.9% vs Unstructured 93.4% (hi-res) and Marker 91.7%. Used in RAG/agentic pipelines in production.
- **Cost:** Low-moderate to stand up; higher if you need GPU for throughput at corpus scale.
- **How it fails:** ~97.9% means ~2% of cells wrong — for a national statistics corpus that is *thousands* of wrong numbers. No extractor is trustworthy without a validation gate (section E). Borderless/whitespace-aligned tables and tables spanning page breaks are the common failure classes. Chart extraction is "coming soon." (Note: the 97.9% figure is IBM-published/vendor-reported; independently reproduced once, but not broadly audited.)
- **Link:** https://github.com/docling-project/docling

**Camelot / pdfplumber / Tabula / Marker / Unstructured / LlamaParse / Textract / Document AI / Azure Document Intelligence** — *the rest of the field.*
- **What/verdict, blunt:** `pdfplumber` remains the workhorse for well-behaved digital PDFs and precise cell geometry (mature, widely used). Camelot is useful for ruled tables but has historically had slow/uneven maintenance — verify last release before depending on it (I could not confirm its 2025–2026 maintenance status within budget). Marker and Unstructured are solid but scored below Docling on complex tables in independent tests. LlamaParse is fast (~6s regardless of size) but is a paid cloud API. Amazon Textract / Google Document AI / Azure Document Intelligence are mature managed services with per-page costs and data-egress implications — relevant if PBS scans are image-only, but you send government PDFs to a US cloud.
- **How they fail:** All are probabilistic on complex tables; none tell you *when they failed* — that is your validation layer's job, not the extractor's.

**Verdict on D:** Docling as primary, pdfplumber for geometry-precise digital tables, a managed OCR service only for image-only scans. **The extractor choice matters less than the validation gate after it.**

### E. Deterministic data validation (code, not models) — the core of your verification layer

**R `validate` + the CBS data-cleaning ecosystem (`validatetools`, `errorlocate`, `dcmodify`, `simputation`)** — *the single best-matched body of work to your problem.*
- **What:** Statistics Netherlands' `validate` lets you declare validation rules (per-field, in-record, cross-record, cross-dataset) as first-class, versionable objects, confront data with them, and summarize/visualize failures. It even supports rules implied by an SDMX DSD. There is a published *Data Validation Cookbook* and a JSS paper (van der Loo & de Jonge). This is rule-based validation of official statistics, in production at a national statistical office, which is precisely your use case.
- **Maturity:** Actively maintained (CRAN updates through July 2025; package manual dated 2025-07-22); institutionally backed by CBS; EU-funded. The broader ESS "Methodology for data validation" handbook and validation-levels framework sit behind it.
- **Cost:** Low-moderate. If your stack is Python, the cost is either running R for this piece or porting the *rule discipline* to Pandera/Great Expectations. The concepts transfer; the maturity and official-statistics fit are unmatched.
- **How it fails:** It's R. Cross-dataset rules need a "contract" on variable names. It validates data, not prose.
- **Link:** https://github.com/data-cleaning/validate

**Pandera vs Great Expectations vs Soda Core (Python)** — *the Python-native options.*
- **Pandera:** Code-native, type-hint/schema validation for pandas/Polars; lightweight; lives next to your transformations. Best fit for a small Python team that wants validation in-process. Fails at: cross-table/warehouse-wide governance, non-technical reporting.
- **Great Expectations:** Full-featured, human-readable "Data Docs," multi-engine (pandas/Spark/SQL). Powerful but heavy; teams report it becoming a maintenance burden. Overkill for 1–3 people unless you need the stakeholder-facing docs.
- **Soda Core:** Lightweight YAML/SQL checks (SodaCL), good middle ground, integrates with orchestration for production monitoring.
- **Verdict:** **Pandera** for in-pipeline row/type validation; add **Soda Core** if you want scheduled production monitoring of the Postgres tables. Skip Great Expectations unless you need its docs. Consider running CBS `validate` for the genuinely statistical cross-record rules.

**Frictionless Data (Table Schema + Data Package) + `frictionless validate`** — *lightweight provenance/schema for a portal.*
- Good, cheap way to attach a schema and validation to each published dataset for your public data portal; low adoption cost. Fails at: not a heavy validator, no vintage model.

### F. Claim-verification and citation-grounding that is mechanical

**Literate programming / reproducible reporting: Quarto (and R Markdown / knitr / Jupyter Book)** — *the mechanism that makes symptom 2/3 structurally impossible in the final report.*
- **What:** Quarto inline code (`` `r ... ` `` / inline Python) embeds computed values directly in prose; numbers cannot drift from source because they are *not typed*. "No hardcoded numbers in prose" becomes enforceable: every figure in the national report is an inline expression that resolves to a query against your Postgres/metric layer. This is the single most important thing you can adopt for the *writing* stage, and it is exactly what the AEA and central banks do.
- **Maturity:** Quarto is mature, actively developed (Posit), multi-language, multi-format (PDF/Word/HTML). Ships with RStudio; VS Code extension.
- **Cost:** Low — days, not weeks. The discipline (ban literal numerals in prose) is the hard part, not the tooling.
- **How it fails:** It governs the *report*, not the agent's exploratory claims. It cannot stop an assistant from saying something wrong in chat; it stops wrong numbers from reaching the published document. Combine with a lint/CI check that greps the `.qmd` source for bare numerals in prose.
- **Link:** https://quarto.org/

**"Every number resolves to a cell" pattern + AEA Data Editor practice** — *the organizational answer, from people who do exactly this.*
- The AEA Data and Code Availability Policy (Lars Vilhuber, Data Editor since 2018) enforces that published results are regenerable from data+code; the Social Science Data Editors' README template and "reproducibility from day 1" workshops are directly reusable. Adopt their replication-package discipline for your national report: the report *is* a replication package.
- **Link:** https://aeadataeditor.github.io/

**Automated fact-checking infrastructure (ClaimReview, Full Fact, Google Fact Check Tools, QuanTemp, FEVER/FEVEROUS/TabFact)** — *mostly NOT production-usable by you.*
- **Blunt verdict:** This ecosystem is built for verifying *claims in the wild against open evidence*, not for guaranteeing your own prose matches your own database. QuanTemp shows the task is hard even for research systems (best 58.32 macro-F1; CheckThat! 2025 ~0.57). FEVEROUS/TabFact (claim-vs-table verification) are datasets/benchmarks, not deployable tools. ClaimReview/Google Fact Check Tools are for publishing/consuming fact-check metadata. **None of this replaces the deterministic "the number in the sentence equals the cell in the DB" check, which you can write in an afternoon.** Do not invest here.

### G. Data journalism / newsroom number-provenance practice

**Datasette (Simon Willison) + "publish the data behind every number"** — *the newsroom pattern most transferable to your public portal.*
- **What:** Datasette publishes SQLite/queryable data behind stories so every figure is traceable to a row; the broader data-desk discipline (Reuters/FT/The Economist/ProPublica, IRE/NICAR "bulletproofing" checklists) is: no number in a story without a documented source cell and a second-person check.
- **Caveat:** My live search on Datasette's current release specifics was cut off by budget before I could confirm 2025–2026 release dates — verify maturity before depending on it, though the project is well-established and actively developed by its author.
- **Verdict:** The *practice* — data-behind-the-number, checklist bulletproofing, "trace every figure to a cell" — is exactly your need and is more valuable to copy than any single tool. It converges with the AEA and Quarto approaches.

### H. Scientific-publishing reproducibility

- **AEA Data Editor / Social Science Data Editors** (above) is the most directly applicable: treat the national report as a reproducible package. **CODECHECK, cascad, Whole Tale, ReproZip, Binder** are real but oriented to academic paper reproduction; for a 3-person team they are mostly *inspiration*, not adoption targets. **W3C PROV / PROV-O** is the standard vocabulary for provenance (which extraction produced which cell from which PDF vintage) — worth borrowing conceptually for a `provenance` table; full PROV-O tooling is overkill.

### I. Agents degrading on large corpora — what actually fixed it (practitioner evidence)

This is symptom 1, and it is the best-documented external problem.

- **Context rot is real and measured.** Chroma's July 2025 "Context Rot" report (Kelly Hong, Anton Troynikov, Jeff Huber) tested 18 models and found reliability degrades as input grows *even well below the context limit* — not just near it. RULER (NVIDIA) and NoLiMa show most models' *effective* context is far below their advertised window (NoLiMa, Adobe Research, arXiv:2502.05167 v3: of 13 models tested, 11 drop below 50% of their short-length baselines by 32K; many effective lengths ≤2K–8K). "Lost in the middle" persists. **Implication: piling the corpus into a long context will not save you; it makes symptom 1 worse.**
- **Anthropic's published fix (primary source):** agentic search (glob→grep→read) beat their own RAG+vector-DB for Claude Code — its creator Boris Cherny states "agentic search generally works better… it is also simpler and doesn't have the same issues around security, privacy, staleness, and reliability" (HN item 43164253). And **subagents with isolated context windows** (each returns a distilled ~1–2k-token summary to a lead agent) gave a "substantial improvement over single-agent systems." This is the architecture to copy for your corpus.
- **Aider's repository map** (tree-sitter + personalized PageRank over the symbol graph, rendered to a ~1k-token budget) is the mature reference for giving an agent a *compressed structural view of a large tree* instead of reading everything. Actively maintained (v0.86.0 dated 2025-08-09; ~48k GitHub stars). Fails on: huge monorepos (map goes coarse), dynamically-referenced/poorly-named code, and it's a code-symbol map, not a data-catalog map — but the *idea* (a ranked, budgeted index of "what exists") is exactly what your corpus needs. Link: https://aider.chat/2023/10/22/repomap.html
- **AGENTS.md / CLAUDE.md convention** (open, donated to the Linux Foundation's Agentic AI Foundation Dec 2025; 60,000+ repos, 30+ tools) — a root instruction file telling the agent what exists and how to navigate. **Measured result (Vercel):** a compressed docs index embedded in AGENTS.md hit **100% task success vs 79%** for on-demand lookup and **53%** baseline on Next.js tasks — the cleanest before/after in the literature (caveat: framework-doc tasks, not big-tree navigation; vendor-reported). Fails on: oversized instruction files themselves consume context and can trigger compaction (OpenCode issue #18037: a ~100KB file made it "unusable"). Link: https://agents.md/
- **The concrete "silently stops seeing files" bug is real and reproducible:** Claude Code issue #16043 (Glob's ripgrep hits a timeout on a large gitignored dir → SIGTERM → returns "0 results" silently instead of erroring); #12534 (subdirectory contents invisible in large repos); Read-tool silent truncation at 2000 lines (model reasons over the head of the file as if it were whole). **This is your symptom 1, filed by other people.** The fixes practitioners use: preflight with `wc -l`/`find`, scope caps ("read at most 3 files, explain why first"), reference specific files not directories, and — most relevant to you — **replace directory-browsing with an index/DB query.** Link: https://github.com/anthropics/claude-code/issues/16043
- **Structured-retrieval-beats-filesystem is contested but leans your way for a *stable, curated* corpus.** Vercel/Oracle/Elastic report index/DB retrieval winning for stable data; Anthropic and Amplify Partners argue filesystem/agentic-grep wins on *fast-changing* code. Vercel's own note: indexes "go stale between reindex runs, so [they] degrade exactly on the recently changed code." **Your corpus is mostly stable historical statistics with periodic revisions — the regime where a structured index/catalog wins.** The consensus answer is **hybrid: query the catalog/DB to narrow, then read the specific source PDF/cell to confirm.**

### J. Make the corpus queryable, not browsable

- **This is the structural fix for symptom 1 and the delivery mechanism for the identity/state model.** The agent should issue SQL against Postgres and a metadata catalog, not walk folders. The metric layer (section A) is the semantic front door; a catalog is the index.
- **Catalog options for a tiny team, blunt:** **OpenMetadata / DataHub / Amundsen / Apache Atlas** are enterprise-scale and heavy — do **not** deploy these for 3 people. **CKAN** is the right weight if you want a public open-data portal with dataset-level metadata (it's what many government open-data portals run). **Datasette** is excellent for making SQLite/Postgres slices instantly queryable and publishable. **dbt docs** gives you a free auto-generated catalog if you adopt dbt anyway. **Marquez/OpenLineage** is the lightweight option if you specifically want lineage (which extraction run produced which table).
- **Text-to-SQL reliability is the risk here:** BIRD execution accuracy tops out at 71.83% published SOTA (and the benchmark's own scoring is only ~62% aligned with humans). **So do not let the agent free-form SQL against raw tables.** Force it through the semantic layer's defined metrics and a set of parameterized, reviewed queries/views. That converts an unreliable text-to-SQL problem into a reliable "call a named metric" problem.

### K. Crawl freshness / change detection (symptom 4)

- **changedetection.io** (open-source, Apache-2.0 option; active PyPI releases e.g. 0.60.x; used by newsrooms and to monitor government pages) is the ready-made tool for "did the .gov page silently change," including **PDF text-change and checksum monitoring**. Low adoption cost. Fails on: it's page/file-level change alerting, not a full diff-and-reconcile against your DB. Link: https://changedetection.io/
- **EDGI (Environmental Data & Governance Initiative)** built exactly the "did the government web page change" monitoring stack and maintains the **awesome-website-change-monitoring** list (511 stars, updated through Oct 2025) — the reference community for this precise problem (they solved it pre-LLM for US government data-rescue). Copy their approach. Link: https://github.com/edgi-govdata-archiving/awesome-website-change-monitoring
- **Content hashing / near-dup:** simhash/minhash/ssdeep for detecting revised-vs-republished documents; HTTP conditional requests (ETag/If-Modified-Since) and sitemaps for cheap freshness. These are standard, cheap, and deterministic — the right tools for symptom 4.
- **Verdict:** Store a content hash + fetch timestamp + HTTP validators per crawled artifact; drive re-extraction off hash changes; and record the transaction-time when your store's belief changed (ties directly to section B's bitemporality). changedetection.io for alerting, EDGI patterns for architecture.

### L. Pakistan-specific reality

- **State Bank of Pakistan — EasyData (easydata.sbp.org.pk):** This is the good news. SBP's Monthly Statistical Bulletin (Feb 2025) states EasyData holds "a collection of more than fourteen thousand variables" (up from "nearly 8,000" at the June 2022 launch per SBP/ProPakistani), includes SBP data plus PBS data, and — importantly — SBP explicitly advertises "a new API to retrieve a complete dataset," plus email notifications on releases. This is the one genuinely machine-readable Pakistani official source; build your SBP pipeline on the API, not on scraping the Monthly Statistical Bulletin PDFs.
- **Pakistan Bureau of Statistics (pbs.gov.pk):** Primarily PDF/HTML publications (Statistical Yearbook, HIES/PSLM, CPI releases, trade statistics). No robust public SDMX/API; the Code for Pakistan "Open Data Playbook" explicitly complains that PBS statistics are locked in human-readable PDFs. Expect to extract, not to consume a feed. Pakistan is on the IMF **e-GDDS** (not SDDS), so calendar discipline is limited.
- **Existing pipelines to reuse rather than rebuild:** **data4pakistan.com** (district poverty + 120+ development indicators from PSLM/MICS, six rounds 2004–2018); **opendata.com.pk** (Open Data Pakistan portal with PBS trade, HIES, provincial development statistics); provincial bureaus (e.g., **Bureau of Statistics Punjab** — Punjab Development Statistics) publish their own PDFs. World Bank and IHME/GHDx have curated PSLM/HIES microdata. Check these before re-extracting the same tables.
- **Verdict:** Consume SBP EasyData via API. Treat PBS + provincial bureaus as PDF-extraction targets with a mandatory validation gate. Reuse data4pakistan/opendata.com.pk where they already cover a series.

---

## Recommendations (staged, concrete)

**Stage 0 — decide the architecture (before more tooling).** Commit to: the agent queries Postgres + a metric catalog; it does not browse the corpus to answer factual questions. This single decision addresses symptoms 1, 2, and 3 at once. Benchmark that would change this: if your corpus were fast-changing free text rather than mostly-stable tables, agentic filesystem search would compete — but it isn't, so the catalog wins.

**Stage 1 — identity + state (load-bearing, ~2–4 weeks for one engineer).**
1. Add an append-only, bitemporal schema: every observation carries `series_id`, `valid_period`, `published_at`, `superseded_at`, `source_document_id`, `extraction_run_id`. Never update in place.
2. Build a `series` registry and a `metrics` layer (dbt MetricFlow, or hand-rolled views + a metrics table) so each contested concept ("real GNI per capita") is one defined object. Borrow SDMX/DDI code-list discipline for the identity columns.
3. Build a `release_calendar` table and a hard guard: the agent cannot state a figure whose `actual_release_date` is null. This kills the "nonexistent datapoint" error deterministically.

**Stage 2 — deterministic validation gate (~2–3 weeks).**
4. Put every extraction through rule-based validation before it lands: Pandera in-pipeline, plus CBS-`validate`-style statistical/cross-record rules (run R for this piece if worthwhile). Reject or quarantine on failure; extraction accuracy of ~98% means you *will* get thousands of bad cells without this.
5. Record provenance (PDF → page → cell → value → extraction run) in a `provenance` table (PROV-O concepts, not full PROV-O tooling).

**Stage 3 — literate reporting (~1–2 weeks + discipline).**
6. Write the national report in Quarto with **zero hardcoded numerals in prose** — every figure is an inline query against the metric layer. Add a CI check that greps the source for bare numerals in prose. This makes symptoms 2 and 3 structurally impossible in the published artifact.

**Stage 4 — retrieval architecture for the agent (~2–3 weeks).**
7. Give the agent an AGENTS.md/CLAUDE.md that describes the *schema and metric catalog*, not the file tree, and force factual questions through named metrics/parameterized views (not free-form text-to-SQL — BIRD says that's ~72% at best).
8. Use subagents with isolated context for corpus exploration; have them return distilled summaries. Adopt an Aider-style ranked index of "what exists" over the corpus (a catalog query, in your case).

**Stage 5 — freshness (~1–2 weeks).**
9. changedetection.io (or EDGI patterns) + content hashing + HTTP validators on every crawled URL; drive re-extraction off hash changes; record the transaction-time of belief changes (Stage 1 schema).
10. Consume SBP EasyData via its API instead of scraping its PDFs.

**Benchmarks that change the plan:** If upstream PBS starts publishing SDMX/CSVW (they don't today), drop extraction for those series. If your team grows past ~5 and non-technical stakeholders need validation dashboards, revisit Great Expectations and a heavier catalog (OpenMetadata). If text-to-SQL through the semantic layer measurably clears ~90% on your own held-out question set, you can widen the agent's query latitude.

## Caveats and what came back empty or thin

- **Model-based verification:** I looked hard for evidence that a model-checking-a-model approach works at production reliability for numerical claims and found the opposite (QuanTemp best 58.32 macro-F1; CheckThat! 2025 ~0.57; correlated failures). If you want to run a small model-based checker as a *second, non-authoritative* signal that only flags for human review, that's defensible — but it cannot be the gate.
- **Pakistani machine-readable sources:** Thin by design. SBP EasyData's API is the only strong hit. No PBS SDMX/API, no machine-readable national release calendar. This is a real gap, not a search failure.
- **Datasette current release specifics / Camelot's latest maintenance status:** my live searches on these were cut off by budget before I could confirm 2025–2026 release dates — treat those two maturity notes as slightly under-sourced and verify before depending on them.
- **Cline-specific and OpenAI Codex-specific measured large-repo fixes:** came back empty — no strong primary-source before/after numbers surfaced (Codex mostly appears via AGENTS.md adoption and the Vercel Next.js eval leaderboard).
- **Sourcegraph Cody as a current consumer agent:** effectively discontinued — Cody Free/Pro/Enterprise-Starter sign-ups closed 25 Jun 2025, access cut off 23 Jul 2025; Sourcegraph pivoted to "Amp" (spun out as a separate company 2 Dec 2025). Anyone citing "Cody" as a current option is out of date.
- **A turnkey product that does all of this for official statistics:** does not exist. The closest coherent worldview is the CBS/ESS official-statistics-software stack (R-centric) plus ALFRED's vintage model plus a semantic layer plus Quarto. You will assemble, not buy.
- **Some cited long-context "arXiv" preprints surfaced with implausible future IDs** during research and were excluded as unverifiable; the load-bearing long-context claims here rest on Chroma's Context Rot report, NVIDIA RULER, NoLiMa (arXiv:2502.05167), and Anthropic's engineering posts, which are solid.
- **Unverified vendor numbers:** the Docling ~97.9%, Vercel 100%-vs-79%, and Cursor +12.5%-hybrid figures are vendor/practitioner-reported; directionally consistent with independent tests but not independently audited. Treat as indicative.