# -*- coding: utf-8 -*-
"""
断点续传管理器 — 记录每个文件的处理阶段，中断后可恢复
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkpoint.json")

# 处理阶段定义（数字越大越靠后）
STAGES = {
    "pending": 0,     # 刚发现，未处理
    "extracted": 1,   # OCR/转写完成
    "classified": 2,  # 分类完成
    "enriched": 3,    # 搜索+向量检索完成
    "rewritten": 4,   # AI重写完成
    "done": 5,        # 已归档完成
}

STAGE_NAMES = {
    0: "待处理",
    1: "文字提取",
    2: "内容分类",
    3: "检索增强",
    4: "AI重写",
    5: "归档完成",
}

def _ensure_dir():
    """确保 checkpoint 目录存在"""
    Path(CHECKPOINT_FILE).parent.mkdir(parents=True, exist_ok=True)

def _now():
    return datetime.now().isoformat(timespec="seconds")

def load():
    """加载 checkpoint"""
    _ensure_dir()
    if not os.path.exists(CHECKPOINT_FILE):
        return {"version": 2, "files": {}, "completed_count": 0, "last_run": None}
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 兼容旧格式升级
        if "files" not in data:
            data["files"] = {}
        return data
    except (json.JSONDecodeError, IOError):
        return {"version": 2, "files": {}, "completed_count": 0, "last_run": None}

def save(data):
    """保存 checkpoint"""
    _ensure_dir()
    data["last_run"] = _now()
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_file(filepath):
    """初始化一个新文件的 checkpoint 条目"""
    data = load()
    relpath = os.path.relpath(filepath) if os.path.isabs(filepath) else filepath
    if relpath not in data["files"]:
        data["files"][relpath] = {
            "stage": "pending",
            "stage_num": 0,
            "mtime": _now(),
            "error": None,
            "retries": 0,
        }
    save(data)
    return relpath

def set_stage(filepath, stage, error=None):
    """设置文件处理到某个阶段

    Args:
        filepath: 文件路径（相对或绝对）
        stage: 阶段名 (pending/extracted/classified/enriched/rewritten/done)
        error: 可选的错误信息
    """
    if stage not in STAGES:
        raise ValueError(f"未知阶段: {stage}，可选: {list(STAGES.keys())}")

    data = load()
    relpath = os.path.relpath(filepath) if os.path.isabs(filepath) else filepath

    if relpath not in data["files"]:
        data["files"][relpath] = {}

    data["files"][relpath].update({
        "stage": stage,
        "stage_num": STAGES[stage],
        "mtime": _now(),
        "error": error,
        "retries": data["files"][relpath].get("retries", 0) + 1 if error else 0,
    })

    save(data)
    return relpath

def get_file_info(filepath):
    """获取某个文件的 checkpoint 信息"""
    data = load()
    relpath = os.path.relpath(filepath) if os.path.isabs(filepath) else filepath
    return data["files"].get(relpath, {"stage": "pending", "stage_num": 0})

def get_pending():
    """获取所有未完成的文件（stage < done）"""
    data = load()
    pending = {}
    for fpath, info in data["files"].items():
        if info.get("stage_num", 0) < STAGES["done"]:
            pending[fpath] = info
    return pending

def get_interrupted():
    """获取中断的文件（有stage但没到done，适合恢复）"""
    pending = get_pending()
    # 过滤掉纯粹"pending"状态的（可能是之前正常处理过的未归档）
    interrupted = {
        k: v for k, v in pending.items()
        if v.get("stage_num", 0) > 0
    }
    return interrupted

def get_errors():
    """获取有错误的文件"""
    data = load()
    return {
        k: v for k, v in data["files"].items()
        if v.get("error")
    }

def remove_file(filepath):
    """文件处理完成后清理 checkpoint 条目"""
    data = load()
    relpath = os.path.relpath(filepath) if os.path.isabs(filepath) else filepath
    if relpath in data["files"]:
        data["completed_count"] = data.get("completed_count", 0) + 1
        del data["files"][relpath]
    save(data)

def clear_all():
    """清空所有 checkpoint（重新开始）"""
    save({"version": 2, "files": {}, "completed_count": 0, "last_run": _now()})

def need_process(filepath, stage):
    """检查某个文件是否需要执行某阶段（跳过已完成的）

    Args:
        filepath: 文件路径
        stage: 要检查的阶段名

    Returns:
        True = 需要处理（未完成），False = 已跳过
    """
    info = get_file_info(filepath)
    current = info.get("stage_num", 0)
    return current < STAGES[stage]

def summary():
    """返回可读的中文摘要"""
    data = load()
    files = data.get("files", {})
    total = len(files)
    stages_count = {}
    errors = 0
    for info in files.values():
        s = info.get("stage", "pending")
        stages_count[s] = stages_count.get(s, 0) + 1
        if info.get("error"):
            errors += 1

    lines = [
        f"📋 Checkpoint 摘要",
        f"  总记录: {total} 个文件",
        f"  已完成(累计): {data.get('completed_count', 0)} 个",
    ]
    for s, n in sorted(stages_count.items(), key=lambda x: STAGES.get(x[0], 0)):
        lines.append(f"    {STAGE_NAMES.get(STAGES.get(s, 0), s)}: {n} 个")
    if errors:
        lines.append(f"  ⚠️ 有错误: {errors} 个文件")
    lines.append(f"  最后运行: {data.get('last_run', '从未')}")
    return "\n".join(lines)

# ---------- 简化的文件流处理装饰器 ----------

class StageContext:
    """用于 with 语句的阶段性上下文，自动 checkpoint 写入"""

    def __init__(self, filepath, stage):
        self.filepath = filepath
        self.stage = stage
        self.relpath = None

    def __enter__(self):
        self.relpath = init_file(self.filepath)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            set_stage(self.filepath, self.stage)
        else:
            set_stage(self.filepath, self.stage, error=str(exc_val))
        return False  # 不吞异常