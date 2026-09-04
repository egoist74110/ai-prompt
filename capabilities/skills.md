# Skills Index

本文件只负责 **skill 发现**。`skills/<name>/SKILL.md` frontmatter 才是唯一元数据源；
仓库内路径全部相对 `router.md` 所在目录解析，本索引禁止保存机器绝对路径。

规则：只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`；不要全量读取。

## Skills

- `ado-pr` — `skills/ado-pr/SKILL.md` — 与自建 Azure DevOps Server（*.cg1alias.com，非 dev.azure.com）交互的统一入口——读工单、读/列 PR、建 PR 并关联工单。命中工单号、PR、发布/建 PR、合并到 main/master 等意图时使用。优先复用本机已验证的本地 strategy；只有首次或缓存失效时才探测认证来源、执行侧和 API 路径。
- `anysearch` — `skills/anysearch/SKILL.md` — Real-time web/domain search and URL extraction. Use the portable cached launcher; runtime selection is discovered once per machine and stored in .local instead of re-reading per-skill runtime.conf every activation.
- `backend-architecture-review` — `skills/backend-architecture-review/SKILL.md` — Use before implementing any backend feature — ask the five architecture questions first, then approve the data model and access boundary before writing code.
- `backend-business-safety` — `skills/backend-business-safety/SKILL.md` — Use when designing or changing backend business logic with jobs, workers, publish/deploy/sync/import/export flows, cancellation, retry, timeout, locks, registries, caches, external APIs, or long-running stateful tasks. Focuses on lifecycle …
- `backend-security-review` — `skills/backend-security-review/SKILL.md` — Per-feature security gate for backend APIs and data access — focus on auth, permissions, token handling, and injection risks on each specific endpoint or operation being implemented.
- `bilibili-auto-transcript` — `skills/bilibili-auto-transcript/SKILL.md` — B站视频/收藏夹转录。优先 CC→AI 字幕→Whisper；机器路径、Bash、输出目录、数据库、收藏夹 ID 走 .local 缓存，避免跨 macOS/Windows/WSL 重复探测。
- `cdn-asset-ops` — `skills/cdn-asset-ops/SKILL.md` — Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
- `data-consistency-review` — `skills/data-consistency-review/SKILL.md` — Check multi-step write operations for partial failure and orphaned state — transaction boundaries, atomicity, and rollback paths. Run after implementation, before claiming done.
- `diagnose` — `skills/diagnose/SKILL.md` — Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwi…
- `grill-me` — `skills/grill-me/SKILL.md` — Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
- `improve-codebase-architecture` — `skills/improve-codebase-architecture/SKILL.md` — Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the decisions in docs/adr/. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, …
- `playwright` — `skills/playwright/SKILL.md` — Use for real-browser terminal automation. Resolve the bundled launcher from the current skill directory, cache the working npx/Node launcher locally, and reuse it across Codex/Claude/other runtimes.
- `production-readiness-review` — `skills/production-readiness-review/SKILL.md` — Pre-ship ops checklist for backend features — timeout, retry, circuit breaker, idempotency, monitoring, and failure recovery. Run before declaring a backend feature production-ready.
- `receiving-code-review` — `skills/receiving-code-review/SKILL.md` — Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
- `resource-lifecycle-audit` — `skills/resource-lifecycle-audit/SKILL.md` — Audit every resource opened in an implementation for a matching close/kill/unsubscribe. The most common silent killer in vibe-coded backends. Run after implementation, before claiming done.
- `script-engineering` — `skills/script-engineering/SKILL.md` — Mandatory guardrail when writing, modifying, reviewing, or debugging PowerShell, CMD/Batch, Bash, sh, zsh, WSL glue, installer/bootstrap scripts, CI shell snippets, or cross-platform command sequences. Prevents AI-authored script failures f…
- `security-best-practices` — `skills/security-best-practices/SKILL.md` — Perform language and framework specific security best-practice reviews and suggest improvements. Trigger only when the user explicitly requests security best practices guidance, a security review/report, or secure-by-default coding help. Tr…
- `tdd` — `skills/tdd/SKILL.md` — Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development.
- `ui-ux-pro-max` — `skills/ui-ux-pro-max/SKILL.md` — UI/UX design intelligence: styles, palettes, typography, UX rules, charts and stack guidance. Use for UI design/implementation/review/refactor. Resolve scripts from this skill directory; do not assume repo cwd or a specific OS Python comman…
- `verification-before-completion` — `skills/verification-before-completion/SKILL.md` — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always

## Runtime / Plugin Skills

运行时原生或插件提供的 skill/tool 以**当前会话实际暴露**为准，不在本仓库维护固定清单或本机路径。
