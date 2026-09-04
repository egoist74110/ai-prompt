---
name: ado-pr
description: 与自建 Azure DevOps Server（*.cg1alias.com，非 dev.azure.com）交互的统一入口——读工单、读/列 PR、建 PR 并关联工单。命中工单号、PR、发布/建 PR、合并到 main/master 等意图时使用。优先复用本机已验证的本地 strategy；只有首次或缓存失效时才探测认证来源、执行侧和 API 路径。
---

# ado-pr — Azure DevOps Server 统一操作

目标：用本机可用的 PAT / CLI / REST 直接操作自建 Azure DevOps Server，不依赖额外 ADO MCP 后台。

## 0. 先复用本机已验证状态

所有仓库内相对路径以 `router.md` 所在目录为根。

先看 `.local/runtime.json` / `.local/state.json`（若存在）：

- `state.skills.ado-pr.strategy`
- `runtime.credentials.ado_pat`
- `state.skills.ado-pr.request_executor`
- `state.skills.ado-pr.network`
- `state.skills.ado-pr.api`

若这些信息仍可用，**直接走缓存路径，不要重新扫描 keychain、WSL、配置目录、CLI 或网络**。

只有以下情况才重新 discovery：

1. 本机从未跑过本 skill；
2. 缓存中的命令 / 文件 / credential locator 已失效；
3. 缓存策略执行失败，且失败原因明确指向环境变化。

Discovery 跑通后，把机器相关、非敏感事实写回 `.local/`。禁止把 PAT 明文写入缓存。

示例：

```text
python tools/runtime_state.py set state skills.ado-pr.strategy '"windows-rest"'
python tools/runtime_state.py set state skills.ado-pr.request_executor '"powershell"'
```

## 1. 每次任务仍要实时确认的仓库事实

这些不能长期缓存：

1. `git remote -v`：解析 host / organization / project / repository。
2. `git branch --show-current`：source branch。
3. `git ls-remote --heads origin`：目标分支默认 main，无 main 才用 master。
4. 写操作前 `git status` + `git push --dry-run origin <branch>`。
5. 工单号来自用户输入、分支名或 commit message；找不到再问，不要编。

## 2. Strategy Discovery（只在首次或缓存失效时）

### macOS 候选：`az-cli`

优先探测：

- `security` 是否存在；
- `az` 是否存在；
- `~/.config/my-own-script/ui_settings.yaml` 是否存在并能按当前 host 找到 library id。

已知 credential 规则：

- keyring service：`my-own-script`
- account：`azuredevops_pat:<library-id>`

登录时不要把 PAT 打印出来：

```bash
security find-generic-password -s "my-own-script" -a "azuredevops_pat:<library-id>" -w \
  | az devops login --organization "<organization>"
```

成功后缓存 locator，而不是 token：

```json
{
  "type": "keychain",
  "service": "my-own-script",
  "account": "azuredevops_pat:<library-id>"
}
```

并缓存：`strategy=az-cli`。

### Windows / WSL 候选：`windows-rest`

不要假定 WSL distro 名、token 路径、Windows 用户名或网络拓扑。

首次需要按当前机器实测：

1. 找到 PAT 的**已知配置来源**；若项目/用户已有明确 locator，优先用它，不要全盘扫描。
2. 若 locator 位于 WSL，记录当前 distro 和 Windows 可访问的 UNC 路径；agent 本身在 WSL 时也可记录对应 Linux 路径。
3. 分别验证目标 ADO host 从当前执行侧是否可达；若 WSL 不通而 Windows 可达，记录 `request_executor=powershell`，以后不要再从 WSL 等超时。
4. 用最小只读 REST 请求验证 PAT 与 API。

成功后缓存类似：

```json
{
  "strategy": "windows-rest",
  "request_executor": "powershell",
  "network": {
    "windows_direct": true,
    "wsl_direct": false
  }
}
```

credential locator 放 `runtime.credentials.ado_pat`，例如：

```json
{
  "type": "file",
  "path": "<machine-local-path>"
}
```

不要把某台机器的 distro 名或绝对路径写回本 SKILL。

## 3. 服务固有事实（可跨机器复用）

以下是目标自建 ADO/TFS 服务已验证的 API 行为，可保留在中央：

- Server 版 API，不要套用 dev.azure.com 云端假设。
- comments 端点需要 `api-version=4.1-preview`。
- comments 响应字段是 `comments`，不是新版常见的 `value`。
- JSON 按 UTF-8 处理。
- `Code` 与 `Work Items` PAT scope 相互独立；能读不能写时优先检查对应 scope 的 Read / Read & write。
- 单条 work item GET 对 URL 中 project 路由段较宽松，但**列表/查询类端点不要类推**。

如果以后在别的服务器实例发现不同，按 host 维度记录到本地 state，别直接把单机/单实例差异提升成全局真理。

## 4. 读取工单

### `az-cli`

```bash
az boards work-item show --id <work-item-id> \
  --organization "<organization>" -o json
```

评论：

```bash
az devops invoke --area wit --resource comments \
  --route-parameters project="<project>" workItemId=<work-item-id> \
  --organization "<organization>" --api-version 4.1-preview -o json
```

### `windows-rest`

使用缓存的 credential locator 取 PAT，整个过程中不要打印明文；然后从缓存的 `request_executor` 发请求。

PowerShell 形态：

```powershell
$tok = (<按 runtime.credentials.ado_pat 读取>).Trim()
$b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$tok"))
$headers = @{ Authorization = "Basic $b64" }
$S = "<organization>/<project>/_apis"
Invoke-RestMethod -Uri "$S/wit/workitems/<id>?api-version=4.1&`$expand=all" -Headers $headers
Invoke-RestMethod -Uri "$S/wit/workitems/<id>/comments?api-version=4.1-preview" -Headers $headers
$tok = $null
```

如果当前 PowerShell 控制台导致中文输出损坏，保存响应原始 UTF-8 字节后再由 Python/支持 UTF-8 的工具读取；这是输出层问题，不要误判服务返回 GBK。

## 5. 读取 / 列出 PR

`az-cli` 已知可用：

```bash
az repos pr list --organization "<organization>" --project "<project>" --repository "<repository>" -o json
az repos pr show --id <pr-id> --organization "<organization>" -o json
```

REST strategy 若当前 state 已缓存对应端点并验证成功，直接复用；没有缓存时只探测一次，成功后把 endpoint/version 写入 `state.skills.ado-pr.api`。

## 6. 建 PR

`az-cli`：

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

REST strategy 同上：已验证就复用；未验证时探测后缓存 endpoint/version，不要每次重新猜 URL。

PR 描述基于实际 diff 生成，默认格式：

```text
## 說明
<一两句话>

## 變更內容
- <要点>

## 關聯單
AB#<id>
```

`--work-items` 做硬关联；正文 `AB#<id>` 便于阅读和自动链接。

## 7. 缓存写回规则

适合写入 `.local/runtime.json`：

- PAT locator
- WSL distro / Windows / WSL 路径映射
- CLI 可执行路径
- 固定外部程序位置

适合写入 `.local/state.json`：

- 当前机器已验证 strategy
- request executor
- WSL/Windows 网络可达性
- REST endpoint/version
- 某 MCP/CLI 已配置且最后一次验证成功

不应写入本地缓存：

- token/password/cookie/私钥正文
- 当前分支、当前工单号、当前 PR 号等一次性任务数据

不应写回中央 SKILL：

- 某台机器用户名/home
- 某台机器 WSL distro 名
- 某台机器 token 文件绝对路径
- 某台机器 VPN/路由导致的网络结论

## 8. 收尾

- 写操作只做用户要求的范围。
- 报告 PR 号、链接、关联工单、source→target。
- 本次若首次探测出新的机器事实且已成功验证，确认已写回 `.local/`，避免下次重复排障。
