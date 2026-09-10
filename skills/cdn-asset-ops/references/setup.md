# CDN / MinIO Setup

Read this only when preflight reports that no usable `mc` alias is configured. Reuse an already verified alias instead of reconfiguring it.

## 1. Parse a Console URL

A MinIO Console URL commonly has this shape:

```text
https://<host>:<console-port>/browser/<bucket>/<base64-prefix>
```

Extract the host, bucket, and encoded prefix. `/browser/...` is a Console web route, not an S3 API endpoint. Decode the final segment only when the URL format identifies it as the encoded object prefix.

## 2. Console Port Is Not Necessarily the S3 API Port

`mc` must connect to the S3 API endpoint. A response identifying itself as MinIO Console or returning the Console HTML is not a valid API endpoint for `mc alias set`.

Use preflight/runtime facts first. If endpoint discovery is required, probe only a small justified candidate set derived from supplied configuration or deployment conventions; do not scan arbitrary hosts or broad port ranges.

If no candidate can be verified, ask for the real S3 API endpoint instead of guessing.

## 3. Install `mc` When Missing

Use the platform's supported MinIO Client installation method. Installation changes the machine and requires user confirmation when the current environment/policy requires approval for package installation.

After installation verify:

```text
mc --version
```

## 4. Configure an Alias

```text
mc alias set <alias> <S3_API_ENDPOINT> <AccessKey> <SecretKey>
```

Credentials are secret inputs. Never echo, log, cache in `.local`, include in review prompts, or commit them. When showing a command, use placeholders.

## 5. Verify Before Use

```text
mc ls <alias>
mc ls <alias>/<bucket>
```

Configuration is verified only after the alias can reach the intended service and the expected bucket is accessible. A syntactically successful `alias set` alone is not proof that the target is correct.
