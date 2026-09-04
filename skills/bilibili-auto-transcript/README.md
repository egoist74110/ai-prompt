# Bilibili Auto Transcript

B站视频转录与收藏夹扫描：CC 字幕 → B站 AI 字幕 → Whisper 本地转录，并支持可选 AI 摘要。

## 当前架构

这个 Skill 已从 OpenClaw 专属目录迁成 ai-prompt 的 runtime/state 模式：

- Skill 代码位置由当前 `SKILL.md` 自身解析；
- 机器配置缓存到 `AI_PROMPT_ROOT/.local/runtime.json`；
- state/output/db/Bash/browser locator 不再写死；
- 旧 OpenClaw/旧 knowledge/db 目录存在时首次会自动复用并缓存，避免历史数据断开；
- API key/Cookie 等 secret 仍只放环境变量或 gitignored `.env`，不进 `.local`。

详细 Agent 规则见 `SKILL.md`。

## 快速开始

查看本机已解析配置：

```text
python <skill_dir>/scripts/runtime_config.py show
```

单视频：

```text
python <skill_dir>/scripts/run_transcript.py "https://www.bilibili.com/video/BVxxxxx/"
```

收藏夹扫描：

```text
python <skill_dir>/scripts/bilibili_scanner.py
```

批量转录：

```text
python <skill_dir>/scripts/batch_transcribe.py
```

`<skill_dir>` 表示当前这份 Skill 的实际目录，不要替换成某个固定 OpenClaw/Codex/Claude home。

## 依赖

- Python
- `yt-dlp`
- `ffmpeg`
- `requests`
- Bash（当前单视频底层引擎仍为 Bash；Windows 可使用 Git Bash）
- `openai-whisper`（只有字幕都拿不到时才需要）
- `python-dotenv`（使用 Skill `.env` 时）
- `opencc`（可选）

建议在 Skill 目录创建虚拟环境，但 venv 的可执行路径是机器事实；Windows/macOS/Linux 不共用固定 `.venv/bin/python3` 字符串。

## 配置

非 secret 的稳定设置可写/自动缓存到：

```text
.local/runtime.json -> skills.bilibili-auto-transcript
```

支持：`state_dir`、`output_dir`、`db_path`、`bash`、`browser_type`、`favorite_media_id`。

临时覆盖环境变量：

- `BILIBILI_STATE_DIR`
- `BILIBILI_OUTPUT_DIR`
- `BILIBILI_DB_PATH`
- `BILIBILI_BASH`
- `BILIBILI_BROWSER`
- `FAV_MEDIA_ID`

Secret/摘要配置继续用 `.env` 或环境变量：

- `OPENAI_API_KEY`
- `SUMMARY_API_URL`
- `SUMMARY_API_MODEL`

## 数据

- SQLite 是转录/摘要主数据源；
- TXT 是展示层；
- processed list、CSV report、log 统一属于本机 state；
- 输出默认按发布年月分目录；
- 同一 BV 按 `bvid` upsert。

## 目录

```text
bilibili-auto-transcript/
├── SKILL.md
├── README.md
├── .env.example
├── scripts/
│   ├── runtime_config.py
│   ├── run_transcript.py
│   ├── bilibili_scanner.py
│   ├── batch_transcribe.py
│   ├── bilibili_transcript.sh
│   ├── transcript_db.py
│   ├── generate_summary.py
│   ├── fill_summaries.py
│   └── logger.py
└── references/
```

机器生成的数据不应作为仓库内容提交。
