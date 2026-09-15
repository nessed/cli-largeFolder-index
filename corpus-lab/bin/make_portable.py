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

```
.venv\\Scripts\\python.exe bin\\c_selftest.py --db .\\artefacts\\pages.db --shelf .\\artefacts\\shelf\\shelf.db
```

## Remove it

```
.venv\\Scripts\\python.exe bin\\setup_folder.py uninstall --folder <your folder>
```

Add `--purge --artefacts .\\artefacts` to delete the index as well.
"""


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
