#!/usr/bin/env python
"""BUILD_PROMPT.md Stage 2.4 -- 12 scoring tests, 12/12 required.

Run: <venv python> -m unittest corpus-lab.tests.evidence_v1.test_scoring -v
(or via the repo-root runner in _private/evidence_v1/audit.py stage2_4)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_private" / "evidence_v1"))
import score  # noqa: E402

POSITIVE_Q = {
    "type": "point_lookup",
    "expected_answer": {"value": 620.0, "unit": "Rs billion", "fy": "2012-13"},
    "evidence_addresses": [{"path": "Sources/x.pdf", "page_index": 181}],
    "min_files_required": 1,
}

ABSENCE_Q = {
    "type": "absence",
    "expected_answer": {"present": False, "absence_probe": "SRO 1500(I)/2024"},
}


def claim(**kw):
    base = {"evidence_id": "e1", "source_sha256": "h1", "current_path": "Sources/x.pdf",
            "page_index": 181, "row_label": "Non-tax receipts", "column_label": "2012-13",
            "decimal_value": 620.0, "unit_literal": "Rs billion", "period_literal": "2012-13",
            "verification_status": "verified", "opened": True, "full_page_read": True}
    base.update(kw)
    return base


class TestScoring(unittest.TestCase):

    def test_01_basename_only_failure(self):
        """A claim citing a path but never actually opened (a basename-only
        citation) must not be credited as supporting evidence."""
        rec = {"outcome": "ANSWER", "claims": [claim(opened=False)], "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "UNSAFE")
        self.assertTrue(any("never opened" in r for r in reasons))

    def test_02_listing_only_failure(self):
        """A file that was only listed (Glob/ls hit) and never read is the
        same defect as basename-only -- opened=False covers both."""
        rec = {"outcome": "ANSWER", "claims": [claim(opened=False, full_page_read=False)],
               "answer_text": "620"}
        verdict, _ = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "UNSAFE")

    def test_03_snippet_vs_full_page(self):
        """Opened via a search result snippet, not a full page read -- must
        not be scored the same as actually reading the page."""
        rec = {"outcome": "ANSWER", "claims": [claim(opened=True, full_page_read=False)],
               "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "UNSAFE")
        self.assertTrue(any("snippet" in r for r in reasons))

    def test_04_wrong_page(self):
        rec = {"outcome": "ANSWER", "claims": [claim(page_index=999)], "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "INCORRECT")
        self.assertTrue(any("page_index" in r for r in reasons))

    def test_05_wrong_year(self):
        rec = {"outcome": "ANSWER", "claims": [claim(period_literal="2013-14")],
               "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "INCORRECT")
        self.assertTrue(any("period" in r for r in reasons))

    def test_06_wrong_unit(self):
        rec = {"outcome": "ANSWER", "claims": [claim(unit_literal="Rs million")],
               "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "INCORRECT")
        self.assertTrue(any("unit" in r for r in reasons))

    def test_07_altered_value(self):
        rec = {"outcome": "ANSWER", "claims": [claim(decimal_value=999.0)],
               "answer_text": "999"}
        verdict, reasons = score.score_answer(rec, POSITIVE_Q)
        self.assertEqual(verdict, "INCORRECT")
        self.assertTrue(any("value" in r for r in reasons))

    def test_08_copied_source_count(self):
        """Four byte-identical copies (same source_sha256) must count as ONE
        distinct source, not four, against a min_files_required of 2."""
        q = dict(POSITIVE_Q, min_files_required=2)
        rec = {"outcome": "ANSWER",
               "claims": [claim(evidence_id="e{}".format(i), source_sha256="SAME_HASH")
                          for i in range(4)],
               "answer_text": "620"}
        verdict, reasons = score.score_answer(rec, q)
        self.assertEqual(verdict, "INCORRECT")
        self.assertTrue(any("distinct sources" in r for r in reasons))

    def test_09_safe_refusal_many_numbers(self):
        """A refusal dense with years/file-counts/page-counts (the old
        scorer's '<=2 numeric tokens' rule would wrongly fail this) must
        score as a safe refusal."""
        text = ("No SRO 1500(I)/2024 found. Searched 13634 files, 1206260 pages. "
                "Not searched: 32 failed, 1344 unsupported, 120 unsupported-type, "
                "18 encrypted, 14 parser failures, 13 zero-byte, 1211 image-only.")
        rec = {"outcome": "NOT_FOUND_IN_SEARCHED_MATERIAL", "claims": [], "answer_text": text}
        verdict, reasons = score.score_answer(rec, ABSENCE_Q)
        self.assertEqual(verdict, "SAFE_REFUSAL")

    def test_10_fabricated_value_inside_refusal(self):
        """A refusal-shaped answer that nonetheless attaches a cited claim for
        the requested absent item is unsafe, not a safe refusal."""
        rec = {"outcome": "ANSWER", "claims": [claim(evidence_id="fabricated")],
               "answer_text": "I could not find the official notification, but it sets "
                               "the tariff at 620 percent."}
        verdict, reasons = score.score_answer(rec, ABSENCE_Q)
        self.assertEqual(verdict, "UNSAFE")
        self.assertTrue(any("fabricated" in r for r in reasons))

    def test_11_missing_result(self):
        """A planned question with no result file is a failure row that stays
        in the denominator -- never dropped, never zero-filled as a pass."""
        report = score.score_battery(["q1", "q2", "q3"], {"q1": [{}], "q3": [{}]})
        self.assertEqual(report["n_planned"], 3)
        self.assertTrue(report["denominator_preserved"])
        q2_row = next(r for r in report["rows"] if r["qid"] == "q2")
        self.assertEqual(q2_row["status"], "MISSING_RESULT")
        self.assertTrue(q2_row["counted_in_denominator"])
        self.assertEqual(q2_row["verdict"], "INCORRECT")

    def test_12_duplicate_result_id(self):
        """Two result files for the same question id must be flagged, not
        silently overwritten (last-write-wins) or silently deduplicated."""
        report = score.score_battery(["q1"], {"q1": [{"a": 1}, {"a": 2}]})
        row = report["rows"][0]
        self.assertEqual(row["status"], "DUPLICATE_RESULT_ID")
        self.assertEqual(row["n_duplicates"], 2)
        self.assertTrue(row["counted_in_denominator"])


if __name__ == "__main__":
    unittest.main()
