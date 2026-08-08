# -*- coding: utf-8 -*-
"""B站视频内容提取降级链 — 参考 Web Clipper 渐进式架构

五级降级链：
  Level 0: 字幕缓存命中（已处理过的视频直接返回）
  Level 2: B站 API 获取 CC 字幕
  Level 3: B站 API 获取 AI 生成字幕
  Level 4: 下载音频 + faster-whisper 转写
  Level 5: 纯元数据归档（兜底）
"""

import hashlib, json, os, re
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "subtitle_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

from dotenv import load_dotenv; load_dotenv()
_BILI_SD = os.environ.get("BILIBILI_SESSDATA", "")
_BILI_BJ = os.environ.get("BILIBILI_BILI_JCT", "")
_BILI_DID = os.environ.get("BILIBILI_DEDE_USER_ID", "")

_BV_PATTERN = re.compile(r"(?:bv\s*)?(BV[1-9A-HJ-NP-Za-km-z]{10})", re.IGNORECASE)
_URL_PATTERN = re.compile(r"https?://(?:www\.)?bilibili\.com/video/(BV[1-9A-HJ-NP-Za-km-z]{10})", re.IGNORECASE)

def extract_bvid(text: str) -> Optional[str]:
    """从URL或文本中提取BV号"""
    m = _URL_PATTERN.search(text)
    if m: return m.group(1)
    m = _BV_PATTERN.search(text)
    return m.group(1) if m else None

def _cache_get(bvid: str) -> Optional[dict]:
    path = CACHE_DIR / f"{bvid}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def _cache_set(bvid: str, data: dict):
    path = CACHE_DIR / f"{bvid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _make_credential():
    from bilibili_api import Credential
    if _BILI_SD and _BILI_BJ:
        return Credential(sessdata=_BILI_SD, bili_jct=_BILI_BJ, dedeuserid=_BILI_DID)
    return Credential()

def _get_video_info(bvid: str) -> dict:
    """获取视频元信息（~200ms）"""
    from bilibili_api import video, sync
    v = video.Video(bvid=bvid, credential=_make_credential())
    info = sync(v.get_info())
    return {
        "bvid": bvid,
        "title": info.get("title", "未知标题"),
        "owner": info.get("owner", {}).get("name", "未知"),
        "pubdate": info.get("pubdate", 0),
        "desc": (info.get("desc") or "").strip(),
        "cover": info.get("pic", ""),
        "duration": info.get("duration", 0),
        "tags": [t.get("tag_name","") if isinstance(t,dict) else str(t) for t in (info.get("tag") or [])],
    }

def _fetch_subtitle_text(subtitle_list: list) -> tuple:
    """从字幕列表下载第一条可用字幕文本"""
    import requests as req
    zh_sub = None
    fallback = None
    for sub in subtitle_list:
        if not isinstance(sub, dict): continue
        lang = sub.get("lan", "").lower()
        if "zh" in lang or "ch" in lang or "cn" in lang:
            zh_sub = sub; break
        if fallback is None: fallback = sub
    target = zh_sub or fallback
    if target is None: return "", "unknown"
    sub_url = target.get("subtitle_url", "")
    lang = target.get("lan_doc", target.get("lan", "unknown"))
    if not sub_url: return "", lang
    if sub_url.startswith("//"): sub_url = "https:" + sub_url
    elif not sub_url.startswith("http"): sub_url = "https:" + sub_url
    try:
        resp = req.get(sub_url, timeout=15); resp.raise_for_status()
        body = resp.json().get("body", [])
        if isinstance(body, list):
            return "\n".join(item.get("content","") for item in body if isinstance(item,dict)), lang
    except Exception: pass
    return "", lang


def _get_api_subtitles(bvid: str) -> dict:
    """Level 2+3: 先 CC 后 AI 字幕"""
    from bilibili_api import video, sync
    v = video.Video(bvid=bvid, credential=_make_credential())
    info = sync(v.get_info())
    # Level 2: CC 字幕
    sub_list = info.get("subtitle", {}).get("list", [])
    if sub_list:
        text, lang = _fetch_subtitle_text(sub_list)
        if text:
            return {"available": True, "text": text, "source": "CC字幕", "lang": lang}
    # Level 3: AI 字幕
    try:
        player = sync(v.get_player_info(cid=0))
        ai_sub = player.get("subtitle",{}).get("subtitles",[])
        if ai_sub:
            text, lang = _fetch_subtitle_text(ai_sub)
            if text:
                return {"available": True, "text": text, "source": "AI字幕", "lang": lang}
    except Exception: pass
    return {"available": False, "error": "无可用字幕"}


def _download_audio(bvid: str, cid: int = 0) -> Optional[str]:
    """下载B站DASH音频流"""
    import tempfile
    import requests as req
    from bilibili_api import video, sync
    v = video.Video(bvid=bvid, credential=_make_credential())
    if cid == 0:
        info = sync(v.get_info())
        pages = info.get("pages", [])
        if pages: cid = pages[0]["cid"]
        else: return None
    url_data = sync(v.get_download_url(cid=cid))
    audios = url_data.get("dash",{}).get("audio",[])
    if not audios: return None
    best = max(audios, key=lambda x: x.get("id",0) or 0)
    audio_url = best.get("baseUrl","")
    if not audio_url: return None
    ext = best.get("mimeType","audio/mp4").split("/")[-1].split(";")[0]
    out_dir = os.path.join(tempfile.gettempdir(), "bilibili_audio")
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, f"{bvid}_{cid}.{ext}")
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return filepath
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://www.bilibili.com/"}
    resp = req.get(audio_url, headers=headers, stream=True, timeout=120)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return filepath


def _transcribe_with_whisper(audio_path: str) -> str:
    from transcriber import transcribe_audio
    return transcribe_audio(audio_path)


def _metadata_text(info: dict) -> str:
    lines = [
        "# " + info["title"],
        "UP主：" + info["owner"],
        "时长：" + str(info["duration"]) + "秒",
        "简介：" + info["desc"],
        "标签：" + "、".join(info["tags"][:10]),
    ]
    return "\n".join(lines)


def extract_video(url_or_bvid: str, skip_cache: bool = False, force_whisper: bool = False) -> dict:
    """提取B站视频文本内容 — 五级降级链

    Args:
        url_or_bvid: B站视频URL或BV号
        skip_cache: 强制跳过缓存
        force_whisper: 强制走Whisper（即使有字幕）

    Returns:
        dict with keys: available, text, source, level, cached, video_info, ...
    """
    bvid = extract_bvid(url_or_bvid)
    if not bvid:
        return {"available": False, "text": "", "source": "无效BV号", "error": "无法提取BV号: " + url_or_bvid}

    # Level 0: 缓存命中
    if not skip_cache:
        cached = _cache_get(bvid)
        if cached and cached.get("available"):
            return {**cached, "cached": True}

    # 先拿元数据（快，~200ms）
    try:
        info = _get_video_info(bvid)
    except Exception as e:
        return {"available": False, "text": "", "source": "API失败", "error": str(e), "cached": False}

    result = {"bvid": bvid, "video_info": info, "cached": False}

    if not force_whisper:
        # Level 2+3: API 字幕
        sub = _get_api_subtitles(bvid)
        if sub.get("available"):
            result["available"] = True
            result["text"] = sub["text"]
            result["source"] = sub["source"]
            result["lang"] = sub.get("lang", "zh")
            result["level"] = "2" if sub["source"] == "CC字幕" else "3"
            _cache_set(bvid, result)
            return result

    # Level 4: 音频下载 + Whisper
    print(f"  [B站] {bvid} 无API字幕，下载音频转写...", flush=True)
    try:
        audio_path = _download_audio(bvid)
        if audio_path and os.path.getsize(audio_path) > 0:
            text = _transcribe_with_whisper(audio_path)
            if text and len(text) > 50:
                result["available"] = True
                result["text"] = text
                result["source"] = "音频转写 (Whisper tiny)"
                result["level"] = "4"
                _cache_set(bvid, result)
                return result
    except Exception as e:
        print(f"  [B站] Whisper 失败: {e}", flush=True)

    # Level 5: 纯元数据归档（兜底）
    result["available"] = True
    result["text"] = _metadata_text(info)
    result["source"] = "元数据归档（无字幕）"
    result["level"] = "5"
    result["error"] = "字幕获取失败，仅保留元数据"
    _cache_set(bvid, result)
    return result

def extract_local_video(file_path: str) -> str:
    """本地视频：ffmpeg 提取音频 → faster-whisper 转写（与B站 Level 4 同款链路）

    降级链（本地视频无 B站 API 字幕）：
      Level 4a: ffmpeg 提取音频轨 → faster-whisper 转写
      兜底:     返回空字符串（由上层归档或跳过）
    """
    import subprocess, tempfile
    if not os.path.isfile(file_path):
        return ""
    tmp_dir = tempfile.mkdtemp(prefix="video_audio_")
    audio_path = os.path.join(tmp_dir, "audio.wav")
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", file_path,
             "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
             audio_path],
            capture_output=True, timeout=600,
        )
        if r.returncode != 0 or not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            print(f"   [视频] ffmpeg 提取音频失败: {file_path}")
            return ""
        print(f"   [视频] 音频提取完成，Whisper 转写中...")
        from transcriber import transcribe_audio
        return transcribe_audio(audio_path)
    except Exception as e:
        print(f"   [视频] 提取失败: {e}")
        return ""
    finally:
        try:
            for f in os.listdir(tmp_dir):
                os.remove(os.path.join(tmp_dir, f))
            os.rmdir(tmp_dir)
        except Exception:
            pass


