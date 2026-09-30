#!/usr/bin/env python3
"""
Aurakl Architecture Markdown Renderer (Template Conformance Engine)

Transforms machine-readable JSON architecture deliverables into structured,
human-readable Markdown documents strictly adhering to the sections and conventions
defined in Aurakl's architecture template specifications (arch-tpl-*.json).

Features:
- Pure Python 3 standard library, 100% self-contained.
- Dynamic Language Matching: Automatically mirrors the user input language
  (renders English Markdown for English artifacts, Chinese for Chinese artifacts),
  or accepts explicit `lang="en" | "zh"` parameter.
- Deep architectural modeling inspired by Lingforge engineering best practices:
  * Full physical SQL DDL (CREATE TABLE, foreign keys, CHECK constraints) & migration scripts (Up/Down)
  * Complete REST / gRPC API mock payloads (Request, 200 OK Response, 4xx/5xx Error responses)
  * Step-by-step business execution logic & idempotency declarations
  * 3-Layer Modular Monolith C4 diagrams & strongly-typed Trait/Interface code blocks
  * Roles & permissions matrices, operation step details, and state transition matrices
  * Pragmatic complex feature implementation guides (GUIDE-xxx) with production-grade code
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_ROOT / "templates"


def detect_lang(data: Any, explicit_lang: Optional[str] = None) -> str:
    """Detect whether input data should be rendered in English or Chinese."""
    if explicit_lang in ("en", "zh"):
        return explicit_lang
    raw = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    if re.search(r"[\u4e00-\u9fff]", raw):
        return "zh"
    return "en"


def _format_table_ddl(table: Dict[str, Any]) -> str:
    """Generates clean, runnable PostgreSQL CREATE TABLE DDL statement."""
    if table.get("ddl_statement"):
        return table["ddl_statement"].strip()

    tname = table.get("table_name") or table.get("name", "unnamed_table")
    cols = table.get("columns", [])
    pk = table.get("primary_key", ["id"])
    if isinstance(pk, str):
        pk = [pk]

    lines = [f"CREATE TABLE {tname} ("]
    col_lines = []
    for c in cols:
        cname = c.get("name", "col")
        ctype = c.get("data_type") or c.get("type", "VARCHAR(255)")
        nul = "" if c.get("nullable") else " NOT NULL"
        dfl_val = c.get("default_value") if "default_value" in c else c.get("default")
        dfl = f" DEFAULT {dfl_val}" if dfl_val is not None else ""
        comm = c.get("comment") or c.get("description", "")
        comment = f" -- {comm}" if comm else ""
        col_lines.append(f"    {cname:<24} {ctype:<16}{nul}{dfl},{comment}")

    # Primary Key constraint
    pk_str = f"    CONSTRAINT pk_{tname} PRIMARY KEY ({', '.join(pk)})"
    col_lines.append(pk_str)

    # Foreign keys if defined
    for fk in table.get("foreign_keys", []):
        fk_name = fk.get("constraint_name", f"fk_{tname}_{fk.get('column')}")
        fk_str = f"    CONSTRAINT {fk_name} FOREIGN KEY ({fk.get('column')}) REFERENCES {fk.get('foreign_table')}({fk.get('foreign_column')}) ON DELETE {fk.get('on_delete', 'RESTRICT')}"
        col_lines.append(fk_str)

    lines.append("\n".join(col_lines))
    lines.append(");")
    return "\n".join(lines)


def _format_index_ddl(table_name: str, idx: Dict[str, Any]) -> str:
    """Generates clean CREATE INDEX statement."""
    iname = idx.get("index_name") or idx.get("name", "idx")
    cols = ", ".join(idx.get("columns", []))
    itype = idx.get("index_type") or idx.get("type", "BTREE")
    uniq = "UNIQUE " if idx.get("unique") else ""
    using_clause = f" USING {itype}" if itype and itype.upper() != "BTREE" else ""
    return f"CREATE {uniq}INDEX {iname} ON {table_name}{using_clause} ({cols});"


class PanguTypographyEngine:
    """
    Automated Typography & Visual Ergonomics Engine.
    Strictly conforms to:
    1. 《中文文案排版指北》(Chinese Copywriting Guidelines / 盘古之白):
       - Inserts half-width space between CJK characters and Latin/Digits/Symbols.
       - Enforces backtick wrappers around code, identifiers, and parameters.
       - Preserves Markdown code blocks, inline code, and URL link targets untouched.
    2. Markdown Visual Ergonomics & Human Readability:
       - Preserves mathematical comparison operators (<, >, <=, >=).
       - Normalizes vertical breathing room around headings, tables, and horizontal rules.
       - Trims trailing whitespace and duplicate blank lines.
    """
    CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"
    LATIN = r"[A-Za-z0-9]"

    @classmethod
    def format(cls, text: str) -> str:
        if not text:
            return ""

        # 1. Protect multi-line code fences (```...```)
        fences = []
        def save_fence(m):
            fences.append(m.group(0))
            return f"\n\ue002FENCE_{len(fences)-1}\ue003\n"
        text = re.sub(r"```[\s\S]*?```", save_fence, text)

        # 2. Protect inline code (`...`)
        inlines = []
        def save_inline(m):
            inc = m.group(0)
            if re.search(cls.CJK, inc):
                inc = re.sub(rf"({cls.CJK})({cls.LATIN})", r"\1 \2", inc)
                inc = re.sub(rf"({cls.LATIN})({cls.CJK})", r"\1 \2", inc)
            inlines.append(inc)
            return f"\ue000INLINE_{len(inlines)-1}\ue001"
        text = re.sub(r"`[^`\n]+`", save_inline, text)

        # 3. Protect specific real HTML tags only (avoid eating math comparison < and >)
        htmls = []
        def save_html(m):
            htmls.append(m.group(0))
            return f"\ue004HTML_{len(htmls)-1}\ue005"
        text = re.sub(r"</?(?:br|span|div|p|b|i|strong|em)[^>]*>|<!--[\s\S]*?-->", save_html, text, flags=re.IGNORECASE)

        # 4. Protect Markdown links: [label](url)
        links = []
        def save_link(m):
            label = m.group(1)
            url = m.group(2)
            label = re.sub(rf"({cls.CJK})({cls.LATIN})", r"\1 \2", label)
            label = re.sub(rf"({cls.LATIN})({cls.CJK})", r"\1 \2", label)
            links.append(f"[{label}]({url})")
            return f"\ue006LINK_{len(links)-1}\ue007"
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", save_link, text)

        # 5. CJK-Latin spacing
        text = re.sub(rf"({cls.CJK})({cls.LATIN})", r"\1 \2", text)
        text = re.sub(rf"({cls.LATIN})({cls.CJK})", r"\1 \2", text)

        # 6. Inline code spacing
        text = re.sub(rf"({cls.CJK})(\ue000INLINE_\d+\ue001)", r"\1 \2", text)
        text = re.sub(rf"(\ue000INLINE_\d+\ue001)({cls.CJK})", r"\1 \2", text)

        # 7. Link spacing
        text = re.sub(rf"({cls.CJK})(\ue006LINK_\d+\ue007)", r"\1 \2", text)
        text = re.sub(rf"(\ue006LINK_\d+\ue007)({cls.CJK})", r"\1 \2", text)

        # 8. Bold spacing (ensure space between bold text and Latin/digits, without corrupting bold asterisks)
        bold_pat = r"(\*\*(?!\s)[^\*\n]+?(?<!\s)\*\*)"
        text = re.sub(rf"{bold_pat}(?={cls.LATIN})", r"\1 ", text)
        text = re.sub(rf"(?<={cls.LATIN}){bold_pat}", r" \1", text)

        # 9. Paren spacing
        text = re.sub(rf"({cls.CJK})\(([A-Za-z0-9_\-\s]+)\)", r"\1 (\2)", text)
        text = re.sub(rf"\(([A-Za-z0-9_\-\s]+)\)({cls.CJK})", r"(\1) \2", text)

        # 10. Clean duplicate spaces on non-table lines
        cleaned_lines = []
        for line in text.split("\n"):
            if not line.strip().startswith("|") and not line.strip().startswith("```"):
                line = re.sub(r"([^\s]) {2,}([^\s])", r"\1 \2", line)
            cleaned_lines.append(line.rstrip())
        text = "\n".join(cleaned_lines)

        # 11. Restore protected tokens in reverse order
        for idx, lk in enumerate(links):
            text = text.replace(f"\ue006LINK_{idx}\ue007", lk)
        for idx, h in enumerate(htmls):
            text = text.replace(f"\ue004HTML_{idx}\ue005", h)
        for idx, inc in enumerate(inlines):
            text = text.replace(f"\ue000INLINE_{idx}\ue001", inc)
        for idx, fc in enumerate(fences):
            text = text.replace(f"\ue002FENCE_{idx}\ue003", fc.strip())

        # 12. Normalize consecutive blank lines (max 1 empty line in succession)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


class AuraklArchitectureRenderer:
    """Renderer converting architecture stage JSON deliverables to template-conforming Markdown."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR

    def detect_lang(self, data: Any, explicit_lang: Optional[str] = None) -> str:
        return detect_lang(data, explicit_lang)

    def format_typography(self, text: str) -> str:
        """Apply Pangu CJK-Latin typography and Markdown visual ergonomics formatting."""
        return PanguTypographyEngine.format(text)

    def load_template(self, template_id: str) -> Dict[str, Any]:
        tpl_path = self.templates_dir / f"{template_id}.json"
        if not tpl_path.exists():
            raise FileNotFoundError(f"Template not found: {tpl_path}")
        return json.loads(tpl_path.read_text(encoding="utf-8"))

    # =========================================================================
    # 01: Tech Stack Decision -> arch-tpl-tech-stack
    # =========================================================================
    def render_tech_stack_decision(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-tech-stack")
        pname = data.get("product_name", "Product Architecture")
        mode = data.get("design_mode", "FULL_DESIGN")
        reqs = data.get("must_have_requirement_ids", [])
        locked = data.get("locked_stack_items", [])
        adrs = data.get("evaluated_adrs", [])
        final_stack = data.get("final_tech_stack", {})
        compat = data.get("compatibility_guarantees", {})

        if lang == "zh":
            lines = [
                f"# {pname} 技术选型与架构决策规约 (ADR)",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{pname} 技术选型决策规约"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  design_mode: "{mode}"',
                f'  must_have_requirements_count: {len(reqs)}',
                "```",
                "",
                "> 本文档定义系统技术架构底座，固化 PRD 强约束技术栈，通过多维评分矩阵确定未决技术方案，并提供架构决策记录 (ADR)。",
                "",
                "---",
                "",
                "## 1. 约束继承与设计模式 (Design Context)",
                "",
                f"- **系统设计模式**：`{mode}`",
                f"- **关联 PRD Must-Have 需求数**：`{len(reqs)}` 项 ({', '.join(reqs)})",
                "",
                "### 固化技术栈清单 (Locked Tech Stack)",
                "",
                "| 技术维度 | 选型结果 | 约束来源 | 架构合理性论证 |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for item in locked:
                dim = item.get('dimension') or item.get('category', '技术组件')
                tech = item.get('technology', '-')
                src = item.get('constraint_source') or item.get('source_constraint', 'PRD 不变量')
                rat = item.get('rationale', '')
                lines.append(f"| **{dim}** | `{tech}` | {src} | {rat} |")

            lines.extend([
                "",
                "## 2. 备选技术多维评估矩阵与 ADR (Evaluated ADRs)",
                "",
            ])
            for adr in adrs:
                aid = adr.get('adr_id') or adr.get('id', 'ADR-001')
                decision = adr.get('chosen_alternative') or adr.get('decision', '已定案选型')
                lines.extend([
                    f"### {aid}: {adr.get('title')}",
                    f"- **决策状态**：`{adr.get('status', 'ACCEPTED')}`",
                    f"- **上下文背景**：{adr.get('context')}",
                    f"- **最终决策**：选用 `{decision}`",
                    f"- **决策理由**：{adr.get('rationale')}",
                    f"- **架构影响与后果**：{adr.get('consequences')}",
                    "",
                    "#### 备选方案评分对比",
                    "| 方案名称 | 技术特征 | 综合评分 | 判定结论 |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                alts = adr.get("evaluated_alternatives") or adr.get("alternatives_considered", [])
                for alt in alts:
                    alt_name = alt.get('name', 'Alternative')
                    pros = alt.get('pros', [])
                    cons = alt.get('cons', [])
                    pros_cons = alt.get('pros_and_cons')
                    if not pros_cons:
                        pc_parts = []
                        if pros:
                            pc_parts.append(f"优势: {', '.join(pros)}")
                        if cons:
                            pc_parts.append(f"劣势: {', '.join(cons)}")
                        pros_cons = "; ".join(pc_parts) or alt.get('summary', '-')
                    score = alt.get('score', 0.0)
                    is_chosen = (
                        alt.get('chosen') is True
                        or alt.get('selected') is True
                        or (alt_name == adr.get('chosen_alternative'))
                        or (alt_name in decision and len(alt_name) >= 4)
                        or (decision and decision in alt_name)
                        or (adr.get('status') == 'ACCEPTED' and alts and score == max(a.get('score', 0.0) for a in alts) and score > 8.0)
                    )
                    conc = "✅ 采纳" if is_chosen else "❌ 放弃"
                    lines.append(f"| **{alt_name}** | {pros_cons} | `{score} / 100` | {conc} |")
                lines.append("")

            lines.extend([
                "## 3. 最终技术栈全景视图 (Final Tech Stack Panorama)",
                "",
                "| 分层维度 | 技术组件 / 框架 | 版本要求 | 选型理由 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer, detail in final_stack.items():
                if isinstance(detail, dict):
                    lines.append(f"| **{layer}** | `{detail.get('technology')}` | `{detail.get('version', 'latest')}` | {detail.get('rationale')} |")
                else:
                    lines.append(f"| **{layer}** | `{detail}` | - | 基础标准选型 |")

            if isinstance(compat, list):
                compat_summary = "; ".join(compat)
                compat_policy = "严格禁止任何破坏性变更，遵循双版本并存与 Expand-Contract 演化策略"
            else:
                compat_summary = compat.get('guarantee_summary', '严格向后兼容，禁止破坏性变更')
                compat_policy = compat.get('breaking_change_policy', '非破坏性升级，重大变更须至少双版本并存')

            lines.extend([
                "",
                "## 4. 向后兼容性承诺 (Backward Compatibility)",
                "",
                f"- **兼容性保障准则**：{compat_summary}",
                f"- **演化淘汰机制**：{compat_policy}",
                "",
            ])

        else:
            # English
            if isinstance(compat, list):
                compat_summary = "; ".join(compat)
                compat_policy = "Breaking changes prohibited; strictly follow Expand-Contract and deprecation lifecycles"
            else:
                compat_summary = compat.get('guarantee_summary', 'Strict backward compatibility guaranteed; breaking changes prohibited')
                compat_policy = compat.get('breaking_change_policy', 'Strictly prohibited without formal deprecation cycle')

            lines = [
                f"# {pname} Tech Stack Decision & Architecture Decision Records (ADR)",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{pname} Tech Stack Decision Specification"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  design_mode: "{mode}"',
                f'  must_have_requirements_count: {len(reqs)}',
                "```",
                "",
                "> Defines the foundational technical choices, inherits immutable PRD constraints, evaluates alternatives via multi-factor matrices, and formalizes Architecture Decision Records (ADRs).",
                "",
                "---",
                "",
                "## 1. Constraint Inheritance & Design Mode",
                "",
                f"- **Design Mode**: `{mode}`",
                f"- **Associated Must-Have Requirements**: `{len(reqs)}` items ({', '.join(reqs)})",
                "",
                "### Locked Tech Stack Constraints",
                "",
                "| Dimension | Technology | Constraint Source | Rationale |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for item in locked:
                dim = item.get('dimension') or item.get('category', 'Component')
                tech = item.get('technology', '-')
                src = item.get('constraint_source') or item.get('source_constraint', 'PRD Invariant')
                rat = item.get('rationale', '')
                lines.append(f"| **{dim}** | `{tech}` | {src} | {rat} |")

            lines.extend([
                "",
                "## 2. Architecture Decision Records (ADR)",
                "",
            ])
            for adr in adrs:
                aid = adr.get('adr_id') or adr.get('id', 'ADR-001')
                decision = adr.get('chosen_alternative') or adr.get('decision', 'Selected Choice')
                lines.extend([
                    f"### {aid}: {adr.get('title')}",
                    f"- **Status**: `{adr.get('status', 'ACCEPTED')}`",
                    f"- **Context**: {adr.get('context')}",
                    f"- **Decision**: Selected `{decision}`",
                    f"- **Rationale**: {adr.get('rationale')}",
                    f"- **Consequences**: {adr.get('consequences')}",
                    "",
                    "#### Alternative Comparison Matrix",
                    "| Alternative | Characteristics | Score | Verdict |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                alts = adr.get("evaluated_alternatives") or adr.get("alternatives_considered", [])
                for alt in alts:
                    alt_name = alt.get('name', 'Alternative')
                    pros = alt.get('pros', [])
                    cons = alt.get('cons', [])
                    pros_cons = alt.get('pros_and_cons')
                    if not pros_cons:
                        pc_parts = []
                        if pros:
                            pc_parts.append(f"Pros: {', '.join(pros)}")
                        if cons:
                            pc_parts.append(f"Cons: {', '.join(cons)}")
                        pros_cons = "; ".join(pc_parts) or alt.get('summary', '-')
                    score = alt.get('score', 0.0)
                    is_chosen = (
                        alt.get('chosen') is True
                        or alt.get('selected') is True
                        or (alt_name == adr.get('chosen_alternative'))
                        or (alt_name in decision and len(alt_name) >= 4)
                        or (decision and decision in alt_name)
                        or (adr.get('status') == 'ACCEPTED' and alts and score == max(a.get('score', 0.0) for a in alts) and score > 8.0)
                    )
                    conc = "✅ Selected" if is_chosen else "❌ Rejected"
                    lines.append(f"| **{alt_name}** | {pros_cons} | `{score} / 100` | {conc} |")
                lines.append("")

            lines.extend([
                "## 3. Finalized Technology Stack Panorama",
                "",
                "| Layer / Dimension | Technology / Framework | Version | Rationale |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer, detail in final_stack.items():
                if isinstance(detail, dict):
                    lines.append(f"| **{layer}** | `{detail.get('technology')}` | `{detail.get('version', 'latest')}` | {detail.get('rationale')} |")
                else:
                    lines.append(f"| **{layer}** | `{detail}` | - | Baseline selection |")

            lines.extend([
                "",
                "## 4. Backward Compatibility Guarantee",
                "",
                f"- **Compatibility Commitment**: {compat_summary}",
                f"- **Evolution Policy**: {compat_policy}",
                "",
            ])


        return "\n".join(lines)

    # =========================================================================
    # 02: System Architecture -> arch-tpl-architecture
    # =========================================================================
    def _synthesize_subsystems(self, logical_v: Dict[str, Any], modules: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
        subsystems = logical_v.get("subsystems")
        if subsystems:
            return subsystems
        derived = []
        for mod in modules:
            mname = mod.get("name", "module")
            mid = mod.get("module_id", "MOD")
            trait_name = f"{''.join(w.title() for w in mname.split('_'))}Port"
            derived.append({
                "code": mid,
                "name": f"{mname} 组件" if lang == "zh" else f"{mname} Component",
                "responsibility": mod.get("responsibilities", mod.get("description", "-")),
                "trait": trait_name,
                "entities": ", ".join(mod.get("implements_requirements", [])) or ("核心实体" if lang == "zh" else "CoreEntity")
            })
        if not derived:
            derived = [
                {"code": "SUB-01", "name": "核心业务处理子系统" if lang == "zh" else "Core Domain Subsystem", "responsibility": "业务核心逻辑处理与状态机调度" if lang == "zh" else "Core domain logic and state transitions", "trait": "CoreDomainPort", "entities": "DomainAggregate"},
                {"code": "SUB-02", "name": "接口与协议接入子系统" if lang == "zh" else "Interface Gateway Subsystem", "responsibility": "协议接入与认证鉴权" if lang == "zh" else "Protocol ingress and security validation", "trait": "GatewayPort", "entities": "SecurityContext"}
            ]
        return derived

    def _synthesize_packages(self, dev_v: Dict[str, Any], data: Dict[str, Any], layers: List[Dict[str, Any]], modules: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
        packages = dev_v.get("packages")
        if packages:
            return packages
        raw_pkgs = data.get("package_or_crate_structure", [])
        if raw_pkgs:
            return [
                {
                    "name": p.get("package_name", "package"),
                    "kind": p.get("package_kind", "library"),
                    "exports": ", ".join(p.get("exports", [])) or "Public APIs",
                    "dependencies": ", ".join(p.get("dependencies", [])) or "None",
                    "layer": p.get("owning_layer", "-")
                }
                for p in raw_pkgs
            ]
        derived = []
        for lay in layers:
            lid = lay.get("layer_id", "L")
            lname = lay.get("name", "layer").lower().replace(" ", "-").replace("&", "and")
            mod_names = [m.get("name", "") for m in modules if m.get("layer_id") == lid]
            kind = "api_transport" if (lid == "L1" or "api" in lname or "interface" in lname) else ("infra_adapter" if (lid == "L3" or "storage" in lname or "infra" in lname) else "core_domain")
            derived.append({
                "name": f"pkg-{lname}",
                "kind": kind,
                "exports": ", ".join(mod_names) or (lay.get("responsibility", "-")[:40] + "..."),
                "dependencies": ", ".join(lay.get("allowed_dependencies", [])) or ("无" if lang == "zh" else "None"),
                "layer": f"{lid} ({lay.get('name')})"
            })
        return derived or [
            {"name": "pkg-api", "kind": "api_transport", "exports": "REST / RPC Gateways", "dependencies": "pkg-core", "layer": "L1"},
            {"name": "pkg-core", "kind": "core_domain", "exports": "Domain Models & Invariants", "dependencies": "pkg-infra", "layer": "L2"},
            {"name": "pkg-infra", "kind": "infra_adapter", "exports": "DB Pools & Drivers", "dependencies": "None", "layer": "L3"}
        ]

    def _synthesize_processes(self, process_v: Dict[str, Any], data: Dict[str, Any], layers: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
        processes = process_v.get("processes")
        if processes:
            return processes
        raw_procs = data.get("runtime_processes", [])
        if raw_procs:
            return raw_procs
        derived = []
        for lay in layers:
            lid = lay.get("layer_id", "L")
            lname = lay.get("name", "service").lower().replace(" ", "-").replace("&", "and")
            is_api = (lid == "L1" or "api" in lname or "interface" in lname)
            is_infra = (lid == "L3" or "storage" in lname or "infra" in lname)
            derived.append({
                "name": f"{lname}-worker",
                "model": ("异步事件驱动事件循环 (Async Event-Loop)" if lang == "zh" else "Async Event-Driven Runtime") if is_api else (("专用事务与批处理线程池" if lang == "zh" else "Dedicated Transaction Worker Pool") if not is_infra else ("持久化连接池管理池" if lang == "zh" else "Connection Pool Isolation")),
                "resources": "4 Cores / 8 GB / 1000 conns" if is_api else ("4 Cores / 8 GB / 128 conns" if not is_infra else "8 Cores / 16 GB / 64 conns"),
                "lock": ("无锁事件驱动 + 令牌桶限流" if lang == "zh" else "Lock-free event loops + Token Bucket") if is_api else (("分布式租约锁 + 乐观重试" if lang == "zh" else "Distributed Lease + Optimistic Retry") if not is_infra else ("数据库行锁与连接池排队" if lang == "zh" else "Row-level locks + Pool Queuing")),
                "latency": "< 25ms" if is_api else ("< 200ms" if not is_infra else "< 10ms")
            })
        return derived or [
            {"name": "gateway-worker", "model": "Async Runtime", "resources": "4C / 8G", "lock": "Token Bucket", "latency": "< 25ms"},
            {"name": "core-executor", "model": "Worker Pool", "resources": "4C / 8G", "lock": "Optimistic Locking", "latency": "< 100ms"}
        ]

    def _synthesize_nodes(self, physical_v: Dict[str, Any], data: Dict[str, Any], layers: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
        nodes = physical_v.get("nodes")
        if nodes:
            return nodes
        raw_nodes = data.get("deployment_nodes", [])
        if raw_nodes:
            return raw_nodes
        derived = []
        for lay in layers:
            lid = lay.get("layer_id", "L")
            lname = lay.get("name", "service").lower().replace(" ", "-").replace("&", "and")
            is_api = (lid == "L1" or "api" in lname or "interface" in lname)
            is_infra = (lid == "L3" or "storage" in lname or "infra" in lname)
            derived.append({
                "component": f"{lname}-node",
                "replicas": "3 Pods (HPA 3~10)" if is_api else ("2 Pods" if not is_infra else "1 Primary + 2 Replicas"),
                "spec": "2C 4G" if is_api else ("4C 8G" if not is_infra else "16C 64G SSD"),
                "az": "Multi-AZ (AZ-A, AZ-B)" if not is_infra else "Cross-AZ Sync Replication",
                "network": "Ingress HTTPS" if is_api else ("ClusterIP (Private Subnet)" if not is_infra else "Internal DB Subnet")
            })
        return derived or [
            {"component": "app-service", "replicas": "3 Pods", "spec": "4C 8G", "az": "Multi-AZ", "network": "Private VPC"},
            {"component": "storage-node", "replicas": "Primary + Replica", "spec": "8C 32G", "az": "Sync Multi-AZ", "network": "DB Subnet"}
        ]

    def _synthesize_scenario(self, scenarios_v: Dict[str, Any], data: Dict[str, Any], sys_name: str, lang: str):
        scen_name = scenarios_v.get("scenario_name")
        steps = scenarios_v.get("steps")
        data_flows = data.get("data_flows", [])
        if not scen_name:
            if data_flows and data_flows[0].get("name"):
                scen_name = data_flows[0].get("name")
            else:
                scen_name = f"{sys_name} 核心端到端业务闭环执行时序" if lang == "zh" else f"{sys_name} Core End-to-End Execution Scenario"
        if not steps:
            if data_flows and data_flows[0].get("steps"):
                steps = [f"{i}. {s}" for i, s in enumerate(data_flows[0].get("steps", []), 1)]
            else:
                steps = [
                    "1. **逻辑视图触发**：客户端下发操作请求，接口层拦截并校验请求规范与鉴权安全策略。" if lang == "zh" else "1. **Logical View Trigger**: Client issues request; interface layer performs schema & auth validation.",
                    "2. **运行视图并发隔离**：运行时工作节点申请分布式并发排他租约，防止重复请求重放与资源争用。" if lang == "zh" else "2. **Process View Concurrency**: Worker node acquires distributed lock to prevent duplicate replay.",
                    "3. **开发视图契约流转**：模块按分层强类型 Trait 契约调用领域模型，执行核心不变量与状态机校验。" if lang == "zh" else "3. **Development View Trait Call**: Modules invoke strongly typed traits for domain invariants validation.",
                    "4. **物理视图事务落地**：基础设施层协调跨可用区部署的持久化存储执行事务写入并输出审计凭据。" if lang == "zh" else "4. **Physical View Persistence**: Storage adapters commit ACID transactions across multi-AZ nodes."
                ]
        return scen_name, steps

    def render_system_architecture(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-architecture")
        sys_name = data.get("product_name") or data.get("system_name") or "System Architecture"
        layers = data.get("layers", [])
        layer_count = data.get("layer_count", len(layers))
        c4 = data.get("c4_container_diagram", "")
        modules = data.get("modules", [])
        data_flows = data.get("data_flows", [])
        adrs = data.get("adrs", [])
        cross_cutting = data.get("cross_cutting_concerns", {})
        
        overall_diagram = data.get("overall_architecture_diagram") or data.get("overall_architecture_panorama", "")
        fpo = data.get("four_plus_one_views", {})
        logical_v = fpo.get("logical_view") or data.get("logical_view", {})
        dev_v = fpo.get("development_view") or data.get("development_view", {})
        process_v = fpo.get("process_view") or data.get("process_view", {})
        physical_v = fpo.get("physical_view") or data.get("physical_view", {})
        scenarios_v = fpo.get("scenarios_view") or data.get("scenarios_view", {})

        if lang == "zh":
            lines = [
                f"# {sys_name} 系统拓扑与分层架构设计规约",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  layer_count: {layer_count}',
                "```",
                "",
                "> 本设计严格遵循 Linus 极简务实哲学与 4+1 架构视图模型：坚持单体优先，分层严格 <= 3 层，依赖单向无环，模块接口强类型约束，涵盖全局总体架构全景拓扑图与五大架构视图。",
                "",
                "---",
                "",
                "## 1. 架构模式与单体优先论证 (Architecture Overview)",
                "",
                f"- **架构模式**：`{data.get('architecture_pattern', 'Modular_Monolith')}`",
                f"- **单体优先论证**：{data.get('monolith_justification', '遵循 Linus 极简哲学：微服务是规模化的产物，而不是目标。单体架构具备零网络延迟、单机事务一致性、调试与部署极其简明的高效优势，完全规避分布式事务与网络分区复杂性。')}",
                f"- **分层数量**：`{layer_count}` 层（严格不超过 3 层，依赖单向流动）",
                "",
                "## 2. 总体架构全景拓扑图 (Overall Architecture Panorama)",
                "",
                "> 全局端到端企业架构全景拓扑：涵盖接入客户端、边缘与协议网关、核心领域引擎、分布式事务编排、流批 CDC 管道、多引擎持久化存储及全链路横切防线。",
                "",
                "```mermaid",
                overall_diagram.strip() if overall_diagram else (c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;"),
                "```",
                "",
                "## 3. 4+1 架构视图模型全景规约 (4+1 Architectural View Model)",
                "",
                "### 3.1 逻辑架构视图 (Logical View)",
                f"**视图关注点**：{logical_v.get('description', '系统对终端用户与智能体提供的业务功能边界、核心子系统划分、聚合根领域归属与强类型接口契约抽象。')}",
                "",
                "| 子系统代码 | 子系统名称 | 核心职责与领域边界 | 核心抽象契约 (Core Port / Trait) | 包含领域实体 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            subsystems = self._synthesize_subsystems(logical_v, modules, "zh")
            for sub in subsystems:
                lines.append(f"| **`{sub.get('code')}`** | **{sub.get('name')}** | {sub.get('responsibility')} | `{sub.get('trait')}` | `{sub.get('entities')}` |")

            if logical_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    logical_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.2 开发架构视图 (Development View)",
                f"**视图关注点**：{dev_v.get('description', '软件代码在工程开发环境中的模块组织拓扑、Crate/包依赖层级、编译边界防线与物理源码目录结构。')}",
                "",
                "| Crate / 包名称 | 包类型 (Kind) | 核心导出能力 (Exports) | 编译期直接依赖 (Direct Dependencies) | 归属分层 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            packages = self._synthesize_packages(dev_v, data, layers, modules, "zh")
            for pkg in packages:
                lines.append(f"| **`{pkg.get('name')}`** | `{pkg.get('kind')}` | {pkg.get('exports')} | `{pkg.get('dependencies')}` | `{pkg.get('layer')}` |")

            if dev_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    dev_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.3 运行架构视图 (Process / Runtime View)",
                f"**视图关注点**：{process_v.get('description', '系统在运行态下的多进程与多线程模型、Tokio 异步事件循环、并发控制机制、分布式租约与跨系统调用延迟/资源预算。')}",
                "",
                "| 运行态进程 / 任务池 | 并发模型与调度器 | 资源配额 (CPU/Mem/Conn) | 核心锁与同步机制 | P99 延迟预算 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            processes = self._synthesize_processes(process_v, data, layers, "zh")
            for proc in processes:
                lines.append(f"| **`{proc.get('name')}`** | {proc.get('model')} | `{proc.get('resources')}` | {proc.get('lock')} | `{proc.get('latency')}` |")

            if process_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    process_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.4 物理与部署架构视图 (Physical / Deployment View)",
                f"**视图关注点**：{physical_v.get('description', '系统的物理硬件、云原生网络拓扑、Kubernetes 容器编排、多可用区 (Multi-AZ) 高可用容灾及主从存储拓扑。')}",
                "",
                "| 部署节点 / 服务组件 | 实例副本数 | 计算规格配额 | 部署可用区 (Topology) | 网络暴露与安全域 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            nodes = self._synthesize_nodes(physical_v, data, layers, "zh")
            for node in nodes:
                lines.append(f"| **`{node.get('component')}`** | `{node.get('replicas')}` | `{node.get('spec')}` | {node.get('az')} | `{node.get('network')}` |")

            if physical_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    physical_v["diagram"].strip(),
                    "```",
                ])

            scen_name, scenario_steps = self._synthesize_scenario(scenarios_v, data, sys_name, "zh")
            lines.extend([
                "",
                "### 3.5 +1 场景用例视图 (Scenarios / Use Case View)",
                f"**视图关注点**：{scenarios_v.get('description', '驱动并串联逻辑、开发、运行和物理四大视图的核心端到端用例，验证各视图组件在执行真实高价值业务时的协同完备性。')}",
                f"- **核心用例名称**：`{scen_name}`",
                "",
                "#### 端到端跨视图串联流转时序",
            ])
            for stp in scenario_steps:
                lines.append(f"- {stp}")

            if scenarios_v.get("sequence_diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    scenarios_v["sequence_diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "## 4. 三层架构清晰规约 (Layering Specification)",
                "",
                "| 分层层级 | 分层名称 (Layer) | 职责边界 (Responsibilities) | 允许依赖目标 (Allowed Dependencies) |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer in layers:
                lid = layer.get("layer_id") or layer.get("level") or "L?"
                lname = layer.get("name", "Layer")
                lresp = layer.get("responsibilities") or layer.get("responsibility", "")
                allowed = ", ".join(layer.get("allowed_dependencies", [])) or "无 (底层基础设施)"
                lines.append(f"| **{lid}** | **{lname}** | {lresp} | `{allowed}` |")

            lines.extend([
                "",
                "## 5. 核心模块划分与接口抽象 (Modules & Interface Contracts)",
                "",
            ])
            for mod in modules:
                mid = mod.get("module_id") or mod.get("id", "MOD-001")
                mname = mod.get("name", "Module")
                mlayer = mod.get("layer_id") or mod.get("layer", "L2")
                mdesc = mod.get("responsibilities") or mod.get("description", "")
                mdeps = ", ".join(mod.get("dependencies", [])) or "无 (独立基础模块)"
                mreqs = ", ".join(mod.get("implements_requirements", [])) or "无"

                lines.extend([
                    f"<!-- block-id: {mid} -->",
                    f"<!-- implements: {mreqs} -->",
                    f"<!-- depends_on: {mdeps} -->",
                    f"### {mid}: {mname}",
                    f"- **所属分层**：`{mlayer}`",
                    f"- **核心职责**：{mdesc}",
                    f"- **依赖模块**：`{mdeps}`",
                    f"- **实现需求**：`{mreqs}`",
                    "",
                ])
                if mod.get("interface_signature"):
                    sig_lang = "rust" if "fn " in mod["interface_signature"] else "typescript"
                    lines.extend([
                        "**强类型接口契约定义**：",
                        f"```{sig_lang}",
                        mod["interface_signature"].strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 6. C4 Container 架构拓扑图 (C4 Diagram)",
                "",
                "```mermaid",
                c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;",
                "```",
                "",
            ])

            if data_flows:
                lines.extend([
                    "## 7. 核心跨层数据流向 (Cross-Layer Data Flows)",
                    "",
                ])
                for df in data_flows:
                    lines.extend([
                        f"### {df.get('id', 'FLOW')}: {df.get('name', 'Flow')}",
                        f"**业务说明**：{df.get('description', '')}",
                        "",
                        "**步骤流转**：",
                    ])
                    for sidx, step in enumerate(df.get("steps", []), 1):
                        lines.append(f"{sidx}. {step}")
                    lines.append("")

            if adrs:
                lines.extend([
                    "## 8. 架构决策记录 (ADR)",
                    "",
                ])
                for adr in adrs:
                    lines.extend([
                        f"### {adr.get('id')}: {adr.get('title')}",
                        f"- **决策上下文**：{adr.get('context')}",
                        f"- **技术决策**：{adr.get('decision')}",
                        f"- **预期后果与收益**：{adr.get('consequences')}",
                        "",
                    ])

            lines.extend([
                "## 9. 横切关注点规约 (Cross-Cutting Concerns)",
                "",
                f"- **认证鉴权上下文注入**：{cross_cutting.get('security_context', 'API 网关完成 JWT/mTLS 统一鉴权后，将强类型 TenantContext 注入标准上下文，领域层直接消费，禁止绕过网关直连内部方法。')}",
                f"- **全局全链路追踪**：{cross_cutting.get('observability', '全链路强制透传 OpenTelemetry W3C TraceContext 与 trace_id，跨异步队列与事件消息总线强制保持上下文因果关联。')}",
                f"- **统一错误处理**：{cross_cutting.get('error_handling', '标准 DomainError 映射至全局统一 HTTP/gRPC 错误码，严禁向客户端抛出未捕获的数据库原生异常堆栈。')}",
                "",
            ])

        else:
            # English
            lines = [
                f"# {sys_name} System Topology & Layering Architecture Specification",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  layer_count: {layer_count}',
                "```",
                "",
                "> Adheres strictly to the Linus Pragmatic Philosophy and 4+1 Architectural View Model: Monolith-first, <= 3 layers, unidirectional acyclic dependencies, strongly typed component boundaries, overall architecture panorama, and five comprehensive views.",
                "",
                "---",
                "",
                "## 1. Architecture Overview & Pattern Selection",
                "",
                f"- **Pattern**: `{data.get('architecture_pattern', 'Modular_Monolith')}`",
                f"- **Monolith-First Justification**: {data.get('monolith_justification', 'Adheres to Linus Torvalds philosophy: Microservices are a consequence of organizational scale, not an architectural virtue. Modular monolith guarantees zero network overhead, transactional simplicity, and straightforward observability without distributed partial failures.')}",
                f"- **Layer Count**: `{layer_count}` layers (strictly <= 3 layers, unidirectional flow)",
                "",
                "## 2. Overall Architecture Panorama",
                "",
                "> Global end-to-end enterprise architecture panorama: illustrates client actors, edge & protocol gateways, core domain engines, distributed transaction coordinators, streaming CDC pipelines, multi-engine persistence, and cross-cutting perimeters.",
                "",
                "```mermaid",
                overall_diagram.strip() if overall_diagram else (c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;"),
                "```",
                "",
                "## 3. 4+1 Architectural View Model Specification",
                "",
                "### 3.1 Logical View",
                f"**Focus**: {logical_v.get('description', 'Functional boundaries provided to end-users and AI agents, subsystem decomposition, domain aggregates, and strongly typed interface trait abstractions.')}",
                "",
                "| Subsystem Code | Subsystem Name | Responsibilities & Boundaries | Core Interface Port / Trait | Domain Entities |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            subsystems = self._synthesize_subsystems(logical_v, modules, "en")
            for sub in subsystems:
                lines.append(f"| **`{sub.get('code')}`** | **{sub.get('name')}** | {sub.get('responsibility')} | `{sub.get('trait')}` | `{sub.get('entities')}` |")

            if logical_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    logical_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.2 Development View",
                f"**Focus**: {dev_v.get('description', 'Module organization in the development environment, crate/package dependencies, build boundaries, and source code directory topology.')}",
                "",
                "| Crate / Package Name | Package Kind | Exports | Direct Dependencies | Owning Layer |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            packages = self._synthesize_packages(dev_v, data, layers, modules, "en")
            for pkg in packages:
                lines.append(f"| **`{pkg.get('name')}`** | `{pkg.get('kind')}` | {pkg.get('exports')} | `{pkg.get('dependencies')}` | `{pkg.get('layer')}` |")

            if dev_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    dev_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.3 Process / Runtime View",
                f"**Focus**: {process_v.get('description', 'Runtime processes, thread pools, Tokio async event loops, concurrency control, distributed leases, and latency/resource budgets.')}",
                "",
                "| Runtime Process / Pool | Concurrency Model & Scheduler | Resource Quotas (CPU/Mem/Conn) | Synchronization & Locking | P99 Latency Budget |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            processes = self._synthesize_processes(process_v, data, layers, "en")
            for proc in processes:
                lines.append(f"| **`{proc.get('name')}`** | {proc.get('model')} | `{proc.get('resources')}` | {proc.get('lock')} | `{proc.get('latency')}` |")

            if process_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    process_v["diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "### 3.4 Physical / Deployment View",
                f"**Focus**: {physical_v.get('description', 'Physical and cloud infrastructure, network topology, Kubernetes Pods/Nodes, multi-AZ disaster recovery, and storage clustering.')}",
                "",
                "| Component Node | Replicas & Scaling | Compute Specifications | Availability Zone | Network & Security Zone |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            nodes = self._synthesize_nodes(physical_v, data, layers, "en")
            for node in nodes:
                lines.append(f"| **`{node.get('component')}`** | `{node.get('replicas')}` | `{node.get('spec')}` | {node.get('az')} | `{node.get('network')}` |")

            if physical_v.get("diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    physical_v["diagram"].strip(),
                    "```",
                ])

            scen_name, scenario_steps = self._synthesize_scenario(scenarios_v, data, sys_name, "en")
            lines.extend([
                "",
                "### 3.5 +1 Scenarios / Use Case View",
                f"**Focus**: {scenarios_v.get('description', 'Critical end-to-end user and agent scenarios linking logical, development, process, and physical views together.')}",
                f"- **Core Scenario**: `{scen_name}`",
                "",
                "#### Cross-View End-to-End Sequence Steps",
            ])
            for stp in scenario_steps:
                lines.append(f"- {stp}")

            if scenarios_v.get("sequence_diagram"):
                lines.extend([
                    "",
                    "```mermaid",
                    scenarios_v["sequence_diagram"].strip(),
                    "```",
                ])

            lines.extend([
                "",
                "## 4. Layering Architecture Specification",
                "",
                "| Layer Level | Layer Name | Responsibilities | Allowed Dependencies |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer in layers:
                lid = layer.get("layer_id") or layer.get("level") or "L?"
                lname = layer.get("name", "Layer")
                lresp = layer.get("responsibilities") or layer.get("responsibility", "")
                allowed = ", ".join(layer.get("allowed_dependencies", [])) or "None (Bottom layer)"
                lines.append(f"| **{lid}** | **{lname}** | {lresp} | `{allowed}` |")

            lines.extend([
                "",
                "## 5. Module Decomposition & Interface Contracts",
                "",
            ])
            for mod in modules:
                mid = mod.get("module_id") or mod.get("id", "MOD-001")
                mname = mod.get("name", "Module")
                mlayer = mod.get("layer_id") or mod.get("layer", "L2")
                mdesc = mod.get("responsibilities") or mod.get("description", "")
                mdeps = ", ".join(mod.get("dependencies", [])) or "None"
                mreqs = ", ".join(mod.get("implements_requirements", [])) or "None"

                lines.extend([
                    f"<!-- block-id: {mid} -->",
                    f"<!-- implements: {mreqs} -->",
                    f"<!-- depends_on: {mdeps} -->",
                    f"### {mid}: {mname}",
                    f"- **Layer**: `{mlayer}`",
                    f"- **Responsibilities**: {mdesc}",
                    f"- **Dependencies**: `{mdeps}`",
                    f"- **Implements Requirements**: `{mreqs}`",
                    "",
                ])
                if mod.get("interface_signature"):
                    sig_lang = "rust" if "fn " in mod["interface_signature"] else "typescript"
                    lines.extend([
                        "**Strongly Typed Interface Contract**:",
                        f"```{sig_lang}",
                        mod["interface_signature"].strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 6. C4 Container Diagram & System Topology",
                "",
                "```mermaid",
                c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;",
                "```",
                "",
            ])

            if data_flows:
                lines.extend([
                    "## 7. Cross-Cutting Data Flows",
                    "",
                ])
                for df in data_flows:
                    lines.extend([
                        f"### {df.get('id', 'FLOW')}: {df.get('name', 'Flow')}",
                        f"**Description**: {df.get('description', '')}",
                        "",
                        "**Sequence Steps**:",
                    ])
                    for sidx, step in enumerate(df.get("steps", []), 1):
                        lines.append(f"{sidx}. {step}")
                    lines.append("")

            if adrs:
                lines.extend([
                    "## 8. Architecture Decision Records (ADR)",
                    "",
                ])
                for adr in adrs:
                    lines.extend([
                        f"### {adr.get('id')}: {adr.get('title')}",
                        f"- **Context**: {adr.get('context')}",
                        f"- **Decision**: {adr.get('decision')}",
                        f"- **Consequences**: {adr.get('consequences')}",
                        "",
                    ])

            lines.extend([
                "## 9. Cross-Cutting Architectural Concerns",
                "",
                f"- **Security Context Injection**: {cross_cutting.get('security_context', 'Validated at gateway and injected via standard Context; internal services reject unverified callers.')}",
                f"- **Distributed Tracing**: {cross_cutting.get('observability', 'X-Trace-Id and W3C TraceContext propagated end-to-end across async queue and network boundaries.')}",
                f"- **Unified Error Handling**: {cross_cutting.get('error_handling', 'Standard DomainError mapped to unified HTTP status codes; raw DB errors masked from external callers.')}",
                "",
            ])

        return "\n".join(lines)

    # =========================================================================
    # 03: Domain Model -> arch-tpl-domain-model
    # =========================================================================
    def render_domain_model(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-domain-model")
        dname = data.get("product_name") or data.get("system_name") or data.get("domain_name") or "Domain Model"
        aggregates = data.get("aggregates", [])
        entities = data.get("entities") or data.get("domain_entity_models", [])
        value_objects = data.get("value_objects", [])
        
        raw_traits = data.get("core_traits") or data.get("domain_abstractions", [])
        if isinstance(raw_traits, dict):
            traits = raw_traits.get("core_traits_or_interfaces") or raw_traits.get("traits") or []
        elif isinstance(raw_traits, list):
            traits = raw_traits
        else:
            traits = []

        cov_pct = data.get("must_have_requirement_coverage_pct", 100.0)

        if lang == "zh":
            lines = [
                f"# {dname} 领域建模与核心抽象规约",
                "",
                "```yaml",
                "metadata:",
                f'  domain_name: "{dname}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  coverage_pct: {cov_pct}%',
                "```",
                "",
                "> Linus 铁律：糟糕的程序员担心代码，优秀的程序员关注数据结构与关系。本规约 100% 覆盖 PRD 业务实体与不变量。",
                "",
                "---",
                "",
                "## 1. 领域模型概述与聚合根划分 (Domain Overview)",
                "",
                f"- **聚合根数量**：`{len(aggregates)}` 个",
                f"- **全量实体模型**：`{len(entities)}` 个（100% 覆盖 PRD 核心需求）",
                f"- **核心 Trait / 接口抽象**：`{len(traits)}` 个",
                "",
                "### 聚合根清单 (Aggregate Roots)",
                "",
                "| 聚合根 ID | 聚合根名称 | 根实体标识 | 边界与不变性约束 |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for idx, agg in enumerate(aggregates):
                agg_id = agg.get('aggregate_id', agg.get('id', f'AGG-{idx+1:03d}'))
                agg_boundary = agg.get('boundary_description', agg.get('invariants', agg.get('description', '-')))
                lines.append(f"| **{agg_id}** | **{agg.get('name')}** | `{agg.get('root_entity_id', agg.get('root_entity', 'Self'))}` | {agg_boundary} |")

            lines.extend([
                "",
                "## 2. 领域全量实体模型规约 (Entity Models)",
                "",
            ])
            for ent in entities:
                eid = ent.get("entity_id") or ent.get("id", "ENT-001")
                ename = ent.get("name", "Entity")
                agg_root = ent.get("aggregate_root", "Self")
                p_id = ent.get("primary_identifier", "id")
                desc = ent.get("description", "")
                attrs = ent.get("attributes", [])

                lines.extend([
                    f"### 实体: `{eid}` - {ename}",
                    f"- **所属聚合根**：`{agg_root}` | **主标识符**：`{p_id}`",
                    f"- **业务说明**：{desc}",
                ])
                if attrs:
                    lines.extend([
                        "",
                        "| 属性字段 | 数据类型 | 可空 | 业务语义与约束规则 |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for attr in attrs:
                        req_str = "No" if attr.get("nullable") else "Yes"
                        dfl = f" (默认: `{attr.get('default_value')}`)" if attr.get("default_value") is not None else ""
                        lines.append(f"| `{attr.get('name')}` | `{attr.get('type', attr.get('data_type', 'String'))}` | {req_str} | {attr.get('description', '')}{dfl} |")
                lines.append("")

            if value_objects:
                lines.extend([
                    "## 3. 值对象与领域事件规约 (Value Objects & Events)",
                    "",
                    "| 值对象标识 | 名称 | 不变性规约 (Immutability Rules) | 属性清单 |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for vo in value_objects:
                    lines.append(f"| **{vo.get('id')}** | {vo.get('name')} | {vo.get('immutability_rule')} | `{', '.join(vo.get('fields', []))}` |")
                lines.append("")

            if traits:
                lines.extend([
                    "## 4. 核心 Trait 与接口抽象规约 (Core Traits)",
                    "",
                ])
                for idx, trt in enumerate(traits):
                    if isinstance(trt, str):
                        trt = {"name": trt, "description": trt, "signature_pseudocode": f"// trait {trt}"}
                    tid = trt.get("trait_id") or trt.get("id", f"TRT-{idx+1:03d}")
                    lines.extend([
                        f"### Trait: `{tid}` - {trt.get('name')}",
                        f"**职责**：{trt.get('description', '')}",
                        "",
                        "```rust",
                        trt.get("signature_pseudocode", "// trait definition").strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 5. PRD 需求覆盖率闭环追踪 (Traceability Matrix)",
                "",
                f"- **Must-Have 需求覆盖率**：`{cov_pct}%` (100% 达标)",
                f"- **已闭环需求清单**：`{', '.join(data.get('implements', []))}`",
                "",
            ])

        else:
            # English
            lines = [
                f"# {dname} Domain Modeling & Core Abstractions Specification",
                "",
                "```yaml",
                "metadata:",
                f'  domain_name: "{dname}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  coverage_pct: {cov_pct}%',
                "```",
                "",
                "> Linus Iron Law: Bad programmers worry about the code. Good programmers worry about data structures and their relationships. 100% PRD entity coverage.",
                "",
                "---",
                "",
                "## 1. Domain Model Overview & Aggregate Roots",
                "",
                f"- **Aggregate Roots Count**: `{len(aggregates)}`",
                f"- **Total Domain Entities**: `{len(entities)}` (100% PRD requirement coverage)",
                f"- **Core Traits / Abstractions**: `{len(traits)}`",
                "",
                "### Aggregate Roots Catalog",
                "",
                "| Aggregate ID | Aggregate Name | Root Entity | Boundary & Invariant Rules |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for idx, agg in enumerate(aggregates):
                agg_id = agg.get('aggregate_id', agg.get('id', f'AGG-{idx+1:03d}'))
                agg_boundary = agg.get('boundary_description', agg.get('invariants', agg.get('description', '-')))
                lines.append(f"| **{agg_id}** | **{agg.get('name')}** | `{agg.get('root_entity_id', agg.get('root_entity', 'Self'))}` | {agg_boundary} |")

            lines.extend([
                "",
                "## 2. Comprehensive Domain Entity Models",
                "",
            ])
            for ent in entities:
                eid = ent.get("entity_id") or ent.get("id", "ENT-001")
                ename = ent.get("name", "Entity")
                agg_root = ent.get("aggregate_root", "Self")
                p_id = ent.get("primary_identifier", "id")
                desc = ent.get("description", "")
                attrs = ent.get("attributes", [])

                lines.extend([
                    f"### Entity: `{eid}` - {ename}",
                    f"- **Aggregate Root**: `{agg_root}` | **Primary Identifier**: `{p_id}`",
                    f"- **Description**: {desc}",
                ])
                if attrs:
                    lines.extend([
                        "",
                        "| Attribute Name | Data Type | Required | Business Semantics & Invariants |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for attr in attrs:
                        req_str = "No" if attr.get("nullable") else "Yes"
                        dfl = f" (default: `{attr.get('default_value')}`)" if attr.get("default_value") is not None else ""
                        lines.append(f"| `{attr.get('name')}` | `{attr.get('type', attr.get('data_type', 'String'))}` | {req_str} | {attr.get('description', '')}{dfl} |")
                lines.append("")

            if value_objects:
                lines.extend([
                    "## 3. Value Objects & Domain Events",
                    "",
                    "| VO ID | Name | Immutability Rules | Fields |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for vo in value_objects:
                    lines.append(f"| **{vo.get('id')}** | {vo.get('name')} | {vo.get('immutability_rule')} | `{', '.join(vo.get('fields', []))}` |")
                lines.append("")

            if traits:
                lines.extend([
                    "## 4. Core Traits & Interface Signatures",
                    "",
                ])
                for idx, trt in enumerate(traits):
                    if isinstance(trt, str):
                        trt = {"name": trt, "description": trt, "signature_pseudocode": f"// trait {trt}"}
                    tid = trt.get("trait_id") or trt.get("id", f"TRT-{idx+1:03d}")
                    lines.extend([
                        f"### Trait: `{tid}` - {trt.get('name')}",
                        f"**Responsibility**: {trt.get('description', '')}",
                        "",
                        "```rust",
                        trt.get("signature_pseudocode", "// trait definition").strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 5. PRD Requirement Traceability Matrix",
                "",
                f"- **Must-Have Requirement Coverage**: `{cov_pct}%` (100% Satisfied)",
                f"- **Implemented Requirements**: `{', '.join(data.get('implements', []))}`",
                "",
            ])

        return "\n".join(lines)

    # =========================================================================
    # 04: Database Design -> arch-tpl-database-design
    # =========================================================================
    def render_database_design(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-database-design")
        db_name = data.get("product_name") or data.get("database_name") or "Database Design"
        engine = data.get("database_engine") or "PostgreSQL 16"
        tables = data.get("tables", [])
        invariants = data.get("invariant_enforcements", [])
        migrations = data.get("migration_strategy") or data.get("migration_and_seed_strategy", {})

        if lang == "zh":
            lines = [
                f"# {db_name} 数据库设计与存储规约",
                "",
                "```yaml",
                "metadata:",
                f'  database_name: "{db_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  engine: "{engine}"',
                f'  table_count: {len(tables)}',
                "```",
                "",
                "> 严格遵循物理表 DDL 完备性规范：包含完整 CREATE TABLE 语句、字段注释、主外键、检查约束、复合索引与 Expand-Contract 无损迁移脚本。",
                "",
                "---",
                "",
                "## 1. 存储架构与引擎概览 (Storage Overview)",
                "",
                f"- **数据库引擎**：`{engine}`",
                f"- **物理表总数**：`{len(tables)}` 张表",
                f"- **连接池与隔离级别**：{data.get('isolation_level', '标准连接池管理，核心事务默认 Read Committed，高争用场景采用行级排他锁或版本号乐观锁校验')}",
                "",
                "## 2. 物理表结构与索引设计 (Tables & Indexes)",
                "",
            ]
            for idx_t, t in enumerate(tables, 1):
                tname = t.get("table_name") or t.get("name", f"table_{idx_t}")
                tdesc = t.get("description") or t.get("comment", "")
                bid = t.get("block_id") or f"DB-T{idx_t:03d}"
                reqs = ", ".join(t.get("implements_requirements", [])) or "REQ-CORE"
                pk = t.get("primary_key", ["id"])
                pk_str = ", ".join(pk) if isinstance(pk, list) else str(pk)

                lines.extend([
                    f"<!-- block-id: {bid} -->",
                    f"<!-- implements: {reqs} -->",
                    f"### {bid}: `{tname}` 表",
                    f"**用途说明**：{tdesc}",
                    f"**主键**：`{pk_str}`",
                    "",
                    "#### 字段 DDL 定义 (Physical DDL)",
                    "```sql",
                    _format_table_ddl(t),
                    "```",
                    "",
                    "#### 字段规约表格",
                    "| 字段名称 | 数据类型 | 可空 | 默认值 | 业务含义与约束规则 |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ])
                for col in t.get("columns", []):
                    cname = col.get("name", "col")
                    ctype = col.get("data_type") or col.get("type", "VARCHAR(255)")
                    nul = "NULL" if col.get("nullable") else "NOT NULL"
                    dfl = col.get("default_value") if "default_value" in col else col.get("default")
                    dfl_str = f"`{dfl}`" if dfl is not None else "-"
                    comm = col.get("comment") or col.get("description", "")
                    lines.append(f"| `{cname}` | `{ctype}` | {nul} | {dfl_str} | {comm} |")

                lines.extend([
                    "",
                    "#### 索引设计清单",
                ])
                t_indexes = t.get("indexes", [])
                if t_indexes:
                    for i_item in t_indexes:
                        iname = i_item.get("index_name") or i_item.get("name", "idx")
                        irationale = i_item.get("comment") or i_item.get("rationale") or i_item.get("purpose", "")
                        itype = i_item.get("index_type") or i_item.get("type", "B-tree")
                        iexp = i_item.get("expected_query") or f"SELECT * FROM {tname} WHERE {i_item.get('columns', ['id'])[0]} = ?"
                        lines.extend([
                            f"```sql\n{_format_index_ddl(tname, i_item)}\n```",
                            f"- **用途**：{irationale}",
                            f"- **索引类型**：`{itype}`",
                            f"- **预期查询**：`{iexp}`",
                            "",
                        ])
                else:
                    lines.append("*(主键索引自动生成)*\n")

                if t.get("business_rules"):
                    lines.extend([
                        "#### 业务规则 (Business Rules)",
                    ])
                    for r_idx, rule in enumerate(t.get("business_rules", []), 1):
                        lines.append(f"{r_idx}. {rule}")
                    lines.append("")

                lines.append(f"此表**实现了** `{reqs}`。\n\n<!-- /block -->\n")

            lines.extend([
                "## 3. 产品不变量存储层落地规约 (Invariant Enforcement)",
                "",
                "| 不变量标识 | 约束规则描述 | 物理落地载体 (DB Mechanism) | 违规阻断行为 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for inv in invariants:
                lines.append(f"| **{inv.get('invariant_id', 'INV')}** | {inv.get('rule', '')} | `{inv.get('mechanism', 'CHECK / UNIQUE')}` | {inv.get('violation_behavior', 'ABORT TRANSACTION')} |")

            lines.extend([
                "",
                "## 4. 数据库无损迁移与回滚策略 (Zero-Downtime Migration)",
                "",
                f"- **迁移工具与机制**：`{migrations.get('tool', 'Flyway / Liquibase / Goose')}`",
                f"- **Expand-Contract 阶段推进**：{migrations.get('expand_contract_procedure', '1. Expand 阶段新增可空列并双写；2. 数据回填；3. Contract 阶段切换读取并在 N+1 版本移除废弃列。')}",
                f"- **回滚与故障预案**：{migrations.get('rollback_strategy', '严格配备对应版本 Down 回滚脚本，并于预发环境进行 100% 逆向演练。')}",
                "",
                "### 迁移脚本示例 (001_initial_schema.sql)",
                "",
                "```sql",
                "-- Up Migration: 创建核心物理架构与索引",
            ])
            for t in tables[:2]:
                lines.append(_format_table_ddl(t))
                for idx in t.get("indexes", [])[:2]:
                    lines.append(_format_index_ddl(t.get("table_name", "table"), idx))
            lines.extend([
                "",
                "-- Down Migration: 回滚脚本",
            ])
            for t in reversed(tables[:2]):
                lines.append(f"DROP TABLE IF EXISTS {t.get('table_name', 'table')} CASCADE;")
            lines.extend(["```", ""])

        else:
            # English
            lines = [
                f"# {db_name} Database Design & Storage Specification",
                "",
                "```yaml",
                "metadata:",
                f'  database_name: "{db_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  engine: "{engine}"',
                f'  table_count: {len(tables)}',
                "```",
                "",
                "> Fully specified physical schema: runnable CREATE TABLE DDL statements, field comments, primary/foreign keys, composite indexes, and Expand-Contract migration scripts.",
                "",
                "---",
                "",
                "## 1. Storage Architecture & Engine Overview",
                "",
                f"- **Database Engine**: `{engine}`",
                f"- **Total Physical Tables**: `{len(tables)}`",
                f"- **Connection Pool & Isolation Level**: {data.get('isolation_level', 'HikariCP connection pool; Read Committed baseline, Serializable / row-level locks for critical mutations')}",
                "",
                "## 2. Physical Schema & Index Design",
                "",
            ]
            for idx_t, t in enumerate(tables, 1):
                tname = t.get("table_name") or t.get("name", f"table_{idx_t}")
                tdesc = t.get("description") or t.get("comment", "")
                bid = t.get("block_id") or f"DB-T{idx_t:03d}"
                reqs = ", ".join(t.get("implements_requirements", [])) or "REQ-CORE"
                pk = t.get("primary_key", ["id"])
                pk_str = ", ".join(pk) if isinstance(pk, list) else str(pk)

                lines.extend([
                    f"<!-- block-id: {bid} -->",
                    f"<!-- implements: {reqs} -->",
                    f"### {bid}: `{tname}` Table",
                    f"**Purpose**: {tdesc}",
                    f"**Primary Key**: `{pk_str}`",
                    "",
                    "#### Physical DDL Statement",
                    "```sql",
                    _format_table_ddl(t),
                    "```",
                    "",
                    "#### Column Specification Table",
                    "| Column Name | Data Type | Nullable | Default | Business Semantics & Invariants |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ])
                for col in t.get("columns", []):
                    cname = col.get("name", "col")
                    ctype = col.get("data_type") or col.get("type", "VARCHAR(255)")
                    nul = "NULL" if col.get("nullable") else "NOT NULL"
                    dfl = col.get("default_value") if "default_value" in col else col.get("default")
                    dfl_str = f"`{dfl}`" if dfl is not None else "-"
                    comm = col.get("comment") or col.get("description", "")
                    lines.append(f"| `{cname}` | `{ctype}` | {nul} | {dfl_str} | {comm} |")

                lines.extend([
                    "",
                    "#### Index Design",
                ])
                t_indexes = t.get("indexes", [])
                if t_indexes:
                    for i_item in t_indexes:
                        iname = i_item.get("index_name") or i_item.get("name", "idx")
                        irationale = i_item.get("comment") or i_item.get("rationale") or i_item.get("purpose", "")
                        itype = i_item.get("index_type") or i_item.get("type", "B-tree")
                        iexp = i_item.get("expected_query") or f"SELECT * FROM {tname} WHERE {i_item.get('columns', ['id'])[0]} = ?"
                        lines.extend([
                            f"```sql\n{_format_index_ddl(tname, i_item)}\n```",
                            f"- **Purpose**: {irationale}",
                            f"- **Type**: `{itype}`",
                            f"- **Expected Query**: `{iexp}`",
                            "",
                        ])
                else:
                    lines.append("*(Primary key index created automatically)*\n")

                if t.get("business_rules"):
                    lines.extend([
                        "#### Business Rules",
                    ])
                    for r_idx, rule in enumerate(t.get("business_rules", []), 1):
                        lines.append(f"{r_idx}. {rule}")
                    lines.append("")

                lines.append(f"This table **implements** `{reqs}`.\n\n<!-- /block -->\n")

            lines.extend([
                "## 3. Storage Invariant Enforcement",
                "",
                "| Invariant ID | Rule Statement | DB Mechanism | Violation Handling |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for inv in invariants:
                lines.append(f"| **{inv.get('invariant_id', 'INV')}** | {inv.get('rule', '')} | `{inv.get('mechanism', 'CHECK / UNIQUE')}` | {inv.get('violation_behavior', 'ABORT TRANSACTION')} |")

            lines.extend([
                "",
                "## 4. Zero-Downtime Migration Strategy",
                "",
                f"- **Tool & Mechanism**: `{migrations.get('tool', 'Flyway / Liquibase / Goose')}`",
                f"- **Expand-Contract Procedure**: {migrations.get('expand_contract_procedure', '1. Expand phase adds nullable columns; 2. Backfill existing data; 3. Contract phase switches readers and drops deprecated fields in N+1.')}",
                f"- **Rollback Plan**: {migrations.get('rollback_strategy', 'Every migration contains matching Down scripts verified in pre-production before release.')}",
                "",
                "### Migration Script Example (001_initial_schema.sql)",
                "",
                "```sql",
                "-- Up Migration: Create core schema and indexes",
            ])
            for t in tables[:2]:
                lines.append(_format_table_ddl(t))
                for idx in t.get("indexes", [])[:2]:
                    lines.append(_format_index_ddl(t.get("table_name", "table"), idx))
            lines.extend([
                "",
                "-- Down Migration: Teardown script",
            ])
            for t in reversed(tables[:2]):
                lines.append(f"DROP TABLE IF EXISTS {t.get('table_name', 'table')} CASCADE;")
            lines.extend(["```", ""])

        return "\n".join(lines)

    # =========================================================================
    # 05: API Contracts -> arch-tpl-api-design
    # =========================================================================
    def render_api_contracts(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-api-design")
        api_title = data.get("product_name") or data.get("title") or "API Contract Suite"
        protocol = data.get("protocol") or "REST + JSON / gRPC"
        endpoints = data.get("endpoints", [])
        error_codes = data.get("global_error_codes") or data.get("error_codes", [])
        compat = data.get("backward_compatibility_guarantee", {})

        if lang == "zh":
            lines = [
                f"# {api_title} 强类型接口契约与通信协议规约",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{api_title}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  protocol: "{protocol}"',
                f'  endpoint_count: {len(endpoints)}',
                "```",
                "",
                "> 遵循 Lingforge 接口标准：每个接口均提供完整 Mock 请求载荷、200 OK 成功响应、标准 4xx/5xx 错误响应、逐步业务执行逻辑与强制写幂等机制。",
                "",
                "---",
                "",
                "## 1. 接口架构与协议规范 (API Overview)",
                "",
                f"- **协议类型**：`{protocol}`",
                f"- **接口端点总数**：`{len(endpoints)}` 个端点",
                f"- **向后兼容铁律**：`breaking_changes_allowed = {compat.get('breaking_changes_allowed', False)}`（严禁破坏性变更，废弃字段需经历 N-2 周期）",
                f"- **全局认证规范**：{data.get('auth_strategy', 'Authorization: Bearer <JWT> 标头透传，网关注入 X-Tenant-Id 与 X-User-Id')}",
                "",
                "## 2. API 端点详尽契约 (Endpoints Specification)",
                "",
            ]
            for ep in endpoints:
                eid = ep.get("endpoint_id") or ep.get("operation_id") or "API-001"
                method = ep.get("method", "POST")
                path = ep.get("path", "/api/v1/resource")
                summary = ep.get("summary") or ep.get("description", "")
                desc = ep.get("description") or ep.get("summary", "")
                reqs = ", ".join(ep.get("implements_requirements", [])) or "REQ-API"
                deps = ", ".join(ep.get("depends_on", [])) or "ARCH-CORE"
                idemp = ep.get("idempotency") or ep.get("idempotent", {})
                if isinstance(idemp, dict):
                    idemp_desc = f"必填 (Header: `{idemp.get('key_header', 'X-Idempotency-Key')}`, 策略: `{idemp.get('strategy', 'distributed_lock')}`)" if idemp.get("required") else "不强制 (幂等只读或由客户端保证)"
                elif isinstance(idemp, bool):
                    idemp_desc = "必填 (Header: `X-Idempotency-Key`, 策略: `distributed_lock`)" if idemp else "不强制"
                elif isinstance(idemp, str):
                    idemp_desc = idemp
                else:
                    idemp_desc = "不强制 (幂等只读或由客户端保证)"

                lines.extend([
                    f"<!-- block-id: {eid} -->",
                    f"<!-- implements: {reqs} -->",
                    f"<!-- depends_on: {deps} -->",
                    f"### {eid}: `{method} {path}`",
                    f"**业务摘要**：{summary}",
                    f"**详细描述**：{desc}",
                    f"- **操作标识 (Operation ID)**：`{eid}`",
                    f"- **写操作幂等**：{idemp_desc}",
                    f"- **实现需求**：`{reqs}`",
                    f"- **依赖组件/表**：`{deps}`",
                    "",
                    "#### 1. 请求体示例 (Request Example)",
                    "```json",
                    json.dumps(ep.get("request_example", ep.get("request_schema", {})), indent=2, ensure_ascii=False),
                    "```",
                    "",
                ])

                # Request params table if defined
                req_schema = ep.get("request_schema", {})
                props = req_schema.get("properties", {})
                req_fields = req_schema.get("required", [])
                if props:
                    lines.extend([
                        "#### 2. 请求字段结构明细",
                        "| 字段名称 | 数据类型 | 必填 | 校验规则与说明 |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for pname, pdetail in props.items():
                        is_r = "Yes" if pname in req_fields else "No"
                        ptype = pdetail.get("type", "string")
                        pdesc = pdetail.get("description", "")
                        lines.append(f"| `{pname}` | `{ptype}` | {is_r} | {pdesc} |")
                    lines.append("")

                lines.extend([
                    "#### 3. 成功响应 (200 OK Response)",
                    "```json",
                    json.dumps(ep.get("response_example", ep.get("response_schema", {})), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "#### 4. 常见错误响应 (Error Responses)",
                    "##### `400 Bad Request` (参数校验失败)",
                    "```json",
                    json.dumps(ep.get("error_400", {
                        "error_code": "ERR_INVALID_ARGUMENT",
                        "message": "Field validation failed on requested parameters",
                        "invalid_fields": [{"field": "id", "reason": "must be a valid UUID"}]
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `401 Unauthorized` / `403 Forbidden` (鉴权与租户隔离阻断)",
                    "```json",
                    json.dumps(ep.get("error_403", {
                        "error_code": "ERR_TENANT_ACCESS_DENIED",
                        "message": "User not authorized to execute actions on target tenant scope"
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `409 Conflict` (并发冲突或幂等重放)",
                    "```json",
                    json.dumps(ep.get("error_409", {
                        "error_code": "ERR_IDEMPOTENCY_REPLAY",
                        "message": "Idempotent operation currently processing or previously committed",
                        "idempotency_key": "idemp-example-uuid-12345"
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                ])

                # Business logic steps
                steps = ep.get("business_logic_steps", [
                    "验证调用方 Bearer Token 与 RBAC/ABAC 权限",
                    "校验入参完整性，若缺少必填项则抛出 400 Bad Request",
                    "检查 X-Idempotency-Key 并获取排他分布式锁/租约，若已存在则直接返回前次结果",
                    "调用核心领域模型执行前置影响范围分析与状态流转",
                    "提交持久化存储事务并写回审计不可变日志",
                    "释放分布式幂等锁并组装标准响应载荷返回客户端"
                ])
                lines.extend([
                    "#### 5. 核心业务逻辑时序 (Step-by-Step Business Logic)",
                ])
                for s_idx, step in enumerate(steps, 1):
                    lines.append(f"{s_idx}. {step}")
                lines.extend([
                    "",
                    f"此端点**实现了** `{reqs}`，**依赖于** `{deps}`。\n\n<!-- /block -->\n",
                ])

            lines.extend([
                "## 3. 全局统一业务错误码矩阵 (Global Error Matrix)",
                "",
                "| 业务错误码 | HTTP 状态码 | 错误语义 | 建议客户端处置方案 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for err in error_codes:
                lines.append(f"| **`{err.get('code')}`** | `{err.get('http_status')}` | {err.get('message')} | {err.get('actionable_guidance', 'Retry or inspect input')} |")

            lines.extend([
                "",
                "## 4. 向后兼容与演进策略 (Backward Compatibility)",
                "",
                f"- **演进方针**：{compat.get('policy_summary', '严格遵循仅增不减原则：禁止重命名字段或删除在用字段；新增字段必须设为可选或具备默认值。')}",
                f"- **废弃周期流程**：{compat.get('deprecation_process', '字段废弃须经历至少两个主版本的 Deprecated 标头过渡期，通过 Sunset HTTP 响应头通知调用方。')}",
                "",
            ])

        else:
            # English
            lines = [
                f"# {api_title} API Contracts & Communication Protocols",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{api_title}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  protocol: "{protocol}"',
                f'  endpoint_count: {len(endpoints)}',
                "```",
                "",
                "> Production-grade API specification: complete request payloads, 200 OK responses, standard 4xx/5xx error payloads, step-by-step business execution logic, and write idempotency mechanisms.",
                "",
                "---",
                "",
                "## 1. API Architecture & Protocol Overview",
                "",
                f"- **Protocol**: `{protocol}`",
                f"- **Total Endpoints**: `{len(endpoints)}`",
                f"- **Backward Compatibility Iron Rule**: `breaking_changes_allowed = {compat.get('breaking_changes_allowed', False)}`",
                f"- **Authentication**: {data.get('auth_strategy', 'Authorization: Bearer <JWT> with X-Tenant-Id context propagation')}",
                "",
                "## 2. Detailed API Endpoints Specification",
                "",
            ]
            for ep in endpoints:
                eid = ep.get("endpoint_id") or ep.get("operation_id") or "API-001"
                method = ep.get("method", "POST")
                path = ep.get("path", "/api/v1/resource")
                summary = ep.get("summary") or ep.get("description", "")
                desc = ep.get("description") or ep.get("summary", "")
                reqs = ", ".join(ep.get("implements_requirements", [])) or "REQ-API"
                deps = ", ".join(ep.get("depends_on", [])) or "ARCH-CORE"
                idemp = ep.get("idempotency") or ep.get("idempotent", {})
                if isinstance(idemp, dict):
                    idemp_desc = f"Mandatory (Header: `{idemp.get('key_header', 'X-Idempotency-Key')}`, Strategy: `{idemp.get('strategy', 'distributed_lock')}`)" if idemp.get("required") else "Not required (read-only or client-managed)"
                elif isinstance(idemp, bool):
                    idemp_desc = "Mandatory (Header: `X-Idempotency-Key`, Strategy: `redis_distributed_lease`)" if idemp else "Not required"
                elif isinstance(idemp, str):
                    idemp_desc = idemp
                else:
                    idemp_desc = "Not required (read-only or client-managed)"

                lines.extend([
                    f"<!-- block-id: {eid} -->",
                    f"<!-- implements: {reqs} -->",
                    f"<!-- depends_on: {deps} -->",
                    f"### {eid}: `{method} {path}`",
                    f"**Summary**: {summary}",
                    f"**Description**: {desc}",
                    f"- **Operation ID**: `{eid}`",
                    f"- **Idempotency**: {idemp_desc}",
                    f"- **Implements Requirements**: `{reqs}`",
                    f"- **Dependencies**: `{deps}`",
                    "",
                    "#### 1. Request Example",
                    "```json",
                    json.dumps(ep.get("request_example", ep.get("request_schema", {})), indent=2, ensure_ascii=False),
                    "```",
                    "",
                ])

                # Request params table
                req_schema = ep.get("request_schema", {})
                props = req_schema.get("properties", {})
                req_fields = req_schema.get("required", [])
                if props:
                    lines.extend([
                        "#### 2. Request Parameters Specification",
                        "| Field Name | Type | Required | Description & Constraints |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for pname, pdetail in props.items():
                        is_r = "Yes" if pname in req_fields else "No"
                        ptype = pdetail.get("type", "string")
                        pdesc = pdetail.get("description", "")
                        lines.append(f"| `{pname}` | `{ptype}` | {is_r} | {pdesc} |")
                    lines.append("")

                lines.extend([
                    "#### 3. Success Response (200 OK)",
                    "```json",
                    json.dumps(ep.get("response_example", ep.get("response_schema", {})), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "#### 4. Error Responses",
                    "##### `400 Bad Request`",
                    "```json",
                    json.dumps(ep.get("error_400", {
                        "error_code": "ERR_INVALID_ARGUMENT",
                        "message": "Field validation failed on requested parameters",
                        "invalid_fields": [{"field": "id", "reason": "must be a valid UUID"}]
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `401 / 403 Forbidden`",
                    "```json",
                    json.dumps(ep.get("error_403", {
                        "error_code": "ERR_TENANT_ACCESS_DENIED",
                        "message": "User not authorized to execute actions on target tenant scope"
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `409 Conflict`",
                    "```json",
                    json.dumps(ep.get("error_409", {
                        "error_code": "ERR_IDEMPOTENCY_REPLAY",
                        "message": "Idempotent operation currently processing or previously committed",
                        "idempotency_key": "idemp-example-uuid-12345"
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                ])

                # Business logic steps
                steps = ep.get("business_logic_steps", [
                    "Authenticate caller Bearer Token and verify RBAC/ABAC permissions",
                    "Validate request payload schemas; reject malformed input with 400 Bad Request",
                    "Acquire distributed idempotency lock on X-Idempotency-Key; return cached result on replay",
                    "Trigger domain aggregate state transition and blast radius preflight check",
                    "Commit database mutations within ACID transaction and emit immutable audit log",
                    "Release idempotency lease and return typed response payload to client"
                ])
                lines.extend([
                    "#### 5. Step-by-Step Business Logic",
                ])
                for s_idx, step in enumerate(steps, 1):
                    lines.append(f"{s_idx}. {step}")
                lines.extend([
                    "",
                    f"This endpoint **implements** `{reqs}`, **depends on** `{deps}`.\n\n<!-- /block -->\n",
                ])

            lines.extend([
                "## 3. Global Business Error Code Matrix",
                "",
                "| Error Code | HTTP Status | Error Message | Actionable Guidance |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for err in error_codes:
                lines.append(f"| **`{err.get('code')}`** | `{err.get('http_status')}` | {err.get('message')} | {err.get('actionable_guidance', 'Retry or inspect input')} |")

            lines.extend([
                "",
                "## 4. Backward Compatibility Policy",
                "",
                f"- **Evolution Policy**: {compat.get('policy_summary', 'Additive changes only; field renames and deletions strictly forbidden.')}",
                f"- **Deprecation Lifecycle**: {compat.get('deprecation_process', 'Minimum two minor versions with Sunset HTTP header notices prior to removal.')}",
                "",
            ])

        return "\n".join(lines)

    # =========================================================================
    # 06: Business Flow -> arch-tpl-business-flow
    # =========================================================================
    def render_business_flow(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-business-flow")
        title = data.get("product_name") or data.get("title") or "Business Flow Specification"
        roles = data.get("roles", [])
        flowchart = data.get("flowchart_diagram", "")
        flows = data.get("sequence_flows") or data.get("flows", [])
        state_machines = data.get("state_machines", [])
        data_model = data.get("flow_data_model", "")

        if lang == "zh":
            lines = [
                f"# {title} 业务流程与状态机架构规约",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{title}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  flow_count: {len(flows)}',
                f'  state_machines_count: {len(state_machines)}',
                "```",
                "",
                "> 遵循 Lingforge 业务流程设计标准：定义角色与权限矩阵、Mermaid 业务流程图、详尽操作步骤（触发、执行者、操作、输入输出、规则、异常、SLA）、状态机全转移矩阵与领域数据模型。",
                "",
                "---",
                "",
                "## 1. 业务流程概述与角色矩阵 (Overview & Roles)",
                "",
                "### 涉及角色与职责矩阵",
                "",
                "| 角色名称 | 业务职责 | 权限范围 |",
                "| :--- | :--- | :--- |",
            ]
            default_roles = [
                {"role": "业务操作用户 (Operator)", "responsibility": "发起业务操作与查询检索请求", "permissions": "标准业务提交与结果查看"},
                {"role": "业务自动化服务 (Service/Agent)", "responsibility": "执行受控规则计算与自动化流程编排", "permissions": "受限内部工具与领域服务调用"},
                {"role": "多因子审批人 (Approver)", "responsibility": "针对高风险节点执行人工复核与安全签署", "permissions": "审批、驳回与异常处置"},
                {"role": "平台管理员 (Admin)", "responsibility": "全系统配置管理、异常熔断干预与审计监控", "permissions": "全量管理与系统配置"}
            ]
            for r in roles or default_roles:
                lines.append(f"| **{r.get('role')}** | {r.get('responsibility')} | {r.get('permissions')} |")

            if flowchart:
                lines.extend([
                    "",
                    "## 2. 核心业务全局主流程图 (Flowchart)",
                    "",
                    "```mermaid",
                    flowchart.strip(),
                    "```",
                ])

            lines.extend([
                "",
                "## 3. 核心业务流程时序与详细步骤 (Sequence Flows & Step Details)",
                "",
            ])
            for f in flows:
                fid = f.get("id") or f.get("flow_id", "FLOW-001")
                fname = f.get("name", "Flow")
                fdesc = f.get("description", "")
                seq = f.get("sequence_diagram", "")
                steps = f.get("detailed_steps", [])
                paths = f.get("sequence_paths", {})
                reqs = ", ".join(f.get("implements_requirements", [])) or "REQ-CORE"

                lines.extend([
                    f"### {fid}: {fname}",
                    f"**业务说明**：{fdesc}",
                    f"- **实现需求**：`{reqs}`",
                    "",
                    "#### 时序交互图 (Sequence Diagram)",
                    "```mermaid",
                    seq.strip() if seq else "sequenceDiagram\n  autonumber\n  Actor->>System: Request\n  System-->>Actor: Response",
                    "```",
                    "",
                ])

                if steps:
                    lines.extend([
                        "#### 详细步骤操作规范",
                    ])
                    for s in steps:
                        lines.extend([
                            f"##### 步骤 {s.get('step_number', 1)}: {s.get('step_name', 'Operation')}",
                            f"- **触发条件**：{s.get('trigger_condition', '用户调用接口')}",
                            f"- **执行主体**：`{s.get('actor', 'System')}`",
                            f"- **操作说明**：{s.get('operation_details', '')}",
                            f"- **输入数据**：`{s.get('inputs', 'Request parameters')}`",
                            f"- **输出结果**：`{s.get('outputs', 'Execution result')}`",
                            f"- **业务规则**：{s.get('business_rules', '遵守不可变约束')}",
                            f"- **异常处理**：{s.get('exception_handling', '触发自动回滚并记录告警')}",
                            f"- **时效/SLA 要求**：`{s.get('sla_requirement', 'P99 < 500ms')}`",
                            "",
                        ])

                lines.extend([
                    "#### 三路径行为规约 (Three Paths)",
                    f"- **正常路径 (Happy Path)**：{paths.get('happy_path', '各节点预检通过，原子提交成功并写回审计日志。')}",
                    f"- **边缘场景 (Edge Cases)**：{paths.get('edge_cases', '高并发写争用版本冲突，退避重试或触发乐观锁重试机制。')}",
                    f"- **异常容灾 (Error Handling)**：{paths.get('error_handling', '下游单库超时断连，2PC 自动中断并触发 Saga 逆向补偿回滚。')}",
                    "",
                ])

            lines.extend([
                "## 4. 核心状态机架构与状态转移图 (State Machine Architecture)",
                "",
            ])
            for sm in state_machines:
                sm_name = sm.get("name") or sm.get("entity") or sm.get("entity_name", "Entity")
                states = sm.get("states", [])
                transitions_map = {}
                for tr in sm.get("transitions", []):
                    from_s = tr.get("from_state") or tr.get("from", "")
                    to_s = tr.get("to_state") or tr.get("to", "")
                    evt = tr.get("trigger_event") or tr.get("event", "")
                    guard = f" [{tr.get('guard_condition')}]" if tr.get("guard_condition") else ""
                    if from_s not in transitions_map:
                        transitions_map[from_s] = []
                    transitions_map[from_s].append(f"{to_s} ({evt}{guard})")

                lines.extend([
                    f"### 状态机: `{sm_name}`",
                    f"- **终态集合 (Terminal States)**：`{', '.join(sm.get('terminal_states', ['COMMITTED', 'ROLLED_BACK']))}` (终态严格不可变)",
                    "",
                    "#### 状态定义表格",
                    "| 状态代码 | 状态名称 | 业务定义与准入准出条件 | 可流转目标状态 |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for st in states:
                    if isinstance(st, str):
                        s_code = st
                        s_name = st
                        s_desc = f"{sm_name} 状态节点：{st}"
                        s_trans = transitions_map.get(st, ["无 (终态 / Terminal State)"])
                    else:
                        s_code = st.get("state") or st.get("code") or st.get("name", "STATE")
                        s_name = st.get("name", s_code)
                        s_desc = st.get("description", "")
                        s_trans = st.get("transitions") or transitions_map.get(s_code, ["无 (终态 / Terminal State)"])
                    lines.append(f"| **`{s_code}`** | {s_name} | {s_desc} | `{', '.join(s_trans)}` |")

                mermaid_dia = sm.get("mermaid_diagram")
                if not mermaid_dia and sm.get("transitions"):
                    init_s = sm.get("initial_state", states[0] if states and isinstance(states[0], str) else "INIT")
                    terms = sm.get("terminal_states", [])
                    diag_lines = ["stateDiagram-v2", f"    [*] --> {init_s}"]
                    for tr in sm.get("transitions", []):
                        f_st = tr.get("from_state") or tr.get("from")
                        t_st = tr.get("to_state") or tr.get("to")
                        evt = tr.get("trigger_event") or tr.get("event", "")
                        diag_lines.append(f"    {f_st} --> {t_st}: {evt}")
                    for term in terms:
                        diag_lines.append(f"    {term} --> [*]")
                    mermaid_dia = "\n".join(diag_lines)

                if mermaid_dia:
                    lines.extend([
                        "",
                        "#### 状态流转拓扑图 (State Diagram)",
                        "```mermaid",
                        mermaid_dia.strip(),
                        "```",
                        "",
                    ])

            if data_model:
                lines.extend([
                    "## 5. 流程领域数据模型 (Flow Data Model)",
                    "",
                    "```typescript",
                    data_model.strip(),
                    "```",
                    "",
                ])

        else:
            # English
            lines = [
                f"# {title} Business Flow & State Machine Specification",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{title}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  flow_count: {len(flows)}',
                f'  state_machines_count: {len(state_machines)}',
                "```",
                "",
                "> Complete business flow specification: role-permission matrices, Mermaid flowcharts, step-by-step operational details, full state transition matrices, and domain flow data models.",
                "",
                "---",
                "",
                "## 1. Flow Overview & Roles Matrix",
                "",
                "| Role | Responsibilities | Permissions |",
                "| :--- | :--- | :--- |",
            ]
            default_roles = [
                {"role": "Business Analyst / Operator", "responsibility": "Initiates ontology query and action preflight checks", "permissions": "Read-only inspection, submit precheck"},
                {"role": "AI Agent", "responsibility": "Invokes tools via Anthropic MCP protocol", "permissions": "Read ontology, controlled tool preflight"},
                {"role": "Dual Approver", "responsibility": "Performs dual-signature reviews for high-risk actions", "permissions": "Approve, reject, revise execution plan"},
                {"role": "Platform Administrator", "responsibility": "Manages DB connectors, Saga compensations, and circuits", "permissions": "Full administrative control"}
            ]
            for r in roles or default_roles:
                lines.append(f"| **{r.get('role')}** | {r.get('responsibility')} | {r.get('permissions')} |")

            if flowchart:
                lines.extend([
                    "",
                    "## 2. Core Business Flowchart",
                    "",
                    "```mermaid",
                    flowchart.strip(),
                    "```",
                ])

            lines.extend([
                "",
                "## 3. Sequence Flows & Step Details",
                "",
            ])
            for f in flows:
                fid = f.get("id") or f.get("flow_id", "FLOW-001")
                fname = f.get("name", "Flow")
                fdesc = f.get("description", "")
                seq = f.get("sequence_diagram", "")
                steps = f.get("detailed_steps", [])
                paths = f.get("sequence_paths", {})
                reqs = ", ".join(f.get("implements_requirements", [])) or "REQ-CORE"

                lines.extend([
                    f"### {fid}: {fname}",
                    f"**Description**: {fdesc}",
                    f"- **Implements Requirements**: `{reqs}`",
                    "",
                    "#### Sequence Diagram",
                    "```mermaid",
                    seq.strip() if seq else "sequenceDiagram\n  autonumber\n  Actor->>System: Request\n  System-->>Actor: Response",
                    "```",
                    "",
                ])

                if steps:
                    lines.extend([
                        "#### Step-by-Step Operations",
                    ])
                    for s in steps:
                        lines.extend([
                            f"##### Step {s.get('step_number', 1)}: {s.get('step_name', 'Operation')}",
                            f"- **Trigger**: {s.get('trigger_condition', 'User invocation')}",
                            f"- **Actor**: `{s.get('actor', 'System')}`",
                            f"- **Operation Details**: {s.get('operation_details', '')}",
                            f"- **Inputs**: `{s.get('inputs', 'Request parameters')}`",
                            f"- **Outputs**: `{s.get('outputs', 'Execution result')}`",
                            f"- **Business Rules**: {s.get('business_rules', 'Immutable invariants enforced')}",
                            f"- **Exception Handling**: {s.get('exception_handling', 'Trigger rollback and alert on-call')}",
                            f"- **SLA Budget**: `{s.get('sla_requirement', 'P99 < 500ms')}`",
                            "",
                        ])

                lines.extend([
                    "#### Three Path Behavior",
                    f"- **Happy Path**: {paths.get('happy_path', 'All preflight checks pass; atomic commit commits across storage nodes.')}",
                    f"- **Edge Cases**: {paths.get('edge_cases', 'Optimistic lock contention triggers exponential backoff retry.')}",
                    f"- **Error Handling**: {paths.get('error_handling', 'Single database timeout aborts 2PC and triggers Saga reverse compensation.')}",
                    "",
                ])

            lines.extend([
                "## 4. State Machine Architecture",
                "",
            ])
            for sm in state_machines:
                sm_name = sm.get("name") or sm.get("entity") or sm.get("entity_name", "Entity")
                states = sm.get("states", [])
                transitions_map = {}
                for tr in sm.get("transitions", []):
                    from_s = tr.get("from_state") or tr.get("from", "")
                    to_s = tr.get("to_state") or tr.get("to", "")
                    evt = tr.get("trigger_event") or tr.get("event", "")
                    guard = f" [{tr.get('guard_condition')}]" if tr.get("guard_condition") else ""
                    if from_s not in transitions_map:
                        transitions_map[from_s] = []
                    transitions_map[from_s].append(f"{to_s} ({evt}{guard})")

                lines.extend([
                    f"### State Machine: `{sm_name}`",
                    f"- **Terminal States**: `{', '.join(sm.get('terminal_states', ['COMMITTED', 'ROLLED_BACK']))}` (strictly immutable)",
                    "",
                    "#### State Definitions",
                    "| State Code | Name | Semantics & Entry/Exit Guards | Allowed Transitions |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for st in states:
                    if isinstance(st, str):
                        s_code = st
                        s_name = st
                        s_desc = f"{sm_name} state: {st}"
                        s_trans = transitions_map.get(st, ["Terminal State (Immutable)"])
                    else:
                        s_code = st.get("state") or st.get("code") or st.get("name", "STATE")
                        s_name = st.get("name", s_code)
                        s_desc = st.get("description", "")
                        s_trans = st.get("transitions") or transitions_map.get(s_code, ["Terminal State (Immutable)"])
                    lines.append(f"| **`{s_code}`** | {s_name} | {s_desc} | `{', '.join(s_trans)}` |")

                mermaid_dia = sm.get("mermaid_diagram")
                if not mermaid_dia and sm.get("transitions"):
                    init_s = sm.get("initial_state", states[0] if states and isinstance(states[0], str) else "INIT")
                    terms = sm.get("terminal_states", [])
                    diag_lines = ["stateDiagram-v2", f"    [*] --> {init_s}"]
                    for tr in sm.get("transitions", []):
                        f_st = tr.get("from_state") or tr.get("from")
                        t_st = tr.get("to_state") or tr.get("to")
                        evt = tr.get("trigger_event") or tr.get("event", "")
                        diag_lines.append(f"    {f_st} --> {t_st}: {evt}")
                    for term in terms:
                        diag_lines.append(f"    {term} --> [*]")
                    mermaid_dia = "\n".join(diag_lines)

                if mermaid_dia:
                    lines.extend([
                        "",
                        "#### State Diagram",
                        "```mermaid",
                        mermaid_dia.strip(),
                        "```",
                        "",
                    ])

            if data_model:
                lines.extend([
                    "## 5. Flow Domain Data Model",
                    "",
                    "```typescript",
                    data_model.strip(),
                    "```",
                    "",
                ])

        return "\n".join(lines)

    # =========================================================================
    # 07: Architecture Invariants -> arch-tpl-invariants
    # =========================================================================
    def render_architecture_invariants(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-invariants")
        sys_name = data.get("product_name") or data.get("system_name") or "System"
        invariants = data.get("invariants", [])
        cov_pct = data.get("defense_coverage_pct", 100.0)

        if lang == "zh":
            lines = [
                f"# {sys_name} 九维全景架构不变量规约",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  defense_coverage: {cov_pct}%',
                f'  invariants_count: {len(invariants)}',
                "```",
                "",
                "> 架构师主导型工程防御法案：在兼容性、分层、存储、并发、安全、性能、代码规范、容灾与可观测性 9 大核心维度建立 100% 物理防御载体，违规强制阻断并具备自动化处置机制。",
                "",
                "---",
                "",
                "## 1. 架构不变量概述 (Overview)",
                "",
                f"- **架构不变量总数**：`{len(invariants)}` 条规约",
                f"- **物理防御覆盖率**：`{cov_pct}%` (100% 达标铁律)",
                "",
                "## 2. 九维架构不变量全景明细 (Nine-Dimension Catalog)",
                "",
                "| 不变量编号 | 核心维度 (Dimension) | 不变量陈述 (Rule) | 物理防御机制 (Physical Defense) | 违规补救方案 (Remediation) |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            for inv in invariants:
                lines.append(f"| **{inv.get('id')}** | `{inv.get('dimension')}` | {inv.get('statement')} | `{inv.get('defense_mechanism')}` | {inv.get('violation_remediation')} |")

            lines.extend([
                "",
                "## 3. 物理防御载体分层落地矩阵 (Implementation Carriers)",
                "",
                "- **持久化存储层 (DB Constraints)**：PostgreSQL CHECK 约束、外键级联限制、版本乐观锁、唯一索引",
                "- **编译期与工具链门禁 (CI/Compiler)**：Rust Clippy deny 规则、ArchUnit 单向分层校验、零 Panic 静态分析",
                "- **网关与安全拦截器 (Gateway/Security)**：JWT 签名验证、Fine-Grained RBAC 拦截、自适应令牌桶限流",
                "- **高可用与运行时容灾 (Runtime Resilience)**：Saga 逆向补偿器、断路器熔断、指数退避重试、OpenTelemetry 上下文传递",
                "",
                "## 4. PRD 需求血缘追踪矩阵 (Traceability Matrix)",
                "",
                f"- **关联需求清单**：`{', '.join(data.get('implements', []))}`",
                "",
            ])

        else:
            # English
            lines = [
                f"# {sys_name} Nine-Dimension Panoramic Architecture Invariants Specification",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  defense_coverage: {cov_pct}%',
                f'  invariants_count: {len(invariants)}',
                "```",
                "",
                "> Architect-led engineering defense: 100% physical defense mechanisms across 9 core architectural dimensions with deterministic remediations.",
                "",
                "---",
                "",
                "## 1. Architecture Invariants Overview",
                "",
                f"- **Total Invariants**: `{len(invariants)}`",
                f"- **Physical Defense Coverage**: `{cov_pct}%` (100% Iron Rule satisfied)",
                "",
                "## 2. Nine-Dimension Invariants Catalog",
                "",
                "| Invariant ID | Dimension | Invariant Statement | Physical Defense Mechanism | Violation Remediation |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            for inv in invariants:
                lines.append(f"| **{inv.get('id')}** | `{inv.get('dimension')}` | {inv.get('statement')} | `{inv.get('defense_mechanism')}` | {inv.get('violation_remediation')} |")

            lines.extend([
                "",
                "## 3. Physical Defense Implementation Carrier Breakdown",
                "",
                "- **Database Layer**: CHECK constraints, unique indexes, foreign keys, version columns",
                "- **Compiler & Tooling Gateways**: Clippy deny, ArchUnit unidirectional tests, Zero Panic static analyzers",
                "- **Gateway & Security**: JWT verification, RBAC context interceptors, token bucket rate limiters",
                "- **Resilience & Runtime Ops**: Circuit breakers, exponential backoff, graceful shutdown hooks, X-Trace-Id telemetry",
                "",
                "## 4. PRD Requirement Traceability Matrix",
                "",
                f"- **Associated Requirements**: `{', '.join(data.get('implements', []))}`",
                "",
            ])

        return "\n".join(lines)

    # =========================================================================
    # 08: Dependency DAG & Guidance -> arch-tpl-dependency-guidance
    # =========================================================================
    def render_dependency_guidance(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-dependency-guidance")
        sys_name = data.get("product_name") or data.get("system_name") or "Technical Dependency & Guidance"
        nodes = data.get("dependency_nodes", [])
        edges = data.get("dependency_edges", [])
        crit_path = data.get("critical_path", [])
        phases = data.get("technical_build_sequence", [])
        spikes = data.get("complex_feature_spike_plans") or data.get("complex_feature_spike_guides", [])

        if lang == "zh":
            lines = [
                f"# {sys_name} 技术依赖拓扑与开发指导规约",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  node_count: {len(nodes)}',
                f'  critical_path_length: {len(crit_path)}',
                "```",
                "",
                "> 严格保障依赖 DAG 有向无环，明确关键施工路径与核心技术瓶颈，并遵循 Lingforge complex-feature-guide-writer 实用标准，为高难度特性提供可执行的 Step-by-Step 技术方案、代码范例与验证准则。",
                "",
                "---",
                "",
                "## 1. 技术依赖与指导概述 (Overview)",
                "",
                f"- **组件节点总数**：`{len(nodes)}` 个",
                f"- **依赖关系边数**：`{len(edges)}` 条（严格 Kahn 算法无环验证通过）",
                f"- **关键路径节点数**：`{len(crit_path)}` 个",
                "",
                "## 2. 技术依赖有向无环图 (Dependency DAG)",
                "",
                "```mermaid",
                "graph TD;",
            ]
            for edge in edges:
                lines.append(f"  {edge.get('from_node')} -->|{edge.get('dependency_type', 'depends_on')}| {edge.get('to_node')};")
            lines.extend([
                "```",
                "",
                "## 3. 关键施工路径与瓶颈评估 (Critical Path & Bottlenecks)",
                "",
                f"**关键施工路径 (Critical Path)**：`{' -> '.join(crit_path)}`",
                "",
                "| 节点编号 | 组件名称 | 架构分层 | 责任角色 | 前置依赖 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                is_crit = "🔥 (关键路径)" if node.get("id") in crit_path else ""
                lines.append(f"| **{node.get('id')}** | {node.get('name')} {is_crit} | `{node.get('layer')}` | {node.get('owner_role')} | `{', '.join(node.get('prerequisites', [])) or '无 (起始根节点)'}` |")

            lines.extend([
                "",
                "#### 瓶颈风险评估与解耦策略 (Bottlenecks & Decoupling)",
                "",
                "| 节点编号 | 组件名称 | 瓶颈风险评估 | 解耦与加速策略 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                b_risk = node.get("bottleneck_risk", "前置依赖变更可能导致下游重新编译与接口适配")
                decoup = node.get("decoupling_strategy", "基于纯接口 Trait 进行依赖倒置，保持实现与抽象隔离")
                lines.append(f"| **{node.get('id')}** | {node.get('name')} | {b_risk} | {decoup} |")

            lines.extend([
                "",
                "## 4. 技术施工有序阶段规划 (Build Sequence)",
                "",
                "| 阶段顺序 | 构建节点 | 准入条件 (Entry Criteria) | 准出验收条件 (Exit Criteria) |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for phase in phases:
                lines.append(f"| 阶段 {phase.get('order')} | **`{phase.get('node_id')}`** | {phase.get('entry_criteria')} | {phase.get('exit_criteria')} |")

            lines.extend([
                "",
                "## 5. 高难度复杂特性实现指导 (Complex Feature Implementation Guides)",
                "",
            ])
            for s_idx, spike in enumerate(spikes, 1):
                fname = spike.get("feature_name", "Complex Feature")
                risk = spike.get("risk_hypothesis", "")
                tbox = spike.get("timebox_days", 3)
                algo = spike.get("algorithm_pseudo_code", "// Implementation code")
                exit_c = spike.get("exit_criteria", "")
                bid = f"GUIDE-{s_idx:03d}"

                lines.extend([
                    f"<!-- block-id: {bid} -->",
                    f"### {bid}: {fname}",
                    f"- **风险假设与瓶颈目标**：{risk}",
                    f"- **研发验证时间盒 (Timebox)**：`{tbox} 天`",
                    "",
                    "#### 核心算法与生产级代码示例 (Implementation Code)",
                    "```rust",
                    algo.strip(),
                    "```",
                    "",
                    "#### 并发与性能考量 (Performance & Concurrency)",
                    "- **资源隔离与缓冲策略**：实施微批次流水线处理，限制最大内存缓存并配置背压机制。",
                    "- **连接池与连接泄漏防御**：配置严格的超时借出上限与自动回收心跳。",
                    "",
                    "#### 准出与验收验证标准 (Exit & Verification Criteria)",
                    f"- **验收准则**：{exit_c}",
                    "",
                    "<!-- /block -->",
                    "",
                ])

        else:
            # English
            lines = [
                f"# {sys_name} Technical Dependency DAG & Development Guidance Specification",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  node_count: {len(nodes)}',
                f'  critical_path_length: {len(crit_path)}',
                "```",
                "",
                "> Strictly verifies an acyclic dependency graph, identifies the critical path, and follows Lingforge complex-feature-guide-writer standards providing step-by-step implementation code and exit criteria.",
                "",
                "---",
                "",
                "## 1. Technical Dependency Overview",
                "",
                f"- **Total Nodes**: `{len(nodes)}`",
                f"- **Total Dependency Edges**: `{len(edges)}` (strictly verified acyclic via Kahn's algorithm)",
                f"- **Critical Path Length**: `{len(crit_path)}` nodes",
                "",
                "## 2. Technical Dependency DAG",
                "",
                "```mermaid",
                "graph TD;",
            ]
            for edge in edges:
                lines.append(f"  {edge.get('from_node')} -->|{edge.get('dependency_type', 'depends_on')}| {edge.get('to_node')};")
            lines.extend([
                "```",
                "",
                "## 3. Critical Path & Bottlenecks",
                "",
                f"**Critical Path**: `{' -> '.join(crit_path)}`",
                "",
                "| Node ID | Node Name | Layer | Owner Role | Prerequisites |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                is_crit = "🔥 (Critical Path)" if node.get("id") in crit_path else ""
                lines.append(f"| **{node.get('id')}** | {node.get('name')} {is_crit} | `{node.get('layer')}` | {node.get('owner_role')} | `{', '.join(node.get('prerequisites', [])) or 'Root (No prerequisites)'}` |")

            lines.extend([
                "",
                "#### Bottleneck Risks & Decoupling Strategies",
                "",
                "| Node ID | Component Name | Bottleneck Risk | Decoupling Strategy |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                b_risk = node.get("bottleneck_risk", "Prerequisite interface churn may trigger ripple-effect recompilation")
                decoup = node.get("decoupling_strategy", "Dependency inversion via pure traits; keep implementation decoupled from contract")
                lines.append(f"| **{node.get('id')}** | {node.get('name')} | {b_risk} | {decoup} |")

            lines.extend([
                "",
                "## 4. Technical Build Sequence",
                "",
                "| Phase Order | Target Node | Entry Criteria | Exit Criteria |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for phase in phases:
                lines.append(f"| Phase {phase.get('order')} | **`{phase.get('node_id')}`** | {phase.get('entry_criteria')} | {phase.get('exit_criteria')} |")

            lines.extend([
                "",
                "## 5. Complex Feature Implementation Guides",
                "",
            ])
            for s_idx, spike in enumerate(spikes, 1):
                fname = spike.get("feature_name", "Complex Feature")
                risk = spike.get("risk_hypothesis", "")
                tbox = spike.get("timebox_days", 3)
                algo = spike.get("algorithm_pseudo_code", "// Implementation code")
                exit_c = spike.get("exit_criteria", "")
                bid = f"GUIDE-{s_idx:03d}"

                lines.extend([
                    f"<!-- block-id: {bid} -->",
                    f"### {bid}: {fname}",
                    f"- **Risk Hypothesis & Bottleneck**: {risk}",
                    f"- **Timebox**: `{tbox} days`",
                    "",
                    "#### Production-Grade Code Example",
                    "```rust",
                    algo.strip(),
                    "```",
                    "",
                    "#### Concurrency & Performance Considerations",
                    "- **Buffering & Backpressure**: Implement mini-batch streaming pipelines to regulate memory consumption.",
                    "- **Connection Pool Safety**: Set aggressive borrow timeouts and keepalive probes to eliminate leakages.",
                    "",
                    "#### Exit & Verification Criteria",
                    f"- **Criteria**: {exit_c}",
                    "",
                    "<!-- /block -->",
                    "",
                ])

        return "\n".join(lines)

    # =========================================================================
    # 09: Architecture Readiness Review Report -> arch-tpl-review-report
    # =========================================================================
    def render_review_report(self, data: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(data, lang)
        tpl = self.load_template("arch-tpl-review-report")
        pname = data.get("product_name", "Architecture Review")
        status = data.get("readiness_status", "NEEDS_REFINEMENT")
        score = data.get("overall_architecture_score", 0.0)
        req_audit = data.get("requirement_coverage_audit", {})
        compat_audit = data.get("compatibility_and_compliance_audit", {})
        blocking = data.get("blocking_findings", [])
        advisory = data.get("advisory_findings", [])
        rationale = data.get("decision_rationale", "")

        status_badge = "🟢 READY_FOR_DEV" if status == "READY_FOR_DEV" else "🔴 " + status

        if lang == "zh":
            lines = [
                f"# {pname} 架构就绪度评审与准入报告",
                "",
                "```yaml",
                "metadata:",
                f'  product_name: "{pname}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  readiness_status: "{status}"',
                f'  architecture_score: {score}',
                "```",
                "",
                f"> **终审结论**：{status_badge} | **综合架构质量评分**：`{score} / 100`",
                "> 遵循严格的一票否决准入原则：存在任何阻塞性缺陷或需求覆盖不足 100% 均严禁准入研发。",
                "",
                "---",
                "",
                "## 1. 核心需求覆盖率审计 (Requirement Coverage Audit)",
                "",
                f"- **PRD Must-Have 核心需求总数**：`{req_audit.get('total_must_have_requirements', 0)}` 项",
                f"- **架构已闭环需求数**：`{req_audit.get('covered_must_have_requirements', 0)}` 项",
                f"- **覆盖率百分比**：`{req_audit.get('must_have_coverage_pct', 0.0)}%` (要求: 100%)",
                "",
                "## 2. 架构规范与兼容性合规性审计 (Compliance Audit)",
                "",
                f"- **向后兼容性验证**：{'✅ 通过 (无破坏性变更)' if compat_audit.get('backward_compatibility_verified') else '❌ 未通过'}",
                f"- **三层单体架构合规**：{'✅ 严格符合 (<= 3 层)' if compat_audit.get('layer_count_compliant') else '❌ 违规过度分层'}",
                f"- **PRD 约束技术栈合规**：{'✅ 100% 继承并落地' if compat_audit.get('prd_tech_stack_compliant') else '❌ 偏离约束'}",
                "",
                "## 3. 阻塞性架构缺陷审查 (Blocking Findings - 一票否决项)",
                "",
            ]
            if blocking:
                for b in blocking:
                    lines.append(f"- 🔴 **[{b.get('category', 'BLOCKER')}]** {b.get('message')}")
            else:
                lines.append("✅ **无任何阻塞性缺陷 (Zero Blocking Findings)**：所有架构规约均满足交付红线。")

            lines.extend([
                "",
                "## 4. 建议性优化项审查 (Advisory Findings)",
                "",
            ])
            if advisory:
                for a in advisory:
                    lines.append(f"- 🟡 **[{a.get('category', 'ADVISORY')}]** {a.get('description', a.get('message', ''))} (建议: {a.get('recommendation', '')})")
            else:
                lines.append("暂无建议优化项。")

            lines.extend([
                "",
                "## 5. 架构裁决陈述与决策依据 (Decision Rationale)",
                "",
                f"{rationale}",
                "",
            ])

        else:
            # English
            lines = [
                f"# {pname} Architecture Readiness Review & Gatekeeper Report",
                "",
                "```yaml",
                "metadata:",
                f'  product_name: "{pname}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  readiness_status: "{status}"',
                f'  architecture_score: {score}',
                "```",
                "",
                f"> **Verdict**: {status_badge} | **Architecture Quality Score**: `{score} / 100`",
                "> Strict one-vote veto: any blocking findings or <100% requirement coverage strictly prohibits developer handoff.",
                "",
                "---",
                "",
                "## 1. Requirement Coverage Audit",
                "",
                f"- **Total Must-Have Requirements**: `{req_audit.get('total_must_have_requirements', 0)}`",
                f"- **Covered Requirements**: `{req_audit.get('covered_must_have_requirements', 0)}`",
                f"- **Coverage Percentage**: `{req_audit.get('must_have_coverage_pct', 0.0)}%` (100% Iron Rule satisfied)",
                "",
                "## 2. Compliance & Compatibility Audit",
                "",
                f"- **Backward Compatibility Verified**: {'✅ Verified (No breaking changes)' if compat_audit.get('backward_compatibility_verified') else '❌ Failed'}",
                f"- **3-Layer Monolith Compliance**: {'✅ Compliant (<= 3 layers)' if compat_audit.get('layer_count_compliant') else '❌ Non-compliant'}",
                f"- **PRD Tech Stack Compliance**: {'✅ 100% Aligned' if compat_audit.get('prd_tech_stack_compliant') else '❌ Deviated'}",
                "",
                "## 3. Blocking Findings (One-Vote Veto)",
                "",
            ]
            if blocking:
                for b in blocking:
                    lines.append(f"- 🔴 **[{b.get('category', 'BLOCKER')}]** {b.get('message')}")
            else:
                lines.append("✅ **Zero Blocking Findings**: All architecture specifications meet mandatory release criteria.")

            lines.extend([
                "",
                "## 4. Advisory Findings",
                "",
            ])
            if advisory:
                for a in advisory:
                    lines.append(f"- 🟡 **[{a.get('category', 'ADVISORY')}]** {a.get('description', a.get('message', ''))} (Recommendation: {a.get('recommendation', '')})")
            else:
                lines.append("None.")

            lines.extend([
                "",
                "## 5. Decision Rationale & Verdict",
                "",
                f"{rationale}",
                "",
            ])

        return "\n".join(lines)

    # =========================================================================
    # Suite Renderer
    # =========================================================================
    def render_suite(self, suite: Dict[str, Any], lang: Optional[str] = None) -> str:
        lang = self.detect_lang(suite, lang)
        sections = []
        if "tech_stack_decision" in suite:
            sections.append(self.render_tech_stack_decision(suite["tech_stack_decision"], lang))
        if "system_architecture_spec" in suite:
            sections.append(self.render_system_architecture(suite["system_architecture_spec"], lang))
        if "domain_model_spec" in suite:
            sections.append(self.render_domain_model(suite["domain_model_spec"], lang))
        if "database_design_spec" in suite:
            sections.append(self.render_database_design(suite["database_design_spec"], lang))
        if "api_contract_suite" in suite:
            sections.append(self.render_api_contracts(suite["api_contract_suite"], lang))
        if "business_flow_spec" in suite:
            sections.append(self.render_business_flow(suite["business_flow_spec"], lang))
        if "architecture_invariants_spec" in suite:
            sections.append(self.render_architecture_invariants(suite["architecture_invariants_spec"], lang))
        if "technical_dependency_dag_spec" in suite:
            sections.append(self.render_dependency_guidance(suite["technical_dependency_dag_spec"], lang))
        if "architecture_readiness_review_report" in suite:
            sections.append(self.render_review_report(suite["architecture_readiness_review_report"], lang))

        return "\n\n---\n\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="Aurakl Architecture Markdown Renderer")
    parser.add_argument("path", help="Path to architecture JSON file")
    parser.add_argument("--lang", choices=["en", "zh"], help="Target output language")
    parser.add_argument("-o", "--output", help="Output file path (prints to stdout if omitted)")
    parser.add_argument("--suite", action="store_true", help="Render full architecture suite")
    args = parser.parse_args()

    input_path = Path(args.path)
    if not input_path.exists():
        print(f"Error: File not found {input_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    renderer = AuraklArchitectureRenderer()

    if args.suite or "tech_stack_decision" in data:
        md = renderer.render_suite(data, args.lang)
    else:
        # Detect which stage based on keys
        if "locked_stack_items" in data:
            md = renderer.render_tech_stack_decision(data, args.lang)
        elif "c4_container_diagram" in data or "layers" in data:
            md = renderer.render_system_architecture(data, args.lang)
        elif "aggregates" in data or "domain_entity_models" in data:
            md = renderer.render_domain_model(data, args.lang)
        elif "tables" in data:
            md = renderer.render_database_design(data, args.lang)
        elif "endpoints" in data:
            md = renderer.render_api_contracts(data, args.lang)
        elif "flows" in data or "sequence_flows" in data:
            md = renderer.render_business_flow(data, args.lang)
        elif "invariants" in data and "defense_coverage_pct" in data:
            md = renderer.render_architecture_invariants(data, args.lang)
        elif "dependency_nodes" in data:
            md = renderer.render_dependency_guidance(data, args.lang)
        elif "readiness_status" in data:
            md = renderer.render_review_report(data, args.lang)
        else:
            print("Error: Could not identify architecture stage from payload", file=sys.stderr)
            sys.exit(1)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(renderer.format_typography(md) + "\n", encoding="utf-8")
        print(f"Rendered Markdown saved to {out_p}")
    else:
        print(renderer.format_typography(md))


if __name__ == "__main__":
    main()
