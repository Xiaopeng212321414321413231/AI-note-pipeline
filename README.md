markdown



AI Obsidian OCR 重写工具

将扫描图片/截图中的文字，自动模仿 Obsidian 笔记风格，重写为规范的 Markdown 笔记。



技术栈

OCR: Tesseract

大模型: 智谱 AI GLM-4-Flash（免费）

语言: Python

安装

代码

· bash

pip install -r requirements.txt



\## 配置

1\. 复制 `.env.example` 为 `.env`

2\. 填写 API Key 和 Obsidian 路径



\## 运行

```bash

python src/main.py



