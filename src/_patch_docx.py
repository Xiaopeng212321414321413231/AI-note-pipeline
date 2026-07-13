# -*- coding: utf-8 -*-
import os
os.chdir("G:/ai软件/git/zhipu manage")

with open("src/main.py","r",encoding="utf-8") as f:
    orig = f.readlines()

# Build replacement block
block = []

block.append("    elif ext == '.docx':")
block.append('        from docx import Document')
block.append('        import zipfile, os as _os, re as _re')
block.append('        doc = Document(file_path)')
block.append("        docx_text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())")
block.append('        # 提取 docx 内嵌图片并 OCR（过滤垃圾识别）')
block.append('        img_texts = []')
block.append("        tmp_dir = _os.path.join(_os.path.dirname(file_path), '_docx_imgs')")
block.append('        _os.makedirs(tmp_dir, exist_ok=True)')
block.append("        with zipfile.ZipFile(file_path, 'r') as z:")
block.append('            for name in z.namelist():')
block.append("                if name.startswith('word/media/') and name.lower().endswith(('.png','.jpg','.jpeg')):")
block.append('                    img_path = _os.path.join(tmp_dir, _os.path.basename(name))')
block.append("                    with open(img_path, 'wb') as f: f.write(z.read(name))")
block.append('                    if _os.path.getsize(img_path) > 5000:')
block.append('                        ocr_result = extract_text_from_image(img_path)')
block.append('                        if ocr_result and len(ocr_result.strip()) > 20:')
block.append("                            good = sum(1 for c in ocr_result if c.isprintable() or '一' <= c <= '鿿')")
block.append('                            if good / max(len(ocr_result), 1) > 0.4:')
block.append('                        img_texts.append(ocr_result)')
block.append('        for f in _os.listdir(tmp_dir):')
block.append('            try: _os.remove(_os.path.join(tmp_dir, f))')
block.append('            except: pass')
block.append('        try: _os.rmdir(tmp_dir)')
block.append('        except: pass')
block.append('        try:')
block.append('            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text')
block.append('        except:')
block.append('            fixed_text = docx_text')
block.append('        if img_texts:')
block.append("            fixed_text += '\n\n=== 图片内容（OCR） ===\n\n' + '\n\n'.join(img_texts)")
block.append('        return fixed_text')

# Find docx block boundaries
start = None
for i, l in enumerate(orig):
    if "elif ext == '.docx':" in l:
        start = i
        break

end = None
for i in range(start+1, len(orig)):
    s = orig[i].lstrip()
    if i > start+1 and (s.startswith("elif ") or s.startswith("else:")):
        end = i
        break
if end is None:
    end = len(orig)

print(f"Replacing lines {start+1} to {end}")
orig[start:end] = [l + chr(10) for l in block]

with open("src/main.py","w",encoding="utf-8") as f:
    f.writelines(orig)
print("main.py patched")
