#!/usr/bin/env python3
"""Cross-platform, read-only deployment doctor for ai-prompt."""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
LOCAL_RUNTIME = ROOT / ".local" / "runtime.json"
LOCAL_STATE = ROOT / ".local" / "state.json"

fail = False


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def bad(msg: str) -> None:
    global fail
    fail = True
    print(f"  ✗ {msg}")


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path}: root must be JSON object")
    return data


def norm(value: str | Path) -> str:
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


def points_to(path: Path, target: Path) -> bool:
    try:
        if is_linkish(path):
            return norm(path.resolve()) == norm(target.resolve())
    except OSError:
        pass
    return False


def configured_path(runtime: dict, runtime_name: str, key: str, fallback: Path) -> Path:
    value = runtime.get("runtimes", {}).get(runtime_name, {}).get(key)
    return Path(value).expanduser() if value else fallback


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def main() -> int:
    runtime: dict = {}

    print("== 0. root / local state ==")
    ok(f"AI_PROMPT_ROOT={ROOT}")
    if LOCAL_RUNTIME.is_file() and LOCAL_STATE.is_file():
        try:
            runtime = read_json(LOCAL_RUNTIME)
            read_json(LOCAL_STATE)
            ok(".local runtime/state JSON 有效")
        except RuntimeError as exc:
            bad(str(exc))
    else:
        warn(".local 尚未初始化；首次需要缓存时运行 tools/runtime_state.py init")

    print("== 1. router 引用文件 ==")
    required = [
        "common.md",
        "models/high.md",
        "models/scout.md",
        "capabilities/skills.md",
        "capabilities/mcp.md",
        "capabilities/search.md",
        "capabilities/cross-review.md",
        "config/README.md",
        "tools/local_state.py",
        "tools/runtime_state.py",
        "tools/sync_skills.py",
    ]
    for rel in required:
        path = ROOT / rel
        ok(rel) if path.is_file() else bad(f"{rel} 缺失")

    print("== 2. 运行时入口（只检查实际存在的） ==")
    entry_defaults = {
        "claude": HOME / ".claude" / "CLAUDE.md",
        "codex": HOME / ".codex" / "AGENTS.md",
        "gemini": HOME / ".gemini" / "GEMINI.md",
        "dsh": HOME / ".dsh" / "AGENTS.md",
    }
    router = ROOT / "router.md"
    found = False
    for name, fallback in entry_defaults.items():
        entry = configured_path(runtime, name, "entry_path", fallback)
        if not entry.is_file():
            continue
        found = True
        try:
            text = entry.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            bad(f"{entry}: {exc}")
            continue
        candidates = {str(router), str(router).replace("\\", "/"), str(router).replace("/", "\\")}
        if any(c in text for c in candidates):
            ok(f"{name}: {entry} → router.md")
        else:
            warn(f"{name}: {entry} 存在，但未检测到当前 router 路径")
    if not found:
        warn("未发现已知运行时入口；自定义入口可在 .local/runtime.json 记录")

    print("== 3. skills 部署 ==")
    central = ROOT / "skills"
    central_names = {p.name for p in central.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}

    claude_dir = configured_path(runtime, "claude", "skills_path", HOME / ".claude" / "skills")
    if claude_dir.exists() or is_linkish(claude_dir):
        if points_to(claude_dir, central):
            ok(f"claude skills → {central}")
        else:
            warn(f"claude skills 使用其它布局：{claude_dir}；以 runtime/实测为准")

    codex_dir = configured_path(runtime, "codex", "skills_path", HOME / ".codex" / "skills")
    if codex_dir.is_dir():
        missing = []
        dangling = []
        real_dirs = []
        for name in sorted(central_names):
            dest = codex_dir / name
            if not is_linkish(dest):
                missing.append(name)
            elif not points_to(dest, central / name):
                dangling.append(name)
        for dest in codex_dir.iterdir():
            if dest.name == ".system":
                continue
            if dest.is_dir() and not is_linkish(dest):
                real_dirs.append(dest.name)
        if not missing and not dangling:
            ok("codex 中央 skill 链接完整")
        if missing:
            warn("codex 缺中央 skill: " + ", ".join(missing))
        if dangling:
            warn("codex 链接目标不一致: " + ", ".join(dangling))
        if real_dirs:
            warn("codex 真实目录（可能是私有/孤儿）: " + ", ".join(sorted(real_dirs)))

    print("== 4. skills 索引 ==")
    proc = run([sys.executable, "tools/gen-index.py", "--check"])
    if proc.returncode == 0:
        ok((proc.stdout.strip().splitlines() or ["gen-index --check 通过"])[0])
    else:
        bad("gen-index --check 未通过")
        for line in (proc.stdout + proc.stderr).strip().splitlines():
            print(f"      {line}")

    print("== 5. pre-commit hook ==")
    git = shutil.which("git")
    if not git:
        warn("git 不在 PATH，跳过 hook 检查")
    else:
        inside = run([git, "rev-parse", "--is-inside-work-tree"])
        if inside.returncode != 0:
            warn("当前部署不是 git 工作副本，跳过 hook 检查")
        else:
            hp = run([git, "rev-parse", "--git-path", "hooks"])
            hook_dir = Path(hp.stdout.strip())
            if not hook_dir.is_absolute():
                hook_dir = ROOT / hook_dir
            installed = hook_dir / "pre-commit"
            canonical = ROOT / "tools" / "hooks" / "pre-commit"
            if installed.is_file():
                try:
                    if installed.read_bytes() == canonical.read_bytes():
                        ok("pre-commit hook 已安装且与正典一致")
                    else:
                        warn("pre-commit hook 已安装但版本过期 → 重新运行 install-hooks")
                except OSError as exc:
                    warn(f"hook 比对失败: {exc}")
            else:
                warn("pre-commit hook 未安装；编辑机建议安装")

    print("== 6. 通用命令 ==")
    for command in ("git", "node", "python3", "python", "az", "mc", "gh", "claude", "codex", "agy"):
        path = shutil.which(command)
        if path:
            ok(f"{command}: {path}")
        else:
            warn(f"{command} 不在 PATH")

    print()
    print("doctor: 全部硬性检查通过" if not fail else "doctor: 有 ✗ 项，按上面提示修")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
