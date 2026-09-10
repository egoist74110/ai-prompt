---
name: bilibili-auto-transcript
version: "6.0.0"
description: "Transcribe Bilibili videos or favorites. Prefer human CC, then AI subtitles, then Whisper. Cache machine paths, Bash, output/database locations, and favorite IDs in .local to avoid repeated macOS/Windows/WSL discovery."
---

# Bilibili Auto Transcript

Handle single-video transcription and favorite-list batch scanning. Keep only portable workflow here; machine paths/runtime locators belong in `.local/runtime.json`.

## Priority

1. Current environment/session facts.
2. Cached `.local/runtime.json` `skills.bilibili-auto-transcript` config.
3. First-use discovery.
4. Cache verified discovery immediately and reuse it.

Secrets remain in environment variables or this skill's gitignored `.env`. NEVER store API keys/cookies in `.local`.

## Local configuration

Resolve through `scripts/runtime_config.py`:

```text
python <skill_dir>/scripts/runtime_config.py show
```

Expected shape:

```json
{"skills":{"bilibili-auto-transcript":{"state_dir":"<machine path>","output_dir":"<machine path>","db_path":"<machine path>","bash":"<resolved bash executable>","browser_type":"chromium","favorite_media_id":"<non-secret id>"}}}
```

Temporary overrides: `BILIBILI_STATE_DIR`, `BILIBILI_OUTPUT_DIR`, `BILIBILI_DB_PATH`, `BILIBILI_BASH`, `BILIBILI_BROWSER`, `FAV_MEDIA_ID`.

On first run, legacy OpenClaw state, `~/workspace/knowledge/bilibili`, or old `.db/transcripts.db` may be reused and cached if present. New machines default under `AI_PROMPT_ROOT/.local/skills/bilibili-auto-transcript/`; do not create OpenClaw-specific paths.

## Single video

Call the Python entrypoint, not Bash directly:

```text
python <skill_dir>/scripts/run_transcript.py "https://www.bilibili.com/video/BVxxxx/"
python <skill_dir>/scripts/run_transcript.py "<url>" --output "<dir>" --browser chromium
```

`run_transcript.py` MUST reuse cached Bash/output/browser locators, discover Bash once if missing, pass runtime config to the legacy Bash engine, and report missing Bash on pure Windows rather than pretending success.

Transcription priority: human CC → Bilibili AI subtitles → local Whisper ASR.

Whisper model selection may adapt to GPU/VRAM/video length; do not rediscover installation paths every run.

## Favorite-list batch mode

```text
python <skill_dir>/scripts/bilibili_scanner.py
python <skill_dir>/scripts/batch_transcribe.py
```

`FAV_MEDIA_ID` may be cached as non-secret local config after first resolution. Batch state, processed list, CSV reports, and logs share `state_dir`; SQLite uses `db_path`; rendered output uses `output_dir`.

## Summaries

When configured, use OpenAI-compatible summary settings from `OPENAI_API_KEY`, `SUMMARY_API_URL`, and `SUMMARY_API_MODEL`. Keep them in environment/`.env`; never store the key in `.local/runtime.json`.

Without a key, transcription still completes. Fill summary placeholders later with:

```text
python <skill_dir>/scripts/fill_summaries.py
```

## Dependencies

Base: Python, `yt-dlp`, `ffmpeg`, `requests`, Bash. Whisper fallback requires `openai-whisper` in the skill `.venv`.

Never assume `.venv/bin/python3` exists on Windows. If a legacy Bash venv locator fails, rediscover for the current machine and cache the executable locator locally instead of adding Windows-specific paths here.

## Cookies

- Never store cookie contents in `.local`, logs, or commits.
- Browser type may be cached; browser profile location is a machine fact.
- Without cookies, continue with public CC/download/Whisper paths instead of aborting the workflow.

## Data model

SQLite is the source of truth; TXT is presentation output. `scripts/transcript_db.py` uses local `db_path`; `render_txt()` uses local `output_dir`; reprocessing the same BV upserts by `bvid`; organize output by publication year/month.

## Guardrails

- Never write API keys, cookies, or tokens to `.local`.
- Never write machine home paths, OpenClaw paths, or WSL distro names into this SKILL.
- If cache conflicts with real execution failure, trust execution and refresh cache.
- Cache external-command locators after first verified success; do not repeatedly scan the machine.
- Produce transcripts, summaries, and database records only. Do not install unrelated RAG skills unless explicitly requested.
