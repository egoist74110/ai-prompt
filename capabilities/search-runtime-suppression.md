# Runtime-Native Search Suppression

Use this capability only when a local/self-hosted runtime exposes a search tool that is deterministically unusable but keeps steering the model to call it.

A prompt-level warning or `.local/state.json` `blocked` flag is insufficient if the runtime still injects the tool schema and related system instructions into every new session.

## 1. Two-layer disable

### Logical circuit breaker

Record in `.local/state.json`:

- `status=blocked|cooldown|degraded|healthy`
- failure class/reason
- retry condition

This decides whether policy may call the backend.

### Physical tool suppression

If the runtime supports reversible tool enable/disable, plugin toggles, profile overrides, tool filters, or equivalent configuration, disable the failed tool there as well.

This decides whether the model sees the obsolete tool in the next session.

For deterministic hard failures, both layers are required. `blocked` with a still-registered tool is incomplete suppression.

## 2. When physical suppression is required

Apply only to deterministic failures:

- required credential/key is confirmed missing and will not be configured now;
- the current account/subscription does not support the tool;
- runtime/provider configuration is absent;
- endpoint/provider is explicitly unsupported;
- the user explicitly requires that the tool no longer be used.

Do NOT physically suppress for timeout, transient network failure, 429/5xx, temporary provider unavailability, or poor result quality with a healthy transport. Use cooldown/degraded instead.

## 3. Recovery flow

```text
confirmed hard failure
→ mark backend blocked
→ check for reversible runtime tool disable/unregister
  ├─ supported
  │  → find the narrowest current profile/runtime scope
  │  → disable only the failed search tool
  │  → cache config locator + suppression strategy in runtime.json
  │  → reload/restart/start a new session
  │  → verify the tool is absent from the exposed tool schema
  │  → cache verified_absent=true
  └─ unsupported
     → keep blocked
     → cache suppression_status=unsupported
     → never call it proactively again
```

This is authorized search self-repair when the failure is deterministic and the change is minimal, reversible, and limited to that search tool. Ask the user before changes that expand permissions, disable unrelated capabilities, affect non-search behavior, or have unclear scope.

## 4. Local cache

Product-specific paths and config formats are machine facts. Store them locally, not in central prompts.

```json
{
  "search": {
    "contexts": {
      "<context-id>": {
        "native_tools": {
          "<tool-id>": {
            "backend": "<backend-id>",
            "policy": "disabled",
            "suppression": {
              "strategy": "runtime-config|tool-filter|plugin-toggle|profile-override|other",
              "config_locator": "<local non-secret locator>",
              "scope": "<profile/session/runtime>",
              "verified_absent": true,
              "requires_restart": true
            }
          }
        }
      }
    }
  }
}
```

`config_locator` may identify a local file or selector. Never store token/key contents.

Backend state remains in `.local/state.json`:

```json
{
  "search": {
    "backends": {
      "<backend-id>": {
        "status": "blocked",
        "reason_code": "missing-credential",
        "suppression_status": "verified",
        "retry": "when-config-changes"
      }
    }
  }
}
```

## 5. Verification

Physical suppression is complete only after checking the actual tool list after reload/new session.

Pass only if:

- the failed tool is no longer exposed;
- unrelated local search backends still work;
- required web/fetch/browser capabilities remain enabled;
- new search requests go directly to a local-managed backend without the known failed call.

If a runtime uses stable tool registration even when a provider is unavailable, missing credentials alone will not remove the schema; use the runtime's explicit disable/filter mechanism.

## 6. Prohibitions

- Do not merely report the error and retry it next session.
- Do not equate `tool exposed` with `tool healthy`.
- Do not disable an entire runtime to remove one search tool.
- Do not delete credentials or rewrite unrelated providers.
- Do not permanently suppress transient timeout/429/5xx failures.
- Do not hardcode product-specific config paths in central prompts; discover once and cache the machine-local locator.

**Rule:** `blocked` tells policy not to call a tool; physical suppression prevents the model from seeing it. Deterministically obsolete search tools require physical suppression when the runtime supports it.
