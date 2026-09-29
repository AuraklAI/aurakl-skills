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
        self.assertEqual(detect_lang("这是包含中文的架构文档"), "zh")
        self.assertEqual(detect_lang({"key": "Pure english"}), "en")
        self.assertEqual(detect_lang({"key": "中文内容"}), "zh")
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
        self.assertIn("技术选型与架构决策规约 (ADR)", md)
        self.assertIn("系统拓扑与分层架构设计规约", md)
        self.assertIn("领域建模与核心抽象规约", md)
        self.assertIn("数据库设计与存储规约", md)
        self.assertIn("接口契约与通信协议规约", md)
        self.assertIn("九维全景架构不变量规约", md)
        self.assertIn("技术依赖拓扑与开发指导规约", md)
        self.assertIn("架构就绪度评审与准入报告", md)

        # Assert Chinese table headers
        self.assertIn("| 分层维度 | 技术组件 / 框架 | 版本要求 | 选型理由 |", md)
        self.assertIn("| 不变量编号 | 核心维度 (Dimension) | 不变量陈述 (Rule) | 物理防御机制 (Physical Defense) | 违规补救方案 (Remediation) |", md)
        self.assertIn("| 节点编号 | 组件名称 | 瓶颈风险评估 | 解耦与加速策略 |", md)

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
