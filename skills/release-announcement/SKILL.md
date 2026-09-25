---
name: release-announcement
description: "Draft the customer-facing back-office version-update announcement (customer release-notes template) from real work items and verified project code. Hard gates: refuses without a work-item number, and refuses (asks the user) until the project repository is unambiguous. Use when the user asks, in any language, to write release notes, update notes, a version-update announcement, or a back-office announcement for a release; also supports the customer-service variant."
---

# release-announcement — Customer Version-Update Announcement

Produce the text of a back-office announcement (category: version update) that tenants read. Output is customer language, grounded in work items and verified against the code that actually shipped.

This Skill only drafts text. It never publishes an announcement, edits a work item, or changes code.

Resolve files relative to this Skill directory:

- `templates/customer.md` — customer version layout + reference example (Chinese output).
- `templates/customer-service.md` — extra sections for the customer-service variant.

## 0. Hard gates (check before any other work)

Run both gates first. If either fails, stop and reply to the user; draft nothing, not even a placeholder.

### Gate 1 — Work-item number

- Require at least one explicit work-item number from the user's message, or from the current branch name / commit messages when the user points to them.
- If no number is available: **refuse**. Tell the user a work-item number is required and ask for it.
- NEVER invent, guess, or search for a "likely" work item.

### Gate 2 — Project repository

- The target project (repository path) must be unambiguous: the user named it, or the current working directory is clearly that product's repository.
- If the cwd is not a code repository of that product, several candidate repos exist, or the work item does not match the cwd project: **refuse and ask the user** which project/path to use.
- NEVER assume a repo from memory or from a similarly named directory.

Only when both gates pass, continue.

## 1. Read the work items

- Use the `ado-pr` Skill (self-hosted Azure DevOps) to read each work item: title, description, acceptance criteria, state, and comments.
- If a work item cannot be read (404, permission, network), stop and report it. Do not write from the title alone unless the user explicitly accepts that.
- Surface work items that are not resolved/closed; do not silently include unfinished work.

## 2. Verify against project code

For every candidate bullet, search the confirmed repository to confirm it shipped and to learn the real UI wording:

1. Locate the change: branch / commits / merged PR linked to the work item (`git log --grep=<id>`, branch names, PR links), then the touched files.
2. Confirm the behavior exists in code (component, route, handler, enum/type such as a new cash-record type).
3. Resolve customer-visible names from UI source, not code identifiers: menu/route config, i18n/locale strings, page titles, tab labels, button text.
4. Build each affected-page path from the real menu hierarchy (`Level1 > Level2 > Page/Tab`).

Rules:

- Work item describes something the code does not implement → drop it; list it as "Unverified" in the reply.
- Code contains a customer-visible change the work item does not mention → list it as "Found in code, not in work item"; let the user decide.
- Never describe behavior seen in neither the work item nor the code.

## 3. Version and release time

- Version format: `vYYYY.MM.DD.N` (release date + same-day sequence starting at 1).
- Take the version from the user, a release tag, or the release branch. If none exists, ask; do not invent one.
- Release time comes from the user or the release plan. If unknown, use the "pending" placeholder from the template and say so.

## 4. Output format

Follow `templates/customer.md` exactly. The announcement body is always Simplified Chinese, whatever the conversation language.

Section rules:

- Fixed order: New → Improved → Fixed → Action required → Affected pages.
- Omit New / Improved / Fixed when empty; never write a "none" bullet.
- Include Action required only when tenants must act (configure, re-login, notify players, etc.).
- Affected pages is always present: one path per line, deduplicated, ordered by menu.
- Recipient (all tenants / specified tenants) is metadata, not body text; report it separately when known.

## 5. Writing rules

- Write for tenants, not developers. No field names, API paths, table names, class names, flags, work-item numbers, or internal team terms.
- One bullet = one customer-visible change: what changed + what the customer gains. One sentence, ending with a Chinese full stop.
- Quote UI names exactly as the product shows them, wrapped in Chinese corner brackets (tabs, columns, buttons, types).
- Classify honestly: new capability → New; better existing behavior → Improved; wrong behavior corrected → Fixed.
- Merge work items that describe one customer-visible change into a single bullet.
- Exclude purely internal changes (refactors, logging, infra, tests) unless tenants can perceive them.
- No marketing superlatives, no promises about future work.
- Match the tone and granularity of the reference example in `templates/customer.md`.

## 6. Customer-service variant

Only when the user asks for the customer-service version: output the customer version unchanged, then append the sections in `templates/customer-service.md` (likely tenant questions with answers; known issues with workarounds).

Derive both sections only from work-item comments, acceptance notes, and code limits actually seen.

## 7. Reply to the user

Return, in this order:

1. The announcement text in one code block, ready to paste.
2. Recipient, if known.
3. Sources: work-item IDs read; repository, commits, and files used for verification.
4. Gaps: Unverified items, Found in code but not in work item, missing version/time, unfinished work items.

Do not claim an item is verified unless it was confirmed in code.
