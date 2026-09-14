# retrieval-lab — the whole project, start to finish

*Assembled 2026-09-13. Everything in this folder is a **copy**; every original is still
where it was. Nothing here was edited in the copying.*

This folder collects every report and result produced by the project so far, in the order
they happened, with a plain-English walkthrough. If you have never seen this repository,
read this page top to bottom and you will know what the problem is, what was tried, what
each attempt actually measured, what is solved, and what is not.

There is one deliberate omission: nothing from `_private/` is copied here. That tree holds
the answer keys for the test questions. Keeping it out means this folder can be read by
anyone — including a future automated test run — without contaminating a measurement.

[`MANIFEST.md`](MANIFEST.md) lists all 46 files with the original path and a checksum for
each, so any copy can be traced back and verified against its source. Three were written
directly here and two carry a superseded-recommendation notice; the manifest marks both.

*On GitHub, one file listed in the manifest is absent: `ACCEPTANCE.md` is an oracle (gold
paths, literal values, page indices) and is excluded from the repository — see
[`04_evidence_v1_build/ACCEPTANCE_NOT_PUBLISHED.md`](04_evidence_v1_build/ACCEPTANCE_NOT_PUBLISHED.md).
It is present in the local copy.*

---

## 1. The problem, in one paragraph

Someone has a research folder — roughly 15,000 files, mostly PDFs of government
statistical publications, many of them near-identical yearly editions of the same
report. He wants to open Claude Code in that folder, ask a question in ordinary language
— *"how does Pakistan's development spending trajectory look since 2015?"* — and get the
actual number back, with the file and page it came from. And when the answer genuinely
isn't in the folder, he wants to be told that, rather than be handed a confident
invention.

Those are two separate requirements, and the project scores every attempt on both:

1. **Right page, cited.** Did the correct source page actually reach the model, and did
   the model actually open and cite it?
2. **Honest absence.** When the material isn't there, does it say so?

Cheaper, faster, or fewer tool calls are not progress on their own.

**Why it's hard, specifically:** the corpus repeats itself. The same fiscal table is
republished every year across dozens of editions, so hundreds of documents match a
question's words about equally well. A question like "over the last decade" doesn't name
the years it wants. This turns out to be the central difficulty, and it took four nights
of measurement to isolate it.

**Read next:** [`00_orientation/PROJECT_INDEX.md`](00_orientation/PROJECT_INDEX.md) (the
repo map and ground rules), [`00_orientation/SOLVE_BRIEF.md`](00_orientation/SOLVE_BRIEF.md)
(the problem stated for an outside designer, with all the evidence and deliberately no
suggestions).

### The measuring apparatus

Because the real folder can't be experimented on, a stand-in was built: `harness/corpus_15000`,
15,010 files shaped like the target. Of those, 13,634 have extractable text across
1,206,260 pages. The rest are genuinely unreachable without OCR — 1,211 image-only PDFs,
18 encrypted, 14 parser failures, 120 unsupported types, 13 zero-byte files. That 8%
image-only share is a real, unfixed coverage hole, and nobody has yet checked what the
equivalent number is in the actual target folder.

Two test batteries run against it:

- **Canaries** — a known phrase is planted in a known file, and the session is given the
  exact phrase and asked which file holds it. This tests whether a tool can find something
  you can already quote. It is the easy test.
- **Questions** — a frozen set of 20 vague questions (17 answerable, 3 where the answer is
  deliberately absent), scored against an answer key naming the exact evidence pages. This
  is the real job. A larger 135-question key exists behind it.

Everything below is scored on the question battery unless it says otherwise.

---

## 2. Night 1 — can stock tools already do this?

📁 [`01_night1_stock_tools/`](01_night1_stock_tools/)

The first night tested Claude Code with no additions, on a real repository fixture
(`ra-ship`). It found 4 of 12 planted phrases and the conclusion drawn was that a search
index was clearly needed.

**That conclusion was later shown to be mostly wrong**, and it's worth understanding why,
because it's the project's best example of a fixture lying to you. `ra-ship` is a git
repository whose `.gitignore` excludes every document directory — so the built-in search
skipped the documents by design, not by weakness. When the same test ran on the
harness (no `.gitignore` anywhere), stock search found **15 of 17**. Stock tools on a plain
folder are fine. Night 1's headline was an artifact of the test subject.

Files: the full write-up, the night's decision memo (superseded), and its ranked list of
open questions.

---

## 3. Night 2 — the bake-off

📁 [`02_night2_bakeoff/`](02_night2_bakeoff/)

Six approaches ("stacks") were specified; three were measured end to end and three were
stopped with a measured reason rather than a guess.

| stack | what it is | planted-phrase test | real questions |
|---|---|---|---|
| s0_baseline | stock Claude Code, nothing added | 15/17 | 0.167 |
| s1_policy | full-text index + a line in `CLAUDE.md` telling the model to use it | 17/17 | 0.176 |
| s2_hook | same index, but a hook *forces* its use | 17/17 | 0.118 |
| s3_hybrid | add semantic/embedding search | not built | — |
| s4_pdfmcp | a PDF-specific MCP server | install gate failed | — |
| s5_recoll | a desktop search engine | no headless installer exists | — |

Three things came out of this night, and all three still stand:

1. **Telling the model is enough; forcing it adds nothing.** One line in `CLAUDE.md` moved
   index adoption from 0 of 38 sessions to 38 of 38. The hook that enforced the same thing
   scored slightly worse and removed the fallback path. **This is the single finding that
   is adoptable today**, and it's cheap.
2. **None of it moved the actual result.** 0.167 / 0.176 / 0.118 are all inside noise.
   Absence was answered honestly **0 out of 3 times on every stack** — every one of them
   invented an answer rather than admitting the material wasn't there.
3. **The three unbuilt stacks were ruled out on measurements, not opinion.** Embeddings
   over full pages ran at 8.2 pages/s on this CPU-only machine, projecting a 40.9–46-hour
   build. The PDF MCP server took 415 seconds to process five small PDFs and accepted
   neither a directory nor a glob. Recoll has no unattended install path on Windows.

Cost to here: about $31 across 189 measured sessions. Everything after this night was free.

---

## 4. Night 3 — re-scoring, and the experiment that closed a door

📁 [`03_night3_rescore_and_rank/`](03_night3_rescore_and_rank/)

Entirely offline; no sessions run, nothing spent. Four results, all machine-readable:

**The scorer was undercounting.** It only saw files the agent named in a tool *input*, so
a file the agent learned about from a search *result* was invisible to it — which
structurally penalised exactly the index stacks. Re-scored: s1 0.176 → 0.235, s2 0.118 →
0.176, s0 unchanged. The ordering still sits inside noise. (`rescore_from_results.json`)

**A second, independent failure was hiding underneath the first.** On 5 of 17 questions,
the search *did* hand s1 a correct document — and the agent opened **none of them**. Three
were cited without ever being opened. No amount of retrieval improvement fixes this; it is
a behaviour problem downstream of retrieval, and it is why the "quote the line before you
cite it" rule was later written.

**A relevance score cannot decide absence.** Questions whose answers don't exist score
inside the same range as questions whose answers do. There is no threshold that separates
them. This kills the obvious approach to the honest-"not here" half of the goal.
(`probe_score_floor.json`)

**And the decisive one:** the search front door had a bug — it required *every* word of the
question to match, so a nine-word question matched nothing at all. Fixing it removed every
empty result and improved finding by **exactly nothing**: across eight different ways of
turning a question into a query, the right file appeared in the global top-50 on **0 of 17
questions**. The correct page typically sits at rank ~500–3,000 out of 1.2 million.
(`rank_experiments.json`, `verify_search_fix.json`)

That last result is the hinge of the whole project. **Word-matching over a flat pile of
pages is finished here.** It is not a tuning problem.

---

## 5. Night 4, part one — evidence_v1, a purpose-built engine

📁 [`04_evidence_v1_build/`](04_evidence_v1_build/)

Given that ranking whole pages fails, the next idea was to stop indexing pages and index
**tables** instead — build a catalogue of table "cards" (caption, row labels, column
headers, units, source line), search that much smaller and higher-signal space, then open
and verify the actual cell on the original page before answering. `SOLUTION.md` is the
design; `BUILD_PROMPT.md` is the contract it was built against — a strict staged
specification with named stop conditions, a spending cap, and a rule that the corpus is
never modified.

**Stages 1 through 4 genuinely passed.** Corpus integrity verified byte-identical.
Scorer and answer-oracle audited against the frozen questions. The full runtime
(store, inventory, extraction, catalogue, retrieval, verification, answer compiler, hooks,
installer) built and unit-tested — 61 of 64 free tests passing, plus clean
install/uninstall round trips. A cold catalogue build over all 15,010 files finished in
1,109 seconds against an 1,800-second budget, with every file accounted for.

Two real infrastructure bugs were found and fixed during that build, both caught by
comparing the database against the disk rather than trusting the build's own counters: a
cleanup step that scanned unindexed columns and got slower as the catalogue grew, and a
rare write-lock race that could silently drop a file under 8-way concurrency.

**Stage 5 — the retrieval gate — failed honestly at 3 of 17.** The contract required 15 of
17; an authorised relaxation required 10 of 17. It stopped rather than widening the bar.
No money was spent; the gate is entirely free and the stop happened before any paid
session.

**The root cause is mechanical and worth reading in full**
([`STOP_REASON_run2_retrieval_gate_failed.md`](04_evidence_v1_build/STOP_REASON_run2_retrieval_gate_failed.md)):
of 1,201,574 cards in the catalogue, **1,111,638 — 92.5% — were not tables at all.** The
specification's own rule for detecting an uncaptioned table ("an aligned block with at
least two year headers and two numeric cells within twelve lines") is satisfied by an
ordinary English sentence like *"spending shifted from 3.3 billion in 2012-13 to 3.5
billion in 2013-14."* On this corpus's prose style the detector fired on nearly every page.
So the catalogue that was supposed to be small and high-signal ended up essentially the
same size as the page index it was built to beat — 1.2 million cards versus 1.2 million
pages. The design never actually got tested.

*(There are two stop reports in this folder. The first run stopped at Stage 1 because the
corpus baseline had changed underneath it — two stray files from an old error. That was
cleaned up and the run restarted; that first report is included for completeness.)*

---

## 6. Night 4, part two — the tuning loop

📁 [`05_evidence_v1_tuning/`](05_evidence_v1_tuning/)

After the honest stop, a disciplined tuning loop ran against the retrieval layer only. The
discipline matters as much as the result: a 30-question **holdout** was frozen up front,
drawn from questions outside the tuned set and never inspected per-question. Every change
was scored on both sets, kept only if **both** improved, reverted otherwise, and logged.
Nothing was ever derived from the answer key.

Thirteen logged change attempts across six ideas — 2 kept, 11 reverted. Full ledger in
[`tuning_log.jsonl`](05_evidence_v1_tuning/tuning_log.jsonl); narrative in
[`TUNING_SUMMARY.md`](05_evidence_v1_tuning/TUNING_SUMMARY.md).

**Two genuine bugs were found and fixed:**

- **Alias matching never fired.** The lookup compared single words against multi-word
  phrases, so "non-tax revenue" could never bridge to the corpus's "non-tax receipts."
  Fixing it moved the battery from 0/17 to 3/17.
- **Table row labels were capturing numbers instead of text.** This corpus often prints a
  bare data row directly under its header, with the descriptive label appearing further
  down near the source line. The code took the first non-blank line unconditionally, so a
  large fraction of cards carried `"69.4 78.0 87.0 94.4 112.9 R"` as their label instead
  of `"Sindh — Annual Development Programme"`. This was the largest single improvement
  measured all night.

**Four ideas were tried and measured out to nothing**, each with a traced reason rather
than a shrug: tightening the false-positive table detector (made it worse three different
ways — some answers really do live only in prose sentences); multi-query fusion (summing
across rewordings rewards documents for repeating shared generic words, not for relevance);
walking the family of related table editions; and widening the vocabulary bridge from
labels observed in the corpus.

**Final: 2 of 17 on the tuned set, 3 of 30 on the holdout, against a 10-of-17 bar.**

The conclusion, stated plainly in the summary: the remaining gap is **not** a vocabulary
problem. It is that hundreds of near-identical yearly editions match a question's words
equally well — measured directly, 778 distinct cards match "Sindh" + "Annual Development
Programme" on caption alone. Which specific years a vague question wants cannot be decided
by word matching, because the question usually doesn't say.

---

## 7. Night 4, part three — Approach C, the shelf

📁 [`06_approach_c_shelf/`](06_approach_c_shelf/)

Run in parallel by a separate agent against the same index. Different idea: stop ranking
1.2 million pages and **find the document first**, the way a person does — build a "shelf"
of publications and their editions, pick the right book, then search inside that one book.

The shelf built: 12,760 distinct documents (plus 874 exact duplicates collapsed by hash,
accounting exactly to the 13,634 indexed), 1,618 publication families, 393 of them with
two or more editions, 89,380 explicit table captions harvested. Embedding those cards took
28 minutes at 7.6 per second — feasible, unlike the 40.9–46 hours full-page embedding would
have needed. All 13 self-tests pass.

**The gate result is mixed, and it is the most interesting result in the whole project:**

| measure | result | gate |
|---|---|---|
| right document ranked in top 10 | 6/17 (**9/17** with query rewrites — CORRECTED 2026-09-14) | **FAIL** — needed ≥12 |
| right page in top 5, once in the right document | **42.1% of 57** — CORRECTED 2026-09-14; the 43.9% was measured with a defective query | **FAIL** against the 60% bar |
| trajectory questions resolved across editions | 1/4 (was 0/4 — see below) | **FAIL** — needed 3/4 |
| **absence: correctly said "no edition for that"** | **11/11** | **PASS** |
| **absence: exact-identifier searches correctly returned nothing** | **4/4** | **PASS** |
| control: correctly confirmed editions it *does* hold | 14/17 was circular; the honest symmetric control is **8/11** — CORRECTED 2026-09-14 | weak pass |

> **Corrected 2026-09-14.** Four defects in the harness behind this table were found by an
> adversarial review and fixed; every historical number above still reproduces exactly from
> the same code path. What changed is what they were measurements *of*. See
> [`08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md)
> and the dated correction block at the top of
> [`06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md`](06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md).

**Finding the right document is still the failure. But absence is not.** Every earlier
stack scored 0 out of 3 on honest refusal. Approach C scored 11/11 and 4/4 — because it
stopped asking "is the score low enough?" (which night 3 proved can't work) and started
asking a structural question: *do I hold any edition of this publication for that year?*
That question has a yes-or-no answer that doesn't depend on a threshold.

The shelf itself carries a caveat: it is flagged `GATE1_FAILED_STRUCTURAL` because its
family clustering has a known defect — a repeatedly-copied paper reads as 16 "editions."
The numbers above are measured on that unrepaired shelf.

**Two things about this result were corrected on review, and both are worth knowing.**

*The trajectory number moved.* It first measured 0/4, which reads as a total failure of the
"search inside one document" idea. Writing up the gate turned up two defects in the test
rather than the approach: the in-document search was being handed the entire question as its
phrase (far past its 4-word exact-match cutoff, so it fell through to a near-useless
any-word match), and the walk was re-finding each publication family by searching for the
family's own internal name — a template containing a literal `{fy}` placeholder, which
matches no real title, so on at least one question it walked the wrong document entirely.
Fixed, it measures **1/4**. Still a failure against the 3/4 bar, but now a measurement of
the approach rather than of the harness.

*Semantic retrieval is inside these numbers, not missing from them.* The shelf ranks
documents by fusing FTS5 and BGE-small semantic top-200 lists with reciprocal-rank fusion,
plus query rewrites. So 6/17 and 9/17 (corrected 2026-09-14; 8/17 as first measured) are what lexical **and** dense retrieval achieve
together over the small card pool — which retires the idea, stated elsewhere in this repo,
that card-scale embedding was the big untried lever.

**Why it still misses, and the one concrete lead that follows.** Once the right document is
found, the search space drops from 1.2 million pages to a few hundred — and it *still*
misses, because this corpus restates each year's figure in prose across many pages of the
same publication. Measured on one real document: searching it for "cotton production"
returns eight pages, and the actual table ranks **sixth**, behind five prose restatements.
Picking the right book off the shelf shrinks the haystack; it doesn't remove it.

The lead: a `Table N.N:` caption is a *label*, not a restatement, and Stage 1 already
harvested 89,380 of them — covering **100% of every PDF ≥100 pages (1,895 of 1,895)**, i.e.
essentially all the large statistical publications. The in-document search doesn't use that
channel yet. Full detail in
[`STAGE3_OFFLINE_GATE_REPORT.md`](06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md).

---

## 8. Approach B — planned, never built

📁 [`07_approach_b_planned/`](07_approach_b_planned/)

Hybrid keyword-plus-embedding search with several query rewrites fused together and
reranked. Fully specified, evidence-checked against the lab's own numbers, never executed.
Included because the plan documents are substantial and because the parts of it that
survive scrutiny — multi-query and reranking over a *small card pool*, not over full pages
— are carried into the recommendation below.

---

## 9. Where this goes next

📁 [`08_what_next/`](08_what_next/)

[`RESEARCH_2026-09-13.md`](08_what_next/RESEARCH_2026-09-13.md) is a research pass that
reads all the evidence above and recommends a specific next build, **Shelf V2**: keep
approach C's document-first structure, but with strict table cards (only from real
captions, contents entries, native spreadsheet structure, or confirmed page geometry —
never the years-and-numbers rule that produced 92.5% junk), explicit query routing,
bounded decomposition of multi-part questions into at most four separate searches, and
page-level verification before any number is quoted. It also reuses the parts of
evidence_v1 that are known-good — inventory, content hashing, provenance records, the
evidence compiler, install/teardown, the test suite — rather than starting over.
[`EXECUTE_SHELF_V2.md`](08_what_next/EXECUTE_SHELF_V2.md) is the build contract for it.

It explicitly rejects, on this project's own measured evidence: relevance thresholds for
absence, full-page dense embedding, swapping in a search server, treating a search snippet
as a citation, and grading a design intended to run several searches by giving it one.

> ⚠️ **That recommendation is superseded —
> [`CORRECTION_2026-09-13.md`](08_what_next/CORRECTION_2026-09-13.md).** It named semantic
> retrieval over the small card pool as the central untested lever. Approach C had already
> built and measured exactly that route (BGE-small vectors over 12,760 document cards, fused
> with FTS5 by reciprocal-rank fusion, plus rewrites and family grouping) and it failed the
> offline gate. The research body is kept unchanged as the historical recommendation, and
> its individual rejections above still stand on their own evidence. What does *not* follow
> from the evidence is rebuilding the same shelf architecture as the next experiment; future
> work should be a separately specified, offline-gated ablation on the shelf that already
> exists — the caption channel in §7 being the clearest candidate.

---

## 10. The ledgers

📁 [`09_ledgers/`](09_ledgers/)

- [`FINDINGS_LIVE.md`](09_ledgers/FINDINGS_LIVE.md) — every finding as it landed, each
  with the exact condition it holds under. F1–F6 night 1, the night-2 grid run, F20–F24
  night 3, F40 approach C.
- [`progress.jsonl`](09_ledgers/progress.jsonl) — one line per step across all four nights — the
  audit trail. Appended to, never edited.
- [`RESUME.md`](09_ledgers/RESUME.md) — how to pick the work back up from cold, including
  the traps worth not rediscovering.

---

## 11. Honest summary

**What is solved:**

- Getting the model to *use* a tool you give it. One line in `CLAUDE.md`, 0/38 → 38/38.
- Knowing when the material genuinely isn't there — but only via approach C's structural
  edition check (11/11, 4/4), not via any scoring threshold.
- A large amount of trustworthy infrastructure: extraction and coverage accounting over
  15,010 files, content hashing and provenance, table-cell verification, the answer
  compiler with typed evidence, safe install and teardown, and test suites for all of it.
  None of that depends on which retrieval idea eventually wins.

**What is not solved — the one open problem:**

Putting the right page in front of the model for a vague question. Every approach tried has
failed this, and the numbers have barely moved across four nights:

| approach | best result | bar |
|---|---|---|
| stock tools / index / enforced index | 0.167 / 0.235 / 0.176 recall | — |
| eight lexical query strategies | right file in top-50: **1/17** (term-coverage rerank; 0 for the other seven) | — |
| evidence_v1 table catalogue | 3/17, then 2/17 after tuning | 10/17 |
| approach C shelf (lexical + semantic, fused) | right document in top-10: 6/17, **9/17** with rewrites (CORRECTED) | 12/17 |
| approach C, the same pool at depth 100 | right document in the pool on **16/17** (NEW) | — |
| approach C + compact cross-encoder reranker | **9/17** (NEW, gate STOP) | 12/17 |
| approach C, multi-year trajectory walk | 1/4 | 3/4 |
| approach C, right page once document is right | **24/57 (42.1%)** (CORRECTED) | 60% |
| approach C + caption-aware page retrieval | **42/57 (73.7%)**, all of it on trajectory questions (NEW) | 60% |
| approach C, structural edition selection | **3/17** (NEW) | 15/17 |

See [`08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md`](08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-14.md),
[`08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md`](08_what_next/ARCHITECTURE_REVIEW_2026-09-13.md)
and [`08_what_next/HANDOFF_2026-09-14.md`](08_what_next/HANDOFF_2026-09-14.md).

**The diagnosis is now specific, and it is the same one from two independent directions.**
The corpus is full of near-identical yearly editions of the same publications. A vague
question's words match hundreds of them about equally, and the question usually doesn't
name the year it wants. This is a *disambiguation* problem, not a vocabulary or indexing
problem — which is why better word matching, more rewordings, wider aliases, and deeper
candidate pools all measured out to approximately zero.

And it operates at **two scales, not one**: across the corpus (the right page at rank
500–3,000 of 1.2 million) and *within* a single correct document (the right table at rank 6
of 8 matching pages). Cutting the haystack from 1.2 million pages to a few hundred — which
approach C does successfully — does not by itself solve the second one.

**Matching on meaning rather than words HAS now been tested, and it did not rescue this.**
An earlier draft of this summary called it the one big untried lever, on the reasoning that
dense embedding had only ever been costed over full pages (40.9–46 hours for this harness) and not over the much
smaller card pool. Approach C then built it — BGE-small vectors over 12,760 document cards
in 28 minutes, fused with FTS5 top-200 by reciprocal-rank fusion, with query rewrites and
family grouping on top — and that combined lexical-plus-semantic route is what produced the
6/17 and 9/17 above. Card-scale semantic retrieval is measured, not missing.

**The clearest genuinely untried lever is narrower and more specific:** use the harvested
`Table N.N:` captions to tell a canonical table apart from prose that merely repeats its
subject. 89,380 captions are already extracted, covering 100% of every PDF ≥100 pages
(1,895 of 1,895). Neither the in-document search nor the series walk uses that channel yet,
and the failure it would address — the real table ranking 6th behind five prose
restatements *inside the correct document* — is measured, not hypothesised.

**A second failure that no retrieval fix addresses:** on 5 of 17 questions the right
document *was* handed to the agent and it opened none of them, citing snippets instead. A
"quote the line before you cite it" rule was written for this and has never been run.

**Spend:** about $31 total, all of it on night 2. Nights 3 and 4, the evidence_v1 build,
the entire tuning loop, and approach C's shelf build and gate were all free. Nothing is
currently running, no stack is installed in any corpus, and the corpus has been verified
byte-identical to its baseline throughout.

---

## 12. Night 5 (2026-09-15) — both "untried levers" above were tried, and the first live battery ran

**§11 named two things as the clearest untried levers. Both were built and measured tonight.
Neither rescued the project, and the second one failed in a way nobody predicted.** The
paragraphs above are kept exactly as written, because they were an honest statement of what
was believed on 2026-09-14; this section is the correction.

### The caption channel — built, measured, STOP

§11 said: *use the harvested `Table N.N:` captions to tell a canonical table apart from prose
that merely repeats its subject. Neither the in-document search nor the series walk uses that
channel yet.* Both now do, at three levels.

- **At page level inside a known-correct document** (B2, measured 2026-09-14): 24 → **42 of
  57** addresses in the top five. A large win — but **all of it on trajectory questions** and
  nothing on the other four types.
- **At corpus level as a document channel** (E1, NEW): a new FTS5 index over all **89,380**
  captions, entering each query's fusion as a third ranked list. Right document in the top ten
  **9 → 10 of 17**; on the 30-question holdout the top ten did not move (14), but recall@20
  went 16 → 20, recall@50 24 → 28, and **recall@100 28 → 29, the first movement of that
  number in the project's history**. The pre-registered gate needed both halves. **STOP.**
- **With caption embeddings as well** (E2, NEW): all 89,380 captions embedded. Dev **9**,
  holdout **13** — the first configuration to go *below* the baseline. **STOP.**

**The diagnostic that matters is not the score.** Taking the union of each question's top-20
caption hits across all six rewrites — up to 120 (file, page) pairs — a gold evidence address
appears in it on **1 of 13** questions. And a year-aware variant of the page rule (B2b, NEW)
came out *identical to B2 at every single address*, because on all **6** year-asking questions
**no caption in the correct document contains the question's subject words at all**, with or
without the year.

So the honest restatement is: **the captions this corpus yields describe the tables that
trajectory questions want and do not describe the tables the other question types want.** That
is a fact about caption *coverage*, not about caption *matching* — it cannot be fixed by
another matching rule, which is exactly what B2b was.

### The open-before-cite rule — run, and the result is the surprise of the night

§11 said: *on 5 of 17 questions the right document was handed to the agent and it opened none
of them, citing snippets instead. A "quote the line before you cite it" rule was written for
this and has never been run.*

**It has now been run**, in the first live Claude Code battery on a frozen retrieval
configuration: 35 real sessions (`claude-sonnet-5`, fresh process per question, the folder's
own `CLAUDE.md`, no memory carried between sessions, $8.53, 0 timeouts).

| | |
|---|---|
| an evidence path was printed to the session | **8 / 17** |
| it opened *any* evidence file | **2 / 17** |
| it opened the *right page* | **1 / 17** |
| it cited the right page | **0 / 17** |
| it named a file it had never opened | **5** (on 2 questions) |
| it wrote a note before answering | 12 / 17 |

**The rule was followed. That is the finding.** Every one of the 17 sessions issued `open`
commands — 56 of them across 16 of the 20 sessions — and only two questions produced a
citation to an unopened file. The agents did not answer from snippets this time. **They opened
the wrong pages**: on 6 of the 8 questions where the right path was printed on screen, the
session went and opened something else.

So the behavioural fix that has been sitting in the backlog for two nights turns out to be
close to free and close to worthless *on its own*. The bottleneck is one step earlier — in
which of the ranked candidates is worth opening — and no rule about citation discipline
reaches it.

### And the one thing that was solved is now in question

The status table at the top of the repository has said, for four nights, that honest refusal
works: 11/11 and 4/4. Under the live battery's stricter scorer, **`absence_ok2` is 1 of 15**.

But **14 of those 15 sessions did run the shelf, get its absence verdict, and print it**. The
scorer requires two things at once — a decline phrase *and* no numeric figures — and each half
fails separately: 8 of 15 assert no figures but do not match the inherited decline regex, and
6 decline in substance while quoting *the shelf's own edition counts*, which the metric reads
as invented figures.

**Both numbers are published, because only one of them can be right and it is not yet known
which.** The next experiment is not a retrieval idea: repair the scorer against those two
named defects, write the gate first, and re-read the 32 transcripts already on disk. If the
repaired number is ≥10/15 the absence box goes back to *solved* and 1/15 was an artefact. If
it stays low, then the one thing this project believed it had solved has been quietly failing,
which would be the most important correction it has made.

### Where this leaves the project

Every retrieval lever has now been pulled: more rewrites, a cross-encoder reranker, a
different fusion rule, a lexical caption channel, a dense caption channel, a caption page
rule, a year-aware page rule, and two edition-selection rules. **The best of them moves the
document top-ten from 9 to 10 of 17 and does not survive the holdout.** Six pre-registered
gates were read on 2026-09-15 and all six STOPped or FAILED, with no bar moved.

The end-to-end pipeline was also run for the first time, deterministically, with the printed
table cell checked by the geometry-aware verifier rather than compared to the answer key —
see F52 and the 2026-09-15 architecture note for its loss decomposition.

*Full detail: [`08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md`](08_what_next/CURRENT_WORKING_ARCHITECTURE_2026-09-15.md)
and [`08_what_next/HANDOFF_2026-09-15.md`](08_what_next/HANDOFF_2026-09-15.md); findings F46–F52.*
