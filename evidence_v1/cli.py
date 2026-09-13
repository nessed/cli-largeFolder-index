#!/usr/bin/env python
"""evidence_v1.cli -- the evidence.py command dispatcher. Runtime code, no
labpaths import. All commands return JSON on stdout except `compose`, which
returns the exact terminal answer plus receipt (still as JSON envelope here;
the policy-level "return verbatim" contract is enforced by the installed
CLAUDE.md instructions, not by this CLI's own formatting).
"""
import argparse
import json
import shutil
import sqlite3
import sys
import time
import uuid
from pathlib import Path

from . import compile as compiler
from . import extract, install, inventory, request as req_mod, retrieve, store, verify

PDFTOTEXT_EXE = shutil.which("pdftotext") or "pdftotext"
MAX_CONCEPT_SEARCHES = 4
MAX_CANDIDATES = 12
MAX_PAGES_PER_REQUEST = 24
MAX_EVIDENCE_IDS = 64


def _claude_exe_path():
    p = Path(r"C:/nvm4w/nodejs/node_modules/@anthropic-ai/claude-code/bin/claude.exe")
    return str(p) if p.exists() else None


def cmd_doctor(args):
    root = Path(args.root).resolve()
    out = {"ready": False, "root": str(root)}
    if not root.is_dir():
        out["error"] = "root does not exist"
        print(json.dumps(out, indent=1))
        return 1

    out["python_version"] = ".".join(map(str, sys.version_info[:3]))
    out["python_ok"] = sys.version_info >= (3, 11)
    out["pdftotext_path"] = shutil.which("pdftotext")
    out["pdftotext_ok"] = bool(out["pdftotext_path"])
    out["claude_exe_path"] = _claude_exe_path()
    out["claude_exe_ok"] = bool(out["claude_exe_path"])
    try:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        out["fts5_ok"] = True
        con.close()
    except sqlite3.OperationalError:
        out["fts5_ok"] = False

    db = store.db_path(root)
    out["db_path"] = str(db)
    out["db_exists"] = db.exists()
    if db.exists():
        try:
            con = store.connect(root, timeout_s=2.0)
            root_id = store.root_id_for(root)
            counts = dict(con.execute(
                "SELECT status, COUNT(*) FROM files WHERE root_id=? AND tombstoned=0 "
                "GROUP BY status", (root_id,)).fetchall())
            n_pending = counts.get("pending", 0)
            n_total = sum(counts.values())
            out["status_counts"] = counts
            out["n_discovered"] = n_total
            out["pending"] = n_pending
            out["accounting_residual"] = 0
            out["ready"] = (n_total > 0)
            con.close()
        except sqlite3.OperationalError:
            out["ready"] = False
            out["error"] = "INDEX_PENDING: catalogue DB locked by another writer"
    out["hooks_installed"] = install.hook_status(root).get("installed", False)
    print(json.dumps(out, indent=1))
    return 0 if (out["python_ok"] and out["pdftotext_ok"] and out["claude_exe_ok"]
                 and out["fts5_ok"]) else 1


def cmd_install(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"error": "root does not exist"}))
        return 1
    t0 = time.time()
    result = inventory.build_catalogue(root, PDFTOTEXT_EXE, max_workers=args.workers,
                                        time_budget_s=args.time_budget_s)
    elapsed = time.time() - t0
    hook_result = install.install_hooks(root) if not args.no_hooks else {"skipped": True}
    out = {
        "root": str(root), "elapsed_s": round(elapsed, 2),
        "n_discovered": result["n_discovered"], "n_processed": result["n_processed"],
        "timed_out": result["timed_out"], "status_counts": result["status_counts"],
        "excluded_dir_counts": result["excluded_dir_counts"],
        "n_pending": len(result["pending_paths"]),
        "accounting_residual": result["n_discovered"] - sum(result["status_counts"].values()) - len(result["pending_paths"]),
        "ready": (not result["timed_out"]) and len(result["pending_paths"]) == 0,
        "hooks": hook_result,
    }
    print("READY root={}".format(root) if out["ready"] else "INDEX_PENDING root={}".format(root))
    print("accounting_residual={}".format(out["accounting_residual"]))
    print(json.dumps(out, indent=1))
    return 0 if out["ready"] else 1


def cmd_uninstall(args):
    root = Path(args.root).resolve()
    result = install.uninstall_hooks(root)
    print(json.dumps(result, indent=1))
    print("UNINSTALLED" if result.get("ok") else "UNINSTALL_FAILED")
    return 0 if result.get("ok") else 1


def _coverage_counts(root):
    root_id = store.root_id_for(root)
    con = store.connect(root, timeout_s=2.0)
    try:
        counts = dict(con.execute(
            "SELECT status, COUNT(*) FROM files WHERE root_id=? AND tombstoned=0 "
            "GROUP BY status", (root_id,)).fetchall())
    finally:
        con.close()
    readable = counts.get("readable", 0) + counts.get("partially_readable", 0)
    unavailable = sum(counts.get(k, 0) for k in
                       ("no_text", "empty", "encrypted", "parser_failed", "unsupported"))
    pending = counts.get("pending", 0)
    return {"files": sum(counts.values()), "readable_files": readable,
            "unavailable": unavailable, "pending": pending, "status_counts": counts}


def cmd_prepare(args):
    root = Path(args.root).resolve()
    try:
        refresh_result = inventory.refresh(root, PDFTOTEXT_EXE, time_budget_s=8.0)
    except sqlite3.OperationalError:
        print(json.dumps({"outcome": "INDEX_PENDING",
                           "reason": "catalogue DB locked by another writer"}))
        return 1

    request_id = str(uuid.uuid4())
    req_mod.new(root, request_id, args.question, deadline_s=60)
    discovery = retrieve.discover(root, args.question, max_leads=24)
    req_mod.register_candidates(root, request_id, discovery["leads"])
    cov = _coverage_counts(root)
    out = {
        "request_id": request_id, "deadline_s": 60, "coverage": cov,
        "refresh": {"n_pending": refresh_result["n_pending"],
                    "n_vanished": refresh_result["n_vanished"]},
        "leads": [{"candidate_id": req_mod.candidate_id(l["key"]), "score": l["score"]}
                  for l in discovery["leads"]],
        "terms_used": discovery["terms_used"],
    }
    print(json.dumps(out, indent=1))
    return 0


def cmd_search(args):
    root = Path(args.root).resolve()
    data = req_mod.load(root, args.request)
    if data is None:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "unknown request_id"}))
        return 1
    if data["searches_used"] >= MAX_CONCEPT_SEARCHES:
        print(json.dumps({"outcome": "ENGINE_ERROR",
                           "reason": "search limit (4 per request) reached"}))
        return 1
    if len(args.concept) > 120:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "concept exceeds 120 characters"}))
        return 1
    result = retrieve.search(root, args.concept, args.entity or "", args.period or "unspecified",
                              args.kind, max_results=120)
    data["searches_used"] += 1
    save_data = req_mod.register_candidates(root, args.request, result["results"])
    save_data["searches_used"] = data["searches_used"]
    req_mod.save(root, args.request, save_data)
    out = {
        "results": [{"candidate_id": req_mod.candidate_id(l["key"]), "score": l["score"]}
                    for l in result["results"]],
        "terms_used": result["terms_used"], "searches_used": data["searches_used"],
        "searches_remaining": MAX_CONCEPT_SEARCHES - data["searches_used"],
    }
    print(json.dumps(out, indent=1))
    return 0


def _resolve_candidate_to_source(con, root, candidate):
    if candidate["key"][0] == "card":
        card_id = candidate["key"][1]
        row = con.execute(
            "SELECT content_sha256, page_index, row_labels, col_headers, caption, "
            "table_ordinal FROM cards WHERE card_id=?", (card_id,)).fetchone()
        if not row:
            return None
        content_sha, page_index = row[0], row[1]
    elif candidate["key"][0] in ("doc", "page"):
        content_sha = candidate["content_sha256"]
        page_index = candidate["key"][2] if candidate["key"][0] == "page" else None
    else:
        return None
    frow = con.execute(
        "SELECT current_path, status FROM files WHERE content_sha256=? AND tombstoned=0 "
        "LIMIT 1", (content_sha,)).fetchone()
    if not frow:
        return None
    crow = con.execute("SELECT format FROM contents WHERE content_sha256=?",
                        (content_sha,)).fetchone()
    return {"current_path": frow[0], "content_sha256": content_sha, "page_index": page_index,
            "format": crow[0] if crow else None}


def cmd_read(args):
    root = Path(args.root).resolve()
    data = req_mod.load(root, args.request)
    if data is None:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "unknown request_id"}))
        return 1
    cand_ids = args.candidates.split(",")
    if len(cand_ids) > MAX_CANDIDATES:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "at most 12 candidates per read"}))
        return 1

    con = store.connect(root, timeout_s=2.0)
    out_evidence = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    root_id = store.root_id_for(root)
    pages_this_call = 0
    try:
        for cid in cand_ids:
            cand = data["candidates"].get(cid)
            if cand is None:
                out_evidence.append({"candidate_id": cid, "status": "UNKNOWN_CANDIDATE"})
                continue
            src = _resolve_candidate_to_source(con, root, cand)
            if src is None:
                out_evidence.append({"candidate_id": cid, "status": "vanished"})
                continue
            if data["pages_read"] + pages_this_call >= MAX_PAGES_PER_REQUEST:
                out_evidence.append({"candidate_id": cid, "status": "PAGE_BUDGET_EXHAUSTED"})
                continue
            pages_this_call += 1
            abs_path = Path(src["current_path"])
            ev_id = str(uuid.uuid4())
            if src["format"] == "pdf" and src["page_index"] is not None:
                vresult = verify.verify_pdf_cell(
                    abs_path, src["page_index"],
                    cand.get("row_labels", [""])[0] if isinstance(cand.get("row_labels"), list)
                    else "", None)
            else:
                vresult = {"verification_status": "verified" if abs_path.exists() else "failed"}
            ev = {
                "evidence_id": ev_id, "request_id": args.request, "root_id": root_id,
                "source_sha256": src["content_sha256"], "generation": 0,
                "current_path": str(abs_path), "format": src["format"],
                "page_index": src["page_index"],
                "viewer_page": (src["page_index"] + 1) if src["page_index"] is not None else None,
                "verification_status": vresult.get("verification_status", "failed"),
                "raw_value": vresult.get("raw_value"),
                "decimal_value": vresult.get("decimal_value"),
                "status_literal": vresult.get("status_literal"),
                "created_at": now,
            }
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO evidence(evidence_id, request_id, root_id, source_sha256, "
                "generation, current_path, format, page_index, viewer_page, verification_status, "
                "raw_value, decimal_value, status_literal, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ev["evidence_id"], ev["request_id"], ev["root_id"], ev["source_sha256"],
                 ev["generation"], ev["current_path"], ev["format"], ev["page_index"],
                 ev["viewer_page"], ev["verification_status"], ev["raw_value"],
                 ev["decimal_value"], ev["status_literal"], ev["created_at"]))
            con.execute("COMMIT")
            data["issued_evidence_ids"].append(ev_id)
            out_evidence.append(ev)
    finally:
        con.close()
    data["pages_read"] += pages_this_call
    req_mod.save(root, args.request, data)
    print(json.dumps({"evidence": out_evidence, "pages_read_total": data["pages_read"]}, indent=1))
    return 0


def cmd_compose(args):
    root = Path(args.root).resolve()
    data = req_mod.load(root, args.request)
    if data is None:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "unknown request_id"}))
        return 1
    ev_ids = args.evidence.split(",") if args.evidence else []
    if len(ev_ids) > MAX_EVIDENCE_IDS:
        print(json.dumps({"outcome": "ENGINE_ERROR", "reason": "at most 64 evidence IDs"}))
        return 1
    con = store.connect(root, timeout_s=2.0)
    try:
        rows = []
        for eid in ev_ids:
            r = con.execute("SELECT * FROM evidence WHERE evidence_id=? AND request_id=?",
                             (eid, args.request)).fetchone()
            if r is None:
                continue
            cols = [c[0] for c in con.execute("PRAGMA table_info(evidence)")]
            rows.append(dict(zip(cols, r)))
    finally:
        con.close()
    result = compiler.compose(args.operation, rows, args.request,
                               requested={"issued_evidence_ids": set(data["issued_evidence_ids"])})
    con = store.connect(root)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO receipts(receipt_id, request_id, operation, output, created_at) "
            "VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), args.request, args.operation,
             json.dumps(result, default=str), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        con.execute("COMMIT")
    finally:
        con.close()
    print(result.get("answer_text") or json.dumps(result, default=str))
    return 0


def cmd_explain(args):
    root = Path(args.root).resolve()
    con = store.connect(root, timeout_s=2.0)
    try:
        rows = con.execute(
            "SELECT evidence_id, current_path, page_index, viewer_page, verification_status, "
            "raw_value FROM evidence WHERE request_id=?", (args.request,)).fetchall()
    finally:
        con.close()
    out = [{"evidence_id": r[0], "path": r[1], "page_index": r[2], "viewer_page": r[3],
            "verification_status": r[4], "raw_value": r[5]} for r in rows]
    print(json.dumps({"request_id": args.request, "evidence": out}, indent=1))
    return 0


def cmd_open(args):
    root = Path(args.root).resolve()
    con = store.connect(root, timeout_s=2.0)
    try:
        row = con.execute("SELECT current_path, viewer_page FROM evidence WHERE "
                           "evidence_id=? AND request_id=?", (args.evidence, args.request)).fetchone()
    finally:
        con.close()
    if row is None:
        print(json.dumps({"error": "unknown evidence id for this request"}))
        return 1
    print(json.dumps({"path": row[0], "viewer_page": row[1],
                       "note": "open this path in the default PDF viewer at the stated page"}))
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="evidence.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("doctor")
    p.add_argument("--root", required=True)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("install")
    p.add_argument("--root", required=True)
    p.add_argument("--time-budget-s", type=float, default=1800.0)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--no-hooks", action="store_true", default=False)
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("uninstall")
    p.add_argument("--root", required=True)
    p.set_defaults(func=cmd_uninstall)

    p = sub.add_parser("prepare")
    p.add_argument("--root", required=True)
    p.add_argument("--question", required=True)
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("search")
    p.add_argument("--root", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--concept", required=True)
    p.add_argument("--entity", default="")
    p.add_argument("--period", default="unspecified")
    p.add_argument("--kind", default="lookup")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("read")
    p.add_argument("--root", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--candidates", required=True)
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("compose")
    p.add_argument("--root", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--operation", required=True)
    p.set_defaults(func=cmd_compose)

    p = sub.add_parser("explain")
    p.add_argument("--root", required=True)
    p.add_argument("--request", required=True)
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("open")
    p.add_argument("--root", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--evidence", required=True)
    p.set_defaults(func=cmd_open)

    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
