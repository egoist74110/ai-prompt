---
name: cdn-asset-ops
description: Operate MinIO / S3-compatible CDN buckets safely. Reuse cached mc/alias/endpoint state first; discover only on first use or cache failure. Use for upload/list/move/rename-prefix/delete and MinIO Console URLs.
credentials:
  - name: MinIO AccessKey / SecretKey
    required: true
    description: "S3 凭证。只用于 mc alias 配置；绝不回显、绝不写入 ai-prompt local state。"
    storage: "由 mc 自己的本机配置管理，ai-prompt 只缓存 alias/endpoint/mc locator。"
---

# CDN Asset Ops (MinIO / S3)

操控 CDN 对象存储。核心规则：**当前事实 > 本地缓存 > discovery**，并严格限制删除爆炸半径。

## Trigger

满足任一即激活：

1. 用户给 MinIO Console URL，如 `http://<host>:<port>/browser/<bucket>/...`。
2. 用户要上传、列举、移动/重命名前缀、删除 CDN/S3 对象。
3. 用户要配置 `mc` / S3 alias，或排查 CDN 404/路径问题。

## 第 0 步 — 缓存优先 Preflight

使用跨平台 Python 入口：

```text
python <skill_dir>/scripts/cdn_preflight.py "<console URL 或 host>"
```

它会：

- 先查 `.local/state.json` 是否已有该 host 的已验证 alias/endpoint；
- cache hit 时直接返回，不再每次扫 alias 和 8 个端口；
- 无缓存/缓存失效时才检查 `mc`、匹配 alias、探测 S3 API endpoint；
- 成功后缓存 `mc` locator、alias 名、endpoint、验证时间；
- **绝不缓存 AccessKey / SecretKey**。

实际操作失败、网络/VPN/MinIO 配置改变时再强制重探：

```text
python <skill_dir>/scripts/cdn_preflight.py "<target>" --refresh
```

旧 `scripts/cdn_preflight.sh` 仅保留兼容；新流程以 Python 入口为准。

## 配置（仅确认未配置时）

读 `references/setup.md`，按流程配置：解析 Console URL → 确认 API endpoint → 安装/定位 `mc` → `mc alias set`。

- AccessKey / SecretKey 由用户提供或由现有安全存储取得，只用于 `mc alias set`。
- 不把密钥写入 `.local/runtime.json` / `.local/state.json`；这里只缓存 `mc` 路径、alias 名、endpoint。
- 配完用 `mc ls <alias>` 做最小验证，然后重新跑 preflight `--refresh` 写入成功缓存。

> Console 端口 ≠ S3 API 端口。端口必须来自已有 alias、实际探测或用户明确提供，不能猜。

## 操作

读 `references/operations.md` 获取精确命令。常见动作：列举、上传、重命名前缀（=复制+删除）、删除。

Console URL 中 `/browser/<bucket>/<base64>` 的尾段可能是对象前缀编码；解析前先确认该 Console 版本的 URL 语义，不要仅凭格式假定。

## Guardrails

1. **密钥零泄露**：不回显、不记录、不提交 AccessKey/SecretKey。
2. **删除/覆盖二段式**：先复制/上传并核对；再把将删除的完整 alias/bucket/prefix + 对象数量展示给用户，得到明确确认后才删。
3. `mc rm --recursive --force` 前必须重新核对完整目标，禁止对 bucket 根做无前缀递归删除。
4. 改 CDN 路径前提醒同步修改前端引用，否则会 404。
5. 上传前检查目标是否已有同名对象；覆盖要先告知。
6. endpoint 只信当前实测/缓存；缓存调用失败就 `--refresh`，不要把失败补成中央机器特例。
7. 当前会话若已经有可直接操作该 S3/MinIO 的原生工具，实时工具事实优先于本地 `mc` 缓存。

## Bundled Files

- `scripts/cdn_preflight.py` — 正典：跨平台、只读、带本地缓存的 preflight。
- `scripts/cdn_preflight.sh` — 旧兼容入口，不再作为默认路径。
- `references/setup.md` — 配置流程与 endpoint 坑。
- `references/operations.md` — 列举/上传/移动/删除的安全命令流程。
