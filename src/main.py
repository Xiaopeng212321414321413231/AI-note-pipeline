"""

AI 多模态笔记处理流水线 v2.0

任何输入（图片/音频/PDF/URL/文本） 提取文字  价值分类  深度加工（检索+联网） 风格重写  Obsidian

"""

import os

import sys

import time

import logging

import json

from datetime import datetime

import hashlib

import argparse

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

#  模块导入

from ocr import extract_text_from_image

from transcriber import transcribe_audio

from ai_rewrite import rewrite_text_with_ai, classify_topic, repair_ocr_text

from vector_store import ObsidianVectorStore

from classifier import classify_content

from search import search_web, fetch_webpage, translate_append

from healthcheck import run_all as healthcheck

from config import (
    ZHIPUAI_API_KEY, OBSIDIAN_VAULT_PATH, OUTPUT_DIR,
    TESSERACT_PATH, CHROMA_DB_PATH, INPUT_DIR,
    TAVILY_API_KEY,
)

import re

os.makedirs(OUTPUT_DIR, exist_ok=True)

os.makedirs(INPUT_DIR, exist_ok=True)

os.makedirs("logs", exist_ok=True)

logging.basicConfig(

    level=logging.INFO,

    format='%(asctime)s - %(levelname)s - %(message)s',

    handlers=[

        logging.FileHandler('logs/app.log', encoding='utf-8'),

        logging.StreamHandler()

    ]

)

logger = logging.getLogger(__name__)

#  全局向量库

_vector_store = None

def get_vector_store():

    global _vector_store

    if _vector_store is None:

        print("   [处理] 初始化向量数据库...")

        _vector_store = ObsidianVectorStore(

            api_key="",

            vault_path=OBSIDIAN_VAULT_PATH,

            db_path=CHROMA_DB_PATH

        )

        _vector_store.index_vault()

        stats = _vector_store.get_stats()

        print(f"   向量库中 {stats['total_notes']} 篇笔记")

    return _vector_store

#  提取文字

def extract_text_from_file(file_path: str, clean_only: bool = False) -> str:

    ext = os.path.splitext(file_path)[1].lower()

    if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):

        print(f"   🖼️ 图片识别（GLM-4V-Flash）...")

        ocr_text = extract_text_from_image(file_path, ZHIPUAI_API_KEY)

        # GLM-4V 已返回干净文字，无需再 AI repair

        return ocr_text or ""

    elif ext == '.pdf':

        print(f"   [文档] PDF 提取...")

        try:

            from ocr import extract_text_from_file as pdf_extract

            return pdf_extract(file_path, TESSERACT_PATH)

        except Exception:

            import fitz

            doc = fitz.open(file_path)

            text = "\n".join(page.get_text() for page in doc)

            doc.close()

            return text.strip()

    elif ext in ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.amr'):

        print(f"   [音频] 音频转写...")

        return transcribe_audio(file_path)

    elif ext == '.docx':

        from docx import Document

        import zipfile, os as _os, re as _re

        from concurrent.futures import ThreadPoolExecutor, as_completed

        doc = Document(file_path)

        docx_text = chr(10).join(p.text for p in doc.paragraphs if p.text.strip())

        if clean_only:

            return docx_text

        # 提取 docx 内嵌图片（GLM-4V-Flash 并发识别）

        tmp_dir = _os.path.join(_os.path.dirname(file_path), '_docx_imgs')

        _os.makedirs(tmp_dir, exist_ok=True)

        img_paths = []

        with zipfile.ZipFile(file_path, 'r') as z:

            for name in z.namelist():

                if name.startswith('word/media/') and name.lower().endswith(('.png','.jpg','.jpeg')):

                    img_path = _os.path.join(tmp_dir, _os.path.basename(name))

                    with open(img_path, 'wb') as f: f.write(z.read(name))

                    if _os.path.getsize(img_path) > 1000:

                        img_paths.append(img_path)

        # 并发调用 GLM-4V-Flash（5路并发）

        img_texts = []

        if img_paths:

            count = len(img_paths)

            print(f"    🖼️ 并发识别 {count} 张图片（GLM-4V-Flash，5路并发）...")

            with ThreadPoolExecutor(max_workers=5) as pool:

                fut_map = {pool.submit(extract_text_from_image, p, ZHIPUAI_API_KEY): p for p in img_paths}

                for fut in as_completed(fut_map):

                    try:

                        result = fut.result()

                        if result and len(result.strip()) > 10:

                            img_texts.append(result)

                    except Exception:

                        pass

        # 清理临时目录

        for f in _os.listdir(tmp_dir):

            try: _os.remove(_os.path.join(tmp_dir, f))

            except: pass

        try: _os.rmdir(tmp_dir)

        except: pass

        try:

            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text

        except:

            fixed_text = docx_text

        if img_texts:

            fixed_text += chr(10)*2 + '=== 图片内容（视觉识别）===' + chr(10)*2 + (chr(10)*2).join(img_texts)

        return fixed_text

    elif ext in ('.md', '.txt'):

        print(f"   [文本] 读取文本...")

        with open(file_path, 'r', encoding='utf-8') as f:

            return f.read().strip()

    else:

        raise ValueError(f"不支持的文件格式: {ext}")

#  核心处理

def process_content(raw_text: str, source_name: str) -> str:

    raw_text = raw_text.strip()

    if not raw_text or len(raw_text) < 10:

        print(f"   [文档] 内容较短（{len(raw_text)}字符），直接保存原文: {source_name}")

        return raw_text  # 短内容也保留

    category = classify_content(ZHIPUAI_API_KEY, raw_text)

    print(f"   [定位] 分类: {category}")

    if category == 'skip':

        print(f"   ️ 无价值，丢弃: {source_name}")

        return None

    elif category == 'save_only':

        print(f"    仅保存原文")

        return raw_text

    vector_store = get_vector_store()

    topic = classify_topic(ZHIPUAI_API_KEY, raw_text)

    if isinstance(topic, dict):

        topic_name = topic.get("topic", "其他")

    else:

        topic_name = str(topic)

    print(f"   [搜索] 话题: {topic_name}")

    similar_docs, similar_metas = vector_store.retrieve_similar(

        f"{topic_name} {raw_text[:200]}", n_results=3

    )

    style_notes = similar_docs if similar_docs else []

    # 联网搜索（Bing 优先，Tavily 备胎）

    web_context = ""


    if len(style_notes) <= 1:

        print(f"   [网络] 联网搜索补充背景...")

        web_context = search_web(f"{topic_name} {raw_text[:150]}")

        if not web_context and TAVILY_API_KEY:

            print(f"   Tavily 备胎...")

            web_context = search_web(f"{topic_name} {raw_text[:150]}", TAVILY_API_KEY)

    if web_context:

        print(f"   [完成] 联网获取 {len(web_context)} 字符")

    else:

        print(f"   ️ 联网无结果")

    # 百度翻译：检测中英混杂，自动补充中文翻译

    trans_context = translate_append(raw_text)

    if trans_context:

        print(f"   🌐 检测到中英混杂，已自动翻译补充")

    print(f"   ️ AI 风格重写...")

    rewritten = rewrite_text_with_ai(

        ZHIPUAI_API_KEY, raw_text, style_notes, topic,

        web_context=web_context + trans_context

    )

    if not rewritten:

        raise RuntimeError("AI 重写返回空结果")

    print(f"   [完成] 重写完成 ({len(rewritten)} 字符)")

    return rewritten

def save_result(content, filename="", html_title=None, url=""):
    if not content:
        return ""
    title = html_title if html_title else (filename if filename else "未命名")
    from html import escape
    today_date = datetime.now().strftime("%Y-%m-%d")
    safe = "".join(c for c in title if c.isalnum() or c in " -_""").strip()
    if not safe:
        safe = "unnamed"
    safe = safe.rstrip(".")
    filename_final = f"{today_date}-{safe}.md"
    yt = title.replace(chr(34), chr(92)+chr(34))
    frontmatter = f"---\ntitle: \"{yt}\"\ndate: {today_date}\ntags: [rss, ai-generated]\n---\n\n"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    full_path = os.path.join(OUTPUT_DIR, filename_final)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + content)
    print(f"[save] {filename_final}")
    log_dir = os.path.join("logs", "daily")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{today_date}.jsonl")
    log_entry = {
        "time": datetime.now().strftime("%H:%M"),
        "file": filename_final,
        "url": url,
        "chars": len(content)
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + chr(10))
    return full_path
def process_file(file_path: str):

    file_name = os.path.basename(file_path)

    print(f"\n[{file_name}]")

    try:

        raw_text = extract_text_from_file(file_path, clean_only=True) if file_path.lower().endswith('.docx') else extract_text_from_file(file_path)

        if raw_text is None:

            raw_text = ""

        if not raw_text or len(raw_text.strip()) < 5:

            print(f"   [警告]️ 未提取到有效文字")

            # 音频短内容也保留，不丢弃

            ext = os.path.splitext(file_path)[1].lower()

            if ext in ('.mp3','.wav','.m4a','.flac','.aac','.ogg','.amr','.m4a'):

                raw_text = raw_text or "(音频文件，转写无文字内容)"

                _archive_file(file_path, "skip")

            else:

                _archive_file(file_path, "skip")

            return

        # docx：段落文本短（<100字），内容在截图里，提取全文（含RapidOCR+AI修复）后保存

        if file_path.lower().endswith('.docx') and len(raw_text.strip()) < 100:

            print(f"   [定位] 段落文本仅{len(raw_text.strip())}字，内容在截图里，提取全文并AI修复")

            full_text = extract_text_from_file(file_path)

            # extract_text_from_file 内部已调 repair_ocr_text，无需重复

            if not full_text or len(full_text.strip()) < 10:

                print(f"   [警告] 提取结果为空，跳过")

                _archive_file(file_path, "skip")

                return

            print(f"   [完成] 提取{len(full_text)}字，保存到笔记")

            save_result(full_text, os.path.splitext(file_name)[0] + ".md")

            _archive_file(file_path, "done")

            return

        result = process_content(raw_text, file_name)

        if result is None:

            _archive_file(file_path, "skip")

            return

        base_name = os.path.splitext(file_name)[0]

        save_result(result, f"{base_name}.md")

        # 添加到向量库

        try:

            vs = get_vector_store()

            doc_id = f"local_{base_name[:20]}_{datetime.now().strftime('%Y%m%d')}"

            vs.add_document(result, doc_id, {"file": file_name, "source": "local"})

        except Exception:

            pass

        _archive_file(file_path, "done")

    except Exception as e:

        print(f"   [失败] 失败: {e}")

        _archive_file(file_path, "error")

def _archive_file(file_path: str, subdir: str):

    dest_dir = os.path.join(INPUT_DIR, subdir)

    os.makedirs(dest_dir, exist_ok=True)

    dest = os.path.join(dest_dir, os.path.basename(file_path))

    try:

        os.rename(file_path, dest)

    except Exception:

        pass

#  处理 URL

def _fetch_html(url):

    """Fetch HTML content and extract title"""

    import urllib.request, re

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:

        resp = urllib.request.urlopen(req, timeout=30)

        html = resp.read().decode("utf-8", errors="replace")

        m = re.search(r'<title[^>]*>(.*?)<\/title>', html, re.I | re.S)

        title = m.group(1).strip() if m else ""

        return html, title

    except:

        return "", ""

def _html_to_markdown(html):

    """Simple HTML to Markdown conversion"""

    import re

    text = html

    # Remove nav/script/style/footer/header

    for tag in ('script', 'style', 'nav', 'header', 'footer'):

        text = re.sub(r'<' + tag + r'[^>]*>.*?<\/' + tag + r'>', '', text, flags=re.I|re.S)

    text = re.sub(r'<h1[^>]*>(.*?)<\/h1>', r'# \1', text, flags=re.I|re.S)

    text = re.sub(r'<h2[^>]*>(.*?)<\/h2>', r'## \1', text, flags=re.I|re.S)

    text = re.sub(r'<h3[^>]*>(.*?)<\/h3>', r'### \1', text, flags=re.I|re.S)

    text = re.sub(r'<p[^>]*>(.*?)<\/p>', r'\1\n\n', text, flags=re.I|re.S)

    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)

    text = re.sub(r'<li[^>]*>(.*?)<\/li>', r'- \1\n', text, flags=re.I|re.S)

    text = re.sub(r'<strong[^>]*>(.*?)<\/strong>', r'**\1**', text, flags=re.I|re.S)

    text = re.sub(r'<em[^>]*>(.*?)<\/em>', r'*\1*', text, flags=re.I|re.S)

    text = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*alt=["\'](.*?)["\'][^>]*/>', r'![\2](\1)', text, flags=re.I|re.S)

    text = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*>', r'![image](\1)', text, flags=re.I|re.S)

    text = re.sub(r'<[^>]+>', '', text)

    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

def process_url(url: str):

    """Process URL with fallback and title extraction"""

    from urllib.request import Request, urlopen

    name = hashlib.md5(url.encode()).hexdigest()[:8]

    print(f"[url] {url[:60]}")

    raw_text = ""

    html_title = ""

    # Try Jina Reader

    try:

        j_url = "https://r.jina.ai/" + url

        req = Request(j_url, headers={"Accept": "text/plain"})

        resp = urlopen(req, timeout=30)

        raw_text = resp.read().decode("utf-8", errors="replace")

        m = re.search(r'<title[^>]*>(.*?)<\/title>', raw_text, re.I | re.S)

        if m:

            html_title = m.group(1).strip()

        print(f"  [Jina] {len(raw_text)} chars")

    except Exception:

        print(f"  [Jina] failed, fallback...")

    # Fallback

    if not raw_text or len(raw_text) < 200:

        print("  [fallback] direct HTML...")

        html_raw, html_title = _fetch_html(url)

        if html_raw:

            raw_text = _html_to_markdown(html_raw)

            print(f"  [Direct] {len(raw_text)} chars, title={html_title[:40]}")

    if not raw_text:

        print("[error] cannot fetch")

        return

    # 全流水线处理（向量库检索+话题分类+联网搜索+翻译+AI重写）

    result = process_content(raw_text, f"web_{name}")

    if result is None:

        print(f"  [skip] {html_title[:40]} 被跳过")

        return

    save_result(result, "", html_title, url=url)

    # 添加到向量库

    try:

        vs = get_vector_store()

        doc_id = f"web_{name}_{datetime.now().strftime('%Y%m%d')}"

        vs.add_document(result, doc_id, {"url": url, "title": html_title, "source": "web"})

        print(f"  [vector] 已加入向量库 ({doc_id})")

    except Exception as ve:

        print(f"  [vector] 添加失败: {ve}")

# === GUI 调用函数（process_input_dir / resume_interrupted / run_pipeline）===

def process_batch():

    """批量处理 input/ 目录中的所有文件"""

    if not os.path.exists(INPUT_DIR):

        print(f"[错误] input 目录不存在: {INPUT_DIR}")

        return

    files = [f for f in os.listdir(INPUT_DIR)

             if os.path.isfile(os.path.join(INPUT_DIR, f))

             and not f.startswith('.')

             and f != 'desktop.ini']

    if not files:

        print(f"[info] input 目录为空")

        return

    print()  # blank line before batch

    print(f"[Batch] input/ 下有 {len(files)} 个文件")

    for fname in sorted(files):

        fpath = os.path.join(INPUT_DIR, fname)

        process_file(fpath)

# process_batch done

def process_input_dir():

    """处理 input/ 目录并返回处理的文件数(供 GUI 调用)"""

    process_batch()

    # 统计已归档到 output 的数量

    count = 0

    if os.path.exists(OUTPUT_DIR):

        count = len([f for f in os.listdir(OUTPUT_DIR)

                     if f.endswith('.md') and os.path.isfile(os.path.join(OUTPUT_DIR, f))])

    return count

def resume_interrupted():

    """从 checkpoint 恢复中断的文件（供 GUI 调用）"""

    try:

        from checkpoint import get_interrupted, set_stage, init_file

    except ImportError:

        return 0

    interrupted = get_interrupted()

    if not interrupted:

        return 0

    count = 0

    for relpath, info in interrupted.items():

        # 转换为绝对路径

        abspath = os.path.join(os.getcwd(), relpath) if not os.path.isabs(relpath) else relpath

        if os.path.exists(abspath):

            print(f"  [恢复] {relpath} (stage={info.get('stage','?')})")

            process_file(abspath)

            count += 1

        else:

            print(f"  [跳过] 文件不存在: {relpath}")

    return count


def _cleanup_old_input_files(max_days=15):
    """删除 input/ 及其子目录中超过 max_days 的旧文件"""
    cutoff = time.time() - max_days * 86400
    deleted = 0
    for root, _dirs, files in os.walk(INPUT_DIR):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    deleted += 1
            except Exception:
                pass
    if deleted:
        logger.info(f"清理了 {deleted} 个超过 {max_days} 天的旧输入文件")

def run_pipeline():

    """完整流水线：先恢复中断，再处理新文件"""

    print("\n=== AI 笔记流水线 ===")

    r = resume_interrupted()

    if r:

        print(f"恢复完成: {r} 个文件")

    process_input_dir()

def main():

    parser = argparse.ArgumentParser(description="AI 多模态笔记处理流水线")

    parser.add_argument("--watch", action="store_true", help="监听模式")

    parser.add_argument("--file", type=str, help="处理单个文件")

    parser.add_argument("--url", type=str, help="处理网页链接")

    parser.add_argument("--batch", action="store_true", help="批量处理 input/")

    args = parser.parse_args()

    if args.file:

        process_file(args.file)

    elif args.url:

        process_url(args.url)

    elif args.watch:

        from watcher import start_watcher

        start_watcher(INPUT_DIR)

    else:

        process_batch()

if __name__ == "__main__":

    main()

