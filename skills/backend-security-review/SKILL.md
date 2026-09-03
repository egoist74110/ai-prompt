---
name: backend-security-review
description: Per-feature security gate for backend APIs and data access — focus on auth, permissions, token handling, and injection risks on each specific endpoint or operation being implemented.
---

# Backend Security Review

This is a per-feature security checklist for backend endpoints and operations. It is not a full codebase audit (use `security-best-practices` for that). The goal: before any endpoint ships, answer the four security questions for that specific feature.

## Trigger

Before completing any backend endpoint, data mutation, file operation, or external integration. Skip for: read-only config, internal-only utility functions with no user input.

## Four Questions Per Endpoint

For every endpoint or operation being reviewed, answer:

1. **What happens if the request is unauthenticated?**
   Should return 401. Is the auth middleware actually in place? Check route registration, not just middleware declaration.

2. **What happens if a lower-privilege user sends this request?**
   Should return 403. Is the permission check on the resource, not just the route? Can user A access user B's data by changing an ID in the URL or body?

3. **What happens with adversarial input?**
   - String fields: SQL/NoSQL injection, path traversal (`../../etc/passwd`), shell injection if passed to subprocess, XSS if reflected to frontend
   - URLs: SSRF (user-supplied URLs fetched by the server)
   - File uploads: path, MIME type, size limits
   - IDs: are resource IDs validated to belong to the requesting user?

4. **Where do secrets and tokens go?**
   - Are API keys, tokens, passwords logged anywhere (request body dump, error messages, debug output)?
   - Are credentials stored in environment variables, not hardcoded?
   - Are user tokens/secrets encrypted at rest, not stored plaintext?

## Per-Risk Checklist

| Risk | Mitigated? | How |
|---|---|---|
| Unauthenticated access | | |
| Horizontal privilege escalation (IDOR) | | |
| SQL / NoSQL injection | | |
| Path traversal | | |
| Command injection | | |
| SSRF | | |
| Sensitive data in logs | | |
| Hardcoded secrets | | |
| Missing input size limits | | |

## Common Vibe-Coding Mistakes

- Auth check on the router level but not the service level — passes route guard but data fetched without user scoping
- `user_id` taken from request body instead of auth token — any user can impersonate another
- `str(user_input)` passed directly to `subprocess.run(shell=True)` — command injection
- `open(user_supplied_path)` without sanitization — path traversal
- Logging `request.body` or full headers — leaks tokens and passwords
- `requests.get(user_supplied_url)` — SSRF

## Completion Gate

Before merging:
- All four questions answered for each modified endpoint.
- No unchecked inputs reach DB queries, file paths, shell commands, or outbound HTTP calls.
- No secrets or user tokens appear in log output.
