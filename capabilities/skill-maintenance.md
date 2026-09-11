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
