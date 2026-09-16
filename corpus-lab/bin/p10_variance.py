#!/usr/bin/env python
"""p10_variance.py - how much does the number move when nothing changes?

Plan E Phase 4.3, governed by corpus-lab/state/phase10_variance_spec.md.

Every headline this project has published is one run of one battery. "Sonnet
13/17, Opus 14/17" has been quoted as though the gap meant something. This
reports, for each metric, **every individual value**, its denominator, and the
observed range -- so that a later reader can see at a glance whether a
difference is bigger than the noise or smaller than it.

Sample standard deviation is reported ONLY where n >= 3. With n = 2 a standard
deviation is arithmetic theatre.

  python p10_variance.py [--out corpus-lab/state/c_variance_2026-09-16.json]
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402

SONNET = ["P9S_live", "P10S1_live", "P10S2_live", "P10S3_live"]
OPUS = ["P9O_live", "P10O1_live", "P10O2_live"]

# metric -> (source file kind, field, denominator)
METRICS = [
    ("cited_right_page_equiv_v2", "v2", "cited_right_page_equiv", 17),
    ("cited_right_page_equiv_v3", "v3", "cited_right_page_equiv", 17),
    ("cited_right_page_strict_v3", "v3", "cited_right_page_strict", 17),
    ("cited_unopened_total_v3", "v3", "cited_unopened_total", None),
    ("mentioned_unopened_total_v3", "v3", "mentioned_unopened_total", None),
    ("value_correct_v3", "v3", "value_correct", 5),
    ("vector_full_keyv2", "kv", "vector_full", 9),
    ("absence_ok3_frozen3_v3", "v3", "absence_ok3_frozen3", 3),
    ("n_answer_fragments_v3", "v3", "n_answer_fragments", None),
    ("n_opens_loop_only_total_v3", "v3", "n_opens_loop_only_total", None),
    ("sessions_lost_v3", "v3", "sessions_lost", None),
    ("median_wall_s_v3", "v3", "median_wall_s", None),
    ("p90_wall_s_v3", "v3", "p90_wall_s", None),
    ("total_cost_usd_v3", "v3", "total_cost_usd", None),
]


def session_accounting(phase):
    """Per battery, from the DRIVER records rather than the scorer: how many
    sessions actually ran to completion.

    A session the account's own rate limit cut short is not a wrong answer, but
    every scorer in this project counts it as one, because it arrives as a
    normal-looking assistant message. Reporting it here keeps the denominator
    visible without editing a frozen scorer or adjusting a number by hand.
    """
    d = L.RUNS / phase
    if not d.is_dir():
        return None
    total, done, limited, other_fail = 0, 0, [], []
    for f in sorted(d.glob("*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(r, dict) or "qid" not in r:
            continue
        total += 1
        if r.get("returncode") == 0:
            done += 1
        elif "session limit" in (r.get("answer_text") or ""):
            limited.append(r["qid"])
        else:
            other_fail.append(r["qid"])
    out = {"n_sessions": total, "n_completed": done,
           "n_cut_by_account_rate_limit": len(limited),
           "rate_limited_qids": sorted(limited),
           "n_failed_other": len(other_fail),
           "failed_other_qids": sorted(other_fail),
           "partial": bool(limited or other_fail)}
    if out["partial"]:
        out["read_this_as"] = (
            "This battery is PARTIAL. %d of %d sessions never produced an "
            "answer because the operating account hit its own session limit. "
            "Every scorer counts those as misses, so this battery's scores are "
            "a FLOOR, not an estimate." % (len(limited) + len(other_fail), total))
    return out


def load(kind, phase):
    name = {"v2": "c_live_battery_v2__%s.json" % phase,
            "v3": "c_live_battery_v3__%s.json" % phase,
            "kv": "c_live_battery_v3__%s__keyv2.json" % phase}[kind]
    p = L.STATE / name
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "sessions_lost" not in d:
        d["sessions_lost"] = (d.get("no_answer_max_turns", 0)
                              + d.get("no_answer_timeout", 0)
                              + d.get("no_answer_other_empty", 0))
    return d


def per_question_agreement(phases):
    """Of the 17 answerable questions, how many got the SAME v3 equivalence
    verdict in every repeat? The aggregate can be stable while the individual
    questions churn underneath it, and that is worth knowing."""
    rows = {}
    used = []
    for ph in phases:
        p = L.SCORES / ("live_v3__%s.json" % ph)
        if not p.exists():
            continue
        used.append(ph)
        d = json.loads(p.read_text(encoding="utf-8"))
        for r in d["answerable"]:
            if "status" in r:
                continue
            rows.setdefault(r["q_id"], []).append(bool(r["cited_right_page_equiv"]))
    if len(used) < 2:
        return {"n_repeats": len(used), "note": "needs at least two batteries"}
    full = {q: v for q, v in rows.items() if len(v) == len(used)}
    agree = sum(1 for v in full.values() if len(set(v)) == 1)
    always = sorted(q for q, v in full.items() if all(v))
    never = sorted(q for q, v in full.items() if not any(v))
    churn = sorted(q for q, v in full.items() if len(set(v)) > 1)
    return {"n_repeats": len(used), "phases": used,
            "n_questions_compared": len(full),
            "n_same_verdict_every_time": agree,
            "always_hit": always, "never_hit": never,
            "changed_between_runs": churn}


def summarise(phases, label):
    present = [p for p in phases if load("v3", p) is not None]
    out = {"model_group": label, "phases_requested": phases,
           "phases_present": present, "n": len(present), "metrics": {}}
    for name, kind, field, denom in METRICS:
        vals, by_phase = [], {}
        for ph in present:
            d = load(kind, ph)
            v = d.get(field) if d else None
            by_phase[ph] = v
            if isinstance(v, (int, float)):
                vals.append(v)
        entry = {"per_battery": by_phase, "n": len(vals), "denominator": denom}
        if vals:
            entry.update({"mean": round(statistics.fmean(vals), 4),
                          "min": min(vals), "max": max(vals),
                          "range": round(max(vals) - min(vals), 4)})
            entry["sd"] = (round(statistics.stdev(vals), 4) if len(vals) >= 3
                           else None)
            entry["sd_note"] = (None if len(vals) >= 3
                                else "n<3: a standard deviation would be theatre")
        out["metrics"][name] = entry
    out["per_question_agreement_v3_equiv"] = per_question_agreement(present)
    out["session_accounting"] = {ph: session_accounting(ph) for ph in present}
    partial = sorted(ph for ph, acc in out["session_accounting"].items()
                     if acc and acc["partial"])
    out["partial_batteries"] = partial
    if partial:
        out["partial_warning"] = (
            "The range below includes %s, which did not complete. Its low value "
            "is depressed by sessions that were cut off, not by sessions that "
            "answered badly, so the range is WIDER than the stack's true "
            "variance. It may not be quoted as a noise band."
            % ", ".join(partial))

    ref = load("v3", present[0]) if present else {}
    out["provenance"] = {
        "scorer_version": ref.get("scorer_version"),
        "scorer_sha256": ref.get("scorer_sha256"),
        "key_file": ref.get("key_file"),
        "key_sha256": ref.get("key_sha256"),
        "group_definition_sha256": ref.get("group_definition_sha256"),
    }
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.STATE / "c_variance_2026-09-16.json"))
    a = ap.parse_args(argv[1:])

    son = summarise(SONNET, "claude-sonnet-5")
    opu = summarise(OPUS, "claude-opus-5")

    eq = "cited_right_page_equiv_v3"
    s_rng = son["metrics"][eq].get("range")
    o_rng = opu["metrics"][eq].get("range")
    s_vals = [v for v in son["metrics"][eq]["per_battery"].values() if v is not None]
    o_vals = [v for v in opu["metrics"][eq]["per_battery"].values() if v is not None]

    overlap = None
    if s_vals and o_vals:
        inside = (min(o_vals) <= max(s_vals) and min(s_vals) <= max(o_vals))
        overlap = ("both fall inside each other's observed range" if inside
                   else "they do NOT fall inside each other's observed range")

    out = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "spec": "corpus-lab/state/phase10_variance_spec.md",
        "what_this_is": (
            "The same stack, the same 20 questions, the same flags, run several "
            "times. Nothing was changed between runs and nothing was tuned."),
        "scorer_version": "v3 (frozen) beside v2",
        "sonnet": son,
        "opus": opu,
        "decision_rule": {
            "sonnet_equivalence_range_v3": s_rng,
            "opus_equivalence_range_v3": o_rng,
            "rule": ("A difference between two single Sonnet batteries on "
                     "cited_right_page_equiv smaller than %s may NOT be used to "
                     "prefer a configuration." % s_rng),
            "opus_caveat": ("The Opus range from n=%d is a LOWER BOUND on Opus "
                            "noise, not a band." % opu["n"]),
            "cross_model": overlap,
            "cross_model_rule": ("Sonnet-versus-Opus differences are not "
                                 "interpreted beyond this sentence."),
        },
    }
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote %s" % a.out)

    for grp in (son, opu):
        print("\n%s  (n=%d: %s)" % (grp["model_group"], grp["n"],
                                    ", ".join(grp["phases_present"]) or "none"))
        print("  %-30s %-28s %6s %6s %6s %s"
              % ("metric", "per battery", "mean", "min", "max", "range"))
        for name, _k, _f, denom in METRICS:
            m = grp["metrics"][name]
            if not m["n"]:
                continue
            vals = ", ".join(str(v) for v in m["per_battery"].values()
                             if v is not None)
            print("  %-30s %-28s %6s %6s %6s %s%s"
                  % (name, vals[:28], m.get("mean"), m.get("min"), m.get("max"),
                     m.get("range"), "  sd=%s" % m["sd"] if m.get("sd") else ""))
        for ph, acc in grp["session_accounting"].items():
            if acc and acc["partial"]:
                print("  PARTIAL %s: %d/%d completed; cut by account rate "
                      "limit: %s" % (ph, acc["n_completed"], acc["n_sessions"],
                                     ", ".join(acc["rate_limited_qids"])))
        ag = grp["per_question_agreement_v3_equiv"]
        if ag.get("n_questions_compared"):
            print("  per-question agreement: %d of %d questions got the same "
                  "verdict in all %d runs"
                  % (ag["n_same_verdict_every_time"], ag["n_questions_compared"],
                     ag["n_repeats"]))
            if ag["changed_between_runs"]:
                print("    changed between runs: %s"
                      % ", ".join(ag["changed_between_runs"]))
    print("\ncross-model: %s" % overlap)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
