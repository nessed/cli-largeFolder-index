#!/usr/bin/env python
"""diag_streamjson.py - isolate the stream-json break.

Symptom (night 1, and reproduced in phase 2.6): the same claude.cmd invocation
with --output-format stream-json --verbose sometimes emits valid JSON lines and
sometimes emits plain prose, with returncode 0 and empty stderr either way.
Night 1 concluded it correlated with the corpus root. Phase 2.6 saw it on BOTH
roots -- and between night 1 and now, ask.py changed stdout from a FILE handle to
a PIPE. That is the variable this script tests.

Runs the same trivial question four ways and reports what came back.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

Q = "Reply with exactly the word: pong. Do not use any tools."


def base_cmd():
    return [L.CLAUDE, "-p", Q,
            "--output-format", "stream-json", "--verbose",
            "--model", "claude-sonnet-5",
            "--max-turns", "2",
            "--permission-mode", "bypassPermissions"]


def classify(text):
    t = (text or "").strip()
    if not t:
        return "EMPTY", 0
    n = 0
    for line in t.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            n += 1
        except Exception:
            pass
    return ("STREAM_JSON" if (t[0] == "{" and n) else "PROSE"), n


def run_to_file(cwd, extra=None):
    with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False,
                                     encoding="utf-8") as fh:
        p = fh.name
    with open(p, "w", encoding="utf-8") as fh, open(os.devnull) as dn:
        rc = subprocess.run(base_cmd() + (extra or []), cwd=cwd, stdout=fh,
                            stderr=subprocess.DEVNULL, stdin=dn).returncode
    t = Path(p).read_text(encoding="utf-8", errors="replace")
    Path(p).unlink(missing_ok=True)
    return rc, t


def run_to_pipe(cwd, extra=None, text_mode=True):
    with open(os.devnull) as dn:
        pr = subprocess.run(base_cmd() + (extra or []), cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            stdin=dn, text=text_mode,
                            encoding="utf-8" if text_mode else None,
                            errors="replace" if text_mode else None)
    out = pr.stdout if text_mode else pr.stdout.decode("utf-8", "replace")
    return pr.returncode, out


CASES = [
    ("stdout -> FILE                 ", lambda c: run_to_file(c)),
    ("stdout -> PIPE (text mode)     ", lambda c: run_to_pipe(c, text_mode=True)),
    ("stdout -> PIPE (binary mode)   ", lambda c: run_to_pipe(c, text_mode=False)),
    ("stdout -> FILE + disallowTools ", lambda c: run_to_file(
        c, ["--disallowedTools", "Write", "Edit", "NotebookEdit"])),
    ("stdout -> PIPE + disallowTools ", lambda c: run_to_pipe(
        c, ["--disallowedTools", "Write", "Edit", "NotebookEdit"], text_mode=True)),
]

if __name__ == "__main__":
    roots = {"h15000": str(L.rung(15000)), "raship": str(L.RASHIP)}
    results = {}
    for rname, root in roots.items():
        print(f"\n########## cwd = {rname}  ({root})")
        for label, fn in CASES:
            try:
                rc, out = fn(root)
            except Exception as e:
                print(f"  {label} EXCEPTION {e}")
                continue
            kind, n = classify(out)
            head = " ".join((out or "").strip().splitlines()[:1])[:70]
            print(f"  {label} rc={rc} -> {kind:<12} json_lines={n:<3} | {head}")
            results[f"{rname}|{label.strip()}"] = {"rc": rc, "kind": kind,
                                                   "json_lines": n, "head": head}
    dest = L.STATE / "diag_streamjson.json"
    dest.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\nwritten: {dest}")
