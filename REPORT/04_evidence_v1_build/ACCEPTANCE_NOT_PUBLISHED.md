# ACCEPTANCE.md is intentionally not in this repository

`ACCEPTANCE.md` — the acceptance criteria for the `evidence_v1` build — exists in the
local copy of this folder and is listed in [`../MANIFEST.md`](../MANIFEST.md), but it is
excluded from git by `.gitignore`.

**Why.** It is an oracle in prose. For each of the 30 acceptance cells it states the
required source anchor as a full gold file path, together with the literal cell value, the
table number and the PDF page index. Publishing it would hand any reader the answers to a
large part of the benchmark.

**What you lose by not having it.** Only the expected answers. The *criteria* it encodes —
what counts as a valid address, what makes a numeric claim verifiable, which outcome codes
the compiler may emit — are all described in
[`BUILD_PROMPT.md`](BUILD_PROMPT.md) and [`SOLUTION.md`](SOLUTION.md), both of which are
published here in full and contain no gold answers.

See the caveat in the [repository README](../../README.md) for the answer-derived material
that *was* published in earlier commits and remains in place.
