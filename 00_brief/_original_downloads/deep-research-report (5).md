# Making a Huge Research Folder Reliably Searchable to CLI Agents

## The diagnosis: the folder is not the real problem

Your framing is close, but one part is wrong: **thousands of files nested several levels deep is not intrinsically “too large” for a filesystem or a search index. It is too large for an agent that treats filesystem exploration as ad-hoc browsing.**

Recoll, an ordinary full-text desktop indexer built on Xapian, documents deployments with **11+ million documents and indexes hundreds of gigabytes in size**. Your corpus—thousands or tens of thousands of files—is tiny by information-retrieval standards. citeturn19search0turn19search1

The failure is this:

> **You are asking a probabilistic agent to perform discovery, retrieval, context selection and reasoning all at once by walking a tree through bounded tools.**

That is not a reliable architecture.

A coding agent does not literally “see `~/research`”. It gets tools such as file search, `grep`, directory listing and file read. Those tools may respect ignore rules, cap result counts, omit hidden files, truncate outputs, limit file sizes or simply not be invoked on branches the model never decides to inspect. `fd`, for example, deliberately ignores hidden paths and `.gitignore` matches by default; its own maintainer has called ignored-file behaviour a major pitfall for users. citeturn20search6turn20search2

There are also **actual agent-tool bugs**, not merely fundamental model limits. Claude Code has had user reports where `@` file discovery failed to find most files, where its editor integration omitted `.py` files, and where file search became painfully slow in large trees. Another Claude Code report found its Search task walking millions of ignored paths with `find`; the reporter proposed `rg` specifically because the underlying search method was the bottleneck. citeturn23search32turn23search24turn23search0turn23search4

So the first conclusion is fairly strong:

**Do not solve this primarily by reorganising the folders. Build a persistent retrieval layer in front of them.**

The system you actually want has five separate responsibilities:

1. **Complete inventory:** it knows every file exists, including ignored, hidden and deeply nested material.
2. **Document understanding:** PDF/DOCX/XLSX/email/etc. are converted into searchable text without destroying tables, page references or metadata.
3. **Retrieval:** filename/path search + exact full-text/BM25 + semantic vector search + reranking.
4. **Lineage:** it knows `table.csv → came from → report.pdf`, and ideally `claim → supported by → table.csv/report.pdf`.
5. **Fail-closed agent access:** the LLM queries that layer rather than wandering the filesystem, and the layer reports when indexing is stale or incomplete.

The last point matters most. **A better search engine that can silently have 4% of the corpus missing has recreated your original problem.**

My overall recommendation is:

> **For the serious local solution: Docling → LanceDB hybrid index + Recoll/ripgrep-all lexical safety net + a small provenance SQLite DB/DataLad → expose six MCP tools to the coding agent.**
>
> **For the least engineering: LlamaParse Index + its MCP is currently the closest off-the-shelf product I found to exactly the interface you described.**
>
> **For “make this useful tonight”: install Recoll and `pdf-mcp` first.**

Confidence in that conclusion: **high**.

## The things that actually fit the problem

The important distinction below is between a **component** and a **complete solution**. A lot of “RAG” software looks relevant until you notice it does not guarantee corpus coverage, cannot search exact identifiers, cannot parse your mixed files, or has no concept of provenance.

| Thing | Fit to your goal | Maintained? | Software cost | My setup estimate | Main failure mode | Confidence |
|---|---|---:|---:|---:|---|---|
| [LlamaParse Index + MCP](https://developers.llamaindex.ai/llamaparse/cloud-index-v2/getting_started/) | **Closest turnkey whole-corpus agent interface** | Very active in 2026 | Starter currently $50/month + usage credits | 1–3 hours + upload time | Cloud dependency, sync semantics, cost, provenance still separate | **High** |
| [Recoll](https://www.recoll.org/) | **Best boring local universal lexical index** | Active | $0 | 30–90 min | Not semantic; parsers/helpers can fail | **Very high** |
| [Docling](https://docling-project.github.io/docling/) | **Best local normalisation/parser layer I found** | Very active | $0 | 1–4 hours | Heavy PDFs/OOM edge cases; parser != search | **High** |
| [LanceDB](https://docs.lancedb.com/) | **Excellent embedded hybrid retrieval store** | Active | $0 OSS locally | 3–8 hours with ingestion code | You must build ingestion/metadata correctly | **High** |
| [pdf-mcp](https://github.com/jztan/pdf-mcp) | **Excellent immediate answer for giant PDF branches** | Very active/newer project | $0 | 10–30 min | PDF-only | **Medium-high** |
| [ripgrep-all](https://github.com/phiresky/ripgrep-all) | **Excellent verification/fallback search** | Maintained, slower cadence | $0 | 10–20 min | No semantic retrieval; extraction occurs around search/cache | **High** |
| [DataLad](https://docs.datalad.org/) | **Best fit here for recording extraction lineage** | Active | $0 | Half-day–2 days | Only knows lineage you actually record | **High** |
| [mcp-local-rag](https://github.com/shinpr/mcp-local-rag) | Interesting ready-made local MCP hybrid search | Active small project | $0 | 10–30 min | Primarily pitched at code/technical docs; parser breadth less convincing | **Medium** |
| [RO-Crate](https://w3id.org/ro/crate/) | Standard for portable research metadata/provenance | Active standard | $0 | Moderate | A standard, not an automatic indexer | **High for provenance, not retrieval** |

### LlamaParse Index and MCP

This is the product that most directly made me think: **“they are solving the same problem.”**

Its current Index API takes a directory of documents, parses, chunks, embeds and indexes them. Its retrieval endpoint does **hybrid vector + full-text search, metadata filtering and reranking**. citeturn16search2turn16search3

More importantly, the MCP exposes:

- `findFilesInIndex`
- `grepFileFromIndex`
- `readFileFromIndex`
- `retrieveFromIndex`

The first searches names, the second performs regex search inside parsed files, the third reads document text, and the fourth performs semantic/full-text hybrid retrieval. citeturn16search0turn16search2

That is almost precisely the abstraction you asked for. LlamaIndex itself described its 2026 “Retrieval Harness” as giving agents **filesystem-level list/grep/read plus hybrid retrieval**, specifically so agents can traverse and verify a corpus instead of trusting one semantic search result. citeturn16search1

So to your phrase:

> “mentioning a thing that only exists inside the asscrack of the thing as if it’s on root”

**Yes. That is essentially what this interface provides.** The physical path stops being the primary lookup mechanism. The agent searches an index representing the entire corpus.

Current pricing is the obvious downside. The Index getting-started documentation currently requires a **Starter, Pro or Enterprise** account. LlamaIndex lists Starter at **$50/month with 40,000 credits**, Pro at $500/month, and charges $1.25 per 1,000 additional credits. Parse modes range from 1 to 45 credits per page depending on tier, and other platform operations also consume credits. citeturn15search0turn15search7turn16search3

It also needs a proper synchronisation wrapper. Their documentation explicitly warns that after adding/updating/removing files you must trigger an index sync, and that merely checking for `status == ready` can incorrectly tell you a new sync is finished; they recommend comparing `last_synced_at` as well. citeturn17search0

That warning is telling: **even a managed retrieval system can silently serve stale knowledge if the integration is naïve.**

**Verdict:** closest turnkey answer I found. Use it if cloud processing, monthly cost and uploading the research corpus are acceptable.

### Recoll

Recoll is much less fashionable and, for this reason, possibly more useful.

It is a desktop/document full-text search engine using Xapian. It handles filenames and contents, Boolean queries, phrases, proximity, wildcards, document types, directory filtering, archives and nested containers such as attachments inside email/archives. It offers GUI, CLI and Python APIs. citeturn19search0turn19search6

The scale is not remotely a concern: its documentation cites an **11+ million document / 550 GB index** example. citeturn19search1

Agent integration is trivial because `recollq` is designed for command-line/programmatic output:

```bash
# update the index incrementally
recollindex

# continuously monitor changes
recollindex -m

# exact-ish all-word content search
recollq -a 'motor vehicle production 2021'

# filename search
recollq -f 'statistical-yearbook-2020'

# retry files that failed extraction earlier
recollindex -k
```

`recollq` can emit filenames/URLs, snippets, page information where available, metadata or full extracted content, and can query multiple indexes. citeturn19search3turn19search6

There is one **extremely important trap** for your requirement: Recoll intentionally remembers files that failed during an earlier indexing pass and normally **does not retry them** until you use `recollindex -k`. Missing extractors, corruption, decompression problems and similar issues can therefore leave holes unless you audit indexing. citeturn18search15turn19search0

That makes Recoll a good example of why I keep insisting on an `index_health()` mechanism.

Its real-time mode is `recollindex -m`; the documentation also notes that very large monitored trees can consume OS file-watch resources, making periodic incremental indexing preferable in some situations. citeturn18search27

**Verdict:** I would install this regardless of whatever “AI RAG” layer you eventually choose. It is your boring, deterministic truth serum.

### Docling plus LanceDB

This is my preferred **fully local build**.

[Docling](https://docling-project.github.io/docling/) converts PDFs and many other formats into a unified document representation. Current support includes PDF, DOCX, XLSX, PPTX, legacy Office via LibreOffice, OpenDocument formats, EPUB, Apple Pages, Markdown, emails, images, audio/video-related inputs, LaTeX and plain text. Its PDF pipeline handles page layout, reading order, tables, formulae and other document structure. citeturn18search4turn18search8

Installation is straightforward:

```bash
pip install docling
```

Docling now also exposes an MCP server. Their documented client configuration is:

```json
{
  "mcpServers": {
    "docling": {
      "command": "uvx",
      "args": [
        "--from=docling-mcp",
        "docling-mcp-server"
      ]
    }
  }
}
```

citeturn18search0

Maintenance looks excellent: the project was at v2.126.0 on its current releases page when I checked, with a long sequence of recent releases. citeturn18search5

It is not perfect. An open June 2026 issue documents large-PDF conversion failures/OOM behaviour on particular inputs and backends. That is exactly why converted files need an explicit `parse_status`, rather than assuming “the parser ran” means “the corpus is indexed”. citeturn18search13

Docling handles **understanding**, not corpus retrieval. Feed its normalised output into [LanceDB](https://docs.lancedb.com/).

LanceDB's local open-source library is embedded—no search server has to run separately—and its current feature set includes vector search, full-text/BM25 search, hybrid search, reranking, filtering and SQL. It has dedicated vector, FTS and scalar indexes, so a chunk can simultaneously carry semantic embeddings, ordinary text and structured metadata such as `project`, `year`, `agency`, `path` or `run_id`. citeturn14search4turn14search6

That means one local table can contain something like:

```text
chunk_id
file_id
sha256
path
project
agency
series
year
mime
page_start
page_end
section
text
embedding
parser
parsed_at
```

And a query such as:

> “Where was the post-2021 localisation target discussed?”

can use vector similarity, while:

> `SRO 656(I)/2006`

gets caught by BM25/full text. Metadata can constrain results to `project=auto-policy-2026` or `agency=pbs`.

That hybrid approach matters. Anthropic's Contextual Retrieval work found that combining contextualised embeddings with contextualised BM25 materially reduced retrieval failures in their experiments, with further improvement from reranking. Their central observation was that chunks detached from document-level context become harder to retrieve correctly. citeturn9search0

For your corpus, I would prefix/index every chunk with context such as:

```text
Project: auto-policy-2026
Path: sources/pbs/statistical-yearbook-2020/chapter-07.pdf
Agency: Pakistan Bureau of Statistics
Series: Statistical Yearbook
Year: 2020
Document: Chapter 7 — Manufacturing
Page: 84
```

before the actual passage.

That one detail prevents a lot of “orphan chunk” retrieval failure.

**Verdict:** strongest long-term local architecture; it requires some glue code, but the pieces are mature.

### pdf-mcp

For the enormous `sources/pbs/`, `sbp/`, policy notification and bulletin branches, [pdf-mcp](https://github.com/jztan/pdf-mcp) is unusually on-target.

It is an MCP server specifically designed to let coding agents search **one PDF or an entire folder of PDFs** using hybrid BM25 + semantic retrieval, then selectively read relevant pages. It also has table/image handling, OCR, multi-column reading-order logic and a persistent SQLite cache. citeturn21search2

Installation:

```bash
pip install pdf-mcp
```

For Claude Code:

```bash
claude mcp add pdf-mcp -- pdf-mcp
```

OCR requires Tesseract separately. citeturn21search2

This is almost comically appropriate for:

```text
sources/pbs/statistical-yearbook-2015/
...
sources/pbs/statistical-yearbook-2025/
sources/pbs/cpi-monthly/
sources/sbp/bulletins/
```

It can warm and search the folder as a corpus rather than opening 700 PDFs one at a time. citeturn21search2

The catch is decisive: **it is PDF-focused**. It does not solve `notes/*.md`, CSV extraction runs, DOCX drafts and correspondence as one global knowledge space.

So I view it as an excellent immediate sidecar, not your final global solution.

### ripgrep-all

[ripgrep-all](https://github.com/phiresky/ripgrep-all) wraps ripgrep with adapters for PDFs, DOCX/ODT/EPUB, SQLite databases, archives, media and other formats, recursively entering archives it understands. citeturn20search0

It is not semantic search, but that is a feature when you need to prove something exists:

```bash
rga 'SRO[ -]?656' ~/research
rga 'localisation target' ~/research
rga 'motor vehicle production' ~/research
```

The latest release visible in the project when researched was v0.10.10 from November 2025; the project has also added a SQLite cache, configurable adapters and debugging/performance instrumentation. citeturn20search1

I would make this the agent's **verification fallback**.

The semantic index says “I think these 12 chunks are relevant.”

`rga`/Recoll says “this exact token occurs in these 27 physical files.”

You want both.

### mcp-local-rag

[mcp-local-rag](https://github.com/shinpr/mcp-local-rag) is worth trying because it already packages local semantic + keyword search behind MCP/CLI and uses LanceDB and Transformers.js. Its metadata currently identifies version 0.18.3 and supports one or multiple base directories through `BASE_DIR`/`BASE_DIRS`. citeturn21search0turn21search4

That makes it a very cheap experiment:

```bash
npx mcp-local-rag
```

The reason I am not telling you to make this your production answer is that its stated target is **code and technical documentation**, whereas your corpus contains serious PDF tables, Word documents, email exports, CSVs and potentially scanned documents. citeturn21search0

**Verdict:** try it before writing custom LanceDB glue. Keep it only if your own retrieval benchmark proves its loader covers the corpus.

I also found [knowledge-rag](https://github.com/lyonzin/knowledge-rag), whose configuration explicitly recursively scans a documents directory and even ships a research-oriented preset. That is directionally interesting. citeturn21search1 I could not establish enough current primary-source evidence about its release/maintenance surface to recommend putting a research archive behind it yet, so I am treating it as a watchlist project rather than a core recommendation.

## The architecture I would actually build

This is the part that gets you all the way to your stated goal rather than merely making search somewhat nicer.

### Keep the tree; add a shadow research index

I would **not** migrate the entire corpus into a new clever folder taxonomy first.

Create:

```text
~/research/
  auto-policy-2026/
  project-two/
  project-three/
  ...

  .research-index/
    manifest.sqlite
    lineage.sqlite
    lancedb/
    normalized/
    logs/
    index-status.json
```

The user-facing physical tree remains whatever chaotic structure accumulated naturally.

Every physical file gets a stable record:

```text
file_id       = content hash / UUID
path          = current absolute/relative path
sha256        = file content hash
mime
size
mtime
project
parser
parse_status
indexed_at
```

The important shift is:

> **Path becomes metadata, not identity.**

If someone moves:

```text
sources/pbs/statistical-yearbook-2020/ch7.pdf
```

to:

```text
archive/pbs/yearbook/2020/ch7.pdf
```

the content hash is unchanged, so all lineage can continue to point to the same `file_id`.

That is vastly more robust than encoding relationships in directory names.

### Maintain two retrieval routes, not one

Every agent query should run these in parallel:

```text
lexical_query = BM25 / full-text / exact filename / regex
semantic_query = vector search over contextualised chunks
```

Then union and rerank.

The lexical route catches:

```text
SRO 656(I)/2006
Table 7.3
Honda Atlas
FY2020-21
Chapter 14
run-2026-02-03
```

The semantic route catches:

```text
"where did they discuss import substitution for locally assembled cars?"
```

when the document actually says:

```text
"progressive manufacturing/local content requirements..."
```

LanceDB natively supports the components needed for that style of hybrid retrieval, while Anthropic's retrieval experiments provide good evidence that BM25 and semantic embeddings are complementary rather than substitutes. citeturn14search4turn9search0

**Do not build vector-only RAG for this corpus.**

Identifiers, policy notification numbers, dates, table labels and filenames are exactly the sort of evidence where lexical search shines.

### Retrieve hierarchically

Do not embed 100,000 anonymous 1,000-token chunks and throw `top_k=5` at them.

For each document, create:

```text
document summary
    ↓
sections/pages
    ↓
fine-grained chunks
```

First retrieve likely **files**, then retrieve relevant **sections/pages inside those files**, then open the original evidence.

For example:

```text
query
  "How did vehicle production change after the 2021 policy?"

document retrieval
  1. PBS Statistical Yearbook 2022, Manufacturing chapter
  2. Auto Policy 2021
  3. PBS Statistical Yearbook 2023, Manufacturing chapter
  4. extraction run 2026-02-03/table_0047.csv

section retrieval
  Yearbook 2022 pp. 196–201
  Policy pp. 9–14
  CSV rows 40–63

final agent context
  ~8 relevant slices, not 600 files
```

That is how you prevent context rot: **do not put the corpus in context. Put retrieval in front of context.**

### Expose an agent API, not the filesystem

Your agent should get six boring tools:

```text
find_file(query)
search_all(query, mode="hybrid", top_k=30, filters={})
grep_all(pattern, filters={})
read(path_or_file_id, page_or_range=None)
related(path_or_file_id, direction="both")
index_health()
```

If you choose LlamaParse, much of this already maps almost one-for-one onto `findFilesInIndex`, `grepFileFromIndex`, `readFileFromIndex` and `retrieveFromIndex`. citeturn16search0turn16search2

If you build locally:

```text
find_file     → manifest SQLite / Recoll
search_all    → LanceDB hybrid
grep_all      → Recoll / rga
read          → original / Docling representation
related       → lineage.sqlite
index_health  → your manifest/index auditor
```

Then put something like this in the CLI agent's persistent instructions:

```markdown
## Research corpus rules

Do not discover research evidence by recursively browsing directories.

Before answering a research question:

1. Call `index_health`.
2. Search the entire corpus using both hybrid retrieval and exact/lexical search.
3. Inspect at least the highest-ranked source files rather than relying only on
   retrieved snippets.
4. For extracted tables or analysis outputs, call `related` and inspect their
   upstream source documents.
5. For claims based on generated files, prefer the original source plus the
   generated artefact.
6. Cite path + page/section/row for every substantive claim.
7. If index coverage is incomplete, stale, or a relevant parser failed, report
   that explicitly rather than answering as though the corpus were complete.
```

That instruction is far more valuable than:

```text
"Be thorough and look through all relevant files."
```

The latter is unenforceable.

### Make completeness a first-class property

This is the part almost every casual RAG tutorial misses.

Run an unrestricted inventory independently of the AI index:

```bash
fd -u -t f . ~/research
```

`fd -u` is specifically the option its documentation recommends when you need to include hidden and ignored files rather than its normal `.gitignore`/hidden-file filtering. citeturn20search6

For each manifest entry, require one of:

```text
indexed_ok
unsupported_type
parse_failed:<reason>
intentionally_excluded:<reason>
pending
```

Never permit:

```text
???
```

Then:

```text
index_health()

files_on_disk:       18,421
indexed_ok:          18,397
parse_failed:            11
unsupported:              8
intentionally_excluded:   5
pending:                  0
last_scan:       2026-09-08T14:42:10+05:00
last_index:      2026-09-08T14:42:48+05:00
```

If there are 11 failed PDFs, the agent knows that.

This is how you remove **silent** missing.

Recoll's own behaviour demonstrates why this is necessary: previously failing files are normally skipped on future passes until explicitly retried. citeturn18search15 Docling likewise has documented large-document failure cases. citeturn18search13

### Test retrieval with canaries

Do not subjectively decide “the search seems better”.

Create a tiny test set:

```yaml
- query: "SRO 656(I)/2006"
  expected:
    - auto-policy-2026/sources/ministry-of-industries/notifications/...

- query: "PBS vehicle production table for 2020"
  expected:
    - auto-policy-2026/sources/pbs/statistical-yearbook-2020/...

- query: "output created by the February 3 extraction run from Yearbook 2020"
  expected:
    - auto-policy-2026/extractions/run-2026-02-03/...
    - auto-policy-2026/sources/pbs/statistical-yearbook-2020/...
```

Also deliberately put a unique phrase in files at:

```text
depth 1
depth 4
depth 8
.gitignored directory
hidden directory
PDF
DOCX
CSV
Markdown
email
```

After every indexer change, run those queries.

For the small “known needle” suite, I would demand effectively **100% retrieval of the expected file in the candidate set**. If an index misses a known deep file once, you now have an observable test failure rather than an LLM hallucinating around the omission.

That is how this becomes infrastructure rather than vibes.

## Provenance: search alone cannot create relationships that were never recorded

This is the second place where I would push back on the original framing.

You said:

> the agent needs to know that a number in `extractions/run-2026-02-03/` came out of a specific PDF in `sources/pbs/`, and a claim in `drafts/chapter-3/` depends on both.

Retrieval can discover **similarity**.

It cannot reliably recover **causal provenance**.

Suppose:

```text
table_00831.csv
```

contains a number that also appears in fourteen PBS PDFs.

No embedding model can prove which of those PDFs your extraction process actually used.

**That fact has to be recorded at extraction time.**

### DataLad is unusually appropriate here

[DataLad](https://docs.datalad.org/) is built around versioned research datasets and reproducible computation. Its `datalad run` command can record the command that generated outputs and supports explicit `--input` and `--output` declarations. That provenance can later be used for re-execution. citeturn22search1turn22search4

Instead of:

```bash
python extract_tables.py \
  sources/pbs/statistical-yearbook-2020/chapter-07.pdf \
  > extractions/run-2026-02-03/table-07.csv
```

run the process under a provenance wrapper:

```bash
datalad run \
  --input sources/pbs/statistical-yearbook-2020/chapter-07.pdf \
  --output extractions/run-2026-02-03/table-07.csv \
  -m "Extract manufacturing table from PBS Yearbook 2020" \
  "python extract_tables.py \
     {inputs} > {outputs}"
```

DataLad explicitly recommends declaring inputs and outputs precisely so they can be used as actionable provenance for later re-execution. citeturn22search4 Its YODA workflow documentation describes this as linking results to scripts and input data. citeturn22search11turn22search16

Then your `related(table-07.csv)` tool can surface:

```text
DERIVED_FROM
  sources/pbs/statistical-yearbook-2020/chapter-07.pdf

GENERATED_BY
  extract_tables.py

RUN
  2026-02-03
```

DataLad does **not** magically reconstruct old unrecorded provenance, and it does not inherently know that paragraph 4 of `v2-final-ACTUAL.docx` relies on one particular cell of the CSV. That latter relationship still needs to be recorded through citations, notes or your own claim graph.

### You probably do not need Neo4j

For this scale, I would start with one SQLite table:

```sql
CREATE TABLE edges (
    src_file_id TEXT NOT NULL,
    relation    TEXT NOT NULL,
    dst_file_id TEXT NOT NULL,
    detail_json TEXT,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (src_file_id, relation, dst_file_id)
);
```

Example rows:

```text
table-07.csv
  DERIVED_FROM
  statistical-yearbook-2020-ch07.pdf

chapter-3-v2.docx
  SUPPORTS_CLAIM
  table-07.csv

chapter-3-v2.docx
  CITES
  statistical-yearbook-2020-ch07.pdf

run-2026-02-03
  GENERATED
  table-07.csv
```

That is enough to answer:

```text
related("table-07.csv")
related("chapter-3-v2.docx")
related("statistical-yearbook-2020-ch07.pdf")
```

with graph traversal.

If later you want a standards-compatible representation rather than your own schema, [RO-Crate](https://w3id.org/ro/crate/) represents research objects using machine-readable linked metadata, and its ecosystem includes workflow-run provenance profiles for inputs, outputs, software and execution relationships. citeturn22search3

I would regard RO-Crate as an **export/interchange format**, not something you need to query interactively on day one.

### Existing chaos can still be partially recovered

For the old extraction runs, you can bootstrap probable lineage by combining:

```text
filenames
timestamps
run logs
identical table values
PDF table text
nearby script configuration
folder dates
hashes
```

Then label relationships:

```text
provenance_status = recorded
```

versus:

```text
provenance_status = inferred
confidence = 0.91
```

Do **not** silently convert inferred lineage into historical fact.

That distinction will matter enormously six months later.

For drafts, the best future discipline is explicit claim/source linkage. Even a lightweight annotation such as:

```markdown
Vehicle production increased ... [source:pbstable2020-7-3]
```

is infinitely more trustworthy than asking an embedding model two years later which table the sentence was probably inspired by.

## Bugs, limitations and why the tree currently “disappears”

There are several independent failure mechanisms that all look like “the agent forgot files”.

| Failure | Bug or fundamental? | What to check |
|---|---|---|
| Agent never searches a branch | Architecture/model behaviour | Replace browsing with global index |
| `.gitignore`/hidden files omitted | Search-tool default | Test unrestricted inventory |
| `@` autocomplete omits files | Can be a tool bug | Compare agent search with `fd -u` |
| File discovery gets slow and gives poor exploration | Tool implementation/performance | Use indexed search / `rg` / Recoll |
| Huge command output gets truncated | Tool/context-budget limitation | Return ranked results, not full trees |
| PDF parser fails | Parser limitation/bug | Explicit per-file parse status |
| Index says “ready” but is stale | Integration/sync bug | Version/freshness checks |
| Vector search misses an exact identifier | Retrieval-design limitation | BM25/regex alongside vectors |
| Relevant chunk loses its document context | Chunking design flaw | Contextual metadata + hierarchy |
| CSV↔PDF causal relationship unknown | Missing historical information | Record provenance |
| Multiple agents independently roam directories | Agent architecture flaw | Shared central retrieval service |

Some of these are demonstrably ordinary tooling bugs.

Claude Code's issue tracker includes reports of `@` file search missing most files after an update and of `.py` files being absent from editor autocomplete while terminal behaviour differed. citeturn23search32turn23search24 Those are not “LLMs cannot understand large repositories”. They are file-discovery regressions.

Other reports describe file search taking seconds per keystroke in large repositories and a Search task traversing millions of ignored paths. citeturn23search0turn23search4 Again, tool implementation.

And `fd` itself explicitly documents the easiest accidental blind spot: by default it does not search hidden directories and respects `.gitignore`; `-u` is how you ask for everything. citeturn20search6

That is particularly relevant to your layout because researchers often `.gitignore` precisely the branches the agent later needs:

```text
extractions/
old/
downloads/
*.pdf
*.csv
*.docx
```

A coding-oriented search stack may interpret “generated/unversioned” as “irrelevant”. A research agent absolutely cannot.

So the very first experiment I would run on the broken projects is:

```bash
cd ~/research

fd -u -t f . | wc -l
```

Then compare that with however many paths the agent's own file-discovery tool can enumerate.

Pick twenty known “asscrack” files and explicitly test whether the built-in search can name them.

There is a decent chance part of what you have been experiencing is **not a context-window phenomenon at all**.

## The agent and subagent design that gets you there

Subagents are useful, but not in the way “give each agent one subtree” suggests.

If four agents each recursively browse:

```text
sources/
extractions/
notes/
drafts/
```

you have taken one unreliable filesystem walker and multiplied it by four.

They also start with different partial contexts, so connecting evidence across branches becomes *harder*.

Instead, every subagent should see the **same global retrieval service**.

I would use roles like:

```text
Coordinator
    |
    +-- lexical locator
    |     exact names, IDs, dates, table numbers, regex
    |
    +-- semantic researcher
    |     hybrid retrieval, paraphrases, related concepts
    |
    +-- provenance tracer
    |     CSV → run → PDF → draft dependencies
    |
    +-- evidence verifier
          opens originals; checks page/row/path
```

The locator is not “the PBS folder agent”. It searches everything.

The semantic researcher is not “the notes agent”. It searches everything.

The provenance tracer follows explicit edges across everything.

The verifier is explicitly hostile: its job is to prove the other agents' candidate evidence exists in the actual files.

This means:

> **parallelism is by retrieval strategy/task, not by directory branch.**

That matters because your core problem is *cross-branch reasoning*.

Modern retrieval tooling increasingly reflects the same pattern. LlamaParse's current MCP deliberately exposes separate find/grep/read/hybrid-retrieve operations rather than asking the LLM to consume a whole knowledge base at once. citeturn16search0turn16search1 LanceDB similarly treats full-text, vector and metadata filtering as complementary retrieval mechanisms. citeturn14search4turn14search6

For many questions, I would not even spawn four LLMs. A single strong agent can issue lexical and semantic searches in parallel, open the ten best candidates, call `related()` and answer. Subagents earn their keep on difficult synthesis, not ordinary file discovery.

The important invariant is:

```text
all agents
    ↓
one authoritative corpus index
    ↓
one authoritative provenance store
    ↓
actual physical files
```

Not:

```text
agent
    ↓
"let me ls around and see what looks relevant"
```

## What I would install on this exact machine

I would do this in stages rather than build a majestic six-component RAG system before testing the obvious fix.

### Immediate local layer

Install **Recoll** first and point it at the entire `~/research`, not one project. It gives you deterministic content and filename retrieval across the corpus, a CLI the coding agent can invoke, incremental updates and a known ability to handle vastly larger collections. citeturn19search0turn19search3

Add **ripgrep-all** as a second independent search path. Its value is partly redundancy: when the index claims zero matches, the agent can directly search the underlying documents. citeturn20search0

For PDF-heavy source trees, install **pdf-mcp** immediately:

```bash
pip install pdf-mcp
```

and attach it to the CLI agent. citeturn21search2

At this point you can already transform:

```text
"Find the policy notification about local-content requirements"
```

from:

```text
agent randomly explores sources/ministry-of-industries/
```

to:

```text
global Recoll search
+
global PDF hybrid search
→ 8 candidate files
→ read candidate pages
```

That alone may remove most of the failure you currently observe.

**Time:** probably an evening.

**Money:** zero software cost.

**Confidence this materially improves the current problem:** **very high**.

### Serious local layer

Then:

```bash
pip install docling
pip install lancedb
```

Normalise all mixed files into a generated representation under `.research-index/normalized/`, preserving original path, content hash and page/section information. Docling covers far more of your mixed document set than a PDF-only extractor and is receiving frequent releases. citeturn18search4turn18search5

Index those records in LanceDB using:

```text
BM25/full text
+
vector embeddings
+
metadata
```

because those retrieval modes are directly supported by LanceDB OSS. citeturn14search4turn14search6

Write the small six-tool MCP façade described earlier.

The implementation does **not** need to be 20,000 lines. The core operations are ordinary search/database calls.

The difficult engineering is not the MCP protocol. It is:

```text
correct ingestion
correct chunk metadata
incremental updates
parser error visibility
lineage
tests
```

**Time:** realistically one solid day for a prototype, several days to make it boring and trustworthy.

**Money:** $0 software plus your local compute/storage.

**Confidence that this is the best long-term answer under a local/private constraint:** **high**.

### Provenance layer

Start wrapping new extraction/analysis operations with **DataLad** or, if adopting DataLad across an existing project feels too invasive, at least emit the SQLite relation rows yourself.

DataLad is appealing because provenance is not a side feature: `run`, explicit inputs/outputs and reproducible reruns are part of its documented model. citeturn22search1turn22search4

Do this prospectively.

Do not spend two weeks perfectly reconstructing every mysterious historical `old/` directory first.

### Managed alternative

Before writing the local MCP, I would personally run a small representative project through **LlamaParse Index** as an A/B test.

Use:

```text
one PBS yearbook series
CPI monthly releases
one extraction run
notes
chapter draft
```

and give its MCP to the same coding agent.

Its product already contains the exact find/grep/read/retrieve tool split you are about to build. citeturn16search0turn16search2

If it nails your retrieval benchmark, you have learned two things:

1. the architecture is correct;
2. you can decide whether $50+/month and cloud storage are worth avoiding the engineering.

That is a much better build-vs-buy test than reading RAG benchmarks.

### The final target

The finished experience should look like this:

```text
You:
"Where did we get the 2020 production number in chapter 3?"

Agent:
→ search_all("2020 production number chapter 3")
→ finds chapter-3 draft
→ related(chapter-3)
→ finds table_0047.csv
→ related(table_0047.csv)
→ finds PBS Yearbook 2021, Manufacturing chapter
→ opens CSV row
→ opens PDF page 198
→ compares values
→ answers with all three paths and source page
```

The agent never has to know that the PDF was eight directories away.

Or:

```text
You:
"Find that SRO about reduced duties on CKD kits. I don't remember
the number or year."

Agent:
→ semantic search across all projects
→ lexical expansion over candidate terms
→ finds 6 notifications
→ reranks
→ opens three likely SROs
→ answers
```

Or:

```text
You:
"Was this table generated in the failed Feb 28 run or the Feb 3 run?"

Agent:
→ find_file(table)
→ related(table)
→ reads recorded execution lineage
→ answers deterministically
```

That is the system you are asking for.

The folder hierarchy has become an implementation detail.

### What I searched that did not produce a convincing answer

I specifically looked for a **single mature, self-hosted package that simultaneously** watches an arbitrary recursive local folder, robustly parses PDFs/Office/email/CSV, performs hybrid lexical+semantic search, exposes agent/MCP tools, records exact computational provenance, monitors index completeness and connects drafts back to source artefacts.

I did **not** find one.

The closest managed answer is LlamaParse Index/MCP. The closest local answer is still a composition of document parsing + retrieval + provenance.

I looked for a strong current official DVC route for this exact provenance problem during the research pass; the search did not return reliable current official material I was comfortable using as the basis for a recommendation. DataLad's own documentation was much more directly aligned with research datasets, input/output recording and reproducible execution, so I scored DataLad instead. citeturn22search1turn22search4

I did not find a Stack Overflow answer I considered strong enough to cite as “the solution”. The useful real-world failure evidence came instead from current project issue trackers: ignored paths, broken `@` discovery, slow repository search, parser failures and synchronisation edge cases. citeturn20search2turn23search0turn23search32turn18search13turn17search0

I also did **not** find a credible system capable of inferring exact historical causal lineage—“this CSV was definitely generated from this PDF”—purely from an old chaotic tree when that relationship was never recorded. That is not really a search problem. You can reconstruct probable relationships, but exact provenance requires metadata from the process that created the output. DataLad's design makes the same assumption explicitly by recording declared inputs, outputs and execution commands. citeturn22search4turn22search11

And that leads to the final judgement:

**The clean fix is not a bigger-context model, not better folder names, and not more subagents. It is to stop making the LLM perform corpus discovery.**

Give it a corpus service that can:

```text
find
grep
retrieve
read
trace
self-audit
```

across the entire tree.

For your exact use case, my ranking is:

**Best turnkey:** [LlamaParse Index + MCP](https://developers.llamaindex.ai/llamaparse/cloud-index-v2/getting_started/). citeturn16search3

**Best local foundation:** [Docling](https://docling-project.github.io/docling/) + [LanceDB](https://docs.lancedb.com/) + a small MCP façade. citeturn18search4turn14search6

**Install regardless:** [Recoll](https://www.recoll.org/) as the global deterministic corpus index and [ripgrep-all](https://github.com/phiresky/ripgrep-all) as the direct-search safety net. citeturn19search0turn20search0

**Best immediate PDF upgrade:** [pdf-mcp](https://github.com/jztan/pdf-mcp). citeturn21search2

**For real cross-branch causal relationships:** [DataLad](https://docs.datalad.org/) or a tiny explicit lineage database; retrieval alone cannot supply provenance that was never captured. citeturn22search1turn22search4

And the non-negotiable piece tying all of them together is **coverage auditing**. Until the agent can distinguish “there is no relevant file” from “my index/search layer failed to see 37 files”, you have not actually fixed the original bug.