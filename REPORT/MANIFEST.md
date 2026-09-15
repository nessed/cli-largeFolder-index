# MANIFEST — where every file in this folder came from

Most files here are byte-for-byte copies. The `original` column is relative to the
project root (`C:\Users\Ali\Desktop\retrieval-lab\`). The short hash is the first
16 hex characters of the copy's SHA-256, so a reviewer can confirm a copy still
matches its original.

Two kinds of entry are not plain copies, and are marked in the table:

- **(notice added)** — the copy carries a superseded-recommendation notice that the
  original also carries, but with links rewritten to resolve from this folder.
- **(written here)** — authored directly in `REPORT/`; there is no external original.

Nothing from `_private/` is copied here — that tree holds the answer keys, and this
folder is meant to be safe for anyone (or any future test run) to read. One further
file is absent on GitHub: `ACCEPTANCE.md` is an oracle and is excluded by `.gitignore`
— see `04_evidence_v1_build/ACCEPTANCE_NOT_PUBLISHED.md`.

## `00_orientation/` — What the project is and how it is laid out

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `GRID_RUN_SPEC.md` | `00_brief/GRID_RUN_SPEC.md` | 28,036 | `8cba645e3066122a` |
| `PROJECT_INDEX.md` | `INDEX.md` | 11,417 | `06aaf6a305ce0435` |
| `SOLVE_BRIEF.md` | `00_brief/SOLVE_BRIEF.md` | 16,790 | `372e8f15349c80fa` |
| `TOOL_MATRIX.md` | `corpus-lab/01_reports/TOOL_MATRIX.md` | 9,032 | `1f8cdc05cfd87c52` |

## `01_night1_stock_tools/` — Night 1 - can stock Claude Code already do this?

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `DECISION_MEMO.md` | `corpus-lab/05_findings/DECISION_MEMO.md` | 11,839 | `3a385a886ff0ee64` |
| `NIGHT1_FULL_WRITEUP.md` | `corpus-lab/NIGHT1_FULL_WRITEUP.md` | 24,115 | `b60c6264541ea7be` |
| `OPEN_QUESTIONS.md` | `corpus-lab/05_findings/OPEN_QUESTIONS.md` | 4,264 | `3b6d8a39b91a97ac` |

## `02_night2_bakeoff/` — Night 2 - six approaches specified, three measured

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `GRID.md` | `corpus-lab/05_findings/GRID.md` | 16,780 | `c5a62431710182e3` |
| `NIGHT2_FULL_REPORT.md` | `corpus-lab/05_findings/NIGHT2_FULL_REPORT.md` | 20,338 | `287880dc377d7884` |

## `03_night3_rescore_and_rank/` — Night 3 - offline re-scoring and the ranking experiments

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `bench_embed__raship.json` | `corpus-lab/state/bench_embed__raship.json` | 322 | `6d8293768b03ebf1` |
| `diagnose_recall.json` | `corpus-lab/state/diagnose_recall.json` | 2,921 | `4eff968adc1a16fa` |
| `probe_score_floor.json` | `corpus-lab/state/probe_score_floor.json` | 14,957 | `df206bce07f5f837` |
| `rank_experiments.json` | `corpus-lab/state/rank_experiments.json` | 7,440 | `bd5701075622a2ad` |
| `rescore_from_results.json` | `corpus-lab/state/rescore_from_results.json` | 34,818 | `22441f1013a138ca` |
| `verify_search_fix.json` | `corpus-lab/state/verify_search_fix.json` | 4,392 | `d5e48755c9502d9f` |

## `04_evidence_v1_build/` — Night 4a - the evidence_v1 table-catalogue engine and its stop

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `ACCEPTANCE.md` | `ACCEPTANCE.md` | 14,136 | `c61bb8276652b97f` |
| `ACCEPTANCE_NOT_PUBLISHED.md` | *(written here)* — why the ACCEPTANCE.md oracle is excluded from the repository | 1,094 | `8aa2a5b58a66c1d6` |
| `BUILD_PROMPT.md` | `BUILD_PROMPT.md` | 38,809 | `d49c11d99881baa2` |
| `SOLUTION.md` | `SOLUTION.md` | 26,228 | `e7e1ec6dcdd34429` |
| `STOP_REASON_run1_corpus_baseline_changed.md` | `corpus-lab/state/evidence_v1/20260912T214913Z-7864bc46/STOP_REASON.md` | 2,508 | `2be3b8bff91eab5a` |
| `STOP_REASON_run2_retrieval_gate_failed.md` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/STOP_REASON.md` | 7,201 | `b50a505e02353d87` |
| `run2_free-tests.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/free-tests.json` | 761 | `c90074c0a278ea9a` |
| `run2_integrity-after.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/integrity-after.json` | 313 | `41ab3f999e3aab67` |
| `run2_retrieval.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/retrieval.json` | 9,431 | `c6dd460105c1a179` |
| `run2_setup.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/setup.json` | 1,186 | `e23e92c53a3319e1` |
| `run2_stage2_gate.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/stage2_gate.json` | 646 | `32ec7ddf9aa7c12f` |
| `run2_status.json` | `corpus-lab/state/evidence_v1/20260912T220732Z-cede10c8/status.json` | 2,134 | `bd915c13f2d3ddb3` |

## `05_evidence_v1_tuning/` — Night 4b - the disciplined tuning loop against a frozen holdout

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `TUNING_SUMMARY.md` | `corpus-lab/state/evidence_v1/TUNING_SUMMARY_2026-09-13.md` | 8,735 | `749888b132294395` |
| `tuning_log.jsonl` | `corpus-lab/state/evidence_v1/tuning_log.jsonl` | 17,101 | `ed41996518230cf4` |

## `06_approach_c_shelf/` — Night 4c - approach C, document-first 'shelf', built and gated

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `C_SHELF_FIRST_BUILD.md` | `plans_fable/C_SHELF_FIRST_BUILD.md` | 29,833 | `01273da06c41c63c` |
| `C_SHELF_FIRST_PLAN.md` | `plans_fable/C_SHELF_FIRST_PLAN.md` | 9,369 | `a9d338016d0e64d3` |
| `STAGE3_OFFLINE_GATE_REPORT.md` | *(written here)* — approach C's offline gate in full, incl. the corrected series-walk result | 14,509 | `a5c2ae6624a26227` |
| `c_offline_gate.json` | `corpus-lab/state/c_offline_gate.json` | 784 | `6c43c8dc788c2cab` |
| `c_preflight.json` | `corpus-lab/state/c_preflight.json` | 1,123 | `c91c200402b30f67` |
| `c_queries.json` | `corpus-lab/state/c_queries.json` | 8,268 | `0b72574499c20e81` |
| `c_shelf_build.json` | `corpus-lab/state/c_shelf_build.json` | 1,143 | `47861b2f0795444c` |
| `c_shelf_selftest.json` | `corpus-lab/state/c_shelf_selftest.json` | 991 | `e8ad8b451ce7ff87` |

## `07_approach_b_planned/` — Approach B - hybrid multi-query, planned but never built

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `B_HYBRID_MULTIQUERY_BUILD.md` | `plans_fable/B_HYBRID_MULTIQUERY_BUILD.md` | 33,830 | `e3a1b81283936b0d` |
| `B_HYBRID_MULTIQUERY_PLAN.md` | `plans_fable/B_HYBRID_MULTIQUERY_PLAN.md` | 13,036 | `ab23c155d96a5c12` |
| `plans_fable_README.md` | `plans_fable/README.md` | 4,272 | `a85874fbe738f1fc` |

## `08_what_next/` — The research pass, its correction, and the next-build contract

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `CORRECTION_2026-09-13.md` | *(written here)* — supersedes the Shelf V2 recommendation in RESEARCH_2026-09-13.md | 1,469 | `7d222a6eb79a7b26` |
| `ARCHITECTURE_REVIEW_2026-09-13.md` | *(written here)* — the adversarial review of the 2026-09-13 architecture, archived verbatim | 37,790 | `94883e6be6f57b9a` |
| `CURRENT_WORKING_ARCHITECTURE_2026-09-13.md` | *(written here)* — the synthesis the review attacked; superseded 2026-09-14 | 9,374 | `24120b6b5388e248` |
| `CURRENT_WORKING_ARCHITECTURE_2026-09-14.md` | *(written here)* — corrected architecture after experiments A and B were run; superseded 2026-09-15 | 9,806 | `5b7c92f903a47cae` |
| `HANDOFF_2026-09-14.md` | *(written here)* — the corrected-continuation phase in twelve answers | 8,924 | `598b0529780064d3` |
| `CURRENT_WORKING_ARCHITECTURE_2026-09-15.md` | *(written here)* — architecture after the caption experiments, the first live battery and the first end-to-end run | 30,408 | `ad59af75f1589c7b` |
| `HANDOFF_2026-09-15.md` | *(written here)* — the 2026-09-15 phase in thirteen answers | 15,914 | `8489faec6fe93b78` |
| `HANDOFF_2026-09-15_pm.md` | *(written here)* — the afternoon forensics phase in seven answers | 11,772 | `84443c51113727c5` |
| `HANDOFF_2026-09-15_evening.md` | *(written here)* — Experiment G, the production changes, chain v2 and the third live battery, in seven answers | 9,954 | `a4cd1678583c757c` |
| `HANDOFF_2026-09-16_night.md` | *(written here)* — the production hardening night: latency, shelf v2's STOP, the two measurement repairs, and LIVE-5 on both models | 12,825 | `ff87c9a056b3d2d1` |
| `DEMO_2026-09-16.md` | *(written here)* — the morning demo script, with measured timings and the caveats to volunteer unasked | 7,339 | `f785eb518c4f79c6` |
| `CURRENT_WORKING_ARCHITECTURE_2026-09-16_night_addendum.md` | *(written here)* — addendum H: what is in production after the night, and why shelf v2 is not | 5,795 | `aa25c26ea0b93780` |
| `HANDOFF_2026-09-16.md` | *(written here)* — the model as document selector, the citation guard, and the fourth live battery, in eight answers | 9,392 | `de8cfb8cec5d8a1c` |
| `SESSION_LOG_2026-09-13_to_09-14.md` | *(written here)* — the full handover: six execution phases, the manual Sonnet/Opus sessions verbatim with timings and accuracy, the current state, and an operating manual | 58,819 | `c1094ee9ec4abc10` |
| `EXECUTE_SHELF_V2.md` | `EXECUTE_SHELF_V2.md` *(notice added)* | 10,923 | `5d89454913c705d5` |
| `RESEARCH_2026-09-13.md` | `RESEARCH_2026-09-13.md` *(notice added)* | 12,302 | `314fd7ed6cf90162` |

## `09_ledgers/` — Raw ledgers - every finding, every step, and how to resume

| file | original | bytes | sha256[:16] |
|---|---|---|---|
| `FINDINGS_LIVE.md` | `corpus-lab/05_findings/FINDINGS_LIVE.md` | 118,352 | `950c5e66146e12d6` |
| `RESUME.md` | `corpus-lab/RESUME.md` | 11,283 | `b9fe6c5fbce760f8` |
| `progress.jsonl` | `corpus-lab/state/progress.jsonl` | 119,772 | `b1421e8ed9b0b2d5` |

## Phase 9 state artefacts — 2026-09-16 production hardening night

Not copied into `REPORT/`; listed with checksums so a reviewer can confirm the numbers in
F64–F69 against the files that produced them. Paths are relative to the project root.

| file | bytes | sha256[:16] |
|---|---|---|
| `corpus-lab/state/phase9_live_spec.md` | 4,180 | `461863316e709655` |
| `corpus-lab/state/c_shelf_bench.json` | 17,516 | `68ff0967cabd3f38` |
| `corpus-lab/state/c_open_equiv.json` | 204 | `fa7e842b6a8f2a59` |
| `corpus-lab/state/c_caption_align.json` | 309 | `6737205f6809b7fc` |
| `corpus-lab/state/c_inside_equiv.json` | 276 | `617cf490d00976fe` |
| `corpus-lab/state/c_compact_depth.json` | 352 | `db0576b77146bc0c` |
| `corpus-lab/state/c_shelf_build_v2.json` | 862 | `c02b58dcb451e509` |
| `corpus-lab/state/c_shelf_v2_gate.json` | 2,762 | `33c7d000e3ff26b2` |
| `corpus-lab/state/c_score_live_v2_selftest.json` | 625 | `632e69d641502d53` |
| `corpus-lab/state/c_live_battery_v2__P9S_live.json` | 1,384 | `a5fd738720c7fa8f` |
| `corpus-lab/state/c_live_battery_v2__P9O_live.json` | 1,384 | `28bade0b2b4ab2ed` |
| `corpus-lab/state/c_live_forensics_p9s.json` | 4,999 | `0c8d31392a67b1b8` |
| `corpus-lab/state/c_live_forensics_p9o.json` | 5,144 | `e4013d74dba26a41` |
| `corpus-lab/state/phase9_probes__P9S.json` | 921 | `c4736c25430bb9cb` |
| `corpus-lab/state/phase9_probes__P9O.json` | 925 | `258affc7ab14a934` |
| `corpus-lab/state/phase9_rehearsal.json` | 781 | `fcda2ec03db6845f` |
| `corpus-lab/state/c_selftest_corpus500.json` | 1,523 | `cc018e6816c9b8cf` |
| `corpus-lab/state/phase9_checkpoint.json` | 5,962 | `51b8fa0c3076b1fd` |
| `corpus-lab/state/checksums/s7_phase9_pre.json` | 4,789 | `7d5c03b54239bb76` |
| `corpus-lab/state/checksums/s7_phase9_live_pre.json` | 4,794 | `1357036bc8400b71` |

20 files, 59,692 bytes. Generated 2026-09-15 → 09-16.

---

51 files, 714,866 bytes. Regenerated 2026-09-14.
