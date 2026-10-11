# AI Prompt Hub

[简体中文](README.md) · **English**

A shared, progressively loaded prompt entry point for multiple AI agents and model runtimes.

The repository separates portable rules from machine-specific runtime facts. Start with [`router.md`](router.md), which is the authoritative source for routing and precedence. This README is a human-facing overview; when it conflicts with the router, follow the router.

## Design

The system starts with the lightest prompt path that can handle the current request, and loads specialized guidance only when needed. Routing follows the user's current intent, not a keyword or the topic alone.

- **`router.md`** — The only always-loaded file. Routes requests to Direct, Skill-first, Engineering, or Scout, and contains the safeguards shared by every route plus the response-language rules (reply in the user's language by default; lasting language, tone, or persona preferences live in the machine-local `.local/response-profile.md` cache).
- **`models/high.md`** — Engineering workflow, loaded only for actual project work.
- **`models/scout.md`** — Delegated context gathering and low-risk mechanical work.
- **`capabilities/` and `skills/`** — On-demand, specialized workflows.
- **`.local/`** — Machine-specific runtime registry and verified local strategies. It is not committed.
- **`config/runtime-templates.json`** — Starter data used to initialize a local runtime registry.

An already loaded prompt may remain in context, but its gates apply only while the current task still matches that route. A follow-up question can return to Direct without inheriting the previous task's Engineering workflow.

## Routing at a glance

| Route | Typical requests | Load |
| --- | --- | --- |
| **Direct** | Questions, explanations, summaries, translations, brainstorming, simple code or API questions | `router.md` |
| **Skill-first** | A named Skill or a request matching Skill metadata | Skill discovery guidance, then the matched `SKILL.md` |
| **Engineering** | Implementations, project debugging, code/config changes, architecture, refactoring, reviews, build/deployment changes, substantial repository analysis | `models/high.md` plus only the relevant capabilities and Skills |
| **Scout** | Delegated reconnaissance, context gathering, or low-risk mechanical tasks | `models/scout.md` |

A Skill that runs a command or writes a requested output does not automatically turn a Skill-first request into Engineering. Load `capabilities/cleanup.md` before the first task-owned side effect (such as a temporary file, process, port, or configuration change); Engineering tasks also follow its full regression and delivery gates.

## Runtime registry

The registry keeps runtime support data-driven. The tools iterate over locally registered runtimes instead of branching on product names. Runtime names may appear in replaceable starter data, but machine-specific availability and verified behavior belong in `.local/`.

Initialize and inspect the local registry:

```sh
python tools/runtime_state.py init
python tools/runtime_state.py runtime list
```

Register another runtime without changing central code:

```sh
python tools/runtime_state.py runtime add <runtime-id> \
  --commands-json '["<command>"]' \
  --capabilities-json '["agent","review","skills"]'
```

See [`config/README.md`](config/README.md) for registry configuration and options. On systems where the command is `python3`, use that instead of `python`.

## Skills

Skills are discovered from their frontmatter. The generated `capabilities/skills.md` index is a discovery aid; each `skills/<name>/SKILL.md` frontmatter is the source of truth.

Before substantial work such as planning, design, implementation, investigation, review, or producing a file, the router can offer a matching Skill. It asks briefly and waits for the user's choice. A Skill is used without asking when the user names it, its trigger is explicit, a preference already applies, it is a required guardrail, or its tools are necessary. After a refusal, it is not offered again for that task. In unattended use, the candidate is reported without waiting.

Do not bulk-load all Skills or capabilities. For Skill creation, editing, deployment, or synchronization, load `capabilities/skill-maintenance.md`; ordinary Skill execution does not require it.

## Local state and search

Portable repository rules describe what should happen and provide initial templates. The ignored `.local/` directory records what is actually available and what has been verified on this machine.

The precedence is: **current session facts → local runtime/state → discovery**. Cache reusable, non-sensitive results after a successful discovery and reuse them until they become stale. Secrets themselves must not be stored in `.local/`.

Load `capabilities/runtime.md` only when working with the runtime registry, local discovery, or shared local state. Load `capabilities/search.md` when selecting a search backend, falling back, or handling search failures; a working native search path does not need this extra policy.

## Cleanup and delivery

Cleanup rules protect user-owned state and distinguish it from resources created for the current task. Remove only task-owned temporary resources, and restore temporary configuration and permissions. Do not use broad destructive cleanup commands that can affect pre-existing files or processes.

For Engineering work, the delivery flow includes risk-appropriate regression checks, any required review and follow-up fixes, inspection of the final diff and untracked files, cleanup, a post-cleanup smoke check, and a clear report of what was verified.

## Upstream Skills

GitHub-sourced Skills can include an `UPSTREAM.json` manifest. Use `tools/skill_upstream.py` to inspect and update them:

```sh
python3 tools/skill_upstream.py list
python3 tools/skill_upstream.py check --force
python3 tools/skill_upstream.py update tdd             # preview
python3 tools/skill_upstream.py update tdd --apply     # apply
python3 tools/skill_upstream.py adopt <name> --repo owner/repo --path <subdirectory>
```

Updates use a three-way merge to preserve local changes. Review conflicts and newly added scripts or network calls before accepting upstream changes. An upstream update is not applied without user confirmation.

## Maintenance

Before changing prompts or documentation, read [`CONTRIBUTING.md`](CONTRIBUTING.md). It defines the boundary between human-facing documentation and machine-facing prompts.

Useful tools include:

- `tools/runtime_state.py` — Initialize, migrate, inspect, and update local runtime/state data.
- `tools/doctor.py` — Read-only checks of the local registry across platforms.
- `tools/sync_skills.py` — Sync Skills declared by registered runtimes.
- `tools/skill_upstream.py` — Track and merge updates from upstream Skill sources.
- `tools/gen-index.py` — Generate or validate the Skill discovery index.

Run the repository's tests with:

```sh
python -m unittest discover -s tests
```

## Boundaries

The central repository answers **what should happen** and provides **initial templates**. The local `.local/` directory answers **what this machine has available** and **what has been verified to work here**.

