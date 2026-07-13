# -*- coding: utf-8 -*-
import os
os.chdir("G:/ai软件/git/zhipu manage")
with open("src/main.py","r") as f:
    c = f.read()
idx=c.find("elif ext == '.docx':")
rest=c[idx:]
end=rest.find("elif ext in")
old=rest[:end]
import re
new = re.sub(r"from docx import Document.*?import zipfile, os as _os", "from docx import Document
        import zipfile, os as _os, re as _re", old)
new = new.replace("if ocr_result.strip():", "if _os.path.getsize(img_path) > 5000:
                        ocr_result = extract_text_from_image(img_path)
                        if ocr_result and len(ocr_result.strip()) > 20:")
new = re.sub(r"combined = docx_text
        if img_texts:.*?return combined", "try:
            return repair_ocr_text(ZHIPUAI_API_KEY, docx_text) if docx_text.strip() else docx_text
        except:
            return docx_text", new, flags=re.DOTALL)
print("NEW BLOCK:")
print(new)
