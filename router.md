# AI Prompt Router

Unified lightweight entry point for all AI agents and model runtimes.

## Root

- `AI_PROMPT_ROOT` = directory containing this file. Resolve repository-relative paths from it; never assume a machine-specific home path.

## Progressive Loading

Always begin with the lightest sufficient route. Read `common.md` first, then load only the prompt material required by the current request.

- Do not preload `models/high.md`, Skills, or capabilities.
- Do not select a heavy route from topic keywords alone. A request can mention code without being an engineering task.
- Reuse prompt material already loaded in the current session when it is still current; do not reread it mechanically.
- Re-evaluate the route when user intent changes. Escalate only when the current route lacks required workflow or guarantees.
- A previous heavy turn does not make later lightweight requests engineering tasks automatically.
- Never under-route an explicit request merely to save tokens.

## Routes

### 1. Direct

Use for ordinary Q&A, explanation, summarization, translation, brainstorming, simple code/API/syntax questions, and other work that does not need a specialized workflow or repository/project engineering guarantees.

Load only `common.md` plus any capability that the task itself actually requires. Do **not** load `models/high.md` for Direct requests.

### 2. Skill-first

Use when the user names a Skill or the request clearly matches reusable Skill metadata.

- If central Skill metadata is not already exposed in the session, read `capabilities/skills.md` once for discovery.
- Load only the matching `skills/<name>/SKILL.md` file(s).
- A matching Skill does not by itself require `models/high.md`; Skill execution may run commands or create requested artifacts while remaining Skill-first.
- If the underlying task is repository/project engineering, use the Engineering route and add the matching Skill there instead.

### 3. Engineering

Use when the request needs repository/project engineering workflow or guarantees: implementation, code/config changes, project debugging, architecture/refactoring, code review, build/deploy changes, or substantial repository analysis/planning.

- Read `models/high.md`.
- Load Skill metadata and matching Skills only when relevant.
- Code-related subject matter alone is not enough to select this route.

### 4. Scout

If this execution is delegated only for context collection, repository scouting, or low-risk mechanical work, read `models/scout.md` instead of `models/high.md`. The primary Engineering agent remains responsible for decisions and acceptance.

## Escalation

Routes are per current intent, not permanent conversation labels.

- Direct -> Skill-first when a reusable specialized procedure is needed.
- Direct or Skill-first -> Engineering when the user asks for project inspection, modification, debugging, review, or engineering-level guarantees.
- Engineering adds capabilities only when their trigger becomes active.
- If a request mixes routes, use the lightest route that fully covers each required part; escalate only the parts that need it.

## On-demand Capabilities

Load only when triggered:

- Skill discovery -> `capabilities/skills.md`;
- Skill creation/update/rename/delete/deployment maintenance -> `capabilities/skill-maintenance.md`;
- runtime registry, machine discovery, or shared local runtime/state work -> `capabilities/runtime.md`;
- MCP/tool discovery -> `capabilities/mcp.md`;
- search backend selection, fallback, or failure handling -> `capabilities/search.md`;
- cross-review -> `capabilities/cross-review.md` as directed by `models/high.md`;
- Engineering side effects/regression/cleanup -> `capabilities/cleanup.md` as directed by `models/high.md`.

Do not bulk-read Skills or capabilities.

## Native Entrypoints

Runtime-specific entry files should stay thin:

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

Entrypoint paths may use runtime-supported variables or verified local paths. Central docs must not define fixed product-specific locations.
