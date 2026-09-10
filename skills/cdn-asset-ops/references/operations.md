# CDN Object Operations

Prerequisite: the `mc` alias is configured and connectivity to the target bucket is verified. Read `setup.md` only when preflight reports missing configuration.

## List

```bash
mc ls <alias>
mc ls <alias>/<bucket>
mc ls <alias>/<bucket>/<prefix>/
mc ls --recursive <alias>/<bucket>/<prefix>/
```

## Upload

Before upload, list the target prefix and check for same-name objects. Never silently overwrite an existing object; disclose the collision and obtain confirmation before intentional replacement.

```bash
mc cp ./banner.png <alias>/<bucket>/<prefix>/
mc cp --recursive ./static/ <alias>/<bucket>/<prefix>/
```

## Rename a Prefix

S3/MinIO has no real folders. Renaming a folder means copying every object from the old key prefix to the new prefix, verifying the copy, then deleting the old prefix.

Use two phases; never combine copy and delete into one irreversible operation.

### Phase 1 — Copy and Verify

```bash
mc cp --recursive <alias>/<bucket>/<old-prefix>/ <alias>/<bucket>/<new-prefix>/
mc ls --recursive <alias>/<bucket>/<old-prefix>/
mc ls --recursive <alias>/<bucket>/<new-prefix>/
```

Verify object counts and, when practical for the task risk, representative object metadata/content. If verification differs, stop and do not delete the source.

Tell the user when the CDN URL prefix changes because application references may also need updating.

### Phase 2 — Delete Old Prefix

Before deletion, state the complete target prefix and verified object count and obtain explicit user confirmation.

```bash
mc rm --recursive --force <alias>/<bucket>/<old-prefix>/
```

## Delete

Deletion always requires explicit confirmation of the exact target. Recursive deletion additionally requires the object count.

```bash
mc rm <alias>/<bucket>/<object>
mc rm --recursive --force <alias>/<bucket>/<prefix>/
```

Never recursively delete a bucket root or an empty/unspecified prefix.

## Automation

If wrapping these operations in code, keep copy/verification and confirmed deletion as separate steps. Pass command arguments as an array (`execFile` or equivalent), never interpolate credentials into shell command strings. Credentials are secret inputs: do not echo, log, cache, or commit them.
