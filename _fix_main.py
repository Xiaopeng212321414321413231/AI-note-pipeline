# -*- coding: utf-8 -*-
import os
os.chdir("G:/ai软件/git/zhipu manage")
with open("src/main.py","rb") as fh:
    data = fh.read()

# 1. Add re import
data = data.replace(b"import zipfile, os as _os", b"import zipfile, os as _os, re as _re")
print("1/4 import done")

# 2. Replace image handling: size check + length check
data = data.replace(
    b"ocr_result = extract_text_from_image(img_path)
                    if ocr_result.strip():
                        img_texts.append(ocr_result)",
    b"if _os.path.getsize(img_path) > 5000:
                        ocr_result = extract_text_from_image(img_path)
                        if ocr_result and len(ocr_result.strip()) > 20:"
)
print("2/4 image handling done")

# 3. Add readability filter before img_texts.append
# Find "img_texts.append(ocr_result)
" after the OCR block
# Insert readability filter before it
old = b"                        img_texts.append(ocr_result)
        for f in _os.listdir(tmp_dir)"
new = b"                            good = sum(1 for c in ocr_result if c.isprintable() or ("一" <= c <= "鿿"))
"
new += b"                            if good / max(len(ocr_result), 1) > 0.4:
                        img_texts.append(ocr_result)
"
new += b"        for f in _os.listdir(tmp_dir)"
data = data.replace(old, new)
print("3/4 filter done")

# 4. Replace combined/repair logic: only repair paragraphs, not OCR garbage
old = b"        combined = docx_text
        if img_texts:
"
old += b"            combined += '\n\n=== 图片内容 ===\n\n' + '\n\n'.join(img_texts)
"
old += b"        try:
            return repair_ocr_text(ZHIPUAI_API_KEY, combined)
        except:
            return combined"
new = b"        try:
            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text"
new += b"
        except:
            fixed_text = docx_text
"
new += b"        if img_texts:
            fixed_text += '\n\n=== 图片内容（OCR） ===\n\n' + '\n\n'.join(img_texts)
"
new += b"        return fixed_text"
data = data.replace(old, new)
print("4/4 combined logic replaced")

with open("src/main.py","wb") as fh:
    fh.write(data)
print("ALL DONE")
