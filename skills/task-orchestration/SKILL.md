---
name: task-orchestration
description: "Split a large task into plan and execution: planner mode writes a self-contained step plan with acceptance checks; executor mode runs each step in an isolated subagent with a resumable ledger and escalations. Use to plan big tasks for later/local runs or to run a plan file."
---

# Task Orchestration

Two roles, usually run by different models:

- **Planner** - usually an online model. Owns the goal, decomposition, key decisions, and boundaries. Does not execute steps.
- **Executor** - usually a local model acting as the parent agent. Dispatches each step to an isolated subagent, verifies results, and handles execution-level problems itself within the autonomy the plan grants.

Do not assume the executor is weaker. The split usually exists to save online quota and use the local model's long context, so the plan sets an explicit `executor_autonomy` level instead of hard-coding distrust.

The plan file is the only contract between them. It must carry everything the executor cannot rediscover from the repository: the user's intent, decisions already made and why, and the boundaries.

## Pick the Mode

- The user asks to plan, decompose, or prepare a task for execution -> **Planner**: read `references/planner.md` (relative to this Skill directory).
- The user gives a plan file/task id to run or resume -> **Executor**: read `references/executor.md` only. Do not read the planner reference; it wastes executor context.
- Unclear -> ask which role.

## Plan Location

Default: `<AI_PROMPT_ROOT>/.local/orchestration/<task-id>/` where `AI_PROMPT_ROOT` is the directory containing `router.md` (git-ignored, machine-local).

- `plan.md` - written by the planner; the executor never edits it.
- `ledger.md` - written by the executor; progress, evidence, and stop reasons.

The plan records the absolute target repository path, so it works from any working directory. Never put secrets in either file.

## Shared Rules

- Steps run serially in plan order unless the plan explicitly marks a step `parallel_with`.
- Autonomy levels (set in the plan, default `standard`):
  - `strict` - follow packets verbatim; pass/fail only by the plan's checks; stop on any failure after retries.
  - `standard` - may adapt packets to facts discovered in the repository, judge semantic acceptance criteria with evidence, retry with a different approach inside the step's goal and write scope, and fix small integration glue. Must escalate anything in the escalation list below.
  - `adaptive` - additionally may split, merge, or reorder remaining steps and add steps inside the plan's goal and overall write scope, recording every change in the ledger.
- Always escalate (stop and report), at any level: changing the goal or a requirement, expanding the plan's overall write scope, an architecture/data-model/public-interface decision not made in the plan, adding or upgrading dependencies, destructive or irreversible operations, security-sensitive changes not covered by the plan, and any conflict between the plan and repository reality that changes the approach.
- Workers never dispatch further agents; they do not commit, push, publish, or deploy.
- Nothing is committed, pushed, merged, published, or deployed until the user approves the final report, unless the plan lists that step and the user approved the plan with it.
- A worker's "done" is a claim. Only the plan's checks decide pass/fail.
