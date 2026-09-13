#!/usr/bin/env python
"""evidence_v1.request -- request lifecycle: prepare/search/read/compose state,
persisted under the runtime dir as requests/<request_id>.json. Runtime code,
no labpaths import.
"""
import json
import time
from pathlib import Path

from . import store

MAX_SEARCHES_PER_REQUEST = 4
MAX_PAGES_PER_REQUEST = 24
MAX_CANDIDATES_PER_READ = 12


def request_path(root_path, request_id):
    return store.runtime_dir(root_path) / "requests" / "{}.json".format(request_id)


def load(root_path, request_id):
    p = request_path(root_path, request_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(root_path, request_id, data):
    p = request_path(root_path, request_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def new(root_path, request_id, question, deadline_s=60):
    data = {
        "request_id": request_id, "question": question,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "deadline_unix": time.time() + deadline_s,
        "searches_used": 0, "pages_read": 0,
        "candidates": {}, "issued_evidence_ids": [], "status": "open",
    }
    save(root_path, request_id, data)
    root_id = store.root_id_for(root_path)
    con = store.connect(root_path)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO requests(request_id, root_id, question, created_at, deadline_at, "
            "status) VALUES (?,?,?,?,?,?)",
            (request_id, root_id, question, data["created_utc"],
             str(data["deadline_unix"]), "open"))
        con.execute("COMMIT")
    finally:
        con.close()
    return data


def candidate_id(key):
    if key[0] == "card":
        return "card_{}".format(key[1])
    if key[0] == "doc":
        return "doc_{}".format(key[1][:16])
    if key[0] == "page":
        return "page_{}_{}".format(key[1][:16], key[2])
    raise ValueError("unknown candidate key shape: {!r}".format(key))


def register_candidates(root_path, request_id, leads):
    data = load(root_path, request_id)
    for lead in leads:
        cid = candidate_id(lead["key"])
        data["candidates"][cid] = lead
    save(root_path, request_id, data)
    return data
