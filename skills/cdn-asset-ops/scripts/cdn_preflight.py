#!/usr/bin/env python3
"""Read-only, versioned MinIO/S3 preflight cache."""
from __future__ import annotations
import argparse, os, re, shutil, ssl, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
SKILL_DIR=Path(__file__).resolve().parents[1]; ROOT=SKILL_DIR.parents[1]; TOOLS=ROOT/"tools"
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from local_state import migrate_local_files, read_kind, update_kind  # noqa: E402
SKILL="cdn-asset-ops"; CACHE_VERSION=2

def parse_host(value):
    raw=value.strip(); parsed=urlparse(raw if "://" in raw else f"//{raw}"); host=parsed.hostname
    if not host:raise ValueError(f"无法解析 host: {value}")
    try:port=parsed.port
    except ValueError:port=None
    return host.lower().rstrip("."),port,parsed.scheme or None
def endpoint_matches_host(endpoint,host):
    try:return (urlparse(str(endpoint)).hostname or "").lower().rstrip(".")==host.lower().rstrip(".")
    except ValueError:return False
def find_alias(mc,host):
    proc=subprocess.run([mc,"alias","ls"],text=True,capture_output=True)
    if proc.returncode!=0:return None,None
    current=None; wanted=host.lower().rstrip(".")
    for line in proc.stdout.splitlines():
        stripped=line.strip()
        if not stripped:continue
        if re.search(r"accesskey|secretkey",stripped,re.I):continue
        if not line[:1].isspace() and ":" not in stripped:current=stripped; continue
        match=re.match(r"URL\s*:\s*(\S+)",stripped,re.I)
        if match and endpoint_matches_host(match.group(1),wanted):return current,match.group(1)
    return None,None
def probe(endpoint):
    req=Request(endpoint.rstrip("/")+"/minio/health/live",method="HEAD",headers={"User-Agent":"ai-prompt-cdn-preflight/2"}); context=ssl.create_default_context()
    try:
        with urlopen(req,timeout=3,context=context) as response:
            server=response.headers.get("Server",""); return "minio" in server.lower() and "console" not in server.lower(),server
    except Exception:return False,""
def discover_endpoints(host,hinted_port,hinted_scheme):
    ports=([hinted_port] if hinted_port else [])+[9000,9001,9002,9003,9004,9005,80,443]; seen=set(); ports=[p for p in ports if not (p in seen or seen.add(p))]; schemes=([hinted_scheme] if hinted_scheme in {"http","https"} else [])+[s for s in ("http","https") if s!=hinted_scheme]; found=[]
    for scheme in schemes:
        for port in ports:
            endpoint=f"{scheme}://{host}:{port}"; ok,server=probe(endpoint)
            if ok:found.append((endpoint,server))
    return found
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("target"); parser.add_argument("--refresh",action="store_true"); args=parser.parse_args(); host,port,scheme=parse_host(args.target); migrate_local_files(); runtime=read_kind("runtime"); state=read_kind("state"); runtime_entry=runtime.setdefault("skills",{}).setdefault(SKILL,{}); hosts=state.setdefault("skills",{}).setdefault(SKILL,{}).setdefault("hosts",{}); cached=hosts.get(host,{})
    cache_valid=(cached.get("verified") is True and cached.get("verification_version")==CACHE_VERSION and endpoint_matches_host(cached.get("endpoint"),host))
    if cache_valid and not args.refresh:
        print("===== CDN PREFLIGHT (cached) ====="); print(f"host: {host}"); print(f"mc: {runtime_entry.get('mc','<unknown>')}"); print(f"alias: {cached.get('alias') or '<none>'}"); print(f"endpoint: {cached.get('endpoint') or '<unknown>'}"); print("cache: hit"); return 0
    if cached.get("verified") and not cache_valid and not args.refresh:print("cache: legacy/mismatched verification ignored; re-probing")
    mc=os.environ.get("MC_BIN","").strip() or runtime_entry.get("mc") or shutil.which("mc")
    if not mc or (not Path(mc).exists() and not shutil.which(str(mc))):print("mc: NOT installed / not found"); return 2
    alias,alias_url=find_alias(str(mc),host); alias_verified=False
    if alias_url:alias_verified,_=probe(alias_url)
    endpoints=discover_endpoints(host,port,scheme); endpoint=alias_url if alias_verified else (endpoints[0][0] if endpoints else None)
    print("===== CDN PREFLIGHT (read-only discovery) ====="); print(f"host: {host}"); print(f"mc: {mc}"); print(f"alias: {alias or '<none>'}"); print(f"alias endpoint: {alias_url or '<none>'}"); print(f"alias verified: {'yes' if alias_verified else 'no'}")
    def save_runtime(latest):latest.setdefault("skills",{}).setdefault(SKILL,{})["mc"]=str(mc)
    update_kind("runtime",save_runtime); stamp=datetime.now(timezone.utc).isoformat()
    if endpoint:
        def save_success(latest):latest.setdefault("skills",{}).setdefault(SKILL,{}).setdefault("hosts",{})[host]={"verified":True,"verification_version":CACHE_VERSION,"alias":alias if alias_verified else None,"endpoint":endpoint,"last_verified":stamp}
        update_kind("state",save_success); print("cache: verified endpoint stored"); return 0
    def save_failure(latest):latest.setdefault("skills",{}).setdefault(SKILL,{}).setdefault("hosts",{})[host]={"verified":False,"verification_version":CACHE_VERSION,"reason":"no verified matching alias or S3 endpoint discovered","retry":"when-network-or-config-changes","last_verified":stamp}
    update_kind("state",save_failure); print("result: no verified S3 endpoint"); return 3
if __name__=="__main__":raise SystemExit(main())
