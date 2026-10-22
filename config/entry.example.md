# AI prompt entry

Root: <AI_PROMPT_ROOT>

Before anything else, pick a role from what the task asks and who sent it, not from keywords:

- First line `role: <name>` -> that role.
- A pinpointed defect (location or cause given) to fix with a small change -> `hotfix`.
- Only run, add, or repair tests -> `test`.
- Implement a plan/spec/ticket whose design is already decided -> `build`.
- Oversee overall progress: requirement coverage, direction, risk, other sessions' work -> `audit`.
- Delegated context collection or explicitly listed mechanical steps -> `scout`.

Role found -> say it in one short line, then read only `<root>/roles/<name>.md` (`scout`: `<root>/models/scout.md`) and follow it; do not read `router.md`.
No clear role, or the request outgrows the role later -> read `<root>/router.md` first, then follow it.
