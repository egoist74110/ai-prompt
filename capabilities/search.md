# Local / Self-Hosted Web Search Policy

> **LOCAL-ONLY CAPABILITY.** Load only for confirmed `local` / `self-hosted` models or APIs. If a cloud provider supplies native search, use that search and do not load this file.

This file defines portable local-search policy only. Installed backends, command paths, MCP config, credential locators, provider endpoints, disable flags, and health state belong in `.local/runtime.json` / `.local/state.json`. Never store secrets or machine absolute paths here.

## 0. Entry gate

Follow `router.md` Local Search Contract Step 0:

1. Check cached `search.contexts`.
2. If absent, perform minimal read-only discovery. Treat LAN/private-IP endpoints as self-hosted; cloud vendor endpoint + API key as cloud.
3. If still ambiguous, ask the user. NEVER guess.
4. Cache the resolved context.

Continue only when hosting is confirmed `local`/`self-hosted`, the endpoint is confirmed local/self-hosted, or `.local/runtime.json.search.contexts.<id>.lane=local-managed`.

A runtime-exposed `web_search`, browser, or provider-native search tool is NOT proof that the tool is usable or belongs to the local-search lane.

## 1. Cache before discovery

Read in order:

1. `.local/runtime.json.search.contexts.<id>`
2. `.local/runtime.json.search.backends`
3. `.local/state.json.search.backends`
4. Skip `enabled=false`, `blocked`, active cooldown, and non-`local-managed` backends.
5. Prefer current-context `preferred_backends`.
6. Discover only on missing/stale cache; cache verified results immediately.

Persist blocked/cooldown/degraded state in `.local/state.json.search.backends`; persist verified locators, roles, and priority in `.local/runtime.json.search.backends`.

```text
python tools/search_state.py plan --context <context-id>
python tools/search_state.py plan --context <context-id> --role repo
python tools/search_state.py plan --context <context-id> --role general
python tools/search_state.py plan --context <context-id> --role accurate
python tools/search_state.py plan --context <context-id> --role precise
python tools/search_state.py plan --context <context-id> --role fetch
```

Backends without declared `roles` may remain generic fallbacks for backward compatibility.

## 1.5 Cost ladder

Escalate one level at a time; external calls spend user resources.

1. **L0 Direct answer:** existing knowledge + fetched context is sufficient → no external call.
2. **L1 Free direct fetch:** known URL or structured fact such as weather/version/release/exchange rate → use direct fetch or a free public API.
3. **L2 Free search:** if search is necessary, use a free local-managed backend; query one fact at a time.
4. **L3 Paid last resort:** use a paid backend only after free options returned empty, irrelevant, or stale results and the fact matters. Briefly state why escalation was needed.

Do not repeat paid calls for the same small fact. If free search fails and paid search is unavailable, answer from available evidence and disclose uncertainty.

## 2. Select backend by task

- **repo/release/tag/issue/PR/code:** use `repo`/`code`; prefer official GitHub data over general search.
- **general web:** use `general` for broad low-cost first-pass candidates.
- **technical/version/date/price/freshness:** use or escalate to `accurate`, but the cost ladder still applies.
- **`site:`/exact phrase/freshness:** use `precise`.
- **known URL:** use `fetch`/`crawl`/`extract`; do not search for the URL again.

Example role mapping:

| Backend class | Roles | Typical use |
|---|---|---|
| GitHub API / `gh` | `repo`, `code`, `precise` | repositories, releases, tags, issues, PRs, code |
| aggregator | `general`, `fetch` | first-pass web search, crawl/extract |
| high-accuracy search | `accurate`, `research`, `fetch` | technical/fresh/high-accuracy second pass |
| precise search | `precise`, `general` | `site:`, quoted phrases, freshness, fallback |
| other free search | `general`, `fallback` | general fallback |
| internal/self-hosted | capability-dependent | user-managed search |

Product names are examples, never a fixed installation list.

## 3. A successful request may still be a bad search

Validate every result set:

1. **Entity alignment:** top results mention the target entity/project or a clear synonym.
2. **Source quality:** prefer official sites, repositories, releases, and vendor docs for technical facts.
3. **Topic pollution:** unrelated languages, localhost pages, random mirrors, or same-name products indicate weakness.
4. **Time alignment:** fresh/version/price/date questions need current dated evidence.
5. **Backend degradation:** `degraded=true` or degraded engine pools invalidate nominal success.
6. **Relevance score:** zero/very low lexical or entity alignment indicates weakness.

Mark weak-but-working backends `degraded`, not permanently blocked:

```text
python tools/search_state.py fail <backend-id> --class quality --reason "top results irrelevant / SEO-heavy / degraded"
```

## 4. Two-pass search

### First pass

- Query one fact at a time.
- Avoid long open-ended sentences.
- Include exact product/project names for technical queries.
- Prefer repo backends for repository/release facts.

Split broad queries such as:

```text
TypeScript 7 native Go port release status performance roadmap
```

into focused queries:

```text
TypeScript 7 release
microsoft typescript-go releases
```

### Second pass

If first-pass evidence is weak, do NOT force an answer. Automatically:

1. quote the core entity;
2. add `site:` for an official domain;
3. add repository owner/name;
4. split multi-fact queries;
5. switch to `accurate` / `precise`;
6. fetch official source text when needed.

## 5. Failure classes and circuit breaker

### Deterministic failure → `blocked`

Missing key, 401/403, missing subscription/config, explicit unsupported:

```text
python tools/search_state.py fail <backend-id> --class missing-credential --reason "missing search credential"
```

Skip until configuration changes or state is reset.

### Transient failure → `cooldown`

Timeout, temporary network error, 5xx, 429:

```text
python tools/search_state.py fail <backend-id> --class timeout --reason "request timed out" --retry-after-minutes 15
```

Use the next backend during cooldown.

### Valid success → `healthy`

```text
python tools/search_state.py success <backend-id>
```

## 6. Deterministically broken runtime-native search must be physically suppressed

`blocked` may not stop runtimes with stable tool registration from injecting a broken tool schema/system prompt into every session.

For confirmed deterministic failures in local/self-hosted sessions:

```text
first real hard failure
→ mark backend blocked
→ if reversible runtime disable/unregister exists
   → disable only the failed search tool at the narrowest scope
   → cache suppression locator/strategy
   → reload/restart/new session
   → verify the tool is absent
   → cache verified_absent=true
→ otherwise cache suppression_status=unsupported and never call it proactively
```

This minimal, reversible, search-only repair is authorized automatically after deterministic failure. Ask before broader permission/config/capability changes. Never physically suppress transient timeout/429/5xx failures.

See `capabilities/search-runtime-suppression.md`.

## 7. MCP / wrapper / discovery

If an MCP/wrapper fails:

- reuse a cached equivalent CLI/command locator for the same backend;
- otherwise switch to the next verified backend;
- do not reinstall an existing capability merely because one wrapper failed.

Only discover when no local backend is available:

1. inspect local runtime/state;
2. inspect current runtime MCP config;
3. inspect PATH/known wrappers;
4. probe only the most likely one or two candidates;
5. cache locator + roles + priority + healthy immediately after success;
6. persist failures as blocked/cooldown.

First-time discovery may take detours. Subsequent sessions MUST NOT rediscover known keys, MCPs, script paths, or retry deterministically obsolete tools.

## 8. Execution summary

```text
need external information
→ cost ladder: direct answer / free direct fetch first
→ read context + backend cache + circuit breaker
→ filter blocked/cooldown/physically disabled native tools
→ choose local-managed backend by role
→ first pass
→ validate evidence quality
   ├─ good → healthy + answer
   └─ weak → degraded → rewrite query → second backend/pass
→ hard failure → blocked + physical suppression when supported
→ transient failure → cooldown
→ if all local-managed backends fail, report concrete failure reasons
```

**Rule:** local search means using verified local-managed backends, automatically retrying weak evidence with a better query/backend, and removing deterministically obsolete runtime-native search tools from model visibility when possible.
