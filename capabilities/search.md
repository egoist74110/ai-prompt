# 网页搜索策略（本机 macOS / Users/wesker）

> 正典副本。DSH 另有私有副本 `~/.dsh/AGENTS.md`（保留供 DSH 会话直接加载）；两边若冲突，以本文件为准。
> 当前运行时若已暴露对应 MCP 工具（DSH 会话暴露 `mcp__wigolo__*` / `mcp__tavily__*`），直接调工具；未暴露的运行时直接用各节的 bash 命令，效果等价。

## 0. 先自查：当前 API 有没有原生搜索（决定走哪套）

判断依据是**本次会话实际接入的模型/API**，不是哪个 AI 工具（Claude/Codex/DSH 都可能接不同 API，能力跟着 API 走）：

1. **当前 API 自带原生搜索**（带内置 web search 的云端 API，如 Claude / GPT / Gemini 系列；或会话工具列表里有模型/云端提供的**原生**搜索工具——不是 `mcp__*` 本地包装、不是 bash 脚本）→ **用它自己的原生搜索，下面「本地五路」整套不需要**。仅当原生搜索不可用、或结果明显弱/离题时，才降级用本地五路补查（bash 命令对任何运行时都可用）。
2. **当前 API 没有搜索能力**（本地/自托管模型，或没有内置联网搜索的云端 API）→ **必须走下面「本地五路」**（MCP 已暴露 → 用 MCP；未暴露 → 用各节 bash 命令）。**禁止回答"我没有联网能力 / 查不了天气"**——先按五路去查；所有后端都失败才说明具体原因。

实用判断信号：

- 会话工具列表里有原生搜索工具 → 有。
- **工具列表可能是延迟加载的**：有的运行时（如 Claude Code）把 `WebSearch` / `WebFetch` 放在"按需检索才出现"的延迟工具里，默认列表看不到 ≠ 没有。云端 API 运行时先按 API 能力判断、必要时先检索一次工具，**不要仅凭初始列表为空就断定没有原生搜索**然后白绕一圈本地路。
- 确认没有原生搜索工具 → 走本地路（本机永远可用，不赌"应该有原生搜索"）。
- 本地模型（自托管权重，如 Ollama / 本地部署）→ 一定没有，直接走本地路。

## 1. 搜索纪律（所有路径都必须遵守，含原生搜索）

查询纪律：

1. **缩小查询**：别用开放式长句（如 `TypeScript 7 native Go port release status`）。改成精确查询：`site:github.com/microsoft/typescript-go release`、`site:typescriptlang.org TypeScript 7`。
2. **开发技术优先官方域名**：软件版本、框架、SDK、开发者工具类问题，先查官网、官方 GitHub 仓库/Releases、官方厂商博客；搜不到再放宽到聚合器。
3. **一次只查一个事实**：不要让一次搜索处理多个概念。例：先查"X 是否发布"，再查"Y 的进展"。
4. **结果校验**：Top 3 结果的标题/摘要里没出现核心实体（如 `TypeScript`）→ 直接判无效并重搜，不硬拿垃圾结果回答。wigolo 的 `lexical_alignment` 分量为 0，或结果混入 localhost、无关语言内容、明显离题站点 → 同样判无效。
5. **两轮搜索**：第一轮普通搜索；结果离题就自动改写成带 `site:`、引号、GitHub repo 名的精确查询跑第二轮。

For software versions, releases, APIs, libraries, frameworks, and developer tools:

1. Prefer official documentation, official GitHub repositories/releases, and official vendor blogs.
2. Reject search results whose title/snippet does not contain the queried product/project name.
3. If the first search returns weak or unrelated results, retry with quoted entity names and `site:` filters for official domains.
4. Do not answer from unrelated search results.

## 2. 本地搜索路径（仅无原生联网能力时使用）

**4 条可用路 + 1 条已禁用（仅作记录，别当成"还没试的一路"）+ bash 兜底。** 其余文件里沿用的"本地五路"说法指的就是本节。

### 2.1 wigolo — 免费，第一轮通用首选

本地引擎在 `~/.wigolo`，无 key 无账单；DSH 会话已连 MCP（`mcp__wigolo__*`），其余运行时用 2.6 的 bash 命令。暴露的工具：

| 工具 | 用途 |
|---|---|
| search | 主搜索，返回带评分的证据片段 + 引用 |
| fetch | 抓单个 URL 转 markdown，支持 JS 渲染、auth 复用、交互动作 |
| crawl | 从种子 URL 爬多页（bfs/dfs/sitemap/map） |
| extract | 从页面抽结构化数据（表格/schema/metadata/brand） |
| cache | 查本地缓存，免网络；也支持检查页面变化 |
| find_similar | 找与某 URL 或概念相关的页面 |
| research / agent | 多步调研 |
| diff / watch | 版本对比 / 延迟轮询变更 |

**已知弱点**：`~/.wigolo/config.json` 未配置任何引擎，裸跑默认池（bing + duckduckgo 爬取式 + wikipedia + marginalia），实测会退化——marginalia 429 熔断、wikipedia 0 结果、bing 被 dedup 清空、Top 5 被 SEO 博客站占满。出现 `engine_pool.degraded: true` 且 Top 3 全是 SEO 博客 → 判弱结果，直接进第二轮（走 Tavily/Brave/GitHub）。

### 2.2 GitHub API — repo/release/代码类问题首选

`gh` CLI 已登录（有 token，5000 req/hr）。查仓库、版本、release、tag、代码时**直接走 GitHub，不过聚合器**：

```sh
gh search repos "typescript-go"
gh api repos/microsoft/typescript-go/releases --jq '.[0:3] | .[] | {tag_name, published_at}'
gh api repos/microsoft/typescript-go/tags --jq '.[0:5] | .[].name'
gh search code "query" --limit 5
```

### 2.3 Tavily — 免费额度内开发/时效查询首选，第二轮必用

key 在 `~/.config/tavily/.env`；DSH 会话已连 MCP（`mcp__tavily__*`），其余运行时用 bash：`/Users/wesker/tavily_search.sh`。工具：`tavily_search`、`tavily_extract`、`tavily_crawl`、`tavily_map`、`tavily_research`。

**使用条件（已放宽）**：开发技术、版本、release、价格、日期等时效性强或要求准确的事实 → 可以直接用（免费额度内）；wigolo 第一轮判为弱结果 → 第二轮必用。静态知识、本地可查、普通写码、wigolo 结果已够用 → 不碰。

### 2.4 Brave Search — 第三个免费后端（2000 次/月）

key 在 `~/.config/brave/.env`（`BRAVE_API_KEY`，免费申请：https://brave.com/search/api/）。

```sh
/Users/wesker/brave_search.sh "query" [count] [freshness]   # freshness: pd/pw/pm/py
```

原生支持 `site:example.com`、`"exact phrase"`、`-negation` 查询语法。**用途**：Tavily 免费额度耗尽/限流时的替代，或需要 `site:` 式精确搜索时。

### 2.4b duckduckgo MCP — 已配但非首选

`~/.gemini/config/mcp_config.json` 里配了 `duckduckgo`（`npx -y duckduckgo-websearch`），部分运行时会话会暴露 `mcp__duckduckgo__search` / `mcp__duckduckgo__fetch_content`。**当作 wigolo 的同级免费路**：已暴露且 wigolo 不可用时可以直接用，结果校验纪律（第 1 节第 4 条）完全照用。不专门为它新增配置。

### 2.5 DSH 内置 `web_search` — 禁用（仅 DSH，不计入可用路数）

DSH 的内置 `web_search` 背后是 DeepSeek 搜索 API，本机没有 `DEEPSEEK_API_KEY`，调用必失败（报错 "no API key for DEEPSEEK_API_KEY"）。策略明确不用。（注意：这是 **DSH 的**内置工具问题；云模型运行时的原生搜索不受此限，见第 0 节。）

### 2.6 兜底 — MCP 挂了走 bash

```sh
cd /Users/wesker/.wigolo-mcp && node node_modules/wigolo/dist/index.js search "query" --json   # 免费
/Users/wesker/tavily_search.sh "query" [max_results]   # Tavily
/Users/wesker/brave_search.sh "query" [count]          # Brave
gh search repos "query"                                # GitHub
```

**一句话总结**：先自查有没有原生联网（第 0 节，注意延迟加载工具）——有 → 用原生；没有 → repo/版本类直接 `gh api`，其余第一轮 wigolo search（或已暴露的 duckduckgo）；结果判弱（离题 / SEO 博客占满 / `lexical_alignment`=0）→ 第二轮用 Tavily 或 Brave 跑 `site:` + 引号精确查询；MCP 挂 → bash 兜底；DSH 内置 `web_search` 永远不用；**任何时候都不要直接回答"我没有联网能力"**。
