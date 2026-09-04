# Local Runtime / State Contract

本目录只保存**规范与示例**；真实机器配置必须写到仓库根目录的 `.local/`，该目录被 git 忽略，禁止提交。

## 两类本地数据

### `.local/runtime.json`

保存“这台机器是什么、资源在哪里”的相对稳定事实，例如：

- 当前 OS / shell / 是否处于 WSL
- Windows home、WSL distro、可执行文件路径
- 某个凭据应该从 keychain / 文件 / 环境变量中的哪里读取
- 某个服务应该从 Windows 宿主、WSL、macOS 哪一侧发请求

**禁止保存 token、密码、cookie、私钥正文。** 只允许保存 credential locator，例如 `{"type":"file","path":"..."}` 或 `{"type":"keychain","service":"..."}`。

### `.local/state.json`

保存“这台机器上已经实测跑通过什么”的经验缓存，例如：

- skill 已验证的 strategy
- MCP 是否已配置、transport、最近一次验证时间
- 某个服务在 WSL 侧是否可达
- API 返回编码 / 字段差异等与当前环境相关的实测结果

它不是永久真理。当前会话事实永远优先于缓存；缓存路径/命令/连接失败时，应重新 discovery，成功后覆盖旧值。

## 优先级

处理 skill / MCP / 外部 API 时统一遵循：

1. **当前会话事实**：已经暴露的工具、当前命令实际输出、当前环境变量。
2. **本地 runtime/state**：`.local/runtime.json`、`.local/state.json` 中已验证的信息。
3. **Discovery**：只有前两层无法解决或缓存失效时才探测。
4. **中央文档**：保存可移植规则、候选策略和服务固有事实，不保存单机事实。

Discovery 一旦成功，必须把可复用的非敏感结果写回 `.local/`，避免下一次重复绕路和浪费 token。

## 路径规则

仓库内路径全部以 `router.md` 所在目录为根（`AI_PROMPT_ROOT`），禁止在中央文档里写 `/Users/<name>/.ai-prompt/...`、`C:\\Users\\<name>\\...` 等单机绝对路径。

外部路径允许存在于 `.local/runtime.json`，因为它本来就是机器本地配置。

## 初始化与读写

使用纯标准库脚本：

```text
python tools/runtime_state.py init
python tools/runtime_state.py show runtime
python tools/runtime_state.py show state
python tools/runtime_state.py get state skills.ado-pr.strategy
python tools/runtime_state.py set state skills.ado-pr.strategy '"windows-rest"'
python tools/runtime_state.py unset state skills.ado-pr
```

macOS 若只有 `python3`，把上面的 `python` 换成 `python3`。

`set` 的值按 JSON 解析；例如字符串必须带 JSON 引号，布尔值直接写 `true/false`。
