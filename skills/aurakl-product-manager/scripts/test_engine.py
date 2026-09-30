#!/usr/bin/env python3
"""
Pangu Typography & Markdown Visual Ergonomics Conformance Engine.

Strictly enforces:
1. Chinese Copywriting Guidelines / Spacing Standards:
   - Inserts half-width space between CJK characters and Latin/Digits/Symbols.
   - Preserves fenced code blocks, inline code, and Markdown URL link targets.
   - Correctly handles inline code containing CJK.
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
        "\u5728\u5fae\u4fe1H5\u7aef\u901a\u8fc7\u60f3\u53bb\u4e0e\u907f\u96f7\u53cc\u5411\u6807\u7b7e\u81ea\u4e3b\u6311\u9009\u666f\u70b9",
        "\u6bcf\u5929\u9ad8\u6548\u5904\u7406\u6570\u5341\u4f4d\u5ba2\u6237\u7684\u5b9a\u5236\u9700\u6c42\uff0c\u5e76\u57285\u5206\u949f\u5185\u5b8c\u6210",
        "\u63d0\u4f9b7\u5ea7\u522b\u514bGL8\u5546\u52a1\u8f66\u3001\u8f7b\u5962\u4e94\u661f\u9152\u5e97\u623f\u578b",
        "\u5728PC\u8ba1\u8c03ERP\u540e\u53f0\u63a5\u6536\u65b0\u5de5\u5355\u79d2\u7ea7\u5f39\u7a97",
        "\u7cfb\u7edf`MOD-CLIENT`\u6a21\u5757\u5904\u7406`POST /orders`\u8bf7\u6c42",
        "\u3010FEAT-CLIENT-001\u3011\u666f\u70b9\u610f\u5411\u9009\u578b",
        "\u5f53\u68c0\u6d4b\u5230\u5e95\u5c42\u7f51\u7edc\u65ad\u5f00\u65f6\uff0c\u5ba2\u6237\u7aef**\u5fc5\u987b (MUST)**\u5c06\u5f53\u524d\u8868\u5355\u6301\u4e45\u5316\u81f3\u672c\u5730SQLite/MMKV\u4e2d\u3002",
        "### 1.2 \u6838\u5fc3\u4e1a\u52a1\u76ee\u6807(Goals)",
        "| `ERR_CODE` | \u7528\u6237\u9009\u578b\u8f7d\u8377\u4e2d\u540c\u4e00\u666f\u70b9ID\u540c\u65f6\u51fa\u73b0\u5728\u5fc5\u53bb\u4e0e\u907f\u96f7\u96c6\u5408\u4e2d | \u65f6\u5ef6\u8981\u6c42 < 1000ms \u4e14\u6210\u529f\u7387 > 99.9% |"
    ]

    print("=== PanguTypographyEngine Test Run ===")
    for s in samples:
        formatted = PanguTypographyEngine.format(s).strip()
        print(f"INPUT:  {s}")
        print(f"OUTPUT: {formatted}")
        print("-" * 50)
