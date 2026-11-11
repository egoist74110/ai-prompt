# Dispatch Protocol

Applies to every agent launch, including CLI and session tools.

## Launch gate

- High-tier families: Claude Fable, Claude Opus, and GPT Astra (e.g. `gpt-6-astra`), including versioned IDs and aliases. They may neither launch agents nor run as workers.
- Only a top-level, non-high-tier agent designated by the user or matched to `.local/prefs.json` `roles.lead` may launch agents. Delegated workers never launch agents, even if assigned `lead`.
- Launch only when the user asks or an authorized workflow requires delegation. Use the fewest workers needed and reuse existing workers for follow-ups.
- Verify both model identities. If ineligible, work directly when optional or hand off to an existing eligible dispatcher or the user. Never launch a dispatcher as a workaround.

## Prompt

- First line: `role: <name>` (`lead`, `build`, `test`, `hotfix`, `review`, `scout`).
- Self-contained brief: goal, scope, acceptance checks, Skills the worker must load (mandatory or user-selected), and the known `build`/`hotfix` domain.
- Cross-runtime mechanics (flags, sessions, model/effort options): `capabilities/runtime.md`.

## Model choice

Choose the role by the assigned work: implementation uses `build`; scouting uses `scout`. Never reclassify work to reach another model list.

The task role's `.local/prefs.json` `roles.<name>` `models` is a strict allowlist of `{runtime, model, effort}`. Resolve only explicit `"use": "<role>"` aliases. Exclude high-tier and unknown models. Rank eligible entries only:

1. The user's choice if it matches an eligible entry.
2. Domain: use `domains` to rank candidates by `runtime` in `domains.<domain>` order. This overrides step 3. Split mixed frontend/backend work by domain when possible; otherwise skip this step.
3. The candidate whose `runtime` is your own runtime, then the rest in `models` order.

Missing, empty, invalid, or exhausted list -> do optional work directly or report required delegation blocked.

Pass the selected model explicitly and use its configured effort. Skip tools that cannot pin the model. Never inherit the parent's model or use runtime defaults.

If out of quota, rate-limited, or unavailable, fall back to the remaining `models` on the same allowlist. Never switch roles or upgrade effort to bypass it.

## Report

For each dispatch, state the role and the runtime/model/effort that actually ran, and any fallback taken and why.
