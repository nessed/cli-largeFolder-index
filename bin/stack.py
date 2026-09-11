#!/usr/bin/env python
"""stack.py - install / remove a candidate stack's delivery layer in a corpus root.

Writes ONLY into <corpus>/.claude/settings.json and <corpus>/CLAUDE.md, records
whatever was there before, and restores exactly on teardown. Nothing else in the
corpus is ever touched.

Stacks:
  s1_policy    CLAUDE.md tells the agent the index exists. No enforcement.
               -> tests whether instructions alone are enough. (Round-one reports
                  assumed CLAUDE.md + scripts might do; issue #47565 says otherwise.)
  s2_hook      PreToolUse hook denies Grep/Glob AND Bash crawls, redirecting to the
               index. Plus the same CLAUDE.md.
               -> tests whether hard enforcement holds, and what it costs.
"""
import argparse, json, os, shutil, sys
from pathlib import Path

LAB = Path(r"C:\Users\Ali\Desktop\corpus-lab")
HOOK = LAB / "bin" / "hook_frontdoor.py"
SEARCH = LAB / "bin" / "corpus_search.py"
PY = sys.executable

CLAUDE_MD = """# Corpus retrieval policy

This repository's .gitignore excludes every document directory, so the built-in
Grep and Glob see 495 of 217,527 files and return "No files found" for material
that is present. They fail silently. Do not rely on them to find research material.

A page-level index of the whole corpus (including gitignored directories, PDFs and
DOCX) is available. Use it first:

    python "{search}" "search terms"          # ranked page hits
    python "{search}" --exact "literal"       # exact phrase
    python "{search}" --page <path> <n>       # read one page
    python "{search}" --coverage              # what is and is not indexed

Cite file path + page_index for every claim. Before saying something is absent,
run --coverage and say what was not searched.
"""


def settings_for(stack):
    if stack != "s2_hook":
        return None
    return {"hooks": {"PreToolUse": [{
        "matcher": "Grep|Glob|Bash",
        "hooks": [{"type": "command",
                   "command": f'"{PY}" "{HOOK}"'}]}]}}


def setup(corpus, stack, db):
    root = Path(corpus)
    cdir = root / ".claude"
    cdir.mkdir(exist_ok=True)
    state = {"stack": stack, "corpus": str(root), "created": [], "backed_up": []}

    md = root / "CLAUDE.md"
    if md.exists():
        shutil.copy2(md, LAB / "99_scratch" / "CLAUDE.md.bak")
        state["backed_up"].append(str(md))
    else:
        state["created"].append(str(md))
    md.write_text(CLAUDE_MD.format(search=SEARCH), encoding="utf-8")

    sj = cdir / "settings.json"
    cfg = settings_for(stack)
    if cfg:
        if sj.exists():
            shutil.copy2(sj, LAB / "99_scratch" / "settings.json.bak")
            state["backed_up"].append(str(sj))
        else:
            state["created"].append(str(sj))
        sj.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    (LAB / "99_scratch" / "stack_state.json").write_text(
        json.dumps(state, indent=1), encoding="utf-8")
    print(f"INSTALLED {stack} in {root}")
    print(f"  CLAUDE.md written; settings.json {'written' if cfg else 'not used'}")
    print(f"  CORPUS_DB should be set to: {db}")


def teardown():
    sf = LAB / "99_scratch" / "stack_state.json"
    if not sf.exists():
        print("no stack installed"); return
    state = json.loads(sf.read_text(encoding="utf-8"))
    for p in state["created"]:
        if Path(p).exists():
            Path(p).unlink()
            print(f"  removed {p}")
    for p in state["backed_up"]:
        name = Path(p).name + ".bak"
        bak = LAB / "99_scratch" / name
        if bak.exists():
            shutil.copy2(bak, p)
            print(f"  restored {p}")
    sf.unlink()
    print(f"REMOVED {state['stack']} from {state['corpus']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["setup", "teardown"])
    ap.add_argument("--corpus", default=r"C:\Users\Ali\Desktop\Projects\Code\ra-ship")
    ap.add_argument("--stack", default="s2_hook")
    ap.add_argument("--db", default=str(LAB / "02_stacks" / "s2_fts5" / "raship.db"))
    a = ap.parse_args()
    (LAB / "99_scratch").mkdir(exist_ok=True)
    if a.action == "setup":
        setup(a.corpus, a.stack, a.db)
    else:
        teardown()
