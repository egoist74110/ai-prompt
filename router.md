# AI Prompt Router

这是所有 AI Agent / 模型运行时的统一入口。任何运行时只要能读取本文件，就应按这里进入完整工作流。

## Root / Local State（先读，再往下）

- `AI_PROMPT_ROOT` = **本文件 `router.md` 所在目录**。
- 本仓库内所有相对路径都以 `AI_PROMPT_ROOT` 为基准解析。禁止根据某台机器的 `/Users/...`、`C:\Users\...` 等前缀做字符串替换。
- 机器差异、外部绝对路径、凭据定位方式写入本机 `.local/runtime.json`；已实测跑通的 strategy / MCP / API 行为写入 `.local/state.json`。两者都不得提交。
- 若 `.local/` 不存在且当前环境允许执行本仓库脚本，可运行 `python tools/runtime_state.py init`（macOS 只有 `python3` 时用 `python3`）。没有 Python 也不影响读取中央规则，只是不能使用这个辅助缓存工具。
- **禁止把 token、密码、cookie、私钥正文写入 local state**；只缓存“去哪里取”的 locator。

### 本地事实优先级

需要 Skill / MCP / 外部服务时统一按以下顺序：

1. 当前会话已经暴露的工具、当前命令实际输出、当前环境变量等**实时事实**。
2. `.local/runtime.json` / `.local/state.json` 中本机已经验证过的配置与经验。
3. 只有前两层无法解决，或缓存已经失效时，才做 discovery / 探测。
4. discovery 一旦成功，把可复用且非敏感的结果写回 `.local/`，后续直接复用，不要每次重走排障路径。

详细规范见 `config/README.md`。

## Read Order

1. 先读 `common.md`。
2. 直接处理完整问题时，再读 `models/high.md`。
3. 被明确要求做侦查、上下文收集、列路径、引用原文或机械执行时，只读 `models/scout.md`，不要再读 high。
4. 需要 skill/MCP 时，只先读索引：
   - `capabilities/skills.md`
   - `capabilities/mcp.md`
   - 交付前做交叉审查时读 `capabilities/cross-review.md`（触发条件见 `models/high.md` 的 Cross-Review Gate）
5. 需要网页搜索 / 获取外部信息时，先读 `capabilities/search.md`，不要自创搜索路径。

## Capability Loading

- 不要全量读取 `skills/`、`<runtime-skills>` 或所有外部 `SKILL.md`。
- 只有用户点名能力，或任务明显匹配索引里的 description / Use for，才读取对应文件。
- 需要安装、启用或新增 MCP / plugin / connector 前，必须先说明原因、命令/配置和影响范围，得到用户确认后再执行。
- 若某能力第一次在本机跑通，优先把**机器相关**的结果缓存到 `.local/state.json`；只有跨机器都成立的规则才回写中央 `SKILL.md` / capabilities 文档。

## Skill Contract（skill 唯一出生地）

`skills/` 是全部 skill 的**唯一正典库**，`capabilities/skills.md` 是它的索引。私有 skill 允许存在，但中央必须同步，保证任何运行时都用得上最新版：

1. **已有直接用**：用 skill 前先查索引；中央库里已有的 skill，直接读中央 `SKILL.md`，不要在自己运行时目录里再建/再读私有副本。
2. **新增必须同步**：可以先在自己运行时私有 skills 目录创建，但同一步内必须把完整目录同步到 `AI_PROMPT_ROOT/skills/<name>/`，并更新 `capabilities/skills.md`（跑 `tools/gen-index.py` 重新生成索引段，或手工补条目）。没同步完不算完成。
3. **更新改正典**：中央已有同名 skill → 直接改中央文件，不要在私有目录分叉；已有旧私有副本 → 更新中央后删掉私有副本。
4. **索引不许过期**：任何新增/删除/改名 skill 都必须伴随 `capabilities/skills.md` 变更；中央仓库（git）里改完记得 commit。
5. **运行时 skills 布局属于机器事实，不写死**：Claude/Codex/其它运行时可能是整目录 symlink、逐 skill symlink、junction 或真实目录。优先读 `.local/runtime.json` 中已记录布局；没有记录时实测一次，成功后缓存。同步中央时再按当前布局处理。
6. **只信实测，不信推断**：缓存与当前实际不符时，以当前实际为准并刷新缓存。跑 `tools/doctor.sh` 可做仓库部署体检。

## Native Entrypoints

不同 AI 工具会读取不同的私有目录、项目级文件或全局入口设置。入口只需要保留很薄的一层，让运行时读取**当前部署位置**的 `router.md`：

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

入口文件可以使用该运行时支持的 `~` / 环境变量 / 当前实际绝对路径，但**中央仓库不再规定某个用户名或 home 路径**。如果某个运行时不支持自动入口文件，就在第一次对话里显式要求它读取本文件。
