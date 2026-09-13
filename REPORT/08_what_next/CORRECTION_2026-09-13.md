# Correction to `RESEARCH_2026-09-13.md`

**Logged 2026-09-13. No retrieval experiment was run for this correction.**

The research recommendation to build Shelf V2 is superseded. It incorrectly described semantic retrieval over the small shelf-card pool as the main untested lever.

Approach C had already built and measured that route:

- 12,760 document cards and 89,380 explicit table captions;
- BGE-small vectors over the document-card text;
- FTS5 and semantic top-200 candidate lists fused with reciprocal-rank fusion;
- document-family grouping, query rewrites, and in-document retrieval.

Its offline gate failed: the correct family was in the top 10 for 6/17 verbatim questions and 8/17 with rewrites, against a 12/17 bar. The corrected trajectory walk reached 1/4, against a 3/4 bar. The 43.9% within-document top-5 page rate is only a weak pass. See [the detailed Stage 3 gate report](../06_approach_c_shelf/STAGE3_OFFLINE_GATE_REPORT.md) and [the Approach C build specification](../06_approach_c_shelf/C_SHELF_FIRST_BUILD.md).

The evidence still supports retaining structural edition checks for scoped absence, opened-page evidence verification, and Astra's inventory/provenance/compiler infrastructure. It does not support rebuilding the same shelf architecture as a new immediate experiment.

Any future work should be a separately specified, offline-gated ablation on the existing shelf rather than implementation of the superseded Shelf V2 contract.
