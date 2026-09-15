#!/usr/bin/env python
"""p10_check_ask.py - Gate R2's real question, about one headless answer.

Plan E §3.4: the answer must end with a Sources block **every line of which names
a page the transcript shows as OPENED**. Nothing is scored against a key -- this
is not a retrieval measurement, it is a check that the citation discipline holds
on a corpus the tool has not been tuned against.

The parsing is the frozen v3 scorer's own (`opened_pairs_v3`,
`citations_and_mentions`, `reconstruct_full_answer`), so this asks exactly the
question the rest of the night asks, rather than a second, slightly different one.

  python p10_check_ask.py --room C
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c_score_live_v3 as V3  # noqa: E402
import c_score_live as V1  # noqa: E402
import p10_cleanroom as CR  # noqa: E402

GUARD_MARKERS = ("OPEN_BEFORE_CITE", "Stop hook", "cited a page")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", default="C")
    ap.add_argument("--jsonl", default=None)
    a = ap.parse_args(argv[1:])

    room = CR.room_dir(a.room)
    raw = Path(a.jsonl) if a.jsonl else (room / "ask.jsonl")
    if not raw.exists():
        raise SystemExit("no transcript at %s" % raw)

    recon = V3.reconstruct_full_answer(raw)
    answer = recon["answer_text_full"]
    opens = V3.opened_pairs_v3(raw, None)
    citations, mentions = V3.citations_and_mentions(answer)

    blob = "\n".join(opens["results"])
    guard_blocks = sum(1 for m in GUARD_MARKERS if m in blob) and sum(
        blob.count(m) for m in GUARD_MARKERS)

    # every citation must name a page that was opened
    unopened = []
    for cp, cpg in sorted(citations):
        if not any(pg == cpg and V1._same_path(rel, cp)
                   for rel, pg in opens["pairs"]):
            unopened.append("%s p%s" % (cp, cpg))

    has_sources = bool(re.search(r"^\s*sources\s*:?\s*$", answer or "",
                                 re.I | re.M)) or "Sources:" in (answer or "")

    out = {
        "room": a.room,
        "transcript": str(raw),
        "answer_chars": len(answer),
        "answer_was_fragment": recon["was_fragment"],
        "n_hook_blocks": recon["n_hook_blocks"],
        "has_sources_block": has_sources,
        "n_sources": len(citations),
        "n_mentions": len(mentions),
        "n_opened": len(opens["pairs"]),
        "n_opens_from_output": opens["n_opens_from_output"],
        "n_opens_from_command": opens["n_opens_from_command"],
        "sources_unopened": unopened,
        "sources_all_opened": (len(citations) > 0 and not unopened),
        "guard_blocks": recon["n_hook_blocks"],
        "scorer": "c_score_live_v3.py (frozen)",
    }

    rec_p = room / "room.json"
    if rec_p.exists():
        rec = json.loads(rec_p.read_text(encoding="utf-8"))
        rec["ask"] = out
        rec_p.write_text(json.dumps(rec, indent=1), encoding="utf-8")

    print(json.dumps(out, indent=1))
    return 0 if out["sources_all_opened"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
