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

from aurakl_validator import AuraklValidator, LumenValidator
from aurakl_renderer import AuraklMarkdownRenderer, LumenMarkdownRenderer


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
                "title": "Demo 用户故事",
                "status": "draft",
                "author": "product@example.com",
                "created": "2026-03-01",
                "updated": "2026-03-12",
                "implements": ["epic-demo-platform"],
                "tags": ["mvp", "demo"],
                "priority": "P0"
            },
            "overview": "这是测试用户故事集的业务目标概述说明。",
            "epics": [
                {
                    "id": "EPIC-DEMO-001",
                    "name": "核心认证与授权",
                    "goal": "完成统一身份鉴权与安全门禁",
                    "business_value": "降低企业越权风险并提供审计溯源",
                    "contained_stories": ["USR-DEMO-001"],
                    "priority": "Must",
                    "estimated_effort": "2 人周"
                }
            ],
            "stories": [
                {
                    "id": "USR-DEMO-001",
                    "title": "用户多因素身份认证",
                    "implements_epic": "EPIC-DEMO-001",
                    "depends_on": [],
                    "as_a": "企业安全管理员",
                    "i_want": "启用多因素动态口令认证",
                    "so_that": "防止密码泄漏导致的非授权操作",
                    "priority": "Must",
                    "estimated_effort": "3 人天",
                    "sprint": "Sprint 1",
                    "background": "传统密码方式容易遭受字典攻击与钓鱼漏洞。",
                    "acceptance_criteria": [
                        {
                            "given": "用户输入正确的用户名与密码",
                            "when": "触发二次短信/TOTP 动态口令校验",
                            "then": "验证成功签发高安全级别 JWT Token"
                        }
                    ],
                    "dependencies": ["无"],
                    "ui_ux_notes": ["在登录框下方动态呼出 6 位验证码输入卡片"],
                    "technical_constraints": ["验证码有效时间为 60 秒，重试 3 次锁定"],
                    "success_metrics": "登录成功率 > 99.5%，异常拦截率 100%",
                    "related_prd": "prd-demo-v1"
                }
            ],
            "personas": [
                {
                    "id": "PERSONA-001",
                    "name": "张工",
                    "description": "安全合规专家",
                    "demographics": {
                        "age_range": "30-40",
                        "occupation": "安全架构师",
                        "tech_level": "专家",
                        "usage_context": "企业安全管控台"
                    },
                    "pain_points": ["日志格式不一致，溯源取证耗时长"],
                    "goals_and_needs": {
                        "goals": ["保障生产环境核心数据库零违规访问"],
                        "needs": ["全链路操作审计证据链与自动化拦截"]
                    },
                    "related_stories": ["USR-DEMO-001"]
                }
            ],
            "journeys": [
                {
                    "id": "JOURNEY-001",
                    "name": "高危操作审批与执行旅程",
                    "scenario": "管理员下发批量数据订正任务",
                    "involved_personas": ["PERSONA-001"],
                    "steps": [
                        {
                            "user_action": "输入管理员账号密码并输入 TOTP 口令",
                            "system_response": "校验成功进入主控台",
                            "user_feeling": "顺畅且安全",
                            "related_story": "USR-DEMO-001"
                        }
                    ],
                    "current_pain_points": ["现有流程人工审批需要等 2 天"],
                    "improvements": ["引入动态风控规则引擎与分钟级审批通道"],
                    "involved_stories": ["USR-DEMO-001"]
                }
            ],
            "priority_matrix": {
                "must_have": [
                    {
                        "story_id": "USR-DEMO-001",
                        "title": "用户多因素身份认证",
                        "business_value": "高",
                        "tech_complexity": "中",
                        "dependencies": "无",
                        "estimated_effort": "3 人天"
                    }
                ],
                "should_have": [],
                "could_have": []
            },
            "upstream_dependencies": ["无"],
            "downstream_deliverables": {
                "prd": "prd-demo-v1",
                "acceptance_criteria": "ac-demo-v1"
            },
            "version_history": [
                {
                    "version": "1.0",
                    "date": "2026-03-01",
                    "changes": "初始创建",
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
        self.assertIn("- [ ] **Given** 用户输入正确的用户名与密码", md)
        self.assertIn("## 优先级矩阵 {#priority-matrix}", md)

    def test_lingforge_prd_validation_and_rendering(self):
        sample_prd_data = {
            "metadata": {
                "id": "prd-demo-v1",
                "type": "prd",
                "version": "1.0",
                "title": "Demo 产品需求文档",
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
                "background": "解决跨系统数据孤岛与传统脚本改写数据库缺乏事务保护的问题。",
                "objectives": [
                    {
                        "metric_name": "双向同步成功率",
                        "baseline": "0%",
                        "target": "> 99.9%",
                        "timeframe": "上线后 2 周"
                    }
                ],
                "scope": {
                    "in_scope": ["实时数据流接入", "分布式写事务控制"],
                    "out_of_scope": [
                        {
                            "item": "全场景低代码拖拽构建器",
                            "reason": "首期聚焦核心稳定性与事务一致性底座"
                        }
                    ]
                }
            },
            "features": [
                {
                    "block_id": "REQ-F001",
                    "implements_story_id": "USR-DEMO-001",
                    "depends_on": [],
                    "name": "多源 CDC 数据接入流编排",
                    "user_story": {
                        "role": "架构师",
                        "target": "接入物理库变更流",
                        "benefit": "保持业务语义最新状态"
                    },
                    "priority": "Must Have",
                    "story_id": "USR-DEMO-001",
                    "feature_id": "F-001-001",
                    "preconditions": {
                        "dependencies": ["底层数据库开启动态 binlog"],
                        "state_prerequisites": ["Flink 集群网络联通"],
                        "permissions": ["物理库读写权限"],
                        "usage_scenario": "数据源接入配置页面"
                    },
                    "description": "系统监听物理库变更流并在 500ms 内同步更新至本体模型。",
                    "main_flow": [
                        {
                            "step_num": 1,
                            "user_action": "用户输入数据源连接串并点击测试连接",
                            "system_response": "系统在 3 秒内返回网络与权限探活正常"
                        },
                        {
                            "step_num": 2,
                            "user_action": "用户选择目标同步表并点击启动流任务",
                            "system_response": "系统初始化 Flink 监听器并建立增量流通道"
                        }
                    ],
                    "exception_handling": [
                        {
                            "scenario": "网络中断或数据库超时",
                            "handling": "记录 Savepoint 并进行指数退避重试 3 次"
                        }
                    ],
                    "inputs": [
                        {
                            "field": "connectionUrl",
                            "type": "string",
                            "required": True,
                            "description": "数据库连接 JDBC URL",
                            "constraints": "格式为 jdbc:mysql://...",
                            "example": "jdbc:mysql://10.0.0.1:3306/db"
                        }
                    ],
                    "outputs": [
                        {
                            "field": "streamId",
                            "type": "string",
                            "description": "分配的流任务唯一标识",
                            "example": "STR-001"
                        }
                    ],
                    "error_handling": [
                        {
                            "code": "ERR_CONN_TIMEOUT",
                            "scenario": "数据库握手超时",
                            "user_message": "无法连接至指定数据库，请检查防火墙",
                            "suggestion": "检查目标端口是否放通并核对账户密码"
                        }
                    ],
                    "acceptance_criteria": [
                        {
                            "ac_id": "AC-001",
                            "given": "数据库凭证正确且网络联通",
                            "when": "点击启动同步",
                            "then": "流通道状态变为 RUNNING，延迟低于 500ms"
                        }
                    ],
                    "boundary_conditions": ["单表最高支持 10000 QPS 写入吞吐"],
                    "business_rules": ["同一实体的数据变更必须保持时序严格递增"],
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
                        "dimension": "端到端同步延迟",
                        "requirement": "流批变更实时透传",
                        "metric": "< 500ms (P99)"
                    }
                ],
                "security": [
                    {
                        "dimension": "传输加密",
                        "requirement": "数据流防窃听",
                        "measure": "全链路强制 TLS 1.3"
                    }
                ],
                "compatibility": [
                    {
                        "platform": "数据库引擎",
                        "supported_versions": "MySQL 5.7+, PostgreSQL 12+, Oracle 19c+"
                    }
                ]
            },
            "dependencies_and_constraints": {
                "dependencies": [
                    {
                        "target": "Flink 集群 1.18+",
                        "description": "分布式流式计算底座"
                    }
                ],
                "constraints": {
                    "mvp_excludes": ["图数据原生计算引擎集成"],
                    "technical_constraints": ["单节点 JVM 堆内存不少于 8GB"]
                }
            },
            "risks_and_assumptions": {
                "risks": [
                    {
                        "category": "技术稳定性",
                        "description": "源库大事务 binlog 可能引发瞬时积压",
                        "likelihood": "中",
                        "impact": "中",
                        "mitigation": "设置背压流控阈值并在超过告警水位时自动扩容任务槽位"
                    }
                ],
                "assumptions": [
                    {
                        "assumption": "目标物理库支持行级变更日志解析",
                        "validation_method": "连接预检自动扫描 binlog_format 配置",
                        "fallback": "如仅支持语句级复制则退回至定时全量轮询模式"
                    }
                ]
            },
            "version_history": [
                {
                    "version": "1.0",
                    "date": "2026-03-01",
                    "changes": "初始创建",
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
        self.assertIn("| 字段 | 类型 | 必需 | 说明 |", md)
        self.assertIn("| 错误码 | 场景 | 用户提示 | 处理建议 |", md)
        self.assertIn("- AC-001: **Given** 数据库凭证正确且网络联通", md)
        self.assertIn("<!-- block-id: REQ-NF001 -->", md)
        self.assertIn("## 风险与假设 {#risks-assumptions}", md)


if __name__ == "__main__":
    unittest.main()
