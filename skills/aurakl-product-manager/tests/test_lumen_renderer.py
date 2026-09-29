#!/usr/bin/env python3
"""
Unit tests for AuraklMarkdownRenderer / LumenMarkdownRenderer (Template Conformance Engine).

Tests English template generation (default for English fixtures) and dynamic
language matching (switching to Chinese headers and labels when Chinese input is provided).
"""

import json
from pathlib import Path
import sys
import unittest

TEST_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TEST_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from lumen_renderer import LumenMarkdownRenderer, AuraklMarkdownRenderer, render_all_artifacts

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "fixtures"


class TestLumenMarkdownRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = LumenMarkdownRenderer()
        golden_suite_path = FIXTURES_DIR / "golden_product_suite.json"
        self.golden_suite = json.loads(golden_suite_path.read_text(encoding="utf-8"))

    # =========================================================================
    # English Rendering Tests (Derived from English Golden Suite)
    # =========================================================================
    def test_renders_requirement_analysis_with_all_required_sections(self):
        req = self.golden_suite["requirement_analysis"]
        md = self.renderer.render_requirement_analysis(req)
        self.assertIn("## What (Deliverables & Scope)", md)
        self.assertIn("## Why (Business Motivation)", md)
        self.assertIn("## Who (Stakeholder Personas)", md)
        self.assertIn("## When / Where / How (Context & Journey)", md)
        self.assertIn("## Implicit Requirements", md)
        self.assertIn("## Non-Goals", md)
        self.assertIn("## Core Feature Priorities", md)
        self.assertIn("## Product Classification", md)
        self.assertIn("## Open Questions & Decisions", md)
        self.assertIn("pm-tpl-requirement-analysis", md)

    def test_renders_competitive_analysis_with_all_required_sections(self):
        comp = self.golden_suite["competitive_intelligence"]
        md = self.renderer.render_competitive_analysis(comp)
        self.assertIn("## Market Overview", md)
        self.assertIn("## Mainstream Competitor Analysis Matrix", md)
        self.assertIn("## Beachhead Strategy", md)
        self.assertIn("## Long-Term Moat Assessment", md)
        self.assertIn("## Why We Win", md)
        self.assertIn("pm-tpl-competitive-analysis", md)

    def test_renders_user_stories_with_all_required_sections(self):
        story = self.golden_suite["user_story_set"]
        journey = self.golden_suite["user_journey_model"]
        md = self.renderer.render_user_stories(story, journey)
        self.assertIn("## Overview", md)
        self.assertIn("## User Personas", md)
        self.assertIn("## User Journeys", md)
        self.assertIn("## Epics", md)
        self.assertIn("## User Stories", md)
        self.assertIn("## Priority Matrix", md)
        self.assertIn("## Dependencies", md)
        self.assertIn("## Version History", md)
        self.assertIn("pm-tpl-user-story-set", md)

    def test_renders_prd_with_all_required_sections(self):
        prd = self.golden_suite["comprehensive_prd"]
        md = self.renderer.render_prd(prd)
        self.assertIn("## Cloud Scope of Responsibility", md)
        self.assertIn("## Service Modules Inventory", md)
        self.assertIn("## Core Service Requirements", md)
        self.assertIn("## AI Service Integration Requirements", md)
        self.assertIn("## Data Storage Requirements", md)
        self.assertIn("## Privacy & Compliance Requirements", md)
        self.assertIn("## SLA Definitions", md)
        self.assertIn("## Background Tasks & Jobs", md)
        self.assertIn("## Admin Console Requirements", md)
        self.assertIn("## Non-Functional Requirements", md)
        self.assertIn("## Dependencies & Constraints", md)
        self.assertIn("## Risks & Assumptions", md)
        self.assertIn("## Version History", md)
        self.assertIn("pm-tpl-prd-cloud-platform", md)

    def test_renders_product_invariants_with_all_required_sections(self):
        inv = self.golden_suite["product_invariant_set"]
        md = self.renderer.render_product_invariants(inv)
        self.assertIn("## State Machine Invariants", md)
        self.assertIn("## Data Integrity & Conservation Invariants", md)
        self.assertIn("## Access Control & Tenant Isolation Invariants", md)
        self.assertIn("## UX & Interaction Safety Invariants", md)
        self.assertIn("pm-tpl-product-invariants", md)

    def test_renders_acceptance_criteria_with_all_required_sections(self):
        crit = self.golden_suite["acceptance_criteria_set"]
        md = self.renderer.render_acceptance_criteria(crit)
        self.assertIn("## Overview", md)
        self.assertIn("## Functional Acceptance Criteria", md)
        self.assertIn("## Non-Functional Acceptance Criteria", md)
        self.assertIn("## Integration Test Acceptance Criteria", md)
        self.assertIn("## Test Data Requirements", md)
        self.assertIn("## Defect Severity & Release Gates", md)
        self.assertIn("## Acceptance Criteria Priority", md)
        self.assertIn("## Version History", md)
        self.assertIn("pm-tpl-acceptance-criteria", md)

    def test_renders_review_report_with_all_required_sections(self):
        rep = self.golden_suite["product_readiness_review_report"]
        md = self.renderer.render_review_report(rep)
        self.assertIn("## Executive Summary & Verdict", md)
        self.assertIn("## Traceability Lineage Audit", md)
        self.assertIn("## Invariant Defense Audit", md)
        self.assertIn("## Blocking Findings", md)
        self.assertIn("## Advisory Findings", md)
        self.assertIn("## Decision Rationale", md)
        self.assertIn("pm-tpl-review-report", md)

    # =========================================================================
    # Dynamic Language Matching Tests (Chinese Detection & Explicit Override)
    # =========================================================================
    def test_dynamic_language_matching_chinese_input(self):
        zh_req = {
            "product_name": "测试安全哨兵",
            "five_w_one_h": {
                "what": "构建企业级不可篡改审计系统",
                "why": "满足数据主权监管与防篡改硬性要求",
                "who": "安全架构师与合规官",
                "when": "实时处理",
                "where": "私有云环境",
                "how": "基于流式日志审计"
            },
            "demand_validation": {
                "problem_nature": "painkiller",
                "willingness_to_pay_or_suffer": "监管罚单高达数千万元",
                "current_workarounds": ["手工审计日志"],
                "falsification_hypotheses": ["若自建开源方案可达到同等合规水准"],
                "validation_experiment": "对标客户试点比对"
            },
            "stakeholders": [],
            "goals": [{"id": "G-001", "statement": "零漏报违规流转", "success_metric": "100% 检出"}],
            "non_goals": [{"statement": "不做通用报表引擎", "reason": "保持领域专注"}],
            "explicit_requirements": [{"id": "REQ-001", "statement": "日志写入即落锁", "priority": "P0", "related_goal_id": "G-001", "source_quote": "必须支持 WORM"}],
            "implicit_requirements": [],
            "product_type": "cloud_platform",
            "open_questions": []
        }

        # Auto-detects Chinese from contents
        md_zh = self.renderer.render_requirement_analysis(zh_req)
        self.assertIn("## What（做什么）", md_zh)
        self.assertIn("## Why（为什么）", md_zh)
        self.assertIn("## Who（给谁用）", md_zh)
        self.assertIn("## 隐性需求挖掘", md_zh)
        self.assertIn("## 核心功能优先级", md_zh)

        # Explicit language parameter forces English if requested
        md_en_forced = self.renderer.render_requirement_analysis(zh_req, lang="en")
        self.assertIn("## What (Deliverables & Scope)", md_en_forced)
        self.assertIn("## Why (Business Motivation)", md_en_forced)

    def test_dynamic_language_matching_chinese_prd_and_invariants(self):
        zh_inv = {
            "product_name": "中文测试产品",
            "state_invariants": [{"invariant_id": "INV-STA-001", "target_entity": "交易流", "formal_rule": "单向推进", "severity": "CRITICAL", "violation_consequence": "状态逆流"}],
            "data_integrity_invariants": [{"invariant_id": "INV-DAT-001", "target_data_model": "账户账本", "conservation_rule": "借贷必平衡", "severity": "CRITICAL", "violation_consequence": "账实不符"}],
            "security_and_privacy_invariants": [{"invariant_id": "INV-SEC-001", "scope": "租户隔离", "isolation_rule": "硬性隔离", "severity": "CRITICAL", "violation_consequence": "跨租户泄露"}],
            "ux_and_safety_invariants": [{"invariant_id": "INV-UXS-001", "interaction_scope": "销毁操作", "safety_rule": "二次确认", "severity": "HIGH", "violation_consequence": "误删除"}]
        }
        md = self.renderer.render_product_invariants(zh_inv)
        self.assertIn("## 状态机不变量", md)
        self.assertIn("## 数据一致性与守恒不变量", md)
        self.assertIn("## 权限与租户隔离不变量", md)
        self.assertIn("## 交互体验安全不变量", md)

    def test_backward_compatibility_alias(self):
        self.assertIs(AuraklMarkdownRenderer, LumenMarkdownRenderer)


if __name__ == "__main__":
    unittest.main()
