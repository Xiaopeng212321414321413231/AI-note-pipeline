with open('src/ocr.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_text = "'请提取这张图片中的所有文字内容，包括代码和文本。如果是代码截图，保持缩进、空格、符号完全不变。如果是中文段落，完整提取。不要添加解释说明。'"

new_text = (
    "'你是一个文档识别助手。请提取这张图片中的所有内容，严格按以下规则输出：\n\n"
    "1. 【代码检测】如果图片包含Python代码（有缩进、def/for/if/print/变量赋值等特征），"
    "用 ```python 和 ``` 包裹完整的代码块，包括其中的中文注释（#开头的内容也放在代码块内部）\n"
    "2. 【注释处理】# 开头的注释行（如 # 方式一、# 案例等）要放在代码块内部，不能放到外面当标题\n"
    "3. 【表格】表格内容用 Markdown 表格格式 |---|---| 输出\n"
    "4. 【标题】章节标题用 # 号表示层级（注意和代码中的 # 注释区分）\n"
    "5. 【正文】普通段落直接输出文本\n"
    "6. 【准确性】不要添加原图中没有的内容，不要输出对图片的描述\n"
    "\n格式要求：\n"
    "- 代码必须用 ```python 包裹，注释行保持为 # 开头放在代码块内\n"
    "- 中文文字必须完整保留'"
)

if old_text in text:
    text = text.replace(old_text, new_text)
    with open('src/ocr.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('✅ 提示词已更新')
else:
    print('❌ 旧提示词匹配失败')
    # 找包含"请提取"的行
    for i, line in enumerate(text.split('\n')):
        if '请提取' in line:
            print(f'行{i+1}: {line[:100]}')
