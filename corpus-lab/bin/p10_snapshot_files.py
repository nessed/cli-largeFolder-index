#!/usr/bin/env python
"""p10_snapshot_files.py - the list docs_check.py compares against.

Plan E Phase 0.4: `docs_check.py` fails if a state or score file written tonight
shares a path with a file that already existed. That test needs a list of what
existed before the run, taken once, at the top of Phase 0, and committed.

Writes repo-relative POSIX paths, sorted, to
corpus-lab/state/phase10_preexisting_files.txt.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

SKIP_DIRS = {".git", ".venv", "99_scratch", "node_modules", "__pycache__",
             "dist", ".pytest_cache"}

# Only the directories docs_check.py guards. Walking the whole tree would list
# 15,000 corpus files and -- worse -- every filename under _private/harness_keys,
# which the contamination rule keeps out of committed files. Scored outputs are
# derived filenames, not key content, so 04_scores is in scope and the rest of
# _private is not.
SCOPE = [
    "corpus-lab/state",
    "corpus-lab/experiments",
    "corpus-lab/bin",
    "corpus-lab/tests",
    "REPORT",
    "_private/results/04_scores",
]
OUT = L.STATE / "phase10_preexisting_files.txt"


def main():
    root = L.RETRIEVAL_LAB
    rows = []
    for scope in SCOPE:
        base = root / scope
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                p = Path(dirpath) / f
                try:
                    rows.append(p.relative_to(root).as_posix())
                except ValueError:
                    continue
    rows = sorted(set(rows))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("snapshotted %d pre-existing files -> %s" % (len(rows), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
