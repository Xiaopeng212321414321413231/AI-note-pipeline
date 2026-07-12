import pathlib, sys
sys.path.insert(0, 'src')

content = r'''"""AI 重写模块：OCR修复 + 话题分类 + 风格重写"""
import json
import re
from openai import OpenAI

def _call_zhipu(api_key, messages, temperature=0.7):
    client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
    resp = client.chat.completions.create(
        model="glm-4-flash",
        messages=messages,
        temperature=temperature
    )
    return resp.choices[0].message.content

def classify_topic(api_key, text):
    """判断文本的主题类别"""
    messages = [
        {"role": "system", "content": "你是一个内容分类器。根据文本内容判断主题类型，只返回一个JSON：{\"topic\": \"主题名\", \"keywords\": [\"关键词\", \"关键词\"]}\n\n从以下分类中选择最匹配的（可以扩展新分类）：\n- \"编程/代码\" — 代码片段、技术实现、bug修复\n- \"AI/机器学习\" — AI模型、训练、推理、工具\n- \"技术教程/学习\" — 学习笔记、课程、教程\n- \"个人笔记/日记\" — 个人思考、日记、随手记\n- \"新闻/资讯\" — 新闻、信息简报\n- \"产品/工具评测\" — 产品使用体验、工具对比\n- \"写作/创作\" — 文章、创意写作、文案\n- \"知识整理\" — 知识总结、脑图、知识点\n- \"其他\" — 以上都不匹配"},
        {"role": "user", "content": f"请判断以下文本的主题：\n\n{text[:500]}"}
    ]
    result = _call_zhipu(api_key, messages, temperature=0.2)
    try:
        start = result.find('{')
        end = result.rfind('}') + 1
        return json.loads(result[start:end])
    except:
        return {"topic": "其他", "keywords": [text[:20]]}

def repair_ocr_text(api_key, ocr_text):
    """修复OCR识别错误"""
    messages = [
        {"role": "system", "content": "你是OCR文字修复助手。修复以上OCR识别出的文字中的错误：纠正乱码、恢复正确标点、修正明显错字。保持原文内容和语气不变，不要重写或总结。"},
        {"role": "user", "content": f"请修复以上OCR文字：\n\n{ocr_text}"}
    ]
    return _call_zhipu(api_key, messages, temperature=0.3)

def _clean_notes(notes):
    """清理参考笔记：限制长度，但保留图片链接"""
    cleaned = []
    for note in notes:
        note = re.sub(r'\n{4,}', '\n\n\n', note)
        note = note.strip()[:2000]
        if len(note) > 50:
            cleaned.append(note)
    return cleaned[:2]

def rewrite_text_with_ai(api_key, clean_text, reference_notes=None, topic_info=None, web_context=""):
    """用AI重写文本，融入个人风格和有深度的技术解析"""
    ref_text = ""
    if reference_notes:
        cleaned = _clean_notes(reference_notes)
        ref_text = "\n\n---\n\n".join(cleaned)

    topic_name = topic_info.get('topic', '') if topic_info else ''
    keywords = ', '.join(topic_info.get('keywords', [])) if topic_info else ''

    extra_context = ""
    if web_context:
        extra_context = f"\n\n【补充背景知识】\n{web_context}\n"

    topic_section = ""
    if topic_name:
        topic_section = f"## 本文主题\n{topic_name}\n关键词：{keywords}"

    system_prompt = f"""你是一个资深技术写手，擅长写有深度又好看的笔记。

# 你的任务
把【待重写内容】改写成一篇有技术深度、有阅读吸引力的笔记。

# 风格要求
- **要有干货**：不要停留在表面描述，要解释"为什么"和"怎么做到的"
- **要有观点**：加入你的理解和判断，比如"这个方案比传统做法好在哪"
- **用词要准**：技术名词用对，用具体数据说话，别用"显著""大幅"这种空洞词
- **结构清晰**：用标题分层，关键信息加粗，重要概念可以画成对比表或伪代码
- **让人想看完**：开头要有吸引力，内容有节奏感，不要平铺直叙
- **图片处理**：原文有图片链接(![[...]])可以保留，但每个图片前后必须有至少2-3句文字说明这张图讲什么、为什么重要

# 关键原则
- **每个图片前后必须配有充分的文字说明**，不能图片连着图片没有文字
- 参考笔记只是风格参考，不要复制其具体内容
- 要写出增量：比原文更完整、更深入、更好理解

{topic_section}"""

    user_prompt = f"""{extra_context}
【参考笔记风格】
{ref_text or '请使用专业、清晰、有条理的中文技术写作风格。'}

【待重写内容】
{clean_text}"""

    return _call_zhipu(api_key, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], temperature=0.8)
'''

with open('src/ai_rewrite.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')