# AI 多模态笔记处理流水线 v2.6

> 图片/PDF/Word/音频/网页 → OCR/ASR → 向量检索+联网补充 → AI 中英双语重写 → Obsidian 归档

全自动 AI 笔记流水线，支持 8 种输入格式，自动提取文字 → 分类话题 → 语义检索相似笔记 → 联网补充 → 以个人风格中英双语重写 → 存入 Obsidian vault。

🎯 **自动运行**：每日 08:00 / 14:20 / 20:00 三次定时任务，全无人值守。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 图片 OCR | glm-4v-flash → RapidOCR → Tesseract（中文+英文）三级递进 |
| PDF 提取 | ZhDocParser → PyMuPDF → OCR 三级递进 |
| Word 文档 | .docx 文字 + 内嵌图片 OCR（GLM-4V 并发识别） |
| 音频转写 | faster-whisper tiny CPU int8，>5min 自动切片 |
| 网页抓取 | Jina Reader → 原生 urllib fallback |
| 文本/Markdown | 直接读取 .txt / .md |
| RSS 订阅 | 量子位 / 机器之心 / Karpathy / Sam Altman / 知乎专栏 |
| 话题分类 | glm-4-flash 自动三级分类（skip / save_only / deep_rewrite） |
| 向量检索 | ChromaDB + all-MiniLM-L6-v2 本地语义检索 |
| 联网补充 | **Bing 直连优先**（免费无限次），Tavily 备胎 |
| 中英翻译 | 百度大模型翻译 API，中英混杂自动翻译 |
| 智能联网 | 参考笔记 ≥ 2 篇时自动跳过联网，节省 API 额度 |
| AI 风格重写 | 中英双语输出：英文 → 中文翻译引用块 |
| GUI 控制面板 | Tkinter 界面，分区：本地文件 / 联网处理 |
| 文件监听 | watchdog 自动处理拖入 input/ 的文件 |
| 每日报表 | 每晚 21:00 自动生成流水线日报嵌入 Obsidian |
| **日志轮转** | 10MB 自动分割，保留 15 天，不怕撑爆磁盘 |
| **input 自动清理** | 处理后超过 15 天的旧文件自动删除 |
| **启动配置校验** | 跑之前检查 API Key / 路径是否有效 |
| **健康检查** | Healthchecks.io 心跳，流水线崩了发告警 |
| **增量索引** | ChromaDB 启动只扫新文件，节省 3-5 秒 |
| **队列可见性** | 启动时打印「待处理 X 条 / 去重 Y 条」 |
| **代码质量门禁** | ruff 零错误 + pytest 7 条集成测试 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows 10+（推荐；Linux/macOS 需调整路径）
- 推荐：`uv` 包管理器（`pip install uv`）

### 安装

```bash
git clone https://github.com/Xiaopeng212321414321413231/AI-note-pipeline.git
cd AI-note-pipeline
uv pip install -r requirements.txt
```

### 配置

创建 `.env` 文件：

```env
# 🔴 必填
ZHIPUAI_API_KEY=xxx              # 智谱 API Key（驱动全部 AI 推理）

# 🟡 建议填写
HEALTHCHECK_UUID=xxx             # Healthchecks.io UUID（心跳告警，免费）

# 🟢 可选
BAIDU_APP_ID=xxx                 # 百度 OCR
BAIDU_SECRET_KEY=xxx             # 百度 OCR 密钥
FANYI_APP_ID=xxx                 # 百度翻译 APPID
FANYI_SECRET_KEY=xxx             # 百度翻译密钥
TAVILY_API_KEY=xxx               # Tavily 搜索（Bing 不需要 key）
```

### 运行

```bash
# GUI 控制面板（推荐入门）
python src/gui.py

# 完整流水线（自动处理 input/ + RSS 队列）
python src/main.py --batch

# 监听模式
python src/main.py --watch

# 单文件处理
python src/main.py --file "路径/文件.pdf"

# 单 URL 处理
python src/main.py --url "https://example.com/article"
```

---

## 项目结构

```
AI-note-pipeline/
├── src/
│   ├── main.py          # 流水线编排中心
│   ├── config.py        # 集中化配置
│   ├── notify.py        # Healthchecks.io 心跳
│   ├── ai_rewrite.py    # GLM-4-Flash 推理核心
│   ├── classifier.py    # 内容价值三级分类
│   ├── vector_store.py  # ChromaDB（增量索引）
│   ├── search.py        # Bing + Tavily + 百度翻译
│   ├── ocr.py           # GLM-4V → RapidOCR → Tesseract
│   ├── zh_parser.py     # ZhDocParser 结构化解析
│   ├── transcriber.py   # faster-whisper 音频转写
│   ├── gui.py           # Tkinter 控制面板
│   ├── healthcheck.py   # 启动配置校验
│   ├── daily_report.py  # 日报生成
│   ├── rss_importer.py  # RSS 源导入
│   ├── watcher.py       # 文件监听
│   ├── webhook_bridge.py # HTTP API :9876
│   ├── checkpoint.py    # 断点续传
│   └── note_loader.py   # 笔记加载
├── tests/
│   └── test_pipeline.py # 7 条集成测试
├── data/
│   ├── chroma_db/       # ChromaDB 持久化
│   ├── input/           # 输入文件（自动清理 15 天以上旧文件）
│   │   ├── done/        # 成功归档
│   │   └── error/       # 失败归档
│   ├── rss_queue.json   # RSS 待处理队列
│   └── rss_dedup.json   # RSS 去重记录
├── logs/
│   ├── pipeline.log     # 日志轮转（10MB / 保留 15 天）
│   └── daily/           # 每日 JSONL 流水线日志
├── requirements.txt
├── .env.example
└── README.md
```

---

## 数据流

```
任何输入（图片/音频/PDF/URL/文本/网页/RSS）
    ↓
extract_text_from_file / process_url → process_content
    ↓
classify_content（三级分类：skip / save_only / deep_rewrite）
    ↓  [仅 deep_rewrite 走以下流程]
classify_topic（话题分类）
    ↓
vector_store.retrieve_similar（ChromaDB 查询相似笔记）
    ↓  [参考笔记 ≤ 1 篇时触发联网]
search_web（Bing 优先 → Tavily 备胎）
    ↓
translate_append（中英混杂自动百度翻译）
    ↓
rewrite_text_with_ai（GLM-4-Flash 中英双语重写）
    ↓
save_result（YAML frontmatter .md → Obsidian）
    ↓
vector_store.add_document（自动入库 ChromaDB）
    ↓
日报：每日 21:00 cronjob → Obsidian
```

---

## 可观测性

| 机制 | 效果 |
|------|------|
| **Healthchecks.io** | 流水线崩了发通知到手机/邮箱 |
| **loguru 日志轮转** | 10MB 自动分割，保留 15 天 |
| **启动配置校验** | 缺 API Key / 路径提前告警 |
| **队列可见性** | 启动时打印待处理/去重条数 |
| **input 自动清理** | 超过 15 天的旧文件自动删除 |

---

## 代码质量

```bash
ruff check src/ --fix    # Lint：零错误 ✅
pytest tests/ -v         # 测试：7/7 通过 ✅
```

---

## 定时任务（Windows）

```powershell
# 08:00 / 14:20 / 20:00
cd G:\ai软件\git\zhipu manage && python src\main.py --batch
```

或运行 `create_task.ps1` 一键创建。

---

## 技术栈

| 层 | 技术 |
|------|------|
| AI 推理 | 智谱 GLM-4-Flash / GLM-4V-Flash（免费） |
| 向量数据库 | ChromaDB + all-MiniLM-L6-v2 |
| 搜索 | Bing 直连（免费无限次）→ Tavily API |
| 翻译 | 百度大模型翻译 API |
| 音频 | faster-whisper tiny（CPU int8） |
| OCR | GLM-4V-Flash → RapidOCR → Tesseract |
| 日志 | loguru（轮转：10MB / 保留 15 天） |
| 监控 | Healthchecks.io |
| 代码质量 | ruff + pytest |

---

## License

MIT
