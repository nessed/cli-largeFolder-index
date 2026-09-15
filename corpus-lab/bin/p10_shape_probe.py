#!/usr/bin/env python
"""p10_shape_probe.py - what SHAPES does a recorded session contain?

Plan E Phase 1 needs three parsing facts about the recordings before the v3
scorer can be written:

  * how an `OPENED <rel> p<N>` line appears in a tool result, and how often it
    appears with no matching `open ... <N>` in any command string (the loop-open
    case that made v1 undercount opens);
  * how a Stop-hook block appears in the stream, so the assistant text BEFORE it
    can be recovered (the fragment case);
  * how many sessions carry each.

It prints COUNTS AND SHAPE NAMES ONLY -- never answer text, never a corpus path,
never a value. Structure is what the scorer needs; content is what the
contamination rule keeps out.

  python p10_shape_probe.py --phase P9O_live [--phase P9S_live ...]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import c_score_live as V1  # noqa: E402

OPENED_LINE = re.compile(r"^OPENED\s+(?P<rel>.+?)\s+p(?P<page>\d+)\s*$", re.M)


def event_types(raw):
    """Every (type, subtype) pair in the stream, counted."""
    c = Counter()
    hook_keys = Counter()
    for line in Path(raw).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            c["<unparseable>"] += 1
            continue
        t = d.get("type")
        c[str(t)] += 1
        blob = json.dumps(d)
        for marker in ("stop_hook", "Stop hook", "stopHook", "hook_event_name",
                       "OPEN_BEFORE_CITE", "PreToolUse", "Stop"):
            if marker in blob:
                hook_keys["%s:%s" % (t, marker)] += 1
    return c, hook_keys


def probe_phase(phase, sample_ids=None):
    key_dir = L.RUNS / phase
    rows = []
    for jl in sorted(key_dir.glob("*.jsonl")):
        qid = jl.stem.split("__")[-1]
        if sample_ids and qid not in sample_ids:
            continue
        results, bash_cmds, texts = V1.read_transcript(jl)
        blob = "\n".join(results)
        opened_out = set()
        for m in OPENED_LINE.finditer(blob):
            opened_out.add((m.group("rel").strip(), int(m.group("page"))))
        opened_cmd = set(V1.opens_from_bash(bash_cmds))

        # normalise both sides the way the scorer will, to compare fairly
        import scoring as SC
        norm_out = {(SC.norm_path(r), p) for r, p in opened_out}
        loop_only = norm_out - opened_cmd

        ev, hooks = event_types(jl)
        rows.append({
            "q_id": qid,
            "n_opened_lines_in_output": len(norm_out),
            "n_opens_from_command": len(opened_cmd),
            "n_opens_loop_only": len(loop_only),
            "n_assistant_text_blocks": len(texts),
            "n_bash_cmds": len(bash_cmds),
            "has_for_loop": any(re.search(r"\bfor\s+\w+\s+in\b", c) for c in bash_cmds),
            "event_types": dict(ev),
            "hook_markers": dict(hooks),
        })
    return rows


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", action="append", required=True)
    ap.add_argument("--ids", default=None,
                    help="comma-separated q_id suffixes to restrict to")
    a = ap.parse_args(argv[1:])
    ids = set(a.ids.split(",")) if a.ids else None
    out = {}
    for ph in a.phase:
        rows = probe_phase(ph, ids)
        out[ph] = {
            "n_sessions": len(rows),
            "n_with_loop_only_opens": sum(1 for r in rows if r["n_opens_loop_only"]),
            "total_loop_only_opens": sum(r["n_opens_loop_only"] for r in rows),
            "n_with_for_loop": sum(1 for r in rows if r["has_for_loop"]),
            "event_type_union": sorted(
                {k for r in rows for k in r["event_types"]}),
            "hook_marker_union": sorted(
                {k for r in rows for k in r["hook_markers"]}),
            "rows": rows,
        }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
