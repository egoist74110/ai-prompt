#!/usr/bin/env python3
"""本机公共密钥库 CLI：secrets/secrets.json（已 gitignore，目录 700 / 文件 600）。

结构：{"version": 1, "secrets": {"<索引名>": {"description": "...", "value": "...", "created_at": ..., "updated_at": ...}}}

安全约定：
- 密钥值不经 argv 传入（避免进 shell history / 进程列表），只从隐藏输入或 stdin 读取。
- list/show 永不输出值；只有 get 把值写到 stdout（供管道/命令替换使用）。
- 写入为原子替换，并限制为仅当前用户可读写：
  POSIX（macOS/Linux/WSL）用 chmod 700/600；Windows 用 icacls 断开继承、只授权当前用户。
- 跨平台 I/O 固定 UTF-8，不依赖控制台代码页（Windows cp936 / PowerShell BOM）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "secrets"
FILE = DIR / "secrets.json"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
IS_WINDOWS = os.name == "nt"


def _now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _windows_user() -> str:
    user = os.environ.get("USERNAME") or getpass.getuser()
    domain = os.environ.get("USERDOMAIN")
    return f"{domain}\\{user}" if domain else user


def _restrict(path: Path, is_dir: bool) -> None:
    """把权限收紧到仅当前用户；无法收紧时告警而不是静默继续。"""
    if IS_WINDOWS:
        grant = f"{_windows_user()}:{'(OI)(CI)F' if is_dir else 'F'}"
        res = subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", grant],
                             capture_output=True, text=True)
        if res.returncode != 0:
            print(f"警告: icacls 收紧权限失败（{path}）: {(res.stderr or res.stdout).strip()}", file=sys.stderr)
        return
    mode = 0o700 if is_dir else 0o600
    os.chmod(path, mode)
    actual = os.stat(path).st_mode & 0o777
    if actual != mode:  # 如 WSL 下 /mnt/<盘符> 未启用 metadata 挂载时 chmod 不生效
        print(f"警告: {path} 权限为 {oct(actual)}，未能设为 {oct(mode)}；请把仓库放在支持 POSIX 权限的文件系统上。", file=sys.stderr)


def _ensure(repair: bool = False) -> None:
    created = not DIR.exists()
    DIR.mkdir(exist_ok=True)
    if created or repair:
        _restrict(DIR, is_dir=True)
    if not FILE.exists():
        _write({"version": 1, "secrets": {}})
    elif repair:
        _restrict(FILE, is_dir=False)


def _read() -> dict:
    _ensure()
    data = json.loads(FILE.read_text(encoding="utf-8"))
    data.setdefault("secrets", {})
    return data


def _write(data: dict) -> None:
    # 临时文件与目标同目录：Windows 下继承目录的受限 ACL，os.replace 也能原子替换
    fd, tmp = tempfile.mkstemp(dir=DIR, prefix=".secrets.", suffix=".tmp")
    try:
        if not IS_WINDOWS:
            os.chmod(tmp, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, FILE)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _read_value(from_stdin: bool) -> str:
    if from_stdin or not sys.stdin.isatty():
        raw = sys.stdin.buffer.read()
        try:
            value = raw.decode("utf-8-sig")  # 兼容 PowerShell 管道带 BOM
        except UnicodeDecodeError:
            value = raw.decode(sys.stdin.encoding or "utf-8")
        value = value.rstrip("\r\n")
    else:
        value = getpass.getpass("密钥值（输入不回显）: ")
        if getpass.getpass("再次输入确认: ") != value:
            sys.exit("两次输入不一致，未写入。")
    if not value:
        sys.exit("密钥值为空，未写入。")
    return value


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="创建密钥库；已存在则重新收紧权限")
    sub.add_parser("list", help="列出索引名与说明（不含值）")
    s = sub.add_parser("set", help="新增/更新密钥；值从隐藏输入或 stdin 读取")
    s.add_argument("name", help="索引名，如 openai.api_key")
    s.add_argument("-d", "--description", help="用途说明（新增时必填）")
    s.add_argument("--stdin", action="store_true", help="从 stdin 读取值")
    d = sub.add_parser("describe", help="只修改说明，不动值")
    d.add_argument("name"); d.add_argument("description")
    g = sub.add_parser("get", help="把值输出到 stdout")
    g.add_argument("name")
    r = sub.add_parser("remove", help="删除一个密钥")
    r.add_argument("name")
    args = p.parse_args()
    # 说明文字含中文：避免 Windows 控制台/重定向时因代码页报 UnicodeEncodeError
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    if args.cmd == "init":
        _ensure(repair=True); print(f"ok: {FILE.relative_to(ROOT)}"); return 0

    data = _read(); items = data["secrets"]

    if args.cmd == "list":
        if not items:
            print("(空)"); return 0
        width = max(len(k) for k in items)
        for k in sorted(items):
            print(f"{k:<{width}}  {items[k].get('description', '')}")
        return 0

    name = args.name
    if not NAME_RE.match(name):
        sys.exit("索引名只允许字母、数字、. _ -，且须以字母或数字开头。")

    if args.cmd == "set":
        entry = items.get(name)
        if entry is None and not args.description:
            sys.exit("新增密钥必须用 -d/--description 写明用途。")
        value = _read_value(args.stdin)
        now = _now()
        items[name] = {
            "description": args.description or entry["description"],
            "value": value,
            "created_at": entry["created_at"] if entry else now,
            "updated_at": now,
        }
        _write(data); print(f"{'updated' if entry else 'added'}: {name}")
        return 0

    if name not in items:
        sys.exit(f"不存在: {name}")

    if args.cmd == "describe":
        items[name]["description"] = args.description; items[name]["updated_at"] = _now()
        _write(data); print(f"described: {name}")
    elif args.cmd == "get":
        sys.stdout.flush()
        sys.stdout.buffer.write(items[name]["value"].encode("utf-8"))  # 不受代码页影响
        if sys.stdout.isatty(): sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    elif args.cmd == "remove":
        del items[name]; _write(data); print(f"removed: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
