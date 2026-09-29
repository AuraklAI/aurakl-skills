#!/usr/bin/env python3
"""
Unit Tests for Aurakl Architecture Cartesian Completeness Engine (arch_cartesian_engine.py)
"""

import json
from pathlib import Path
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from arch_cartesian_engine import AuraklArchCartesianEngine, ARCH_FAILURE_CLASSES

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestArchCartesianEngine(unittest.TestCase):

    def setUp(self):
        with open(FIXTURES_DIR / "golden_architecture_suite.json", "r", encoding="utf-8") as f:
            self.golden_suite = json.load(f)

    def test_golden_suite_cartesian_audit_complete(self):
        report = AuraklArchCartesianEngine.audit_suite(self.golden_suite)
        self.assertTrue(report.is_complete, f"Expected complete but got gaps: {report.gaps}")
        self.assertTrue(report.dag_acyclic)
        self.assertEqual(report.critical_path_length, 4)
        self.assertEqual(len(report.missing_invariant_dimensions), 0)
        self.assertEqual(report.requirement_coverage_pct, 100.0)
        self.assertEqual(len(report.uncovered_requirements), 0)

    def test_failure_classes_defined(self):
        self.assertEqual(len(ARCH_FAILURE_CLASSES), 16)
        domains = {fc["domain"] for fc in ARCH_FAILURE_CLASSES}
        self.assertTrue({"Storage", "Concurrency", "Security", "Resilience"}.issubset(domains))

    def test_unhandled_state_transition_detection(self):
        state_machines = [
            {
                "entity_name": "TestEntity",
                "initial_state": "CREATED",
                "terminal_states": ["DELETED"],
                "transitions": [
                    {"from_state": "CREATED", "event": "ACTIVATE", "to_state": "ACTIVE"}
                    # missing transitions from ACTIVE
                ]
            }
        ]
        total, unhandled = AuraklArchCartesianEngine.audit_state_transitions(state_machines)
        self.assertTrue(len(unhandled) > 0)
        self.assertEqual(unhandled[0]["entity"], "TestEntity")


if __name__ == "__main__":
    unittest.main()
