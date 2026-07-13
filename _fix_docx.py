import os
os.chdir("G:/ai软件/git/zhipu manage")
with open("src/main.py","r",encoding="utf-8") as fh:
    lines = fh.readlines()
new_block = [
    "    elif ext == '.docx':\n",
    '        from docx import Document\n',
    '        import zipfile, os as _os, re as _re\n',
    '        doc = Document(file_path)\n',
    "        docx_text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())\n",
    '        # 提取 docx 内嵌图片并 OCR（过滤垃圾识别）\n',
    '        img_texts = []\n',
    "        tmp_dir = _os.path.join(_os.path.dirname(file_path), '_docx_imgs')\n",
    '        _os.makedirs(tmp_dir, exist_ok=True)\n',
    "        with zipfile.ZipFile(file_path, 'r') as z:\n",
    '            for name in z.namelist():\n',
    "                if name.startswith('word/media/') and name.lower().endswith(('.png','.jpg','.jpeg')):\n",
    '                    img_path = _os.path.join(tmp_dir, _os.path.basename(name))\n',
    "                    with open(img_path, 'wb') as f: f.write(z.read(name))\n",
    '                    if _os.path.getsize(img_path) > 5000:\n',
    '                        ocr_result = extract_text_from_image(img_path)\n',
    '                        if ocr_result and len(ocr_result.strip()) > 20:\n',
    "                            good = sum(1 for c in ocr_result if c.isprintable() or '一' <= c <= '鿿')\n",
    '                            if good / max(len(ocr_result), 1) > 0.4:\n',
    '                        img_texts.append(ocr_result)\n',
    '        for f in _os.listdir(tmp_dir):\n',
    '            try: _os.remove(_os.path.join(tmp_dir, f))\n',
    '            except: pass\n',
    '        try: _os.rmdir(tmp_dir)\n',
    '        except: pass\n',
    '        try:\n',
    '            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text\n',
    '        except:\n',
    '            fixed_text = docx_text\n',
    '        if img_texts:\n',
    "            fixed_text += '\n\n=== 图片内容（OCR） ===\n\n' + '\n\n\n\n'.join(img_texts)\n",
    '        return fixed_text\n',
]
lines[91:120] = new_block
with open("src/main.py","w",encoding="utf-8") as fh:
    fh.writelines(lines)
print("OK")
