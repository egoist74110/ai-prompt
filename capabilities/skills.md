# Skills Index

规则：不要全量读取所有 skill。只有用户点名 skill，或任务明显匹配 description 时，才读取对应 `SKILL.md`。

## Custom
- `ui-ux-pro-max`
  - Path: local custom UI skill path, if present on this machine.
  - Use for: 唯一 UI/UX skill；用于页面/组件/交互/视觉的设计、实现、评审、优化、配色、排版、无障碍、移动端适配。
  - Guardrails: 不再并行使用其它前端设计 skill；需要前端视觉时优先它，避免 UI skill 之间互相覆盖。
- `anysearch`
  - Path: `/Users/wesker/.ai-prompt/skills/anysearch/SKILL.md`
  - Runtime: `node /Users/wesker/.ai-prompt/skills/anysearch/scripts/anysearch_cli.js`
  - Use for: 实时外部搜索、批量搜索、垂直领域检索、URL 正文抽取。
  - Guardrails: 按需使用，不作为默认搜索；不用于密码、私密工单、内部代码、商业机密等敏感查询；不要让它覆盖官方文档优先规则。
- `bilibili-auto-transcript`
  - Path: `/Users/wesker/.ai-prompt/skills/bilibili-auto-transcript/SKILL.md`
  - Runtime: `bash /Users/wesker/.ai-prompt/skills/bilibili-auto-transcript/scripts/bilibili_transcript.sh "<B站视频链接>"`
  - Use for: B站/Bilibili 视频链接转录、收藏夹扫描、新视频自动处理；三级降级为 CC 字幕 → AI 字幕 → Whisper。
  - Guardrails: 脚本输出 TXT 后必须读取全文并替换“AI待处理”摘要占位符，再向用户报告完成；默认只输出转录文件，索引交给 knowledge-rag 或用户明确要求的 RAG 脚本。
  - Source: https://clawhub.ai/54lynnn/bilibili-auto-transcript / https://github.com/54Lynnn/bilibili-auto-transcript

## Runtime System Skills（运行时自带，本仓库不提供）

以下 `.system` skill 由运行时自身提供，不在本仓库内。`<runtime-skills>` 表示**当前运行时自己的** skill 目录（各运行时不同）。只有该运行时实际装了对应 skill 时才读取；不要因为索引里出现就假设已安装。

- `skill-creator`
  - Path: `<runtime-skills>/.system/skill-creator/SKILL.md`
  - Use for: 当用户觉得某个重复流程有必要封装成可复用 skill 时，创建或更新本地 skill；也可把稳定工作流、操作手册、提示词套路沉淀成 skill。
  - Guardrails: 只有明确要创建/更新 skill，或用户指出某流程值得复用时才读；不要为了普通任务临时造 skill。
- `skill-installer`
  - Path: `<runtime-skills>/.system/skill-installer/SKILL.md`
  - Use for: 列出可安装 skill、安装精选 skill 或从 GitHub repo 安装 skill。
  - Guardrails: 先判断是否真的需要安装；优先用已有能力和索引，避免“看到推荐就全装”。
- `plugin-creator`
  - Path: `<runtime-skills>/.system/plugin-creator/SKILL.md`
  - Use for: 创建或更新运行时插件，而不是普通 skill。
- `official-docs`
  - Path: `<runtime-skills>/.system/official-docs/SKILL.md`
  - Use for: 对应产品/API 的最新官方文档、模型选择、迁移和提示升级。
- `imagegen`
  - Path: `<runtime-skills>/.system/imagegen/SKILL.md`
  - Use for: 需要 AI 生成或编辑位图视觉资产的任务。

## Engineering Skills（本仓库自带，部署在 `/Users/wesker/.ai-prompt/skills`）

**后端开发五步工作流**（仅后端任务触发，按顺序执行）：
实现前 `backend-architecture-review` → 实现 → 实现后 `resource-lifecycle-audit` + `data-consistency-review` → 交付前 `backend-security-review` → 上线前 `production-readiness-review`

- `backend-architecture-review`
  - Path: `/Users/wesker/.ai-prompt/skills/backend-architecture-review/SKILL.md`
  - Use for: 后端新功能/endpoint/数据流实现前；先回答「产生什么数据、数据去哪、谁能访问、并发冲突、失败清理」五个问题再动手。
  - Guardrails: 只在后端新功能实现前触发；纯配置变更、一次性脚本、前端任务不触发。
- `resource-lifecycle-audit`
  - Path: `/Users/wesker/.ai-prompt/skills/resource-lifecycle-audit/SKILL.md`
  - Use for: 后端实现完成后；审查所有 subprocess/DB连接/Redis/WebSocket/Timer/文件句柄/事件监听器是否都有对应的 close/kill/unsubscribe，每条路径都覆盖。
  - Guardrails: 实现后、声称完成前必须执行；纯函数、无 I/O 的代码不触发。
- `data-consistency-review`
  - Path: `/Users/wesker/.ai-prompt/skills/data-consistency-review/SKILL.md`
  - Use for: 后端实现完成后；检查多步写操作的事务边界、部分失败留下的孤儿数据、read-modify-write 竞争、DB写入与外部副作用的顺序。
  - Guardrails: 实现后触发；单行读、纯查询、只有一个原子写的操作不触发。
- `backend-security-review`
  - Path: `/Users/wesker/.ai-prompt/skills/backend-security-review/SKILL.md`
  - Use for: 后端 endpoint 或数据操作交付前；检查每个接口的鉴权、越权（IDOR）、注入（SQL/命令/路径穿越/SSRF）和敏感数据日志。
  - Guardrails: 只做 per-feature 安全门控；全量代码安全报告用 security-best-practices；纯前端、只读配置不触发。
- `production-readiness-review`
  - Path: `/Users/wesker/.ai-prompt/skills/production-readiness-review/SKILL.md`
  - Use for: 后端功能上线或提交 staging 前；检查超时值、重试预算、幂等设计、可观测性、第三方挂了的降级方案。
  - Guardrails: 上线前触发；本地 dev 工具、一次性迁移脚本、明确不上线的原型不触发。
- `backend-business-safety`
  - Path: `/Users/wesker/.ai-prompt/skills/backend-business-safety/SKILL.md`
  - Use for: 后端业务生命周期安全；涉及 worker/job/发布/同步/导入导出、取消/重试/超时、registry/lock/cache、外部 API、长任务状态时先检查状态机、不变量、清理、幂等和并发。
  - Guardrails: 不用于简单纯函数、小 UI、静态配置或一次性脚本；只在状态可能跨请求/线程/任务存活时触发。
- `grill-me`
  - Path: `/Users/wesker/.ai-prompt/skills/grill-me/SKILL.md`
  - Use for: 需求、计划或设计仍模糊时的拷问模式；先一问一答澄清决策树，再动手实现。
  - Guardrails: 只在需求不清、大模块设计、用户明确要求“拷问/追问/grill me”时触发；小修小补不要触发。
- `tdd`
  - Path: `/Users/wesker/.ai-prompt/skills/tdd/SKILL.md`
  - Use for: 新功能、bugfix、重构或行为变更的测试优先开发；强调公共接口、行为测试、垂直切片。
  - Guardrails: 原型、纯配置、一次性脚本可不触发；没有测试框架时先说明并建议最小验证方案。
- `diagnose`
  - Path: `/Users/wesker/.ai-prompt/skills/diagnose/SKILL.md`
  - Use for: 代码跑不通、逻辑不可用、测试失败、构建失败、性能回退、线上/本地 bug。
  - Guardrails: 先建立可运行反馈回路，再复现、假设、插桩、修复、回归测试；不要凭直觉打补丁。
- `improve-codebase-architecture`
  - Path: `/Users/wesker/.ai-prompt/skills/improve-codebase-architecture/SKILL.md`
  - Use for: 大模块设计、架构隐患排查、重构机会分析、提升可测试性和可维护性。
  - Guardrails: 不默认触发；只在用户要求架构/重构/大模块设计，或诊断后发现缺少测试 seam、耦合严重时触发。
- `verification-before-completion`
  - Path: `/Users/wesker/.ai-prompt/skills/verification-before-completion/SKILL.md`
  - Use for: 声称完成、修好、通过、可提交或可交付之前。
  - Guardrails: 必须有新鲜验证证据；跑不了验证就明确说明原因和剩余风险。
- `receiving-code-review`
  - Path: `/Users/wesker/.ai-prompt/skills/receiving-code-review/SKILL.md`
  - Use for: 收到 review 反馈、PR 评论、或用户点名“帮我提交/合并”且需要先处理外部反馈时。
  - Guardrails: 不盲从 review；先理解、核对代码现实、评估是否技术正确，再逐项处理和验证。
- `security-best-practices`
  - Path: `/Users/wesker/.ai-prompt/skills/security-best-practices/SKILL.md`
  - Use for: 安全最佳实践、安全审查、安全报告、或需要 secure-by-default 的 Python / JavaScript / TypeScript / Go 代码。
  - Guardrails: 只处理安全维度；普通代码 review、调试、UI 问题不要触发。

## Ops Skills（本仓库自带）

- `cdn-asset-ops`
  - Path: `/Users/wesker/.ai-prompt/skills/cdn-asset-ops/SKILL.md`
  - Preflight: `bash /Users/wesker/.ai-prompt/skills/cdn-asset-ops/scripts/cdn_preflight.sh "<console URL 或 host>"`
  - Use for: 操控 MinIO / S3 兼容 CDN 的上传、列举、重命名前缀(=拷贝+删除)、删除；用户给 `http://host:port/browser/<bucket>/...` 形式的 Console 链接、或要配置 `mc`、或抱怨 CDN 资源 404 时触发。
  - Guardrails: 先跑 Preflight 判断配没配好（已配好就复用 alias，别重跑教程）；Console 端口≠S3 API 端口，端口靠探测不靠猜；密钥绝不回显；删除/覆盖一律二段式（cp+核对数量→用户确认→rm），改路径前提醒前端引用会 404。

## Runtime Plugin Skills

以下是可选插件/连接器 skill 的候选路径。使用前先确认当前会话是否已暴露对应工具；未暴露时不要自行安装，必须先向用户说明用途和变更，再等用户确认。
- GitHub:
  - Skills: `github`、`gh-fix-ci`、`gh-address-comments`、`yeet`
- Documents:
  - Skills: `documents`
- Spreadsheets:
  - Skills: `spreadsheets`
- Presentations:
  - Skills: `presentations`
- Browser / Chrome / Computer Use:
  - Skills: `control-in-app-browser`、`control-chrome`、`computer-use`
