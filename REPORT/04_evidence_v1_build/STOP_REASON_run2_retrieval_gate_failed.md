# STOP_REASON: RETRIEVAL_GATE_FAILED

Run: 20260912T220732Z-cede10c8
Stage reached: 5 (retrieval proof)

## The measured result

Chosen alternative: A (search_text alternative A).
3/17 positive frozen questions had a correct address in the top 24 leads.
3/17 had every required address in the top 120.
Macro address recall@120 = 0.2353.
Neither the strict gate (>=15/17 top-24, >=14/17 top-120, recall>=0.90) nor Ali's
authorized amendment (>=10/17 top-24) is met. Per the contract: "Failure then ->
RETRIEVAL_GATE_FAILED and Stage 10. This is the decisive inexpensive stop; no
embeddings/reranker/new engine detour." No threshold was widened to pass this.

## What was verified working (Stages 1-4, and the catalogue mechanics themselves)

- Full corpus integrity: CONFIRMED byte-identical. 15010/15010 files, byte-identical to the
  Stage 1 baseline, confirmed by independent re-hash, not merely re-asserted.
- Cold catalogue build: 15010/15010 files accounted, 0 residual, 1109s/1800s budget.
  Two real bugs were found and fixed during this build (see setup.json): an
  idempotent-cleanup step scanning three unindexed FTS5 columns that got slower as
  the catalogue grew, and a rare SQLite write-lock race that could silently drop a
  file from the catalogue under 8-way concurrency. Both confirmed fixed by direct
  disk-vs-database comparison, not by the build's own self-reported counters.
- 61/64 free-test suite (Stage 2.4 scoring, 3.3 inventory, 6.2 cell parsing, 6.3
  compiler, 7.4 hooks) passing, plus 2/2 install/uninstall round trips with
  byte-identical restoration.
- A genuine, independently-confirmed alias bug: the original alias lookup matched
  single tokens against multi-word alias phrases ("non-tax revenue" / "non-tax
  receipts") and could never fire. Fixing it to match phrases against the question
  text directly moved pl_01 (a single-table lookup) from absent-in-top-120 to rank
  #2, and raised the whole-battery hit rate from 0/17 to 3/17. This is real,
  verified signal that aliasing the RIGHT way helps -- it is not enough.

## What was tried and reverted

An AND-the-terms-first, OR-fallback query strategy (matching night 3's own
corpus_search.py fix) was measured and made the aggregate result WORSE (3/17 ->
2/17 hit@24): a narrow AND match is often confidently wrong rather than absent,
which starves the OR fallback of the chance to surface the actually-correct,
lower-ranked card. Reverted; the code for it remains, unused by default, rather
than deleted, so a future session does not re-discover this the hard way.

## Root cause, as far as this run's evidence goes

1. Single-table point lookups with a literal label mismatch (pl_01: question says
   "non-tax revenue", the table says "Non-tax receipts") CAN be solved by this
   catalogue once the alias bridges the exact phrase (rank #2 of 120). pl_14
   (sales tax -> GST collection) also succeeds.
2. 7/17 of the 17 positive questions (multi_branch and trajectory types)
   inherently need MULTIPLE source documents for one answer. The contract's own
   design assumes these are resolved through several explicit `search` calls
   after the initial `prepare` (up to 4 per request) -- but Stage 5.1's own
   protocol measures exactly one bag-of-words query per question, with no
   subsequent searches. That protocol may be structurally unable to pass for
   these types regardless of catalogue quality; this run cannot distinguish "the
   catalogue is bad at this" from "this gate does not test what these types
   need." Recorded as a real limit of the measurement, not resolved by widening
   the gate.
3. At least one remaining single-lookup failure (pl_21) was traced to a genuine
   catalogue-construction gap: the detected table card's captured body text
   lacked the row's numeric cells entirely, because this particular page's data
   row sits away from its own caption in a way the line-window capture in
   extract.py does not reach. Not fixed in this run -- it would need geometry-
   aware capture (the same class of fix Stage 6's verifier already uses for cell
   reading, not yet applied to catalogue construction).

## What is safe

- $0 metered spend, 0/175 sessions used -- the retrieval gate is entirely free and
  the stop happened before any model session was spent.
- 0 corpus content changes (independently re-verified, not just asserted).
- 0 live stacks, 0 engine processes, no stray CLAUDE.md/settings.json left in
  corpus_15000.

## Resume

The runtime code (store/inventory/extract/catalogue/retrieve/verify/compile/hooks/
install/cli) and its test suites are real, working, and reusable. A future attempt
at this gate needs either (a) a genuinely different retrieval mechanism for
multi-concept questions -- most plausibly letting Stage 5 itself issue the same
multi-search sequence `search` supports, rather than one query, which the
contract's protocol as specified does not permit without Ali revising Stage 5's
measurement itself -- or (b) the semantic/embedding approach SOLUTION.md
deliberately deferred, now with a much smaller effective denominator (cards, not
raw pages) than the 20.8h full-page embedding estimate that shelved it originally.
Neither is authorized by this run's instructions.

    .venv\Scripts\python.exe _private\evidence_v1\audit.py stage1

mints a fresh run and starts over; it does not reuse this run's (unused) budget.

## Addendum, same run, found after the stop while writing this report

Checked why the catalogue (1,201,574 cards) is barely smaller than the old
full-page index (1,206,260 pages) -- the entire premise of this design was a
SMALLER, more precise search space than whole-page text.

    table (captioned, high-confidence detector):   89,936 cards
    uncaptioned (aligned-block detector):        1,111,638 cards

92.5% of every card in the catalogue came from the CAPTIONLESS detector --
BUILD_PROMPT.md's own specified rule, implemented faithfully: "aligned blocks
with >=2 year headers and >=2 numerical cells within 12 lines." On this
corpus's prose style, an ordinary narrative sentence like "Education Affairs
... shifted from 3.3 Rs billion in 2012-13 to 3.5 Rs billion in 2013-14"
satisfies that rule by itself -- two years, two numbers, one sentence. The
detector is firing on nearly every page, not on the rare genuine captionless
table it was meant for, so the catalogue never achieved the smaller
denominator the whole design leaned on.

This is a concrete, mechanical, well-understood defect -- not a new
architecture, not a threshold widened to pass a gate. It was found AFTER the
one permitted correction pass had already been spent (the AND/OR experiment),
so it is recorded here rather than acted on in this run. A plausible cheap fix
for next time: require the aligned-block window to look like an actual table
(e.g. a preceding "Indicator"-style header line, or >=2 DISTINCT lines each
carrying multiple numbers, not one sentence's worth) rather than any 12 lines
containing the bare minimum of two years and two numbers anywhere. Untested;
not applied; the next attempt should measure it before trusting it.
