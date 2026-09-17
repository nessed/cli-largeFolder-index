"""Plan F / Phase 11, finding F-01.

`INSTALL.md` promises "Claude Code on the PATH" and Gate R3 greps the package
for `C:\\Users` and `Desktop`. Neither caught the two absolute paths that were
this machine's alone: `pdftotext.exe` under `C:\\Program Files\\Git` and
`claude.exe` under `C:\\nvm4w`. On a second machine `doctor` printed FAIL beside
a directory the reader does not have and INSTALL.md never mentions, and nothing
in the package looked the tools up on PATH.

These tests pin the resolution order that replaced them:
env var, then this machine's historical location, then PATH, then the ordinary
install locations, then a bare name that fails honestly.
"""
import importlib
import os
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
sys.path.insert(0, str(BIN))


class _Env:
    """Set/clear env vars for the duration of a with-block."""

    def __init__(self, **kw):
        self.kw = kw
        self.old = {}

    def __enter__(self):
        for k, v in self.kw.items():
            self.old[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return self

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _fresh_labpaths():
    import labpaths
    return importlib.reload(labpaths)


class TestNoHardcodedToolPaths(unittest.TestCase):
    def test_01_no_module_carries_a_literal_tool_path(self):
        """The literals may live only in labpaths, as the last-resort candidate."""
        for name in ("setup_folder.py", "index_build.py"):
            src = (BIN / name).read_text(encoding="utf-8")
            self.assertNotIn(r"C:\Program Files\Git", src, name)
            self.assertNotIn(r"C:\nvm4w", src, name)

    def test_02_env_var_wins_for_pdftotext(self):
        with _Env(PDFTOTEXT_EXE=r"D:\somewhere\poppler\pdftotext.exe"):
            L = _fresh_labpaths()
            self.assertEqual(L.PDFTOTEXT, r"D:\somewhere\poppler\pdftotext.exe")

    def test_03_env_var_wins_for_claude(self):
        with _Env(CLAUDE_CMD=r"D:\somewhere\claude.exe"):
            L = _fresh_labpaths()
            self.assertEqual(L.CLAUDE, r"D:\somewhere\claude.exe")

    def test_04_path_is_consulted_when_the_known_location_is_absent(self):
        """The real regression: a machine with no Git for Windows and no nvm4w."""
        import labpaths
        L = _fresh_labpaths()
        with _Env(PDFTOTEXT_EXE=None, CLAUDE_CMD=None):
            missing = Path(r"Z:\does-not-exist\nothing.exe")
            old_pdf, old_cl = L._GIT_PDFTOTEXT, L._NVM_CLAUDE_EXE
            old_which = labpaths.shutil.which
            try:
                L._GIT_PDFTOTEXT = missing
                L._NVM_CLAUDE_EXE = missing
                seen = []

                def which(name):
                    seen.append(name)
                    if name == "pdftotext":
                        return r"E:\onpath\pdftotext.exe"
                    if name == "claude.exe":
                        return r"E:\onpath\claude.exe"
                    return None

                labpaths.shutil.which = which
                self.assertEqual(L.find_pdftotext(), r"E:\onpath\pdftotext.exe")
                self.assertEqual(L.find_claude(), r"E:\onpath\claude.exe")
                self.assertIn("pdftotext", seen)
            finally:
                labpaths.shutil.which = old_which
                L._GIT_PDFTOTEXT, L._NVM_CLAUDE_EXE = old_pdf, old_cl

    def test_05_last_resort_is_a_bare_name_not_a_strangers_directory(self):
        import labpaths
        L = _fresh_labpaths()
        with _Env(PDFTOTEXT_EXE=None, CLAUDE_CMD=None):
            missing = Path(r"Z:\does-not-exist\nothing.exe")
            old_pdf, old_cl = L._GIT_PDFTOTEXT, L._NVM_CLAUDE_EXE
            old_which, old_exists = labpaths.shutil.which, L._exists
            try:
                L._GIT_PDFTOTEXT = missing
                L._NVM_CLAUDE_EXE = missing
                labpaths.shutil.which = lambda name: None
                L._exists = lambda p: False
                self.assertEqual(L.find_pdftotext(), "pdftotext.exe")
                self.assertEqual(L.find_claude(), "claude.exe")
            finally:
                labpaths.shutil.which = old_which
                L._exists = old_exists
                L._GIT_PDFTOTEXT, L._NVM_CLAUDE_EXE = old_pdf, old_cl

    def test_06_doctor_names_a_fix_instead_of_a_path_nobody_has(self):
        """A reader whose doctor fails must be told what to install."""
        src = (BIN / "setup_folder.py").read_text(encoding="utf-8")
        self.assertIn("not found on PATH", src)
        self.assertIn("Git for Windows", src)
        self.assertIn("PDFTOTEXT_EXE", src)
        self.assertIn("CLAUDE_CMD", src)

    def test_07_this_machine_still_resolves_to_what_it_always_did(self):
        """No recorded run changes: the historical locations still win here."""
        L = _fresh_labpaths()
        if L._GIT_PDFTOTEXT.exists():
            self.assertEqual(L.PDFTOTEXT, str(L._GIT_PDFTOTEXT))
        if L._NVM_CLAUDE_EXE.exists():
            self.assertEqual(L.CLAUDE, str(L._NVM_CLAUDE_EXE))


if __name__ == "__main__":
    unittest.main()
