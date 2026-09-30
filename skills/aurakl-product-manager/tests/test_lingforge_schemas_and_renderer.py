#!/usr/bin/env python3
"""
Unit tests for Lingforge-compatible User Story and PRD JSON Schemas and Renderers.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

# Setup path
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from aurakl_validator import AuraklValidator
from aurakl_renderer import AuraklMarkdownRenderer


class TestLingforgeSchemasAndRenderer(unittest.TestCase):

    def setUp(self):
        self.validator = AuraklValidator()
        self.renderer = AuraklMarkdownRenderer()

    def test_schemas_resolvable(self):
        resolved_story = self.validator.resolve_schema("user-story-lingforge.v1.json")
        self.assertIsNotNone(resolved_story)
        self.assertEqual(resolved_story[0], "user-story-lingforge.v1.json")

        resolved_prd = self.validator.resolve_schema("prd-lingforge.v1.json")
        self.assertIsNotNone(resolved_prd)
        self.assertEqual(resolved_prd[0], "prd-lingforge.v1.json")

    def test_lingforge_user_story_validation_and_rendering(self):
        sample_story_data = {
            "metadata": {
                "id": "story-demo-v1",
                "type": "story",
                "version": "1.0",
                "title": "Demo \u7528\u6237\u6545\u4e8b",
                "status": "draft",
                "author": "product@example.com",
                "created": "2026-03-01",
                "updated": "2026-03-12",
                "implements": ["epic-demo-platform"],
                "tags": ["mvp", "demo"],
                "priority": "P0"
            },
            "overview": "\u8fd9\u662f\u6d4b\u8bd5\u7528\u6237\u6545\u4e8b\u96c6\u7684\u4e1a\u52a1\u76ee\u6807\u6982\u8ff0\u8bf4\u660e\u3002",
            "epics": [
                {
                    "id": "EPIC-DEMO-001",
                    "name": "\u6838\u5fc3\u8ba4\u8bc1\u4e0e\u6388\u6743",
                    "goal": "\u5b8c\u6210\u7edf\u4e00\u8eab\u4efd\u9274\u6743\u4e0e\u5b89\u5168\u95e8\u7981",
                    "business_value": "\u964d\u4f4e\u4f01\u4e1a\u8d8a\u6743\u98ce\u9669\u5e76\u63d0\u4f9b\u5ba1\u8ba1\u6eaf\u6e90",
                    "contained_stories": ["USR-DEMO-001"],
                    "priority": "Must",
                    "estimated_effort": "2 \u4eba\u5468"
                }
            ],
            "stories": [
                {
                    "id": "USR-DEMO-001",
                    "title": "\u7528\u6237\u591a\u56e0\u7d20\u8eab\u4efd\u8ba4\u8bc1",
                    "implements_epic": "EPIC-DEMO-001",
                    "depends_on": [],
                    "as_a": "\u4f01\u4e1a\u5b89\u5168\u7ba1\u7406\u5458",
                    "i_want": "\u542f\u7528\u591a\u56e0\u7d20\u52a8\u6001\u53e3\u4ee4\u8ba4\u8bc1",
                    "so_that": "\u9632\u6b62\u5bc6\u7801\u6cc4\u6f0f\u5bfc\u81f4\u7684\u975e\u6388\u6743\u64cd\u4f5c",
                    "priority": "Must",
                    "estimated_effort": "3 \u4eba\u5929",
                    "sprint": "Sprint 1",
                    "background": "\u4f20\u7edf\u5bc6\u7801\u65b9\u5f0f\u5bb9\u6613\u906d\u53d7\u5b57\u5178\u653b\u51fb\u4e0e\u9493\u9c7c\u6f0f\u6d1e\u3002",
                    "acceptance_criteria": [
                        {
                            "given": "\u7528\u6237\u8f93\u5165\u6b63\u786e\u7684\u7528\u6237\u540d\u4e0e\u5bc6\u7801",
                            "when": "\u89e6\u53d1\u4e8c\u6b21\u77ed\u4fe1/TOTP \u52a8\u6001\u53e3\u4ee4\u6821\u9a8c",
                            "then": "\u9a8c\u8bc1\u6210\u529f\u7b7e\u53d1\u9ad8\u5b89\u5168\u7ea7\u522b JWT Token"
                        }
                    ],
                    "dependencies": ["\u65e0"],
                    "ui_ux_notes": ["\u5728\u767b\u5f55\u6846\u4e0b\u65b9\u52a8\u6001\u547c\u51fa 6 \u4f4d\u9a8c\u8bc1\u7801\u8f93\u5165\u5361\u7247"],
                    "technical_constraints": ["\u9a8c\u8bc1\u7801\u6709\u6548\u65f6\u95f4\u4e3a 60 \u79d2\uff0c\u91cd\u8bd5 3 \u6b21\u9501\u5b9a"],
                    "success_metrics": "\u767b\u5f55\u6210\u529f\u7387 > 99.5%\uff0c\u5f02\u5e38\u62e6\u622a\u7387 100%",
                    "related_prd": "prd-demo-v1"
                }
            ],
            "personas": [
                {
                    "id": "PERSONA-001",
                    "name": "\u5f20\u5de5",
                    "description": "\u5b89\u5168\u5408\u89c4\u4e13\u5bb6",
                    "demographics": {
                        "age_range": "30-40",
                        "occupation": "\u5b89\u5168\u67b6\u6784\u5e08",
                        "tech_level": "\u4e13\u5bb6",
                        "usage_context": "\u4f01\u4e1a\u5b89\u5168\u7ba1\u63a7\u53f0"
                    },
                    "pain_points": ["\u65e5\u5fd7\u683c\u5f0f\u4e0d\u4e00\u81f4\uff0c\u6eaf\u6e90\u53d6\u8bc1\u8017\u65f6\u957f"],
                    "goals_and_needs": {
                        "goals": ["\u4fdd\u969c\u751f\u4ea7\u73af\u5883\u6838\u5fc3\u6570\u636e\u5e93\u96f6\u8fdd\u89c4\u8bbf\u95ee"],
                        "needs": ["\u5168\u94fe\u8def\u64cd\u4f5c\u5ba1\u8ba1\u8bc1\u636e\u94fe\u4e0e\u81ea\u52a8\u5316\u62e6\u622a"]
                    },
                    "related_stories": ["USR-DEMO-001"]
                }
            ],
            "journeys": [
                {
                    "id": "JOURNEY-001",
                    "name": "\u9ad8\u5371\u64cd\u4f5c\u5ba1\u6279\u4e0e\u6267\u884c\u65c5\u7a0b",
                    "scenario": "\u7ba1\u7406\u5458\u4e0b\u53d1\u6279\u91cf\u6570\u636e\u8ba2\u6b63\u4efb\u52a1",
                    "involved_personas": ["PERSONA-001"],
                    "steps": [
                        {
                            "user_action": "\u8f93\u5165\u7ba1\u7406\u5458\u8d26\u53f7\u5bc6\u7801\u5e76\u8f93\u5165 TOTP \u53e3\u4ee4",
                            "system_response": "\u6821\u9a8c\u6210\u529f\u8fdb\u5165\u4e3b\u63a7\u53f0",
                            "user_feeling": "\u987a\u7545\u4e14\u5b89\u5168",
                            "related_story": "USR-DEMO-001"
                        }
                    ],
                    "current_pain_points": ["\u73b0\u6709\u6d41\u7a0b\u4eba\u5de5\u5ba1\u6279\u9700\u8981\u7b49 2 \u5929"],
                    "improvements": ["\u5f15\u5165\u52a8\u6001\u98ce\u63a7\u89c4\u5219\u5f15\u64ce\u4e0e\u5206\u949f\u7ea7\u5ba1\u6279\u901a\u9053"],
                    "involved_stories": ["USR-DEMO-001"]
                }
            ],
            "priority_matrix": {
                "must_have": [
                    {
                        "story_id": "USR-DEMO-001",
                        "title": "\u7528\u6237\u591a\u56e0\u7d20\u8eab\u4efd\u8ba4\u8bc1",
                        "business_value": "\u9ad8",
                        "tech_complexity": "\u4e2d",
                        "dependencies": "\u65e0",
                        "estimated_effort": "3 \u4eba\u5929"
                    }
                ],
                "should_have": [],
                "could_have": []
            },
            "upstream_dependencies": ["\u65e0"],
            "downstream_deliverables": {
                "prd": "prd-demo-v1",
                "acceptance_criteria": "ac-demo-v1"
            },
            "version_history": [
                {
                    "version": "1.0",
                    "date": "2026-03-01",
                    "changes": "\u521d\u59cb\u521b\u5efa",
                    "author": "product@example.com"
                }
            ]
        }

        # 1. Validate JSON
        verdict = self.validator.validate_artifact("user-story-lingforge", sample_story_data)
        self.assertTrue(verdict.passed, f"Validation failed: {[i.message for i in verdict.issues]}")

        # 2. Render Markdown
        md = self.renderer.render_user_stories(sample_story_data)
        self.assertIn("---", md)
        self.assertIn("id: story-demo-v1", md)
        self.assertIn("<!-- block-id: EPIC-DEMO-001 -->", md)
        self.assertIn("<!-- block-id: USR-DEMO-001 -->", md)
        self.assertIn("<!-- implements: EPIC-DEMO-001 -->", md)
        self.assertIn("<!-- /block -->", md)
        self.assertIn("- [ ] **Given** \u7528\u6237\u8f93\u5165\u6b63\u786e\u7684\u7528\u6237\u540d\u4e0e\u5bc6\u7801", md)
        self.assertIn("## \u4f18\u5148\u7ea7\u77e9\u9635 {#priority-matrix}", md)

    def test_lingforge_prd_validation_and_rendering(self):
        sample_prd_data = {
            "metadata": {
                "id": "prd-demo-v1",
                "type": "prd",
                "version": "1.0",
                "title": "Demo \u4ea7\u54c1\u9700\u6c42\u6587\u6863",
                "status": "draft",
                "author": "product@example.com",
                "created": "2026-03-01",
                "updated": "2026-03-12",
                "depends_on": ["design-security-framework"],
                "implements": ["story-demo-v1"],
                "tags": ["mvp", "demo"],
                "priority": "P0"
            },
            "overview": {
                "background": "\u89e3\u51b3\u8de8\u7cfb\u7edf\u6570\u636e\u5b64\u5c9b\u4e0e\u4f20\u7edf\u811a\u672c\u6539\u5199\u6570\u636e\u5e93\u7f3a\u4e4f\u4e8b\u52a1\u4fdd\u62a4\u7684\u95ee\u9898\u3002",
                "objectives": [
                    {
                        "metric_name": "\u53cc\u5411\u540c\u6b65\u6210\u529f\u7387",
                        "baseline": "0%",
                        "target": "> 99.9%",
                        "timeframe": "\u4e0a\u7ebf\u540e 2 \u5468"
                    }
                ],
                "scope": {
                    "in_scope": ["\u5b9e\u65f6\u6570\u636e\u6d41\u63a5\u5165", "\u5206\u5e03\u5f0f\u5199\u4e8b\u52a1\u63a7\u5236"],
                    "out_of_scope": [
                        {
                            "item": "\u5168\u573a\u666f\u4f4e\u4ee3\u7801\u62d6\u62fd\u6784\u5efa\u5668",
                            "reason": "\u9996\u671f\u805a\u7126\u6838\u5fc3\u7a33\u5b9a\u6027\u4e0e\u4e8b\u52a1\u4e00\u81f4\u6027\u5e95\u5ea7"
                        }
                    ]
                }
            },
            "features": [
                {
                    "block_id": "REQ-F001",
                    "implements_story_id": "USR-DEMO-001",
                    "depends_on": [],
                    "name": "\u591a\u6e90 CDC \u6570\u636e\u63a5\u5165\u6d41\u7f16\u6392",
                    "user_story": {
                        "role": "\u67b6\u6784\u5e08",
                        "target": "\u63a5\u5165\u7269\u7406\u5e93\u53d8\u66f4\u6d41",
                        "benefit": "\u4fdd\u6301\u4e1a\u52a1\u8bed\u4e49\u6700\u65b0\u72b6\u6001"
                    },
                    "priority": "Must Have",
                    "story_id": "USR-DEMO-001",
                    "feature_id": "F-001-001",
                    "preconditions": {
                        "dependencies": ["\u5e95\u5c42\u6570\u636e\u5e93\u5f00\u542f\u52a8\u6001 binlog"],
                        "state_prerequisites": ["Flink \u96c6\u7fa4\u7f51\u7edc\u8054\u901a"],
                        "permissions": ["\u7269\u7406\u5e93\u8bfb\u5199\u6743\u9650"],
                        "usage_scenario": "\u6570\u636e\u6e90\u63a5\u5165\u914d\u7f6e\u9875\u9762"
                    },
                    "description": "\u7cfb\u7edf\u76d1\u542c\u7269\u7406\u5e93\u53d8\u66f4\u6d41\u5e76\u5728 500ms \u5185\u540c\u6b65\u66f4\u65b0\u81f3\u672c\u4f53\u6a21\u578b\u3002",
                    "main_flow": [
                        {
                            "step_num": 1,
                            "user_action": "\u7528\u6237\u8f93\u5165\u6570\u636e\u6e90\u8fde\u63a5\u4e32\u5e76\u70b9\u51fb\u6d4b\u8bd5\u8fde\u63a5",
                            "system_response": "\u7cfb\u7edf\u5728 3 \u79d2\u5185\u8fd4\u56de\u7f51\u7edc\u4e0e\u6743\u9650\u63a2\u6d3b\u6b63\u5e38"
                        },
                        {
                            "step_num": 2,
                            "user_action": "\u7528\u6237\u9009\u62e9\u76ee\u6807\u540c\u6b65\u8868\u5e76\u70b9\u51fb\u542f\u52a8\u6d41\u4efb\u52a1",
                            "system_response": "\u7cfb\u7edf\u521d\u59cb\u5316 Flink \u76d1\u542c\u5668\u5e76\u5efa\u7acb\u589e\u91cf\u6d41\u901a\u9053"
                        }
                    ],
                    "exception_handling": [
                        {
                            "scenario": "\u7f51\u7edc\u4e2d\u65ad\u6216\u6570\u636e\u5e93\u8d85\u65f6",
                            "handling": "\u8bb0\u5f55 Savepoint \u5e76\u8fdb\u884c\u6307\u6570\u9000\u907f\u91cd\u8bd5 3 \u6b21"
                        }
                    ],
                    "inputs": [
                        {
                            "field": "connectionUrl",
                            "type": "string",
                            "required": True,
                            "description": "\u6570\u636e\u5e93\u8fde\u63a5 JDBC URL",
                            "constraints": "\u683c\u5f0f\u4e3a jdbc:mysql://...",
                            "example": "jdbc:mysql://10.0.0.1:3306/db"
                        }
                    ],
                    "outputs": [
                        {
                            "field": "streamId",
                            "type": "string",
                            "description": "\u5206\u914d\u7684\u6d41\u4efb\u52a1\u552f\u4e00\u6807\u8bc6",
                            "example": "STR-001"
                        }
                    ],
                    "error_handling": [
                        {
                            "code": "ERR_CONN_TIMEOUT",
                            "scenario": "\u6570\u636e\u5e93\u63e1\u624b\u8d85\u65f6",
                            "user_message": "\u65e0\u6cd5\u8fde\u63a5\u81f3\u6307\u5b9a\u6570\u636e\u5e93\uff0c\u8bf7\u68c0\u67e5\u9632\u706b\u5899",
                            "suggestion": "\u68c0\u67e5\u76ee\u6807\u7aef\u53e3\u662f\u5426\u653e\u901a\u5e76\u6838\u5bf9\u8d26\u6237\u5bc6\u7801"
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "ac_id": "AC-001",
                            "given": "\u6570\u636e\u5e93\u51ed\u8bc1\u6b63\u786e\u4e14\u7f51\u7edc\u8054\u901a",
                            "when": "\u70b9\u51fb\u542f\u52a8\u540c\u6b65",
                            "then": "\u6d41\u901a\u9053\u72b6\u6001\u53d8\u4e3a RUNNING\uff0c\u5ef6\u8fdf\u4f4e\u4e8e 500ms"
                        }
                    ],
                    "boundary_conditions": ["\u5355\u8868\u6700\u9ad8\u652f\u6301 10000 QPS \u5199\u5165\u541e\u5410"],
                    "business_rules": ["\u540c\u4e00\u5b9e\u4f53\u7684\u6570\u636e\u53d8\u66f4\u5fc5\u987b\u4fdd\u6301\u65f6\u5e8f\u4e25\u683c\u9012\u589e"],
                    "test_requirements": {
                        "normal": True,
                        "boundary": True,
                        "error": True,
                        "performance": True,
                        "security": True
                    },
                    "related_design": ["design-cdc-sync-engine"]
                }
            ],
            "non_functional_requirements": {
                "performance": [
                    {
                        "dimension": "\u7aef\u5230\u7aef\u540c\u6b65\u5ef6\u8fdf",
                        "requirement": "\u6d41\u6279\u53d8\u66f4\u5b9e\u65f6\u900f\u4f20",
                        "metric": "< 500ms (P99)"
                    }
                ],
                "security": [
                    {
                        "dimension": "\u4f20\u8f93\u52a0\u5bc6",
                        "requirement": "\u6570\u636e\u6d41\u9632\u7a83\u542c",
                        "measure": "\u5168\u94fe\u8def\u5f3a\u5236 TLS 1.3"
                    }
                ],
                "compatibility": [
                    {
                        "platform": "\u6570\u636e\u5e93\u5f15\u64ce",
                        "supported_versions": "MySQL 5.7+, PostgreSQL 12+, Oracle 19c+"
                    }
                ]
            },
            "dependencies_and_constraints": {
                "dependencies": [
                    {
                        "target": "Flink \u96c6\u7fa4 1.18+",
                        "description": "\u5206\u5e03\u5f0f\u6d41\u5f0f\u8ba1\u7b97\u5e95\u5ea7"
                    }
                ],
                "constraints": {
                    "mvp_excludes": ["\u56fe\u6570\u636e\u539f\u751f\u8ba1\u7b97\u5f15\u64ce\u96c6\u6210"],
                    "technical_constraints": ["\u5355\u8282\u70b9 JVM \u5806\u5185\u5b58\u4e0d\u5c11\u4e8e 8GB"]
                }
            },
            "risks_and_assumptions": {
                "risks": [
                    {
                        "category": "\u6280\u672f\u7a33\u5b9a\u6027",
                        "description": "\u6e90\u5e93\u5927\u4e8b\u52a1 binlog \u53ef\u80fd\u5f15\u53d1\u77ac\u65f6\u79ef\u538b",
                        "likelihood": "\u4e2d",
                        "impact": "\u4e2d",
                        "mitigation": "\u8bbe\u7f6e\u80cc\u538b\u6d41\u63a7\u9608\u503c\u5e76\u5728\u8d85\u8fc7\u544a\u8b66\u6c34\u4f4d\u65f6\u81ea\u52a8\u6269\u5bb9\u4efb\u52a1\u69fd\u4f4d"
                    }
                ],
                "assumptions": [
                    {
                        "assumption": "\u76ee\u6807\u7269\u7406\u5e93\u652f\u6301\u884c\u7ea7\u53d8\u66f4\u65e5\u5fd7\u89e3\u6790",
                        "validation_method": "\u8fde\u63a5\u9884\u68c0\u81ea\u52a8\u626b\u63cf binlog_format \u914d\u7f6e",
                        "fallback": "\u5982\u4ec5\u652f\u6301\u8bed\u53e5\u7ea7\u590d\u5236\u5219\u9000\u56de\u81f3\u5b9a\u65f6\u5168\u91cf\u8f6e\u8be2\u6a21\u5f0f"
                    }
                ]
            },
            "version_history": [
                {
                    "version": "1.0",
                    "date": "2026-03-01",
                    "changes": "\u521d\u59cb\u521b\u5efa",
                    "author": "product@example.com"
                }
            ]
        }

        # 1. Validate JSON
        verdict = self.validator.validate_artifact("prd-lingforge", sample_prd_data)
        self.assertTrue(verdict.passed, f"Validation failed: {[i.message for i in verdict.issues]}")

        # 2. Render Markdown
        md = self.renderer.render_prd(sample_prd_data)
        self.assertIn("---", md)
        self.assertIn("id: prd-demo-v1", md)
        self.assertIn("<!-- block-id: REQ-F001 -->", md)
        self.assertIn("<!-- implements: USR-DEMO-001 -->", md)
        self.assertIn("<!-- /block -->", md)
        self.assertIn("| \u5b57\u6bb5 | \u7c7b\u578b | \u5fc5\u9700 | \u8bf4\u660e |", md)
        self.assertIn("| \u9519\u8bef\u7801 | \u573a\u666f | \u7528\u6237\u63d0\u793a | \u5904\u7406\u5efa\u8bae |", md)
        self.assertIn("- AC-001: **Given** \u6570\u636e\u5e93\u51ed\u8bc1\u6b63\u786e\u4e14\u7f51\u7edc\u8054\u901a", md)
        self.assertIn("<!-- block-id: REQ-NF001 -->", md)
        self.assertIn("## \u98ce\u9669\u4e0e\u5047\u8bbe {#risks-assumptions}", md)


if __name__ == "__main__":
    unittest.main()
