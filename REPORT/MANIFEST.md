# MANIFEST — where every file in this folder came from

Every file here is a byte-for-byte copy. The `original` column is relative to the
project root (`C:\Users\Ali\Desktop\retrieval-lab\`). The short hash is the first
16 hex characters of the copy's SHA-256, so a reviewer can confirm a copy still
matches its original.

Nothing from `_private/` is copied here — that tree holds the answer keys, and this
folder is meant to be safe for anyone (or any future test run) to read.

## `00_orientation/` — What the project is and how it is laid out

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `PROJECT_INDEX.md` | `INDEX.md` | 11,417 | `06aaf6a305ce0435` |
| `SOLVE_BRIEF.md` | `00_brief/SOLVE_BRIEF.md` | 16,790 | `372e8f15349c80fa` |
| `GRID_RUN_SPEC.md` | `00_brief/GRID_RUN_SPEC.md` | 28,036 | `8cba645e3066122a` |
| `TOOL_MATRIX.md` | `corpus-lab/01_reports/TOOL_MATRIX.md` | 9,032 | `1f8cdc05cfd87c52` |

## `01_night1_stock_tools/` — Night 1 - can stock Claude Code already do this?

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `NIGHT1_FULL_WRITEUP.md` | `corpus-lab/NIGHT1_FULL_WRITEUP.md` | 24,115 | `b60c6264541ea7be` |
| `DECISION_MEMO.md` | `corpus-lab/05_findings/DECISION_MEMO.md` | 11,839 | `3a385a886ff0ee64` |
| `OPEN_QUESTIONS.md` | `corpus-lab/05_findings/OPEN_QUESTIONS.md` | 4,264 | `3b6d8a39b91a97ac` |

## `02_night2_bakeoff/` — Night 2 - six approaches specified, three measured

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `NIGHT2_FULL_REPORT.md` | `corpus-lab/05_findings/NIGHT2_FULL_REPORT.md` | 20,338 | `287880dc377d7884` |
| `GRID.md` | `corpus-lab/05_findings/GRID.md` | 16,780 | `c5a62431710182e3` |

## `03_night3_rescore_and_rank/` — Night 3 - offline re-scoring and the ranking experiments

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `rescore_from_results.json` | `corpus-lab/state/rescore_from_results.json` | 34,818 | `22441f1013a138ca` |
| `rank_experiments.json` | `corpus-lab/state/rank_experiments.json` | 7,440 | `bd5701075622a2ad` |
| `probe_score_floor.json` | `corpus-lab/state/probe_score_floor.json` | 14,957 | `df206bce07f5f837` |
| `verify_search_fix.json` | `corpus-lab/state/verify_search_fix.json` | 4,392 | `d5e48755c9502d9f` |
| `diagnose_recall.json` | `corpus-lab/state/diagnose_recall.json` | 2,921 | `4eff968adc1a16fa` |
| `bench_embed__raship.json` | `corpus-lab/state/bench_embed__raship.json` | 322 | `6d8293768b03ebf1` |

## `04_evidence_v1_build/` — Night 4a - the evidence_v1 table-catalogue engine and its stop

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `SOLUTION.md` | `SOLUTION.md` | 26,228 | `e7e1ec6dcdd34429` |
| `BUILD_PROMPT.md` | `BUILD_PROMPT.md` | 38,809 | `d49c11d99881baa2` |
| `ACCEPTANCE.md` | `ACCEPTANCE.md` | 14,136 | `c61bb8276652b97f` |
| `STOP_REASON_run1_corpus_baseline_changed.md` | `corpus-lab/state/evidence_v1/20260912T214913Z-7864bc46/STOP_REASON.md` | 2,508 | `2be3b8bff91eab5a` |
| `STOP_REASON_run2_retrieval_gate_failed.md` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/STOP_REASON.md` | 7,201 | `b50a505e02353d87` |
| `run2_retrieval.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/retrieval.json` | 9,431 | `c6dd460105c1a179` |
| `run2_setup.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/setup.json` | 1,186 | `e23e92c53a3319e1` |
| `run2_status.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/status.json` | 2,134 | `bd915c13f2d3ddb3` |
| `run2_stage2_gate.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/stage2_gate.json` | 646 | `32ec7ddf9aa7c12f` |
| `run2_free-tests.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/free-tests.json` | 761 | `c90074c0a278ea9a` |
| `run2_integrity-after.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/integrity-after.json` | 313 | `41ab3f999e3aab67` |

## `05_evidence_v1_tuning/` — Night 4b - the disciplined tuning loop against a frozen holdout

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `TUNING_SUMMARY.md` | `corpus-lab/state/evidence_v1/TUNING_SUMMARY_2026-09-13.md` | 8,735 | `749888b132294395` |
| `tuning_log.jsonl` | `corpus-lab/state/evidence_v1/tuning_log.jsonl` | 17,101 | `ed41996518230cf4` |

## `06_approach_c_shelf/` — Night 4c - approach C, document-first 'shelf', built and gated

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `C_SHELF_FIRST_PLAN.md` | `plans_fable/C_SHELF_FIRST_PLAN.md` | 9,369 | `a9d338016d0e64d3` |
| `C_SHELF_FIRST_BUILD.md` | `plans_fable/C_SHELF_FIRST_BUILD.md` | 29,833 | `01273da06c41c63c` |
| `c_preflight.json` | `corpus-lab/state/c_preflight.json` | 1,123 | `c91c200402b30f67` |
| `c_shelf_build.json` | `corpus-lab/state/c_shelf_build.json` | 1,143 | `47861b2f0795444c` |
| `c_shelf_selftest.json` | `corpus-lab/state/c_shelf_selftest.json` | 991 | `e8ad8b451ce7ff87` |
| `c_offline_gate.json` | `corpus-lab/state/c_offline_gate.json` | 784 | `6c43c8dc788c2cab` |
| `c_queries.json` | `corpus-lab/state/c_queries.json` | 8,268 | `0b72574499c20e81` |

## `07_approach_b_planned/` — Approach B - hybrid multi-query, planned but never built

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `B_HYBRID_MULTIQUERY_PLAN.md` | `plans_fable/B_HYBRID_MULTIQUERY_PLAN.md` | 13,036 | `ab23c155d96a5c12` |
| `B_HYBRID_MULTIQUERY_BUILD.md` | `plans_fable/B_HYBRID_MULTIQUERY_BUILD.md` | 33,830 | `e3a1b81283936b0d` |
| `plans_fable_README.md` | `plans_fable/README.md` | 4,272 | `a85874fbe738f1fc` |

## `08_what_next/` — The research pass and the recommended next build

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `RESEARCH_2026-09-13.md` | `RESEARCH_2026-09-13.md` | 11,845 | `ca9b6b886993ea79` |
| `EXECUTE_SHELF_V2.md` | `EXECUTE_SHELF_V2.md` | 9,900 | `09b332cad6ede006` |

## `09_ledgers/` — Raw ledgers - every finding, every step, and how to resume

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `FINDINGS_LIVE.md` | `corpus-lab/05_findings/FINDINGS_LIVE.md` | 34,970 | `f169b414499e2e51` |
| `progress.jsonl` | `corpus-lab/state/progress.jsonl` | 92,872 | `8914cac5775b5a33` |
| `RESUME.md` | `corpus-lab/RESUME.md` | 11,283 | `b9fe6c5fbce760f8` |

---

43 files, 600,169 bytes total. Assembled 2026-09-13.
