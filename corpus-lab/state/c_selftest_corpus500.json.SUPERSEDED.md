# SUPERSEDED — for production-portability claims only

`c_selftest_corpus500.json` is the Phase 6 cold test on `corpus_500` (2026-09-15).

**By what:** Gate R1, Phase 10.3 (2026-09-16) —
`corpus-lab/experiments/p10_portable_r1/README.md`,
`corpus-lab/state/phase10_gate_r1_result.json`.

**Why:** that cold test ran the installer as it then stood, which built the shelf with
the **experimental v2 builder** (the one that failed Gate S) and wrote its artefacts into
the development repo, using scripts loaded from the development repo. It therefore
validated the experimental stack, from inside the lab — not the production stack, and not
portability. Plan E §1.4.

Gate R1 re-ran the same corpus twice from a packaged copy under `%TEMP%`, with its own
venv, every lab environment variable asserted unset, and the **v1** builder: 500 files,
118 seconds per install, 18/18 self-test in both rooms, bit-identical vectors, and all 31
retrieval probes identical.

**Where the replacement lives:** `corpus-lab/state/phase10_gate_r1_result.json` and the
`build_manifest.json` / `BUILD_REPORT.md` / `canonical_export.json` each clean-room
install wrote.

**What is NOT superseded:** the Phase 6 cold test remains a true record that the
installer ran end to end on 500 files on 2026-09-15. It is superseded only as evidence
for *production portability*. The file itself is untouched (Plan E rule 15).
