#!/usr/bin/env python
"""diag_quotes.py - second hypothesis for the stream-json break.

diag_streamjson.py ruled out the corpus root and the stdout destination: all ten
combinations returned valid stream-json for a short, quote-free prompt. The phase
2.6 probe that DID break used a long prompt containing embedded double quotes and
newlines.

claude.cmd is a cmd.exe batch wrapper. cmd.exe re-parses the command line before
handing it to node, and an embedded double quote can terminate the quoted prompt
argument early -- so everything after it, INCLUDING --output-format stream-json,
gets absorbed into the prompt text instead of being parsed as a flag. The session
then runs in default text mode, returns prose, exits 0, and writes nothing to
stderr. Which is exactly the reported symptom.

This varies ONLY the prompt and holds everything else fixed.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

PROMPTS = {
    "plain                 ": "Reply with exactly: pong. Do not use any tools.",
    "with_double_quotes    ": 'Reply with exactly: pong. Ignore the phrase "hello there". Do not use any tools.',
    "with_single_quotes    ": "Reply with exactly: pong. Ignore the phrase 'hello there'. Do not use any tools.",
    "with_newlines         ": "Reply with exactly: pong.\n\nDo not use any tools.",
    "with_backticks        ": "Reply with exactly: pong. Ignore `hello`. Do not use any tools.",
    "with_caret_and_amp    ": "Reply with exactly: pong. Ignore a^b & c. Do not use any tools.",
    "with_percent          ": "Reply with exactly: pong. Ignore %PATH% and %%x. Do not use any tools.",
    "quotes_and_newlines   ": 'Reply with exactly: pong.\n\nRun: type "C:\\some\\path.csv"\n\nDo not use any tools.',
}


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


def run(prompt, exe):
    cmd = [exe, "-p", prompt,
           "--output-format", "stream-json", "--verbose",
           "--model", "claude-sonnet-5", "--max-turns", "2",
           "--permission-mode", "bypassPermissions"]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                     encoding="utf-8") as fh:
        p = fh.name
    with open(p, "w", encoding="utf-8") as fh, open(os.devnull) as dn:
        rc = subprocess.run(cmd, cwd=str(L.RASHIP), stdout=fh,
                            stderr=subprocess.DEVNULL, stdin=dn).returncode
    t = Path(p).read_text(encoding="utf-8", errors="replace")
    Path(p).unlink(missing_ok=True)
    return rc, t


if __name__ == "__main__":
    out = {}
    print(f"exe = {L.CLAUDE}")
    for label, prompt in PROMPTS.items():
        rc, text = run(prompt, L.CLAUDE)
        kind, n = classify(text)
        head = " ".join((text or "").strip().splitlines()[:1])[:60]
        flag = "" if kind == "STREAM_JSON" else "   <<<< BREAKS"
        print(f"  {label} rc={rc} -> {kind:<12} lines={n:<3} | {head}{flag}")
        out[label.strip()] = {"rc": rc, "kind": kind, "json_lines": n}
    dest = L.STATE / "diag_quotes.json"
    dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"written: {dest}")
