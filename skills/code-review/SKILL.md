---
name: code-review
description: General code-review protocol for diffs, commits, PRs, implementations, and closure rounds. Use when acting as a reviewer or when another AI is delegated to review code; produce evidence-backed findings with stable ids and verify prior findings before regressions on later rounds.
---

# Code Review

Review code for correctness and risk, not for performative completeness. Findings must be supported by repository evidence and tied to an observable failure, contract violation, regression, or material maintainability risk.

## Trigger

Use this Skill when:

- the user requests a general code review;
- this runtime is delegated by another AI to review an implementation;
- reviewing a diff, commit, PR, patch, or explicit file scope;
- performing a second or later closure review after fixes.

This Skill defines **how to review code**. Cross-runtime selection, reviewer identity isolation, session/cache continuation, and multi-round orchestration belong to `capabilities/cross-review.md`.

## Scope Contract

Before judging code, establish:

1. the requirement or intended behavior;
2. the exact review boundary: diff, commit range, PR, or explicit files;
3. relevant compatibility/runtime constraints;
4. previous findings and changed boundary when this is a closure round.

Review the supplied scope. Read unchanged callers, callees, schemas, tests, configuration, and adjacent code only when needed to verify the changed behavior or a plausible regression.

Do not invent requirements. Mark materially unverifiable claims as `unknown` rather than converting uncertainty into a finding.

## Review Method

Trace changed behavior from inputs to externally visible outcomes. Prefer concrete execution paths and contracts over local line-by-line style commentary.

Check the dimensions that are relevant to the change:

### Requirement and Behavior

- Does every requested behavior have an implementation path?
- Are success, rejection, validation, and error states consistent with the requirement?
- Did the implementation silently skip a required step because an API, field, permission, dependency, or state is missing?
- Are defaults and fallbacks semantically correct rather than merely convenient?

### Interfaces and Data Contracts

- Do callers and callees agree on types, fields, nullability, units, identifiers, ownership, and error semantics?
- Are API/schema/config migrations backward-compatible where required?
- Can stale, partial, malformed, or unexpected data cross the boundary safely?

### Failure and Edge Paths

- What happens on timeout, cancellation, partial failure, empty input, duplicate input, retry, restart, or unavailable dependency when relevant?
- Are errors propagated, translated, or recovered at the correct layer?
- Does a failure leave durable or in-memory state inconsistent?

### State, Concurrency, and Transactions

- Can concurrent operations race, overwrite, double-apply, or observe intermediate state?
- Are multi-step writes atomic enough for their contract?
- Are idempotency, locking, deduplication, and retry semantics correct where needed?

### Security and Trust Boundaries

- Are authentication, authorization, tenant/user/resource ownership, secret handling, input validation, and injection boundaries preserved?
- Did the change broaden access or trust data that was previously constrained?

Do not substitute this general pass for a dedicated security review when the task explicitly requires one.

### Resource Lifecycle

- Does every opened resource have a correct close/kill/unsubscribe/release path on success, error, cancellation, and early return?
- Are processes, connections, listeners, timers, locks, temporary files, and caches left in a valid lifecycle state?

### Architecture and Regression

- Does the change violate an existing layering, ownership, lifecycle, or dependency contract?
- Did fixing one path break another supported caller, platform, version, or mode?
- Is duplicated or coupled logic likely to diverge in a way that creates a concrete correctness risk?

Architecture preference alone is not a finding without a material consequence.

### Verification and Tests

- Do tests exercise the changed contract and meaningful failure paths?
- Can a test pass while the actual requested behavior is still broken?
- Are mocks hiding integration assumptions that the implementation depends on?

Missing tests are a finding only when they leave a material behavior/regression risk insufficiently protected; do not demand tests mechanically.

## Specialized Skills

Load only matching specialized Skills when their trigger applies. They supplement this general protocol rather than replacing its finding/output contract.

Examples include:

- `backend-security-review` for backend auth/data-access security;
- `data-consistency-review` for multi-step writes and partial failure;
- `production-readiness-review` for production operational readiness;
- `resource-lifecycle-audit` for resource ownership/cleanup;
- `script-engineering` when shell/PowerShell/CMD/WSL scripts are in scope;
- `ui-ux-pro-max` when the requested review includes UI/UX quality.

Do not bulk-load unrelated review Skills.

## Finding Contract

Each actionable finding MUST contain:

- a stable finding id, such as `CR-001`;
- severity: `blocker`, `major`, or `minor`;
- `file:line` or the narrowest available location;
- the violated behavior/contract;
- concrete evidence or execution path;
- user/system impact;
- the smallest directionally correct recommendation.

A finding is not valid merely because code could be cleaner, shorter, more idiomatic, or differently structured.

Severity means:

- **blocker** — unsafe to ship/merge because it can cause severe security, data-loss/corruption, or fundamentally unusable behavior;
- **major** — material correctness/regression/reliability issue that should be fixed before considering the reviewed requirement complete;
- **minor** — real but limited-scope defect or robustness gap that does not invalidate the main implementation.

Do not promote style preferences, speculative future extensibility, or unsupported hypotheticals into findings.

## Closure Review

For round 2 or later in the same review thread:

1. keep the same finding ids for the same defects;
2. verify every previously `fixed` finding against its original failure condition, not merely the edited line;
3. reconsider `rejected` findings using the implementer's evidence;
4. report `deferred`/`blocked` findings with their current status;
5. inspect the new delta for regressions or new issues caused by the fixes;
6. do not reopen a closed finding unless evidence shows it is still broken or has regressed.

A closure review is not a fresh full-repository audit unless the scope explicitly changed.

## Conclusion Contract

Finish with exactly one overall conclusion:

- `pass` — no actionable findings remain in the reviewed scope;
- `pass after minor fixes` — only minor actionable findings remain;
- `rework required` — at least one blocker/major finding remains.

If evidence needed for a conclusion is unavailable, state the specific `unknown` and do not falsely report `pass`.

## Reviewer Discipline

- Review before proposing fixes; do not modify code unless the delegated request explicitly authorizes implementation.
- Prefer a small number of high-confidence findings over a large speculative list.
- Verify repository facts directly when accessible.
- Do not repeat already-closed findings in later rounds unless they regressed.
- Do not dispatch another reviewer when this execution is itself the delegated reviewer; reviewer recursion is governed by `capabilities/cross-review.md`.
