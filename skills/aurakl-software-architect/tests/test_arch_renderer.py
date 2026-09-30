#!/usr/bin/env python3
"""
Unit Tests for Aurakl Architecture Markdown Renderer & Dynamic Language Matching
"""

import json
from pathlib import Path
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from arch_renderer import AuraklArchitectureRenderer, detect_lang

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class TestArchRenderer(unittest.TestCase):

    def setUp(self):
        self.renderer = AuraklArchitectureRenderer()
        with open(FIXTURES_DIR / "golden_architecture_suite.json", "r", encoding="utf-8") as f:
            self.golden_suite = json.load(f)

    def test_language_detection(self):
        self.assertEqual(detect_lang("Pure English text without CJK"), "en")
        self.assertEqual(detect_lang("\u8fd9\u662f\u5305\u542b\u4e2d\u6587\u7684\u67b6\u6784\u6587\u6863"), "zh")
        self.assertEqual(detect_lang({"key": "Pure english"}), "en")
        self.assertEqual(detect_lang({"key": "\u4e2d\u6587\u5185\u5bb9"}), "zh")
        self.assertEqual(detect_lang("any text", explicit_lang="zh"), "zh")
        self.assertEqual(detect_lang("any text", explicit_lang="en"), "en")

    def test_render_suite_english(self):
        md = self.renderer.render_suite(self.golden_suite, lang="en")
        # Assert English section titles
        self.assertIn("Tech Stack Decision & Architecture Decision Records (ADR)", md)
        self.assertIn("System Topology & Layering Architecture Specification", md)
        self.assertIn("Domain Modeling & Core Abstractions Specification", md)
        self.assertIn("Database Design & Storage Specification", md)
        self.assertIn("API Contracts & Communication Protocols", md)
        self.assertIn("Nine-Dimension Panoramic Architecture Invariants Specification", md)
        self.assertIn("Technical Dependency DAG & Development Guidance Specification", md)
        self.assertIn("Architecture Readiness Review & Gatekeeper Report", md)

        # Assert English table headers
        self.assertIn("| Layer / Dimension | Technology / Framework | Version | Rationale |", md)
        self.assertIn("| Invariant ID | Dimension | Invariant Statement | Physical Defense Mechanism | Violation Remediation |", md)
        self.assertIn("| Node ID | Component Name | Bottleneck Risk | Decoupling Strategy |", md)

    def test_render_suite_chinese(self):
        md = self.renderer.render_suite(self.golden_suite, lang="zh")
        # Assert Chinese section titles
        self.assertIn("\u6280\u672f\u9009\u578b\u4e0e\u67b6\u6784\u51b3\u7b56\u89c4\u7ea6 (ADR)", md)
        self.assertIn("\u7cfb\u7edf\u62d3\u6251\u4e0e\u5206\u5c42\u67b6\u6784\u8bbe\u8ba1\u89c4\u7ea6", md)
        self.assertIn("\u9886\u57df\u5efa\u6a21\u4e0e\u6838\u5fc3\u62bd\u8c61\u89c4\u7ea6", md)
        self.assertIn("\u6570\u636e\u5e93\u8bbe\u8ba1\u4e0e\u5b58\u50a8\u89c4\u7ea6", md)
        self.assertIn("\u63a5\u53e3\u5951\u7ea6\u4e0e\u901a\u4fe1\u534f\u8bae\u89c4\u7ea6", md)
        self.assertIn("\u4e5d\u7ef4\u5168\u666f\u67b6\u6784\u4e0d\u53d8\u91cf\u89c4\u7ea6", md)
        self.assertIn("\u6280\u672f\u4f9d\u8d56\u62d3\u6251\u4e0e\u5f00\u53d1\u6307\u5bfc\u89c4\u7ea6", md)
        self.assertIn("\u67b6\u6784\u5c31\u7eea\u5ea6\u8bc4\u5ba1\u4e0e\u51c6\u5165\u62a5\u544a", md)

        # Assert Chinese table headers
        self.assertIn("| \u5206\u5c42\u7ef4\u5ea6 | \u6280\u672f\u7ec4\u4ef6 / \u6846\u67b6 | \u7248\u672c\u8981\u6c42 | \u9009\u578b\u7406\u7531 |", md)
        self.assertIn("| \u4e0d\u53d8\u91cf\u7f16\u53f7 | \u6838\u5fc3\u7ef4\u5ea6 (Dimension) | \u4e0d\u53d8\u91cf\u9648\u8ff0 (Rule) | \u7269\u7406\u9632\u5fa1\u673a\u5236 (Physical Defense) | \u8fdd\u89c4\u8865\u6551\u65b9\u6848 (Remediation) |", md)
        self.assertIn("| \u8282\u70b9\u7f16\u53f7 | \u7ec4\u4ef6\u540d\u79f0 | \u74f6\u9888\u98ce\u9669\u8bc4\u4f30 | \u89e3\u8026\u4e0e\u52a0\u901f\u7b56\u7565 |", md)

    def test_mermaid_diagrams_rendered(self):
        md_en = self.renderer.render_suite(self.golden_suite, lang="en")
        self.assertIn("```mermaid", md_en)
        self.assertIn("graph TD;", md_en)
        self.assertIn("sequenceDiagram", md_en)

    def test_individual_stage_renders(self):
        tech_md = self.renderer.render_tech_stack_decision(self.golden_suite["tech_stack_decision"], "en")
        self.assertTrue(len(tech_md) > 100)

        arch_md = self.renderer.render_system_architecture(self.golden_suite["system_architecture_spec"], "en")
        self.assertTrue(len(arch_md) > 100)

        domain_md = self.renderer.render_domain_model(self.golden_suite["domain_model_spec"], "en")
        self.assertTrue(len(domain_md) > 100)

        db_md = self.renderer.render_database_design(self.golden_suite["database_design_spec"], "en")
        self.assertTrue(len(db_md) > 100)

        api_md = self.renderer.render_api_contracts(self.golden_suite["api_contract_suite"], "en")
        self.assertTrue(len(api_md) > 100)

        flow_md = self.renderer.render_business_flow(self.golden_suite["business_flow_spec"], "en")
        self.assertTrue(len(flow_md) > 100)

        inv_md = self.renderer.render_architecture_invariants(self.golden_suite["architecture_invariants_spec"], "en")
        self.assertTrue(len(inv_md) > 100)

        dag_md = self.renderer.render_dependency_guidance(self.golden_suite["technical_dependency_dag_spec"], "en")
        self.assertTrue(len(dag_md) > 100)

        rev_md = self.renderer.render_review_report(self.golden_suite["architecture_readiness_review_report"], "en")
        self.assertTrue(len(rev_md) > 100)


if __name__ == "__main__":
    unittest.main()
