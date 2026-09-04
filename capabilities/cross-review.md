# 交叉审查（Cross-Review：不同高级模型互审代码）

实现方与审查方**不能是同一个运行时**。本文件只保存跨机器成立的流程；可用运行时、命令、权限、trusted workspace、headless 能力都属于本地 runtime/state，不写死在中央文档。

## 先判身份（递归终止条件）

- **实现方**：当前请求要你写/改代码并交付 → 才适用本文件的派审流程。
- **审查方 / 验证方**：当前请求明确限定为只读、只出意见、不改代码 → 完成审查后结束。

**审查方绝对不得再次派交叉审查。** 身份按当前阶段重判；实现完自己复看只是自检，不算跨运行时审查。

## 何时用

1. 用户明确要求“审查 / 交叉审查 / 审一下”等 → 直接执行，不二次确认。
2. 用户没提，但改动命中高风险面（安全、关键数据流、跨模块重构、上线就绪、高模自检仍不确定）→ 先说明建议派哪个运行时审什么，等用户确认。
3. 非交互 headless 场景且用户没有事先授权 → 不擅自消耗另一个运行时额度；把建议写进输出后结束。

trivial 修复、纯配置、一行改动、无外部副作用的局部逻辑可直接自检交付。

## 审查运行时选择：只读 registry，不认固定名字

候选只来自 `.local/runtime.json.runtimes`。中央**不维护 Claude / Codex / Gemini / Qwen Code / 其它 CLI 的固定名单或固定顺序**。

筛选规则：

1. `enabled != false`。
2. `capabilities` 包含 `review`。
3. runtime id 不等于当前实现方。
4. 有已解析的 `executable`，或可通过它自己的 `command_candidates` 做最小 discovery。
5. `review.args` 已配置；如果该 CLI 不需要额外参数，可以是空数组。
6. 优先使用 `.local/state.json.cross_review.runtimes.<id>.headless_verified == true` 的条目。
7. 多个都可用时按 registry 中 `review.priority` 从高到低；没填优先级的排在已填值之后。

因此新增任何审查工具只需要注册本地数据，不需要修改本文件或 Python 代码。

## Headless invocation

统一调用模型：

```text
<runtime.executable> <runtime.review.args...> "<审查请求>"
```

命令名、参数、路径、模型选择都来自 registry / 当前会话事实。中央不保存某个产品的具体 CLI 示例作为逻辑依赖。

本地 runtime 结构示例：

```json
{
  "runtimes": {
    "<runtime-id>": {
      "command_candidates": ["<command>"],
      "executable": "<resolved executable>",
      "capabilities": ["agent", "review"],
      "review": {
        "args": ["<headless-arg>"],
        "priority": 80
      }
    }
  }
}
```

成功/失败状态写入 `.local/state.json`：

```json
{
  "cross_review": {
    "runtimes": {
      "<runtime-id>": {
        "headless_verified": true,
        "last_result": "ok"
      }
    }
  }
}
```

缓存不得包含登录 token、cookie、密钥正文。

### 新增审查运行时

使用通用 registry CLI；下面只是字段结构示例，不代表某个固定产品：

```text
python tools/runtime_state.py runtime add <runtime-id> \
  --commands-json '["<command>"]' \
  --capabilities-json '["agent","review"]' \
  --review-args-json '["<headless-arg>"]' \
  --review-priority 70
```

注册后会自动 detect；也可单独运行：

```text
python tools/runtime_state.py runtime detect <runtime-id> --refresh
```

## 权限与 workspace

headless 运行时常见前置条件包括：

- 目标仓库必须在该运行时允许读取的 workspace 范围内。
- 需要 `git diff`、测试命令等时，可能需要细粒度 command 权限。
- 某些运行时的 plan/headless 权限可能根本不能读文件。

这些都属于**机器配置**：权限文件路径、allowed root、trustedWorkspaces 当前值等写进本地 runtime/state，中央只保留规则。

**修改任何运行时权限配置都意味着扩大 AI 的访问面，必须先取得用户确认。** 不要为了审查方便启用类似“跳过所有权限检查”的高危参数。

审查方无输出 / 调用失败时，不能当成通过：

1. 检查 registry/state 缓存是否过期。
2. 对该 runtime 做最小 discovery：executable、workspace、读文件权限、必要命令权限。
3. 成功后刷新本地缓存；仍失败则顺延下一个 registry 候选或如实报告。

## 审查请求格式

请求至少包含：

1. **改动范围**：文件列表或 `git diff`；大改动按模块分批。
   - 给外部运行时的文件路径应在发起时解析成**当前机器真实绝对路径**，避免另一个运行时 cwd 不一致。
   - 这里的“绝对路径”是运行时生成的数据，不得预写某个用户名/home 到中央文档。
2. **背景**：一句话说明需求/工单/这次改了什么。
3. **审查清单**：正确性与边界条件；并发与失败路径；安全；现有架构一致性；资源生命周期。
4. **输出要求**：每条问题给 `file:line` + 问题 + 严重度（blocker / major / minor）+ 具体建议；结尾给“通过 / 修 minor 后可过 / 需返工”。
5. **禁令**：只审给定范围；无法确认标 unknown；不得把纯风格偏好标 blocker；用户没要求时不要直接改代码。

## 收反馈（实现方）

- 按 `receiving-code-review` skill：逐条核实，不盲从。
- blocker / major 修复并复验。
- minor 可解释后保留，但写进交付汇报。
- 审查结论是输入，不替代实现方自己的验证。

## 验证交接

静态读码无法确认、必须实际运行才能验证的项，生成一段可直接交给验证运行时的自包含提示词。至少包含：

- 当前仓库**实际绝对路径**、分支/commit、文件范围。
- 需求背景和上一轮审查修了什么。
- 启动命令、精确入口、必要权限、前置状态构造方法。
- happy path 之外的破坏性/边界场景：快速连点、中途改值、脏数据、断网/超时、并发等。
- 本轮修复项标为【回归重点】。
- 报告格式：现象、复现步骤、期望 vs 实际、严重度、涉及文件；结尾三档结论。
- 验证者只收集事实，不改代码、不编结果。

机器相关的验证入口、测试账号 locator、项目绝对路径等只出现在**本次生成的提示词或 `.local/`**，不回写中央文档。

## Guardrails

- 不维护快速过期的模型名/版本列表。
- 不维护固定运行时名单、固定优先级或固定 CLI invocation。
- runtime 第一次跑通后缓存，后续直接复用；失败才重新 discovery。
- 不为了审查方便扩大运行时权限。
- 审查方不得递归再派审查。
