import os

# 1. 修复 .env（UTF-8）
env_content = """ZHIPUAI_API_KEY=f1d0a36649ad4528bf1ccf87f846db4f.eHnvPy97mvhq357z
BAIDU_APP_ID=7908591
BAIDU_API_KEY=vwBg7MAfcRV6O97RsFCXzZEw
BAIDU_SECRET_KEY=VlHTxML4NCw71AKRJ6E7k0rT71Ukz0qS
OBSIDIAN_VAULT_PATH=G:/ai软件/obsidian/ai新闻
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
TAVILY_API_KEY=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
"""
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)

# 2. 修复 classifier.py - 降低深度重写门槛
with open('src/classifier.py', 'r', encoding='utf-8') as f:
    c = f.read()
old = "1. **skip**：无价值信息，如购物清单、随手涂鸦、无意义的闲聊、临时备忘录。\n2. **save_only**：有价值但只需原文保存无需重写，比如新闻简讯、事实性数据、代码片段、引用原文。\n3. **deep_rewrite**：值得深度加工，需要参考个人风格重写并融入知识体系，比如读书笔记、深刻思考、系统论述、教程内容。"
new = "1. **skip**：无价值，如购物清单、随手涂鸦、无意义闲聊。\n2. **save_only**：纯事实/纯数据/原文已很完整无需改动。\n3. **deep_rewrite**：需要风格重写融入知识体系的——技术分析、学习笔记、教程、思考总结、读书笔记都归此类。"
c = c.replace(old, new)
with open('src/classifier.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 3. 重写 search.py（增加 fetch_webpage）
search_content = '''"""联网搜索补充 + 网页抓取"""
import os
import json
import re
import urllib.request

def search_web(query: str, api_key: str = "") -> str:
    """Tavily 联网搜索"""
    if not api_key:
        return ""
    url = "https://api.tavily.com/search"
    payload = json.dumps({"api_key": api_key, "query": query[:300], "search_depth": "basic", "max_results": 3, "include_answer": True}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = []
        if data.get("answer"):
            parts.append(f"【摘要】{data['answer']}")
        for item in data.get("results", []):
            content = item.get("content", "")
            if content:
                parts.append(f"- {content[:300]}")
        return "\\n\\n".join(parts) if parts else ""
    except Exception as e:
        print(f"   \\u26a0\\ufe0f 搜索失败（跳过）: {e}")
        return ""

def fetch_webpage(url: str) -> str:
    """直接抓取网页正文"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\\s+", " ", text).strip()
        return text[:5000]
    except Exception as e:
        print(f"   \\u26a0\\ufe0f 网页抓取失败: {e}")
        return ""
'''
with open('src/search.py', 'w', encoding='utf-8') as f:
    f.write(search_content)

# 4. 更新 main.py import
with open('src/main.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("from search import search_web", "from search import search_web, fetch_webpage")
old_fetch = '''        import urllib.request
        reader_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(reader_url, headers={"Accept": "text/plain"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_text = resp.read().decode("utf-8")'''
new_fetch = '''        from search import fetch_webpage
        raw_text = fetch_webpage(url)'''
c = c.replace(old_fetch, new_fetch)
with open('src/main.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("✅ 全部修复完成！")