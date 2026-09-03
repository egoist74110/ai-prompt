# MCP 笔记（去中心化）

规则：MCP 由**各运行时各自配置、各自管理**，本文件不维护"哪个运行时配了什么"的清单，也不做对账。任务需要 MCP 时，先按下面「用已有的，别重新拉」排查；确需新增/授权/改配置时，必须先说明原因、命令、影响范围，得到用户确认后再执行。本文件只保留两类东西：① 纪律；② 已知 server 的**推荐接法 + 踩坑笔记**（自己接入时照推荐来，避免重蹈覆辙）。

## 纪律：用已有的，别重新拉（最常见的错误顺序，务必照此判断）

接入一个 MCP 前，先按「已暴露工具 → 已配置 server → 需新增」三级递降排查，命中上一级就停，不要跳到下一级：

1. 会话已暴露该 MCP 工具 → 直接调，**完全不要**碰 add / authenticate / 启动命令。
2. 工具没暴露但 `<runtime> mcp list`（如 `claude mcp list`）已列出该 server → 它已配置，**绝不再 add**（会报 "already exists"）；按下方该 server 的「排查顺序」处理其状态。
3. 既没暴露也没配置 → 才考虑新增，且先征得用户同意，并按下方推荐接法配置。

- OAuth 类 server 报 "Needs authentication" **不等于要重新授权**：先判断是不是 App 侧未登录、或上一次授权回跳还没完成；client 侧授权流整个接入周期**只走一次**，不要每轮重新生成新授权 URL 把上一次作废。

## HTTP MCP 字段名——各运行时不同，写错会报 "serverURL or command must be specified"

| 运行时 | HTTP URL 字段 | 示例 |
| --- | --- | --- |
| Claude Code CLI | `--transport http` flag | `claude mcp add --transport http lark <url>` |
| Codex TOML | `url` | `url = "http://localhost:3000/mcp"` |
| Gemini CLI / `agy` JSON | `serverUrl` | `"lark": {"serverUrl": "http://localhost:3000/mcp"}` |
| Antigravity IDE JSON | `serverUrl` | `"lark": {"serverUrl": "http://localhost:3000/mcp"}` |
| opencode JSON | `type: "remote"` + `url` | `{"type":"remote","url":"http://localhost:3000/mcp","enabled":true}` |

## 已知 server：推荐接法 + 踩坑笔记

- `lark` / `飞书`: 飞书/Lark 云文档与知识库读取。
  - **必须走 App 托管的共享 HTTP 实例**（`http://localhost:3000/mcp`，端口可在 App 设置改）。Lark 用 OAuth user_access_token，refresh_token 每次刷新即轮换，两层保障缺一不可：
    1. **单实例**：不能各自 spawn stdio 进程——多进程并发各自持有同一 refresh_token 去刷，第一个轮换掉、其余拿旧值 → 20038。
    2. **单进程内 single-flight**：单实例只消掉多进程竞争，消不掉单进程内的并发刷新。令牌过期后第一波并发调用会同时触发刷新路径，若客户端库无去重锁，同样 20038。刷新路径必须 single-flight：同一时刻只放一个刷新在途，并发其余复用同一 in-flight Promise/Future。库缺锁时用 `NODE_OPTIONS=--require <preload>` 注入补丁包住刷新方法（方法名不存在时静默跳过，不要把 server 带挂）。不要用定时保活替代 single-flight。
  - **前提**：先在 App UI 完成 OAuth 登录，确认 App 已在运行。
  - **排查顺序**（看到 "Needs authentication" 别条件反射重新授权）：
    1. 会话已暴露 `mcp__lark__*` 工具 → 直接调，**不要** add / authenticate。
    2. `<runtime> mcp list` 已列出 lark → server 已配置，**绝不再 add**（必报 "already exists"）。
    3. "Needs authentication" → token 在 **App 侧**。先确认 App 在跑且已登录；client 侧授权流**整个接入周期只走一次**，**不要每轮重新生成新授权 URL**（新 URL 作废上一次，用户永远跳不完）。回跳页报连接错误时，让用户贴地址栏完整 `…/callback?code=…` URL 收口，而不是重发授权。
    4. `curl localhost:3000/` 或 `/health` 返回 "Cannot GET" 是**正常的**——只有 `/mcp` 是 MCP 端点，根路径/`health` 本就 404，判活探 `/mcp`。
  - Fallback（仅不支持 HTTP transport 的运行时）: stdio wrapper `mcp_lark_server.py`，**同一时间只允许一个客户端用此模式**。
  - Typical tools: `wiki_v2_space_getNode`（wiki 链接 token → 实际 docx token）、`docx_v1_document_rawContent`（取正文）、`wiki_v1_node_search`、`docx_builtin_search`、`drive_v1_permissionMember_create`。
  - Workflow: 读 wiki 链接（URL 里 `/wiki/<token>`）先用 `wiki_v2_space_getNode` 拿 `obj_token`，再用 `docx_v1_document_rawContent` 取正文；云文档直链（`/docx/<token>`）直接用该 token。
  - 图片: 工具集需含 `docx.v1.documentBlock.list` + `drive.v1.media.batchGetTmpDownloadUrl`。若 `rawContent` 把图片显示成 `image.png` 占位名，说明该运行时挂的 lark 用了更窄的 `tools` 列表，需放开这两个工具并重连。
- `figma`: Figma 设计稿读取（Framelink figma-developer-mcp，PAT 方案，stdio 即可）。
  - **架构**：Figma 用静态 PAT（不自动轮换），多客户端各自 spawn stdio 进程不会互毁 token，**不需要**单实例 HTTP（与 Lark 的区别）。
  - 推荐命令：`/Users/wesker/my-own-script/.venv/bin/python /Users/wesker/my-own-script/app_figma/mcp_figma_server.py`
  - **前提**：先在 App UI > MCP配置 > Figma MCP 填入 PAT（存 keyring）。PAT 最长 90 天，到期重新生成，App 显示剩余天数。
  - Typical tools: `get_figma_data`、`download_figma_images`。
  - **踩坑**：PAT 有效性**以本地记录的设置日期+有效期为准**；GET `/v1/me` 返回 403 **不代表 token 失效**——只有文件读权限的 token 调此接口也会 403，不能据此判失效。官方 Dev Mode MCP 需 Dev/Full 付费席位，当前走第三方 PAT 方案。
- `chrome-devtools`: 浏览器页面操作、元素检查、console/network、性能调试。
  - 推荐命令：`npx -y chrome-devtools-mcp@latest --no-usage-statistics --isolated`（`--isolated`：独立临时 profile，退出即清，不抢用户 Chrome 锁、不堆僵尸进程）。
  - **不要自顾自开浏览器**：仅在任务确实需要、且用户点名或任务明显匹配时才启动；不要为"顺手验证"主动 spawn。用完即止，清理残留进程，**绝不动用户自己的 Chrome**。
  - 先 `list_pages` / `select_page` 确认目标页，不要假设当前页面正确。需要复用用户 Chrome 登录态时用 `--autoConnect` 或 `--browser-url=http://127.0.0.1:9222`（与 `--isolated` 互斥，按需取舍）。
  - Frontend workflow: 元素优先。调试前端先用 snapshot / selector / `evaluate_script` 读取关键 DOM、文本、class、`getBoundingClientRect()`、`getComputedStyle()`、console、network。禁止默认全量 snapshot、全页 DOM dump；先把范围缩到目标区域再取关键字段。元素/样式/console/network 能确认事实就不截图；只有确认遮挡、对齐、颜色、响应式等视觉事实时才截图。
- `ado-work-items` / `adoWorkItems`: Azure DevOps work items（依赖 my-own-script 后台脚本常驻）。
  - **优先级低于 `ado-pr` skill**（见 `capabilities/skills.md`）：涉及 `*.cg1alias.com` 的工单/PR 读写优先 `ado-pr`（钥匙串 PAT + az CLI 直连，连通性更稳），不要因为这个 MCP"已暴露在会话里"就默认走它。仅当 skill 不可用（无钥匙串/az CLI 的环境）或用户明确要 MCP 时才用。
  - 推荐命令：`/Users/wesker/my-own-script/.venv/bin/python /Users/wesker/my-own-script/app_ado/mcp_ado_work_items_server.py`
- `serena`: 代码语义/符号导航。入口不明确、调用链长、跨文件关系复杂时，辅助定位候选文件/类/函数/引用/诊断。
  - 推荐命令：`/Users/wesker/.local/bin/serena start-mcp-server --context=<runtime> --project-from-cwd --enable-web-dashboard=false --log-level=WARNING`（env PATH 需含 `/Users/wesker/.local/bin`）。
  - Typical tools: `initial_instructions`、`activate_project`、`get_symbols_overview`、`find_symbol`、`find_referencing_symbols`、`find_declaration`、`get_diagnostics_for_file`。
  - Guardrails: 不替代源码阅读和测试；只提供候选入口和关系线索，关键事实必须回到源码/命令输出/验证结果核对。用户已给出精确文件/模块，或任务很小直接读文件更快时，不必使用。语言服务不可用时退回文本搜索 + 读文件 + 现有工程 skills。
- `node_repl`: Node 持久 REPL，辅助浏览器/脚本自动化（Codex 的由 ChatGPT.app 自动注入，无需手动配置）。
- 搜索类（`wigolo` / `tavily` / `duckduckgo` / `brave`）：各运行时按需自配，用法纪律见 `capabilities/search.md`，不在本文件重复。

## 已知但不可用

- `figma-remote-mcp`: Figma 官方 Dev Mode MCP；需 Dev/Full 付费席位，当前走第三方 PAT 方案，此条不可用。

## Runtime Plugins（运行时自带，非 MCP）

- GitHub、Browser、Chrome、Computer Use、Documents、Spreadsheets、Presentations（Codex/ChatGPT.app 侧由插件系统自动管理）。
