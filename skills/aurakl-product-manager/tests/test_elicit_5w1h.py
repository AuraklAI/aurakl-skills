#!/usr/bin/env python3
"""Unit tests for the 5W1H requirement elicitation engine."""

import copy
import json
from pathlib import Path
import unittest

import sys
TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from elicit_5w1h import ElicitationEngine, REQUIRED_SLOTS
SKILL_ROOT = TEST_DIR.parent
FIXTURES_DIR = SKILL_ROOT / "fixtures"
if not FIXTURES_DIR.exists():
    FIXTURES_DIR = SKILL_ROOT.parents[2] / "definitions/product-management/fixtures"


class TestElicit5W1H(unittest.TestCase):
    def setUp(self):
        self.brief_file = FIXTURES_DIR / "product_brief.json"
        self.golden_file = FIXTURES_DIR / "golden_product_suite.json"

    def test_brief_ingestion_identifies_missing_slots(self):
        engine = ElicitationEngine(self.brief_file)
        report = engine.assess()

        # Brief only has product_name, vision (what), pain_points (why), stakeholders (who), timeline (when), context (where)
        # It misses: how, current_workarounds, willingness_to_pay, goals, non_goals, implicit_requirements
        self.assertFalse(report.can_proceed)
        self.assertLess(report.completeness_score, 100.0)
        self.assertIn("five_w_one_h.how", report.missing_slots)
        self.assertIn("non_goals", report.missing_slots)
        self.assertIn("implicit_requirements", report.missing_slots)
        self.assertTrue(len(report.questions) > 0)

    def test_golden_requirement_analysis_passes_fully(self):
        golden_suite = json.loads(self.golden_file.read_text(encoding="utf-8"))
        req = golden_suite["requirement_analysis"]
        engine = ElicitationEngine(req)
        report = engine.assess()

        self.assertTrue(report.can_proceed)
        self.assertEqual(report.completeness_score, 100.0)
        self.assertEqual(len(report.missing_slots), 0)
        self.assertEqual(len(report.questions), 0)

    def test_slot_filling_and_export(self):
        engine = ElicitationEngine(self.brief_file)
        # Fill missing slots manually
        engine.set_slot("five_w_one_h.how", "Execute local CLI scans and automatically generate quality reports during PR review")
        engine.set_slot("demand_validation.problem_nature", "painkiller")
        engine.set_slot("demand_validation.current_workarounds", "Manual peer code review and error-prone spreadsheet reconciliation")
        engine.set_slot("demand_validation.willingness_to_pay_or_suffer", "Dedicated engineering productivity budget with strong adoption mandate")
        engine.set_slot("demand_validation.falsification_hypotheses", ["If production incidents are not caused by invariant violations, value proposition is void"])
        engine.set_slot("demand_validation.validation_experiment", "Conduct a 1-month canary trial across 2 mission-critical engineering teams")
        engine.set_slot("goals", ["Reduce production invariant violation incidents to zero", "Shorten PRD review cycle by 50%"])
        engine.set_slot("non_goals", [
            {"item": "Do not replace underlying VCS or IDE platforms", "rationale": "Focus on contract auditing rather than developer editing tools"},
            {"item": "Do not support native mobile clients in MVP", "rationale": "Prioritize core backend microservice architectures"}
        ])
        engine.set_slot("implicit_requirements", [
            {"category": "security", "requirement": "Proprietary source code must never leave enterprise perimeter", "decision": "included"},
            {"category": "performance", "requirement": "Single pipeline audit cycle must complete within 5 seconds", "decision": "included"},
            {"category": "reliability", "requirement": "System must guarantee 100% deterministic idempotent results", "decision": "included"}
        ])

        report = engine.assess()
        self.assertTrue(report.can_proceed)
        self.assertEqual(report.completeness_score, 100.0)

        exported = engine.export_requirement_analysis()
        self.assertEqual(exported["product_name"], "Aurakl Sentinel")
        self.assertEqual(len(exported["non_goals"]), 2)
        self.assertEqual(len(exported["implicit_requirements"]), 3)

    def test_detects_forbidden_non_goals_positive_phrasing(self):
        engine = ElicitationEngine()
        engine.set_slot("non_goals", [
            "Positive statement: system only supports Linux platform",
            "Standard valid non-goal exclusion"
        ])
        report = engine.assess()
        self.assertIn("non_goals", report.missing_slots)
        self.assertIn("only supports", report.slot_diagnostics["non_goals"])


if __name__ == "__main__":
    unittest.main()
