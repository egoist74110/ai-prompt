# Cross-Review

The implementer and reviewer **MUST NOT be the same runtime**. This file contains only cross-machine workflow rules. Available runtimes, commands, permissions, trusted workspaces, and headless capability are local runtime/state facts and must not be hard-coded here.

## Identity and Recursion Termination

- **Implementer:** the current request requires writing/modifying code and delivering it -> this file's dispatch workflow applies.
- **Reviewer / verifier:** the current request explicitly limits the runtime to read-only review/opinions and forbids code changes -> finish the review and stop.

**A reviewer MUST NEVER dispatch another cross-review.** Re-evaluate identity by the current phase. An implementer rereading its own work is self-review, not cross-runtime review.

## When to Use

1. The user explicitly requests review/cross-review -> execute directly without asking again.
2. The user did not request it, but changes touch high-risk areas such as security, critical data flow, cross-module refactoring, production readiness, or unresolved high-model uncertainty -> state which runtime you recommend and what it should review, then wait for confirmation.
3. In non-interactive headless mode without prior authorization -> do not consume another runtime's quota automatically; include the recommendation in output and stop.

Trivial fixes, pure configuration, one-line changes, and isolated logic without external side effects may be delivered after self-review.

## Reviewer Selection: Registry Only

Candidates come only from `.local/runtime.json.runtimes`. Central rules maintain **no fixed list or order of Claude, Codex, Gemini, Qwen Code, or any other CLI**.

Filter candidates as follows:

1. `enabled != false`.
2. `capabilities` contains `review`.
3. Runtime id differs from the current implementer.
4. A resolved `executable` exists, or minimal discovery can resolve one from its own `command_candidates`.
5. `review.args` is configured; it may be an empty array when the CLI needs no additional arguments.
6. Prefer entries where `.local/state.json.cross_review.runtimes.<id>.headless_verified == true`.
7. If multiple candidates remain, sort by `review.priority` descending. Entries without priority follow entries with explicit priority.

Adding a reviewer therefore requires only local registry data, not changes to this file or central Python.

## Headless Invocation

Use the generic form:

```text
<runtime.executable> <runtime.review.args...> "<review request>"
```

Command names, arguments, paths, and model selection come from the registry/current-session facts. Central rules must not depend on product-specific CLI examples.

Example local runtime structure:

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

Write success/failure state to `.local/state.json`:

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

Never cache login tokens, cookies, or secret contents.

### Adding a Review Runtime

Use the generic registry CLI. This illustrates field structure only and does not define a fixed product:

```text
python tools/runtime_state.py runtime add <runtime-id> \
  --commands-json '["<command>"]' \
  --capabilities-json '["agent","review"]' \
  --review-args-json '["<headless-arg>"]' \
  --review-priority 70
```

Registration performs detection automatically. It may also be refreshed explicitly:

```text
python tools/runtime_state.py runtime detect <runtime-id> --refresh
```

## Permissions and Workspace

Common headless prerequisites include:

- The target repository must be inside the runtime's readable workspace.
- `git diff`, tests, and similar operations may require fine-grained command permissions.
- Some plan/headless permission modes may not allow file reads at all.

These are **machine configuration**. Store permission-file paths, allowed roots, trusted-workspace values, etc. in local runtime/state; central rules contain only policy.

**Changing runtime permissions expands AI access and requires user confirmation first.** Never enable dangerous options equivalent to skipping all permission checks merely to make review convenient.

No output or invocation failure is not a passing review:

1. Check whether registry/state cache is stale.
2. Perform minimal discovery for that runtime: executable, workspace access, file-read permission, and required command permissions.
3. Refresh local cache after success. If it still fails, try the next registry candidate or report the failure accurately.

## Review Request Format

A review request must contain at least:

1. **Change scope:** file list or `git diff`; split large changes by module.
   - Resolve paths sent to an external runtime to the **current machine's real absolute paths** at dispatch time so cwd differences do not break review.
   - Absolute paths are generated runtime data. Never pre-write a username/home path into central docs.
2. **Context:** one sentence describing the requirement/ticket/change.
3. **Review checklist:** correctness and edge cases; concurrency and failure paths; security; architectural consistency; resource lifecycle.
4. **Output contract:** each finding must include `file:line`, problem, severity (`blocker` / `major` / `minor`), and concrete recommendation; finish with one of `pass`, `pass after minor fixes`, or `rework required`.
5. **Restrictions:** review only the supplied scope; mark unverifiable claims `unknown`; do not label pure style preferences as blockers; do not modify code unless explicitly requested.

## Receiving Feedback

For the implementer:

- Use the `receiving-code-review` skill to verify findings one by one; never follow feedback blindly.
- Fix and re-verify blocker/major findings.
- Minor findings may be retained with justification, but mention them in delivery.
- Reviewer conclusions are inputs, not substitutes for implementer validation.

## Verification Handoff

For findings that static inspection cannot resolve and that require execution, generate a self-contained prompt for a verification runtime containing at least:

- Current repository **real absolute path**, branch/commit, and file scope.
- Requirement context and what the previous review/fix changed.
- Start command, exact entrypoint, required permissions, and prerequisite-state construction.
- Destructive/edge scenarios beyond the happy path: rapid repeated actions, mid-flow value changes, dirty data, network loss/timeout, concurrency, etc.
- Mark current fixes as `[REGRESSION FOCUS]`.
- Report format: observation, reproduction steps, expected vs actual, severity, affected files; finish with a three-level conclusion.
- The verifier collects facts only; it does not modify code or fabricate results.

Machine-specific verification entrypoints, test-account locators, and absolute project paths belong only in the **generated per-run prompt or `.local/`**, never in central docs.

## Guardrails

- Do not maintain fast-expiring model/version lists.
- Do not maintain fixed runtime lists, fixed priorities, or fixed CLI invocations.
- Cache a runtime after first successful verification; reuse it until failure requires discovery again.
- Never expand runtime permissions merely for review convenience.
- A reviewer must never recursively dispatch another review.
