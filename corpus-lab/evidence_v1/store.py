#!/usr/bin/env python
"""evidence_v1.store -- SQLite schema, connection and runtime-path management.

Runtime code. Imports NOTHING from corpus-lab/bin/labpaths.py and carries no
private-key defaults: the corpus root always comes from an explicit --root
argument supplied to the CLI, never inferred from this builder's environment.

Runtime state lives ONLY under
    %LOCALAPPDATA%/RetrievalLab/evidence-v1/roots/<root_id>/
where root_id = sha256(normalized, resolved absolute root path). Nothing here
ever writes inside the research root itself except via evidence_v1.install
(CLAUDE.md / .claude/settings.json, through corpus-lab/bin/stack.py only).
"""
import hashlib
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

SCHEMA_VERSION = 1


def root_id_for(root_path):
    norm = str(Path(root_path).resolve()).replace("\\", "/").rstrip("/").lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def runtime_base():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is not set; cannot locate runtime storage")
    return Path(base) / "RetrievalLab" / "evidence-v1"


def runtime_dir(root_path):
    d = runtime_base() / "roots" / root_id_for(root_path)
    for sub in ("pages", "requests", "cells", "crops"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def db_path(root_path):
    return runtime_dir(root_path) / "catalogue.db"


def new_request_id():
    return str(uuid.uuid4())


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roots (
    root_id TEXT PRIMARY KEY,
    root_path TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    last_refresh_at TEXT
);

CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_id TEXT NOT NULL REFERENCES roots(root_id),
    normalized_path TEXT NOT NULL,
    current_path TEXT NOT NULL,
    size INTEGER,
    mtime_ns INTEGER,
    content_sha256 TEXT,
    status TEXT NOT NULL,
    error_class TEXT,
    generation INTEGER NOT NULL,
    discovered_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    tombstoned INTEGER NOT NULL DEFAULT 0,
    UNIQUE(root_id, normalized_path)
);
CREATE INDEX IF NOT EXISTS idx_files_root_path ON files(root_id, normalized_path);
CREATE INDEX IF NOT EXISTS idx_files_sha ON files(content_sha256);

CREATE TABLE IF NOT EXISTS contents (
    content_sha256 TEXT PRIMARY KEY,
    format TEXT NOT NULL,
    n_pages INTEGER,
    n_text_pages INTEGER,
    status TEXT NOT NULL,
    error_class TEXT,
    extractor_versions TEXT,
    extracted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_sha256 TEXT NOT NULL REFERENCES contents(content_sha256),
    page_index INTEGER NOT NULL,
    text_status TEXT NOT NULL,
    raw_text TEXT,
    UNIQUE(content_sha256, page_index)
);
CREATE INDEX IF NOT EXISTS idx_pages_sha_page ON pages(content_sha256, page_index);

CREATE TABLE IF NOT EXISTS cards (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_sha256 TEXT NOT NULL REFERENCES contents(content_sha256),
    page_index INTEGER,
    kind TEXT NOT NULL,
    caption TEXT,
    heading TEXT,
    row_labels TEXT,
    col_headers TEXT,
    unit_literal TEXT,
    source_literal TEXT,
    flags TEXT,
    search_text TEXT NOT NULL,
    search_text_b TEXT,
    full_text TEXT,
    truncated INTEGER NOT NULL DEFAULT 0,
    table_ordinal INTEGER,
    parent_card_id INTEGER REFERENCES cards(card_id)
);
CREATE INDEX IF NOT EXISTS idx_cards_sha_page ON cards(content_sha256, page_index);
CREATE INDEX IF NOT EXISTS idx_cards_parent ON cards(parent_card_id);

CREATE TABLE IF NOT EXISTS links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_sha256 TEXT NOT NULL REFERENCES contents(content_sha256),
    page_index INTEGER,
    target_text TEXT NOT NULL,
    resolved_normalized_path TEXT
);

CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    root_id TEXT NOT NULL REFERENCES roots(root_id),
    question TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deadline_at TEXT,
    status TEXT NOT NULL,
    searches_used INTEGER NOT NULL DEFAULT 0,
    pages_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(request_id),
    root_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    generation INTEGER NOT NULL,
    current_path TEXT NOT NULL,
    format TEXT NOT NULL,
    page_index INTEGER,
    viewer_page INTEGER,
    printed_label TEXT,
    table_id TEXT,
    table_label TEXT,
    row_label TEXT,
    column_label TEXT,
    raw_value TEXT,
    decimal_value REAL,
    unit_literal TEXT,
    unit_multiplier REAL,
    period_literal TEXT,
    geography_literal TEXT,
    population_literal TEXT,
    status_literal TEXT,
    source_literal TEXT,
    bbox TEXT,
    quote TEXT,
    extractor_versions TEXT,
    verification_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_request ON evidence(request_id);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(request_id),
    operation TEXT NOT NULL,
    output TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Plain (non-contentless) FTS5 tables. card_id/content_sha256/page_index ride
-- along UNINDEXED so a hit can be joined straight back without ever scanning
-- an unindexed column on `rel`/path -- a full page read always goes through
-- the (content_sha256,page_index) index on `pages`, never through FTS.
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
    search_text, search_text_b, caption, heading, row_labels, col_headers, source_literal,
    card_id UNINDEXED, content_sha256 UNINDEXED, page_index UNINDEXED,
    tokenize='unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS prose_fts USING fts5(
    body,
    content_sha256 UNINDEXED, page_index UNINDEXED, unit_index UNINDEXED,
    tokenize='unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS title_fts USING fts5(
    title, content_sha256 UNINDEXED, tokenize='unicode61'
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    body, content_sha256 UNINDEXED, page_index UNINDEXED, tokenize='unicode61'
);
"""


def connect(root_path, timeout_s=2.0, check_same_thread=True):
    rd = runtime_dir(root_path)
    con = sqlite3.connect(str(rd / "catalogue.db"), timeout=timeout_s, isolation_level=None,
                           check_same_thread=check_same_thread)
    con.execute("PRAGMA busy_timeout = {}".format(int(timeout_s * 1000)))
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    # NORMAL is the standard, still-durable pairing with WAL (SQLite docs):
    # a commit is safe across an application crash (the WAL survives), and
    # only an OS-level power loss could lose the last few commits. FULL's
    # per-commit fsync is what was serializing every worker behind one
    # writer on this corpus's ~477-card, ~2500-paragraph documents.
    con.execute("PRAGMA synchronous = NORMAL")
    return con


def init_db(root_path):
    con = connect(root_path)
    try:
        con.executescript(SCHEMA_SQL)
        rid = root_id_for(root_path)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        con.execute(
            "INSERT OR IGNORE INTO roots(root_id, root_path, schema_version, created_at) "
            "VALUES (?,?,?,?)", (rid, str(Path(root_path).resolve()), SCHEMA_VERSION, now))
        con.commit()
    finally:
        con.close()
    return db_path(root_path)


def next_generation(con, root_id):
    row = con.execute(
        "SELECT COALESCE(MAX(generation), 0) FROM files WHERE root_id=?", (root_id,)).fetchone()
    return (row[0] or 0) + 1
