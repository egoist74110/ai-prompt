# Skills Index

本文件只负责 **skill 发现**。`skills/<name>/SKILL.md` frontmatter 才是唯一元数据源；仓库内路径全部相对 `router.md` 所在目录解析，本索引禁止保存机器绝对路径。

规则：只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`；不要全量读取。

## Skills

- `ado-pr` — `skills/ado-pr/SKILL.md` — 自建 Azure DevOps Server（`*.cg1alias.com`，非 dev.azure.com）的工单/PR 统一入口。优先复用本机已验证的 strategy；首次或缓存失效时才探测认证来源、执行侧和 API 路径。
- `anysearch` — `skills/anysearch/SKILL.md` — Real-time web/domain search and URL extraction. Use the portable cached launcher; runtime selection is discovered once per machine and stored in .local instead of re-reading per-skill runtime.conf every activation.
- `backend-architecture-review` — `skills/backend-architecture-review/SKILL.md` — 后端新功能实现前的架构检查：数据产生、流向、访问边界、并发冲突和失败清理。
- `backend-business-safety` — `skills/backend-business-safety/SKILL.md` — 后端长生命周期业务流程的状态机、不变量、幂等、并发与清理检查。
- `backend-security-review` — `skills/backend-security-review/SKILL.md` — 后端 endpoint / 数据操作交付前的鉴权、越权、注入和敏感数据检查。
- `bilibili-auto-transcript` — `skills/bilibili-auto-transcript/SKILL.md` — B站视频/收藏夹转录。优先 CC→AI 字幕→Whisper；机器路径、Bash、输出目录、数据库、收藏夹 ID 走 .local 缓存，避免跨 macOS/Windows/WSL 重复探测。
- `cdn-asset-ops` — `skills/cdn-asset-ops/SKILL.md` — Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
- `data-consistency-review` — `skills/data-consistency-review/SKILL.md` — 多步写操作的事务边界、部分失败、孤儿状态和并发一致性检查。
- `diagnose` — `skills/diagnose/SKILL.md` — 复现 → 最小化 → 假设 → 插桩 → 修复 → 回归测试的系统化排障流程。
- `grill-me` — `skills/grill-me/SKILL.md` — 对仍模糊的需求、计划或设计逐分支追问，直到形成共享理解。
- `improve-codebase-architecture` — `skills/improve-codebase-architecture/SKILL.md` — 架构隐患排查、重构机会分析、提升可测试性和可维护性。
- `playwright` — `skills/playwright/SKILL.md` — Use for real-browser terminal automation. Resolve the bundled launcher from the current skill directory, cache the working npx/Node launcher locally, and reuse it across Codex/Claude/other runtimes.
- `production-readiness-review` — `skills/production-readiness-review/SKILL.md` — 后端上线前的 timeout、retry、幂等、监控和故障恢复检查。
- `receiving-code-review` — `skills/receiving-code-review/SKILL.md` — 收到 review 反馈后先核对技术事实，再逐项处理和验证，避免盲从。
- `resource-lifecycle-audit` — `skills/resource-lifecycle-audit/SKILL.md` — 审查 subprocess、DB、Redis、WebSocket、Timer、文件句柄、监听器等资源是否完整释放。
- `security-best-practices` — `skills/security-best-practices/SKILL.md` — Python / JavaScript / TypeScript / Go 等语言和框架的安全最佳实践审查。
- `tdd` — `skills/tdd/SKILL.md` — Red-Green-Refactor 测试优先开发，用于新功能、bugfix、重构和行为变更。
- `ui-ux-pro-max` — `skills/ui-ux-pro-max/SKILL.md` — UI/UX design intelligence: styles, palettes, typography, UX rules, charts and stack guidance. Use for UI design/implementation/review/refactor. Resolve scripts from this skill directory; do not assume repo cwd or a specific OS Python command.
- `verification-before-completion` — `skills/verification-before-completion/SKILL.md` — 在声称完成、修好、通过、可提交或可交付前要求新鲜验证证据。

## Runtime / Plugin Skills

运行时原生或插件提供的 skill/tool 以**当前会话实际暴露**为准，不在本仓库维护固定清单或本机路径。
