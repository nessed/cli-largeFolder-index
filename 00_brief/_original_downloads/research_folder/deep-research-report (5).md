# Deep research: making a huge research tree behave like one addressable corpus inside Claude Code

## Bottom line

Your framing is now mostly right, with one correction:

**The remaining problem is not “search a very large folder”. It is building an evidence-addressable corpus whose filesystem happens to be the backing store.**

Once the tree reaches tens of thousands of heterogeneous files, letting Claude discover evidence by recursively browsing paths is the wrong abstraction. Even if Glob/Grep were flawless, a path is too coarse a retrieval unit, paths are unstable under moves, a ranked top-five result is not an audit trail, and “same series in ten annual reports” is an identity problem rather than a search problem.

The architecture I would build is:

> **filesystem → audited manifest → addressable evidence units → canonical series/provenance registry → hybrid retrieval → retrieval receipt → MCP tools → Claude Code**

Claude should almost never need to know where something sits in the directory tree. It should be able to ask for:

```text
"Pakistan automobile production trajectory, cars vs LCVs, 2015–2025"
```

and receive objects more like:

```text
evidence://sha256:abc.../page/340/table/4.2
  current_path: sources/pbs/statistical-yearbook-2023/chapter-14.pdf
  section: Manufacturing
  table: 4.2 — Production of Selected Manufactured Items
  page_pdf: 340
  printed_page: 322
  series_ids:
    - pbs.auto.passenger_cars.units.annual
    - pbs.auto.lcv_jeeps.units.annual

evidence://sha256:def.../page/117/table/7
  current_path: sources/pbs/statistical-yearbook-2019/...
  canonical_series: pbs.auto.passenger_cars.units.annual

derived://sha256:ghi.../row/18
  current_path: extractions/run-2026-02-03/table_00481.csv
  derived_from: evidence://sha256:abc.../page/340/table/4.2
```

That stable address layer is the missing conceptual piece. **The path is metadata; it must not be the identity.**

The strongest practical stack I found is:

| Requirement | What I would actually use |
|---|---|
| Page/table retrieval | your existing structured extraction + **Sentence Transformers `MultiVectorEncoder`/ColQwen2.5** for visual page retrieval; optionally **PageIndex** for very long text-heavy documents |
| Structure-aware chunks | evidence units preserving page/section/table metadata; **Unstructured's chunking model is worth copying even if you do not use its extractor** |
| Same series across years | **canonical series registry** + **Valentine** candidate matching + agency metadata/SDMX where available; human confirmation for ambiguous merges |
| SBP specifically | exploit **SBP EasyData metadata API** before reverse-engineering its PDFs |
| Ingestion completeness | small manifest/audit database + **Apache Tika Pipes** as a broad file-health probe |
| File churn | content IDs + path aliases + **Watchman** or **watchfiles** + mandatory SessionStart reconciliation |
| Query audit | custom **retrieval receipt**, optionally traced in **Phoenix/OpenInference** |
| “Not in corpus” | calibrated evidence sufficiency gate; never pretend top-k retrieval proves absence |
| Claude delivery | **local MCP server + SessionStart/PreToolUse hooks + permissions + tiny CLAUDE.md** |
| Prevent Claude bypassing it | conditionally deny Glob/Grep with `PreToolUse`, or completely remove them with permissions/`--disallowedTools` |
| Parallel research | custom Claude Code subagents sharing the same MCP corpus service |

The incremental software cost of the fully local version is effectively **PKR 0**, aside from hardware and the Claude Max subscription you already have. Where I convert dollar costs below, I use roughly **PKR 277.4/USD**, around the September 8, 2026 interbank close. citeturn23search1turn23search3

No round-one conclusion you listed was overturned. One adjacent update matters: the original `colpali-engine` route is now deprecated for new deployments; Sentence Transformers v6 has absorbed ColBERT/ColPali-style multi-vector retrieval into `MultiVectorEncoder`. citeturn24search0turn24search1


## Sub-document addressing: stop indexing PDFs as files

A 600-page PDF should exist in the corpus simultaneously as a document, a hierarchy of sections, a sequence of pages, a collection of tables/figures, and a set of text chunks. Retrieval should operate over those children and return the parent relationship.

The trick is **not choosing one universal chunk size**. It is creating several retrievable representations that point back to one immutable evidence address.

### Sentence Transformers MultiVectorEncoder with ColQwen-style visual retrieval

This is the most interesting thing I found for your exact “page 340 has the thing” problem.

Sentence Transformers v6, released in August 2026, added `MultiVectorEncoder`, bringing ColBERT-style late-interaction models and ColPali-style visual document retrieval into the mainstream Sentence Transformers library. A visual document retriever treats each PDF page as an image, encodes it into many patch-level vectors, and allows a text query to retrieve the page directly—including relevance arising from tables, charts and layout rather than only extracted prose. citeturn24search0turn24search1turn24search6

Install:

```bash
pip install -U "sentence-transformers[image]"
```

A currently supported starting point is:

```python
MultiVectorEncoder("vidore/colqwen2.5-v0.2")
```

Sentence Transformers' current tested-model list explicitly includes visual document models and describes them as embedding **page images as documents and text as queries**. The library is now maintained by Hugging Face. citeturn24search1turn24search2turn24search6

This changes your retrieval unit cleanly:

```text
PDF file
  ├── page 1 visual embedding
  ├── page 2 visual embedding
  ...
  ├── page 340 visual embedding  ← retrieved
  ...
```

Then page 340's structured extraction tells Claude which table and cells are on it.

This is not speculative architecture: the published Weaviate ColQwen recipe builds exactly this kind of PDF system by embedding individual pages and retrieving them with textual queries under late-interaction MaxSim scoring. citeturn24search9

**Why I like it for your corpus:** it is unusually good insurance against the thing that breaks ordinary textual retrieval—tables whose semantic relationship comes from two-dimensional layout. It also gives you an obvious citation primitive: **document + physical PDF page**.

**What it does not solve:** it retrieves a page, not automatically “Table 4.2, row Passenger Cars, column 2023”. Your existing extractor still supplies that finer-grained representation. It also produces much larger indexes than one-vector-per-chunk retrieval because a page becomes hundreds of patch/token vectors. Sentence Transformers itself describes stronger retrieval as coming at the price of a larger index. citeturn24search0turn24search6

**Maintenance:** very active; this feature landed only weeks ago in Sentence Transformers v6, under Hugging Face maintenance. citeturn24search0turn24search1

**Setup:** my estimate is **4–8 hours** to create page images, index one project and expose a basic page-search command; **1–2 days** to integrate citations and fallbacks properly.

**Incremental cash:** **PKR 0 software** when run locally. GPU/RAM is the actual cost. I would test it as a reranker or second-stage page retriever before committing to a full multi-vector index.

**Failure modes:** index size; GPU requirements for the better visual models; visually similar pages can rank together; it only narrows to pages; exact numeric interpretation still needs structured table data.

**Confidence for your goal: high.**

### PageIndex

PageIndex is the other serious answer, but I would use it selectively rather than make it your only corpus index.

As of August 2026, PageIndex has a local Python SDK:

```bash
pip install -U pageindex
```

It creates a hierarchical tree from a long document's natural sections and lets an LLM reason down that tree rather than retrieving fixed chunks. Its local version exposes page-level citations; PageIndex Cloud exposes line-level citations. The repository explicitly targets financial reports, regulatory filings, textbooks and other long professional documents. citeturn27view0

That is almost exactly the operation you want inside one Economic Survey:

```text
Economic Survey 2025
 └─ Manufacturing
     └─ Automobile industry
         └─ Production
             └─ pages 337–342
```

rather than “embed every 800 tokens and hope”.

It is extremely actively developed: the project reports 429 commits, more than 35,000 GitHub stars, local mode and a new “Flash” indexer in August 2026. citeturn27view0

Its own benchmark reports roughly **US$0.001/page** for local tree construction using its example lightweight indexing model. At the working exchange rate above, that is roughly **PKR 0.28/page**, or **PKR 277 for a 1,000-page document**, plus query-model calls. citeturn27view0turn23search1

There are two major caveats.

First, the open-source/local project is still fundamentally document-oriented. The repository describes local multi-document scaling as manual, whereas PageIndex's corpus-level “File System” and MCP facilities sit on its Cloud offering. citeturn27view0

Second, do not over-read the headline accuracy numbers. Its published OSS benchmark is 62 lookup questions across 34 PDFs and explicitly says the answers are facts in **running text**. That is useful evidence that the tree works; it is not strong evidence that PageIndex alone solves ugly statistical tables. citeturn27view0

So my deployment would be:

> **visual/page index across the entire corpus; PageIndex trees for selected monster reports where document hierarchy itself carries substantial meaning.**

**Setup:** **2–4 hours** for a proof of concept on a few Economic Surveys; roughly **1 working day** to make its returned references conform to your evidence-address format.

**Cash:** open-source software **PKR 0**; its own model-call benchmark is ~PKR 0.28/page at current exchange rates. Claude Max does **not** turn unrelated external API calls into free Claude Code usage, so treat PageIndex's indexing/chat-model calls as separate unless you configure a local/provider route covered by your infrastructure. citeturn27view0

**Failure modes:** text-heavy local mode is much stronger than scanned/image-heavy local documents; OSS corpus scaling is not its strongest mode; LLM tree navigation itself can choose the wrong branch; current public benchmark evidence is stronger for prose facts than statistical tables. citeturn27view0

**Confidence: high for within-document navigation, medium for being your whole-corpus system.**

### The chunking pattern worth stealing from Unstructured

This is not a recommendation to reopen your extraction decision.

What is useful is **Unstructured's data model for retrieval units**.

Its current chunker supports:

- `by_title`, preserving section boundaries;
- `by_page`, preventing a chunk from crossing page boundaries;
- `Table` elements, which are kept separate from prose;
- `TableChunk` for oversized tables;
- `orig_elements`, preserving the elements from which a chunk came. citeturn26search1

Its own table-retrieval design keeps the structured table attached to the evidence unit while embedding a natural-language representation of it, with section and page metadata retained. citeturn26search3

That is the right *shape*.

One historical gotcha is telling: users have reported cases where a table title and its table ended up as separate chunks. citeturn26search5 This is exactly why blindly accepting a library's chunk boundaries is dangerous for your corpus.

I would therefore **copy the principle, not necessarily the implementation**:

```text
evidence_unit
    content_id
    unit_id
    kind = paragraph | section | page | table | figure
    pdf_page
    printed_page_label
    section_path[]
    displayed_table_number
    synthetic_table_ordinal
    text
    structured_payload
    bbox                  # where available
    parent_unit_id
    source_path_current
```

For tables, I would index at least two searchable forms:

```text
search representation:
"Production of passenger cars and LCVs in Pakistan by fiscal year,
units, Pakistan Bureau of Statistics, manufacturing"

payload:
actual table rows/columns/cells

provenance:
file content-id + page + table number + bounding box/extractor element
```

### The address format matters more than it looks

Do not let the citation key be:

```text
sources/pbs/yearbook-2023/chapter14.pdf:340
```

because it becomes wrong the day somebody moves `chapter14.pdf`.

Make the stable identity content-based:

```text
research://sha256/<document-content-id>/page/340/table/4.2
```

and resolve that to the current path at read time.

Store both:

```text
pdf_page_index        # unambiguous physical page
printed_page_label    # "322", "A-17", etc.
```

because government reports routinely have covers, Roman-number front matter and printed numbering that does not match the PDF viewer.

This is also how your cross-branch lineage becomes deterministic:

```text
research://abc/page/340/table/4.2
          ↓ derived_into
derived://xyz/table/pbs_auto_2023
          ↓ supports
claim://chapter3/claim/17
```

At that point Claude does not need to *rediscover* that an extracted CSV came from a particular PDF each session. You told the corpus once.

**That is a much bigger win than another embedding model.**


## Same statistical series across years: this is entity resolution, not retrieval

This is the least solved part of your problem.

I found several useful building blocks. I did **not** find a maintained package that you can point at ten renamed, reformatted government-report tables and reliably receive:

```text
2016 table 7 row "Motor Cars"
2017 table 9 row "Cars"
2022 table 4.2 row "Passenger Cars"
2025 annex II row "Passenger Cars (including taxis)"
        ↓
same statistical series
```

end-to-end.

That empty space is real.

The practical solution is a **canonical series registry** with automated candidate matching around it.

### First exploit real statistical identifiers when the agency has them

The clean version of this problem was solved years ago by statistical-data standards.

**SDMX** defines formal data structures, dimensions, code lists and series keys specifically so statistical observations can retain stable identities independent of display tables. SDMX 3.1 was released in 2025; the standard is used by national statistical agencies, central banks and international organisations. citeturn15search4

The Python implementation worth installing is:

```bash
pip install sdmx1
```

It supports SDMX 2.1 and 3.0, can retrieve and parse datasets and structural metadata, and can expose a provider's available series keys. The project is Apache-licensed and has current 2026 documentation. citeturn15search1turn15search2turn15search3

For IMF/OECD/World Bank/Eurostat-type material, use those identifiers rather than reverse-engineering PDF tables whenever possible. The library maintains built-in support/testing against a range of SDMX REST providers. citeturn15search5

**Setup:** **1–4 hours per provider** once you know its dataflow.

**Cost:** **PKR 0**.

**Failure mode:** this solves identity only where the publisher actually publishes usable SDMX structure.

**Confidence: very high when upstream SDMX exists.**

### SBP is better than I expected

A Pakistan-specific search produced one useful exception to the “everything is PDFs” problem.

State Bank of Pakistan's **EasyData** portal announced in February 2025 that registered users could access a dataset's metadata through a new API; SBP also reported further EasyData upgrades in 2026. citeturn20search0turn20search2

I would therefore mine the EasyData metadata **before** building aliases from SBP's historical PDF bulletins. Even if a particular historical observation remains PDF-only, agency-provided dataset names/dimensions can seed your canonical IDs.

I did **not** find equivalent evidence that Pakistan Bureau of Statistics currently exposes a general SDMX service or similarly useful statistical metadata API. More on that in the empty-search section.

**Setup:** likely **2–6 hours** to inspect EasyData metadata and see how much of your SBP corpus it covers.

**Cost:** no paid API pricing surfaced in my search.

**Failure:** metadata API existence does not imply every historical bulletin series is exposed through it.

**Confidence: high that the EasyData metadata API exists; medium on how much of your historical corpus it eliminates.**

### Valentine is the best lightweight candidate generator I found

**Valentine** is an actively developed Python library specifically for finding relationships between columns in different tabular datasets:

```bash
pip install valentine
```

The repository currently supports Python 3.10 through <3.15, pandas and Polars, and has 394 commits. It can match an arbitrary collection of DataFrames pairwise. citeturn18view0

It includes several schema-matching algorithms, including COMA, Cupid and distribution-based methods, and a Jaccard/Tversky matcher that can optionally use Sentence Transformer embeddings. Results include similarity scores and per-matcher details for COMA. citeturn18view0

This is useful when:

```text
2019: "Motor cars"                units
2020: "Passenger cars"            units
2021: "Passenger cars / taxis"    units
```

occur as *columns/schema fields*.

For many government tables, however, the series are rows rather than columns. In that case I would first normalise each candidate series into one record:

```json
{
  "label": "Passenger Cars",
  "table_title": "Production of Selected Manufactured Items",
  "agency": "PBS",
  "unit": "Nos.",
  "frequency": "annual",
  "geography": "Pakistan",
  "dimensions": ["fiscal_year"],
  "first_period": "2015-16",
  "last_period": "2023-24",
  "values": [...]
}
```

and match those records rather than the raw PDF table schemas.

**Setup:** **4–8 hours** to get useful candidates once tables are already extracted.

**Cost:** **PKR 0 software**. citeturn18view0

**Failure:** a high schema similarity score is not proof that two economic concepts are identical. Changed units, changed baskets, rebasing, geographic scope changes and definitional breaks can all make two similarly named series non-equivalent.

**Confidence: high as a candidate generator; low if used as an automatic merge authority.**

### pyJedAI is useful once you represent a series as an entity

**pyJedAI** is a maintained open-source entity-resolution library designed for end-to-end record/entity matching workflows; its repository currently has 363 commits and current documentation. citeturn18view1

Its role here is not “understand PDFs”. It is:

```text
series candidate A
series candidate B
        ↓
blocking / similarity / matching
        ↓
possible same canonical series
```

This is especially useful after you enrich a candidate with label, source, unit, table context, dimensions and a small value fingerprint.

**Setup:** roughly **0.5–1 day** because you need to create useful series records first.

**Cost:** **PKR 0 software**.

**Failure:** entity resolution learns similarity among the features you give it. It has no magical knowledge that a revised CPI with a new base year should—or should not—be treated as one continuous economic series.

**Confidence: medium-high as a component.**

### OpenRefine remains unusually appropriate for the ambiguous 5–10%

OpenRefine has reconciliation workflows specifically for mapping messy labels to canonical entities, and its current documentation continues to support interactive reconciliation. citeturn18view2

I would not put every observation through a GUI. I would use it for the review queue:

```text
automatic:
  exact known alias                       → accept
  same agency + unit + dimensions +
  near-identical labels/value overlap     → accept/high confidence

review:
  label changed + unit changed
  base year changed
  table title changed substantially
  overlapping values disagree
  scope changed
```

The output of review becomes permanent registry knowledge, so you do not pay the ambiguity cost repeatedly.

### The actual object you should build

Something like:

```sql
series
------
series_id                   TEXT PRIMARY KEY
canonical_name              TEXT
agency                      TEXT
concept                     TEXT
unit                        TEXT
frequency                   TEXT
geography                   TEXT
population_scope            TEXT
base_period                  TEXT NULL
definition_notes            TEXT

series_alias
------------
series_id
source_content_id
evidence_unit_id
source_label
source_table_title
source_unit
valid_from
valid_to
match_method
match_score
review_status
reviewed_by
```

Your retrieval tool can then answer:

```text
research_series("passenger car production pakistan")
```

with a stable series object first and only then fan out into the annual evidence units.

The matcher I would implement should combine:

```text
normalised series label
+ agency
+ unit
+ frequency
+ geography
+ dimension signature
+ table/section title
+ neighbouring row labels
+ overlap of reported periods
+ overlap of numeric values
+ known alias history
```

Numeric overlap is particularly useful. If the 2021 report says:

```text
2018  230,000
2019  210,000
2020  115,000
```

and the 2022 report repeats those historical observations under a changed row name, that overlap is strong evidence of identity. It still cannot automatically settle revisions/rebasing, so preserve the discrepancy rather than forcing a merge.

This is where I would push back hardest on an LLM-first approach:

> **Do not ask Claude to rediscover series identity from scratch on every query.**

Let Claude propose a new alias when necessary. Once confirmed, write the mapping into the registry.

That turns an impossible recurring semantic problem into a finite curation problem.

Research systems built around schema matching and data-lake table union search, including Valentine, Starmie and Pylon, confirm that finding semantically unionable heterogeneous tables is a real research field, not a solved filesystem-search primitive. citeturn16academia3turn15academia9turn15academia10

**Overall confidence on this recommendation: very high.**

The disappointing bit is that the canonical registry is the thing you have to own. I found no library that removes that responsibility.


## Coverage accounting and index freshness: you are right about staleness

The previous conclusion that index staleness was unimportant because source PDFs rarely change is wrong **for the system you actually described**.

Those are two different statements:

```text
source bytes rarely change               probably true
filesystem identities/paths rarely change     false
```

Your working tree has moves, reorganisations, replacement extractions, failed runs, old directories and duplicated outputs. Therefore an index in which:

```text
primary_key = "/old/path/to/file.pdf"
```

is a correctness bug waiting to happen.

A stale result pointing to a plausible path that no longer represents the indexed content is worse than a failed lookup.

### Content identity must be separate from location

The index should treat:

```text
content_id = digest(file bytes)
```

as document identity.

A path is a mutable alias:

```text
content_id abc...
    paths:
      /research/foo/sources/a.pdf      current
      /research/old/a.pdf              previous
```

A rename then becomes:

```text
same content_id
old path removed
new path added
no re-embedding necessary
```

whereas changed bytes become:

```text
new content_id
old index entries retired/superseded
new extraction/index required
```

This is also why derived extractions should refer to source **content ID + evidence address**, not only the source pathname.

### Apache Tika Pipes is the closest existing thing to the failure accounting you asked for

You do not need to switch your main extractor to Tika.

Use **Apache Tika Pipes** as an ingestion/audit pattern or broad file-health probe.

Current Tika 4 server/Pipes interfaces support batch parsing and return per-document result status/messages rather than simply disappearing a failed document. Tika's `PipesForkParser` is specifically designed to isolate parsing in forked processes so parse exceptions, crashes, OOM conditions and timeouts can be surfaced as document-level results. citeturn8search0turn8search5

Tika 4 has also moved error handling towards structured responses and correct HTTP statuses. citeturn8search2

**Maintenance:** Apache project, current 4.x documentation. citeturn8search0turn8search2

**Setup:** **2–4 hours** to run it; **4–8 hours** to integrate its statuses into your own manifest.

**Cost:** **PKR 0 software**.

**Failure:** a parser returning success does not mean the document is semantically useful. An image-only PDF may technically parse while yielding essentially no text. You still need your own classification layer.

**Confidence: high as an auditing primitive, not as a replacement extractor.**

### The cheapest correct coverage system is a tiny manifest, not another indexing product

This is one of the places where the answer really is “write 300 lines of boring code”.

The critical design decision is:

> **Inventory the universe first; process second.**

Bad ingestion:

```text
for document emitted by parser:
    index(document)
```

There is no denominator. Failed input can vanish.

Correct ingestion:

```text
walk filesystem
↓
manifest every discovered file
↓
attempt every eligible file
↓
record one terminal state for every file
↓
assert accounting identity
```

Terminal states should be explicit:

```text
indexed
failed_corrupt
failed_encrypted
failed_permission
failed_parser
failed_timeout
failed_changed_during_read
unsupported_type
image_only_no_text
zero_byte
skipped_policy
duplicate_content
pending
missing_since_last_scan
```

Then:

```text
discovered =
    indexed
  + failed
  + skipped
  + pending
```

must always hold.

A useful command should literally print:

```text
Corpus generation: 2026-09-09T12:14:03+05:00

Discovered files               48,100
Successfully addressable       47,203   98.14%
Failed                            897    1.86%

Failure breakdown
  encrypted PDF                   112
  corrupt PDF                      37
  permission denied                18
  parser exception                126
  extraction timeout               9
  image-only / no text            441
  unsupported                      98
  zero-byte                        56

Addressable evidence units     386,492
Tables                          34,201
Pages                          129,118
Canonical series                 6,481
```

And:

```bash
research-index failures --reason parser_exception
```

must give paths, content IDs, parser version and error.

I would keep this in SQLite because it is boring, transactional, inspectable and already fits the round-one architecture. There is no need for a second infrastructure service just to count files.

### Watchman is the strongest watcher for the “tree never stops moving” case

**Watchman**, maintained primarily by Meta's source-control team, exists specifically to watch files, record changes and trigger actions when matching files change. The repository has more than 14,000 commits and supports current Windows, macOS and Linux builds. citeturn31view0

**Maintenance:** very active, institutionally maintained. citeturn31view0

**Cost:** **PKR 0**, MIT licensed. citeturn31view0

**Setup:** **3–6 hours** including translating events into manifest/index updates.

**How it fails:** the watcher cannot tell you what happened while it was not running. That means it is an acceleration mechanism, never your sole correctness mechanism.

**Confidence: high.**

### watchfiles is easier if everything else is Python

If you prefer not to introduce Watchman's daemon, **watchfiles** is a tiny Python-facing alternative implemented on Rust filesystem notifications:

```bash
pip install watchfiles
```

It supports Python 3.10–3.15 and Linux/macOS/Windows and can recursively yield filesystem changes or trigger a process. citeturn31view1

**Setup:** **1–3 hours**.

**Cost:** **PKR 0**, MIT licensed. citeturn31view1

**Confidence: high for a personal workstation; Watchman is the more industrial choice.**

### Refresh strategy I would actually deploy

Use two layers.

**Fast path: filesystem watcher**

```text
add     → manifest + index
change  → compare content identity → re-extract/index if bytes changed
unlink  → remove current path alias
rename  → new path + same content ID → relink without reembedding
```

**Correctness backstop: reconciliation on every Claude session start**

```text
research-index reconcile --fast
```

It should:

```text
rescan paths
compare against prior generation
discover watcher downtime changes
repair path aliases
queue genuinely new/changed content
mark vanished files
verify no indexed object points only at a dead path
```

Use a full content hash only when needed. A cheap initial comparison of path/stat metadata can identify most unchanged files; new or suspicious files can then be hashed.

Before Claude opens evidence, your MCP resolver should also resolve:

```text
stable content ID → current path
```

and fail loudly if it cannot.

Do **not** hand Claude an old stored path and hope.

Your refresh strategy therefore becomes:

```text
watcher            low latency
+
SessionStart audit correctness
+
stable content IDs rename resilience
+
generation ID      query reproducibility
```

**The user is right on this contradiction.** The immutability of archival PDFs reduces re-extraction cost; it does not remove index-staleness risk.


## Omission reporting: what can be explained, and what cannot be proved

This requirement needs one blunt correction.

> **No practical semantic retriever can honestly prove that the other 47,995 files are irrelevant.**

A top-k result means:

```text
these were ranked highest by this retrieval procedure
```

not:

```text
every omitted document has been semantically proven unrelated
```

Dense similarity scores are not probabilities. ANN/vector search does not constitute a logical exhaustive proof. Reranker scores do not acquire that property either.

There is meaningful research on making retrieval coverage measurable, but it does not change this basic limitation.

For example, recent work on conformal context filtering attempts statistical coverage guarantees under calibration assumptions rather than universal semantic proofs. citeturn9academia10 Q-CARE, published in 2026, proposes query decomposition and reference-free coverage-aware retriever evaluation, but again this is an evaluation method, not proof that a production corpus contains no answer. citeturn9academia11

The existence of dedicated unanswerable-RAG benchmarks such as CRUMQs is itself evidence that distinguishing “the corpus does not support an answer” from failed retrieval remains an open problem. citeturn10academia9 Recent work on detecting sufficient/insufficient/conflicting context improves that classification experimentally, but one approach relies on internal model activations—which you cannot access inside hosted Claude. citeturn10academia8

### What you can produce is a retrieval receipt

Every corpus query should return a machine-readable audit object along with the evidence:

```json
{
  "corpus_generation": "2026-09-09T12:14:03+05:00",
  "coverage": {
    "discovered_files": 48100,
    "addressable_files": 47203,
    "failed_files": 897
  },

  "query": "Pakistan automobile production trajectory",

  "query_expansions": [
    "automobile production Pakistan",
    "passenger cars production",
    "motor vehicles manufacturing",
    "LCV jeep production"
  ],

  "retrieval_passes": [
    {
      "type": "lexical",
      "searched_units": 386492,
      "returned": 72
    },
    {
      "type": "semantic",
      "indexed_units": 386492,
      "returned": 50
    },
    {
      "type": "visual_page",
      "indexed_pages": 129118,
      "returned": 20
    }
  ],

  "union_candidates": 103,
  "reranked": 30,
  "opened": 8,

  "selected_evidence": [
    "research://.../page/340/table/4.2",
    "research://.../page/117/table/7"
  ],

  "unavailable_corpus": {
    "count": 897,
    "by_reason": {"encrypted":112, "...":"..."}
  }
}
```

Now when somebody asks:

> “Why didn't you look at the other 47,995?”

the honest answer is:

> “They were represented in the indexed corpus but were not selected by any of the lexical/semantic/visual candidate passes above; 103 candidates survived first-stage retrieval, 30 were reranked, and eight evidence units were opened. Separately, 897 files were not searchable and are listed in the failure report.”

That is explainable retrieval.

It is **not** a claim that each omitted file was read and disproved.

### Phoenix plus OpenInference gives you a ready-made trace layer

**Arize Phoenix** is an actively developed AI-observability/evaluation project; its repository currently has almost 10,000 commits. **OpenInference** provides OpenTelemetry instrumentation conventions for AI observability. citeturn31view2turn31view3

I would use them only to store/inspect retrieval spans:

```text
query
 ├─ rewrite
 ├─ FTS retrieval
 ├─ semantic retrieval
 ├─ visual retrieval
 ├─ dedupe
 ├─ rerank
 ├─ evidence fetch
 └─ answer
```

The authoritative audit should still be your own small JSON receipt, because you need it to become an MCP return value, not just an observability dashboard.

**Setup:** **2–4 hours** once the retrieval function exists.

**Incremental cash:** local/self-hosted tooling can be run without per-query model charges; storage/compute remains yours.

**Failure:** tracing shows *what your retriever did*. It cannot tell you whether your retriever should have discovered something it never surfaced.

**Confidence: high for traceability; zero as a magical omission proof.**

### RAGChecker is for testing the retriever, not explaining an individual question

Amazon Science's **RAGChecker** performs fine-grained evaluation of retrieval and generation behaviour. It is useful for a test set where you know the expected evidence/answer. citeturn9search0turn9search3

That lets you measure questions such as:

```text
"When the correct evidence was somewhere in this project,
how often was it in top 5?"
```

Build perhaps 100–300 benchmark questions from real work:

```text
query
known evidence addresses
known answerability
```

Then measure retrieval recall whenever you alter chunking, reranking or indexing.

This matters because a search system that “feels good” on five examples is exactly how silent omissions survive.

**Setup:** **4–8 hours** once you have a gold query/evidence set.

**Cost:** project itself open source; evaluator model calls may cost money depending on configuration.

**Failure:** requires ground truth; therefore not a per-query coverage proof.

**Confidence: high as regression testing.**

### The correct wording for “not in corpus”

Do not allow the agent to emit:

> “This information is not in the corpus.”

from an ordinary top-k miss.

Allow:

> “I found no supporting evidence in the currently indexed corpus.”

and attach:

```text
indexed coverage: 47,203 / 48,100 files
failed/unavailable: 897
retrieval strategies used: lexical + semantic + visual page
broadened second pass: yes
```

For high-value questions I would implement:

```text
query
 ↓
retrieve narrowly
 ↓
evidence sufficient?
 ├─ yes → answer
 └─ no
      ↓
   expand synonyms/query decomposition
   raise candidate K
   search series registry
   use exact lexical pass
   visual page search
      ↓
   evidence sufficient?
   ├─ yes → answer
   └─ no → "insufficient evidence found"
```

For an exact identifier, filename, SRO number, quoted phrase or numeric series ID, exhaustive lexical/database search can provide a much stronger negative statement.

For an arbitrary semantic proposition, **the honest state of the art does not give you a corpus-wide proof of absence.**

That is not an engineering failure. Pretending otherwise would be one.


## Claude Code delivery: MCP plus hooks is the answer, and Glob/Grep can actually be blocked

This changed materially from the simplistic “put instructions in CLAUDE.md and hope” picture.

The best architecture is not MCP *versus* hooks *versus* skill.

It is:

> **MCP = capability**  
> **hooks = enforcement/lifecycle**  
> **permissions = hard tool policy**  
> **skill/CLAUDE.md = workflow semantics**

### MCP should be the corpus front door

Expose a small purpose-built local MCP server with tools such as:

```text
research_search(
    query,
    project?,
    kinds?,
    date_range?,
    top_k?
)

research_open(
    evidence_address
)

research_series(
    query_or_series_id
)

research_related(
    evidence_address
)

research_coverage()

research_failures(
    reason?
)

research_explain(
    query_id
)
```

`research_search` should return **evidence units, not arbitrary file paths**.

Example:

```text
1. PBS Statistical Yearbook 2023
   page 340 · Table 4.2
   relevance: ...
   address: research://abc/page/340/table/4.2

2. PBS Statistical Yearbook 2020
   page 327 · Table 7
   same canonical series:
   pbs.auto.passenger_cars.units.annual
```

The MCP process talks to your local manifest/index/series registry. Claude's context contains only the result it asked for.

### Can you actually get ahead of built-in Glob and Grep?

**Yes. This is stronger than “tell Claude not to use them”.**

Current Claude Code permissions support bare tool-name deny rules, and the CLI exposes `--disallowedTools`; disallowed tools can be removed from Claude's usable tool context. citeturn13view0turn13view1

So the blunt configuration is:

```text
deny Glob
deny Grep
```

and leave your MCP search tools available.

That is a real hard lever.

I would probably not do it globally, because Glob/Grep remain useful when Claude is editing your scripts.

Instead use a **PreToolUse hook**.

Current Claude Code hooks run before tool calls and can deterministically deny a tool invocation and give Claude a reason. The denial happens before normal permission handling; the hook can inspect the tool name and input. citeturn13view2

Conceptually:

```text
Claude tries:
Glob("~/research/**/*survey*")

PreToolUse:
DENY
"Do not crawl the research corpus with Glob.
Use research_search through the research MCP server."

Claude:
research_search("survey ...")
```

You can allow:

```text
Glob(.claude/**)
Grep(..., scripts/)
```

but deny broad corpus crawls.

This is the answer to your specific “can I replace/intercept the tool path?” question:

**Intercept/deny: yes.**  
**Remove completely: yes.**  
**Transparently rewrite one built-in Glob call into an MCP tool call under the same invocation: I found no supported mechanism.**

A PreToolUse hook can alter inputs/add context or deny the invocation, but the clean design is to deny it and direct Claude to the MCP tool. citeturn13view2

### A real user has already used this enforcement pattern

This is not just documentation.

Claude Code issue **#22699** describes a working third-party `smart-read` PreToolUse hook. It intercepts Read calls, runs a line-count preflight, denies oversized reads, and tells the model to use offset/limit or Grep instead. The reporter says the agent adapts quickly once denied. citeturn28search1

That is virtually the same enforcement structure you need:

```text
smart-read:
Read → hook → reject → alternative tool

your system:
Glob/Grep corpus crawl → hook → reject → research MCP
```

So this is a proven Claude Code extension pattern, not merely something the hooks API theoretically permits.

### Hooks can also solve session-start freshness

Claude Code currently has lifecycle hooks including `SessionStart`, `PreToolUse`, `PostToolUse` and `FileChanged`. citeturn13view2turn13view3

I would configure SessionStart to run:

```bash
research-index reconcile --fast
```

and feed a tiny status back into Claude:

```text
Research corpus ready.
Generation: 2026-09-09T12:14+05:00
47,203 / 48,100 files addressable.
897 ingestion failures.
Use research_search before filesystem search for research evidence.
```

That removes the “did I remember to update it?” failure mode.

Current `FileChanged` hooks can also observe add/change/unlink events; watch paths can be supplied dynamically by session/cwd hooks. citeturn13view3

I would **not** make Claude Code's FileChanged mechanism the sole watcher for a tens-of-thousands-file corpus. Watchman/watchfiles should maintain the corpus independently; Claude's SessionStart hook verifies/reconciles it.

That way the corpus is healthy even when Claude Code is not running.

### Skills are useful but not enforcement

Claude Code Skills are instruction bundles loaded when relevant; they can also run in a forked subagent and declare tool restrictions. citeturn11search2turn12search3

Make one:

```text
.claude/skills/research-corpus/SKILL.md
```

whose job is to teach:

```text
- use research_search for evidence discovery
- cite evidence addresses
- ask research_series for longitudinal statistics
- inspect research_coverage before strong absence claims
- never infer extraction provenance from filenames
```

But a skill by itself is not enough, because model invocation of the skill is still part of agent behaviour.

**Use hooks/permissions for hard constraints; Skills for policy.**

### CLAUDE.md belongs at the bottom of the hierarchy

Put perhaps ten lines in it:

```text
The research corpus is indexed and exposed through research_* MCP tools.
For research evidence discovery, use research_search before Glob/Grep.
Evidence citations must use returned evidence addresses.
Use research_series for longitudinal statistics.
Do not claim corpus absence without research_coverage/research_explain.
```

Nothing more.

CLAUDE.md has no execution mechanism. It does not refresh an index. It cannot itself prevent the built-in tools. A documented issue about large-file reads explicitly notes that CLAUDE.md workarounds can be ignored whereas PreToolUse hooks provide deterministic enforcement. citeturn28search1

### Subagents become much more useful after this

Current Claude Code custom subagents can have their own tool allowlists/denylists, MCP servers and specialised instructions. citeturn12search2

I would create roughly:

```text
source-hunter
  tools:
    research_search
    research_open
    research_related

series-analyst
  tools:
    research_series
    research_open
    Python/analysis tools

contradiction-checker
  tools:
    research_search
    research_open
    research_explain

synthesiser
  receives:
    evidence addresses + analysis from others
```

Every one of them queries the **same corpus layer**.

This is critical:

> Four subagents independently Glob-ing the tree are not four times smarter. They are four opportunities for silent partial traversal.

Parallelism belongs **above** the index, not instead of it.

### Delivery-mechanism scorecard

| Mechanism | Invocation | Automatic refresh | Can stop Glob/Grep? | Role here |
|---|---|---:|---:|---|
| **MCP server** | Claude selects named tools | Server can maintain its own index; not inherently session lifecycle | No | **Primary interface** |
| **PreToolUse hook** | Deterministic before matching tool calls | Can run checks | **Yes, conditionally** | **Enforcement** |
| **SessionStart hook** | Automatically every session | **Yes** | N/A | **Reconciliation/status** |
| **FileChanged hook** | On watched changes | Yes while CC active | N/A | Secondary notification |
| **Skill** | relevance-driven or explicit | No persistent watcher | Can restrict tools inside skill/subagent | Workflow |
| **CLAUDE.md** | loaded as instructions | No | No | Tiny policy reminder |
| **permissions / `--disallowedTools`** | client policy | N/A | **Yes, absolutely** | Hard global block |
| **plain scripts** | MCP/hooks/shell call them | Whatever you implement | Not alone | Actual implementation |

The docs support the hook, permission, skill, CLI and subagent behaviours above. citeturn13view0turn13view1turn13view2turn13view3turn12search2turn12search3

**My implementation estimate:** once the underlying index commands exist, **4–8 hours** to build the MCP façade and hooks; **1–2 focused days** to harden tool contracts, error paths and receipts.

**Incremental money:** **PKR 0** for local scripts/MCP/hooks beyond your existing Claude plan.

**Confidence: very high.**


## Claude Code bug verification

These claims are not equally solid.

### Bug status table

| Claim | Verdict | Current evidence |
|---|---|---|
| **#16043 — Glob/ripgrep timeout silently becomes zero results** | **Real, correct issue number** | Closed as duplicate |
| **#12534 — subdirectories disappear in large repos** | **Real issue, but your wording overstates it** | Closed as duplicate; reporter explicitly says CLI worked |
| **#42542 — silent microcompaction clears tool results from ~2.1.89** | **Real and currently open** | Strong filed reproduction; affected reporter saw 2.1.90, last good 2.1.81 |
| **Read truncates at 2000 lines with no error** | **The 2,000-line behaviour is real; calling it a single current Read “bug” is misleading** | Default Read limit exists; separate issues document contradictory/`@` behaviour |

### Glob timeout: issue #16043

The issue is real and has exactly the title you described: **“Glob silently fails when large .gitignore'd directories cause ripgrep timeout”**. It was opened January 2, 2026 and is currently **closed as duplicate**. citeturn1view0turn2view1

The reporter's reproduction is unusually good:

- Claude Code version **2.0.76**;
- Glob invokes ripgrep with `--no-ignore --hidden`;
- a 107 GB ignored ActiveStorage directory makes the operation exceed roughly ten seconds;
- Claude Code sends SIGTERM to ripgrep;
- the Glob result presented to the agent is effectively “No files found” rather than an explicit timeout;
- manually letting the equivalent search finish took about 10.5 seconds and found the expected file. citeturn2view1

That is therefore a legitimate example of exactly the failure class you've seen: **a tool failure converted into apparently valid negative evidence**.

The practical workaround in the report is to remove/move the enormous ignored directory or otherwise stop it being scanned.

What I **cannot substantiate** from the fetched issue is a specific Claude Code version in which this was fixed. “Closed as duplicate” means this issue record was deduplicated; it does not by itself prove the underlying bug was fixed.

So in a senior-facing document I would say:

> “Anthropic's Claude Code tracker has a filed reproduction (#16043, version 2.0.76) in which Glob's internal ripgrep process is terminated after a large-tree timeout and the tool reports no files rather than surfacing the timeout. The ticket is closed as a duplicate; I did not find a verified fix version.”

**Confidence: high on existence/behaviour; medium on current susceptibility because the issue does not establish a fix version.**

### Invisible subdirectories: issue #12534

The number is real, but this one should **not** be used as evidence that the terminal Claude Code agent loses nested filesystem visibility.

Issue #12534 is titled **“VS Code Extension cannot detect files in subdirectories of large codebases.”** It was opened November 27, 2025 and is closed as a duplicate. citeturn1view1turn2view2

Crucially, the reporter says the opposite about the terminal client:

> the **terminal CLI could see all files including subdirectories perfectly**, while the VS Code extension's nested `@` file browsing failed. citeturn2view2

The reported workaround was to open VS Code directly on the smaller subfolder. The issue listed the affected extension as version “1.0.x or higher (latest)” at the time. citeturn2view2

Therefore this claim:

> “#12534 proves subdirectory contents become invisible to Claude Code in large repositories”

is **wrong**.

This claim is supportable:

> “#12534 documents a large-repository nested-file discovery problem in the Claude Code VS Code extension; the same reporter says the terminal CLI did not exhibit it.”

Again, I found no verified fix-version evidence attached to the material I could retrieve.

**Confidence: very high.**

### Silent microcompaction: issue #42542

This one is real and more relevant to your “context rot” concern than I expected.

Issue #42542 is currently **open**, labelled as a core bug with a reproduction. The reporter describes previous tool outputs being silently replaced by:

```text
[Old tool result content cleared]
```

without the normal visible compaction notification. citeturn1view2turn2view0

The reported environment is:

```text
Claude Code 2.1.90
Opus 4.6 with 1M context
Ubuntu
```

and the reporter says the last version they had used without the problem was **2.1.81**, with the behaviour appearing around **2.1.89/2.1.90**. citeturn2view0

The issue's analysis identifies multiple internal microcompaction paths and says:

```text
DISABLE_AUTO_COMPACT=true
```

does **not** disable these microcompactions, whereas:

```text
DISABLE_COMPACT=true
```

does, but also disables manual compaction and is therefore a fairly blunt workaround. citeturn2view0

As of the issue state I fetched, it remains open and I found no linked fixed release.

One qualification: “regression since v2.1.89” is the reporter's observed regression boundary, not an Anthropic post-mortem proving that exact release introduced the root cause.

Senior-facing wording:

> “Open issue #42542 contains a reproducible report that Claude Code 2.1.90 can silently clear older tool results during long 1M-context sessions, with the reporter placing the regression between 2.1.81 and roughly 2.1.89/2.1.90. `DISABLE_AUTO_COMPACT` reportedly does not prevent it; `DISABLE_COMPACT` does but disables all compaction. The issue remains open.”

**Confidence: high that the issue and observed behaviour are real; medium-high that v2.1.89 is the exact regression point.**

### The 2,000-line Read claim needs rewriting

Claude Code's **2,000-line default Read limit is real**, but the history is messy enough that “Read silently truncates at 2,000 lines with no error” should not be presented as one straightforward filed current bug.

Issue #6910, on Claude Code **1.0.98**, actually reports the *opposite*: although the tool description said Read should default to 2,000 lines, the tool tried to process a 20,010-line file wholesale and instead hit its token ceiling. The issue was closed as not planned. citeturn28search0

A later issue, #22699, describes the present user-visible problem as Read loading up to its 2,000-line limit even when most of that content is unnecessary, and proposes a PreToolUse guard that blocks oversized reads before the context is consumed. citeturn28search1

Issue #20223 supplies more direct evidence for **silent truncation with the `@` attachment mechanism**: the reporter tested a 5,000-line file and observed only the first 2,000 lines entering context without an explicit warning. The issue says both CLI and VS Code exhibited the behaviour. citeturn28search2

So I would write:

> “Claude Code's Read tool has a default 2,000-line read boundary; explicit `offset`/`limit` should be used for large text files. There are separate filed issues around inconsistent enforcement of that boundary, and #20223 documents silent 2,000-line truncation for `@` file attachment. I would not describe the normal Read boundary itself as a bug.”

The workaround is exactly what your corpus layer avoids: retrieve the relevant evidence unit first, then Read only that small object or page.

And you can enforce that with the same PreToolUse pattern documented by the working `smart-read` proof of concept in #22699. citeturn28search1

**Confidence: high on the 2,000-line default/behaviour; medium on any blanket claim that current Read itself always truncates silently.**


## What I would install and build

The smallest system I think actually reaches your stated goal is surprisingly modest.

### The installable pieces

**Core page retrieval**

```bash
pip install -U "sentence-transformers[image]"
```

Use `MultiVectorEncoder` and start with a tested ColQwen-family visual document retriever such as `vidore/colqwen2.5-v0.2`. citeturn24search0turn24search6

**Optional long-document hierarchy**

```bash
pip install -U pageindex
```

for selected 200–1,000-page text-heavy reports. citeturn27view0

**Statistical identifiers**

```bash
pip install sdmx1
```

for publishers that expose SDMX structure/series keys. citeturn15search1turn15search2

**Cross-table matching**

```bash
pip install valentine
```

for schema/column candidate matching. citeturn18view0

Add **pyJedAI** if the canonical-series entity-resolution problem becomes large enough to need an actual ER pipeline. citeturn18view1

**Filesystem watching**

For easy Python integration:

```bash
pip install watchfiles
```

citeturn31view1

or use **Watchman** when you want the watcher to be a separate robust service maintained independently of the Python process. citeturn31view0

**Coverage probe**

Run **Apache Tika 4/Pipes** alongside your chosen extractor to classify broad format/parser failures and preserve per-file processing outcomes. citeturn8search0turn8search5

**Tracing**

Use **Phoenix/OpenInference** if you want a UI and trace store around the retrieval receipts. citeturn31view2turn31view3

### The custom part is four deliberately boring components

I would call them:

```text
research-index
research-search
research-series
research-mcp
```

`research-index` owns:

```text
file manifest
content IDs
path aliases
evidence-unit table
failure table
index generation
filesystem watcher
```

`research-series` owns:

```text
canonical series
aliases
series/evidence mappings
candidate reconciliation
```

`research-search` owns:

```text
query expansion
existing round-one lexical/semantic index
page-visual retrieval
reranking
evidence-unit fetch
retrieval receipt
```

`research-mcp` exposes these operations to Claude.

### A query would execute like this

```text
User:
"what happened to passenger-car production after the 2016 auto policy?"

Claude
  ↓
research_search(...)
  ↓
hybrid corpus search
  ├── textual evidence units
  ├── visual PDF pages
  ├── policy documents
  └── series registry
  ↓
returns:
  policy.pdf p.18 section 3.1
  Yearbook 2017 p.311 table 8
  Yearbook 2018 p.319 table 8
  ...
  Yearbook 2025 p.340 table 4.2
  canonical series ID
  retrieval receipt
  ↓
Claude asks:
research_series(series_id)
  ↓
structured longitudinal observations +
each value's exact source evidence
  ↓
maybe quantitative subagent computes trajectory
  ↓
qualitative subagent reads policy clauses
  ↓
synthesiser gets:
numbers + source addresses + analysis
```

Claude never has to discover:

```text
"Was it under pbs? provincial? extractions? old?"
```

Those distinctions have ceased to be retrieval concerns.

### The first build order

I would spend the first block of work on **identity and accounting**, not sophisticated retrieval.

**Rough effort, assuming round one's extractor/store already exists:**

| Work | My estimate |
|---|---:|
| manifest + coverage report | 4–8 hours |
| content-ID/path-alias logic | 3–5 hours |
| evidence-address schema + subdocument ingestion | 4–8 hours |
| page visual search POC | 4–8 hours |
| MCP server | 4–6 hours |
| Claude SessionStart + PreToolUse hooks | 2–4 hours |
| retrieval receipt | 3–5 hours |
| initial series registry | 4–8 hours |
| Valentine candidate matcher | 4–8 hours |
| watcher/reconciliation | 3–6 hours |
| first real retrieval benchmark | 4–8 hours |

So a convincing MVP is roughly **three to five focused days**, not a three-month platform project. A version I would trust with serious research is more like **one to two weeks of hardening plus the unavoidable series-curation work**.

Almost all of that can remain **PKR 0 in incremental software cost** using local models and the round-one local index. The obvious recurring exceptions are any external model calls used by PageIndex and any cloud/GPU service you choose to rent. PageIndex's own published local indexing example works out around **PKR 277 per thousand pages** at the current exchange-rate assumption, before query calls. citeturn27view0turn23search1

### What I would not build

I would not build a giant knowledge graph over every extracted sentence.

I would not put an LLM in the ingestion critical path for deciding whether a file succeeded.

I would not let canonical series identity exist only as embeddings.

I would not use pathnames as document IDs.

I would not make filesystem watchers the only freshness mechanism.

I would not make one vector similarity score the definition of “relevant”.

I would not have subagents independently browse the whole directory tree.

And I absolutely would not allow:

```text
0 retrieval results
```

to silently mutate into:

```text
there is no evidence
```

given that issue #16043 demonstrates exactly why those are different statements. citeturn2view1


## Searches that came back empty or weaker than expected

These matter because several holes in the ecosystem are genuine rather than things I simply failed to name.

**A turnkey “same statistical series across annual PDFs” product:** I found none. Searches around schema matching, table-union search, entity resolution, data-lake discovery, statistical-series IDs, LLM schema matching and annual-report reconciliation led to Valentine, Starmie, Pylon, pyJedAI and SDMX—but nothing that solves the full PDF-to-canonical-series problem without you maintaining canonical identity. citeturn16academia3turn15academia9turn15academia10turn18view1

**Pakistan Bureau of Statistics SDMX / useful official statistical API:** targeted searches for PBS + SDMX/API did not surface a convincing official statistical-series service. Search results mostly surfaced the PBS web site and generic mentions of “API” as an acronym. In contrast, the same search did surface SBP EasyData's explicit metadata-API announcement. citeturn20search0turn20search1

**A query-time proof that every omitted document is irrelevant:** none. The current research I found focuses on retrieval evaluation, calibrated coverage or answerability detection, not logical corpus-wide omission certificates. citeturn9academia10turn9academia11turn10academia8turn10academia9

**A system that can honestly prove a semantic fact “isn't in the corpus” without exhaustive semantic understanding:** none. This remains an open reliability problem; the defensible output is “no supporting evidence found under these retrieval procedures and this ingestion coverage”.

**A supported Claude Code facility that transparently substitutes an MCP search call *inside* an attempted built-in Glob/Grep invocation:** none found. Claude Code can deny/remove tools and hooks can conditionally intercept them, which is enough to force the agent towards MCP; I found no supported same-call transparent replacement mechanism. citeturn13view0turn13view1turn13view2

**Authoritative proof that #16043 is fixed in a particular release:** not found. The issue exists and is closed as a duplicate, but the material I could verify did not establish a fix version. citeturn2view1

**Authoritative proof that #12534 reflects a CLI large-tree bug:** the search produced the opposite. The issue is specifically about the VS Code extension, and its reporter says CLI traversal worked. citeturn2view2

**A clean current bug corresponding to “Read always silently truncates at 2,000 lines”:** not found in that exact form. What exists is a documented/default 2,000-line Read boundary, an older issue where Read sometimes ignored it and hit a token error, and a separate reproducible report of silent 2,000-line truncation through `@` attachments. citeturn28search0turn28search2

**Evidence that PageIndex OSS by itself is already a drop-in thousands-of-documents research filesystem:** weaker than the marketing headline. Its local/open-source system is excellent for document hierarchy, but the repository explicitly positions large multi-document File System scaling and MCP as Cloud capabilities; its public OSS benchmark is also prose-fact-heavy rather than a test of ugly statistical tables. citeturn27view0

The consequence of all of this is fairly clean:

**You do not need a cleverer agent to crawl the asscrack of the directory tree. You need to make “the asscrack of the tree” cease to exist from the agent's perspective.**

Give every meaningful piece of evidence a stable address. Give every file a manifest state. Give recurring statistical concepts permanent IDs. Make retrieval produce receipts. Keep paths mutable. Make the index reconcile itself. Put that behind MCP. Then use Claude Code's current hooks and permissions to make that MCP service the unavoidable front door.

That gets much closer to the actual goal than teaching Claude to crawl harder.