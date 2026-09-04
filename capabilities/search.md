# 网页搜索策略

本文件只保存**跨机器成立的搜索纪律、资格判断、熔断与降级规则**。某台机器实际装了什么、模型/provider 在哪里跑、endpoint、命令、key locator、某个后端当前是否健康，全部属于本地事实，写入 `.local/runtime.json` / `.local/state.json`。

## 0. 核心原则：暴露 ≠ 可用

**搜索工具出现在当前会话的 tool list 中，只说明“运行时暴露了这个调用入口”，绝不等于它在当前模型/provider/订阅下真的可用。**

选择搜索后端前，先判断当前执行上下文，再判断后端资格：

1. 当前运行时 / provider / model 是 cloud、local/self-hosted 还是 unknown。
2. `.local/runtime.json.search.contexts.*` 是否已有该上下文的稳定事实。
3. `.local/state.json.search.backends.*` 是否已把某个后端标为 blocked / cooldown / degraded。
4. 只有通过资格判断的后端才允许实际调用。

禁止为了“看看能不能用”而重复调用一个已经被本地 state 判定为不可用的搜索后端。

## 1. 执行上下文优先于工具暴露

### Cloud 模型 / Provider

- `hosting=cloud` 时，当前会话真正提供的原生 Web Search / Browser / MCP 可以作为高优先级候选。
- 但仍需服从本地熔断状态：之前已经验证缺权限、缺订阅、缺 credential 或处于 cooldown 时，直接跳过。
- 原生搜索失败不代表以后永久不可用；按失败类型进入 blocked 或 cooldown。

### Local / Self-hosted 模型

- `hosting=local` 或 `hosting=self-hosted` 时，**运行时附带的云端搜索入口默认不具备资格**。
- 尤其是需要运行时自己的云端 API key、订阅、额度或远端 provider 才能工作的 `web_search` / browser tool：即使当前会话把它暴露出来，也**禁止调用试探**。
- 默认直接走 `.local/runtime.json.search.backends` 中已经配置、且本地 state 判定可用的搜索后端。
- 只有 `.local/runtime.json.search.contexts.<id>.native_search_policy=allow`，并且该 native backend 已经在本机验证成功，local/self-hosted 模型才允许使用它。

一句话：**本地模型不拿“工具出现了”当联网能力；必须有明确的本地配置/验证证据。**

### Unknown

- 若 hosting 未知，不要按模型品牌或运行时名字猜。
- 先从当前运行时/provider 配置做最小 discovery：endpoint 是 localhost/本机服务、明确自托管配置，或用户已说明本地模型时，记录为 local/self-hosted；明确云端 provider 时记录为 cloud。
- 该事实属于本地配置，确认后写入 runtime，后续直接复用。

示例：

```json
{
  "search": {
    "contexts": {
      "<context-id>": {
        "runtime": "<runtime-id>",
        "provider": "<provider-id>",
        "model": "<model>",
        "hosting": "self-hosted",
        "endpoint": "http://127.0.0.1:<port>",
        "native_search_policy": "deny",
        "preferred_backends": ["<configured-local-backend>"]
      }
    }
  }
}
```

可用工具辅助写入：

```text
python tools/search_state.py context-set <context-id> \
  --runtime <runtime-id> \
  --provider <provider-id> \
  --model <model> \
  --hosting self-hosted \
  --endpoint <non-secret-endpoint> \
  --native-search-policy deny \
  --preferred-backends-json '["<backend-id>"]'
```

## 2. 搜索后端选择顺序

不要固定写死某个产品名。后端列表来自 `.local/runtime.json.search.backends`。

统一流程：

1. 判定当前 search context。
2. 跳过 `enabled=false` 的后端。
3. 跳过 state 中 `status=blocked` 的后端。
4. 跳过仍在 `status=cooldown` 且 `retry_at` 尚未到期的后端。
5. local/self-hosted context 下，若 `native_search_policy=deny`，跳过 `kind=native|runtime-native|session-native`。
6. `preferred_backends` 中的已配置后端优先。
7. 其余按 runtime 中的 `priority` 排序；`degraded` 后端排在健康/未知后端之后。
8. 调用成功/失败后立即更新 state。

可直接查看当前已配置且有资格的后端：

```text
python tools/search_state.py plan --context <context-id>
```

若没有配置 context，可先省略 `--context`，但不能据此绕过已经存在的 blocked/cooldown 状态。

## 3. 搜索失败必须进入熔断状态

失败后不能只在当前对话里记一句“这个不好用”。必须把失败写入 `.local/state.json`，让后续会话直接避开。

### A. 确定性失败 → blocked

以下属于配置/能力事实：

- missing credential / missing key
- 401 / 403 或明确 permission denied
- subscription 未开通
- provider/运行时明确不支持该搜索能力
- 配置文件不存在或后端未配置
- 本地模型调用了只对云端订阅生效的 runtime-native search

写成：

```text
python tools/search_state.py fail <backend-id> \
  --class missing-credential \
  --reason "<non-secret reason>"
```

状态结果应为：

```json
{
  "status": "blocked",
  "retry": "when-config-changes"
}
```

**后续所有会话直接跳过。** 只有配置/credential locator/订阅发生变化，或用户明确要求 reset/refresh，才允许重新尝试。

### B. 临时失败 → cooldown

以下不要永久封死：

- timeout / 临时网络错误
- 5xx
- 429 / quota / rate limit
- 服务短时不可达

写成：

```text
python tools/search_state.py fail <backend-id> \
  --class timeout \
  --reason "request timed out" \
  --retry-after-minutes 15
```

cooldown 未到期前不再调用，到期后允许一次 half-open 式重试；再次失败继续 cooldown。若服务返回 Retry-After，应优先使用实际 Retry-After。

### C. 结果质量差 → degraded

请求本身成功，但 Top 结果明显无关、SEO 垃圾、信息陈旧或 backend 自报 degraded：

```text
python tools/search_state.py fail <backend-id> \
  --class quality \
  --reason "weak/irrelevant results"
```

`degraded` 不代表完全不可用，只降低排序并立即换下一个后端。

### D. 成功 → 清除熔断

```text
python tools/search_state.py success <backend-id>
```

成功后把状态恢复为 `healthy`，清掉 failure_count/retry/reason。

手动清除历史状态：

```text
python tools/search_state.py reset <backend-id>
```

## 4. 本地后端配置

中央不规定必须使用 wigolo、Tavily、Brave、DDG 或其它产品；它们都只是可选后端。真正使用哪些由当前机器 `.local/runtime.json.search.backends` 决定。

示例：

```json
{
  "search": {
    "backends": {
      "my-search": {
        "enabled": true,
        "kind": "mcp",
        "priority": 100,
        "config_path": "<local config locator>",
        "credential": {
          "type": "env|file|keychain|none",
          "locator": "<locator only, never secret>"
        }
      }
    }
  }
}
```

第一次配置并验证成功后，同时写：

```text
python tools/search_state.py success my-search
```

之后本地/self-hosted 模型应直接走这个后端，不再尝试已经 blocked 的 runtime-native 搜索。

## 5. Discovery 规则

只有**没有已验证路径**或**缓存明确失效**时才 discovery：

1. 先读 search context，确认 cloud/local/self-hosted。
2. 再读 runtime 中已配置 backend 和 credential locator。
3. 再读 state 熔断状态；blocked/cooldown 先排除。
4. PATH/MCP/config 只做最小探测，不要五路同时盲跑。
5. 成功立即 `search_state.py success`；失败立即按类型 `fail`。
6. 发现当前 provider/model 的 hosting/endpoint 是稳定本机事实时，写 `search.contexts`，不要下次重新读配置再猜。

**禁止反复试探已经失败且失败原因没有变化的后端。** 这是节省 token 和避免无意义工具调用的硬规则。

## 6. 搜索质量纪律

1. 一次查询聚焦一个事实。
2. 技术问题优先官网、官方 GitHub、release、vendor docs。
3. 第一轮弱结果时自动改用引号、`site:`、repo 名或更精确实体，并切换其它 eligible backend。
4. “请求成功”和“搜索质量足够”分别判断。
5. 所有 eligible backend 都失败时，报告实际失败点；不要虚构联网结果。

## 7. 典型行为

### 本地模型 + runtime 暴露 `web_search` + 该工具依赖云端 key

```text
context = self-hosted
native_search_policy = deny
→ 不调用 web_search 试探
→ 读取 preferred/configured local search backend
→ 直接调用本地后端
```

### 某 native search 已经报 missing key

```text
第一次失败
→ state: blocked / retry when-config-changes

下一次会话
→ 读取 state
→ 直接跳过
→ 使用 configured backend
```

### 云端搜索短时 5xx

```text
失败
→ cooldown
→ 当前请求切备用后端
→ cooldown 到期后才允许重新探测
```

一句话：**先判模型/provider 的执行环境，再判后端资格；搜索失败必须持久化熔断，后续优先走用户已经配置并验证的后端。**
