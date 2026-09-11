#!/usr/bin/env python
"""run_canaries.py - S0..Sn canary battery on the ra-ship corpus.

Runs one headless Claude Code session per canary phrase, in parallel, via ask.py.
Then scores: did the answer name the correct file path?
"""
import argparse, csv, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LAB = Path(r"C:\Users\Ali\Desktop\corpus-lab")
MANIFEST = Path(r"C:\Users\Ali\Desktop\canary_manifest_pass1.csv")
RA = Path(r"C:\Users\Ali\Desktop\Projects\Code\ra-ship")

QUESTION = (
    "Somewhere in this repository there is exactly one file containing the literal "
    "string `{phrase}`. Find it. Reply with ONLY the path of that file relative to the "
    "repository root, or the exact text NOT_FOUND if you are confident it is not here."
)


def load_canaries():
    rows = []
    with open(MANIFEST, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if not r.get("canary_phrase"):
                continue
            rows.append({
                "qid": r["canary_phrase"].split("-")[0] + "_" + r["canary_phrase"][-6:],
                "phrase": r["canary_phrase"],
                "expect": r["relative_path"].replace("\\", "/").lower(),
                "depth": r["depth"], "format": r["format"],
                "tracked": r["tracked_status"], "in_venv": r["in_venv"],
                "branch": r["branch"],
            })
    return rows


def one(c, args):
    cmd = [sys.executable, str(LAB / "bin" / "ask.py"),
           "--phase", args.phase, "--stack", args.stack,
           "--corpus", str(RA), "--corpus-label", "raship",
           "--qid", c["qid"], "--question", QUESTION.format(phrase=c["phrase"]),
           "--model", args.model, "--max-turns", str(args.max_turns),
           "--timeout", str(args.timeout)]
    if args.settings:
        cmd += ["--settings", args.settings]
    if args.mcp_config:
        cmd += ["--mcp-config", args.mcp_config]
    if args.disallowed:
        cmd += ["--disallowed", args.disallowed]
    if args.append_system_prompt:
        cmd += ["--append-system-prompt", args.append_system_prompt]
    if args.force:
        cmd += ["--force"]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return c["qid"], p.returncode, (p.stdout or "").strip()[-300:], (p.stderr or "")[-300:]


def score(args, canaries):
    outdir = LAB / "03_runs" / args.phase
    rows = []
    for c in canaries:
        f = outdir / f"{args.stack}__raship__{c['qid']}.json"
        if not f.exists():
            rows.append({**c, "found": None, "note": "no result file"})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        ans = (d.get("answer_text") or "").replace("\\", "/").lower()
        exp = c["expect"]
        base = exp.split("/")[-1]
        found = exp in ans or (base in ans and len(base) > 8)
        said_missing = "not_found" in ans
        opened = [x["path"] for x in d.get("files_opened", []) if x.get("path")]
        venv_noise = sum(1 for p in opened if "02_tool_runs" in p or "site-packages" in p)
        rows.append({
            **c, "found": bool(found), "said_not_found": said_missing,
            "n_tool_calls": d.get("n_tool_calls"), "n_files_opened": d.get("n_files_opened"),
            "venv_noise": venv_noise, "wall_s": d.get("wall_s"),
            "cost_usd": d.get("cost_usd"), "timed_out": d.get("timed_out"),
            "tools": json.dumps(d.get("tool_histogram", {})),
            "answer": (d.get("answer_text") or "")[:200],
        })
    out = LAB / "04_scores" / f"canaries__{args.stack}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    hits = sum(1 for r in rows if r.get("found"))
    cost = sum((r.get("cost_usd") or 0) for r in rows)
    print(f"\n=== {args.stack}: {hits}/{len(rows)} canaries found | ${cost:.2f} ===")
    for r in rows:
        print(f"  {'HIT ' if r.get('found') else 'MISS'} {r['qid']:<20} "
              f"tracked={r['tracked']:<8} depth={r['depth']:<2} fmt={r['format'][:14]:<14} "
              f"calls={r.get('n_tool_calls')} wall={r.get('wall_s')}s")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P2_s0_baseline")
    ap.add_argument("--stack", default="s0_baseline")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--max-turns", type=int, default=25)
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--settings", default=None)
    ap.add_argument("--mcp-config", default=None)
    ap.add_argument("--disallowed", default=None)
    ap.add_argument("--append-system-prompt", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args()

    cans = load_canaries()
    print(f"{len(cans)} canaries loaded")
    if not a.score_only:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=a.parallel) as ex:
            for qid, rc, so, se in ex.map(lambda c: one(c, a), cans):
                print(f"[{qid}] rc={rc} {so}")
        print(f"battery wall {time.time()-t0:.0f}s")
    score(a, cans)
