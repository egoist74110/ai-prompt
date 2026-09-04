"""Shared logging for bilibili-auto-transcript."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from runtime_config import state_dir

LOG_DIR = state_dir() / "logs"
LOG_FILE = LOG_DIR / "transcript.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(source, message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] [{source}] {message}\n"
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception:
        pass  # 日志失败不影响主流程


def info(source, message):
    log(source, message, "INFO")


def success(source, message):
    log(source, message, "SUCCESS")


def warn(source, message):
    log(source, message, "WARN")


def error(source, message):
    log(source, message, "ERROR")
