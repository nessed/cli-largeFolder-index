#!/usr/bin/env python
"""SessionStart hook entry: lightweight health check, no model call."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evidence_v1 import store  # noqa: E402


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    cwd = data.get("cwd") or os.getcwd()
    root = Path(cwd)
    db = store.db_path(root)
    msg = "Evidence engine ready." if db.exists() else (
        "Evidence engine not yet installed for this folder -- run SETUP_EVIDENCE.ps1.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                              "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
