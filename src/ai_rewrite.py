"""AI 重写模块：OCR修复 + 话题分类 + 风格重写"""
import json
import re
from loguru import logger
from openai import OpenAI

def _call_zhipu(api_key, messages, temperature=0.7):
    import re as _re
    _pat = _re.compile("[" + chr(0) + "-" + chr(8) + chr(11) + chr(12) + chr(14) + "-" + chr(31) + chr(127) + "]")
    client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
    for msg in messages:
        if isinstance(msg.get("content"), str):
            msg["content"] = _pat.sub("", msg["content"])
    resp = client.chat.completions.create(model="glm-4-flash", messages=messages, temperature=temperature, timeout=300)
    return resp.choices[0].message.content

def classify_topic(api_key, text):
    """判断文本的主题类别"""
    system_msg = (
        '你是一个分类器。只返回JSON：{"topic": "主题名", "keywords": ["关键词"]}\n'
        '可选分类：编程/代码、AI/机器学习、技术教程/学习、个人笔记/日记、新闻/资讯、产品/工具评测、写作/创作、知识整理、其他'
    )
    result = _call_zhipu(api_key, [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"判断文本主题：\n{text[:500]}"}
    ], temperature=0.2)
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        return json.loads(result[start:end])
    except json.JSONDecodeError as e:
        logger.warning("主题分类JSON解析失败: {}", e)
        return {"topic": "其他", "keywords": [text[:20]]}

def repair_ocr_text(api_key, ocr_text):
    """修复OCR识别错误"""
    return _call_zhipu(api_key, [
        {"role": "system", "content": "你是OCR文字修复助手。修复乱码和错字，保持原意。如果内容是Python代码，在每一段代码后用#号注释说明该代码的含义和输出结果，格式如：# 该代码的作用是过滤偶数并输出平方列表，输出为 [4, 16, 36, ...]"},
        {"role": "user", "content": f"修复以下文字：\n{ocr_text}"}
    ], temperature=0.3)

def _clean_notes(notes):
    """清理参考笔记"""
    cleaned = []
    for note in notes:
        note = re.sub(r"\n{4,}", "\n\n\n", note)
        note = note.strip()[:2000]
        if len(note) > 50:
            cleaned.append(note)
    return cleaned[:2]

def rewrite_text_with_ai(api_key, clean_text, reference_notes=None, topic_info=None, web_context=""):
    """用AI重写文本，融入个人观点和技术对比"""
    ref_text = ""
    if reference_notes:
        cleaned = _clean_notes(reference_notes)
        ref_text = "\n\n---\n\n".join(cleaned)

    topic_name = topic_info.get("topic", "") if topic_info else ""
    keywords = ", ".join(topic_info.get("keywords", [])) if topic_info else ""

    topic_section = ""
    if topic_name:
        topic_section = f"主题：{topic_name} | 关键词：{keywords}"

    system_rules = """首要规则——中英双语对照输出】
你必须输出中英双语对照版本！每段英文原文段落后，紧跟 > 引用块中文翻译。
顺序永远是：英文段落在上 → 中文翻译在引用块中紧跟在下。
不得只输出英文！

【铁律——每一条都必须遵守】
1. 保留原文全部关键信息，不得删减重要内容
2. 保留原文所有数据、数字、专有名词
3. 保留原文图片引用
4. 原文中最重要的 1-3 个句子，在中文翻译中用 **加粗** 强调
5. 关键术语首次出现时标注英文原文
6. 不要添加原文没有的内容

【富文本格式要求】
- 使用 **加粗** 强调关键术语、数字、重要结论
- 使用 > 引用块突出中文翻译
- 使用 ### 层级标题组织内容结构
- 如果原文包含图片，必须保留图片并配文字说明
"""


    if topic_section:
        system_rules = f"本文相关：{topic_section}\n\n" + system_rules

    system_prompt = f"你是一个有技术深度、有个性观点的写手。\n\n{system_rules}"

    user_prompt = ""
    if ref_text:
        user_prompt += f"【参考笔记风格】\n{ref_text}\n\n"
    user_prompt += "===== 重要命令 =====\n你必须输出中英双语对照文本：\n每段英文原文后，用 > 引用在其中，> 中文翻译紧跟在下面。\n\n"

    return _call_zhipu(api_key, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], temperature=0.8)