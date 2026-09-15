#!/usr/bin/env python
"""p10_hook_probe.py - the SHAPE of a Stop-hook interruption in the stream.

Plan E Phase 1.3 has to reconstruct the complete answer across a guard
interruption: the harness keeps the LAST assistant message, so in a session the
guard challenged, the recorded `answer_text` can be just the post-guard reply
("Confirmed -- the citation stands.") and the real answer is the assistant text
immediately BEFORE the hook block.

To write that reconstruction correctly, the event shape has to be known rather
than guessed. This prints the JSON KEY PATHS around each Stop-hook event and the
LENGTHS of the text blocks either side -- never the text itself.

  python p10_hook_probe.py --phase P9S_live [--limit 3]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402


def keypaths(o, prefix="", out=None, depth=0):
    if out is None:
        out = []
    if depth > 6:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            kp = prefix + "." + str(k) if prefix else str(k)
            if isinstance(v, (dict, list)):
                keypaths(v, kp, out, depth + 1)
            else:
                out.append("%s=<%s len=%s>" % (
                    kp, type(v).__name__,
                    len(v) if isinstance(v, str) else ""))
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            keypaths(v, "%s[%d]" % (prefix, i), out, depth + 1)
    return out


def probe(phase, limit):
    shown = 0
    for jl in sorted((L.RUNS / phase).glob("*.jsonl")):
        events = []
        for line in jl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
        hook_idx = [i for i, d in enumerate(events)
                    if "Stop hook" in json.dumps(d)]
        if not hook_idx:
            continue
        print("=" * 70)
        print("session %s : %d event(s) mention a Stop hook, %d events total"
              % (jl.stem.split("__")[-1], len(hook_idx), len(events)))
        i = hook_idx[0]
        for j in range(max(0, i - 2), min(len(events), i + 3)):
            d = events[j]
            mark = " <-- HOOK" if j in hook_idx else ""
            kinds = []
            for c in (d.get("message", {}) or {}).get("content", []) or []:
                if isinstance(c, dict):
                    kinds.append("%s(len=%s)" % (
                        c.get("type"),
                        len(c.get("text") or "") if c.get("type") == "text" else "-"))
            print("  [%d] type=%s content=%s%s"
                  % (j, d.get("type"), ",".join(kinds) or "-", mark))
            if j == i:
                for kp in keypaths(d)[:25]:
                    print("        " + kp)
        shown += 1
        if shown >= limit:
            return


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--limit", type=int, default=3)
    a = ap.parse_args(argv[1:])
    probe(a.phase, a.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
