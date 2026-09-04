#!/usr/bin/env python3
"""Cross-platform, read-only deployment doctor for ai-prompt."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
LOCAL_RUNTIME = ROOT / ".local" / "runtime.json"
LOCAL_STATE = ROOT / ".local" / "state.json"

sys.path.insert(0, str(ROOT / "tools"))
from platform_fs import is_linkish, points_to  # noqa: E402

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


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def run(cmd: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def check_script(label: str, script: str) -> None:
    proc = run([sys.executable, script])
    if proc.returncode == 0:
        first = (proc.stdout.strip().splitlines() or [f"{label} 通过"])[0]
        ok(first)
    else:
        bad(f"{label} 未通过")
        for line in (proc.stdout + proc.stderr).strip().splitlines():
            print(f"      {line}")


def check_runtime_entry(name: str, entry: dict, router: Path) -> None:
    label = entry.get("display_name", name)
    executable = entry.get("executable")
    if executable:
        ok(f"runtime {name} ({label}): {executable}")
    else:
        warn(f"runtime {name} ({label}): 未检测到 executable")

    entry_path = entry.get("entry_path")
    if entry_path:
        path = expand_path(str(entry_path))
        if not path.is_file():
            warn(f"runtime {name}: entry_path 不存在: {path}")
        else:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                warn(f"runtime {name}: 无法读取 entry: {exc}")
            else:
                candidates = {
                    str(router),
                    str(router).replace("\\", "/"),
                    str(router).replace("/", "\\"),
                }
                if any(candidate in text for candidate in candidates):
                    ok(f"runtime {name}: entry → router.md")
                else:
                    warn(f"runtime {name}: entry 存在，但未检测到当前 router 路径")
    elif entry.get("entry_candidates") and executable:
        warn(f"runtime {name}: 已检测到 CLI，但没有可用 entry_path")


def check_runtime_skills(name: str, entry: dict, central: Path, central_names: set[str]) -> None:
    mode = entry.get("skills_sync_mode", "none")
    if mode in (None, "none"):
        return

    raw_target = entry.get("skills_path")
    if not raw_target:
        candidates = entry.get("skills_candidates", []) or []
        if candidates:
            raw_target = candidates[0]
    if not raw_target:
        warn(f"runtime {name}: skills_sync_mode={mode} 但没有 skills path/candidate")
        return

    target = expand_path(str(raw_target))
    if mode == "central-dir-link":
        if points_to(target, central):
            ok(f"runtime {name}: skills → central-dir-link")
        elif target.exists() or is_linkish(target):
            warn(f"runtime {name}: skills 目标存在但不是中央目录链接: {target}")
        elif entry.get("executable"):
            warn(f"runtime {name}: skills 尚未部署: {target}")
        return

    if mode != "per-skill-link":
        warn(f"runtime {name}: 未知 skills_sync_mode={mode}")
        return
    if not target.is_dir():
        if entry.get("executable"):
            warn(f"runtime {name}: skills 目录不存在: {target}")
        return

    missing = []
    incorrect = []
    real_dirs = []
    for skill_name in sorted(central_names):
        dest = target / skill_name
        if not is_linkish(dest):
            missing.append(skill_name)
        elif not points_to(dest, central / skill_name):
            incorrect.append(skill_name)
    for dest in target.iterdir():
        if dest.name == ".system":
            continue
        if dest.is_dir() and not is_linkish(dest):
            real_dirs.append(dest.name)

    if not missing and not incorrect:
        ok(f"runtime {name}: central skill links 完整")
    if missing:
        warn(f"runtime {name}: 缺中央 skill: " + ", ".join(missing))
    if incorrect:
        warn(f"runtime {name}: skill 链接目标不一致: " + ", ".join(incorrect))
    if real_dirs:
        warn(f"runtime {name}: 真实目录（可能是私有/孤儿）: " + ", ".join(sorted(real_dirs)))


def main() -> int:
    runtime: dict = {}

    print("== 0. root / local state ==")
    ok(f"AI_PROMPT_ROOT={ROOT}")
    if LOCAL_RUNTIME.is_file() and LOCAL_STATE.is_file():
        try:
            runtime = read_json(LOCAL_RUNTIME)
            read_json(LOCAL_STATE)
            ok(".local runtime/state JSON 有效")
            if runtime.get("bootstrap", {}).get("last_discovered"):
                ok("bootstrap machine discovery 已运行")
            else:
                warn("local runtime 尚无 bootstrap 记录 → 可运行 runtime_state.py detect")
        except RuntimeError as exc:
            bad(str(exc))
    else:
        warn(".local 尚未初始化；运行 tools/runtime_state.py init 可初始化 registry 并探测本机能力")

    print("== 1. router 引用文件 ==")
    required = [
        "common.md",
        "models/high.md",
        "models/scout.md",
        "capabilities/skills.md",
        "capabilities/mcp.md",
        "capabilities/search.md",
        "capabilities/cross-review.md",
        "capabilities/cleanup.md",
        "config/README.md",
        "config/runtime-templates.json",
        "tools/local_state.py",
        "tools/runtime_registry.py",
        "tools/bootstrap.py",
        "tools/runtime_state.py",
        "tools/search_state.py",
        "tools/sync_skills.py",
        "tools/check_portability.py",
    ]
    for rel in required:
        path = ROOT / rel
        ok(rel) if path.is_file() else bad(f"{rel} 缺失")

    print("== 2. 中央规则可移植性 ==")
    check_script("portability check", "tools/check_portability.py")

    print("== 3. 动态 runtime registry ==")
    router = ROOT / "router.md"
    entries = runtime.get("runtimes", {})
    enabled_entries = [
        (name, entry)
        for name, entry in entries.items()
        if isinstance(entry, dict) and entry.get("enabled", True)
    ]
    if not enabled_entries:
        warn("没有启用的 runtime；可用 runtime_state.py runtime add 注册任意 CLI/runtime")
    for name, entry in sorted(enabled_entries):
        check_runtime_entry(name, entry, router)

    print("== 4. runtime skills 部署 ==")
    central = ROOT / "skills"
    central_names = {p.name for p in central.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    for name, entry in sorted(enabled_entries):
        check_runtime_skills(name, entry, central, central_names)

    print("== 5. search local policy ==")
    search_cfg = runtime.get("search", {}) if isinstance(runtime.get("search", {}), dict) else {}
    contexts = search_cfg.get("contexts", {}) if isinstance(search_cfg, dict) else {}
    backends = search_cfg.get("backends", {}) if isinstance(search_cfg, dict) else {}
    ok(f"search contexts: {len(contexts) if isinstance(contexts, dict) else 0}")
    ok(f"configured search backends: {len(backends) if isinstance(backends, dict) else 0}")
    if isinstance(contexts, dict):
        local_contexts = [
            name for name, entry in contexts.items()
            if isinstance(entry, dict) and entry.get("hosting") in {"local", "self-hosted"}
        ]
        for name in local_contexts:
            policy = contexts[name].get("native_search_policy", "auto")
            if policy == "deny":
                ok(f"search context {name}: local/self-hosted native search denied")
            else:
                warn(f"search context {name}: local/self-hosted but native_search_policy={policy}")

    print("== 6. skills 索引 ==")
    proc = run([sys.executable, "tools/gen-index.py", "--check"])
    if proc.returncode == 0:
        ok((proc.stdout.strip().splitlines() or ["gen-index --check 通过"])[0])
    else:
        bad("gen-index --check 未通过")
        for line in (proc.stdout + proc.stderr).strip().splitlines():
            print(f"      {line}")

    print("== 7. pre-commit hook ==")
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

    print("== 8. 本机 support command probes ==")
    cached_commands = runtime.get("paths", {}).get("commands", {})
    for command in runtime.get("probe_commands", []) or []:
        path = cached_commands.get(command) or shutil.which(command)
        if path:
            ok(f"{command}: {path}")
        else:
            warn(f"{command} 不在 PATH")

    print()
    print("doctor: 全部硬性检查通过" if not fail else "doctor: 有 ✗ 项，按上面提示修")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
