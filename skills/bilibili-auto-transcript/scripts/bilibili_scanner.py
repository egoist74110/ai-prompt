#!/usr/bin/env python3
"""B站收藏夹快速扫描：只扫描，不转录；输出 JSON。"""
from __future__ import annotations

import json
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(SKILL_DIR, ".env"))
except Exception:
    pass

import requests
from runtime_config import favorite_media_id, state_dir

FAV_MEDIA_ID = favorite_media_id()
STATE_DIR = state_dir()
PROCESSED_FILE = STATE_DIR / "processed_videos.txt"
API_BASE = "https://api.bilibili.com/x/v3/fav/resource/list"


def fetch_all_medias():
    """分页获取收藏夹中的所有视频。"""
    all_medias = []
    pn = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    while True:
        url = f"{API_BASE}?media_id={FAV_MEDIA_ID}&ps=20&pn={pn}"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            print(json.dumps({"error": f"网络请求失败 - {exc}"}, ensure_ascii=False))
            return None
        except ValueError as exc:
            print(json.dumps({"error": f"API响应解析失败 - {exc}"}, ensure_ascii=False))
            return None

        if data.get("code") != 0:
            print(json.dumps({"error": f"B站API返回错误 - {data.get('message', '未知')}"}, ensure_ascii=False))
            return None

        medias = data.get("data", {}).get("medias", [])
        all_medias.extend(medias)
        if not data.get("data", {}).get("has_more"):
            break
        pn += 1

    return all_medias


def main():
    if not FAV_MEDIA_ID:
        print(json.dumps({
            "error": (
                "未配置收藏夹ID。可设置 FAV_MEDIA_ID，或把非敏感 ID 缓存到 "
                ".local/runtime.json 的 skills.bilibili-auto-transcript.favorite_media_id"
            )
        }, ensure_ascii=False))
        return 1

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    medias = fetch_all_medias()
    if medias is None:
        return 1

    processed = set()
    if PROCESSED_FILE.exists():
        with PROCESSED_FILE.open(encoding="utf-8") as fh:
            processed = {line.strip() for line in fh if line.strip()}

    new_videos = []
    for media in medias:
        bvid = media.get("bvid", "") or media.get("bv_id", "")
        if not bvid or bvid in processed:
            continue
        new_videos.append({
            "bvid": bvid,
            "title": media.get("title", ""),
            "duration": media.get("duration", 0),
            "upper": media.get("upper", {}).get("name", ""),
            "pubtime": media.get("pubtime", 0),
        })

    output = {
        "collection_total": len(medias),
        "processed": len(processed),
        "new_videos": new_videos,
        "status": f"new_videos:{len(new_videos)}" if new_videos else "all_caught_up",
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
