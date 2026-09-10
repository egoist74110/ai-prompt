# Skills Index

This file is for skill discovery only. `skills/<name>/SKILL.md` frontmatter is the sole metadata source. Resolve repository paths relative to the directory containing `router.md`; never store machine absolute paths here.

Load a `SKILL.md` only when the user names the skill or the task clearly matches its description. Never load all skills by default.

## Skills

- `ado-pr` — `skills/ado-pr/SKILL.md` — Unified interface for self-hosted Azure DevOps Server (*.cg1alias.com, not dev.azure.com): read work items, read/list PRs, create PRs, and link work items. Use for work-item/PR/create-publish/merge-to-main-or-master intent. Reuse verified local strategy first; discover only on first use or stale cache.
- `anysearch` — `skills/anysearch/SKILL.md` — Real-time web/domain search and URL extraction. Use the portable cached launcher; runtime selection is discovered once per machine and stored in .local instead of re-reading per-skill runtime.conf every activation.
- `backend-architecture-review` — `skills/backend-architecture-review/SKILL.md` — Use before implementing any backend feature — ask the five architecture questions first, then approve the data model and access boundary before writing code.
- `backend-business-safety` — `skills/backend-business-safety/SKILL.md` — Use when designing or changing backend business logic with jobs, workers, publish/deploy/sync/import/export flows, cancellation, retry, timeout, locks, registries, caches, external APIs, or long-running stateful tasks.
- `backend-security-review` — `skills/backend-security-review/SKILL.md` — Per-feature security gate for backend APIs and data access — focus on auth, permissions, token handling, and injection risks on each specific endpoint or operation being implemented.
- `bilibili-auto-transcript` — `skills/bilibili-auto-transcript/SKILL.md` — Transcribe Bilibili videos or favorites. Prefer human CC, then AI subtitles, then Whisper. Cache machine paths, Bash, output/database locations, and favorite IDs in .local to avoid repeated macOS/Windows/WSL discovery.
- `cdn-asset-ops` — `skills/cdn-asset-ops/SKILL.md` — Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
- `data-consistency-review` — `skills/data-consistency-review/SKILL.md` — Check multi-step write operations for partial failure and orphaned state — transaction boundaries, atomicity, and rollback paths. Run after implementation, before claiming done.
- `diagnose` — `skills/diagnose/SKILL.md` — Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test.
- `grill-me` — `skills/grill-me/SKILL.md` — Interview the user relentlessly about a plan or design until reaching shared understanding and resolving each branch of the decision tree.
- `improve-codebase-architecture` — `skills/improve-codebase-architecture/SKILL.md` — Find deepening opportunities in a codebase using domain language and architecture decisions.
- `playwright` — `skills/playwright/SKILL.md` — Use for real-browser terminal automation. Resolve the bundled launcher from the current skill directory, cache the working npx/Node launcher locally, and reuse it across runtimes.
- `production-readiness-review` — `skills/production-readiness-review/SKILL.md` — Pre-ship ops checklist for backend features — timeout, retry, circuit breaker, idempotency, monitoring, and failure recovery.
- `receiving-code-review` — `skills/receiving-code-review/SKILL.md` — Use when receiving code review feedback before implementing suggestions; require technical verification rather than blind agreement.
- `resource-lifecycle-audit` — `skills/resource-lifecycle-audit/SKILL.md` — Audit every resource opened in an implementation for a matching close/kill/unsubscribe before claiming done.
- `script-engineering` — `skills/script-engineering/SKILL.md` — Mandatory guardrail for writing, modifying, reviewing, or debugging shell/PowerShell/Batch/WSL/CI command sequences.
- `security-best-practices` — `skills/security-best-practices/SKILL.md` — Perform language/framework security best-practice reviews when explicitly requested.
- `tdd` — `skills/tdd/SKILL.md` — Test-driven development with a red-green-refactor loop.
- `ui-ux-pro-max` — `skills/ui-ux-pro-max/SKILL.md` — UI/UX design intelligence for design, implementation, review, and refactoring.
- `verification-before-completion` — `skills/verification-before-completion/SKILL.md` — Require verification evidence before claiming work is complete, fixed, or passing.

## Runtime / Plugin Skills

Runtime-native or plugin-provided skills/tools are determined by what the current session actually exposes. Do not maintain a fixed central list or machine-local paths here.
