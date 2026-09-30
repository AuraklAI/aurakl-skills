#!/usr/bin/env python3
"""
Unit tests for AuraklMarkdownRenderer (Template Conformance Engine).

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

from aurakl_renderer import AuraklMarkdownRenderer, render_all_artifacts

SKILL_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = SKILL_ROOT / "fixtures"


class TestAuraklMarkdownRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = AuraklMarkdownRenderer()
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
            "product_name": "\u6d4b\u8bd5\u5b89\u5168\u54e8\u5175",
            "five_w_one_h": {
                "what": "\u6784\u5efa\u4f01\u4e1a\u7ea7\u4e0d\u53ef\u7be1\u6539\u5ba1\u8ba1\u7cfb\u7edf",
                "why": "\u6ee1\u8db3\u6570\u636e\u4e3b\u6743\u76d1\u7ba1\u4e0e\u9632\u7be1\u6539\u786c\u6027\u8981\u6c42",
                "who": "\u5b89\u5168\u67b6\u6784\u5e08\u4e0e\u5408\u89c4\u5b98",
                "when": "\u5b9e\u65f6\u5904\u7406",
                "where": "\u79c1\u6709\u4e91\u73af\u5883",
                "how": "\u57fa\u4e8e\u6d41\u5f0f\u65e5\u5fd7\u5ba1\u8ba1"
            },
            "demand_validation": {
                "problem_nature": "painkiller",
                "willingness_to_pay_or_suffer": "\u76d1\u7ba1\u7f5a\u5355\u9ad8\u8fbe\u6570\u5343\u4e07\u5143",
                "current_workarounds": ["\u624b\u5de5\u5ba1\u8ba1\u65e5\u5fd7"],
                "falsification_hypotheses": ["\u82e5\u81ea\u5efa\u5f00\u6e90\u65b9\u6848\u53ef\u8fbe\u5230\u540c\u7b49\u5408\u89c4\u6c34\u51c6"],
                "validation_experiment": "\u5bf9\u6807\u5ba2\u6237\u8bd5\u70b9\u6bd4\u5bf9"
            },
            "stakeholders": [],
            "goals": [{"id": "G-001", "statement": "\u96f6\u6f0f\u62a5\u8fdd\u89c4\u6d41\u8f6c", "success_metric": "100% \u68c0\u51fa"}],
            "non_goals": [{"statement": "\u4e0d\u505a\u901a\u7528\u62a5\u8868\u5f15\u64ce", "reason": "\u4fdd\u6301\u9886\u57df\u4e13\u6ce8"}],
            "explicit_requirements": [{"id": "REQ-001", "statement": "\u65e5\u5fd7\u5199\u5165\u5373\u843d\u9501", "priority": "P0", "related_goal_id": "G-001", "source_quote": "\u5fc5\u987b\u652f\u6301 WORM"}],
            "implicit_requirements": [],
            "product_type": "cloud_platform",
            "open_questions": []
        }

        # Auto-detects Chinese from contents
        md_zh = self.renderer.render_requirement_analysis(zh_req)
        self.assertIn("## What\uff08\u505a\u4ec0\u4e48\uff09", md_zh)
        self.assertIn("## Why\uff08\u4e3a\u4ec0\u4e48\uff09", md_zh)
        self.assertIn("## Who\uff08\u7ed9\u8c01\u7528\uff09", md_zh)
        self.assertIn("## \u9690\u6027\u9700\u6c42\u6316\u6398", md_zh)
        self.assertIn("## \u6838\u5fc3\u529f\u80fd\u4f18\u5148\u7ea7", md_zh)

        # Explicit language parameter forces English if requested
        md_en_forced = self.renderer.render_requirement_analysis(zh_req, lang="en")
        self.assertIn("## What (Deliverables & Scope)", md_en_forced)
        self.assertIn("## Why (Business Motivation)", md_en_forced)

    def test_dynamic_language_matching_chinese_prd_and_invariants(self):
        zh_inv = {
            "product_name": "\u4e2d\u6587\u6d4b\u8bd5\u4ea7\u54c1",
            "state_invariants": [{"invariant_id": "INV-STA-001", "target_entity": "\u4ea4\u6613\u6d41", "formal_rule": "\u5355\u5411\u63a8\u8fdb", "severity": "CRITICAL", "violation_consequence": "\u72b6\u6001\u9006\u6d41"}],
            "data_integrity_invariants": [{"invariant_id": "INV-DAT-001", "target_data_model": "\u8d26\u6237\u8d26\u672c", "conservation_rule": "\u501f\u8d37\u5fc5\u5e73\u8861", "severity": "CRITICAL", "violation_consequence": "\u8d26\u5b9e\u4e0d\u7b26"}],
            "security_and_privacy_invariants": [{"invariant_id": "INV-SEC-001", "scope": "\u79df\u6237\u9694\u79bb", "isolation_rule": "\u786c\u6027\u9694\u79bb", "severity": "CRITICAL", "violation_consequence": "\u8de8\u79df\u6237\u6cc4\u9732"}],
            "ux_and_safety_invariants": [{"invariant_id": "INV-UXS-001", "interaction_scope": "\u9500\u6bc1\u64cd\u4f5c", "safety_rule": "\u4e8c\u6b21\u786e\u8ba4", "severity": "HIGH", "violation_consequence": "\u8bef\u5220\u9664"}]
        }
        md = self.renderer.render_product_invariants(zh_inv)
        self.assertIn("## \u72b6\u6001\u673a\u4e0d\u53d8\u91cf", md)
        self.assertIn("## \u6570\u636e\u4e00\u81f4\u6027\u4e0e\u5b88\u6052\u4e0d\u53d8\u91cf", md)
        self.assertIn("## \u6743\u9650\u4e0e\u79df\u6237\u9694\u79bb\u4e0d\u53d8\u91cf", md)
        self.assertIn("## \u4ea4\u4e92\u4f53\u9a8c\u5b89\u5168\u4e0d\u53d8\u91cf", md)

    def test_renderer_initialization(self):
        self.assertIsInstance(self.renderer, AuraklMarkdownRenderer)


if __name__ == "__main__":
    unittest.main()
