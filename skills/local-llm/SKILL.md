---
name: local-llm
description: Call the user's self-hosted OpenAI-compatible endpoint (base URL + key kept in a git-ignored local .env): list models, chat, generate images/video/speech, transcribe audio. Use when the user asks to use the local/own model, or to generate image/video/audio through it.
credentials:
  - name: LOCAL_LLM_BASE_URL / LOCAL_LLM_API_KEY
    required: true
    description: "Endpoint (ending in /v1) and API key. Stored only in skills/local-llm/.env (git-ignored) or environment variables."
    storage: "skills/local-llm/.env, never committed"
---

# local-llm

Thin CLI over an OpenAI-compatible server. Stdlib Python only.

## Config (once)

Copy `.env.example` to `.env` in this skill dir and fill `LOCAL_LLM_BASE_URL` and `LOCAL_LLM_API_KEY`. Environment variables of the same name override `.env`. If either is missing the script exits with code 2 and says so: tell the user to fill it; never ask them to paste the key in chat, never echo it, never write the URL/key into any tracked file.

## Use

```text
python <skill_dir>/scripts/llm.py models                       # discover what the server supports first
python <skill_dir>/scripts/llm.py chat "prompt" [-m MODEL] [-s SYSTEM]
python <skill_dir>/scripts/llm.py image "prompt" [-m MODEL] [--size 1024x1024] [-n 1]
python <skill_dir>/scripts/llm.py speech "text" [-m MODEL] [--voice alloy] [--format mp3]
python <skill_dir>/scripts/llm.py transcribe FILE [-m MODEL]
python <skill_dir>/scripts/llm.py video "prompt" [-m MODEL] [--seconds 5] [--size 1280x720]
python <skill_dir>/scripts/llm.py raw METHOD /path [--json '{...}']   # any other endpoint
```

- Run `models` first and pick model ids from it; capabilities depend on the server. A 404/400 on an endpoint means unsupported: report it, don't fake it.
- Binary outputs are saved to `~/Downloads` by default (override with `LOCAL_LLM_OUT_DIR`), or `-o PATH`; the script prints the saved path(s).
- `video` uses the OpenAI `/videos` job API (create, poll, download). Servers with a different video API: use `raw`.
- TTS: use `-m Comfy-anomalous-tts --voice <角色名>` (e.g. `--voice 伊莉雅`); the `TTS-*` entries in `models` returned 502 and `--voice` defaults to `alloy`, which this server rejects. Image: `response_format=b64_json` is the default, otherwise the server returns unreachable internal URLs.
- TTS language check (mandatory): each voice speaks one language only (伊莉雅 = Japanese; names with 中文/_ZH = Chinese; others such as 小黑/美游 are unconfirmed). Before calling `speech`, confirm the voice's language with the user if unknown, and write the text in that language (translate if needed, tell the user). The script refuses mismatches; `--force-lang` bypasses it only when the user said so. To record a confirmed voice, add it to `VOICE_LANG` in `scripts/llm.py`.
- HTTP errors print status and body (the key is never printed).
- After generating a file, ALWAYS surface it in the Claude conversation: call `SendUserFile` with the printed path(s) (`display: "render"` for images/audio/video the user should see or hear now). Reading the file yourself is not enough, the user cannot see it. Never say the file is done without sending it. The app's file pane only opens files inside the session's folders: if the pane says the file is outside the session, call `request_directory` for the output folder (e.g. `~/Downloads`) once, then resend.
