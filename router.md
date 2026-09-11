# AI Prompt Router

Lightweight entry point for all AI agents and model runtimes.

## Root

`AI_PROMPT_ROOT` is the directory containing this file. Resolve repository paths from it; never assume machine-specific home paths.

## Progressive Loading

Always begin with the lightest sufficient route. Read `common.md` first, then load only what the current request needs.

- Do not preload `models/high.md`, Skills, or capabilities.
- Route by user intent, not keywords. Mentioning code does not make a task Engineering.
- Reuse still-current prompt material already loaded in this session; do not reread it mechanically.
- Re-evaluate when intent changes. Load heavier workflow only when the current route lacks required guarantees.
- Never under-route an explicit request merely to save tokens.

## Routes

### Direct

Use for ordinary Q&A, explanation, summarization, translation, brainstorming, simple code/API/syntax questions, and other work needing no specialized workflow or repository/project engineering guarantees.

Do **not** load `models/high.md` for Direct requests. Add only capabilities the task actually needs.

### Skill-first

Use when the user names a Skill or the request clearly matches Skill metadata.

- If central Skill metadata is not already exposed, read `capabilities/skills.md` once.
- Load only matching `skills/<name>/SKILL.md` files.
- A matching Skill does not by itself require `models/high.md`; commands or requested output artifacts may remain Skill-first.
- If the underlying task is repository/project engineering, use Engineering and add the Skill there.

### Engineering

Use for repository/project implementation, code/config changes, project debugging, architecture/refactoring, code review, build/deploy changes, or substantial repository analysis/planning.

- Read `models/high.md`.
- If central Skill metadata is not already exposed, read `capabilities/skills.md` once before planning so relevant canonical Skills can be matched.
- Load only matching Skills.
- Code-related subject matter alone is not enough to select this route.

### Scout

If this execution is delegated only for context collection, repository scouting, or low-risk mechanical work, read `models/scout.md` instead of `models/high.md`. The primary Engineering agent owns decisions and acceptance.

## Route Changes

Routes are per current intent, not permanent conversation labels.

- Direct -> Skill-first when a reusable specialized procedure is needed.
- Direct or Skill-first -> Engineering when project inspection, modification, debugging, review, or engineering guarantees become required.
- Engineering or Skill-first -> Direct when the new request is ordinary Q&A. Already-loaded material may remain available, but Engineering gates apply only to Engineering work currently in scope.
- Engineering adds capabilities only when triggered.
- Mixed requests may use the lightest sufficient route for each part.

## On-demand Capabilities

Load only when triggered:

- Skill discovery -> `capabilities/skills.md`;
- Skill maintenance/deployment -> `capabilities/skill-maintenance.md`;
- runtime registry/machine discovery/shared local state -> `capabilities/runtime.md`;
- MCP/tool discovery -> `capabilities/mcp.md`;
- search backend selection/fallback/failure -> `capabilities/search.md`;
- cross-review -> `capabilities/cross-review.md` via `models/high.md`;
- any route that starts task-owned processes, allocates ports, changes temporary config/permissions, or creates temporary/unrequested files -> `capabilities/cleanup.md` before the first such side effect; Engineering additionally applies its regression/delivery rules.

Do not bulk-read Skills or capabilities.

## Native Entrypoints

Runtime-specific entry files should stay thin:

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

Entrypoint paths may use runtime-supported variables or verified local paths. Central docs must not define fixed product-specific locations.
