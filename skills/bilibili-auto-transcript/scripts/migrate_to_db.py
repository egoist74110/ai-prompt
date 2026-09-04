#!/usr/bin/env python3
"""将旧 TXT 转录文件导入当前本机配置的 SQLite 数据库。"""
from __future__ import annotations

import argparse
import os
import re

from runtime_config import output_dir
from transcript_db import TranscriptDB

DEFAULT_SOURCE_DIR = output_dir()


def parse_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    data = {}
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("📹 视频标题："):
            data["title"] = line.replace("📹 视频标题：", "").strip()
        elif line.startswith("🔗 B站链接："):
            data["url"] = line.replace("🔗 B站链接：", "").strip()
        elif line.startswith("👤 作者："):
            data["author"] = line.replace("👤 作者：", "").strip()
        elif line.startswith("📅 发布时间："):
            data["upload_date"] = line.replace("📅 发布时间：", "").strip()
        elif line.startswith("⏱️  视频时长："):
            data["duration"] = line.replace("⏱️  视频时长：", "").strip()
        elif line.startswith("📝 转录来源："):
            data["transcript_source"] = line.replace("📝 转录来源：", "").strip()
        elif line.startswith("⏰ 转录时间："):
            data["transcribe_date"] = line.replace("⏰ 转录时间：", "").strip()

    bvid = None
    if data.get("url"):
        match = re.search(r"BV[a-zA-Z0-9]+", data["url"])
        if match:
            bvid = match.group(0)
    if not bvid:
        match = re.search(r"BV[a-zA-Z0-9]+", os.path.basename(path))
        if match:
            bvid = match.group(0)
    if not bvid:
        return None
    data["bvid"] = bvid

    summary_header = "第一部分：视频摘要"
    transcript_header = "第二部分：完整原文"
    summary = ""
    in_summary = False
    in_transcript = False
    transcript_lines = []
    for line in lines:
        if summary_header in line:
            in_summary = True
            continue
        if transcript_header in line:
            in_summary = False
            in_transcript = True
            continue
        if "文档结束" in line:
            in_transcript = False
            continue
        if in_summary:
            stripped = line.strip()
            if stripped and not re.match(r"^=+$", stripped) and "【AI待处理" not in stripped and "待处理" not in stripped:
                summary += stripped + "\n"
        if in_transcript:
            transcript_lines.append(line)

    data["summary"] = summary.strip()
    data["transcript_text"] = "\n".join(transcript_lines).strip()
    data.setdefault("title", os.path.basename(path))
    data.setdefault("author", "未知")
    data.setdefault("duration", "未知")
    data.setdefault("upload_date", "未知")
    if data.get("transcribe_date"):
        data["created_at"] = data.pop("transcribe_date")
    return data


def migrate(source_dir, dry_run=False):
    source_dir = os.path.expanduser(str(source_dir))
    if not os.path.isdir(source_dir):
        print(f"错误: 目录不存在 {source_dir}")
        return 2

    txt_files = []
    for root, _dirs, files in os.walk(source_dir):
        for filename in files:
            if filename.endswith(".txt"):
                txt_files.append(os.path.join(root, filename))

    print(f"找到 {len(txt_files)} 个转录文件")
    skipped_no_bvid = skipped_exists = imported = has_summary = parsed_source = 0

    with TranscriptDB() as db:
        for path in txt_files:
            data = parse_txt(path)
            if not data:
                skipped_no_bvid += 1
                continue
            bvid = data["bvid"]
            if db.get_by_bvid(bvid):
                skipped_exists += 1
                continue
            if not dry_run:
                db.conn.execute(
                    """INSERT INTO transcripts
                    (bvid, url, title, author, duration, upload_date,
                     transcript_source, transcript_file, transcript_text, summary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        bvid, data.get("url", ""), data.get("title", ""), data.get("author", ""),
                        data.get("duration", ""), data.get("upload_date", ""),
                        data.get("transcript_source", ""), path,
                        data.get("transcript_text", ""), data.get("summary", ""),
                        data.get("created_at", ""),
                    ),
                )
                db.conn.commit()
            imported += 1
            has_summary += int(bool(data.get("summary")))
            parsed_source += int(bool(data.get("transcript_source")))
            print(f"  {'[DRY] ' if dry_run else ''}✓ {data['title'][:40]} ({bvid})")

    print()
    print("=" * 50)
    if dry_run:
        print("[DRY RUN - 未实际写入]")
    print(f"总文件数:        {len(txt_files)}")
    print(f"成功导入:        {imported}")
    print(f"已有记录跳过:    {skipped_exists}")
    print(f"无法解析BVID:    {skipped_no_bvid}")
    print(f"已有摘要:        {has_summary}")
    print(f"缺少摘要:        {imported - has_summary}")
    print(f"已有转录来源:    {parsed_source}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="将旧转录TXT导入当前配置的 SQLite 数据库")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不写入")
    parser.add_argument("--stats", action="store_true", help="显示DB统计")
    parser.add_argument("--source-dir", "--knowledge-dir", dest="source_dir", default=str(DEFAULT_SOURCE_DIR), help="旧 TXT 来源目录；默认使用本机缓存 output_dir")
    args = parser.parse_args()

    if args.stats:
        with TranscriptDB() as db:
            stats = db.stats()
            print("📊 数据库统计:")
            print(f"   总记录: {stats['total']}")
            print(f"   已有摘要: {stats['with_summary']}")
            print(f"   待补摘要: {stats['pending_summary']}")
        return 0

    print(f"来源目录: {args.source_dir}")
    print(f"模式: {'试运行 (不写入)' if args.dry_run else '正式导入'}")
    print()
    return migrate(args.source_dir, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
