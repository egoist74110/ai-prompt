# AI Prompt Router

这是所有 AI Agent / 模型运行时的统一入口。任何运行时只要能读取本文件，就应按这里进入完整工作流。

## Read Order

1. 先读 `/Users/wesker/.ai-prompt/common.md`。
2. 直接处理完整问题时，再读 `/Users/wesker/.ai-prompt/models/high.md`。
3. 被明确要求做侦查、上下文收集、列路径、引用原文或机械执行时，只读 `/Users/wesker/.ai-prompt/models/scout.md`，不要再读 high。
4. 需要 skill/MCP 时，只先读索引：
   - `/Users/wesker/.ai-prompt/capabilities/skills.md`
   - `/Users/wesker/.ai-prompt/capabilities/mcp.md`

## Capability Loading

- 不要全量读取 `/Users/wesker/.ai-prompt/skills`、`/Users/wesker/.ai-prompt/mcp`、`<runtime-skills>` 或所有外部 `SKILL.md`。
- 只有用户点名能力，或任务明显匹配索引里的 description / Use for，才读取对应文件。
- 需要安装、启用或新增 MCP / plugin / connector 前，必须先说明原因、命令/配置和影响范围，得到用户确认后再执行。

## Native Entrypoints

不同 AI 工具会读取不同的私有目录、项目级文件或全局入口设置。那些入口只需要保留很薄的一层：

```text
Read /Users/wesker/.ai-prompt/router.md first, then follow it.
```

目标不是让其它 AI 读取这个仓库，而是让它们读取已经部署好的 `/Users/wesker/.ai-prompt/router.md`。如果某个运行时不支持自动入口文件，就在第一次对话里显式要求它读取本文件。
