# AI Prompt Router

Unified entry point for all AI agents and model runtimes.

## Root / Local State

- `AI_PROMPT_ROOT` = directory containing this file. Resolve repository-relative paths from it; never assume a machine-specific home path.
- `.local/runtime.json`: machine facts (OS, paths, runtime registry, capability/credential locators).
- `.local/state.json`: verified experience (availability, strategy, failures, retry/invalidation conditions).
- Never commit `.local/` or store secret contents there; store credential locators only.
- If `.local/` is absent and Python is available, run `python tools/runtime_state.py init` (`python3` if required).

## Runtime Registry

Runtime names are local data, not central constants.

- `config/runtime-templates.json` is bootstrap data only; `.local/runtime.json.runtimes` is authoritative after initialization.
- Bootstrap, doctor, Skill sync, review, and other consumers MUST iterate the registry. Never add product-name branches to central code.
- Users may register arbitrary runtimes; central Python must not require edits for each new runtime.
- Full schema: `config/README.md`.

### Fact Priority

For Skills, MCP, search, APIs, headless runtimes, and local tools, stop at the first sufficient layer:

1. current-session execution facts;
2. verified `.local/runtime.json` / `.local/state.json` facts, including valid `blocked`, `cooldown`, and `unsupported` state;
3. exposed tools are candidates only, not proof that they should be retried;
4. discover/probe only if earlier layers cannot resolve the need or cached state requires retry.

After successful discovery, cache machine locators/config in runtime and verified strategy/result/retry state in state. Current execution overrides stale cache, but merely exposing a previously blocked tool does not invalidate its retry condition.

## Search Routing

Before external search, determine hosting and actual search availability without making a search call:

1. use verified `.local/runtime.json.search.contexts` if available;
2. otherwise inspect local runtime/config/process facts; private/LAN endpoint implies self-hosted, provider domain + API key implies cloud;
3. if hosting is still unknown, ask the user; never guess;
4. separately determine whether a usable platform-native search backend exists; tool exposure alone is not success;
5. cache verified facts.

- usable platform-native search -> prefer it;
- no usable native search -> use an already verified eligible MCP/CLI/fetch backend regardless of model hosting;
- read `capabilities/search.md` whenever backend selection, fallback, or search failure policy is needed.

Hosting and backend availability are independent. Same-lane backends are preferred, but cloud contexts may use verified configured fallbacks when native search is absent. Deterministic runtime-native search failures in local/self-hosted sessions alone may trigger `capabilities/search-runtime-suppression.md`.

## Read Order

1. Always read `common.md`.
2. Complete problem solving/implementation -> read `models/high.md`.
3. Scout/context collection/mechanical execution only -> read `models/scout.md`, not `models/high.md`.
4. If the current session does not already expose the central Skill metadata, read `capabilities/skills.md` once before planning implementation/review work; load only matching `skills/<name>/SKILL.md` files.
5. Load other capabilities only when triggered:
   - MCP/tool discovery -> `capabilities/mcp.md`;
   - cross-review -> `capabilities/cross-review.md` when triggered by `models/high.md`;
   - search strategy -> `capabilities/search.md` when required by the routing rules above;
   - any role that will create file/config/process/build/debug side effects -> read `capabilities/cleanup.md` before the first side effect and follow its applicable cleanup rules on success, failure, and early exit.

Do not bulk-read Skills/capabilities.

## Capability Rules

- Load a capability only when named by the user or clearly matched by its metadata/task trigger.
- Respect verified local `blocked`, `cooldown`, or `unsupported` state until its retry condition is met.
- Before installing/enabling a plugin, MCP, connector, or expanded permission, explain reason/impact and obtain confirmation.
- Cache machine-specific facts locally after first verification; keep only cross-machine rules in central docs.

## Skill Contract

`skills/` is canonical; `capabilities/skills.md` is only its discovery index.

- Use an existing canonical Skill directly; do not maintain runtime-private forks.
- Move newly created reusable Skills into `skills/<name>/` in the same task.
- Update the canonical copy when it exists.
- `SKILL.md` frontmatter is the metadata source of truth. Regenerate the index with `tools/gen-index.py` after add/delete/rename/description changes.
- Resolve Skill-internal paths relative to that Skill, not cwd or a runtime home path.
- Runtime Skill layout is machine-specific; use registry facts and verification.
- `tools/doctor.py` is the canonical cross-platform health check.

## Side Effects / Delivery

`capabilities/cleanup.md` is authoritative for ownership, regression scope, process/port/config cleanup, failure paths, and post-cleanup smoke. The trigger above applies to every role, not only implementers.

## Native Entrypoints

Runtime-specific entry files should stay thin:

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

Entrypoint paths may use runtime-supported variables or verified local paths. Central docs must not define fixed product-specific locations.
