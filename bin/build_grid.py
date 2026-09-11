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


def short_reason(stack, tree):
    """Cells get a short reason plus a footnote marker; the full text is printed
    once below the table. A three-line reason repeated across six columns makes
    the table unreadable, which defeats the point of having one."""
    full = not_run_reason(stack, tree)
    if full.startswith("install failed"):
        return "install failed[^" + stack + "]", full
    head = full.split(".")[0].replace("not run - ", "")
    if len(head) > 44:
        head = head[:41] + "..."
    return f"not run[^{stack}] — {head}", full


def cell_for(stack, tree, notes):
    can = load(f"summary_canaries__{stack}__{tree}.json")
    q = load(f"summary__{stack}__rung15000.json") if tree == "h15000" else None
    # The canary battery and the question battery are independent: a tree can have
    # one without the other, and an early build dropped a real question result on
    # the floor because no canary battery had run on that tree yet.
    qcell = "n/a"
    if tree == "h15000":
        if q:
            qcell = (f"{q.get('mean_retrieval_recall')} "
                     f"({q.get('questions_with_zero_recall')}/{q.get('n_questions')} zero, "
                     f"{q.get('total_forbidden_citations')} forbidden, "
                     f"absence {q.get('absence_correct')})")
        else:
            qcell = short_reason(stack, tree)[0]

    if not can:
        short, full = short_reason(stack, tree)
        notes[stack] = full
        return {"canary": short, "retrieval": "-", "question": qcell,
                "cost": (f"${q.get('total_cost_usd')} ({q.get('cost_n_of_m')}) [questions]"
                         if q else "-"),
                "tools": "-",
                "wall": f"{q.get('mean_wall_s_excl_suspended')}s [questions]" if q else "-",
                "excluded": "-", "stale": False}

    # Provenance. A summary file from night 1 sits in the same directory with the
    # same name shape as tonight's. Without this check the grid would silently
    # present a night-1 number as a night-2 result, which is exactly the class of
    # error this whole run exists to remove.
    ph = str(can.get("phase", ""))
    old = "" if ph.startswith("P7_") else " **[night 1]**"
    partial = " (PARTIAL)" if can.get("battery_is_stale") else ""
    partial += old
    ex = can.get("excluded_by_design_row", {})
    return {
        "canary": can.get("answer_recall", "-") + partial,
        "retrieval": can.get("retrieval_recall", "-"),
        "question": qcell,
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
    notes = {}
    for s in STACKS:
        h = cell_for(s, "h15000", notes)
        r = cell_for(s, "raship", notes)
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
    if notes:
        out.append("**Why a cell was not run:**")
        out.append("")
        for k in sorted(notes):
            out.append(f"[^{k}]: **{k}** — {notes[k]}")
        out.append("")
    if any("[night 1]" in str(c) for _, h, r in rows for c in (h, r)):
        out.append("A cell marked **[night 1]** is a re-scored night-1 battery, not a "
                   "measurement taken tonight. It is shown so the row is not empty, and "
                   "it must not be compared against a night-2 cell as though the "
                   "instrument were the same — it was not.")
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
