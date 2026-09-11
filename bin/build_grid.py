#!/usr/bin/env python
"""build_grid.py - phase 8. Assemble GRID.md from the scored summaries on disk.

Written as a script rather than composed by hand at the end, because night 1's
write-up was composed from memory after the fact and that is how a headline came
to contradict a table inside its own document. Every cell here is read from a
summary file or is explicitly "not run - <reason>". There are no empty cells:
a stack with no summary gets a stated reason.

  python bin\\build_grid.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L

STACKS = ["s0_baseline", "s1_policy", "s2_hook", "s3_hybrid", "s4_pdfmcp", "s5_recoll"]
TREES = ["h15000", "raship"]


def load(name):
    p = L.SCORES / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def not_run_reason(stack, tree):
    """Why a cell is missing, read from the run state rather than guessed."""
    cell = L.STATE / "cells" / f"{stack}__{tree}.json"
    if cell.exists():
        try:
            c = json.loads(cell.read_text(encoding="utf-8"))
            inst = c.get("steps", {}).get("install")
            if isinstance(inst, str) and inst.startswith("failed"):
                return f"install failed - {inst}"
        except Exception:
            pass
    reasons = L.STATE / "not_run_reasons.json"
    if reasons.exists():
        try:
            r = json.loads(reasons.read_text(encoding="utf-8"))
            if f"{stack}__{tree}" in r:
                return "not run - " + r[f"{stack}__{tree}"]
            if stack in r:
                return "not run - " + r[stack]
        except Exception:
            pass
    return "not run - no result on disk"


def cell_for(stack, tree):
    can = load(f"summary_canaries__{stack}__{tree}.json")
    q = load(f"summary__{stack}__rung15000.json") if tree == "h15000" else None
    if not can:
        reason = not_run_reason(stack, tree)
        return {"canary": reason, "question": reason if tree == "h15000" else "n/a",
                "cost": reason, "tools": "-", "wall": "-", "excluded": "-",
                "stale": False}
    partial = " (PARTIAL)" if can.get("battery_is_stale") else ""
    ex = can.get("excluded_by_design_row", {})
    return {
        "canary": can.get("answer_recall", "-") + partial,
        "retrieval": can.get("retrieval_recall", "-"),
        "question": (f"{q.get('mean_retrieval_recall')}" if q else
                     ("n/a" if tree == "raship" else "not run - no question battery")),
        "cost": f"${can.get('cost_usd_total')} ({can.get('cost_n_of_m')})",
        "tools": can.get("total_tool_calls", "-"),
        "wall": (f"{can.get('mean_wall_s_excl_suspended')}s"
                 + (f" [{can['n_suspended_excluded_from_timing']} suspended excl]"
                    if can.get("n_suspended_excluded_from_timing") else "")),
        "excluded": f"{ex.get('answer_found', '-')}/{ex.get('n', '-')}",
        "timeouts": can.get("timeouts"),
        "stale": can.get("battery_is_stale"),
    }


def setup_time(stack):
    p = L.STATE / "setup_times.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get(stack, "-")
        except Exception:
            pass
    return "-"


def main():
    rows = []
    for s in STACKS:
        h = cell_for(s, "h15000")
        r = cell_for(s, "raship")
        rows.append((s, h, r))

    out = []
    out.append("# GRID — night 2, " + time.strftime("%Y-%m-%d"))
    out.append("")
    out.append("Every cell is a number, `not run — <reason>`, or `install failed — "
               "<error>`. No empty cells.")
    out.append("")
    out.append("`canary recall` is **answer recall**: the answer named enough of the "
               "path to address the file. `retrieval` is the stricter question of "
               "whether the session actually opened it — see the caveat below the "
               "table, it is not comparable across stacks.")
    out.append("")
    out.append("| stack | harness-15k canary | harness-15k question | ra-ship canary | "
               "ra-ship retrieval | cost (n/m) | tool calls | wall (excl. suspended) | "
               "setup | excluded-by-design |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for s, h, r in rows:
        out.append(
            f"| **{s}** | {h['canary']} | {h['question']} | {r['canary']} | "
            f"{r.get('retrieval', '-')} | {r['cost']} | {r['tools']} | {r['wall']} | "
            f"{setup_time(s)} | h15k {h['excluded']} / ra-ship {r['excluded']} |")
    out.append("")
    dest = L.FINDINGS / "GRID.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.read_text(encoding="utf-8") if dest.exists() else ""
    marker = "<!-- TABLE:AUTO -->"
    table = marker + "\n" + "\n".join(out) + "\n" + marker
    if marker in existing:
        pre, _, rest = existing.partition(marker)
        _, _, post = rest.partition(marker)
        dest.write_text(pre + table + post, encoding="utf-8")
    else:
        dest.write_text(table + "\n", encoding="utf-8")
    print("\n".join(out))
    print(f"\nwritten: {dest}")


if __name__ == "__main__":
    main()
