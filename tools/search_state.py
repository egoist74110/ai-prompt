#!/usr/bin/env python3
"""Persistent search backend policy/circuit-breaker state."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timedelta,timezone
from typing import Any
from local_state import migrate_local_files,read_kind,update_kind
HARD_FAILURES={"auth","config","permission","unsupported","missing-credential","subscription"};TRANSIENT_FAILURES={"transient","timeout","network","server","rate-limit","quota"};ALL_FAILURES=sorted(HARD_FAILURES|TRANSIENT_FAILURES|{"quality"});LANES={"cloud-native","local-managed"};BACKEND_LANES=LANES|{"both"};FALLBACK_POLICY_VERSION=2
def now():return datetime.now(timezone.utc)
def iso(dt=None):return(dt or now()).isoformat()
def parse_iso(v):
    if not v:return None
    try:return datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError:return None
def derive_lane(h):return "cloud-native" if h=="cloud" else("local-managed" if h in {"local","self-hosted"} else None)
def infer_backend_lane(c):
    e=c.get("lane")
    if e in BACKEND_LANES:return str(e)
    return "cloud-native" if str(c.get("kind","")) in {"native","runtime-native","session-native"} else "local-managed"
def backend_roles(c):
    r=c.get("roles",[]);return[str(x) for x in r if isinstance(x,str)]if isinstance(r,list)else[]
def role_rank(r,q):
    if not q:return 0
    if q in r:return 0
    if not r:return 1
    return 2 if "fallback" in r else None
def backend_state(s,b):return s.setdefault("search",{}).setdefault("backends",{}).setdefault(b,{})
def mark_failure(s,b,c,reason,retry_after_minutes=None):
    e=backend_state(s,b);e.update(failure_count=int(e.get("failure_count",0))+1,last_failure=iso(),reason_code=c,reason=reason)
    if c in HARD_FAILURES:e.update(verified=False,status="blocked",retry="when-config-changes",retry_at=None)
    elif c in TRANSIENT_FAILURES:
        m=retry_after_minutes if retry_after_minutes is not None else(60 if c in {"rate-limit","quota"}else 15);e.update(verified=False,status="cooldown",retry="after-cooldown",retry_at=iso(now()+timedelta(minutes=max(1,m))))
    else:e.update(verified=True,status="degraded",last_success=e.get("last_success")or iso(),retry="next-query-or-other-backend",retry_at=None)
    return e
def mark_success(s,b):
    e=backend_state(s,b);e.update(verified=True,status="healthy",last_success=iso(),reason_code=None,reason=None,retry=None,retry_at=None,failure_count=0);return e
def reset_backend(s,b):return s.setdefault("search",{}).setdefault("backends",{}).pop(b,None)is not None
def set_context(runtime,context_id,*,runtime_id,provider,model,hosting,lane,endpoint,preferred_backends,allow_cross_lane_fallback):
    e=runtime.setdefault("search",{}).setdefault("contexts",{}).setdefault(context_id,{});resolved=lane or derive_lane(hosting)
    for k,v in {"runtime":runtime_id,"provider":provider,"model":model,"hosting":hosting,"lane":resolved,"endpoint":endpoint}.items():
        if v is not None:e[k]=v
    if preferred_backends is not None:e["preferred_backends"]=preferred_backends
    if allow_cross_lane_fallback is not None:e["allow_cross_lane_fallback"]=allow_cross_lane_fallback;e["cross_lane_explicit"]=True
    elif not e.get("cross_lane_explicit"):
        # Values written before policy v2 were defaults, not user intent.
        e["allow_cross_lane_fallback"]=resolved=="cloud-native"
    e["fallback_policy_version"]=FALLBACK_POLICY_VERSION
    if resolved=="local-managed":e["native_search_policy"]="deny"
    elif resolved=="cloud-native":e["native_search_policy"]="allow"
    e["last_updated"]=iso();return e
def is_blocked(e):
    if e.get("status")=="blocked":return True,"blocked-until-config-change"
    if e.get("status")=="cooldown":
        r=parse_iso(e.get("retry_at"))
        if r and r>now():return True,f"cooldown-until-{e.get('retry_at')}"
    return False,None
def _allow_cross(context,lane):
    if context.get("cross_lane_explicit"):return bool(context.get("allow_cross_lane_fallback"))
    # Legacy false was previously auto-written for every context; migrate behavior
    # logically even before context-set rewrites the cache.
    return lane=="cloud-native"
def planned_backends(runtime,state,context_id,requested_role=None):
    sc=runtime.get("search",{});configured=sc.get("backends",{})if isinstance(sc,dict)else{};contexts=sc.get("contexts",{})if isinstance(sc,dict)else{};context=contexts.get(context_id,{})if isinstance(contexts,dict)else{}
    if not isinstance(context,dict):return[]
    lane=context.get("lane")or derive_lane(str(context.get("hosting","unknown")))
    if lane not in LANES:return[]
    allow_cross=_allow_cross(context,lane);preferred=context.get("preferred_backends",[])or[];pr={n:i for i,n in enumerate(preferred)};sb=state.get("search",{}).get("backends",{});rows=[]
    for name,cfg in configured.items():
        if not isinstance(cfg,dict)or cfg.get("enabled",True)is False:continue
        health=sb.get(name,{})if isinstance(sb,dict)else{};blocked,reason=is_blocked(health if isinstance(health,dict)else{})
        if blocked:continue
        bl=infer_backend_lane(cfg);match=bl in {lane,"both"}
        if not match and not allow_cross:continue
        roles=backend_roles(cfg);rr=role_rank(roles,requested_role)
        if rr is None:continue
        degraded=isinstance(health,dict)and health.get("status")=="degraded";rows.append({"backend":name,"lane":bl,"context_lane":lane,"cross_lane":not match,"roles":roles,"requested_role":requested_role,"role_rank":rr,"kind":cfg.get("kind"),"priority":int(cfg.get("priority",0)or 0),"preferred":name in pr,"status":health.get("status","unknown")if isinstance(health,dict)else"unknown","degraded":degraded,"block_reason":reason})
    rows.sort(key=lambda r:(1 if r["cross_lane"]else 0,r["role_rank"],0 if r["preferred"]else 1,pr.get(r["backend"],10**6),1 if r["degraded"]else 0,-r["priority"],r["backend"]));return rows
def json_list(v):
    p=json.loads(v)
    if not isinstance(p,list)or not all(isinstance(x,str)for x in p):raise ValueError("expected JSON array of strings")
    return p
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True);plan=sub.add_parser("plan");plan.add_argument("--context",required=True);plan.add_argument("--role");success=sub.add_parser("success");success.add_argument("backend");fail=sub.add_parser("fail");fail.add_argument("backend");fail.add_argument("--class",dest="failure_class",choices=ALL_FAILURES,required=True);fail.add_argument("--reason",required=True);fail.add_argument("--retry-after-minutes",type=int);reset=sub.add_parser("reset");reset.add_argument("backend");status=sub.add_parser("status");status.add_argument("backend",nargs="?");ctx=sub.add_parser("context-set");ctx.add_argument("context_id");ctx.add_argument("--runtime");ctx.add_argument("--provider");ctx.add_argument("--model");ctx.add_argument("--hosting",choices=["cloud","local","self-hosted","unknown"],required=True);ctx.add_argument("--lane",choices=sorted(LANES));ctx.add_argument("--endpoint");ctx.add_argument("--preferred-backends-json");ctx.add_argument("--allow-cross-lane-fallback",action=argparse.BooleanOptionalAction,default=None);a=p.parse_args();migrate_local_files()
    if a.cmd=="plan":
        r=read_kind("runtime");s=read_kind("state");contexts=r.get("search",{}).get("contexts",{})
        if a.context not in contexts:p.error(f"search context is not registered: {a.context}")
        rows=planned_backends(r,s,a.context,a.role);d=contexts.get(a.context,{});lane=d.get("lane")or derive_lane(d.get("hosting"))
        if lane not in LANES:p.error("search context has unknown hosting/lane; discover and cache it before searching")
        print(json.dumps(rows,ensure_ascii=False,indent=2));return 0
    if a.cmd=="success":h={};update_kind("state",lambda s:h.setdefault("r",dict(mark_success(s,a.backend))));print(json.dumps(h["r"],ensure_ascii=False,indent=2));return 0
    if a.cmd=="fail":h={};update_kind("state",lambda s:h.setdefault("r",dict(mark_failure(s,a.backend,a.failure_class,a.reason,a.retry_after_minutes))));print(json.dumps(h["r"],ensure_ascii=False,indent=2));return 0
    if a.cmd=="reset":h={"c":False};update_kind("state",lambda s:h.update(c=reset_backend(s,a.backend)));return 0 if h["c"]else 2
    if a.cmd=="status":b=read_kind("state").get("search",{}).get("backends",{});print(json.dumps(b.get(a.backend,{})if a.backend else b,ensure_ascii=False,indent=2));return 0
    if a.cmd=="context-set":
        preferred=None
        if a.preferred_backends_json is not None:
            try:preferred=json_list(a.preferred_backends_json)
            except(json.JSONDecodeError,ValueError)as exc:p.error(str(exc))
        derived=derive_lane(a.hosting)
        if a.lane and derived and a.lane!=derived:p.error(f"lane {a.lane} conflicts with hosting {a.hosting}; expected {derived}")
        h={};update_kind("runtime",lambda r:h.setdefault("r",dict(set_context(r,a.context_id,runtime_id=a.runtime,provider=a.provider,model=a.model,hosting=a.hosting,lane=a.lane,endpoint=a.endpoint,preferred_backends=preferred,allow_cross_lane_fallback=a.allow_cross_lane_fallback))));print(json.dumps(h["r"],ensure_ascii=False,indent=2));return 0
    return 1
if __name__=="__main__":raise SystemExit(main())
