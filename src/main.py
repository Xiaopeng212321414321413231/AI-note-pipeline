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
import sys
sys.path.insert(0, os.path.dirname(__file__))
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

#  模块导入 
from ocr import extract_text_from_image
from transcriber import transcribe_audio
from ai_rewrite import rewrite_text_with_ai, classify_topic, repair_ocr_text
from vector_store import ObsidianVectorStore
from classifier import classify_content
from search import search_web, fetch_webpage
from healthcheck import run_all as healthcheck

#  配置（注意变量名：ZHIPUAI_API_KEY 不是 ZHIPU_API_KEY）
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "G:/ai软件/obsidian/ai新闻")
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "C:/Program Files/Tesseract-OCR/tesseract.exe")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
INPUT_DIR = os.getenv("INPUT_DIR", "input")
OUTPUT_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "AI生成笔记")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

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
    print(f"    参考笔记: {len(style_notes)} 篇")

    web_context = ""
    if len(style_notes) <= 1 and TAVILY_API_KEY:
        print(f"   [网络] 联网搜索补充背景...")
        web_context = search_web(f"{topic_name} {raw_text[:150]}", TAVILY_API_KEY)
        if web_context:
            print(f"   [完成] 联网获取 {len(web_context)} 字符")
        else:
            print(f"   ️ 联网无结果")

    print(f"   ️ AI 风格重写...")
    rewritten = rewrite_text_with_ai(
        ZHIPUAI_API_KEY, raw_text, style_notes, topic
    )
    if not rewritten:
        raise RuntimeError("AI 重写返回空结果")
    print(f"   [完成] 重写完成 ({len(rewritten)} 字符)")
    return rewritten

#  保存 
def save_result(content: str, filename: str):
    if content is None or not content.strip():
        print("   \u26a0\ufe0f \u5185\u5bb9\u4e3a\u7a7a\uff0c\u4e0d\u4fdd\u5b58")
        return
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
        print(f"   \u2705 \u5df2\u4fdd\u5b58: {out_path}")
    import json,datetime as _dt
    os.makedirs("logs/daily", exist_ok=True)
    log_path = os.path.join("logs", "daily", _dt.datetime.now().strftime("%Y-%m-%d") + ".jsonl")
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(json.dumps({"time":_dt.datetime.now().strftime("%H:%M:%S"),"file":os.path.basename(filename),"chars":len(content),"path":os.path.abspath(out_path)}, ensure_ascii=False) + chr(10))
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
def process_url(url: str):
    print(f"\n[网络] [{url[:60]}...]")
    try:
        import urllib.request
        reader_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(reader_url, headers={"Accept": "text/plain"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_text = resp.read().decode('utf-8')

        if not raw_text or len(raw_text.strip()) < 50:
            print(f"   [警告]️ 网页内容太短")
            return

        result = process_content(raw_text, url)
        if result:
            name = hashlib.md5(url.encode()).hexdigest()[:8]
            save_result(result, f"web_{name}.md")
    except Exception as e:
        print(f"   [失败] 网页处理失败: {e}")

#  批量处理 
#  批量处理
def process_batch():
    # 1. 启动健康检查
    report, has_error = healthcheck()
    print(report)
    if has_error:
        print('  ❌ 环境检查未通过，请修复后重试')
        return

    # 2. 自动重试 error 文件夹里的文件（移回 input）
    error_dir = os.path.join(INPUT_DIR, 'error')
    if os.path.isdir(error_dir):
        error_files = [f for f in os.listdir(error_dir) if os.path.isfile(os.path.join(error_dir, f)) and not f.startswith('.')]
        if error_files:
            print()
            print('  ' + '='*46)
            print(f'  🔄 发现 {len(error_files)} 个待重试文件，正在移回...')
            print('  ' + '='*46)
            for f in error_files:
                src = os.path.join(error_dir, f)
                dst = os.path.join(INPUT_DIR, f)
                try:
                    os.rename(src, dst)
                    print(f'    ↩️ {f}')
                except Exception as e:
                    print(f'    ⚠️ {f} 移动失败: {e}')

    # 3. 扫描 input 目录
    if not os.path.isdir(INPUT_DIR):
        print('input 目录不存在')
        return
    files = sorted([
        os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR)
        if os.path.isfile(os.path.join(INPUT_DIR, f))
        and not f.startswith('.')
    ])
    skip_dirs = {os.path.join(INPUT_DIR, d) for d in ('done', 'skip', 'error')}
    files = [f for f in files if not any(f.startswith(d) for d in skip_dirs)]
    if not files:
        print('[失败] input 文件夹为空（无待处理文件）')
        return
    print()
    print('  ' + '='*46)
    print(f'  共发现 {len(files)} 个文件')
    print('  ' + '='*46)
    for f in files:
        process_file(f)
    print()
    print('  ' + '='*46)
    print('  完成！')
    print('  ' + '='*46)

#  主入口 
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
