# 网页搜索策略

本文件只保存**跨机器成立的搜索纪律、后端候选与降级规则**。某台机器实际装了什么、命令在哪、key 从哪里取、某个后端当前是否可用，全部属于本地事实，写入 `.local/runtime.json` / `.local/state.json`，不要写死在这里。

## 0. 总优先级

搜索能力统一按以下顺序判断：

1. **当前会话实时能力**：本次会话已经暴露的原生 Web Search / Browser / MCP 搜索工具，直接用。
2. **本地已验证后端**：读取 `.local/state.json` 中 `search.backends.*` 的已验证状态；对应命令、配置路径、credential locator 从 `.local/runtime.json` 读取。
3. **Discovery**：前两层都没有可用路径，或缓存失效时，才检查 PATH、运行时 MCP 列表、配置文件或做最小健康探测。
4. Discovery 成功后，把**非敏感结果**写回 `.local/`。后续不要重复搜配置、重复猜脚本路径、重复判断有没有 key。

当前会话事实永远覆盖缓存。缓存说可用，但实际调用失败，应重探并刷新缓存。

## 1. 原生搜索优先

判断依据是**本次会话实际能力**，不是运行时名字：Claude、Codex、DSH、Gemini 等都可能接不同模型/API。

- 当前会话有原生搜索工具 → 优先原生搜索。
- 有些运行时工具会延迟加载；初始列表没看到，不等于一定没有。能做能力检索时先检索一次。
- 本地/自托管模型没有原生联网时，再走本地后端。
- 不能因为当前模型本身没联网就直接回答“无法搜索”；先检查本地已验证后端。

## 2. 搜索质量纪律

1. **缩小查询**：一次只查一个事实；避免把多个问题拼成长句。
2. **技术问题优先官方来源**：版本、框架、SDK、API、开发工具，优先官网、官方 GitHub、Releases、厂商博客。
3. **结果对齐**：Top 结果标题/摘要没有核心实体、混入明显无关页面、SEO 聚合页占满时，判弱结果，不硬答。
4. **两轮策略**：第一轮普通搜索；弱结果时自动改成引号、`site:`、repo 名等精确查询再跑第二轮。
5. 搜索后端的“能调用”不等于“结果可信”；结果质量判断与后端可用性是两件事。

## 3. 本地后端候选

下面只定义**能力与适用场景**，不宣称当前机器一定已经安装或登录。

### GitHub CLI / API

适合仓库、release、tag、issue、PR、代码搜索。若 `gh` 在当前机器可用且认证有效，repo/版本类问题优先它，不绕聚合搜索。

候选命令形态：

```text
gh search repos "query"
gh api repos/<owner>/<repo>/releases
gh api repos/<owner>/<repo>/tags
gh search code "query"
```

第一次确认 `gh` 可执行且认证有效后，记录：

```json
{
  "search": {
    "backends": {
      "github": {
        "kind": "cli",
        "command": "gh"
      }
    }
  }
}
```

状态写入 `.local/state.json`，例如 `verified: true`、最近验证时间和必要的非敏感能力说明。

### wigolo

适合免费通用搜索、抓取、crawl、extract、cache、相似页面和 research。若当前会话已经暴露对应 MCP 工具，直接用；否则从本地 runtime 中读取已验证的启动/CLI locator。

已知质量信号：若返回 `engine_pool.degraded: true`，或 Top 结果明显被 SEO 站点占满，应判弱并换第二后端，不要把“请求成功”当成“搜索成功”。

### Tavily

适合开发技术、版本、release、价格、日期等时效性强或要求较高准确性的事实；也适合作为第二轮后端。

中央文档**不保存 API key 路径和 wrapper 绝对路径**。本地配置只允许保存：

```json
{
  "search": {
    "backends": {
      "tavily": {
        "kind": "mcp-or-command",
        "command": ["<resolved-command-or-script>"],
        "credential": {
          "type": "env-or-file",
          "locator": "<local locator, not secret>"
        }
      }
    }
  }
}
```

### Brave Search

适合 Tavily 不可用/限流时替代，或需要 `site:`、精确短语、freshness 等条件时使用。和 Tavily 一样，key 来源与脚本路径都是本地 runtime，不进中央文档。

### DuckDuckGo / 其它 MCP 搜索

当前会话已经暴露就可直接使用；工具没暴露时，先查本地 state 是否已配置，不要每轮重新 add。只有确认未配置且任务确实需要时，才按 `capabilities/mcp.md` 的纪律新增。

### 运行时自带 `web_search`

不要在中央仓库永久标记“某运行时一定可用/一定禁用”。是否缺 API key、是否启用、背后是什么 provider 都是当前机器/当前会话事实。

若某台机器上已经验证某个 runtime 的 `web_search` 因缺 key 恒定失败，可在本地 state 记录：

```json
{
  "search": {
    "backends": {
      "dsh-web-search": {
        "verified": false,
        "reason": "missing credential",
        "retry": "when-config-changes"
      }
    }
  }
}
```

这样后续直接跳过，直到配置发生变化，不需要每轮再失败一次。

## 4. Discovery 规则

首次需要本地搜索且 state 没记录时，只做最小探测：

1. 当前会话有没有现成原生/MCP 工具。
2. `.local/runtime.json` 有没有已知 command / config / credential locator。
3. PATH 中有没有候选 CLI；运行时自己的 MCP list 是否已经配置相应 server。
4. 只对最有希望的一两个后端做最小健康请求，不要五路全部盲跑。
5. 跑通后立即缓存；失败也可缓存明确的、可失效的失败原因，避免短时间重复踩同一个坑。

缓存只记录 locator、策略、能力和验证结果，**绝不记录 key/token 正文**。

## 5. 推荐选择顺序

- 软件仓库 / release / tag / PR / issue → 原生 GitHub 工具或已验证 `gh`。
- 普通网页搜索 → 当前会话原生搜索优先；没有时使用本地 state 中优先级最高的通用后端。
- 第一轮结果弱 → Tavily / Brave / 其它已验证第二后端，配合 `site:`、引号、官方域名重搜。
- MCP 后端未暴露 → 先看 state 是否已配；已配就恢复/连接，不要重复 add。
- 所有已验证路径都失败 → 报告具体失败点；不要虚构搜索结果。

一句话：**搜索策略是中央知识，搜索环境是本地状态。第一次允许 discovery，第二次必须尽量复用已验证路径。**
