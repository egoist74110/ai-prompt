---
name: cdn-asset-ops
description: Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
credentials:
  - name: MinIO AccessKey / SecretKey
    required: true
    description: "S3 credentials used only for mc alias configuration. Never echo or store them in ai-prompt local state."
    storage: "Managed by mc machine-local configuration; ai-prompt caches only alias/endpoint/mc locators."
---

# CDN Asset Ops (MinIO / S3)

Operate CDN object storage with the priority **current facts > local cache > discovery** and strict deletion blast-radius controls.

## Trigger

Activate when the user provides a MinIO Console URL, requests upload/list/move/rename-prefix/delete operations on CDN/S3 objects, wants to configure `mc`/an S3 alias, or needs CDN 404/path diagnosis.

## Step 0 — Cache-first preflight

Use the cross-platform Python entrypoint:

```text
python <skill_dir>/scripts/cdn_preflight.py "<console URL or host>"
```

It MUST check `.local/state.json` for a verified host alias/endpoint first; return directly on a valid cache hit; inspect `mc`, aliases, and S3 API endpoints only when cache is absent/stale; cache verified `mc` locator, alias, endpoint, and verification time; NEVER cache AccessKey/SecretKey.

On real operation failure or environment/network/MinIO changes, force rediscovery:

```text
python <skill_dir>/scripts/cdn_preflight.py "<target>" --refresh
```

`scripts/cdn_preflight.sh` is legacy compatibility only; prefer Python.

## Configuration

Only when configuration is confirmed missing, read `references/setup.md`: parse Console URL → determine API endpoint → install/locate `mc` → `mc alias set`.

Credentials come from the user or existing secure storage and are used only for `mc alias set`. Never write them to `.local/runtime.json` / `.local/state.json`. After setup, minimally verify with `mc ls <alias>`, then rerun preflight `--refresh` to cache success.

Console port is NOT necessarily the S3 API port. Resolve it from an existing alias, real probe, or explicit user input; NEVER guess.

## Operations

Read `references/operations.md` for exact commands. Common operations are list, upload, prefix rename (copy + delete), and delete.

The `/browser/<bucket>/<base64>` tail in a Console URL may encode an object prefix. Confirm the current Console URL semantics before assuming that interpretation.

## Guardrails

1. **Zero credential leakage:** never echo, log, or commit AccessKey/SecretKey.
2. **Two-phase overwrite/delete:** copy/upload and verify first; then show the exact alias/bucket/prefix and object count to be deleted and require explicit confirmation.
3. Before `mc rm --recursive --force`, re-check the complete target. NEVER recursively delete a bucket root without a prefix.
4. When changing CDN paths, warn that frontend references must change or they will 404.
5. Check for same-name target objects before upload; disclose overwrite before doing it.
6. Trust only measured/cached endpoints. On cache failure use `--refresh`; do not add machine exceptions to central prompts.
7. If the current session exposes a native tool that can operate the target S3/MinIO directly, current session facts outrank cached `mc` state.

## Bundled files

- `scripts/cdn_preflight.py` — canonical cross-platform read-only cached preflight.
- `scripts/cdn_preflight.sh` — legacy compatibility entrypoint.
- `references/setup.md` — setup and endpoint details.
- `references/operations.md` — safe list/upload/move/delete procedures.
