"""Plan F / Phase 11, finding F-17.

`INSTALL.md`'s "Check the build" section prints a `c_selftest.py` command. Run
exactly as printed against any folder other than the frozen 15,000 rung, it
exits 1: `--expect-pages` defaults to 1,206,260, that rung's page count, so the
`coverage` check fails and `_overall` goes false. The engine is fine; the
document is wrong.

`p10_cleanroom.py:205-212` already passes `--expect-pages 0` with a comment
saying "the flag exists for exactly this case". The clean-room gate therefore
never ran the command a reader of INSTALL.md would run -- the same blind spot
that hid F-02.

These tests pin the two halves together: the flag still means what it means, and
the document prints it.
"""
import re
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))


class TestInstallMdSelftestCommand(unittest.TestCase):
    def setUp(self):
        self.mp = (BIN / "make_portable.py").read_text(encoding="utf-8")
        self.st = (BIN / "c_selftest.py").read_text(encoding="utf-8")

    def _install_md(self):
        import make_portable
        return make_portable.INSTALL_MD

    def test_01_expect_pages_still_defaults_to_the_15000_rung(self):
        """If this default ever changes, the reason for the flag changes too."""
        m = re.search(r'"--expect-pages".{0,200}?default=(\d+)', self.st, re.S)
        self.assertIsNotNone(m, "could not find the --expect-pages default")
        self.assertEqual(int(m.group(1)), 1206260)

    def test_02_install_md_selftest_command_passes_expect_pages_zero(self):
        """The command as printed must work on a folder that is not that rung."""
        md = self._install_md()
        line = [l for l in md.splitlines() if "c_selftest.py" in l]
        self.assertTrue(line, "INSTALL.md prints no c_selftest.py command")
        self.assertIn(
            "--expect-pages 0", line[0],
            "INSTALL.md's c_selftest command omits --expect-pages 0, so it "
            "asserts the 15,000-rung page count against the user's folder and "
            "exits 1 on every folder but that one")

    def test_03_install_md_selftest_command_still_passes_db_and_shelf(self):
        md = self._install_md()
        line = [l for l in md.splitlines() if "c_selftest.py" in l][0]
        self.assertIn("--db", line)
        self.assertIn("--shelf", line)

    def test_04_install_md_has_no_absolute_paths(self):
        """Gate R3's rule, asserted on the document this plan edits."""
        md = self._install_md()
        self.assertNotIn("C:" + chr(92) + "Users", md)
        self.assertNotIn("Desktop", md)


if __name__ == "__main__":
    unittest.main()
