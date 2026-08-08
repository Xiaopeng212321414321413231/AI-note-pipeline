# 🧠 zhipu manage 流水线 — 代码心智模型（CONTEXT）

> 本文件是 Agent 的项目上下文参考，保存项目的完整代码结构、数据流和关键接口。

## 📦 项目概览

| 指标 | 值 |
|------|------|
| 项目路径 | `<项目本地路径>`（README 中说明） |
| GitHub | `github.com/Xiaopeng212321414321413231/AI-note-pipeline` |
| 版本 | v2.7 |
| 模型 | glm-4-flash（文字推理）、glm-4v-flash（视觉）、all-MiniLM-L6-v2（向量嵌入） |
| 数据库 | ChromaDB（余弦距离，持久化到 `data/chroma_db/`） |
| API 依赖 | ZHIPUAI_API_KEY（智谱）、百度翻译（FANYI_APP_ID/FANYI_SECRET_KEY）、Tavily（备胎搜索） |

## 📡 数据流

任何输入（图片/音频/PDF/URL/文本/网页/RSS）
    ↓
extract_text_from_file / process_url → process_content
    ↓
classify_content（三级分类：skip / save_only / deep_rewrite）
    ↓  [仅 deep_rewrite 走以下流程]
classify_topic（话题分类）
    ↓
vector_store.retrieve_similar（ChromaDB 查询相似笔记 → 风格参考）
    ↓  [向量库笔记 ≤1 篇时触发联网]
search_web（Bing 优先 → Tavily 备胎）
    ↓
translate_append（中英混杂自动百度翻译）
    ↓
rewrite_text_with_ai（GLM-4-Flash 中英双语重写）
    ↓
save_result（生成 YAML frontmatter .md → Obsidian + 写入 daily JSONL 日志）
    ↓
vector_store.add_document（写入后自动入库 ChromaDB）

## 🗺️ 模块地图

### src/main.py — 流水线编排中心（~800 行）
核心函数: get_vector_store(), extract_text_from_file(), process_content(), save_result(), process_file(), _archive_file(), _fetch_html(), _html_to_markdown(), process_url(), process_batch(), process_input_dir(), resume_interrupted(), run_pipeline(), _cleanup_old_input_files(), main()

Entry Points: --batch / --file / --url / gui.py / 每日任务.bat / webhook_bridge.py(:9876)

### 其他核心模块
| 模块 | 行数 | 功能 |
|------|------|------|
| ai_rewrite.py | ~100 | _call_zhipu(), classify_topic(), repair_ocr_text(), rewrite_text_with_ai() |
| config.py | 25 | 集中化配置 |
| notify.py | 35 | Healthchecks.io 心跳 |
| classifier.py | 46 | 内容价值分类 |
| vector_store.py | ~110 | ChromaDB 增量索引，集合 obsidian_notes |
| search.py | 147 | Bing 联网搜索 + 百度翻译 |
| ocr.py | 191 | GLM-4V-Flash → RapidOCR → Tesseract |
| transcriber.py | 40 | faster-whisper tiny CPU int8 |
| checkpoint.py | 208 | JSON 断点续传（6 阶段） |
| gui.py | 479 | Tkinter 界面（700×580） |
| daily_report.py | 60 | Obsidian 日报 |
| healthcheck.py | ~100 | 启动配置校验 |
| rss_importer.py | 182 | RSS 源导入 |
| article_extractor.py | ~150 | 文章四级降级链（缓存→RSS摘要→Jina→HTML） |
| video_extractor.py | ~300 | B站视频五级降级链（字幕缓存→CC→AI字幕→Whisper→元数据） |
| watcher.py | 73 | watchdog 监听模式 |
| webhook_bridge.py | 89 | HTTP API :9876 |
| zh_parser.py | 85 | ZhDocParser PDF/DOCX |
| note_loader.py | 26 | Obsidian 笔记加载 |

## 🛡️ 代码质量
```bash
ruff check src/ --fix    # Lint：零错误 ✅
pytest tests/ -v         # 测试：7/7 通过 ✅
```

## 🛑 已知 Bug
| # | 严重度 | 位置 | 问题 |
|---|--------|------|------|
| 1 | 🟡 | vector_store.py | HF_HUB_OFFLINE=1 硬编码，首次部署无本地缓存会失败 |

## ⚠️ 历史踩坑
- 自修补脚本要立入 .gitignore（_patch*.py / _fix*.py）
- push 前先做隐私审计（见 sensitive-data-audit skill）
- README / .env.example / requirements.txt 三者需同步更新

## ⚙️ 机器配置
| 硬件 | 规格 |
|------|------|
| RAM | 16.00 GB |
| GPU | Intel UHD 770（集成显卡 — 无独显） |
| 磁盘 G: | 139GB 剩余（201GB 总量） |
| Python | 3.11.15（uv pip install） |
