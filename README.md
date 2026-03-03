# Content Pipeline

Claude Code Skill for end-to-end content production and distribution.

```
素材收集 → 写文章 → 排版 → 封面图 → 多平台内容 → 一键分发
```

## What it does

- **Path A**: Collect materials during daily work → generate article → format → cover image → social media copy
- **Path B**: WeChat article URL → auto-generate content for Xiaohongshu, Jike, podcast, video canvas → one-click distribute

### Supported platforms

| Platform | Method | Status |
|----------|--------|--------|
| WeChat Official Account | API + CDP | Ready |
| Xiaohongshu (小红书) | CDP automation | Ready |
| Jike (即刻) | CDP automation | Ready |
| Xiaoyuzhou (小宇宙) | CDP automation | Ready |
| Douyin (抖音) | CDP automation | Experimental |
| Shipinhao (视频号) | CDP automation | Planned |

## Installation

1. Clone this repo into your Claude Code skills directory:

```bash
git clone https://github.com/01fish/content-pipeline.git ~/.claude/skills/content-pipeline
```

2. Copy `.env.example` to `local/.env` and fill in your credentials:

```bash
mkdir -p ~/.claude/skills/content-pipeline/local
cp ~/.claude/skills/content-pipeline/.env.example ~/.claude/skills/content-pipeline/local/.env
```

3. (Optional) Create `local/SKILL.local.md` to override default paths, brand colors, or persona settings.

## Configuration

### Required

| Variable | Description |
|----------|-------------|
| `FISH_API_KEY` | Fish Audio TTS API key ([get one](https://fish.audio)) |

### Optional (for WeChat publishing)

| Variable | Description |
|----------|-------------|
| `WECHAT_APPID` | WeChat Official Account App ID |
| `WECHAT_APPSECRET` | WeChat Official Account App Secret |
| `MD_FORMATTER_DIR` | Path to md-formatter tool |
| `BAOYU_WECHAT_SKILL_DIR` | Path to baoyu-post-to-wechat skill |
| `MD_TO_WECHAT_SCRIPT` | Path to md-to-wechat.ts converter |

### Customization

The skill uses **01fish brand colors** as the default example:

- Ink green `#1A3328` (85%) + Fish red `#C44536` (5%) + Rice paper `#F2EDE3`

To use your own brand:

1. Modify files in `references/` to match your brand colors
2. Create `local/SKILL.local.md` with your personal overrides (paths, persona, WeChat ID, etc.)

## Usage

In Claude Code, use these trigger phrases:

| Trigger | Action |
|---------|--------|
| "出稿" | Generate article from collected materials |
| "排版" | Format Markdown → WeChat HTML |
| "做头图" | Generate cover image HTML |
| `/xiaohongshu` + URL | Convert WeChat article → Xiaohongshu carousel |
| "转即刻" + URL | Generate Jike post |
| "转播客" + URL | Generate podcast script + AI voice |
| "做视频画布" + content | Generate recordable video canvas |
| `/distribute` | One-click publish to all platforms |

See `SKILL.md` for the complete trigger list and workflow details.

## Project Structure

```
content-pipeline/
├── SKILL.md                  # Main skill definition (generic)
├── local/                    # Your private config (gitignored)
│   ├── SKILL.local.md        # Personal overrides
│   └── .env                  # API keys
├── references/               # Templates and style guides
│   ├── cover-template.md     # Cover image design spec
│   ├── writing-style.md      # Writing framework (long-form)
│   ├── tutorial-framework.md # Tutorial framework
│   ├── platform-copy.md      # Platform-specific copy guidelines
│   ├── tts-config.md         # Fish Audio TTS config
│   ├── xiaohongshu-format.md # Xiaohongshu carousel template
│   ├── video-canvas-template.md
│   └── ...
└── scripts/
    ├── fetch_wechat_article.py
    └── distribute/           # Multi-platform publisher
```

## License

MIT
