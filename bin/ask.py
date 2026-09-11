#!/usr/bin/env python
"""ask.py - run ONE headless Claude Code session and capture what it actually did.

This is the measurement instrument for the whole bake-off. Everything else scores
its output. Idempotent: if result.json already exists for (stack, corpus, qid) it
exits early unless --force.

Emits 03_runs/<phase>/<stack>__<corpus>__<qid>.json with:
  answer_text, files_opened[], tool_calls[], wall_s, cost_usd, turns, timed_out
"""
import argparse, json, os, subprocess, sys, time, re
from pathlib import Path

LAB = Path(r"C:\Users\Ali\Desktop\corpus-lab")
# `claude` on PATH is a shell wrapper; Windows CreateProcess needs the .cmd explicitly.
CLAUDE = r"C:\nvm4w\nodejs\claude.cmd"

# tool-call argument fields that name a file/dir the agent touched
PATH_FIELDS = ("file_path", "path", "notebook_path", "filePath", "file")


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
    for m in re.finditer(r'[A-Za-z0-9_\-./\\]+\.[A-Za-z0-9]{1,5}', cmd or ""):
        tok = m.group(0)
        if len(tok) > 3:
            out.append(norm(tok, root))
    return out


def run(args):
    root = str(Path(args.corpus).resolve())
    outdir = LAB / "03_runs" / args.phase
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.stack}__{args.corpus_label}__{args.qid}"
    result_path = outdir / f"{stem}.json"
    raw_path = outdir / f"{stem}.jsonl"

    if result_path.exists() and not args.force:
        print(f"SKIP (done): {stem}")
        return 0

    cmd = [
        CLAUDE, "-p", args.question,
        "--output-format", "stream-json", "--verbose",
        "--model", args.model,
        "--max-turns", str(args.max_turns),
        "--permission-mode", args.permission_mode,
    ]
    if args.settings:
        cmd += ["--settings", args.settings]
    if args.mcp_config:
        cmd += ["--mcp-config", args.mcp_config, "--strict-mcp-config"]
    if args.disallowed:
        cmd += ["--disallowedTools"] + args.disallowed.split(",")
    if args.append_system_prompt:
        cmd += ["--append-system-prompt", args.append_system_prompt]

    # NOTE (hard-won): claude.cmd is a cmd.exe wrapper. subprocess timeout kills the
    # wrapper but NOT the node grandchild, and a piped stderr then blocks forever.
    # So: stderr to a file (never a pipe), and taskkill /T /F the whole tree on timeout.
    err_path = outdir / f"{stem}.err"
    t0 = time.time()
    timed_out = False
    with open(raw_path, "w", encoding="utf-8") as fh, \
         open(err_path, "w", encoding="utf-8") as eh, open(os.devnull) as devnull:
        proc = subprocess.Popen(cmd, cwd=root, stdout=fh, stderr=eh, stdin=devnull)
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
    wall = time.time() - t0
    stderr = err_path.read_text(encoding="utf-8", errors="replace") if err_path.exists() else ""
    if timed_out:
        stderr = "TIMEOUT\n" + stderr

    # ---- parse the stream ----
    tool_calls, files_opened, answer, cost, turns = [], [], None, None, None
    n_rate_limit = 0
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            if t == "assistant":
                for c in d.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use":
                        name, inp = c.get("name"), c.get("input", {}) or {}
                        tool_calls.append({"name": name, "input": inp})
                        hit = False
                        for f in PATH_FIELDS:
                            if inp.get(f):
                                files_opened.append(
                                    {"tool": name, "path": norm(inp[f], root)}
                                )
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

    rec = {
        "stack": args.stack, "corpus": args.corpus_label, "corpus_root": root,
        "qid": args.qid, "question": args.question, "model": args.model,
        "answer_text": answer, "files_opened": files_opened,
        "n_files_opened": len(files_opened),
        "tool_calls": tool_calls, "n_tool_calls": len(tool_calls),
        "tool_histogram": {},
        "wall_s": round(wall, 2), "cost_usd": cost, "turns": turns,
        "timed_out": timed_out, "returncode": rc,
        "rate_limit_events": n_rate_limit,
        "stderr_tail": (stderr or "")[-800:],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    for tc in tool_calls:
        rec["tool_histogram"][tc["name"]] = rec["tool_histogram"].get(tc["name"], 0) + 1

    result_path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"OK {stem}: {len(tool_calls)} calls, {len(files_opened)} paths, "
          f"{wall:.1f}s, ${cost}, timeout={timed_out}")
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
    ap.add_argument("--disallowed", default=None)
    ap.add_argument("--append-system-prompt", default=None)
    ap.add_argument("--force", action="store_true")
    sys.exit(run(ap.parse_args()))
