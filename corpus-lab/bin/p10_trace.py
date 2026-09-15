#!/usr/bin/env python
"""p10_trace.py - Gate R3: prove the install reads nothing from the dev repo.

Plan E Phase 3.5. `labpaths.py` resolves its root from `__file__`, so a copied
`bin/` SHOULD work standalone -- but "should" is the word that made this gate
necessary. The only way to know is to record every path the install opens.

A `sitecustomize.py` is written into the clean venv, so every python process it
launches -- the installer and every child it spawns -- inherits the hooks before
any lab code runs. It wraps `builtins.open`, `io.open`, `sqlite3.connect`,
`os.scandir` and `os.listdir`, and appends every absolute path to `reads.log`.

  python p10_trace.py --room A --corpus <rung>

Writes <room>/reads.log and <room>/trace.json.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import p10_cleanroom as CR  # noqa: E402

SITECUSTOMIZE = '''"""Gate R3 read tracer. Written by p10_trace.py; not part of the package.

Every python process started from this venv inherits it, which is the point:
the installer spawns children, and a tracer that only saw the parent would miss
exactly the reads that matter.

Two things this has to get right, both learned the hard way:

  * `_note` must use the SAVED original open. Using the module-global `open`
    means calling the wrapper from inside the wrapper, which recurses into the
    lock it is already holding and hangs the whole install.
  * one file-open per traced open is not a tracer. An indexing run makes
    hundreds of thousands of them, so lines are buffered and flushed at exit.
"""
import atexit
import builtins
import io
import os
import sqlite3
import threading

_LOG = os.environ.get("P10_READS_LOG")
_lock = threading.Lock()
_local = threading.local()
_buf = []
_open = builtins.open          # saved BEFORE anything is replaced


def _flush():
    if not _LOG or not _buf:
        return
    with _lock:
        lines, _buf[:] = list(_buf), []
    try:
        with _open(_LOG, "a", encoding="utf-8", errors="replace") as fh:
            fh.writelines(lines)
    except Exception:
        pass


atexit.register(_flush)


def _note(kind, path):
    if not _LOG or getattr(_local, "busy", False):
        return
    _local.busy = True
    try:
        try:
            p = os.path.abspath(str(path))
        except Exception:
            return
        _buf.append("%s\\t%s\\n" % (kind, p))
        if len(_buf) >= 2000:
            _flush()
    finally:
        _local.busy = False


def _traced_open(file, *a, **k):
    if not isinstance(file, int):
        _note("open", file)
    return _open(file, *a, **k)


builtins.open = _traced_open
io.open = _traced_open

_connect = sqlite3.connect


def _traced_connect(database, *a, **k):
    _note("sqlite", database)
    return _connect(database, *a, **k)


sqlite3.connect = _traced_connect

_scandir = os.scandir


def _traced_scandir(path="."):
    _note("scandir", path)
    return _scandir(path)


os.scandir = _traced_scandir

_listdir = os.listdir


def _traced_listdir(path="."):
    _note("listdir", path)
    return _listdir(path)


os.listdir = _traced_listdir
'''


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", default="A")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv[1:])

    room = CR.room_dir(a.room)
    rec_p = room / "room.json"
    if not rec_p.exists():
        raise SystemExit("room %s has no room.json; build it first" % a.room)
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    pkg = room / "package"
    venv = pkg / ".venv"
    py = venv / "Scripts" / "python.exe"

    # find the venv's site-packages and drop the tracer in
    sp = None
    for c in (venv / "Lib" / "site-packages",):
        if c.exists():
            sp = c
    if sp is None:
        raise SystemExit("no site-packages in %s" % venv)
    (sp / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")

    reads_log = room / "reads.log"
    if reads_log.exists():
        reads_log.unlink()

    # a FRESH corpus copy, so the trace covers a real first install
    corpus = room / "corpus_trace"
    if corpus.exists():
        shutil.rmtree(corpus, ignore_errors=True)
    shutil.copytree(Path(a.corpus).resolve(), corpus)
    art = room / "artefacts_trace"
    if art.exists():
        shutil.rmtree(art, ignore_errors=True)

    env = CR.clean_env()
    env["P10_READS_LOG"] = str(reads_log)

    print("tracing install in room %s ..." % a.room, flush=True)
    t0 = time.time()
    rc, wall, out, err = CR._run(
        [str(py), "-u", str(pkg / "bin" / "setup_folder.py"), "install",
         "--folder", str(corpus), "--artefacts", str(art),
         "--seed-env", "--workers", str(a.workers)],
        pkg, env, log=room / "trace_install.log")
    print("install rc=%d in %.0fs" % (rc, wall), flush=True)

    dev_root = str(L.RETRIEVAL_LAB).lower()
    proj_root = str(Path.home() / ".claude" / "projects").lower()
    dev_key = "retrieval-lab"

    paths, dev_hits, proj_hits = set(), [], []
    if reads_log.exists():
        for line in reads_log.read_text(encoding="utf-8", errors="replace").splitlines():
            if "\t" not in line:
                continue
            kind, p = line.split("\t", 1)
            lp = p.lower()
            paths.add(p)
            if lp.startswith(dev_root):
                dev_hits.append("%s %s" % (kind, p))
            elif lp.startswith(proj_root) and dev_key in lp:
                proj_hits.append("%s %s" % (kind, p))

    trace = {
        "room": a.room,
        "traced_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "install_rc": rc,
        "install_s": round(wall, 1),
        "corpus": str(Path(a.corpus).resolve()),
        "dev_repo_root_checked": str(L.RETRIEVAL_LAB),
        "project_key_root_checked": str(Path.home() / ".claude" / "projects"),
        "n_paths": len(paths),
        "n_dev_repo_hits": len(dev_hits),
        "dev_repo_hits": dev_hits[:50],
        "n_project_key_hits": len(proj_hits),
        "project_key_hits": proj_hits[:50],
        "package_manifest": str(pkg / "PACKAGE_MANIFEST.json"),
    }
    (room / "trace.json").write_text(json.dumps(trace, indent=1), encoding="utf-8")
    print("%d distinct paths read; %d under the dev repo; %d under its project key"
          % (len(paths), len(dev_hits), len(proj_hits)))
    for h in dev_hits[:10]:
        print("   DEV: %s" % h)

    # clean up the tracer and the extra copies
    (sp / "sitecustomize.py").unlink(missing_ok=True)
    shutil.rmtree(corpus, ignore_errors=True)
    shutil.rmtree(art, ignore_errors=True)
    rec["trace"] = {k: trace[k] for k in
                    ("install_rc", "n_paths", "n_dev_repo_hits", "n_project_key_hits")}
    rec_p.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
