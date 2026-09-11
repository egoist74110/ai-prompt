# Local Runtime / State Contract

本目录只保存**规范与初始化模板**；真实机器配置必须写到仓库根目录的 `.local/`，该目录被 git 忽略，禁止提交。

## 两类本地数据

### `.local/runtime.json`

保存“这台机器是什么、资源在哪里”的相对稳定事实，例如：

- 当前 OS / shell / 是否处于 WSL
- home、WSL distro、Python/CLI 可执行文件路径
- 动态 runtime registry：任意 AI CLI / Agent 的 command、entry、skills、capabilities、review invocation
- reviewer 的已验证 continuation strategy / resume args / native cache locator
- credential locator（去哪里取，不保存 secret）
- 某个服务从 Windows/WSL/macOS 哪一侧执行
- Search/MCP/headless 后端的命令或配置 locator
- Search context：runtime/provider/model 的 hosting、lane、endpoint、preferred backends
- 已废弃 runtime-native tool 的**物理禁用 locator/strategy**

**禁止保存 token、密码、cookie、私钥正文。** 只允许保存 locator，例如文件路径、keychain service/account、环境变量名或读取命令。

### `.local/state.json`

保存“这台机器已经实测过什么”的经验缓存，例如：

- Skill 已验证 strategy
- MCP transport / configured / last verified
- 搜索后端 healthy/degraded/cooldown/blocked、失败原因、重试条件
- runtime-native 搜索工具的 suppression 是否 pending/verified/unsupported
- headless review 是否跑通
- cross-review 的 review session、round、session ref/cache locator、finding ledger 与 continuation 状态
- 网络/API/编码/字段等环境实测事实

它不是永久真理。**新的实际执行结果**可以刷新缓存；“tool 被暴露”本身不算成功事实，不能覆盖已经验证的 blocked 状态。

## Review Session / Conversation Continuity

代码审核是可持续的多轮会话，不是每一轮重新调用一个失忆 reviewer。

每次新的跨 AI 审核创建稳定 `review_id`，并在仓库内建立：

```text
.local/reviews/<review_id>/
```

这里保存非敏感的审核请求/响应快照、finding ledger、round metadata 和 continuation notes。索引状态写入：

```text
.local/state.json -> cross_review.sessions.<review_id>
```

至少记录：

- `runtime_id` / `runtime_identity`
- repository/worktree + scope
- `session_ref`
- `cache_locator`
- `continuation_strategy`
- `continuity`
- `round`
- `last_reviewed_boundary`
- `last_result`
- `open_findings`

Reviewer 自己的原生 conversation cache 可以位于 CLI/runtime 的默认目录；不要为了统一目录复制 opaque cache。只记录实际验证过、能够恢复该会话的非敏感 locator/session id。

Runtime registry 中 `review.continuation` 是**机器事实**，建议结构：

```text
review.continuation.strategy = native-session|persistent-process|cwd-cache|unknown|unsupported
review.continuation.resume_args = [<runtime-specific verified args; may contain {session_ref}>]
review.continuation.session_ref_source = stdout|stderr|cache-metadata|process|none
review.continuation.cache_locator = <non-secret verified locator or null>
```

这些值不得靠中央文档猜测。第一次需要多轮 review 时，对当前 runtime 做最小 discovery，验证后写入本地 runtime/state。产品版本升级、cache 被清理或 resume 失败时，应重新验证。

第二轮及以后必须：

1. 使用相同 `review_id` 与 `runtime_identity`；
2. resume 同一个 native reviewer conversation；
3. 先让 reviewer 复核上一轮 finding 的关闭状态；
4. 再检查修复造成的 regression / 新问题；
5. 复用同一 finding id 表示同一缺陷。

如果原会话无法恢复，不能静默启动新会话并称为“二审”。将 `continuity=broken`，保留旧审核记录，并由用户决定是否开一个新的 review session。详细行为以 `capabilities/cross-review.md` 为准。

## Runtime Registry：模板不是名单

`config/runtime-templates.json` 只是首次初始化 starter data，不是永久支持名单。中央 Python 不允许按产品名分支。

初始化：

1. seed 尚未存在的 starter entry；
2. 对 registry 中每个启用条目统一探测 `command_candidates`、`entry_candidates`、`skills_candidates`；
3. seed 后本地 registry 是权威；用户修改/禁用/自定义的值不被普通 detect 覆盖。

新增任意 runtime：

```text
python tools/runtime_state.py runtime add <runtime-id> \
  --display-name "<name>" \
  --commands-json '["<command>"]' \
  --entries-json '["~/<runtime-dir>/<entry-file>"]' \
  --skills-json '["~/<runtime-dir>/skills"]' \
  --capabilities-json '["agent","review","skills"]' \
  --skills-sync-mode per-skill-link \
  --review-args-json '["<headless-arg>"]' \
  --review-priority 70
```

常用命令：

```text
python tools/runtime_state.py runtime list
python tools/runtime_state.py runtime detect <runtime-id> --refresh
python tools/runtime_state.py runtime disable <runtime-id>
python tools/runtime_state.py runtime enable <runtime-id>
python tools/runtime_state.py runtime remove <runtime-id>
python tools/runtime_state.py runtime seed --refresh-templates
```

`seed --refresh-templates` 只补缺失声明字段，不覆盖本地解析值或 `source=user` 的自定义 runtime。

## Search Context / Circuit Breaker / Tool Suppression

搜索状态分三层，不能混在一起：

### 1. Execution context

写：

```text
.local/runtime.json -> search.contexts.<context-id>
```

保存 runtime/provider/model、`hosting=cloud|local|self-hosted|unknown`、`lane`、非敏感 endpoint、preferred backends。

用：

```text
python tools/search_state.py context-set <context-id> \
  --runtime <runtime-id> \
  --provider <provider-id> \
  --model <model> \
  --hosting self-hosted \
  --endpoint http://127.0.0.1:<port> \
  --preferred-backends-json '["<backend-id>"]'
```

`hosting=self-hosted|local` 会导出 `lane=local-managed`；`hosting=cloud` 导出 `lane=cloud-native`。不要再使用旧的 `--native-search-policy` 参数。

### 2. Search backend config + logical circuit breaker

配置写：

```text
.local/runtime.json -> search.backends.<backend-id>
```

健康/失败写：

```text
.local/state.json -> search.backends.<backend-id>
```

常用：

```text
python tools/search_state.py plan --context <context-id> --role general
python tools/search_state.py fail <backend-id> --class missing-credential --reason "missing key"
python tools/search_state.py fail <backend-id> --class timeout --reason "timeout" --retry-after-minutes 15
python tools/search_state.py success <backend-id>
python tools/search_state.py reset <backend-id>
```

失败分类：

- `auth/config/permission/unsupported/missing-credential/subscription` → `blocked`，仅配置变化后重试。
- `transient/timeout/network/server/rate-limit/quota` → `cooldown`。
- `quality` → `degraded`，降低优先级但不永久禁用。
- 成功 → `healthy`。

### 3. Runtime-native tool physical suppression

这是逻辑熔断之外的第三层。

某些 runtime 会稳定注册 `web_search` 一类工具：即使 provider/key 缺失，tool schema 和 system guidance 仍会出现在每个新会话，只在真正执行时才失败。此时：

```text
state.status=blocked
```

**并不足以阻止下一会话再次被工具提示诱导。**

对于确定性硬失败，并且 runtime 支持可逆的 tool disable/unregister/filter：

1. 先把 backend 标 `blocked`；
2. discovery 当前 runtime 最小作用域的禁用方式；
3. 只关闭失败的 search tool，不顺手关闭其它 web/fetch/browser 能力；
4. 把本机 locator/strategy 写 `runtime.json`；
5. reload/restart/new session；
6. 验证 tool schema 中已不存在；
7. state 记录 `suppression_status=verified`。

建议结构：

```text
.local/runtime.json
  search.contexts.<context-id>.native_tools.<tool-id>
    backend
    policy=disabled
    suppression.strategy
    suppression.config_locator
    suppression.scope
    suppression.verified_absent
    suppression.requires_restart

.local/state.json
  search.backends.<backend-id>
    status=blocked
    reason_code=<hard failure>
    suppression_status=pending|verified|unsupported
```

具体产品配置路径、profile 名、插件 id 属于**本机 discovery 结果**，不得变成中央代码常量。完整规则见 `capabilities/search-runtime-suppression.md`。

不要对 timeout/429/5xx 等瞬时错误做物理 suppression；只 cooldown。

## 优先级

处理 Skill / MCP / Search / 外部 API / headless runtime 时：

1. 当前会话**实际执行结果**；
2. 本地 `runtime/state` 已验证事实；
3. 缓存缺失或失效才 discovery；
4. 中央文档只给可移植规则/候选策略。

**工具暴露不是实际成功。** 已有 blocked/cooldown 时，不能因为 tool list 仍有入口就再次试探；确定性 hard-blocked runtime-native search 还应按上节做物理下架。

Discovery 成功后必须写回非敏感结果。失败也要缓存 failure class + retry condition，不能只留在对话里。

## 路径规则

仓库内部全部以 `router.md` 所在目录为 `AI_PROMPT_ROOT`，使用相对路径。

中央文档禁止写具体用户 home、WSL distro、token 文件绝对路径等机器事实。外部绝对路径可以存在 `.local/runtime.json`，因为它本来就是单机配置。

## 代码结构

- `config/runtime-templates.json`：starter data，不是 runtime 白名单。
- `tools/local_state.py`：本地配置/状态读写库。
- `tools/runtime_registry.py`：runtime seed/register/discovery 数据层。
- `tools/runtime_state.py`：runtime/state CLI。
- `tools/search_state.py`：search context、backend 排序和 circuit breaker。
- `tools/bootstrap.py`：遍历 registry 做机器发现。
- `tools/sync_skills.py`：按 registry 声明同步 Skill。
- `tools/doctor.py`：跨平台体检。
- `tools/*.sh`：只做兼容入口，不承载主要跨平台逻辑。

## 初始化、迁移与通用读写

```text
python tools/runtime_state.py init
python tools/runtime_state.py migrate
python tools/runtime_state.py detect --refresh
python tools/runtime_state.py show runtime
python tools/runtime_state.py show state
python tools/runtime_state.py get state skills.ado-pr.strategy
python tools/runtime_state.py set state skills.ado-pr.strategy '"windows-rest"'
python tools/runtime_state.py unset state skills.ado-pr
```

macOS/Linux 只有 `python3` 时用 `python3`；Windows 用 `py`/`python` 均可。

`init` 创建缺失文件、seed starter templates 并做首次 discovery；`migrate` 只补 schema/模板缺失，不覆盖现有机器配置。`set` 的值按 JSON 解析。

示例：

- `config/runtime.example.json`
- `config/state.example.json`
