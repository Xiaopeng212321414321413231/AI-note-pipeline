# -*- coding: utf-8 -*-
"""Fix docx handling in main.py"""
import re

with open("src/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find docx block
start = None
for i, line in enumerate(lines):
    if "elif ext == '.docx':" in line:
        start = i
        break

end = None
for i in range(start + 1, len(lines)):
    stripped = lines[i].lstrip()
    if i > start + 1 and (stripped.startswith("elif ") or stripped.startswith("else:")):
        end = i
        break
if end is None:
    end = len(lines)

print(f"docx block: lines {start+1}-{end}")

new_lines = [
    "        from docx import Document\n",
    "        import zipfile, os as _os, tempfile, shutil\n",
    "        doc = Document(file_path)\n",
    '        docx_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())\n',
    "        img_texts = []\n",
    "        with zipfile.ZipFile(file_path, 'r') as z:\n",
    "            imgs = [n for n in z.namelist() if n.startswith('word/media/') and n.lower().endswith(('.png','.jpg','.jpeg'))]\n",
    "            if imgs:\n",
    "                tmp = tempfile.mkdtemp()\n",
    "                for name in imgs:\n",
    "                    z.extract(name, tmp)\n",
    "                    img_path = _os.path.join(tmp, name)\n",
    "                    if _os.path.getsize(img_path) > 5000:\n",
    "                        ocr_result = extract_text_from_image(img_path)\n",
    "                        if ocr_result and len(ocr_result.strip()) > 20:\n",
    "                            clean_chars = len(re.findall(r'[\u4e00-\u9fff\u3000-\u30ffa-zA-Z0-9 \n\r.,!?;:()\[\]{}<>\-+=@#$%^&*|/\\\'\"`~]', ocr_result))\n",
    "                            ratio = clean_chars / len(ocr_result) if len(ocr_result) > 0 else 0\n",
    "                            if ratio > 0.4:\n",
    "                                img_texts.append(ocr_result)\n",
    "                shutil.rmtree(tmp, ignore_errors=True)\n",
    "        try:\n",
    "            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text\n",
    "        except:\n",
    "            fixed_text = docx_text\n",
    "        if img_texts:\n",
    '            fixed_text += "\n\n=== 图片内容（OCR） ===\n\n" + "\n\n".join(img_texts)\n',
    "        return fixed_text\n",
    "    \n",
]

lines[start:end] = new_lines
with open("src/main.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("main.py docx部分已更新！")
