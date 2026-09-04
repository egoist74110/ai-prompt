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

from local_state import migrate_local_files, read_kind, write_kind  # noqa: E402

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
    return host, port, scheme


def find_alias(mc: str, host: str) -> tuple[str | None, str | None]:
    proc = subprocess.run([mc, "alias", "ls"], text=True, capture_output=True)
    if proc.returncode != 0:
        return None, None
    current = None
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
        if match and host.lower() in match.group(1).lower():
            return current, match.group(1)
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
    if not mc or not Path(mc).exists() and not shutil.which(str(mc)):
        print("mc: NOT installed / not found")
        print("result: 先安装 MinIO mc；安装路径属于本机配置，成功后会缓存")
        return 2

    runtime_entry["mc"] = str(mc)
    alias, alias_url = find_alias(str(mc), host)
    endpoints = discover_endpoints(host, port, scheme)
    endpoint = alias_url if alias_url else (endpoints[0][0] if endpoints else None)

    print("===== CDN PREFLIGHT (read-only discovery) =====")
    print(f"host: {host}")
    print(f"mc: {mc}")
    print(f"alias: {alias or '<none>'}")
    print(f"alias endpoint: {alias_url or '<none>'}")
    if endpoints:
        print("probed S3 endpoint(s):")
        for item, server in endpoints:
            print(f"  {item} [{server or 'MinIO'}]")
    else:
        print("probed S3 endpoint: none")

    if endpoint:
        hosts[host] = {
            "verified": True,
            "alias": alias,
            "endpoint": endpoint,
            "last_verified": datetime.now(timezone.utc).isoformat(),
        }
        write_kind("runtime", runtime)
        write_kind("state", state)
        print("cache: 已写入 .local；下次先直接复用")
        return 0

    write_kind("runtime", runtime)
    hosts[host] = {
        "verified": False,
        "reason": "no matching alias or S3 endpoint discovered",
        "retry": "when-network-or-config-changes",
        "last_verified": datetime.now(timezone.utc).isoformat(),
    }
    write_kind("state", state)
    print("result: 未确认 S3 endpoint；向用户确认真实 endpoint 后再配置 alias")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
