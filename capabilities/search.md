# Web Search Backend Policy

Load this file when backend selection/fallback is needed. Model hosting and search-backend availability are separate facts: a cloud runtime may have no native search and may use an already verified MCP/CLI/fetch backend. If a cloud runtime has usable platform-native search, prefer it and skip this file unless fallback is needed.

Installed backends, command paths, MCP config, credential locators, provider endpoints, disable flags, and health state belong in `.local/runtime.json` / `.local/state.json`. Never store secrets or machine absolute paths here.

## 0. Entry gate

Follow `router.md` search routing:

1. Resolve the current search context from verified cache or minimal read-only discovery; never guess hosting.
2. Determine whether a usable platform-native search backend actually exists. Tool exposure alone is not proof of usability.
3. If native search is absent/unusable, select from verified configured backends regardless of model hosting.
4. Cache verified context/backend facts.

`cloud-native` and `local-managed` are backend-selection lanes, not a prohibition on fallback. Same-lane backends sort first. Cloud contexts may fall back to verified local-managed MCP/CLI/fetch backends; an explicit `allow_cross_lane_fallback=false` disables that behavior.

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

Select by role:

- repo/release/tag/issue/PR/code -> `repo` / `code`; prefer official repository data;
- broad web -> `general`;
- technical/version/date/price/freshness -> `accurate`;
- `site:` / exact phrase / freshness -> `precise`;
- known URL -> `fetch` / `crawl` / `extract`, not another search.

Do not repeat paid calls for the same small fact.

## 3. Validate results

A successful request may still be a bad search. Check:

1. entity/project alignment;
2. source authority;
3. topic pollution;
4. time alignment for freshness-sensitive facts;
5. backend degradation;
6. lexical/entity relevance.

Weak-but-working evidence is `degraded`, not permanently blocked.

## 4. Two-pass search

First pass: query one fact at a time, use exact entity names, and prefer repository backends for repository facts.

If evidence is weak, do not force an answer. Rewrite/narrow the query, add an official `site:` or repository identity when appropriate, switch role/backend, and fetch the authoritative source text when needed.

## 5. Failure classes and circuit breaker

Deterministic auth/config/permission/subscription/unsupported failures -> `blocked` until configuration changes.

Transient timeout/network/5xx/429/quota failures -> `cooldown` and use the next backend.

Valid success -> `healthy`. Quality failure -> `degraded`.

Use `tools/search_state.py fail|success|reset` to persist these facts.

## 6. Physical suppression is local/self-hosted only

Logical backend fallback applies to any hosting context. Physical removal of a broken runtime-native search tool is different and applies only to confirmed local/self-hosted sessions where the runtime supports a reversible narrow disable/unregister operation.

For a deterministic local runtime-native failure: mark blocked, disable only that failed search tool at the narrowest scope when supported, reload, verify absence, and cache the suppression fact. Never physically suppress transient failures. See `capabilities/search-runtime-suppression.md`.

## 7. MCP / wrapper / discovery

If a wrapper fails, reuse a cached equivalent CLI/locator for the same backend or move to the next verified backend. Do not reinstall an existing capability merely because one wrapper failed.

Discover only when no verified usable backend remains: inspect runtime/state, current MCP config, PATH/known wrappers, then probe only likely candidates. Cache successful locators and persist failures immediately.

## 8. Execution summary

```text
need external information
-> prefer usable platform-native search when present
-> otherwise read context + backend cache + circuit breaker
-> select same-lane backend first, then permitted verified fallback
-> execute focused first pass
-> validate evidence
   -> good: healthy + answer
   -> weak: degraded + rewrite/switch backend
-> hard failure: blocked
-> transient failure: cooldown
-> local runtime-native deterministic failure: optional physical suppression
-> if all eligible backends fail: report concrete failure reasons
```

**Rule:** hosting determines runtime behavior; verified backend availability determines how search is executed. Never infer one from the other.
