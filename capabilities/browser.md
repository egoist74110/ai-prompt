# Browser Control

Browser preferences live in `.local/prefs.json` → `browser` (read with the other prefs once per session; the user's in-session declaration overrides). Never hardcode a driver or choice in this file.

| key | meaning when set |
| --- | --- |
| `driver` | Browser to control. `ego-browser` = the `ego-browser` skill (ego lite). Other values name a line below or a runtime browser tool. Absent = pick by Routing. |
| `reuse_user_pages` | `true`: before opening anything, list the user's open tabs and drive a matching one (same origin/path). Open a new tab only if none matches, and say so. |
| `reuse_user_servers` | `true`: use the address the user already runs (dev server, preview URL, tab already pointing at it). Never start `npm run dev` or any server for browsing; if none is reachable, ask the user to start it. |
| `ask_when_multiple_ports` | `true`: if the project exposes more than one port/app (frontend, API, admin, ...) or several candidate tabs/ports match, ask which one before controlling the browser. Do not guess. |

Order before any browser action: preferences → find user's existing page/address (tabs, listening ports the user started) → ask if ambiguous (multi-port) → drive. Only then fall back to opening pages or servers yourself, and only if the preference is not `true`.

Persist: when the user states a lasting browser preference, record it with `python3 tools/runtime_state.py set prefs browser '<full JSON object>'` (merge existing keys) and say so in one line.

Machine install state: `.local/state.json` → `services.browser`. Machine notes: `.local/browser-notes.md`. Read them only when the chosen driver's tools are missing or setup is in question. Driver missing: tell the user what is missing; never silently switch drivers.

## Driver: ego-browser (ego lite)

Load the `ego-browser` skill and follow it (it runs `ego-browser skill` for the version-matched guide). It uses the user's logged-in browser, so reuse tabs per the preferences above.

Legacy lines below apply only when `driver` is absent or names them. Never hand-build browser commands in a shell (playwright-cli, npx, bare `bsk` calls).

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
- `prefs.browser.driver` wins over the rules above; an explicit in-session user choice wins over everything.
- Neither line available: tell the user what is missing and ask before installing; no silent fallback, no hand-built commands.

## Version Pitfalls

- BrowserSkill CLI, extension, and DSH plugin share one version number since 0.2.0. DSH 0.2 host needs plugin ≥ 0.3.2 (0.3.1 has a peer-dependency break, #338: zero `browser_*` tools).
- Plugins do not auto-update: after `dsh plugin update ... --latest`, restart that profile.
- The plugin patch entry `id: browserskill` replaces the whole config object; keep every required field when editing it.
- `lazyTools: false` registers tools at Agent start; the default `true` injects them only after `/browser-skill` is invoked.
- The desktop profile is owned by the Electron app; CLI `--dump-config` on it is refused. Verify config changes with a temporary profile (`dsh --profile <tmp> --from-default-profile web --dump-config`), then delete it.
