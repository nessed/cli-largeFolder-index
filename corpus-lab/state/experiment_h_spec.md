# Experiment H — the answering model selects the publication from the pool. Spec, pre-registered 2026-09-16

**Committed before any call was made.** The prompt below is fixed verbatim; the gate bands are
fixed and may not be moved or re-read.

## Hypothesis

The candidate pool contains the right document on **16 of 17** questions (F41) and on 28 of 30
of holdout-1. Five statistical rankers have now failed to pull it into the top ten:

| mechanism | result |
|---|---|
| six query rewrites, RRF fusion | 9/17 |
| a compact cross-encoder over catalogue cards (F44) | 9/17 |
| per-query best-rank selection instead of summation (F46) | 5/17 |
| captions as a retrieval channel, lexical then dense (F47, F49) | 10/17, 9/17 |
| caption similarity as a reranker over the pool (F57) | 9/17 |

Every one of them scores a *document* against a *query* by some measure of surface similarity.
The judgement the task actually needs is different in kind: **which sort of publication would
print this sort of table.** That requires knowing what a statistical yearbook is, what a budget
document contains, that a tax may be listed under its statutory name — knowledge a general
language model has and none of the five rankers had access to.

H tests exactly that and nothing else: same pool, same order, no new index, no new embedding.
The only new thing is that a language model reads the list.

## Mechanism — one configuration

For each question: the frozen configuration's **top-100 families in fused order**. One compact
card per family, built from **shelf fields only**:

- the index (1–100),
- the family words (`_family_words`, which strips the `{fy}` placeholder),
- edition count and first/last fiscal year — or, for a family with no dated primaries, the words
  `single file` and the file's extension,
- the two `why` lines `do_find` already computes (catalogue lines overlapping the query).

**No paths. No page numbers. Nothing derived from the answer key.**

One headless call per question: `claude.exe -p` with `--model claude-sonnet-5` (the live model),
`--max-turns 1`, `--output-format text`, every tool disallowed, cwd the scratch directory.

### The prompt, fixed verbatim

> *(the question)*
>
> Below are 100 publications held in a research folder, each with the years held and two lines
> from its table of contents. Which of them most likely print the table or figure that answers
> the question? Reply with JSON: {"picks": [up to 10 indices, most likely first],
> "publication_guess": "the name a Pakistani government publication would have for the document
> you would look in"}. Judge by what kind of publication would carry this series, not by word
> overlap.
>
> *(the 100 cards)*

Parse the JSON; on parse failure retry **once**, then record `no_answer`, which counts as a
miss. Raw responses cached under `_private/results/h_cache/`; only ranks and counts are
persisted to `state/c_llm_select_gate.json`.

## Gate H — fixed before measuring

Gold family within the returned `picks`, top 10, n = 17, against the frozen configuration's
**10/17**. Holdout-2 has never been measured by anything, so its bar is **absolute**, not
relative.

- **PASS** — ≥13/17 **and** holdout-2 ≥17/30
- **WEAK** — 11–12/17 **and** holdout-2 ≥16/30
- **STOP** — ≤10/17

**Also reported: top-3**, because the live agent opens about three publications. If top-3 reaches
≥9/17 while top-10 stops, that is recorded as a finding — but it **does not change the band**.

**Secondary diagnostic, free from the same call:** `do_have(publication_guess)` — is the gold
family in `have`'s top 3? This is the generative route (name the publication, then look it up)
as opposed to the selective route (pick from a list). Reported, not gated.

## Contamination

The prompt carries **question text and shelf card text only**. The answer key is read solely to
score the parsed indices, after the call has returned. Neither this spec nor the card builder
contains a literal title, family name, label or year. Holdout-2 is looked at once (look 1 of 2),
aggregate counts only.

## Budget

17 dev + 30 holdout-2 = **47 calls**, against a cap of 50. That leaves **3** for parse-failure
retries. If retries would take the total past 50, the run stops and records `n-of-m`.
