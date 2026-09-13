#!/usr/bin/env python
"""Stop hook entry: the returned final text must equal the latest compose
output for this session's most recent request, verbatim. One correction is
permitted; a second mismatch is logged VISIBLE_OUTPUT_UNVERIFIED and the
session fails. This hook cannot retroactively hide text already streamed to
the user -- it only decides whether to ask Claude to correct itself once.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evidence_v1 import store  # noqa: E402

RETRY_MARKER_NAME = ".ev1_stop_retry"


def _last_assistant_text(transcript_path):
    p = Path(transcript_path)
    if not p.exists():
        return None
    last_text = None
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = rec.get("message", {})
            if msg.get("role") == "assistant":
                content = msg.get("content")
                if isinstance(content, list):
                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    if texts:
                        last_text = "".join(texts)
                elif isinstance(content, str):
                    last_text = content
    return last_text


def _latest_receipt_answer(root):
    try:
        con = store.connect(root, timeout_s=2.0)
        row = con.execute(
            "SELECT output FROM receipts ORDER BY created_at DESC LIMIT 1").fetchone()
        con.close()
    except Exception:
        return None
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    return data.get("answer_text")


def _norm(text):
    return " ".join((text or "").split())


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    cwd = data.get("cwd") or os.getcwd()
    root = Path(cwd)
    transcript_path = data.get("transcript_path")

    expected = _latest_receipt_answer(root)
    if expected is None:
        print(json.dumps({"decision": "approve"}))
        return 0

    actual = _last_assistant_text(transcript_path) if transcript_path else None
    if actual is not None and _norm(actual) == _norm(expected):
        print(json.dumps({"decision": "approve"}))
        return 0

    retry_marker = store.runtime_dir(root) / RETRY_MARKER_NAME
    if retry_marker.exists():
        retry_marker.unlink()
        print(json.dumps({
            "decision": "block",
            "reason": "VISIBLE_OUTPUT_UNVERIFIED: returned text still does not match the "
                      "compiler's latest output after one correction. Failing this session "
                      "rather than claiming the hidden receipt is authoritative.",
        }))
        return 0

    retry_marker.parent.mkdir(parents=True, exist_ok=True)
    retry_marker.write_text("1", encoding="utf-8")
    print(json.dumps({
        "decision": "block",
        "reason": "Return the most recent compose output verbatim. Do not add factual claims.",
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
