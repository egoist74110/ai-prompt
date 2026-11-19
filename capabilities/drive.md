# Drive

Default-proceed policy for carrying out a task: code, config, files, or any multi-step work. It decides when to keep going and when to stop and ask. It never widens scope and never removes a gate: external actions, installs, persistent permissions, agent-launch approval, destructive deletes, a role's own scope limits, and a user's "ask me first" stay as written. Where another file only says to ask, offer, or confirm before work, this file sets the timing.

Not for Q&A, explanation, or Think-route advice.

## Start

- State the goal in one line and the 2-3 implicit requirements you infer (e.g. match existing patterns, update tests/docs the change affects, keep current behavior working). Then start; do not wait for a reply.
- If a stop condition below is already visible, ask every such question in one message before or while starting, each with your recommended answer. Begin the parts they do not affect. Do not trickle questions out one at a time.

## Proceed by default

- A reversible, local choice with a conventional answer (naming, file placement, error text, a library the project already uses, how to structure the change): pick the option most consistent with the repository and note it in the report.
- A small missing detail: infer it from repository evidence, not from what is easiest.
- Follow-through the user would expect is part of the task: fix the callers, types, tests, and docs your change breaks.
- Done means the acceptance checks pass: the user's stated criteria plus the tests/build/lint the change touches. A failing check -> diagnose, fix, rerun. Do not hand back after the first failure. Stop retrying when the same approach fails twice with no new information; report what you tried and what you suspect.
- Skill offers in `ask` mode: put the offer in the message where you start, and proceed without the Skill unless it is mandatory for the work.
- Cross-review a change would merit: finish the implementation and self-review first, then recommend it. Never block implementation waiting for that answer.

## Stop and ask only when

1. An external or irreversible action the user did not name (see the external-action rule).
2. A decision changes a public interface, data model, or user-visible behavior, and neither the request nor the repository supports one option over another.
3. The request has two readings that produce different deliverables.
4. A hard gate applies: install/enable a tool, widen persistent permissions, launch a high-tier worker, delete data permanently.

Blocked on one item -> keep working on the rest, and ask with your recommendation.

## Limits

- Proceeding is not license to expand: no opportunistic refactors, features, or files beyond the goal and its follow-through.
- Every assumption you made goes in the report, so the user can reverse it.
