#!/usr/bin/env python3
"""Track and update Skills vendored from GitHub.

A vendored Skill has `skills/<name>/UPSTREAM.json`:

    {"repo": "owner/name", "path": "dir/in/repo", "ref": "main",
     "commit": "<upstream sha the local copy is based on, or null>",
     "synced_at": "YYYY-MM-DD", "local_changes": "none | <note>", "exclude": ["glob", ...]}

Commands:
  list                       show tracked Skills
  adopt NAME --repo --path   create UPSTREAM.json; detect the base commit by blob hashes
  check [NAME...]            compare pinned commit with upstream (TTL-cached in .local/state.json)
  update NAME [--apply]      3-way merge upstream changes into the local copy (dry-run by default)
  pin NAME SHA               record a manually resolved base commit

Downloaded upstream content is data only: it is extracted, compared, and merged, never executed.
Auth (optional): GH_TOKEN / GITHUB_TOKEN, else `gh auth token`. Tokens are never printed or stored.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from local_state import LOCAL, read_kind, update_kind

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SIDECAR = "UPSTREAM.json"
API = "https://api.github.com"
DEFAULT_MAX_AGE_DAYS = 7
ALWAYS_IGNORED = (SIDECAR, ".last-update-check", ".DS_Store", "*/.DS_Store", "__pycache__/*", "*/__pycache__/*", "*.pyc", ".env", "runtime.conf")


class UpstreamError(RuntimeError):
    pass


# ---------- GitHub access ----------

_TOKEN: str | None = None
_TOKEN_LOADED = False


def token() -> str | None:
    global _TOKEN, _TOKEN_LOADED
    if _TOKEN_LOADED:
        return _TOKEN
    _TOKEN_LOADED = True
    _TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not _TOKEN and shutil.which("gh"):
        try:
            out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
            if out.returncode == 0 and out.stdout.strip():
                _TOKEN = out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return _TOKEN


def request(url: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "ai-prompt-skill-upstream"})
    tok = token()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise UpstreamError(f"HTTP {exc.code} for {url.split('?')[0]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpstreamError(f"network error for {url.split('?')[0]}: {exc}") from exc


def api(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    return json.loads(request(f"{API}{endpoint}{query}").decode("utf-8"))


def default_branch(repo: str) -> str:
    return api(f"/repos/{repo}")["default_branch"]


def path_commits(repo: str, ref: str, path: str, limit: int) -> list[dict[str, str]]:
    """Newest-first commits on `ref` touching `path` (repo-wide when path is empty)."""
    out: list[dict[str, str]] = []
    page = 1
    while len(out) < limit:
        params: dict[str, Any] = {"sha": ref, "per_page": min(100, limit), "page": page}
        if path:
            params["path"] = path
        batch = api(f"/repos/{repo}/commits", params)
        if not batch:
            break
        for item in batch:
            out.append({"sha": item["sha"], "date": item["commit"]["committer"]["date"][:10]})
        if len(batch) < params["per_page"]:
            break
        page += 1
    return out[:limit]


def path_exists(repo: str, ref: str, path: str) -> bool:
    try:
        api(f"/repos/{repo}/contents/{urllib.parse.quote(path)}", {"ref": ref})
        return True
    except UpstreamError as exc:
        if "HTTP 404" in str(exc):
            return False
        raise


def tree_blobs(repo: str, commit: str, path: str) -> dict[str, str]:
    """Map of relpath -> git blob sha for files under `path` at `commit`."""
    data = api(f"/repos/{repo}/git/trees/{commit}", {"recursive": 1})
    if data.get("truncated"):
        raise UpstreamError(f"{repo} tree at {commit[:8]} is truncated by the API; compare manually")
    prefix = f"{path.strip('/')}/" if path.strip("/") else ""
    return {
        item["path"][len(prefix):]: item["sha"]
        for item in data.get("tree", [])
        if item.get("type") == "blob" and item["path"].startswith(prefix)
    }


def download_subtree(repo: str, commit: str, path: str, dest: Path) -> dict[str, int]:
    """Extract `path` at `commit` into dest. Returns relpath -> mode. Regular files only."""
    raw = request(f"{API}/repos/{repo}/tarball/{commit}", accept="application/vnd.github+json")
    dest.mkdir(parents=True, exist_ok=True)
    modes: dict[str, int] = {}
    sub = path.strip("/")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2:
                continue
            rel = PurePosixPath(*parts[1:])  # drop "<owner>-<repo>-<sha>/"
            if sub:
                try:
                    rel = rel.relative_to(sub)
                except ValueError:
                    continue
            if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            target = dest.joinpath(*rel.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(handle.read())
            if member.mode & 0o111:
                target.chmod(target.stat().st_mode | 0o755)
            modes[rel.as_posix()] = member.mode
    return modes


# ---------- local helpers ----------

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def ignored(rel: str, extra: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in (*ALWAYS_IGNORED, *extra))


def files_under(base: Path, extra: list[str]) -> dict[str, Path]:
    if not base.is_dir():
        return {}
    out = {}
    for p in sorted(base.rglob("*")):
        if p.is_file() and not p.is_symlink():
            rel = p.relative_to(base).as_posix()
            if not ignored(rel, extra):
                out[rel] = p
    return out


def local_blobs(skill_dir: Path, extra: list[str]) -> dict[str, str]:
    return {rel: blob_sha(p.read_bytes()) for rel, p in files_under(skill_dir, extra).items()}


def skill_dir(name: str) -> Path:
    d = SKILLS / name
    if not (d / "SKILL.md").is_file():
        raise UpstreamError(f"skills/{name}/SKILL.md not found")
    return d


def load_meta(name: str) -> dict[str, Any]:
    f = skill_dir(name) / SIDECAR
    if not f.is_file():
        raise UpstreamError(f"skills/{name} has no {SIDECAR}; use `adopt` first")
    meta = json.loads(f.read_text(encoding="utf-8"))
    for key in ("repo", "path", "ref"):
        if not isinstance(meta.get(key), str):
            raise UpstreamError(f"skills/{name}/{SIDECAR}: `{key}` must be a string")
    meta.setdefault("exclude", [])
    return meta


def save_meta(name: str, meta: dict[str, Any]) -> None:
    order = ("repo", "path", "ref", "commit", "synced_at", "local_changes", "exclude", "index_description", "note")
    data = {k: meta[k] for k in order if k in meta}
    data.update({k: v for k, v in meta.items() if k not in data})
    with (skill_dir(name) / SIDECAR).open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def tracked() -> list[str]:
    return sorted(p.parent.name for p in SKILLS.glob(f"*/{SIDECAR}") if (p.parent / "SKILL.md").is_file())


def describe_diff(local: dict[str, str], upstream: dict[str, str]) -> str:
    modified = sorted(k for k in local if k in upstream and local[k] != upstream[k])
    local_only = sorted(k for k in local if k not in upstream)
    missing = sorted(k for k in upstream if k not in local)
    if not (modified or local_only or missing):
        return "none"
    bits = []
    for label, items in (("modified", modified), ("local-only", local_only), ("not vendored", missing)):
        if items:
            shown = ", ".join(items[:8]) + (f" (+{len(items) - 8})" if len(items) > 8 else "")
            bits.append(f"{label}: {shown}")
    return "auto-detected; " + "; ".join(bits)


# ---------- commands ----------

def cmd_list(_: argparse.Namespace) -> int:
    names = tracked()
    if not names:
        print("no vendored skills tracked")
        return 0
    for name in names:
        m = load_meta(name)
        commit = (m.get("commit") or "unpinned")[:8]
        print(f"{name:32} {m['repo']}:{m['path'] or '.'}@{m['ref']}  base={commit}  synced={m.get('synced_at')}")
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    name = args.name
    target = skill_dir(name) / SIDECAR
    if target.exists() and not args.force:
        raise UpstreamError(f"{target.relative_to(ROOT)} exists; pass --force to re-detect")
    ref = args.ref or default_branch(args.repo)
    path = args.path.strip("/")
    exclude = list(args.exclude or [])
    local = local_blobs(skill_dir(name), exclude)
    commits = path_commits(args.repo, ref, path, args.depth)
    if not commits:
        raise UpstreamError(f"no commits touch {args.repo}:{path or '.'} on {ref}; check repo/path")
    best: tuple[int, int, dict[str, str]] | None = None
    best_commit = None
    for c in commits:
        up = {k: v for k, v in tree_blobs(args.repo, c["sha"], path).items() if not ignored(k, exclude)}
        matches = sum(1 for k, v in up.items() if local.get(k) == v)
        key = (int(up.get("SKILL.md") is not None and up.get("SKILL.md") == local.get("SKILL.md")), matches, up)
        if best is None or key[:2] > best[:2]:
            best, best_commit = key, c
        if up == local:
            break
    meta: dict[str, Any] = {"repo": args.repo, "path": path, "ref": ref}
    if best and best[1] > 0:
        meta["commit"] = best_commit["sha"]
        meta["local_changes"] = describe_diff(local, best[2])
    else:
        meta["commit"] = None
        meta["local_changes"] = "base unknown: no upstream revision in the scanned history shares files with the local copy"
    meta["synced_at"] = date.today().isoformat()
    meta["exclude"] = exclude
    save_meta(name, meta)
    base = (meta["commit"] or "none")[:8]
    print(f"{name}: base={base} ({best_commit['date'] if meta['commit'] else '-'}) local_changes={meta['local_changes']}")
    if meta["commit"] and best_commit is not commits[0]:
        print(f"{name}: upstream has newer commits; run `check {name}` / `update {name}`")
    return 0


def _cached(name: str, max_age: int) -> dict[str, Any] | None:
    entry = read_kind("state").get("skills_upstream", {}).get(name)
    if not isinstance(entry, dict) or not entry.get("checked_at"):
        return None
    try:
        checked = datetime.fromisoformat(entry["checked_at"])
    except ValueError:
        return None
    return entry if datetime.now(timezone.utc) - checked < timedelta(days=max_age) else None


def check_one(name: str, meta: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"pinned": meta.get("commit")}
    try:
        commits = path_commits(meta["repo"], meta["ref"], meta["path"], 100)
    except UpstreamError as exc:
        return {**result, "status": "error", "detail": str(exc)}
    if not commits:
        return {**result, "status": "path-missing", "detail": f"{meta['repo']}:{meta['path'] or '.'} has no commits on {meta['ref']} (moved, renamed, or removed upstream)"}
    if meta["path"] and not path_exists(meta["repo"], meta["ref"], meta["path"]):
        return {**result, "status": "path-missing", "detail": f"{meta['path']} no longer exists on {meta['ref']} (moved, renamed, or removed upstream); find the new path and re-adopt"}
    latest = commits[0]
    result.update(latest=latest["sha"], latest_date=latest["date"])
    pinned = meta.get("commit")
    if not pinned:
        return {**result, "status": "unpinned", "detail": "no base commit recorded; review upstream manually, then `pin`"}
    shas = [c["sha"] for c in commits]
    if pinned == latest["sha"]:
        return {**result, "status": "current", "behind": 0}
    behind = shas.index(pinned) if pinned in shas else None
    return {**result, "status": "behind", "behind": behind if behind is not None else "100+"}


def cmd_check(args: argparse.Namespace) -> int:
    names = args.names or tracked()
    rows = []
    for name in names:
        meta = load_meta(name)
        entry = None if args.force else _cached(name, args.max_age_days)
        if entry and entry.get("pinned") == meta.get("commit"):
            entry = {**entry, "cached": True}
        else:
            entry = check_one(name, meta)
            entry["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if entry["status"] != "error":
                update_kind("state", lambda s, n=name, e=dict(entry): s.setdefault("skills_upstream", {}).__setitem__(n, e))
        rows.append((name, meta, entry))
    if args.json:
        print(json.dumps({n: e for n, _, e in rows}, ensure_ascii=False, indent=2))
        return 0
    for name, meta, e in rows:
        if args.quiet and e["status"] == "current":
            continue
        extra = ""
        if e["status"] == "behind":
            extra = f" by {e['behind']} commit(s); latest {str(e.get('latest'))[:8]} ({e.get('latest_date')})"
        elif e.get("detail"):
            extra = f": {e['detail']}"
        cached = " [cached]" if e.get("cached") else ""
        print(f"{name}: {e['status']}{extra}{cached}  ({meta['repo']}:{meta['path'] or '.'})")
    return 0


def _merge_text(local: bytes, base: bytes, theirs: bytes, work: Path) -> tuple[bytes, int]:
    paths = []
    for label, data in (("local", local), ("base", base), ("upstream", theirs)):
        p = work / f"merge.{label}"
        p.write_bytes(data)
        paths.append(str(p))
    proc = subprocess.run(
        ["git", "merge-file", "-p", "-L", "local", "-L", "base", "-L", "upstream", *paths],
        capture_output=True,
    )
    if proc.returncode < 0 or proc.returncode > 127:
        raise UpstreamError(f"git merge-file failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout, proc.returncode


def plan_update(local_dir: Path, base_dir: Path, new_dir: Path, exclude: list[str], work: Path):
    """Yield (rel, action, payload).

    add/update: write payload; delete: remove; keep/skip: leave local (payload = reason);
    conflict: payload is a merge with conflict markers; conflict-copy: upstream version
    goes beside the local file as `<file>.upstream` (binary or no common base).
    """
    local = files_under(local_dir, exclude)
    base = files_under(base_dir, exclude)
    new = files_under(new_dir, exclude)
    for rel in sorted(set(base) | set(new)):
        b = base[rel].read_bytes() if rel in base else None
        n = new[rel].read_bytes() if rel in new else None
        l = local[rel].read_bytes() if rel in local else None
        if b == n:
            continue  # upstream did not change this file
        if n is None:  # deleted upstream
            if l is None:
                continue
            yield (rel, "delete", None) if l == b else (rel, "keep", "deleted upstream but modified locally")
            continue
        if l is None:
            yield (rel, "add", n) if b is None else (rel, "skip", "changed upstream but removed locally")
            continue
        if l == n:
            continue
        if b is None or l == b:
            yield (rel, "update", n) if b is not None else (rel, "conflict-copy", n)
            continue
        if b"\0" in l or b"\0" in n or b"\0" in b:
            yield rel, "conflict-copy", n
            continue
        merged, conflicts = _merge_text(l, b, n, work)
        yield (rel, "conflict" if conflicts else "update", merged)


def cmd_update(args: argparse.Namespace) -> int:
    name = args.name
    meta = load_meta(name)
    base_sha = meta.get("commit")
    if not base_sha:
        raise UpstreamError(f"{name}: no base commit; review upstream manually, then `pin {name} <sha>`")
    target_sha = args.to or path_commits(meta["repo"], meta["ref"], meta["path"], 1)[0]["sha"]
    if target_sha == base_sha:
        print(f"{name}: already at {base_sha[:8]}")
        return 0
    tmp_root = LOCAL / "tmp" / "skill-upstream"
    tmp_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=tmp_root))
    try:
        download_subtree(meta["repo"], base_sha, meta["path"], work / "base")
        modes = download_subtree(meta["repo"], target_sha, meta["path"], work / "new")
        local_dir = skill_dir(name)
        actions = list(plan_update(local_dir, work / "base", work / "new", meta["exclude"], work))
        conflicts = [a for a in actions if a[1].startswith("conflict")]
        print(f"{name}: {base_sha[:8]} -> {target_sha[:8]}  ({len(actions)} file action(s), {len(conflicts)} conflict(s))")
        for rel, action, payload in actions:
            note = f"  ({payload})" if isinstance(payload, str) else ""
            print(f"  {action:13} {rel}{note}")
        if not args.apply:
            print("dry run; re-run with --apply to write changes")
            return 0
        for rel, action, payload in actions:
            dest = local_dir.joinpath(*rel.split("/"))
            if action in ("add", "update", "conflict", "conflict-copy") and isinstance(payload, bytes):
                if action == "conflict-copy":
                    dest = dest.with_name(dest.name + ".upstream")
                dest.parent.mkdir(parents=True, exist_ok=True)
                existed = dest.exists()
                dest.write_bytes(payload)
                if not existed and modes.get(rel, 0) & 0o111:
                    dest.chmod(dest.stat().st_mode | 0o755)
            elif action == "delete":
                dest.unlink()
        if conflicts:
            print("conflicts left with markers (or *.upstream for binary); resolve them, then "
                  f"`pin {name} {target_sha}`. Base commit unchanged.")
            return 2
        meta["commit"] = target_sha
        meta["synced_at"] = date.today().isoformat()
        save_meta(name, meta)
        update_kind("state", lambda s: s.setdefault("skills_upstream", {}).pop(name, None))
        print(f"{name}: updated; base is now {target_sha[:8]}. If SKILL.md frontmatter changed, run tools/gen-index.py.")
        return 0
    finally:
        if args.keep:
            print(f"kept snapshots: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
            try:
                tmp_root.rmdir()  # only succeeds when no other snapshot is kept
            except OSError:
                pass


def cmd_pin(args: argparse.Namespace) -> int:
    meta = load_meta(args.name)
    meta["commit"] = args.sha
    meta["synced_at"] = date.today().isoformat()
    if args.local_changes is not None:
        meta["local_changes"] = args.local_changes
    save_meta(args.name, meta)
    update_kind("state", lambda s: s.setdefault("skills_upstream", {}).pop(args.name, None))
    print(f"{args.name}: base pinned to {args.sha[:8]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(func=cmd_list)

    p = sub.add_parser("adopt")
    p.add_argument("name")
    p.add_argument("--repo", required=True, help="owner/name")
    p.add_argument("--path", default="", help="Skill directory inside the repo ('' = repo root)")
    p.add_argument("--ref", help="branch or tag to track (default: repo default branch)")
    p.add_argument("--exclude", action="append", help="glob of local/upstream files to ignore (repeatable)")
    p.add_argument("--depth", type=int, default=40, help="upstream commits to scan for the base")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_adopt)

    p = sub.add_parser("check")
    p.add_argument("names", nargs="*")
    p.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    p.add_argument("--force", action="store_true", help="ignore the TTL cache")
    p.add_argument("--quiet", action="store_true", help="print only Skills that need attention")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("update")
    p.add_argument("name")
    p.add_argument("--to", help="upstream commit (default: latest on ref)")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--keep", action="store_true", help="keep downloaded snapshots under .local/tmp")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("pin")
    p.add_argument("name")
    p.add_argument("sha")
    p.add_argument("--local-changes")
    p.set_defaults(func=cmd_pin)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UpstreamError as exc:
        print(f"skill_upstream: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
