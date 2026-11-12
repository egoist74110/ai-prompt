# Runtime / Local State Policy

Load this file only when the task needs runtime-registry operations, machine-specific discovery, shared local capability state, headless runtime selection, bootstrap/doctor/sync work, or equivalent runtime facts. Do not load it for ordinary Q&A or when current-session facts and a matching Skill already provide everything required.

## Root / Local State

- `AI_PROMPT_ROOT` = directory containing `router.md`. Resolve repository-relative paths from it; never assume a machine-specific home path.
- `.local/runtime.json`: machine facts such as OS, paths, runtime registry, capability locators, and credential locators.
- `.local/state.json`: verified experience such as availability, strategy, failures, and retry/invalidation conditions.
- `.local/prefs.json`: user preference entries only (e.g. `response_profile`), read every session; keep it tiny and never put runtime facts or experience there.
- Never commit `.local/` or store secret contents there; store credential locators only.
- Secret values live in the git-ignored local store `secrets/secrets.json` (indexed name + description + value). Manage it only via `python tools/secrets_store.py` (`python3`/`py` as available; the tool handles POSIX chmod and Windows icacls itself) (`list` / `set` / `get` / `describe` / `remove`); never pass a value on the command line, never echo values into chat/logs, and use `secrets:<name>` as the credential locator.
- If `.local/` is required but absent and Python is available, run `python tools/runtime_state.py init` (`python3` if required).

## Runtime Registry

Runtime names are local data, not central constants.

- `config/runtime-templates.json` is bootstrap data only; `.local/runtime.json.runtimes` is authoritative after initialization.
- Bootstrap, doctor, Skill sync, review, and other runtime consumers MUST iterate the registry. Never add product-name branches to central code.
- Users may register arbitrary runtimes; central Python must not require edits for each new runtime.
- Full schema: `config/README.md`.

## Dispatching To A Runtime CLI

For a worker on another runtime (or when the in-session agent tool cannot pin the model), launch that runtime's CLI from `.local/runtime.json` `runtimes.<id>.dispatch`:

- `read` (scout/test) or `write` (build/hotfix) is an argv template; substitute `{model}`, `{effort}`, `{prompt}` from the selected allowlist entry and the brief, and `{root}` with `AI_PROMPT_ROOT`; pass each item as one argument. Run from the task's working directory with stdin closed (`</dev/null`); obey its `notes`. `shell: false` means that CLI cannot run commands headless: never pick it for work that must run commands (tests, builds), and never bypass with a skip-all-permissions flag.
- No `dispatch` entry -> read that CLI's `--help` once, run a minimal read-only probe that proves the model and effort took effect, and record the verified template plus version in `dispatch`. An unverifiable model pin -> skip that candidate.
- Report the model/effort the CLI actually reported, not just the one requested.

## Fact Priority

Stop at the first sufficient layer:

1. current-session execution facts;
2. verified `.local/runtime.json` / `.local/state.json` facts, including valid `blocked`, `cooldown`, and `unsupported` state;
3. exposed tools are candidates only, not proof that they should be retried;
4. discover/probe only if earlier layers cannot resolve the need or cached state requires retry.

After successful discovery, cache machine locators/config in runtime and verified strategy/result/retry state in state. Current execution overrides stale cache, but merely exposing a previously blocked tool does not invalidate its retry condition.

Before installing/enabling a plugin, MCP, connector, or expanded permission, explain reason/impact and obtain confirmation.

## Native Entrypoints

Runtime-specific entry files should stay thin:

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

Entrypoint paths may use runtime-supported variables or verified local paths. Central docs must not define fixed product-specific locations.
