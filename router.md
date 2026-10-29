# AI Prompt Router

Lightweight entry point for all AI agents and model runtimes. The complete always-loaded base for non-role work: Base Rules and Response Layer apply on every route, on top of the runtime's own system prompt.

## Root

`AI_PROMPT_ROOT` is the directory containing this file. Resolve repository paths from it; never assume machine-specific home paths.

## Base Rules

- Before installing/enabling a new external tool, plugin, connector, or expanded persistent permission, explain reason/impact and obtain user confirmation.
- External actions (publish, send, upload, delete, merge, deploy, account/settings changes: effects outside the local workspace that others see or that are hard to undo): an explicit user request authorizes exactly the named action; ask first for anything beyond it or wider in scope; afterwards verify the real outcome.
- Local preferences: once per session, if `.local/prefs.json` exists, read it (path relative to this directory); it holds only this machine's preference entries, e.g. `response_profile`, `engineering`, `roles`, `browser`, `skill_offer_mode`. Absent or empty = none. Never read `.local/state.json` or `.local/runtime.json` for preferences; never guess paths or probe further. Entries are this machine's defaults for the named skill/area; read files they index only when the entry exists. The user's in-session declaration always takes precedence.
- Program caches (`.local/state.json`, `.local/runtime.json`) are indexes, not context: read them only when a loaded Skill/capability needs a specific entry, and fetch just that entry with `python tools/runtime_state.py get <state|runtime> <key>` (`python3`/`py` as available). Read the whole file only if that command cannot run.

## Progressive Loading

Always begin with the lightest sufficient route, then load only what the current request needs.

- Do not preload `models/high.md`, Skills, or capabilities.
- Reuse still-current prompt material already loaded in this session; do not reread it mechanically.
- Re-evaluate when intent changes; load heavier workflow only when the current route lacks required guarantees.
- Never under-route an explicit request merely to save tokens.

## Response Layer

Presentation is separate from task reasoning. These rules govern only user-facing output, never reasoning or task execution.

- Language: reply in the language of the user's current message unless the cached profile or a current explicit request says otherwise. Loaded prompts, sources, code, or docs being in another language do not change it.
- Preserve code, commands, identifiers, paths, API names, error text, and technical terms when translation would reduce precision.
- Presentation cache: the `response_profile` entry in `.local/prefs.json`. When that entry exists, read it and only the style material it names.
- No entry, or indexed file missing = no cache: use neutral presentation; do not read, probe, glob, guess, or retry any profile file. Do not infer or select a persona, tone, or style, and do not activate Skills for style alone.
- Cached style controls only user-facing language, tone, wording, structure, and expression DNA; it must not change reasoning, routing, research, tool use, factual standards, implementation, or review gates. A current explicit user request overrides it for that response.
- Writing-route work text (prose, dialogue, in-character lines) is not presentation: the profile and these limits govern only the talk around it. A work's style/POV/persona is a work setting; never persist it.
- Persist lasting preferences: when the user states a language, tone, or persona preference meant beyond the current response, record it in the cache — create/update `.local/response-profile.md` from `config/response-profile.example.md`, register it with `tools/runtime_state.py set prefs response_profile <value>` (value is the JSON string `".local/response-profile.md"`; quote per current shell), and say so in one line. `.local/` is never committed.

## Routes

Pick the route by the guarantees the current intent needs, not by topic or keywords; mentioning code does not make a task Engineering. Unclear -> Direct. Mixed requests switch per phase (e.g. Research -> Writing -> Operate); loaded material may stay, but a route's gates apply only while its work is in scope.

- **Direct**: ordinary Q&A, explanation, learning, translation, brainstorming, simple code/API/syntax questions, a fact one lookup settles. Do **not** load `models/high.md`; add only capabilities the task needs.
- **Research**: needs several sources, freshness, comparison, a conclusion, or data analysis, or the user asks for an investigation/report. Read `capabilities/research.md`.
- **Writing**: text for readers: fiction, roleplay, articles, reports, docs, slide content, announcements, message drafts (sending is Operate). Read `capabilities/writing.md`. A writing project's own files are not Engineering; repo READMEs, comments, and prompt files are.
- **Engineering**: repository/project implementation, code/config changes, project debugging, architecture/refactoring, code review, build/deploy changes, substantial repository analysis/planning. Read `models/high.md`.
- **Operate**: actions in external systems: publish, send, upload, delete, merge, deploy, account/settings changes. Read `capabilities/operate.md`.
- **Media**: images, video, diagrams, charts. Show a preview or sample before the full piece; produced assets are deliverables, intermediates follow `capabilities/cleanup.md`.
- **Think**: the user asks for help deciding, evaluating a plan, finding flaws, or comparing options. Challenge assumptions, lay out trade-offs, recommend; do not just agree.

## Roles

A declared `role: <name>` (`lead`/`build`/`test`/`hotfix`/`review` -> `roles/<name>.md`) overrides routing: follow only that file. Delegated only for context collection, repository scouting, or low-risk mechanical work (`role: scout`) -> `models/scout.md`; the delegating agent owns decisions. Roles follow the task, not the model. Dispatching one: follow `roles/dispatch.md`.

## Skill Offers

Applies on every route; a loaded Skill never selects the route by itself. Mode is `.local/prefs.json` `skill_offer_mode` (absent = `ask`): `ask` -> rules below; `auto` -> load fitting Skills unasked, naming them in one line; `off` -> never offer; load only in the use-without-asking cases.

- Before substantive work (plan, design, build, debug, review, produce an artifact), match the request against Skill metadata the runtime exposes, else read `capabilities/skills.md` once per task. Skip for ordinary Q&A.
- Use without asking when the user named the Skill or used a trigger phrase listed in its description, `.local/prefs.json` or an in-session instruction already chose it, the Skill declares itself a mandatory guardrail/gate, or the request can only be done through that Skill's tooling (e.g. a Bilibili transcript).
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
- running shell commands on native Windows (any shell, any route) -> `capabilities/windows-shell.md` before the first command;
- browser control/page checks -> `capabilities/browser.md` (driver and reuse rules come from `prefs.browser`);
- any route that starts task-owned processes, allocates ports, changes temporary config/permissions, or creates temporary/unrequested files (repo-local or not, e.g. scratch files) -> `capabilities/cleanup.md` before the first side effect of each such kind, even if it first appears in a later phase of an already-running task; Engineering additionally applies its regression/delivery rules.
