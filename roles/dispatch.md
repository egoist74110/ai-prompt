# Dispatch Protocol

Read before handing work to another session, subagent, or runtime as a role. Not a role itself. Paths are relative to `AI_PROMPT_ROOT`, the parent of `roles/`.

## Prompt

- First line: `role: <name>` (`lead`, `build`, `test`, `hotfix`, `review`, `scout`).
- Self-contained brief: goal, scope, acceptance checks, the Skills the worker must load (matching mandatory guardrails, e.g. `script-engineering`, plus any the user chose), and for `build`/`hotfix` the domain (`frontend`/`backend`) when it is clear.
- Cross-runtime mechanics (flags, sessions, model/effort options): `capabilities/runtime.md`.

## Model choice

Candidates come from `.local/prefs.json` `roles.<name>`: `models` is a list of `{runtime, model, effort}`; `"use": "<role>"` means take that role's entry instead. Pick in this order:

1. The user's explicit choice for this dispatch.
2. Domain: if the entry has `domains` and the piece is clearly one domain, take candidates whose `runtime` appears in `domains.<domain>`, in that list's order. This overrides step 3. Mixed frontend/backend work: split it into one piece per domain first; if it cannot be split, skip this step.
3. The candidate whose `runtime` is your own runtime, then the rest in `models` order.
4. Nothing configured -> your runtime's defaults.

A candidate that is out of quota, rate-limited, or unavailable -> try the next one. When every domain candidate fails, fall back to the remaining `models` of that role and say the domain preference could not be met.

## Report

For each dispatch, state the role and the runtime/model/effort that actually ran, and any fallback taken and why.
