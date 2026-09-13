#!/usr/bin/env python
"""BUILD_PROMPT.md Stage 6.3 -- 20 adversarial compiler cases, 20/20 required.
Pure logic tests against evidence_v1.compile; no corpus, no model, no I/O.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "corpus-lab"))
from evidence_v1 import compile as C  # noqa: E402


def ev(**kw):
    base = {
        "evidence_id": "e1", "source_sha256": "h1", "current_path": "x.pdf",
        "format": "pdf", "page_index": 0, "viewer_page": 1, "row_label": "Row",
        "column_label": "2012-13", "period_literal": "2012-13", "raw_value": "620",
        "unit_literal": "Rs billion", "status_literal": None,
        "verification_status": "verified", "table_label": "Table 1",
    }
    base.update(kw)
    return base


class TestCompile(unittest.TestCase):
    # -- wrong year (2) --------------------------------------------------- #
    def test_01_wrong_year_table(self):
        r = C.compose("table", [ev(period_literal="2013-14")], "req1",
                       requested={"period_literal": "2012-13"})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_02_wrong_year_quote(self):
        r = C.compose("table", [ev(period_literal="1999-00")], "req1",
                       requested={"period_literal": "2012-13"})
        self.assertEqual(r["outcome"], "CONFLICT")

    # -- wrong units (2) --------------------------------------------------- #
    def test_03_wrong_units_no_conversion(self):
        r = C.compose("table", [ev(unit_literal="percent")], "req1",
                       requested={"unit_literal": "Rs billion"})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_04_wrong_units_mismatched_currency(self):
        r = C.compose("table", [ev(unit_literal="USD million")], "req1",
                       requested={"unit_literal": "Rs billion"})
        self.assertEqual(r["outcome"], "CONFLICT")

    # -- allocation vs execution (2) --------------------------------------- #
    def test_05_allocation_vs_execution_psdp(self):
        r = C.compose("table", [ev(series_kind="allocation")], "req1",
                       requested={"series_kind": "execution"})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_06_allocation_vs_execution_adp(self):
        r = C.compose("table", [ev(series_kind="released")], "req1",
                       requested={"series_kind": "allocation"})
        self.assertEqual(r["outcome"], "CONFLICT")

    # -- population/sex denominator mismatch (2) ---------------------------- #
    def test_07_population_mismatch_sex(self):
        r = C.compose("table", [ev(population_literal="female")], "req1",
                       requested={"population_literal": "total"})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_08_population_mismatch_age_universe(self):
        r = C.compose("table", [ev(population_literal="15+")], "req1",
                       requested={"population_literal": "10+"})
        self.assertEqual(r["outcome"], "CONFLICT")

    # -- changed label without bridge (2) ------------------------------------ #
    def test_09_changed_label_no_bridge(self):
        r = C.compose("table", [ev(row_label="Sales Tax")], "req1",
                       requested={"row_label": "GST collection"})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_10_changed_label_with_bridge_is_allowed(self):
        """The same mismatch IS allowed through when an explicit bridge is
        supplied -- an alias cannot silently authorize it, but a stated
        bridge can."""
        r = C.compose("table", [ev(row_label="Sales Tax")], "req1",
                       requested={"row_label": "GST collection", "label_bridge": True})
        self.assertNotEqual(r["outcome"], "CONFLICT")

    # -- missing five-year-mean observation (2) ------------------------------ #
    def test_11_mean_compare_missing_one_year(self):
        years = ["2001-02", "2002-03", "2003-04", "2004-05", "2005-06",
                 "2006-07", "2007-08", "2008-09", "2009-10", "2010-11"]
        evs = [ev(period_literal=y, raw_value="100") for y in years[:9]]  # 9, not 10
        r = C.compose("mean_compare", evs, "req1", requested_years=years)
        self.assertEqual(r["outcome"], "UNAVAILABLE_COVERAGE")

    def test_12_mean_compare_no_interval_supplied(self):
        r = C.compose("mean_compare", [ev()], "req1", requested_years=None)
        self.assertEqual(r["outcome"], "AMBIGUOUS_EXTRACTION")

    # -- duplicate alias as second source (2) -------------------------------- #
    def test_13_duplicate_source_trajectory_two_periods(self):
        evs = [ev(source_sha256="SAME", period_literal="2012-13"),
               ev(source_sha256="SAME", period_literal="2013-14")]
        r = C.compose("trajectory", evs, "req1")
        self.assertEqual(r["n_distinct_sources"], 1)

    def test_14_duplicate_source_three_copies_one_distinct(self):
        evs = [ev(source_sha256="SAME", period_literal=y)
               for y in ("2012-13", "2013-14", "2014-15")]
        r = C.compose("trajectory", evs, "req1")
        self.assertEqual(r["n_distinct_sources"], 1)

    # -- forged evidence ID (2) ------------------------------------------------ #
    def test_15_forged_evidence_id_rejected(self):
        r = C.compose("table", [ev(evidence_id="forged-not-issued")], "req1",
                       requested={"issued_evidence_ids": {"real-id-1", "real-id-2"}})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_16_forged_evidence_id_empty_issued_set(self):
        r = C.compose("table", [ev(evidence_id="anything")], "req1",
                       requested={"issued_evidence_ids": set()})
        self.assertEqual(r["outcome"], "CONFLICT")

    # -- stale hash (2) --------------------------------------------------------- #
    def test_17_stale_hash_rejected(self):
        r = C.compose("table", [ev(source_sha256="old_hash", current_hash_at_read="new_hash")],
                       "req1", requested={})
        self.assertEqual(r["outcome"], "CONFLICT")

    def test_18_stale_hash_matching_is_accepted(self):
        r = C.compose("table", [ev(source_sha256="same_hash", current_hash_at_read="same_hash")],
                       "req1", requested={})
        self.assertNotEqual(r["outcome"], "CONFLICT")

    # -- provisional/negative/zero value handling (2) ---------------------------- #
    def test_19_provisional_flag_preserved(self):
        # status_literal is normally set by verify.py from the printed P/R
        # flag; this fixture sets it directly since no real PDF is involved.
        r = C.compose("table", [ev(raw_value="117.2 P", status_literal="Provisional")], "req1")
        self.assertIn("Provisional", r["answer_text"])

    def test_20_zero_value_not_treated_as_missing(self):
        """A printed 0 is a real observation, not a falsy 'no value'."""
        r = C.compose("table", [ev(raw_value="0")], "req1")
        self.assertEqual(r["outcome"], "ANSWER")
        self.assertIn(": 0 ", r["answer_text"])


if __name__ == "__main__":
    unittest.main()
