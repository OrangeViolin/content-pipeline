# Fish Audio TTS 配置

> 来源：wechat-to-xiaohongshu skill 的 TTS 部分

---

## 配置

| 参数 | 值 |
|------|-----|
| API 地址 | `https://api.fish.audio/v1/tts` |
| API Key | 环境变量 `FISH_API_KEY`（在 `local/.env` 中配置） |
| Voice ID | `5ff3a1267d6b4677872a9f3331c1a7a2`（鱼头的声音模型） |
| 输出格式 | MP3 |

---

## 分段策略

- 单次请求最大 **800 字**
- 按段落边界（`\n\n`）分割
- 逐段请求 TTS，拼接 MP3 数据

---

## 生成脚本

使用 Python + httpx 直接调用 HTTP API（不使用 fish-audio-sdk，因为有架构兼容问题）。

```python
#!/usr/bin/env python3
import httpx, os

API_KEY = os.environ.get("FISH_API_KEY", "")
VOICE_ID = "5ff3a1267d6b4677872a9f3331c1a7a2"

def generate_podcast(script_path: str, output_path: str):
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    # 分段
    MAX_CHARS = 800
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > MAX_CHARS and current:
            chunks.append(current.strip())
            current = p
        else:
            current += "\n\n" + p if current else p
    if current.strip():
        chunks.append(current.strip())

    # 逐段生成
    all_audio = b""
    client = httpx.Client(timeout=httpx.Timeout(120.0))
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}/{len(chunks)}] 生成中 ({len(chunk)} 字)...")
        r = client.post(
            "https://api.fish.audio/v1/tts",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"text": chunk, "reference_id": VOICE_ID, "format": "mp3", "latency": "balanced"},
        )
        if r.status_code == 200:
            all_audio += r.content
        else:
            print(f"    失败 (status {r.status_code}): {r.text}")
    client.close()

    with open(output_path, "wb") as f:
        f.write(all_audio)
    print(f"播客音频已生成: {output_path} ({len(all_audio)/(1024*1024):.1f} MB)")
```

---

## 故障处理

| 问题 | 处理 |
|------|------|
| 402 余额不足 | 提示用户去 fish.audio 充值 |
| 401 Key 无效 | 提示用户检查 API Key |
| 超时 | 增加 timeout 到 180s，或减小分段大小 |
| 生成失败 | 只输出脚本文本，提示用户手动录制或稍后重试 |
