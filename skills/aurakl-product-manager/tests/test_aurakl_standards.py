#!/usr/bin/env python3
"""
Unit tests for Aurakl Quality Standards Integration.
"""

import json
from pathlib import Path
import sys
import unittest

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from aurakl_validator import AuraklValidator, LumenValidator, STANDARDS_DIR

SKILL_ROOT = TEST_DIR.parent
FIXTURES_DIR = SKILL_ROOT / "fixtures"


class TestAuraklStandards(unittest.TestCase):
    def setUp(self):
        self.validator = AuraklValidator()
        golden_suite_path = FIXTURES_DIR / "golden_product_suite.json"
        self.golden_suite = json.loads(golden_suite_path.read_text(encoding="utf-8"))

    def test_all_standards_are_present_and_loadable(self):
        standards = self.validator.load_standards()
        self.assertGreaterEqual(len(standards), 9)
        expected_ids = [
            "pm-std-requirement-quality",
            "pm-std-requirement-gathering-quality",
            "pm-std-competitive-analysis",
            "pm-std-user-journey-and-stories",
            "pm-std-user-story-quality",
            "pm-std-prd-quality",
            "pm-std-product-invariants",
            "pm-std-acceptance-criteria-quality",
            "pm-std-review-quality",
        ]
        for eid in expected_ids:
            self.assertIn(eid, standards, f"Missing standard: {eid}")
            std = standards[eid]
            self.assertEqual(std.get("kind"), "Standard")
            self.assertTrue(bool(std.get("spec", {}).get("rules")))

    def test_schema_to_standard_mapping(self):
        self.assertEqual(
            self.validator.get_governing_standard_id("requirement-analysis.v2.json"),
            "pm-std-requirement-quality",
        )
        self.assertEqual(
            self.validator.get_governing_standard_id("competitive_analysis"),
            "pm-std-competitive-analysis",
        )
        self.assertEqual(
            self.validator.get_governing_standard_id("product_invariants"),
            "pm-std-product-invariants",
        )
        self.assertEqual(
            self.validator.get_governing_standard_id("acceptance-criteria.v2.json"),
            "pm-std-acceptance-criteria-quality",
        )
        self.assertEqual(
            self.validator.get_governing_standard_id("product_review_report"),
            "pm-std-review-quality",
        )

    def test_governing_standard_evaluates_on_product_invariants(self):
        inv = self.golden_suite["product_invariant_set"]
        verdict = self.validator.validate_artifact("product-invariants.v1.json", inv)
        self.assertTrue(verdict.passed)
        std_info = verdict.observations.get("governing_standard")
        self.assertIsNotNone(std_info)
        self.assertEqual(std_info["id"], "pm-std-product-invariants")
        self.assertIn("inv.all_dimensions_covered", std_info["rules_evaluated"])
        self.assertIn("inv.explicit_severity_and_consequence", std_info["rules_evaluated"])

    def test_standard_rule_catches_missing_dimension_in_invariants(self):
        inv_bad = {
            "product_name": "Bad Product",
            "state_invariants": [{"invariant_id": "INV-STA-001", "target_entity": "E", "formal_rule": "R", "severity": "HIGH", "violation_consequence": "C"}],
            "data_integrity_invariants": [],  # Missing/empty
            "security_and_privacy_invariants": [],
            "ux_and_safety_invariants": [],
            "summary": "Bad summary"
        }
        verdict = self.validator.validate_artifact("product-invariants.v1.json", inv_bad)
        self.assertFalse(verdict.passed)
        err_codes = [issue.code for issue in verdict.issues]
        self.assertTrue(any("inv.all_dimensions_covered" in c for c in err_codes))


if __name__ == "__main__":
    unittest.main()
