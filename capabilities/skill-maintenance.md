# Skill Maintenance Policy

Load this file only when creating, updating, renaming, deleting, deploying, syncing, or structurally troubleshooting canonical Skills. Normal Skill execution should use discovery metadata plus the matching `SKILL.md` without loading this file.

## Canonical Source

`skills/` is canonical; `capabilities/skills.md` is only its generated discovery index.

- Use an existing canonical Skill directly; do not maintain runtime-private forks.
- Move newly created reusable Skills into `skills/<name>/` in the same task.
- Update the canonical copy when it exists.
- `SKILL.md` frontmatter is the metadata source of truth.
- Regenerate the index with `python tools/gen-index.py` after add/delete/rename/description changes; use `--check` for validation.
- Resolve Skill-internal paths relative to that Skill, not cwd or a runtime home path.

## Runtime Layout

Runtime Skill layout is machine-specific. If maintenance requires runtime registry, deployment paths, discovery, or sync state, load `capabilities/runtime.md` and use verified local facts rather than fixed product paths.

`tools/doctor.py` is the canonical cross-platform health check for deployed Skill/runtime state.

## Upstream (Vendored) Skills

A Skill copied from a GitHub repo MUST carry `skills/<name>/UPSTREAM.json` (`repo`, `path`, `ref`, `commit`, `synced_at`, `local_changes`, optional `exclude`/`note`). Manage it only with `tools/skill_upstream.py`; never hand-edit `commit`.

- Vendoring a new Skill: copy it, then `adopt <name> --repo owner/name --path <dir> [--ref <branch>]`. `adopt` detects the base commit from blob hashes; never guess a SHA.
- Keep intentional local edits minimal and describe them in `local_changes`; they survive updates through 3-way merge.
- `check [names] [--force]`: `behind` -> offer an update; `path-missing` -> upstream moved/renamed/removed the Skill, locate the new path and re-adopt (renames may need an index/name decision); `unpinned` -> base unknown, review upstream manually, then `pin`.
- Before resolving a conflict, check `git log` for that file: a file never edited in this repo is an older upstream copy, not a local patch -> take upstream verbatim. Only real local commits are intent to preserve.
- When upstream splits, renames, or stubs a Skill (it now defers to Skills not vendored here), keep the local Skill self-contained: track the new upstream path if the content moved, otherwise port useful changes by hand and `pin` the reviewed commit.
- Updating requires user confirmation. Run `update <name>` (dry run) first and show its plan; then `update <name> --apply`. On conflicts, resolve markers/`*.upstream` files with the user's local intent preserved, then `pin <name> <sha>`.
- After an update: review the diff for new scripts, network calls, or permission changes (upstream content is untrusted); re-run `tools/gen-index.py` if frontmatter changed; re-check repo tests.
- Prefer a runtime plugin/marketplace install over vendoring when the user only needs that runtime; if both exist, say so.
