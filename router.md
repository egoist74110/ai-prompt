# AI Prompt Router

这是所有 AI Agent / 模型运行时的统一入口。任何运行时只要能读取本文件，就应按这里进入完整工作流。

## Root / Local State（先读，再往下）

- `AI_PROMPT_ROOT` = **本文件 `router.md` 所在目录**。
- 本仓库内所有相对路径都以 `AI_PROMPT_ROOT` 为基准解析。禁止根据某台机器的具体用户目录前缀做字符串替换。
- `.local/runtime.json` 保存“这台机器怎么做”：OS、外部绝对路径、可执行文件、动态 runtime registry、Skill/MCP/Search locator、credential locator、执行侧等。
- `.local/state.json` 保存“这台机器已经验证过什么”：Skill strategy、MCP/search/headless 可用性、API/网络行为、最近成功/失败及失效条件等。
- 两者都不得提交。
- 若 `.local/` 不存在且当前环境允许执行本仓库脚本，可运行 `python tools/runtime_state.py init`（只有 `python3` 时用 `python3`）。没有 Python 仍可读取中央规则，只是不能自动维护本地缓存。
- **禁止把 token、密码、cookie、私钥正文写入 local state/runtime**；只能缓存“去哪里取”的 credential locator。

## Runtime Registry Contract

AI 运行时名称本身也是**本地数据**，不是中央代码常量。

- `config/runtime-templates.json` 只是首次初始化 starter template，不是永久支持名单。
- 真正可用的运行时来自 `.local/runtime.json.runtimes`。
- bootstrap、doctor、Skill 同步、交叉审查等消费者必须**遍历 registry**，禁止写 `if runtime == <某产品>` 这种产品名分支。
- runtime entry 可声明：`command_candidates`、`entry_candidates`、`skills_candidates`、`capabilities`、`skills_sync_mode`、`review.args`、`review.priority` 等。
- 用户可以注册任意新 runtime；新增工具不应要求修改中央 Python：

```text
python tools/runtime_state.py runtime add <runtime-id> --commands-json '["<command>"]'
```

完整字段见 `config/README.md`。

### 本地事实优先级

需要 Skill / MCP / Search / 外部 API / headless runtime / 本地工具时统一按以下顺序：

1. 当前会话**实际执行产生的事实**：成功/失败的工具调用结果、当前命令输出、当前环境变量。
2. `.local/runtime.json` / `.local/state.json` 中本机已经验证过的配置与经验。
3. 当前会话“暴露了某个工具”只表示**候选入口存在**，不等于该工具在当前 provider/订阅/credential 下可用；它不能覆盖本地已经验证的 `blocked` / `cooldown` / `unsupported` 状态。
4. 只有前两层无法解决，或缓存已满足失效/重试条件时，才做 discovery / 探测。
5. discovery 成功后：
   - executable/path/transport/endpoint/config location/credential locator → 写 `runtime.json`；
   - strategy/verified/result/failure/retry condition → 写 `state.json`。
6. 后续直接复用；缓存实际执行失败时，以当前输出为准刷新缓存，而不是在中央文档追加“某机器例外”。

详细规范见 `config/README.md`。

## Search Lane Contract

需要联网搜索时，**必须先选 Search Lane，再选工具**；禁止把云端搜索和本机搜索混成一个候选池。

```text
hosting=cloud
→ lane=cloud-native
→ 默认只用当前云端平台/Provider 自带搜索

hosting=local|self-hosted
→ lane=local-managed
→ 默认只用用户本机配置并验证的搜索后端
```

- `unknown` 不是第三条路线；先做最小 discovery，确认 hosting/lane 并缓存到 `.local/runtime.json.search.contexts`，之后再搜索。
- 默认禁止跨 Lane fallback；只有用户明确要求或 context 明确设置 `allow_cross_lane_fallback=true` 才允许。
- 本地/self-hosted 模型即使会话暴露了云端 `web_search`，也不能据此调用；Cloud 模型也不应因为本机恰好配置了搜索 CLI/MCP 就绕去 local-managed lane。
- backend 的 blocked/cooldown/degraded 状态继续由 `.local/state.json` 持久化控制。
- 具体规则见 `capabilities/search.md`；可用 `tools/search_state.py` 维护 context/lane 和熔断。

## Read Order

1. 先读 `common.md`。
2. 直接处理完整问题时，再读 `models/high.md`。
3. 被明确要求做侦查、上下文收集、列路径、引用原文或机械执行时，只读 `models/scout.md`，不要再读 high。
4. 需要 Skill/MCP 时，只先读索引/规则：
   - `capabilities/skills.md`
   - `capabilities/mcp.md`
   - 交付前做交叉审查时读 `capabilities/cross-review.md`（触发条件见 `models/high.md`）
5. 需要网页搜索/外部信息时，先读 `capabilities/search.md`；先确定 Search Lane，再使用该 Lane 内的搜索能力。

## Capability Loading

- 不要全量读取 `skills/`、`<runtime-skills>` 或所有外部 `SKILL.md`。
- 只有用户点名能力，或任务明显匹配索引里的 description / Use for，才读取对应文件。
- 当前会话已有原生/插件工具且适合任务时，可以作为候选；但若本地 state 已验证该能力 blocked/cooldown/unsupported，应直接跳过，除非已满足其重试条件。
- 需要安装、启用、新增 MCP/plugin/connector，或扩大权限前，必须先说明原因、命令/配置和影响范围，取得用户确认。
- 第一次在本机跑通某能力后，把**机器相关 locator 写 runtime、验证经验写 state**；只有跨机器成立的规则才回写中央 `SKILL.md` / capabilities 文档。

## Skill Contract（skill 唯一出生地）

`skills/` 是全部自定义 Skill 的**唯一正典库**，`capabilities/skills.md` 是发现索引：

1. **已有直接用**：先查索引；中央已有的 Skill 直接读 `skills/<name>/SKILL.md`，不要在运行时私有目录再维护第二份副本。
2. **新增必须同步**：运行时临时创建的新 Skill，同一步内必须迁回 `AI_PROMPT_ROOT/skills/<name>/`，再生成索引。没同步完不算完成。
3. **更新改正典**：中央已有同名 Skill → 直接改中央；旧私有副本应移除/改成链接，避免分叉。
4. **frontmatter 是唯一元数据源**：新增/删除/改名/改 description 后运行 `tools/gen-index.py`；`capabilities/skills.md` 不手工维护机器路径或第二套元数据。
5. **Skill 内路径相对 Skill 自身解析**：不要依赖 cwd，不要假定任何 runtime-specific home、用户名或私有目录。
6. **运行时 skills 布局属于机器事实**：可能是整目录 symlink、逐 Skill symlink、junction、真实目录或根本不支持 Skill。以 registry 声明 + 当前实测为准。
7. **只信实测，不信推断**：缓存与当前实际不符时刷新缓存。`tools/doctor.py` 是跨平台正典体检入口；`doctor.sh` 只是兼容包装。

## Native Entrypoints

不同 AI 工具会读取不同的私有目录、项目级文件或全局入口设置。入口只需要保留很薄的一层，让运行时读取**当前部署位置**的 `router.md`：

```text
Read <current-ai-prompt-root>/router.md first, then follow it.
```

入口文件可以使用该运行时支持的 home 变量、环境变量或当前实际绝对路径，但中央仓库不规定某个产品的固定入口。候选入口来自 runtime registry，第一次验证后的实际路径写回 `.local/runtime.json`。
