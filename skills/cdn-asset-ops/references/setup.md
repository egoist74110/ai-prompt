# Setup — 从 Console URL 到可用的 mc alias

只在 Preflight 判定「未配置」时读这篇。已有 alias 就直接复用。

## 1. 解析 Console URL

用户常给这种地址：

```txt
http://43.198.44.29:9000/browser/cg-cdn-minio/cHVibGljL2V2ZW50L3N0YXRpYy8=
```

拆出：

```txt
Console 地址 : http://43.198.44.29:9000
Bucket       : cg-cdn-minio
路径(前缀)   : cHVibGljL2V2ZW50L3N0YXRpYy8=  -> base64 解码
```

`/browser/...` 是 MinIO Console 的**网页**路径，不是 S3 API。最后那段是前缀的 base64：

```bash
echo 'cHVibGljL2V2ZW50L3N0YXRpYy8=' | base64 -d   # => public/event/static/
```

## 2. 坑：Console 端口 ≠ S3 API 端口

`mc` 连的是 S3 API，不是 Console 网页端口。确认某端口是不是 Console：

```bash
curl -I http://43.198.44.29:9000/minio/health/live
```

返回里出现 `Server: MinIO Console` + `Content-Type: text/html` → 这是控制台端口，**不能**拿来 `mc alias set`。

## 3. 探测真正的 S3 API 端口

Preflight 脚本已经做了这步。手动等价命令：

```bash
for p in 9000 9001 9002 9003 9004 9005 80 443; do
  echo "===== port $p ====="
  curl -s -I --max-time 3 http://43.198.44.29:$p/minio/health/live | head -n 5
done
```

返回 `HTTP/1.1 200 OK` + `Server: MinIO`（注意：是 MinIO，不是 MinIO Console）的端口就是 API。

典型结果：`9000 = Console`，`9001 = API` → API endpoint 是 `http://43.198.44.29:9001`。

探不到就别硬猜，向用户要真实 API endpoint（可能走了网关 / 自定义端口）。

## 4. 安装 mc

```bash
brew install minio/stable/mc   # macOS
mc --version                   # 确认
```

## 5. 配置 alias

```bash
mc alias set <aliasName> <S3_API_ENDPOINT> <AccessKey> <SecretKey>
# 例：
mc alias set myminio http://43.198.44.29:9001 <AccessKey> <SecretKey>
```

成功输出 `Added \`myminio\` successfully.`

- AccessKey/SecretKey 由用户给，**绝不回显/记录**；复述命令用占位符。
- 配完立刻验证连通：

```bash
mc ls myminio                  # 列 bucket
mc ls myminio/cg-cdn-minio     # 列指定 bucket
```

连得上、能看到目标 bucket，才算配置成功，再进 operations。
