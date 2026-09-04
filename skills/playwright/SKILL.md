---
name: playwright
description: "Use for real-browser terminal automation. Resolve the bundled launcher from the current skill directory, cache the working npx/Node launcher locally, and reuse it across Codex/Claude/other runtimes."
---

# Playwright CLI Skill

Drive a real browser from the terminal using `@playwright/cli`. This Skill is **runtime-neutral**: do not assume it lives under `$CODEX_HOME` or that cwd is the ai-prompt root.

## Fast path

Use the Python wrapper relative to the currently loaded Skill directory:

```text
python <skill_dir>/scripts/playwright_cli.py <command> [args]
```

Examples:

```text
python <skill_dir>/scripts/playwright_cli.py open https://playwright.dev --headed
python <skill_dir>/scripts/playwright_cli.py snapshot
python <skill_dir>/scripts/playwright_cli.py click e15
python <skill_dir>/scripts/playwright_cli.py screenshot
```

The wrapper follows the project-wide rule:

1. check `.local/runtime.json` for `skills.playwright.launcher`;
2. if still valid, reuse it directly;
3. otherwise discover `npx` once;
4. on Windows, resolve a direct Node + `npx-cli.js` launcher when possible instead of routing user arguments through `cmd.exe`;
5. cache the resolved launcher for later sessions.

`PLAYWRIGHT_NPX` can override discovery for the current machine/session.

Legacy `scripts/playwright_cli.sh` is only a compatibility wrapper around the Python launcher.

## Prerequisite

Node.js/npm is required because the launcher uses `npx --package @playwright/cli` semantics. If discovery reports no `npx`, ask the user to install Node.js/npm. Do not re-run the same PATH hunt every turn after a successful discovery has already been cached.

A global `playwright-cli` install is optional; the bundled launcher is preferred because it keeps the invocation consistent across machines.

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture screenshot/pdf/trace only when useful.

Example:

```text
python <skill_dir>/scripts/playwright_cli.py open https://example.com
python <skill_dir>/scripts/playwright_cli.py snapshot
python <skill_dir>/scripts/playwright_cli.py click e3
python <skill_dir>/scripts/playwright_cli.py snapshot
```

## Session reuse

If `PLAYWRIGHT_CLI_SESSION` is set, the wrapper automatically appends `--session` unless the caller already supplied one. The session name is runtime data; do not hardcode a machine/user-specific session in this Skill.

## When to snapshot again

Snapshot after:

- navigation;
- major DOM changes;
- opening/closing modal/menu;
- tab switches;
- a stale/missing element ref error.

## References

Open only what is needed:

- `references/cli.md`
- `references/workflows.md`

Paths are relative to this Skill directory, not cwd.

## Guardrails

- Snapshot before using element ids such as `e12`.
- Re-snapshot when refs may be stale.
- Prefer explicit CLI actions over arbitrary `eval`/`run-code`.
- Use `--headed` when visual inspection is actually needed.
- Artifacts should go to a task/project-appropriate output directory; do not assume the ai-prompt repository itself is the user project.
- Current session browser tools, if already exposed by the runtime and suitable for the task, are realtime facts and may be preferable to launching another browser process.
- If cached launcher fails, invalidate/re-discover it and refresh `.local/runtime.json`; do not add another OS-specific absolute path to this file.
