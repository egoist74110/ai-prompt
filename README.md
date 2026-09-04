# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

**权威顺序以 `router.md` 为准**，本文件只是给人看的概览，冲突时信 router。

## 核心架构

仓库只保存**可移植规则**；机器差异和已验证经验不再写死进 prompt / skill：

- `router.md`：统一入口；仓库内路径全部相对 `router.md` 解析。
- `skills/` / `capabilities/`：跨机器成立的能力规则和索引。
- `.local/runtime.json`：当前机器的 OS、路径、credential locator、执行侧等本地配置；不提交。
- `.local/state.json`：当前机器上已经实测跑通的 skill/MCP/API strategy；不提交。
- `config/README.md`：local runtime/state 规范。
- `tools/runtime_state.py`：纯 Python 标准库的跨平台本地状态读写工具。

统一优先级：**当前会话事实 > 本地 runtime/state > discovery**。第一次跑通后缓存非敏感结果，后续直接复用；缓存失效才重新探测。

## Read Order

- 所有模型先读 `router.md`，再由它进入完整工作流。
- `router.md` 要求先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- 需要工具能力时，只读索引：`capabilities/skills.md`、`capabilities/mcp.md`。
- 需要网页搜索/外部信息时读 `capabilities/search.md`；交付前做交叉审查时读 `capabilities/cross-review.md`。

## Rule

- 不要每次全量读取 `skills/` 或外部 `SKILL.md`。
- 不要在中央文档里保存用户名、home、WSL distro、token 文件绝对路径、某台机器的 VPN/网络拓扑等单机事实。
- Token/密码/cookie/私钥正文不得写入 `.local/`；只能缓存 credential locator。
- Skill/MCP 首次成功 discovery 后，应把可复用的机器事实写入 `.local/`，避免后续重复绕路。

## 本地初始化

```text
python tools/runtime_state.py init
python tools/runtime_state.py show runtime
python tools/runtime_state.py show state
```

macOS 只有 `python3` 时使用 `python3`。

## 维护

- `tools/runtime_state.py` — 初始化、读取和更新机器本地 runtime/state。
- `tools/doctor.sh` — 现有部署体检；后续应逐步只依赖相对 root 和本地 runtime，而不是硬编码机器路径。
- `tools/install-hooks.sh` — 安装仓库 pre-commit hook。
- `tools/gen-index.py` — 重建 `capabilities/skills.md` Auto 登记表，并校验索引。
- `tools/sync-codex-skills.sh` — 同步中央 skills 到当前 Codex skills 布局；具体布局应以当前机器实测/runtime 为准。
