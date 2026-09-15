#!/usr/bin/env python
"""p10_gate_r.py - read Gates R1, R2 and R3 against their pre-registered spec.

corpus-lab/state/phase10_gate_r_spec.md was committed before any clean-room
command ran. This evaluates it and writes the verdict. A failed line is recorded
with the first thing that actually differed -- never smoothed over.

  python p10_gate_r.py r1 --a A --b B
  python p10_gate_r.py r2 --room C
  python p10_gate_r.py r3 --room A
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import labpaths as L  # noqa: E402
import p10_cleanroom as CR  # noqa: E402

SPEC = L.STATE / "phase10_gate_r_spec.md"

COUNT_KEYS = ["n_docs", "n_families", "n_editions", "n_dupes",
              "n_duplicate_groups", "n_captions", "n_cards",
              "n_pages_status", "n_status", "n_files", "status_counts"]


def sha_obj(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def load(p):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def room_files(room):
    d = CR.room_dir(room)
    rec = load(d / "room.json")
    art = Path(rec["artefacts"]) if rec and rec.get("artefacts") else d / "artefacts"
    return {
        "room": rec, "dir": d,
        "manifest": load(art / "build_manifest.json"),
        "canonical": load(art / "canonical_export.json"),
        "retrieval": load(d / "retrieval_outputs.json"),
        "selftest": load(d / "selftest.json"),
        "artefacts": art,
    }


def first_table_difference(ca, cb):
    """Name the first table and row that differs, rather than just 'differs'."""
    ta, tb = ca.get("tables", {}), cb.get("tables", {})
    only_a = sorted(set(ta) - set(tb))
    only_b = sorted(set(tb) - set(ta))
    if only_a or only_b:
        return "table sets differ: only in A %s; only in B %s" % (only_a, only_b)
    for t in sorted(ta):
        ra, rb = ta[t], tb[t]
        if len(ra) != len(rb):
            return "%s: %d rows in A, %d in B" % (t, len(ra), len(rb))
        for i, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                keys = sorted(set(x) | set(y))
                diff = [k for k in keys if x.get(k) != y.get(k)]
                return "%s row %d: columns %s differ (first: %r vs %r)" % (
                    t, i, diff, x.get(diff[0]) if diff else None,
                    y.get(diff[0]) if diff else None)
    return None


def compare_vectors(ma, mb):
    """sha equal -> deterministic; else classify, using what the manifest holds."""
    out = {}
    for name in ("cards", "captions"):
        va = (ma.get("vectors") or {}).get(name) or {}
        vb = (mb.get("vectors") or {}).get(name) or {}
        ka = [k for k in va if k.startswith("sha256_rounded")]
        if not ka:
            out[name] = {"class": "unknown", "detail": "no rounded hash recorded"}
            continue
        k = ka[0]
        if va.get(k) and va.get(k) == vb.get(k):
            out[name] = {"class": "deterministic",
                         "detail": "rounded-to-3dp hashes equal; shape %s"
                                   % va.get("shape")}
        elif va.get("shape") != vb.get("shape"):
            out[name] = {"class": "FAIL",
                         "detail": "shapes differ: %s vs %s"
                                   % (va.get("shape"), vb.get("shape"))}
        else:
            out[name] = {"class": "differs_beyond_3dp",
                         "detail": "rounded hashes differ: %s vs %s"
                                   % (str(va.get(k))[:16], str(vb.get(k))[:16])}
    return out


def compare_retrieval(ra, rb):
    """Rank lists identical? If not, name the first probe that differs."""
    if not ra or not rb:
        return {"identical": False, "detail": "a retrieval capture is missing"}
    diffs = []
    for section in ("find", "inside", "series", "have"):
        la, lb = ra.get(section) or [], rb.get(section) or []
        if len(la) != len(lb):
            diffs.append("%s: %d probes in A, %d in B" % (section, len(la), len(lb)))
            continue
        for i, (x, y) in enumerate(zip(la, lb)):
            if x.get("stdout") != y.get("stdout"):
                diffs.append("%s[%d] %r: output differs" % (section, i, x.get("args")))
    if (ra.get("coverage") or {}).get("stdout") != (rb.get("coverage") or {}).get("stdout"):
        diffs.append("coverage: output differs")
    if (ra.get("families_probed") != rb.get("families_probed")):
        diffs.append("families_probed differs: %s vs %s"
                     % (ra.get("families_probed"), rb.get("families_probed")))
    return {"identical": not diffs, "n_differing_probes": len(diffs),
            "first_differences": diffs[:5]}


def cmd_r1(a):
    A, B = room_files(a.a), room_files(a.b)
    rows = []

    def row(rid, check, ok, actual):
        rows.append({"id": rid, "check": check, "pass": bool(ok), "actual": actual})

    ra, rb = A["room"] or {}, B["room"] or {}
    row("R1.1", "both installs exit 0",
        ra.get("install_rc") == 0 and rb.get("install_rc") == 0,
        "A rc=%s B rc=%s" % (ra.get("install_rc"), rb.get("install_rc")))
    row("R1.2", "each install <= 20 min",
        (ra.get("install_s") or 1e9) <= 1200 and (rb.get("install_s") or 1e9) <= 1200,
        "A %.0fs B %.0fs" % (ra.get("install_s") or -1, rb.get("install_s") or -1))

    ca, cb = A["canonical"], B["canonical"]
    same_canon = bool(ca and cb) and sha_obj(ca) == sha_obj(cb)
    row("R1.3", "canonical_export.json sha256 A == B", same_canon,
        ("equal: %s" % sha_obj(ca)[:16]) if same_canon
        else ("FIRST DIFFERENCE -> %s" % (first_table_difference(ca, cb)
                                          if ca and cb else "a canonical export is missing")))

    ma, mb = A["manifest"] or {}, B["manifest"] or {}
    cnt_a = {k: (ma.get("counts") or {}).get(k) for k in COUNT_KEYS}
    cnt_b = {k: (mb.get("counts") or {}).get(k) for k in COUNT_KEYS}
    bad = {k: (cnt_a[k], cnt_b[k]) for k in COUNT_KEYS if cnt_a[k] != cnt_b[k]}
    nfa = (ma.get("corpus") or {}).get("n_files")
    nfb = (mb.get("corpus") or {}).get("n_files")
    row("R1.4", "build_manifest counts A == B (incl. file count)",
        not bad and nfa == nfb,
        ("all equal; n_files=%s; %s" % (nfa, {k: v for k, v in cnt_a.items()
                                              if v is not None}))
        if (not bad and nfa == nfb) else "differ: %s ; n_files %s vs %s" % (bad, nfa, nfb))

    vec = compare_vectors(ma, mb)
    vec_ok = all(v["class"] in ("deterministic", "deterministic_float_noise")
                 for v in vec.values())
    row("R1.5", "vectors deterministic (or float noise within bar)", vec_ok, vec)

    ret = compare_retrieval(A["retrieval"], B["retrieval"])
    row("R1.6", "retrieval outputs A == B", ret["identical"], ret)

    sa = set(ra.get("selftest_checks") or [])
    sb = set(rb.get("selftest_checks") or [])
    row("R1.7", "c_selftest same check set, passing in both",
        sa == sb and sa and ra.get("selftest_pass") and rb.get("selftest_pass"),
        "A %d checks pass=%s, B %d checks pass=%s; symmetric difference %s"
        % (len(sa), ra.get("selftest_pass"), len(sb), rb.get("selftest_pass"),
           sorted(sa ^ sb)))

    row("R1.8", "memory files 0 before and after in both rooms",
        (ra.get("memory_files_before") == 0 and rb.get("memory_files_before") == 0
         and ra.get("memory_files_after") == 0 and rb.get("memory_files_after") == 0),
        "A before=%s after=%s; B before=%s after=%s"
        % (ra.get("memory_files_before"), ra.get("memory_files_after"),
           rb.get("memory_files_before"), rb.get("memory_files_after")))

    failed = [r["id"] for r in rows if not r["pass"]]
    rec = {"gate": "R1", "spec": "corpus-lab/state/phase10_gate_r_spec.md",
           "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "verdict": "PASS" if not failed else "GATE_R1_STOP",
           "rows_failed": failed, "rows": rows,
           "vector_class": vec,
           "canonical_sha256": {"A": sha_obj(ca) if ca else None,
                                "B": sha_obj(cb) if cb else None},
           "builder": {"A": ma.get("builder"), "B": mb.get("builder")}}
    (L.STATE / "phase10_gate_r1_result.json").write_text(
        json.dumps(rec, indent=1), encoding="utf-8")
    _print(rec)
    return 0


def cmd_r2(a):
    C = room_files(a.room)
    rc = C["room"] or {}
    rows = []

    def row(rid, check, ok, actual):
        rows.append({"id": rid, "check": check, "pass": bool(ok), "actual": actual})

    row("R2.1", "install exits 0", rc.get("install_rc") == 0,
        "rc=%s" % rc.get("install_rc"))
    row("R2.2", "wall <= 60 min", (rc.get("install_s") or 1e9) <= 3600,
        "%.0fs" % (rc.get("install_s") or -1))
    row("R2.3", "self-test passes its applicable checks", rc.get("selftest_pass"),
        "%d checks, failed: %s" % (len(rc.get("selftest_checks") or []),
                                   rc.get("selftest_failed") or "none"))
    ask = rc.get("ask") or {}
    row("R2.4", "answer ends with a Sources block naming only OPENED pages",
        ask.get("sources_all_opened") is True,
        "n_sources=%s n_opened=%s unopened=%s"
        % (ask.get("n_sources"), ask.get("n_opened"), ask.get("sources_unopened")))
    row("R2.5", "guard block count recorded", ask.get("guard_blocks") is not None,
        "guard_blocks=%s" % ask.get("guard_blocks"))
    row("R2.6", "memory files 0 before and after",
        rc.get("memory_files_before") == 0 and rc.get("memory_files_after") == 0,
        "before=%s after=%s" % (rc.get("memory_files_before"),
                                rc.get("memory_files_after")))

    failed = [r["id"] for r in rows if not r["pass"]]
    rec = {"gate": "R2", "spec": "corpus-lab/state/phase10_gate_r_spec.md",
           "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "verdict": "PASS" if not failed else "GATE_R2_STOP",
           "rows_failed": failed, "rows": rows,
           "what_this_does_not_show": (
               "corpus_2000 is another generated corpus from the same fixture "
               "ecosystem; this is not real-world validation; genuine "
               "cross-folder generalisation remains untested.")}
    (L.STATE / "phase10_gate_r2_result.json").write_text(
        json.dumps(rec, indent=1), encoding="utf-8")
    _print(rec)
    return 0


def cmd_r3(a):
    d = CR.room_dir(a.room)
    trace = load(d / "trace.json") or {}
    rows = []

    def row(rid, check, ok, actual):
        rows.append({"id": rid, "check": check, "pass": bool(ok), "actual": actual})

    dev_hits = trace.get("dev_repo_hits") or []
    proj_hits = trace.get("project_key_hits") or []
    pkg = load(Path(trace.get("package_manifest") or "nonexistent")) or {}
    grep_hits = pkg.get("forbidden_string_hits", None)

    row("R3.1", "no read under the development repo", not dev_hits,
        ("%d reads traced, none under the dev repo" % trace.get("n_paths", 0))
        if not dev_hits else "first offending path: %s" % dev_hits[0])
    row("R3.2", "no read under the dev repo's claude project key", not proj_hits,
        "none" if not proj_hits else "first: %s" % proj_hits[0])
    row("R3.3", "package grep for C:\\Users and Desktop is empty",
        grep_hits == [], "hits=%s" % (grep_hits if grep_hits else 0))
    row("R3.4", "the traced install actually ran", trace.get("install_rc") == 0,
        "rc=%s, %s paths traced" % (trace.get("install_rc"), trace.get("n_paths")))

    failed = [r["id"] for r in rows if not r["pass"]]
    rec = {"gate": "R3", "spec": "corpus-lab/state/phase10_gate_r_spec.md",
           "evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "verdict": "PASS" if not failed else "GATE_R3_STOP",
           "rows_failed": failed, "rows": rows,
           "what_this_does_not_show": (
               "A trace proves no dev-repo read ON THIS RUN, on this OS, for this "
               "corpus. It is a trace, not a proof about all inputs.")}
    (L.STATE / "phase10_gate_r3_result.json").write_text(
        json.dumps(rec, indent=1), encoding="utf-8")
    _print(rec)
    return 0


def _print(rec):
    print("=" * 72)
    print("GATE %s: %s" % (rec["gate"], rec["verdict"]))
    print("=" * 72)
    for r in rec["rows"]:
        print("  [%s] %-6s %s" % ("PASS" if r["pass"] else "FAIL", r["id"], r["check"]))
        act = r["actual"]
        print("           actual: %s" % (json.dumps(act) if isinstance(act, (dict, list))
                                         else act))
    print()


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("r1"); p.add_argument("--a", default="A"); p.add_argument("--b", default="B"); p.set_defaults(fn=cmd_r1)
    p = sub.add_parser("r2"); p.add_argument("--room", default="C"); p.set_defaults(fn=cmd_r2)
    p = sub.add_parser("r3"); p.add_argument("--room", default="A"); p.set_defaults(fn=cmd_r3)
    a = ap.parse_args(argv[1:])
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
