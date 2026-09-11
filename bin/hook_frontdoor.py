#!/usr/bin/env python
"""PreToolUse hook: make the corpus index the unmistakable front door.

Denies the built-in Grep/Glob AND the Bash escape hatches (grep/rg/find/ls -R),
because the measured baseline showed the model routes around a Grep-only deny
within a single turn. Denies built-ins deliberately -- per Claude Code issue
#33106 a deny is NOT enforced against MCP tools, so the only workable direction
is: block the built-ins, let the model fall through to the index.

Exit 0 with a JSON permissionDecision. Logs every decision so enforcement is provable.
"""
import json, os, re, sys, time
from pathlib import Path

LOG = Path(os.environ.get("HOOK_LOG",
           r"C:\Users\Ali\Desktop\corpus-lab\03_runs\hooks\frontdoor.log"))
LOG.parent.mkdir(parents=True, exist_ok=True)
SEARCH = r"C:\Users\Ali\Desktop\corpus-lab\bin\corpus_search.py"
PY = sys.executable

# Bash commands that are a corpus crawl in disguise.
CRAWL = re.compile(
    r"(^|[\s|;&])(grep|egrep|fgrep|rg|ag|ack|find|fd)\b"
    r"|ls\s+-[a-zA-Z]*R"
    r"|Get-ChildItem\s+.*-Recurse"
    r"|Select-String",
    re.I)

REDIRECT = (
    "The built-in {tool} is disabled in this corpus and you must not retry it.\n\n"
    "WHY: this repository's .gitignore excludes every document directory, so "
    "gitignore-aware search sees 495 of 217,527 files (0.2%) and returns "
    "'No files found' for material that is present. It fails silently.\n\n"
    "USE THIS INSTEAD (Bash):\n"
    '  python "{search}" "your search terms"\n'
    '  python "{search}" --exact "literal phrase"\n'
    '  python "{search}" --page <relative/path> <page_index>\n'
    '  python "{search}" --coverage\n\n'
    "It searches a page-level index of the whole corpus including gitignored "
    "directories, PDFs and DOCX, returns file+page addresses, and prints a receipt "
    "saying what was and was not searched."
)


def decide(tool, inp):
    if tool in ("Grep", "Glob"):
        return "deny", REDIRECT.format(tool=tool, search=SEARCH)
    if tool == "Bash":
        cmd = inp.get("command", "") or ""
        if SEARCH.lower() in cmd.lower() or "corpus_search" in cmd.lower():
            return "allow", "corpus index query - permitted"
        if CRAWL.search(cmd):
            return "deny", REDIRECT.format(tool="filesystem crawl via Bash", search=SEARCH)
    return None, None


def main():
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw)
    except Exception:
        print("{}"); return
    tool = ev.get("tool_name") or ev.get("toolName") or ""
    inp = ev.get("tool_input") or ev.get("toolInput") or {}
    decision, reason = decide(tool, inp)

    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": time.strftime("%H:%M:%S"), "tool": tool,
                             "decision": decision,
                             "input": str(inp)[:400]}, ensure_ascii=False) + "\n")

    if decision == "deny":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
            "additionalContext": reason}}))
    else:
        print("{}")


if __name__ == "__main__":
    main()
