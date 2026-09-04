# 本地 / 自托管模型网页搜索策略

> **LOCAL-ONLY CAPABILITY**：本文件只给 `local` / `self-hosted` 模型/API 使用。
>
> 如果当前模型/API 是云端并且平台自身提供联网搜索，**不要读取、不要执行、不要套用本文件剩余内容**。云端模型直接使用平台自己的搜索能力即可。

本文件保存的是本地模型如何联网搜索的**跨机器策略**：怎么选后端、怎么判断结果垃圾、什么时候重搜、什么时候 fallback、什么时候熔断。

某台机器实际装了哪些后端、命令路径、MCP 配置、credential locator、provider endpoint、健康状态，属于本地事实，只写 `.local/runtime.json` / `.local/state.json`，禁止把绝对路径或 secret 写回这里。

---

## 0. 入口判定

只有满足以下任一条件才继续读：

- 当前 provider/model 明确 `hosting=local` 或 `hosting=self-hosted`；
- endpoint 是已确认的本机/自托管服务；
- `.local/runtime.json.search.contexts.<id>` 已缓存 `lane=local-managed`。

若 hosting 未知，先做一次最小 discovery，确认并缓存；若结果是 cloud，立即停止读取本文件。

本地模型即使看到 runtime 暴露了 `web_search` / browser / provider-native search，也不能据此认为自己已经联网。只有用户自己管理、配置并验证的 `local-managed` backend 才是本文件的搜索能力。

**禁止直接回答“我没有联网能力”。** 先按下面流程检查本机已配置后端；只有所有 eligible backend 都不可用时，才报告具体失败点。

---

## 1. 搜索前先读本地缓存

顺序固定：

1. 读取当前 search context：`.local/runtime.json.search.contexts.<id>`。
2. 读取用户已配置后端：`.local/runtime.json.search.backends`。
3. 读取健康/熔断状态：`.local/state.json.search.backends`。
4. 跳过：
   - `enabled=false`；
   - `status=blocked`；
   - `status=cooldown` 且 `retry_at` 未到；
   - 不属于 `local-managed` lane 的后端。
5. 优先复用 `preferred_backends`；不要每次重新扫描 MCP、PATH、配置文件和 key。
6. 没有已配置路径，或缓存明确失效时，才 discovery。

可以用：

```text
python tools/search_state.py plan --context <context-id>
```

如果任务类型明确，可进一步按 backend role 过滤：

```text
python tools/search_state.py plan --context <context-id> --role repo
python tools/search_state.py plan --context <context-id> --role general
python tools/search_state.py plan --context <context-id> --role accurate
python tools/search_state.py plan --context <context-id> --role precise
python tools/search_state.py plan --context <context-id> --role fetch
```

backend 没声明 `roles` 时仍可作为 generic fallback，不要因此把已跑通的旧配置判无效。

---

## 2. 先按任务类型选搜索路径

不要所有问题都丢给同一个聚合搜索。

### A. 仓库 / release / tag / issue / PR / 代码

**直接走 repo/code 类后端，优先官方 GitHub 数据，不先绕通用搜索引擎。**

典型 role：

```json
["repo", "code"]
```

若本机 `gh` 已验证，可直接使用类似：

```text
gh search repos "query"
gh api repos/<owner>/<repo>/releases
gh api repos/<owner>/<repo>/tags
gh search code "query"
```

核心原则：能直接查一手仓库数据，就不要拿 SEO 搜索结果猜 release/version。

### B. 普通网页问题

先走 `general` 后端，目标是低成本、覆盖广、快速拿到第一轮候选。

典型实现可以是用户自己的聚合搜索/MCP。历史上 wigolo 属于这一类：免费、能力多，适合第一轮 `search/fetch/crawl/extract/cache`，但必须做结果质量检查，不能因为请求成功就直接相信结果。

### C. 开发技术 / 版本 / release / 日期 / 价格 / 强时效事实

优先或第二轮切 `accurate` 后端。

典型实现可以是 Tavily 一类质量更高的搜索 API/MCP。对于这类问题，不必为了“省一次请求”强行先用明显质量较差的通用聚合器；如果本机策略把 accurate backend 设为 preferred，可以直接用。

### D. `site:` / 精确短语 / freshness / 定向检索

走 `precise` 后端。

典型实现可以是 Brave 一类支持 `site:`、引号、freshness 的搜索。尤其适合第一轮离题后的第二轮精确检索。

### E. 已知 URL，需要正文/页面结构

不要重新搜索这个 URL；走 `fetch` / `crawl` / `extract` 后端直接抓正文或结构化内容。

---

## 3. 本地搜索最重要的纪律：判结果，不只判调用成功

本地搜索“垃圾”的主要问题往往不是 API 报错，而是**成功返回了一堆不能用的结果**。

每轮结果都必须做以下质量检查：

1. **实体对齐**：Top 3 的标题/摘要应出现核心实体、项目名或明显同义指代；完全不沾边 → 本轮无效。
2. **来源质量**：开发技术问题优先官网、官方 GitHub、release、vendor docs；SEO 聚合博客占满 Top 结果 → 判弱。
3. **语言/主题污染**：混入无关语言、localhost、随机镜像、完全不同产品同名页面 → 判弱。
4. **时间对齐**：问“最新/版本/今天/价格/发布日期”时，结果没有日期或明显陈旧 → 判弱。
5. **后端自报退化**：若 backend 返回类似 `degraded=true` / engine pool degraded 的信号 → 不把“HTTP 成功”当成搜索成功。
6. **相关性评分异常**：若后端有 lexical/entity alignment 等评分，核心相关性为 0 或极低 → 判弱。

历史 wigolo 的典型弱结果就是：engine pool 退化、部分引擎 429/0 结果、最终 Top 结果被 SEO 博客占满。遇到这种情况必须换后端，而不是让模型在垃圾结果上继续推理。

弱结果写成 `degraded`，不是永久封死：

```text
python tools/search_state.py fail <backend-id> \
  --class quality \
  --reason "top results are irrelevant / SEO-heavy / degraded"
```

---

## 4. 两轮搜索策略

### 第一轮：窄问题、正常查询

- 一次只查一个事实。
- 不写开放式长句。
- 技术问题尽量带精确产品/项目名。
- repo/release 问题优先 repo backend。

错误示例：

```text
TypeScript 7 native Go port release status performance roadmap
```

更好的拆法：

```text
TypeScript 7 release
microsoft typescript-go releases
site:typescriptlang.org "TypeScript 7"
```

### 第二轮：第一轮弱/离题时自动改写

不要拿弱结果硬答，自动执行：

1. 给核心实体加引号；
2. 加 `site:` 官方域名；
3. 加 repo owner/name；
4. 把多事实拆成单事实；
5. 切到 `accurate` 或 `precise` 后端；
6. 仍有疑问时直接 fetch 官方结果正文核对。

例：

```text
第一轮 general:
TypeScript 7 release

结果弱
↓

第二轮 accurate/precise:
site:typescriptlang.org "TypeScript 7"
site:github.com/microsoft/typescript-go releases
```

---

## 5. 推荐后端角色映射

这只是**跨机器的能力分类**，不是要求当前机器必须安装这些产品：

| 后端/类型 | 推荐 role | 用途 |
|---|---|---|
| GitHub API / `gh` | `repo`, `code`, `precise` | repo、release、tag、issue、PR、代码 |
| wigolo 类聚合器 | `general`, `fetch` | 免费第一轮通用搜索、抓取、crawl/extract |
| Tavily 类 | `accurate`, `research`, `fetch` | 技术/时效/高准确事实、弱结果第二轮 |
| Brave 类 | `precise`, `general` | `site:`、引号、freshness、Tavily fallback |
| DuckDuckGo / 其它搜索 MCP | `general`, `fallback` | 通用备用 |
| 内部/自建搜索 | 按实际能力声明 | 用户自己的联网入口 |

真正路径、command、MCP server、credential locator 全部来自 `.local/runtime.json`。

例如：

```json
{
  "search": {
    "backends": {
      "my-general-search": {
        "enabled": true,
        "lane": "local-managed",
        "roles": ["general", "fetch"],
        "priority": 100,
        "kind": "mcp",
        "config_path": "<local locator>"
      },
      "my-accurate-search": {
        "enabled": true,
        "lane": "local-managed",
        "roles": ["accurate", "research"],
        "priority": 90,
        "kind": "command",
        "command": ["<resolved command>"],
        "credential": {
          "type": "env|file|keychain",
          "locator": "<locator only>"
        }
      }
    }
  }
}
```

---

## 6. 失败、熔断和 fallback

### 确定性失败 → blocked

缺 key、401/403、没订阅、明确 unsupported、配置不存在：

```text
python tools/search_state.py fail <backend-id> \
  --class missing-credential \
  --reason "missing search credential"
```

后续直接跳过，直到配置变化或手动 reset。

### 临时失败 → cooldown

timeout、5xx、429、短时网络错误：

```text
python tools/search_state.py fail <backend-id> \
  --class timeout \
  --reason "request timed out" \
  --retry-after-minutes 15
```

cooldown 期间直接换下一 eligible backend，不重复撞。

### 请求成功且结果可用 → healthy

```text
python tools/search_state.py success <backend-id>
```

### MCP/包装层挂了

优先查看同一 backend 是否已经缓存了等价 CLI/command locator；有就走等价入口，不要重新安装 MCP。

如果没有等价入口，切下一个已验证 backend。只有所有本地路径都失败，才向用户报告无可用搜索能力及各路径失败原因。

---

## 7. Discovery：只允许第一次绕路

如果本机还没有配置任何搜索 backend：

1. 查 local runtime/state；
2. 查当前 runtime 已配置 MCP；
3. 查 PATH/已知本地 wrapper；
4. 一次只探最有希望的一两个；
5. 成功后立即把 locator + roles + priority 写 runtime，把健康状态写 state；
6. 失败按类型写 blocked/cooldown；
7. 下一次直接复用。

不要每次重新找 key、重新判断哪个 MCP 装了、重新猜脚本路径。

---

## 8. 最终执行摘要

```text
本地模型需要外部信息
↓
读 context + local backend cache + circuit breaker
↓
按任务类型选 role
├─ repo/release/code → repo/code backend
├─ 普通网页 → general backend
├─ 技术/时效/高准确 → accurate backend
├─ site:/freshness → precise backend
└─ 已知 URL → fetch backend
↓
执行第一轮
↓
质量检查
├─ 好 → 引用/回答 + 标 healthy
└─ 差 → 标 degraded
          ↓
       改写查询
          ↓
       切 accurate/precise backend 第二轮
↓
确定性失败 → blocked
临时失败 → cooldown
↓
所有 local-managed backend 都不可用
→ 才报告具体失败原因
```

一句话：**本地模型联网的关键不是“有个 search tool”，而是“按任务选后端 + 对结果做质量判定 + 弱结果自动二搜 + 失败持久化熔断 + 跑通过的本机配置以后直接复用”。**
