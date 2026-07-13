# -*- coding: utf-8 -*-
"""提取文本的统一入口：图片(RapidOCR→Tesseract)、PDF、Word、音频(Whisper)"""
import os, tempfile, shutil, subprocess as sp

SUPPORTED_AUDIO = (".mp3",".wav",".m4a",".flac",".aac",".ogg",".amr")
SUPPORTED_IMAGE = (".png",".jpg",".jpeg",".bmp",".tiff",".webp")

TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ---------- RapidOCR 引擎（主OCR，质量远优于Tesseract） ----------
_RAPID_ENGINE = None

def _get_rapid_engine():
    """懒加载 RapidOCR 引擎（单例，避免每次重新加载模型）"""
    global _RAPID_ENGINE
    if _RAPID_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_ENGINE = RapidOCR()
        except ImportError:
            _RAPID_ENGINE = False  # 标记不可用
    return _RAPID_ENGINE if _RAPID_ENGINE is not False else None

def _rapid_ocr(path):
    """使用 RapidOCR 识别图片，返回文字字符串"""
    engine = _get_rapid_engine()
    if engine is None:
        return None  # RapidOCR 不可用，让调用者降级
    try:
        result, elapse = engine(path)
        if result:
            texts = [line[1] for line in result]
            return '\n'.join(texts)
        return ""
    except Exception:
        return None  # 出错，降级

def _tesseract_ocr(path, lang):
    """用指定语言跑 Tesseract，返回文字（安全编码处理）"""
    try:
        r = sp.run([TESSERACT, path, "stdout", "-l", lang, "--psm", "3"],
                    capture_output=True, timeout=30)
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""

def extract_text_from_image(path):
    """从图片提取文字：RapidOCR 为主，Tesseract 为后备"""
    # 1. 尝试 RapidOCR（高质量，支持中英混合）
    rapid_result = _rapid_ocr(path)
    if rapid_result is not None and len(rapid_result.strip()) > 5:
        return repair_ocr_text(rapid_result)
    
    # 2. 后备：Tesseract 中英混合
    txt1 = _tesseract_ocr(path, "chi_sim+eng")
    txt2 = _tesseract_ocr(path, "eng")
    
    if not txt1 and not txt2:
        return rapid_result or ""
    if not txt1:
        return repair_ocr_text(txt2) if txt2.strip() else ""
    if not txt2:
        return repair_ocr_text(txt1) if txt1.strip() else ""
    
    score1 = sum(1 for c in txt1 if c.isalpha() or c.isdigit()) / max(len(txt1), 1)
    score2 = sum(1 for c in txt2 if c.isalpha() or c.isdigit()) / max(len(txt2), 1)
    
    if len(txt2) > len(txt1) * 1.2 and score2 > 0.7:
        best = txt2
    elif score1 >= score2:
        best = txt1
    else:
        best = txt2
    
    return repair_ocr_text(best)

def repair_ocr_text(text):
    """本地简单清理 OCR 结果（去空白行、去空格）"""
    if not text or not text.strip():
        return ""
    text = text.replace(" ", "").replace("\n\n", "\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines)

def extract_text(file_path: str) -> str:
    """统一入口：根据文件类型选择提取方式"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_AUDIO:
        from transcriber import transcribe_audio
        return transcribe_audio(file_path)
    if ext in SUPPORTED_IMAGE:
        return extract_text_from_image(file_path)
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    for enc in ('utf-8', 'gbk', 'gb2312', 'gb18030'):
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read().strip()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()

def extract_text_from_pdf(path):
    try:
        from PyPDF2 import PdfReader
        r = PdfReader(path)
        return "\n".join(p.extract_text() for p in r.pages if p.extract_text())
    except:
        pass
    try:
        txt = _tesseract_ocr(path, "chi_sim+eng")
        return txt
    except:
        return ""

def extract_text_from_docx(path):
    """提取 docx 文字 + 图片 OCR"""
    try:
        from docx import Document
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        text = ""
    
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            imgs = sorted([n for n in z.namelist() if n.startswith("word/media/") and n.lower().endswith(('.png','.jpg','.jpeg'))])
            if not imgs:
                return text.strip()
            
            tmp = tempfile.mkdtemp()
            img_texts = []
            for img_name in imgs:
                z.extract(img_name, tmp)
                img_path = os.path.join(tmp, img_name)
                if os.path.getsize(img_path) > 5000:
                    ocr_result = extract_text_from_image(img_path)
                    if ocr_result and len(ocr_result) > 10:
                        img_texts.append(ocr_result)
            shutil.rmtree(tmp, ignore_errors=True)
            
            if img_texts:
                if text.strip():
                    text += "\n\n" + "\n---\n".join(img_texts)
                else:
                    text = "\n---\n".join(img_texts)
    except Exception:
        pass
    
    return text.strip()
