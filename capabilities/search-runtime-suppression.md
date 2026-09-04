# Runtime-Native Search Suppression

本文件只处理一个问题：**本地 / 自托管模型的运行时自己暴露了一个搜索工具，但这个工具已经确定不可用，却仍反复诱导模型先调用一次。**

这类问题不能只靠 Prompt 里写“别用”，也不能只靠 `.local/state.json` 写 `blocked`。如果运行时仍把工具 schema 和配套 system prompt 注入每个新会话，模型每次都会重新看见它，造成重复失败和 token 浪费。

## 1. 两层禁用

### Logical circuit breaker

`.local/state.json` 记录：

- `status=blocked|cooldown|degraded|healthy`
- failure class / reason
- retry condition

它回答：**策略层还要不要调用这个 backend。**

### Physical tool suppression

运行时本身支持 tool enable/disable、plugin toggle、profile override、tool filter 或等价配置时，记录并执行真正的下架。

它回答：**下一会话里模型还看不看得到这个废弃工具。**

对于确定性硬失败，两层都要做；只有 `blocked` 而 tool 仍持续注册，视为未完成禁用。

## 2. 什么时候必须物理下架

仅适用于确定性失败：

- credential/key 明确缺失且当前不准备配置；
- 当前账号/订阅明确不支持；
- runtime/provider 配置缺失；
- endpoint/provider 明确 unsupported；
- 用户明确指定以后不要再使用该工具。

不适用于：

- timeout；
- 临时网络故障；
- 429/5xx；
- 偶发 provider unavailable；
- 搜索结果质量差但 transport 正常。

这些只进入 cooldown/degraded，不要因为一次临时故障就改运行时工具注册。

## 3. 自动修复流程

首次确认 runtime-native search 硬失败后：

```text
实际失败
↓
state 标 blocked
↓
检查 runtime 是否支持可逆的 tool disable/unregister
├─ 支持
│  ↓
│ 找到最小作用域配置（当前 profile/runtime 优先）
│  ↓
│ 只关闭失败的 search tool，不顺手关其它 web/fetch 能力
│  ↓
│ 缓存 config locator + suppression strategy 到 runtime.json
│  ↓
│ reload/restart/new session
│  ↓
│ 验证该 tool 已不再暴露
│  ↓
│ 缓存 verified_absent=true
│
└─ 不支持
   ↓
   保持 blocked
   ↓
   缓存 suppression_status=unsupported
   ↓
   后续绝不主动调用；只接受运行时无法隐藏 schema 的限制
```

这是用户已授权的搜索自愈行为：**对已经确定废弃的搜索入口，允许做最小、可逆、只影响该工具的本地运行时配置修改，不需要每次再次询问。** 如果修改会扩大权限、删除其它能力、影响非搜索功能或作用域无法判断，则仍需用户确认。

## 4. 本地缓存结构

具体路径、产品名和配置格式都属于机器事实，不写中央规则。建议记录：

```json
{
  "search": {
    "contexts": {
      "<context-id>": {
        "native_tools": {
          "<tool-id>": {
            "backend": "<backend-id>",
            "policy": "disabled",
            "suppression": {
              "strategy": "runtime-config|tool-filter|plugin-toggle|profile-override|other",
              "config_locator": "<local non-secret locator>",
              "scope": "<profile/session/runtime>",
              "verified_absent": true,
              "requires_restart": true
            }
          }
        }
      }
    }
  }
}
```

`config_locator` 可以是本机文件路径/配置 selector；禁止存 token/key 正文。

状态仍写：

```json
{
  "search": {
    "backends": {
      "<backend-id>": {
        "status": "blocked",
        "reason_code": "missing-credential",
        "suppression_status": "verified",
        "retry": "when-config-changes"
      }
    }
  }
}
```

## 5. 验证标准

物理禁用完成必须验证**下一会话/重载后的实际工具表**，不能只看配置文件写成功。

通过条件：

- 失败工具不再暴露给模型；
- 与它无关的本地搜索后端仍可用；
- 用户需要保留的 web/fetch/browser 能力没有被误关；
- 新搜索请求直接走 local-managed backend，不再先制造一次已知失败。

若运行时采用“工具稳定注册，即使 provider 不可用也始终暴露”的设计，那么单纯缺 key 不会自动让 schema 消失；必须使用运行时自己的 disable/filter 配置。

## 6. 禁止事项

- 不要只把报错写进回答，然后下一会话继续试。
- 不要把 `tool exposed` 当成 `tool healthy`。
- 不要为了关一个 search tool 禁掉整个 runtime。
- 不要删除用户 credential 或改写其它 provider。
- 不要对 timeout/429 这种暂态错误做永久 tool suppression。
- 不要把某个产品的固定配置路径写入中央 Prompt；第一次发现后缓存本机 locator。

一句话：**blocked 是告诉模型“别用”，physical suppression 是让模型“根本看不见”；确定性废弃搜索必须做到后者。**
