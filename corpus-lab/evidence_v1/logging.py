#!/usr/bin/env python
"""evidence_v1.logging -- append-only runtime.jsonl under the runtime dir.
Runtime code, no labpaths import, no key content ever written here."""
import json
import time

from . import store


def log_event(root_path, event, **fields):
    rd = store.runtime_dir(root_path)
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event}
    rec.update(fields)
    with open(rd / "runtime.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
