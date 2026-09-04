---
name: anysearch
description: Real-time web/domain search and URL extraction. Use the portable cached launcher; runtime selection is discovered once per machine and stored in .local instead of re-reading per-skill runtime.conf every activation.
version: 3.0.0
credentials:
  - name: ANYSEARCH_API_KEY
    required: false
    description: "Optional API key for higher rate limits; anonymous access is supported."
    storage: "Environment or skill-local .env (gitignored). Never copy the key into .local runtime/state."
---

# AnySearch

Unified search service for normal web search, batch search, vertical/domain search and URL extraction.

## Project-wide priority

Before activating this Skill, follow `capabilities/search.md`:

1. current session native search/tool if already available;
2. local verified search backend/cache;
3. discovery only when needed.

Do not force AnySearch over a better current-session native search tool.

## Portable entrypoint

Use:

```text
python <skill_dir>/scripts/run_anysearch.py <command> [options]
```

The wrapper checks `.local/runtime.json -> skills.anysearch.launcher` first. If absent/stale it discovers once:

1. current Python + `requests`;
2. Node.js;
3. PowerShell on Windows;
4. bash/sh on Unix-like systems.

The successful launcher is cached. `runtime.conf` from older installs is treated only as a legacy artifact; the new source of machine truth is top-level `.local/runtime.json`.

A successful call also records verified status in `.local/state.json`. Service/query failures must not automatically trigger a full runtime rediscovery; invalidate the launcher only when the launcher/runtime itself is broken.

## Commands

Search:

```text
python <skill_dir>/scripts/run_anysearch.py search "query" --max_results 5
```

Batch:

```text
python <skill_dir>/scripts/run_anysearch.py batch_search --queries '[{"query":"q1","max_results":5},{"query":"q2","max_results":5}]'
```

Extract page content:

```text
python <skill_dir>/scripts/run_anysearch.py extract "https://example.com/page"
```

List vertical domains:

```text
python <skill_dir>/scripts/run_anysearch.py list_domains
```

Run `doc` only when the CLI/schema is actually unknown, changed, or recovery is needed. Do not read full docs every activation.

## Vertical-domain rule

When the query clearly maps to a supported structured domain and the correct `sub_domain/query_format` is not already known from the current task, call `list_domains` first. Do not repeatedly call it within the same task after the relevant schema is known.

## API key

Priority remains whatever the bundled CLI supports (explicit flag/environment/skill `.env`/anonymous). The key itself is a secret and **must not be written into `.local`**.

If the service returns an auto-registered replacement key:

1. do not silently persist it;
2. ask the user before saving secret material;
3. if approved, save to an ignored secret store such as the skill `.env` or another user-selected secure location;
4. retry the failed request.

The local cache may remember only the credential **locator/type**, never the key body.

## Search discipline

- one factual intent per query where practical;
- technical/version/API questions prefer official sources;
- weak/SEO-heavy results should be retried with quoted terms, `site:`, repo/vendor names, or another backend;
- a successful HTTP request is not proof that results are high quality;
- do not send passwords, private source code, internal work items, secrets or other sensitive material to external search providers without explicit reason/authorization.

## Fallback

If AnySearch is unavailable because of quota/service/network failure, use the project search strategy and another already-available backend. Do not make the user approve every normal fallback when the user simply asked to search; approval is required for installing/configuring new capabilities or persisting secrets, not for using an already-available search path.

## Guardrails

- launcher/path/runtime facts go to `.local/runtime.json`;
- verified success/failure goes to `.local/state.json`;
- API key stays out of both;
- cached launcher failure → re-discover and refresh cache, not add an OS-specific path to this SKILL;
- never assume cwd; all bundled script paths are relative to `<skill_dir>`.
