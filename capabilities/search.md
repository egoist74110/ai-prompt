# 本地 / 自托管模型网页搜索策略

> **LOCAL-ONLY CAPABILITY**：本文件只给 `local` / `self-hosted` 模型/API 使用。
>
> Cloud API/provider 自带搜索时不要读本文件，直接用平台自己的搜索。

本文件只规定跨机器成立的本地搜索策略。某台机器实际装了什么、命令路径、MCP 配置、credential locator、provider endpoint、禁用开关和健康状态，都写 `.local/runtime.json` / `.local/state.json`，不写绝对路径或 secret 到中央仓库。

## 0. 入口判定

判定方法固定为 `router.md` Local Search Contract 的 **Step 0 自判**：先查 `search.contexts` 缓存 → 缓存缺失才做最小 discovery（只读本地来源，按 endpoint 判：局域网/私有 IP = self-hosted，云厂商域名 + API key = cloud）→ 仍判不出就**问用户，禁止猜**。判出后结果回写 `search.contexts`。

只有判定结果满足以下任一条件才继续：

- 当前 provider/model 已确认 `hosting=local` 或 `hosting=self-hosted`；
- endpoint 已确认是本机/自托管服务；
- `.local/runtime.json.search.contexts.<id>.lane=local-managed`。

判定为 cloud 就停止读本文件，用平台搜索；判不出来就回去完成 Step 0，不要猜。

**本地模型看到 runtime 暴露了 `web_search` / browser / provider-native search，不代表该工具可用，也不代表它属于本地搜索路径。**

## 1. 先读缓存，再搜索

固定顺序：

1. 读 `.local/runtime.json.search.contexts.<id>`。
2. 读 `.local/runtime.json.search.backends`。
3. 读 `.local/state.json.search.backends`。
4. 跳过 `enabled=false`、`blocked`、尚在 cooldown、或不属于 `local-managed` 的后端。
5. 优先当前 context 的 `preferred_backends`。
6. 只有缓存缺失/失效才 discovery；跑通后立即缓存。

状态持久化：后端 blocked/cooldown/degraded 写 `.local/state.json.search.backends`；验证过的 locator、roles、priority 写 `.local/runtime.json.search.backends`。

可用：

```text
python tools/search_state.py plan --context <context-id>
python tools/search_state.py plan --context <context-id> --role repo
python tools/search_state.py plan --context <context-id> --role general
python tools/search_state.py plan --context <context-id> --role accurate
python tools/search_state.py plan --context <context-id> --role precise
python tools/search_state.py plan --context <context-id> --role fetch
```

backend 没声明 `roles` 时可作为 generic fallback，避免旧配置失效。

## 1.5 成本阶梯（外部调用花的是用户的钱，最便宜优先）

选任何后端之前先过这个阶梯，逐级升级：

1. **L0 直答**：已有知识 + 已抓取上下文能回答 → 不做任何外部调用。
2. **L1 免费直取**：目标是结构化数据（天气/价格/版本/release/汇率等）或已知 URL → 直接 curl / web_fetch / 免费公开 API，不走任何搜索后端。
3. **L2 免费搜索**：确实需要搜索 → 免费 local-managed 后端（按本机配置优先级），一次只查一个事实。
4. **L3 付费最后手段**：付费后端仅当免费层**已试过**且结果空/垃圾/过时，且事实对用户重要。小问题默认不升级付费；确要用时先一句话说明免费层为什么失败。

同一小问题不重复付费调用。免费层失败又用不了付费层时，用已有信息回答并说明不确定，不硬搜。

## 2. 按任务类型选后端

不要所有问题都扔给同一个聚合搜索。

### repo / release / tag / issue / PR / code

走 `repo` / `code` 后端，优先官方 GitHub 数据，不先绕通用搜索。

若本机 `gh` 已验证，可直接使用类似：

```text
gh search repos "query"
gh api repos/<owner>/<repo>/releases
gh api repos/<owner>/<repo>/tags
gh search code "query"
```

能查一手仓库数据就不要拿 SEO 页面猜版本。

### 普通网页

先走 `general` 后端，目标是低成本、覆盖广、快速拿第一轮候选。wigolo 类聚合器属于这一类，但必须判结果质量。

### 技术 / 版本 / 日期 / 价格 / 强时效

优先或第二轮切 `accurate` 后端。Tavily 类属于这一类；**但"强时效"不等于可以直接用付费后端**——按 §1.5 成本阶梯，它仍是最后手段：先跑一轮免费后端，结果空/垃圾/过时再升级；本机配置把它标为 preferred 也不例外。

### `site:` / 精确短语 / freshness

走 `precise` 后端。Brave 类属于这一类，也适合作为第一轮离题后的二次精确检索。

### 已知 URL

不要重新搜索 URL；直接走 `fetch` / `crawl` / `extract` 后端拿正文或结构化数据。

推荐能力分类：

| 类型 | role | 典型用途 |
|---|---|---|
| GitHub API / `gh` | `repo`, `code`, `precise` | repo、release、tag、issue、PR、代码 |
| wigolo 类 | `general`, `fetch` | 第一轮通用搜索、抓取/crawl/extract |
| Tavily 类 | `accurate`, `research`, `fetch` | 技术/时效/高准确、第二轮 |
| Brave 类 | `precise`, `general` | `site:`、引号、freshness、fallback |
| DDG / 其它 MCP | `general`, `fallback` | 通用备用 |
| 内部/自建搜索 | 按实际能力 | 用户自己的联网入口 |

产品名只是能力例子，不是固定安装清单。

## 3. 搜索成功 != 结果可用

本地搜索最常见的问题不是 API 报错，而是成功返回垃圾结果。每轮都检查：

1. **实体对齐**：Top 3 标题/摘要是否出现核心实体、项目名或明显同义指代；完全不沾边 → 无效。
2. **来源质量**：开发技术优先官网、官方 GitHub、release、vendor docs；SEO 聚合博客占满 → 弱。
3. **主题污染**：无关语言、localhost、随机镜像、不同产品同名页面 → 弱。
4. **时间对齐**：问最新/版本/今天/价格/发布日期时，没有日期或明显陈旧 → 弱。
5. **后端退化信号**：`degraded=true` / engine pool degraded 等 → 请求成功也不能算搜索成功。
6. **相关性评分异常**：lexical/entity alignment 为 0 或极低 → 弱。

历史上 wigolo 裸引擎池出现过引擎 429/0 结果、Top 结果被 SEO 博客占满的情况。遇到这种结果必须换后端，不在垃圾证据上继续推理。

弱结果：

```text
python tools/search_state.py fail <backend-id> \
  --class quality \
  --reason "top results irrelevant / SEO-heavy / degraded"
```

它应进入 `degraded`，不是永久封死。

## 4. 两轮搜索

### 第一轮

- 一次只查一个事实。
- 不写开放式长句。
- 技术问题带精确产品/项目名。
- repo/release 优先 repo backend。

不要：

```text
TypeScript 7 native Go port release status performance roadmap
```

改成拆查：

```text
TypeScript 7 release
microsoft typescript-go releases
```

### 第二轮

第一轮弱/离题时，不硬答，自动：

1. 核心实体加引号；
2. 加 `site:` 官方域名；
3. 加 repo owner/name；
4. 多事实拆单事实；
5. 切 `accurate` / `precise` 后端；
6. 必要时 fetch 官方正文核对。

例如：

```text
site:typescriptlang.org "TypeScript 7"
site:github.com/microsoft/typescript-go releases
```

## 5. 失败分类与熔断

### 确定性失败 → blocked

缺 key、401/403、没订阅、配置不存在、明确 unsupported：

```text
python tools/search_state.py fail <backend-id> \
  --class missing-credential \
  --reason "missing search credential"
```

后续直接跳过，直到配置变化或手动 reset。

### 临时失败 → cooldown

timeout、短时网络错误、5xx、429：

```text
python tools/search_state.py fail <backend-id> \
  --class timeout \
  --reason "request timed out" \
  --retry-after-minutes 15
```

cooldown 期间换下一后端，不重复撞。

### 成功且结果可用 → healthy

```text
python tools/search_state.py success <backend-id>
```

## 6. 最重要：废弃 runtime-native search 必须物理下架

**`blocked` 只解决策略层，不一定解决运行时注入。**

有些 runtime 会采用 stable tool registration：即使 provider/key 不可用，仍把 `web_search` schema 暴露给模型，并继续注入“使用 web_search”的 system prompt；真正缺 key 只在执行时才报错。此时 state 明明已经 `blocked`，下一新会话模型还是会重新看到并被诱导调用一次。

因此，对于 local/self-hosted 会话中已经确认的**确定性硬失败 runtime-native/provider-native search**：

```text
首次实际失败
↓
state 标 blocked
↓
runtime 支持可逆 tool disable/unregister？
├─ 是 → 找当前 profile/runtime 的最小作用域开关
│       → 只关失败的 search tool
│       → 缓存 suppression locator/strategy 到 runtime.json
│       → reload/restart/new session
│       → 验证该 tool 已不再出现在 tool schema
│       → verified_absent=true
└─ 否 → 缓存 suppression_status=unsupported
        → 保持 blocked，永不主动调用
```

**这一动作是搜索自愈的一部分，已授权自动执行**：只要失败是确定性的，并且修改是最小、可逆、只关闭该搜索工具，可以直接处理，不必每次再次询问。若会扩大权限、关闭其它能力、影响非搜索功能或作用域无法确认，才需要用户确认。

不要对 timeout/429/5xx/偶发网络问题做永久物理下架；它们只 cooldown。

具体产品的配置路径、profile 名、开关格式属于本机事实：首次发现后写 `.local/runtime.json.search.contexts.<id>.native_tools`，不要硬编码进中央文档。

完整 suppression contract 见 `capabilities/search-runtime-suppression.md`。

## 7. MCP / wrapper / discovery

MCP 或包装层挂了：

- 同一 backend 已缓存等价 CLI/command locator → 直接走等价入口；
- 没有 → 换下一已验证 backend；
- 不要因为 MCP 失败就重新安装一遍已有能力。

本机一个搜索 backend 都没有时才 discovery：

1. 查 local runtime/state；
2. 查当前 runtime 已配置 MCP；
3. 查 PATH / 已知 wrapper；
4. 一次只探最可能的一两个；
5. 成功后立即写 locator + roles + priority + healthy；
6. 失败按 blocked/cooldown 写状态。

**第一次可以绕路，第二次不准重新找 key、MCP、脚本路径或再次调用已知废弃工具。**

## 8. 最终执行摘要

```text
本地模型需要外部信息
↓
成本阶梯（§1.5）：能直答就直答；能免费直取就直取
↓
读 context + backend cache + circuit breaker
↓
先过滤 blocked/cooldown/被物理禁用的 native tools
↓
按任务 role 选 local-managed backend
├─ repo/release/code → repo/code
├─ 普通网页 → general
├─ 技术/时效/高准确 → accurate
├─ site:/freshness → precise
└─ 已知 URL → fetch
↓
第一轮
↓
质量检查
├─ 好 → healthy + 回答
└─ 差 → degraded → 改写查询 → 换 accurate/precise 第二轮
↓
硬失败 → blocked；若是 runtime-native 且可关闭 → 同时物理下架
临时失败 → cooldown
↓
所有 local-managed backend 都不可用
→ 才报告具体失败原因
```

一句话：**本地模型联网不是“看见 search tool 就点”，而是“只走已配置的 local-managed 后端；垃圾结果自动二搜；确定性废弃工具既熔断又从运行时物理摘掉”。**
