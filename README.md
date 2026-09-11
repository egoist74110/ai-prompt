# AI Prompt Hub

本目录是不同 AI Agent / 模型运行时共享的统一提示词入口。

**权威顺序以 `router.md` 为准**，本文件只是给人看的概览，冲突时信 router。

> **文档约束：给人看的用中文大白话，给 AI 执行的用简洁英文。** 新增或修改 Prompt 前先判断消费者，不要把两类文档混写。完整维护规则见 `CONTRIBUTING.md`。

## 核心架构

> **交互式架构图**：[docs/architecture/ai-prompt-architecture.html](docs/architecture/ai-prompt-architecture.html) —— 一张图看清加载链（router → common → 按需升级）、Skill 发现/加载、tools 工具链与 `.local/` 本机层的关系。支持缩放、深浅色切换和三个分视角（主加载链 / Skill 加载 / .local 本机层）。源文件是同目录的 `ai-prompt-architecture.json`，改完重新生成即可。

仓库只保存**可移植规则**；机器差异、运行时名单和已验证经验不再写死进 prompt / skill / Python：

- `router.md`：轻量统一入口，只负责判断当前请求走 Direct、Skill-first、Engineering 还是 Scout，并按当前意图动态切换。
- `common.md`：所有请求真正都需要的最小公共规则，不放工程验证、回归、交付之类的重规则；只保留跨路由都必须成立的安全/真实性底线。
- `models/high.md`：只服务 Engineering 路径；普通问答和单纯 Skill 执行不再默认加载。
- `models/scout.md`：只用于被委派的上下文收集、仓库侦查和低风险机械任务；超出委派范围后回到 router 重新选路，而不是默认跳 High。
- `skills/` / `capabilities/`：按触发条件加载的专业流程；禁止为了“可能有用”而全量塞入上下文。
- `capabilities/runtime.md`：只有需要 runtime registry、本机 discovery、共享 `.local` 状态时才加载。
- `capabilities/skill-maintenance.md`：只有创建、修改、重命名、删除、部署或同步 Skill 时才加载；正常执行 Skill 不需要它。
- `capabilities/cleanup.md`：任何路由只要产生任务自有的临时文件/进程/端口/配置等副作用，就按需加载 ownership/cleanup 规则；Engineering 额外执行完整回归与交付规则。
- `config/runtime-templates.json`：首次初始化的 starter runtime data；不是永久支持名单。
- `.local/runtime.json`：当前机器 OS、路径、**动态 runtime registry**、credential locator、执行侧等本地配置；不提交。
- `.local/state.json`：当前机器已经实测跑通的 skill/MCP/search/API/headless strategy；不提交。
- `tools/runtime_registry.py`：runtime seed/register/discovery 通用数据层，不认识具体产品名。
- `tools/runtime_state.py`：本地状态 + runtime registry CLI。
- `tools/doctor.py`：遍历本地 registry 做跨平台只读体检。
- `tools/sync_skills.py`：按 registry 中的 skills sync 声明做跨平台同步。

统一优先级：**当前会话事实 > 本地 runtime/state > discovery**。第一次跑通后缓存非敏感结果，后续直接复用；缓存失效才重新探测。

## 渐进式提示词加载

新的基本原则是：**永远从足够完成当前请求的最轻路径开始，只有当前能力不足时才升级；当前意图变轻时也允许降级。**

不是看到“代码”两个字就进入完整工程流程，也不是看到 Skill 会执行命令就自动加载 High。路由判断的是当前用户到底要完成什么，而不是话题属于哪个领域。

```text
普通问答 / 解释 / 简单代码知识
router + common
→ 直接回答

“提取这个 Bilibili 视频字幕”
router + common
→ skills index
→ bilibili-auto-transcript/SKILL.md
→ 执行

“分析这个仓库为什么登录失败”
router + common
→ Engineering
→ high
→ 按需 skills index / diagnose / MCP / scout

“直接修好，再让另一个 AI 审查”
已有 Engineering 上下文
→ implementation
→ cross-review
→ fix
→ re-review（按闭环规则继续）

“顺便解释一下刚才那个 API”
Engineering 上下文可以保留
→ 当前意图重新判定为 Direct
→ 不再继续套 Engineering gate
```

路由是**当前 intent 的属性，不是整段 conversation 的永久标签**。已经加载过的 Prompt 可以继续留在上下文里复用，但只有当前任务仍属于该路由时，对应 gate 才继续生效。

为了防止架构再次退化成“不断往总 Prompt 里堆东西”，测试不再只看单个文件有多大，而是检查 Direct / Scout / Engineering / Skill-discovery 的**基础加载链预算**，并检查 capability 触发覆盖、跨文件引用与 section anchor 是否闭环。

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

- 所有模型先读 `router.md`，然后只读最小 `common.md`。
- **Direct**：普通问答、解释、总结、翻译、头脑风暴、简单代码/API/语法问题，直接处理；默认不读 `models/high.md`。
- **Skill-first**：用户点名 Skill 或请求明确命中 Skill metadata 时，只读 `capabilities/skills.md` 做发现，再加载匹配的 `skills/<name>/SKILL.md`；不会因为 Skill 会运行命令或输出文件就自动进入 High。
- **Engineering**：真正需要仓库/项目工程流程时才读 `models/high.md`，包括实现、代码/配置修改、项目调试、架构/重构、代码审查、构建/部署变更、较重的仓库分析和实现规划。当前 runtime 没有直接暴露中央 Skill metadata 时，规划前读一次 `capabilities/skills.md`，避免 canonical Skill 静默失效。
- **Scout**：被要求做侦查、上下文收集、机械执行时，只读 `models/scout.md`；任务超出 Scout 委派范围时回到 router 重新判断当前 intent，不默认跳 High。
- Skill 的创建/修改/部署维护才加载 `capabilities/skill-maintenance.md`；普通 Skill 执行不加载。
- 需要 runtime registry、本机 discovery 或共享 `.local` 状态时才加载 `capabilities/runtime.md`。
- MCP、搜索、交叉审查等能力继续按各自 trigger 加载，不做预加载。
- 任何路由如果会启动任务自有进程、占用端口、修改临时配置/权限或产生临时/非请求文件，在首次副作用前加载 `capabilities/cleanup.md`；非 Engineering 只应用必要的 ownership/cleanup，Engineering 再执行完整回归与交付。
- 网页搜索按实际后端可用性分流：有可用平台原生搜索且无需回退时不必加载搜索策略；需要选择后端、回退或处理失败时读取 `capabilities/search.md`。

## Local Search

`capabilities/search.md` 是按需加载的后端选择与失败处理策略；模型 hosting 和后端可用性是独立事实。

核心流程：

```text
当前任务需要外部信息
→ 读本地 search context/backend/state
→ 按任务 role 选 repo/general/accurate/precise/fetch 后端
→ 第一轮搜索
→ 检查实体对齐、来源质量、时效性、SEO/退化信号
→ 结果弱：自动改写查询 + 切第二后端
→ 确定性失败 blocked；临时失败 cooldown；弱质量 degraded
→ 跑通过的本机 locator/roles/priority 以后直接复用
```

具有可用原生搜索、且不需要回退的上下文，无需加载这套策略。

## Regression / Cleanup Gate

`capabilities/cleanup.md` 分成两层理解：

- **任何路由**：只要产生任务自有副作用，就使用必要的 baseline / ownership / failure-path / cleanup 规则，避免浏览器、进程、临时配置、文件残留或误删用户原有状态。
- **Engineering**：在上述基础上执行完整的 regression、workspace hygiene、post-cleanup smoke 和 delivery gate。

Skill-first 产生一个用户明确请求的正常输出文件，并不自动变成 Engineering；真正触发 cleanup 的是任务自有的临时/辅助副作用。

Engineering 任务不是“功能跑通”就结束，而是：

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

- 不要每次全量读取 `skills/`、capabilities 或外部 `SKILL.md`。
- 不要把“涉及代码”直接等价为 Engineering；简单代码知识仍然可以 Direct。
- 不要把“Skill 会执行命令/写文件”直接等价为 Engineering；看用户真实意图和 Skill 自己的流程。
- 不要因为之前一轮进入了 Engineering，就让后续普通问答继续继承 Engineering gate。
- 安装/启用新的外部工具、plugin、connector 或扩大持久权限前，必须先说明原因/影响并取得用户确认。
- 不要在中央文档保存用户名、home、WSL distro、token 文件绝对路径、某台机器 VPN/网络拓扑、当前某 CLI 是否安装等单机事实。
- 不要在消费者代码里维护固定 runtime 名单、固定优先级或固定 runtime-specific 路径。
- Token/密码/cookie/私钥正文不得写入 `.local/`；只能缓存 credential locator。
- Skill/MCP/search/headless runtime 首次成功 discovery 后，应把可复用的机器事实写入 `.local/`，避免后续重复绕路。
- 失败也可以缓存，但必须说明何时应重试，不能把临时失败写成中央永久规则。
- 任何路由的 task-owned 临时副作用都应在任务结束或失败路径中恢复到合理 baseline；Engineering 额外执行完整回归/交付闭环。
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

修改 Prompt 或文档前先看 `CONTRIBUTING.md`。它规定了人类文档与机器 Prompt 的语言、写法和职责边界。

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
