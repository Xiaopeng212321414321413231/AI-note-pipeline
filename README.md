# AI 多模态笔记处理流水线

> 图片/PDF/Word/音频/网页 → OCR/ASR → 向量检索+联网补充 → AI 风格重写 → Obsidian 归档

一条全自动的 AI 笔记流水线，支持多种输入格式，自动提取文字、分类话题、检索相关笔记、联网补充背景，最后以个人风格重写并存入 Obsidian vault。

## 功能

| 功能 | 说明 |
|------|------|
| 图片 OCR | Tesseract 识别截图/扫描件（中文+英文） |
| PDF 提取 | 自动解析 PDF 文字内容 |
| Word 文档 | .docx 文字 + 内嵌图片 OCR |
| 音频转写 | Whisper tiny 离线转写（支持 >5分钟长音频自动切片） |
| 网页抓取 | 输入 URL 自动提取正文 |
| 文本/Markdown | 直接读取 .txt/.md |
| 话题分类 | 智谱 AI 自动分类 |
| 向量检索 | ChromaDB + all-MiniLM-L6-v2 本地语义检索（844 篇） |
| 联网补充 | **Bing 优先**（免费无限次），Tavily 备用 |
| 中英翻译 | 百度大模型翻译 API，中英混杂自动翻译补充 |
| 智能联网 | 参考笔记 ≥ 2 篇时自动跳过联网，节省 API 额度 |
| AI 风格重写 | 模仿 Obsidian 笔记风格，保留全部原始信息 |
| GUI 控制面板 | Tkinter 界面 — 启动/停止监听、实时日志 |
| 文件监听 | watchdog 自动处理拖入 input/ 的文件 |
| 每日报表 | 每晚 21:00 自动生成流水线日报 |

## 搜索与翻译

**联网搜索（Bing → Tavily）**
- **Bing 搜索**：HTTP 直接请求，国内可用，无次数限制，不需要 API Key
- **Tavily 搜索**：当 Bing 无结果时自动切换为备用
- **智能触发**：仅在参考笔记 ≤ 1 篇时联网，节省额度

**百度翻译（大模型翻译 API）**
- 检测到中英混杂文本时自动翻译中文并追加在笔记后
- 使用 Bearer Token 鉴权（无需 MD5 签名）
- 纯中文文本自动跳过，不浪费额度

## 快速开始

### 安装
```bash
pip install -r requirements.txt
```

### 配置
复制 `.env.example` 为 `.env`，填写 API Key：

```env
ZHIPUAI_API_KEY=xxx           # 智谱 API key（必填）
BAIDU_APP_ID=xxx              # 百度 OCR（可选）
BAIDU_SECRET_KEY=xxx          # 百度 OCR 密钥（可选）
FANYI_APP_ID=xxx              # 百度翻译 APPID（可选）
FANYI_SECRET_KEY=xxx          # 百度翻译密钥（可选）
TAVILY_API_KEY=xxx            # Tavily 搜索（可选，Bing 不需要 key）
```

### 使用
```bash
# GUI 控制面板（推荐）
python src/gui.py

# 批量处理
python src/main.py

# 监听模式
python src/main.py --watch
```

## 项目结构

```
src/
  main.py          # 主流水线
  ocr.py           # 图片/PDF/Word OCR
  transcriber.py   # 音频转写（Whisper + 切片）
  vector_store.py  # ChromaDB 向量检索
  classifier.py    # 话题分类
  search.py        # 联网搜索（Bing+Tavily）+ 百度翻译
  note_loader.py   # 加载参考笔记
  ai_rewrite.py    # AI 风格重写
  watcher.py       # 文件监听
  gui.py           # Tkinter 面板
  daily_report.py  # 每日日报
```

## 关联资源

- GitHub: https://github.com/Xiaopeng212321414321413231/AI-note-pipeline
- 驱动模型：智谱 GLM-4V-Flash（免费）
- 向量数据库：ChromaDB（本地，all-MiniLM-L6-v2）
