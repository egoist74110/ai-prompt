# AI Prompt Router

这是所有 AI Agent / 模型运行时的统一入口。任何运行时只要能读取本文件，就应按这里进入完整工作流。

## Root / Local State（先读，再往下）

- `AI_PROMPT_ROOT` = **本文件 `router.md` 所在目录**。
- 本仓库内所有相对路径都以 `AI_PROMPT_ROOT` 为基准解析。禁止根据某台机器的 `/Users/...`、`C:\Users\...` 等前缀做字符串替换。
- `.local/runtime.json` 保存“这台机器怎么做”：OS、外部绝对路径、可执行文件、运行时/Skill/MCP/Search locator、credential locator、执行侧等。
- `.local/state.json` 保存“这台机器已经验证过什么”：Skill strategy、MCP/search/headless 可用性、API/网络行为、最近成功/失败及失效条件等。
- 两者都不得提交。
- 若 `.local/` 不存在且当前环境允许执行本仓库脚本，可运行 `python tools/runtime_state.py init`（只有 `python3` 时用 `python3`）。没有 Python 仍可读取中央规则，只是不能自动维护本地缓存。
- **禁止把 token、密码、cookie、私钥正文写入 local state/runtime**；只能缓存“去哪里取”的 credential locator。

### 本地事实优先级

需要 Skill / MCP / Search / 外部 API / headless runtime / 本地工具时统一按以下顺序：

1. 当前会话已经暴露的工具、当前命令实际输出、当前环境变量等**实时事实**。
2. `.local/runtime.json` / `.local/state.json` 中本机已经验证过的配置与经验。
3. 只有前两层无法解决，或缓存已失效时，才做 discovery / 探测。
4. discovery 成功后：
   - executable/path/transport/endpoint/config location/credential locator → 写 `runtime.json`；
   - strategy/verified/result/failure/retry condition → 写 `state.json`。
5. 后续直接复用；缓存实际执行失败时，以当前输出为准刷新缓存，而不是在中央文档追加“某机器例外”。

详细规范见 `config/README.md`。

## Read Order

1. 先读 `common.md`。
2. 直接处理完整问题时，再读 `models/high.md`。
3. 被明确要求做侦查、上下文收集、列路径、引用原文或机械执行时，只读 `models/scout.md`，不要再读 high。
4. 需要 Skill/MCP 时，只先读索引/规则：
   - `capabilities/skills.md`
   - `capabilities/mcp.md`
   - 交付前做交叉审查时读 `capabilities/cross-review.md`（触发条件见 `models/high.md`）
5. 需要网页搜索/外部信息时，先读 `capabilities/search.md`。

## Capability Loading

- 不要全量读取 `skills/`、`<runtime-skills>` 或所有外部 `SKILL.md`。
- 只有用户点名能力，或任务明显匹配索引里的 description / Use for，才读取对应文件。
- 当前会话已有原生/插件工具且适合任务时，优先实时工具事实，不因为中央存在同名 Skill/MCP 就重复启动另一套。
- 需要安装、启用、新增 MCP/plugin/connector，或扩大权限前，必须先说明原因、命令/配置和影响范围，取得用户确认。
- 第一次在本机跑通某能力后，把**机器相关 locator 写 runtime、验证经验写 state**；只有跨机器成立的规则才回写中央 `SKILL.md` / capabilities 文档。

## Skill Contract（skill 唯一出生地）

`skills/` 是全部自定义 Skill 的**唯一正典库**，`capabilities/skills.md` 是发现索引：

1. **已有直接用**：先查索引；中央已有的 Skill 直接读 `skills/<name>/SKILL.md`，不要在运行时私有目录再维护第二份副本。
2. **新增必须同步**：运行时临时创建的新 Skill，同一步内必须迁回 `AI_PROMPT_ROOT/skills/<name>/`，再生成索引。没同步完不算完成。
3. **更新改正典**：中央已有同名 Skill → 直接改中央；旧私有副本应移除/改成链接，避免分叉。
4. **frontmatter 是唯一元数据源**：新增/删除/改名/改 description 后运行 `tools/gen-index.py`；`capabilities/skills.md` 不手工维护机器路径或第二套元数据。
5. **Skill 内路径相对 Skill 自身解析**：不要依赖 cwd，不要假定 `$CODEX_HOME`、`~/.claude`、某用户名或某运行时私有目录。
6. **运行时 skills 布局属于机器事实**：可能是整目录 symlink、逐 Skill symlink、junction 或真实目录。优先读 local runtime；没有记录才实测一次并缓存。
7. **只信实测，不信推断**：缓存与当前实际不符时刷新缓存。`tools/doctor.py` 是跨平台正典体检入口；`doctor.sh` 只是兼容包装。

## Native Entrypoints

不同 AI 工具会读取不同的私有目录、项目级文件或全局入口设置。入口只需要保留很薄的一层，让运行时读取**当前部署位置**的 `router.md`：

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

入口文件可以使用该运行时支持的 `~` / 环境变量 / 当前实际绝对路径，但中央仓库不规定某个用户名或 home。当前入口/skills 路径第一次验证后可缓存到 `.local/runtime.json`。
