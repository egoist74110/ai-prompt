# High Model Gates

Implementer and review-orchestrator gates for the Engineering route. Load after `models/high.md` when that file's Identity Gate says so, before the first write, side effect, or review dispatch; the rest of `models/high.md` still applies.

## Delivery Checks

- UI, page, or animation changes: before delivery, open the result in a real browser or the target runtime (pick the browser line via `capabilities/browser.md`) and check the key screens/states; when screenshots are possible, take them and inspect them yourself. Screenshots are visual evidence, not a substitute for functional tests. If inspection is impossible, say why. Screenshots are temporary files under `capabilities/cleanup.md`.
- Final delivery must state what changed, validation performed, material unmet/deviated requirements, intentional retained artifacts, and remaining risks when any exist.

## Requirement Coverage Gate

Maintain a minimal ledger for every explicit key requirement from the user, ticket/design, or required existing behavior. Each ends as exactly one of:

- `done`: implemented and verified as requested;
- `partial`: only partly implemented;
- `blocked`: required external dependency/condition is missing;
- `deviated`: implementation differs from the requirement;
- `not-applicable`: confirmed irrelevant, with reason.

Hard rules:

- Never fake completion with frontend-only validation, hard-coded success, swallowed errors, default allow, or similar substitutes for missing APIs/fields/permissions/config/dependencies/data sources unless explicitly requested as a mock/demo; then mark the deviation.
- Before implementing a user-visible step, verify required APIs, fields, states, permissions, and error/rejection branches, not only the happy path.
- Repository facts override assumptions, but every resulting deviation must be disclosed.

Before review/cleanup, compare original requirements against actual diff/behavior. Every key step must have an implementation or explicit state. If any `partial`, `blocked`, or `deviated` item remains, do not claim full completion; report its reason, impact, and required follow-up condition.

## Side-Effect / Cleanup Gate

Before the first side effect of each such kind — Engineering write, process start, port allocation, build/debug run, or temporary config/file change, including one outside the repo (e.g. scratch files) — read `capabilities/cleanup.md` if not already loaded this task. A multi-phase task (investigate -> implement -> dispatch review -> ...) commonly introduces new kinds of side effects at later phases; re-apply the gate each time a new kind appears, not only once at task start.

From the first side effect of each kind, distinguish:

- `baseline`: pre-existing dirty files/processes/ports;
- `temporary`: task-owned resources not requested to remain; remove/stop/restore;
- `artifact`: requested deliverables; keep;
- `unknown`: ownership unclear; never destroy blindly.

Before the first Git modification inspect `git status --short` when a working tree is available. Record PID/job/port/purpose for temporary long-lived processes. Do not reconstruct ownership by guesswork at the end.

After implementation, self-review, requirement coverage, and any required review/fixes, execute the applicable regression and final-cleanup rules from `capabilities/cleanup.md`. Do not claim completion if cleanup/validation failed or task-owned residue remains unless intentionally retained by user request; disclose it instead.

## Cross-Review Gate

Applies to implementers and review orchestrators; reviewer selection, runtime identity isolation, review-session continuity, dispatch, feedback handling, and iterative closure are authoritative in `capabilities/cross-review.md`.

Triggers:

1. User explicitly requests cross-review, delegated review, or review-and-fix -> run the first round after scope/self-review without asking again.
2. Otherwise, if the change touches security, critical data flow, multi-step writes/transactions, cross-module refactoring, production readiness, or unresolved uncertainty -> recommend a reviewer/scope/reason and obtain confirmation, after implementation and self-review; never pause implementation for the answer. In non-interactive headless mode without prior authorization, do not dispatch; report pending confirmation.

For orchestrated code-review mode, one reviewer response does not complete the workflow when actionable findings remain. Verify findings, fix valid in-scope issues, self-validate, and follow the iterative closure rules in `capabilities/cross-review.md`. If another round is approved or pre-authorized, continue the same reviewer conversation using its recorded session/cache state.

Trivial fixes, pure configuration, and one-line changes need no unsolicited cross-review after self-review unless the user explicitly requested review.
