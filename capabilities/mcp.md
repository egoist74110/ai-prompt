# MCP Index

规则：先确认任务需要 MCP，再使用对应能力。`Configured MCP` 表示本机已知、可由运行时配置或本索引命令启动的能力；任务明确需要时应优先直接访问它，不要先读私有实现脚本绕路。若当前会话已暴露对应 MCP 工具，直接调用工具；若未暴露但索引给出本机命令，可启动该命令做轻量 `tools/list`/任务调用。只有新增、安装、授权、或写入/修改运行时 MCP 配置前，才必须先说明原因、命令/配置和影响范围并取得用户确认。

**用已有的，别重新拉**（最常见的错误顺序，务必照此判断）：接入一个 MCP 前，先按「已暴露工具 → 已配置 server → 需新增」三级递降排查，命中上一级就停，不要跳到下一级。
1. 会话已暴露该 MCP 工具 → 直接调，**完全不要**碰 add / authenticate / 启动命令。
2. 工具没暴露但 `<runtime> mcp list`（如 `claude mcp list`）已列出该 server → 它已配置，**绝不再 add**（会报 "already exists"）；按下方该 server 的「接入/排查顺序」处理其状态。
3. 既没暴露也没配置 → 才考虑新增，且按确认规则先征得用户同意。
- OAuth 类 server 报 "Needs authentication" **不等于要重新授权**：先判断是不是 App 侧未登录、或上一次授权回跳还没完成；client 侧授权流整个接入周期**只走一次**，不要每轮重新生成新授权 URL 把上一次作废。

## HTTP MCP 字段名——各运行时不同，写错会报 "serverURL or command must be specified"

| 运行时 | HTTP URL 字段 | 示例 |
| --- | --- | --- |
| Claude Code CLI | `--transport http` flag | `claude mcp add --transport http lark <url>` |
| Codex TOML | `url` | `url = "http://localhost:3000/mcp"` |
| Gemini CLI / `agy` JSON | `serverUrl` | `"lark": {"serverUrl": "http://localhost:3000/mcp"}` |
| Antigravity IDE JSON | `serverUrl` | `"lark": {"serverUrl": "http://localhost:3000/mcp"}` |
| opencode JSON | `type: "remote"` + `url` | `{"type":"remote","url":"http://localhost:3000/mcp","enabled":true}` |

## Configured MCP
- `ado-work-items` / `adoWorkItems`: Azure DevOps work items。
  - **优先级低于 `ado-pr` skill**：涉及 azuredevops.cg1alias.com 的工单/PR 读写，若当前运行时能加载 `~/.claude/skills/ado-pr/SKILL.md`（钥匙串 PAT + az CLI 直连，无额外后台依赖），优先用它，不要因为这个 MCP"已暴露在会话里"就默认走它——它依赖 my-own-script 后台脚本常驻，连通性不如直连稳定。仅当该 skill 不可用（非 Claude Code 运行时、或用户明确要用 MCP）时才用这个 MCP。
  - Example config:
    ```toml
    [mcp_servers.adoWorkItems]
    command = "/Users/wesker/my-own-script/.venv/bin/python"
    args = ["/Users/wesker/my-own-script/app_ado/mcp_ado_work_items_server.py"]
    ```
- `lark` / `飞书`: 飞书/Lark 云文档与知识库读取。
  - **架构**：Lark 走 OAuth user_access_token，refresh_token 每次刷新即轮换，有两层保障缺一不可：
    1. **单实例**：必须连 App 托管的共享 HTTP 实例，不能各自 spawn stdio 进程——多进程并发各自持有同一 refresh_token 去刷，第一个轮换掉、其余拿旧值 → 20038。
    2. **单进程内 single-flight**：单实例只消掉多进程竞争，消不掉单进程内的并发刷新。令牌过期后第一波并发调用会同时触发刷新路径，若客户端库无去重锁，同样会以同一 refresh_token 各自发请求 → 第一个成功轮换，其余失败 → 20038。刷新路径必须 single-flight：同一时刻只放一个刷新在途，并发其余复用同一 in-flight Promise/Future 等结果。
    - 库缺锁时用 `NODE_OPTIONS=--require <preload>` 注入补丁包住刷新方法（方法名不存在时静默跳过，不要把 server 带挂）。
    - 不要用定时保活替代 single-flight：库通常到期才刷、无提前量，保活只缩小窗口，消不掉竞争。
    - 刷新失败时页面给一键重登兜底。
  - Example config（HTTP，主要接入方式——字段名因运行时而异，见上表）:
    ```bash
    # Claude Code
    claude mcp add --scope user --transport http lark http://localhost:3000/mcp
    ```
    ```toml
    # Codex
    [mcp_servers.lark]
    url = "http://localhost:3000/mcp"
    ```
    ```json
    // Gemini CLI (agy) / Antigravity IDE — 同一字段名
    {"lark": {"serverUrl": "http://localhost:3000/mcp"}}
    ```
  - **前提**：先在 App UI 完成 OAuth 登录，确认 App 已在运行（HTTP server 由 App 托管）。端口默认 3000，可在 App 设置里改。
  - **接入/排查顺序**（看到 "Needs authentication" 别条件反射重新授权，照此走）：
    1. 会话已暴露 `mcp__lark__*` 工具 → 直接调，**不要** add / authenticate。
    2. `claude mcp list` 已列出 lark → server 已配置，**绝不再 `claude mcp add`**（必报 "already exists"）。
    3. 状态 "Needs authentication" → token 在 **App 侧**（HTTP server 由 App 托管）。先确认 App 在跑且已在 App UI 完成 OAuth 登录；client 侧 `authenticate` 流**整个接入周期只走一次**，给出 URL 后等用户在浏览器完成回跳，**不要每轮重新生成新授权 URL**（新 URL 会作废上一次，用户永远跳不完）。回跳页报连接错误时，让用户贴地址栏完整 `…/callback?code=…` URL，用 `complete_authentication` 收口，而不是重发授权。
    4. `curl localhost:3000/` 或 `/health` 返回 "Cannot GET" 是**正常**的——只有 `/mcp` 是 MCP 端点，根路径/`health` 本就 404，**不能据此判 server 没起或要重连**；判活探 `/mcp`。
  - Fallback（仅不支持 HTTP transport 的运行时）: stdio wrapper `mcp_lark_server.py`，已内置进程监管，但**同一时间只允许一个客户端用此模式**，避免并发刷新 token 互毁。
  - Typical tools: `wiki_v2_space_getNode`（wiki 链接 token → 实际 docx token）、`docx_v1_document_rawContent`（取文档纯文本）、`wiki_v1_node_search`、`docx_builtin_search`、`docx_builtin_import`、`drive_v1_permissionMember_create`。
  - Workflow: 读 wiki 链接（URL 里 `/wiki/<token>`）先用 `wiki_v2_space_getNode` 拿到 `obj_token`，再用 `docx_v1_document_rawContent` 以该 token 取正文。云文档直链（`/docx/<token>`）可直接用该 token 取正文。
  - 图片: server **支持读图**——需要工具集含 `docx.v1.documentBlock.list`（列图片 block 拿 image token）+ `drive.v1.media.batchGetTmpDownloadUrl`（token→临时下载 URL），脚本 `DEFAULT_TOOLS` 已含这两个。若当前会话只暴露了纯文本工具、`rawContent` 把图片显示成 `image.png` 占位名，说明该运行时挂的 lark 用了更窄的 `tools` 列表，需在 lark 设置里放开这两个工具并重连，再 block 列举 + 取临时 URL 下载原图。
  - Guardrails: MCP 是**各运行时各自配置**——本索引列出不等于当前运行时已挂载。启动失败时再读取本机脚本/配置排查。写入运行时配置前仍需用户确认。
- `figma`: Figma 设计稿读取（Framelink figma-developer-mcp，PAT 方案）。
  - **架构**：Figma 用静态 PAT（不自动轮换），多客户端各自 spawn stdio 进程不会互毁 token，保持 stdio 模式即可；**不需要**单实例 HTTP（与 Lark 的区别）。每个客户端独立进程，资源略多但不影响正确性。
  - Example config:
    ```bash
    claude mcp add figma --scope user -- /Users/wesker/my-own-script/.venv/bin/python /Users/wesker/my-own-script/app_figma/mcp_figma_server.py
    ```
    ```toml
    # Codex
    [mcp_servers.figma]
    command = "/Users/wesker/my-own-script/.venv/bin/python"
    args = ["/Users/wesker/my-own-script/app_figma/mcp_figma_server.py"]
    ```
  - **前提**：先在 App UI > MCP配置 > Figma MCP 填入 PAT 并保存到 keyring。PAT 最长 90 天，到期需重新生成，App 会显示剩余天数提醒。
  - Typical tools: `get_figma_data`（获取 Figma 文件/节点设计数据）、`download_figma_images`（导出节点为图片）。
  - Guardrails: PAT 有效性**以本地记录的设置日期+有效期为准**；GET `/v1/me` 返回 403 **不代表 token 失效**——只有文件读权限的 token 调此接口也会 403，Figma 对"无效 token"和"权限不足的有效 token"返回相同错误码，不能据此判失效。官方 Dev Mode MCP 需 Dev/Full 付费席位，当前走第三方 PAT 方案。本机私有脚本，换机器先改路径。
- `chrome-devtools`: 浏览器页面操作、元素检查、console/network、性能调试。配置位置因运行时而异，按当前 agent 的 MCP 配置文件为准。
  - Command: `npx -y chrome-devtools-mcp@latest --no-usage-statistics --isolated`（`--isolated`：每次用独立临时 profile，退出即清，不抢用户 Chrome 锁、不堆积僵尸进程）。
  - **不要自顾自开浏览器**：仅在任务确实需要浏览器、且用户点名或任务明显匹配时才启动 MCP 浏览器；不要为"顺手验证"主动 spawn。用完即止，避免关闭后残留进程。残留时排查 `chrome-devtools-mcp` 相关进程清理，**绝不动用户自己的 Chrome**。
  - Guardrails: 不要假设当前页面正确；先 `list_pages` / `select_page` 确认目标页。若需要复用用户正在使用的 Chrome 登录态，可使用 `--autoConnect` 或 `--browser-url=http://127.0.0.1:9222`（注意 `--isolated` 与连接现有 Chrome 互斥，按需取舍）。
  - Frontend workflow: 元素优先。调试前端时先用 snapshot / selector / `evaluate_script` 读取关键 DOM、文本、class、`getBoundingClientRect()`、`getComputedStyle()`、console、network。禁止默认全量 snapshot、全页 DOM dump 或一次性读取所有元素；必须先根据路由、用户描述、选择器、可见文本、console/network 错误把范围缩到目标区域，再只取关键字段。若通过元素、样式、尺寸、console/network 已能确认事实，不截图；只有元素读取无法确认视觉事实时，才截图确认遮挡、对齐、颜色、响应式等问题。
  - Fallback: 若运行时提供 Browser/Chrome 类插件，可处理 localhost / 普通网页验证；需要用户 Chrome 登录态、扩展、现有标签页时用 Chrome 插件或 `chrome-devtools` 的 running Chrome 连接模式。
- `node_repl`: Node 持久 REPL；可辅助浏览器/脚本自动化；配置位置因运行时而异。
- `serena`: 代码语义/符号导航 MCP；用于在入口不明确、调用链较长、跨文件关系复杂时，辅助定位候选文件、类、函数、引用、声明和诊断。
  - Example config:

    ```toml
    [mcp_servers.serena]
    command = "/Users/wesker/.local/bin/serena"
    args = ["start-mcp-server", "--context=<runtime>", "--project-from-cwd", "--enable-web-dashboard=false", "--log-level=WARNING"]

    [mcp_servers.serena.env]
    PATH = "/Users/wesker/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    ```

  - Trigger: 用户描述模糊、没有给出明确文件/模块、需要理解跨文件调用关系、或要做符号级修改时，由高级模型自行判断是否值得使用。
  - Typical tools: `initial_instructions`、`activate_project`、`get_symbols_overview`、`find_symbol`、`find_referencing_symbols`、`find_declaration`、`get_diagnostics_for_file`。
  - Guardrails: 不替代源码阅读和测试；Serena 只提供候选入口和关系线索，关键事实必须回到源码、命令输出或验证结果核对。用户已给出精确文件/模块，或任务很小、直接读文件更快时，不必使用。索引/语言服务不可用时，退回文本搜索 + 读取文件 + 现有工程 skills。

## External / Not Configured

- `figma-remote-mcp`: Figma 官方 Dev Mode MCP；需 Dev/Full 付费席位，当前走第三方 PAT 方案，此条不可用。

## Runtime Plugins
- GitHub、Browser、Chrome、Computer Use、Documents、Spreadsheets、Presentations。
- 相关 skill 入口见 `capabilities/skills.md`。
