# Web Search Backend Policy

Load this file when backend selection/fallback is needed. Model hosting and search-backend availability are separate facts: a cloud runtime may have no native search and may use an already verified MCP/CLI/fetch backend. If a cloud runtime has usable platform-native search, prefer it and skip this file unless fallback is needed.

Installed backends, command paths, MCP config, credential locators, provider endpoints, disable flags, and health state belong in `.local/runtime.json` / `.local/state.json`. Never store secrets or machine absolute paths here.

## 0. Entry gate

Follow `router.md` search routing:

Resolve hosting without making a search call: use verified `.local/runtime.json.search.contexts` first, then minimal runtime/config/process facts. A private/LAN endpoint indicates self-hosted hosting; a provider domain with an API key indicates cloud hosting. If hosting remains unknown, ask the user before searching.

1. Resolve the current search context from verified cache or minimal read-only discovery; never guess hosting.
2. Determine whether a usable platform-native search backend actually exists. Tool exposure alone is not proof of usability.
3. If native search is absent/unusable, select from verified configured backends regardless of model hosting.
4. Cache verified context/backend facts.

`cloud-native` and `local-managed` are backend-selection lanes, not a prohibition on fallback. Same-lane backends sort first. New cloud contexts may fall back to verified local-managed MCP/CLI/fetch backends by default; an explicit `allow_cross_lane_fallback=false` disables that behavior.

Legacy contexts keep any stored `allow_cross_lane_fallback` boolean exactly as written because the old schema cannot prove whether it was a default or a user choice. Never silently reinterpret a legacy `false` as `true`. If the user wants an existing context to adopt the current lane default, use the explicit migration command:

```text
python tools/search_state.py context-adopt-fallback-default <context-id>
```

## 1. Cache before discovery

Read in order:

1. `.local/runtime.json.search.contexts.<id>`
2. `.local/runtime.json.search.backends`
3. `.local/state.json.search.backends`
4. Skip `enabled=false`, `blocked`, active cooldown, and physically suppressed tools.
5. Prefer same-lane and current-context `preferred_backends`; then permitted cross-lane fallbacks.
6. Discover only on missing/stale cache; cache verified results immediately.

Persist blocked/cooldown/degraded state in `.local/state.json.search.backends`; persist verified locators, roles, and priority in `.local/runtime.json.search.backends`.

```text
python tools/search_state.py plan --context <context-id> [--role <role>]
```

Backends without declared `roles` may remain generic fallbacks for backward compatibility.

## 2. Cost and task selection

Escalate one level at a time; external calls spend user resources:

1. existing knowledge/fetched context sufficient -> no call;
2. known URL/structured fact -> direct fetch/free public API;
3. verified free search backend;
4. paid backend only when cheaper evidence is insufficient and the fact matters.

Prefer repository APIs for repo/release/tag/issue/PR/code facts, `general` for broad first-pass search, `accurate` for technical/fresh facts, `precise` for quoted/site-scoped queries, and `fetch`/`crawl`/`extract` for known URLs. Product/backend names are examples, never a fixed installation list.

## 3. Validate result quality

A successful request may still be a bad search. Check entity alignment, authoritative sources, topic pollution, freshness, backend degradation, and low relevance. Weak-but-working evidence is `degraded`, not permanently blocked. Rewrite the query or switch backend before forcing an answer.

## 4. Failure classes

- deterministic auth/config/permission/unsupported/subscription failures -> `blocked` until configuration changes;
- timeout/network/server/rate-limit/quota -> `cooldown`;
- weak results -> `degraded`;
- valid result -> `healthy`.

Persist these states with `tools/search_state.py`; do not repeatedly rediscover or retry a known hard failure.

## 5. Physical suppression is local/self-hosted only

Logical backend selection and runtime tool suppression are separate. A cloud context using a local-managed CLI fallback does **not** make the cloud runtime eligible for physical native-tool suppression.

For confirmed deterministic runtime-native search failures in a local/self-hosted session only, follow `capabilities/search-runtime-suppression.md`: disable only the failed search tool at the narrowest reversible scope, verify absence, and cache the suppression result. Never physically suppress transient failures.

## 6. MCP / wrapper fallback

If a wrapper fails, reuse a cached equivalent locator for the same backend or switch to the next verified backend. Discover only when no usable cached backend exists, then cache success/failure immediately.

**Rule:** choose search backends from verified capability facts rather than model hosting alone; preserve explicit/legacy fallback policy, and keep physical suppression limited to confirmed local/self-hosted runtime-native failures.
