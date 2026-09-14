#!/usr/bin/env python
"""p9_gate_s.py - run the three offline gates against a shelf and report Gate S.

Phase 9.2.3. The three gates each write their own state file to a FIXED path, so
running them against the v2 shelf would overwrite the v1 numbers this repository
rests on. This runs each one with --shelf-dir, captures its state file
immediately, restores the v1 file from git, and collects the readings into the
Gate S verdict.

  python -u corpus-lab/bin/p9_gate_s.py --v2-shelf-dir corpus-lab/02_stacks/s7_shelf_v2

Writes state/c_shelf_v2_gate.json and leaves every v1 state file as it found it.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# gate script -> the state file it overwrites
GATES = {
    "caption": (["c_caption_gate.py", "--channel", "lex"], "c_caption_family_gate.json"),
    "page": (["c_offline_gate.py", "--v2", "--page-only", "--query-mode", "row",
              "--caption-channel", "dense_first"], "c_page_gate.json"),
    "route": (["c_route_gate.py"], "c_route_gate.json"),
}


def run_gate(name, shelf_dir):
    argv, state_name = GATES[name]
    cmd = [sys.executable, "-u", str(L.BIN / argv[0])] + argv[1:] + \
          ["--shelf-dir", str(shelf_dir)]
    print("  running %s ..." % argv[0], flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    sp = L.STATE / state_name
    data = None
    if sp.exists():
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            pass
    # put the v1 file back exactly as committed, so no recorded number is lost
    subprocess.run(["git", "checkout", "HEAD", "--", "corpus-lab/state/" + state_name],
                   cwd=str(L.RETRIEVAL_LAB), capture_output=True, text=True)
    return p.returncode, (p.stdout or ""), data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-shelf-dir", dest="v2",
                    default=str(L.STACKS / "s7_shelf_v2"))
    ap.add_argument("--v1-shelf-dir", dest="v1", default=str(L.STACKS / "s7_shelf"))
    a = ap.parse_args()

    print("Gate S: running the three offline gates against %s" % a.v2)
    readings = {}

    rc, so, data = run_gate("caption", a.v2)
    top10 = pool100 = None
    for line in so.splitlines():
        if line.startswith("dev lex"):
            print("   ", line.strip())
            try:
                top10 = int(line.split("le10=")[1].split()[0])
                curve = line.split("curve=")[1]
                pool100 = int(curve.split("'recall_at_100':")[1].split(",")[0].strip(" }"))
            except Exception:
                pass
    readings["document_top10_dev"] = top10
    readings["document_pool100_dev"] = pool100

    rc, so, data = run_gate("page", a.v2)
    b2c = None
    if data:
        cfg = data.get("row+caption_dense_first") or {}
        b2c = cfg.get("micro_hits")
        print("    B2c pages: %s / %s" % (b2c, cfg.get("micro_n")))
    readings["b2c_pages_dev"] = b2c

    rc, so, data = run_gate("route", a.v2)
    rdoc = rident = None
    if data:
        rdoc = (data.get("document_level") or {}).get("routed_absent")
        rident = (data.get("identifier_level") or {}).get("routed_absent")
        print("    ROUTE: %s/11 document, %s/4 identifier" % (rdoc, rident))
    readings["route_document_level"] = rdoc
    readings["route_identifier_level"] = rident

    print("\nreadings: %s" % json.dumps(readings))
    print("collecting the verdict ...")
    cmd = [sys.executable, "-u", str(L.BIN / "c_shelf_v2_gate.py"),
           "--v1-shelf-dir", str(a.v1), "--v2-shelf-dir", str(a.v2)]
    for flag, key in (("--doc-top10", "document_top10_dev"),
                      ("--doc-pool100", "document_pool100_dev"),
                      ("--b2c", "b2c_pages_dev"),
                      ("--route-doc", "route_document_level"),
                      ("--route-ident", "route_identifier_level")):
        if readings.get(key) is not None:
            cmd += [flag, str(readings[key])]
    p = subprocess.run(cmd, text=True)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
