# Tool matrix — distilled from the 4 research passes, filtered by what this machine can run

**The four passes now live in this workspace** — copied out of the Desktop dump on
11 Sep 2026, byte-identical, named by pass label. Read them from here, not from
Desktop; the Desktop copies are the originals and may be tidied away at any time.

**Mapping settled — do not re-derive it:**

| pass | saved copy | original filename on Desktop |
|---|---|---|
| **C1** — round 1, Claude | `01_reports/passes/C1-round1-claude.md` | `compass_artifact_wf-123e4124-3394-53bb-bfc5-b93dac6499ba_text_markdown.md` |
| **G1** — round 1, GPT | `01_reports/passes/G1-round1-gpt.md` | `deep-research-report (5).md` |
| **C2** — round 2, Claude | `01_reports/passes/C2-round2-claude.md` | `compass_artifact_wf-04149506-23dc-52d5-8a24-d35a5a07e16c_text_markdown.md` |
| **G2** — round 2, GPT | `01_reports/passes/G2-round2-gpt.md` | `deep-research-report (6).md` |

`deep-research-report (4).md` is **NOT a research pass** — it is a Bluetooth earbuds
buying guide. It was deliberately left on Desktop and not copied here. Ignore it.

There are **four** passes, not five.

Titles, so a pass can be recognised without opening it:

- **C1** — "Why Your Agent Goes Blind Deep in the Tree — and How to Fix It"
- **G1** — "Making a Huge Research Folder Reliably Searchable to CLI Agents"
- **C2** — "Round Two: Sub-Document Addressing, Series Continuity, Coverage Accounting,
  and the Claude Code Build Shape"
- **G2** — "Deep research: making a huge research tree behave like one addressable
  corpus inside Claude Code"

---

## The filter that actually decides things

This machine: **no NVIDIA GPU, no CUDA, no Docker, no WSL, no cargo/Rust, no pandoc, no
tesseract, no sqlite3 CLI, no real `rg` binary.** 8C/16T AMD, 31 GiB RAM.
No research pass was ever asked about Windows — that is the single biggest gap between the
research and this build.

### Survives the filter (all free, all present or pip-only)

| tool | layer | status |
|---|---|---|
| **SQLite FTS5** | lexical index | **IN USE.** Python stdlib, verified working. The only zero-install index available. |
| **pdftotext 4.00** | PDF text | **IN USE.** Ships with Git for Windows. `-layout` preserves visual structure; split on `\f` for pages. ~940 pages/s with 12 workers. |
| **Python stdlib zipfile** | DOCX/XLSX/PPTX text | **IN USE.** Strip XML tags. No python-docx needed for read-only. |
| pdfplumber | table extraction at known bbox | pip, pure-Python, no system deps. Not yet used. |
| DuckDB | numeric layer over extracted CSVs | pip. C2: *"once tables are CSVs, `SELECT …` beats embedding numbers."* Not yet used. |
| sdmx1 v2.27.0 | WB/IMF series | pip. **Not** the dead `pandaSDMX`. Only helps where publishers emit SDMX — not provincial yearbook tables. |
| watchfiles | index refresh | pip, **explicitly confirmed Windows-supported** (one of only two tools in the whole corpus of reports that is). |
| Watchman | index refresh | **explicitly confirmed Windows.** Heavier; Meta-maintained. |
| Valentine | schema matching for series | pip, 394 commits. Candidate generator only — *"a high schema similarity score is not proof that two economic concepts are identical."* |

### Ruled out on this machine

| tool | why |
|---|---|
| **ripgrep-all (rga)** | needs cargo/Rust. **This was C1's #1 "do this first" pick and it is not installable here.** |
| **ColQwen2.5 / SentenceTransformers v6 MultiVectorEncoder** | G2's centrepiece. Needs a GPU. Also produces hundreds of vectors per page. |
| **Docling / MinerU** | pip-able but PyTorch stack, CPU-only here, 2–3 orders of magnitude slower than pdftotext. Only worth it if we need table *structure*, not table *text*. |
| Qdrant, Elasticsearch, Datashare, Aleph, paperless-ngx, Onyx | all need Docker |
| Recoll | Windows support never confirmed by the report that recommended it "regardless". Its trap is severe: **remembers files that failed extraction and will not retry until `recollindex -k`** — silent permanent holes. |
| DEVONthink | Mac-only, paid |
| **LlamaParse Index + MCP** | **$50/month minimum.** G1's headline pick, disqualified by the zero-cost constraint. Its 4-tool surface (`findFilesInIndex`/`grepFileFromIndex`/`readFileFromIndex`/`retrieveFromIndex`) is still the best-validated API template. |
| **GraphRAG** | ~$33,000 to index a single 5 GB dataset. All four passes say skip. |
| Marker | GPL-3.0 + RAIL-M weight licence with a commercial revenue threshold |
| Sherlock / Sato / Doduo / py_entitymatching | research code, dormant, not installable |

---

## Rulings that survived all four passes (stop researching these)

- **Hybrid lexical + semantic, never vector-only.** Identifiers, SRO numbers, dates and
  table labels are exactly where lexical wins. Unanimous.
- **No knowledge graph.** "You probably do not need Neo4j." Unanimous.
- **Path is not identity — content hash is.** Path is a mutable alias. Same model as
  git-annex / DataLad / IPFS. C1 was wrong that staleness doesn't matter; both round-two
  passes overturned it. The failure is the *working tree churning*, not the PDFs changing.
- **Provenance must be recorded at extraction time.** It cannot be recovered later.
- **Strong omission proof is impossible.** Top-k means "ranked highest by this procedure,"
  not "everything else was disproved." What is achievable is a *retrieval receipt*.
  Wording rule: never "this is not in the corpus," only **"I found no supporting evidence in
  the currently indexed corpus"** with coverage numbers attached.
  **Exception:** for exact identifiers, exhaustive lexical search *does* support a strong
  negative. That is most of what sir asks.
- **Coverage accounting needs a closed status enum with no "unknown".**
  `discovered = indexed + failed + excluded + pending` must always hold. **Implemented.**
- **Subagents split by function, never by directory branch.** *"Four subagents independently
  globbing the tree are not four times smarter, they are four chances at silent partial
  traversal."* All three passes that addressed it agree. Role taxonomy still disputed.
- **Same-series-across-years: nothing off the shelf exists.** Needs a hand-curated registry
  keyed by content hash, with vintages, rebasings and label drift recorded. Neither
  base-year rebasing nor chain-linking can be automated — **record the break, don't force
  the merge.** Numeric overlap is strong identity evidence.

---

## Delivery mechanism — what the reports said vs what we measured

| | reports | **measured here** |
|---|---|---|
| MCP server | both round-two passes assume it | untested — the Bash CLI proved faster to build and works |
| PreToolUse deny on Grep/Glob | recommended by both, **tested by neither** | **fires from project `.claude/settings.json` only, NOT from `--settings`** |
| Is deny enough? | not addressed | **No — model escapes via `Bash: grep` in the same turn. Must deny Bash crawls too.** |
| #33106 | C2 only: deny is **not** enforced for MCP tools, **is** for built-ins | not retested; C2's direction (deny built-ins, fall through to index) is what we built |
| CLAUDE.md | G2 says ten lines max; C1 cites arXiv:2602.11988 showing generated context files *reduce* task success | we ship ~12 lines |

**Working precedents named (all MIT/OSS, none tried yet):** Beacon
(`sagarmk/beacon-plugin`) — closest template, sqlite-vec + FTS5, PreToolUse deny with
`additionalContext` redirect, PostToolUse re-embed, PreCompact re-inject. ContextStream —
blocks Glob/Grep/Search/Explore/Task but only when the project is indexed, graceful
fallthrough. `BeaconBay/ck`, `yoanbernabeu/grepai`, and the #22699 smart-read hook.

---

## Evaluation ideas worth stealing

- **Retrieval receipt** (G2's JSON shape): corpus generation timestamp, coverage counts,
  query expansions, per-pass searched/returned counts, union candidates, reranked, opened,
  selected evidence addresses, unavailable-by-reason. **Partially implemented** in
  `corpus_search.py` — we have coverage + searched counts, not query expansion or rerank.
- **Gold set of 100–300 real questions** with known evidence addresses as a retrieval
  regression test. The harness answer key already is this (135 questions).
- **RAGChecker** for retrieval recall regression; **RAGAS / Phoenix** as faithfulness gates.
  All need ground truth, which we have.

## Research gaps nobody covered

1. **Windows.** Two tools confirmed across four passes.
2. **No reranker model is named anywhere.** Reranking is a stage in every architecture and a
   concrete tool in none.
3. **No pages/sec figure for any extractor.** Every effort estimate is in engineer-hours.
   *We measured this: ~940 pages/s for pdftotext.*
4. The reports assume ~48k files; ra-ship is 217k. Several stated thresholds
   ("if you cross ~100k files…") are already exceeded.
