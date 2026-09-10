---
name: receiving-code-review
description: Use when receiving code review feedback before implementing suggestions; verify each finding against codebase reality and never apply external feedback blindly.
---

# Receiving Code Review

## Core Rule

External review is evidence to verify, not an order to follow.

For each finding:

1. Understand the claimed problem and requested outcome.
2. Verify it against the actual code, requirements, compatibility constraints, and tests.
3. Classify it as valid, invalid, unclear, or unverifiable.
4. Fix valid findings with the smallest correct change and re-verify the affected behavior.
5. Push back on invalid findings with concrete technical evidence.
6. Report unclear/unverifiable findings and what information is missing.

Do not use performative agreement as a substitute for verification.

## Unclear Feedback

Unclear feedback blocks only work that depends on resolving it.

- Ask for clarification when ambiguity can change the correct implementation.
- Continue independent, understood findings when they cannot conflict with the unclear item.
- Pause related items when ordering, shared architecture, or overlapping code makes partial work unsafe.
- Never guess merely to clear a review item.

## External Reviewer Checks

Before implementing a suggestion, check whether it:

- is correct for this codebase and supported versions;
- breaks existing behavior or contradicts explicit requirements;
- misunderstands why the current implementation exists;
- adds unused scope or speculative infrastructure;
- conflicts with a prior user architectural decision.

If runtime evidence is required but unavailable, state that limitation instead of treating the finding as confirmed.

## Priority and Verification

Process blocker/security/correctness findings before minor cleanup. Test fixes at the smallest meaningful scope and check adjacent regression when shared behavior changes.

For blocker/major findings, re-verify the actual failure condition after the fix; changing the cited line is not sufficient evidence.

## GitHub Threads

When replying to an inline GitHub review comment, reply in that existing review thread rather than creating an unrelated top-level PR comment.

## Output

Keep feedback handling technical and concise: finding, verification result, action taken or reason rejected/blocked, and validation evidence.
