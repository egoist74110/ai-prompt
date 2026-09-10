#!/usr/bin/env python3
"""Reject machine identities, runtime-name hardcoding, and unsafe local-state writes."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

SELF = Path(__file__).resolve()
ROOT = SELF.parents[1]
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml"}
IGNORE_DIRS = {".git", ".local", "__pycache__", ".venv", "node_modules"}
USERNAME = r"[A-Za-z0-9_.\-]+"

PATTERNS = [
    ("concrete macOS home", re.compile(r"/Users/(?![<{\$])" + USERNAME + "/")),
    ("concrete Linux home", re.compile(r"/home/(?![<{\$])" + USERNAME + "/")),
    ("concrete Windows user home", re.compile(r"[A-Za-z]:\\Users\\(?![<{%$])" + USERNAME + r"\\", re.I)),
    ("fixed WSL distro UNC", re.compile(r"\\\\wsl(?:\.localhost|\$)\\(?![<{%$])" + USERNAME + r"\\", re.I)),
]
FORBIDDEN_LITERALS = {
    "PCMClawUbuntu": "fixed WSL distro name",
    "/Users/wesker/": "old canonical-user path",
    "C:\\Users\\wesker\\": "old Windows-user path",
}
RUNTIME_CONSUMERS = [ROOT / "tools" / name for name in ("bootstrap.py", "doctor.py", "sync_skills.py", "runtime_state.py", "runtime_registry.py")]
RUNTIME_TEMPLATE = ROOT / "config" / "runtime-templates.json"


def iter_files():
    for path in ROOT.rglob("*"):
        if path.resolve() == SELF or not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def iter_python_files():
    for path in ROOT.rglob("*.py"):
        if path.resolve() == SELF or any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        yield path


def starter_runtime_ids() -> list[str]:
    try:
        data = json.loads(RUNTIME_TEMPLATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    runtimes = data.get("runtimes", {}) if isinstance(data, dict) else {}
    return sorted(runtimes) if isinstance(runtimes, dict) else []


def check_runtime_name_hardcoding(problems: list[tuple[Path, int, str, str]]) -> None:
    for path in RUNTIME_CONSUMERS:
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for runtime_id in starter_runtime_ids():
                if re.search(rf"(['\"]){re.escape(runtime_id)}\1", line, re.I):
                    problems.append((rel, lineno, "hardcoded starter runtime id in core consumer", runtime_id))


def imported_local_state_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    read_names: set[str] = set()
    write_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != "local_state":
            continue
        for alias in node.names:
            local = alias.asname or alias.name
            if alias.name == "read_kind":
                read_names.add(local)
            elif alias.name == "write_kind":
                write_names.add(local)
    return read_names, write_names


def assigned_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def check_unsafe_state_writes(problems: list[tuple[Path, int, str, str]]) -> None:
    """Reject obvious read_kind -> mutate -> write_kind read-modify-write flows.

    write_kind remains legal for intentional whole-document replacement. A variable
    populated by read_kind must not later be passed back to write_kind; use
    update_kind so the read and write share one lock.
    """
    for path in iter_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        read_names, write_names = imported_local_state_names(tree)
        if not read_names or not write_names:
            continue
        tainted: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in read_names:
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        name = assigned_name(target)
                        if name:
                            tainted.add(name)
        rel = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id not in write_names:
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Name):
                continue
            if node.args[1].id in tainted:
                problems.append((rel, node.lineno, "unsafe local-state read-modify-write", f"{node.func.id}(..., {node.args[1].id})"))


def main() -> int:
    problems: list[tuple[Path, int, str, str]] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                match = pattern.search(line)
                if match:
                    problems.append((rel, lineno, label, match.group(0)))
            for literal, label in FORBIDDEN_LITERALS.items():
                if literal in line:
                    problems.append((rel, lineno, label, literal))

    check_runtime_name_hardcoding(problems)
    check_unsafe_state_writes(problems)

    if problems:
        print("portability check failed:", file=sys.stderr)
        for rel, lineno, label, value in problems:
            print(f"  {rel}:{lineno}: {label}: {value}", file=sys.stderr)
        print("Machine facts belong in .local; runtime consumers stay data-driven; read-modify-write local-state mutations must use update_kind().", file=sys.stderr)
        return 1

    print("portability check: machine identities, runtime consumers, and local-state writes are portable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
