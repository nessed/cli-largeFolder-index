#!/usr/bin/env python
"""rescore_from_results.py - re-score evidence contact from tool RESULTS, not just inputs.

WHY THIS EXISTS
---------------
`ask.py` builds `files_opened[]` inside one branch only:

    if t == "assistant":                    # ask.py:201
        ... if c["type"] == "tool_use":     # ask.py:203
            for f in PATH_FIELDS: ...       # ask.py:207-210  <- tool INPUTS

A tool RESULT arrives as a separate stream event, `type == "user"` with a
`tool_result` content block, and that branch does not exist. So every path the
session learned about from a result is invisible to the scorer.

That undercounts the index stacks specifically, and by construction: an S1/S2
session runs `corpus_search.py` and reads its hits, which look like

    Sources/Federal/Demands for Grants/2016-17/... Vol-3.pdf  [page_index=583]  score=-4.76
        ...Provisional estimates place Non-tax >>receipts<< at 573 Rs billion...

The agent has now seen that file's path AND a snippet of its content, and the
old scorer recorded nothing. S0, by contrast, mostly reaches files through
`Read(file_path=...)` — an input — so it was scored nearly in full. The measured
comparison was therefore biased against the very stacks the run was built to test.

WHAT IT DOES NOT DO
-------------------
It does not modify `ask.py` and it does not write into `04_scores/`. It reads the
raw `.jsonl` stream that `ask.py` already saved beside every result, so this costs
nothing and runs no sessions. Output: `state/rescore_from_results.json`.

TIERS - the honest part
-----------------------
Not every path in a result means the same thing, and collapsing them would replace
one bias with a bigger one in the other direction:

  input    a path in a tool's own arguments. The old metric. `Read(file_path=X)`.
  snippet  a path that arrived ATTACHED TO CONTENT of that file - a corpus_search
           hit line, or a Grep match line carrying the matched text. The session
           saw material from the file. This is the fair analogue of "opened".
  listing  a path that arrived as a bare name in a directory or match listing -
           Glob, `ls`, `find`, Grep in files_with_matches mode. The session learned
           the file EXISTS and nothing about what is in it.
  mention  a path-shaped token inside a file's own content (a README naming a CSV)
           or inside subagent metadata. Recorded, never counted.

The headline re-score is **input | snippet**. `listing` is reported separately as an
upper bound, because counting it would hand S0 credit for a `**/*budget*` glob that
printed 200 paths it never looked at - which is exactly how night 1's scorer got
inflated, in the other direction.

BLIND SPOT THAT REMAINS
-----------------------
S0 spawned `Agent` subagents (11 calls). A subagent's file access happens in its own
session and never enters the parent's stream at all. No re-score can recover it.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

# Question batteries only. One phase dir per stack, as run on night 2.
PHASES = {
    "s0_baseline": "P7_s0_baseline_h15000",
    "s1_policy": "P7_s1_policy_h15000",
    "s2_hook": "P7_s2_hook_h15000",
}
CORPUS_LABEL = "harness15000"

EXT = (r"pdf|md|csv|json|txt|docx|xlsx|xls|log|py|html|htm|dta|do|zip|tex|ipynb"
       r"|yaml|yml|parquet|png|jpg|jpeg|tsv|xml|bib|sql|sh|bat|ps1|ini|cfg|toml")

# corpus_search.py hit line: relative path, then [page_index=N], then score.
RE_SEARCH_HIT = re.compile(rf"^\s*(?P<p>\S.*?\.(?:{EXT}))\s+\[page_index=(?P<pg>\d+)\]", re.I)
# ripgrep content mode: path:line:text  (drive letters mean the colon can be 2 chars in)
RE_GREP_CONTENT = re.compile(rf"^(?P<p>(?:[A-Za-z]:)?[^:]*?\.(?:{EXT})):(?P<ln>\d+):", re.I)
# a line that is nothing but a path - Glob output, ls, find, grep -l
RE_BARE_PATH = re.compile(rf"^(?P<p>(?:[A-Za-z]:)?[\w\W]{{1,400}}?\.(?:{EXT}))$", re.I)
# a path-shaped token anywhere in a line (mention tier only)
RE_TOKEN = re.compile(rf"[\w./\\ ()\-&,'+#]+?\.(?:{EXT})", re.I)

RE_NUMBERED_LINE = re.compile(r"^\s*\d+\t")          # Read tool output
RE_RECEIPT = re.compile(r"^\s*(searched|NOT searched|a 'no match')")


def norm_rel(p, root):
    """Corpus-relative, forward-slashed, lowercase. Mirrors ask.py:norm + run_harness:norm."""
    if not p:
        return None
    s = str(p).strip().strip('"').strip("'")
    if not s:
        return None
    try:
        pp = Path(s)
        if pp.is_absolute():
            try:
                rel = os.path.relpath(str(pp), str(root))
            except Exception:
                rel = s
        else:
            rel = s
    except Exception:
        rel = s
    rel = rel.replace("\\", "/").lower().strip()
    while rel.startswith("./") or rel.startswith("/"):
        rel = rel.lstrip("/")
        if rel.startswith("./"):
            rel = rel[2:]
    # a path that climbed out of the corpus is not a corpus file
    if rel.startswith("../") or ":" in rel.split("/")[0]:
        return None
    return rel or None


def result_text(block):
    """tool_result content is a string or a list of {type:text}."""
    c = block.get("content")
    if isinstance(c, list):
        return "\n".join(str(x.get("text", "")) for x in c if isinstance(x, dict))
    return str(c or "")


def classify_result(tool, inp, text, root):
    """-> {path: tier} for one tool result. Tier per the docstring."""
    out = {}
    cmd = json.dumps(inp or {}, ensure_ascii=False)
    is_search = tool == "Bash" and "corpus_search" in cmd
    # Read returns the file's own content; its path is already an input, and tokens
    # inside the content are other files being *named*, not reached.
    read_like = tool in ("Read", "NotebookRead")

    def put(p, tier):
        p = norm_rel(p, root)
        if not p:
            return
        rank = {"snippet": 3, "listing": 2, "mention": 1}
        if rank[tier] > rank.get(out.get(p, "mention"), 0) or p not in out:
            out[p] = tier

    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip() or RE_RECEIPT.match(line):
            continue

        if is_search:
            m = RE_SEARCH_HIT.match(line)
            if m:
                put(m.group("p"), "snippet")
            continue

        if read_like or RE_NUMBERED_LINE.match(line):
            for t in RE_TOKEN.findall(line):
                put(t, "mention")
            continue

        m = RE_GREP_CONTENT.match(line)
        if m and tool in ("Grep", "Bash"):
            put(m.group("p"), "snippet")
            continue

        m = RE_BARE_PATH.match(line.strip())
        if m:
            put(m.group("p"), "listing")
            continue

        for t in RE_TOKEN.findall(line):
            put(t, "mention")
    return out


def walk_stream(jsonl_path, root):
    """Replay one session's raw stream. -> (paths_by_tier, tool_use_names)."""
    calls = {}
    tiers = {}
    rank = {"snippet": 3, "listing": 2, "mention": 1}
    with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type")
            if t == "assistant":
                for c in d.get("message", {}).get("content", []) or []:
                    if c.get("type") == "tool_use":
                        calls[c.get("id")] = (c.get("name"), c.get("input") or {})
            elif t == "user":
                for c in d.get("message", {}).get("content", []) or []:
                    if not isinstance(c, dict) or c.get("type") != "tool_result":
                        continue
                    tool, inp = calls.get(c.get("tool_use_id"), ("?", {}))
                    for p, tier in classify_result(tool, inp, result_text(c), root).items():
                        if rank[tier] > rank.get(tiers.get(p, ""), 0):
                            tiers[p] = tier
    return tiers, calls


def load_key():
    key = json.loads(L.ANSWER_KEY.read_text(encoding="utf-8"))
    return {q["q_id"]: q for q in key["questions"]}


def main():
    key = load_key()
    sample = json.loads(L.QUESTION_SAMPLE.read_text(encoding="utf-8"))
    qids = sample["q_ids"]
    diag = json.loads((L.STATE / "diagnose_recall.json").read_text(encoding="utf-8"))
    indexed17 = [r["q_id"] for r in diag["per_question"]]

    report = {"qids": qids, "indexed17": indexed17, "stacks": {}}

    for stack, phase in PHASES.items():
        rows = {}
        for qid in qids:
            base = L.RUNS / phase / f"{stack}__{CORPUS_LABEL}__{qid}"
            rj, rl = base.with_suffix(".json"), base.with_suffix(".jsonl")
            if not rj.exists():
                rows[qid] = {"status": "no_result"}
                continue
            d = json.loads(rj.read_text(encoding="utf-8"))
            root = d.get("corpus_root") or str(L.rung(15000))
            q = key[qid]
            ev = {norm_rel(a["path"], root) for a in q.get("evidence_addresses", [])}
            ev.discard(None)

            # --- old: exactly run_harness.py:98-104 ---
            opened_old = {norm_rel(x["path"], root)
                          for x in d.get("files_opened", []) if x.get("path")}
            opened_old.discard(None)
            ans_n = (d.get("answer_text") or "").replace("\\", "/").lower()
            cited = {p for p in ev if p in ans_n or p.split("/")[-1] in ans_n}
            reached_old = (opened_old | cited) & ev

            # --- new: add paths learned from RESULTS ---
            tiers, calls = ({}, {})
            if rl.exists():
                tiers, calls = walk_stream(rl, root)
            snip = {p for p, t in tiers.items() if t == "snippet"}
            listed = {p for p, t in tiers.items() if t == "listing"}
            reached_new = (opened_old | cited | snip) & ev
            reached_loose = (opened_old | cited | snip | listed) & ev
            # strictest tier: tool inputs alone, no answer-text credit. This is what
            # diagnose_recall.py:70-74 counts, and why its 4/0/0 differs from
            # run_harness.py's recall, which also credits a cited path.
            reached_inputonly = opened_old & ev

            n_ev = len(ev)
            rows[qid] = {
                "status": "ok",
                "type": q["type"],
                "n_evidence": n_ev,
                "recall_old": round(len(reached_old) / n_ev, 3) if n_ev else None,
                "recall_new": round(len(reached_new) / n_ev, 3) if n_ev else None,
                "recall_loose": round(len(reached_loose) / n_ev, 3) if n_ev else None,
                "n_reached_inputonly": len(reached_inputonly),
                "n_reached_old": len(reached_old),
                "n_reached_new": len(reached_new),
                "n_reached_loose": len(reached_loose),
                "surfaced_by_search": sorted(snip & ev),
                "opened_after_surfacing": sorted(snip & ev & opened_old),
                "gained_by_snippet": sorted(reached_new - reached_old),
                "gained_by_listing": sorted(reached_loose - reached_new),
                "n_paths_snippet": len(snip),
                "n_paths_listing": len(listed),
                "n_files_opened_old": len(opened_old),
                "n_agent_calls": sum(1 for n, _ in calls.values() if n == "Agent"),
                "timed_out": d.get("timed_out"),
            }
        report["stacks"][stack] = rows

    # ---------------- printing ----------------
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    def hdr(t):
        print("\n" + t)
        print("=" * len(t))

    hdr("MEAN RETRIEVAL RECALL - old (inputs only) vs new (inputs + result snippets)")
    print(f"{'stack':<14}{'n':>4}{'old':>9}{'new':>9}{'delta':>9}"
          f"{'loose':>9}   published")
    published = {"s0_baseline": 0.167, "s1_policy": 0.176, "s2_hook": 0.118}
    for stack, rows in report["stacks"].items():
        ok = [r for r in rows.values() if r.get("status") == "ok"]
        o, n = mean([r["recall_old"] for r in ok]), mean([r["recall_new"] for r in ok])
        lo = mean([r["recall_loose"] for r in ok])
        d = None if (o is None or n is None) else round(n - o, 3)
        print(f"{stack:<14}{len(ok):>4}{o:>9}{n:>9}{('+' + str(d)) if d else '  0.0':>9}"
              f"{lo:>9}   {published[stack]}")
    print("\n  old == published confirms this re-scorer reproduces run_harness.py exactly.")
    print("  loose also credits bare directory listings - an upper bound, not a result.")

    hdr("EVIDENCE-REACHED - questions where >=1 correct evidence file was reached")
    print("  (the 17 questions whose evidence is fully indexed, as used by diagnose_recall.py)")
    print(f"\n{'stack':<14}{'inputs only':>13}{'+cited':>10}{'+snippet':>10}"
          f"{'+listing':>10}   diagnose_recall.json")
    diag_pub = {"s0_baseline": 4, "s1_policy": 0, "s2_hook": 0}
    for stack, rows in report["stacks"].items():
        c = {}
        for k in ("inputonly", "old", "new", "loose"):
            c[k] = sum(1 for q in indexed17
                       if rows.get(q, {}).get(f"n_reached_{k}", 0) > 0)
        print(f"{stack:<14}{str(c['inputonly']) + '/17':>13}{str(c['old']) + '/17':>10}"
              f"{str(c['new']) + '/17':>10}{str(c['loose']) + '/17':>10}"
              f"   {diag_pub[stack]}/17")
    print("\n  'inputs only' is diagnose_recall.py's tier and must match its column.")
    print("  '+cited' adds answer-text citations, which run_harness.py credits.")

    hdr("PER-QUESTION DIFF - only questions whose recall moved")
    any_moved = False
    for stack, rows in report["stacks"].items():
        moved = [(q, r) for q, r in rows.items()
                 if r.get("status") == "ok" and r.get("recall_new") != r.get("recall_old")]
        print(f"\n-- {stack}: {len(moved)} of 20 moved")
        if not moved:
            print("   (none)")
            continue
        any_moved = True
        for q, r in moved:
            print(f"   {q:<7} {r['type']:<20} {r['recall_old']} -> {r['recall_new']}"
                  f"   ({r['n_reached_old']}/{r['n_evidence']} -> "
                  f"{r['n_reached_new']}/{r['n_evidence']})")
            for p in r["gained_by_snippet"]:
                print(f"           + {p}")
    if not any_moved:
        print("\n   Nothing moved under the snippet tier.")

    hdr("PATH VOLUME - how much the old scorer could not see")
    print(f"{'stack':<14}{'inputs':>9}{'snippet':>9}{'listing':>9}{'Agent':>8}")
    for stack, rows in report["stacks"].items():
        ok = [r for r in rows.values() if r.get("status") == "ok"]
        print(f"{stack:<14}{sum(r['n_files_opened_old'] for r in ok):>9}"
              f"{sum(r['n_paths_snippet'] for r in ok):>9}"
              f"{sum(r['n_paths_listing'] for r in ok):>9}"
              f"{sum(r['n_agent_calls'] for r in ok):>8}")

    hdr("RANKER SURFACED vs AGENT USED - the decomposition the old metric hid")
    print("  of the 17 fully-indexed questions: in how many did a search result contain a")
    print("  correct evidence file, and in how many of those did the agent then OPEN it?")
    print(f"\n{'stack':<14}{'surfaced':>10}{'then opened':>13}{'ignored':>9}")
    for stack, rows in report["stacks"].items():
        surf = [q for q in indexed17 if rows.get(q, {}).get("surfaced_by_search")]
        used = [q for q in surf if rows[q].get("opened_after_surfacing")]
        print(f"{stack:<14}{str(len(surf)) + '/17':>10}{str(len(used)) + '/' + str(len(surf)):>13}"
              f"{len(surf) - len(used):>9}")
    print("\n  S0 has no search front door, so 'surfaced' there means a Grep match line.")

    out = L.STATE / "rescore_from_results.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")
    print("04_scores/ untouched; ask.py untouched.")


if __name__ == "__main__":
    main()
