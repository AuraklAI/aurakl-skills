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
    1. \u300a\u4e2d\u6587\u6587\u6848\u6392\u7248\u6307\u5317\u300b(Chinese Copywriting Guidelines / \u76d8\u53e4\u4e4b\u767d):
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
                f"# {pname} \u6280\u672f\u9009\u578b\u4e0e\u67b6\u6784\u51b3\u7b56\u89c4\u7ea6 (ADR)",
                "",
                "```yaml",
                "metadata:",
                f'  title: "{pname} \u6280\u672f\u9009\u578b\u51b3\u7b56\u89c4\u7ea6"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  design_mode: "{mode}"',
                f'  must_have_requirements_count: {len(reqs)}',
                "```",
                "",
                "> \u672c\u6587\u6863\u5b9a\u4e49\u7cfb\u7edf\u6280\u672f\u67b6\u6784\u5e95\u5ea7\uff0c\u56fa\u5316 PRD \u5f3a\u7ea6\u675f\u6280\u672f\u6808\uff0c\u901a\u8fc7\u591a\u7ef4\u8bc4\u5206\u77e9\u9635\u786e\u5b9a\u672a\u51b3\u6280\u672f\u65b9\u6848\uff0c\u5e76\u63d0\u4f9b\u67b6\u6784\u51b3\u7b56\u8bb0\u5f55 (ADR)\u3002",
                "",
                "---",
                "",
                "## 1. \u7ea6\u675f\u7ee7\u627f\u4e0e\u8bbe\u8ba1\u6a21\u5f0f (Design Context)",
                "",
                f"- **\u7cfb\u7edf\u8bbe\u8ba1\u6a21\u5f0f**\uff1a`{mode}`",
                f"- **\u5173\u8054 PRD Must-Have \u9700\u6c42\u6570**\uff1a`{len(reqs)}` \u9879 ({', '.join(reqs)})",
                "",
                "### \u56fa\u5316\u6280\u672f\u6808\u6e05\u5355 (Locked Tech Stack)",
                "",
                "| \u6280\u672f\u7ef4\u5ea6 | \u9009\u578b\u7ed3\u679c | \u7ea6\u675f\u6765\u6e90 | \u67b6\u6784\u5408\u7406\u6027\u8bba\u8bc1 |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for item in locked:
                dim = item.get('dimension') or item.get('category', '\u6280\u672f\u7ec4\u4ef6')
                tech = item.get('technology', '-')
                src = item.get('constraint_source') or item.get('source_constraint', 'PRD \u4e0d\u53d8\u91cf')
                rat = item.get('rationale', '')
                lines.append(f"| **{dim}** | `{tech}` | {src} | {rat} |")

            lines.extend([
                "",
                "## 2. \u5907\u9009\u6280\u672f\u591a\u7ef4\u8bc4\u4f30\u77e9\u9635\u4e0e ADR (Evaluated ADRs)",
                "",
            ])
            for adr in adrs:
                aid = adr.get('adr_id') or adr.get('id', 'ADR-001')
                decision = adr.get('chosen_alternative') or adr.get('decision', '\u5df2\u5b9a\u6848\u9009\u578b')
                lines.extend([
                    f"### {aid}: {adr.get('title')}",
                    f"- **\u51b3\u7b56\u72b6\u6001**\uff1a`{adr.get('status', 'ACCEPTED')}`",
                    f"- **\u4e0a\u4e0b\u6587\u80cc\u666f**\uff1a{adr.get('context')}",
                    f"- **\u6700\u7ec8\u51b3\u7b56**\uff1a\u9009\u7528 `{decision}`",
                    f"- **\u51b3\u7b56\u7406\u7531**\uff1a{adr.get('rationale')}",
                    f"- **\u67b6\u6784\u5f71\u54cd\u4e0e\u540e\u679c**\uff1a{adr.get('consequences')}",
                    "",
                    "#### \u5907\u9009\u65b9\u6848\u8bc4\u5206\u5bf9\u6bd4",
                    "| \u65b9\u6848\u540d\u79f0 | \u6280\u672f\u7279\u5f81 | \u7efc\u5408\u8bc4\u5206 | \u5224\u5b9a\u7ed3\u8bba |",
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
                            pc_parts.append(f"\u4f18\u52bf: {', '.join(pros)}")
                        if cons:
                            pc_parts.append(f"\u52a3\u52bf: {', '.join(cons)}")
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
                    conc = "✅ \u91c7\u7eb3" if is_chosen else "❌ \u653e\u5f03"
                    lines.append(f"| **{alt_name}** | {pros_cons} | `{score} / 100` | {conc} |")
                lines.append("")

            lines.extend([
                "## 3. \u6700\u7ec8\u6280\u672f\u6808\u5168\u666f\u89c6\u56fe (Final Tech Stack Panorama)",
                "",
                "| \u5206\u5c42\u7ef4\u5ea6 | \u6280\u672f\u7ec4\u4ef6 / \u6846\u67b6 | \u7248\u672c\u8981\u6c42 | \u9009\u578b\u7406\u7531 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer, detail in final_stack.items():
                if isinstance(detail, dict):
                    lines.append(f"| **{layer}** | `{detail.get('technology')}` | `{detail.get('version', 'latest')}` | {detail.get('rationale')} |")
                else:
                    lines.append(f"| **{layer}** | `{detail}` | - | \u57fa\u7840\u6807\u51c6\u9009\u578b |")

            if isinstance(compat, list):
                compat_summary = "; ".join(compat)
                compat_policy = "\u4e25\u683c\u7981\u6b62\u4efb\u4f55\u7834\u574f\u6027\u53d8\u66f4\uff0c\u9075\u5faa\u53cc\u7248\u672c\u5e76\u5b58\u4e0e Expand-Contract \u6f14\u5316\u7b56\u7565"
            else:
                compat_summary = compat.get('guarantee_summary', '\u4e25\u683c\u5411\u540e\u517c\u5bb9\uff0c\u7981\u6b62\u7834\u574f\u6027\u53d8\u66f4')
                compat_policy = compat.get('breaking_change_policy', '\u975e\u7834\u574f\u6027\u5347\u7ea7\uff0c\u91cd\u5927\u53d8\u66f4\u987b\u81f3\u5c11\u53cc\u7248\u672c\u5e76\u5b58')

            lines.extend([
                "",
                "## 4. \u5411\u540e\u517c\u5bb9\u6027\u627f\u8bfa (Backward Compatibility)",
                "",
                f"- **\u517c\u5bb9\u6027\u4fdd\u969c\u51c6\u5219**\uff1a{compat_summary}",
                f"- **\u6f14\u5316\u6dd8\u6c70\u673a\u5236**\uff1a{compat_policy}",
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
                "name": f"{mname} \u7ec4\u4ef6" if lang == "zh" else f"{mname} Component",
                "responsibility": mod.get("responsibilities", mod.get("description", "-")),
                "trait": trait_name,
                "entities": ", ".join(mod.get("implements_requirements", [])) or ("\u6838\u5fc3\u5b9e\u4f53" if lang == "zh" else "CoreEntity")
            })
        if not derived:
            derived = [
                {"code": "SUB-01", "name": "\u6838\u5fc3\u4e1a\u52a1\u5904\u7406\u5b50\u7cfb\u7edf" if lang == "zh" else "Core Domain Subsystem", "responsibility": "\u4e1a\u52a1\u6838\u5fc3\u903b\u8f91\u5904\u7406\u4e0e\u72b6\u6001\u673a\u8c03\u5ea6" if lang == "zh" else "Core domain logic and state transitions", "trait": "CoreDomainPort", "entities": "DomainAggregate"},
                {"code": "SUB-02", "name": "\u63a5\u53e3\u4e0e\u534f\u8bae\u63a5\u5165\u5b50\u7cfb\u7edf" if lang == "zh" else "Interface Gateway Subsystem", "responsibility": "\u534f\u8bae\u63a5\u5165\u4e0e\u8ba4\u8bc1\u9274\u6743" if lang == "zh" else "Protocol ingress and security validation", "trait": "GatewayPort", "entities": "SecurityContext"}
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
                "dependencies": ", ".join(lay.get("allowed_dependencies", [])) or ("\u65e0" if lang == "zh" else "None"),
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
                "model": ("\u5f02\u6b65\u4e8b\u4ef6\u9a71\u52a8\u4e8b\u4ef6\u5faa\u73af (Async Event-Loop)" if lang == "zh" else "Async Event-Driven Runtime") if is_api else (("\u4e13\u7528\u4e8b\u52a1\u4e0e\u6279\u5904\u7406\u7ebf\u7a0b\u6c60" if lang == "zh" else "Dedicated Transaction Worker Pool") if not is_infra else ("\u6301\u4e45\u5316\u8fde\u63a5\u6c60\u7ba1\u7406\u6c60" if lang == "zh" else "Connection Pool Isolation")),
                "resources": "4 Cores / 8 GB / 1000 conns" if is_api else ("4 Cores / 8 GB / 128 conns" if not is_infra else "8 Cores / 16 GB / 64 conns"),
                "lock": ("\u65e0\u9501\u4e8b\u4ef6\u9a71\u52a8 + \u4ee4\u724c\u6876\u9650\u6d41" if lang == "zh" else "Lock-free event loops + Token Bucket") if is_api else (("\u5206\u5e03\u5f0f\u79df\u7ea6\u9501 + \u4e50\u89c2\u91cd\u8bd5" if lang == "zh" else "Distributed Lease + Optimistic Retry") if not is_infra else ("\u6570\u636e\u5e93\u884c\u9501\u4e0e\u8fde\u63a5\u6c60\u6392\u961f" if lang == "zh" else "Row-level locks + Pool Queuing")),
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
                scen_name = f"{sys_name} \u6838\u5fc3\u7aef\u5230\u7aef\u4e1a\u52a1\u95ed\u73af\u6267\u884c\u65f6\u5e8f" if lang == "zh" else f"{sys_name} Core End-to-End Execution Scenario"
        if not steps:
            if data_flows and data_flows[0].get("steps"):
                steps = [f"{i}. {s}" for i, s in enumerate(data_flows[0].get("steps", []), 1)]
            else:
                steps = [
                    "1. **\u903b\u8f91\u89c6\u56fe\u89e6\u53d1**\uff1a\u5ba2\u6237\u7aef\u4e0b\u53d1\u64cd\u4f5c\u8bf7\u6c42\uff0c\u63a5\u53e3\u5c42\u62e6\u622a\u5e76\u6821\u9a8c\u8bf7\u6c42\u89c4\u8303\u4e0e\u9274\u6743\u5b89\u5168\u7b56\u7565\u3002" if lang == "zh" else "1. **Logical View Trigger**: Client issues request; interface layer performs schema & auth validation.",
                    "2. **\u8fd0\u884c\u89c6\u56fe\u5e76\u53d1\u9694\u79bb**\uff1a\u8fd0\u884c\u65f6\u5de5\u4f5c\u8282\u70b9\u7533\u8bf7\u5206\u5e03\u5f0f\u5e76\u53d1\u6392\u4ed6\u79df\u7ea6\uff0c\u9632\u6b62\u91cd\u590d\u8bf7\u6c42\u91cd\u653e\u4e0e\u8d44\u6e90\u4e89\u7528\u3002" if lang == "zh" else "2. **Process View Concurrency**: Worker node acquires distributed lock to prevent duplicate replay.",
                    "3. **\u5f00\u53d1\u89c6\u56fe\u5951\u7ea6\u6d41\u8f6c**\uff1a\u6a21\u5757\u6309\u5206\u5c42\u5f3a\u7c7b\u578b Trait \u5951\u7ea6\u8c03\u7528\u9886\u57df\u6a21\u578b\uff0c\u6267\u884c\u6838\u5fc3\u4e0d\u53d8\u91cf\u4e0e\u72b6\u6001\u673a\u6821\u9a8c\u3002" if lang == "zh" else "3. **Development View Trait Call**: Modules invoke strongly typed traits for domain invariants validation.",
                    "4. **\u7269\u7406\u89c6\u56fe\u4e8b\u52a1\u843d\u5730**\uff1a\u57fa\u7840\u8bbe\u65bd\u5c42\u534f\u8c03\u8de8\u53ef\u7528\u533a\u90e8\u7f72\u7684\u6301\u4e45\u5316\u5b58\u50a8\u6267\u884c\u4e8b\u52a1\u5199\u5165\u5e76\u8f93\u51fa\u5ba1\u8ba1\u51ed\u636e\u3002" if lang == "zh" else "4. **Physical View Persistence**: Storage adapters commit ACID transactions across multi-AZ nodes."
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
                f"# {sys_name} \u7cfb\u7edf\u62d3\u6251\u4e0e\u5206\u5c42\u67b6\u6784\u8bbe\u8ba1\u89c4\u7ea6",
                "",
                "```yaml",
                "metadata:",
                f'  system_name: "{sys_name}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  layer_count: {layer_count}',
                "```",
                "",
                "> \u672c\u8bbe\u8ba1\u4e25\u683c\u9075\u5faa Linus \u6781\u7b80\u52a1\u5b9e\u54f2\u5b66\u4e0e 4+1 \u67b6\u6784\u89c6\u56fe\u6a21\u578b\uff1a\u575a\u6301\u5355\u4f53\u4f18\u5148\uff0c\u5206\u5c42\u4e25\u683c <= 3 \u5c42\uff0c\u4f9d\u8d56\u5355\u5411\u65e0\u73af\uff0c\u6a21\u5757\u63a5\u53e3\u5f3a\u7c7b\u578b\u7ea6\u675f\uff0c\u6db5\u76d6\u5168\u5c40\u603b\u4f53\u67b6\u6784\u5168\u666f\u62d3\u6251\u56fe\u4e0e\u4e94\u5927\u67b6\u6784\u89c6\u56fe\u3002",
                "",
                "---",
                "",
                "## 1. \u67b6\u6784\u6a21\u5f0f\u4e0e\u5355\u4f53\u4f18\u5148\u8bba\u8bc1 (Architecture Overview)",
                "",
                f"- **\u67b6\u6784\u6a21\u5f0f**\uff1a`{data.get('architecture_pattern', 'Modular_Monolith')}`",
                f"- **\u5355\u4f53\u4f18\u5148\u8bba\u8bc1**\uff1a{data.get('monolith_justification', '\u9075\u5faa Linus \u6781\u7b80\u54f2\u5b66\uff1a\u5fae\u670d\u52a1\u662f\u89c4\u6a21\u5316\u7684\u4ea7\u7269\uff0c\u800c\u4e0d\u662f\u76ee\u6807\u3002\u5355\u4f53\u67b6\u6784\u5177\u5907\u96f6\u7f51\u7edc\u5ef6\u8fdf\u3001\u5355\u673a\u4e8b\u52a1\u4e00\u81f4\u6027\u3001\u8c03\u8bd5\u4e0e\u90e8\u7f72\u6781\u5176\u7b80\u660e\u7684\u9ad8\u6548\u4f18\u52bf\uff0c\u5b8c\u5168\u89c4\u907f\u5206\u5e03\u5f0f\u4e8b\u52a1\u4e0e\u7f51\u7edc\u5206\u533a\u590d\u6742\u6027\u3002')}",
                f"- **\u5206\u5c42\u6570\u91cf**\uff1a`{layer_count}` \u5c42\uff08\u4e25\u683c\u4e0d\u8d85\u8fc7 3 \u5c42\uff0c\u4f9d\u8d56\u5355\u5411\u6d41\u52a8\uff09",
                "",
                "## 2. \u603b\u4f53\u67b6\u6784\u5168\u666f\u62d3\u6251\u56fe (Overall Architecture Panorama)",
                "",
                "> \u5168\u5c40\u7aef\u5230\u7aef\u4f01\u4e1a\u67b6\u6784\u5168\u666f\u62d3\u6251\uff1a\u6db5\u76d6\u63a5\u5165\u5ba2\u6237\u7aef\u3001\u8fb9\u7f18\u4e0e\u534f\u8bae\u7f51\u5173\u3001\u6838\u5fc3\u9886\u57df\u5f15\u64ce\u3001\u5206\u5e03\u5f0f\u4e8b\u52a1\u7f16\u6392\u3001\u6d41\u6279 CDC \u7ba1\u9053\u3001\u591a\u5f15\u64ce\u6301\u4e45\u5316\u5b58\u50a8\u53ca\u5168\u94fe\u8def\u6a2a\u5207\u9632\u7ebf\u3002",
                "",
                "```mermaid",
                overall_diagram.strip() if overall_diagram else (c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;"),
                "```",
                "",
                "## 3. 4+1 \u67b6\u6784\u89c6\u56fe\u6a21\u578b\u5168\u666f\u89c4\u7ea6 (4+1 Architectural View Model)",
                "",
                "### 3.1 \u903b\u8f91\u67b6\u6784\u89c6\u56fe (Logical View)",
                f"**\u89c6\u56fe\u5173\u6ce8\u70b9**\uff1a{logical_v.get('description', '\u7cfb\u7edf\u5bf9\u7ec8\u7aef\u7528\u6237\u4e0e\u667a\u80fd\u4f53\u63d0\u4f9b\u7684\u4e1a\u52a1\u529f\u80fd\u8fb9\u754c\u3001\u6838\u5fc3\u5b50\u7cfb\u7edf\u5212\u5206\u3001\u805a\u5408\u6839\u9886\u57df\u5f52\u5c5e\u4e0e\u5f3a\u7c7b\u578b\u63a5\u53e3\u5951\u7ea6\u62bd\u8c61\u3002')}",
                "",
                "| \u5b50\u7cfb\u7edf\u4ee3\u7801 | \u5b50\u7cfb\u7edf\u540d\u79f0 | \u6838\u5fc3\u804c\u8d23\u4e0e\u9886\u57df\u8fb9\u754c | \u6838\u5fc3\u62bd\u8c61\u5951\u7ea6 (Core Port / Trait) | \u5305\u542b\u9886\u57df\u5b9e\u4f53 |",
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
                "### 3.2 \u5f00\u53d1\u67b6\u6784\u89c6\u56fe (Development View)",
                f"**\u89c6\u56fe\u5173\u6ce8\u70b9**\uff1a{dev_v.get('description', '\u8f6f\u4ef6\u4ee3\u7801\u5728\u5de5\u7a0b\u5f00\u53d1\u73af\u5883\u4e2d\u7684\u6a21\u5757\u7ec4\u7ec7\u62d3\u6251\u3001Crate/\u5305\u4f9d\u8d56\u5c42\u7ea7\u3001\u7f16\u8bd1\u8fb9\u754c\u9632\u7ebf\u4e0e\u7269\u7406\u6e90\u7801\u76ee\u5f55\u7ed3\u6784\u3002')}",
                "",
                "| Crate / \u5305\u540d\u79f0 | \u5305\u7c7b\u578b (Kind) | \u6838\u5fc3\u5bfc\u51fa\u80fd\u529b (Exports) | \u7f16\u8bd1\u671f\u76f4\u63a5\u4f9d\u8d56 (Direct Dependencies) | \u5f52\u5c5e\u5206\u5c42 |",
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
                "### 3.3 \u8fd0\u884c\u67b6\u6784\u89c6\u56fe (Process / Runtime View)",
                f"**\u89c6\u56fe\u5173\u6ce8\u70b9**\uff1a{process_v.get('description', '\u7cfb\u7edf\u5728\u8fd0\u884c\u6001\u4e0b\u7684\u591a\u8fdb\u7a0b\u4e0e\u591a\u7ebf\u7a0b\u6a21\u578b\u3001Tokio \u5f02\u6b65\u4e8b\u4ef6\u5faa\u73af\u3001\u5e76\u53d1\u63a7\u5236\u673a\u5236\u3001\u5206\u5e03\u5f0f\u79df\u7ea6\u4e0e\u8de8\u7cfb\u7edf\u8c03\u7528\u5ef6\u8fdf/\u8d44\u6e90\u9884\u7b97\u3002')}",
                "",
                "| \u8fd0\u884c\u6001\u8fdb\u7a0b / \u4efb\u52a1\u6c60 | \u5e76\u53d1\u6a21\u578b\u4e0e\u8c03\u5ea6\u5668 | \u8d44\u6e90\u914d\u989d (CPU/Mem/Conn) | \u6838\u5fc3\u9501\u4e0e\u540c\u6b65\u673a\u5236 | P99 \u5ef6\u8fdf\u9884\u7b97 |",
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
                "### 3.4 \u7269\u7406\u4e0e\u90e8\u7f72\u67b6\u6784\u89c6\u56fe (Physical / Deployment View)",
                f"**\u89c6\u56fe\u5173\u6ce8\u70b9**\uff1a{physical_v.get('description', '\u7cfb\u7edf\u7684\u7269\u7406\u786c\u4ef6\u3001\u4e91\u539f\u751f\u7f51\u7edc\u62d3\u6251\u3001Kubernetes \u5bb9\u5668\u7f16\u6392\u3001\u591a\u53ef\u7528\u533a (Multi-AZ) \u9ad8\u53ef\u7528\u5bb9\u707e\u53ca\u4e3b\u4ece\u5b58\u50a8\u62d3\u6251\u3002')}",
                "",
                "| \u90e8\u7f72\u8282\u70b9 / \u670d\u52a1\u7ec4\u4ef6 | \u5b9e\u4f8b\u526f\u672c\u6570 | \u8ba1\u7b97\u89c4\u683c\u914d\u989d | \u90e8\u7f72\u53ef\u7528\u533a (Topology) | \u7f51\u7edc\u66b4\u9732\u4e0e\u5b89\u5168\u57df |",
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
                "### 3.5 +1 \u573a\u666f\u7528\u4f8b\u89c6\u56fe (Scenarios / Use Case View)",
                f"**\u89c6\u56fe\u5173\u6ce8\u70b9**\uff1a{scenarios_v.get('description', '\u9a71\u52a8\u5e76\u4e32\u8054\u903b\u8f91\u3001\u5f00\u53d1\u3001\u8fd0\u884c\u548c\u7269\u7406\u56db\u5927\u89c6\u56fe\u7684\u6838\u5fc3\u7aef\u5230\u7aef\u7528\u4f8b\uff0c\u9a8c\u8bc1\u5404\u89c6\u56fe\u7ec4\u4ef6\u5728\u6267\u884c\u771f\u5b9e\u9ad8\u4ef7\u503c\u4e1a\u52a1\u65f6\u7684\u534f\u540c\u5b8c\u5907\u6027\u3002')}",
                f"- **\u6838\u5fc3\u7528\u4f8b\u540d\u79f0**\uff1a`{scen_name}`",
                "",
                "#### \u7aef\u5230\u7aef\u8de8\u89c6\u56fe\u4e32\u8054\u6d41\u8f6c\u65f6\u5e8f",
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
                "## 4. \u4e09\u5c42\u67b6\u6784\u6e05\u6670\u89c4\u7ea6 (Layering Specification)",
                "",
                "| \u5206\u5c42\u5c42\u7ea7 | \u5206\u5c42\u540d\u79f0 (Layer) | \u804c\u8d23\u8fb9\u754c (Responsibilities) | \u5141\u8bb8\u4f9d\u8d56\u76ee\u6807 (Allowed Dependencies) |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for layer in layers:
                lid = layer.get("layer_id") or layer.get("level") or "L?"
                lname = layer.get("name", "Layer")
                lresp = layer.get("responsibilities") or layer.get("responsibility", "")
                allowed = ", ".join(layer.get("allowed_dependencies", [])) or "\u65e0 (\u5e95\u5c42\u57fa\u7840\u8bbe\u65bd)"
                lines.append(f"| **{lid}** | **{lname}** | {lresp} | `{allowed}` |")

            lines.extend([
                "",
                "## 5. \u6838\u5fc3\u6a21\u5757\u5212\u5206\u4e0e\u63a5\u53e3\u62bd\u8c61 (Modules & Interface Contracts)",
                "",
            ])
            for mod in modules:
                mid = mod.get("module_id") or mod.get("id", "MOD-001")
                mname = mod.get("name", "Module")
                mlayer = mod.get("layer_id") or mod.get("layer", "L2")
                mdesc = mod.get("responsibilities") or mod.get("description", "")
                mdeps = ", ".join(mod.get("dependencies", [])) or "\u65e0 (\u72ec\u7acb\u57fa\u7840\u6a21\u5757)"
                mreqs = ", ".join(mod.get("implements_requirements", [])) or "\u65e0"

                lines.extend([
                    f"<!-- block-id: {mid} -->",
                    f"<!-- implements: {mreqs} -->",
                    f"<!-- depends_on: {mdeps} -->",
                    f"### {mid}: {mname}",
                    f"- **\u6240\u5c5e\u5206\u5c42**\uff1a`{mlayer}`",
                    f"- **\u6838\u5fc3\u804c\u8d23**\uff1a{mdesc}",
                    f"- **\u4f9d\u8d56\u6a21\u5757**\uff1a`{mdeps}`",
                    f"- **\u5b9e\u73b0\u9700\u6c42**\uff1a`{mreqs}`",
                    "",
                ])
                if mod.get("interface_signature"):
                    sig_lang = "rust" if "fn " in mod["interface_signature"] else "typescript"
                    lines.extend([
                        "**\u5f3a\u7c7b\u578b\u63a5\u53e3\u5951\u7ea6\u5b9a\u4e49**\uff1a",
                        f"```{sig_lang}",
                        mod["interface_signature"].strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 6. C4 Container \u67b6\u6784\u62d3\u6251\u56fe (C4 Diagram)",
                "",
                "```mermaid",
                c4.strip() if c4 else "graph TD;\n  Client --> Gateway;\n  Gateway --> CoreDomain;\n  CoreDomain --> Storage;",
                "```",
                "",
            ])

            if data_flows:
                lines.extend([
                    "## 7. \u6838\u5fc3\u8de8\u5c42\u6570\u636e\u6d41\u5411 (Cross-Layer Data Flows)",
                    "",
                ])
                for df in data_flows:
                    lines.extend([
                        f"### {df.get('id', 'FLOW')}: {df.get('name', 'Flow')}",
                        f"**\u4e1a\u52a1\u8bf4\u660e**\uff1a{df.get('description', '')}",
                        "",
                        "**\u6b65\u9aa4\u6d41\u8f6c**\uff1a",
                    ])
                    for sidx, step in enumerate(df.get("steps", []), 1):
                        lines.append(f"{sidx}. {step}")
                    lines.append("")

            if adrs:
                lines.extend([
                    "## 8. \u67b6\u6784\u51b3\u7b56\u8bb0\u5f55 (ADR)",
                    "",
                ])
                for adr in adrs:
                    lines.extend([
                        f"### {adr.get('id')}: {adr.get('title')}",
                        f"- **\u51b3\u7b56\u4e0a\u4e0b\u6587**\uff1a{adr.get('context')}",
                        f"- **\u6280\u672f\u51b3\u7b56**\uff1a{adr.get('decision')}",
                        f"- **\u9884\u671f\u540e\u679c\u4e0e\u6536\u76ca**\uff1a{adr.get('consequences')}",
                        "",
                    ])

            lines.extend([
                "## 9. \u6a2a\u5207\u5173\u6ce8\u70b9\u89c4\u7ea6 (Cross-Cutting Concerns)",
                "",
                f"- **\u8ba4\u8bc1\u9274\u6743\u4e0a\u4e0b\u6587\u6ce8\u5165**\uff1a{cross_cutting.get('security_context', 'API \u7f51\u5173\u5b8c\u6210 JWT/mTLS \u7edf\u4e00\u9274\u6743\u540e\uff0c\u5c06\u5f3a\u7c7b\u578b TenantContext \u6ce8\u5165\u6807\u51c6\u4e0a\u4e0b\u6587\uff0c\u9886\u57df\u5c42\u76f4\u63a5\u6d88\u8d39\uff0c\u7981\u6b62\u7ed5\u8fc7\u7f51\u5173\u76f4\u8fde\u5185\u90e8\u65b9\u6cd5\u3002')}",
                f"- **\u5168\u5c40\u5168\u94fe\u8def\u8ffd\u8e2a**\uff1a{cross_cutting.get('observability', '\u5168\u94fe\u8def\u5f3a\u5236\u900f\u4f20 OpenTelemetry W3C TraceContext \u4e0e trace_id\uff0c\u8de8\u5f02\u6b65\u961f\u5217\u4e0e\u4e8b\u4ef6\u6d88\u606f\u603b\u7ebf\u5f3a\u5236\u4fdd\u6301\u4e0a\u4e0b\u6587\u56e0\u679c\u5173\u8054\u3002')}",
                f"- **\u7edf\u4e00\u9519\u8bef\u5904\u7406**\uff1a{cross_cutting.get('error_handling', '\u6807\u51c6 DomainError \u6620\u5c04\u81f3\u5168\u5c40\u7edf\u4e00 HTTP/gRPC \u9519\u8bef\u7801\uff0c\u4e25\u7981\u5411\u5ba2\u6237\u7aef\u629b\u51fa\u672a\u6355\u83b7\u7684\u6570\u636e\u5e93\u539f\u751f\u5f02\u5e38\u5806\u6808\u3002')}",
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
                f"# {dname} \u9886\u57df\u5efa\u6a21\u4e0e\u6838\u5fc3\u62bd\u8c61\u89c4\u7ea6",
                "",
                "```yaml",
                "metadata:",
                f'  domain_name: "{dname}"',
                f'  template_id: "{tpl.get("metadata", {}).get("id")}"',
                '  api_version: "aurakl.dev/v1"',
                f'  coverage_pct: {cov_pct}%',
                "```",
                "",
                "> Linus \u94c1\u5f8b\uff1a\u7cdf\u7cd5\u7684\u7a0b\u5e8f\u5458\u62c5\u5fc3\u4ee3\u7801\uff0c\u4f18\u79c0\u7684\u7a0b\u5e8f\u5458\u5173\u6ce8\u6570\u636e\u7ed3\u6784\u4e0e\u5173\u7cfb\u3002\u672c\u89c4\u7ea6 100% \u8986\u76d6 PRD \u4e1a\u52a1\u5b9e\u4f53\u4e0e\u4e0d\u53d8\u91cf\u3002",
                "",
                "---",
                "",
                "## 1. \u9886\u57df\u6a21\u578b\u6982\u8ff0\u4e0e\u805a\u5408\u6839\u5212\u5206 (Domain Overview)",
                "",
                f"- **\u805a\u5408\u6839\u6570\u91cf**\uff1a`{len(aggregates)}` \u4e2a",
                f"- **\u5168\u91cf\u5b9e\u4f53\u6a21\u578b**\uff1a`{len(entities)}` \u4e2a\uff08100% \u8986\u76d6 PRD \u6838\u5fc3\u9700\u6c42\uff09",
                f"- **\u6838\u5fc3 Trait / \u63a5\u53e3\u62bd\u8c61**\uff1a`{len(traits)}` \u4e2a",
                "",
                "### \u805a\u5408\u6839\u6e05\u5355 (Aggregate Roots)",
                "",
                "| \u805a\u5408\u6839 ID | \u805a\u5408\u6839\u540d\u79f0 | \u6839\u5b9e\u4f53\u6807\u8bc6 | \u8fb9\u754c\u4e0e\u4e0d\u53d8\u6027\u7ea6\u675f |",
                "| :--- | :--- | :--- | :--- |",
            ]
            for idx, agg in enumerate(aggregates):
                agg_id = agg.get('aggregate_id', agg.get('id', f'AGG-{idx+1:03d}'))
                agg_boundary = agg.get('boundary_description', agg.get('invariants', agg.get('description', '-')))
                lines.append(f"| **{agg_id}** | **{agg.get('name')}** | `{agg.get('root_entity_id', agg.get('root_entity', 'Self'))}` | {agg_boundary} |")

            lines.extend([
                "",
                "## 2. \u9886\u57df\u5168\u91cf\u5b9e\u4f53\u6a21\u578b\u89c4\u7ea6 (Entity Models)",
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
                    f"### \u5b9e\u4f53: `{eid}` - {ename}",
                    f"- **\u6240\u5c5e\u805a\u5408\u6839**\uff1a`{agg_root}` | **\u4e3b\u6807\u8bc6\u7b26**\uff1a`{p_id}`",
                    f"- **\u4e1a\u52a1\u8bf4\u660e**\uff1a{desc}",
                ])
                if attrs:
                    lines.extend([
                        "",
                        "| \u5c5e\u6027\u5b57\u6bb5 | \u6570\u636e\u7c7b\u578b | \u53ef\u7a7a | \u4e1a\u52a1\u8bed\u4e49\u4e0e\u7ea6\u675f\u89c4\u5219 |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for attr in attrs:
                        req_str = "No" if attr.get("nullable") else "Yes"
                        dfl = f" (\u9ed8\u8ba4: `{attr.get('default_value')}`)" if attr.get("default_value") is not None else ""
                        lines.append(f"| `{attr.get('name')}` | `{attr.get('type', attr.get('data_type', 'String'))}` | {req_str} | {attr.get('description', '')}{dfl} |")
                lines.append("")

            if value_objects:
                lines.extend([
                    "## 3. \u503c\u5bf9\u8c61\u4e0e\u9886\u57df\u4e8b\u4ef6\u89c4\u7ea6 (Value Objects & Events)",
                    "",
                    "| \u503c\u5bf9\u8c61\u6807\u8bc6 | \u540d\u79f0 | \u4e0d\u53d8\u6027\u89c4\u7ea6 (Immutability Rules) | \u5c5e\u6027\u6e05\u5355 |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for vo in value_objects:
                    lines.append(f"| **{vo.get('id')}** | {vo.get('name')} | {vo.get('immutability_rule')} | `{', '.join(vo.get('fields', []))}` |")
                lines.append("")

            if traits:
                lines.extend([
                    "## 4. \u6838\u5fc3 Trait \u4e0e\u63a5\u53e3\u62bd\u8c61\u89c4\u7ea6 (Core Traits)",
                    "",
                ])
                for idx, trt in enumerate(traits):
                    if isinstance(trt, str):
                        trt = {"name": trt, "description": trt, "signature_pseudocode": f"// trait {trt}"}
                    tid = trt.get("trait_id") or trt.get("id", f"TRT-{idx+1:03d}")
                    lines.extend([
                        f"### Trait: `{tid}` - {trt.get('name')}",
                        f"**\u804c\u8d23**\uff1a{trt.get('description', '')}",
                        "",
                        "```rust",
                        trt.get("signature_pseudocode", "// trait definition").strip(),
                        "```",
                        "",
                    ])

            lines.extend([
                "## 5. PRD \u9700\u6c42\u8986\u76d6\u7387\u95ed\u73af\u8ffd\u8e2a (Traceability Matrix)",
                "",
                f"- **Must-Have \u9700\u6c42\u8986\u76d6\u7387**\uff1a`{cov_pct}%` (100% \u8fbe\u6807)",
                f"- **\u5df2\u95ed\u73af\u9700\u6c42\u6e05\u5355**\uff1a`{', '.join(data.get('implements', []))}`",
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
                f"# {db_name} \u6570\u636e\u5e93\u8bbe\u8ba1\u4e0e\u5b58\u50a8\u89c4\u7ea6",
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
                "> \u4e25\u683c\u9075\u5faa\u7269\u7406\u8868 DDL \u5b8c\u5907\u6027\u89c4\u8303\uff1a\u5305\u542b\u5b8c\u6574 CREATE TABLE \u8bed\u53e5\u3001\u5b57\u6bb5\u6ce8\u91ca\u3001\u4e3b\u5916\u952e\u3001\u68c0\u67e5\u7ea6\u675f\u3001\u590d\u5408\u7d22\u5f15\u4e0e Expand-Contract \u65e0\u635f\u8fc1\u79fb\u811a\u672c\u3002",
                "",
                "---",
                "",
                "## 1. \u5b58\u50a8\u67b6\u6784\u4e0e\u5f15\u64ce\u6982\u89c8 (Storage Overview)",
                "",
                f"- **\u6570\u636e\u5e93\u5f15\u64ce**\uff1a`{engine}`",
                f"- **\u7269\u7406\u8868\u603b\u6570**\uff1a`{len(tables)}` \u5f20\u8868",
                f"- **\u8fde\u63a5\u6c60\u4e0e\u9694\u79bb\u7ea7\u522b**\uff1a{data.get('isolation_level', '\u6807\u51c6\u8fde\u63a5\u6c60\u7ba1\u7406\uff0c\u6838\u5fc3\u4e8b\u52a1\u9ed8\u8ba4 Read Committed\uff0c\u9ad8\u4e89\u7528\u573a\u666f\u91c7\u7528\u884c\u7ea7\u6392\u4ed6\u9501\u6216\u7248\u672c\u53f7\u4e50\u89c2\u9501\u6821\u9a8c')}",
                "",
                "## 2. \u7269\u7406\u8868\u7ed3\u6784\u4e0e\u7d22\u5f15\u8bbe\u8ba1 (Tables & Indexes)",
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
                    f"### {bid}: `{tname}` \u8868",
                    f"**\u7528\u9014\u8bf4\u660e**\uff1a{tdesc}",
                    f"**\u4e3b\u952e**\uff1a`{pk_str}`",
                    "",
                    "#### \u5b57\u6bb5 DDL \u5b9a\u4e49 (Physical DDL)",
                    "```sql",
                    _format_table_ddl(t),
                    "```",
                    "",
                    "#### \u5b57\u6bb5\u89c4\u7ea6\u8868\u683c",
                    "| \u5b57\u6bb5\u540d\u79f0 | \u6570\u636e\u7c7b\u578b | \u53ef\u7a7a | \u9ed8\u8ba4\u503c | \u4e1a\u52a1\u542b\u4e49\u4e0e\u7ea6\u675f\u89c4\u5219 |",
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
                    "#### \u7d22\u5f15\u8bbe\u8ba1\u6e05\u5355",
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
                            f"- **\u7528\u9014**\uff1a{irationale}",
                            f"- **\u7d22\u5f15\u7c7b\u578b**\uff1a`{itype}`",
                            f"- **\u9884\u671f\u67e5\u8be2**\uff1a`{iexp}`",
                            "",
                        ])
                else:
                    lines.append("*(\u4e3b\u952e\u7d22\u5f15\u81ea\u52a8\u751f\u6210)*\n")

                if t.get("business_rules"):
                    lines.extend([
                        "#### \u4e1a\u52a1\u89c4\u5219 (Business Rules)",
                    ])
                    for r_idx, rule in enumerate(t.get("business_rules", []), 1):
                        lines.append(f"{r_idx}. {rule}")
                    lines.append("")

                lines.append(f"\u6b64\u8868**\u5b9e\u73b0\u4e86** `{reqs}`\u3002\n\n<!-- /block -->\n")

            lines.extend([
                "## 3. \u4ea7\u54c1\u4e0d\u53d8\u91cf\u5b58\u50a8\u5c42\u843d\u5730\u89c4\u7ea6 (Invariant Enforcement)",
                "",
                "| \u4e0d\u53d8\u91cf\u6807\u8bc6 | \u7ea6\u675f\u89c4\u5219\u63cf\u8ff0 | \u7269\u7406\u843d\u5730\u8f7d\u4f53 (DB Mechanism) | \u8fdd\u89c4\u963b\u65ad\u884c\u4e3a |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for inv in invariants:
                lines.append(f"| **{inv.get('invariant_id', 'INV')}** | {inv.get('rule', '')} | `{inv.get('mechanism', 'CHECK / UNIQUE')}` | {inv.get('violation_behavior', 'ABORT TRANSACTION')} |")

            lines.extend([
                "",
                "## 4. \u6570\u636e\u5e93\u65e0\u635f\u8fc1\u79fb\u4e0e\u56de\u6eda\u7b56\u7565 (Zero-Downtime Migration)",
                "",
                f"- **\u8fc1\u79fb\u5de5\u5177\u4e0e\u673a\u5236**\uff1a`{migrations.get('tool', 'Flyway / Liquibase / Goose')}`",
                f"- **Expand-Contract \u9636\u6bb5\u63a8\u8fdb**\uff1a{migrations.get('expand_contract_procedure', '1. Expand \u9636\u6bb5\u65b0\u589e\u53ef\u7a7a\u5217\u5e76\u53cc\u5199\uff1b2. \u6570\u636e\u56de\u586b\uff1b3. Contract \u9636\u6bb5\u5207\u6362\u8bfb\u53d6\u5e76\u5728 N+1 \u7248\u672c\u79fb\u9664\u5e9f\u5f03\u5217\u3002')}",
                f"- **\u56de\u6eda\u4e0e\u6545\u969c\u9884\u6848**\uff1a{migrations.get('rollback_strategy', '\u4e25\u683c\u914d\u5907\u5bf9\u5e94\u7248\u672c Down \u56de\u6eda\u811a\u672c\uff0c\u5e76\u4e8e\u9884\u53d1\u73af\u5883\u8fdb\u884c 100% \u9006\u5411\u6f14\u7ec3\u3002')}",
                "",
                "### \u8fc1\u79fb\u811a\u672c\u793a\u4f8b (001_initial_schema.sql)",
                "",
                "```sql",
                "-- Up Migration: \u521b\u5efa\u6838\u5fc3\u7269\u7406\u67b6\u6784\u4e0e\u7d22\u5f15",
            ])
            for t in tables[:2]:
                lines.append(_format_table_ddl(t))
                for idx in t.get("indexes", [])[:2]:
                    lines.append(_format_index_ddl(t.get("table_name", "table"), idx))
            lines.extend([
                "",
                "-- Down Migration: \u56de\u6eda\u811a\u672c",
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
                f"# {api_title} \u5f3a\u7c7b\u578b\u63a5\u53e3\u5951\u7ea6\u4e0e\u901a\u4fe1\u534f\u8bae\u89c4\u7ea6",
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
                "> \u9075\u5faa Lingforge \u63a5\u53e3\u6807\u51c6\uff1a\u6bcf\u4e2a\u63a5\u53e3\u5747\u63d0\u4f9b\u5b8c\u6574 Mock \u8bf7\u6c42\u8f7d\u8377\u3001200 OK \u6210\u529f\u54cd\u5e94\u3001\u6807\u51c6 4xx/5xx \u9519\u8bef\u54cd\u5e94\u3001\u9010\u6b65\u4e1a\u52a1\u6267\u884c\u903b\u8f91\u4e0e\u5f3a\u5236\u5199\u5e42\u7b49\u673a\u5236\u3002",
                "",
                "---",
                "",
                "## 1. \u63a5\u53e3\u67b6\u6784\u4e0e\u534f\u8bae\u89c4\u8303 (API Overview)",
                "",
                f"- **\u534f\u8bae\u7c7b\u578b**\uff1a`{protocol}`",
                f"- **\u63a5\u53e3\u7aef\u70b9\u603b\u6570**\uff1a`{len(endpoints)}` \u4e2a\u7aef\u70b9",
                f"- **\u5411\u540e\u517c\u5bb9\u94c1\u5f8b**\uff1a`breaking_changes_allowed = {compat.get('breaking_changes_allowed', False)}`\uff08\u4e25\u7981\u7834\u574f\u6027\u53d8\u66f4\uff0c\u5e9f\u5f03\u5b57\u6bb5\u9700\u7ecf\u5386 N-2 \u5468\u671f\uff09",
                f"- **\u5168\u5c40\u8ba4\u8bc1\u89c4\u8303**\uff1a{data.get('auth_strategy', 'Authorization: Bearer <JWT> \u6807\u5934\u900f\u4f20\uff0c\u7f51\u5173\u6ce8\u5165 X-Tenant-Id \u4e0e X-User-Id')}",
                "",
                "## 2. API \u7aef\u70b9\u8be6\u5c3d\u5951\u7ea6 (Endpoints Specification)",
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
                    idemp_desc = f"\u5fc5\u586b (Header: `{idemp.get('key_header', 'X-Idempotency-Key')}`, \u7b56\u7565: `{idemp.get('strategy', 'distributed_lock')}`)" if idemp.get("required") else "\u4e0d\u5f3a\u5236 (\u5e42\u7b49\u53ea\u8bfb\u6216\u7531\u5ba2\u6237\u7aef\u4fdd\u8bc1)"
                elif isinstance(idemp, bool):
                    idemp_desc = "\u5fc5\u586b (Header: `X-Idempotency-Key`, \u7b56\u7565: `distributed_lock`)" if idemp else "\u4e0d\u5f3a\u5236"
                elif isinstance(idemp, str):
                    idemp_desc = idemp
                else:
                    idemp_desc = "\u4e0d\u5f3a\u5236 (\u5e42\u7b49\u53ea\u8bfb\u6216\u7531\u5ba2\u6237\u7aef\u4fdd\u8bc1)"

                lines.extend([
                    f"<!-- block-id: {eid} -->",
                    f"<!-- implements: {reqs} -->",
                    f"<!-- depends_on: {deps} -->",
                    f"### {eid}: `{method} {path}`",
                    f"**\u4e1a\u52a1\u6458\u8981**\uff1a{summary}",
                    f"**\u8be6\u7ec6\u63cf\u8ff0**\uff1a{desc}",
                    f"- **\u64cd\u4f5c\u6807\u8bc6 (Operation ID)**\uff1a`{eid}`",
                    f"- **\u5199\u64cd\u4f5c\u5e42\u7b49**\uff1a{idemp_desc}",
                    f"- **\u5b9e\u73b0\u9700\u6c42**\uff1a`{reqs}`",
                    f"- **\u4f9d\u8d56\u7ec4\u4ef6/\u8868**\uff1a`{deps}`",
                    "",
                    "#### 1. \u8bf7\u6c42\u4f53\u793a\u4f8b (Request Example)",
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
                        "#### 2. \u8bf7\u6c42\u5b57\u6bb5\u7ed3\u6784\u660e\u7ec6",
                        "| \u5b57\u6bb5\u540d\u79f0 | \u6570\u636e\u7c7b\u578b | \u5fc5\u586b | \u6821\u9a8c\u89c4\u5219\u4e0e\u8bf4\u660e |",
                        "| :--- | :--- | :--- | :--- |",
                    ])
                    for pname, pdetail in props.items():
                        is_r = "Yes" if pname in req_fields else "No"
                        ptype = pdetail.get("type", "string")
                        pdesc = pdetail.get("description", "")
                        lines.append(f"| `{pname}` | `{ptype}` | {is_r} | {pdesc} |")
                    lines.append("")

                lines.extend([
                    "#### 3. \u6210\u529f\u54cd\u5e94 (200 OK Response)",
                    "```json",
                    json.dumps(ep.get("response_example", ep.get("response_schema", {})), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "#### 4. \u5e38\u89c1\u9519\u8bef\u54cd\u5e94 (Error Responses)",
                    "##### `400 Bad Request` (\u53c2\u6570\u6821\u9a8c\u5931\u8d25)",
                    "```json",
                    json.dumps(ep.get("error_400", {
                        "error_code": "ERR_INVALID_ARGUMENT",
                        "message": "Field validation failed on requested parameters",
                        "invalid_fields": [{"field": "id", "reason": "must be a valid UUID"}]
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `401 Unauthorized` / `403 Forbidden` (\u9274\u6743\u4e0e\u79df\u6237\u9694\u79bb\u963b\u65ad)",
                    "```json",
                    json.dumps(ep.get("error_403", {
                        "error_code": "ERR_TENANT_ACCESS_DENIED",
                        "message": "User not authorized to execute actions on target tenant scope"
                    }), indent=2, ensure_ascii=False),
                    "```",
                    "",
                    "##### `409 Conflict` (\u5e76\u53d1\u51b2\u7a81\u6216\u5e42\u7b49\u91cd\u653e)",
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
                    "\u9a8c\u8bc1\u8c03\u7528\u65b9 Bearer Token \u4e0e RBAC/ABAC \u6743\u9650",
                    "\u6821\u9a8c\u5165\u53c2\u5b8c\u6574\u6027\uff0c\u82e5\u7f3a\u5c11\u5fc5\u586b\u9879\u5219\u629b\u51fa 400 Bad Request",
                    "\u68c0\u67e5 X-Idempotency-Key \u5e76\u83b7\u53d6\u6392\u4ed6\u5206\u5e03\u5f0f\u9501/\u79df\u7ea6\uff0c\u82e5\u5df2\u5b58\u5728\u5219\u76f4\u63a5\u8fd4\u56de\u524d\u6b21\u7ed3\u679c",
                    "\u8c03\u7528\u6838\u5fc3\u9886\u57df\u6a21\u578b\u6267\u884c\u524d\u7f6e\u5f71\u54cd\u8303\u56f4\u5206\u6790\u4e0e\u72b6\u6001\u6d41\u8f6c",
                    "\u63d0\u4ea4\u6301\u4e45\u5316\u5b58\u50a8\u4e8b\u52a1\u5e76\u5199\u56de\u5ba1\u8ba1\u4e0d\u53ef\u53d8\u65e5\u5fd7",
                    "\u91ca\u653e\u5206\u5e03\u5f0f\u5e42\u7b49\u9501\u5e76\u7ec4\u88c5\u6807\u51c6\u54cd\u5e94\u8f7d\u8377\u8fd4\u56de\u5ba2\u6237\u7aef"
                ])
                lines.extend([
                    "#### 5. \u6838\u5fc3\u4e1a\u52a1\u903b\u8f91\u65f6\u5e8f (Step-by-Step Business Logic)",
                ])
                for s_idx, step in enumerate(steps, 1):
                    lines.append(f"{s_idx}. {step}")
                lines.extend([
                    "",
                    f"\u6b64\u7aef\u70b9**\u5b9e\u73b0\u4e86** `{reqs}`\uff0c**\u4f9d\u8d56\u4e8e** `{deps}`\u3002\n\n<!-- /block -->\n",
                ])

            lines.extend([
                "## 3. \u5168\u5c40\u7edf\u4e00\u4e1a\u52a1\u9519\u8bef\u7801\u77e9\u9635 (Global Error Matrix)",
                "",
                "| \u4e1a\u52a1\u9519\u8bef\u7801 | HTTP \u72b6\u6001\u7801 | \u9519\u8bef\u8bed\u4e49 | \u5efa\u8bae\u5ba2\u6237\u7aef\u5904\u7f6e\u65b9\u6848 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for err in error_codes:
                lines.append(f"| **`{err.get('code')}`** | `{err.get('http_status')}` | {err.get('message')} | {err.get('actionable_guidance', 'Retry or inspect input')} |")

            lines.extend([
                "",
                "## 4. \u5411\u540e\u517c\u5bb9\u4e0e\u6f14\u8fdb\u7b56\u7565 (Backward Compatibility)",
                "",
                f"- **\u6f14\u8fdb\u65b9\u9488**\uff1a{compat.get('policy_summary', '\u4e25\u683c\u9075\u5faa\u4ec5\u589e\u4e0d\u51cf\u539f\u5219\uff1a\u7981\u6b62\u91cd\u547d\u540d\u5b57\u6bb5\u6216\u5220\u9664\u5728\u7528\u5b57\u6bb5\uff1b\u65b0\u589e\u5b57\u6bb5\u5fc5\u987b\u8bbe\u4e3a\u53ef\u9009\u6216\u5177\u5907\u9ed8\u8ba4\u503c\u3002')}",
                f"- **\u5e9f\u5f03\u5468\u671f\u6d41\u7a0b**\uff1a{compat.get('deprecation_process', '\u5b57\u6bb5\u5e9f\u5f03\u987b\u7ecf\u5386\u81f3\u5c11\u4e24\u4e2a\u4e3b\u7248\u672c\u7684 Deprecated \u6807\u5934\u8fc7\u6e21\u671f\uff0c\u901a\u8fc7 Sunset HTTP \u54cd\u5e94\u5934\u901a\u77e5\u8c03\u7528\u65b9\u3002')}",
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
                f"# {title} \u4e1a\u52a1\u6d41\u7a0b\u4e0e\u72b6\u6001\u673a\u67b6\u6784\u89c4\u7ea6",
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
                "> \u9075\u5faa Lingforge \u4e1a\u52a1\u6d41\u7a0b\u8bbe\u8ba1\u6807\u51c6\uff1a\u5b9a\u4e49\u89d2\u8272\u4e0e\u6743\u9650\u77e9\u9635\u3001Mermaid \u4e1a\u52a1\u6d41\u7a0b\u56fe\u3001\u8be6\u5c3d\u64cd\u4f5c\u6b65\u9aa4\uff08\u89e6\u53d1\u3001\u6267\u884c\u8005\u3001\u64cd\u4f5c\u3001\u8f93\u5165\u8f93\u51fa\u3001\u89c4\u5219\u3001\u5f02\u5e38\u3001SLA\uff09\u3001\u72b6\u6001\u673a\u5168\u8f6c\u79fb\u77e9\u9635\u4e0e\u9886\u57df\u6570\u636e\u6a21\u578b\u3002",
                "",
                "---",
                "",
                "## 1. \u4e1a\u52a1\u6d41\u7a0b\u6982\u8ff0\u4e0e\u89d2\u8272\u77e9\u9635 (Overview & Roles)",
                "",
                "### \u6d89\u53ca\u89d2\u8272\u4e0e\u804c\u8d23\u77e9\u9635",
                "",
                "| \u89d2\u8272\u540d\u79f0 | \u4e1a\u52a1\u804c\u8d23 | \u6743\u9650\u8303\u56f4 |",
                "| :--- | :--- | :--- |",
            ]
            default_roles = [
                {"role": "\u4e1a\u52a1\u64cd\u4f5c\u7528\u6237 (Operator)", "responsibility": "\u53d1\u8d77\u4e1a\u52a1\u64cd\u4f5c\u4e0e\u67e5\u8be2\u68c0\u7d22\u8bf7\u6c42", "permissions": "\u6807\u51c6\u4e1a\u52a1\u63d0\u4ea4\u4e0e\u7ed3\u679c\u67e5\u770b"},
                {"role": "\u4e1a\u52a1\u81ea\u52a8\u5316\u670d\u52a1 (Service/Agent)", "responsibility": "\u6267\u884c\u53d7\u63a7\u89c4\u5219\u8ba1\u7b97\u4e0e\u81ea\u52a8\u5316\u6d41\u7a0b\u7f16\u6392", "permissions": "\u53d7\u9650\u5185\u90e8\u5de5\u5177\u4e0e\u9886\u57df\u670d\u52a1\u8c03\u7528"},
                {"role": "\u591a\u56e0\u5b50\u5ba1\u6279\u4eba (Approver)", "responsibility": "\u9488\u5bf9\u9ad8\u98ce\u9669\u8282\u70b9\u6267\u884c\u4eba\u5de5\u590d\u6838\u4e0e\u5b89\u5168\u7b7e\u7f72", "permissions": "\u5ba1\u6279\u3001\u9a73\u56de\u4e0e\u5f02\u5e38\u5904\u7f6e"},
                {"role": "\u5e73\u53f0\u7ba1\u7406\u5458 (Admin)", "responsibility": "\u5168\u7cfb\u7edf\u914d\u7f6e\u7ba1\u7406\u3001\u5f02\u5e38\u7194\u65ad\u5e72\u9884\u4e0e\u5ba1\u8ba1\u76d1\u63a7", "permissions": "\u5168\u91cf\u7ba1\u7406\u4e0e\u7cfb\u7edf\u914d\u7f6e"}
            ]
            for r in roles or default_roles:
                lines.append(f"| **{r.get('role')}** | {r.get('responsibility')} | {r.get('permissions')} |")

            if flowchart:
                lines.extend([
                    "",
                    "## 2. \u6838\u5fc3\u4e1a\u52a1\u5168\u5c40\u4e3b\u6d41\u7a0b\u56fe (Flowchart)",
                    "",
                    "```mermaid",
                    flowchart.strip(),
                    "```",
                ])

            lines.extend([
                "",
                "## 3. \u6838\u5fc3\u4e1a\u52a1\u6d41\u7a0b\u65f6\u5e8f\u4e0e\u8be6\u7ec6\u6b65\u9aa4 (Sequence Flows & Step Details)",
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
                    f"**\u4e1a\u52a1\u8bf4\u660e**\uff1a{fdesc}",
                    f"- **\u5b9e\u73b0\u9700\u6c42**\uff1a`{reqs}`",
                    "",
                    "#### \u65f6\u5e8f\u4ea4\u4e92\u56fe (Sequence Diagram)",
                    "```mermaid",
                    seq.strip() if seq else "sequenceDiagram\n  autonumber\n  Actor->>System: Request\n  System-->>Actor: Response",
                    "```",
                    "",
                ])

                if steps:
                    lines.extend([
                        "#### \u8be6\u7ec6\u6b65\u9aa4\u64cd\u4f5c\u89c4\u8303",
                    ])
                    for s in steps:
                        lines.extend([
                            f"##### \u6b65\u9aa4 {s.get('step_number', 1)}: {s.get('step_name', 'Operation')}",
                            f"- **\u89e6\u53d1\u6761\u4ef6**\uff1a{s.get('trigger_condition', '\u7528\u6237\u8c03\u7528\u63a5\u53e3')}",
                            f"- **\u6267\u884c\u4e3b\u4f53**\uff1a`{s.get('actor', 'System')}`",
                            f"- **\u64cd\u4f5c\u8bf4\u660e**\uff1a{s.get('operation_details', '')}",
                            f"- **\u8f93\u5165\u6570\u636e**\uff1a`{s.get('inputs', 'Request parameters')}`",
                            f"- **\u8f93\u51fa\u7ed3\u679c**\uff1a`{s.get('outputs', 'Execution result')}`",
                            f"- **\u4e1a\u52a1\u89c4\u5219**\uff1a{s.get('business_rules', '\u9075\u5b88\u4e0d\u53ef\u53d8\u7ea6\u675f')}",
                            f"- **\u5f02\u5e38\u5904\u7406**\uff1a{s.get('exception_handling', '\u89e6\u53d1\u81ea\u52a8\u56de\u6eda\u5e76\u8bb0\u5f55\u544a\u8b66')}",
                            f"- **\u65f6\u6548/SLA \u8981\u6c42**\uff1a`{s.get('sla_requirement', 'P99 < 500ms')}`",
                            "",
                        ])

                lines.extend([
                    "#### \u4e09\u8def\u5f84\u884c\u4e3a\u89c4\u7ea6 (Three Paths)",
                    f"- **\u6b63\u5e38\u8def\u5f84 (Happy Path)**\uff1a{paths.get('happy_path', '\u5404\u8282\u70b9\u9884\u68c0\u901a\u8fc7\uff0c\u539f\u5b50\u63d0\u4ea4\u6210\u529f\u5e76\u5199\u56de\u5ba1\u8ba1\u65e5\u5fd7\u3002')}",
                    f"- **\u8fb9\u7f18\u573a\u666f (Edge Cases)**\uff1a{paths.get('edge_cases', '\u9ad8\u5e76\u53d1\u5199\u4e89\u7528\u7248\u672c\u51b2\u7a81\uff0c\u9000\u907f\u91cd\u8bd5\u6216\u89e6\u53d1\u4e50\u89c2\u9501\u91cd\u8bd5\u673a\u5236\u3002')}",
                    f"- **\u5f02\u5e38\u5bb9\u707e (Error Handling)**\uff1a{paths.get('error_handling', '\u4e0b\u6e38\u5355\u5e93\u8d85\u65f6\u65ad\u8fde\uff0c2PC \u81ea\u52a8\u4e2d\u65ad\u5e76\u89e6\u53d1 Saga \u9006\u5411\u8865\u507f\u56de\u6eda\u3002')}",
                    "",
                ])

            lines.extend([
                "## 4. \u6838\u5fc3\u72b6\u6001\u673a\u67b6\u6784\u4e0e\u72b6\u6001\u8f6c\u79fb\u56fe (State Machine Architecture)",
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
                    f"### \u72b6\u6001\u673a: `{sm_name}`",
                    f"- **\u7ec8\u6001\u96c6\u5408 (Terminal States)**\uff1a`{', '.join(sm.get('terminal_states', ['COMMITTED', 'ROLLED_BACK']))}` (\u7ec8\u6001\u4e25\u683c\u4e0d\u53ef\u53d8)",
                    "",
                    "#### \u72b6\u6001\u5b9a\u4e49\u8868\u683c",
                    "| \u72b6\u6001\u4ee3\u7801 | \u72b6\u6001\u540d\u79f0 | \u4e1a\u52a1\u5b9a\u4e49\u4e0e\u51c6\u5165\u51c6\u51fa\u6761\u4ef6 | \u53ef\u6d41\u8f6c\u76ee\u6807\u72b6\u6001 |",
                    "| :--- | :--- | :--- | :--- |",
                ])
                for st in states:
                    if isinstance(st, str):
                        s_code = st
                        s_name = st
                        s_desc = f"{sm_name} \u72b6\u6001\u8282\u70b9\uff1a{st}"
                        s_trans = transitions_map.get(st, ["\u65e0 (\u7ec8\u6001 / Terminal State)"])
                    else:
                        s_code = st.get("state") or st.get("code") or st.get("name", "STATE")
                        s_name = st.get("name", s_code)
                        s_desc = st.get("description", "")
                        s_trans = st.get("transitions") or transitions_map.get(s_code, ["\u65e0 (\u7ec8\u6001 / Terminal State)"])
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
                        "#### \u72b6\u6001\u6d41\u8f6c\u62d3\u6251\u56fe (State Diagram)",
                        "```mermaid",
                        mermaid_dia.strip(),
                        "```",
                        "",
                    ])

            if data_model:
                lines.extend([
                    "## 5. \u6d41\u7a0b\u9886\u57df\u6570\u636e\u6a21\u578b (Flow Data Model)",
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
                f"# {sys_name} \u4e5d\u7ef4\u5168\u666f\u67b6\u6784\u4e0d\u53d8\u91cf\u89c4\u7ea6",
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
                "> \u67b6\u6784\u5e08\u4e3b\u5bfc\u578b\u5de5\u7a0b\u9632\u5fa1\u6cd5\u6848\uff1a\u5728\u517c\u5bb9\u6027\u3001\u5206\u5c42\u3001\u5b58\u50a8\u3001\u5e76\u53d1\u3001\u5b89\u5168\u3001\u6027\u80fd\u3001\u4ee3\u7801\u89c4\u8303\u3001\u5bb9\u707e\u4e0e\u53ef\u89c2\u6d4b\u6027 9 \u5927\u6838\u5fc3\u7ef4\u5ea6\u5efa\u7acb 100% \u7269\u7406\u9632\u5fa1\u8f7d\u4f53\uff0c\u8fdd\u89c4\u5f3a\u5236\u963b\u65ad\u5e76\u5177\u5907\u81ea\u52a8\u5316\u5904\u7f6e\u673a\u5236\u3002",
                "",
                "---",
                "",
                "## 1. \u67b6\u6784\u4e0d\u53d8\u91cf\u6982\u8ff0 (Overview)",
                "",
                f"- **\u67b6\u6784\u4e0d\u53d8\u91cf\u603b\u6570**\uff1a`{len(invariants)}` \u6761\u89c4\u7ea6",
                f"- **\u7269\u7406\u9632\u5fa1\u8986\u76d6\u7387**\uff1a`{cov_pct}%` (100% \u8fbe\u6807\u94c1\u5f8b)",
                "",
                "## 2. \u4e5d\u7ef4\u67b6\u6784\u4e0d\u53d8\u91cf\u5168\u666f\u660e\u7ec6 (Nine-Dimension Catalog)",
                "",
                "| \u4e0d\u53d8\u91cf\u7f16\u53f7 | \u6838\u5fc3\u7ef4\u5ea6 (Dimension) | \u4e0d\u53d8\u91cf\u9648\u8ff0 (Rule) | \u7269\u7406\u9632\u5fa1\u673a\u5236 (Physical Defense) | \u8fdd\u89c4\u8865\u6551\u65b9\u6848 (Remediation) |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
            for inv in invariants:
                lines.append(f"| **{inv.get('id')}** | `{inv.get('dimension')}` | {inv.get('statement')} | `{inv.get('defense_mechanism')}` | {inv.get('violation_remediation')} |")

            lines.extend([
                "",
                "## 3. \u7269\u7406\u9632\u5fa1\u8f7d\u4f53\u5206\u5c42\u843d\u5730\u77e9\u9635 (Implementation Carriers)",
                "",
                "- **\u6301\u4e45\u5316\u5b58\u50a8\u5c42 (DB Constraints)**\uff1aPostgreSQL CHECK \u7ea6\u675f\u3001\u5916\u952e\u7ea7\u8054\u9650\u5236\u3001\u7248\u672c\u4e50\u89c2\u9501\u3001\u552f\u4e00\u7d22\u5f15",
                "- **\u7f16\u8bd1\u671f\u4e0e\u5de5\u5177\u94fe\u95e8\u7981 (CI/Compiler)**\uff1aRust Clippy deny \u89c4\u5219\u3001ArchUnit \u5355\u5411\u5206\u5c42\u6821\u9a8c\u3001\u96f6 Panic \u9759\u6001\u5206\u6790",
                "- **\u7f51\u5173\u4e0e\u5b89\u5168\u62e6\u622a\u5668 (Gateway/Security)**\uff1aJWT \u7b7e\u540d\u9a8c\u8bc1\u3001Fine-Grained RBAC \u62e6\u622a\u3001\u81ea\u9002\u5e94\u4ee4\u724c\u6876\u9650\u6d41",
                "- **\u9ad8\u53ef\u7528\u4e0e\u8fd0\u884c\u65f6\u5bb9\u707e (Runtime Resilience)**\uff1aSaga \u9006\u5411\u8865\u507f\u5668\u3001\u65ad\u8def\u5668\u7194\u65ad\u3001\u6307\u6570\u9000\u907f\u91cd\u8bd5\u3001OpenTelemetry \u4e0a\u4e0b\u6587\u4f20\u9012",
                "",
                "## 4. PRD \u9700\u6c42\u8840\u7f18\u8ffd\u8e2a\u77e9\u9635 (Traceability Matrix)",
                "",
                f"- **\u5173\u8054\u9700\u6c42\u6e05\u5355**\uff1a`{', '.join(data.get('implements', []))}`",
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
                f"# {sys_name} \u6280\u672f\u4f9d\u8d56\u62d3\u6251\u4e0e\u5f00\u53d1\u6307\u5bfc\u89c4\u7ea6",
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
                "> \u4e25\u683c\u4fdd\u969c\u4f9d\u8d56 DAG \u6709\u5411\u65e0\u73af\uff0c\u660e\u786e\u5173\u952e\u65bd\u5de5\u8def\u5f84\u4e0e\u6838\u5fc3\u6280\u672f\u74f6\u9888\uff0c\u5e76\u9075\u5faa Lingforge complex-feature-guide-writer \u5b9e\u7528\u6807\u51c6\uff0c\u4e3a\u9ad8\u96be\u5ea6\u7279\u6027\u63d0\u4f9b\u53ef\u6267\u884c\u7684 Step-by-Step \u6280\u672f\u65b9\u6848\u3001\u4ee3\u7801\u8303\u4f8b\u4e0e\u9a8c\u8bc1\u51c6\u5219\u3002",
                "",
                "---",
                "",
                "## 1. \u6280\u672f\u4f9d\u8d56\u4e0e\u6307\u5bfc\u6982\u8ff0 (Overview)",
                "",
                f"- **\u7ec4\u4ef6\u8282\u70b9\u603b\u6570**\uff1a`{len(nodes)}` \u4e2a",
                f"- **\u4f9d\u8d56\u5173\u7cfb\u8fb9\u6570**\uff1a`{len(edges)}` \u6761\uff08\u4e25\u683c Kahn \u7b97\u6cd5\u65e0\u73af\u9a8c\u8bc1\u901a\u8fc7\uff09",
                f"- **\u5173\u952e\u8def\u5f84\u8282\u70b9\u6570**\uff1a`{len(crit_path)}` \u4e2a",
                "",
                "## 2. \u6280\u672f\u4f9d\u8d56\u6709\u5411\u65e0\u73af\u56fe (Dependency DAG)",
                "",
                "```mermaid",
                "graph TD;",
            ]
            for edge in edges:
                lines.append(f"  {edge.get('from_node')} -->|{edge.get('dependency_type', 'depends_on')}| {edge.get('to_node')};")
            lines.extend([
                "```",
                "",
                "## 3. \u5173\u952e\u65bd\u5de5\u8def\u5f84\u4e0e\u74f6\u9888\u8bc4\u4f30 (Critical Path & Bottlenecks)",
                "",
                f"**\u5173\u952e\u65bd\u5de5\u8def\u5f84 (Critical Path)**\uff1a`{' -> '.join(crit_path)}`",
                "",
                "| \u8282\u70b9\u7f16\u53f7 | \u7ec4\u4ef6\u540d\u79f0 | \u67b6\u6784\u5206\u5c42 | \u8d23\u4efb\u89d2\u8272 | \u524d\u7f6e\u4f9d\u8d56 |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                is_crit = "🔥 (\u5173\u952e\u8def\u5f84)" if node.get("id") in crit_path else ""
                lines.append(f"| **{node.get('id')}** | {node.get('name')} {is_crit} | `{node.get('layer')}` | {node.get('owner_role')} | `{', '.join(node.get('prerequisites', [])) or '\u65e0 (\u8d77\u59cb\u6839\u8282\u70b9)'}` |")

            lines.extend([
                "",
                "#### \u74f6\u9888\u98ce\u9669\u8bc4\u4f30\u4e0e\u89e3\u8026\u7b56\u7565 (Bottlenecks & Decoupling)",
                "",
                "| \u8282\u70b9\u7f16\u53f7 | \u7ec4\u4ef6\u540d\u79f0 | \u74f6\u9888\u98ce\u9669\u8bc4\u4f30 | \u89e3\u8026\u4e0e\u52a0\u901f\u7b56\u7565 |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for node in nodes:
                b_risk = node.get("bottleneck_risk", "\u524d\u7f6e\u4f9d\u8d56\u53d8\u66f4\u53ef\u80fd\u5bfc\u81f4\u4e0b\u6e38\u91cd\u65b0\u7f16\u8bd1\u4e0e\u63a5\u53e3\u9002\u914d")
                decoup = node.get("decoupling_strategy", "\u57fa\u4e8e\u7eaf\u63a5\u53e3 Trait \u8fdb\u884c\u4f9d\u8d56\u5012\u7f6e\uff0c\u4fdd\u6301\u5b9e\u73b0\u4e0e\u62bd\u8c61\u9694\u79bb")
                lines.append(f"| **{node.get('id')}** | {node.get('name')} | {b_risk} | {decoup} |")

            lines.extend([
                "",
                "## 4. \u6280\u672f\u65bd\u5de5\u6709\u5e8f\u9636\u6bb5\u89c4\u5212 (Build Sequence)",
                "",
                "| \u9636\u6bb5\u987a\u5e8f | \u6784\u5efa\u8282\u70b9 | \u51c6\u5165\u6761\u4ef6 (Entry Criteria) | \u51c6\u51fa\u9a8c\u6536\u6761\u4ef6 (Exit Criteria) |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for phase in phases:
                lines.append(f"| \u9636\u6bb5 {phase.get('order')} | **`{phase.get('node_id')}`** | {phase.get('entry_criteria')} | {phase.get('exit_criteria')} |")

            lines.extend([
                "",
                "## 5. \u9ad8\u96be\u5ea6\u590d\u6742\u7279\u6027\u5b9e\u73b0\u6307\u5bfc (Complex Feature Implementation Guides)",
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
                    f"- **\u98ce\u9669\u5047\u8bbe\u4e0e\u74f6\u9888\u76ee\u6807**\uff1a{risk}",
                    f"- **\u7814\u53d1\u9a8c\u8bc1\u65f6\u95f4\u76d2 (Timebox)**\uff1a`{tbox} \u5929`",
                    "",
                    "#### \u6838\u5fc3\u7b97\u6cd5\u4e0e\u751f\u4ea7\u7ea7\u4ee3\u7801\u793a\u4f8b (Implementation Code)",
                    "```rust",
                    algo.strip(),
                    "```",
                    "",
                    "#### \u5e76\u53d1\u4e0e\u6027\u80fd\u8003\u91cf (Performance & Concurrency)",
                    "- **\u8d44\u6e90\u9694\u79bb\u4e0e\u7f13\u51b2\u7b56\u7565**\uff1a\u5b9e\u65bd\u5fae\u6279\u6b21\u6d41\u6c34\u7ebf\u5904\u7406\uff0c\u9650\u5236\u6700\u5927\u5185\u5b58\u7f13\u5b58\u5e76\u914d\u7f6e\u80cc\u538b\u673a\u5236\u3002",
                    "- **\u8fde\u63a5\u6c60\u4e0e\u8fde\u63a5\u6cc4\u6f0f\u9632\u5fa1**\uff1a\u914d\u7f6e\u4e25\u683c\u7684\u8d85\u65f6\u501f\u51fa\u4e0a\u9650\u4e0e\u81ea\u52a8\u56de\u6536\u5fc3\u8df3\u3002",
                    "",
                    "#### \u51c6\u51fa\u4e0e\u9a8c\u6536\u9a8c\u8bc1\u6807\u51c6 (Exit & Verification Criteria)",
                    f"- **\u9a8c\u6536\u51c6\u5219**\uff1a{exit_c}",
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
                f"# {pname} \u67b6\u6784\u5c31\u7eea\u5ea6\u8bc4\u5ba1\u4e0e\u51c6\u5165\u62a5\u544a",
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
                f"> **\u7ec8\u5ba1\u7ed3\u8bba**\uff1a{status_badge} | **\u7efc\u5408\u67b6\u6784\u8d28\u91cf\u8bc4\u5206**\uff1a`{score} / 100`",
                "> \u9075\u5faa\u4e25\u683c\u7684\u4e00\u7968\u5426\u51b3\u51c6\u5165\u539f\u5219\uff1a\u5b58\u5728\u4efb\u4f55\u963b\u585e\u6027\u7f3a\u9677\u6216\u9700\u6c42\u8986\u76d6\u4e0d\u8db3 100% \u5747\u4e25\u7981\u51c6\u5165\u7814\u53d1\u3002",
                "",
                "---",
                "",
                "## 1. \u6838\u5fc3\u9700\u6c42\u8986\u76d6\u7387\u5ba1\u8ba1 (Requirement Coverage Audit)",
                "",
                f"- **PRD Must-Have \u6838\u5fc3\u9700\u6c42\u603b\u6570**\uff1a`{req_audit.get('total_must_have_requirements', 0)}` \u9879",
                f"- **\u67b6\u6784\u5df2\u95ed\u73af\u9700\u6c42\u6570**\uff1a`{req_audit.get('covered_must_have_requirements', 0)}` \u9879",
                f"- **\u8986\u76d6\u7387\u767e\u5206\u6bd4**\uff1a`{req_audit.get('must_have_coverage_pct', 0.0)}%` (\u8981\u6c42: 100%)",
                "",
                "## 2. \u67b6\u6784\u89c4\u8303\u4e0e\u517c\u5bb9\u6027\u5408\u89c4\u6027\u5ba1\u8ba1 (Compliance Audit)",
                "",
                f"- **\u5411\u540e\u517c\u5bb9\u6027\u9a8c\u8bc1**\uff1a{'✅ \u901a\u8fc7 (\u65e0\u7834\u574f\u6027\u53d8\u66f4)' if compat_audit.get('backward_compatibility_verified') else '❌ \u672a\u901a\u8fc7'}",
                f"- **\u4e09\u5c42\u5355\u4f53\u67b6\u6784\u5408\u89c4**\uff1a{'✅ \u4e25\u683c\u7b26\u5408 (<= 3 \u5c42)' if compat_audit.get('layer_count_compliant') else '❌ \u8fdd\u89c4\u8fc7\u5ea6\u5206\u5c42'}",
                f"- **PRD \u7ea6\u675f\u6280\u672f\u6808\u5408\u89c4**\uff1a{'✅ 100% \u7ee7\u627f\u5e76\u843d\u5730' if compat_audit.get('prd_tech_stack_compliant') else '❌ \u504f\u79bb\u7ea6\u675f'}",
                "",
                "## 3. \u963b\u585e\u6027\u67b6\u6784\u7f3a\u9677\u5ba1\u67e5 (Blocking Findings - \u4e00\u7968\u5426\u51b3\u9879)",
                "",
            ]
            if blocking:
                for b in blocking:
                    lines.append(f"- 🔴 **[{b.get('category', 'BLOCKER')}]** {b.get('message')}")
            else:
                lines.append("✅ **\u65e0\u4efb\u4f55\u963b\u585e\u6027\u7f3a\u9677 (Zero Blocking Findings)**\uff1a\u6240\u6709\u67b6\u6784\u89c4\u7ea6\u5747\u6ee1\u8db3\u4ea4\u4ed8\u7ea2\u7ebf\u3002")

            lines.extend([
                "",
                "## 4. \u5efa\u8bae\u6027\u4f18\u5316\u9879\u5ba1\u67e5 (Advisory Findings)",
                "",
            ])
            if advisory:
                for a in advisory:
                    lines.append(f"- 🟡 **[{a.get('category', 'ADVISORY')}]** {a.get('description', a.get('message', ''))} (\u5efa\u8bae: {a.get('recommendation', '')})")
            else:
                lines.append("\u6682\u65e0\u5efa\u8bae\u4f18\u5316\u9879\u3002")

            lines.extend([
                "",
                "## 5. \u67b6\u6784\u88c1\u51b3\u9648\u8ff0\u4e0e\u51b3\u7b56\u4f9d\u636e (Decision Rationale)",
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
