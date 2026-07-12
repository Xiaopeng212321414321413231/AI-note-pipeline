"""AI 重写模块：OCR修复 + 话题分类 + 风格重写"""
import json
import re
from openai import OpenAI

def _call_zhipu(api_key, messages, temperature=0.7):
    client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
    resp = client.chat.completions.create(model="glm-4-flash", messages=messages, temperature=temperature)
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
    except:
        return {"topic": "其他", "keywords": [text[:20]]}

def repair_ocr_text(api_key, ocr_text):
    """修复OCR识别错误"""
    return _call_zhipu(api_key, [
        {"role": "system", "content": "你是OCR文字修复助手。修复乱码和错字，保持原意。"},
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

    extra_context = ""
    if web_context:
        extra_context = f"## 补充背景知识\n{web_context}\n"

    topic_section = ""
    if topic_name:
        topic_section = f"主题：{topic_name} | 关键词：{keywords}"

    system_rules = """铁律——每一条都必须遵守：
【保留全部内容】原文中的所有知识点、代码、方法、数据、步骤——全部保留，一条都不能少。
AI 只能重写表达方式，不能删除、合并、省略任何原始信息点。
如果原文包含3种方法，输出必须也是3种方法，只换说法不删内容。
【零套话】第一句必须是干货，直接说内容。
禁止任何开场白、背景介绍、过渡句。
正确：DeepSeek的MoE架构通过混合专家设计，将推理成本压低了30%。
错误：在今日的研究中... / 让我们来探讨... / 随着AI的发展...

【个人观点】在保留全部原文信息的基础上，每个知识点后追加一句主观判断。
格式：客观内容（原文保留）→ 我认为/我判断 → 为什么这么想
禁止用个人观点替代原文内容，观点是附加的，不是替换的。

【技术对比】必须在正文中嵌入至少一个对比表格。
可选维度：MoE vs Dense架构对比（激活比例/计算量/显存/推理速度）
也可以选：新旧方案对比 / 不同技术路线对比
表格紧跟在对比文段后面，不要独立堆在末尾。

【用具体数据】违禁词黑名单（零容忍）：显著、大幅、革命性、深远影响、前所未有、更好地、更加高效、极大提升、明显优化、明显优势、大大提高、较高、较低、较好

铁律：表格里的每个值也必须用具体数字，不能用"较高""较低""显著降低"。
✅ 正确表格示例：
| 特性 | MoE架构 | Dense架构 |
|------|---------|-----------|
| 激活比例 | top-2专家（2/64） | 全部64个 |
| 计算量 | 训练FLOPs减少40% | 基准值 |
| 显存占用 | 48GB（5B参数） | 120GB（7B参数） |
| 推理延迟 | 85ms → 降低到60ms | 85ms |

❌ 错误表格示例（禁止）：
| 特性 | MoE架构 | Dense架构 |
|------|---------|-----------|
| 计算量 | 显著降低 | 较高 | （❌ 没有具体数字）

【自我检查】写完回复后，搜索"显著""大幅""较高""较低""较好""革命性"，如果找到任何一个，整段重写。

【参考笔记使用规则】参考笔记是你创作的知识来源，请充分利用：

✅ 提取参考笔记中的关键信息、数据、观点来丰富内容
✅ 如果参考笔记有相关知识，直接引用并整合到当前笔记中
✅ 保留参考笔记中的![[...]]图片链接，并为每张图配文字说明
❌ 不要原样复制参考笔记的段落结构，要重新组织和表达
"""

    if topic_section:
        system_rules = f"本文相关：{topic_section}\n\n" + system_rules

    system_prompt = f"你是一个有技术深度、有个性观点的写手。\n\n{system_rules}"

    user_prompt = ""
    if ref_text:
        user_prompt += f"【参考笔记风格】\n{ref_text}\n\n"
    user_prompt += f"【待重写内容】\n{clean_text}"

    return _call_zhipu(api_key, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ], temperature=0.8)