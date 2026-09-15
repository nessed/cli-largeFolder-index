# Addendum H — production hardening night, 2026-09-16

Appends to `CURRENT_WORKING_ARCHITECTURE_2026-09-15.md`. Sections G1–G5 there are unchanged
except where this says otherwise. Written after Phases 0–5 of
`plans_fable/D_PRODUCTION_HARDENING/EXECUTE_2026-09-15_NIGHT.md`.

---

## H1. What is in production now

The stack is unchanged in shape: one card per document in a shelf, a lexical and a dense channel
fused over the cards, then page search inside the chosen documents, then open-before-cite. What
changed is underneath and around it.

| layer | state | changed tonight |
|---|---|---|
| page index (`s2_fts5/harness_15000.db`) | 1,206,260 pages, 13,634 indexed files | no |
| shelf (`s7_shelf`) | 12,760 docs, 1,618 families | **no — v2 was built and rejected, see H3** |
| caption channel | 89,380 captions, lexical + dense | no ranking change; now read from the stored vectors |
| `find` display | **40 one-line cards, `--show` to expand** | **yes** |
| CLAUDE.md | **v2: compact-40 instruction, vintage rule, Sources-block rule** | **yes** |
| citation guard | **v2 behind `--v2`: prose pages, Sources lines, uncited figures** | **yes** |
| live harness | **60 turns / 900 s available; defaults still 25 / 300** | **yes** |
| scorer | **v2 alongside the frozen strict one** | **yes** |

## H2. The two things that were never the system

Both were found by instrumenting, not by changing retrieval, and both had been quietly inflating
every live loss this project has recorded.

1. **The harness was ending sessions before they answered.** 1–5 sessions of every 20, per
   battery, produced no answer text at all because a 25-turn cap or a 300-second clock fired.
   Every one was scored as a retrieval or answering failure. They are disproportionately the
   multi-document questions — the ones the shelf exists for. (F65)
2. **The scorer was stricter than the answer key it scores against.** The key carries acceptable
   alternates on 45 of 135 questions and a series/vintage/fiscal-year address on every evidence
   address; the scorer read none of it and required one exact address. On the same recorded
   transcripts, reading equivalence instead moves P5–P8 from 0/2/1/1 to 6/4/9/4 of 17. (F68)

**This sharpens G5's standing item rather than answering it.** The evening addendum asked
whether the live harness was losing what offline retrieval gained. Part of the answer is now
measured and it is banal: some of the loss was the stopwatch and the marking scheme. How much of
the remainder is real is what Phase 5 is for.

## H3. Shelf v2 — built, gated, rejected

Three structural defects were measured and three changes written: bare years normalised, fragment
families merged, consensus copy as primary. The merge worked — duplicate slots inside the top 40
of a dev `find` went from 35 across 17 lists to **0**. Every recall row held exactly.

It failed one pre-registered structural row and was rejected: gold evidence files hidden as
non-primary rose **20 → 31**. The cause is an interaction between two of the three changes. The
bare-year change gave an edition to 4,333 documents that had none, and the builder treats a
cluster with no edition as *"every survivor is a primary"*; giving those clusters a year flipped
them to *"one primary, the rest hidden"*. Primaries fell from 7,694 to 4,198.

**Production stays on v1.** The v2 artefacts are kept on disk, unused. (F66)

The architectural lesson is narrower than "v2 was wrong": **the shelf's notion of an edition and
its notion of a visible copy are coupled through a single `None` branch**, and nothing in the
design documents says so. Any future change to how editions are assigned changes how many files
`find` will offer, silently.

## H4. Boxes

- **Keep:** the latency fixes (rank-preserving, proved); `--compact/--show`; CLAUDE.md v2; guard
  v2; scorer v2; the battery limit flags; `setup_folder.py`.
- **Rejected by its own gate:** shelf v2, on one row, not tuned.
- **Uncertified and still the most promising retrieval result:** Experiment H's mechanism — now
  shipped as `--compact 40`, whose offline ceiling is 14/17 against the old display's 11/17, and
  whose live value is what Phase 5 measures for the first time.
- **Untested:** everything here on a real corpus; everything here on holdout-2 (zero looks spent).

## H5. The next experiment

Unchanged in spirit from G5, but the candidate has changed because two of its premises moved.

**First choice — (b) alone.** Rebuild the shelf with *only* the fragment-family merge: no
bare-year change, no consensus-primary change. It is the one change tonight with a measured
benefit (35 → 0 duplicate slots) and no interaction with the edition/visibility branch. The gate
should be written before the build and should keep tonight's structural rows, because they are
what caught the problem: gold files hidden as non-primary **must not rise above 20**, and every
recall row must hold. Cost: one build, no model calls.

**Why not the obvious repair.** Keeping "every survivor is primary" for clusters whose edition
came from a bare year would very likely turn Gate S green. It is a change devised *after* seeing
the gate fail, which is the thing this project's rules exist to prevent. If it is worth doing it
is worth pre-registering as its own experiment, with the counter it is expected to move named in
advance.

**Standing item, still open and now the most valuable question here.** Offline document recall
has moved by five questions across the project while the live outcome has not moved at all. Two
of the candidate explanations were removed tonight — the harness caps and the scorer's strictness.
Phase 5 is the first live battery run without either. Whatever it reads, it is the first honest
measurement of the gap.
