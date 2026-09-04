---
name: bilibili-auto-transcript
version: "6.0.0"
description: "B站视频/收藏夹转录。优先 CC→AI 字幕→Whisper；机器路径、Bash、输出目录、数据库、收藏夹 ID 走 .local 缓存，避免跨 macOS/Windows/WSL 重复探测。"
---

# Bilibili Auto Transcript

用于单视频转录和收藏夹批量扫描。中央 Skill 只保存流程；**本机路径/运行时 locator 已迁到 `.local/runtime.json`**。

## 快速原则

优先级统一为：

1. 当前环境变量/当前会话事实；
2. `.local/runtime.json` 中 `skills.bilibili-auto-transcript` 已缓存配置；
3. 首次 discovery；
4. discovery 成功后立即缓存，后续直接复用。

Secret 仍放环境变量或该 Skill 的 `.env`（已 gitignore）；**不得把 API key/cookie 写入 `.local`**。

## 本地配置

由 `scripts/runtime_config.py` 统一解析。可查看当前解析结果：

```text
python <skill_dir>/scripts/runtime_config.py show
```

主要字段：

```json
{
  "skills": {
    "bilibili-auto-transcript": {
      "state_dir": "<machine path>",
      "output_dir": "<machine path>",
      "db_path": "<machine path>",
      "bash": "<resolved bash executable>",
      "browser_type": "chromium",
      "favorite_media_id": "<non-secret id>"
    }
  }
}
```

环境变量可临时覆盖缓存：

- `BILIBILI_STATE_DIR`
- `BILIBILI_OUTPUT_DIR`
- `BILIBILI_DB_PATH`
- `BILIBILI_BASH`
- `BILIBILI_BROWSER`
- `FAV_MEDIA_ID`

### 旧安装兼容

首次运行时若发现旧目录存在，会优先复用并把路径缓存下来：

- 旧 OpenClaw state；
- 旧 `~/workspace/knowledge/bilibili` 输出；
- Skill 旧 `.db/transcripts.db`。

新机器没有这些旧目录时，默认数据落在 `AI_PROMPT_ROOT/.local/skills/bilibili-auto-transcript/` 下，不再创建 OpenClaw 专属路径。

## 模式一：单视频转录

Agent 默认只调用 Python 入口，不直接调用 Bash：

```text
python <skill_dir>/scripts/run_transcript.py "https://www.bilibili.com/video/BVxxxx/"
```

指定本次输出目录/浏览器：

```text
python <skill_dir>/scripts/run_transcript.py "<url>" --output "<dir>" --browser chromium
```

`run_transcript.py` 会：

- 从本地 runtime 直接拿已验证 Bash/output/browser locator；
- 没缓存时只做一次 Bash discovery 并缓存；
- 把 runtime 配置传给旧 Bash 转录引擎；
- Windows 原生环境可使用已安装的 Git Bash/bash；纯 Windows 若没有 Bash，会明确报缺少依赖，不会假装可运行。

底层转录优先级：

1. 人工 CC 字幕；
2. B站 AI 字幕；
3. Whisper 本地 ASR。

Whisper 模型按 GPU/显存/视频时长自适应，属于执行策略，不需要 Agent 每轮重新判断安装路径。

## 模式二：收藏夹扫描/批量转录

只扫描：

```text
python <skill_dir>/scripts/bilibili_scanner.py
```

批量转录：

```text
python <skill_dir>/scripts/batch_transcribe.py
```

`FAV_MEDIA_ID` 第一次从环境或 `.env` 读到后可缓存为非敏感本地配置；后续无需反复找收藏夹 ID。

批处理状态、processed list、CSV 报告、日志目录都来自同一个 `state_dir`；SQLite 路径来自 `db_path`，输出从 `output_dir` 读取。脚本之间不再各自写死不同 home 路径。

## 摘要

设置 `OPENAI_API_KEY` 时可自动生成摘要；支持 OpenAI 兼容 API：

- `OPENAI_API_KEY`
- `SUMMARY_API_URL`
- `SUMMARY_API_MODEL`

这些都属于本机/用户配置，保留在环境变量或 `.env`。API key 不进入 `.local/runtime.json`。

未设置 key 时，转录照常完成，摘要保留占位符，可用：

```text
python <skill_dir>/scripts/fill_summaries.py
```

后续补全。

## 依赖

基础依赖：

- Python
- `yt-dlp`
- `ffmpeg`
- `requests`
- Bash（当前单视频底层引擎仍为 Bash；Windows 可用 Git Bash）

Whisper fallback 需要 Skill `.venv` 安装 `openai-whisper`。不要假定 `.venv/bin/python3` 在 Windows 也成立；Python 入口负责优先使用当前解释器，涉及 venv 的旧 Bash 路径若失败，应按当前机器重新 discovery 并把可执行 locator 写 local runtime，而不是把 Windows 路径补进中央 Skill。

## Cookie

Cookie 仅用于提高 B站 AI 字幕获取成功率。

- Cookie 本体绝不进入 `.local`、日志或提交。
- 浏览器类型可缓存；浏览器 profile 位置属于机器事实，如果后续把 profile discovery 独立出来，也应缓存 locator 而不是写中央绝对路径。
- 没 Cookie 时允许继续尝试公开 CC/下载/Whisper，不要因为 Cookie 缺失直接终止所有流程。

## 数据模型

SQLite 是数据源，TXT 是展示层：

- `scripts/transcript_db.py` 使用本地 `db_path`；
- `render_txt()` 默认使用本地 `output_dir`；
- 同一 BV 重跑按 `bvid` upsert；
- 输出按发布日期年/月组织。

## Guardrails

- 不把 API key、Cookie、token 写进 `.local`。
- 不把本机 home、OpenClaw 路径、WSL distro 名写回本 SKILL。
- 本地缓存与实际失败冲突时，以实际输出为准，更新缓存。
- 外部命令第一次跑通后缓存 locator，后续不要重新全盘搜索。
- 转录只负责产出转录/摘要/数据库记录；不要自动安装别的 RAG Skill，除非用户明确要求。
