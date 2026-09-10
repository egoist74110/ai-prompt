---
name: ado-pr
description: "Unified interface for self-hosted Azure DevOps Server (*.cg1alias.com, not dev.azure.com): read work items, read/list PRs, create PRs, and link work items. Use for work-item/PR/create-publish/merge-to-main-or-master intent. Reuse verified local strategy first; discover credentials, execution side, and API paths only on first use or stale cache."
---

# ado-pr — Azure DevOps Server Operations

Use locally available PAT/CLI/REST access to operate self-hosted Azure DevOps Server without requiring an additional ADO MCP service.

## 0. Reuse verified machine state

Resolve repository-relative paths from the directory containing `router.md`.

Check `.local/runtime.json` / `.local/state.json` first, especially:

- `state.skills.ado-pr.strategy`
- `runtime.credentials.ado_pat`
- `state.skills.ado-pr.request_executor`
- `state.skills.ado-pr.network`
- `state.skills.ado-pr.api`

If still valid, use cached state directly. Do NOT rescan keychains, WSL, config directories, CLIs, or network paths.

Rediscover only when the skill has never run on this machine, a cached locator is stale, or execution fails for a reason that indicates environment change. Cache verified non-secret machine facts afterward. NEVER cache PAT contents.

## 1. Refresh task-specific repository facts

Do not persist these across tasks:

1. `git remote -v` → host/organization/project/repository.
2. `git branch --show-current` → source branch.
3. `git ls-remote --heads origin` → prefer `main`, fall back to `master`.
4. Before writes: `git status` + `git push --dry-run origin <branch>`.
5. Resolve work-item ID from user input, branch, or commit message. Ask if absent; NEVER invent it.

## 2. Strategy discovery

Run only on first use or stale cache.

### macOS candidate: `az-cli`

Probe `security`, `az`, and the existing user configuration that maps the current host to a library id. Known credential locator shape:

- keyring service: `my-own-script`
- account: `azuredevops_pat:<library-id>`

Do not print the PAT:

```bash
security find-generic-password -s "my-own-script" -a "azuredevops_pat:<library-id>" -w \
  | az devops login --organization "<organization>"
```

Cache the locator, not the token, and cache `strategy=az-cli`.

### Windows / WSL candidate: `windows-rest`

Never assume distro name, token path, Windows username, or network topology.

On first discovery:

1. Prefer an existing explicit credential locator; do not scan the whole machine.
2. If the locator is in WSL, cache the actual distro and accessible Windows UNC/Linux locators locally.
3. Test target ADO reachability from the current execution side. If WSL fails but Windows works, cache `request_executor=powershell` and stop retrying WSL.
4. Verify PAT/API with a minimal read-only REST request.

Cache machine facts such as strategy, request executor, and reachability in `.local`; store the credential locator under `runtime.credentials.ado_pat`.

## 3. Portable service behavior

- This is Azure DevOps Server; do not assume `dev.azure.com` cloud behavior.
- Comments use `api-version=4.1-preview`.
- Comments response field is `comments`, not `value`.
- Treat JSON as UTF-8.
- `Code` and `Work Items` PAT scopes are independent. On read/write mismatch, inspect the relevant scope first.
- Do not generalize permissive single-work-item project routing to list/query endpoints.

If another server instance behaves differently, record the host-specific fact locally instead of promoting it to a global rule.

## 4. Read work items

`az-cli`:

```bash
az boards work-item show --id <work-item-id> --organization "<organization>" -o json
az devops invoke --area wit --resource comments --route-parameters project="<project>" workItemId=<work-item-id> --organization "<organization>" --api-version 4.1-preview -o json
```

For `windows-rest`, resolve the cached PAT without printing it and send requests through the cached executor. If PowerShell console encoding corrupts non-ASCII output, preserve raw UTF-8 response bytes and read them with a UTF-8-capable tool; do not misdiagnose server encoding.

## 5. Read/list PRs

```bash
az repos pr list --organization "<organization>" --project "<project>" --repository "<repository>" -o json
az repos pr show --id <pr-id> --organization "<organization>" -o json
```

For REST, reuse a verified cached endpoint/version. Probe once only if absent, then cache under `state.skills.ado-pr.api`.

## 6. Create PR

```bash
az repos pr create \
  --organization "<organization>" \
  --project "<project>" \
  --repository "<repository>" \
  --source-branch "<source-branch>" \
  --target-branch "<target-branch>" \
  --title "<title>" \
  --description "<description>" \
  --work-items <workitem-id> \
  --auto-complete false \
  -o json
```

REST follows the same cache-first rule. Generate PR description from the real diff. Preserve the repository/team's required PR language/format when known. Use `--work-items` for hard linkage and include `AB#<id>` in the body when appropriate for readable auto-linking.

## 7. Cache boundaries

`.local/runtime.json`: PAT locator, machine path mappings, CLI/executable locators, fixed external-program locations.

`.local/state.json`: verified strategy, request executor, network reachability, REST endpoint/version, verified MCP/CLI state.

Never cache secret contents or task-only branch/work-item/PR IDs.

Never write machine usernames/home paths, WSL distro names, token absolute paths, or machine-specific VPN/routing conclusions into this SKILL.

## 8. Completion

- Perform only requested writes.
- Report PR number/link, linked work item, and source → target.
- If new machine facts were successfully discovered, ensure they were cached in `.local/` for reuse.
