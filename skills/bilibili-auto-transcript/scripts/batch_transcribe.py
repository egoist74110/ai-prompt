#!/usr/bin/env python3
"""批量转录 B站收藏夹中的所有新视频。"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv
    load_dotenv(SKILL_DIR / ".env")
except Exception:
    pass

import requests as _requests
from logger import info, success, error as log_error
from runtime_config import favorite_media_id, output_dir, state_dir
from transcript_db import TranscriptDB

SCANNER = SKILL_DIR / "scripts" / "bilibili_scanner.py"
RUN_TRANSCRIPT = SKILL_DIR / "scripts" / "run_transcript.py"
FAV_MEDIA_ID = favorite_media_id()
STATE_DIR = state_dir()
PROCESSED_FILE = STATE_DIR / "processed_videos.txt"
REPORT_FILE = STATE_DIR / "transcript_report.csv"
OUTPUT_DIR = output_dir()
MAX_RETRIES = 2
BATCH_DELAY = 3


def fetch_latest_titles(media_id: str) -> dict:
    if not media_id:
        return {}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"}
    titles = {}
    page = 1
    while True:
        url = f"https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&ps=20&pn={page}"
        try:
            resp = _requests.get(url, headers=headers, timeout=15)
            data = resp.json()
            if data.get("code") != 0:
                break
            medias = data.get("data", {}).get("medias", [])
            if not medias:
                break
            for item in medias:
                bvid = item.get("bvid", "")
                title = item.get("title", "")
                if bvid and title:
                    titles[bvid] = title
            if data.get("data", {}).get("has_more") is False:
                break
            page += 1
        except Exception:
            break
    return titles


def verify_and_fix_titles():
    latest = fetch_latest_titles(FAV_MEDIA_ID)
    if not latest:
        print("⚠️ 无法获取收藏夹最新标题，跳过校验")
        return 0

    fixed = 0
    try:
        with TranscriptDB() as db:
            rows = db.conn.execute("SELECT bvid, title FROM transcripts").fetchall()
            for row in rows:
                bvid = row["bvid"]
                db_title = row["title"]
                api_title = latest.get(bvid)
                if api_title and api_title != db_title:
                    db.conn.execute("UPDATE transcripts SET title = ? WHERE bvid = ?", (api_title, bvid))
                    db.conn.commit()
                    print(f"   🔧 标题修正: {db_title} → {api_title}")
                    fixed += 1
    except Exception as exc:
        print(f"⚠️ 标题校验出错: {exc}")
    return fixed


def load_processed():
    if not PROCESSED_FILE.exists():
        return set()
    with PROCESSED_FILE.open(encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}


def save_processed(bvid):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PROCESSED_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{bvid}\n")


def get_content_hash(filepath):
    path = Path(filepath)
    if not path.exists():
        return ""
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            h.update(fh.read(65536))
        return h.hexdigest()[:16]
    except Exception:
        return ""


def scan_videos():
    result = subprocess.run(
        [sys.executable, str(SCANNER)], capture_output=True, text=True, cwd=str(SKILL_DIR)
    )
    if result.returncode != 0:
        print(f"Scanner error: {result.stderr or result.stdout}")
        return []
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        print(f"Scanner 输出解析失败: {result.stdout[:200]}")
        return []
    if data.get("error"):
        print(f"Scanner 错误: {data['error']}")
        return []
    print(f"📊 收藏夹共 {data.get('collection_total', 0)} 个，已处理 {data.get('processed', 0)} 个")
    return data.get("new_videos", [])


def _extract_saved_file(stdout: str) -> str | None:
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate.endswith(".txt"):
            continue
        # 新旧引擎都会额外打印一行纯路径；若只有“文件已保存:”提示则截取后半段。
        if "文件已保存:" in candidate:
            candidate = candidate.split("文件已保存:", 1)[1].strip()
        if candidate:
            return candidate
    return None


def transcribe_video(bvid, attempt=1, max_retries=1):
    url = f"https://www.bilibili.com/video/{bvid}/"
    print(f"\n{'='*70}")
    print(f"🎬 开始转录: {bvid} (尝试 {attempt}/{max_retries})")
    print(f"{'='*70}")

    result = subprocess.run(
        [sys.executable, str(RUN_TRANSCRIPT), url, "--output", str(OUTPUT_DIR)],
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
        timeout=7200,
    )
    if result.stdout:
        print(result.stdout[-2000:])
    if result.stderr:
        preview = result.stderr.strip()[-500:]
        if preview:
            print(f"STDERR: {preview}")

    used_stt = "Whisper" in result.stdout or "语音转文字" in result.stdout
    if result.returncode == 0 and "✅ 转录完成" in result.stdout:
        saved_file = _extract_saved_file(result.stdout)
        transcript_source = "unknown"
        try:
            with TranscriptDB() as db:
                record = db.get_by_bvid(bvid)
                if record:
                    transcript_source = record.get("transcript_source", "unknown")
        except Exception:
            pass
        return True, saved_file or "unknown", transcript_source, used_stt

    error_msg = result.stdout[-300:] if result.stdout else (result.stderr[-300:] if result.stderr else "无输出")
    return False, error_msg, None, used_stt


def main():
    print("=" * 70)
    print("📼 B站收藏夹批量转录")
    print("=" * 70)
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"🧠 状态目录: {STATE_DIR}")
    info("batch_transcribe", "开始批量转录任务")

    videos = scan_videos()
    if not videos:
        print("没有新视频需要转录")
        info("batch_transcribe", "没有新视频，结束")
        return 0

    processed = load_processed()
    pending = [v for v in videos if v["bvid"] not in processed]
    total = len(videos)
    remaining = len(pending)
    print(f"\n📊 总计 {total} 个视频")
    print(f"✅ 已处理 {total - remaining} 个")
    print(f"⏳ 待处理 {remaining} 个")
    if remaining == 0:
        return 0

    print("📝 AI摘要生成: 已启用（转录时自动生成）" if os.environ.get("OPENAI_API_KEY") else
          "📝 AI摘要生成: 未启用（设置 OPENAI_API_KEY 可开启）")

    start_time = time.time()
    success_count = 0
    fail_count = 0
    report_rows = []

    for i, video in enumerate(pending, 1):
        bvid = video["bvid"]
        current_remaining = remaining - i + 1
        elapsed = time.time() - start_time if i > 1 else 0
        if elapsed > 0 and i > 1:
            avg_time = elapsed / (i - 1)
            eta = avg_time * current_remaining
            print(f"\n⏱️  已用: {int(elapsed//60)}分{int(elapsed%60)}秒 | 预计剩余: {int(eta//60)}分{int(eta%60)}秒")

        print(f"\n📌 [{total - remaining + i}/{total}] {video['title']}")
        print(f"   ⏱️  {video['duration']} | 👤 {video['upper']}")

        ok = False
        output_file = None
        transcript_source = None
        used_stt = False
        max_attempts = MAX_RETRIES + 1
        for attempt in range(1, max_attempts + 1):
            ok, output_path, transcript_source, used_stt = transcribe_video(bvid, attempt, max_attempts)
            if ok:
                output_file = output_path
                break
            if used_stt:
                print("   ⏭️ Whisper 失败，跳过重试（模型加载耗时）")
                break
            if attempt <= MAX_RETRIES:
                wait = BATCH_DELAY * attempt
                print(f"   ⏳ 等待 {wait} 秒后重试...")
                time.sleep(wait)

        if ok:
            content_hash = get_content_hash(output_file) if output_file and output_file != "unknown" else ""
            report_rows.append({
                "bvid": bvid,
                "title": video.get("title", ""),
                "author": video.get("upper", ""),
                "duration": video.get("duration", ""),
                "source": transcript_source or "unknown",
                "output_file": output_file or "",
                "content_hash": content_hash,
                "status": "success",
                "attempts": attempt,
            })
            success_count += 1
            save_processed(bvid)
            print(f"   ✅ [{success_count}/{remaining}] 成功! 来源: {transcript_source}")
            success("batch_transcribe", f"转录成功: {bvid} ({transcript_source})")
        else:
            report_rows.append({
                "bvid": bvid,
                "title": video.get("title", ""),
                "author": video.get("upper", ""),
                "duration": video.get("duration", ""),
                "source": "失败",
                "output_file": "",
                "content_hash": "",
                "status": f"failed_after_{attempt}_attempts",
                "attempts": attempt,
            })
            fail_count += 1
            print(f"   ❌ [{fail_count}] 失败 (尝试{attempt}次后放弃)")
            log_error("batch_transcribe", f"转录失败: {bvid} (尝试{attempt}次)")

        if i < len(pending):
            time.sleep(BATCH_DELAY)

    total_time = time.time() - start_time
    print(f"\n{'=' * 70}")
    print("📊 批量转录完成")
    print(f"   总计: {remaining} 个 | 成功: {success_count} | 失败: {fail_count}")
    print(f"   耗时: {int(total_time//60)}分{int(total_time%60)}秒")
    info("batch_transcribe", f"批量转录完成: 成功 {success_count}, 失败 {fail_count}")

    if report_rows:
        with REPORT_FILE.open("w", newline="", encoding="utf-8") as fh:
            fieldnames = ["bvid", "title", "author", "duration", "source", "output_file",
                          "content_hash", "status", "attempts"]
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)
        print(f"   📄 报告已保存: {REPORT_FILE}")

    print("\n🔍 校验标题一致性...")
    fixed_titles = verify_and_fix_titles()
    print(f"   🔧 修正了 {fixed_titles} 条标题" if fixed_titles else "   ✅ 所有标题一致或无需修正")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
