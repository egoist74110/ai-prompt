# Runtime / Local State Policy

Load this file only when the task needs runtime-registry operations, machine-specific discovery, shared local capability state, headless runtime selection, bootstrap/doctor/sync work, or equivalent runtime facts. Do not load it for ordinary Q&A or when current-session facts and a matching Skill already provide everything required.

## Root / Local State

- `AI_PROMPT_ROOT` = directory containing `router.md`. Resolve repository-relative paths from it; never assume a machine-specific home path.
- `.local/runtime.json`: machine facts such as OS, paths, runtime registry, capability locators, and credential locators.
- `.local/state.json`: verified experience such as availability, strategy, failures, and retry/invalidation conditions.
- Never commit `.local/` or store secret contents there; store credential locators only.
- If `.local/` is required but absent and Python is available, run `python tools/runtime_state.py init` (`python3` if required).

## Runtime Registry

Runtime names are local data, not central constants.

- `config/runtime-templates.json` is bootstrap data only; `.local/runtime.json.runtimes` is authoritative after initialization.
- Bootstrap, doctor, Skill sync, review, and other runtime consumers MUST iterate the registry. Never add product-name branches to central code.
- Users may register arbitrary runtimes; central Python must not require edits for each new runtime.
- Full schema: `config/README.md`.

## Fact Priority

Stop at the first sufficient layer:

1. current-session execution facts;
2. verified `.local/runtime.json` / `.local/state.json` facts, including valid `blocked`, `cooldown`, and `unsupported` state;
3. exposed tools are candidates only, not proof that they should be retried;
4. discover/probe only if earlier layers cannot resolve the need or cached state requires retry.

After successful discovery, cache machine locators/config in runtime and verified strategy/result/retry state in state. Current execution overrides stale cache, but merely exposing a previously blocked tool does not invalidate its retry condition.

Before installing/enabling a plugin, MCP, connector, or expanded permission, explain reason/impact and obtain confirmation.
