# Cross-Review

Cross-review requires an execution identity different from the implementer. Runtime registry ids are aliases/configuration keys and are not sufficient proof of isolation.

## Identity and Recursion

- **Implementer:** current phase changes code/configuration and delivers it; dispatch rules may apply.
- **Reviewer/verifier:** current phase explicitly requests review/verification without implementation; finish that review and stop.
- A reviewer MUST NEVER dispatch another cross-review. Implementer self-review is not cross-review.

## Trigger

1. User explicitly requests cross-review/review of an implementation -> dispatch after self-review without asking again.
2. Otherwise, for security, critical data flow, multi-step writes/transactions, cross-module refactoring, production readiness, or unresolved high-impact uncertainty -> recommend one reviewer/scope/reason and wait for confirmation.
3. Non-interactive headless execution without prior authorization -> do not consume another runtime's quota; report the pending recommendation.

Trivial fixes and isolated low-risk changes may stop after self-review.

## Reviewer Selection

Candidates come only from `.local/runtime.json.runtimes`. Filter in this order:

1. `enabled != false` and `capabilities` contains `review`.
2. Resolved executable exists (or minimal discovery resolves it) and `review.args` is configured; an empty args array is valid.
3. Candidate `runtime_identity` is present and differs from the implementer's verified `runtime_identity`.
   - Aliases/wrappers of the same underlying reviewer MUST share one `runtime_identity`.
   - Different registry ids with the same identity are the same runtime for isolation purposes.
   - If either identity cannot be verified, do not claim cross-runtime isolation; choose another verified candidate or report that review isolation is unavailable.
4. Prefer locally verified headless candidates, then `review.priority` descending.

`runtime_identity` is local registry data. Starter identities may be seeded from templates, while custom aliases/wrappers must declare the stable identity they represent.

## Invocation

```text
<runtime.executable> <runtime.review.args...> "<review request>"
```

All executable paths, arguments, model selection, permissions, and workspace facts come from current-session/local registry state. Do not hard-code product CLI invocations in central rules.

No output or invocation failure is not a passing review. On failure, minimally verify executable, workspace access, file-read/command permission, and stale cache; then try the next eligible identity or report failure accurately.

Changing runtime permissions expands AI access and requires user confirmation. Never disable permission checks merely to make review work.

## Review Request

Include:

1. change scope (`git diff` or explicit files; split very large changes);
2. one-sentence requirement/context;
3. checklist covering correctness/edge cases, concurrency/failure paths, security, architecture, and resource lifecycle as relevant;
4. output contract: each finding has `file:line`, problem, severity (`blocker`/`major`/`minor`), and recommendation, followed by `pass`, `pass after minor fixes`, or `rework required`;
5. restrictions: review supplied scope only, mark unverifiable claims `unknown`, do not promote style preferences to blockers, and do not modify code unless explicitly requested.

Resolve repository paths for the dispatched runtime from current machine facts. Absolute paths are per-run data, never central constants.

## Receiving Feedback

The implementer MUST load `receiving-code-review` and verify findings individually.

- Fix and re-verify blocker/major findings.
- Minor findings may be retained with justification and disclosed.
- Reviewer conclusions do not replace implementer validation.

For runtime-only verification, create a self-contained request with repository path, branch/commit, scope, prerequisite state, exact start/entrypoint facts, regression focus, destructive/edge scenarios, and expected report format. The verifier collects evidence and does not fabricate results or modify code unless separately authorized.

## Local State

Cache non-secret review facts under `.local/state.json`, including headless verification and last result. Never cache tokens, cookies, credentials, or secret contents.

Use the generic registry CLI to add custom reviewers. Custom aliases that point to the same execution system must use the same `--runtime-identity`.
