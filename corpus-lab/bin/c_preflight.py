#!/usr/bin/env python
"""c_preflight.py - build C, Stage 0. Free, read-only checks before any work starts.

Mirrors approach B's Stage 0 checks (see plans_fable/C_SHELF_FIRST_BUILD.md Stage 0):
Python 3.11, fastembed/numpy import, DB present and >= 6.9 GB, corpus_search.py
--coverage reporting the fixed counts, claude.exe --version, free disk >= 5 GB, and
whether the rung already carries a CLAUDE.md / .claude (informational only).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import corpus_search as CS  # noqa: E402

DB = L.STACKS / "s2_fts5" / "harness_15000.db"
RUNG = L.rung(15000)


def check_python():
    v = sys.version_info
    return {"ok": v.major == 3 and v.minor == 11, "version": sys.version.split()[0]}


def check_imports():
    try:
        import fastembed  # noqa: F401
        import numpy  # noqa: F401
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_db():
    if not DB.exists():
        return {"ok": False, "path": str(DB), "reason": "missing"}
    size = DB.stat().st_size
    gb = size / 1e9
    return {"ok": gb >= 6.9, "path": str(DB), "size_bytes": size, "size_gb": round(gb, 3)}


def check_coverage():
    db = CS.connect(str(DB))
    cov = CS.coverage(db)
    ok = (cov.get("indexed_ok") == 13634 and cov.get("addressable_pages") == 1206260
          and cov.get("accounting_identity_holds") is True)
    return {"ok": ok, "coverage": cov}


def check_claude_exe():
    try:
        r = subprocess.run([L.CLAUDE, "--version"], capture_output=True, text=True, timeout=30)
        out = (r.stdout or "").strip()
        return {"ok": bool(out), "output": out, "rc": r.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_disk():
    total, used, free = shutil.disk_usage(str(L.RETRIEVAL_LAB))
    free_gb = free / 1e9
    return {"ok": free_gb >= 5.0, "free_gb": round(free_gb, 2)}


def check_rung_clean():
    md = RUNG / "CLAUDE.md"
    cd = RUNG / ".claude"
    return {"CLAUDE.md_exists": md.exists(), ".claude_exists": cd.exists()}


def main():
    report = {
        "python": check_python(),
        "imports": check_imports(),
        "db": check_db(),
        "coverage": check_coverage(),
        "claude_exe": check_claude_exe(),
        "disk": check_disk(),
        "rung_informational": check_rung_clean(),
    }
    gates = ["python", "imports", "db", "coverage", "claude_exe", "disk"]
    report["overall_pass"] = all(report[g]["ok"] for g in gates)
    out = L.STATE / "c_preflight.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
