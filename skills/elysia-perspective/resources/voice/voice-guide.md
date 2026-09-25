# 语音运行体安装/排障指南（macOS 适配版）

运行体位置：`<AI_PROMPT_ROOT>/.local/elysia-tts/`（`AI_PROMPT_ROOT` = router.md 所在目录）（以下 `$BASE`）。
引擎：CosyVoice2-0.5B（FunAudioLLM），零样本声线克隆，离线、本地推理。

## 从零重建（2026-09-14 在本机验证过的路径）

```bash
BASE="<AI_PROMPT_ROOT>/.local/elysia-tts"   # 替换为 router.md 所在目录
mkdir -p $BASE
uv venv $BASE/env --python 3.11
git clone --depth 1 https://github.com/FunAudioLLM/CosyVoice.git $BASE/CosyVoice
cd $BASE/CosyVoice
git submodule update --init --recursive          # third_party/Matcha-TTS（必须）

# ① 全部依赖（whisper 除外——见 ②）
grep -v '^openai-whisper' requirements.txt > /tmp/reqs-no-whisper.txt
uv pip install --python $BASE/env/bin/python --index-strategy unsafe-best-match -r /tmp/reqs-no-whisper.txt

# ② openai-whisper 需要老 setuptools 的 pkg_resources
uv pip install --python $BASE/env/bin/python pip "setuptools<81"
$BASE/env/bin/pip install --no-build-isolation openai-whisper==20231117

# ③ 模型（~3GB，ModelScope 国内源）
$BASE/env/bin/python -c "
from modelscope import snapshot_download
snapshot_download('iic/CosyVoice2-0.5B', local_dir='$BASE/models/cosyvoice2')"
```

踩坑记录（为什么长这样）：
- Python 3.13/3.14 下 matcha 系老 pin 编译失败 → 用 3.11。
- uv 默认 index 策略会被 requirements 里的 `--extra-index-url`（CUDA 源）带偏，
  onnxruntime==1.18.0 的 darwin wheel 只在 PyPI → 加 `--index-strategy unsafe-best-match`。
- openai-whisper==20231117 的 setup.py `import pkg_resources`，setuptools≥81 已移除
  → 先装 `setuptools<81` 再 `--no-build-isolation` 装 whisper。
- `import whisper` 在 `cosyvoice/tokenizer/tokenizer.py` 顶层，CLI 推理也绕不开，必须装。

## 排障

| 现象 | 处理 |
|------|------|
| `No module named 'cosyvoice'` | sys.path 要同时含 `$BASE/CosyVoice` 和 `$BASE/CosyVoice/third_party/Matcha-TTS`（tts-elysia.py 已处理） |
| 模型文件缺失 | 重跑 ③；目录里应有 `llm.pt flow.pt hift.pt cosyvoice2.yaml campplus.onnx speech_tokenizer_v2.onnx` |
| 合成很慢 | 正常：CPU/MPS + 0.5B，首次含模型加载 10–30s；保持运行体常驻可省加载（未做服务化，每次调用重新加载） |
| 声线不像 | 换参考 clip（g-01 温柔 / g-05 元气 / g-11 深情）；给 `--prompt-text` 参考音原文可提升韵律贴合 |
| 显存/内存 爆 | 0.5B 不会；若内存 紧张，避免并发调用 |

## 文件必要性（2026-09-14 实测）

CLI 单句合成（tts-elysia.py）只需要：`llm.pt` `flow.pt` `hift.pt` `campplus.onnx`
`speech_tokenizer_v2.onnx` `cosyvoice2.yaml` + `CosyVoice-BlankEN/`（config/vocab/merges/model.safetensors）。
`speech_tokenizer_v2.batch.onnx` 仅 fastapi runtime 批量推理用；`flow.cache.pt` / `flow.*.fp32.onnx` /
`flow.encoder.*.zip` 为加速/备用件，缺失不影响 CLI。整包 4.9GB，CLI 最小集 ≈ 3.5GB。

## 可选升级（未启用）

- 服务化：FastAPI 包一层 `inference_zero_shot`（CosyVoice repo 自带 `runtime/python/fastapi` 可参考），
  模型常驻、首句延迟降到 <1s；需要时才做。
- webui：`$BASE/env/bin/python $BASE/CosyVoice/webui.py --port 9880`（gradio 已装）。
