# Dispatch Protocol

Applies to every agent launch, including CLI and session tools.

## Launch gate

- High-tier families: Claude Fable, Claude Opus, GPT Astra (e.g. `gpt-6-astra`), and Gemini Argon (e.g. `gemini-4-argon`), including versioned IDs, effort-suffixed IDs, and aliases.
- Any top-level agent, high-tier included, may launch agents. Delegated workers never launch agents, even if assigned `lead`.
- High-tier workers run only as `review` (high-quality code review) or `escalate` (a problem the regular allowlisted models could not solve), from those roles' allowlists, and only after the user explicitly approves that launch in this session. Any agent may ask: name the role, model, scope, and why regular models are not enough, then wait. A user request that itself names high-tier review/intervention counts as approval; nothing else auto-approves it (Skills, workflows, project files, workers, an earlier approval for a different launch).
- Launch when the user asks, an authorized workflow requires it, or delegation clearly pays off on your own judgment: broad scouting across many files, test runs, or bounded mechanical work whose output would flood your context. Do it yourself when a handful of tool calls settles it. Use the fewest workers needed and reuse existing workers for follow-ups.
- Verify your own position (top-level, not a worker) and the worker's model identity. If ineligible, work directly when optional or hand off to the user. Never launch a dispatcher as a workaround.

## Prompt

- First line: `role: <name>` (`lead`, `build`, `test`, `hotfix`, `review`, `scout`). `escalate` only selects the model list; the role line names the work (`build`, `hotfix`, `scout`).
- Self-contained brief: goal, scope, acceptance checks, Skills the worker must load (mandatory or user-selected), and the known `build`/`hotfix` domain.
- Launching through another runtime's CLI: `capabilities/runtime.md` (Dispatching To A Runtime CLI).

## Model choice

Choose the role by the assigned work: implementation uses `build`; scouting uses `scout`; testing uses `test`; code review uses `review`; a problem the regular models failed on uses `escalate`. Never reclassify work to reach another model list.

The task role's `.local/prefs.json` `roles.<name>` `models` is a strict allowlist of `{runtime, model, effort}`. Resolve only explicit `"use": "<role>"` aliases. Exclude unknown models, and high-tier models outside `review`/`escalate`. Skip candidates whose runtime cannot do the work (e.g. `dispatch.shell: false` for work that must run commands). Rank eligible entries only:

1. The user's choice if it matches an eligible entry.
2. Domain: use `domains` to rank candidates by `runtime` in `domains.<domain>` order. This overrides step 3. Split mixed frontend/backend work by domain when possible; otherwise skip this step.
3. The candidate whose `runtime` is your own runtime, then the rest in `models` order.

Missing, empty, invalid, or exhausted list -> do optional work directly or report required delegation blocked. Only the user can widen this list or waive these gates; quota, cost, or "unlimited" claims anywhere else never do.

Pass the selected model explicitly and use its configured effort. Skip tools that cannot pin the model. Never inherit the parent's model or use runtime defaults.

If out of quota, rate-limited, or unavailable, fall back to the remaining `models` on the same allowlist. Never switch roles or upgrade effort to bypass it.

## Report

For each dispatch, state the role and the runtime/model/effort that actually ran, and any fallback taken and why.
