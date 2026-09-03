# AI Prompt Router

这是所有 AI Agent / 模型运行时的统一入口。任何运行时只要能读取本文件，就应按这里进入完整工作流。

## Read Order

1. 先读 `/Users/wesker/.ai-prompt/common.md`。
2. 直接处理完整问题时，再读 `/Users/wesker/.ai-prompt/models/high.md`。
3. 被明确要求做侦查、上下文收集、列路径、引用原文或机械执行时，只读 `/Users/wesker/.ai-prompt/models/scout.md`，不要再读 high。
4. 需要 skill/MCP 时，只先读索引：
   - `/Users/wesker/.ai-prompt/capabilities/skills.md`
   - `/Users/wesker/.ai-prompt/capabilities/mcp.md`
   - 交付前做交叉审查时读 `/Users/wesker/.ai-prompt/capabilities/cross-review.md`（触发条件见 `models/high.md` 的 Cross-Review Gate）
5. 需要网页搜索 / 获取外部信息时，先读 `/Users/wesker/.ai-prompt/capabilities/search.md`（搜索纪律 + 五路策略），不要自创搜索路径。

## Capability Loading

- 不要全量读取 `/Users/wesker/.ai-prompt/skills`、`<runtime-skills>` 或所有外部 `SKILL.md`。
- 只有用户点名能力，或任务明显匹配索引里的 description / Use for，才读取对应文件。
- 需要安装、启用或新增 MCP / plugin / connector 前，必须先说明原因、命令/配置和影响范围，得到用户确认后再执行。

## Skill Contract（skill 唯一出生地）

`/Users/wesker/.ai-prompt/skills/` 是全部 skill 的**唯一正典库**，`capabilities/skills.md` 是它的索引。私有 skill 允许存在，但中央必须同步，保证任何运行时都用得上最新版：

1. **已有直接用**：用 skill 前先查索引；中央库里已有的 skill，直接读中央 `SKILL.md`，不要在自己运行时目录里再建/再读私有副本。
2. **新增必须同步**：可以先在自己运行时私有 skills 目录（如 `~/.claude/skills/`、`~/.codex/skills/`）创建，但同一步内必须把完整目录同步到 `/Users/wesker/.ai-prompt/skills/<name>/`，并更新 `capabilities/skills.md`（跑 `tools/gen-index.py` 重新生成索引段，或手工补条目）。没同步完不算完成。
3. **更新改正典**：中央已有同名 skill → 直接改中央文件，不要在私有目录分叉；已有旧私有副本 → 更新中央后删掉私有副本。
4. **索引不许过期**：任何新增/删除/改名 skill 都必须伴随 `capabilities/skills.md` 变更；中央仓库（git）里改完记得 commit。
5. **symlink 布局不同，同步义务也不同**（本机现状，别一概而论）：
   - **Claude**：`~/.claude/skills` 是**整目录** symlink → 中央库。在里面新建目录物理上就是写中央库，第 2 条自动满足，只需更新索引 + commit。
   - **Codex**：`~/.codex/skills/` 下是**逐个 skill 的 symlink**（`.system` 由 codex 自管，不进中央）。在这个目录里直接 `mkdir` 出来的是**真实目录，中央完全无感知**——必须把目录移进 `/Users/wesker/.ai-prompt/skills/<name>/`，再跑 `tools/sync-codex-skills.sh` 建链接。中央 commit 时 pre-commit 会自动跑一次同步。
   - **其它运行时**（agy / DSH 等）：没有 symlink，一律按第 2 条手工同步。
6. **只信实测，不信推断**：不确定当前运行时是哪种布局时，先 `ls -la <runtime-skills>` 看一眼是 symlink 还是真实目录，再决定要不要手工同步。跑 `tools/doctor.sh` 可一次性体检四个入口、两组 symlink 和索引一致性。

## Native Entrypoints

不同 AI 工具会读取不同的私有目录、项目级文件或全局入口设置。那些入口只需要保留很薄的一层：

```text
Read /Users/wesker/.ai-prompt/router.md first, then follow it.
```

目标不是让其它 AI 读取这个仓库，而是让它们读取已经部署好的 `/Users/wesker/.ai-prompt/router.md`。如果某个运行时不支持自动入口文件，就在第一次对话里显式要求它读取本文件。
