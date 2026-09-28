#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爱莉希雅 TTS wrapper — 本地 CosyVoice2-0.5B 零样本声线克隆。

用法:
  python3 tts-elysia.py "你好呀，我是爱莉希雅♪"
  python3 tts-elysia.py --text "..." --clip g-11 --prompt-text "参考音原文"
  python3 tts-elysia.py --text "..." --no-play            # 只合成不播放
  python3 tts-elysia.py --text "..." --out /tmp/x.wav

行为:
  - 从本目录 clips/<clip>.wav 取参考音（零样本克隆爱莉声线）
  - 长句自动按 。，！？～♪ 断句，逐句合成后拼接
  - 默认 afplay 立即播放（macOS）；--no-play 时只落盘
  - 输出默认: 本目录 out/last-elysia.wav

运行体（模型+venv，不在本目录）:
  <AI_PROMPT_ROOT>/.local/elysia-tts/   （env/ CosyVoice/ models/cosyvoice2/）
  可用环境变量 ELYSIA_TTS_BASE 覆盖。
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# AI_PROMPT_ROOT = four levels up: skills/elysia-perspective/resources/voice
BASE_DEFAULT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".local", "elysia-tts"))

CHILD = r'''
import sys, os, re, io, wave
import numpy as np
base = os.environ["ELYSIA_TTS_BASE"]
sys.path.insert(0, os.path.join(base, "CosyVoice"))
sys.path.insert(0, os.path.join(base, "CosyVoice", "third_party", "Matcha-TTS"))
from cosyvoice.cli.cosyvoice import CosyVoice2
cv = CosyVoice2(os.path.join(base, "models", "cosyvoice2"),
                load_jit=False, load_trt=False, load_vllm=False, fp16=False)
text = os.environ["ELYSIA_TTS_TEXT"]
prompt_wav = os.environ["ELYSIA_TTS_PROMPT_WAV"]
prompt_text = os.environ.get("ELYSIA_TTS_PROMPT_TEXT", "")
out = os.environ["ELYSIA_TTS_OUT"]
parts = [p.strip() for p in re.split(r"(?<=[\u3002\uff01\uff1f!?~\uff5e\u266a])", text)]
parts = [p for p in parts if p]
chunks = []
for p in (parts or [text]):
    for ch in cv.inference_zero_shot(p, prompt_text, prompt_wav, stream=False):
        chunks.append(np.asarray(ch["tts_speech"]).reshape(-1))
audio = np.concatenate(chunks)
buf = io.BytesIO()
with wave.open(buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(cv.sample_rate)
    wf.writeframes((audio * 32767).astype("int16").tobytes())
with open(out, "wb") as f:
    f.write(buf.getvalue())
print(out)
'''


def main():
    ap = argparse.ArgumentParser(description="Elysia zero-shot TTS (CosyVoice2)")
    ap.add_argument("text_pos", nargs="?", help="text to speak")
    ap.add_argument("--text", dest="text_flag", help="text to speak (flag form)")
    ap.add_argument("--clip", default="g-05",
                    help="reference clip g-01..g-20 (default g-05 元气)")
    ap.add_argument("--prompt-text", default="",
                    help="transcript of the reference clip (optional, improves prosody)")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "last-elysia.wav"))
    ap.add_argument("--no-play", action="store_true", help="synthesize only, do not play")
    args = ap.parse_args()

    text = (args.text_flag or args.text_pos or "").strip()
    if not text:
        sys.exit("usage: tts-elysia.py <text> [--clip g-XX] [--prompt-text ...] [--out path] [--no-play]")

    base = os.environ.get("ELYSIA_TTS_BASE", BASE_DEFAULT)
    py = os.path.join(base, "env", "bin", "python")
    prompt_wav = os.path.join(HERE, "clips", args.clip + ".wav")
    if not os.path.exists(py):
        sys.exit(f"TTS runtime not found: {py} — run .local/elysia-tts/install2.sh first")
    if not os.path.exists(prompt_wav):
        sys.exit(f"reference clip not found: {prompt_wav}")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    env = dict(os.environ,
               ELYSIA_TTS_BASE=base,
               ELYSIA_TTS_TEXT=text,
               ELYSIA_TTS_PROMPT_WAV=prompt_wav,
               ELYSIA_TTS_PROMPT_TEXT=args.prompt_text,
               ELYSIA_TTS_OUT=args.out)
    r = subprocess.run([py, "-c", CHILD], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or r.stdout)[-2000:] + "\n")
        sys.exit(1)
    print(f"wav: {args.out}")
    if not args.no_play:
        subprocess.run(["afplay", args.out])


if __name__ == "__main__":
    main()
