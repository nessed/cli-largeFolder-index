# Correction — 2026-09-16

Three numbers published on the morning of 2026-09-16 were wrong. All three were faults in
the **scoring program**, not in the system it was measuring, and all three were found by
re-reading the same recorded sessions with a corrected scorer. **No session was re-run to
produce this correction, and no model call was made.**

Two of the three make the system look better than the report said. One makes it look
slightly worse. All are recorded here with the evidence.

**Nothing in this note changes a gate verdict.** Every Phase 9 battery was scored by the
pre-registered v2 scorer and every one of them read STOP. They still do. What follows
corrects *analytical* numbers — the descriptions of what happened — not the adjudications.

The corrected scorer is `corpus-lab/bin/c_score_live_v3.py`, frozen at tag
`scorer-v3-frozen-2026-09-16`, sha256 `09f4105d81114dee…`. Its full side-by-side against v2
is `corpus-lab/state/c_rescore_v2_vs_v3.json`; the reasoning is
`corpus-lab/experiments/p10_scorer_v3/README.md`.

---

## 1. "Gives the right number on only 5 of 17" — withdrawn

**What was published:** that both models read the number correctly on only 5 of 17
questions, and by extension that the system "finds the page far better than it reads the
number", with a specific claim of "0 of 4 totals right on decade-long questions".

**What is true:** **12 of the 17 dev answerable questions carry no numeric value in the
answer key at all.** They are trajectory, multi-branch, reconciliation, relationship and
stale-document questions — they ask for a series across a decade or across several
documents, not for one figure. `accepted_values()` returns an empty list for every one of
them, so `value_correct` could never be true for them whatever any model wrote.

Both models were scored **5 right out of the 5 questions that have a keyed number**:

| | Sonnet | Opus |
|---|---|---|
| published | 5 of 17 | 5 of 17 |
| **corrected** | **5 of 5** (`n_keyed = 5`) | **5 of 5** (`n_keyed = 5`) |

The split was a property of the key. It was identical for both models because it had to be.

**The sentence "reads the number wrong on 12 of 17" is unsupported and is withdrawn.** So
is "4 of 4 wrong totals on decade questions": those four questions have no keyed total to
be wrong about.

**What we can now say instead**, from a measurement that did not exist before (Phase 2, key
v2, derived by script from the generator's own placement records — no value written by
hand):

> On the 7 trajectory and multi-branch questions, the answer carried every expected year's
> value on **4 of 7** (Sonnet) and **4 of 7** (Opus), scored by v3 against key v2
> (sha `773ab75e5018ec58…`). This is the project's first measurement of table reading;
> there is no earlier number to compare it with.

The split inside that number is the interesting part: **trajectory questions — read one
table, carry six or eight years across — came back complete. Multi-branch questions — one
cell each from three different publications — came back at a third or at nothing, for both
models.** The weakness is not arithmetic; it is assembling one answer from several places.
Note also that the vector metric is permissive: a multi-branch cell accepts up to 16
distinct values, which makes those failures stronger evidence, not weaker.

---

## 2. "Opus quoted a file it had not opened 7 times" — corrected to 4

**What was published:** Sonnet 1, Opus 7, and the reading that "Opus is the looser about
where its numbers came from".

**What is true:** the scorer was counting three different things as open-before-cite
violations, and missing one real one. Case by case, from the transcripts:

| session | published | corrected | why |
|---|---|---|---|
| Opus `sd_05` | 2 | **0** | two CSV filenames named in prose — "this file is older than that one" — with no page and no figure. A mention is not a citation. |
| Sonnet `mb_07` | 1 | **0** | the pages *were* opened, inside a bash `for` loop; the command carries the loop variable, so the scorer saw no open. The tool output says `OPENED` for each. |
| Opus `mb_04` | 2 | **0** | the guard challenged the answer, the model then opened the pages **in a loop**, and in the full 8,233-character answer all four citations are to pages it opened. The published reading — "the session ended without opening it" — was made from the post-guard fragment. |
| Opus `pl_01` | 3 | **3** | **genuine.** The answer cites four pages across three survey editions; checking all 14 paths the session opened by any route, none of them is that publication. |
| Opus `mb_07` | 0 | **1** | **genuine, newly visible.** Cites two pages of a document it never opened. |
| Sonnet `rc_07` | 0 | **1** | **genuine, newly visible.** Cites one survey edition at a page it never opened, having opened four neighbouring editions. |

| | published | **corrected** |
|---|---|---|
| Sonnet | 1 | **1** |
| Opus | 7 | **4** |
| fabricated figures | 0 | **0** |

Two of the corrections were predicted by an independent audit; two were not, and one went
the other way. **Fixing the fragment bug revealed violations as well as clearing them** —
`rc_07` and Opus `mb_07` were invisible while the scorer read only the post-guard reply.

**The interpretation must also be withdrawn.** Phase 4 measured how much these numbers move
when nothing changes, and `cited_unopened` moved across repeats of the *same* Sonnet
configuration. Until that range is read, **the gap between 1 and 4 cannot be attributed to
the models.**

---

## 3. Nine Sonnet and five Opus sessions were scored on a fragment

**Not previously reported at all**, because nobody knew.

The harness keeps the **last** assistant message. When the citation guard challenged an
answer, the model replied "Confirmed — the citation stands", and *that* four-line reply
became `answer_text`. The real answer — in one case 2,344 characters, in another 8,233 —
was already in the transcript, immediately before the guard's interruption, and was
discarded.

**9 of 20 Sonnet sessions and 5 of 20 Opus sessions** in the Phase 9 batteries were scored
this way. The same defect appears in P8 (5 sessions). It is the reason two of the
corrections above were invisible in both directions.

`c_score_live_v3.reconstruct_full_answer()` recovers the complete answer, and
`c_live_battery.py --capture full` now records it live. In the Phase 4 batteries the
recovery fired **on session after session** — 716 → 6,447 characters in one case.

---

## 4. The portable package was not the thing that was measured

`setup_folder.py install` built the shelf with `c_shelf_build_v2.py` — the **experimental**
builder that failed Gate S on 2026-09-15 — while production and the demo ran v1. It also
ran its scripts from the development repo and wrote its artefacts there, and had never once
been run from a copy.

So **the Phase 6 cold test on `corpus_500` validated the experimental stack from inside the
lab**, not production portability. It is superseded for any production-portability claim;
see `corpus-lab/state/c_selftest_corpus500.json.SUPERSEDED.md` and
`corpus-lab/state/c_shelf_build_v2.json.SUPERSEDED.md`.

From Phase 10.3 the installer defaults to `--builder v1`. `--builder v2` prints
`EXPERIMENTAL SHELF V2 -- failed Gate S 2026-09-15; not production` and stamps
`builder: v2 (experimental)` into the build manifest, so it cannot be selected silently.

---

## Every superseded sentence, with its replacement

### `REPORT/08_what_next/ORCHESTRATOR_BRIEF_2026-09-16.md`

- **§3, line 140** — "**5 of 17 on the number**. On decade-long trajectory questions Sonnet
  opened the right page …"
  → **"5 of 5 on the questions the key carries a number for (`n_keyed = 5`). The other 12
  ask for a series, not a figure, and the key cannot score them by value."**
- **§7, line 222** — "**The reading gap: 5/17 on the number against 13–14/17 on the page.**
  Largest open defect in …"
  → **"There is no measured reading gap. The two numbers had different denominators: 5/5 on
  keyed questions against 13–14/17 on page citation. The first real measurement of table
  reading is 4 of 7 whole-table questions carried complete, for both models."**

### `REPORT/08_what_next/DEMO_2026-09-16.md`

- **line 134** — "it gives the **right number on only 5 of 17**, either model"
  → **"it gives the right number on 5 of the 5 questions that have one."**
- **line 137** — "**Opus quoted a file it had not opened 7 times in 20 questions**; Sonnet
  did it once."
  → **"Opus cited a page it had not opened 4 times; Sonnet once. Whether that gap is real
  or noise is not yet established — see the variance table."**

### `REPORT/08_what_next/HANDOFF_2026-09-16_night.md`

- **line 71** — "**Finding the page is not reading it.** Both models: 13–14 of 17 on
  citation, **5 of 17 on the …**"
  → **"Both models: 13–14 of 17 on citation, and 5 of 5 on the keyed-value questions. The
  gap that remains is between single-table and multi-document questions, not between
  finding and reading."**

### `README.md`

- **line 97, the LIVE-5 row** — "But **value_correct is 5/17 for both** — it finds the page
  far better than it reads the number, and on decade-long questions it opened 4 of 4 right
  pages and got 0 of 4 totals right. … citing a file never opened (Sonnet 1, Opus 7)."
  → **"value_correct is 5/5 for both on the keyed questions (`n_keyed = 5`); the 12 unkeyed
  ones were never scorable by value. Corrected open-before-cite counts: Sonnet 1, Opus 4,
  zero fabricated figures. The gate verdicts stand: STOP for both, under the pre-registered
  v2 scorer."**
- **line 107** — the summary sentence quoting "**5 of 17**"
  → **"5 of 5 on keyed value; the 5-of-17 figure divided by the wrong denominator."**

### `INSTALL_FOR_SIR.md` (old text)

The whole "How well does it actually work?" table has been **rewritten in place** rather
than pointed at, because that document is handed to somebody who will not read this note.
Its old rows read "gave the right number 5 of 17" and "quoted a file it had not actually
opened — Sonnet 1, Opus 7". Both are corrected there, with the old figure shown beside the
new one, and the sentence "on questions that track a number across a decade it found the
right pages nearly every time and still got the total wrong" is deleted as unsupported.

---

## What did **not** change

- **Every Phase 9 gate verdict.** All six batteries were STOP under the pre-registered v2
  scorer, on conditions v3 does not revisit. They stand as recorded.
- **The headline equivalence numbers, 13/17 and 14/17.** Two scorers with materially
  different citation rules read the same recordings and agreed exactly.
- Rank preservation, latency, the shelf v2 gate numbers, the equivalence registry
  validation at 0.970, the checkpoint log, the clean corpus, and the three rehearsal
  answers. All reproduced from disk; none touched.
- The offline baselines: 10/17 and 16/17 on the caption gate, 52/57 on B2c, 11/11 and 4/4
  on routing. All re-run tonight and identical.

## What is still not known

**Genuine real-world cross-folder generalisation remains untested.** Everything in this
note, and every gate behind it, runs on corpora from one generator. The package has now
been installed against two different folders, but both come from that same generator. A
folder built by different rules has never been tried. That is the next experiment, to be
designed and pre-registered on its own, and it has not been run.
