#!/usr/bin/env python
"""rescore_night1.py - grid-run phase 0.2, second half.

Re-scores the two night-1 batteries with the fixed scorer and prints, per canary,
what the old rule said versus what the new rule says and WHY. The headline pair
(6/13 baseline, 12/13 hook) was produced by a rule that counted any mention of any
README as finding 02_Source_Documents_Read_Only/README.md, so both numbers are
suspect until this runs.

Reads results only. Writes a re-score json next to the other scores. Never
re-runs a session -- the point is to re-grade evidence already on disk.

  set CANARY_MANIFEST=<pass-1 manifest>
  python bin\\rescore_night1.py
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L
import scoring

BATTERIES = [
    ("P2_s0_baseline", "s0_baseline", "night-1 stock Claude Code on ra-ship"),
    ("P5_s2_canaries", "s2_hook", "night-1 FTS5 index + front-door hook on ra-ship"),
]


def load_manifest():
    rows = []
    with open(L.canary_manifest(), newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if not r.get("canary_phrase"):
                continue
            phrase = r["canary_phrase"]
            rows.append({
                "qid": phrase.split("-")[0] + "_" + phrase[-6:],
                "expect": r["relative_path"],
                "format": r.get("format", ""),
                "depth": r.get("depth", ""),
                "in_venv": r.get("in_venv", ""),
                "tracked": r.get("tracked_status", ""),
            })
    return rows


def main():
    cans = load_manifest()
    out = {"canaries": len(cans), "batteries": []}
    for phase, stack, desc in BATTERIES:
        outdir = L.RUNS / phase
        rows = []
        for c in cans:
            f = outdir / f"{stack}__raship__{c['qid']}.json"
            if not f.exists():
                rows.append({**c, "status": "no_result_file"})
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            s = scoring.score_one(d, c["expect"])
            rows.append({
                **c,
                "old_found": scoring.legacy_found(d.get("answer_text"), c["expect"]),
                **s,
                "n_tool_calls": d.get("n_tool_calls"),
                "wall_s": d.get("wall_s"),
                "cost_usd": d.get("cost_usd"),
                "timed_out": d.get("timed_out"),
                "answer_head": (d.get("answer_text") or "")[:160],
            })
        scored = [r for r in rows if "answer_found" in r]
        old = sum(1 for r in scored if r.get("old_found"))
        new = sum(1 for r in scored if r.get("answer_found"))
        ret = sum(1 for r in scored if r.get("retrieval_found"))
        b = {
            "phase": phase, "stack": stack, "description": desc,
            "n_results": len(scored), "n_canaries": len(cans),
            "old_rule_found": old, "new_rule_found": new,
            "retrieval_found": ret,
            "downgraded": [r["expect"] for r in scored
                           if r.get("old_found") and not r.get("answer_found")],
            "rows": rows,
        }
        out["batteries"].append(b)

        print(f"\n=== {stack} ({desc}) ===")
        print(f"  night-1 rule : {old}/{len(scored)}")
        print(f"  fixed rule   : {new}/{len(scored)}   (answer names the path)")
        print(f"  retrieval    : {ret}/{len(scored)}   (session actually opened it)")
        for r in scored:
            mark = ""
            if r.get("old_found") and not r.get("answer_found"):
                mark = "  <-- WAS A FALSE HIT"
            print(f"   old={'HIT ' if r.get('old_found') else 'miss'} "
                  f"new={'HIT ' if r.get('answer_found') else 'miss'} "
                  f"ret={'Y' if r.get('retrieval_found') else 'n'} "
                  f"[{r.get('answer_match_rule')}] {r['expect'][:70]}{mark}")

    dest = L.SCORES / "rescore_night1_fixed_scorer.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten: {dest}")
    return out


if __name__ == "__main__":
    main()
