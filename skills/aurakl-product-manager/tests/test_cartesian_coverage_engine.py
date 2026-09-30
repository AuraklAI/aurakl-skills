#!/usr/bin/env python3
"""
Unit tests for CartesianCoverageEngine and aurakl_pm cartesian CLI command.
"""

import json
from pathlib import Path
import sys
import unittest

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from cartesian_coverage_engine import (
    ALL_FAILURE_CLASSES,
    CartesianCoverageEngine,
    expand_identifiers,
)



class TestCartesianCoverageEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CartesianCoverageEngine()

    def test_expand_identifiers(self):
        sample = {
            "reqs": "REQ-001..003 and REQ-A-010/012",
            "invs": ["INV-KRN-001", "INV-SEC-002..004"],
            "criteria": "AC-001, AC-002/003",
        }
        res = expand_identifiers(sample)
        self.assertIn("REQ-001", res["REQ"])
        self.assertIn("REQ-002", res["REQ"])
        self.assertIn("REQ-003", res["REQ"])
        self.assertIn("REQ-A-010", res["REQ"])
        self.assertIn("REQ-A-012", res["REQ"])

        self.assertIn("INV-KRN-001", res["INV"])
        self.assertIn("INV-SEC-002", res["INV"])
        self.assertIn("INV-SEC-003", res["INV"])
        self.assertIn("INV-SEC-004", res["INV"])

        self.assertIn("AC-001", res["AC"])
        self.assertIn("AC-002", res["AC"])
        self.assertIn("AC-003", res["AC"])

    def test_cartesian_state_machine_matrix_with_unhandled_leaks(self):
        states = ["Initial", "Running", "Completed"]
        events = ["Start", "Finish"]
        # Only 1 transition defined for 3x2 = 6 cells
        declared = [
            {"from_state": "Initial", "trigger_event": "Start", "to_state": "Running", "disposition": "Transition"}
        ]
        rep = self.engine.compute_state_machine_matrix("Task", states, events, declared)
        self.assertEqual(rep.states_count, 3)
        self.assertEqual(rep.events_count, 2)
        self.assertEqual(rep.total_cells, 6)
        # Completed is terminal, gets default rejection
        # Running x Start, Running x Finish are undefined leaks
        self.assertGreater(rep.undefined_cells, 0)
        self.assertLess(rep.coverage_ratio, 100.0)

    def test_cartesian_state_machine_matrix_fully_closed(self):
        states = ["Initial", "Running", "TerminalDone"]
        events = ["Start", "Finish"]
        declared = [
            {"from_state": "Initial", "trigger_event": "Start", "to_state": "Running", "disposition": "Transition"},
            {"from_state": "Initial", "trigger_event": "Finish", "to_state": "Initial", "disposition": "Rejection", "error_code": "ErrNotRunning"},
            {"from_state": "Running", "trigger_event": "Start", "to_state": "Running", "disposition": "No-Op"},
            {"from_state": "Running", "trigger_event": "Finish", "to_state": "TerminalDone", "disposition": "Transition"},
        ]
        rep = self.engine.compute_state_machine_matrix("Task", states, events, declared)
        self.assertEqual(rep.undefined_cells, 0)
        self.assertEqual(rep.coverage_ratio, 100.0)
        self.assertIn("stateDiagram-v2", rep.mermaid_diagram)

    def test_failure_matrix_audit(self):
        inv_data = {
            "invariants": [
                {"id": "INV-001", "name": "SuddenPowerLossCrash", "statement": "Savepoint recovery on power loss"},
                {"id": "INV-002", "name": "TimeoutAndOutcomeUnknown", "statement": "Outcome unknown timeout pending"},
                {"id": "INV-003", "name": "ConcurrencySplitBrain", "statement": "CAS concurrency conflict"},
            ]
        }
        crit_data = {
            "scenarios": [
                {"scenario_id": "SCN-01", "scenario_type": "positive_mainline"},
                {"scenario_id": "SCN-02", "scenario_type": "negative_defense"},
                {"scenario_id": "SCN-03", "scenario_type": "fault_recovery"},
            ]
        }
        rep = self.engine.audit_failure_coverage(inv_data, crit_data)
        self.assertEqual(rep.total_failure_dimensions, 16)
        self.assertGreaterEqual(rep.covered_invariants_count, 3)
        self.assertTrue(rep.meets_30pct_negative_threshold)
        self.assertAlmostEqual(rep.defensive_negative_ratio_pct, 66.67, delta=1.0)

    def test_traceability_closure_detects_orphans_and_missing(self):
        stories = {"stories": [{"id": "USR-001"}, {"id": "USR-002"}]}
        prd = {"features": [{"block_id": "REQ-001", "feature_id": "FEAT-001"}]}
        invariants = {"invariants": [{"id": "INV-001"}, {"id": "INV-002"}]}
        # AC verifies only INV-001 and references only REQ-001, plus a phantom INV-999
        criteria = {
            "scenarios": [
                {
                    "scenario_id": "SCN-01",
                    "derived_from_requirements": ["REQ-001"],
                    "verifies_invariants": ["INV-001", "INV-999"],
                }
            ]
        }
        gap = self.engine.audit_traceability_closure(
            requirements_data=stories,
            prd_data=prd,
            invariants_data=invariants,
            criteria_data=criteria,
        )
        self.assertFalse(gap.closure_passed)
        self.assertIn("INV-002", gap.orphan_invariants)
        self.assertIn("INV-999", gap.missing_invariants)
        self.assertIn("FEAT-001", gap.uncovered_requirements)


if __name__ == "__main__":
    unittest.main()
