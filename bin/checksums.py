#!/usr/bin/env python
"""checksums.py - grid-run phase 0.3, second half.

Measurement sessions run --permission-mode bypassPermissions. ask.py now denies
Write/Edit/NotebookEdit, but Bash is still unrestricted, so a session can still
mutate the corpus with a redirect or a python one-liner. If a planted file is
altered, every later stack is measuring a different tree and nothing would say so.

So: snapshot the sha256 of every planted file before a battery, verify after.
A moved hash is a loud failure, not a footnote.

  set CANARY_MANIFEST=<manifest.csv>
  python bin\\checksums.py snapshot --label s2_hook_pre
  python bin\\checksums.py verify   --against s2_hook_pre

Exit codes: 0 all match, 1 a hash moved or a file vanished, 2 setup problem.
The manifest path comes from CANARY_MANIFEST only (phase 2.3) -- reading this
script must not tell anyone where the answer key lives.
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def manifest_files():
    """Absolute paths of every planted file, from whichever manifest is pointed at.

    Tolerates both manifest shapes: pass 1 uses absolute_path/relative_path against
    ra-ship; pass 2 adds a rung column. Only the path columns are read -- phrases
    are never loaded, so a process that verifies checksums does not thereby acquire
    the answer key.
    """
    mp = L.canary_manifest()
    if not mp.exists():
        print(f"ERROR: manifest not found: {mp}", file=sys.stderr)
        sys.exit(2)
    out = []
    with open(mp, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            ap = (r.get("absolute_path") or "").strip()
            if not ap:
                rel = (r.get("relative_path") or "").strip()
                if not rel:
                    continue
                ap = str(L.RASHIP / rel)
            out.append(ap)
    return out


def snapshot(label):
    rows = {}
    missing = []
    for ap in manifest_files():
        p = Path(ap)
        if not p.exists():
            missing.append(ap)
            continue
        st = p.stat()
        rows[ap] = {"sha256": sha256(p), "size": st.st_size,
                    "mtime": round(st.st_mtime, 3)}
    dest = L.STATE / "checksums" / f"{label}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(
        {"label": label, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "manifest": str(L.canary_manifest()), "n_files": len(rows),
         "missing": missing, "files": rows}, indent=1), encoding="utf-8")
    print(f"snapshot {label}: {len(rows)} files hashed, {len(missing)} missing -> {dest}")
    if missing:
        for m in missing:
            print(f"  MISSING: {m}", file=sys.stderr)
    return dest


def verify(against):
    src = L.STATE / "checksums" / f"{against}.json"
    if not src.exists():
        print(f"ERROR: no snapshot named {against} at {src}", file=sys.stderr)
        sys.exit(2)
    base = json.loads(src.read_text(encoding="utf-8"))
    bad, gone, ok = [], [], 0
    for ap, rec in base["files"].items():
        p = Path(ap)
        if not p.exists():
            gone.append(ap)
            continue
        h = sha256(p)
        if h != rec["sha256"]:
            bad.append({"path": ap, "was": rec["sha256"][:16], "now": h[:16],
                        "size_was": rec["size"], "size_now": p.stat().st_size})
        else:
            ok += 1
    print(f"verify against {against}: {ok} unchanged, {len(bad)} CHANGED, {len(gone)} MISSING")
    for b in bad:
        print(f"  CHANGED: {b['path']}\n      {b['was']}... -> {b['now']}...", file=sys.stderr)
    for g in gone:
        print(f"  MISSING: {g}", file=sys.stderr)
    out = L.STATE / "checksums" / f"verify__{against}__{time.strftime('%H%M%S')}.json"
    out.write_text(json.dumps({"against": against, "ok": ok, "changed": bad,
                               "missing": gone}, indent=1), encoding="utf-8")
    return 1 if (bad or gone) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["snapshot", "verify"])
    ap.add_argument("--label", default="pre")
    ap.add_argument("--against", default="pre")
    a = ap.parse_args()
    if a.action == "snapshot":
        snapshot(a.label)
        sys.exit(0)
    sys.exit(verify(a.against))
