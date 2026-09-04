#!/usr/bin/env python3
"""B站视频转录 SQLite 数据库管理。"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from runtime_config import db_path as configured_db_path, output_dir as configured_output_dir

DB_PATH = configured_db_path()


class TranscriptDB:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path).expanduser() if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bvid TEXT UNIQUE NOT NULL,
                url TEXT,
                title TEXT,
                author TEXT,
                duration TEXT,
                upload_date TEXT,
                transcript_source TEXT,
                transcript_file TEXT,
                transcript_text TEXT,
                summary TEXT,
                status TEXT DEFAULT 'transcribed',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        for col, default in [("url", ""), ("transcript_text", "")]:
            try:
                self.conn.execute(f"ALTER TABLE transcripts ADD COLUMN {col} TEXT DEFAULT '{default}'")
            except sqlite3.OperationalError:
                pass
        self.conn.commit()

    def insert(self, bvid, url="", title="", author="", duration="",
               upload_date="", transcript_source="", transcript_file="",
               transcript_text="", summary="", status="transcribed"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute("""
            INSERT INTO transcripts (bvid, url, title, author, duration, upload_date,
                transcript_source, transcript_file, transcript_text, summary, status,
                created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bvid) DO UPDATE SET
                url=excluded.url, title=excluded.title, author=excluded.author,
                duration=excluded.duration, upload_date=excluded.upload_date,
                transcript_source=excluded.transcript_source,
                transcript_file=excluded.transcript_file,
                transcript_text=excluded.transcript_text,
                summary=excluded.summary, status=excluded.status,
                updated_at=excluded.updated_at
        """, (bvid, url, title, author, duration, upload_date,
              transcript_source, transcript_file, transcript_text, summary, status, now, now))
        self.conn.commit()

    def update_summary(self, bvid, summary):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE transcripts SET summary=?, status='summarized', updated_at=? WHERE bvid=?",
            (summary, now, bvid)
        )
        self.conn.commit()

    def update_summary_by_file(self, transcript_file, summary):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.conn.execute(
            "UPDATE transcripts SET summary=?, status='summarized', updated_at=? WHERE transcript_file=?",
            (summary, now, transcript_file)
        )
        self.conn.commit()

    def get_pending_summaries(self):
        rows = self.conn.execute(
            "SELECT * FROM transcripts WHERE summary IS NULL OR summary = ''"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_bvid(self, bvid):
        row = self.conn.execute("SELECT * FROM transcripts WHERE bvid=?", (bvid,)).fetchone()
        return dict(row) if row else None

    def get_all(self):
        rows = self.conn.execute("SELECT * FROM transcripts ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        with_summary = self.conn.execute(
            "SELECT COUNT(*) FROM transcripts WHERE summary IS NOT NULL AND summary != ''"
        ).fetchone()[0]
        return {
            "total": total,
            "with_summary": with_summary,
            "pending_summary": total - with_summary,
        }

    def render_txt(self, bvid, output_dir=None):
        """从 DB 记录渲染 TXT。output_dir 未指定时使用本机缓存配置。"""
        record = self.get_by_bvid(bvid)
        if not record:
            return None

        base_output = Path(output_dir).expanduser() if output_dir else configured_output_dir()
        upload_date = record.get("upload_date", "")
        target_dir = base_output
        if upload_date and upload_date != "未知时间":
            parts = upload_date.split("-")
            if len(parts) >= 2:
                target_dir = target_dir / parts[0] / parts[1]
        target_dir.mkdir(parents=True, exist_ok=True)

        title = record.get("title", "untitled")
        author = record.get("author", "unknown")
        safe_title = re.sub(r'[\\/:*?"<>|]', '', title)
        safe_title = re.sub(r'[\s\W]+', '-', safe_title).strip('-')[:60] or 'untitled'
        safe_author = re.sub(r'[\\/:*?"<>|]', '', author)
        safe_author = re.sub(r'[\s\W]+', '-', safe_author).strip('-')[:30] or 'unknown'

        video_id = record.get("bvid", "")
        output_file = target_dir / f"{safe_title}_{safe_author}_{upload_date}_{video_id}.txt"
        summary = record.get("summary", "") or ""
        summary_block = summary.strip() if summary else "【AI待处理：请阅读全文后，替换此行，写结构化摘要】"
        transcript_text = record.get("transcript_text", "") or ""
        now = record.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        content = f"""================================================================================
B站视频转录文档
================================================================================

📹 视频标题：{record.get('title', '')}
🔗 B站链接：{record.get('url', '')}
👤 作者：{record.get('author', '')}
📅 发布时间：{record.get('upload_date', '')}
⏱️  视频时长：{record.get('duration', '')}
📝 转录来源：{record.get('transcript_source', '')}
⏰ 转录时间：{now}

================================================================================
第一部分：视频摘要（AI生成）
================================================================================

{summary_block}

================================================================================
第二部分：完整原文
================================================================================

{transcript_text}

================================================================================
文档结束
================================================================================
"""

        output_file.write_text(content, encoding="utf-8")
        self.conn.execute(
            "UPDATE transcripts SET transcript_file=? WHERE bvid=?",
            (str(output_file), bvid)
        )
        self.conn.commit()
        return str(output_file)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
