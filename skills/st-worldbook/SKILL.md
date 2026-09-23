---
name: st-worldbook
description: "Author SillyTavern worldbook entries and inspect or edit books in a local SillyTavern instance. Use for lorebook structure, entry fields, triggers, enabled books, and CSRF-aware worldinfo API operations."
---

# SillyTavern Worldbooks

Use this skill for either entry authoring or local book operations. Read only the relevant reference:

- For worldbook writing, titles, triggers, and mod packs, read [references/authoring.md](references/authoring.md).
- For the API, disk layout, entry schema, or any live book change, read [references/operations.md](references/operations.md).

Machine facts belong in `.local/directory-index.md`. Use the current session's verified facts first, then the current OS's index if it still matches observation. If missing or stale, discover and update only that OS section. Keep install paths, ports, user directories, and inventory out of this portable file. The index is local and gitignored; do not sync it between machines or copy full entry content into it.

## Find the local instance

1. Prefer a URL or path supplied by the user, then the current OS index. Check that the cached installation still has `config.yaml` and `server.js`, and that the API responds when needed.
2. If discovery is needed, find an installation containing `config.yaml`, `server.js`, and `public/index.html`. On Windows, search likely drive and profile locations with bounded depth. On macOS, try Spotlight and likely home folders before a bounded scan. Avoid full-drive recursion.
3. Read `port` and `dataRoot` from `config.yaml`; resolve relative `dataRoot` paths against the installation root. Find the applicable user directory rather than assuming `default-user`, especially when user accounts are enabled. Recent installations use `<user-dir>/worlds/`; check the actual directory on older installations.
4. Verify the target instance and user by listing worldbooks through the API as described in the operations reference. Record verified date, ST version, API URL, data and user directories, globally enabled book names, and a dated inventory of names and entry counts in the current OS section of `.local/directory-index.md`.

The ST data directory contains user data. Read it as needed; write a book only when the user requests that change. Before any write, follow the backup and verification steps in the operations reference. Do not change `settings.json` or another book as a side effect.
