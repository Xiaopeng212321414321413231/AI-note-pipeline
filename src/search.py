"""联网搜索补充 + 网页抓取"""
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
        return "\n\n".join(parts) if parts else ""
    except Exception as e:
        print(f"   \u26a0\ufe0f 搜索失败（跳过）: {e}")
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
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]
    except Exception as e:
        print(f"   \u26a0\ufe0f 网页抓取失败: {e}")
        return ""
