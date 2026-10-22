# AI prompt entry

Root: <AI_PROMPT_ROOT>

Before anything else, pick a role from the task and how it was handed to you; never from which model you are:

- First line `role: <name>` -> that role.
- The user wants you to run the whole effort: split, dispatch, track, accept -> `lead`.
- A pinpointed defect (location or cause given) to fix with a small change -> `hotfix`.
- Only run, add, or repair tests -> `test`.
- Implement a plan/spec/ticket whose design is already decided -> `build`.
- Review a given diff/commit/PR -> `review`.
- Delegated context collection or explicitly listed mechanical steps -> `scout`.

Role found -> say it in one short line (unsure between two: ask the user which), then read only `<root>/roles/<name>.md` (`scout`: `<root>/models/scout.md`); do not read `router.md`.
No clear role, or the request outgrows the role -> read `<root>/router.md` first, then follow it.
