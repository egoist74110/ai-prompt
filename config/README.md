# Local Runtime / State Contract

本目录只保存**规范与初始化模板**；真实机器配置必须写到仓库根目录的 `.local/`，该目录被 git 忽略，禁止提交。

## 两类本地数据

### `.local/runtime.json`

保存“这台机器是什么、资源在哪里”的相对稳定事实，例如：

- 当前 OS / shell / 是否处于 WSL
- home、WSL distro、Python/CLI 可执行文件路径
- **动态 runtime registry**：任意 AI CLI / Agent 的 command、entry、skills、capabilities、review invocation
- 某个凭据应该从 keychain / 文件 / 环境变量中的哪里读取
- 某个服务应该从 Windows 宿主、WSL、macOS 哪一侧发请求
- 搜索/MCP/headless review 后端的命令或配置 locator
- **搜索执行上下文**：当前 runtime/provider/model 是 cloud、local/self-hosted 还是 unknown，以及是否允许 runtime-native search

**禁止保存 token、密码、cookie、私钥正文。** 只允许保存 credential locator，例如 `{"type":"file","path":"..."}`、`{"type":"keychain","service":"..."}` 或环境变量名。

### `.local/state.json`

保存“这台机器上已经实测跑通过什么”的经验缓存，例如：

- skill 已验证的 strategy
- MCP 是否已配置、transport、最近一次验证时间
- 搜索后端是否健康、为什么失败、是否 blocked/cooldown/degraded、何时才值得重试
- 某个 registry runtime 的 headless 审查是否可用
- 某个服务在 WSL/Windows/macOS 哪一侧可达
- API 返回编码 / 字段差异等与当前环境相关的实测结果

它不是永久真理。当前会话**新的实际执行结果**可以更新缓存；但“工具被暴露”本身不算成功事实，不能覆盖已经验证的失败状态。

## Runtime Registry：模板不是名单

`config/runtime-templates.json` 只是**首次初始化模板**。它可以放一些常见 runtime 的候选命令/入口，但中央 Python 代码不得出现“只支持某几个产品”的分支。

初始化时：

1. 把尚未存在的 starter template seed 到 `.local/runtime.json.runtimes`。
2. 对 registry 中每个启用条目统一探测 `command_candidates`、`entry_candidates`、`skills_candidates`。
3. seed 完成后，本地 registry 是权威；用户删除、禁用或修改条目，后续普通 detect 不会被模板重新覆盖。

因此 Qwen Code、opencode、私有 Agent、自研 CLI 等都不需要修改中央代码，只需注册本地条目。

### 注册任意 runtime

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

所有字段都是可选的；只需要填该工具实际支持的部分。注册后默认立即做一次 detect。

常用管理命令：

```text
python tools/runtime_state.py runtime list
python tools/runtime_state.py runtime detect <runtime-id> --refresh
python tools/runtime_state.py runtime disable <runtime-id>
python tools/runtime_state.py runtime enable <runtime-id>
python tools/runtime_state.py runtime remove <runtime-id>
python tools/runtime_state.py runtime seed --refresh-templates
```

`runtime seed --refresh-templates` 只补缺失的模板声明字段，不覆盖已有本地解析值或 `source=user` 的自定义 runtime。

## Search Context / Circuit Breaker

搜索需要区分“当前模型/provider 在哪里运行”和“某个搜索入口是否健康”。

稳定的执行上下文写入：

```text
.local/runtime.json -> search.contexts.<context-id>
```

例如保存 runtime/provider/model、`hosting=cloud|local|self-hosted|unknown`、非敏感 endpoint、`native_search_policy`、preferred backends。

搜索后端配置写：

```text
.local/runtime.json -> search.backends.<backend-id>
```

后端健康/失败状态写：

```text
.local/state.json -> search.backends.<backend-id>
```

统一使用 `tools/search_state.py`：

```text
python tools/search_state.py context-set <context-id> --hosting self-hosted --native-search-policy deny
python tools/search_state.py plan --context <context-id>
python tools/search_state.py fail <backend-id> --class missing-credential --reason "missing key"
python tools/search_state.py fail <backend-id> --class timeout --reason "timeout" --retry-after-minutes 15
python tools/search_state.py success <backend-id>
python tools/search_state.py reset <backend-id>
```

失败分类：

- `auth/config/permission/unsupported/missing-credential/subscription` → `blocked`，只在配置变化后重试。
- `transient/timeout/network/server/rate-limit/quota` → `cooldown`，到期后才允许再次尝试。
- `quality` → `degraded`，降低优先级但不永久禁用。
- 成功 → `healthy`，清除熔断。

本地/self-hosted context 默认不能因为 runtime 暴露了一个需要云端订阅/key 的 `web_search` 就直接调用；详见 `capabilities/search.md`。

## 优先级

处理 skill / MCP / 搜索 / 外部 API / headless runtime 时统一遵循：

1. **当前会话实际结果**：真正成功/失败的工具调用、当前命令输出、当前环境变量。
2. **本地 runtime/state**：`.local/runtime.json`、`.local/state.json` 中已验证的信息。
3. **Discovery**：只有前两层无法解决或缓存失效时才探测。
4. **中央文档**：只保存可移植规则、候选策略和服务固有事实，不保存单机事实。

注意：**工具被暴露不是“实际成功结果”**。已有 blocked/cooldown 状态时，不能因为 tool list 里仍然有该工具就重新试探。

Discovery 一旦成功，必须把可复用的非敏感结果写回 `.local/`，避免下一次重复绕路和浪费 token。失败也必须写明可失效条件，不能只留在当前对话里。

## 路径规则

仓库内路径全部以 `router.md` 所在目录为根（`AI_PROMPT_ROOT`）。中央文档禁止写具体用户 home 的绝对路径。

外部绝对路径允许存在于 `.local/runtime.json`，因为它本来就是机器本地配置。运行时临时生成的目标项目绝对路径也可以出现在本次命令/提示词中，但不能回写中央文档。

## 代码结构

- `config/runtime-templates.json`：仅首次初始化用的 starter data，不是永久 runtime 名单。
- `tools/local_state.py`：本地配置/状态的唯一读写库。
- `tools/runtime_registry.py`：runtime seed / register / discovery 的通用数据层，不认识具体产品名。
- `tools/runtime_state.py`：给人/Agent 使用的通用 runtime/state CLI。
- `tools/search_state.py`：搜索执行上下文、后端排序和持久熔断状态。
- `tools/bootstrap.py`：遍历本地 registry 做机器发现。
- `tools/sync_skills.py`：按 registry 声明的 `skills_sync_mode` 跨平台同步。
- `tools/doctor.py`：遍历 registry 做跨平台只读体检。
- `tools/*.sh`：只保留兼容入口或 Git hook 场景，不再承载主要跨平台逻辑。

## 初始化、迁移与读写

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

macOS/Linux 只有 `python3` 时把 `python` 换成 `python3`。Windows 可直接使用 `py`/`python` 调同一脚本。

`init` 会创建缺失文件、seed starter runtime templates 并做首次 discovery；`migrate` 只补 schema/首次模板缺失，不覆盖已有机器配置和缓存。`set` 的值按 JSON 解析，例如字符串必须带 JSON 引号，布尔值直接写 `true/false`。

示例结构见：

- `config/runtime.example.json`
- `config/state.example.json`
