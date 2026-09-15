# 00_archive — superseded originals

Moved out of the repository root on 2026-09-15. Nothing here is current. Nothing here should
be executed as written. They are kept because `REPORT/MANIFEST.md` lists them as the sources
its published copies were taken from, and because two of them contain reasoning worth reading
even though their recommendations were overturned.

| file | what it is | why it is here |
|---|---|---|
| `SOLUTION.md` | the `evidence_v1` design rationale, 2026-09-13 | that lane stopped at its Stage 2 gate; the shipped system is approach C. Published copy: `REPORT/04_evidence_v1_build/SOLUTION.md` |
| `BUILD_PROMPT.md` | the staged contract `evidence_v1` was executed against | same lane. Published copy: `REPORT/04_evidence_v1_build/BUILD_PROMPT.md` |
| `RESEARCH_2026-09-13.md` | an outside research pass recommending Shelf V2 | its premise — that semantic retrieval over the card pool was untested — was false; approach C had already measured and failed that route. See `REPORT/08_what_next/CORRECTION_2026-09-13.md` |
| `EXECUTE_SHELF_V2.md` | the build contract for that recommendation | superseded with it. Kept for its staging, gating and verification design, which remain sound |
| `ACCEPTANCE.md` | private examination answers — **an oracle in prose** | never in git (`.gitignore:26`), never readable from a measured session. See below |

## The one that matters

`ACCEPTANCE.md` holds gold source paths, literal cell values and page indices. Reading it, or
letting a measured session read it, invalidates every number this project has recorded.

Two independent rules keep that from happening, both in `corpus-lab/bin/c_stack.py`:
this whole directory is on the installed deny list (`EXTRA_READ_DENY_DIRS`), and the file is
denied again by name (`EXTRA_READ_DENY_FILES`). If you move this directory or rename it, update
both — the move that created it was only safe because they were updated first.

Its *criteria* are fully described in `BUILD_PROMPT.md` and `SOLUTION.md`, both published in
`REPORT/`. Only the expected answers are withheld.
