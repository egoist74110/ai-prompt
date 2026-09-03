# Bilibili Auto Transcript

> B站视频一键转录，CC / AI 字幕 / Whisper 三级降级，支持收藏夹自动监控。

基于 OpenClaw / Hermes 的转录技能，手动挡发链接即转，自动挡定时扫描收藏夹。

[![ClawHub](https://img.shields.io/badge/ClawHub-bilibili--auto--transcript-FB7299)](https://clawhub.ai/54lynnn/bilibili-auto-transcript)
[![GitHub](https://img.shields.io/badge/GitHub-54Lynnn%2Fbilibili--auto--transcript-181717)](https://github.com/54Lynnn/bilibili-auto-transcript)

---

## 安装

### OpenClaw（虾）
```bash
clawhub install bilibili-auto-transcript
```

### Hermes（马）
把 ClawHub 链接扔给 Hermes agent，让它做个能跑的版本。

---

## 功能

- 🔗 **手动挡** — 发链接给 AI 立即转录
- 📂 **自动挡** — 定时扫描收藏夹，新视频自动转录
- 🤖 **AI 摘要** — 自动生成结构化摘要
- 📄 **完整 TXT** — 视频信息 + 摘要 + 原文
- 🔄 **三级降级** — CC 字幕 → AI 字幕 → Whisper

---

## 搭配使用

转录后的 TXT 文件会自动进入 [Knowledge RAG](https://clawhub.ai/54lynnn/knowledge-rag) / [GitHub](https://github.com/54Lynnn/knowledge-rag) 的知识库，随时搜索视频内容。

---

## 依赖

- yt-dlp
- ffmpeg
- Ollama（可选，仅 Whisper 模式需要）

---

## 交流

💬 QQ 群：**120363664**（欢迎扫码加入交流）

---

## 许可证

MIT
