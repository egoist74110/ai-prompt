#!/usr/bin/env python3
"""Persistent search backend policy/circuit-breaker state.

Configuration lives in .local/runtime.json; health/failure state lives in .local/state.json.
No secret values are stored here.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from local_state import migrate_local_files, read_kind, write_kind

HARD_FAILURES = {"auth", "config", "permission", "unsupported", "missing-credential", "subscription"}
TRANSIENT_FAILURES = {"transient", "timeout", "network", "server", "rate-limit", "quota"}
ALL_FAILURES = sorted(HARD_FAILURES | TRANSIENT_FAILURES | {"quality"})


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


def backend_state(state: dict[str, Any], backend: str) -> dict[str, Any]:
    return state.setdefault("search", {}).setdefault("backends", {}).setdefault(backend, {})


def mark_failure(
    state: dict[str, Any],
    backend: str,
    failure_class: str,
    reason: str,
    retry_after_minutes: int | None = None,
) -> dict[str, Any]:
    entry = backend_state(state, backend)
    entry["verified"] = False
    entry["failure_count"] = int(entry.get("failure_count", 0)) + 1
    entry["last_failure"] = iso()
    entry["reason_code"] = failure_class
    entry["reason"] = reason

    if failure_class in HARD_FAILURES:
        entry.update({"status": "blocked", "retry": "when-config-changes", "retry_at": None})
    elif failure_class in TRANSIENT_FAILURES:
        minutes = retry_after_minutes if retry_after_minutes is not None else (60 if failure_class in {"rate-limit", "quota"} else 15)
        entry.update(
            {
                "status": "cooldown",
                "retry": "after-cooldown",
                "retry_at": iso(now() + timedelta(minutes=max(1, minutes))),
            }
        )
    else:  # quality: backend worked, but results were weak; lower rank rather than hard-disable.
        entry.update({"status": "degraded", "retry": "next-query-or-other-backend", "retry_at": None})
    return entry


def mark_success(state: dict[str, Any], backend: str) -> dict[str, Any]:
    entry = backend_state(state, backend)
    entry.update(
        {
            "verified": True,
            "status": "healthy",
            "last_success": iso(),
            "reason_code": None,
            "reason": None,
            "retry": None,
            "retry_at": None,
            "failure_count": 0,
        }
    )
    return entry


def reset_backend(state: dict[str, Any], backend: str) -> bool:
    backends = state.setdefault("search", {}).setdefault("backends", {})
    return backends.pop(backend, None) is not None


def set_context(
    runtime: dict[str, Any],
    context_id: str,
    *,
    runtime_id: str | None,
    provider: str | None,
    model: str | None,
    hosting: str,
    endpoint: str | None,
    native_search_policy: str,
    preferred_backends: list[str] | None,
) -> dict[str, Any]:
    contexts = runtime.setdefault("search", {}).setdefault("contexts", {})
    entry = contexts.setdefault(context_id, {})
    for key, value in {
        "runtime": runtime_id,
        "provider": provider,
        "model": model,
        "hosting": hosting,
        "endpoint": endpoint,
        "native_search_policy": native_search_policy,
    }.items():
        if value is not None:
            entry[key] = value
    if preferred_backends is not None:
        entry["preferred_backends"] = preferred_backends
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


def planned_backends(runtime: dict[str, Any], state: dict[str, Any], context_id: str | None) -> list[dict[str, Any]]:
    search_cfg = runtime.get("search", {})
    configured = search_cfg.get("backends", {}) if isinstance(search_cfg, dict) else {}
    contexts = search_cfg.get("contexts", {}) if isinstance(search_cfg, dict) else {}
    context = contexts.get(context_id, {}) if context_id else {}
    preferred = context.get("preferred_backends", []) if isinstance(context, dict) else []
    preferred_rank = {name: idx for idx, name in enumerate(preferred)}
    hosting = context.get("hosting", "unknown") if isinstance(context, dict) else "unknown"
    native_policy = context.get("native_search_policy", "auto") if isinstance(context, dict) else "auto"
    state_backends = state.get("search", {}).get("backends", {})

    rows: list[dict[str, Any]] = []
    for name, cfg in configured.items():
        if not isinstance(cfg, dict) or cfg.get("enabled", True) is False:
            continue
        health = state_backends.get(name, {}) if isinstance(state_backends, dict) else {}
        blocked, block_reason = is_blocked(health if isinstance(health, dict) else {})
        if blocked:
            continue

        kind = str(cfg.get("kind", ""))
        is_native = kind in {"native", "runtime-native", "session-native"}
        if hosting in {"local", "self-hosted"} and is_native and native_policy == "deny":
            continue

        priority = int(cfg.get("priority", 0) or 0)
        degraded = isinstance(health, dict) and health.get("status") == "degraded"
        rows.append(
            {
                "backend": name,
                "kind": kind or None,
                "priority": priority,
                "preferred": name in preferred_rank,
                "status": health.get("status", "unknown") if isinstance(health, dict) else "unknown",
                "degraded": degraded,
                "block_reason": block_reason,
            }
        )

    rows.sort(
        key=lambda row: (
            0 if row["preferred"] else 1,
            preferred_rank.get(row["backend"], 10**6),
            1 if row["degraded"] else 0,
            -row["priority"],
            row["backend"],
        )
    )
    return rows


def json_list(value: str) -> list[str]:
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError("expected JSON array of strings")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="list configured eligible backends in execution order")
    plan.add_argument("--context")

    success = sub.add_parser("success")
    success.add_argument("backend")

    fail = sub.add_parser("fail")
    fail.add_argument("backend")
    fail.add_argument("--class", dest="failure_class", choices=ALL_FAILURES, required=True)
    fail.add_argument("--reason", required=True)
    fail.add_argument("--retry-after-minutes", type=int)

    reset = sub.add_parser("reset")
    reset.add_argument("backend")

    status = sub.add_parser("status")
    status.add_argument("backend", nargs="?")

    context = sub.add_parser("context-set", help="cache local/cloud model-provider facts")
    context.add_argument("context_id")
    context.add_argument("--runtime")
    context.add_argument("--provider")
    context.add_argument("--model")
    context.add_argument("--hosting", choices=["cloud", "local", "self-hosted", "unknown"], required=True)
    context.add_argument("--endpoint")
    context.add_argument("--native-search-policy", choices=["allow", "deny", "auto"], default="auto")
    context.add_argument("--preferred-backends-json")

    args = parser.parse_args()
    migrate_local_files()
    runtime = read_kind("runtime")
    state = read_kind("state")

    if args.cmd == "plan":
        print(json.dumps(planned_backends(runtime, state, args.context), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "success":
        result = mark_success(state, args.backend)
        write_kind("state", state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "fail":
        result = mark_failure(state, args.backend, args.failure_class, args.reason, args.retry_after_minutes)
        write_kind("state", state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "reset":
        changed = reset_backend(state, args.backend)
        if changed:
            write_kind("state", state)
        return 0 if changed else 2
    if args.cmd == "status":
        backends = state.get("search", {}).get("backends", {})
        payload = backends.get(args.backend, {}) if args.backend else backends
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "context-set":
        preferred = None
        if args.preferred_backends_json is not None:
            try:
                preferred = json_list(args.preferred_backends_json)
            except (json.JSONDecodeError, ValueError) as exc:
                parser.error(str(exc))
        result = set_context(
            runtime,
            args.context_id,
            runtime_id=args.runtime,
            provider=args.provider,
            model=args.model,
            hosting=args.hosting,
            endpoint=args.endpoint,
            native_search_policy=args.native_search_policy,
            preferred_backends=preferred,
        )
        write_kind("runtime", runtime)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
