# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

**权威顺序以 `router.md` 为准**，本文件只是给人看的概览，冲突时信 router。

## Read Order
- 所有模型先读 `router.md`，再由它进入完整工作流。
- `router.md` 要求先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- 同一个模型也按调用角色分支：直接解决问题时是高模；被明确作为侦查/机械执行调用时是 scout。
- 需要工具能力时，只读索引：`capabilities/skills.md`、`capabilities/mcp.md`。
- 需要网页搜索/外部信息时读 `capabilities/search.md`；交付前做交叉审查时读 `capabilities/cross-review.md`。

## Rule
- 不要每次全量读取 `skills/` 或外部 `SKILL.md`。
- 先读索引，确认相关后再按需读取对应能力文件。

## 维护
- `tools/doctor.sh` — 只读体检：四个运行时入口、两组 skills symlink、索引一致性、hook 是否装、search.md 声明的后端是否真在。换机/重装/动过 skills 后跑一次。
- `tools/install-hooks.sh` — 把 `tools/hooks/pre-commit` 装进 `.git/hooks/`。**clone 到新机器后必须跑一次**，否则索引重建 + codex symlink 同步的闭环会静默失效（`.git/hooks` 不随 git 分发）。
- `tools/gen-index.py` — 重建 `capabilities/skills.md` 的 Auto 登记表，并校验幽灵条目 / name 与目录名不一致；pre-commit 会自动调用。
- `tools/sync-codex-skills.sh` — 把中央 skills 同步成 `~/.codex/skills` 下的 symlink（含悬空清理）。
