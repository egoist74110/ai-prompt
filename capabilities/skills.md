# Skills Index

本文件只负责 **skill 发现**。`skills/<name>/SKILL.md` frontmatter 才是唯一元数据源；仓库内路径全部相对 `router.md` 所在目录解析，本索引禁止保存机器绝对路径。

规则：只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`；不要全量读取。

## Skills

- `ado-pr` — `skills/ado-pr/SKILL.md` — 自建 Azure DevOps Server（`*.cg1alias.com`，非 dev.azure.com）的工单/PR 统一入口。优先复用本机已验证的 strategy；首次或缓存失效时才探测认证来源、执行侧和 API 路径。
- `anysearch` — `skills/anysearch/SKILL.md` — 实时外部搜索、批量搜索、垂直领域检索和 URL 正文抽取。
- `backend-architecture-review` — `skills/backend-architecture-review/SKILL.md` — 后端新功能实现前的架构检查：数据产生、流向、访问边界、并发冲突和失败清理。
- `backend-business-safety` — `skills/backend-business-safety/SKILL.md` — 后端长生命周期业务流程的状态机、不变量、幂等、并发与清理检查。
- `backend-security-review` — `skills/backend-security-review/SKILL.md` — 后端 endpoint / 数据操作交付前的鉴权、越权、注入和敏感数据检查。
- `bilibili-auto-transcript` — `skills/bilibili-auto-transcript/SKILL.md` — B 站视频转录和收藏夹扫描，支持 CC → AI 字幕 → Whisper 降级及可选摘要。
- `cdn-asset-ops` — `skills/cdn-asset-ops/SKILL.md` — MinIO / S3 兼容 CDN 的配置探测、上传、列举、重命名和安全删除。
- `data-consistency-review` — `skills/data-consistency-review/SKILL.md` — 多步写操作的事务边界、部分失败、孤儿状态和并发一致性检查。
- `diagnose` — `skills/diagnose/SKILL.md` — 复现 → 最小化 → 假设 → 插桩 → 修复 → 回归测试的系统化排障流程。
- `grill-me` — `skills/grill-me/SKILL.md` — 对仍模糊的需求、计划或设计逐分支追问，直到形成共享理解。
- `improve-codebase-architecture` — `skills/improve-codebase-architecture/SKILL.md` — 架构隐患排查、重构机会分析、提升可测试性和可维护性。
- `playwright` — `skills/playwright/SKILL.md` — 通过 Playwright CLI 自动化真实浏览器进行导航、表单、快照、截图、数据提取和 UI 流调试。
- `production-readiness-review` — `skills/production-readiness-review/SKILL.md` — 后端上线前的 timeout、retry、幂等、监控和故障恢复检查。
- `receiving-code-review` — `skills/receiving-code-review/SKILL.md` — 收到 review 反馈后先核对技术事实，再逐项处理和验证，避免盲从。
- `resource-lifecycle-audit` — `skills/resource-lifecycle-audit/SKILL.md` — 审查 subprocess、DB、Redis、WebSocket、Timer、文件句柄、监听器等资源是否完整释放。
- `security-best-practices` — `skills/security-best-practices/SKILL.md` — Python / JavaScript / TypeScript / Go 等语言和框架的安全最佳实践审查。
- `tdd` — `skills/tdd/SKILL.md` — Red-Green-Refactor 测试优先开发，用于新功能、bugfix、重构和行为变更。
- `ui-ux-pro-max` — `skills/ui-ux-pro-max/SKILL.md` — UI/UX 设计、实现、评审、配色、排版、无障碍和多技术栈视觉指导。
- `verification-before-completion` — `skills/verification-before-completion/SKILL.md` — 在声称完成、修好、通过、可提交或可交付前要求新鲜验证证据。

## Runtime / Plugin Skills

运行时原生或插件提供的 skill/tool 以**当前会话实际暴露**为准，不在本仓库维护固定清单或本机路径。
