"""Plan F / Phase 11, finding F-02.

`setup_folder.py install --artefacts <dir>` puts the pages database at
`<dir>/pages.db`, and the shelf at `<dir>/shelf/shelf.db`. The machine-global
registry is what `c_shelf.py` resolves through when the model runs the commands
`CLAUDE.md` prints -- and those carry no `--db`/`--shelf`, so the registry is the
only thing standing between the model and `unable to open database file`.

Before the fix, `c_stack.do_setup` registered the shelf correctly (it is fed by
`--shelf-dir`) but registered the db as a hardcoded development-rung constant,
`<L.STACKS>/s2_fts5/harness_15000.db`, which does not exist in a portable
install. Gate R2 did not catch it because `p10_cleanroom.py` passes `--db` and
`--shelf` explicitly on every call and so never consults the registry.

These tests do not build an index -- that takes minutes. They drive `do_setup`
directly, which is the unit that writes the registry entry, and assert on the
entry and on what `c_shelf._resolve` hands back from inside the folder.
"""
import json
import os
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))

import c_shelf as CSH      # noqa: E402
import c_stack as CST      # noqa: E402


class TestInstallRegistersArtefactsDb(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="p11_f02_"))
        self.root = self.tmp / "research"
        self.root.mkdir()
        (self.root / "a.txt").write_text("hello", encoding="utf-8")
        self.art = self.tmp / "artefacts"
        (self.art / "shelf").mkdir(parents=True)
        # Stand-ins: do_setup only records paths, it never opens them.
        self.db = self.art / "pages.db"
        self.db.write_bytes(b"")
        (self.art / "shelf" / "shelf.db").write_bytes(b"")
        # Keep the real user registry untouched.
        self.reg = self.tmp / "roots.json"
        self._saved = CSH.REG_PATH
        CSH.REG_PATH = self.reg

    def tearDown(self):
        CSH.REG_PATH = self._saved
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _entry(self):
        reg = json.loads(self.reg.read_text(encoding="utf-8"))
        return reg[CSH._norm_root_key(str(self.root))]

    def test_01_registered_db_is_the_artefacts_pages_db(self):
        """The regression itself: the entry must name <artefacts>/pages.db."""
        rc = CST.do_setup(str(self.root),
                          shelf_dir=str(self.art / "shelf"),
                          db_path=str(self.db))
        self.assertEqual(rc, 0)
        self.assertEqual(Path(self._entry()["db"]).resolve(), self.db.resolve())

    def test_02_registered_db_exists_on_disk(self):
        """A path that does not exist is what produced the traceback."""
        CST.do_setup(str(self.root),
                     shelf_dir=str(self.art / "shelf"),
                     db_path=str(self.db))
        self.assertTrue(Path(self._entry()["db"]).exists(),
                        "registered db does not exist: %s" % self._entry()["db"])

    def test_03_shelf_registration_is_unchanged(self):
        """The half that already worked must keep working."""
        CST.do_setup(str(self.root),
                     shelf_dir=str(self.art / "shelf"),
                     db_path=str(self.db))
        self.assertEqual(Path(self._entry()["shelf"]).resolve(),
                         (self.art / "shelf" / "shelf.db").resolve())

    def test_04_resolve_from_inside_the_folder_finds_both(self):
        """What the model actually does: no --db, no --shelf, cwd in the folder."""
        CST.do_setup(str(self.root),
                     shelf_dir=str(self.art / "shelf"),
                     db_path=str(self.db))
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            _root, db, shelf = CSH._resolve(None, None)
        finally:
            os.chdir(cwd)
        self.assertEqual(Path(db).resolve(), self.db.resolve())
        self.assertEqual(Path(shelf).resolve(),
                         (self.art / "shelf" / "shelf.db").resolve())

    def test_05_setup_folder_passes_the_db_through(self):
        """setup_folder.py must hand c_stack the artefacts db on the command line."""
        src = (BIN / "setup_folder.py").read_text(encoding="utf-8")
        i = src.index('"c_stack.py"') if '"c_stack.py"' in src else src.index("c_stack.py")
        window = src[i:i + 400]
        self.assertIn("--shelf-dir", window)
        self.assertIn("--db", window,
                      "setup_folder.py invokes `c_stack.py setup` without --db; "
                      "the registry will name a database that does not exist")


if __name__ == "__main__":
    unittest.main()
