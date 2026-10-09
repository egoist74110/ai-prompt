# Browser Control

Browser tasks use exactly two lines. Never hand-build browser commands in a shell (playwright-cli, npx, bare `bsk` calls); that route is retired.

Machine install state: `.local/state.json` → `services.browser`. Machine notes (paths, versions, verified facts): `.local/browser-notes.md`. Read them only when a line's tools are missing or setup is in question.

## Line A: user's real browser (logged-in)

- Channel: BrowserSkill DSH plugin → native `browser_*` tools (`browser_session`, `browser_page`, `browser_inspect`, `browser_interact`, `browser_tabs`, `browser_assist`).
- Reuses the user's real Chrome/Edge: cookies, sessions, open tabs. Default to a separate Agent Window; use borrow/return when the user's current tab is needed.
- Use for: sites that need login (admin consoles, GitHub, Cloudflare, Azure DevOps), or verifying what the user actually sees.
- Prerequisites (if missing, report to the user; do not fall back to shell):
  1. Windows-side `bsk` CLI on dsh's PATH, or `bskPath` set in the profile patch;
  2. BrowserSkill extension installed in the user's Chrome/Edge, with local connection enabled in its popup;
  3. plugin `@wxg-prc-cpg/browser-skill-dsh-plugin` installed in the desktop profile.
- `browser_*` tools not visible: check `services.browser` install state, tell the user what is missing; never silently switch lines.

## Line B: built-in isolated browser (dev/test)

- Channel: DSH `dsh-browser-use` subsystem plus one provider (Playwright MCP, Chrome DevTools MCP, or Stagehand). Experimental npm package; must be activated explicitly (profile composition + provider launch/attach config).
- Each Session launches its own Chromium, owned by that Session and closed with it; no login state.
- Use for: localhost verification, public pages, scripted or batch page operations.
- Authority: deepseek-ai/deepseek-harness `docs/subsystems/browser-use.md` (provider and Session ownership rules).
- Mounting: browser-use packages are not `dsh.bundle` packages (no `dsh.bundle` field); listing them in `dsh.profile.bundles` is skipped with a warning. Install via profile `dependencies` (pin to the host version) and insert into the composition in `cordis.patch.yml`:
  ```yaml
  - insert:
      - name: '@deepseek-ai/dsh-browser-use'
      - name: '<provider package>'
        config:
          mode: launch   # or attach + endpoint
          headless: true
  ```

## Routing

- Login state, the user's existing pages, or real-browser behavior → Line A.
- localhost, dev verification, clean environment, no login needed → Line B.
- An explicit user choice of browser or line wins.
- Neither line available: tell the user what is missing and ask before installing; no silent fallback, no hand-built commands.

## Version Pitfalls

- BrowserSkill CLI, extension, and DSH plugin share one version number since 0.2.0. DSH 0.2 host needs plugin ≥ 0.3.2 (0.3.1 has a peer-dependency break, #338: zero `browser_*` tools).
- Plugins do not auto-update: after `dsh plugin update ... --latest`, restart that profile.
- The plugin patch entry `id: browserskill` replaces the whole config object; keep every required field when editing it.
- `lazyTools: false` registers tools at Agent start; the default `true` injects them only after `/browser-skill` is invoked.
- The desktop profile is owned by the Electron app; CLI `--dump-config` on it is refused. Verify config changes with a temporary profile (`dsh --profile <tmp> --from-default-profile web --dump-config`), then delete it.
