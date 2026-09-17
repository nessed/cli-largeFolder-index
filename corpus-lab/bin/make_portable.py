#!/usr/bin/env python
"""make_portable.py - build the package another machine can install from.

Plan E Phase 3.1. Before tonight the "portable" installer ran scripts out of the
development repo, wrote its artefacts into the development repo, and built the
shelf with the EXPERIMENTAL v2 builder -- the one that failed Gate S -- while
production and the demo ran v1. It had never been run from a copy. So it was not
portable, and what it built was not what had been measured.

This writes `dist/retrieval-portable-<commit7>/`:

  bin/                       an explicit allowlist, plus whatever those import
  requirements-portable.txt  the runtime closure, pinned
  INSTALL.md                 path-free instructions
  PACKAGE_MANIFEST.json      commit, branch, build time, sha256 per file,
                             the allowlist, default_builder: v1

It carries no `02_stacks`, no `_private`, no `state`, no `99_scratch`. Gate R3
greps the result for `C:\\Users` and `Desktop` and fails on a hit.

The allowlist is a starting point, not the answer: `--closure` follows the
imports of the listed modules and adds what they actually need, so a missing
dependency is found here rather than in the clean room.

  python make_portable.py [--out dist] [--dry-run]
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# Plan E 3.1's allowlist, verbatim. Anything these import is added by closure.
ALLOWLIST = [
    "labpaths.py", "scoring.py", "index_build.py", "c_shelf.py",
    "c_shelf_build.py", "c_shelf_build_v2.py", "c_caption_index.py",
    "c_caption_embed.py", "c_stack.py", "c_stop_guard.py", "c_selftest.py",
    # c_selftest.py shells out to this one and reads the JSON it writes. Gate R1
    # found its absence: stop_guard_behaviour came back {pass: false, n_checks:
    # null} in the clean room, because the script simply was not there.
    "c_stop_guard_selftest.py",
    "setup_folder.py", "run_record.py", "build_manifest.py",
]

# Never packaged, whatever the closure says: these read or write the answer key,
# the recorded results, or the development lab's own state.
NEVER = {
    "c_score_live.py", "c_score_live_v2.py", "c_score_live_v3.py",
    "c_key_v2_build.py", "c_live_battery.py", "ask.py", "run_harness.py",
    "checksums.py", "plog.py", "p9_checkpoint.py", "docs_check.py",
    # Opens the answer key. c_shelf used to import one constant from it; that
    # constant now lives in trajectory_filler.py (Plan E 3.1), so the package
    # can be built without it.
    "c_offline_gate.py",
}

FORBIDDEN_STRINGS = [r"C:\\Users", r"Desktop"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", str(L.RETRIEVAL_LAB)] + list(a),
                          capture_output=True, text=True, timeout=60).stdout.strip()


def local_imports(path):
    """Module names this file imports that live beside it in bin/."""
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                names.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module.split(".")[0])
    return {n for n in names if (L.BIN / ("%s.py" % n)).exists()}


def closure(seed):
    """Everything the seed modules need, transitively, minus NEVER."""
    out, stack, skipped = set(), list(seed), set()
    while stack:
        f = stack.pop()
        if f in out:
            continue
        if f in NEVER:
            skipped.add(f)
            continue
        p = L.BIN / f
        if not p.exists():
            continue
        out.add(f)
        for mod in local_imports(p):
            stack.append("%s.py" % mod)
    return sorted(out), sorted(skipped)


def check_forbidden(root):
    """Gate R3's grep, run here so the package never ships with a dev path."""
    hits = []
    pats = [re.compile(x) for x in FORBIDDEN_STRINGS]
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for rx in pats:
                if rx.search(line):
                    hits.append("%s:%d: %s" % (p.relative_to(root).as_posix(),
                                               i, line.strip()[:110]))
    return hits


INSTALL_MD = """# Install

This package indexes a folder of documents and then lets you ask questions about
it in plain English, with every answer citing the page it came from.

## The short way

Copy `CLAUDE_ROOT.md` to `CLAUDE.md` in the folder that holds both this package
and your documents, open Claude Code there, and say **initialize**. It reads
`INITIALIZE.md` -- this same procedure, addressed to it -- and does everything
below for you, including telling you what to install if something is missing.

The rest of this document is for doing it by hand.

## What you need

- Python 3.11
- Claude Code on the PATH
- about 1 GB of free disk per 2,000 documents
- an internet connection for the **first** run only, to fetch the embedding model

## Install

From this directory:

```
python -m venv .venv
.venv\\Scripts\\pip install -r requirements-portable.txt
.venv\\Scripts\\python.exe bin\\setup_folder.py doctor
```

`doctor` prints one line per prerequisite and exits non-zero if anything is
missing. Fix what it names before going on.

## Index a folder

```
.venv\\Scripts\\python.exe bin\\setup_folder.py install --folder <your folder> --artefacts .\\artefacts --seed-env
```

The folder itself is left read-only apart from two files the tool owns,
`CLAUDE.md` and `.claude/settings.json`; `uninstall` removes exactly those. Every
index artefact goes under `--artefacts`.

This builds the **v1 shelf** -- the one every measured number in the report rests
on. `--builder v2` selects an experimental builder that failed its acceptance gate
on 2026-09-15; it prints a warning and stamps `builder: v2 (experimental)` into
the manifest, so it cannot be used by accident.

An interrupted install is resumed by re-running the identical command.

## Ask it something

```
cd <your folder>
claude --model claude-opus-5
```

or, without leaving this directory:

```
.venv\\Scripts\\python.exe bin\\setup_folder.py ask --folder <your folder> "<question>"
```

## Check the build

The artefacts directory gets three files:

- `build_manifest.json` -- versions, counts, hashes, timings
- `BUILD_REPORT.md` -- the same in one page of plain English
- `canonical_export.json` -- the logical content, sorted, with timestamps removed

Two installs of the same folder produce the same `canonical_export.json` hash.
Raw database files will differ between installs -- they carry timestamps and
filesystem walk order -- and `BUILD_REPORT.md` explains which fields those are.

`--expect-pages 0` says "do not check the page count". Leave it in: without
it the self-test compares your folder against a fixed reference corpus and
reports a failure that is not one.

```
.venv\\Scripts\\python.exe bin\\c_selftest.py --db .\\artefacts\\pages.db --shelf .\\artefacts\\shelf\\shelf.db --expect-pages 0
```

## Remove it

```
.venv\\Scripts\\python.exe bin\\setup_folder.py uninstall --folder <your folder>
```

Add `--purge --artefacts .\\artefacts` to delete the index as well.
"""


# Plan F: the package is handed to someone who has never used a terminal.
# INSTALL.md is for a person doing it by hand; INITIALIZE.md is the same
# procedure addressed to Claude Code, so that `initialize` in a fresh session
# is enough. CLAUDE.md is the pointer that belongs at the distribution root,
# beside `engine` and the documents folder -- that is the directory the
# recipient opens, and Claude Code reads CLAUDE.md from there.
INITIALIZE_MD = '# Initialize\n\nYou are Claude Code. Someone opened a terminal in this folder, started you, and\ntyped **initialize**. They may never have used a terminal before. Do the whole\nsetup yourself, explain it in plain English as you go, and stop and ask when\nsomething is genuinely missing from their machine.\n\nThis document is the whole procedure. You do not need anything outside this\nfolder, and you must not go looking for any.\n\n## What this folder is\n\n```\n<this folder>\n  engine\\          the tool. Never edit anything under engine\\bin.\n  <documents>\\     the folder of research documents. It is the one that is not `engine`.\n  INSTALL.md          the same procedure written for a person doing it by hand.\n```\n\nFind the documents folder first: list this directory, and take the one directory\nthat is not `engine` and not a dot-folder. If there is more than one candidate,\nask which one. Call it `<docs>` below and use its real name in every command.\n\n## Step 0 - tell them what is about to happen\n\nBefore you run anything, say roughly this, in your own words:\n\n> I\'m going to set up a Python environment inside `engine`, then read every\n> document in `<docs>` once and build a searchable index of it. The reading pass\n> is the slow part: roughly three to six minutes per thousand documents, and\n> it uses most of the CPU while it runs. Nothing outside this folder is\n> touched, and nothing in `<docs>` is modified except two small files the\n> tool owns. Say stop at any point and nothing is lost -- rerunning resumes.\n\nThen go, without waiting for permission. They already said initialize.\n\n## Red text is not an error\n\nPowerShell paints everything a program writes to stderr red, and prints a block\nheaded `NativeCommandError` around it. Progress messages, pip\'s "a new release of\npip is available" notice and the index pass\'s *building page-range cache,\none-time* line all arrive that way. It looks exactly like a crash and it is not\none.\n\nJudge every command in this document by its exit code, never by the colour. When\na red block appears, say what it actually is before the person watching decides\nthe tool is broken.\n\n## Step 1 - check Python\n\n```\npython --version\n```\n\nNeeds **3.11 or newer**. If the command is not found, or the version is older,\nstop and tell them: install Python 3.11+ from python.org, tick "Add python.exe to\nPATH" in the installer, close the terminal, open a new one, and run you again.\nDo not try to install Python for them.\n\n## Step 2 - build the environment\n\n```\npython -m venv engine\\.venv\nengine\\.venv\\Scripts\\python.exe -m pip install -r engine\\requirements-portable.txt\n```\n\nThe pip step downloads roughly 200 MB and takes a few minutes on a normal\nconnection. It needs internet. If it fails with a network or proxy error, show\nthem the last few lines and ask whether they are behind a corporate proxy.\n\n## Step 3 - check the prerequisites\n\n```\nengine\\.venv\\Scripts\\python.exe engine\\bin\\setup_folder.py doctor\n```\n\nOne line per prerequisite. Read them all before reacting.\n\n- **pdftotext FAIL** -- this is the one that actually stops people. The tool\n  needs `pdftotext.exe`, which ships inside Git for Windows. Tell them to install\n  Git for Windows from git-scm.com, accepting every default, then close the\n  terminal, open a new one in this folder and run you again. If they already have\n  poppler somewhere, you can instead set `PDFTOTEXT_EXE` to its `pdftotext.exe`\n  and rerun `doctor`.\n- **claude_exe FAIL** -- only matters for the `ask` shortcut in step 6. If they\n  are talking to you right now, Claude Code is installed; set `CLAUDE_CMD` to the\n  `claude.exe` you can find, or just skip it and use the interactive route.\n- **embedding_model ... NOT found** -- not a failure. It says the first index\n  build will download a 130 MB model, so that build needs internet.\n- **free_disk FAIL** -- they need about 1 GB per 2,000 documents. Say the number.\n\nDo not go on to step 4 while `pdftotext` is failing. Everything will index as\n`failed_parser` and the result will look like the tool is broken.\n\n## Step 4 - read the documents\n\nPick the worker count from their machine rather than taking the default:\n\n```\npython -c "import os; print(max(2, min(12, (os.cpu_count() or 4) - 2)))"\n```\n\nThen, with `<docs>` and `<N>` filled in:\n\n```\nengine\\.venv\\Scripts\\python.exe engine\\bin\\setup_folder.py install --folder <docs> --artefacts engine\\artefacts --seed-env --workers <N>\n```\n\nThis is the long one. Tell them the estimate before you start it and let it run.\n\n**Things you will see that are not errors.** Say so plainly if they appear:\n\n- Red `NativeCommandError` blocks, as above. The index pass prints several.\n- Files counted as `failed_parser` or `excluded`. A handful in a large folder is\n  normal -- scanned images with no text layer, zero-byte files, archives. The\n  final report gives the counts. Only worry if most of the folder failed, which\n  almost always means `pdftotext` is missing.\n- An install that stops halfway. Rerun the identical command; it resumes.\n\nWhen it finishes, tell them how many documents were read, how many pages that\ncame to, how long it took, and how many files were skipped and why.\n\n## Step 5 - check the build\n\n```\nengine\\.venv\\Scripts\\python.exe engine\\bin\\c_selftest.py --db engine\\artefacts\\pages.db --shelf engine\\artefacts\\shelf\\shelf.db --expect-pages 0\n```\n\n`--expect-pages 0` means "do not compare this folder against a fixed reference\ncount" and must stay. Report the pass count as one line. If any check fails, show\nthe failing lines verbatim and stop -- do not try to repair the index.\n\n## Step 6 - hand it over\n\nSay, in your own words:\n\n> It\'s ready. To ask it something, open a terminal in the `<docs>` folder and\n> start Claude Code there:\n>\n>     cd <docs>\n>     claude --model claude-opus-5\n>\n> Then ask in plain English -- "how has spending on X changed over the last ten\n> years?" An answer usually takes one to three minutes, because it is opening\n> real pages before it replies. Every number comes with a `Sources` line naming\n> the file and page it came from, and when the folder does not contain the\n> answer, it says so instead of guessing. The first few commands will ask your\n> permission to run; approving them is expected.\n>\n> One thing to know: the answers are only as good as this folder. A `Sources`\n> line is a claim you can check in seconds -- open the file at that page. Do\n> check a few early on.\n\nIf they would rather not leave this terminal, the same question can be asked with:\n\n```\nengine\\.venv\\Scripts\\python.exe engine\\bin\\setup_folder.py ask --folder <docs> "<their question>"\n```\n\n## Rules for you while doing this\n\n- **Do not edit anything under `engine\\bin`.** If a step fails, report it. A\n  patched engine is worse than a broken one, because nobody knows what it is any\n  more.\n- **Do not index anything outside this folder**, and do not read documents to\n  answer questions during setup. Setup is setup.\n- **Do not claim a step worked because it printed something.** Check exit codes.\n- **Do not hide a failure in a summary.** If step 4 skipped 300 files, say 300.\n- If the same command fails twice for the same reason, stop and ask them. Do not\n  try a third variation.\n\n## To remove it\n\n```\nengine\\.venv\\Scripts\\python.exe engine\\bin\\setup_folder.py uninstall --folder <docs> --purge --artefacts engine\\artefacts\n```\n\nThat deletes the two files the tool wrote into `<docs>` and the whole index.\nTheir documents are untouched.\n'

CLAUDE_DROPIN_MD = '# This folder\n\nA folder of research documents, and a tool that can answer questions about them\nwith the page it got each answer from.\n\n**Nothing is set up yet.** To set it up, tell Claude Code:\n\n> initialize\n\nand follow along. The procedure is `engine/INITIALIZE.md` -- read that file and\ndo exactly what it says, start to finish, before anything else. It is written for\nyou, it expects the person watching to be new to all of this, and it is the only\ninstruction you need.\n\nIf you are a person reading this and would rather do it by hand, `engine/INSTALL.md`\nis the same procedure written for you.\n'


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv[1:])

    commit = git("rev-parse", "HEAD")
    files, skipped = closure(ALLOWLIST)
    missing = [f for f in ALLOWLIST if not (L.BIN / f).exists()]
    if missing:
        raise SystemExit("allowlisted file(s) absent from bin/: %s" % ", ".join(missing))

    name = "retrieval-portable-%s" % (commit[:7] or "nocommit")
    root = (L.RETRIEVAL_LAB / a.out / name)

    print("package : %s" % name)
    print("files   : %d (%d allowlisted + %d pulled in by imports)"
          % (len(files), len(ALLOWLIST), len(files) - len(ALLOWLIST)))
    extra = sorted(set(files) - set(ALLOWLIST))
    if extra:
        print("  closure added: %s" % ", ".join(extra))
    if skipped:
        print("  refused (NEVER list -- key, results or dev state): %s"
              % ", ".join(skipped))
    if a.dry_run:
        print("--dry-run: nothing written")
        return 0

    if root.exists():
        shutil.rmtree(root)
    (root / "bin").mkdir(parents=True)

    for f in files:
        shutil.copy2(L.BIN / f, root / "bin" / f)
    shutil.copy2(L.CORPUS_LAB / "requirements-portable.txt",
                 root / "requirements-portable.txt")
    (root / "INSTALL.md").write_text(INSTALL_MD, encoding="utf-8")
    (root / "INITIALIZE.md").write_text(INITIALIZE_MD, encoding="utf-8")
    (root / "CLAUDE_ROOT.md").write_text(CLAUDE_DROPIN_MD, encoding="utf-8")

    manifest = {
        "schema": "package_manifest/1",
        "name": name,
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package_commit": commit,
        "package_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "package_dirty": bool([x for x in git("status", "--short").splitlines()
                               if x.strip()]),
        "default_builder": "v1",
        "builder_note": ("v1 is the builder every measured number rests on. v2 is "
                         "experimental, failed Gate S 2026-09-15, and is reachable "
                         "only via --builder v2, which warns and stamps the manifest."),
        "allowlist": ALLOWLIST,
        "closure_added": extra,
        "refused": skipped,
        "excluded_dirs": ["02_stacks", "_private", "state", "99_scratch",
                          "experiments", "tests"],
        "files_sha256": {},
    }
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "PACKAGE_MANIFEST.json":
            manifest["files_sha256"][p.relative_to(root).as_posix()] = sha256(p)

    hits = check_forbidden(root)
    manifest["forbidden_string_hits"] = hits
    (root / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8")

    print("\nwrote %s" % root)
    print("  %d files hashed into PACKAGE_MANIFEST.json"
          % len(manifest["files_sha256"]))
    if hits:
        print("\nFORBIDDEN STRINGS FOUND (%d) -- Gate R3 would fail:" % len(hits))
        for h in hits[:20]:
            print("   " + h)
        return 1
    print("  grep for %s: clean" % " / ".join(FORBIDDEN_STRINGS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
