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
    "\u6b63\u9762\u9648\u8ff0",
    "\u4e0d\u662f\u4e00\u53e5\u300c\u4e0d\u652f\u6301",
    "\u800c\u4e0d\u662f\u300c\u4e0d\u652f\u6301",
    "\u6539\u5199\u6210\u300c\u7cfb\u7edf\u4ec5",
    "\u7cfb\u7edf\u4ec5\u652f\u6301",
    "\u4ec5\u652f\u6301",
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
    r"\b(TBD|TODO|UNVERIFIED|PENDING|TO_BE_CONFIRMED|\u5f85\u786e\u8ba4|\u5f85\u5b9a|\u6682\u65e0|\u540e\u7eed\u8865\u5145|\u5f85\u5546\u69b7)\b", re.IGNORECASE
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
    SlotItem("five_w_one_h.who", "Who (\u76ee\u6807\u5ba2\u7fa4\u4e0e\u53d7\u76ca\u4eba)", "\u7cfb\u7edf\u7684\u76ee\u6807\u89d2\u8272\u3001\u7528\u6237\u753b\u50cf\u53ca\u6838\u5fc3\u53d7\u76ca\u4eba", 10),
    SlotItem("five_w_one_h.why", "Why (\u6838\u5fc3\u52a8\u673a\u4e0e\u75db\u70b9\u6839\u56e0)", "\u89e6\u53d1\u8be5\u9700\u6c42\u7684\u6df1\u5c42\u75db\u70b9\u3001\u4e1a\u52a1\u963b\u788d\u6216\u5408\u89c4\u52a8\u673a", 15),
    SlotItem("five_w_one_h.what", "What (\u6838\u5fc3\u4ef7\u503c\u8fb9\u754c\u4e0e\u529f\u80fd)", "\u7cfb\u7edf\u4ea4\u4ed8\u7684\u6838\u5fc3\u4ef7\u503c\u3001\u80fd\u529b\u8303\u56f4\u4e0e\u4e1a\u52a1\u5b9e\u4f53", 10),
    SlotItem("five_w_one_h.when", "When (\u89e6\u53d1\u65f6\u673a\u4e0e\u751f\u547d\u5468\u671f)", "\u5728\u4ec0\u4e48\u65f6\u95f4\u3001\u89e6\u53d1\u6761\u4ef6\u6216\u4e1a\u52a1\u9891\u6b21\u4e0b\u4f7f\u7528", 5),
    SlotItem("five_w_one_h.where", "Where (\u8fd0\u884c\u73af\u5883\u4e0e\u7cfb\u7edf\u8fb9\u754c)", "\u5728\u54ea\u4e9b\u5ba2\u6237\u7aef\u3001\u4e91\u73af\u5883\u3001\u5bbf\u4e3b\u5e73\u53f0\u6216\u4e0a\u4e0b\u6587\u4e2d\u8fd0\u884c", 5),
    SlotItem("five_w_one_h.how", "How (\u8fbe\u6210\u8def\u5f84\u4e0e\u4ea4\u4e92\u65b9\u5f0f)", "\u5173\u952e\u4e1a\u52a1\u8def\u5f84\u3001\u7528\u6237\u4ea4\u4e92\u6d41\u7a0b\u4e0e\u8fbe\u6210\u76ee\u6807\u7684\u673a\u5236", 15),
    SlotItem("demand_validation.problem_nature", "\u95ee\u9898\u5c5e\u6027 (Painkiller/Vitamin/Candy)", "\u5c5e\u4e8e\u521a\u9700\u6b62\u75db\u836f(painkiller)\u3001\u9526\u4e0a\u6dfb\u82b1\u7ef4\u4ed6\u547d\u8fd8\u662f\u7cd6\u679c", 4),
    SlotItem("demand_validation.current_workarounds", "\u73b0\u6709\u66ff\u4ee3\u59a5\u534f\u65b9\u6848", "\u7528\u6237\u5728\u6ca1\u6709\u672c\u7cfb\u7edf\u524d\u5982\u4f55\u89e3\u51b3\u8be5\u95ee\u9898\uff08\u7eaf\u624b\u5de5/\u5bb9\u5fcd/\u66ff\u4ee3\u54c1\uff09", 8),
    SlotItem("demand_validation.willingness_to_pay_or_suffer", "\u652f\u4ed8\u610f\u613f\u4e0e\u5fcd\u53d7\u6210\u672c", "\u7528\u6237\u7684\u91c7\u8d2d\u9884\u7b97\u3001\u5207\u6362\u4ee3\u4ef7\u6216\u75db\u70b9\u5fcd\u53d7\u9608\u503c", 8),
    SlotItem("demand_validation.falsification_hypotheses", "\u8bc1\u4f2a\u5047\u8bbe", "\u54ea\u4e9b\u524d\u63d0\u4e00\u65e6\u88ab\u63a8\u7ffb\uff0c\u8be5\u9700\u6c42\u5373\u8bc1\u660e\u4e3a\u4f2a\u9700\u6c42", 10),
    SlotItem("demand_validation.validation_experiment", "\u9a8c\u8bc1\u5b9e\u9a8c", "\u5982\u4f55\u4ee5\u6700\u4f4e\u6210\u672c\u901a\u8fc7\u6570\u636e\u6216\u5b9e\u9a8c\u9a8c\u8bc1\u4e0a\u8ff0\u5047\u8bbe", 10),
    SlotItem("goals", "\u76ee\u6807 Goals", "\u671f\u671b\u8fbe\u6210\u7684\u4e1a\u52a1\u76ee\u6807\u5217\u8868\uff08\u81f3\u5c11 1 \u6761\u660e\u786e\u76ee\u6807\uff09", 10),
    SlotItem("non_goals", "\u975e\u76ee\u6807 Non-Goals", "\u660e\u786e\u6392\u9664\u7684\u8303\u56f4\uff08\u5fc5\u987b >= 2 \u6761\uff0c\u4e14\u4e25\u7981\u6b63\u9762\u6539\u5199\uff09", 10),
    SlotItem("implicit_requirements", "\u9690\u6027\u9700\u6c42", "\u4ece\u5b89\u5168\u3001\u6027\u80fd\u3001\u5408\u89c4\u3001\u5bb9\u707e\u7b49\u7ef4\u5ea6\u6316\u6398\u7684\u9690\u6027\u7ea6\u675f\uff08>= 3 \u6761\uff09", 10),
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
            match = re.search(r"(\u76ee\u6807\u7528\u6237|\u7528\u6237\u89d2\u8272|\u9762\u5411\u5bf9\u8c61|Who|Audience|Users)[:\uff1a\s]+([^\n\u3002\uff1b;]+)", full_text, re.I)
            if match:
                self.state["five_w_one_h"]["who"] = match.group(2).strip()

        if "why" not in self.state["five_w_one_h"]:
            match = re.search(r"(\u6838\u5fc3\u75db\u70b9|\u89e3\u51b3\u4ec0\u4e48\u95ee\u9898|\u80cc\u666f\u52a8\u673a|Why|Problem|Pain Points)[:\uff1a\s]+([^\n\u3002\uff1b;]+)", full_text, re.I)
            if match:
                self.state["five_w_one_h"]["why"] = match.group(2).strip()

        if "what" not in self.state["five_w_one_h"]:
            match = re.search(r"(\u4ea7\u54c1\u613f\u666f|\u6838\u5fc3\u529f\u80fd|\u4e3b\u8981\u80fd\u529b|What|Vision|Features)[:\uff1a\s]+([^\n\u3002\uff1b;]+)", full_text, re.I)
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
                separator = "\u3001" if ZH_CHAR_REGEX.search("".join(roles)) else ", "
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
            return False, "\u69fd\u4f4d\u4e3a\u7a7a" if is_zh else "Slot is empty"

        # String check
        if isinstance(value, str):
            val_str = value.strip()
            if not val_str:
                return False, "\u5185\u5bb9\u4e3a\u7a7a" if is_zh else "Content is empty"
            if len(val_str) < item.min_length:
                if is_zh:
                    return False, f"\u5185\u5bb9\u8fc7\u77ed\uff08\u5f53\u524d\u957f\u5ea6 {len(val_str)}\uff0c\u8981\u6c42\u81f3\u5c11 {item.min_length} \u5b57\u7b26\uff09"
                else:
                    return False, f"Content too short (length {len(val_str)}, required at least {item.min_length} chars)"
            match = PLACEHOLDER_REGEX.search(val_str)
            if match:
                if is_zh:
                    return False, f"\u68c0\u6d4b\u5230\u7981\u6b62\u7684\u5360\u4f4d\u7b26: '{match.group(0)}'"
                else:
                    return False, f"Detected forbidden placeholder: '{match.group(0)}'"
            return True, "\u6709\u6548" if is_zh else "Valid"

        # List check
        if isinstance(value, list):
            if not value:
                return False, "\u5217\u8868\u4e3a\u7a7a" if is_zh else "List is empty"
            if item.key == "non_goals":
                if len(value) < 2:
                    return False, f"\u975e\u76ee\u6807\u6570\u91cf\u4e0d\u8db3\uff08\u5f53\u524d {len(value)} \u6761\uff0c\u8981\u6c42\u81f3\u5c11 2 \u6761\uff09" if is_zh else f"Insufficient Non-Goals ({len(value)} provided, at least 2 required)"
                for ng in value:
                    ng_str = json.dumps(ng, ensure_ascii=False) if isinstance(ng, dict) else str(ng)
                    for forbidden in FORBIDDEN_NON_GOAL_PHRASES:
                        if forbidden in ng_str:
                            return False, f"Non-Goals \u8fdd\u80cc\u89c4\u8303\uff1a\u68c0\u6d4b\u5230\u7981\u6b62\u7684\u6b63\u9762\u9648\u8ff0\u77ed\u8bed '{forbidden}'" if is_zh else f"Non-Goals violation: detected forbidden positive phrasing '{forbidden}'"
            elif item.key == "implicit_requirements":
                if len(value) < 3:
                    return False, f"\u9690\u6027\u9700\u6c42\u6570\u91cf\u4e0d\u8db3\uff08\u5f53\u524d {len(value)} \u6761\uff0c\u8981\u6c42\u81f3\u5c11 3 \u6761\uff09" if is_zh else f"Insufficient Implicit Requirements ({len(value)} provided, at least 3 required)"
            return True, "\u6709\u6548" if is_zh else "Valid"

        return True, "\u6709\u6548" if is_zh else "Valid"

    def _create_question_for_slot(
        self, item: SlotItem, current_val: Any, reason: str
    ) -> Optional[ClarifyingQuestion]:
        """Generates context-rich, actionable questions with recommended choices in the user's language."""
        key = item.key
        name = self.state.get("product_name") or ("\u672c\u9879\u76ee" if self.detected_lang == "zh" else "this product")
        is_zh = (self.detected_lang == "zh")

        if is_zh:
            if key == "five_w_one_h.who":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"\u8bf7\u660e\u786e {name} \u7684\u6838\u5fc3\u76ee\u6807\u7528\u6237\u89d2\u8272\uff08Who\uff09\u53ca\u6700\u7ec8\u53d7\u76ca\u4eba\u662f\u8c01\uff1f",
                    why_needed="\u76ee\u6807\u53d7\u4f17\u76f4\u63a5\u51b3\u5b9a\u4ea7\u54c1\u7684\u4fe1\u606f\u67b6\u6784\u3001\u4ea4\u4e92\u590d\u6742\u5ea6\u4ee5\u53ca\u6838\u5fc3\u6743\u9650\u6a21\u578b\uff0cAI \u4e25\u7981\u8111\u8865\u3002",
                    options=[
                        "\u4f01\u4e1a\u67b6\u6784\u5e08\u4e0e Tech Lead\uff08\u5173\u6ce8\u89c4\u8303\u6267\u884c\u3001\u4e0d\u53d8\u91cf\u4e0e\u7cfb\u7edf\u5408\u89c4\uff09",
                        "\u4e00\u7ebf\u7814\u53d1\u4eba\u5458\u4e0e\u6d4b\u8bd5\u5de5\u7a0b\u5e08\uff08\u5173\u6ce8\u81ea\u52a8\u5316\u5de5\u5177\u3001\u5f00\u53d1\u6548\u7387\u4e0e CI/CD \u63a5\u5165\uff09",
                        "\u4ea7\u54c1\u7ecf\u7406\u4e0e\u4e1a\u52a1\u8d1f\u8d23\u4eba\uff08\u5173\u6ce8\u9700\u6c42\u6d41\u8f6c\u3001\u5bf9\u8d26\u4e0e\u4e1a\u52a1\u4ef7\u503c\u4ea4\u4ed8\uff09",
                    ],
                )
            elif key == "five_w_one_h.why":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"\u8bf7\u9610\u8ff0\u63a8\u52a8 {name} \u7acb\u9879\u7684\u6839\u672c\u52a8\u673a\u4e0e\u6838\u5fc3\u75db\u70b9\uff08Why\uff09\uff1f",
                    why_needed="\u9700\u8981\u660e\u786e\u8fd9\u662f\u907f\u514d\u8d44\u635f\u7684\u521a\u9700\uff0c\u8fd8\u662f\u964d\u672c\u589e\u6548\u7684\u671f\u671b\uff0c\u4ee5\u786e\u5b9a\u4f18\u5148\u7ea7\u4e0e\u9a8c\u6536\u57fa\u7ebf\u3002",
                    options=[
                        "\u91cd\u6784\u6216\u9ad8\u9891\u8fed\u4ee3\u65f6\u6838\u5fc3\u4e1a\u52a1\u903b\u8f91\u5c61\u906d\u7834\u574f\uff0c\u5bfc\u81f4\u91cd\u5927\u7ebf\u4e0a\u8d44\u635f",
                        "\u9700\u6c42\u5230\u7814\u53d1/\u6d4b\u8bd5\u4e25\u91cd\u8131\u8282\uff0c\u8de8\u90e8\u95e8\u5bf9\u8d26\u6210\u672c\u6781\u9ad8\uff0c\u53cd\u590d\u8fd4\u5de5",
                        "\u9762\u4e34\u4e25\u683c\u7684\u5916\u90e8\u5408\u89c4\u4e0e\u5ba1\u8ba1\u8981\u6c42\uff0c\u73b0\u6709\u624b\u5de5\u6587\u6863\u65e0\u6cd5\u63d0\u4f9b\u53cc\u5411\u53ef\u8ffd\u6eaf\u8bc1\u636e\u94fe",
                    ],
                )
            elif key == "five_w_one_h.how":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"\u7528\u6237\u5c06\u901a\u8fc7\u600e\u6837\u7684\u5178\u578b\u4e1a\u52a1\u6d41\u7a0b\u4e0e\u4ea4\u4e92\u673a\u5236\uff08How\uff09\u4f7f\u7528 {name} \u8fbe\u6210\u76ee\u6807\uff1f",
                    why_needed="\u6ca1\u6709\u660e\u786e\u7684\u4f7f\u7528\u8def\u5f84\u4e0e\u8f93\u5165\u8f93\u51fa\uff0c\u65e0\u6cd5\u7f16\u6392\u72b6\u6001\u673a\u4e0e\u7f16\u5199 INVEST \u6545\u4e8b\u3002",
                    options=[
                        "IDE \u63d2\u4ef6/CLI \u5de5\u5177\uff1a\u5f00\u53d1\u8005\u672c\u5730\u89e6\u53d1\uff0c\u62e6\u622a\u4e0d\u5408\u89c4\u53d8\u66f4\u5e76\u7ed9\u51fa\u4fee\u6539\u5efa\u8bae",
                        "CI/CD \u6d41\u6c34\u7ebf\u95f8\u95e8\uff1a\u5728 Pull Request \u65f6\u81ea\u52a8\u8fd0\u884c\u5ba1\u8ba1\u5e76\u8f93\u51fa\u51c6\u5165\u62a5\u544a",
                        "\u4e91\u7aef\u534f\u4f5c\u5e73\u53f0\uff1a\u4ea7\u54c1\u4e0e\u67b6\u6784\u5e08\u5728\u7ebf\u8f93\u5165\u9700\u6c42\u4e0e\u89c4\u5219\uff0c\u81ea\u52a8\u7f16\u8bd1\u5e76\u6d41\u8f6c\u4e0b\u6e38",
                    ],
                )
            elif key == "five_w_one_h.when":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} \u7684\u89e6\u53d1\u65f6\u673a\u4e0e\u4e1a\u52a1\u751f\u547d\u5468\u671f\uff08When\uff09\u662f\u4ec0\u4e48\uff1f",
                    why_needed="\u51b3\u5b9a\u7cfb\u7edf\u662f\u5e38\u9a7b\u76d1\u542c\u3001\u6309\u9700\u89e6\u53d1\uff0c\u8fd8\u662f\u5b9a\u671f\u6279\u5904\u7406\u3002",
                    options=[
                        "\u9700\u6c42\u8bbe\u8ba1\u4e0e PRD \u8bc4\u5ba1\u9636\u6bb5\u5373\u65f6\u89e6\u53d1",
                        "\u4ee3\u7801\u63d0\u4ea4/\u5408\u5e76\uff08PR Review\uff09\u65f6\u81ea\u52a8\u5316\u89e6\u53d1",
                        "\u7cfb\u7edf\u91cd\u5927\u7248\u672c\u53d1\u5e03\u4e0a\u7ebf\u7684\u6700\u7ec8\u51c6\u5165\u5ba1\u6838\u95e8\u7981",
                    ],
                )
            elif key == "five_w_one_h.where":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} \u90e8\u7f72\u4e0e\u8fd0\u884c\u5728\u54ea\u4e9b\u7cfb\u7edf\u73af\u5883\u6216\u7269\u7406\u4e0a\u4e0b\u6587\u4e2d\uff08Where\uff09\uff1f",
                    why_needed="\u51b3\u5b9a\u5b89\u5168\u9694\u79bb\u7ea7\u522b\u3001\u7f51\u7edc\u8bbf\u95ee\u7b56\u7565\u4e0e\u672c\u5730/\u4e91\u7aef\u90e8\u7f72\u4f9d\u8d56\u3002",
                    options=[
                        "\u4f01\u4e1a\u79c1\u6709\u4e91 / \u5c40\u57df\u7f51\u81ea\u5efa\u673a\u623f\u73af\u5883\uff08\u4e25\u7981\u6838\u5fc3\u6570\u636e\u51fa\u5883\uff09",
                        "\u591a\u79df\u6237\u516c\u6709\u4e91 SaaS \u73af\u5883",
                        "\u672c\u5730\u5f00\u53d1\u7ec8\u7aef\uff08macOS / Linux / Windows\uff09",
                    ],
                )
            elif key == "demand_validation.problem_nature":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"{name} \u89e3\u51b3\u7684\u6838\u5fc3\u75db\u70b9\u5c5e\u4e8e\u54ea\u79cd\u5c5e\u6027\uff1f",
                    why_needed="Aurakl \u62d2\u7edd\u4f2a\u9700\u6c42\u3002\u5fc5\u987b\u754c\u5b9a\u662f\u521a\u9700\u6b62\u75db\u836f(painkiller)\u3001\u7ef4\u4ed6\u547d\u8fd8\u662f\u7cd6\u679c\u3002",
                    options=[
                        "painkiller (\u521a\u9700\u6b62\u75db\u836f)\uff1a\u4e0d\u89e3\u51b3\u4f1a\u5bfc\u81f4\u7ebf\u4e0a\u91cd\u5927\u4e8b\u6545\u3001\u8d44\u635f\u6216\u4e1a\u52a1\u963b\u65ad",
                        "vitamin (\u7ef4\u4ed6\u547d)\uff1a\u5e26\u6765\u6548\u7387\u63d0\u5347\u6216\u4f53\u9a8c\u4f18\u5316\uff0c\u4f46\u65e0\u6b64\u5de5\u5177\u4e1a\u52a1\u4ecd\u80fd\u8fd0\u8f6c",
                        "candy (\u7cd6\u679c)\uff1a\u8da3\u5473\u6027\u6216\u8f85\u52a9\u6027\u7279\u6027\uff0c\u7528\u6237\u4ed8\u8d39\u4e0e\u4f7f\u7528\u610f\u613f\u5f31",
                    ],
                )
            elif key == "demand_validation.current_workarounds":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"\u5728\u6ca1\u6709 {name} \u4e4b\u524d\uff0c\u76ee\u6807\u7528\u6237\u76ee\u524d\u662f\u5982\u4f55\u59a5\u534f\u89e3\u51b3\u8be5\u95ee\u9898\u7684\uff1f",
                    why_needed="\u7528\u6237\u73b0\u6709\u59a5\u534f\u89e3\uff08Current Workarounds\uff09\u662f\u8bc1\u4f2a\u771f\u5b9e\u9700\u6c42\u7684\u6700\u6709\u529b\u8bc1\u636e\u3002",
                    options=[
                        "\u7eaf\u4eba\u5de5\u591a\u65b9\u4f1a\u8bae\u5ba1\u67e5\u4e0e Excel \u5bf9\u8d26\uff08\u8017\u65f6\u8017\u529b\u4e14\u6613\u9057\u6f0f\uff09",
                        "\u7f16\u5199\u4e00\u6b21\u6027\u811a\u672c\u6216\u9759\u6001\u4ee3\u7801\u68c0\u67e5\u5de5\u5177\uff08\u65e0\u6cd5\u7a7f\u900f\u4e1a\u52a1\u8bed\u4e49\uff09",
                        "\u5bb9\u5fcd\u73b0\u72b6\u5e76\u627f\u62c5\u5b9a\u671f\u66b4\u96f7\u7684\u4fee\u969c\u6210\u672c",
                    ],
                )
            elif key == "demand_validation.willingness_to_pay_or_suffer":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="\u7528\u6237\u4e3a\u4e86\u89e3\u51b3\u8be5\u95ee\u9898\uff0c\u613f\u610f\u4ed8\u51fa\u591a\u5c11\u9884\u7b97\u6216\u5fcd\u53d7\u591a\u5c11\u53d8\u66f4\u6210\u672c\uff1f",
                    why_needed="\u9a8c\u8bc1\u9700\u6c42\u7684\u5546\u4e1a\u53ef\u884c\u6027\u4e0e\u56e2\u961f\u843d\u5730\u610f\u613f\u3002",
                    options=[
                        "\u6709\u660e\u786e\u7684\u91c7\u8d2d\u6216\u7814\u53d1\u9884\u7b97\uff0c\u652f\u6301\u5f15\u5165\u5e76\u613f\u610f\u6539\u9020\u73b0\u6709\u7814\u53d1\u6d41\u7a0b",
                        "\u5185\u90e8\u5173\u952e\u6218\u7565\u9879\u76ee\uff0cVP \u7ea7\u522b\u8d5e\u52a9\u5e76\u8981\u6c42\u5404\u56e2\u961f\u5f3a\u5236\u63a8\u884c",
                        "\u4ec5\u5728\u4e0d\u589e\u52a0\u4efb\u4f55\u989d\u5916\u5f00\u53d1\u8d1f\u62c5\u7684\u524d\u63d0\u4e0b\u613f\u610f\u8bd5\u7528",
                    ],
                )
            elif key == "non_goals":
                return ClarifyingQuestion(
                    slot_key=key,
                    question=f"\u8bf7\u660e\u786e {name} \u5f53\u524d\u660e\u786e\u300c\u4e0d\u505a\u300d\u7684\u975e\u76ee\u6807\uff08Non-Goals\uff0c\u81f3\u5c11 2 \u9879\uff09\u53ca\u7406\u7531\uff1f",
                    why_needed="\u9632\u6b62\u8303\u56f4\u65e0\u5e8f\u8513\u5ef6\u3002Aurakl \u89c4\u5219\u4e25\u7981\u5c06\u6b63\u9762\u9650\u5236\u5199\u4e3a Non-Goals\uff0c\u5fc5\u987b\u662f\u6e05\u6670\u7684\u8303\u56f4\u6392\u9664\u3002",
                    options=[
                        "\u975e\u76ee\u6807 1: \u4e0d\u66ff\u4ee3\u5e95\u5c42 IDE \u6216\u7248\u672c\u63a7\u5236\u5de5\u5177\uff0c\u4ec5\u4f5c\u4e3a\u5206\u6790\u4e0e\u95e8\u7981\u63d2\u4ef6\u63a5\u5165",
                        "\u975e\u76ee\u6807 2: \u4e0d\u5728 MVP \u9636\u6bb5\u652f\u6301\u79fb\u52a8\u7aef\uff0c\u4ec5\u805a\u7126\u684c\u9762\u7ec8\u7aef\u4e0e CI/CD \u73af\u5883",
                        "\u975e\u76ee\u6807 3: \u4e0d\u63d0\u4f9b\u901a\u7528 LLM \u804a\u5929\u52a9\u624b\u80fd\u529b\uff0c\u4ec5\u63d0\u4f9b\u786e\u5b9a\u6027\u89c4\u5219\u4e0e\u5951\u7ea6\u5ba1\u8ba1",
                    ],
                )
            elif key == "implicit_requirements":
                return ClarifyingQuestion(
                    slot_key=key,
                    question="\u8bf7\u8865\u5145\u81f3\u5c11 3 \u6761\u9690\u6027\u975e\u529f\u80fd\u9700\u6c42\uff08\u6027\u80fd\u3001\u5b89\u5168\u3001\u6743\u9650\u3001\u53ef\u7528\u6027\u6216\u5408\u89c4\uff09\uff1f",
                    why_needed="Aurakl \u8981\u6c42\u663e\u5f0f\u6316\u6398\u9690\u6027\u9700\u6c42\uff0c\u907f\u514d\u751f\u4ea7\u4ea4\u4ed8\u65f6\u51fa\u73b0\u91cd\u5927\u9057\u6f0f\u3002",
                    options=[
                        "\u6027\u80fd\uff1a\u5355\u6b21\u5ba1\u8ba1\u5206\u6790\u8017\u65f6\u5fc5\u987b\u63a7\u5236\u5728 3 \u79d2\u4ee5\u5185\uff0c\u4e0d\u5f97\u963b\u65ad\u7814\u53d1\u6d41\u7545\u5ea6",
                        "\u5b89\u5168\u4e0e\u9690\u79c1\uff1a\u4f01\u4e1a\u6838\u5fc3\u4ee3\u7801\u4e0e\u654f\u611f\u4e1a\u52a1\u6570\u636e\u4e25\u7981\u4e0a\u4f20\u7b2c\u4e09\u65b9\u975e\u6388\u4fe1\u6a21\u578b",
                        "\u53ef\u9760\u6027\u4e0e\u5e42\u7b49\u6027\uff1a\u540c\u4e00\u6279\u8f93\u5165\u91cd\u590d\u8fd0\u884c\u5fc5\u987b\u5f97\u5230 100% \u4e00\u81f4\u7684\u786e\u5b9a\u6027\u7ed3\u679c",
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
                f"\u9700\u6c42\u69fd\u4f4d\u672a\u95ed\u73af\uff08\u5f53\u524d\u5b8c\u6574\u5ea6 {rep.completeness_score}%\uff09\uff0c\u5b58\u5728\u672a\u51b3\u9879: {rep.missing_slots}"
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
                rationale = "\u754c\u5b9a MVP \u8303\u56f4\u8fb9\u754c\uff0c\u907f\u514d\u5de5\u7a0b\u5931\u7126" if self.detected_lang == "zh" else "Define MVP boundary to prevent engineering scope creep"
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
        lines.append(f"  Aurakl 5W1H \u9700\u6c42\u5b8c\u5907\u5ea6\u8bca\u65ad\u62a5\u544a (\u5f97\u5206: {report.completeness_score}%)")
    else:
        lines.append(f"  Aurakl 5W1H Requirement Completeness Report (Score: {report.completeness_score}%)")
    lines.append("=" * 60)

    if is_zh:
        status_str = "✅ \u5b8c\u5907\u95ed\u73af (\u53ef\u6d41\u8f6c)" if report.can_proceed else "❌ \u5b58\u5728\u7f3a\u6f0f (\u963b\u65ad\u4ea7\u51fa)"
        lines.append(f"\u51c6\u5165\u72b6\u6001: {status_str}")
        lines.append(f"\u5df2\u5c31\u7eea\u69fd\u4f4d: {len(report.fulfilled_slots)} \u9879")
        lines.append(f"\u5f85\u6f84\u6e05\u69fd\u4f4d: {len(report.missing_slots)} \u9879")
    else:
        status_str = "✅ Fully Converged (Ready)" if report.can_proceed else "❌ Incomplete (Blocking)"
        lines.append(f"Gate Status: {status_str}")
        lines.append(f"Fulfilled Slots: {len(report.fulfilled_slots)}")
        lines.append(f"Missing Slots: {len(report.missing_slots)}")

    if report.missing_slots:
        lines.append("-" * 60)
        lines.append("\u3010\u5f85\u89e3\u51b3\u7684\u963b\u585e\u9879\u3011:" if is_zh else "[Blocking Missing Items]:")
        for k in report.missing_slots:
            reason = report.slot_diagnostics.get(k, "\u7f3a\u5931" if is_zh else "Missing")
            lines.append(f"  • [{k}]: {reason}")

    if report.questions:
        lines.append("-" * 60)
        lines.append("\u3010\u5411\u7528\u6237\u53d1\u8d77\u8ffd\u95ee\u7684\u6f84\u6e05\u6e05\u5355\u3011:" if is_zh else "[Clarification Inquiries for User]:")
        for idx, q in enumerate(report.questions, 1):
            q_title = f"[\u95ee\u9898 {idx}]" if is_zh else f"[Question {idx}]"
            lines.append(f"\n{q_title} {q.question}")
            reason_label = "\u539f\u56e0" if is_zh else "Rationale"
            lines.append(f"  {reason_label}: {q.why_needed}")
            if q.options:
                opt_label = "\u63a8\u8350\u9009\u9879" if is_zh else "Recommended Options"
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
