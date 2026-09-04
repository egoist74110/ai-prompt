# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

**权威顺序以 `router.md` 为准**，本文件只是给人看的概览，冲突时信 router。

## 核心架构

仓库只保存**可移植规则**；机器差异和已验证经验不再写死进 prompt / skill：

- `router.md`：统一入口；仓库内路径全部相对 `router.md` 解析。
- `skills/` / `capabilities/`：跨机器成立的能力规则和发现索引。
- `.local/runtime.json`：当前机器 OS、路径、运行时布局、credential locator、执行侧等本地配置；不提交。
- `.local/state.json`：当前机器已经实测跑通的 skill/MCP/search/API/headless strategy；不提交。
- `config/README.md`：local runtime/state 规范。
- `tools/local_state.py`：所有工具共用的本地状态读写库。
- `tools/runtime_state.py`：本地状态 CLI。
- `tools/doctor.py`：跨平台只读体检。
- `tools/sync_skills.py`：跨平台 runtime skill 同步核心。

统一优先级：**当前会话事实 > 本地 runtime/state > discovery**。第一次跑通后缓存非敏感结果，后续直接复用；缓存失效才重新探测。

## Read Order

- 所有模型先读 `router.md`，再由它进入完整工作流。
- `router.md` 要求先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- 需要工具能力时，只读 `capabilities/skills.md`、`capabilities/mcp.md`。
- 需要网页搜索/外部信息时读 `capabilities/search.md`；交付前做交叉审查时读 `capabilities/cross-review.md`。

## Rule

- 不要每次全量读取 `skills/` 或外部 `SKILL.md`。
- 不要在中央文档保存用户名、home、WSL distro、token 文件绝对路径、某台机器 VPN/网络拓扑、当前某 CLI 是否安装等单机事实。
- Token/密码/cookie/私钥正文不得写入 `.local/`；只能缓存 credential locator。
- Skill/MCP/search/headless runtime 首次成功 discovery 后，应把可复用的机器事实写入 `.local/`，避免后续重复绕路。
- 失败也可以缓存，但必须说明何时应重试，不能把临时失败写成中央永久规则。
- `skills/<name>/SKILL.md` frontmatter 是 skill 元数据唯一 source of truth；`capabilities/skills.md` 只是可重建发现索引。

## 本地初始化

```text
python tools/runtime_state.py init
python tools/runtime_state.py migrate
python tools/runtime_state.py show runtime
python tools/runtime_state.py show state
```

macOS/Linux 只有 `python3` 时使用 `python3`；Windows 可直接使用原生 Python。

## 维护

- `tools/runtime_state.py` — 初始化、迁移、读取和更新机器本地 runtime/state。
- `tools/doctor.py` — 跨平台只读体检；`tools/doctor.sh` 只是 Bash 兼容入口。
- `tools/sync_skills.py --runtime codex` — 跨平台同步中央 skills，并把真实 target/layout 写入 local runtime；`tools/sync-codex-skills.sh` 只是兼容入口。
- `tools/install-hooks.sh` — 安装 Git pre-commit hook；Git for Windows 环境可直接运行。
- `tools/gen-index.py` — 从 `skills/*/SKILL.md` frontmatter 生成 `capabilities/skills.md`；`--check` 校验漏项、幽灵项、name/目录名和机器绝对路径。

## 设计边界

中央仓库回答“**应该怎么做**”；`.local/` 回答“**这台机器具体怎么做已经跑通过**”。任何新的平台适配、MCP、Skill、Token 获取、搜索后端或外部工具接入，都应先判断它属于哪一层，再决定写中央文档还是写本地缓存。
