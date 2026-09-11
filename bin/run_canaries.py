#!/usr/bin/env python
"""run_canaries.py - canary battery for any stack against any corpus.

One headless Claude Code session per canary phrase, in parallel, via ask.py.
Sessions are never batched: recall only means something if question 5 cannot
benefit from what question 2 found.

Grid-run phase changes:
  0.2  scoring moved to scoring.py -- the answer must ADDRESS the file (full path
       or last two segments), not merely mention a common basename. Retrieval is
       scored separately from answer text.
  0.3  --disallowedTools is on by default in ask.py; checksums are a separate step
       (checksums.py) run either side of the battery by the phase-7 driver.
  0.7  cost is reported as a total PLUS an explicit n-of-m, and timing excludes
       suspended sessions. Two totals with different n are never compared silently.
  0.10 skipped (stale-result) questions are counted and shouted about; a battery
       with any skips is marked stale in its own summary.
  2.3  the manifest path comes from CANARY_MANIFEST only. Reading this script
       tells you the name of an env var, not the location of the answer key.

  set CANARY_MANIFEST=<manifest.csv>
  python bin\\run_canaries.py --phase P7_s2 --stack s2_hook --corpus-kind raship
  python bin\\run_canaries.py --phase P7_s2 --stack s2_hook --corpus-kind rung --rung 15000
  python bin\\run_canaries.py --stack s2_hook --corpus-label raship --score-only
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L
import scoring

RED = "\033[1;31m"
OFF = "\033[0m"

QUESTION = (
    "Somewhere in this repository there is exactly one file containing the literal "
    "string `{phrase}`. Find it. Reply with ONLY the path of that file relative to the "
    "repository root, or the exact text NOT_FOUND if you are confident it is not here."
)

# Phase 7.4: one pass-1 canary lives under site-packages, which index_build.py
# excludes by design. Every index-based stack has a hard ceiling on it; grep-based
# S0 does not. It is scored as its own row, never folded into the headline.
EXCLUDED_BY_DESIGN_MARKERS = ("site-packages", "02_tool_runs")


def qid_for(phrase):
    return phrase.split("-")[0] + "_" + phrase[-6:]


def load_canaries(corpus_root):
    """Read the manifest. Tolerates the pass-1 and pass-2 shapes."""
    rows = []
    with open(L.canary_manifest(), newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            phrase = (r.get("canary_phrase") or r.get("phrase") or "").strip()
            if not phrase:
                continue
            rel = (r.get("relative_path") or "").strip()
            ap = (r.get("absolute_path") or "").strip()
            if not rel and ap:
                try:
                    rel = str(Path(ap).relative_to(Path(corpus_root)))
                except Exception:
                    rel = Path(ap).name
            rows.append({
                "qid": (r.get("qid") or "").strip() or qid_for(phrase),
                "phrase": phrase,
                "expect": scoring.norm_path(rel),
                "abs": ap,
                "depth": r.get("depth", ""),
                "format": r.get("format", ""),
                "tracked": r.get("tracked_status", ""),
                "in_venv": r.get("in_venv", ""),
                "cases": r.get("cases_covered", ""),
                "created": r.get("injected_or_created", ""),
                "page_index": r.get("page_index", ""),
                "printed_page_label": r.get("printed_page_label", ""),
                "excluded_by_design": any(
                    m in scoring.norm_path(rel) for m in EXCLUDED_BY_DESIGN_MARKERS),
            })
    return rows


def one(c, args, corpus_root, corpus_label):
    cmd = [sys.executable, str(L.ASK),
           "--phase", args.phase, "--stack", args.stack,
           "--corpus", str(corpus_root), "--corpus-label", corpus_label,
           "--qid", c["qid"], "--question", QUESTION.format(phrase=c["phrase"]),
           "--model", args.model, "--max-turns", str(args.max_turns),
           "--timeout", str(args.timeout)]
    if args.settings:
        cmd += ["--settings", args.settings]
    if args.mcp_config:
        cmd += ["--mcp-config", args.mcp_config]
    if args.disallowed is not None:
        cmd += ["--disallowed", args.disallowed]
    if args.append_system_prompt:
        cmd += ["--append-system-prompt", args.append_system_prompt]
    if args.force:
        cmd += ["--force"]
    # The child must not inherit the manifest location.
    env = dict(os.environ)
    env.pop("CANARY_MANIFEST", None)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env)
    return c["qid"], p.returncode, (p.stdout or "").strip()[-300:], (p.stderr or "")[-400:]


def score(args, canaries, corpus_label, n_skipped=0):
    outdir = L.RUNS / args.phase
    rows = []
    for c in canaries:
        f = outdir / f"{args.stack}__{corpus_label}__{c['qid']}.json"
        if not f.exists():
            rows.append({**{k: v for k, v in c.items() if k != "phrase"},
                         "status": "no_result_file"})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        s = scoring.score_one(d, c["expect"])
        opened = [x["path"] for x in d.get("files_opened", []) if x.get("path")]
        rows.append({
            **{k: v for k, v in c.items() if k != "phrase"},
            **s,
            "n_tool_calls": d.get("n_tool_calls"),
            "n_files_opened": d.get("n_files_opened"),
            "venv_noise": sum(1 for p in opened
                              if "02_tool_runs" in p or "site-packages" in p),
            "wall_s": d.get("wall_s"),
            "suspended": d.get("suspended"),
            "cost_usd": d.get("cost_usd"),
            "cost_missing": d.get("cost_missing"),
            "timed_out": d.get("timed_out"),
            "stream_json_ok": d.get("stream_json_ok"),
            "tools": d.get("tool_histogram", {}),
            "answer": (d.get("answer_text") or "")[:200],
        })

    scored = [r for r in rows if "answer_found" in r]
    headline = [r for r in scored if not r.get("excluded_by_design")]
    excluded = [r for r in scored if r.get("excluded_by_design")]

    # 0.7 - cost as total plus explicit n-of-m; never a bare total.
    with_cost = [r for r in scored if r.get("cost_usd") is not None]
    cost_total = round(sum(r["cost_usd"] for r in with_cost), 4)
    # 0.6 - suspended sessions are excluded from timing and reported separately.
    timed = [r for r in scored if not r.get("suspended") and not r.get("timed_out")]
    susp = [r for r in scored if r.get("suspended")]

    summary = {
        "stack": args.stack, "phase": args.phase, "corpus": corpus_label,
        "n_canaries": len(canaries), "n_results": len(scored),
        "answer_recall": f"{sum(1 for r in headline if r['answer_found'])}/{len(headline)}",
        "retrieval_recall": f"{sum(1 for r in headline if r['retrieval_found'])}/{len(headline)}",
        "excluded_by_design_row": {
            "n": len(excluded),
            "answer_found": sum(1 for r in excluded if r["answer_found"]),
            "note": "under site-packages; index_build.py excludes it by design, "
                    "so index stacks have a hard ceiling here and grep-based S0 does not",
        },
        "false_not_found": sum(1 for r in headline
                               if r["said_not_found"] and not r["answer_found"]),
        "cost_usd_total": cost_total,
        "cost_n_of_m": f"{len(with_cost)}/{len(scored)}",
        "cost_warning": (None if len(with_cost) == len(scored) else
                         f"{len(scored) - len(with_cost)} session(s) reported no cost "
                         f"(timeout/crash); this total is NOT comparable to a total "
                         f"with a different n"),
        "mean_wall_s_excl_suspended": (
            round(sum(r["wall_s"] or 0 for r in timed) / len(timed), 1) if timed else None),
        "n_suspended_excluded_from_timing": len(susp),
        "total_tool_calls": sum(r.get("n_tool_calls") or 0 for r in scored),
        "timeouts": sum(1 for r in scored if r.get("timed_out")),
        "not_stream_json": sum(1 for r in scored if r.get("stream_json_ok") is False),
        "n_skipped_stale": n_skipped,
        "battery_is_stale": n_skipped > 0,
        "n_missing_results": len(rows) - len(scored),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    L.SCORES.mkdir(parents=True, exist_ok=True)
    (L.SCORES / f"canaries__{args.stack}__{corpus_label}.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    (L.SCORES / f"summary_canaries__{args.stack}__{corpus_label}.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== {args.stack} on {corpus_label} ===")
    for r in scored:
        tag = " [excluded-by-design]" if r.get("excluded_by_design") else ""
        print(f"  {'HIT ' if r['answer_found'] else 'MISS'} "
              f"ret={'Y' if r['retrieval_found'] else 'n'} {r['qid']:<18} "
              f"fmt={str(r.get('format'))[:16]:<16} calls={r.get('n_tool_calls')} "
              f"wall={r.get('wall_s')}s{tag}")
    if n_skipped:
        print(f"{RED}### {n_skipped} question(s) SKIPPED as already-present. "
              f"THIS BATTERY IS STALE.{OFF}", file=sys.stderr)
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="P2_s0_baseline")
    ap.add_argument("--stack", default="s0_baseline")
    ap.add_argument("--corpus-kind", choices=["raship", "rung"], default="raship")
    ap.add_argument("--rung", default="15000")
    ap.add_argument("--corpus-label", default=None)
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

    if a.corpus_kind == "raship":
        corpus_root, label = L.RASHIP, "raship"
    else:
        corpus_root, label = L.rung(a.rung), f"h{a.rung}"
    label = a.corpus_label or label

    cans = load_canaries(corpus_root)
    print(f"{len(cans)} canaries loaded | corpus={corpus_root} label={label}")

    n_skipped = 0
    if not a.score_only:
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=a.parallel) as ex:
            for qid, rc, so, se in ex.map(lambda c: one(c, a, corpus_root, label), cans):
                if rc == 3:
                    n_skipped += 1
                    print(f"{RED}[{qid}] SKIPPED-STALE{OFF}", file=sys.stderr)
                print(f"[{qid}] rc={rc} {so}")
        print(f"battery wall {time.monotonic() - t0:.0f}s")
    score(a, cans, label, n_skipped)
