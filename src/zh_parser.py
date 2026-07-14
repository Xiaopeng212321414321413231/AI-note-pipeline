"""
ZhDocParser 集成模块
用于中文 PDF/DOCX 的结构化解析（标题层级+表格+分块）
作为原有 Tesseract/fitz/python-docx 解析的升级替代
"""

import os
from zhdocparser import parse_file
from zhdocparser.config import ParserConfig


def parse_with_zhdocparser(file_path: str) -> str:
    """
    使用 ZhDocParser 解析文件，返回结构化 Markdown 文本。
    支持 PDF/DOCX 格式，去重输出。
    """
    if not os.path.exists(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ('.pdf', '.docx'):
        return ""

    try:
        doc = parse_file(
            file_path,
            ParserConfig(doc_type_override="general", max_chunk_chars=2000),
        )

        parts = []
        seen = set()

        def add(line: str):
            stripped = line.strip()
            if stripped and stripped not in seen:
                parts.append(stripped)
                seen.add(stripped)
            elif not stripped:
                parts.append("")

        # 标题
        if doc.metadata.title:
            add(f"# {doc.metadata.title}")
            parts.append("")

        # 章节
        for section in doc.sections:
            heading = section.heading.strip() if section.heading else ""
            content = section.content.strip() if section.content else ""
            level = min(getattr(section, "level", 2), 6)
            if heading:
                add(f"{'#' * level} {heading}")
                parts.append("")
            if content:
                add(content)
                parts.append("")

        # 表格
        for table in doc.tables:
            if table.rows:
                header = table.rows[0]
                md = "| " + " | ".join(str(c) for c in header) + " |\n"
                md += "| " + " | ".join(["---"] * len(header)) + " |\n"
                for row in table.rows[1:]:
                    md += "| " + " | ".join(str(c) for c in row) + " |"
                if md not in seen:
                    parts.append(md)
                    parts.append("")
                    seen.add(md)

        return "\n".join(parts).strip()

    except Exception as e:
        print(f"   [ZhDocParser] 解析失败: {e}")
        return ""


def should_use_zhdocparser(file_path: str) -> bool:
    """判断是否应使用 ZhDocParser（中文文档优先）"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ('.pdf', '.docx'):
        return False
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return False
    return True
