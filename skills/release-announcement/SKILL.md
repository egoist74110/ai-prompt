---
name: release-announcement
description: "Draft the customer-facing back-office version-update announcement (customer release-notes template) from real work items and verified project code. Per-project: works only in repositories registered in the local cache, each with its own cached template. Hard gates: refuses without a work-item number or outside a registered project (asks the user). Use when the user asks, in any language, to write release notes, update notes, a version-update announcement, or a back-office announcement, including a bare request like 'write update notes for work item <id>'; always outputs the fixed announcement template, never free prose. Also supports the customer-service variant."
---

# release-announcement — Customer Version-Update Announcement

Produce the text of a back-office announcement (category: version update) that tenants read. Output is customer language, grounded in work items and verified against the code that actually shipped.

This Skill only drafts text. It never publishes an announcement, edits a work item, or changes code.

## Project registry (local cache)

Templates and project facts are per project and live only in the local cache, never in this Skill. Resolve paths from the directory containing `router.md` (`AI_PROMPT_ROOT`).

Registry: `.local/state.json` → `skills.release-announcement.projects.<project-key>`:

```json
{
  "path": "<absolute repo path on this machine>",
  "match": {"remote_suffix": "/_git/<Repo>", "package_name": "<package.json name>"},
  "templates": {
    "customer": ".local/skills/release-announcement/projects/<project-key>/templates/customer.md",
    "customer_service": ".local/skills/release-announcement/projects/<project-key>/templates/customer-service.md"
  },
  "work_items": "ado-pr",
  "code_sources": {"menus": "...", "ui_text": "...", "behavior": "..."},
  "notes": "project-specific quirks"
}
```

- `templates.customer` defines the announcement layout, placeholders, and reference example. It is the only source of output format.
- `templates.customer_service` is optional; without it, the customer-service variant is unavailable for that project.
- `code_sources` tells where menu names, UI text, and behavior live in that repo.
- Template paths are relative to `AI_PROMPT_ROOT`.

## 0. Hard gates (check before any other work)

Run both gates first. If either fails, stop and reply to the user; draft nothing, not even a placeholder.

### Gate 1 — Work-item number

- Require at least one explicit work-item number from the user's message, or from the current branch name / commit messages when the user points to them.
- If no number is available: **refuse**. Tell the user a work-item number is required and ask for it.
- NEVER invent, guess, or search for a "likely" work item.

### Gate 2 — Registered project

1. Determine the target repo: the path the user named, else the cwd's `git rev-parse --show-toplevel`. If neither is a git repo, or several candidates exist: **refuse and ask the user** which project/path to use.
2. Match that repo against the registry: `path` equals the repo root, or `match.remote_suffix` matches `git remote get-url origin` AND `match.package_name` matches `package.json` name (when present).
3. Exactly one entry must match, and its `templates.customer` file must be readable.
4. No match, several matches, or a missing template: **refuse**. Tell the user this project is not registered and offer registration (section 9). Do not draft with another project's template.
5. If the work item clearly belongs to a different project (e.g. backend-only change): refuse and ask.

NEVER assume a repo from memory or from a similarly named directory.

Only when both gates pass, continue.

## 1. Read the work items

- Use the `ado-pr` Skill (self-hosted Azure DevOps) to read each work item: title, description, acceptance criteria, state, and comments.
- If a work item cannot be read (404, permission, network), stop and report it. Do not write from the title alone unless the user explicitly accepts that.
- Surface work items that are not resolved/closed; do not silently include unfinished work.

## 2. Verify against project code

For every candidate bullet, search the confirmed repository to confirm it shipped and to learn the real UI wording:

Apply the matched entry's `code_sources` and `notes` first.

1. Locate the change: PRs/commits/branches linked to the work item (read via `ado-pr`), then `git log --grep=<id>`, branch names, and work-item title keywords. If nothing can be located, stop and ask the user for the branch/commit.
2. Confirm the behavior exists in code (component, route, handler, enum/constant such as a new record type).
3. Resolve customer-visible names from UI source (`code_sources.menus`, `code_sources.ui_text`), not code identifiers.
4. Build each affected-page path from the real menu hierarchy (`Level1 > Level2 > Page/Tab`); append in-page tab/dialog names when relevant.

Rules:

- Work item describes something the code does not implement → drop it; list it as "Unverified" in the reply.
- Code contains a customer-visible change the work item does not mention → list it as "Found in code, not in work item"; let the user decide.
- Never describe behavior seen in neither the work item nor the code.

## 3. Version and release time

- Version format: `vYYYY.MM.DD.N` (release date + same-day sequence starting at 1).
- Take the version from the user, a release tag, or the release branch. Never invent one.
- Release time comes from the user or the release plan. Never invent it.
- A missing version or release time does NOT block drafting: fill the "pending" placeholders from the project's customer template, still output the full template, and list the missing values under Gaps.

## 4. Output format

Read the project's customer template before drafting and follow it exactly. The announcement body uses the template's language, whatever the conversation language.

- Always output the complete template: header line, version/time line, sections with bullets, affected pages.
- Even a single work item uses the full template. NEVER replace it with a title plus summary paragraphs.
- NEVER put work-item numbers in the announcement title or body.

Section rules:

- Fixed order: New → Improved → Fixed → Action required → Affected pages.
- Omit New / Improved / Fixed when empty; never write a "none" bullet.
- Include Action required only when tenants must act (configure, re-login, notify players, etc.).
- Affected pages is always present: one path per line, deduplicated, ordered by menu.
- Recipient (all tenants / specified tenants) is metadata, not body text; report it separately when known.

## 5. Writing rules

- Write for tenants, not developers. No field names, API paths, table names, class names, flags, work-item numbers, or internal team terms.
- One bullet = one customer-visible change: what changed + what the customer gains. One sentence, punctuated as in the template example.
- Quote UI names exactly as the product shows them, wrapped in the quote marks the template example uses (tabs, columns, buttons, types).
- Classify honestly: new capability → New; better existing behavior → Improved; wrong behavior corrected → Fixed.
- Merge work items that describe one customer-visible change into a single bullet.
- Exclude purely internal changes (refactors, logging, infra, tests) unless tenants can perceive them.
- No marketing superlatives, no promises about future work.
- Match the tone and granularity of the reference example in the project's customer template.

## 6. Customer-service variant

Only when the user asks for the customer-service version: output the customer version unchanged, then append the sections in the project's customer-service template (likely tenant questions with answers; known issues with workarounds).

Derive both sections only from work-item comments, acceptance notes, and code limits actually seen.

## 7. Reply to the user

Return, in this order:

1. The announcement text in one code block, ready to paste.
2. Recipient, if known.
3. Sources: work-item IDs read; repository, commits, and files used for verification.
4. Gaps: Unverified items, Found in code but not in work item, missing version/time, unfinished work items.

Do not claim an item is verified unless it was confirmed in code.

## 8. Pre-send self-check

Before replying, confirm every item; fix the draft if any fails:

- [ ] Both hard gates passed; the reply names the registered project and repository used.
- [ ] Header line and version/time line match the project's customer template (placeholders allowed).
- [ ] Content is bullets under the fixed section headings; no free prose paragraphs.
- [ ] Affected pages present, each path taken from real menu/i18n source.
- [ ] No work-item numbers, code identifiers, or internal terms in the announcement.
- [ ] Sources and Gaps are reported after the code block.

## 9. Registering a project

Only when the user asks, or accepts the offer from Gate 2:

1. Confirm the repo root, `origin` URL, and `package.json` name (if any) with the user.
2. Get the template from the user (text, file, or an approved sample announcement). NEVER derive a template from another project's cache or invent one.
3. Find `code_sources` in that repo (router/menu config, locale files, view directories) and show them to the user for confirmation.
4. Write the template files under `.local/skills/release-announcement/projects/<project-key>/templates/`.
5. Write the registry entry with `tools/local_state.py` `update_kind("state", ...)` (read-modify-write under lock); never hand-edit `state.json`.
6. Do not write templates or project facts into this Skill or any tracked file.
