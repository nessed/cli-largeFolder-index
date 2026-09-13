# Cleanup log

Started 2026-09-10 12:10:46. Appended as work proceeds. Nothing committed or pushed at any point.

| time | path | action | bytes |
|---|---|---|---|
| 12:10:58 | `C:\Users\Ali\Desktop\corpus-lab\03_runs\P2_s0_harness\_session_memory_removed` | created; 3 memory files copied here (kept as a result) | 3133 |
| 12:10:58 | `C:\Users\Ali\.claude\projects\C--Users-Ali-Desktop-harness-corpus-500\memory` | DELETED (contaminates future harness runs) | 3133 |
| 12:11:32 | `.claude\projects\*\memory\` | SCANNED all 26 project dirs. ra-ship memory/ = EMPTY (0 files); m0-fixture memory/ = EMPTY (0 files). 18 other project dirs hold pre-existing personal memories (jarvis, akada, lmda, budget, battery, whatsapp-echo-bot, ...) dated Jun-Sep, unrelated to this run. NONE TOUCHED. | 0 |
| 12:11:32 | `C:\Users\Ali\Desktop\corpus-lab\03_runs\_session_archive\raship` | COPIED 32 .jsonl transcripts from C--Users-Ali-desktop-projects-code-ra-ship (verified match) | 12863093 |
| 12:11:33 | `C:\Users\Ali\Desktop\corpus-lab\03_runs\_session_archive\harness_500` | COPIED 20 .jsonl transcripts from C--Users-Ali-Desktop-harness-corpus-500 (verified match) | 8857301 |
| 12:11:33 | `C:\Users\Ali\Desktop\corpus-lab\03_runs\_session_archive\probes` | COPIED 5 .jsonl transcripts from C--Users-Ali-Desktop-corpus-lab-99-scratch-m0-fixture (verified match) | 804853 |
| 12:11:33 | `C:\Users\Ali\Desktop\corpus-lab\01_reports\majestic-finding-swan.md` | COPIED plan file from .claude\plans (verified identical) | 23874 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\raship.db` | DELETED | 3510956032 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\raship.db-shm` | DELETED | 32768 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\raship.db-wal` | DELETED | 0 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\harness_500.db` | DELETED | 203444224 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\harness_500.db-shm` | DELETED | 32768 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\harness_500.db-wal` | DELETED | 0 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\03_runs\T` | DELETED tree (2 files) | 21124 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\04_scores\harness__x__rung500.json` | DELETED | 1614 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\04_scores\summary__x__rung500.json` | DELETED | 285 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\99_scratch\m0_out.jsonl` | DELETED | 21294 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\99_scratch\m0_err.txt` | DELETED | 157 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\99_scratch\m0_fixture` | DELETED tree (3 files) | 315 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\00_RUNBOOK_RESULTS.md` | DELETED | 11839 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\bin\hook_deny.py` | DELETED | 1359 |
| 12:12:18 | `C:\Users\Ali\Desktop\corpus-lab\02_stacks\s2_fts5\settings_deny.json` | DELETED | 266 |
| 12:12:20 | `C:\Users\Ali\Desktop\harness\logs\progress` | CONTENTS DELETED (5772 files), dir kept | 5228 |
| 12:12:36 | `C:\Users\Ali\AppData\Local\Temp\claude` | DELETED 40 task-output files inside the run window; kept 1 later + 907 older | 751081 |
| 12:12:53 | `02_stacks\{s0_baseline,s1_rga,s3_hybrid,s4_stretch}` | KEPT (empty). Stacks defined but never run: **s1_rga** (ripgrep-all not installable - no cargo/Rust), **s3_hybrid** (no CUDA/torch, CPU-only), **s4_stretch** (never chosen, out of time). **s0_baseline** ran but wrote no artefacts here - its results are in `03_runs\P2_s0_baseline`. Only **s2_fts5** produced output. | 0 |
| 12:12:53 | — | CLEANUP COMPLETE | — |
| 12:13:46 | `RESUME.md` | EDITED - section 6 previously said the indexes existed and should not be rebuilt. Now states they were deleted, with the exact rebuild commands and timings. | 0 |

## Summary

| category | bytes freed | note |
|---|---|---|
| SQLite indexes (2 DBs + 4 sidecars) | **3,714,465,792** | regenerable in ~10 min |
| Temp task outputs (40 files, run window only) | 751,081 | 1 later file + 907 older left alone |
| Smoke-test junk (`03_runs\T`, `*__x__*`) | 23,023 | |
| Probe scratch (`m0_*`, `m0_fixture`) | 21,766 | included the live hook config in the fixture |
| Duplicate / superseded (`00_RUNBOOK_RESULTS.md`, `hook_deny.py`, `settings_deny.json`) | 13,464 | duplicate confirmed by sha256 before deleting |
| Harness `logs\progress` markers (5,772 files) | 5,228 | directory kept, now empty |
| **TOTAL** | **3,715,280,354** | **3.715 GB** |

corpus-lab: **3,716,065,953 B -> 24,097,680 B** (3.716 GB -> 24.10 MB), 175 -> 218 files.
File count rose because 57 session transcripts + 3 memory files were archived IN.

## Verification after cleanup
- harness tree: **0 files** with mtime after 2026-09-10 00:00 (only change: `logs\progress` emptied)
- ra-ship: **0 files** modified after midnight; `git status` = the 9-entry canary baseline
- archive: raship 32 / harness_500 20 / probes 5 transcripts, byte-counts matched source exactly
- keep-list: all 18 protected files verified present
- nothing committed, nothing pushed
