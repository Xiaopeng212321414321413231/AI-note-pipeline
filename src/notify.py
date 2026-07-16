"""运行状态通知 — 轻量级 Healthchecks 集成"""
import os
import urllib.request
import urllib.error
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

_raw = os.getenv("HEALTHCHECK_UUID", "")
# 支持填完整 URL（https://hc-ping.com/UUID）或纯 UUID
if "/" in _raw:
    _raw = _raw.rstrip("/").split("/")[-1]
HEALTHCHECK_UUID = _raw


def ping(state: str = "", msg: str = "") -> bool:
    """向 Healthchecks.io 发送心跳

    Args:
        state: ""（完成）、"start"（开始）、"fail"（失败）
        msg:  附带的消息文本（URL 编码后追加）
    Returns:
        True 表示发送成功，False 表示未配置或网络失败
    """
    if not HEALTHCHECK_UUID:
        return False

    suffix = f"/{state}" if state else ""
    url = f"https://hc-ping.com/{HEALTHCHECK_UUID}{suffix}"

    if msg:
        try:
            url += f"?msg={urllib.parse.quote(msg[:200])}"
        except Exception:
            pass  # 消息参数失败也不阻塞主流程

    try:
        urllib.request.urlopen(url, timeout=10)
        logger.debug("Healthcheck ping {} → OK", state or "完成")
        return True
    except Exception as e:
        logger.warning("Healthcheck 发送失败: {}", e)
        return False
