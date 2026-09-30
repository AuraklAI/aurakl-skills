#!/usr/bin/env python3
"""
Aurakl 5W1H Requirement Elicitation & Clarification Engine

Enforces Aurakl's Product Management SOP 01 requirement analysis standards:
1. Prevents Agent from inventing certainty from ambiguous briefs.
2. Extracts and tracks 5W1H, Demand Validation, Goals, Non-Goals, and Implicit Requirements.
3. Computes slot completeness score and generates structured clarifying questions with options.
4. Dynamically mirrors the user's input language (English / Chinese).
5. Exports verified slots as a compliant requirement-analysis record.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

FORBIDDEN_NON_GOAL_PHRASES_ZH = [
    "正面陈述",
    "不是一句「不支持",
    "而不是「不支持",
    "改写成「系统仅",
    "系统仅支持",
    "仅支持",
]

FORBIDDEN_NON_GOAL_PHRASES_EN = [
    "positive statement",
    "only supports",
    "just supports",
    "exclusively supports",
    "is not unsupported",
    "rephrase to",
]

FORBIDDEN_NON_GOAL_PHRASES = FORBIDDEN_NON_GOAL_PHRASES_ZH + FORBIDDEN_NON_GOAL_PHRASES_EN

PLACEHOLDER_REGEX = re.compile(
    r"\b(TBD|TODO|UNVERIFIED|PENDING|TO_BE_CONFIRMED|待确认|待定|暂无|后续补充|待商榷)\b", re.IGNORECASE
)

ZH_CHAR_REGEX = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class SlotItem:
    key: str
    label: str
    description: str
    min_length: int = 5
    required: bool = True


REQUIRED_SLOTS_EN = [
    SlotItem("five_w_one_h.who", "Who (Target Audience & Beneficiaries)", "Target user personas, roles, and core beneficiaries", 10),
    SlotItem("five_w_one_h.why", "Why (Core Motivation & Root Pain Point)", "Underlying business blockers, loss prevention, or compliance mandates", 15),
    SlotItem("five_w_one_h.what", "What (Core Value & Capabilities)", "Deliverable value proposition, capability scope, and business entities", 10),
    SlotItem("five_w_one_h.when", "When (Trigger & Lifecycle)", "Trigger events, business conditions, and operational frequency", 5),
    SlotItem("five_w_one_h.where", "Where (Runtime Environment & Boundary)", "Target client applications, cloud hosts, platforms, or execution contexts", 5),
    SlotItem("five_w_one_h.how", "How (Workflow & Interaction Mechanism)", "Critical user journeys, system interactions, and goal-achievement flow", 15),
    SlotItem("demand_validation.problem_nature", "Problem Nature (Painkiller/Vitamin/Candy)", "Whether this is an essential painkiller, vitamin, or nice-to-have candy", 4),
    SlotItem("demand_validation.current_workarounds", "Current Workarounds", "How users solve or tolerate this problem today without the system", 8),
    SlotItem("demand_validation.willingness_to_pay_or_suffer", "Willingness to Pay or Suffer", "Budget allocation, migration friction tolerance, or switching cost", 8),
    SlotItem("demand_validation.falsification_hypotheses", "Falsification Hypotheses", "Key premises that would invalidate this as a genuine requirement if proven false", 10),
    SlotItem("demand_validation.validation_experiment", "Validation Experiment", "Lowest-cost data or behavioral experiment to test hypotheses", 10),
    SlotItem("goals", "Goals", "Measurable business objectives (at least 1 explicit goal)", 10),
    SlotItem("non_goals", "Non-Goals", "Explicitly excluded scope (at least 2 items, never rephrased positive limits)", 10),
    SlotItem("implicit_requirements", "Implicit Requirements", "Discovered non-functional constraints across security, performance, compliance (>= 3 items)", 10),
]

REQUIRED_SLOTS_ZH = [
    SlotItem("five_w_one_h.who", "Who (目标客群与受益人)", "系统的目标角色、用户画像及核心受益人", 10),
    SlotItem("five_w_one_h.why", "Why (核心动机与痛点根因)", "触发该需求的深层痛点、业务阻碍或合规动机", 15),
    SlotItem("five_w_one_h.what", "What (核心价值边界与功能)", "系统交付的核心价值、能力范围与业务实体", 10),
    SlotItem("five_w_one_h.when", "When (触发时机与生命周期)", "在什么时间、触发条件或业务频次下使用", 5),
    SlotItem("five_w_one_h.where", "Where (运行环境与系统边界)", "在哪些客户端、云环境、宿主平台或上下文中运行", 5),
    SlotItem("five_w_one_h.how", "How (达成路径与交互方式)", "关键业务路径、用户交互流程与达成目标的机制", 15),
    SlotItem("demand_validation.problem_nature", "问题属性 (Painkiller/Vitamin/Candy)", "属于刚需止痛药(painkiller)、锦上添花维他命还是糖果", 4),
    SlotItem("demand_validation.current_workarounds", "现有替代妥协方案", "用户在没有本系统前如何解决该问题（纯手工/容忍/替代品）", 8),
    SlotItem("demand_validation.willingness_to_pay_or_suffer", "支付意愿与忍受成本", "用户的采购预算、切换代价或痛点忍受阈值", 8),
    SlotItem("demand_validation.falsification_hypotheses", "证伪假设", "哪些前提一旦被推翻，该需求即证明为伪需求", 10),
    SlotItem("demand_validation.validation_experiment", "验证实验", "如何以最低成本通过数据或实验验证上述假设", 10),
    SlotItem("goals", "目标 Goals", "期望达成的业务目标列表（至少 1 条明确目标）", 10),
    SlotItem("non_goals", "非目标 Non-Goals", "明确排除的范围（必须 >= 2 条，且严禁正面改写）", 10),
    SlotItem("implicit_requirements", "隐性需求", "从安全、性能、合规、容灾等维度挖掘的隐性约束（>= 3 条）", 10),
]

REQUIRED_SLOTS = REQUIRED_SLOTS_EN


@dataclass
class ClarifyingQuestion:
    slot_key: str
    question: str
    why_needed: str
    options: List[str] = field(default_factory=list)


@dataclass
class AssessmentReport:
    completeness_score: float  # 0.0 ~ 100.0
    can_proceed: bool
    fulfilled_slots: List[str]
    missing_slots: List[str]
    slot_diagnostics: Dict[str, str]
    questions: List[ClarifyingQuestion]
    extracted_state: Dict[str, Any]
    language: str = "en"


class ElicitationEngine:
    """Evaluates brief context, extracts slots, and generates clarification inquiries dynamically."""

    def __init__(self, raw_input: Any = None):
        self.state: Dict[str, Any] = {
            "product_name": "",
            "product_type": "b2b_saas",
            "five_w_one_h": {},
            "demand_validation": {
                "problem_nature": "painkiller",
                "current_workarounds": "",
                "willingness_to_pay_or_suffer": "",
                "falsification_hypotheses": [],
                "validation_experiment": "",
            },
            "goals": [],
            "non_goals": [],
            "implicit_requirements": [],
        }
        self.detected_lang: str = "en"
        if raw_input:
            self.ingest(raw_input)

    def detect_language(self) -> str:
        """Dynamically detects whether the active context/input is Chinese or English."""
        raw_dump = json.dumps(self.state, ensure_ascii=False)
        if ZH_CHAR_REGEX.search(raw_dump):
            return "zh"
        return "en"

    def ingest(self, raw_input: Any) -> None:
        """Ingests dict, JSON string, or file path, extracting recognizable slots."""
        data: Dict[str, Any] = {}
        if isinstance(raw_input, dict):
            data = raw_input
        elif isinstance(raw_input, (str, Path)):
            path = Path(raw_input) if isinstance(raw_input, (str, Path)) else None
            if path and path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8")
                try:
                    data = json.loads(content)
                except Exception:
                    self._extract_from_text(content)
                    return
            elif isinstance(raw_input, str):
                text = raw_input.strip()
                try:
                    data = json.loads(text)
                except Exception:
                    self._extract_from_text(text)
                    return

        self._merge_structured_data(data)
        self.detected_lang = self.detect_language()

    def _extract_from_text(self, text: str) -> None:
        """Lightweight text heuristic extractor for unstructured briefs."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return

        # Attempt to capture product name from first line or header
        first_line = lines[0].lstrip("#").strip()
        if len(first_line) < 50:
            self.state["product_name"] = first_line

        # Heuristics for keywords
        full_text = " ".join(lines)
        if "who" not in self.state["five_w_one_h"]:
            match = re.search(r"(目标用户|用户角色|面向对象|Who|Audience|Users)[:：\s]+([^\n。；;]+)", full_text, re.I)
            if match:
                self.state["five_w_one_h"]["who"] = match.group(2).strip()

        if "why" not in self.state["five_w_one_h"]:
            match = re.search(r"(核心痛点|解决什么问题|背景动机|Why|Problem|Pain Points)[:：\s]+([^\n。；;]+)", full_text, re.I)
            if match:
                self.state["five_w_one_h"]["why"] = match.group(2).strip()

        if "what" not in self.state["five_w_one_h"]:
            match = re.search(r"(产品愿景|核心功能|主要能力|What|Vision|Features)[:：\s]+([^\n。；;]+)", full_text, re.I)
            if match:
                self.state["five_w_one_h"]["what"] = match.group(2).strip()

        self.detected_lang = "zh" if ZH_CHAR_REGEX.search(full_text) else "en"

    def _merge_structured_data(self, data: Dict[str, Any]) -> None:
        """Merges structured dict matching either brief or requirement_analysis format."""
        if "product_name" in data:
            self.state["product_name"] = data["product_name"]
        if "product_type" in data:
            self.state["product_type"] = data["product_type"]

        # Support product_brief format
        if "vision" in data and "what" not in self.state["five_w_one_h"]:
            self.state["five_w_one_h"]["what"] = data["vision"]
        if "core_pain_points" in data and "why" not in self.state["five_w_one_h"]:
            pts = data["core_pain_points"]
            self.state["five_w_one_h"]["why"] = "; ".join(pts) if isinstance(pts, list) else str(pts)
        if "stakeholders" in data and "who" not in self.state["five_w_one_h"]:
            st = data["stakeholders"]
            if isinstance(st, list):
                roles = [f"{s.get('role', '')} ({s.get('category', '')})" for s in st if isinstance(s, dict)]
                separator = "、" if ZH_CHAR_REGEX.search("".join(roles)) else ", "
                self.state["five_w_one_h"]["who"] = separator.join(roles)
        if "budget_and_timeline" in data and "when" not in self.state["five_w_one_h"]:
            self.state["five_w_one_h"]["when"] = str(data["budget_and_timeline"])
        if "client_context" in data and "where" not in self.state["five_w_one_h"]:
            self.state["five_w_one_h"]["where"] = str(data["client_context"])

        # Support requirement_analysis format
        if "five_w_one_h" in data and isinstance(data["five_w_one_h"], dict):
            self.state["five_w_one_h"].update(data["five_w_one_h"])
        if "demand_validation" in data and isinstance(data["demand_validation"], dict):
            self.state["demand_validation"].update(data["demand_validation"])
        if "goals" in data and isinstance(data["goals"], list):
            self.state["goals"] = data["goals"]
        if "non_goals" in data and isinstance(data["non_goals"], list):
            self.state["non_goals"] = data["non_goals"]
        if "implicit_requirements" in data and isinstance(data["implicit_requirements"], list):
            self.state["implicit_requirements"] = data["implicit_requirements"]

    def set_slot(self, slot_key: str, value: Any) -> None:
        """Sets a slot value by dot notation."""
        parts = slot_key.split(".")
        target = self.state
        for p in parts[:-1]:
            if p not in target or not isinstance(target[p], dict):
                target[p] = {}
            target = target[p]
        target[parts[-1]] = value
        self.detected_lang = self.detect_language()

    def get_slot(self, slot_key: str) -> Any:
        parts = slot_key.split(".")
        cur = self.state
        for p in parts:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    def assess(self) -> AssessmentReport:
        """Assesses completeness of all required slots against Aurakl criteria."""
        self.detected_lang = self.detect_language()
        slots_list = REQUIRED_SLOTS_ZH if self.detected_lang == "zh" else REQUIRED_SLOTS_EN

        fulfilled: List[str] = []
        missing: List[str] = []
        diagnostics: Dict[str, str] = {}
        questions: List[ClarifyingQuestion] = []

        total_weight = len(slots_list)
        earned_weight = 0.0

        for item in slots_list:
            val = self.get_slot(item.key)
            is_valid, reason = self._validate_slot(item, val)
            if is_valid:
                fulfilled.append(item.key)
                earned_weight += 1.0
            else:
                missing.append(item.key)
                diagnostics[item.key] = reason
                q = self._create_question_for_slot(item, val, reason)
                if q:
                    questions.append(q)

        score = round((earned_weight / total_weight) * 100.0, 1)
        can_proceed = (len(missing) == 0) and (score == 100.0)

        return AssessmentReport(
            completeness_score=score,
            can_proceed=can_proceed,
            fulfilled_slots=fulfilled,
            missing_slots=missing,
            slot_diagnostics=diagnostics,
            questions=questions,
            extracted_state=self.state,
            language=self.detected_lang,
        )

    def _validate_slot(self, item: SlotItem, value: Any) -> Tuple[bool, str]:
        is_zh = (self.detected_lang == "zh")

        if value is None:
            return False, "槽位为空" if is_zh else "Slot is empty"

        # String check
        if isinstance(value, str):
            val_str = value.strip()
            if not val_str:
                return False, "内容为空" if is_zh else "Content is empty"
            if len(val_str) < item.min_length:
                if is_zh:
                    return False, f"内容过短（当前长度 {len(val_str)}，要求至少 {item.min_length} 字符）"
                else:
                    return False, f"Content too short (length {len(val_str)}, required at least {item.min_length} chars)"
            match = PLACEHOLDER_REGEX.search(val_str)
            if match:
                if is_zh:
                    return False, f"检测到禁止的占位符: '{match.group(0)}'"
                else:
                    return False, f"Detected forbidden placeholder: '{match.group(0)}'"
            return True, "有效" if is_zh else "Valid"

        # List check
        if isinstance(value, list):
            if not value:
                return False, "列表为空" if is_zh else "List is empty"
            if item.key == "non_goals":
                if len(value) < 2:
                    return False, f"非目标数量不足（当前 {len(value)} 条，要求至少 2 条）" if is_zh else f"Insufficient Non-Goals ({len(value)} provided, at least 2 required)"
                for ng in value:
                    ng_str = json.dumps(ng, ensure_ascii=False) if isinstance(ng, dict) else str(ng)
                    for forbidden in FORBIDDEN_NON_GOAL_PHRASES:
                        if forbidden in ng_str:
                            return False, f"Non-Goals 违背规范：检测到禁止的正面陈述短语 '{forbidden}'" if is_zh else f"Non-Goals violation: detected forbidden positive phrasing '{forbidden}'"
            elif item.key == "implicit_requirements":
                if len(value) < 3:
                    return False, f"隐性需求数量不足（当前 {len(value)} 条，要求至少 3 条）" if is_zh else f"Insufficient Implicit Requirements ({len(value)} provided, at least 3 required)"
            return True, "有效" if is_zh else "Valid"

        return True, "有效" if is_zh else "Valid"

    def _create_question_for_slot(
        self, item: SlotItem, current_val: Any, reason: str
    ) -> Optional[ClarifyingQuestion]:
        """Generates context-rich, actionable questions with recommended choices in the user's language."""
        key = item.key
        name = self.state.get("product_name") or ("本项目" if self.detected_lang == "zh" else "this product")
        is_zh = (self.detected_lang == "zh")

        if is_zh:
            if key == "five_w_one_h.who":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"请明确 {name} 的核心目标用户角色（Who）及最终受益人是谁？",
                    why_needed="目标受众直接决定产品的信息架构、交互复杂度以及核心权限模型，AI 严禁脑补。",
                    options=[
                        "企业架构师与 Tech Lead（关注规范执行、不变量与系统合规）",
                        "一线研发人员与测试工程师（关注自动化工具、开发效率与 CI/CD 接入）",
                        "产品经理与业务负责人（关注需求流转、对账与业务价值交付）",
                    ],
                )
            elif key == "five_w_one_h.why":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"请阐述推动 {name} 立项的根本动机与核心痛点（Why）？",
                    why_needed="需要明确这是避免资损的刚需，还是降本增效的期望，以确定优先级与验收基线。",
                    options=[
                        "重构或高频迭代时核心业务逻辑屡遭破坏，导致重大线上资损",
                        "需求到研发/测试严重脱节，跨部门对账成本极高，反复返工",
                        "面临严格的外部合规与审计要求，现有手工文档无法提供双向可追溯证据链",
                    ],
                )
            elif key == "five_w_one_h.how":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"用户将通过怎样的典型业务流程与交互机制（How）使用 {name} 达成目标？",
                    why_needed="没有明确的使用路径与输入输出，无法编排状态机与编写 INVEST 故事。",
                    options=[
                        "IDE 插件/CLI 工具：开发者本地触发，拦截不合规变更并给出修改建议",
                        "CI/CD 流水线闸门：在 Pull Request 时自动运行审计并输出准入报告",
                        "云端协作平台：产品与架构师在线输入需求与规则，自动编译并流转下游",
                    ],
                )
            elif key == "five_w_one_h.when":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} 的触发时机与业务生命周期（When）是什么？",
                    why_needed="决定系统是常驻监听、按需触发，还是定期批处理。",
                    options=[
                        "需求设计与 PRD 评审阶段即时触发",
                        "代码提交/合并（PR Review）时自动化触发",
                        "系统重大版本发布上线的最终准入审核门禁",
                    ],
                )
            elif key == "five_w_one_h.where":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} 部署与运行在哪些系统环境或物理上下文中（Where）？",
                    why_needed="决定安全隔离级别、网络访问策略与本地/云端部署依赖。",
                    options=[
                        "企业私有云 / 局域网自建机房环境（严禁核心数据出境）",
                        "多租户公有云 SaaS 环境",
                        "本地开发终端（macOS / Linux / Windows）",
                    ],
                )
            elif key == "demand_validation.problem_nature":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} 解决的核心痛点属于哪种属性？",
                    why_needed="Aurakl 拒绝伪需求。必须界定是刚需止痛药(painkiller)、维他命还是糖果。",
                    options=[
                        "painkiller (刚需止痛药)：不解决会导致线上重大事故、资损或业务阻断",
                        "vitamin (维他命)：带来效率提升或体验优化，但无此工具业务仍能运转",
                        "candy (糖果)：趣味性或辅助性特性，用户付费与使用意愿弱",
                    ],
                )
            elif key == "demand_validation.current_workarounds":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"在没有 {name} 之前，目标用户目前是如何妥协解决该问题的？",
                    why_needed="用户现有妥协解（Current Workarounds）是证伪真实需求的最有力证据。",
                    options=[
                        "纯人工多方会议审查与 Excel 对账（耗时耗力且易遗漏）",
                        "编写一次性脚本或静态代码检查工具（无法穿透业务语义）",
                        "容忍现状并承担定期暴雷的修障成本",
                    ],
                )
            elif key == "demand_validation.willingness_to_pay_or_suffer":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="用户为了解决该问题，愿意付出多少预算或忍受多少变更成本？",
                    why_needed="验证需求的商业可行性与团队落地意愿。",
                    options=[
                        "有明确的采购或研发预算，支持引入并愿意改造现有研发流程",
                        "内部关键战略项目，VP 级别赞助并要求各团队强制推行",
                        "仅在不增加任何额外开发负担的前提下愿意试用",
                    ],
                )
            elif key == "non_goals":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"请明确 {name} 当前明确「不做」的非目标（Non-Goals，至少 2 项）及理由？",
                    why_needed="防止范围无序蔓延。Aurakl 规则严禁将正面限制写为 Non-Goals，必须是清晰的范围排除。",
                    options=[
                        "非目标 1: 不替代底层 IDE 或版本控制工具，仅作为分析与门禁插件接入",
                        "非目标 2: 不在 MVP 阶段支持移动端，仅聚焦桌面终端与 CI/CD 环境",
                        "非目标 3: 不提供通用 LLM 聊天助手能力，仅提供确定性规则与契约审计",
                    ],
                )
            elif key == "implicit_requirements":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="请补充至少 3 条隐性非功能需求（性能、安全、权限、可用性或合规）？",
                    why_needed="Aurakl 要求显式挖掘隐性需求，避免生产交付时出现重大遗漏。",
                    options=[
                        "性能：单次审计分析耗时必须控制在 3 秒以内，不得阻断研发流畅度",
                        "安全与隐私：企业核心代码与敏感业务数据严禁上传第三方非授信模型",
                        "可靠性与幂等性：同一批输入重复运行必须得到 100% 一致的确定性结果",
                    ],
                )
        else:
            # English Questions
            if key == "five_w_one_h.who":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"Please specify the primary target user personas and key beneficiaries (Who) for {name}.",
                    why_needed="Target personas directly determine information architecture, interaction depth, and permission models.",
                    options=[
                        "Enterprise Architects and Tech Leads (focused on invariant enforcement and governance)",
                        "Software Engineers and QA Leads (focused on automated tooling, developer ergonomics, and CI/CD gates)",
                        "Product Managers and Business Owners (focused on feature traceability, reconciliation, and value delivery)",
                    ],
                )
            elif key == "five_w_one_h.why":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"What is the underlying business driver and core root pain point (Why) justifying {name}?",
                    why_needed="Establishes whether this is a mandatory loss-prevention painkiller or an efficiency optimization.",
                    options=[
                        "Frequent regression and broken invariants during refactoring causing critical production losses",
                        "Severe disconnect between requirements, code, and QA tests leading to costly rework",
                        "Strict regulatory compliance mandates requiring verifiable two-way traceability chains",
                    ],
                )
            elif key == "five_w_one_h.how":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"Through what operational workflow and interaction mechanism (How) will users achieve their goals with {name}?",
                    why_needed="Concrete interaction paths are required to construct state machines and INVEST user stories.",
                    options=[
                        "IDE Extension / CLI Tool: Developers run local audits and receive actionable remediation inline",
                        "CI/CD Pipeline Gate: Automated audit runs during Pull Requests with pass/fail blocking reports",
                        "Cloud Collaboration Platform: PMs and architects configure rules online with automated downstream compilation",
                    ],
                )
            elif key == "five_w_one_h.when":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"What are the operational triggers and lifecycle frequency (When) for {name}?",
                    why_needed="Determines whether the system runs as an on-demand CLI, daemon listener, or scheduled batch job.",
                    options=[
                        "Triggered interactively during requirement analysis and PRD review stages",
                        "Triggered automatically upon code commit or Pull Request review",
                        "Triggered as the final gatekeeper prior to major production release deployment",
                    ],
                )
            elif key == "five_w_one_h.where":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"In what runtime environments and operational contexts (Where) will {name} be deployed?",
                    why_needed="Dictates security isolation levels, network connectivity boundaries, and local vs cloud dependencies.",
                    options=[
                        "Private enterprise VPC / on-premises data center (strict zero external data egress)",
                        "Multi-tenant public cloud SaaS environment",
                        "Local developer workstations (macOS / Linux / Windows)",
                    ],
                )
            elif key == "demand_validation.problem_nature":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"What is the true nature of the problem that {name} solves (Painkiller / Vitamin / Candy)?",
                    why_needed="Aurakl strictly rejects false demand; must determine whether it is a critical necessity.",
                    options=[
                        "painkiller: Essential necessity; failure to solve causes catastrophic outages, losses, or blockers",
                        "vitamin: Productivity or UX improvement, but operations can continue without it",
                        "candy: Nice-to-have or novel feature with low user willingness to pay",
                    ],
                )
            elif key == "demand_validation.current_workarounds":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"How do target users currently work around or tolerate this problem today without {name}?",
                    why_needed="Current workarounds represent the strongest empirical proof of genuine user demand.",
                    options=[
                        "Manual multi-stakeholder meetings and Excel reconciliation (error-prone and labor-intensive)",
                        "Ad-hoc one-off scripts or generic linters that fail to capture business semantics",
                        "Tolerating the status quo and bearing high incident response costs",
                    ],
                )
            elif key == "demand_validation.willingness_to_pay_or_suffer":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="What budget allocation or migration friction is the organization willing to endure to solve this?",
                    why_needed="Validates commercial feasibility and organizational adoption commitment.",
                    options=[
                        "Dedicated engineering productivity budget with mandate to upgrade existing workflows",
                        "VP-sponsored strategic priority mandatory across all product squads",
                        "Trial adoption only under the condition of zero additional developer burden",
                    ],
                )
            elif key == "non_goals":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"Please specify at least 2 explicit Non-Goals that {name} deliberately excludes from scope, and why?",
                    why_needed="Prevents scope creep. Aurakl rules prohibit positive limits as Non-Goals; must be explicit exclusions.",
                    options=[
                        "Non-Goal 1: Does not replace underlying IDE or VCS; functions strictly as an audit gate plugin",
                        "Non-Goal 2: MVP will not support native mobile clients; focused exclusively on desktop and CI/CD",
                        "Non-Goal 3: Does not provide open-ended LLM chat; delivers deterministic rules and contract audits",
                    ],
                )
            elif key == "implicit_requirements":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="Please provide at least 3 implicit non-functional constraints (performance, security, reliability, compliance).",
                    why_needed="Aurakl requires explicit discovery of implicit constraints to prevent production delivery failure.",
                    options=[
                        "Performance: Single audit cycle must complete within 3 seconds without disrupting developer flow",
                        "Security & Privacy: Proprietary source code and sensitive data must never leave the enterprise boundary",
                        "Reliability & Idempotency: Repeated executions against identical inputs must yield 100% deterministic verdicts",
                    ],
                )
        return None

    def export_requirement_analysis(self) -> Dict[str, Any]:
        """Exports state as a fully compliant requirement-analysis v2 document."""
        rep = self.assess()
        if not rep.can_proceed:
            msg = (
                f"需求槽位未闭环（当前完整度 {rep.completeness_score}%），存在未决项: {rep.missing_slots}"
                if self.detected_lang == "zh"
                else f"Requirement slots incomplete (completeness {rep.completeness_score}%); unresolved items: {rep.missing_slots}"
            )
            raise ValueError(msg)

        # Normalize non_goals into object array
        normalized_non_goals = []
        for ng in self.state["non_goals"]:
            if isinstance(ng, dict) and "item" in ng:
                normalized_non_goals.append(ng)
            else:
                rationale = "界定 MVP 范围边界，避免工程失焦" if self.detected_lang == "zh" else "Define MVP boundary to prevent engineering scope creep"
                normalized_non_goals.append({
                    "item": str(ng),
                    "rationale": rationale
                })

        # Normalize implicit requirements
        normalized_implicit = []
        for ir in self.state["implicit_requirements"]:
            if isinstance(ir, dict) and "requirement" in ir:
                normalized_implicit.append(ir)
            else:
                normalized_implicit.append({
                    "category": "system_defense",
                    "requirement": str(ir),
                    "decision": "included" if "decision" not in str(ir) else "approved"
                })

        return {
            "product_name": self.state["product_name"] or "Aurakl Product",
            "product_type": self.state["product_type"],
            "five_w_one_h": self.state["five_w_one_h"],
            "demand_validation": self.state["demand_validation"],
            "goals": self.state["goals"],
            "non_goals": normalized_non_goals,
            "implicit_requirements": normalized_implicit,
        }


def format_report_console(report: AssessmentReport) -> str:
    is_zh = (report.language == "zh")
    lines = []
    lines.append("=" * 60)
    if is_zh:
        lines.append(f"  Aurakl 5W1H 需求完备度诊断报告 (得分: {report.completeness_score}%)")
    else:
        lines.append(f"  Aurakl 5W1H Requirement Completeness Report (Score: {report.completeness_score}%)")
    lines.append("=" * 60)

    if is_zh:
        status_str = "✅ 完备闭环 (可流转)" if report.can_proceed else "❌ 存在缺漏 (阻断产出)"
        lines.append(f"准入状态: {status_str}")
        lines.append(f"已就绪槽位: {len(report.fulfilled_slots)} 项")
        lines.append(f"待澄清槽位: {len(report.missing_slots)} 项")
    else:
        status_str = "✅ Fully Converged (Ready)" if report.can_proceed else "❌ Incomplete (Blocking)"
        lines.append(f"Gate Status: {status_str}")
        lines.append(f"Fulfilled Slots: {len(report.fulfilled_slots)}")
        lines.append(f"Missing Slots: {len(report.missing_slots)}")

    if report.missing_slots:
        lines.append("-" * 60)
        lines.append("【待解决的阻塞项】:" if is_zh else "[Blocking Missing Items]:")
        for k in report.missing_slots:
            reason = report.slot_diagnostics.get(k, "缺失" if is_zh else "Missing")
            lines.append(f"  • [{k}]: {reason}")

    if report.questions:
        lines.append("-" * 60)
        lines.append("【向用户发起追问的澄清清单】:" if is_zh else "[Clarification Inquiries for User]:")
        for idx, q in enumerate(report.questions, 1):
            q_title = f"[问题 {idx}]" if is_zh else f"[Question {idx}]"
            lines.append(f"\n{q_title} {q.question}")
            reason_label = "原因" if is_zh else "Rationale"
            lines.append(f"  {reason_label}: {q.why_needed}")
            if q.options:
                opt_label = "推荐选项" if is_zh else "Recommended Options"
                lines.append(f"  {opt_label}:")
                for opt in q.options:
                    lines.append(f"    - {opt}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aurakl 5W1H Elicitation Engine")
    parser.add_argument("--assess", help="Path to input brief file or raw text to assess")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--export", help="Target path to export verified requirements.json")
    parser.add_argument("--set-slot", nargs=2, metavar=("KEY", "VAL"), help="Set slot value")
    parser.add_argument("--state-file", default=".aurakl_pm_state.json", help="Persistent state file")
    args = parser.parse_args()

    engine = ElicitationEngine()
    state_path = Path(args.state_file)

    if state_path.exists():
        try:
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            engine.ingest(saved)
        except Exception as e:
            print(f"Warning: failed to load state file: {e}", file=sys.stderr)

    if args.assess:
        engine.ingest(args.assess)

    if args.set_slot:
        k, v = args.set_slot
        try:
            parsed_v = json.loads(v)
            engine.set_slot(k, parsed_v)
        except Exception:
            engine.set_slot(k, v)

    # Save state
    try:
        state_path.write_text(json.dumps(engine.state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    report = engine.assess()

    if args.export:
        if not report.can_proceed:
            print(f"Error: Cannot export - requirements are not complete ({report.completeness_score}%).", file=sys.stderr)
            for q in report.questions:
                print(f"- {q.question}", file=sys.stderr)
            return 1
        out = engine.export_requirement_analysis()
        Path(args.export).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Successfully exported valid requirement analysis to: {args.export}")
        return 0

    if args.json:
        # Machine readable
        out_dict = {
            "completeness_score": report.completeness_score,
            "can_proceed": report.can_proceed,
            "fulfilled_slots": report.fulfilled_slots,
            "missing_slots": report.missing_slots,
            "diagnostics": report.slot_diagnostics,
            "questions": [asdict(q) for q in report.questions],
            "language": report.language,
        }
        print(json.dumps(out_dict, ensure_ascii=False, indent=2))
    else:
        print(format_report_console(report))

    return 0 if report.can_proceed else 2


if __name__ == "__main__":
    sys.exit(main())
