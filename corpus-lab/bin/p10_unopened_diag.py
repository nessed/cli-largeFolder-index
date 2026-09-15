#!/usr/bin/env python
"""p10_unopened_diag.py - why does THIS question carry a cited_unopened?

Plan E Phase 1.6 / Gate T. v3 disagreed with the independent audit on which
questions carry open-before-cite violations, in both directions. Deciding
whether v3 or the audit is right needs the structure of one session: what the
answer cited, what the session opened, and which cited pair failed to match.

Prints structure only -- the citation pairs, the opened pairs, and the match
result. It does not print answer prose, tool output, or any value.

  python p10_unopened_diag.py --phase P9O_live --qid pl_01 mb_04
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c_score_live as V1  # noqa: E402
import c_score_live_v3 as V3  # noqa: E402


def short(p, keep=2):
    """Last `keep` path segments -- enough to tell two documents apart, not
    enough to be a corpus listing."""
    segs = [s for s in str(p).split("/") if s]
    return "/".join(segs[-keep:])


def diag(phase, qid):
    rec, raw = V1.load_rec(phase, qid)
    if rec is None:
        print("%s %s: no result" % (phase, qid))
        return
    opens = V3.opened_pairs_v3(raw, rec)
    recon = V3.reconstruct_full_answer(raw)
    answer = recon["answer_text_full"] or (rec.get("answer_text") or "")
    citations, mentions = V3.citations_and_mentions(answer)

    print("=" * 72)
    print("%s / %s" % (phase, qid))
    print("  answer: recorded=%d chars, full=%d chars, fragment=%s, hook_blocks=%d"
          % (len(rec.get("answer_text") or ""), len(answer),
             recon["was_fragment"], recon["n_hook_blocks"]))
    print("  opens: from_output=%d from_command=%d loop_only=%d  (%d distinct paths)"
          % (opens["n_opens_from_output"], opens["n_opens_from_command"],
             opens["n_opens_loop_only"], len(opens["paths"])))
    print("  opened pairs:")
    for rel, pg in sorted(opens["pairs"]):
        print("      p%-5s %s" % (pg, short(rel)))
    print("  citations (%d):" % len(citations))
    for cp, cpg in sorted(citations):
        matched = [op for op in opens["paths"] if V1._same_path(cp, op)]
        same_page = any(pg == cpg and V1._same_path(rel, cp)
                        for rel, pg in opens["pairs"])
        print("      p%-5s %-40s path_opened=%s same_page_opened=%s"
              % (cpg, short(cp), bool(matched), same_page))
    print("  mentions (%d): %s" % (len(mentions),
                                   ", ".join(sorted(short(m) for m in mentions))))
    unopened = [cp for cp in {c[0] for c in citations}
                if not any(V1._same_path(cp, op) for op in opens["paths"])]
    print("  => cited_unopened = %d  %s"
          % (len(unopened), [short(u) for u in unopened]))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True)
    ap.add_argument("--qid", nargs="+", required=True)
    a = ap.parse_args(argv[1:])
    for q in a.qid:
        diag(a.phase, q)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
