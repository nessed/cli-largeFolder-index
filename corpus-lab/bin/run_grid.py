#!/usr/bin/env python
"""run_grid.py - phase 7. Drive one (stack, tree) cell end to end, in order.

The eleven steps of spec 7.2, in sequence, with a gate after each one that can
invalidate the cell. Every step appends to the progress log, so if the laptop
sleeps mid-cell there is a record of exactly where it stopped.

Deliberate properties:
  7.2.2  checksums are VERIFIED, never restored. A restore that silently repairs
         a mutated corpus would hide the very thing the check exists to catch.
         A mismatch aborts the cell and says so.
  7.5    each battery gets a wall-clock cap; over the cap it is killed and the
         partial result is recorded AS partial rather than as a low score.
  7.6    no --force anywhere. A fresh label per cell, always, so a stale result
         can never be silently reused.

  python bin\\run_grid.py --stack s2_hook --tree h15000
  python bin\\run_grid.py --stack s0_baseline --tree raship --canary-timeout 420
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

RED = "\033[1;31m"
GRN = "\033[1;32m"
OFF = "\033[0m"

TREES = {
    "h15000": {"kind": "rung", "rung": "15000", "label": "h15000",
               "manifest_env": "CANARY_MANIFEST_PASS2",
               "db": "harness_15000.db"},
    "raship": {"kind": "raship", "rung": None, "label": "raship",
               "manifest_env": "CANARY_MANIFEST_PASS1",
               "db": "raship.db"},
}


def plog(phase, step, status, note, **nums):
    args = [sys.executable, str(L.PLOG), phase, step, status, note]
    args += [f"{k}={v}" for k, v in nums.items()]
    subprocess.run(args, capture_output=True)


def corpus_root(tree):
    t = TREES[tree]
    return str(L.RASHIP) if t["kind"] == "raship" else str(L.rung(t["rung"]))


def run(cmd, env=None, cap=None, cwd=None):
    """Run a child with a wall cap; kill its whole tree on Windows if it overruns."""
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, env=env, cwd=cwd)
    killed = False
    try:
        rc = p.wait(timeout=cap)
    except subprocess.TimeoutExpired:
        killed = True
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        try:
            rc = p.wait(timeout=30)
        except Exception:
            rc = -9
    return rc, round(time.monotonic() - t0, 1), killed


def step(n, name):
    print(f"\n--- [{n}] {name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stack", required=True)
    ap.add_argument("--tree", required=True, choices=list(TREES))
    ap.add_argument("--phase", default=None)
    ap.add_argument("--canary-timeout", type=int, default=420)
    ap.add_argument("--question-timeout", type=int, default=300)
    ap.add_argument("--battery-cap-s", type=int, default=45 * 60)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--skip-questions", action="store_true")
    a = ap.parse_args()

    tree = TREES[a.tree]
    root = corpus_root(a.tree)
    phase = a.phase or f"P7_{a.stack}_{tree['label']}"
    manifest = os.environ.get(tree["manifest_env"])
    db = L.STACKS / "s2_fts5" / tree["db"]
    cell = {"stack": a.stack, "tree": a.tree, "phase": phase, "steps": {}}

    print(f"===== CELL  stack={a.stack}  tree={a.tree}  phase={phase}")
    print(f"      corpus = {root}")
    print(f"      db     = {db}")
    if not manifest:
        print(f"{RED}ABORT: {tree['manifest_env']} is not set{OFF}")
        return 2

    env = dict(os.environ)
    env["CANARY_MANIFEST"] = manifest
    env["CORPUS_DB"] = str(db)

    # --- 1. teardown, even if nothing is installed --------------------------
    step(1, "teardown")
    run([sys.executable, str(L.BIN / "stack.py"), "teardown", "--corpus", root])

    # --- 2. verify planted-file checksums (VERIFY, never restore) -----------
    step(2, "verify planted-file checksums")
    label = f"{a.tree}_reference"
    ref = L.STATE / "checksums" / f"{label}.json"
    if not ref.exists():
        rc, _, _ = run([sys.executable, str(L.BIN / "checksums.py"),
                        "snapshot", "--label", label], env=env)
        print(f"    (no reference existed; created one, rc={rc})")
        cell["steps"]["checksums_pre"] = "created_reference"
    else:
        rc, _, _ = run([sys.executable, str(L.BIN / "checksums.py"),
                        "verify", "--against", label], env=env)
        cell["steps"]["checksums_pre"] = "ok" if rc == 0 else "MISMATCH"
        if rc != 0:
            print(f"{RED}ABORT: a planted file changed before this cell ran. "
                  f"Not restoring -- see spec 7.2.2 and hard stop 4.{OFF}")
            plog("P7", f"{a.stack}__{a.tree}", "failed",
                 "planted-file checksum mismatch BEFORE battery; cell aborted")
            return 3

    # --- 3. no stray policy or hook from a previous stack -------------------
    step(3, "confirm corpus is clean of a previous stack")
    md = Path(root) / "CLAUDE.md"
    sj = Path(root) / ".claude" / "settings.json"
    stray = []
    if md.exists():
        stray.append(str(md))
    if sj.exists():
        try:
            if json.loads(sj.read_text(encoding="utf-8")).get("hooks"):
                stray.append(str(sj) + " (has hooks block)")
        except Exception:
            stray.append(str(sj) + " (unparseable)")
    if stray:
        print(f"{RED}ABORT: leftover from a previous stack: {stray}{OFF}")
        plog("P7", f"{a.stack}__{a.tree}", "failed", f"stray install: {stray}")
        return 4
    cell["steps"]["clean"] = "ok"
    print("    clean")

    # --- 4. memory dir check ------------------------------------------------
    step(4, "memory dir check")
    mem = memory_state(root, clear=True)
    cell["steps"]["memory_pre"] = mem
    print(f"    {mem}")

    # --- 5. install ---------------------------------------------------------
    step(5, f"install {a.stack}")
    rc, _, _ = run([sys.executable, str(L.BIN / "stack.py"), "setup",
                    "--stack", a.stack, "--corpus", root, "--db", str(db)])
    if rc != 0:
        print(f"{RED}INSTALL FAILED rc={rc}{OFF}")
        cell["steps"]["install"] = f"failed rc={rc}"
        plog("P7", f"{a.stack}__{a.tree}", "failed", f"install failed rc={rc}")
        write_cell(cell)
        return 5
    cell["steps"]["install"] = "ok"

    # --- 6 & 7. canary battery (the install gate is its first question) -----
    step(6, "canary battery")
    cmd = [sys.executable, str(L.BIN / "run_canaries.py"),
           "--phase", phase, "--stack", a.stack,
           "--corpus-kind", tree["kind"], "--corpus-label", tree["label"],
           "--timeout", str(a.canary_timeout), "--parallel", str(a.parallel)]
    if tree["rung"]:
        cmd += ["--rung", tree["rung"]]
    # S4's front door is an MCP server rather than a script, so the sessions need
    # its config. --strict-mcp-config (added by ask.py) keeps every other server
    # this machine has configured out of the measurement.
    if a.stack == "s4_pdfmcp":
        cmd += ["--mcp-config", str(L.STACKS / "s4_pdfmcp" / "mcp_config.json")]
    rc, secs, killed = run(cmd, env=env, cap=a.battery_cap_s)
    cell["steps"]["canary_battery"] = {
        "rc": rc, "wall_s": secs,
        "status": "PARTIAL (hit 45-min cap)" if killed else "complete"}
    if killed:
        print(f"{RED}battery hit the {a.battery_cap_s}s cap; "
              f"results recorded as PARTIAL{OFF}")

    # --- 8. harness question battery (harness only) -------------------------
    if a.tree == "h15000" and not a.skip_questions:
        step(8, "harness question battery (frozen 20)")
        qcmd = [sys.executable, str(L.BIN / "run_harness.py"),
                "--phase", phase, "--stack", a.stack, "--rung", tree["rung"],
                "--timeout", str(a.question_timeout), "--parallel", str(a.parallel)]
        rc, secs, killed = run(qcmd, env=env, cap=a.battery_cap_s)
        cell["steps"]["question_battery"] = {
            "rc": rc, "wall_s": secs,
            "status": "PARTIAL (hit 45-min cap)" if killed else "complete"}
    else:
        cell["steps"]["question_battery"] = "n/a"

    # --- 9. teardown --------------------------------------------------------
    step(9, "teardown")
    run([sys.executable, str(L.BIN / "stack.py"), "teardown", "--corpus", root])

    # --- 10. checksums + memory again ---------------------------------------
    step(10, "verify checksums and memory again")
    rc, _, _ = run([sys.executable, str(L.BIN / "checksums.py"),
                    "verify", "--against", label], env=env)
    cell["steps"]["checksums_post"] = "ok" if rc == 0 else "MISMATCH"
    if rc != 0:
        print(f"{RED}A PLANTED FILE CHANGED DURING THIS BATTERY. "
              f"Every later cell on this tree is suspect.{OFF}")
    cell["steps"]["memory_post"] = memory_state(root, clear=True)
    print(f"    memory: {cell['steps']['memory_post']}")

    # --- 11. summary line ---------------------------------------------------
    write_cell(cell)
    plog("P7", f"{a.stack}__{a.tree}", "done",
         f"cell complete; canary={cell['steps']['canary_battery']}, "
         f"questions={cell['steps']['question_battery']}, "
         f"checksums_pre={cell['steps']['checksums_pre']}, "
         f"checksums_post={cell['steps']['checksums_post']}")
    print(f"\n{GRN}===== CELL DONE {a.stack} / {a.tree}{OFF}")
    return 0


def project_keys_for(root):
    """Find the .claude/projects dir(s) for a corpus root.

    The key is derived from the cwd STRING as it was typed, so its casing does
    not reliably match the resolved path (the live ra-ship key is
    `C--Users-Ali-desktop-projects-code-ra-ship`, mixed case). Deriving it and
    hoping is how a memory dir goes unnoticed, so match case-insensitively
    against the directories that actually exist.
    """
    # "C:\Users\...\ra-ship" -> "c--users-...-ra-ship": the colon becomes a dash
    # too, which is where the doubled dash comes from.
    want = str(root).replace(":", "-").replace("\\", "-").replace("/", "-").lower()
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return []
    return [d for d in base.iterdir() if d.is_dir() and d.name.lower() == want]


def memory_state(root, clear=False):
    """Spec 6.3 / 7.2.4: a memory dir under the corpus's project key lets one
    session hand findings to the next, which would make recall meaningless.

    MEASURED during the phase 2.6 probe: a measurement session DID write
    `memory/sandbox-probe.md` even though ask.py passes
    `--disallowedTools Write,Edit,NotebookEdit`. Memory persistence does not go
    through those tools, so disallowing them does not close this channel.
    Checking is therefore not enough -- anything found is moved aside into the
    private tree and recorded, so a later cell cannot inherit an earlier one's
    notes.
    """
    keys = project_keys_for(root)
    if not keys:
        return "no project key yet"
    out = []
    for k in keys:
        d = k / "memory"
        if not d.exists():
            out.append(f"{k.name}: absent")
            continue
        files = [f for f in d.rglob("*") if f.is_file()]
        if not files:
            out.append(f"{k.name}: empty")
            continue
        if not clear:
            out.append(f"{k.name}: NON-EMPTY ({len(files)} files)")
            continue
        stamp = time.strftime("%Y%m%d_%H%M%S")
        quar = L.PRIVATE / "results" / "_memory_quarantine" / f"{k.name}__{stamp}"
        quar.mkdir(parents=True, exist_ok=True)
        for f in files:
            try:
                f.replace(quar / f.name)
            except Exception as e:
                out.append(f"{k.name}: COULD NOT CLEAR {f.name}: {e}")
        out.append(f"{k.name}: had {len(files)} file(s), MOVED to {quar}")
    return "; ".join(out)


def write_cell(cell):
    dest = L.STATE / "cells"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{cell['stack']}__{cell['tree']}.json").write_text(
        json.dumps(cell, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
