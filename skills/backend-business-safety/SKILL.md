---
name: backend-business-safety
description: Use when designing or changing backend business logic with jobs, workers, publish/deploy/sync/import/export flows, cancellation, retry, timeout, locks, registries, caches, external APIs, or long-running stateful tasks. Focuses on lifecycle invariants, cleanup, idempotency, and failure paths before implementation.
---

# Backend Business Safety

Use this skill before implementing or modifying backend business flows where state can outlive a request.

## Trigger

Use for backend logic involving any of these:
- worker, job, queue, scheduler, background thread, async task
- publish, deploy, sync, import, export, batch operation
- stop, cancel, retry, timeout, rollback, resume
- registry, lock, cache, session, connection, file handle, temp resource
- external API calls, ADO/Jira/GitHub integration, webhooks
- user can click the same action repeatedly or issue stop while work is in progress

Do not use for simple pure functions, small UI changes, static config edits, or throwaway scripts unless they manage long-lived state.

## Required Pre-Code Checklist

Before writing code, produce a short safety plan:

1. State model
   - List all states and terminal states.
   - Identify who owns each state transition.

2. Lifecycle invariant
   - Define what must always be true before, during, and after the operation.
   - Example: every registered task must be removed exactly once on success, failure, cancellation, timeout, or unexpected exception.

3. Termination paths
   - Cover success, validation failure, external API failure, cancellation, timeout, exception, process restart, and duplicate request.
   - For each path, state what is emitted to the user and what cleanup runs.

4. Cleanup ownership
   - Prefer `try/finally`, context managers, or a single lifecycle wrapper.
   - Avoid scattered manual cleanup in individual branches.
   - Every early `return`, `raise`, and cancellation branch must pass through cleanup.

5. Concurrency and idempotency
   - What happens on double-click, repeated publish, repeated stop, stale task id, and worker already exited?
   - Is the operation idempotent? If not, what prevents duplicate side effects?

6. Observability
   - Log task id, operation type, state transition, external call boundary, cancellation reason, and cleanup result.
   - Do not log secrets or full tokens.

7. Tests
   - Add or update tests for at least one happy path and the risky non-happy path.
   - For lifecycle code, include cancellation or exception cleanup tests.

## Implementation Rules

- Implement lifecycle cleanup in one obvious owner.
- Prefer `with task_registry.running(task_id): ...` or equivalent over manual register/pop pairs.
- If cancellation is cooperative, ensure the worker reports a terminal outcome and cleanup still runs.
- Treat "already stopped", "not found", and stale ids as terminal, user-safe outcomes.
- Never leave a registry, lock, or in-memory task marker depending on a UI event to clean itself.

## Completion Gate

Before claiming completion:
- Show the lifecycle invariant and how the code enforces it.
- Run the relevant verification.
- If verification cannot run, state the exact missing condition and residual risk.
