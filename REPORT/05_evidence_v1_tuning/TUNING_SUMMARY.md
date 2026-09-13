# Overnight tuning loop, 2026-09-13 — summary

Ran after the evidence_v1 build's Stage 5 stopped at RETRIEVAL_GATE_FAILED
(3/17 hit@24). Ali authorized an unsupervised tuning loop over the retrieval
layer only: fix on the 17 frozen dev questions, confirm on a frozen 30-question
holdout never inspected per-question, keep a change only if BOTH improved,
$0 metered throughout (no model sessions spent). Full machine-readable log:
`corpus-lab/state/evidence_v1/tuning_log.jsonl` (15 entries).

## Holdout

30 questions sampled (seed 20260913) from the 103 non-absence members of the
118-question pool outside the 17 frozen dev positives. Frozen in
`_private/evidence_v1/holdout_frozen.json`. Never inspected per-question,
only its two aggregate numbers (hit@24 count, macro recall@120), exactly as
instructed.

## Every change tried

| # | Idea | Iters | Result | Dev hit@24 | Dev recall@120 | Holdout hit@24 | Holdout recall@120 |
|---|---|---|---|---|---|---|---|
| — | starting point (post-stop) | — | — | 3/17 | 0.2353 | 0/30 | 0.20 |
| — | baseline re-verify after revert | — | note | 2/17 | 0.1176 | 0/30 | 0.10 |
| 1 | Fix captionless-table detector (3 variants: stricter header-row shape, looser threshold, literal "Indicator" line) | 3 | **All reverted** | 2, 0, 2 /17 | 0.18, 0.00, 0.18 | 1, 0, 1 /30 | 0.10, 0.00, 0.10 |
| 2 | Multi-query (deterministic rewordings: full/tail/clause-split, then clause0+N pairing, then max-not-sum fusion) | 3 | **All reverted** | 2/17 (flat all 3) | 0.12 (flat) | 0/30 (flat) | 0.067, 0.033, 0.067 |
| 6* | Candidate depth + trajectory stopwords (not on the original list — found by tracing tr_04 directly) | 4 | **Iter 1 kept**, 3 further tweaks reverted | 2/17 | 0.18 | 2/30 | 0.167 |
| 7* | Row-label extraction bug (found while debugging idea 5) | 1 | **Kept** | 2/17 | **0.294** | **3/30** | **0.20** |
| 5 | Trajectory/multi-edition family walk | 1 | Reverted | 2/17 | 0.294 | 3/30 | 0.20 |
| 3 | Alias bridge widening from corpus-observed labels | 1 | Reverted | 2/17 | 0.294 | 3/30 | 0.20 |

*Ideas 6 and 7 are not on Ali's original numbered list; they were forced by
what the tracing actually showed and are logged under their own idea tags in
`tuning_log.jsonl` for full auditability.

**Final state**: dev 2/17 hit@24 (recall@120 0.294, all-required@120 2/17);
holdout 3/30 hit@24 (recall@120 0.20, all-required@120 1/30). Corpus
integrity re-verified byte-identical to the Stage-1 baseline
(`33a8e3f9...b360c969`) before teardown. $0 spent, 0 model sessions used.

## Bugs found (both real, both independent of "tuning")

1. **Alias phrase-matching never fired** (found before this loop, already
   folded into the post-stop state used as the starting point here): the
   alias lookup matched single tokens against multi-word phrase keys, so
   "non-tax revenue" → "non-tax receipts" could never bridge. Fixing it
   alone took the battery from 0/17 to 3/17 hit@24 the night before this
   loop started.
2. **`row_labels` was capturing the numeric data row, not the label text**,
   for a large fraction of captioned tables. This corpus's layout often
   prints the bare data row directly under an "Indicator ..." header, with
   the real descriptive label appearing later, near the source line. The
   row-label picker took the first non-blank, non-header line unconditionally
   — which was frequently a string like `"69.4 78.0 87.0 94.4 112.9 R"`, not
   `"Sindh -- Annual Development Programme"`. This was the single biggest
   improvement of the session (recall@120 0.18→0.29 dev, 0.167→0.20 holdout,
   holdout hit@24 2→3) and was found by accident while building something
   else — a reminder that the fastest way to find what is actually broken is
   to trace one real failing question end to end, not to guess at levers.

## What did NOT work, and why (this is the useful part)

- **Fixing the captionless-table false-positive problem made things worse,
  three different ways.** The loose rule really does produce ~92.5% junk
  cards from ordinary prose — but some of that "junk" is the ONLY place a
  few answers actually live (this corpus embeds some figures in narrative
  sentences, not clean tables), and the compact card-shaped version of that
  sentence out-competed the much noisier full-paragraph chunk in the separate
  prose channel. Tightening precision cost more recall than it bought.
- **Multi-query fusion did not help at all**, and the reason is now well
  understood, not just "it didn't work": summing scores across several
  reworded queries rewards a document for repeating the SAME shared words
  across many variants, not for being specifically relevant to one
  sub-concept. Traced concretely on mb_04 — the correct document ranked #6
  when its one genuinely relevant clause-query was run alone, but fell
  completely out of the top 24 once summed against four other variants that
  also happened to repeat "Khyber Pakhtunkhwa". Switching to max-not-sum
  fusion didn't rescue it either, because that same document's own best
  matching card ranked only 24th out of 100 in its own best variant, via the
  wrong page.
- **The real remaining blocker, confirmed on multiple questions (tr_04,
  tr_07, tr_16, mb_04/05/07, rc_05), is volume of near-identical
  candidates, not vocabulary.** This corpus repeats the same handful of
  fiscal tables (ADP by province, PSDP, domestic debt, etc.) across dozens
  of yearly document editions. Example measured directly: 778 distinct
  cards caption-match "Sindh" + "Annual Development Programme" alone. A
  trajectory or multi-branch question's own words are shared by all ~778 of
  them almost equally, so which specific years are wanted cannot be decided
  by term matching at all — the question itself often doesn't name them
  ("...over the last decade or so"). Both the alias-widening idea and the
  family-walk idea were built specifically to attack this and neither
  gained anything once the vocabulary-side bugs were already fixed,
  because the problem isn't which words to search, it's that hundreds of
  documents equally deserve to match on those words.

## Honest read on whether this discovery layer is worth continuing

**Two real, structural bugs were found and fixed this session, and both
mattered (0/17 → 3/17, then 2/17 @ 0.29 recall@120 from a lower base).**
That is a meaningfully different position than "we tried some things and
nothing worked" — the lexical-catalogue idea is not obviously dead, and I
would not conclude that from tonight alone.

**But 11+ measured iterations against a fixed holdout, after two genuine bug
fixes, sit at 2/17 against a 10/17 bar — not close, and the remaining
distance is not a vocabulary problem anymore.** The dominant remaining
failure mode (hundreds of near-duplicate yearly tables competing on
identical generic terms) is a *ranking/disambiguation* problem, and every
idea on the list that could plausibly attack it (multi-query, alias
widening, family walk) has now been tried and shown not to move it, with a
specific, traced reason for each failure — not just "didn't help."

My honest assessment: **further tuning of pure lexical/BM25 ranking on this
catalogue is not a good use of the next hours.** The three ideas pulled from
`plans_fable/` that were NOT tried tonight — embedding the ~88,700 caption
lines with `bge-small-en-v1.5` (measured elsewhere at 7-35 strings/s, cheap
enough to build), reranking a candidate pool with a small cross-encoder, and
answering absence via an edition list — are a different KIND of lever
(semantic similarity and structural document modeling, not more lexical
term tricks) and were explicitly flagged by both parallel plans as the
more promising direction for exactly the disambiguation problem found here.
Continuing to iterate on THIS lexical layer alone, without one of those,
would very likely produce more of tonight's pattern: plausible-sounding
ideas that measure out to zero.

## State left behind

- `corpus-lab/evidence_v1/retrieve.py`: row-label-adjacent stopword list
  (idea 6, kept) is live; `USE_MULTIQUERY` and `USE_FAMILY_WALK` flags exist,
  both default `False` (their code is real and tested but not helpful yet).
- `corpus-lab/evidence_v1/extract.py`: row_label digit-density fix (idea 7,
  kept) is live; the captionless-detector reverts are the ORIGINAL loose
  rule (idea 1's three tightened variants are documented in the tuning log
  but not in the code).
- `corpus-lab/evidence_v1/aliases.json`: unchanged from before this loop.
- Corpus content: byte-identical to Stage 1, confirmed by re-hash, not
  assumed.
- 0 live stacks, 0 CLAUDE.md/settings.json in any rung, 0 engine processes.
- $0 spent, 0/175 model sessions used.
