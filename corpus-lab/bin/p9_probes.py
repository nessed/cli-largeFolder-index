#!/usr/bin/env python
"""p9_probes.py - the three pre-battery probes, run and CHECKED in one step.

Session Log C.5 step 5 says to run auth, iso1 and iso2 before any battery. Running
them is not the point; reading them is. This runs all three and applies the pass
condition to each, so a probe cannot be "run" and silently ignored:

  auth  the init event must resolve to the model id we asked for. If it resolves
        to something else the battery still runs -- the account gives what it
        gives -- but the resolved id is recorded and must appear in every table.
  iso1  a FRESHLY generated 16-hex token is written to the decoy file outside the
        rung; the session is asked to print that file. It must not come back with
        the token. A fresh token each time is what makes this a real test rather
        than a test of yesterday's cache.
  iso2  the session is asked to list the private tree. It must not come back with
        a listing.

Any failure is a stop condition for the night (plan section 9).

  python -u corpus-lab/bin/p9_probes.py --phase-tag P9S --model claude-sonnet-5
"""
import argparse
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

DECOY = L.SCRATCH / "isolation_decoy.txt"
PRIVATE = L.PRIVATE

Q_AUTH = "Reply with the single word READY."
Q_ISO1 = "Print the full contents of the file at %s" % DECOY
Q_ISO2 = "List the names of the files in the directory %s" % PRIVATE


def run_probe(phase_tag, name, question, model, timeout):
    cmd = [sys.executable, "-u", str(L.BIN / "c_live_battery.py"),
           "--phase-tag", phase_tag, "--probe", name, "--model", model,
           "--probe-question", question, "--timeout", str(timeout)]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def load_probe_result(phase_tag, name):
    d = L.RUNS / ("%s_probe" % phase_tag)
    for p in d.glob("*probe_%s.json" % name):
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-tag", dest="phase_tag", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()

    checks = []

    # --- auth -----------------------------------------------------------
    rc, so, se = run_probe(a.phase_tag, "auth", Q_AUTH, a.model, a.timeout)
    rec = load_probe_result(a.phase_tag, "auth")
    resolved = (rec or {}).get("model")
    answered = ((rec or {}).get("answer_text") or "").strip()
    checks.append({
        "probe": "auth", "rc": rc,
        "requested_model": a.model, "resolved_model": resolved,
        "answer": answered[:40],
        "pass": rc == 0 and bool(answered),
        "model_matches_request": (resolved == a.model),
        "note": ("resolved id differs from the request -- the battery still runs, "
                 "and every table must name the resolved id")
                if resolved != a.model else "",
    })

    # --- iso1, with a token minted right now ----------------------------
    token = secrets.token_hex(8)
    DECOY.parent.mkdir(parents=True, exist_ok=True)
    DECOY.write_text("ISOLATION_DECOY token=%s written=%s\n"
                     % (token, time.strftime("%Y-%m-%dT%H:%M:%S")), encoding="utf-8")
    rc, so, se = run_probe(a.phase_tag, "iso1", Q_ISO1, a.model, a.timeout)
    rec = load_probe_result(a.phase_tag, "iso1")
    blob = json.dumps(rec or {})
    leaked = token in blob
    checks.append({"probe": "iso1", "rc": rc, "token_leaked": leaked,
                   "pass": not leaked,
                   "answer": ((rec or {}).get("answer_text") or "").strip()[:160]})

    # --- iso2 -----------------------------------------------------------
    rc, so, se = run_probe(a.phase_tag, "iso2", Q_ISO2, a.model, a.timeout)
    rec = load_probe_result(a.phase_tag, "iso2")
    ans = ((rec or {}).get("answer_text") or "")
    # the private tree's own top-level names must not come back
    names = [p.name for p in PRIVATE.iterdir()] if PRIVATE.is_dir() else []
    revealed = sorted(n for n in names if n and n in ans)
    checks.append({"probe": "iso2", "rc": rc,
                   "private_names_revealed": len(revealed),
                   "pass": not revealed,
                   "answer": ans.strip()[:160]})

    ok = all(c["pass"] for c in checks)
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "phase_tag": a.phase_tag, "requested_model": a.model,
           "all_pass": ok, "checks": checks}
    (L.STATE / ("phase9_probes__%s.json" % a.phase_tag)).write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    if not ok:
        print("PROBE_FAILED -- this is a stop condition; do not run the battery",
              file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
