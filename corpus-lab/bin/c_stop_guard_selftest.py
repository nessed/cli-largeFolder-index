#!/usr/bin/env python
"""c_stop_guard_selftest.py -- 2026-09-16, Phase 2.2.

Tests the citation guard's BEHAVIOUR, not its installation. Four cases, each
driving the real hook as a subprocess with a synthetic transcript on stdin,
exactly as Claude Code would:

  1. an answer citing a path that was never opened  -> blocked once, with reason
  2. the same session stopping a second time        -> passes unconditionally
  3. an answer citing only paths that were opened   -> passes
  4. an answer citing nothing at all                -> passes

  python -u corpus-lab/bin/c_stop_guard_selftest.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

GUARD = str(L.BIN / "c_stop_guard.py")


def transcript(tmp, opens, final_text):
    """A stream-json transcript: some `open` tool calls, then a final answer."""
    lines = []
    for rel, page in opens:
        lines.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
            "content": [{"type": "tool_use", "name": "Bash", "input": {
                "command": 'py c_shelf.py open "%s" %d --slug s1' % (rel, page)}}]}}))
    lines.append(json.dumps({"type": "assistant", "message": {"role": "assistant",
        "content": [{"type": "text", "text": final_text}]}}))
    p = Path(tmp) / ("t%d.jsonl" % int(time.time() * 1000000))
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def run_guard(tpath, session_id, stop_hook_active=False, markers=None):
    env = dict(os.environ)
    if markers:
        env["STOP_GUARD_MARKERS"] = str(markers)
    payload = json.dumps({"session_id": session_id, "transcript_path": str(tpath),
                          "stop_hook_active": stop_hook_active})
    p = subprocess.run([sys.executable, GUARD], input=payload, capture_output=True,
                       text=True, errors="replace", env=env)
    try:
        return json.loads((p.stdout or "").strip() or "{}"), p.returncode
    except Exception:
        return {"_unparsable": (p.stdout or "")[:200]}, p.returncode


def main():
    tmp = tempfile.mkdtemp(prefix="stopguard_")
    markers = Path(tmp) / "markers"
    checks = []

    def chk(name, cond, **extra):
        checks.append(dict(check=name, **{"pass": bool(cond)}, **extra))

    OPENED = "some_dir/a_report.pdf"
    OTHER = "other_dir/never_opened.pdf"

    # 1. cites a path it never opened -> blocked once
    t1 = transcript(tmp, [(OPENED, 7)],
                    "The figure is 4321, from %s page 7 and also %s." % (OPENED, OTHER))
    d1, rc1 = run_guard(t1, "sess-A", markers=markers)
    chk("cited_unopened_blocked", d1.get("decision") == "block", rc=rc1,
        decision=d1.get("decision"))
    chk("block_reason_names_the_path",
        OTHER.split("/")[-1] in (d1.get("reason") or ""), reason=(d1.get("reason") or "")[:90])
    chk("block_reason_offers_both_remedies",
        "open that page" in (d1.get("reason") or "")
        and "remove the citation" in (d1.get("reason") or ""))

    # 2. same session stops again -> passes unconditionally (both routes)
    d2a, _ = run_guard(t1, "sess-A", markers=markers)
    chk("second_stop_passes_via_marker", d2a.get("decision") != "block",
        decision=d2a.get("decision"))
    d2b, _ = run_guard(t1, "sess-B", stop_hook_active=True, markers=markers)
    chk("stop_hook_active_passes", d2b.get("decision") != "block",
        decision=d2b.get("decision"))

    # 3. cites only what it opened -> passes
    t3 = transcript(tmp, [(OPENED, 7)], "The figure is 4321, from %s page 7." % OPENED)
    d3, _ = run_guard(t3, "sess-C", markers=markers)
    chk("cited_opened_passes", d3.get("decision") != "block", decision=d3.get("decision"))

    # 4. cites nothing -> passes
    t4 = transcript(tmp, [(OPENED, 7)],
                    "I could not find supporting evidence for this in the folder.")
    d4, _ = run_guard(t4, "sess-D", markers=markers)
    chk("no_citation_passes", d4.get("decision") != "block", decision=d4.get("decision"))

    # 5. the guard never rewrites an answer
    chk("guard_returns_only_a_decision",
        set(d1.keys()) <= {"decision", "reason"} and set(d3.keys()) <= set())

    # 6. exit code is always 0 -- a hook that errors must not break a session
    chk("exit_code_zero", rc1 == 0, rc=rc1)

    ok = all(c["pass"] for c in checks)
    rec = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "n_checks": len(checks), "n_passed": sum(1 for c in checks if c["pass"]),
           "all_pass": ok, "checks": checks}
    (L.STATE / "c_stop_guard_selftest.json").write_text(json.dumps(rec, indent=1),
                                                        encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "checks"}, indent=1))
    for c in checks:
        if not c["pass"]:
            print("FAILED: %s  %s" % (c["check"],
                                      {k: v for k, v in c.items()
                                       if k not in ("check", "pass")}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
