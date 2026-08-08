"""文章内容提取降级链 — 参考 Web Clipper 渐进式架构

四级降级链：
  Level 1: 直接返回（缓存命中 / RSS 已有全文）
  Level 2: RSS 摘要（>500 字）
  Level 3: Jina Reader（当前做法，下载+提取）
  Level 4: 直接 HTML + 简易 Markdown 转换（备胎）

使用方式：
  from article_extractor import extract_article
  result = extract_article(url, rss_content=rss_entry)
"""

import hashlib, json, os, re, sys
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "article_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


# ═══════════════════════════════════
# 缓存层
# ═══════════════════════════════════

def _cache_key(url: str) -> str:
    return hashlib.md5(url.rstrip("/").lower().encode()).hexdigest()[:16]

def _cache_get(url: str) -> Optional[dict]:
    path = CACHE_DIR / f"{_cache_key(url)}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def _cache_set(url: str, data: dict):
    path = CACHE_DIR / f"{_cache_key(url)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════
# HTML → 纯文本（比 current _html_to_markdown 更保守，不丢正文）
# ═══════════════════════════════════

def _strip_html(html: str) -> str:
    """只去标签，保留原文结构"""
    text = html
    # 砍掉非正文区块
    for tag in ('script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript'):
        text = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.I | re.S)
    # 换行友好
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</p>', '\n\n', text, flags=re.I)
    text = re.sub(r'</(div|li|h[1-6]|tr|blockquote|pre)>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)  # 去所有标签
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


# ═══════════════════════════════════
# Level 3: Jina Reader
# ═══════════════════════════════════

def _via_jina(url: str) -> tuple:
    """返回 (text, title) 或 ('','')"""
    from urllib.request import Request, urlopen
    try:
        j_url = "https://r.jina.ai/" + url
        req = Request(j_url, headers={"Accept": "text/plain"})
        resp = urlopen(req, timeout=30)
        raw = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'<title[^>]*>(.*?)</title>', raw, re.I | re.S)
        title = m.group(1).strip() if m else ""
        return raw, title
    except Exception:
        return "", ""


# ═══════════════════════════════════
# Level 4: 直接 HTML 下载 + 去标签
# ═══════════════════════════════════

def _via_html(url: str) -> tuple:
    """返回 (text, title) 或 ('','')"""
    from urllib.request import Request, urlopen
    try:
        req = Request(url, headers=_HDR)
        resp = urlopen(req, timeout=30)
        html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
        title = m.group(1).strip() if m else ""
        text = _strip_html(html)
        return text, title
    except Exception:
        return "", ""


# ═══════════════════════════════════
# 主入口
# ═══════════════════════════════════

def extract_article(
    url: str,
    rss_entry: Optional[dict] = None,
    skip_cache: bool = False,
) -> dict:
    """提取文章正文内容，返回结构化结果。

    Args:
        url: 文章 URL
        rss_entry: RSS 条目字典（可选），可包含 content / summary 字段
        skip_cache: 强制跳过缓存

    Returns:
        {
            "url": str,
            "title": str,
            "text": str,          # 纯文本正文
            "source": str,         # 来源描述
            "char_count": int,
            "level": str,          # 1/2/3/4
            "cached": bool,
        }
        text 为空表示全部失败。
    """
    # Level 0: 缓存命中
    if not skip_cache:
        cached = _cache_get(url)
        if cached:
            return {**cached, "cached": True}

    title = ""
    text = ""

    # ── Level 1: RSS 全文 ──
    if rss_entry:
        content_list = rss_entry.get("content") or []
        if content_list:
            for c in content_list:
                raw = c.get("value", "") if isinstance(c, dict) else str(c)
                text = _strip_html(raw)
                if len(text) > 500:
                    title = rss_entry.get("title", "")
                    source = f"RSS全文 ({len(text)}字)"
                    level = "1"
                    break

        # ── Level 2: RSS 摘要 ──
        if not text and rss_entry.get("summary"):
            raw = rss_entry["summary"]
            text = _strip_html(raw)
            if len(text) > 200:
                title = rss_entry.get("title", "")
                source = f"RSS摘要 ({len(text)}字)"
                level = "2"

    # ── Level 3: Jina Reader ──
    if not text or len(text) < 200:
        text, title = _via_jina(url)
        if text and len(text) >= 200:
            source = f"Jina Reader ({len(text)}字)"
            level = "3"

    # ── Level 4: 直接 HTML ──
    if not text or len(text) < 200:
        text, title = _via_html(url)
        if text and len(text) >= 200:
            source = f"直接HTML ({len(text)}字)"
            level = "4"
        else:
            source = "全部失败"
            level = "0"

    result = {
        "url": url,
        "title": title or url,
        "text": text,
        "source": source,
        "char_count": len(text),
        "level": level,
        "cached": False,
    }

    # 成功才缓存
    if text and len(text) >= 200:
        _cache_set(url, result)

    return result
