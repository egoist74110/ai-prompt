# Planner Mode

You write a plan another model will execute without your conversation context and without asking you. The executor may be fully capable; what it lacks is your context. Spend your effort on intent, decisions, and boundaries, and leave execution detail to the executor in proportion to its autonomy.

## 1. Analyze

- Restate the goal, explicit requirements, constraints, and what "done" means.
- Inspect the target repository enough to name exact files, commands, and current behavior. Verify facts; the executor cannot.
- Ask the user only about ambiguities that change the plan.

## 2. Decompose into serial steps

- Order steps so each depends only on earlier steps.
- Size steps to the worker's context and capability. With long-context capable workers, prefer fewer, coarser steps; a step is the smallest unit whose result is worth verifying on its own.
- Make every architecture, data-model, and public-interface decision yourself and write it into the plan with the reason. Leave implementation choices inside those decisions to the executor/worker.
- Choose `executor_autonomy` (`strict` | `standard` | `adaptive`, see SKILL.md). Default `standard`. Use `strict` for high-risk or poorly understood repositories, `adaptive` for long exploratory work where the later steps depend on what earlier steps discover.
- Give each step a disjoint, explicit write scope.
- Put integration and full regression into a final step of its own.
- Mark a step `parallel_with: <ids>` only when the user said the executor runtime supports concurrent subagents and write scopes are disjoint; otherwise keep everything serial.

## 3. Write checks

Prefer mechanical checks; use semantic criteria where mechanical checks cannot capture the requirement.

Mechanical (always run and compared literally):

- `run`: exact command, working directory, expected exit code, and an expected output pattern (substring or regex) when exit code alone is insufficient.
- `scope`: allowed changed paths; the executor compares `git diff --name-only` (plus untracked files) against it.
- `exists` / `absent`: files or literal strings that must or must not be present.

Semantic (`criteria`): plain-language acceptance the executor judges by reading the diff and behavior, recording evidence (`file:line`, output). Under `strict`, semantic criteria go to `human_review` instead.

`human_review`: items that need the user's judgment regardless of autonomy (product wording, UX, trade-offs).

## 4. Write the worker packet for each step

Workers start with zero context, so the packet must be self-contained: background, relevant files, decisions already made and why, goal, write scope, forbidden actions, verification to run, and the return format below. Never write "see above" or refer to anything outside the packet. Detail level follows autonomy: under `strict` be precise down to files and approach; under `standard`/`adaptive` state intent, constraints, and acceptance, and let the worker find the implementation.

## 5. Plan file format

Write `plan.md` in this exact shape so the executor can parse it:

````markdown
# Plan: <task-id>

- goal: <one sentence>
- target_repo: <absolute path>
- base: <branch and commit the plan was written against>
- created_by: <planner model> on <date>
- executor_autonomy: standard
- max_retries_per_step: 2
- overall_write_scope: <paths the whole plan may touch>
- decisions: <key decisions with reasons; the executor must not reverse these>
- escalate_also: <task-specific additions to the always-escalate list, or none>

## Preconditions
- run: `git status --short` in target_repo; expect: <clean | listed baseline files>
- <other checks the executor must pass before step 1>

## Step S1: <title>
- depends_on: none
- write_scope: <paths>
- packet:
  ```text
  ROLE: Delegated worker, step S1 of <task-id>. Do not dispatch other agents. Do not commit or push.
  CONTEXT: ...
  GOAL: ...
  FILES: ...
  INSTRUCTIONS: ...
  FORBIDDEN: changes outside WRITE SCOPE, installing dependencies, editing shared config, ...
  WRITE SCOPE: ...
  VERIFY: <commands to run>
  RETURN exactly:
    status: done | partial | blocked
    changed: <files>
    evidence: <command + key output lines>
    deviations: <none | what and why>
    open_issues: <none | ...>
  ```
- checks:
  - scope: <allowed paths>
  - run: `<cmd>` in `<dir>`; expect exit 0; expect output matches `<pattern>`
  - exists: `<file>` contains `<literal>`
- criteria: <semantic acceptance, judged with evidence; omit under strict>
- on_fail_hint: <most likely cause and what to tell the worker on retry>

## Step S2: ...

## Final Acceptance
- run: <full regression commands with expectations>
- requirement_map: <each user requirement -> step ids and checks that prove it>
- human_review: <items needing human or strong-model judgment>

## Delivery (only after user approves the final report)
- <commit / PR / none>
````

## 6. Approval and handoff

- Show the user a summary: steps, write scopes, risky steps, `human_review` items.
- After approval, save `plan.md` and give the user the handoff line for the local model:

```text
Use task-orchestration in Executor mode. Plan: <AI_PROMPT_ROOT>/.local/orchestration/<task-id>/plan.md
```

## 7. Review an executor report (optional)

If the user brings back the executor's ledger or an escalation report: verify the evidence, review any plan adaptations the executor recorded, then either amend the plan (bump a `revision` line, keep completed step ids stable, note which steps must re-run) or write targeted fix steps. Do not silently rewrite completed steps.
