#!/usr/bin/env python3
"""Persistent search backend policy/circuit-breaker state.

The main consumer is the local/self-hosted search policy in capabilities/search.md.
Configuration lives in .local/runtime.json; health/failure state lives in .local/state.json.
No secret values are stored here.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from local_state import migrate_local_files, read_kind, update_kind

HARD_FAILURES = {"auth", "config", "permission", "unsupported", "missing-credential", "subscription"}
TRANSIENT_FAILURES = {"transient", "timeout", "network", "server", "rate-limit", "quota"}
ALL_FAILURES = sorted(HARD_FAILURES | TRANSIENT_FAILURES | {"quality"})
LANES = {"cloud-native", "local-managed"}
BACKEND_LANES = LANES | {"both"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def derive_lane(hosting: str | None) -> str | None:
    if hosting == "cloud":
        return "cloud-native"
    if hosting in {"local", "self-hosted"}:
        return "local-managed"
    return None


def infer_backend_lane(cfg: dict[str, Any]) -> str:
    explicit = cfg.get("lane")
    if explicit in BACKEND_LANES:
        return str(explicit)
    kind = str(cfg.get("kind", ""))
    if kind in {"native", "runtime-native", "session-native"}:
        return "cloud-native"
    return "local-managed"


def backend_roles(cfg: dict[str, Any]) -> list[str]:
    raw = cfg.get("roles", [])
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if isinstance(x, str)]


def role_rank(roles: list[str], requested_role: str | None) -> int | None:
    if not requested_role:
        return 0
    if requested_role in roles:
        return 0
    if not roles:
        return 1
    if "fallback" in roles:
        return 2
    return None


def backend_state(state: dict[str, Any], backend: str) -> dict[str, Any]:
    return state.setdefault("search", {}).setdefault("backends", {}).setdefault(backend, {})


def mark_failure(state: dict[str, Any], backend: str, failure_class: str, reason: str, retry_after_minutes: int | None = None) -> dict[str, Any]:
    entry = backend_state(state, backend)
    entry["failure_count"] = int(entry.get("failure_count", 0)) + 1
    entry["last_failure"] = iso()
    entry["reason_code"] = failure_class
    entry["reason"] = reason
    if failure_class in HARD_FAILURES:
        entry.update({"verified": False, "status": "blocked", "retry": "when-config-changes", "retry_at": None})
    elif failure_class in TRANSIENT_FAILURES:
        minutes = retry_after_minutes if retry_after_minutes is not None else (60 if failure_class in {"rate-limit", "quota"} else 15)
        entry.update({"verified": False, "status": "cooldown", "retry": "after-cooldown", "retry_at": iso(now() + timedelta(minutes=max(1, minutes)))})
    else:
        entry.update({"verified": True, "status": "degraded", "last_success": entry.get("last_success") or iso(), "retry": "next-query-or-other-backend", "retry_at": None})
    return entry


def mark_success(state: dict[str, Any], backend: str) -> dict[str, Any]:
    entry = backend_state(state, backend)
    entry.update({"verified": True, "status": "healthy", "last_success": iso(), "reason_code": None, "reason": None, "retry": None, "retry_at": None, "failure_count": 0})
    return entry


def reset_backend(state: dict[str, Any], backend: str) -> bool:
    backends = state.setdefault("search", {}).setdefault("backends", {})
    return backends.pop(backend, None) is not None


def set_context(runtime: dict[str, Any], context_id: str, *, runtime_id: str | None, provider: str | None, model: str | None, hosting: str, lane: str | None, endpoint: str | None, preferred_backends: list[str] | None, allow_cross_lane_fallback: bool | None) -> dict[str, Any]:
    contexts = runtime.setdefault("search", {}).setdefault("contexts", {})
    entry = contexts.setdefault(context_id, {})
    resolved_lane = lane or derive_lane(hosting)
    for key, value in {"runtime": runtime_id, "provider": provider, "model": model, "hosting": hosting, "lane": resolved_lane, "endpoint": endpoint}.items():
        if value is not None:
            entry[key] = value
    if preferred_backends is not None:
        entry["preferred_backends"] = preferred_backends
    if allow_cross_lane_fallback is not None:
        entry["allow_cross_lane_fallback"] = allow_cross_lane_fallback
    elif "allow_cross_lane_fallback" not in entry:
        entry["allow_cross_lane_fallback"] = False
    if resolved_lane == "local-managed":
        entry["native_search_policy"] = "deny"
    elif resolved_lane == "cloud-native":
        entry["native_search_policy"] = "allow"
    entry["last_updated"] = iso()
    return entry


def is_blocked(entry: dict[str, Any]) -> tuple[bool, str | None]:
    status = entry.get("status")
    if status == "blocked":
        return True, "blocked-until-config-change"
    if status == "cooldown":
        retry_at = parse_iso(entry.get("retry_at"))
        if retry_at and retry_at > now():
            return True, f"cooldown-until-{entry.get('retry_at')}"
    return False, None


def planned_backends(runtime: dict[str, Any], state: dict[str, Any], context_id: str, requested_role: str | None = None) -> list[dict[str, Any]]:
    search_cfg = runtime.get("search", {})
    configured = search_cfg.get("backends", {}) if isinstance(search_cfg, dict) else {}
    contexts = search_cfg.get("contexts", {}) if isinstance(search_cfg, dict) else {}
    context = contexts.get(context_id, {}) if isinstance(contexts, dict) else {}
    if not isinstance(context, dict):
        return []
    hosting = str(context.get("hosting", "unknown"))
    lane = context.get("lane") or derive_lane(hosting)
    if lane not in LANES:
        return []
    allow_cross = bool(context.get("allow_cross_lane_fallback", False))
    preferred = context.get("preferred_backends", []) or []
    preferred_rank = {name: idx for idx, name in enumerate(preferred)}
    state_backends = state.get("search", {}).get("backends", {})
    rows: list[dict[str, Any]] = []
    for name, cfg in configured.items():
        if not isinstance(cfg, dict) or cfg.get("enabled", True) is False:
            continue
        health = state_backends.get(name, {}) if isinstance(state_backends, dict) else {}
        blocked, block_reason = is_blocked(health if isinstance(health, dict) else {})
        if blocked:
            continue
        backend_lane = infer_backend_lane(cfg)
        lane_match = backend_lane in {lane, "both"}
        if not lane_match and not allow_cross:
            continue
        roles = backend_roles(cfg)
        current_role_rank = role_rank(roles, requested_role)
        if current_role_rank is None:
            continue
        priority = int(cfg.get("priority", 0) or 0)
        degraded = isinstance(health, dict) and health.get("status") == "degraded"
        rows.append({"backend": name, "lane": backend_lane, "context_lane": lane, "cross_lane": not lane_match, "roles": roles, "requested_role": requested_role, "role_rank": current_role_rank, "kind": cfg.get("kind"), "priority": priority, "preferred": name in preferred_rank, "status": health.get("status", "unknown") if isinstance(health, dict) else "unknown", "degraded": degraded, "block_reason": block_reason})
    rows.sort(key=lambda row: (1 if row["cross_lane"] else 0, row["role_rank"], 0 if row["preferred"] else 1, preferred_rank.get(row["backend"], 10**6), 1 if row["degraded"] else 0, -row["priority"], row["backend"]))
    return rows


def json_list(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError("expected JSON array of strings")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="list eligible backends for one resolved search context")
    plan.add_argument("--context", required=True)
    plan.add_argument("--role", help="optional task role: repo/general/accurate/precise/fetch/code/research/... ")
    success = sub.add_parser("success"); success.add_argument("backend")
    fail = sub.add_parser("fail"); fail.add_argument("backend"); fail.add_argument("--class", dest="failure_class", choices=ALL_FAILURES, required=True); fail.add_argument("--reason", required=True); fail.add_argument("--retry-after-minutes", type=int)
    reset = sub.add_parser("reset"); reset.add_argument("backend")
    status = sub.add_parser("status"); status.add_argument("backend", nargs="?")
    context = sub.add_parser("context-set", help="cache model/provider hosting and search lane")
    context.add_argument("context_id"); context.add_argument("--runtime"); context.add_argument("--provider"); context.add_argument("--model"); context.add_argument("--hosting", choices=["cloud", "local", "self-hosted", "unknown"], required=True); context.add_argument("--lane", choices=sorted(LANES)); context.add_argument("--endpoint"); context.add_argument("--preferred-backends-json"); context.add_argument("--allow-cross-lane-fallback", action=argparse.BooleanOptionalAction, default=None)
    args = parser.parse_args()
    migrate_local_files()

    if args.cmd == "plan":
        runtime = read_kind("runtime"); state = read_kind("state")
        search_cfg = runtime.get("search", {}); contexts = search_cfg.get("contexts", {}) if isinstance(search_cfg, dict) else {}
        if args.context not in contexts: parser.error(f"search context is not registered: {args.context}")
        rows = planned_backends(runtime, state, args.context, requested_role=args.role)
        context_data = contexts.get(args.context, {}); hosting = context_data.get("hosting") if isinstance(context_data, dict) else None; lane = context_data.get("lane") if isinstance(context_data, dict) else None; lane = lane or derive_lane(hosting)
        if lane not in LANES: parser.error("search context has unknown hosting/lane; discover and cache it before searching")
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
    if args.cmd == "success":
        holder = {}; update_kind("state", lambda state: holder.setdefault("result", dict(mark_success(state, args.backend))))
        print(json.dumps(holder["result"], ensure_ascii=False, indent=2)); return 0
    if args.cmd == "fail":
        holder = {}; update_kind("state", lambda state: holder.setdefault("result", dict(mark_failure(state, args.backend, args.failure_class, args.reason, args.retry_after_minutes))))
        print(json.dumps(holder["result"], ensure_ascii=False, indent=2)); return 0
    if args.cmd == "reset":
        holder = {"changed": False}
        def do_reset(state: dict) -> None: holder["changed"] = reset_backend(state, args.backend)
        update_kind("state", do_reset); return 0 if holder["changed"] else 2
    if args.cmd == "status":
        state = read_kind("state"); backends = state.get("search", {}).get("backends", {}); payload = backends.get(args.backend, {}) if args.backend else backends
        print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
    if args.cmd == "context-set":
        preferred = None
        if args.preferred_backends_json is not None:
            try: preferred = json_list(args.preferred_backends_json)
            except (json.JSONDecodeError, ValueError) as exc: parser.error(str(exc))
        derived = derive_lane(args.hosting)
        if args.lane and derived and args.lane != derived: parser.error(f"lane {args.lane} conflicts with hosting {args.hosting}; expected {derived}")
        holder = {}
        def do_context(runtime: dict) -> None:
            holder["result"] = dict(set_context(runtime, args.context_id, runtime_id=args.runtime, provider=args.provider, model=args.model, hosting=args.hosting, lane=args.lane, endpoint=args.endpoint, preferred_backends=preferred, allow_cross_lane_fallback=args.allow_cross_lane_fallback))
        update_kind("runtime", do_context); print(json.dumps(holder["result"], ensure_ascii=False, indent=2)); return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
