# BUILD B — hybrid search with multi-query fusion, reranking and a notes loop (stack `s6_hybrid`)

You are an executing agent with shell and file access, running unattended in
`C:\Users\Ali\Desktop\retrieval-lab`. Ali is asleep. Follow this file in order. Do not
improvise past a failed gate, do not narrow a task to make a gate pass, and do not
substitute your own judgement where a number is given. When something here is impossible
as written, stop that stage, log why, and continue with the next stage that does not
depend on it.

Read `plans_fable/B_HYBRID_MULTIQUERY_PLAN.md` once for context before starting. You do
not need anything else to do this job, but `corpus-lab/RESUME.md` §7 lists traps that
have already cost hours here; skim it.

---

## 0. Fixed rules — restate them to yourself before Stage 1

1. **Never regenerate any harness corpus.** `harness/corpus_*` are irreplaceable. If any
   command you are about to run writes under `harness/`, other than the two installer
   files named in rule 4, do not run it.
2. **`_private/` must never be reachable from a measured session.** You may read
   `_private/harness_keys/answer_key.json` only inside the offline gate script (Stage 3)
   and the scoring script (Stage 5). Never print an evidence path, row label or expected
   value into `progress.jsonl`, `FINDINGS_LIVE.md`, `CLAUDE.md`, any prompt string, or
   any file under `corpus-lab/bin/`. Counts only.
3. **No hand-written synonym tables, alias lists or example queries derived from the
   corpus or the key.** The only vocabulary bridging allowed is the embedding model and
   the model's own rewrites. If you catch yourself typing a row label you saw in the key
   into any code or prompt, delete it and log `contamination_averted=1`.
4. **The corpus is read-only.** The only files you may create inside
   `harness/corpus_15000` are `CLAUDE.md` and `.claude/settings.json`, via `b_stack.py`,
   and you remove them at the end of Stage 5 whatever happened. Always pass `--corpus`
   to any teardown; never run `stack.py teardown` without `--corpus` — it would tear down
   another agent's install in another corpus.
5. **Do not modify existing instruments.** `ask.py`, `run_harness.py`, `scoring.py`,
   `corpus_search.py`, `index_build.py`, `stack.py`, `labpaths.py`, `checksums.py` are
   read-only for you. Create new files only, named `b_*.py`. If a change to an existing
   instrument looks necessary, log it as `blocked_needs_instrument_change` and stop that
   stage.
6. **Do not touch another agent's work.** `corpus-lab/evidence_v1/`,
   `corpus-lab/bin/evidence.py`, `corpus-lab/tests/`, `_private/evidence_v1/`,
   `corpus-lab/state/evidence_v1/`, and the root files `SOLUTION.md`, `BUILD_PROMPT.md`,
   `ACCEPTANCE.md` are not yours. Never install while their stack is installed (Stage 5.1).
7. **Open the index read-only.** Always `sqlite3.connect(f"file:{db}?mode=ro", uri=True)`.
8. **pip installs go into `.venv` only**: `C:\Users\Ali\Desktop\retrieval-lab\.venv\Scripts\python.exe -m pip install …`.
9. **Invoke `claude.exe`, never `claude.cmd`.** Path: import `labpaths` and use `L.CLAUDE`.
10. **Every step appends one line to `corpus-lab/state/progress.jsonl`** via
    `python corpus-lab/bin/plog.py B <step> <status> <note> k=v …`. Append only. Status is
    one of `started`, `PASS`, `FAIL`, `skipped`, `stopped`. When a stage stops early the
    note says why in one sentence.
11. **Free before paid.** Stages 0–4 spend nothing. Stage 5 is the only paid stage and
    only runs if Stage 3's gate passed.
12. **Run long jobs with `python -u` in the foreground.** No `nohup … &`. If you must
    background something, re-check it finished.
13. **Windows paths never go into bash heredocs feeding `python -c`.** Write scripts to
    files with the Write tool and run the file.

Constants used below:

```
ROOT   = C:\Users\Ali\Desktop\retrieval-lab
PY     = C:\Users\Ali\Desktop\retrieval-lab\.venv\Scripts\python.exe
LAB    = C:\Users\Ali\Desktop\retrieval-lab\corpus-lab
BIN    = LAB\bin
DB     = LAB\02_stacks\s2_fts5\harness_15000.db          (read-only, 6.97 GB)
OUT    = LAB\02_stacks\s6_hybrid\                         (create; NOT covered by corpus-lab/.gitignore today — append the line `02_stacks/s6_hybrid/` to it in Stage 1 so a 7 GB memmap can never be staged)
RUNG   = C:\Users\Ali\Desktop\retrieval-lab\harness\corpus_15000
STATE  = LAB\state
PLOG   = PY BIN\plog.py B
REG    = %LOCALAPPDATA%\retrieval-lab\roots.json          (tool registry: corpus root -> db, vectors)
NOTES  = %LOCALAPPDATA%\retrieval-lab\notes\<corpus-key>\ (notes files; corpus-key = sha256 of the lowercased resolved root, first 12 hex)
STACK  = s6_hybrid
PHASE  = PB_s6_hybrid            (run directory name under _private/results/03_runs)
MODEL  = claude-sonnet-5         (same as S0–S2; do not change)
```

---

## Stage 0 — preflight (free, ≤ 10 min)

Inputs: nothing. Outputs: `STATE\b_preflight.json`. Writes: that file, progress lines.

0.1 `PLOG 0.1 started "preflight"`.

0.2 Verify each of the following and record it in `b_preflight.json`:

| check | pass condition |
|---|---|
| `PY --version` | starts with `Python 3.11` |
| `PY -c "import fastembed, onnxruntime, numpy"` | exit 0 |
| `PY -c "from fastembed.rerank.cross_encoder import TextCrossEncoder"` | exit 0 |
| `DB` exists | size ≥ 6,900,000,000 bytes |
| `PY BIN\corpus_search.py --coverage` with env `CORPUS_DB=DB` | `indexed_ok` = 13634 and `addressable_pages` = 1206260 and `accounting_identity_holds` = true |
| `PY -c "import labpaths as L; print(L.CLAUDE)"` (cwd BIN) | prints a path ending `claude.exe` that exists |
| `"<L.CLAUDE>" --version` | prints a version string |
| `RUNG\CLAUDE.md` and `RUNG\.claude\` | **absent** (record present/absent; absence is not required to continue Stages 0–4) |
| free disk on C: | ≥ 20 GB |

0.3 Gate 0: all rows pass except the `RUNG` row, which is informational.
`PLOG 0.2 PASS "preflight" ...` with the numbers, or `PLOG 0.2 FAIL` with the failing row
and **stop the whole build** — nothing downstream can be trusted on a broken preflight.

---

## Stage 1 — build the vector side from the existing index (free, CPU ≤ 2 h)

Inputs: `DB`. Outputs: `OUT\captions.f16.npy`, `OUT\captions_ids.jsonl`, `OUT\titles.f16.npy`,
`OUT\titles_ids.jsonl`, `OUT\build_manifest.json`, optionally `OUT\pages.f16.npy` +
`OUT\pages_ids.jsonl`. Writes: those files, `STATE\b_embed_build.json`, progress lines.

1.1 Write `BIN\b_embed_build.py`. Behaviour, fixed:

- Open `DB` read-only. Iterate `SELECT rel, page_index, body FROM pages` in rowid order.
- **Caption units.** For every line of every page matching the regex
  `^\s*Table\s+[A-Za-z]?\.?\d+(\.\d+)*\s*[:.\-–]\s*(.{3,160})$` (multiline), take group 2
  stripped as `caption`. Unit text = `f"{doc_title} | {caption}"` where `doc_title` is the
  first non-empty line of that document's page 0 truncated to 120 characters, or the
  filename stem if page 0 is empty. Deduplicate on `(rel, unit_text)`, keep the first
  page_index. Expected count: **60,000–120,000** (a 1-in-25 page sample today projected
  88,700 before dedupe). Outside that range → log the count and continue; below 20,000 →
  `FAIL`, the regex is wrong, inspect 20 random pages containing the word "Table" and fix
  the regex once, rerun. Do not loosen the regex below the `Table <number>` anchor.
- **Title cards.** One per row in `files` with `status='indexed'`: text =
  `f"{filename stem} | {first 600 chars of page 0 (or of the first page for non-PDF)}"`.
  Expected count exactly 13,634.
- **Embedding.** `fastembed.TextEmbedding("BAAI/bge-small-en-v1.5")`, `batch_size=128`,
  default threads (today's measurement: 16 threads gave no gain over the default). Store
  vectors as float16 in a `.npy` written via `numpy.lib.format.open_memmap`, L2-normalised
  before storing. Ids file: one JSON per line `{"i": n, "rel": ..., "page_index": ...,
  "text": ...}` in the same order. Write `build_manifest.json` with counts, model name,
  wall seconds per unit type, and the sha256 of `DB` as recorded in its `meta` table if
  present (else file size + mtime).
- **Resumable**: if the output for a unit type exists and its manifest count matches the
  freshly extracted count, skip that unit type. Never rebuild silently; log `skipped`.
- Measure and print the embed rate per unit type. Record to `STATE\b_embed_build.json`.

1.2 Run captions and titles: `PY -u BIN\b_embed_build.py --db DB --out OUT --units captions,titles`.
Time budget: **2 hours** wall. If not finished by then, kill it, log `stopped` with the
counts done so far, and continue to 1.3 only if titles finished; captions may be
completed on a later run since the script resumes.

1.3 **Static-model page embedding, decided by measurement.** Install `model2vec` into the
venv (`PY -m pip install model2vec`). Write `BIN\b_bench_static.py` that loads
`minishlab/potion-retrieval-32M` via `model2vec.StaticModel.from_pretrained`, embeds 512
real pages (`SELECT body FROM pages WHERE rowid % 997 = 0 LIMIT 512`, truncated to 2,000
chars) and prints pages/s. Also measure query-side: 100 short strings, ms per string.
Rule:

- If pages/s **≥ 250** → run `b_embed_build.py --units pages --model potion` (add the
  `--model` switch: `bge` default, `potion` uses model2vec; potion vectors are 512-d and
  L2-normalised the same way; write to `OUT\pages.f16.npy`). Budget 90 minutes wall;
  1,206,260 pages at 250/s is 80 minutes. Kill at 90 and mark partial; partial page
  vectors are **not used** (delete them) — a partial channel would make the gate
  unrepeatable.
- If pages/s **< 250** → do not build page vectors. Record the rate.

1.4 Gate 1: `titles` count = 13,634 and `captions` count ≥ 20,000 and both `.npy` files
load with `numpy.load(mmap_mode="r")` and have the stated row counts.
`PLOG 1.4 PASS` with `n_captions`, `n_titles`, `n_pages` (0 if none), `captions_per_s`,
`titles_per_s`, `potion_pages_per_s`. On failure `PLOG 1.4 FAIL` and stop the build: the
next stages need these files.

---

## Stage 2 — the front door `b_search.py` (free, ≤ 90 min)

Inputs: `DB`, `OUT`. Outputs: `BIN\b_search.py`, `BIN\b_prompts.py`, `REG` entry for
`RUNG`. Writes: those, `STATE\b_search_selftest.json`, progress lines.

2.1 Write `BIN\b_prompts.py` containing exactly one constant, `REWRITE_INSTRUCTION`,
used verbatim by both `CLAUDE.md` (Stage 4) and the offline rewrite script (Stage 3):

```
Write 6 search queries for the question, one per line, numbered 1-6, nothing else.
1. the question itself, word for word
2. the name a Pakistani government statistical publication would print for this series or table row (a noun phrase, no verbs)
3. the same concept using an alternative official term, spelling or acronym (for example defence/defense, labour/labor, receipts/revenue, expenditure/spending, programme/program)
4. the publication most likely to carry the table, plus the fiscal year or years involved, written like 2015-16
5. only the two to four nouns that name the subject, the place and the period - drop every question word and every conversational filler word
6. how the subject would appear in a memo, a note or a spreadsheet file name
```

2.2 Write `BIN\b_search.py`. Command grammar, fixed. Every subcommand accepts
`--db PATH` and `--vec DIR` overrides; without them it resolves the corpus root by
walking up from the current directory until a path matches a key in `REG`, and errors
with `NO_REGISTERED_ROOT` (exit 2) if none does.

```
b_search.py search --q "…" [--q "…" …] [--k 20] [--pool 200] [--no-vec] [--no-rerank] [--slug NAME]
b_search.py exact "literal phrase" [--k 50]
b_search.py page "<rel>" <page_index> [--slug NAME]
b_search.py note --slug NAME "text"
b_search.py notes --slug NAME
b_search.py coverage
b_search.py register --root DIR --db PATH --vec DIR
```

`search` pipeline, fixed:

1. For each `--q` (1–8 accepted; the first is treated as the user's question):
   - `lex_all`: FTS5 `MATCH` on every content word ANDed (content words as in
     `corpus_search.content_words`, import it), ordered by `bm25(pages)`, LIMIT 300. If
     the query has ≤ 4 content words, run the quoted phrase instead of the AND.
   - `lex_any`: FTS5 OR of the content words, `bm25`, LIMIT 300.
   - `vec_cap`: embed the query with bge-small, cosine against `captions.f16.npy`
     (`numpy` dot on float32 copies of the query only; keep the memmap float16), top 300,
     mapped to `(rel, page_index)`.
   - `vec_title`: same against `titles.f16.npy`, top 100, mapped to `(rel, 0)`.
   - `vec_page`: only if `pages.f16.npy` exists and `--no-vec` not given; top 300.
2. Reciprocal-rank fusion with k = 60 over every list from every query; a key is
   `(rel, page_index)`. Keep the top `--pool` (default 200).
3. Rerank the pool with `TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2")` against the
   first `--q`. Passage = 900 characters of the page starting 300 before the first
   occurrence of the rarest query content word present on that page (rarest = fewest
   FTS5 matches; cache document frequencies in a dict for the run); if no query word is
   present, the first 900 characters. Skip with `--no-rerank` (then order = fused order).
4. Output the top `--k` (default 20) grouped by document, at most 3 pages per document,
   in this exact line format, one page per line:
   ```
   [ 1] 0.873  Sources/Federal/…/File.pdf  p522  not-opened  | …snippet 160 chars…
   ```
   `not-opened` becomes `OPENED` if `page` was called for that `(rel, page_index)` under
   the same `--slug` earlier (kept in the notes file's header lines).
5. Print a receipt after the list:
   ```
   RECEIPT queries=6 lex_all=[n1,…] lex_any=[…] vec_cap=[…] vec_title=[…] vec_page=[…] fused=200 reranked=200 rerank_s=3.1
   COVERAGE indexed=13634 image_only_no_text=1211 failed=32 unsupported=120 pages=1206260
   NOTE: a page that is not opened is not evidence. Use: page "<rel>" <page_index>
   ```

`exact`: FTS5 phrase query `"…"`; print `TOTAL_PAGES_MATCHING=<n>` first, then up to
`--k` hits in the same line format grouped by document, then the COVERAGE line. For
`n == 0` print additionally `NO_PAGE_IN_THE_INDEX_CONTAINS_THIS_STRING` followed by the
count of files the index could not read (image-only + failed), so the model can qualify
its negative.

`page`: print `OPENED <rel> p<page_index> (<n_chars> chars)` then the page body, capped
at 12,000 characters with `…[truncated, N more chars]`. Append a header line
`opened\t<rel>\t<page_index>` to the slug's notes file when `--slug` is given.

`note`: append `- <text>` to `NOTES\<slug>.md`, creating it. `notes`: print the file, or
`NO_NOTES_YET` if it does not exist.

`register`: write/merge the `REG` JSON, key = lowercased resolved root with forward slashes.

Performance requirement: `search` with 6 queries must return in ≤ 12 s wall on this
machine including model load (measure; if model load dominates, cache the ONNX session
in a module-level global and note that a cold call pays it once per process).

2.3 Register the rung: `PY BIN\b_search.py register --root RUNG --db DB --vec OUT`.

2.4 Self-test, from cwd `RUNG` (this is read-only use, nothing is installed yet). Record
each result in `STATE\b_search_selftest.json`:

| test | pass condition |
|---|---|
| `coverage` | prints the COVERAGE line with pages=1206260 |
| `exact "Finance Division, Government of Pakistan"` | TOTAL_PAGES_MATCHING ≥ 1000 |
| `exact "zqxv-nonexistent-string-9931"` | TOTAL_PAGES_MATCHING=0 and the NO_PAGE line |
| `search --q "cotton production" --q "Agriculture: Cotton Production" --no-rerank` | returns 20 lines, receipt shows non-zero lex and vec counts |
| `search` same with rerank | returns in ≤ 12 s; rerank_s printed |
| `page` on the first hit with `--slug selftest` | prints OPENED and body; `notes --slug selftest` shows the opened header |
| `search` again with `--slug selftest` | that hit now shows OPENED |
| `note --slug selftest "x"` then `notes` | shows `- x` |
| a bogus subcommand | exit code 2 and a usage line |

Gate 2: all nine pass. `PLOG 2.4 PASS` with `search_wall_s`. Otherwise fix and rerun; if
still failing after two fixes, `PLOG 2.4 FAIL` and stop.

Delete the `selftest` notes file afterwards.

---

## Stage 3 — the offline gate: does the right file reach the top 20? (free, ≤ 60 min)

Inputs: the frozen 20 (`_private/results/04_scores/question_sample.json`), the key
(`_private/harness_keys/answer_key.json`), `b_search.py`. Outputs:
`STATE\b_queries.json`, `STATE\b_offline_gate.json`, a finding in `FINDINGS_LIVE.md`.
Writes: those, progress lines.

3.1 Write `BIN\b_queries.py`. For each of the 20 frozen questions (read the question text
via `labpaths` and the key; keep only `q_id` and `question` in memory) call:

```
[L.CLAUDE, "-p", REWRITE_INSTRUCTION + "\n\nQuestion: " + question,
 "--model", "claude-haiku-4-5-20251001", "--output-format", "text", "--max-turns", "1",
 "--disallowedTools", "Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "Agent", "NotebookEdit"]
```

with `cwd = LAB\99_scratch\b_llm_cwd\` (create it; it must contain no `CLAUDE.md`), stdin
from `os.devnull`, timeout 120 s, stderr to a file. Parse the six numbered lines; if fewer
than 4 parse, retry once; if still fewer than 4, fall back to `[question]` alone and mark
`rewrite_failed=true`. Save `{"q_id":…, "queries":[…], "rewrite_failed":…}` per question
to `STATE\b_queries.json`. Also generate rewrites for the **12 absence questions not in the
frozen 20** (type `absence` in the key) and save them under a separate key `absence_extra`.
Total: 32 Haiku calls, roughly 5–10 minutes. These draw on the Max subscription, not API
dollars; record `n_calls`.

3.2 Write `BIN\b_offline_gate.py`. For each of the **17 answerable** frozen questions
(the 3 absence ones are handled in 3.3), build the evidence set as the set of
`evidence_addresses[].path` normalised (`corpus_search`-style: forward slashes,
lowercase), and the decoy set from `must_not_cite[].path`. Run these configurations by
calling `b_search.py`'s functions in-process (import it; do not shell out 68 times):

| config | queries | vec | rerank |
|---|---|---|---|
| A `bm25_single` | question only, `lex_any` only | off | off |
| B `mq_lex` | all rewrites, lex channels only | off | off |
| C `mq_lex_vec` | all rewrites | on | off |
| D `mq_lex_vec_rr` | all rewrites | on | on |

For each config record, per question: rank of the first evidence file in the fused/
reranked list (search depth 200 for A–C; the reranked 200 for D), whether an evidence file
is in the top 20 and top 5, whether the exact evidence `page_index` (when the key gives
one) is in the top 20, and whether any decoy outranks the first evidence file. Aggregate
per config: `n_file_top20`, `n_file_top5`, `n_page_top20`, `n_decoy_first`, mean rank
when found. Write `STATE\b_offline_gate.json`. Print the table.

3.3 Absence diagnostic (not a gate): for the 3 frozen absence questions and the 12 extra,
run config D and record the top-5 lines' documents and scores. Record only counts and
score summaries in the state file plus the top-5 `rel` values (these are corpus paths,
not key material). This tells the write-up whether the pool offers a plausible wrong
answer.

3.4 **Gate 3 — the numbers that decide whether money is spent:**

| measure (config D unless stated) | outcome |
|---|---|
| B `mq_lex` `n_file_top20` ≥ 6 of 17 | multi-query alone justified the build; note it |
| D `n_file_top20` **≥ 9 of 17** | **PASS → Stage 4 and 5** |
| D `n_file_top20` 5–8 of 17 | **PASS-WEAK** → Stage 4 and 5, but the battery ceiling drops to $8 and the write-up leads with the gap |
| D `n_file_top20` ≤ 4 of 17 | **FAIL → skip Stage 5**; do Stage 4 (the installer is free), then Stage 6 |

`PLOG 3.4 PASS|PASS-WEAK|FAIL "offline gate"` with all four configs' `n_file_top20`,
`n_file_top5`, `n_page_top20`, `n_decoy_first`.

3.5 Append finding **F30** to `corpus-lab/05_findings/FINDINGS_LIVE.md`: a dated section
with the four-row table, one sentence on which component moved the number (compare A→B,
B→C, C→D), the absence diagnostic in one sentence, and the condition it depends on ("this
corpus, this key, rewrites from Haiku 4.5 rather than from the answering model"). No
question text, no evidence paths.

---

## Stage 4 — installer and `CLAUDE.md` for `s6_hybrid` (free, ≤ 30 min)

Inputs: `stack.py` (import only). Outputs: `BIN\b_stack.py`. Writes: that file,
`STATE\b_stack_roundtrip.json`, progress lines.

4.1 Write `BIN\b_stack.py` with `setup --corpus DIR`, `teardown --corpus DIR`,
`status --corpus DIR`. It imports `BACKSTOP_DENY` from `stack.py` and nothing else from
it. Behaviour:

- `setup`: refuse (exit 3, message `ANOTHER_STACK_PRESENT`) if `DIR\CLAUDE.md` or
  `DIR\.claude\` exists. Otherwise write the state file
  `LAB\99_scratch\b_stack_state__<corpus-key>.json` **first** (`{"stack":"s6_hybrid",
  "corpus":…, "created":[…], "status":"installing"}`), then create `DIR\.claude\settings.json`
  containing `{"permissions": {"deny": BACKSTOP_DENY}}` and `DIR\CLAUDE.md` with the text
  in 4.2, then set state `installed`.
- `teardown`: delete exactly the files listed in the state file, remove `DIR\.claude` if
  it is empty, delete the state file, print `TORN_DOWN`. Idempotent: if no state file,
  check the two paths are absent and print `ALREADY_CLEAN`; if they exist without a state
  file, **do not delete them** (they may be another agent's), print `FOREIGN_FILES_PRESENT`
  and exit 3.
- `status`: print which of the two files exist and whether a state file exists.

4.2 `CLAUDE.md` text, verbatim, with `{PY}`, `{SEARCH}` substituted by absolute paths
(`SEARCH` = `BIN\b_search.py`) and `{REWRITE}` by `REWRITE_INSTRUCTION`:

```
# How to answer questions from this research folder

Built-in Grep and Glob miss most of this tree (PDFs, spreadsheets, scanned files). Do
not rely on them. A search over every readable page is available and you must use it.

## 1. Search — always several queries in one call

Before searching, {REWRITE}

Then run ONE command with all six as separate --q arguments, the question first:

    "{PY}" "{SEARCH}" search --slug <short-slug> --q "<question>" --q "<2>" --q "<3>" --q "<4>" --q "<5>" --q "<6>"

Pick a short slug for this question (letters and digits) and reuse it in every command
for this question. For a literal identifier (an SRO number, a demand number, a code) also run:

    "{PY}" "{SEARCH}" exact "<the literal string>"

## 2. Open before you trust — a search line is an advertisement, not evidence

Every result line says not-opened until you open it. You may not cite, quote or take a
number from a page you have not opened. Open a page with:

    "{PY}" "{SEARCH}" page "<path exactly as printed>" <page_index> --slug <slug>

Open the top candidates one at a time. For a question spanning years, open the matching
page in each edition the search surfaced (different years' editions are different files).

## 3. Save what you find to the notes file, then answer only from the notes

After opening a page that carries something useful, record it immediately:

    "{PY}" "{SEARCH}" note --slug <slug> "<the exact line or table cell, verbatim> | <path> | p<page_index>"

When you have gone through the candidates, print your notes:

    "{PY}" "{SEARCH}" notes --slug <slug>

Write the answer from the notes and nothing else. Every number carries the file path and
page_index it came from, and the verbatim line it came from. If two sources disagree,
show both with their citations; do not pick one silently.

## 4. When it is not there, say so

If the notes are empty after opening the candidates, answer that no supporting evidence
was found, list the queries you ran, and quote the COVERAGE line so the reader knows how
many files could not be read (image-only and failed). For a literal identifier whose
exact search printed TOTAL_PAGES_MATCHING=0, say that no readable page contains it. Never
supply a figure from memory or from a snippet.

## 5. Copies

The folder holds partial copies, drafts and older versions of the same publications.
Prefer the copy with the most pages when several carry the same title, say which copy
you used, and do not name copies you did not open unless the question is about the copies.
```

4.3 Round-trip test on a scratch directory, **not** the rung: create
`LAB\99_scratch\b_roundtrip\` with a dummy `a.txt`; `setup`; assert both files exist and
`settings.json` parses with a `permissions.deny` list of length `len(BACKSTOP_DENY)`;
`teardown`; assert both gone, `.claude` gone, `a.txt` intact; then create a stray
`CLAUDE.md`, run `setup`, assert exit 3 and nothing written; remove the scratch dir.
Record in `STATE\b_stack_roundtrip.json`. Gate 4: all assertions hold. `PLOG 4.3 PASS`.

---

## Stage 5 — paid measurement on the frozen 20 (only if Gate 3 was PASS or PASS-WEAK)

Ceilings: canary battery ≤ $3 and ≤ 40 min; question battery ≤ $12 ($8 on PASS-WEAK) and
≤ 60 min; extra absence battery ≤ $4 and ≤ 30 min. `cost_usd` comes from each session's
result record; sum it after every 5 completed sessions. On a Max plan these draw from the
subscription's limits; the dollar figure is the comparability number. If a ceiling is
hit: stop launching new sessions, let running ones finish, and record the battery as
**partial with n-of-m** — never score a partial battery as if it were whole, and never
fill it in later without a fresh `--only` run that is logged.

5.1 **Exclusivity.** Check `RUNG\CLAUDE.md` and `RUNG\.claude\` are absent and that the
last 20 lines of `progress.jsonl` contain no `started` from another run within the past
30 minutes without a matching `PASS|FAIL|stopped`. If either check fails, wait 5 minutes
and re-check, up to 12 times (60 min). Then `PLOG 5.1 stopped "rung busy"` and go to
Stage 6. Do not install over another agent's files, ever.

5.2 Pre-battery integrity. With env `CANARY_MANIFEST` set to
`ROOT\_private\canaries\canary_manifest_pass2.csv` **for this one command only**:
`PY BIN\checksums.py snapshot --label s6_pre`. Record the count of files under
`%USERPROFILE%\.claude\projects\C--Users-Ali-Desktop-retrieval-lab-harness-corpus-15000\memory\`
(0 if absent) as `mem_before`. `PLOG 5.2 PASS`.

5.3 Install: `PY BIN\b_stack.py setup --corpus RUNG`; `status` must show both files.
`PLOG 5.3 PASS`.

5.4 **Canary battery** (does the new front door still find literal strings?). Run, with
env `CANARY_MANIFEST=ROOT\_private\canaries\canary_manifest_pass2.csv` and `CORPUS_DB=DB`
set for this command only:

```
PY -u BIN\run_canaries.py --phase PHASE --stack s6_hybrid --corpus-kind rung --rung 15000 --corpus-label h15000 --timeout 420 --parallel 3
```

(this is what `run_grid.py` step 6 runs for tree `h15000`; read its lines 170–192 if in
doubt). Gate: **≥ 15 of 17** found. Below 15 → `PLOG 5.4 FAIL`, teardown (5.8), skip 5.5–5.6, go to 5.9
— a front door that loses literal strings is a regression regardless of vague-question
gains. Record cost n-of-m.

5.5 **Question battery.**
`PY -u BIN\run_harness.py --phase PHASE --stack s6_hybrid --rung 15000 --model MODEL --max-turns 25 --timeout 300 --parallel 2`.
Do not pass `--settings`; the corpus's own `.claude/settings.json` is what production
uses. Watch the wall clock and the running cost; apply the ceiling rule. On completion
`PLOG 5.5 PASS|stopped` with `n_done`, `cost_usd`, `cost_n_of_m`, `timeouts`.

5.6 **Extra absence battery** (only if 5.5 completed all 20): for each of the 12 absence
questions not in the frozen sample, call `ask.py` directly with the same arguments
`run_harness.one()` builds (read it), phase `PHASE_abs`, qid = the key's `q_id`, and the
same appended sentence about citing paths and pages. Ceiling $4 / 30 min.
`PLOG 5.6 PASS|stopped` with n-of-m.

5.7 Post-battery integrity: `PY BIN\checksums.py verify --against s6_pre` (same env as
5.2). Any mismatch → `PLOG 5.7 FAIL "planted file changed"` and say so in the write-up;
**verify, never restore.** Count memory files again; if `mem_after > mem_before`, move
the new files to `ROOT\_private\results\_memory_quarantine\PHASE\` and log the count.

5.8 **Teardown, unconditionally:** `PY BIN\b_stack.py teardown --corpus RUNG`, then
`status` must print both files absent. `PLOG 5.8 PASS`. If teardown fails, retry once,
then write the two paths into the progress note in capitals and keep going — Ali must
see it first thing.

5.9 Scoring. `run_harness.py` has already written
`_private/results/04_scores/harness__s6_hybrid__rung15000.json` and the summary. Add
`BIN\b_score_extra.py` which reads the raw `.jsonl` streams in
`_private/results/03_runs/PHASE/` and computes, per question:

- `surfaced`: an evidence path appears in any `tool_result` text;
- `opened`: an evidence path appears in a `page` command's arguments (parse the Bash
  command strings for `page "<rel>" <n>`) or in `files_opened`;
- `quoted`: the answer text contains the evidence path (tail-2 rule from `scoring.py`) and
  at least one `note` command was issued;
- `forbidden`: as `run_harness.py` (opened or named a `must_not_cite` file);
- for absence questions (3 frozen + 12 extra): `declined` by the `run_harness.DECLINE`
  regex, and `figures_asserted` = count of numeric tokens in the answer that are **not**
  fiscal-year shaped (`\d{4}-\d{2}`), not four-digit years, not inside an identifier
  like `SRO 1500(I)/2024`, and not the coverage counts printed by the tool (13634, 1211,
  1206260 and their comma forms). `absence_ok2 = declined and figures_asserted == 0`.

Write `_private/results/04_scores/extra__s6_hybrid__rung15000.json` and a summary with:
`n_surfaced/17`, `n_opened/17`, `n_quoted/17`, `mean_recall` (from the harness score),
`forbidden_total`, `absence_ok2 = a/15` (or `/3` if 5.6 did not run), cost n-of-m,
mean wall excluding suspended. `PLOG 5.9 PASS` with those numbers.

**Gate 5 (reported, not enforced — the write-up states pass/fail):**
`n_opened ≥ 6 of 17` (published best: 1) **and** `absence_ok2 ≥ 10 of 15` **and**
`forbidden_total ≤ 8` (published: 16–21).

---

## Stage 6 — write-up and handoff (free, ≤ 30 min)

6.1 Append to `FINDINGS_LIVE.md`: **F31** (canary result, one paragraph), **F32** (the
question battery: the harness summary numbers next to S0/S1/S2's, the `extra` numbers,
and which of the three parts — rewrites, vectors, rerank, notes loop — the evidence says
did the work, using Stage 3's ablation table), **F33** (absence: the 15-question result
under `absence_ok2`, and the three frozen ones under the old rule for comparability). Each
finding ends with its condition line. Numbers only; no question text, no evidence paths.

6.2 Write `STATE\b_summary.json` with every gate's status and numbers, the ceilings and
what was spent, and `stopped_reason` if any stage stopped early.

6.3 Add a dated note at the top of `GRID.md` under the existing SUPERSEDED note:
"s6_hybrid measured YYYY-MM-DD, see FINDINGS_LIVE F30–F33 and state/b_summary.json." **Do
not run `build_grid.py`** (it regenerates the table and drops notes).

6.4 Add three lines to `corpus-lab/RESUME.md` §0 pointing at `plans_fable/` and
`state/b_summary.json`.

6.5 `PLOG 6.5 PASS "build B complete"` with `total_cost_usd`, `stages_passed`,
`stages_stopped`. Print the same summary to stdout as the last thing you do. Do not
commit anything in `corpus-lab/.git`; Ali commits.

---

## Named recoveries

| symptom | do this |
|---|---|
| `claude.exe -p` returns prose but you asked for text — fine; returns nothing / rc≠0 | read the stderr file; if it mentions login or trust, `PLOG … stopped "claude needs interactive login"` and skip everything that needs sessions (3.1 rewrites: fall back to `[question]` only and mark it; Stage 5 entirely) |
| A session hangs past its timeout | `ask.py` already `taskkill /T /F`s the tree; if a `node.exe` survives, kill it by PID and log it |
| fastembed downloads a model and the network is down | captions/titles use the cached bge-small (already in `%TEMP%\fastembed_cache`); the reranker needs one download of ~80 MB — if it fails, run configs A–C, mark D as `not_run — reranker download failed`, and use C's number for the gate |
| `numpy` memmap of captions fails to load (corrupt partial write) | delete `OUT\captions*` and rerun Stage 1 for captions only |
| `TOTAL_PAGES_MATCHING` for a phrase raises an FTS5 syntax error (quotes, `-` inside) | escape embedded double quotes by doubling them; never strip the user's string silently |
| Deny list blocks one of your own commands while the stack is installed | your cwd is `ROOT`, not the rung, so the rung's settings do not apply to you; if it happens anyway, your cwd is wrong — fix the cwd, do not edit the deny list |
| `run_harness.py` reports `SKIPPED-STALE` | a result with this phase name already exists; you reused a phase label — pick `PHASE` + `_r2` and rerun; never `--force` |
| Battery ceiling hit | stop launching; record n-of-m; the summary must say `partial`; `--only` the missing q_ids later **only** with a fresh progress line explaining it |
| `checksums.py verify` fails | do not restore; record which file, keep the battery's numbers but flag them `corpus_mutated=true` in every summary |
| Another agent's files appear in the rung during your battery | finish nothing further; teardown yours; `PLOG … FAIL "concurrent install detected"`; the battery is void |
| The `memory` dir gained files | quarantine as in 5.7; note it; do not read them |
| You realise a number in a prompt or code came from the key | delete it, `PLOG … PASS "contamination_averted" contamination_averted=1`, rerun the affected stage from scratch |
