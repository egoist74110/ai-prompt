---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase, informed by domain language and ADRs. Use for architecture improvement, refactoring opportunities, tightly coupled modules, testability, or AI navigability.
---

# Improve Codebase Architecture

Find architectural friction and propose **deepening opportunities**: refactors that put substantial behavior behind smaller, clearer interfaces while improving locality and testability.

## Vocabulary

Use the definitions in [LANGUAGE.md](LANGUAGE.md). Prefer its architecture terms consistently when presenting findings: module, interface, implementation, depth, seam, adapter, leverage, and locality.

Key checks:

- **Deletion test:** if deleting a module merely spreads its complexity across callers, it was providing useful depth; if complexity disappears, it may be pass-through structure.
- **Interface is the test surface.**
- **One adapter is a hypothetical seam; multiple adapters demonstrate a real seam.**

Project domain vocabulary and existing ADRs outrank generic architecture terminology for domain concepts.

## 1. Explore

Read relevant project domain documentation such as `CONTEXT.md` when present, plus ADRs for the area under review.

Use the central scout contract (`models/scout.md`) when delegated exploration is available; otherwise explore directly. Do not depend on a product-specific Agent API or subagent parameter.

Look for concrete friction:

- understanding one concept requires bouncing across many shallow modules;
- interfaces expose nearly as much complexity as their implementations;
- extracted helpers improve unit-testability but hide integration mistakes across callers;
- tightly coupled modules leak knowledge across seams;
- important behavior is difficult to test through its current interface.

Apply the deletion test before recommending consolidation. Collect file/line evidence; do not propose architecture from naming alone.

## 2. Present Candidates

Unless the user requested another format, write a self-contained HTML report to the OS temp directory, not the repository. Resolve the temp directory from platform/runtime facts (`TMPDIR`, `TEMP`, or the platform temp API); never hard-code a Unix-only path. Use a unique timestamped filename.

For each candidate include:

- files/modules involved;
- observed friction and evidence;
- proposed direction in plain language;
- locality/leverage/testability benefit;
- before/after visualization when it materially clarifies structure;
- recommendation strength: `Strong`, `Worth exploring`, or `Speculative`.

End with the strongest candidate and why. Respect existing ADRs; surface a conflicting proposal only when concrete friction justifies reconsidering the decision.

Do not invent final interfaces yet. Ask which candidate the user wants to explore.

See [HTML-REPORT.md](HTML-REPORT.md) for report guidance and [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md) when interface alternatives are requested.

## 3. Design Conversation

For the selected candidate, work through constraints, dependencies, the deepened module, its seam, and surviving tests.

- If a durable domain concept is missing or unclear in `CONTEXT.md`, offer/update the glossary when that file is part of the project's documentation convention.
- If the user rejects a candidate for a durable architectural reason, offer to record an ADR only when that reason would prevent future reviewers from repeating the proposal.
- Use the repository's existing ADR format when present; otherwise follow its surrounding ADR conventions instead of depending on an external Skill file.
- Do not create documentation merely to satisfy this Skill when the repository has no such convention and the user did not request it.
