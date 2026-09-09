#!/usr/bin/env python3
"""Cross-platform filesystem helpers for symlink/junction based runtime deployment."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def norm_path(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def is_junction(path: Path) -> bool:
    fn = getattr(path, "is_junction", None)
    if fn is not None:
        try:
            return bool(fn())
        except OSError:
            return False
    if os.name != "nt":
        return False
    try:
        attrs = path.lstat().st_file_attributes
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(attrs & reparse) and path.is_dir() and not path.is_symlink()
    except (AttributeError, OSError):
        return False


def is_linkish(path: Path) -> bool:
    return path.is_symlink() or is_junction(path)


def link_target(path: Path) -> Path | None:
    try:
        if path.is_symlink():
            raw = os.readlink(path)
            target = Path(raw)
            if not target.is_absolute():
                target = path.parent / target
            return target.resolve()
        if is_junction(path):
            return path.resolve()
    except OSError:
        return None
    return None


def points_to(path: Path, target: Path) -> bool:
    current = link_target(path)
    if current is None:
        return False
    try:
        return norm_path(current) == norm_path(target.resolve())
    except OSError:
        return False


def remove_linkish(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif is_junction(path):
        os.rmdir(path)
    else:
        raise RuntimeError(f"not a symlink/junction: {path}")


def create_dir_link(target: Path, link: Path) -> str:
    """Create a directory link without requiring Windows symlink privilege.

    Windows uses an NTFS junction. Unix-like systems use a regular directory symlink.
    """
    target = target.resolve()
    if os.name == "nt":
        command = f'mklink /J "{link}" "{target}"'
        # shell 字符串而非 argv list：Windows 下 list 形式会经 list2cmdline
        # 把内部引号转义成 \" ，cmd.exe 不识别该转义，mklink 收到畸形参数并报
        # "The filename, directory name, or volume label syntax is incorrect"。
        # shell=True 把命令原样交给 cmd，引号保持正确。
        proc = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"mklink /J failed for {link}: {proc.stderr.strip()}")
        return "junction"

    link.symlink_to(target, target_is_directory=True)
    return "symlink"
