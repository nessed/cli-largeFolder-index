#!/usr/bin/env python
"""evidence_v1.install -- wires CLAUDE.md/settings.json installation through
corpus-lab/bin/stack.py. Runtime code that imports NOTHING from labpaths
itself: stack.py is invoked as a SUBPROCESS (it is the one place allowed to
import labpaths, and only it ever writes those two files), never imported as
a module here.
"""
import json
import subprocess
import sys
from pathlib import Path

STACK_PY = Path(__file__).resolve().parent.parent / "bin" / "stack.py"


def install_hooks(root):
    py = sys.executable
    r = subprocess.run(
        [py, str(STACK_PY), "setup-evidence-v1", "--corpus", str(root)],
        capture_output=True, text=True, timeout=30)
    ok = (r.returncode == 0)
    return {"ok": ok, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


def uninstall_hooks(root):
    py = sys.executable
    r = subprocess.run(
        [py, str(STACK_PY), "teardown-evidence-v1", "--corpus", str(root)],
        capture_output=True, text=True, timeout=30)
    ok = (r.returncode == 0)
    return {"ok": ok, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


def hook_status(root):
    sj = Path(root) / ".claude" / "settings.json"
    if not sj.exists():
        return {"installed": False}
    try:
        cfg = json.loads(sj.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"installed": False, "error": "settings.json not valid JSON"}
    return {"installed": bool(cfg.get("__evidence_v1_owned__"))}
