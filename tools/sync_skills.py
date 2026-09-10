#!/usr/bin/env python3
"""Sync central skills without claiming ownership of runtime-private resources."""
from __future__ import annotations
import argparse, os
from datetime import datetime, timezone
from pathlib import Path
from local_state import ROOT, migrate_local_files, read_kind, update_kind
from platform_fs import create_dir_link, is_junction, is_linkish, link_target, points_to, remove_linkish


def _expand(value: str) -> Path: return Path(os.path.expandvars(value)).expanduser()
def _norm(path: Path) -> str: return str(path.expanduser().resolve(strict=False))
def resolve_target(entry: dict) -> Path | None:
    if entry.get("skills_path"): return _expand(str(entry["skills_path"]))
    candidates=entry.get("skills_candidates",[]) or []; return _expand(str(candidates[0])) if candidates else None

def _record(central: Path,target: Path,mode: str,managed: dict[str,str]|None=None,conflicts: list[str]|None=None,status: str="verified") -> dict:
    conflicts=sorted(conflicts or [])
    return {"verified":status=="verified" and not conflicts,"status":"partial" if conflicts else status,"central":_norm(central),"target":_norm(target),"mode":mode,"managed":managed or {},"conflicts":conflicts,"last_verified":datetime.now(timezone.utc).isoformat()}
def _previous_ownership(previous: dict,central: Path,target: Path,mode: str) -> dict[str,str]:
    if previous.get("central")!=_norm(central) or previous.get("target")!=_norm(target) or previous.get("mode")!=mode:return {}
    managed=previous.get("managed",{})
    return {str(k):str(v) for k,v in managed.items()} if isinstance(managed,dict) else {}

def sync_central_dir(runtime_name,entry,central,target):
    if points_to(target,central):
        print(f"{runtime_name}: central skills link is current"); return False,{},_record(central,target,"central-dir-link")
    if target.exists() or is_linkish(target): raise RuntimeError(f"{runtime_name}: {target} exists and is not the managed central-directory link; refusing to replace runtime-private data")
    target.parent.mkdir(parents=True,exist_ok=True); kind=create_dir_link(central,target); print(f"{runtime_name}: added central skills {kind}"); return True,{"skills_path":str(target),"skills_layout":"central-dir-link","link_kind":kind},_record(central,target,"central-dir-link")

def sync_per_skill(runtime_name,entry,central,target,previous):
    if not target.exists():
        if not entry.get("executable"):
            print(f"{runtime_name}: runtime not detected and skills directory is absent; skip")
            return False,{},_record(central,target,"per-skill-link",status="skipped")
        target.mkdir(parents=True,exist_ok=True)
    if not target.is_dir(): raise RuntimeError(f"{runtime_name}: skills target is not a directory: {target}")
    changed=False; link_kind=None; conflicts=[]; central_sources={p.name:p.resolve() for p in central.iterdir() if p.is_dir() and (p/"SKILL.md").is_file()}; owned=_previous_ownership(previous,central,target,"per-skill-link"); managed={}
    for name,source in sorted(central_sources.items()):
        dest=target/name
        if is_linkish(dest):
            current=link_target(dest)
            if current==source:
                managed[name]=_norm(source); link_kind=link_kind or ("junction" if is_junction(dest) else "symlink"); continue
            expected=owned.get(name)
            if expected and current is not None and _norm(current)==expected:
                remove_linkish(dest); link_kind=create_dir_link(source,dest); managed[name]=_norm(source); changed=True; print(f"{runtime_name}: updated managed {name}"); continue
            conflicts.append(name); print(f"{runtime_name}: preserve unmanaged/repointed link {name}; central skill not synced"); continue
        if dest.exists():
            conflicts.append(name); print(f"{runtime_name}: preserve unmanaged path {name}; central skill not synced"); continue
        link_kind=create_dir_link(source,dest); managed[name]=_norm(source); changed=True; print(f"{runtime_name}: added {name}")
    # Delete obsolete entries only when this exact target/central manifest owned the
    # name and the current link still points to the recorded source.
    for name,expected in sorted(owned.items()):
        if name in central_sources: continue
        dest=target/name
        if not is_linkish(dest): continue
        current=link_target(dest)
        if current is None or _norm(current)!=expected:
            print(f"{runtime_name}: preserve repointed obsolete link {name}"); continue
        remove_linkish(dest); changed=True; print(f"{runtime_name}: removed obsolete managed {name}")
    patch={"skills_path":str(target),"skills_layout":"per-skill-link","link_kind":link_kind or entry.get("link_kind")}; record=_record(central,target,"per-skill-link",managed,conflicts)
    if conflicts: print(f"{runtime_name}: skills sync partial; conflicts: {', '.join(conflicts)}")
    else: print(f"{runtime_name}: skills sync complete" if changed else f"{runtime_name}: skills are current")
    return changed,patch,record

def _persist(runtime_name,runtime_patch,state_record):
    def patch_runtime(runtime):
        entries=runtime.setdefault("runtimes",{})
        if runtime_name not in entries: raise KeyError(runtime_name)
        entries[runtime_name].update(runtime_patch)
    def patch_state(state): state.setdefault("skills_sync",{})[runtime_name]=state_record
    update_kind("runtime",patch_runtime); update_kind("state",patch_state)
def sync(runtime_name):
    migrate_local_files(); runtime=read_kind("runtime"); state=read_kind("state"); entries=runtime.setdefault("runtimes",{})
    if runtime_name not in entries: raise KeyError(runtime_name)
    entry=entries[runtime_name]
    if not entry.get("enabled",True): print(f"{runtime_name}: disabled, skip"); return 0
    mode=entry.get("skills_sync_mode","none")
    if mode in (None,"none"): print(f"{runtime_name}: no skills sync mode, skip"); return 0
    target=resolve_target(entry)
    if target is None: print(f"{runtime_name}: no skills path/candidates, skip"); return 0
    central=ROOT/"skills"
    if not central.is_dir(): raise RuntimeError(f"central skills directory missing: {central}")
    previous=state.get("skills_sync",{}).get(runtime_name,{})
    if not isinstance(previous,dict): previous={}
    if mode=="central-dir-link": _,patch,record=sync_central_dir(runtime_name,entry,central,target)
    elif mode=="per-skill-link": _,patch,record=sync_per_skill(runtime_name,entry,central,target,previous)
    else: raise RuntimeError(f"{runtime_name}: unsupported skills_sync_mode: {mode}")
    _persist(runtime_name,patch,record)
    return 2 if record.get("status")=="partial" else 0
def main():
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True); group.add_argument("--runtime"); group.add_argument("--all",action="store_true"); parser.add_argument("--auto-only",action="store_true"); args=parser.parse_args(); runtime=read_kind("runtime")
    names=[args.runtime] if args.runtime else [n for n,e in runtime.get("runtimes",{}).items() if isinstance(e,dict) and e.get("enabled",True) and e.get("skills_sync_mode") not in (None,"none") and (not args.auto_only or e.get("auto_sync_skills",False))]
    failed=False
    for name in names:
        try:
            code=sync(name); failed|=code!=0
        except KeyError: print(f"sync-skills: runtime not registered: {name}"); failed=True
        except Exception as exc: print(f"sync-skills: {name}: {exc}"); failed=True
    return 1 if failed else 0
if __name__=="__main__": raise SystemExit(main())
