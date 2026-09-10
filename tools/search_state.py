#!/usr/bin/env python3
"""Persistent search backend policy/circuit-breaker state.

Search execution and backend availability are separate from model hosting. Cloud
contexts prefer cloud-native backends but may fall back to verified configured
backends; local/self-hosted physical tool suppression remains a separate policy.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, timedelta, timezone
from typing import Any
from local_state import migrate_local_files, read_kind, update_kind

HARD_FAILURES={"auth","config","permission","unsupported","missing-credential","subscription"}; TRANSIENT_FAILURES={"transient","timeout","network","server","rate-limit","quota"}; ALL_FAILURES=sorted(HARD_FAILURES|TRANSIENT_FAILURES|{"quality"}); LANES={"cloud-native","local-managed"}; BACKEND_LANES=LANES|{"both"}
def now(): return datetime.now(timezone.utc)
def iso(dt=None): return (dt or now()).isoformat()
def parse_iso(value):
    if not value:return None
    try:return datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:return None
def derive_lane(hosting):
    if hosting=="cloud":return "cloud-native"
    if hosting in {"local","self-hosted"}:return "local-managed"
    return None
def infer_backend_lane(cfg):
    explicit=cfg.get("lane")
    if explicit in BACKEND_LANES:return str(explicit)
    return "cloud-native" if str(cfg.get("kind","")) in {"native","runtime-native","session-native"} else "local-managed"
def backend_roles(cfg):
    raw=cfg.get("roles",[]); return [str(x) for x in raw if isinstance(x,str)] if isinstance(raw,list) else []
def role_rank(roles,requested_role):
    if not requested_role:return 0
    if requested_role in roles:return 0
    if not roles:return 1
    if "fallback" in roles:return 2
    return None
def backend_state(state,backend):return state.setdefault("search",{}).setdefault("backends",{}).setdefault(backend,{})
def mark_failure(state,backend,failure_class,reason,retry_after_minutes=None):
    entry=backend_state(state,backend); entry["failure_count"]=int(entry.get("failure_count",0))+1; entry["last_failure"]=iso(); entry["reason_code"]=failure_class; entry["reason"]=reason
    if failure_class in HARD_FAILURES:entry.update({"verified":False,"status":"blocked","retry":"when-config-changes","retry_at":None})
    elif failure_class in TRANSIENT_FAILURES:
        minutes=retry_after_minutes if retry_after_minutes is not None else (60 if failure_class in {"rate-limit","quota"} else 15); entry.update({"verified":False,"status":"cooldown","retry":"after-cooldown","retry_at":iso(now()+timedelta(minutes=max(1,minutes)))})
    else:entry.update({"verified":True,"status":"degraded","last_success":entry.get("last_success") or iso(),"retry":"next-query-or-other-backend","retry_at":None})
    return entry
def mark_success(state,backend):
    entry=backend_state(state,backend); entry.update({"verified":True,"status":"healthy","last_success":iso(),"reason_code":None,"reason":None,"retry":None,"retry_at":None,"failure_count":0}); return entry
def reset_backend(state,backend):return state.setdefault("search",{}).setdefault("backends",{}).pop(backend,None) is not None
def set_context(runtime,context_id,*,runtime_id,provider,model,hosting,lane,endpoint,preferred_backends,allow_cross_lane_fallback):
    entry=runtime.setdefault("search",{}).setdefault("contexts",{}).setdefault(context_id,{}); resolved_lane=lane or derive_lane(hosting)
    for key,value in {"runtime":runtime_id,"provider":provider,"model":model,"hosting":hosting,"lane":resolved_lane,"endpoint":endpoint}.items():
        if value is not None:entry[key]=value
    if preferred_backends is not None:entry["preferred_backends"]=preferred_backends
    if allow_cross_lane_fallback is not None:entry["allow_cross_lane_fallback"]=allow_cross_lane_fallback
    elif "allow_cross_lane_fallback" not in entry:
        # Cloud hosting does not imply native search exists. Native backends still sort
        # first; this permits configured MCP/CLI/fetch backends when native is absent.
        entry["allow_cross_lane_fallback"]=resolved_lane=="cloud-native"
    if resolved_lane=="local-managed":entry["native_search_policy"]="deny"
    elif resolved_lane=="cloud-native":entry["native_search_policy"]="allow"
    entry["last_updated"]=iso(); return entry
def is_blocked(entry):
    status=entry.get("status")
    if status=="blocked":return True,"blocked-until-config-change"
    if status=="cooldown":
        retry_at=parse_iso(entry.get("retry_at"))
        if retry_at and retry_at>now():return True,f"cooldown-until-{entry.get('retry_at')}"
    return False,None
def planned_backends(runtime,state,context_id,requested_role=None):
    search_cfg=runtime.get("search",{}); configured=search_cfg.get("backends",{}) if isinstance(search_cfg,dict) else {}; contexts=search_cfg.get("contexts",{}) if isinstance(search_cfg,dict) else {}; context=contexts.get(context_id,{}) if isinstance(contexts,dict) else {}
    if not isinstance(context,dict):return []
    hosting=str(context.get("hosting","unknown")); lane=context.get("lane") or derive_lane(hosting)
    if lane not in LANES:return []
    # Existing contexts created before this contract default cloud to cross-lane
    # fallback unless the user explicitly stored false.
    allow_cross=bool(context.get("allow_cross_lane_fallback", lane=="cloud-native")); preferred=context.get("preferred_backends",[]) or []; preferred_rank={name:i for i,name in enumerate(preferred)}; state_backends=state.get("search",{}).get("backends",{}); rows=[]
    for name,cfg in configured.items():
        if not isinstance(cfg,dict) or cfg.get("enabled",True) is False:continue
        health=state_backends.get(name,{}) if isinstance(state_backends,dict) else {}; blocked,block_reason=is_blocked(health if isinstance(health,dict) else {})
        if blocked:continue
        backend_lane=infer_backend_lane(cfg); lane_match=backend_lane in {lane,"both"}
        if not lane_match and not allow_cross:continue
        roles=backend_roles(cfg); rr=role_rank(roles,requested_role)
        if rr is None:continue
        priority=int(cfg.get("priority",0) or 0); degraded=isinstance(health,dict) and health.get("status")=="degraded"
        rows.append({"backend":name,"lane":backend_lane,"context_lane":lane,"cross_lane":not lane_match,"roles":roles,"requested_role":requested_role,"role_rank":rr,"kind":cfg.get("kind"),"priority":priority,"preferred":name in preferred_rank,"status":health.get("status","unknown") if isinstance(health,dict) else "unknown","degraded":degraded,"block_reason":block_reason})
    rows.sort(key=lambda r:(1 if r["cross_lane"] else 0,r["role_rank"],0 if r["preferred"] else 1,preferred_rank.get(r["backend"],10**6),1 if r["degraded"] else 0,-r["priority"],r["backend"])); return rows
def json_list(value):
    parsed=json.loads(value)
    if not isinstance(parsed,list) or not all(isinstance(x,str) for x in parsed):raise ValueError("expected JSON array of strings")
    return parsed

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd",required=True); plan=sub.add_parser("plan",help="list eligible backends for one resolved search context"); plan.add_argument("--context",required=True); plan.add_argument("--role")
    success=sub.add_parser("success"); success.add_argument("backend"); fail=sub.add_parser("fail"); fail.add_argument("backend"); fail.add_argument("--class",dest="failure_class",choices=ALL_FAILURES,required=True); fail.add_argument("--reason",required=True); fail.add_argument("--retry-after-minutes",type=int); reset=sub.add_parser("reset"); reset.add_argument("backend"); status=sub.add_parser("status"); status.add_argument("backend",nargs="?")
    context=sub.add_parser("context-set"); context.add_argument("context_id"); context.add_argument("--runtime"); context.add_argument("--provider"); context.add_argument("--model"); context.add_argument("--hosting",choices=["cloud","local","self-hosted","unknown"],required=True); context.add_argument("--lane",choices=sorted(LANES)); context.add_argument("--endpoint"); context.add_argument("--preferred-backends-json"); context.add_argument("--allow-cross-lane-fallback",action=argparse.BooleanOptionalAction,default=None); args=parser.parse_args(); migrate_local_files()
    if args.cmd=="plan":
        runtime=read_kind("runtime"); state=read_kind("state"); contexts=runtime.get("search",{}).get("contexts",{})
        if args.context not in contexts:parser.error(f"search context is not registered: {args.context}")
        rows=planned_backends(runtime,state,args.context,args.role); data=contexts.get(args.context,{}); lane=data.get("lane") or derive_lane(data.get("hosting"))
        if lane not in LANES:parser.error("search context has unknown hosting/lane; discover and cache it before searching")
        print(json.dumps(rows,ensure_ascii=False,indent=2)); return 0
    if args.cmd=="success":
        h={}; update_kind("state",lambda s:h.setdefault("result",dict(mark_success(s,args.backend)))); print(json.dumps(h["result"],ensure_ascii=False,indent=2)); return 0
    if args.cmd=="fail":
        h={}; update_kind("state",lambda s:h.setdefault("result",dict(mark_failure(s,args.backend,args.failure_class,args.reason,args.retry_after_minutes)))); print(json.dumps(h["result"],ensure_ascii=False,indent=2)); return 0
    if args.cmd=="reset":
        h={"changed":False}; update_kind("state",lambda s:h.update(changed=reset_backend(s,args.backend))); return 0 if h["changed"] else 2
    if args.cmd=="status":
        b=read_kind("state").get("search",{}).get("backends",{}); print(json.dumps(b.get(args.backend,{}) if args.backend else b,ensure_ascii=False,indent=2)); return 0
    if args.cmd=="context-set":
        preferred=None
        if args.preferred_backends_json is not None:
            try:preferred=json_list(args.preferred_backends_json)
            except (json.JSONDecodeError,ValueError) as exc:parser.error(str(exc))
        derived=derive_lane(args.hosting)
        if args.lane and derived and args.lane!=derived:parser.error(f"lane {args.lane} conflicts with hosting {args.hosting}; expected {derived}")
        h={}; update_kind("runtime",lambda r:h.setdefault("result",dict(set_context(r,args.context_id,runtime_id=args.runtime,provider=args.provider,model=args.model,hosting=args.hosting,lane=args.lane,endpoint=args.endpoint,preferred_backends=preferred,allow_cross_lane_fallback=args.allow_cross_lane_fallback)))); print(json.dumps(h["result"],ensure_ascii=False,indent=2)); return 0
    return 1
if __name__=="__main__":raise SystemExit(main())
