# AI Prompt Router

This is the unified entry point for all AI agents and model runtimes. Any runtime that can read this file should enter the complete workflow through it.

## Root / Local State

Read these first.

- `AI_PROMPT_ROOT` is the directory containing this `router.md`.
- Resolve every relative path in this repository from `AI_PROMPT_ROOT`. Never rewrite paths by assuming a machine-specific user-directory prefix.
- `.local/runtime.json` records **how this machine operates**: OS, external absolute paths, executable locations, dynamic runtime registry, Skill/MCP/Search locators, credential locators, execution side, etc.
- `.local/state.json` records **what this machine has already verified**: Skill strategy, MCP/search/headless availability, API/network behavior, recent success/failure, and invalidation conditions.
- Neither file may be committed.
- If `.local/` does not exist and this environment can execute repository scripts, run `python tools/runtime_state.py init` (`python3` if only that command exists). Without Python, central rules remain readable, but local cache maintenance is unavailable.
- **Never store token/password/cookie/private-key contents in local state/runtime.** Store only a locator describing where credentials can be obtained.

## Runtime Registry Contract

Runtime names are **local data**, not constants in central code.

- `config/runtime-templates.json` is only a bootstrap starter template, not a permanent support list.
- Actual runtimes come from `.local/runtime.json.runtimes`.
- Bootstrap, doctor, Skill sync, cross-review, and other consumers MUST iterate the registry. Do not add product-name branches such as `if runtime == <product>`.
- Runtime entries may declare `command_candidates`, `entry_candidates`, `skills_candidates`, `capabilities`, `skills_sync_mode`, `review.args`, `review.priority`, etc.
- Users may register arbitrary runtimes. Adding a tool must not require modifying central Python:

```text
python tools/runtime_state.py runtime add <runtime-id> --commands-json '["<command>"]'
```

See `config/README.md` for the complete schema.

### Local Fact Priority

When a Skill, MCP, external API, headless runtime, or local tool is needed, use this priority order:

1. Facts produced by **actual execution in the current session**: successful/failed tool calls, command output, current environment variables.
2. Machine-specific configuration and verified experience in `.local/runtime.json` / `.local/state.json`.
3. A tool merely being exposed in the current session means only that a **candidate entry point exists**. It does not prove availability under the current provider/subscription/credentials and cannot override locally verified `blocked`, `cooldown`, or `unsupported` state.
4. Perform discovery/probing only when the first two layers cannot resolve the need or cached state meets its invalidation/retry condition.
5. After successful discovery:
   - executable/path/transport/endpoint/config location/credential locator -> `runtime.json`;
   - strategy/verified/result/failure/retry condition -> `state.json`.
6. Reuse cached facts afterward. If actual execution contradicts the cache, current output wins; refresh the cache instead of adding machine-specific exceptions to central docs.

See `config/README.md` for details.

## Local Search Contract

Before any search/external-information call, determine whether the current model is local/self-hosted. Stop as soon as one layer answers:

1. Read `.local/runtime.json.search.contexts`; if it contains a verified `hosting`, use it.
2. If cache is missing/invalid, inspect only local sources such as environment variables, runtime configuration, and process environment. Infer hosting from the endpoint: LAN/private IP means self-hosted; cloud-provider domain plus API key means cloud.
3. If still unknown, ask the user. **Never guess.** The presence of a search tool, or intuition that the runtime is cloud, is not evidence. No external search call is allowed until hosting is determined.
4. Cache the result in `search.contexts` immediately so later sessions do not repeat discovery.

- **local / self-hosted** -> read and follow `capabilities/search.md`.
- **cloud** -> ignore `capabilities/search.md` and all local-search rules; use the platform's native search.

## Regression / Cleanup Contract

For any task that writes files, changes configuration, runs tests, starts a server/watcher/browser/MCP/worker, or generates build/debug artifacts, **cleanup is part of delivery**.

- Establish a minimal baseline before side effects: distinguish pre-existing dirty files/processes/ports from task-owned resources.
- Track temporary files, processes, ports, configuration changes, and other task-owned side effects while working. Do not reconstruct ownership by guesswork at the end.
- Before final delivery, the implementer MUST read and execute `capabilities/cleanup.md`.
- Order: regression -> diff/untracked inspection -> remove task-owned temporary files -> stop task-owned temporary processes -> restore temporary config/permissions -> post-cleanup smoke -> deliver.
- Clean task-owned side effects even after failure/interruption.
- Clean only task-owned resources. Never delete or terminate pre-existing user files/processes/ports.

A feature that works while leaving task-created garbage files or background processes is **not complete**.

## Read Order

1. Read `common.md` first.
2. When solving a complete problem directly, also read `models/high.md`.
3. When explicitly asked only to scout, collect context, list paths, quote source text, or perform mechanical execution, read only `models/scout.md`; do not read `models/high.md`.
4. When Skill/MCP functionality is needed, initially read only the relevant index/rules:
   - `capabilities/skills.md`
   - `capabilities/mcp.md`
   - `capabilities/cross-review.md` before cross-review at delivery time when triggered by `models/high.md`.
5. For web search/external information, first apply the Local Search Contract: local -> read `capabilities/search.md`; cloud -> ignore it and use platform search.
6. If an implementation task creates file/process/port/configuration side effects, read `capabilities/cleanup.md` before final delivery. Pure read-only Q&A does not load it.

## Capability Loading

- Do not bulk-read `skills/`, `<runtime-skills>`, or every external `SKILL.md`.
- Load a capability only when the user names it or the task clearly matches its indexed `description` / `Use for` metadata.
- Native/plugin tools exposed in the current session may be candidates when appropriate, but skip them when local state has already verified that capability as `blocked`, `cooldown`, or `unsupported`, unless its retry condition has been met.
- **Search has special routing:** cloud models do not load the local-search prompt; local models do.
- **Cleanup is a delivery gate, not an ordinary tool capability:** any implementation that creates side effects must execute it before final response, even if the feature already appears to work.
- Before installing/enabling/adding an MCP/plugin/connector or expanding permissions, explain the reason, command/configuration, and impact, then obtain user confirmation.
- After a capability works for the first time on a machine, store machine-specific locators in runtime and verified experience in state. Only cross-machine rules belong in central `SKILL.md` / capability docs.

## Skill Contract

`skills/` is the **single canonical source** for all custom Skills; `capabilities/skills.md` is the discovery index.

1. **Use existing canonical Skills directly.** Check the index first. If a Skill exists centrally, read `skills/<name>/SKILL.md`; do not maintain a second private copy in a runtime directory.
2. **New Skills must be synchronized.** A Skill created temporarily by a runtime must be moved into `AI_PROMPT_ROOT/skills/<name>/` in the same task, then the index must be regenerated. The task is incomplete until synchronization finishes.
3. **Update the canonical copy.** If a central Skill already exists, modify it directly. Remove or link obsolete private copies to avoid forks.
4. **Frontmatter is the single metadata source.** After adding/deleting/renaming a Skill or changing its description, run `tools/gen-index.py`. Do not manually maintain machine paths or duplicate metadata in `capabilities/skills.md`.
5. **Resolve paths inside a Skill relative to that Skill.** Do not depend on cwd or assume runtime-specific home/user directories.
6. **Runtime Skill layout is a machine fact.** It may use a directory symlink, per-Skill symlinks, junctions, real directories, or no Skill support. Use registry declarations plus actual verification.
7. **Trust execution, not inference.** Refresh cached state when it disagrees with reality. `tools/doctor.py` is the canonical cross-platform health check; `doctor.sh` is only a compatibility wrapper.

## Native Entrypoints

Different AI tools read different private directories, project-level files, or global entry settings. Entrypoints should remain thin and only instruct the runtime to read the `router.md` at the current deployment location:

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

An entry file may use that runtime's supported home/environment variables or the current verified absolute path, but the central repository must not define a fixed product-specific entry location. Candidate entrypoints come from the runtime registry; after first verification, cache the actual path in `.local/runtime.json`.
