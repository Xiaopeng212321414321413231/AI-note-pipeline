"""集中化配置 — 所有配置项从一个地方读取"""
import os

# 智谱 AI
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY", "")

# Obsidian 路径
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "")
OUTPUT_DIR = os.path.join(OBSIDIAN_VAULT_PATH, "AI生成笔记")

# OCR
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "C:/Program Files/Tesseract-OCR/tesseract.exe")

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
