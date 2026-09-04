# MCP 笔记（去中心化 + 本地状态缓存）

MCP 仍由**各运行时各自配置、各自管理**。中央只保存：

1. 使用纪律；
2. 已知 server 的跨机器接入原则；
3. 已验证的服务固有坑。

**某台机器到底配没配、命令在哪里、wrapper 在哪、transport 最终用什么、是否已授权**，全部属于机器事实，写 `.local/runtime.json` / `.local/state.json`，禁止在本文件写用户名和本机绝对路径。

## 统一优先级：会话事实 > 本地缓存 > discovery

任务需要 MCP 时按以下顺序，命中上一级就停：

1. **当前会话已暴露该 MCP 工具** → 直接调用，不碰 add / authenticate / 启动命令。
2. 工具没暴露，但 `.local/state.json` 已记录该 runtime + server 已配置且 locator/transport 仍有效 → 只做最小连接/启动检查，不重新安装、不重新找教程。
3. 没缓存或缓存失效 → 才运行 `<runtime> mcp list` / 查该 runtime 配置，确认是否已配置。
4. 确实未配置 → 才考虑新增；安装、授权、改配置前先说明影响并取得用户确认。
5. 首次成功后把**非敏感**结果写回 `.local/`，避免下一轮重复探测。

推荐 state 结构：

```json
{
  "mcp": {
    "<runtime>": {
      "<server>": {
        "configured": true,
        "transport": "http|stdio",
        "status": "verified",
        "last_verified": "<time>"
      }
    }
  }
}
```

机器上的 command / wrapper / executable path 放 `runtime.services.<server>`，不要放中央文档。

OAuth 类 server 报 `Needs authentication` **不等于要重新授权**。先检查 App/服务端登录状态、旧回跳是否尚未完成、本地 state 是否已有成功授权记录；不要每轮生成新授权 URL 把上一轮作废。

## HTTP MCP 字段名——各运行时不同

| 运行时 | HTTP URL 字段 |
| --- | --- |
| Claude Code CLI | `--transport http` flag |
| Codex TOML | `url` |
| Gemini CLI / `agy` JSON | `serverUrl` |
| Antigravity IDE JSON | `serverUrl` |
| opencode JSON | `type: "remote"` + `url` |

具体 endpoint 若是机器/本地 App 可变端口，缓存进 runtime；不要在中央假定固定值。

## 已知 server

### `lark` / 飞书

用途：飞书/Lark 云文档与知识库读取。

跨机器原则：

- OAuth refresh token 会轮换，必须避免多个独立 stdio 进程同时持有同一 refresh token。
- 推荐共享 HTTP 单实例；实例 endpoint/端口属于机器配置，首次验证后写 runtime。
- 单实例内部仍需 single-flight：同一时刻只允许一个 refresh 在途，其余并发复用结果；不要用定时保活代替。
- 前提是 App 侧已经完成 OAuth 登录且 App 在运行。
- `Needs authentication` 时先查 App 登录态和已有授权，不要直接重新授权。
- 判活应探 MCP endpoint；根路径或 `/health` 返回 404/`Cannot GET` 不足以判服务坏。
- 只有不支持 HTTP transport 的运行时才考虑 stdio wrapper；wrapper 的机器绝对路径写 runtime。

Typical tools：`wiki_v2_space_getNode`、`docx_v1_document_rawContent`、`wiki_v1_node_search`、`docx_builtin_search`、`drive_v1_permissionMember_create`。

读 wiki：URL `/wiki/<token>` → `wiki_v2_space_getNode` 得 `obj_token` → `docx_v1_document_rawContent`。直链 `/docx/<token>` 可直接使用 token。

图片读取需要 `docx.v1.documentBlock.list` + `drive.v1.media.batchGetTmpDownloadUrl`。若只得到 `image.png` 占位，检查当前 runtime 的 tools 白名单。

### `figma`

用途：Figma 设计稿读取（Framelink figma-developer-mcp，PAT + stdio）。

- 静态 PAT 不自动轮换，多客户端各自 spawn stdio 不会像 Lark 那样互毁 refresh token，因此不要求共享单实例 HTTP。
- PAT/Keyring 属于本机配置；server wrapper / Python 路径全部写 runtime，不在中央写死。
- GET `/v1/me` 返回 403 **不能单独判 PAT 失效**；只有文件读权限的 token 也可能 403。
- 官方 Dev Mode MCP 需要对应付费席位；当前第三方 PAT 方案仍是可用 fallback。

Typical tools：`get_figma_data`、`download_figma_images`。

### `chrome-devtools`

用途：浏览器页面操作、元素检查、console/network、性能调试。

推荐命令形态：

```text
npx -y chrome-devtools-mcp@latest --no-usage-statistics --isolated
```

- `--isolated` 使用独立临时 profile，避免抢用户 Chrome 锁和堆僵尸进程。
- 不要为了“顺手验证”主动启动；任务确实需要时才用，用完清理自己启动的实例，绝不动用户自己的 Chrome。
- 先 `list_pages` / `select_page` 确认目标页。
- 需要复用用户登录态时再考虑 `--autoConnect` 或 `--browser-url=...`，与 isolated 按需二选一。
- 前端调试优先 DOM/selector/computed style/console/network；只有视觉事实需要时才截图。

### `ado-work-items` / `adoWorkItems`

Azure DevOps work items MCP，属于可选 fallback。

- 对 `*.cg1alias.com` 工单/PR，优先 `ado-pr` skill；它会复用本机已验证的 PAT/CLI/REST strategy。
- 只有 `ado-pr` 当前机器不可用，或用户明确要求 MCP 时才用本 MCP。
- 后台 wrapper / Python 路径属于机器配置，首次验证后写 `runtime.services.ado-work-items`。

### `serena`

代码语义/符号导航。入口不明确、调用链长、跨文件关系复杂时使用。

推荐命令**形态**：

```text
<serena-executable> start-mcp-server --context=claude-code --project-from-cwd --enable-web-dashboard=false --log-level=WARNING
```

`<serena-executable>` 的实际路径写 runtime。

- `--context` 是 serena 的固定枚举，不是“当前运行时名字”；不确定就跑 `serena start-mcp-server --help`，不要猜。
- Typical tools：`initial_instructions`、`activate_project`、`get_symbols_overview`、`find_symbol`、`find_referencing_symbols`、`find_declaration`、`get_diagnostics_for_file`。
- 不替代源码阅读和测试；只作为候选入口/关系导航。

### `node_repl`

Node 持久 REPL，辅助浏览器/脚本自动化。运行时若原生暴露，直接使用；不要重复配置。

### 搜索类 MCP

`wigolo` / `tavily` / `duckduckgo` / `brave` 等各运行时按需自配。搜索纪律见 `capabilities/search.md`；实际安装状态、命令和 credential locator 走 `.local/`。

## Discovery 成功后的写回纪律

应该缓存：

- server 已配置 / 已验证；
- runtime 名；
- transport；
- endpoint（如果是本机 endpoint）；
- wrapper / executable locator；
- OAuth 是否已成功完成；
- 当前机器需要的特殊启动侧/环境变量 locator。

禁止缓存：

- access token / refresh token / PAT / cookie / secret 正文；
- 一次性 OAuth code；
- 本轮任务临时参数。

如果缓存执行失败，以当前实际输出为准，重新 discovery；跑通后覆盖旧缓存，而不是在中央文档追加“某某机器例外”。

## 已知但不可用/受限

- `figma-remote-mcp`：官方 Dev Mode MCP 受席位限制；可继续使用第三方 PAT 方案。

## Runtime Plugins（非 MCP）

GitHub、Browser、Chrome、Computer Use、Documents、Spreadsheets、Presentations 等若由当前运行时原生/插件系统暴露，属于**当前会话事实**，优先级高于本地缓存，不要因为中央文档提到过就主动安装。
