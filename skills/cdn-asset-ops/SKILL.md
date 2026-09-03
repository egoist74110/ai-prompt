---
name: cdn-asset-ops
description: Operate MinIO / S3-compatible CDN buckets via the mc client — detect whether mc is configured, help configure it from a Console URL, then list / upload / rename-prefix / delete objects safely. Use when the user gives a MinIO console URL (http://host:port/browser/<bucket>/...) or asks to upload, list, move, rename a "folder", or delete files on the CDN / object store.
credentials:
  - name: MinIO AccessKey / SecretKey
    required: true
    description: "S3 凭证。只用于 `mc alias set`，绝不回显、绝不写进日志/命令复述/输出。"
    storage: "由用户在会话中提供，或已存在的 mc alias。不要持久化到本仓库。"
---

# CDN Asset Ops (MinIO / S3)

操控 CDN 对象存储（MinIO / 任意 S3 兼容）的上传、列举、重命名前缀、删除。核心不是“会不会跑命令”，而是 **先判断配没配好** + **不让 AI 发疯乱删**。

## Trigger

满足任一即激活：

1. 用户给了 MinIO Console 链接，形如 `http://<host>:<port>/browser/<bucket>/<base64-or-path>`。
2. 用户要 上传 / 列举 / 移动 / “重命名文件夹” / 删除 CDN、对象存储、bucket 里的资源。
3. 用户要配置 `mc` / S3 alias，或抱怨 CDN 资源 404、路径不对。

## 第 0 步 — 永远先 Preflight（只读，不改任何东西）

直接跑捆绑脚本，**不要**凭记忆猜端口、猜 alias：

```bash
bash <skill_dir>/scripts/cdn_preflight.sh "<用户给的 console URL 或 host>"
```

它会告诉你三件事：mc 装没装、目标 host 有没有现成 alias、S3 API endpoint 是哪个端口。

- **已有匹配 alias** → 已配置好，跳到「操作」。别重新跑配置教程。
- **没有 alias / mc 没装 / 没探到 API 端口** → 进「配置」。

> 关键坑：Console 端口 ≠ S3 API 端口（常见 9000=Console、9001=API）。`mc alias set` 必须用 `Server: MinIO` 的那个端口，用错端口会一直连不上。详见 `references/setup.md`。

## 配置（仅当 Preflight 判定未配置时）

读 `references/setup.md`，按里面的流程走：解析 Console URL → 探测 API 端口 → 装 mc → `mc alias set`。

- AccessKey / SecretKey 由用户提供。拿到后**只**用于 `mc alias set`。
- **绝不**把密钥打印到回显、日志、命令复述或总结里。复述命令时用 `<AccessKey> <SecretKey>` 占位。
- 配完用 `mc ls <alias>` 验证连通，再继续。

## 操作

读 `references/operations.md` 拿到精确命令。常见动作：列举、上传、重命名前缀（= 拷贝+删除）、删除。

从 Console URL 解析出的 base64 段（`/browser/<bucket>/<base64>`）是路径前缀的 base64，可 `echo <seg> | base64 -d` 还原成 `public/event/static/...`。

## Guardrails — 防止乱搞（必须遵守）

1. **密钥零泄露**：任何时候都不回显 AccessKey/SecretKey；不写进文件、日志、提交、总结。
2. **删除/覆盖一律二段式，禁止一键 cp+rm**：
   - 第一段：`mc cp --recursive 旧前缀 新前缀`，然后 `mc ls 新前缀` 核对对象数量与旧前缀**一致**。
   - 第二段：把「将删除的完整前缀 + 对象数量」复述给用户，**等用户明确确认**，才 `mc rm --recursive --force 旧前缀`。
   - 数量对不上 → 停下来报告，绝不删。
3. **`mc rm --recursive --force` 前必须复述目标并等确认**，不允许在用户没看清前缀的情况下执行。
4. **改 CDN 路径会让前端引用 404**：重命名/移动前缀前，主动提醒用户「前端引用这些资源的路径也要同步改，否则线上 404」。
5. **上传前先 `mc ls` 看目标前缀是否已有同名对象**，避免静默覆盖；要覆盖也先告知。
6. **端口靠探测，不靠猜**：用 Preflight 的结果，别硬编码 9000/9001。
7. **不扩大爆炸半径**：命令里的 bucket 和前缀严格用核对过的值；不对 bucket 根、不带前缀地做 `--recursive` 删除。

## Bundled Files

- `scripts/cdn_preflight.sh` — 只读探测：mc 状态 + alias 匹配 + S3 API 端口。
- `references/setup.md` — 从 Console URL 到 `mc alias set` 的完整配置流程与踩坑。
- `references/operations.md` — 列举 / 上传 / 重命名前缀 / 删除 的精确命令与二段式删除流程。
