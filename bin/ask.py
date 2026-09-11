#!/usr/bin/env python
"""ask.py - run ONE headless Claude Code session and capture what it actually did.

This is the measurement instrument for the whole bake-off. Everything else scores
its output. One session per question, always: if questions shared a session,
question 5 would benefit from what question 2 found and recall would mean nothing.

Emits <RUNS>/<phase>/<stack>__<corpus>__<qid>.json with:
  answer_text, files_opened[], tool_calls[], wall_s, cost_usd, turns, timed_out,
  suspended, max_event_gap_s

Grid-run phase 0 changes:
  0.3  --disallowedTools "Write,Edit,NotebookEdit" by default. Measurement sessions
       run bypassPermissions; without this one session can silently edit the corpus
       and every later stack measures a different tree.
  0.6  timing off time.monotonic(), plus suspend detection (see timing note below).
  0.7  cost recorded as-is including null, and flagged, so batteries report n-of-m
       rather than silently summing a biased subset.
  0.9  HOOK_LOG set per (stack, corpus) so hook evidence never interleaves.
  0.10 a skip is LOUD and returns rc 3, so a reused label cannot quietly return
       last night's numbers.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

PATH_FIELDS = ("file_path", "path", "notebook_path", "filePath", "file")

RED = "\033[1;31m"
YEL = "\033[1;33m"
OFF = "\033[0m"

# Phase 0.3: never let a measurement session mutate the corpus under test.
DEFAULT_DISALLOWED = "Write,Edit,NotebookEdit"

# Phase 0.6 - suspend detection, and why it is done this way.
# The spec's rule is "wall exceeds summed inter-event time by more than 60 s".
# Taken literally that can never fire: inter-event gaps are measured by a reader
# thread in real time, so they sum to the wall time by construction -- a laptop
# sleeping mid-session lands INSIDE one gap, it does not vanish from the sum.
# What does distinguish them is the clock source:
#   time.time()         wall clock, advances across suspend
#   time.perf_counter() QueryPerformanceCounter, does NOT advance across suspend
# so the divergence between the two IS the suspend, measured directly. Every clock
# is recorded, plus the largest single inter-event gap, and the flag fires on
# either signal, so nothing hides behind one rule.
SUSPEND_TOLERANCE_S = 60.0
IMPLAUSIBLE_GAP_S = 900.0


def norm(p, root):
    """Normalise a path to corpus-relative, forward-slashed, lowercase."""
    if not p:
        return None
    try:
        pp = Path(str(p))
        if not pp.is_absolute():
            pp = Path(root) / pp
        rel = os.path.relpath(str(pp), str(root))
    except Exception:
        return str(p).replace("\\", "/").lower()
    return rel.replace("\\", "/").lower()


def extract_paths_from_bash(cmd, root):
    """Best-effort: pull file-ish tokens out of a bash command line."""
    out = []
    for m in re.finditer(r"[A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]{1,5}", cmd or ""):
        tok = m.group(0)
        if len(tok) > 3:
            out.append(norm(tok, root))
    return out


def run(args):
    root = str(Path(args.corpus).resolve())
    outdir = Path(args.runs_root or L.RUNS) / args.phase
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.stack}__{args.corpus_label}__{args.qid}"
    result_path = outdir / f"{stem}.json"
    raw_path = outdir / f"{stem}.jsonl"

    # --- 0.10: a silent skip is how a reused label returns last night's number ---
    if result_path.exists() and not args.force:
        for msg in (
            f"#### SKIPPED (result exists, --force not given): {stem}",
            f"#### existing file: {result_path}",
            "#### THE NUMBER YOU ARE ABOUT TO SCORE IS STALE.",
        ):
            print(RED + msg + OFF, file=sys.stderr, flush=True)
        print(f"SKIP_STALE {stem}")
        return 3

    disallowed = args.disallowed if args.disallowed is not None else DEFAULT_DISALLOWED

    cmd = [
        L.CLAUDE, "-p", args.question,
        "--output-format", "stream-json", "--verbose",
        "--model", args.model,
        "--max-turns", str(args.max_turns),
        "--permission-mode", args.permission_mode,
    ]
    if args.settings:
        cmd += ["--settings", args.settings]
    if args.mcp_config:
        cmd += ["--mcp-config", args.mcp_config, "--strict-mcp-config"]
    if disallowed:
        cmd += ["--disallowedTools"] + [t for t in disallowed.split(",") if t]
    if args.append_system_prompt:
        cmd += ["--append-system-prompt", args.append_system_prompt]

    # 0.9: per-(stack, corpus) hook log, inherited by the hook subprocess.
    env = dict(os.environ)
    env["HOOK_LOG"] = str(L.hook_log(args.stack, args.corpus_label))
    # Never hand a measurement session the manifest location (phase 2.3).
    env.pop("CANARY_MANIFEST", None)

    # NOTE (hard-won): claude.cmd is a cmd.exe wrapper. subprocess timeout kills the
    # wrapper but NOT the node grandchild, and a piped stderr then blocks forever.
    # So: stderr to a FILE, never a pipe, and taskkill /T /F the whole tree on timeout.
    # stdout IS piped, but a dedicated thread drains it line by line so it can never
    # block the child, and each line is timestamped on arrival so gaps are measurable.
    err_path = outdir / f"{stem}.err"
    lines = []
    gaps = []
    t_mono0 = time.monotonic()
    t_perf0 = time.perf_counter()
    t_wall0 = time.time()
    timed_out = False

    def drain(pipe, fh):
        last = time.monotonic()
        try:
            for raw in pipe:
                now = time.monotonic()
                gaps.append(now - last)
                last = now
                fh.write(raw)
                fh.flush()
                lines.append(raw)
        except Exception:
            pass

    with open(raw_path, "w", encoding="utf-8") as fh, \
            open(err_path, "w", encoding="utf-8") as eh, \
            open(os.devnull) as devnull:
        proc = subprocess.Popen(
            cmd, cwd=root, stdout=subprocess.PIPE, stderr=eh, stdin=devnull,
            env=env, text=True, encoding="utf-8", errors="replace", bufsize=1)
        th = threading.Thread(target=drain, args=(proc.stdout, fh), daemon=True)
        th.start()
        try:
            rc = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out, rc = True, -1
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True)
            try:
                proc.wait(timeout=20)
            except Exception:
                pass
        th.join(timeout=15)

    wall = time.monotonic() - t_mono0
    perf = time.perf_counter() - t_perf0
    wallclock = time.time() - t_wall0
    max_gap = max(gaps) if gaps else 0.0
    clock_skew = max(wallclock - perf, wall - perf)
    suspended = bool(clock_skew > SUSPEND_TOLERANCE_S or max_gap > IMPLAUSIBLE_GAP_S)

    stderr = ""
    if err_path.exists():
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
    if timed_out:
        stderr = "TIMEOUT\n" + stderr

    # ---- parse the stream ----
    tool_calls, files_opened = [], []
    answer = cost = turns = None
    n_rate_limit = 0
    n_json_lines = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        n_json_lines += 1
        t = d.get("type")
        if t == "assistant":
            for c in d.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    name, inp = c.get("name"), c.get("input", {}) or {}
                    tool_calls.append({"name": name, "input": inp})
                    hit = False
                    for f in PATH_FIELDS:
                        if inp.get(f):
                            files_opened.append({"tool": name, "path": norm(inp[f], root)})
                            hit = True
                    if name == "Bash" and not hit:
                        for p in extract_paths_from_bash(inp.get("command", ""), root):
                            files_opened.append({"tool": "Bash", "path": p})
        elif t == "rate_limit_event":
            n_rate_limit += 1
        elif t == "result":
            answer = d.get("result")
            cost = d.get("total_cost_usd")
            turns = d.get("num_turns")

    first_char = ""
    for line in lines:
        if line.strip():
            first_char = line.strip()[0]
            break
    stream_json_ok = bool(first_char == "{" and n_json_lines > 0)

    rec = {
        "stack": args.stack, "corpus": args.corpus_label, "corpus_root": root,
        "qid": args.qid, "question": args.question, "model": args.model,
        "answer_text": answer, "files_opened": files_opened,
        "n_files_opened": len(files_opened),
        "tool_calls": tool_calls, "n_tool_calls": len(tool_calls),
        "tool_histogram": {},
        "wall_s": round(wall, 2),
        "wall_clock_s": round(wallclock, 2),
        "perf_s": round(perf, 2),
        "clock_skew_s": round(clock_skew, 2),
        "max_event_gap_s": round(max_gap, 2),
        "suspended": suspended,
        "cost_usd": cost, "cost_missing": cost is None,
        "turns": turns,
        "timed_out": timed_out, "returncode": rc,
        "stream_json_ok": stream_json_ok, "n_stream_events": n_json_lines,
        "disallowed_tools": disallowed,
        "permission_mode": args.permission_mode,
        "rate_limit_events": n_rate_limit,
        "stderr_tail": (stderr or "")[-800:],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    for tc in tool_calls:
        rec["tool_histogram"][tc["name"]] = rec["tool_histogram"].get(tc["name"], 0) + 1

    result_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")

    flags = []
    if timed_out:
        flags.append("TIMEOUT")
    if suspended:
        flags.append(YEL + f"SUSPENDED(skew={clock_skew:.0f}s,gap={max_gap:.0f}s)" + OFF)
    if not stream_json_ok:
        flags.append(RED + "NOT-STREAM-JSON" + OFF)
    print(f"OK {stem}: {len(tool_calls)} calls, {len(files_opened)} paths, "
          f"{wall:.1f}s, ${cost}, {' '.join(flags) if flags else 'clean'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--stack", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--corpus-label", required=True)
    ap.add_argument("--qid", required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--max-turns", type=int, default=30)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--permission-mode", default="bypassPermissions")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--mcp-config", default=None)
    ap.add_argument("--disallowed", default=None,
                    help="comma list; default " + repr(DEFAULT_DISALLOWED) +
                         ". Pass '' to allow corpus writes (never for a battery).")
    ap.add_argument("--append-system-prompt", default=None)
    ap.add_argument("--runs-root", default=None)
    ap.add_argument("--force", action="store_true")
    sys.exit(run(ap.parse_args()))
