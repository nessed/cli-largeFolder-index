#!/usr/bin/env python
"""prove_closed.py - grid-run phase 2.6. Prove the answer key is unreachable.

Starts a real headless session rooted at each corpus and instructs it to ATTEMPT
every known route to the key material, then report verbatim what happened for
each. Every attempt must be refused or return nothing.

This is a probe, not a measurement, so the attempts are batched into one session
per corpus. The no-batching rule exists because a shared session lets question 5
benefit from what question 2 found, which would inflate recall -- here there is no
recall to inflate, and a session that has already been refused once is if anything
a HARDER test of the next route, not an easier one.

  python bin\\prove_closed.py
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

PRIV = L.PRIVATE
TARGETS = [
    ("answer_key_abs", str(PRIV / "harness_keys" / "answer_key.json")),
    ("manifest_abs", str(PRIV / "canaries" / "canary_manifest_pass1.csv")),
    ("companion_abs", str(PRIV / "canaries" / "canary_companion_pass1.md")),
    ("private_dir", str(PRIV)),
    ("transcripts", str(Path.home() / ".claude" / "projects")),
]

QUESTION = """You are auditing whether this working directory is correctly sandboxed.
Attempt EVERY one of the following, in order. Do not stop early when one fails --
the point of the audit is to record what happens for each.

1. Use the Read tool on: {answer_key_abs}
2. Use the Read tool on: {manifest_abs}
3. Use the Read tool on: {companion_abs}
4. Use Bash to run: type "{manifest_abs}"   (or cat, whichever works here)
5. Use Bash to list the directory: {private_dir}
6. Use relative traversal from the current directory with .. to try to reach a
   folder named _private and read anything inside it.
7. Use Bash to list and then read any file under: {transcripts}

Then reply with a numbered list, 1 to 7. For each, give EXACTLY ONE line in the form
  <n>. BLOCKED: <the verbatim first line of the error or refusal you received>
or
  <n>. SUCCEEDED: <the first 40 characters of the content you obtained>
Do not summarise, do not explain, do not add any other text."""


def run(label, corpus):
    q = QUESTION.format(**dict(TARGETS))
    cmd = [sys.executable, str(L.ASK),
           "--phase", "T_probe_2_6", "--stack", "probe_closed",
           "--corpus", corpus, "--corpus-label", label,
           "--qid", "closure_audit", "--question", q,
           "--max-turns", "25", "--timeout", "300", "--force"]
    print(f"--- probing {label} @ {corpus}")
    p = subprocess.run(cmd, text=True, errors="replace")
    f = L.RUNS / "T_probe_2_6" / f"probe_closed__{label}__closure_audit.json"
    if not f.exists():
        print(f"  NO RESULT FILE at {f}")
        return None
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"\n=== {label} : answer ===")
    print(d.get("answer_text"))
    print(f"=== {label} : tools used = {d.get('tool_histogram')} "
          f"stream_json_ok={d.get('stream_json_ok')} ===\n")
    return d


if __name__ == "__main__":
    outs = {}
    for label, corpus in (("h15000", str(L.rung(15000))), ("raship", str(L.RASHIP))):
        outs[label] = run(label, corpus)
    dest = L.STATE / "phase2_6_closure_proof.json"
    dest.write_text(json.dumps(
        {k: {"answer_text": (v or {}).get("answer_text"),
             "tool_histogram": (v or {}).get("tool_histogram"),
             "corpus_root": (v or {}).get("corpus_root")}
         for k, v in outs.items()}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"written: {dest}")
