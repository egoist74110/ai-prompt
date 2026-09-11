# Cross-Review

Cross-review requires an execution identity different from the implementer. Runtime registry ids are aliases/configuration keys and are not sufficient proof of isolation.

## Roles, Identity, and Recursion

- **Review orchestrator:** the current phase owns a review-and-fix workflow. It may inspect the repository, dispatch one isolated reviewer, validate findings, modify code, and coordinate later review rounds. For the cross-review gate it follows implementer rules.
- **Implementer:** the current phase changes code/configuration and delivers it; dispatch rules may apply.
- **Reviewer/verifier:** the current phase was delegated a bounded review/verification request and must not implement fixes or dispatch another reviewer.
- A reviewer/verifier MUST NEVER dispatch another cross-review. Implementer/orchestrator self-review is not cross-review.
- A user request such as "code review mode", "review and fix", or an explicit request to have another AI review the code is an orchestrated workflow unless the user explicitly requests read-only review/no modification.

## Trigger

1. User explicitly requests cross-review, delegated review, or review-and-fix -> dispatch after the orchestrator/implementer establishes scope and performs any required self-review; do not ask for first-round authorization again.
2. Otherwise, for security, critical data flow, multi-step writes/transactions, cross-module refactoring, production readiness, or unresolved high-impact uncertainty -> recommend one reviewer/scope/reason and wait for confirmation.
3. Non-interactive headless execution without prior authorization -> do not consume another runtime's quota; report the pending recommendation.

Trivial fixes and isolated low-risk changes may stop after self-review unless the user explicitly requested review.

## Reviewer Selection

Candidates come only from `.local/runtime.json.runtimes`. Filter in this order:

1. `enabled != false` and `capabilities` contains `review`.
2. Resolved executable exists (or minimal discovery resolves it) and `review.args` is configured; an empty args array is valid.
3. Candidate `runtime_identity` is present and differs from the orchestrator/implementer's verified `runtime_identity`.
   - Aliases/wrappers of the same underlying reviewer MUST share one `runtime_identity`.
   - Different registry ids with the same identity are the same runtime for isolation purposes.
   - If either identity cannot be verified, do not claim cross-runtime isolation; choose another verified candidate or report that review isolation is unavailable.
4. Prefer locally verified headless candidates, then `review.priority` descending.

`runtime_identity` is local registry data. Starter identities may be seeded from templates, while custom aliases/wrappers must declare the stable identity they represent.

## Review Session and Conversation Continuity

Cross-review is a multi-round conversation, not a sequence of unrelated one-shot calls.

For the first dispatched round, allocate a stable `review_id` and create a local review directory under:

```text
<repo>/.local/reviews/<review_id>/
```

Keep non-secret review artifacts there (for example request/response snapshots, finding ledger, round metadata, and continuation notes). `.local/` is ignored by git and is the default same-repository cache location for the orchestrator's review state.

Also record the session in `.local/state.json -> cross_review.sessions.<review_id>`, including at minimum:

- selected `runtime_id` and verified `runtime_identity`;
- repository/worktree identity and review scope;
- current round number and status;
- last reviewed commit/tree/diff boundary;
- reviewer conclusion and unresolved finding ids;
- reviewer-native `session_ref` when available;
- actual non-secret `cache_locator` or process/session locator when available;
- verified continuation strategy and last successful resume time.

The reviewer runtime may keep its native conversation cache outside the repository. Do not copy opaque runtime caches just to centralize them. Record the verified locator/session reference needed to resume them. Never cache tokens, cookies, credentials, secret prompts, or secret file contents.

On the first round, discover continuation facts only as far as needed. If the runtime exposes a native session/conversation id, resumable cache, cwd-scoped conversation, or persistent process handle, capture it and cache the verified strategy in local runtime/state data. Product-specific resume flags and cache paths are machine/runtime facts, not central constants.

### Continuation Rule

Every second or later review round MUST continue the same reviewer conversation whenever that round belongs to the same review thread.

- Reuse the same `review_id` and reviewer `runtime_identity`.
- Resume the recorded native `session_ref`, cache, or persistent process instead of starting a fresh conversation.
- Tell the reviewer what the orchestrator changed since the previous round, which previous findings were fixed/rejected/deferred, and the new diff/commit boundary.
- Ask the reviewer to verify closure of previous findings first, then inspect regressions/new issues in the changed scope.
- Preserve finding ids across rounds when referring to the same defect.

If the recorded reviewer conversation cannot be resumed, do **not** silently start a fresh reviewer and call it round 2/3. Mark continuity `broken`, preserve the existing review artifacts, explain the failure, and obtain user approval before starting a replacement review session. A replacement session receives a compact prior-round packet but is explicitly a new conversation with a new `review_id`.

## Invocation

First round:

```text
<runtime.executable> <runtime.review.args...> "<review request>"
```

Later rounds use the verified runtime-native continuation strategy from local registry/state facts. Do not invent resume flags. Resolve executable paths, arguments, model selection, permissions, workspace facts, session refs, and cache locators from current-session/local registry state.

No output, an invocation failure, or a failed resume is not a passing review. On failure, minimally verify executable, workspace access, file-read/command permission, session/cache validity, and stale cache; then either resume successfully, try another eligible identity for a **new** review session, or report failure accurately.

Changing runtime permissions expands AI access and requires user confirmation. Never disable permission checks merely to make review work.

## Review Request

Include:

1. change scope (`git diff` or explicit files; split very large changes);
2. one-sentence requirement/context;
3. checklist covering correctness/edge cases, concurrency/failure paths, security, architecture, and resource lifecycle as relevant;
4. output contract: each finding has a stable finding id, `file:line`, problem, severity (`blocker`/`major`/`minor`), and recommendation, followed by `pass`, `pass after minor fixes`, or `rework required`;
5. restrictions: review supplied scope only, mark unverifiable claims `unknown`, do not promote style preferences to blockers, and do not modify code unless explicitly requested;
6. for round 2+, previous finding status plus the exact delta since the prior reviewed boundary.

Resolve repository paths for the dispatched runtime from current machine facts. Absolute paths are per-run data, never central constants.

## Receiving Feedback and Fixing

The orchestrator/implementer MUST load `receiving-code-review` and verify findings individually.

- Track every finding by stable id as `open`, `fixed`, `rejected`, `deferred`, or `blocked`.
- Fix and re-verify valid blocker/major findings.
- Fix valid minor findings when they are safely within the requested scope; otherwise retain them only with a concrete justification and disclose them.
- Rejected findings require evidence/rationale and must be included in the next resumed reviewer turn so the reviewer can confirm or challenge the rejection.
- Reviewer conclusions do not replace orchestrator/implementer validation.
- After fixes, run the smallest sufficient self-validation before offering another review round.

For runtime-only verification, create a self-contained request with repository path, branch/commit, scope, prerequisite state, exact start/entrypoint facts, regression focus, destructive/edge scenarios, and expected report format. The verifier collects evidence and does not fabricate results or modify code unless separately authorized.

## Iterative Closure

A requested code-review workflow does not end after the first reviewer response if actionable findings were produced.

1. Round 1 reviewer returns findings/conclusion.
2. Orchestrator verifies and fixes all valid in-scope findings it can safely fix, records exceptions, and self-validates.
3. If the reviewer returned `pass` with no actionable findings, close the review session and deliver; do not ask for a redundant round.
4. Otherwise, after fixes/triage, explicitly ask whether the user wants round 2 review unless the user already authorized continuous review-to-pass.
5. If approved, resume the **same reviewer conversation** and verify previous findings plus regressions/new issues.
6. Repeat the same rule for round 3 and later. Do not impose an arbitrary three-round maximum.
7. Close only when the resumed reviewer reports no actionable findings, the user declines another round, or further progress is blocked. Record which condition ended the loop.

If the user pre-authorizes "review until clean/pass", the orchestrator may continue rounds without asking after every fix cycle, but MUST stop and surface the issue when a fix requires a material requirement/architecture change, expanded permissions, destructive action, or other decision that needs user authorization.

## Local State

Cache non-secret review facts under `.local/state.json`, including headless verification, review sessions, continuation state, and last result. Store per-review artifacts under `.local/reviews/<review_id>/`. Never cache tokens, cookies, credentials, or secret contents.

Use the generic registry CLI to add custom reviewers. Custom aliases that point to the same execution system must use the same `--runtime-identity`.
