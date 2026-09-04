# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

**权威顺序以 `router.md` 为准**，本文件只是给人看的概览，冲突时信 router。

## 核心架构

仓库只保存**可移植规则**；机器差异、运行时名单和已验证经验不再写死进 prompt / skill / Python：

- `router.md`：统一入口；仓库内路径全部相对 `router.md` 解析。
- `skills/` / `capabilities/`：跨机器成立的能力规则和发现索引。
- `config/runtime-templates.json`：首次初始化的 starter runtime data；不是永久支持名单。
- `.local/runtime.json`：当前机器 OS、路径、**动态 runtime registry**、credential locator、执行侧等本地配置；不提交。
- `.local/state.json`：当前机器已经实测跑通的 skill/MCP/search/API/headless strategy；不提交。
- `tools/runtime_registry.py`：runtime seed/register/discovery 通用数据层，不认识具体产品名。
- `tools/runtime_state.py`：本地状态 + runtime registry CLI。
- `tools/doctor.py`：遍历本地 registry 做跨平台只读体检。
- `tools/sync_skills.py`：按 registry 中的 skills sync 声明做跨平台同步。

统一优先级：**当前会话事实 > 本地 runtime/state > discovery**。第一次跑通后缓存非敏感结果，后续直接复用；缓存失效才重新探测。

## Runtime Registry

初始化：

```text
python tools/runtime_state.py init
python tools/runtime_state.py runtime list
```

`init` 会把 starter template seed 到本地 registry，再统一探测；之后本地 registry 是权威。

新增任何 AI CLI/runtime 不需要改中央代码，例如：

```text
python tools/runtime_state.py runtime add <runtime-id> \
  --commands-json '["<command>"]' \
  --capabilities-json '["agent","review","skills"]'
```

还可以配置 entry/skills 候选目录、Skill 同步模式、headless review 参数和优先级。详见 `config/README.md`。

**原则：代码只遍历 registry，不允许按 Claude/Codex/Gemini/Qwen Code/其它产品名写分支。** 这些名字最多只能出现在 `config/runtime-templates.json` 这种可替换 starter data 里。

## Read Order

- 所有模型先读 `router.md`，再由它进入完整工作流。
- `router.md` 要求先读 `common.md`。
- 高级模型处理完整问题时，再读 `models/high.md`。
- 被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`，不要再读 `models/high.md`。
- 需要工具能力时，只读 `capabilities/skills.md`、`capabilities/mcp.md`。
- 网页搜索按当前 API/provider 分流：
  - cloud + 平台自带搜索 → 直接使用平台搜索，**不读取 `capabilities/search.md`**；
  - local/self-hosted → 才读取 `capabilities/search.md`，使用本机已配置搜索后端。
- 实现任务产生文件/进程/端口/配置副作用时，最终交付前读 `capabilities/cleanup.md`。
- 交付前做交叉审查时读 `capabilities/cross-review.md`。

## Local Search

`capabilities/search.md` 是本地/自托管模型专用的联网策略，不是云端模型的公共搜索 Prompt。

核心流程：

```text
本地模型需要外部信息
→ 读本地 search context/backend/state
→ 按任务 role 选 repo/general/accurate/precise/fetch 后端
→ 第一轮搜索
→ 检查实体对齐、来源质量、时效性、SEO/退化信号
→ 结果弱：自动改写查询 + 切第二后端
→ 确定性失败 blocked；临时失败 cooldown；弱质量 degraded
→ 跑通过的本机 locator/roles/priority 以后直接复用
```

云端模型不需要为这套本地搜索策略占用上下文 token。

## Regression / Cleanup Gate

`capabilities/cleanup.md` 定义实现任务最后的“回归 + 清场”闭环。

任务不是“功能跑通”就结束，而是：

```text
实现
→ 必要回归
→ 必要交叉审查 / 补修 / 复验
→ 检查 git diff + untracked
→ 删除本次临时文件/调试产物
→ 停止本次启动且不需常驻的 server/watcher/browser/worker/MCP
→ 恢复本次临时配置/权限
→ 相关端口恢复到开工 baseline
→ 清场后再做一次最小 smoke
→ 交付
```

开工时先区分用户原有状态与本次 task-owned 资源；清场只处理能确认属于本次任务的东西。**禁止为了干净而误删用户原有 untracked 文件、误杀已有进程，也禁止默认使用 `git clean -fd` / `git reset --hard` / `killall` / `pkill` 这类粗暴手段。**

任务中途失败也要清本次已产生的临时资源；用户明确要求保留的 artifact/服务则保留并在交付中说明。

## Rule

- 不要每次全量读取 `skills/` 或外部 `SKILL.md`。
- 不要在中央文档保存用户名、home、WSL distro、token 文件绝对路径、某台机器 VPN/网络拓扑、当前某 CLI 是否安装等单机事实。
- 不要在消费者代码里维护固定 runtime 名单、固定优先级或固定 runtime-specific 路径。
- Token/密码/cookie/私钥正文不得写入 `.local/`；只能缓存 credential locator。
- Skill/MCP/search/headless runtime 首次成功 discovery 后，应把可复用的机器事实写入 `.local/`，避免后续重复绕路。
- 失败也可以缓存，但必须说明何时应重试，不能把临时失败写成中央永久规则。
- **收尾属于任务本身**：本次临时文件、进程、端口、配置、副作用应在交付前恢复到合理 baseline。
- `skills/<name>/SKILL.md` frontmatter 是 skill 元数据唯一 source of truth；`capabilities/skills.md` 只是可重建发现索引。

## 本地初始化

```text
python tools/runtime_state.py init
python tools/runtime_state.py migrate
python tools/runtime_state.py detect --refresh
python tools/runtime_state.py show runtime
python tools/runtime_state.py show state
```

macOS/Linux 只有 `python3` 时使用 `python3`；Windows 可直接使用原生 Python。

## 维护

- `tools/runtime_state.py` — 初始化、迁移、runtime 注册、读取和更新机器本地 runtime/state。
- `tools/runtime_registry.py` — 数据驱动 runtime registry 核心。
- `tools/bootstrap.py` — 遍历 registry 做本机 discovery。
- `tools/search_state.py` — 本地搜索 context、backend role 计划、熔断状态管理。
- `tools/doctor.py` — 跨平台只读体检；`tools/doctor.sh` 只是 Bash 兼容入口。
- `tools/sync_skills.py --runtime <runtime-id>` — 同步指定 registry runtime。
- `tools/sync_skills.py --all --auto-only` — 同步所有声明自动同步的 registry runtime。
- `tools/install-hooks.sh` — 安装 Git pre-commit hook；Git for Windows 环境可直接运行。
- `tools/gen-index.py` — 从 `skills/*/SKILL.md` frontmatter 生成 `capabilities/skills.md`；`--check` 校验漏项、幽灵项、name/目录名和机器绝对路径。

## 设计边界

中央仓库回答“**应该怎么做 / 首次可用什么模板**”；`.local/` 回答“**这台机器实际有哪些工具，以及具体怎么做已经跑通过**”。任何新的 runtime、平台适配、MCP、Skill、Token 获取、搜索后端或外部工具接入，都应先判断它属于哪一层，再决定写 starter template、中央规则还是本地缓存。
