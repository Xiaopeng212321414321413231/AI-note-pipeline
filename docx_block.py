# replacement for docx block in main.py
    elif ext == '.docx':
        from docx import Document
        import zipfile, os as _os, re as _re
        doc = Document(file_path)
        docx_text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        # 提取 docx 内嵌图片并 OCR（过滤垃圾识别）
        img_texts = []
        tmp_dir = _os.path.join(_os.path.dirname(file_path), '_docx_imgs')
        _os.makedirs(tmp_dir, exist_ok=True)
        with zipfile.ZipFile(file_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('word/media/') and name.lower().endswith(('.png','.jpg','.jpeg')):
                    img_path = _os.path.join(tmp_dir, _os.path.basename(name))
                    with open(img_path, 'wb') as f: f.write(z.read(name))
                    if _os.path.getsize(img_path) > 5000:
                        ocr_result = extract_text_from_image(img_path)
                        if ocr_result and len(ocr_result.strip()) > 20:
                            good = sum(1 for c in ocr_result if c.isprintable() or '一' <= c <= '鿿')
                            if good / max(len(ocr_result), 1) > 0.4:
                        img_texts.append(ocr_result)
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
            fixed_text += '\n\n=== 图片内容（OCR） ===\n\n' + '\n\n'.join(img_texts)
        return fixed_text
last_line: "            fixed_text += '\\n\\n=== 图片内容（OCR） ===\\n\\n' + '\\n\\n'.join(img_texts)"
separator_js: "'\\n\\n'"
