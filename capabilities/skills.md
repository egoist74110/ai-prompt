# Skills Index

This file is for skill discovery only. Each entry is `skills/<name>/SKILL.md`; its frontmatter (or `index_description` in a vendored Skill's `UPSTREAM.json`) is the metadata source.
Resolve repository paths relative to the directory containing `router.md`; never store machine absolute paths here.

Match and offer Skills per `router.md` Skill Offers; load a `SKILL.md` only when that rule allows it. Never load all skills by default.

## Skills

- `ado-pr` — Self-hosted Azure DevOps Server (*.cg1alias.com, not dev.azure.com): read work items, read/list/create PRs, link work items, merge to main/master. Reuse the cached local strategy; rediscover only on first use or stale cache.
- `anysearch` — Real-time web/domain search and URL extraction. Use the portable cached launcher; runtime selection is discovered once per machine and stored in .local instead of re-reading per-skill runtime.conf every activation.
- `archify` — Build validated architecture, workflow, sequence, data-flow, and state diagrams as interactive standalone HTML with themes and export; also converts or beautifies Mermaid. Use to visualize systems, pipelines, API flows, or state machines.
- `backend-architecture-review` — Use before implementing any backend feature — ask the five architecture questions first, then approve the data model and access boundary before writing code.
- `backend-business-safety` — Use when designing or changing backend logic with jobs, workers, publish/deploy/sync/import/export, retry, cancellation, timeouts, locks, caches, or external APIs: check lifecycle invariants, cleanup, idempotency, and failure paths before coding.
- `backend-security-review` — Per-feature security gate for backend APIs and data access — focus on auth, permissions, token handling, and injection risks on each specific endpoint or operation being implemented.
- `bilibili-auto-transcript` — Transcribe Bilibili videos or favorites. Prefer human CC, then AI subtitles, then Whisper. Cache machine paths, Bash, output/database locations, and favorite IDs in .local to avoid repeated macOS/Windows/WSL discovery.
- `cdn-asset-ops` — Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
- `code-review` — Code-review protocol for diffs, commits, PRs, and follow-up rounds, as reviewer or for a delegated reviewer: evidence-backed findings with stable ids; re-verify prior findings each round.
- `comfyui` — Drive the user's local ComfyUI via its comfy-mcp server: text-to-image, image edits, workflow runs, outputs, model/VRAM checks, and diagnosing a missing comfy MCP. Use for local image generation, ComfyUI workflows, or 'generate an image'.
- `data-consistency-review` — Check multi-step write operations for partial failure and orphaned state — transaction boundaries, atomicity, and rollback paths. Run after implementation, before claiming done.
- `diagnose` — Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
- `elysia-perspective` — Elysia (Honkai Impact 3rd) perspective and roleplay, including the Herrscher of Erosion branch: analyze people, decisions, or relationships in her frame, or speak in her voice. Only when explicitly asked (e.g. 'Elysia mode', 'ask Elysia'); not for lore questions.
- `figma` — Read Figma design files (node structure, styles, images). Parses file_key + node_id from a Figma URL and calls the REST API with a PAT to fetch design data. Use when the intent matches a design link, Figma, or extracting design parameters.
- `grill-me` — Grill the user relentlessly about a plan, decision, or idea in rounds of numbered questions with recommended answers until shared understanding. Use when the user wants to stress-test a plan or design, or says "grill me" or similar.
- `html-plan` — Write an implementation plan or RFC as one interactive HTML page of claims, each with an exhibit and inline decisions for the user. Use for /html-plan or plans touching more than a couple of files.
- `huashu-nuwa` — Distill a person or theme into a runnable perspective Skill via multi-agent research and mental-model extraction. Use for 'distill [person]', 'nuwa', or 'how does [person] think'.
- `improve-codebase-architecture` — Find deepening opportunities in a codebase, informed by domain language and ADRs. Use for architecture improvement, refactoring opportunities, tightly coupled modules, testability, or AI navigability.
- `playwright` — Use for real-browser terminal automation. Resolve the bundled launcher from the current skill directory, cache the working npx/Node launcher locally, and reuse it across Codex/Claude/other runtimes.
- `production-readiness-review` — Pre-ship ops checklist for backend features — timeout, retry, circuit breaker, idempotency, monitoring, and failure recovery. Run before declaring a backend feature production-ready.
- `receiving-code-review` — Use when receiving code review feedback before implementing suggestions; verify each finding against codebase reality and never apply external feedback blindly.
- `release-announcement` — Draft the customer-facing back-office version-update announcement (release/update notes) from work items and verified code, always in the project's fixed template; customer-service variant too. Needs a work-item number and a registered project, else asks.
- `resource-lifecycle-audit` — Audit every resource opened in an implementation for a matching close/kill/unsubscribe. The most common silent killer in vibe-coded backends. Run after implementation, before claiming done.
- `script-engineering` — Mandatory guardrail when writing, changing, reviewing, or debugging shell scripts (PowerShell, CMD, Bash, sh, zsh, WSL, CI snippets, installers): prevents shell/version, encoding, quoting, path, and line-ending failures; requires verification.
- `security-best-practices` — Language/framework-specific security best-practice review for Python, JS/TS, and Go. Only when a security review or secure-by-default guidance is explicitly requested.
- `st-worldbook` — Create, expand, repair, or audit SillyTavern World Info/lorebooks, and inspect or edit books in a local instance. Use for planning lore structure, writing entries, trigger design, importable JSON, or World Info operations.
- `task-orchestration` — Split a large task into plan and execution: planner mode writes a self-contained step plan with acceptance checks; executor mode runs each step in an isolated subagent with a resumable ledger and escalations. Use to plan big tasks for later/local runs or to run a plan file.
- `tdd` — Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
- `ui-ux-pro-max` — UI/UX design intelligence: styles, palettes, typography, UX rules, charts and stack guidance. Use for UI design/implementation/review/refactor. Resolve scripts from this skill directory; do not assume repo cwd or a specific OS Python command.
- `verification-before-completion` — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always

## Runtime / Plugin Skills

Runtime-native or plugin-provided skills/tools are determined by what the current session actually exposes. Do not maintain a fixed central list or machine-local paths here.
