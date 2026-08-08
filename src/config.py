"""集中化配置 — 所有配置项从一个地方读取"""
import os

# 智谱 AI
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY", "")

# Obsidian 路径
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")
# 输出目录（旧，兼容保留）
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(OBSIDIAN_VAULT_PATH, "ai", "📰每日新闻"))

# ── 2026-08-05 新路径：按来源分流 ──
# 网页抓取 → Obsidian 流水线/AI生成笔记/
WEB_OUTPUT_DIR = os.getenv("WEB_OUTPUT_DIR", os.path.join(OBSIDIAN_VAULT_PATH, "流水线", "AI生成笔记"))
# 本地文件处理 → Obsidian 流水线/本地转写/
LOCAL_OUTPUT_DIR = os.getenv("LOCAL_OUTPUT_DIR", os.path.join(OBSIDIAN_VAULT_PATH, "流水线", "本地转写"))
# 流水线日报 → Obsidian 流水线/流水线日报/
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", os.path.join(OBSIDIAN_VAULT_PATH, "流水线", "流水线日报"))

# OCR
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")  # 留空则自动检测 (PATH/常见安装路径)

# 数据库
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")

# 输入目录
INPUT_DIR = os.getenv("INPUT_DIR", "input")

# 搜索 / 翻译
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── 健康检查 ──
HEALTHCHECK_UUID = os.getenv("HEALTHCHECK_UUID", "")
FANYI_APP_ID = os.getenv("FANYI_APP_ID", os.getenv("BAIDU_APP_ID", ""))
FANYI_SECRET_KEY = os.getenv("FANYI_SECRET_KEY", os.getenv("BAIDU_SECRET_KEY", ""))
