#!/usr/bin/env python
"""BUILD_PROMPT.md Stage 7.4 -- 12 local hook-input tests, 12/12 required.
0 forbidden commands allowed, 1/1 legitimate command allowed.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "corpus-lab"))
from evidence_v1 import hooks  # noqa: E402

PY = r"C:/Users/Ali/Desktop/retrieval-lab/.venv/Scripts/python.exe"
CLI = r"C:/Users/Ali/Desktop/retrieval-lab/corpus-lab/bin/evidence.py"


def check(cmd):
    return hooks.validate_bash_command(cmd, PY, CLI)


class TestHooks(unittest.TestCase):
    def test_01_legitimate_command_allowed(self):
        cmd = '{} {} doctor --root "C:/Users/Ali/Desktop/retrieval-lab/harness/corpus_15000"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertTrue(ok, reason)

    def test_02_quoted_spaces_still_allowed(self):
        cmd = '{} {} search --request abc123 --concept "sales tax GST"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertTrue(ok, reason)

    def test_03_newline_rejected(self):
        cmd = '{} {} doctor --root "x"\n--evil yes'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_04_semicolon_rejected(self):
        cmd = '{} {} doctor --root "x"; rm -rf /'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_05_pipe_rejected(self):
        cmd = '{} {} doctor --root "x" | cat /etc/passwd'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_06_command_substitution_rejected(self):
        cmd = '{} {} doctor --root "$(cat secret.txt)"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_07_environment_prefix_rejected(self):
        cmd = 'EVIL=1 {} {} doctor --root "x"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_08_path_traversal_rejected(self):
        cmd = '{} {} doctor --root "../../../etc"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_09_alternate_executable_rejected(self):
        cmd = 'C:/Windows/System32/cmd.exe {} doctor --root "x"'.format(CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_10_forged_request_id_rejected_by_value_grammar(self):
        cmd = '{} {} search --request "abc; evil" --concept "x"'.format(PY, CLI)
        ok, reason = check(cmd)
        self.assertFalse(ok)

    def test_11_unowned_image_read_rejected(self):
        ok, reason = hooks.validate_read(
            r"C:\Users\Ali\Desktop\retrieval-lab\harness\corpus_15000\secret.png",
            "req-123", r"C:\Users\Ali\AppData\Local\RetrievalLab\evidence-v1\roots\abc")
        self.assertFalse(ok)

    def test_12_private_file_read_rejected(self):
        ok, reason = hooks.validate_read(
            r"C:\Users\Ali\Desktop\retrieval-lab\_private\harness_keys\answer_key.json",
            "req-123", r"C:\Users\Ali\AppData\Local\RetrievalLab\evidence-v1\roots\abc")
        self.assertFalse(ok)

    # -- supporting case: a request-owned crop IS allowed -------------------- #
    def test_13_request_owned_crop_is_allowed(self):
        runtime = r"C:\Users\Ali\AppData\Local\RetrievalLab\evidence-v1\roots\abc"
        ok, reason = hooks.validate_read(
            runtime + r"\crops\req-123_ev1.png", "req-123", runtime)
        self.assertTrue(ok, reason)


if __name__ == "__main__":
    unittest.main()
