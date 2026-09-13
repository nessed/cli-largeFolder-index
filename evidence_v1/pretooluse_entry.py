#!/usr/bin/env python
"""PreToolUse hook entry -- thin stdin/stdout wrapper around hooks.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evidence_v1 import hooks  # noqa: E402

if __name__ == "__main__":
    sys.exit(hooks.main_pretooluse())
