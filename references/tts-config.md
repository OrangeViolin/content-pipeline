# IndexTTS2 本地 TTS 配置

> 开源零样本语音克隆，MIT 协议，本地运行，免费。

---

## 配置

| 参数 | 值 |
|------|-----|
| 仓库 | [index-tts/index-tts](https://github.com/index-tts/index-tts) |
| 安装目录 | `~/index-tts`（或自定义，在 `local/.env` 中配置 `INDEXTTS_DIR`） |
| 推理入口 | `indextts.infer_v2.IndexTTS2` |
| 参考音频 | 2-10 秒清晰人声，WAV 格式，单声道 24kHz |
| 输出格式 | WAV（可用 ffmpeg 转 MP3） |

---

## 安装（一次性）

```bash
# 前置依赖
brew install git-lfs
git lfs install

# 克隆仓库
git clone https://github.com/index-tts/index-tts.git ~/index-tts
cd ~/index-tts

# 安装（只用 uv，不要用 pip）
uv sync --all-extras

# 下载模型
uv run huggingface-cli download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

> 踩坑提示：`infer.py` 导入的是 v1 模型类，但 checkpoint 是 v2。必须用 `infer_v2.py` 的 `IndexTTS2` 类。

---

## 参考音频准备

```bash
# 从你的录音中截取 8 秒（跳过开头静音）
ffmpeg -i 你的录音.mp3 -ss 5 -t 8 -ac 1 -ar 24000 voice_ref.wav -y
```

参考音频路径配置在 `local/.env` 中：
```
VOICE_REF=/path/to/your/voice_ref.wav
INDEXTTS_DIR=/path/to/index-tts
```

---

## 分段策略

- 单次推理最大 **300 字**（Apple Silicon 上更短分段效果更好）
- 按段落边界（`\n\n`）分割
- 逐段生成 WAV，拼接后转 MP3

---

## 生成脚本

```python
#!/usr/bin/env python3
import os, sys, time, wave

sys.path.insert(0, os.environ.get("INDEXTTS_DIR", os.path.expanduser("~/index-tts")))
os.chdir(os.environ.get("INDEXTTS_DIR", os.path.expanduser("~/index-tts")))

from indextts.infer_v2 import IndexTTS2

VOICE_REF = os.environ.get("VOICE_REF", "/tmp/voice_ref.wav")

def split_text(text, max_chars=300):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars and current:
            chunks.append(current.strip())
            current = p
        else:
            current += "\n\n" + p if current else p
    if current.strip():
        chunks.append(current.strip())
    return chunks

def concat_wavs(wav_files, output_path):
    with wave.open(wav_files[0], "r") as w:
        params = w.getparams()
    all_frames = b""
    for wf in wav_files:
        with wave.open(wf, "r") as w:
            all_frames += w.readframes(w.getnframes())
    with wave.open(output_path, "w") as out:
        out.setparams(params)
        out.writeframes(all_frames)

def generate_podcast(script_path: str, output_path: str):
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    chunks = split_text(text)
    print(f"Loading IndexTTS2 model...")
    tts = IndexTTS2(model_dir="checkpoints", cfg_path="checkpoints/config.yaml")

    wav_parts = []
    for i, chunk in enumerate(chunks):
        part_path = f"/tmp/_tts_part_{i:03d}.wav"
        print(f"  [{i+1}/{len(chunks)}] ({len(chunk)} chars)...")
        tts.infer(VOICE_REF, chunk, part_path)
        wav_parts.append(part_path)

    concat_wavs(wav_parts, output_path)
    for p in wav_parts:
        os.remove(p)
    print(f"Audio saved: {output_path}")
```

---

## 性能参考（Apple Silicon）

| 参数 | 值 |
|------|-----|
| 模型加载（首次） | ~4 分钟 |
| 模型加载（缓存后） | ~26 秒 |
| 生成速度 | ~10x RTF（1 秒音频需 10 秒计算） |
| 15 分钟播客 | ~27 分钟生成 |
| 输出质量 | 22kHz，16bit mono |

---

## 故障处理

| 问题 | 处理 |
|------|------|
| `emo_condition_module` 报错 | 用 `infer_v2.py` 的 `IndexTTS2`，不是 `infer.py` 的 `IndexTTS` |
| `Missing key bigvgan` | 同上，v1/v2 不兼容 |
| 参考音频生成静音 | 检查参考音频是否有声音（振幅 > 1000），跳过开头静音段 |
| 生成太慢 | 减小分段大小到 200 字；或考虑使用 NVIDIA GPU 机器 |
| 模型下载失败 | 检查 HuggingFace 网络连接，或用镜像 `HF_ENDPOINT=https://hf-mirror.com` |
