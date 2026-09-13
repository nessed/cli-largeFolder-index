#!/usr/bin/env python
"""corpus-lab/bin/evidence.py -- public CLI entrypoint. Thin wrapper: all logic
lives in corpus-lab/evidence_v1/cli.py (runtime, no labpaths import)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evidence_v1 import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli.main())
