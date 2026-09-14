#!/usr/bin/env python
"""c_stop_guard.py -- Stop hook: a citation guard at the answer boundary.

2026-09-16. F59 measured that enforcing provenance at the `note` boundary does
nothing, because the answer never passes through the note: the session notes
the pages it opened and then names extra paths in its final message, where no
check existed. `cited_unopened_total` went 8 -> 10 with the note guard live.

So the check moves to the only place the answer actually is. On Stop this hook
reads the session transcript, collects every `open "<path>" <page>` the session
issued, collects every path-like string in the final assistant message, and if
a cited path was never opened it blocks ONCE with a reason.

**This is not the S2 hook.** S2 denied the search tools outright and forced a
route; it was a controller. This reads one property of a finished answer and
asks once. It never edits text, never blocks an answer that cites nothing, and
a second stop passes unconditionally -- so a session that disagrees, or that
cannot open the page, always terminates.

Installed by c_stack.py into the rung's .claude/settings.json.
Exit 0 with a JSON decision, as Claude Code's Stop hook contract requires.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

LOG = Path(os.environ.get("STOP_GUARD_LOG",
                          str(L.RUNS / "hooks" / "stop_guard__unlabelled.log")))
MARKER_DIR = Path(os.environ.get("STOP_GUARD_MARKERS",
                                 str(L.SCRATCH / "stop_guard_markers")))

EXTS = r"(?:pdf|xlsx|xls|docx|doc|csv|txt|md|pptx|ppt)"
# a path-like string in free answer text: at least one separator, then a known
# corpus extension. Directory names in this corpus contain spaces.
CITED_RE = re.compile(
    r"[A-Za-z0-9_\-.()\[\]][A-Za-z0-9_\-./\\()\[\] ]{0,180}?[/\\][A-Za-z0-9_\-.()\[\] ]{1,120}?\." + EXTS,
    re.I)
# `... c_shelf.py open "<rel>" <page>` in a Bash command string
OPEN_RE = re.compile(r"open\s+(?P<q>[\"'])(?P<rel>.+?)(?P=q)\s+(?P<page>\d+)", re.S)
OPEN_BARE_RE = re.compile(r"open\s+(?P<rel>\S+\." + EXTS + r")\s+(?P<page>\d+)", re.I)

REASON = ("You cited {path} without opening it. Either open that page and quote the "
          "supporting line, or remove the citation. Do not add any figure you have "
          "not opened.")


def segs_of(s):
    return [x for x in str(s or "").replace("\\", "/").lower().split("/") if x]


def tail2(s):
    return "/".join(segs_of(s)[-2:])


def same_path(cited, opened):
    """Directory names in this corpus contain spaces, so a path lifted out of
    free answer text keeps whatever prose word preceded it ("from some_dir/x.pdf").
    Comparing those literally marks a file the session DID open as unopened,
    which turns the guard into a false-positive generator -- it blocked the
    opened file in its own self-test. The filename must match exactly and the
    parent directory by suffix; that is the same rule scoring.py uses."""
    a, b = segs_of(cited), segs_of(opened)
    if not a or not b or a[-1] != b[-1]:
        return False
    if len(a) >= 2 and len(b) >= 2:
        return a[-2].endswith(b[-2]) or b[-2].endswith(a[-2])
    return True


def read_transcript(path):
    """Returns (opened_paths, final_assistant_text)."""
    opened, texts = set(), []
    p = Path(path) if path else None
    if not p or not p.exists():
        return opened, ""
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        msg = d.get("message") or {}
        if d.get("type") == "assistant" or msg.get("role") == "assistant":
            content = msg.get("content")
            if isinstance(content, list):
                chunk = []
                for c in content:
                    if c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        cmd = inp.get("command") or ""
                        for rx in (OPEN_RE, OPEN_BARE_RE):
                            for m in rx.finditer(cmd):
                                opened.add(m.group("rel"))
                    elif c.get("type") == "text":
                        chunk.append(c.get("text") or "")
                if chunk:
                    texts.append("\n".join(chunk))
            elif isinstance(content, str):
                texts.append(content)
    return opened, (texts[-1] if texts else "")


def cited_paths(text):
    out = []
    for m in CITED_RE.finditer(text or ""):
        tok = m.group(0).strip().strip("`'\"()[],.")
        if len(tok) > 6:
            out.append(tok)
    return out


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return 0

    session_id = str(payload.get("session_id") or "nosession")
    transcript = payload.get("transcript_path")
    stop_hook_active = bool(payload.get("stop_hook_active"))

    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    marker = MARKER_DIR / ("%s.blocked" % re.sub(r"[^A-Za-z0-9_.-]", "_", session_id))

    decision = {}
    reason = None
    unopened = []

    # Ask at most once per session, and never on a re-entry the hook caused.
    if not stop_hook_active and not marker.exists():
        opened, final = read_transcript(transcript)
        for c in cited_paths(final):
            if not any(same_path(c, o) for o in opened):
                unopened.append(c)
        if unopened:
            marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
            reason = REASON.format(path=tail2(unopened[0]))
            decision = {"decision": "block", "reason": reason}

    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "session": session_id[:40],
                "stop_hook_active": stop_hook_active,
                "n_cited_unopened": len(unopened),
                "blocked": bool(reason),
            }) + "\n")
    except Exception:
        pass

    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
