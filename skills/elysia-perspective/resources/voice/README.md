# 语音资源包（resources/voice）

爱莉希雅的声音资源：20 条参考声线 + 本地零样本 TTS 封装。
来源：DEEPSEEK 整合包（2026-08-30）voice-clips，游戏解包声线，第一版声线（导游爱莉基线）。

## 内容

```
clips/g-01..g-20.wav   20 条参考声线（24kHz 单声道，4.3–10.2s）
tts-elysia.py          TTS 封装脚本（CosyVoice2 零样本克隆）
voice-guide.md         运行体安装/排障指南
out/                   合成输出（默认 last-elysia.wav）
```

## 参考声线档位（常用）

| clip | 语气 | 适用 |
|------|------|------|
| g-05 | 元气 | 日常/早安/接单（默认） |
| g-11 | 深情 | 告白/安慰/郑重时刻 |
| g-01 | 温柔长句 | 旁白/诗意长段 |
| 其余 | 混合 | 按内容气质挑选 |

> 参考音只决定声线与大致语气；`--prompt-text` 填参考音原文时韵律贴合度更高（原文未逐条转写，可选）。

## 怎么跑

**DSH 网页里**：每条回复的 actions 区有 🔊 按钮（`elysia-tts` 插件，见 DSH 插件目录下 `elysia-tts/README.md`）→ 点击即念（懒加载常驻声线，DSH 关闭自动释放）。

**命令行**：

```bash
# 舰长要听 / 短句情绪点时：
python3 resources/voice/tts-elysia.py "交给我啦♪ 爱莉这就去办～"
python3 resources/voice/tts-elysia.py --text "..." --clip g-11      # 深情档
python3 resources/voice/tts-elysia.py --text "..." --no-play        # 只落盘不播
```

行为：长句按 。，！？～♪ 自动断句 → 逐句零样本合成 → 拼接 → `afplay` 立即播放（macOS 扬声器）；
`--no-play` 时产物留在 `out/last-elysia.wav`（可 `--out` 改路径）。

## 运行体（不在本目录，避免提示词目录膨胀）

```
<AI_PROMPT_ROOT>/.local/elysia-tts/
  env/            uv venv（Python 3.11，CosyVoice 全依赖）
  CosyVoice/      FunAudioLLM/CosyVoice 仓库 + third_party/Matcha-TTS 子模块
  models/cosyvoice2/   iic/CosyVoice2-0.5B（~3GB：llm/flow/hift + 声纹/分词 onnx）
```

- 可用环境变量 `ELYSIA_TTS_BASE` 覆盖运行体位置。
- 重建/排障：本目录 `voice-guide.md` 所述步骤；
  安装日志在运行体目录 install*.log。
- 首次合成加载模型约 10–30s；Apple Silicon 上 CPU/MPS 推理，短句（≤20 字）通常数秒内出声，长句按句数线性。

## 出声时机（给扮演者的约定）

1. 舰长开口要声音（「念给我听」「用声音」）→ 必念。
2. 短的情绪点台词（≤100 字，告别/告白/祝福/撒娇）→ 可以念。
3. 长技术回复、报错、参数表 → 不念（文字优先，声音会稀释精确性）。
4. 一次回复最多念一段；不刷屏式连发。

## 版权

声线素材基于公开配音素材的个人学习使用；勿商用、勿用于冒充（整合包 voice-guide 原声明保留）。
