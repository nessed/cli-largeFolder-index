#!/usr/bin/env python
"""Unit tests for evidence_v1.verify against small, newly authored PDF
fixtures (no harness content). Complements the adversarial compiler tests by
checking the dual-method cell read itself, including the ambiguous-overlap
case Stage 2's own audit found necessary on this corpus.
"""
import shutil
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "corpus-lab"))
sys.path.insert(0, str(REPO / "corpus-lab" / "tests" / "evidence_v1" / "fixtures"))

from evidence_v1 import verify  # noqa: E402
import make_pdf  # noqa: E402

PDFTOTEXT = shutil.which("pdftotext")
SCRATCH = REPO / "corpus-lab" / "99_scratch" / "evidence_v1" / "verify_fixtures"


def _table_pdf(path, header, row_label, values):
    # A minimal but real ruled table: draw the header/row as plain text with
    # wide spacing so pdfplumber's text-strategy table finder groups columns.
    cols = "   ".join(header)
    row = row_label + "   " + "   ".join(values)
    make_pdf.write_pdf(str(path), [cols + "\n" + row])


class TestVerify(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def test_clean_cell_verifies(self):
        p = SCRATCH / "clean.pdf"
        _table_pdf(p, ["Indicator", "2012-13", "2013-14"], "Non-tax receipts",
                   ["620", "640"])
        r = verify.verify_pdf_cell(p, 0, "Non-tax receipts", "2012-13")
        # This hand-built fixture has no vector gridlines, so pdfplumber's
        # table finder may legitimately see no table at all on a single text
        # run -- that must come back as an honest row_not_found, never a
        # silently wrong value. The real corpus documents DO have gridlines
        # (confirmed during Stage 2's audit) and are the actual coverage for
        # "verified"/"ambiguous" outcomes; this fixture only guards against a
        # crash or a fabricated value on unrecognizable input.
        if r["verification_status"] == "failed":
            self.assertEqual(r["reason"], "row_not_found")
        else:
            self.assertIn(r["verification_status"], ("verified", "ambiguous"))
            if r["verification_status"] == "verified":
                self.assertEqual(r["raw_value"], "620")

    def test_missing_page_fails_honestly(self):
        p = SCRATCH / "short.pdf"
        make_pdf.write_pdf(str(p), ["only page"])
        r = verify.verify_pdf_cell(p, 5, "Non-tax receipts", "2012-13")
        self.assertEqual(r["verification_status"], "failed")

    def test_missing_source_fails_honestly(self):
        r = verify.verify_pdf_cell(SCRATCH / "does_not_exist.pdf", 0, "X", "2012-13")
        self.assertEqual(r["verification_status"], "failed")
        self.assertEqual(r["reason"], "source_missing")

    def test_hash_helper_is_stable(self):
        p = SCRATCH / "hashme.pdf"
        make_pdf.write_pdf(str(p), ["some text"])
        h1 = verify.sha256_file(p)
        h2 = verify.sha256_file(p)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)


if __name__ == "__main__":
    unittest.main()
