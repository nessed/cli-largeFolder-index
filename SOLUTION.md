# A local evidence engine for Claude Code

Planning document, 13 September 2026. No implementation or new model battery has been run for this proposal. `BUILD_PROMPT.md` is the execution contract; `ACCEPTANCE.md` contains private examination answers. All three documents must be inaccessible to measured research sessions.

## 1. Decision

Build a short-lived Python evidence engine that Claude Code invokes automatically. Keep SQLite and the fast PDF text extractor. Replace whole-page ranking as the primary discovery method with a searchable catalogue of **table captions, row labels, column headers, units and source identity**, with links back to physical pages. Extract and verify numerical cells only on the small set of pages selected for the question. Let Claude interpret the question and choose evidence; let code retrieve values, check compatibility, calculate and render the factual answer.

This is a new retrieval representation and an evidence contract, not another instruction to use the existing search command. There is no service, listening port, resident model, watcher or second application. A synchronous hook runs when a question arrives; subsequent bounded commands run and exit. SQLite files survive; processes do not.

The narrow, credible first product is **cited answers about readable local tables and notes, with explicit partial answers and abstentions**. Universal correct answers from an arbitrary research folder in 60 seconds are not achievable under these constraints. Neither missing scans nor ambiguous economic definitions can be repaired by a stronger ranker. A successful build must pass the numerical gates below before it is described as working; tomorrow's availability is an aspiration, not a measured fact.

## 2. What the evidence actually establishes

I inspected `labpaths.py`, ingestion, search, session capture, stack installation, scoring and offline diagnostics; their raw state files; the frozen sample and answer key; all nine absence answers from the three question batteries; selected actual PDF pages and a DOCX table. I inspected the five outside research passes as background, not as validated recommendations. No older solution proposal was used as a starting architecture.

### Corrections that change the design

| Claim in the record | What the code or source says | Consequence |
|---|---|---|
| Every stack fabricated all three absence answers | `run_harness.py` requires a refusal regex **and at most two numeric tokens**. Years, identifiers and coverage counts trigger failure. All nine inspected answers declined the requested figure/notification contents. S1's two SRO answers explicitly disclose unreadable files. Some others overclaim exhaustive absence. | The reported 0/3 is not evidence of nine hallucinations. Test non-fabrication and justified scope separately. Do not promise a new refusal mechanism has fixed a failure that was mis-scored. |
| 64 evidence files are indexed | `diagnose_recall.py` sums evidence-address references without deduplicating paths. Its 64/64 is 64 references, not necessarily 64 distinct files. `indexed` says some text exists, not that the target cell survived correctly. | Audit exact address, row, column and value. File coverage alone is inadequate. |
| Vocabulary is not the problem | `pl_14` asks for **sales tax**; its actual table says **GST collection**. `pl_21` asks for **direct taxes**; its table says **Income and Corporation Tax**. These are not the same tokens. The failed rare-word experiments even select terms with document frequency zero. | Query interpretation and vocabulary bridging are necessary. The old evidence does not establish that lexical retrieval is intrinsically incapable. |
| Re-scored recall means correct answers | The re-score credits a search snippet attached to a path. The original harness also credits basenames and conflates opening a forbidden source with citing it. Neither verifies numerical entailment. | Track candidate discovery, page reads, supported cells, answers and disallowed use separately. |
| Hash identity and churn are implemented | `index_build.py` skips any path already in `files`. It does not refresh changed files or remove deleted ones. Its large-file hash samples head and tail. | Implement transactional change detection and full hashes; do not reuse the existing resume logic. |
| Embeddings cannot run on this machine | One run embedded 512 truncated pages, at 8.2 pages/s, after a 20.8 s load. The 20.82 h projection is for **614,150 ra-ship pages**. The same rate gives about **40.86 h** for 1,206,260 harness pages. | Reject full-page embedding for setup time, not all CPU semantic work. A compact catalogue has a different denominator. Measure that denominator before considering embeddings. |
| The answer key is a complete correctness oracle | `mb_04` asks for a KP comparison around 2019-20, but its expected components use FY2016-17, FY2019-20 and FY2013-14. The first is a federal total, not necessarily an allocation to KP. The key also lists Rs million where the addressed allocation table prints Rs billion. | Do not reward mixing years, populations or units to match the key. Preserve the key and add a private, versioned source audit. |

The shared index's measured counts are confirmed by a read-only SQL query: 13,634 `indexed`, 1,211 `image_only_no_text`, 18 encrypted failures, 14 parser failures, 120 unsupported, 13 zero-byte: **15,010 files**. The recorded build took 782 s. The DB is 6,971,469,824 bytes, approximately 6.49 GiB. The page total is 1,206,260. “No extracted text” is a parser observation; the new inventory must distinguish blank, scanned and partially readable PDFs instead of assuming every empty extraction is a scan.

The corrected file-contact means in the supplied re-score are 0.167/0.235/0.176 for S0/S1/S2. These are weak retrieval results, not measured answer accuracy. Recorded question-cost totals cover **14/20, 15/20 and 16/20 sessions**, respectively; $12.5381/$2.8934/$2.6832 are incomplete totals. The 92/25/21 tool-call comparison is from canaries, not the 20-question answer batteries. Three absence questions, one answering-model configuration, and a synthetic corpus cannot establish a general accuracy or confidence threshold.

### What the pages suggest

The examined PDFs put long, repetitive economic prose around a small number of compact tables. A page-length score treats the prose and the desired table as the same object. The 2016-17 grants page for non-tax receipts repeats many years' figures; its actual table is a short labelled row. `pdftotext -layout` moves the row label and first value away from later values even though the rendered table is clear. This is direct evidence for separating **discovery text** from **cell interpretation**.

It is not proof that the proposed catalogue will retrieve all questions. Stage 5 of the build is the cheap falsification test. A full-tree learned reranker, new vector database, or $30 battery is not the first experiment.

## 3. Mechanism and data flow

```text
question in Claude Code
  -> synchronous prepare hook: inventory delta + request ID + catalogue leads
  -> Claude selects concept, dimensions and operation using typed commands
  -> multi-channel catalogue retrieval, then bounded page/notes fallback
  -> read selected source pages; coordinate-based table extraction
  -> evidence cells with exact labels, units, period, flags and provenance
  -> compatibility checks + Decimal calculations + deterministic answer
  -> Claude returns that answer; Stop hook checks the returned answer matches
```

### Discovery has several representations, with no hard folder filter

Each document has its observed title, content hash, every live path alias and any explicit source/publication metadata. Document title and year are **not** accepted as the geography or observation year of every table within it. This matters even in the fixture: a Gilgit-Baltistan white paper contains a national FBR tax table.

Each detected table has a compact card: caption, heading context, raw row-label candidates, literal year/column headers, unit strings, source footer and flags. Discovery cards omit numerical observations from ranking. A card is a pointer, not an authoritative parsed dataset. TOC entries are navigation leads, not table evidence. Ordinary prose remains searchable in a separate FTS index, and short notes retain paragraph/line addresses and outgoing local document references.

The initial catalogue is extracted with deterministic text/line rules. It does not ask an LLM to summarize 15,000 documents. Numbered captions are one detector; aligned year-header/numeric-row blocks are a second; explicit table markup/CSV/Office structures are a third. The paragraph channel remains available when those detectors miss an unusual layout. Tables without captions therefore remain reachable.

Claude supplies concept phrases and explicit dimensions. The engine expands a small, declared economics vocabulary for discovery only: for example sales tax/GST, defence/defense, labour/labor, receipts/revenue. It never treats “development expenditure”, “PSDP allocations”, “releases” and “development expenditure and net lending” as interchangeable observations. Unknown terms remain searchable; corpus-derived labels are offered to Claude. No question IDs, gold paths or gold series IDs enter this vocabulary.

Retrieve independently from caption/row labels, headings/source text, document titles, notes/references and ordinary paragraphs. Fuse ranks, collapse exact duplicates, and reserve slots for different label families and periods. Do not retrieve 50 pages from the same repetitive PDF. Do not first select “official-looking directories”: filenames and folder names are fallible evidence. Follow explicit references one hop. For trajectories, retrieve the table family across the requested years after the initial discovery, rather than expecting a single top-k list to cover time.

Fixed parameters and the only permitted A/B alternative are specified in the build contract. Full embeddings and an added neural reranker are outside v1. If this catalogue fails its recall gate, report that failure with its unresolved cases; do not hide it by widening an LLM prompt or hardcoding gold answers.

### Verification binds each value to its actual cell

Selected PDF pages are reopened from the current source. Use PDFium for text coordinates and rendering, and pdfplumber on those pages for table geometry. Rectangles, row/header bands, and source labels constrain cell assignment. Numerical extraction must agree between the two views at the selected cell, including sign, decimal point and R/P markers. Agreement is useful corroboration, not proof: the PDF image remains the inspectable original.

Ambiguous/overlapping cells are not coerced into a successful parse. The engine either uses a separate unambiguous sentence on a cited page with explicit subject/year/unit, or returns `AMBIGUOUS_EXTRACTION`. It does not use OCR or a visual model to certify an unreadable number in v1. A screenshot can be offered for inspection without turning an OCR guess into a verified observation.

CSV, XLSX and DOCX get structural adapters, not XML tag stripping. An XLSX address is workbook/sheet/cell with its header and cached value; missing formula results are unavailable, never recalculated by guesswork. A DOCX address is table/row/column, not an invented PDF page. Notes cite original line spans. Archive members remain explicitly unsupported in v1.

An evidence record contains full SHA-256, live relative path, physical PDF page index (zero-based), viewer page (index + 1), printed label if observed, table/row/column text, value text, Decimal value, unit/multiplier, period, geography/population if explicit, source, P/R flag, bbox, extractor version and source quote. Unknown metadata stays unknown. IDs are hashes of this record, not of the question.

The answer compiler accepts evidence IDs and named operations, never a model-supplied numeric result. It checks unit conversions, complete denominators, matching periods and geographic scope. Cross-year merges require matching literal definitions or an explicit, cited bridge. An alias used to **find** a table cannot authorize a merge. Even identical numerical overlap does not prove conceptual identity. A conflict produces side-by-side values and an explanation of the unresolved dimension.

For a vague question, return the supported interpretation with its literal label and a concise scope statement. Where there are two materially different interpretations, show both and say what remains undecided. For female labour-force participation by industry, distinguish participation rate, employment share and count, and require sex, age universe, industry classification and denominator to match. The 135-question fixture contains no direct female-participation or defence-comparison question: passing it cannot certify those examples.

### Honest negative and incomplete answers

Use these outcomes: `ANSWER`, `PARTIAL`, `CONFLICT`, `NOT_FOUND_IN_SEARCHED_MATERIAL`, `UNAVAILABLE_COVERAGE`, `AMBIGUOUS_EXTRACTION`, `INDEX_PENDING`, `ENGINE_ERROR`.

An exact identifier query preserves the whole identifier and searches literal and normalized variants, without a top-k cutoff on occurrence counting. A year token alone is not an identifier match. A semantic query exhausts the specified discovery channels and budget before reporting no supporting evidence. Both outcomes disclose searchable files/pages, unreadable files/pages, pending changes and truncated candidate pools. Neither says a missing semantic answer is proven absent from the entire tree.

The compiler's no-evidence output contains zero requested financial/statistical claims. It may contain years, notification numbers and coverage counts. That is precisely why the previous “at most two numbers” scorer is rejected.

### Source selection is an epistemic limit

Exact copies count once. Notes, scripts and derived tables can explain provenance and direct a search. A file's `Source: Ministry of Finance` text is an attribution, not authentication of government authorship. An official-looking duplicate can be edited. If two credible sources disagree and no source states which supersedes which, show the disagreement. The system cannot recover hidden author intent, authenticate an unlabelled edit, or infer which identical copy an answer-key writer preferred. These are limitations of the available evidence, not reasons to pick by filename or mtime.

## 4. What runs, and where it lives

Source code: `corpus-lab/evidence_v1/`; public CLI: `corpus-lab/bin/evidence.py`; setup: project-root `SETUP_EVIDENCE.ps1` (created by the builder, not by this planning turn). Python dependencies install only into the project-root `.venv`. The initial machine already has pypdf 6.18.1, pdfplumber 0.11.10 and pypdfium2 5.13.0; their wheel installation and imports still need a reproducible installation check.

Persistent runtime state is outside the research folder at `%LOCALAPPDATA%/RetrievalLab/evidence-v1/roots/<root-id>/`. It contains a manifest/catalogue SQLite DB, compressed page store, verified-cell cache keyed by source hash, request receipts and evidence crops. Root ID is SHA-256 of the normalized absolute root. There is no dependence on git. Runtime code imports no `labpaths.py` private-key defaults.

Only a marked section of `CLAUDE.md` and entries in `.claude/settings.json` are installed in the research root. Use `stack.py` for **all** corpus configuration writes and removals, extending it with an `evidence_v1` configuration. Preserve existing bytes and settings, record backups before mutation, and remove only owned entries on uninstall. Installed absolute paths make the source-code location stable; moving it requires running setup again, not editing hooks manually.

On first setup, enumerate and extract the corpus in the foreground, display progress every 10 seconds, and finish with `READY` only after the setup and integrity gates pass. Normal use is just `claude` in the folder and a question. First-time Claude authentication/trust may require the owner once; the unattended build never simulates a trust acknowledgement. Setup fails clearly if that prerequisite is missing.

Every question inventories the tree with `os.scandir`, without git ignores and without following reparse points outside the root. Compare size, `mtime_ns` and file identity. Full-hash new/changed files. For cited files, recheck a full hash immediately before compilation. Delete/tombstone removed aliases; a moved file reuses content by full hash. Failed extraction retries when bytes change and once per day, with a bounded per-query budget. Update each file transactionally; a killed extractor leaves the last complete generation plus an explicit pending change.

No passive watcher means changes are noticed at the next question. Same-size edits with deliberately preserved timestamps can evade an inventory scan: cited-source hashing catches them if selected, but newly relevant content can be missed until the automatic daily full-hash audit completes. This is an explicit freshness limit. Query work is bounded; a large overnight import can yield `INDEX_PENDING` rather than a false claim of complete coverage. It continues automatically on later questions. The user never remembers a re-index command.

## 5. Claude integration and what it can enforce

Use synchronous command hooks and a typed CLI; do not install an MCP server. `UserPromptSubmit` prepares a request and catalogue leads automatically. `PreToolUse` restricts research access to the verified CLI, with an exact argument grammar, and permits only request-owned image reads. `Stop` checks that the final answer equals the compiler output and permits at most one correction. These hooks control workflow, not economic truth. Test the installed version: local `claude.exe --version` returned **2.1.257** during planning.

There is a hard boundary to the promise: a Stop hook cannot retroactively hide text already streamed to the user. Current documentation also describes `MessageDisplay`, but it fails open on handler errors and leaves the original transcript unchanged. Do **not** use it as a security or correctness boundary. A compiler-issued evidence receipt is the authoritative result; uncompiled prose is not certified. If acceptance finds substantive unsupported claims in visible output, the integration fails release even if the hidden receipt is correct. Absolute no-hallucination enforcement under arbitrary Claude/hook failure would require control of the application renderer, which the requested interface does not provide. [Claude hook reference](https://code.claude.com/docs/en/hooks).

Measured children must not be descendants of the builder's context. Launch a fresh `claude.exe` process for each question. Remove unnecessary tools, external connectors and web access. Absolute denies must cover `_private`, all three planning documents, generator/world/seed data, evaluator outputs, the builder's transcripts and memory. A hook that merely rejects command strings containing `_private` is not a sandbox; arbitrary Python/Bash can construct the path. The new CLI accepts only root-contained evidence IDs and typed parameters, never code or arbitrary SQL. The isolation stage attempts actual escape routes before any useful model evaluation.

## 6. Setup, runtime and development budgets

| Item | Proposed budget / interpretation |
|---|---|
| Human installation | One setup command after Python, Git/pdftotext and Claude sign-in exist; at most 5 minutes of active operator work. New-machine prerequisites are counted separately, with a 15-minute target, not concealed. |
| Full cold index + catalogue on this harness | Target <=1,800 s, peak process-tree RAM <=8 GiB, new runtime storage <=12 GiB. Measured old extraction alone is 782 s; catalogue cost is **unmeasured**. Existing DB reuse is a development acceleration, never a cold-install benchmark. |
| Question | Target <=60 s end-to-end on the installed Max account; local retrieval <=5 s p95, selected-page verification <=15 s p95. Network/model latency is outside local control; report actual failures. |
| Software/cloud indexing | $0. No embedding API, hosted parser, download of research documents, or server subscription. |
| Answering | Uses the professor's existing Claude Code Max entitlement; consumes its quota. API-equivalent telemetry is not automatically an invoice. Account limits and extra usage must be checked. [Max use in Claude Code](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan). |
| Default build evaluation | $0 incremental metered spend; maximum 175 fresh answering sessions, one at a time, only if existing subscription authentication is verified. Stop on quota exhaustion; never switch billing mode. |
| Optional separately authorized API evaluation | Maximum $6 total, including failed attempts; 20-question development battery only, $0.25 request allowance plus $0.05 reserve per request. Do not enable this from the current brief. Missing answers remain in the denominator. |
| Engineering effort | Estimate 16-28 focused engineer-hours for the full contract; an unattended agent may be faster or slower. There is no evidence for a guaranteed overnight implementation. The release marker stays absent until gates pass. |

If the setup gate fails, preserve the prototype and report its measured setup requirement. Do not claim that leaving a daemon running, removing difficult formats from the count, or shipping a prebuilt harness-only DB meets the goal.

## 7. Rechecked alternatives

The shared “needs Docker” exclusion was incorrect. These checks are documentary, not new installation benchmarks.

| Tool | Corrected finding and decision |
|---|---|
| Elasticsearch | Official Windows ZIP installation exists. Still requires a running search process and does not bind economic cells. Reject for this interface, not lack of Windows support. [Official Windows installation](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-with-zip-on-windows). |
| Qdrant | Python local mode works without a Qdrant server. It is a possible embedded vector store, but it does not eliminate embedding cost or solve table semantics; v1 needs no vector store. [Maintainer client documentation](https://github.com/qdrant/qdrant-client). |
| Datashare | Maintainer repository documents Windows installers. “Docker only” is not an adequate dismissal. It is a larger document-search application whose operational shape adds no necessary component to this proposal. [Installer repository](https://github.com/ICIJ/datashare-installer). |
| paperless-ngx | Documents a bare-metal route as well as Docker, with webserver/consumer/worker/scheduler processes. Fails the no-running-service contract. [Setup documentation](https://docs.paperless-ngx.com/setup/). |
| Onyx | Documented local route deploys a service stack through Docker Compose; no verified native, transient Windows route established here. Reject the documented deployment shape. [Official local deployment](https://docs.onyx.app/deployment/local/docker). |
| Aleph | The legacy maintainer repository announces end of maintenance after December 2025 and a transition to Aleph Pro. Do not build a new single-user Windows dependency on that legacy stack. [Maintainer notice](https://github.com/alephdata/aleph). |

No global claim is made that Marker licensing, lack of cargo, or lack of NVIDIA rules out every extractor/search alternative. None is needed to falsify this design cheaply. PDFium rendering and pdfplumber's geometric extraction are existing local capabilities worth applying only to selected pages. [PDFium API](https://pypdfium2.readthedocs.io/en/stable/python_api.html), [pdfplumber documentation](https://github.com/jsvine/pdfplumber).

## 8. What passing means, and what it will not establish

The build contract requires separate gates for catalogue reach, cell accuracy, refusal scope, integrity after churn, cold setup, ordinary-language answer quality, and visible terminal output. Original 135-question results and source-audited results are both retained, with fixed denominators. A filename hit is never a correct answer. Byte-identical aliases are valid evidence but count as one source. A contradiction in the fixture is not a licence to alter a question or silently remove it.

Sir's actual question is **not in the 135-question key**. The acceptance document supplies a separately labelled, source-checked four-survey case. Its passing answer must distinguish the older development-expenditure definition from development expenditure **and net lending**, not manufacture one smooth comparable series. Four survey editions that repeat a table are four documents, not four independent measurements.

The frozen corpus must remain unchanged. Add small, separate hostile fixtures for changed files, table layout failures, fake instructions in documents and unsupported formats. No regeneration and no new canary planting. Transfer to real research remains unproven until a real-folder examination supplies at least 12 human-adjudicated questions, including 3 absent/ambiguous cases. This can be a separate later exercise; it must not be represented as done tonight.

Reach limits: image-only PDFs and images; encrypted/damaged files; ZIP members and unsupported formats; Urdu-only semantics; badly overlapped tables; unknown formula results; disputed provenance; definitions requiring an economist's decision; very large churn; and Claude/account/network failures. These produce explicit incomplete outcomes. A CPU OCR extension could reduce the scan hole, but its installation, throughput and accuracy require their own measured gate and are outside v1.

The machine is adequate for the proposed local mechanics. Whether those mechanics meet the 60-second, correct-answer goal is an experimental question with an affordable test. The right handoff is a falsifiable build contract and an honest release label, not another optimistic search-tool comparison.
