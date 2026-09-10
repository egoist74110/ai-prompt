# MCP Policy

MCP configuration remains runtime-owned. Central prompts store only portable usage rules, cross-machine integration principles, and verified service-specific behavior. Machine-specific installation state, commands, wrappers, transport, endpoints, authorization state, usernames, and absolute paths belong in `.local/runtime.json` / `.local/state.json`.

## Priority: session facts > local cache > discovery

Apply `router.md` Fact Priority before calling or probing MCP. In particular, a tool being exposed in the current session is only a candidate when a still-valid local `blocked`, `cooldown`, or `unsupported` record says not to retry it yet.

When MCP is needed, stop at the first sufficient level:

1. If current-session execution facts prove the exposed MCP tool usable and no valid suppression state blocks it, call it directly. Do not add, authenticate, or restart it.
2. Otherwise honor verified local state and its retry/invalidation condition. If it records a usable runtime/server and its locator/transport is still valid, perform only the minimum connection/start check.
3. If cache is absent/stale or its retry condition is met, inspect `<runtime> mcp list` or equivalent runtime configuration.
4. Configure a missing server only when necessary. Explain impact and obtain user approval before installation, authorization, or persistent config changes.
5. After first success, cache non-secret machine facts in `.local/`.

Recommended state shape:

```json
{"mcp":{"<runtime>":{"<server>":{"configured":true,"transport":"http|stdio","status":"verified","last_verified":"<time>"}}}}
```

Store command/wrapper/executable locators under `runtime.services.<server>`, never in central prompts.

`Needs authentication` does NOT automatically mean reauthorization is required. First inspect app/service login state, pending callbacks, and previous successful local authorization state. Do not invalidate an in-progress OAuth flow by generating a new URL every turn.

## HTTP field differences

| Runtime/config | HTTP URL field |
| --- | --- |
| Claude Code CLI | `--transport http` flag |
| Codex TOML | `url` |
| Gemini CLI / `agy` JSON | `serverUrl` |
| Antigravity IDE JSON | `serverUrl` |
| opencode JSON | `type: "remote"` + `url` |

Variable local endpoints are machine facts; discover and cache them.

## Known servers

### `lark`

Lark cloud documents and knowledge bases.

- OAuth refresh tokens rotate. Avoid multiple independent stdio processes sharing one refresh token.
- Prefer one shared HTTP instance; cache its endpoint/port locally after verification.
- The shared instance still needs single-flight refresh: only one refresh in flight, concurrent callers reuse the result.
- Require the app-side OAuth login to be complete and the app running.
- On `Needs authentication`, inspect existing login/authorization before reauthorizing.
- Probe the MCP endpoint for liveness. A 404/`Cannot GET` on `/` or `/health` alone does not prove failure.
- Use a stdio wrapper only for runtimes without HTTP transport; cache its absolute path locally.

Typical tools: `wiki_v2_space_getNode`, `docx_v1_document_rawContent`, `wiki_v1_node_search`, `docx_builtin_search`, `drive_v1_permissionMember_create`.

Wiki flow: `/wiki/<token>` → `wiki_v2_space_getNode` → `obj_token` → `docx_v1_document_rawContent`. A `/docx/<token>` URL may use its token directly.

Images require `docx.v1.documentBlock.list` + `drive.v1.media.batchGetTmpDownloadUrl`. If only an `image.png` placeholder is returned, inspect the runtime tool allowlist.

### `figma`

Figma design access through Framelink `figma-developer-mcp` (PAT + stdio).

- Static PATs do not rotate automatically, so separate stdio clients do not have the Lark refresh-token race.
- PAT/keyring and wrapper/Python paths are machine-local facts.
- A 403 from GET `/v1/me` alone does NOT prove the PAT invalid; file-read-only tokens may return 403 there.
- Official Dev Mode MCP may require a paid seat; third-party PAT access is a valid fallback when available.

Typical tools: `get_figma_data`, `download_figma_images`.

### `chrome-devtools`

Browser interaction, DOM inspection, console/network, and performance debugging.

Preferred command shape:

```text
npx -y chrome-devtools-mcp@latest --no-usage-statistics --isolated
```

- Prefer `--isolated` to avoid user Chrome profile locks and orphaned processes.
- Start only when the task requires it; clean up task-owned instances afterward. Never terminate the user's existing Chrome.
- Use `list_pages` / `select_page` before operating on a page.
- Use `--autoConnect` or `--browser-url=...` only when existing login state is required; choose it instead of isolated mode as appropriate.
- Prefer DOM/selectors/computed style/console/network for frontend debugging; screenshot only for visual facts.

### `ado-work-items` / `adoWorkItems`

Optional Azure DevOps work-item fallback.

- For `*.cg1alias.com` work items/PRs, prefer the `ado-pr` skill and its verified local PAT/CLI/REST strategy.
- Use this MCP only if `ado-pr` is unavailable on the current machine or the user explicitly requests MCP.
- Cache wrapper/Python locators under `runtime.services.ado-work-items`.

### `serena`

Semantic code/symbol navigation for unclear entry points, long call chains, or cross-file relationships.

Command shape:

```text
<serena-executable> start-mcp-server --context=claude-code --project-from-cwd --enable-web-dashboard=false --log-level=WARNING
```

Cache the actual executable locator locally. `--context` is a Serena enum, not the current runtime name; inspect `serena start-mcp-server --help` if uncertain.

Typical tools: `initial_instructions`, `activate_project`, `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, `find_declaration`, `get_diagnostics_for_file`.

Serena supplements source reading/testing; it does not replace them.

### `node_repl`

Persistent Node REPL for browser/script automation. If the runtime already exposes it and no valid suppression state blocks it, use it directly and do not duplicate configuration.

### Search MCPs

Search servers such as `wigolo`, `tavily`, `duckduckgo`, or `brave` are runtime-local. Follow `capabilities/search.md`; store installation state, commands, and credential locators in `.local/`.

## Cache after successful discovery

Cache non-secret facts: configured/verified status, runtime, transport, local endpoint, wrapper/executable locator, successful OAuth state, and required execution side/environment-variable locator.

Never cache access/refresh tokens, PATs, cookies, secret values, one-time OAuth codes, or task-only arguments.

If cached execution fails, trust current output and update failure/suppression state. Rediscover only when its retry/invalidation condition permits it or evidence shows the cached locator itself is stale. Do not add machine exceptions to central prompts.

## Runtime/plugin capabilities

GitHub, Browser, Chrome, Computer Use, Documents, Spreadsheets, Presentations, or similar tools exposed natively by the current runtime are session candidates. Apply router Fact Priority before use; do not install them merely because central documentation mentions them.
