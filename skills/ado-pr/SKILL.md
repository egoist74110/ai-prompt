---
name: ado-pr
description: 与自建 Azure DevOps Server（azuredevops.cg1alias.com，非 dev.azure.com）交互的统一入口——读工单、读PR/列表、建PR并关联工单。当用户提到"工单"、"关联单"、给出一个工单号（如"4877"、"#4877"、"工单5023"），或提到"PR"、"发布PR"、"建PR"、"提PR"、"合并到main/master"等——不管是想读取还是想发起——都用这个技能，直接用本机钥匙串 PAT + az CLI 读写，不依赖任何额外的 ADO MCP/后台服务。
---

# ado-pr — Azure DevOps Server 统一操作（工单/PR，读+写）

用户所有代码仓库都托管在自建 Azure DevOps Server（不是 dev.azure.com，是 `https://<xxx>.cg1alias.com` 这类私有域名），必须用 `az boards` / `az repos`（REST 走 Server 版 API），不能假设是云端 ADO。

**核心原则：只用本机钥匙串里的 PAT + az CLI 直连。不要因为某个 MCP 工具"已暴露在会话里"就默认走它去读/写 ADO 内容——那类 MCP（如 ado-work-items，依赖 my-own-script 后台脚本）不是必需依赖，会有额外的连通性风险；本技能的路径更直接、更可控，优先级更高。**

## 触发条件（读、写都算，不止 PR）

- 用户给出工单号并想**读取**：例如"读取工单5023""查一下工单4877""工单xxxx写的什么"——直接读，不发PR。
- 用户提到工单号 + "PR"/"发布"/"合并"/"建PR" 等**写**意图，例如"关联单4877""帮我发布PR""建个PR关联一下xxxx"。
- 用户想看 PR 列表/详情，例如"看下这个仓库的PR""PR xxx 是什么状态"。
- 用户只说"发个PR"没给工单号：先按下面步骤找当前分支相关的工单线索（commit message、分支名），找不到就直接问用户工单号，不要瞎编。

## 前置：一次性事实收集（不要臆测，实测确认）

1. **确认当前仓库信息**：`git remote -v` 拿 origin push URL，形如
   `https://<host>/DefaultCollection/<Project>/_git/<Repo>`。从中拆出 `organization = https://<host>/DefaultCollection`、`project`、`repository`。
2. **确认当前分支 / 目标分支**：`git branch --show-current` 拿 source；target 默认 `main`（远端没有 main 就用 `master`，用 `git ls-remote --heads origin` 确认，不要瞎猜）。
3. **确认干净可推送**：`git status`，若有未合并冲突/未提交改动，先处理完（合并冲突走正常解决流程，不要用 `-X ours/theirs` 抢答，除非用户明确要求）。`git push --dry-run origin <branch>`确认能推，需要真推时才 `git push`。
4. **工单号**：用户给的数字/`#4877`/"关联单xxx"/"工单xxx"里的号。需要查标题/状态/描述时，直接走下面「认证」+「读取工单」两步用 az CLI 读，**不要**去调什么 ado 相关 MCP 工具——那是另一套依赖 my-own-script 后台服务的路径，连通性不受控，本技能的钥匙串+az CLI 直连已经够用，且更快更稳。

## 认证：从本机钥匙串取 PAT（不要在别处翻找）

PAT 由 `my-own-script` 项目统一管理，存在 macOS 系统钥匙串里，规则见记忆 [[ado-pat-keychain-storage]]：

- keyring service 固定 `my-own-script`。
- account 名是 `azuredevops_pat:{library.id}`，**library.id 是 uuid 形式的 id（如 `lib:1a4fdcde-...`），不是显示名（如 `cg1alias`）**。
- 找 library id：读 `~/.config/my-own-script/ui_settings.yaml`，在 `libraries:` 列表里按 `base_url` 匹配当前仓库的 host（第 1 步拿到的 `<host>`），取对应的 `id` 字段。这台机器目前已知的一条：`base_url: https://azuredevops.cg1alias.com` → `id: lib:1a4fdcde-65e6-4af8-b2c5-0419f5d97dfb`（如果以后配置变了，以文件内容为准，不要硬编)。
- 取值并登录（一条命令管道，不要分两步打印密码到终端）：
  ```bash
  security find-generic-password -s "my-own-script" -a "azuredevops_pat:<library-id>" -w | az devops login --organization "<organization>"
  ```
  这一步会触发 macOS 钥匙串授权确认弹窗，属于正常流程。
- 不要用 `security find-generic-password ... -w` 单独跑出来把明文打到聊天记录/日志里；始终用管道直接喂给 `az devops login`。
- 不要为了"找PAT"去扫 `.zshrc`/`.env`/`~/.azure`/keychain 列表等——存放规则已知，直接按上面公式取，不要重新侦查。

### 认证成功但某个操作仍 401/403

先看是哪个资源域：`Code`（repos/PR）和 `Work Items`（工单）是 PAT 里两个独立的 scope，各自有 Read / Read&Write 档位，互不影响——`az repos pr create` 报 `requires user authentication` 而 `az repos pr list` 能正常读，是 `Code` scope 只给了 `Read`；工单侧同理，能读不能改（比如加评论）就是 `Work Items` scope 只给了 `Read`。处理方式：

1. 告诉用户去 ADO 个人设置 → Personal Access Tokens，把对应资源域的权限从 `Read` 改成 `Read & write`（或更高）。
2. 用户确认改完后（PAT 值不变，钥匙串里存的还是同一串，不用重新取），直接重跑刚才失败的命令，不需要重新登录。

## 读取工单

登录（见上方「认证」）之后，直接读，不经过任何 MCP：

```bash
az boards work-item show --id <work-item-id> --organization "<organization>" -o json
```

返回 JSON 里 `fields` 下常用字段：`System.Title`（标题）、`System.State`（状态）、`System.Description`（描述，可能是 HTML）、`System.AssignedTo`、`System.WorkItemType`。

需要评论时（`az boards` 没有直接子命令），走 az CLI 的通用 REST 网关，同一份登录态即可用：

```bash
az devops invoke --area wit --resource comments \
  --route-parameters project="<project>" workItemId=<work-item-id> \
  --organization "<organization>" --api-version 7.1-preview -o json
```

## 读取 / 列出 PR

```bash
# 列表（当前仓库）
az repos pr list --organization "<organization>" --project "<project>" --repository "<repository>" -o json

# 单个 PR 详情
az repos pr show --id <pr-id> --organization "<organization>" -o json
```

## 建 PR

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

- `--work-items` 用来做硬关联（ADO 侧 work item links）；描述里再补一行 `## 關聯單\nAB#<id>` 方便正文里也能一眼看到、且触发 ADO 的文本自动链接。
- 标题/描述默认用繁体中文（这是该用户过往 PR 的语言习惯），格式：
  ```
  ## 說明
  <一两句话说清楚这次PR做了什么>

  ## 變更內容
  - <要点1>
  - <要点2>

  ## 關聯單
  AB#<id>
  ```
  内容要基于实际 diff（`git log <target>..HEAD --oneline`、`git diff <target>...HEAD --stat`）来写，不要照抄工单标题敷衍。
- 命令成功会返回 JSON，里面 `pullRequestId` 和 `repository.webUrl` 拼出可访问链接：
  `<repository.webUrl>/pullRequest/<pullRequestId>`。把这个链接和 PR 号回报给用户。

## 收尾

- 报告：PR 号、链接、关联的工单号、source→target 分支。
- 不要额外做用户没要求的事（比如自动 set auto-complete、加审阅人、改工单状态）——除非用户这次话里明确要求。
