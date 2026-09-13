#!/usr/bin/env python
"""UserPromptSubmit hook entry: calls `prepare` automatically. No model call
-- this only runs deterministic retrieval/inventory code and injects the
resulting request_id/leads as additional context for Claude to use via the
CLI, per policy.txt.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evidence_v1 import cli as ev_cli  # noqa: E402


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    cwd = data.get("cwd") or os.getcwd()
    question = data.get("prompt", "")
    root = Path(cwd)

    class Args:
        pass
    args = Args()
    args.root = str(root)
    args.question = question

    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        ev_cli.cmd_prepare(args)
    except Exception as e:
        sys.stdout = old_stdout
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                   "additionalContext":
                                                   "evidence engine prepare failed: {}".format(e)}}))
        return 0
    finally:
        sys.stdout = old_stdout
    context = "Evidence engine prepared this request:\n" + buf.getvalue()
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                              "additionalContext": context}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
