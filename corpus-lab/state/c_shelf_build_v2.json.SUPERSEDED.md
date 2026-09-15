# SUPERSEDED — for production-portability claims only

`c_shelf_build_v2.json` records a build made with the **experimental v2 shelf builder**,
`c_shelf_build_v2.py`, which **failed Gate S on 2026-09-15**.

**By what:** Gate R1, Phase 10.3 (2026-09-16). Two clean-room installs of the portable
package, both using the **v1** builder, which is what production and the demo run and
what every measured number in the report rests on. See
`corpus-lab/experiments/p10_portable_r1/README.md` and
`corpus-lab/state/phase10_gate_r1_result.json`.

**Why:** `setup_folder.py install` shipped `c_shelf_build_v2.py` unconditionally while
production ran v1. Any claim of the form "the portable builds what we measured" that
rested on a v2 build was claiming something about a different artefact. From Phase 10.3
the installer defaults to `--builder v1`; `--builder v2` prints
`EXPERIMENTAL SHELF V2 -- failed Gate S 2026-09-15; not production` and stamps
`builder: v2 (experimental)` into `build_manifest.json`, so v2 can never be used silently.

**Where the replacement lives:** `corpus-lab/state/phase10_gate_r1_result.json`, and the
per-install `build_manifest.json` / `BUILD_REPORT.md` / `canonical_export.json` written
into each artefacts directory.

**What is NOT superseded:** this file remains the correct record of the v2 builder's own
gate numbers, and the shelf v2 experiment itself stands as recorded. v2 is still a
live idea; it is simply not what ships, and not what any portability claim may rest on.
The file itself is untouched (Plan E rule 15).
