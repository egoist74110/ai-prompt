# 网页搜索策略

本文件只保存**跨机器成立的搜索分流、资格判断、熔断与降级规则**。某台机器实际装了什么、模型/provider 在哪里跑、endpoint、命令、key locator、某个后端当前是否健康，全部属于本地事实，写入 `.local/runtime.json` / `.local/state.json`。

## 0. 第一原则：搜索先分流，再选工具

搜索不是一个统一候选池。任何需要联网的任务，**先确定 Search Lane，再执行该 Lane 自己的搜索流程**。

只有两条正常路线：

```text
Cloud model/provider
    → lane = cloud-native
    → 只走当前云端运行时/平台提供的原生搜索能力

Local / self-hosted model/provider
    → lane = local-managed
    → 只走用户在本机配置并验证的搜索后端
```

`unknown` 不是第三条搜索路线。hosting/lane 未知时，必须先做一次最小 discovery，确认后缓存，再开始搜索。

**默认禁止跨 Lane 偷跑。** 云端模型不要因为本机恰好装了 Tavily/Brave/MCP 就绕去本地搜索；本地模型也不要因为 runtime 暴露了一个 `web_search` 就调用云端搜索。

只有用户明确要求，或 `.local/runtime.json.search.contexts.<id>` 明确配置 `allow_cross_lane_fallback=true` 时，才允许跨 Lane fallback。

## 1. 工具暴露 ≠ 工具可用

搜索工具出现在当前会话 tool list 中，只表示“运行时暴露了调用入口”，**不表示这个入口属于当前 Search Lane，也不表示当前 provider/key/订阅下可用**。

因此：

- tool list 只用于发现候选入口；
- Search Lane 决定候选是否有资格；
- `.local/state.json` 的 blocked/cooldown 决定候选当前是否允许实际调用；
- 已验证 blocked 的工具禁止为了“试试看”再次调用。

## 2. Lane A：Cloud Native Search

适用条件：

```text
hosting = cloud
lane = cloud-native
```

执行规则：

1. 优先使用**当前云端会话实际提供**的 Web Search / Browser / Search connector / provider-native search。
2. 不需要读取本机 PATH、MCP 配置、Tavily/Brave/DDG wrapper，也不要因为本机有这些能力就切过去。
3. 当前会话原生搜索存在，但本地 state 已记录该 backend `blocked` / 尚在 `cooldown` → 直接跳过，不重复撞失败。
4. 云端原生搜索实际失败时按 §6 熔断；不要因为 tool list 仍显示它就下一轮继续撞。
5. 若当前云端会话根本没有搜索能力：默认如实报告该会话缺少云端搜索；只有明确允许 cross-lane fallback 时才进入本地后端。

Cloud lane 的核心是：

> **云端模型使用平台/Provider 自己的云端搜索；本机搜索栈默认与它无关。**

## 3. Lane B：Local Managed Search

适用条件：

```text
hosting = local | self-hosted
lane = local-managed
```

执行规则：

1. **禁止调用 runtime 暴露的云端 `web_search` / browser / provider-native search 试探。**
2. 即使这些工具出现在当前会话 tool list，也视为另一条 Lane 的工具，默认没有资格。
3. 直接读取 `.local/runtime.json.search.backends` 中用户已经配置的本地托管搜索后端。
4. 读取 `.local/state.json.search.backends`，过滤 disabled / blocked / cooldown。
5. 优先使用当前 context 的 `preferred_backends`；没有 preferred 时按 backend `priority`。
6. `degraded` 后端可用但降级排序；当前请求优先换健康后端。
7. 若一个本地搜索后端都没有配置/可用：明确报告“local-managed lane 无可用 backend”，不要回头尝试 cloud-native search。

这里的“本地搜索后端”指**由用户自己管理配置和 credential 的联网入口**，不要求搜索服务本身物理运行在本机。例如用户自行配置的 Tavily CLI/MCP、Brave wrapper、wigolo、DDG MCP、内部搜索服务都属于 `local-managed`。

Local lane 的核心是：

> **本地模型只使用用户自己配置的联网逻辑；运行时附赠的云端搜索入口默认完全忽略。**

## 4. Search Context 必须缓存 Lane

第一次确认 provider/model 执行位置后，写入：

```json
{
  "search": {
    "contexts": {
      "<context-id>": {
        "runtime": "<runtime-id>",
        "provider": "<provider-id>",
        "model": "<model>",
        "hosting": "self-hosted",
        "lane": "local-managed",
        "endpoint": "http://127.0.0.1:<port>",
        "preferred_backends": ["<configured-backend>"],
        "allow_cross_lane_fallback": false
      }
    }
  }
}
```

Cloud context 对应：

```json
{
  "hosting": "cloud",
  "lane": "cloud-native",
  "allow_cross_lane_fallback": false
}
```

若 hosting 已知而 lane 缺失：

```text
cloud               → cloud-native
local/self-hosted   → local-managed
```

确认后立即缓存，不要每个会话重新读 provider 配置再判断。

可用 CLI：

```text
python tools/search_state.py context-set <context-id> \
  --runtime <runtime-id> \
  --provider <provider-id> \
  --model <model> \
  --hosting self-hosted \
  --lane local-managed \
  --endpoint <non-secret-endpoint> \
  --preferred-backends-json '["<backend-id>"]'
```

## 5. Backend 也声明所属 Lane

本地配置中的 backend 可以声明：

```json
{
  "search": {
    "backends": {
      "my-search": {
        "enabled": true,
        "lane": "local-managed",
        "kind": "mcp",
        "priority": 100,
        "credential": {
          "type": "env|file|keychain|none",
          "locator": "<locator only>"
        }
      }
    }
  }
}
```

允许值：

- `cloud-native`：云端会话/Provider 自带搜索。
- `local-managed`：用户自己管理的 CLI/MCP/API/wrapper。
- `both`：只有确实跨两种上下文都验证成功时才使用；不要图省事默认写 `both`。

旧配置没写 `lane` 时按 `kind` 推断：

```text
native / runtime-native / session-native → cloud-native
其它                                → local-managed
```

## 6. 搜索失败必须持久化熔断

失败后不能只在当前对话里记住，必须更新 `.local/state.json`。

### A. 确定性失败 → blocked

包括：

- missing credential / missing key
- 401 / 403 / permission denied
- subscription 未开通
- provider/runtime 明确不支持
- 配置文件/后端不存在
- 调用了错误 Lane 的 backend

```text
python tools/search_state.py fail <backend-id> \
  --class missing-credential \
  --reason "<non-secret reason>"
```

结果：

```json
{
  "status": "blocked",
  "retry": "when-config-changes"
}
```

后续直接跳过，直到配置变化或明确 reset/refresh。

### B. 临时失败 → cooldown

包括 timeout、临时网络错误、5xx、429、quota/rate-limit。

```text
python tools/search_state.py fail <backend-id> \
  --class timeout \
  --reason "request timed out" \
  --retry-after-minutes 15
```

cooldown 到期后才允许一次重试。

### C. 搜索成功但质量差 → degraded

```text
python tools/search_state.py fail <backend-id> \
  --class quality \
  --reason "weak/irrelevant results"
```

`degraded` 不禁用，只降低排序并切同 Lane 的下一后端。

### D. 成功 → healthy

```text
python tools/search_state.py success <backend-id>
```

成功清除历史熔断。

## 7. Discovery 只负责确定 Lane 和补本 Lane 缺口

### hosting/lane unknown

只做最小 discovery：

1. 读取当前 provider/runtime 已知配置。
2. localhost / 127.0.0.1 / 明确自托管 endpoint → `hosting=self-hosted` → `lane=local-managed`。
3. 明确远程云 Provider → `hosting=cloud` → `lane=cloud-native`。
4. 缓存 context。
5. 然后才进入对应 Lane。

不要在 hosting unknown 时同时试一次云端搜索、再试一次本地搜索来“猜哪边能跑”。

### local-managed lane 没 backend

可以 discovery 本机已经存在的用户搜索配置：PATH、MCP list、已有 config locator；但只做最小探测。

发现并验证后写 runtime/state。若确实没有，就报告缺 backend；安装/新增 MCP/API key 属于配置变更，按对应能力规则处理。

### cloud-native lane

只检查当前云端会话原生能力；不要扫描本机搜索 CLI/MCP。

## 8. 搜索质量纪律

1. 一次查询聚焦一个事实。
2. 技术问题优先官网、官方 GitHub、release、vendor docs。
3. 第一轮结果弱，优先在**同一 Lane**中换 query / 换 backend。
4. 不因为搜索质量差就自动跨 Lane。
5. “请求成功”和“结果可信”分别判断。
6. 本 Lane 所有路径都失败时，报告实际失败点，不虚构搜索结果。

## 9. 典型流程

### 云端模型

```text
hosting=cloud
→ lane=cloud-native
→ 用当前平台 Web Search
→ 不碰本机 Tavily / wigolo / DDG / wrapper
```

### 本地模型

```text
hosting=self-hosted
→ lane=local-managed
→ 忽略 runtime 暴露的 cloud web_search
→ 读 preferred_backends
→ 调用户配置好的搜索
```

### 本地模型没有本地搜索 backend

```text
lane=local-managed
→ eligible backend = 0
→ 报告本地搜索尚未配置
→ 不偷跑 cloud-native web_search
```

### backend 第一次缺 key

```text
实际失败
→ blocked / when-config-changes
→ 下一会话直接跳过
```

一句话：**Cloud 走 Cloud，Local 走 Local；先选 Lane，后选工具。默认绝不混用。**
