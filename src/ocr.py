"""提取文本的统一入口：图片(OCR)、PDF、Word、音频(Whisper)"""
import os
from transcriber import transcribe_audio

SUPPORTED_AUDIO = (".mp3",".wav",".m4a",".flac",".aac",".ogg",".amr")
SUPPORTED_IMAGE = (".png",".jpg",".jpeg",".bmp",".tiff",".webp")

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_AUDIO:
        return transcribe_audio(file_path)
    if ext in SUPPORTED_IMAGE:
        return extract_text_from_image(file_path)
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def extract_text_from_image(path):
    import subprocess as sp
    tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    txt = sp.run([tesseract, path, "stdout", "-l", "chi_sim+eng"], capture_output=True, text=True).stdout.strip()
    return repair_ocr_text(txt) if txt else txt

def repair_ocr_text(text):
    text = text.replace(" ", "").replace("\n\n", "\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines)

def extract_text_from_pdf(path):
    try:
        from PyPDF2 import PdfReader
        r = PdfReader(path)
        return "\n".join(p.extract_text() for p in r.pages if p.extract_text())
    except:
        pass
    try:
        import subprocess as sp
        txt = sp.run([r"C:\Program Files\Tesseract-OCR\tesseract.exe", path, "stdout", "-l", "chi_sim+eng"], capture_output=True, text=True).stdout.strip()
        return txt
    except:
        return ""

def extract_text_from_docx(path):
    try:
        from docx import Document
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
        import zipfile, tempfile
        try:
            with zipfile.ZipFile(path) as z:
                imgs = [n for n in z.namelist() if n.startswith("word/media/")]
                if imgs:
                    tmp = tempfile.mkdtemp()
                    for img in imgs:
                        z.extract(img, tmp)
                        img_path = os.path.join(tmp, img)
                        if os.path.getsize(img_path) > 1000:
                            img_text = extract_text_from_image(img_path)
                            if img_text:
                                text += "\n" + img_text
        except:
            pass
        return text
    except:
        return ""
