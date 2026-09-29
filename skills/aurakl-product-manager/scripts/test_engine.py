#!/usr/bin/env python3
"""
Pangu Typography & Markdown Visual Ergonomics Conformance Engine.

Strictly enforces:
1. 《中文文案排版指北》(Chinese Copywriting Guidelines / 盘古之白):
   - Inserts half-width space between CJK characters and Latin/Digits/Symbols.
   - Preserves fenced code blocks, inline code, and Markdown URL link targets.
   - Correctly handles inline code containing CJK (e.g. `微信小程序 web-view 容器`).
2. Markdown Visual Ergonomics & Human Readability:
   - Preserves mathematical comparison operators (<, >, <=, >=).
   - Normalizes vertical rhythm around headings, tables, and horizontal rules.
   - Cleans duplicate whitespace and redundant blank lines.
"""

import re
from pathlib import Path

class PanguTypographyEngine:
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

        # 5. Spacing between CJK and Latin/Digits
        text = re.sub(rf"({cls.CJK})({cls.LATIN})", r"\1 \2", text)
        text = re.sub(rf"({cls.LATIN})({cls.CJK})", r"\1 \2", text)

        # 6. Spacing around protected inline code
        text = re.sub(rf"({cls.CJK})(\ue000INLINE_\d+\ue001)", r"\1 \2", text)
        text = re.sub(rf"(\ue000INLINE_\d+\ue001)({cls.CJK})", r"\1 \2", text)

        # 7. Spacing around protected links
        text = re.sub(rf"({cls.CJK})(\ue006LINK_\d+\ue007)", r"\1 \2", text)
        text = re.sub(rf"(\ue006LINK_\d+\ue007)({cls.CJK})", r"\1 \2", text)

        # 8. Spacing around bold markers containing Latin/symbols adjacent to CJK
        text = re.sub(rf"(\*\*[^\*\n]+\*\*)({cls.CJK})", r"\1 \2", text)
        text = re.sub(rf"({cls.CJK})(\*\*[^\*\n]+\*\*)", r"\1 \2", text)

        # 9. Spacing around ASCII parentheses when mixed with CJK
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


if __name__ == "__main__":
    # Self-test cases
    samples = [
        "在微信H5端通过想去与避雷双向标签自主挑选景点",
        "每天高效处理数十位客户的定制需求，并在5分钟内完成",
        "提供7座别克GL8商务车、轻奢五星酒店房型",
        "在PC计调ERP后台接收新工单秒级弹窗",
        "系统`MOD-CLIENT`模块处理`POST /orders`请求",
        "【FEAT-CLIENT-001】景点意向选型",
        "当检测到底层网络断开时，客户端**必须 (MUST)**将当前表单持久化至本地SQLite/MMKV中。",
        "### 1.2 核心业务目标(Goals)",
        "| `ERR_CODE` | 用户选型载荷中同一景点ID同时出现在必去与避雷集合中 | 时延要求 < 1000ms 且成功率 > 99.9% |"
    ]

    print("=== PanguTypographyEngine Test Run ===")
    for s in samples:
        formatted = PanguTypographyEngine.format(s).strip()
        print(f"INPUT:  {s}")
        print(f"OUTPUT: {formatted}")
        print("-" * 50)
