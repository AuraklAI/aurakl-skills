#!/usr/bin/env python3
"""
Unit Tests for Aurakl Architecture Validator Engine (arch_validator.py)
"""

import json
from pathlib import Path
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from arch_validator import AuraklArchitectureValidator

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestArchValidator(unittest.TestCase):

    def setUp(self):
        self.validator = AuraklArchitectureValidator()
        with open(FIXTURES_DIR / "golden_architecture_suite.json", "r", encoding="utf-8") as f:
            self.golden_suite = json.load(f)

    def test_golden_suite_validates_successfully(self):
        verdict = self.validator.validate_suite(self.golden_suite)
        self.assertTrue(verdict.passed, f"Validation failed with issues: {verdict.issues}")
        self.assertEqual(len(verdict.issues), 0)

    def test_placeholder_rejection(self):
        bad_doc = {"notes": "This feature is TODO and pending confirmation"}
        issues = self.validator.validate_grounding(bad_doc)
        self.assertTrue(any(i.code == "forbidden_placeholder" for i in issues))

    def test_chinese_placeholder_rejection(self):
        bad_doc = {"notes": "\u8be5\u7b97\u6cd5\u5f85\u5b9a\uff0c\u540e\u7eed\u8865\u5145"}
        issues = self.validator.validate_grounding(bad_doc)
        self.assertTrue(any(i.code == "forbidden_placeholder" for i in issues))

    def test_individual_tech_stack_validation(self):
        tech_spec = self.golden_suite["tech_stack_decision"]
        verdict = self.validator.validate_artifact("tech_stack_decision", tech_spec)
        self.assertTrue(verdict.passed)

    def test_individual_system_architecture_validation(self):
        sys_spec = self.golden_suite["system_architecture_spec"]
        verdict = self.validator.validate_artifact("system_architecture_spec", sys_spec)
        self.assertTrue(verdict.passed)

    def test_individual_domain_model_validation(self):
        domain_spec = self.golden_suite["domain_model_spec"]
        verdict = self.validator.validate_artifact("domain_model_spec", domain_spec)
        self.assertTrue(verdict.passed)

    def test_individual_database_design_validation(self):
        db_spec = self.golden_suite["database_design_spec"]
        verdict = self.validator.validate_artifact("database_design_spec", db_spec)
        self.assertTrue(verdict.passed)

    def test_individual_api_contracts_validation(self):
        api_spec = self.golden_suite["api_contract_suite"]
        verdict = self.validator.validate_artifact("api_contract_suite", api_spec)
        self.assertTrue(verdict.passed)

    def test_individual_business_flow_validation(self):
        flow_spec = self.golden_suite["business_flow_spec"]
        verdict = self.validator.validate_artifact("business_flow_spec", flow_spec)
        self.assertTrue(verdict.passed)

    def test_individual_invariants_validation(self):
        inv_spec = self.golden_suite["architecture_invariants_spec"]
        verdict = self.validator.validate_artifact("architecture_invariants_spec", inv_spec)
        self.assertTrue(verdict.passed)

    def test_individual_dag_validation(self):
        dag_spec = self.golden_suite["technical_dependency_dag_spec"]
        verdict = self.validator.validate_artifact("technical_dependency_dag_spec", dag_spec)
        self.assertTrue(verdict.passed)

    def test_individual_review_report_validation(self):
        rev_spec = self.golden_suite["architecture_readiness_review_report"]
        verdict = self.validator.validate_artifact("architecture_readiness_review_report", rev_spec)
        self.assertTrue(verdict.passed)


if __name__ == "__main__":
    unittest.main()
