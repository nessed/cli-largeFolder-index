"""Plan F / Phase 11: `INITIALIZE.md`, the agent-facing runbook.

The package is handed to someone who has never used a terminal. The intended
first move is: open Claude Code in the folder, say `initialize`. That only works
if the document Claude Code reads is complete, correct against the engine it
describes, and does not quietly drift from `INSTALL.md`.

Every command INITIALIZE.md prints is checked here against the flags the engine
actually accepts, because a runbook that names a flag the tool dropped is worse
than no runbook: the agent will improvise.
"""
import re
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))


class TestInitializeMd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import make_portable
        cls.md = make_portable.INITIALIZE_MD
        cls.dropin = make_portable.CLAUDE_DROPIN_MD
        cls.install = make_portable.INSTALL_MD
        cls.setup_src = (BIN / "setup_folder.py").read_text(encoding="utf-8")

    def test_01_every_step_is_present_and_in_order(self):
        steps = ["## Step 0", "## Step 1", "## Step 2", "## Step 3",
                 "## Step 4", "## Step 5", "## Step 6"]
        last = -1
        for s in steps:
            i = self.md.find(s)
            self.assertNotEqual(i, -1, "missing %s" % s)
            self.assertGreater(i, last, "%s is out of order" % s)
            last = i

    def test_02_install_flags_exist_in_the_engine(self):
        """A flag named here that argparse does not define sends the agent guessing."""
        for flag in ("--folder", "--artefacts", "--seed-env", "--workers"):
            self.assertIn(flag, self.md, "INITIALIZE.md never uses %s" % flag)
            dest = flag.lstrip("-")
            self.assertIn('"%s"' % flag, self.setup_src,
                          "setup_folder.py does not accept %s" % dest)

    def test_03_subcommands_named_here_exist(self):
        for sub in ("doctor", "install", "uninstall", "ask"):
            self.assertIn("setup_folder.py " + sub, self.md, sub)
            self.assertIn('"%s"' % sub, self.setup_src, sub)

    def test_04_selftest_keeps_expect_pages_zero(self):
        """F-17 again: without it the command exits 1 on any real folder."""
        m = re.search(r"c_selftest\.py[^\n]*", self.md)
        self.assertIsNotNone(m)
        self.assertIn("--expect-pages 0", m.group(0))

    def test_05_the_two_env_escapes_are_documented(self):
        """F-01: when a tool is not where the package guessed, say the way out."""
        self.assertIn("PDFTOTEXT_EXE", self.md)
        self.assertIn("CLAUDE_CMD", self.md)
        self.assertIn("Git for Windows", self.md)

    def test_06_the_stderr_red_text_is_called_out(self):
        """F-16: a routine progress line renders as a red NativeCommandError."""
        self.assertIn("NativeCommandError", self.md)
        self.assertIn("not a crash", self.md)

    def test_07_it_forbids_editing_the_engine(self):
        self.assertIn("Do not edit anything under", self.md)
        self.assertIn("bin", self.md)

    def test_08_it_never_hardcodes_a_documents_folder_name(self):
        """The package ships to many folders; `research` is this stage's name only.

        The word may appear as English ("the folder of research documents"); what
        must never appear is a command with a folder name already filled in."""
        self.assertIn("<docs>", self.md)
        for line in self.md.splitlines():
            if "setup_folder.py" in line or "cd " in line:
                self.assertNotIn("research", line, line)

    def test_09_dropin_points_at_the_runbook_and_nothing_else(self):
        self.assertIn("initialize", self.dropin)
        self.assertIn("engine/INITIALIZE.md", self.dropin)
        self.assertIn("engine/INSTALL.md", self.dropin)

    def test_10_install_md_advertises_the_short_way(self):
        self.assertIn("CLAUDE_ROOT.md", self.install)
        self.assertIn("initialize", self.install)

    def test_11_the_package_writes_both_files(self):
        src = (BIN / "make_portable.py").read_text(encoding="utf-8")
        self.assertIn('"INITIALIZE.md").write_text(INITIALIZE_MD', src)
        self.assertIn('"CLAUDE_ROOT.md").write_text(CLAUDE_DROPIN_MD', src)

    def test_12_no_absolute_user_path_leaks_into_either_document(self):
        for doc in (self.md, self.dropin):
            self.assertNotIn(r"C:\Users", doc)
            self.assertNotIn("Desktop", doc)


if __name__ == "__main__":
    unittest.main()
