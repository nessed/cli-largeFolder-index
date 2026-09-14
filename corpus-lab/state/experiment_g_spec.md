# Experiment G — caption similarity at the document level. Spec, pre-registered 2026-09-15 evening

**Written and committed before the mechanism was run.** Gate bands below are fixed and may not
be moved, re-specified, or read a second time.

## Why this and not another retrieval idea

Three facts, each already measured, and G is the only experiment they jointly license:

1. **F41** — the right document is in the top-100 candidate pool on **16 of 17** and **28 of
   30**. Candidate generation is not the loss; ranking inside the pool is.
2. **F44** — a cross-encoder over *catalogue cards* could not reorder that pool (4/17 alone,
   9/17 fused). A card is a label for a document, not a description of what is inside it.
3. **F55 (B2c)** — embedding a document's *captions* and ranking them by cosine separates the
   right table from its neighbours **inside** a document: 52/57 dev, 67/81 holdout, and it
   fixes 5 of the 6 questions on which no caption matched lexically at all.

G carries (3) up one level. If caption similarity can say *which table in this document*, the
same signal may be able to say *which document has a table like this* — a question the catalogue
card cannot answer, because the card never mentions the tables.

This is deliberately **a reranker over the existing pool**, not a new retrieval channel. E1/E2
already tested captions as a retrieval channel and stopped; the failure there was that caption
*retrieval* surfaces documents by lexical or dense caption hits with no reference to the pool
the rest of the system trusts.

## Mechanism

For each family in the frozen configuration's **top-100 pool**:

```
caption_score(family) = max over queries, over documents in the family, over captions
                        of cosine(label_word_embedding(query), caption_embedding)
```

- Label words are exactly B2c's: content words minus FY tokens minus `_TRAJECTORY_FILLER`.
- Embeddings come from the existing `captions.f16.npy` / `captions_ids.jsonl`; nothing is
  re-embedded and no index is built.
- The six C2 queries per question are used, as the frozen configuration uses them;
  `caption_score` is computed per query and the **maximum** is taken across queries.
- **No thresholds and no weights.**

### The two configurations, and there are only two

- **G1** — rank the pool by RRF (k=60) of two rank lists: the frozen fused rank, and the
  `caption_score` rank. A family with no captions contributes only its fused rank.
- **G2** — G1 applied **only when the question is table-like**, judged by the generic signals
  that already exist in `c_offline_gate.py`: `FY_RE` matches, or `_ROW_SEP_RE` matches, or any
  `_TRAJECTORY_FILLER` word is present. Otherwise the frozen ranking is returned unchanged.

**Rationale for G2, stated before measuring:** F44 and F54 both showed that catalogue-derived
signals help dated publications and bury single files, and that the harm concentrates on
questions about notes, copies and spreadsheets — which those same generic signals identify from
the question text alone. G2 is the hypothesis that the signal is good where it applies and
should be switched off where it does not. It introduces no new rule about the corpus, only a
reuse of three regexes already in the repository.

## Gate G — fixed before measuring

Gold family in the top 10, n = 17, against the frozen configuration's **10/17** and **14/30**.
The better of G1/G2 **on the development set** is chosen first; only then is it confirmed with
the **last remaining holdout-1 look**.

- **PASS** — ≥13/17 **and** holdout ≥17/30
- **WEAK** — 11–12/17 **and** holdout ≥16/30
- **STOP** — ≤10/17, **or** holdout <16/30

If G reaches WEAK or better it becomes the frozen document configuration; otherwise the
overnight configuration stands unchanged.

**Do not**, to get past this gate: tune the fusion constant, weight the two rank lists, change
the pool depth, lower or introduce a caption-score cut, add a seventh rewrite, or try a third
configuration. Holdout-1 is retired for this branch after this look whatever the result.

## Persisted

`state/c_caption_doc_gate.json`: recall@10/20/50/100 for G1 and G2, the aggregate
singleton-versus-fy counts of families ranked above gold, and one diagnostic — of the **9**
questions the live battery classified L0 (the right publication never appeared on screen), how
many now reach the top 10 under the chosen configuration. Count only.

## ED3, same phase

With the gold family supplied, for the 10 year-bearing questions: edition set = primaries whose
**B2c** top-5 contains a page whose body holds the asked FY token. Persist set recall /10 and
mean set size to `state/c_edition_set_v3.json`. Reading as ED2's: ≥8/10 with mean ≤3 supports
"locate the table and the edition follows"; ≥8/10 with larger sets means a vintage rule is the
next sub-problem; <8/10 means captions-plus-year do not select editions.
