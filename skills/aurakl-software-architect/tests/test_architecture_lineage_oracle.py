#!/usr/bin/env python3
"""
Unit and Contract Tests for Aurakl Architecture Lineage Oracle
"""

import json
from pathlib import Path
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from architecture_lineage_oracle import (
    AuraklArchitectureOracle,
    is_dag_acyclic,
    validate_coverage,
    validate_dependency_dag,
    validate_invariants_defense,
    validate_pipeline,
    validate_review_consistency,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestArchitectureLineageOracle(unittest.TestCase):

    def setUp(self):
        with open(FIXTURES_DIR / "golden_architecture_suite.json", "r", encoding="utf-8") as f:
            self.golden_suite = json.load(f)

    def test_pipeline_golden_suite_passes(self):
        result = validate_pipeline(self.golden_suite)
        self.assertEqual(result["verdict"], "passed")
        obs = result["observation"]
        self.assertTrue(obs["checks"]["technical_requirements_derived"])
        self.assertTrue(obs["checks"]["layer_count_valid"])
        self.assertTrue(obs["checks"]["domain_model_100_percent_covered"])
        self.assertTrue(obs["checks"]["database_invariants_aligned"])
        self.assertTrue(obs["checks"]["api_backward_compatible"])
        self.assertTrue(obs["checks"]["invariants_defense_covered"])
        self.assertTrue(obs["checks"]["dependency_dag_acyclic"])
        self.assertTrue(obs["checks"]["must_have_requirements_covered"])
        self.assertTrue(obs["checks"]["readiness_consistency"])
        self.assertEqual(len(obs["mismatches"]), 0)

    def test_pipeline_uncovered_must_have_fails(self):
        suite = json.loads(json.dumps(self.golden_suite))
        suite["tech_stack_decision"]["must_have_requirement_ids"].append("REQ-999")
        result = validate_pipeline(suite)
        self.assertEqual(result["verdict"], "failed")
        self.assertIn("Uncovered Must-Have requirements: ['REQ-999']", result["observation"]["mismatches"])

    def test_layer_count_exceeded_fails(self):
        suite = json.loads(json.dumps(self.golden_suite))
        suite["system_architecture_spec"]["layer_count"] = 4
        result = validate_pipeline(suite)
        self.assertEqual(result["verdict"], "failed")
        self.assertIn("layer_count 4 violates max 3 layers rule", result["observation"]["mismatches"])

    def test_api_breaking_changes_allowed_fails(self):
        suite = json.loads(json.dumps(self.golden_suite))
        suite["api_contract_suite"]["backward_compatibility_guarantee"]["breaking_changes_allowed"] = True
        result = validate_pipeline(suite)
        self.assertEqual(result["verdict"], "failed")
        self.assertIn("API contracts must guarantee breaking_changes_allowed == false", result["observation"]["mismatches"])

    def test_invariants_missing_dimension_fails(self):
        suite = json.loads(json.dumps(self.golden_suite))
        suite["architecture_invariants_spec"]["invariants"] = [
            inv for inv in suite["architecture_invariants_spec"]["invariants"]
            if inv.get("dimension") != "observability_and_runtime_ops"
        ]
        result = validate_pipeline(suite)
        self.assertEqual(result["verdict"], "failed")
        mismatches = " ".join(result["observation"]["mismatches"])
        self.assertIn("observability_and_runtime_ops", mismatches)

    def test_dag_acyclic_and_cycle_detection(self):
        nodes = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        edges_acyclic = [{"from_node": "A", "to_node": "B"}, {"from_node": "B", "to_node": "C"}]
        self.assertTrue(is_dag_acyclic(nodes, edges_acyclic))

        edges_cyclic = [{"from_node": "A", "to_node": "B"}, {"from_node": "B", "to_node": "C"}, {"from_node": "C", "to_node": "A"}]
        self.assertFalse(is_dag_acyclic(nodes, edges_cyclic))

    def test_one_vote_veto_gatekeeper(self):
        # When blocking findings exist, READY_FOR_DEV must be rejected
        payload = {
            "report": {
                "readiness_status": "READY_FOR_DEV",
                "blocking_findings": [{"id": "BLOCK-01", "description": "Database unindexed table"}]
            }
        }
        res = validate_review_consistency(payload)
        self.assertEqual(res["verdict"], "failed")
        self.assertIn("Veto violation", res["observation"]["mismatches"][0])


if __name__ == "__main__":
    unittest.main()
