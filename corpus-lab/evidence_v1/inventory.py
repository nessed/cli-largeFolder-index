#!/usr/bin/env python
"""evidence_v1.inventory -- file discovery, hashing, change detection, and the
transactional per-file ingest that drives both cold install and refresh.

Runtime code, no labpaths import, no corpus writes (except via evidence_v1.install,
which only ever touches CLAUDE.md / .claude/settings.json through stack.py).
"""
import hashlib
import json
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from . import extract, store

EXCLUDED_DIR_NAMES = {".git", ".venv", "venv", "node_modules", "site-packages", "__pycache__"}
OWNED_CONFIG_RELATIVE = {"claude.md", ".claude/settings.json"}
MAX_FILE_SIZE = 300 * 1024 * 1024
DEFAULT_WORKERS_BUILD = 8
DEFAULT_WORKERS_REFRESH = 4
MAX_OUTSTANDING = 16
PER_FILE_TIMEOUT_S = 180


def _normalize_rel(root, abs_path):
    return str(Path(abs_path).relative_to(root)).replace("\\", "/")


def scan_root(root_path):
    """os.scandir walk, no git-ignore semantics, never follows a symlink or
    junction that leaves root. Yields (abs_path, normalized_path, stat_result).
    Tracks visited real directories to avoid a junction cycle even within root."""
    root = Path(root_path).resolve()
    root_real = os.path.realpath(str(root))
    stack = [root]
    seen_dirs = set()
    excluded_counts = {}
    while stack:
        d = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            if entry.is_dir(follow_symlinks=True):
                if name.lower() in EXCLUDED_DIR_NAMES:
                    excluded_counts[name.lower()] = excluded_counts.get(name.lower(), 0) + 1
                    continue
                # realpath resolves Windows junctions too (a reparse-point tag
                # Python's is_symlink() does NOT recognize as a symlink), so
                # this check does not rely on is_symlink() to catch an escape.
                child_real = os.path.realpath(entry.path)
                if not (child_real == root_real or child_real.startswith(root_real + os.sep)
                        or child_real.startswith(root_real + "/")):
                    excluded_counts["out_of_root_link"] = excluded_counts.get("out_of_root_link", 0) + 1
                    continue
                if child_real in seen_dirs:
                    continue
                seen_dirs.add(child_real)
                stack.append(Path(entry.path))
            else:
                try:
                    if entry.is_symlink():
                        continue
                except OSError:
                    continue
                rel = _normalize_rel(root, entry.path).lower()
                if rel in OWNED_CONFIG_RELATIVE:
                    excluded_counts["owned_config"] = excluded_counts.get("owned_config", 0) + 1
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                yield entry.path, _normalize_rel(root, entry.path), st
    scan_root.last_excluded_counts = excluded_counts


def sha256_file(path, bufsize=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _write_minimal_status_row(con, root_id, normalized_path, abs_path_str, generation, now,
                               status, error_class, size=None, mtime_ns=None):
    """Last-resort row write: guarantees every discovered path gets SOME
    `files` row, even when hashing/extraction/the main transaction raised
    something unanticipated. No content/pages/cards are written -- just
    enough for accounting to balance and for the file to show up as an
    explicit, investigable failure rather than a silent gap."""
    try:
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute(
            "SELECT file_id FROM files WHERE root_id=? AND normalized_path=?",
            (root_id, normalized_path)).fetchone()
        if existing:
            con.execute(
                "UPDATE files SET current_path=?, size=?, mtime_ns=?, content_sha256=NULL, "
                "status=?, error_class=?, generation=?, updated_at=? WHERE file_id=?",
                (abs_path_str, size, mtime_ns, status, error_class, generation, now, existing[0]))
        else:
            con.execute(
                "INSERT INTO files(root_id, normalized_path, current_path, size, mtime_ns, "
                "content_sha256, status, error_class, generation, discovered_at, updated_at) "
                "VALUES (?,?,?,?,?,NULL,?,?,?,?,?)",
                (root_id, normalized_path, abs_path_str, size, mtime_ns, status, error_class,
                 generation, now, now))
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return {"normalized_path": normalized_path, "status": status}


def _ingest_one(con_factory, root_id, generation, abs_path, normalized_path, pdftotext_exe):
    """Hash + extract + write one file transactionally. Returns a status dict.
    Opens its own connection so threads never share a sqlite3.Connection.

    "Per-generation discovered files = sum of mutually exclusive file
    statuses; zero residual" (contract, Stage 3) means every path the scanner
    discovered MUST end up with a `files` row, even when something in
    hashing/extraction raises an exception nobody anticipated -- an
    in-memory-only counter that never reaches the database is exactly the
    kind of residual this function must not produce. The fallback below is
    deliberately the LAST resort, after the specific, classified error paths
    in extract.py; it exists so an unclassified crash still becomes a real,
    queryable parser_failed row instead of a file that silently has no
    status at all.
    """
    con = con_factory()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        st = os.stat(abs_path)
    except OSError:
        return _write_minimal_status_row(con, root_id, normalized_path, str(abs_path),
                                          generation, now, "vanished", "stat_failed")

    try:
        if st.st_size > MAX_FILE_SIZE:
            status, error_class, content_sha = "unsupported", "unsupported_size", None
            ext_result = None
        else:
            content_sha = sha256_file(abs_path)
            existing_content = con.execute(
                "SELECT status, error_class FROM contents WHERE content_sha256=?",
                (content_sha,)).fetchone()
            if existing_content is not None:
                # Content already ingested under this hash (identical copy, or a
                # moved file) -- reuse it by hash; pages/cards are keyed only by
                # content_sha256 so they are already shared. No re-extraction.
                ext_result = None
                status, error_class = existing_content[0], existing_content[1]
            else:
                ext = Path(abs_path).suffix
                ext_result = extract.extract(abs_path, ext, pdftotext_exe, st.st_size)
                status = ext_result["status"]
                error_class = ext_result.get("error_class")
    except Exception as e:
        return _write_minimal_status_row(con, root_id, normalized_path, str(abs_path),
                                          generation, now, "parser_failed",
                                          "unclassified:{}".format(type(e).__name__),
                                          size=getattr(st, "st_size", None),
                                          mtime_ns=getattr(st, "st_mtime_ns", None))

    try:
        con.execute("BEGIN IMMEDIATE")
        existing = con.execute(
            "SELECT file_id FROM files WHERE root_id=? AND normalized_path=?",
            (root_id, normalized_path)).fetchone()
        if existing:
            con.execute(
                "UPDATE files SET current_path=?, size=?, mtime_ns=?, content_sha256=?, "
                "status=?, error_class=?, generation=?, updated_at=?, tombstoned=0 "
                "WHERE file_id=?",
                (str(abs_path), st.st_size, st.st_mtime_ns, content_sha, status,
                 error_class, generation, now, existing[0]))
        else:
            con.execute(
                "INSERT INTO files(root_id, normalized_path, current_path, size, mtime_ns, "
                "content_sha256, status, error_class, generation, discovered_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (root_id, normalized_path, str(abs_path), st.st_size, st.st_mtime_ns,
                 content_sha, status, error_class, generation, now, now))

        if content_sha and ext_result:
            # This whole block only runs when the pre-transaction check found
            # NO existing `contents` row for this hash -- i.e. genuinely new
            # bytes. Re-check for a race (another thread committing the same
            # new content_sha256 first) INSIDE the transaction, with an
            # indexed lookup, and only pay for cleanup (which touches FTS5
            # tables with no usable index on content_sha256 -- a full scan
            # that got materially slower as those tables grew over the
            # course of this exact build) in that narrow, now-confirmed case.
            race_existing = con.execute(
                "SELECT 1 FROM contents WHERE content_sha256=?", (content_sha,)).fetchone()
            if race_existing:
                con.execute("DELETE FROM pages WHERE content_sha256=?", (content_sha,))
                old_card_ids = [r[0] for r in con.execute(
                    "SELECT card_id FROM cards WHERE content_sha256=?", (content_sha,))]
                if old_card_ids:
                    con.executemany("DELETE FROM cards_fts WHERE card_id=?",
                                     [(cid,) for cid in old_card_ids])
                con.execute("DELETE FROM cards WHERE content_sha256=?", (content_sha,))
                con.execute("DELETE FROM prose_fts WHERE content_sha256=?", (content_sha,))
                con.execute("DELETE FROM notes_fts WHERE content_sha256=?", (content_sha,))
                con.execute("DELETE FROM title_fts WHERE content_sha256=?", (content_sha,))

            con.execute(
                "INSERT OR REPLACE INTO contents(content_sha256, format, n_pages, "
                "n_text_pages, status, error_class, extractor_versions, extracted_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (content_sha, ext_result["format"], ext_result["n_pages"],
                 ext_result["n_text_pages"], ext_result["status"], ext_result.get("error_class"),
                 json.dumps(extract.EXTRACTOR_VERSIONS), now))

            con.executemany(
                "INSERT OR REPLACE INTO pages(content_sha256, page_index, text_status, "
                "raw_text) VALUES (?,?,?,?)",
                [(content_sha, p["page_index"], p["text_status"], p["raw_text"])
                 for p in ext_result["pages"]])

            notes_rows, prose_rows = [], []
            for p in ext_result["pages"]:
                if p["text_status"] != "readable":
                    continue
                if ext_result["format"] == "text":
                    notes_rows.append((p["raw_text"], content_sha, p["page_index"]))
                elif ext_result["format"] == "pdf":
                    for unit in extract.paragraph_units(p["raw_text"]):
                        prose_rows.append((unit, content_sha, p["page_index"], 0))
            if notes_rows:
                con.executemany(
                    "INSERT INTO notes_fts(body, content_sha256, page_index) VALUES (?,?,?)",
                    notes_rows)
            if prose_rows:
                con.executemany(
                    "INSERT INTO prose_fts(body, content_sha256, page_index, unit_index) "
                    "VALUES (?,?,?,?)", prose_rows)

            tables = ext_result["tables"]
            if tables:
                con.executemany(
                    "INSERT INTO cards(content_sha256, page_index, kind, caption, heading, "
                    "row_labels, col_headers, unit_literal, source_literal, search_text, "
                    "search_text_b, full_text, truncated, table_ordinal) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(content_sha, t.get("page_index"), t.get("kind", "table"), t.get("caption"),
                      t.get("heading"), json.dumps(t.get("row_labels") or []),
                      json.dumps(t.get("col_headers") or []), t.get("unit_literal"),
                      t.get("source_literal"), t.get("search_text", ""),
                      t.get("search_text_b", t.get("search_text", "")), t.get("full_text"),
                      int(t.get("truncated", False)), t.get("table_ordinal")) for t in tables])
                # AUTOINCREMENT rowids are assigned in insertion order within this
                # single-writer transaction, so the N most recent card_ids for
                # this content_sha256, taken in ascending id order, line up
                # positionally with `tables` in the same order they were inserted.
                new_ids = [r[0] for r in con.execute(
                    "SELECT card_id FROM cards WHERE content_sha256=? ORDER BY card_id DESC LIMIT ?",
                    (content_sha, len(tables)))][::-1]
                con.executemany(
                    "INSERT INTO cards_fts(search_text, search_text_b, caption, heading, "
                    "row_labels, col_headers, source_literal, card_id, content_sha256, "
                    "page_index) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(t.get("search_text", ""), t.get("search_text_b", ""), t.get("caption") or "",
                      t.get("heading") or "", " ".join(t.get("row_labels") or []),
                      " ".join(str(c) for c in (t.get("col_headers") or [])),
                      t.get("source_literal") or "", cid, content_sha, t.get("page_index"))
                     for cid, t in zip(new_ids, tables)])
            if ext_result["format"] in ("pdf", "docx", "xlsx", "csv"):
                title_text = Path(abs_path).stem.replace("_", " ").replace("-", " ")
                con.execute("INSERT INTO title_fts(title, content_sha256) VALUES (?,?)",
                            (title_text, content_sha))
        con.execute("COMMIT")
    except Exception as e:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        con.close()
        con2 = con_factory(timeout_s=20.0)
        try:
            return _write_minimal_status_row(
                con2, root_id, normalized_path, str(abs_path), generation, now,
                "parser_failed", "transaction_failed:{}".format(type(e).__name__))
        finally:
            con2.close()
    con.close()
    return {"normalized_path": normalized_path, "status": status}


def rehash_single(root_path, normalized_path, pdftotext_exe):
    """Force-rehash one file regardless of size/mtime_ns agreement. This is
    the mitigation for the acknowledged gap in refresh()'s cheap scan: a
    same-size edit with a deliberately preserved mtime evades the ordinary
    inventory diff, but a source about to be cited for compose is always
    rehashed here first. Returns the ingest result, or None if the path no
    longer exists (caller should treat that as 'vanished', not stale-trust)."""
    root_path = Path(root_path).resolve()
    root_id = store.root_id_for(root_path)
    abs_path = root_path / normalized_path
    if not abs_path.exists():
        con = store.connect(root_path)
        try:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            con.execute(
                "UPDATE files SET tombstoned=1, status='vanished', updated_at=? "
                "WHERE root_id=? AND normalized_path=?", (now, root_id, normalized_path))
            con.commit()
        finally:
            con.close()
        return None
    con = store.connect(root_path)
    generation = store.next_generation(con, root_id)
    con.close()
    return _ingest_one(lambda: store.connect(root_path), root_id, generation,
                        str(abs_path), normalized_path, pdftotext_exe)


def build_catalogue(root_path, pdftotext_exe, max_workers=DEFAULT_WORKERS_BUILD,
                     time_budget_s=None, progress_every_s=10):
    root_path = Path(root_path).resolve()
    store.init_db(root_path)
    root_id = store.root_id_for(root_path)

    def con_factory(timeout_s=2.0):
        return store.connect(root_path, timeout_s=timeout_s)

    con = con_factory()
    generation = store.next_generation(con, root_id)
    con.close()

    t0 = time.time()
    last_report = t0
    results = {"readable": 0, "partially_readable": 0, "no_text": 0, "empty": 0,
               "encrypted": 0, "parser_failed": 0, "unsupported": 0, "vanished": 0,
               "pending": 0}
    n_done = 0
    n_total_seen = 0
    timed_out = False
    pending_paths = []

    futures = {}
    file_iter = scan_root(root_path)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        def submit_next():
            nonlocal n_total_seen
            try:
                abs_path, normalized_path, st = next(file_iter)
            except StopIteration:
                return False
            n_total_seen += 1
            fut = pool.submit(_ingest_one, con_factory, root_id, generation,
                               abs_path, normalized_path, pdftotext_exe)
            futures[fut] = normalized_path
            return True

        for _ in range(max_workers * 2):
            if not submit_next():
                break

        while futures:
            if time_budget_s is not None and (time.time() - t0) > time_budget_s:
                timed_out = True
                for f, p in futures.items():
                    pending_paths.append(p)
                break
            done_set, _ = wait(futures.keys(), timeout=1, return_when=FIRST_COMPLETED)
            for fut in done_set:
                normalized_path = futures.pop(fut)
                try:
                    r = fut.result()
                    results[r["status"]] = results.get(r["status"], 0) + 1
                except Exception as e:
                    # _ingest_one already tries hard to write SOME row for
                    # every path it's handed; reaching here means even its
                    # own fallback write failed (e.g. con_factory() itself
                    # raised). Try once more directly so this path still
                    # gets a row instead of becoming an accounting residual.
                    try:
                        _con = con_factory(timeout_s=20.0)
                        try:
                            _write_minimal_status_row(
                                _con, root_id, normalized_path, normalized_path,
                                generation, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "parser_failed", "outer_handler:{}".format(type(e).__name__))
                        finally:
                            _con.close()
                    except Exception:
                        pass
                    results["parser_failed"] += 1
                n_done += 1
                if len(futures) < max_workers * 2 and not timed_out:
                    submit_next()
            now = time.time()
            if now - last_report >= progress_every_s:
                print("  [catalogue] {} files processed, {:.0f}s elapsed".format(
                    n_done, now - t0), flush=True)
                last_report = now
            if time_budget_s is not None and (time.time() - t0) > time_budget_s:
                timed_out = True
                for f, p in futures.items():
                    pending_paths.append(p)
                break

    excluded = getattr(scan_root, "last_excluded_counts", {})
    wall_s = time.time() - t0
    return {
        "root_id": root_id, "generation": generation, "wall_s": round(wall_s, 2),
        "n_discovered": n_total_seen, "n_processed": n_done, "timed_out": timed_out,
        "status_counts": results, "excluded_dir_counts": excluded,
        "pending_paths": pending_paths,
    }


def refresh(root_path, pdftotext_exe, time_budget_s=8.0, max_workers=DEFAULT_WORKERS_REFRESH):
    """Incremental pass: compare size/mtime_ns against the DB; full-hash only
    what looks new/changed; tombstone vanished paths immediately; whatever
    doesn't fit the time budget becomes an explicit pending change, not a
    silent gap."""
    root_path = Path(root_path).resolve()
    root_id = store.root_id_for(root_path)
    con = store.connect(root_path)
    try:
        existing = {row[0]: row for row in con.execute(
            "SELECT normalized_path, size, mtime_ns, content_sha256, status, generation "
            "FROM files WHERE root_id=? AND tombstoned=0", (root_id,))}
    finally:
        con.close()

    t0 = time.time()
    seen_paths = set()
    to_ingest = []
    for abs_path, normalized_path, st in scan_root(root_path):
        seen_paths.add(normalized_path)
        prior = existing.get(normalized_path)
        if prior is None or prior[1] != st.st_size or prior[2] != st.st_mtime_ns:
            to_ingest.append((abs_path, normalized_path))
        if time.time() - t0 > time_budget_s * 4:  # scanning itself must not run away
            break

    vanished = sorted(set(existing.keys()) - seen_paths)
    con = store.connect(root_path)
    try:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for normalized_path in vanished:
            con.execute(
                "UPDATE files SET tombstoned=1, status='vanished', updated_at=? "
                "WHERE root_id=? AND normalized_path=?", (now, root_id, normalized_path))
        con.commit()
    finally:
        con.close()

    con = store.connect(root_path)
    generation = store.next_generation(con, root_id)
    con.close()

    def con_factory(timeout_s=2.0):
        return store.connect(root_path, timeout_s=timeout_s)

    done, pending = [], []
    remaining_budget = max(0.1, time_budget_s - (time.time() - t0))
    deadline = time.time() + remaining_budget
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        it = iter(to_ingest)

        def submit_next():
            try:
                abs_path, normalized_path = next(it)
            except StopIteration:
                return False
            futures[pool.submit(_ingest_one, con_factory, root_id, generation,
                                 abs_path, normalized_path, pdftotext_exe)] = normalized_path
            return True

        for _ in range(max_workers * 2):
            if not submit_next():
                break
        while futures:
            if time.time() > deadline:
                pending.extend(futures.values())
                break
            done_set, _ = wait(futures.keys(), timeout=0.5, return_when=FIRST_COMPLETED)
            for fut in done_set:
                normalized_path = futures.pop(fut)
                try:
                    fut.result()
                    done.append(normalized_path)
                except Exception:
                    pending.append(normalized_path)
                if time.time() <= deadline:
                    submit_next()

    return {
        "root_id": root_id, "generation": generation,
        "n_scanned": len(seen_paths), "n_changed_or_new": len(to_ingest),
        "n_ingested": len(done), "n_pending": len(pending), "n_vanished": len(vanished),
        "pending_paths": pending, "vanished_paths": vanished,
        "wall_s": round(time.time() - t0, 2),
    }
