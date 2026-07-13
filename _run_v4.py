"""运行 GLM-4V 流水线并保存结果"""
import sys, os
sys.path.insert(0, 'src')

# 加载 .env
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
            k, _, v = line.partition('=')
            os.environ[k.strip()] = v.strip()

from main import extract_text_from_file

docx = r'G:\ai软件\git\zhipu manage\input\2026.7.12python笔记.docx'
print(f"处理: {os.path.basename(docx)} ({os.path.getsize(docx)//1024} KB)")

result = extract_text_from_file(docx)

out = r'G:\ai软件\obsidian\ai新闻\AI生成笔记\2026.7.12python笔记_v4_GLM4V.md'
with open(out, 'w', encoding='utf-8') as f:
    f.write(result)

print(f"✅ 完成！{len(result)} 字符 -> {out}")
