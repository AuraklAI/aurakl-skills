#!/usr/bin/env python3
"""Contract and mutation tests for the Aurakl five-dimensional validator."""

import copy
import json
from pathlib import Path
import unittest

import sys
TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from aurakl_validator import AuraklValidator, PurePythonSchemaValidator
SKILL_ROOT = TEST_DIR.parent
FIXTURES_DIR = SKILL_ROOT / "fixtures"
if not FIXTURES_DIR.exists():
    FIXTURES_DIR = SKILL_ROOT.parents[2] / "definitions/product-management/fixtures"


class TestAuraklValidator(unittest.TestCase):
    def setUp(self):
        self.golden_file = FIXTURES_DIR / "golden_product_suite.json"
        self.golden_suite = json.loads(self.golden_file.read_text(encoding="utf-8"))
        self.validator = AuraklValidator()

    def test_golden_suite_passes_all_gates(self):
        verdict = self.validator.validate_suite_oracle(self.golden_suite)
        self.assertTrue(verdict.passed)
        self.assertEqual(len(verdict.issues), 0)
        self.assertIn("oracle_pipeline", verdict.observations)
        self.assertEqual(verdict.observations["oracle_pipeline"]["checks"]["invariant_coverage"], True)
        self.assertEqual(verdict.observations["oracle_pipeline"]["checks"]["negative_ratio"], True)

    def test_golden_requirement_analysis_passes_individual_gate(self):
        req = self.golden_suite["requirement_analysis"]
        verdict = self.validator.validate_artifact("requirement_analysis", req)
        self.assertTrue(verdict.passed)
        self.assertEqual(len(verdict.issues), 0)

    def test_placeholder_todo_is_strictly_rejected(self):
        mutated = copy.deepcopy(self.golden_suite["requirement_analysis"])
        mutated["five_w_one_h"]["why"] = "Frequent regression during refactoring requires defense TODO"
        verdict = self.validator.validate_artifact("requirement_analysis", mutated)

        self.assertFalse(verdict.passed)
        placeholder_issues = [i for i in verdict.issues if i.code == "placeholder_forbidden"]
        self.assertTrue(len(placeholder_issues) > 0)
        self.assertIn("TODO", placeholder_issues[0].message)

    def test_missing_5w1h_is_rejected(self):
        mutated = copy.deepcopy(self.golden_suite["requirement_analysis"])
        mutated["five_w_one_h"].pop("how")
        verdict = self.validator.validate_artifact("requirement_analysis", mutated)

        self.assertFalse(verdict.passed)
        codes = [i.code for i in verdict.issues]
        self.assertIn("missing_5w1h:how", codes)

    def test_insufficient_non_goals_rejected(self):
        mutated = copy.deepcopy(self.golden_suite["requirement_analysis"])
        mutated["non_goals"] = [{"item": "Only one item"}]
        verdict = self.validator.validate_artifact("requirement_analysis", mutated)

        self.assertFalse(verdict.passed)
        codes = [i.code for i in verdict.issues]
        self.assertIn("insufficient_non_goals", codes)

    def test_forbidden_positive_non_goals_phrasing_rejected(self):
        mutated = copy.deepcopy(self.golden_suite["requirement_analysis"])
        mutated["non_goals"] = [
            {"item": "rephrase to only supports backend architecture", "rationale": "positive statement"},
            {"item": "Standard valid non-goal", "rationale": "Legitimate rationale"}
        ]
        verdict = self.validator.validate_artifact("requirement_analysis", mutated)

        self.assertFalse(verdict.passed)
        codes = [i.code for i in verdict.issues]
        self.assertIn("forbidden_non_goal_phrase", codes)

    def test_negative_scenario_ratio_below_30_rejected(self):
        criteria = copy.deepcopy(self.golden_suite["acceptance_criteria_set"])
        # Change scenario types to all happy_path
        for s in criteria.get("scenarios", []):
            s["scenario_type"] = "happy_path"
        verdict = self.validator.validate_artifact("acceptance_criteria", criteria)

        self.assertFalse(verdict.passed)
        codes = [i.code for i in verdict.issues]
        self.assertIn("negative_ratio_below_threshold", codes)

    def test_oracle_catches_matrix_drift(self):
        mutated_suite = copy.deepcopy(self.golden_suite)
        # Drift matrix counts
        mutated_suite["acceptance_criteria_set"]["invariant_coverage_matrix"]["total_invariants_count"] = 999
        verdict = self.validator.validate_suite_oracle(mutated_suite)

        self.assertFalse(verdict.passed)
        oracle_issues = [i for i in verdict.issues if i.dimension == "oracle"]
        self.assertTrue(len(oracle_issues) > 0)

    def test_all_31_schemas_are_registered_and_resolvable(self):
        schemas = self.validator.list_all_schemas()
        self.assertGreaterEqual(len(schemas), 31)
        for s in schemas:
            fname = s["filename"]
            resolved = self.validator.resolve_schema(fname)
            self.assertIsNotNone(resolved, f"Failed to resolve schema by filename: {fname}")
            # Also test resolving by stem
            stem = Path(fname).stem
            resolved_stem = self.validator.resolve_schema(stem)
            self.assertIsNotNone(resolved_stem, f"Failed to resolve schema by stem: {stem}")

    def test_sub_step_schema_validation(self):
        # Test beachhead-strategy.v1
        valid_beachhead = {
            "product_name": "Aurakl Sentinel",
            "gap_analysis": {
                "unmet_customer_needs": ["Unable to automate code compliance auditing"],
                "feature_parity_gaps": ["Lacking integration with mainstream CI tools"],
                "user_experience_frictions": ["Tedious manual spreadsheet reconciliation"]
            },
            "beachhead_strategy": {
                "target_niche": "Financial risk core engineering teams",
                "entry_point_feature": "Sub-3s invariant gatekeeper upon code commit",
                "value_curve_differentiation": "Deterministic algebra formulas vs heuristic regex"
            },
            "summary": "Target financial-grade consistency to establish an irreplaceable beachhead"
        }
        verdict = self.validator.validate_artifact("beachhead-strategy.v1", valid_beachhead)
        self.assertTrue(verdict.passed)
        self.assertEqual(len(verdict.issues), 0)

    def test_calc_metrics_helpers(self):
        inv_data = self.golden_suite["product_invariant_set"]
        crit_data = self.golden_suite["acceptance_criteria_set"]

        cov = self.validator.calc_invariant_coverage(inv_data, crit_data)
        self.assertTrue(cov["is_full_coverage"])
        self.assertEqual(cov["coverage_basis_points"], 10000)
        self.assertEqual(cov["total_invariants"], 4)
        self.assertEqual(cov["covered_invariants"], 4)

        neg = self.validator.calc_negative_ratio(crit_data)
        self.assertTrue(neg["meets_safety_threshold"])
        self.assertEqual(neg["negative_ratio_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
