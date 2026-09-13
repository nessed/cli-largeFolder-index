#!/usr/bin/env python
"""evidence_v1.hooks -- PreToolUse/SessionStart/UserPromptSubmit/Stop hook
logic. Runtime code, no labpaths import.

PreToolUse denies everything except an EXACT, fully-parsed invocation of the
installed evidence.py CLI with a known subcommand and its own permitted flags
-- no shell operators, redirects, substitutions, environment prefixes, extra
commands, or unknown options -- plus Read, but ONLY for this request's own
crop/page image outputs. Parsing a command string that contains no shell
metacharacters and tokenizing it with shlex is not, by itself, a sandbox --
rule 2's own warning applies -- so this still runs inside Claude Code's
existing PreToolUse deny/allow plumbing, not as a standalone execution
boundary.
"""
import json
import re
import shlex
from pathlib import Path

# Rule 2 of BUILD_PROMPT.md: no shell operators, redirects, substitutions,
# environment prefixes. Reject the raw string outright if any of these
# appear anywhere, even inside what looks like a quoted argument -- this CLI
# never legitimately needs any of them.
FORBIDDEN_CHARS = set(";|&$`<>\n\r")
FORBIDDEN_SUBSTRINGS = ("&&", "||", "$(", "`", ">>", "<<", "2>", "1>")

SUBCOMMANDS = {
    "doctor": {"--root"},
    "install": {"--root", "--time-budget-s", "--workers"},
    "prepare": {"--root", "--question"},
    "search": {"--request", "--concept", "--entity", "--period", "--kind"},
    "read": {"--request", "--candidates"},
    "compose": {"--request", "--evidence", "--operation"},
    "explain": {"--request"},
    "open": {"--request", "--evidence"},
    "uninstall": {"--root"},
}


def _contains_forbidden(raw):
    if any(ch in FORBIDDEN_CHARS for ch in raw):
        return True
    return any(sub in raw for sub in FORBIDDEN_SUBSTRINGS)


def validate_bash_command(raw_command, python_exe, cli_path):
    """Returns (allowed: bool, reason: str)."""
    if _contains_forbidden(raw_command):
        return False, "forbidden shell metacharacter or operator in command string"
    try:
        tokens = shlex.split(raw_command, posix=True)
    except ValueError as e:
        return False, "unparseable command: {}".format(e)
    if len(tokens) < 3:
        return False, "too few tokens for a valid evidence.py invocation"

    norm_py = str(Path(python_exe)).replace("\\", "/").lower()
    norm_cli = str(Path(cli_path)).replace("\\", "/").lower()
    tok0 = str(Path(tokens[0])).replace("\\", "/").lower()
    tok1 = str(Path(tokens[1])).replace("\\", "/").lower()
    if tok0 != norm_py:
        return False, "first token is not the exact installed python.exe"
    if tok1 != norm_cli:
        return False, "second token is not the exact installed evidence.py path"

    subcmd = tokens[2]
    if subcmd not in SUBCOMMANDS:
        return False, "unknown subcommand: {!r}".format(subcmd)

    allowed_flags = SUBCOMMANDS[subcmd]
    i = 3
    seen_flags = set()
    while i < len(tokens):
        flag = tokens[i]
        if not flag.startswith("--"):
            return False, "unexpected bare argument (not a --flag): {!r}".format(flag)
        if flag not in allowed_flags:
            return False, "flag {!r} is not permitted for subcommand {!r}".format(flag, subcmd)
        if flag in seen_flags:
            return False, "flag {!r} repeated".format(flag)
        seen_flags.add(flag)
        if i + 1 >= len(tokens):
            return False, "flag {!r} missing a value".format(flag)
        value = tokens[i + 1]
        ok, reason = _validate_flag_value(flag, value)
        if not ok:
            return False, reason
        i += 2

    return True, "ok"


_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9 _\-./:\\]+$")
_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")
_CANDIDATES_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}(,[A-Za-z0-9_\-]{1,128}){0,11}$")
_KIND_RE = re.compile(r"^(lookup|trajectory|compare|mean_compare|relationship|status|identifier)$")
_OPERATION_RE = re.compile(r"^(table|trajectory|compare|mean_compare|quote|not_found)$")


def _validate_flag_value(flag, value):
    if ".." in value or value.startswith("~"):
        return False, "path traversal pattern in value for {}: {!r}".format(flag, value)
    if flag in ("--root",):
        if not _SAFE_VALUE_RE.match(value):
            return False, "unsafe characters in --root value"
        return True, "ok"
    if flag in ("--request",):
        return (True, "ok") if _ID_RE.match(value) else (False, "malformed --request id")
    if flag == "--candidates":
        if not _CANDIDATES_RE.match(value):
            return False, "malformed --candidates (max 12, [A-Za-z0-9_-] ids only)"
        return True, "ok"
    if flag == "--evidence":
        if not _CANDIDATES_RE.match(value):
            return False, "malformed --evidence id list"
        return True, "ok"
    if flag == "--kind":
        return (True, "ok") if _KIND_RE.match(value) else (False, "unknown --kind value")
    if flag == "--operation":
        return (True, "ok") if _OPERATION_RE.match(value) else (False, "unknown --operation value")
    if flag in ("--concept", "--entity"):
        if len(value) > 120 or re.search(r"[;&|$`<>]", value):
            return False, "concept/entity value too long or unsafe"
        return True, "ok"
    if flag == "--period":
        if not re.match(r"^(unspecified|\d{4}-\d{2}(:\d{4}-\d{2})?)$", value):
            return False, "malformed --period (expected FY, FY:FY, or unspecified)"
        return True, "ok"
    if flag in ("--time-budget-s",):
        try:
            float(value)
        except ValueError:
            return False, "non-numeric --time-budget-s"
        return True, "ok"
    if flag == "--workers":
        return (True, "ok") if value.isdigit() else (False, "non-numeric --workers")
    if flag == "--question":
        if len(value) > 2000 or re.search(r"[;&|`]", value):
            return False, "question value too long or unsafe"
        return True, "ok"
    return True, "ok"


def validate_read(path, request_id, runtime_dir):
    """Read is permitted ONLY for this request's own crop/page image outputs
    under the runtime dir -- never a research-root path, never another
    request's output, never any _private/builder path."""
    p = Path(path)
    try:
        resolved = p.resolve()
    except OSError:
        return False, "unresolvable path"
    runtime_dir = Path(runtime_dir).resolve()
    allowed_dirs = [runtime_dir / "crops", runtime_dir / "pages"]
    for d in allowed_dirs:
        try:
            resolved.relative_to(d)
        except ValueError:
            continue
        if request_id and request_id not in resolved.name and request_id not in str(resolved):
            return False, "path does not belong to the active request"
        return True, "ok"
    return False, "Read is only permitted for this request's own crop/page outputs"


def pretooluse_decision(hook_input, python_exe, cli_path, active_request_id, runtime_dir):
    tool_name = hook_input.get("tool_name")
    tool_input = hook_input.get("tool_input", {})
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        ok, reason = validate_bash_command(cmd, python_exe, cli_path)
        return {"permissionDecision": "allow" if ok else "deny", "reason": reason}
    if tool_name == "Read":
        ok, reason = validate_read(tool_input.get("file_path", ""), active_request_id, runtime_dir)
        return {"permissionDecision": "allow" if ok else "deny", "reason": reason}
    if tool_name in ("Grep", "Glob", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch",
                      "Agent", "Task"):
        return {"permissionDecision": "deny",
                "reason": "evidence requests must go through evidence.py; {} is disabled "
                          "while a request is active".format(tool_name)}
    return {"permissionDecision": "deny", "reason": "tool not recognized by evidence_v1 policy"}


def main_pretooluse():
    import os
    import sys
    raw = sys.stdin.read()
    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"permissionDecision": "deny", "reason": "malformed hook input"}))
        return 0
    python_exe = os.environ.get("EVIDENCE_V1_PYTHON", sys.executable)
    cli_path = os.environ.get("EVIDENCE_V1_CLI", "")
    request_id = os.environ.get("EVIDENCE_V1_ACTIVE_REQUEST", "")
    runtime_dir = os.environ.get("EVIDENCE_V1_RUNTIME_DIR", "")
    decision = pretooluse_decision(hook_input, python_exe, cli_path, request_id, runtime_dir)
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main_pretooluse())
