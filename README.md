# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

## Read Order
- 所有模型先读 `router.md`，再由它进入完整工作流。
- `router.md` 要求先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- 同一个模型也按调用角色分支：直接解决问题时是高模；被明确作为侦查/机械执行调用时是 scout。
- 需要工具能力时，只读索引：`capabilities/skills.md`、`capabilities/mcp.md`。

## Rule
- 不要每次全量读取 `skills/`、`mcp/` 或外部 `SKILL.md`。
- 先读索引，确认相关后再按需读取对应能力文件。
