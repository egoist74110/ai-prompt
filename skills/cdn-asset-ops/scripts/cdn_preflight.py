#!/usr/bin/env python3
"""Read-only, cached MinIO/S3 preflight.

No credentials are printed or copied into ai-prompt local state. The cache stores only mc locator,
alias name and verified endpoint for a host.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from local_state import migrate_local_files, read_kind, update_kind  # noqa: E402

SKILL = "cdn-asset-ops"


def parse_host(value: str) -> tuple[str, int | None, str | None]:
    raw = value.strip()
    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    host = parsed.hostname
    if not host:
        raise ValueError(f"无法解析 host: {value}")
    try:
        port = parsed.port
    except ValueError:
        port = None
    scheme = parsed.scheme or None
    return host.lower().rstrip("."), port, scheme


def find_alias(mc: str, host: str) -> tuple[str | None, str | None]:
    proc = subprocess.run([mc, "alias", "ls"], text=True, capture_output=True)
    if proc.returncode != 0:
        return None, None
    current = None
    wanted = host.lower().rstrip(".")
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Never print or persist AccessKey/SecretKey lines.
        if re.search(r"accesskey|secretkey", stripped, re.I):
            continue
        if not line[:1].isspace() and ":" not in stripped:
            current = stripped
            continue
        match = re.match(r"URL\s*:\s*(\S+)", stripped, re.I)
        if not match:
            continue
        alias_url = match.group(1)
        alias_host = (urlparse(alias_url).hostname or "").lower().rstrip(".")
        if alias_host == wanted:
            return current, alias_url
    return None, None


def probe(endpoint: str) -> tuple[bool, str]:
    url = endpoint.rstrip("/") + "/minio/health/live"
    req = Request(url, method="HEAD", headers={"User-Agent": "ai-prompt-cdn-preflight/1"})
    context = ssl.create_default_context()
    try:
        with urlopen(req, timeout=3, context=context) as response:
            server = response.headers.get("Server", "")
            return "minio" in server.lower() and "console" not in server.lower(), server
    except Exception:
        return False, ""


def discover_endpoints(host: str, hinted_port: int | None, hinted_scheme: str | None):
    ports = []
    if hinted_port:
        ports.append(hinted_port)
    ports.extend([9000, 9001, 9002, 9003, 9004, 9005, 80, 443])
    seen = set()
    ordered_ports = [p for p in ports if not (p in seen or seen.add(p))]
    schemes = [hinted_scheme] if hinted_scheme in {"http", "https"} else []
    schemes += [s for s in ("http", "https") if s not in schemes]

    found = []
    for scheme in schemes:
        for port in ordered_ports:
            endpoint = f"{scheme}://{host}:{port}"
            ok, server = probe(endpoint)
            if ok:
                found.append((endpoint, server))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="MinIO console URL or host")
    parser.add_argument("--refresh", action="store_true", help="ignore cache and re-probe")
    args = parser.parse_args()

    host, port, scheme = parse_host(args.target)
    migrate_local_files()
    runtime = read_kind("runtime")
    state = read_kind("state")
    runtime_entry = runtime.setdefault("skills", {}).setdefault(SKILL, {})
    hosts = state.setdefault("skills", {}).setdefault(SKILL, {}).setdefault("hosts", {})
    cached = hosts.get(host, {})

    if cached.get("verified") and not args.refresh:
        print("===== CDN PREFLIGHT (cached) =====")
        print(f"host: {host}")
        print(f"mc: {runtime_entry.get('mc', '<unknown>')}")
        print(f"alias: {cached.get('alias') or '<none>'}")
        print(f"endpoint: {cached.get('endpoint') or '<unknown>'}")
        print("cache: hit；实际操作失败时再用 --refresh 重探")
        return 0

    mc = os.environ.get("MC_BIN", "").strip() or runtime_entry.get("mc") or shutil.which("mc")
    if not mc or (not Path(mc).exists() and not shutil.which(str(mc))):
        print("mc: NOT installed / not found")
        print("result: 先安装 MinIO mc；安装路径属于本机配置，成功后会缓存")
        return 2

    alias, alias_url = find_alias(str(mc), host)
    alias_verified = False
    if alias_url:
        alias_verified, _ = probe(alias_url)
    endpoints = discover_endpoints(host, port, scheme)
    endpoint = alias_url if alias_verified else (endpoints[0][0] if endpoints else None)

    print("===== CDN PREFLIGHT (read-only discovery) =====")
    print(f"host: {host}")
    print(f"mc: {mc}")
    print(f"alias: {alias or '<none>'}")
    print(f"alias endpoint: {alias_url or '<none>'}")
    print(f"alias verified: {'yes' if alias_verified else 'no'}")
    if endpoints:
        print("probed S3 endpoint(s):")
        for item, server in endpoints:
            print(f"  {item} [{server or 'MinIO'}]")
    else:
        print("probed S3 endpoint: none")

    def save_runtime(latest: dict) -> None:
        latest.setdefault("skills", {}).setdefault(SKILL, {})["mc"] = str(mc)

    update_kind("runtime", save_runtime)
    now = datetime.now(timezone.utc).isoformat()

    if endpoint:
        def save_success(latest: dict) -> None:
            latest_hosts = latest.setdefault("skills", {}).setdefault(SKILL, {}).setdefault("hosts", {})
            latest_hosts[host] = {
                "verified": True,
                "alias": alias if alias_verified else None,
                "endpoint": endpoint,
                "last_verified": now,
            }

        update_kind("state", save_success)
        print("cache: 已写入 .local；下次先直接复用")
        return 0

    def save_failure(latest: dict) -> None:
        latest_hosts = latest.setdefault("skills", {}).setdefault(SKILL, {}).setdefault("hosts", {})
        latest_hosts[host] = {
            "verified": False,
            "reason": "no verified matching alias or S3 endpoint discovered",
            "retry": "when-network-or-config-changes",
            "last_verified": now,
        }

    update_kind("state", save_failure)
    print("result: 未确认 S3 endpoint；向用户确认真实 endpoint 后再配置 alias")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
