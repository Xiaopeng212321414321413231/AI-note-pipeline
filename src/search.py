"""联网搜索补充 + 网页抓取 + 百度翻译"""
import os
import json
import re
import urllib.request
import urllib.parse
import hashlib
import random
import html as html_mod

# ─── Bing 搜索（国内可用，免费无限次） ───

def search_web(query, api_key=""):
    """Bing 联网搜索（国内可用，无需 API Key）"""
    try:
        encoded = urllib.parse.quote(query[:300])
        url = f"https://www.bing.com/search?q={encoded}&setlang=zh-CN"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html_data = resp.read().decode("utf-8", errors="ignore")

        results = []
        # 提取 b_algo 块
        blocks = re.findall(
            r'<li[^>]*class="[^"]*\bb_algo\b[^"]*"[^>]*>(.*?)</li>',
            html_data, re.DOTALL
        )
        for block in blocks:
            # 跳过 CSS 块（不含 tilk 类）
            if 'tilk' not in block:
                continue
            # 标题
            title_match = re.search(r'aria-label="([^"]+)"', block)
            if not title_match:
                continue
            title = html_mod.unescape(title_match.group(1))
            # URL（跳过 Bing 内部链接）
            url_match = re.search(r'href="(https?://[^"]+)"', block)
            if not url_match:
                continue
            link = url_match.group(1)
            if any(x in link for x in ['bing.com', 'microsoft.com', 'go.microsoft']):
                continue
            # 摘要
            snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
            snippet = ""
            if snippet_match:
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1))
                snippet = html_mod.unescape(snippet).strip()
                snippet = re.sub(r'\s+', ' ', snippet)[:200]
            results.append(f"- {title}：{snippet}" if snippet else f"- {title}")
            if len(results) >= 3:
                break

        if results:
            return "【联网搜索结果】\n" + "\n\n".join(results)
        return ""
    except Exception as e:
        print(f"   搜索失败（跳过）: {e}")
        return ""


# ─── 百度翻译 API（每月 200 万字符免费） ───

def detect_mixed_language(text):
    """检测文本是否混合了中英文"""
    if not text:
        return False
    en_chars = sum(1 for c in text if "a" <= c.lower() <= "z" or c in ".,;:!?()-[]{}")
    total_chars = len(text.strip())
    if total_chars < 20:
        return False
    return (en_chars / total_chars) > 0.15


def translate_text(text, from_lang="auto", to_lang="zh"):
    """百度大模型文本翻译 API（Bearer Token 鉴权）"""
    from config import FANYI_APP_ID as appid, FANYI_SECRET_KEY as secret_key
    if not appid or not secret_key:
        print("   百度翻译未配置（.env 加 FANYI_APP_ID / FANYI_SECRET_KEY）")
        return ""
    if not text or len(text.strip()) < 10:
        return ""
    query = text[:2000].strip()
    # 中英混杂强行指定源语言为 en，避免 auto 误判为 zh
    en_ratio = sum(1 for c in query if "a" <= c.lower() <= "z" or c in ".,;:!?()-[]{}") / max(len(query), 1)
    src_lang = "en" if en_ratio > 0.15 else from_lang
    data = json.dumps({
        "appid": appid,
        "from": src_lang,
        "to": to_lang,
        "q": query
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url="https://fanyi-api.baidu.com/ait/api/aiTextTranslate",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secret_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if "error_code" in result:
            print(f"   翻译失败（错误码: {result['error_code']}）")
            return ""
        trans_list = result.get("trans_result", [])
        if trans_list:
            return chr(10).join(item["dst"] for item in trans_list)
        return ""
    except Exception as e:
        print(f"   翻译请求失败: {e}")
        return ""


def translate_append(text):
    """检测中英混杂，必要时翻译并追加到原文后"""
    if not detect_mixed_language(text):
        return ""
    translated = translate_text(text[:1500])
    if translated:
        return "\n\n> 🌐 **中文翻译参考**\n> \n> " + translated[:2000]
    return ""


# ─── 网页抓取 ───

def fetch_webpage(url):
    """直接抓取网页正文"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html_data = resp.read().decode("utf-8", errors="ignore")
        html_data = re.sub(r"<script[^>]*>.*?</script>", "", html_data, flags=re.DOTALL | re.IGNORECASE)
        html_data = re.sub(r"<style[^>]*>.*?</style>", "", html_data, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html_data)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]
    except Exception as e:
        print(f"   网页抓取失败: {e}")
        return ""
