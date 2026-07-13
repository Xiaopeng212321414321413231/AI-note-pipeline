# -*- coding: utf-8 -*-
with open("src/main.py","rb") as f:
    data=f.read()

# Step 1: add re import
data = data.replace(
    b"import zipfile, os as _os",
    b"import zipfile, os as _os, re as _re"
)

# Step 2: replace size threshold and add readability check
old_ocr = b"""                    ocr_result = extract_text_from_image(img_path)
                    if ocr_result.strip():
                        img_texts.append(ocr_result)"""
new_ocr = b"""                    if _os.path.getsize(img_path) > 5000:
                        ocr_result = extract_text_from_image(img_path)
                        if ocr_result and len(ocr_result.strip()) > 20:
                            good = sum(1 for c in ocr_result if 32 <= ord(c) < 127 or '一' <= c <= '鿿')
                            if good / max(len(ocr_result), 1) > 0.4:
                        img_texts.append(ocr_result)"""
data = data.replace(old_ocr, new_ocr)

# Step 3: replace combined+repair logic with paragraph-only repair
old_combined = b"""        combined = docx_text
        if img_texts:
            combined += '

=== 图片内容 ===

' + '

'.join(img_texts)
        try:
            return repair_ocr_text(ZHIPUAI_API_KEY, combined)
        except:
            return combined"""
new_combined = b"""        try:
            fixed_text = repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text
        except:
            fixed_text = docx_text
        if img_texts:
            fixed_text += '

=== 图片内容（OCR） ===

' + '

'.join(img_texts)
        return fixed_text"""
data = data.replace(old_combined, new_combined)

with open("src/main.py","wb") as f:
    f.write(data)
print("main.py modified OK")
