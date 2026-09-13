#!/usr/bin/env python
"""BUILD_PROMPT.md Stage 3.3 -- 12 inventory tests, 12/12 required.
Scratch-only, newly authored tiny fixtures. Never touches the harness.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "corpus-lab"))
sys.path.insert(0, str(REPO / "corpus-lab" / "tests" / "evidence_v1" / "fixtures"))
os.environ.setdefault("LOCALAPPDATA", str(REPO / "corpus-lab" / "99_scratch" / "evidence_v1" / "fake_localappdata"))

from evidence_v1 import inventory, store  # noqa: E402
import make_pdf  # noqa: E402

PDFTOTEXT = shutil.which("pdftotext")


def _fresh_root():
    d = Path(tempfile.mkdtemp(prefix="ev1_inv_", dir=str(
        REPO / "corpus-lab" / "99_scratch" / "evidence_v1")))
    return d


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.root = _fresh_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        rid = store.root_id_for(self.root)
        rd = store.runtime_dir(self.root)
        self.addCleanup(shutil.rmtree, rd, ignore_errors=True)

    def _files_rows(self):
        con = store.connect(self.root)
        try:
            rows = {r[0]: r for r in con.execute(
                "SELECT normalized_path, status, content_sha256, tombstoned, generation "
                "FROM files")}
        finally:
            con.close()
        return rows

    def test_01_add(self):
        (self.root / "a.md").write_text("hello world", encoding="utf-8")
        res = inventory.build_catalogue(self.root, PDFTOTEXT)
        self.assertEqual(res["n_discovered"], 1)
        rows = self._files_rows()
        self.assertIn("a.md", rows)
        self.assertEqual(rows["a.md"][1], "readable")

    def test_02_edit(self):
        p = self.root / "a.md"
        p.write_text("version one", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        sha1 = self._files_rows()["a.md"][2]
        time.sleep(0.01)
        p.write_text("version two, much longer content to force a new hash", encoding="utf-8")
        os.utime(p, None)  # ensure mtime advances even on coarse filesystems
        inventory.refresh(self.root, PDFTOTEXT, time_budget_s=5)
        sha2 = self._files_rows()["a.md"][2]
        self.assertNotEqual(sha1, sha2)

    def test_03_delete(self):
        p = self.root / "a.md"
        p.write_text("to be deleted", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        p.unlink()
        inventory.refresh(self.root, PDFTOTEXT, time_budget_s=5)
        rows = self._files_rows()
        self.assertEqual(rows["a.md"][3], 1)  # tombstoned
        self.assertEqual(rows["a.md"][1], "vanished")

    def test_04_move(self):
        p = self.root / "a.md"
        p.write_text("moving content", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        sha_before = self._files_rows()["a.md"][2]
        (self.root / "sub").mkdir()
        new_p = self.root / "sub" / "a.md"
        shutil.move(str(p), str(new_p))
        inventory.refresh(self.root, PDFTOTEXT, time_budget_s=5)
        rows = self._files_rows()
        self.assertEqual(rows["a.md"][3], 1)  # old path tombstoned
        self.assertIn("sub/a.md", rows)
        self.assertEqual(rows["sub/a.md"][2], sha_before)  # content reused by hash

    def test_05_identical_copy(self):
        (self.root / "a.md").write_text("same bytes", encoding="utf-8")
        (self.root / "b.md").write_text("same bytes", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        rows = self._files_rows()
        self.assertEqual(rows["a.md"][2], rows["b.md"][2])
        con = store.connect(self.root)
        try:
            n_contents = con.execute(
                "SELECT COUNT(*) FROM contents WHERE content_sha256=?",
                (rows["a.md"][2],)).fetchone()[0]
        finally:
            con.close()
        self.assertEqual(n_contents, 1)  # one contents row serves both files

    def test_06_same_size_edit(self):
        """Same byte-length edit with a NORMAL (advancing) mtime must still
        be caught -- this is the ordinary case refresh() is expected to
        handle, contrasted with test_07's deliberately-preserved-mtime gap."""
        p = self.root / "a.md"
        p.write_text("AAAAAAAAAA", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        sha1 = self._files_rows()["a.md"][2]
        time.sleep(0.05)
        p.write_text("BBBBBBBBBB", encoding="utf-8")  # same length, different bytes
        inventory.refresh(self.root, PDFTOTEXT, time_budget_s=5)
        sha2 = self._files_rows()["a.md"][2]
        self.assertNotEqual(sha1, sha2)

    def test_07_retained_mtime_cited_edit(self):
        """Documents the acknowledged gap: same size + explicitly preserved
        mtime evades refresh()'s cheap scan, AND shows the mitigation --
        rehash_single() (called before compose on any cited source) always
        catches it regardless of what refresh() missed."""
        p = self.root / "a.md"
        p.write_text("AAAAAAAAAA", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)
        sha1 = self._files_rows()["a.md"][2]
        st_before = p.stat()
        p.write_text("BBBBBBBBBB", encoding="utf-8")
        # ns= is required here: a float-seconds os.utime() call loses enough
        # precision that refresh()'s st_mtime_ns comparison sees a difference
        # anyway, which would defeat the point of this test.
        os.utime(p, ns=(st_before.st_atime_ns, st_before.st_mtime_ns))
        inventory.refresh(self.root, PDFTOTEXT, time_budget_s=5)
        sha_after_refresh = self._files_rows()["a.md"][2]
        self.assertEqual(sha1, sha_after_refresh,
                          "refresh() is expected to miss this -- documenting the gap")
        inventory.rehash_single(self.root, "a.md", PDFTOTEXT)
        sha_after_rehash = self._files_rows()["a.md"][2]
        self.assertNotEqual(sha1, sha_after_rehash,
                             "rehash_single() must catch what refresh() missed")

    def test_08_partially_readable_pdf(self):
        make_pdf.write_pdf(str(self.root / "mixed.pdf"),
                            ["first page text", None, "third page text"])
        inventory.build_catalogue(self.root, PDFTOTEXT)
        rows = self._files_rows()
        self.assertEqual(rows["mixed.pdf"][1], "partially_readable")

    def test_09_encrypted_pdf(self):
        make_pdf.write_encrypted_pdf(str(self.root / "locked.pdf"), ["secret"])
        inventory.build_catalogue(self.root, PDFTOTEXT)
        rows = self._files_rows()
        self.assertEqual(rows["locked.pdf"][1], "encrypted")

    def test_10_extraction_crash(self):
        """A file with a .pdf extension that is not actually a PDF must
        become parser_failed, not crash the batch or silently vanish."""
        (self.root / "corrupt.pdf").write_bytes(b"not actually a pdf file at all")
        (self.root / "ok.md").write_text("still processed", encoding="utf-8")
        res = inventory.build_catalogue(self.root, PDFTOTEXT)
        rows = self._files_rows()
        self.assertEqual(rows["corrupt.pdf"][1], "parser_failed")
        self.assertEqual(rows["ok.md"][1], "readable")  # batch continued
        self.assertEqual(res["n_processed"], 2)

    def test_11_stale_lock(self):
        """Hold an exclusive write transaction open on the DB; a concurrent
        writer must time out within the configured busy_timeout (~2s) rather
        than hang indefinitely or corrupt state."""
        (self.root / "a.md").write_text("x", encoding="utf-8")
        inventory.build_catalogue(self.root, PDFTOTEXT)

        blocker = store.connect(self.root, timeout_s=10, check_same_thread=False)
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("UPDATE files SET status='readable' WHERE normalized_path='a.md'")

        def release_after(delay):
            time.sleep(delay)
            blocker.execute("COMMIT")
            blocker.close()

        releaser = threading.Thread(target=release_after, args=(3.0,))
        releaser.start()
        t0 = time.time()
        con2 = store.connect(self.root, timeout_s=2.0)
        with self.assertRaises(sqlite3.OperationalError):
            con2.execute("BEGIN IMMEDIATE")
            con2.execute("UPDATE files SET status='readable' WHERE normalized_path='a.md'")
        elapsed = time.time() - t0
        con2.close()
        releaser.join()
        self.assertLess(elapsed, 4.0)
        self.assertGreaterEqual(elapsed, 1.8)

    def test_12_out_of_root_junction(self):
        """A junction/symlink inside root pointing OUTSIDE root must never be
        followed -- 0 root escapes."""
        outside = Path(tempfile.mkdtemp(prefix="ev1_outside_", dir=str(
            REPO / "corpus-lab" / "99_scratch" / "evidence_v1")))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        (outside / "secret.md").write_text("must never be scanned", encoding="utf-8")
        link_path = self.root / "escape_link"
        try:
            os.symlink(str(outside), str(link_path), target_is_directory=True)
        except (OSError, NotImplementedError):
            import subprocess
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link_path), str(outside)],
                                capture_output=True, text=True)
            if r.returncode != 0:
                self.skipTest("could not create a junction/symlink on this system: " + r.stderr)
        (self.root / "inside.md").write_text("inside root", encoding="utf-8")
        res = inventory.build_catalogue(self.root, PDFTOTEXT)
        rows = self._files_rows()
        self.assertNotIn("escape_link/secret.md", rows)
        self.assertIn("inside.md", rows)
        self.assertEqual(res["excluded_dir_counts"].get("out_of_root_link", 0), 1)


if __name__ == "__main__":
    unittest.main()
