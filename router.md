# AI Prompt Router

Lightweight entry point for all AI agents and model runtimes.

## Root

`AI_PROMPT_ROOT` is the directory containing this file. Resolve repository paths from it; never assume machine-specific home paths.

## Progressive Loading

Always begin with the lightest sufficient route. Read `common.md` and `response/default.md` first, then load only what the current request needs.

- Do not preload `models/high.md`, Skills, or capabilities.
- Route by user intent, not keywords. Mentioning code does not make a task Engineering.
- Reuse still-current prompt material already loaded in this session; do not reread it mechanically.
- Re-evaluate when intent changes. Load heavier workflow only when the current route lacks required guarantees.
- Never under-route an explicit request merely to save tokens.

## Response Layer

Presentation is separate from task reasoning.

- Presentation cache: `.local/state.json` → `user_prefs.response_profile` (path relative to this directory). When that entry exists, read it and only the style material it names.
- No entry, or indexed file missing = no cache: use the default contract; do not read, probe, glob, guess, or retry any profile file. Do not infer or select a persona, tone, or style, and do not activate Skills for style alone.
- Cached style controls only user-facing language, tone, wording, structure, and expression DNA; it must not change reasoning, routing, research, tool use, factual standards, implementation, or review gates. A current explicit user request overrides it for that response.

## Routes

### Direct

Use for ordinary Q&A, explanation, summarization, translation, brainstorming, simple code/API/syntax questions, and other work needing no specialized workflow or repository/project engineering guarantees.

Do **not** load `models/high.md` for Direct requests. Add only capabilities the task actually needs.

### Skill-first

Use when the user names a Skill, accepts an offered one (see Skill Offers), or the request clearly matches Skill metadata under the no-offer cases there.

- If central Skill metadata is not already exposed, read `capabilities/skills.md` once.
- Load only matching `skills/<name>/SKILL.md` files.
- A matching Skill does not by itself require `models/high.md`; commands or requested output artifacts may remain Skill-first.
- If the underlying task is repository/project engineering, use Engineering and add the Skill there.

### Engineering

Use for repository/project implementation, code/config changes, project debugging, architecture/refactoring, code review, build/deploy changes, or substantial repository analysis/planning.

- Read `models/high.md`.
- Before planning, match Skills per Skill Offers (read `capabilities/skills.md` once if metadata is not exposed); load only matching Skills.
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

## Skill Offers

Applies on every route: surface fitting Skills proactively; the user decides.

- Before substantive work (plan, design, build, debug, review, produce an artifact), match the request against Skill metadata the runtime exposes, else read `capabilities/skills.md` once per task. Skip for ordinary Q&A.
- Use without asking when the user named the Skill or used a trigger phrase listed in its description, `user_prefs` or an in-session instruction already chose it, the Skill declares itself a mandatory guardrail/gate, or the request can only be done through that Skill's tooling (e.g. a Bilibili transcript).
- Otherwise offer before starting: one short line naming at most 3 candidates with a few-word reason each, asking whether to use them (bundle with any needed clarifying question). Do not load an offered `SKILL.md` until the user agrees.
- Declined -> do not re-offer it for the same task. Headless/non-interactive -> proceed without it and name the candidate in the final report.
- Loading a Skill whose directory has `UPSTREAM.json` -> once per session run `tools/skill_upstream.py check <name> --quiet` from this root with `python3`/`python`/`py` (TTL-cached). If it prints a status, mention it in one line and offer `update` after the current task; never update without confirmation. On error, continue.

## On-demand Capabilities

Load only when triggered:

- Skill discovery -> `capabilities/skills.md`;
- Skill maintenance/deployment -> `capabilities/skill-maintenance.md`;
- runtime registry/machine discovery/shared local state -> `capabilities/runtime.md`;
- MCP/tool discovery -> `capabilities/mcp.md`;
- search backend selection/fallback/failure -> `capabilities/search.md`;
- cross-review -> `capabilities/cross-review.md` via `models/high.md`;
- any route that starts task-owned processes, allocates ports, changes temporary config/permissions, or creates temporary/unrequested files (repo-local or not, e.g. scratch files) -> `capabilities/cleanup.md` before the first side effect of each such kind, even if it first appears in a later phase of an already-running task; Engineering additionally applies its regression/delivery rules.

Do not bulk-read Skills or capabilities.
