import zipfile
import os
import tempfile

def extract_images_from_docx(docx_path, output_dir):
    """从 docx 里提取图片"""
    os.makedirs(output_dir, exist_ok=True)
    images = []
    with zipfile.ZipFile(docx_path, 'r') as z:
        for name in z.namelist():
            if name.startswith('word/media/') and name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                ext = os.path.splitext(name)[1]
                out_name = f"docx_img_{len(images)}{ext}"
                out_path = os.path.join(output_dir, out_name)
                with open(out_path, 'wb') as f:
                    f.write(z.read(name))
                images.append(out_path)
    return images

# 测试
DOCX_PATH = "G:/ai软件/git/zhipu manage/input/done/新建 DOCX 文档 (2).docx"
TMP_DIR = "G:/ai软件/git/zhipu manage/tmp_images"
imgs = extract_images_from_docx(DOCX_PATH, TMP_DIR)
print(f"提取了 {len(imgs)} 张图片")
for p in imgs:
    sz = os.path.getsize(p)
    print(f"  {p} ({sz} bytes)")