"""信息价值三级分类器：skip / save_only / deep_rewrite"""
import os
from openai import OpenAI

def classify_content(api_key: str, text: str) -> str:
    """
    对输入文本进行价值分类

    返回:
        'skip'        → 丢弃（无价值信息，如购物清单、随手涂鸦、无意义闲聊）
        'save_only'   → 仅保存原文（有价值但无需重写，如新闻简讯、代码片段、事实性数据）
        'deep_rewrite'→ 深度加工（需要参考风格重写并融入知识体系）
    """
    text = text.strip()
    if len(text) < 30:
        return 'skip'  # 太短，不可能有价值

    client = OpenAI(
        api_key=api_key,
        base_url="https://open.bigmodel.cn/api/paas/v4/"
    )

    prompt = f"""你是一个信息价值判断专家。请阅读以下文本，判断它属于哪一类：

1. **skip**：无价值，如购物清单、随手涂鸦、无意义闲聊。
2. **save_only**：纯事实/纯数据/原文已很完整无需改动。
3. **deep_rewrite**：需要风格重写融入知识体系的——技术分析、学习笔记、教程、思考总结、读书笔记都归此类。

请只回复一个词：skip / save_only / deep_rewrite。

文本内容：
{text[:800]}"""

    try:
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=10
        )
        result = response.choices[0].message.content.strip().lower()
        if result in ('skip', 'save_only', 'deep_rewrite'):
            return result
        return 'deep_rewrite'  # 默认深度加工
    except Exception as e:
        print(f"   ⚠️ 分类失败，默认 deep_rewrite: {e}")
        return 'deep_rewrite'