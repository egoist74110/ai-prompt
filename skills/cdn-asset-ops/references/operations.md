# Operations — 列举 / 上传 / 重命名前缀 / 删除

前提：alias 已配好并验证连通（见 setup.md）。下面用 `myminio` + bucket `cg-cdn-minio` 举例，按实际替换。

## 列举

```bash
mc ls myminio                                          # 所有 bucket
mc ls myminio/cg-cdn-minio                             # bucket 根
mc ls myminio/cg-cdn-minio/public/event/static/        # 指定前缀
mc ls --recursive myminio/cg-cdn-minio/public/event/static/   # 递归，可用来数对象数量
```

## 上传

```bash
# 单文件
mc cp ./banner.png myminio/cg-cdn-minio/public/event/static/

# 整目录递归
mc cp --recursive ./static/ myminio/cg-cdn-minio/public/event/static/
```

上传前先 `mc ls` 看目标前缀有没有同名对象，避免静默覆盖；要覆盖先告知用户。

## “重命名文件夹” 的本质

MinIO/S3 没有真文件夹。`public/event/static/continuous-signin/` 只是对象 Key 的前缀。所以“重命名文件夹” = **把旧前缀下所有对象拷到新前缀 → 核对 → 删旧前缀**。

### 二段式（强制，禁止一键 cp+rm）

旧：`public/event/static/continuous-signin/`，新：`public/event/static/continuous-sign-in/`

**第一段 — 拷贝 + 核对（只读校验）**

```bash
mc cp --recursive \
  myminio/cg-cdn-minio/public/event/static/continuous-signin/ \
  myminio/cg-cdn-minio/public/event/static/continuous-sign-in/

# 核对两边对象数量是否一致
mc ls --recursive myminio/cg-cdn-minio/public/event/static/continuous-signin/  | wc -l
mc ls --recursive myminio/cg-cdn-minio/public/event/static/continuous-sign-in/ | wc -l
```

数量不一致 → 停下报告，**不要删**。

**提醒用户**：CDN 路径变了，前端引用这些资源的 URL 也要同步改，否则线上 404。

**第二段 — 删旧前缀（需用户明确确认）**

先把「将删除的完整前缀 + 对象数量」复述给用户，等确认：

```bash
mc rm --recursive --force \
  myminio/cg-cdn-minio/public/event/static/continuous-signin/
```

## 删除（独立删除同样要确认）

```bash
mc rm myminio/cg-cdn-minio/public/event/static/old.png         # 单对象
mc rm --recursive --force myminio/cg-cdn-minio/public/event/static/tmp/   # 递归
```

`--recursive --force` 前必须复述目标前缀 + 对象数，等用户确认。严禁对 bucket 根或无前缀做递归删除。

## 自动化封装（如果要写进工具）

```ts
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
const run = promisify(execFile)

await run('mc', ['alias', 'set', 'myminio', 'http://43.198.44.29:9001', accessKey, secretKey])
await run('mc', ['cp', '--recursive', `${alias}/${bucket}/${oldPrefix}`, `${alias}/${bucket}/${newPrefix}`])
// 核对数量一致 + 用户确认后才：
await run('mc', ['rm', '--recursive', '--force', `${alias}/${bucket}/${oldPrefix}`])
```

工具层把流程拆成「复制+核对」与「确认后删除」两个独立步骤，不要做成一键操作。
