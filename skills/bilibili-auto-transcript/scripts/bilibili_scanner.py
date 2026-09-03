#!/usr/bin/env python3
"""
B站收藏夹快速扫描脚本 - 只扫描，不转录
输出新视频列表供 Hermes Agent 处理（生成摘要、通知等）
"""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FAV_MEDIA_ID = ""                   # ⬅️ 必填！换成你自己的B站收藏夹ID
                                     # 从收藏夹URL ?fid= 后面的数字获取
STATE_DIR = os.path.expanduser("~/.openclaw/workspace/.auto-transcript-state")
PROCESSED_FILE = os.path.join(STATE_DIR, "processed_videos.txt")
API_URL = f"https://api.bilibili.com/x/v3/fav/resource/list?media_id={FAV_MEDIA_ID}&ps=20&pn=1"


def main():
    if not FAV_MEDIA_ID:
        print("ERROR: 请先设置收藏夹ID！编辑 scripts/bilibili_scanner.py，将 FAV_MEDIA_ID 改为你的收藏夹ID")
        return 1

    os.makedirs(STATE_DIR, exist_ok=True)

    # 获取收藏夹列表
    try:
        req = Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"ERROR: 无法读取B站收藏夹API - {exc}")
        return 1

    if data.get("code") != 0:
        print(f"ERROR: B站API返回错误 - {data.get('message', '未知')}")
        return 1

    medias = data["data"]["medias"]
    print(f"COLLECTION_TOTAL:{len(medias)}")

    # 加载已处理记录
    processed = set()
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            processed = set(line.strip() for line in f if line.strip())
    print(f"PROCESSED:{len(processed)}")

    # 找出新视频
    new_videos = []
    for m in medias:
        avid = str(m["id"])
        if avid not in processed:
            new_videos.append({
                "avid": avid,
                "bvid": m.get("bvid", "") or m.get("bv_id", ""),
                "title": m["title"],
                "duration": m["duration"],
                "upper": m["upper"]["name"],
                "pubtime": m.get("pubtime", 0),
            })

    if not new_videos:
        print("ALL_CAUGHT_UP")
        return 0

    print(f"NEW_VIDEOS:{len(new_videos)}")
    for v in new_videos:
        mins = v["duration"] // 60
        secs = v["duration"] % 60
        print(f"  - BVID:{v['bvid']}")
        print(f"    TITLE:{v['title']}")
        print(f"    DURATION:{mins}分{secs}秒")
        print(f"    UPPER:{v['upper']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
