# Content Pipeline — Claude Code 内容生产管线

一句话给 Claude Code，从素材到多平台发布全自动。

```
素材/文章/书籍 → 写稿 → 排版 → 封面 → 小红书 → 即刻 → 播客 → 视频 → 一键发布
```

## 它能干什么

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 写文章 | 从素材自动出稿，支持说明书/教程/深度长文三种框架 | `出稿` |
| 公众号排版 | Markdown → 微信公众号 HTML，带品牌主题 | `排版` |
| 封面图 | 头图 + 配图 + 竖版封面，HTML 一键导出 PNG | `做头图`、`做配图` |
| 微信 → 小红书 | 公众号文章自动转 8-10 张轮播图 | `/xiaohongshu` + 链接 |
| 微信 → 即刻 | 自动生成即刻文案 | `转即刻` + 链接 |
| 微信 → 播客 | 生成播客脚本 + AI 语音（声音克隆） + 封面 | `转播客`、`/podcast` |
| 录屏画布 | 全屏网页演示 + 摄像头露脸 + 提词器 + 录制 | `做视频画布` |
| 一键发布 | Chrome CDP 自动化，全平台分发 | `/distribute` |

### 支持平台

| 平台 | 方式 | 状态 |
|------|------|------|
| 公众号 | API 直推草稿箱 | 可用 |
| 小红书 | Chrome CDP 自动化 | 可用 |
| 即刻 | Chrome CDP 自动化 | 可用 |
| 小宇宙（播客） | Chrome CDP 自动化 | 可用 |
| 抖音 | Chrome CDP 自动化 | 实验性 |
| 视频号 | — | 待开发 |

---

## 快速开始

### 1. 克隆到 Claude Code 技能目录

```bash
git clone https://github.com/OrangeViolin/content-pipeline.git ~/.claude/skills/content-pipeline
```

### 2. 配置私有信息

```bash
# 创建本地配置目录（已被 .gitignore 排除，不会上传）
mkdir -p ~/.claude/skills/content-pipeline/local

# 复制环境变量模板
cp ~/.claude/skills/content-pipeline/.env.example ~/.claude/skills/content-pipeline/local/.env
```

编辑 `local/.env`，填入你的密钥：

```bash
# 播客语音生成（Fish Audio）
FISH_API_KEY=你的_Fish_Audio_API_Key

# 公众号 API（可选，用于自动推送草稿箱）
WECHAT_APPID=你的_AppID
WECHAT_APPSECRET=你的_AppSecret

# 排版工具路径（可选）
MD_FORMATTER_DIR=/path/to/your/md-formatter
```

### 3. 个性化配置（可选）

创建 `local/SKILL.local.md` 覆盖默认设定：

```markdown
# 本地覆盖配置

## 存储位置
默认输出目录：`/your/output/path/`

## 个人信息
- 微信号：你的微信号
- 品牌色文档路径：/path/to/your/brand-colors.md

## TTS 声音
在 local/.env 中配置 Voice ID（Fish Audio 控制台获取）
```

### 4. 开始使用

在 Claude Code 中直接说：

```
"出稿"          → 从积累的素材生成文章
"排版"          → Markdown 转公众号 HTML
"/podcast" + 文章  → 生成 15 分钟播客（脚本+AI语音+封面）
"/distribute"    → 一键发布到所有平台
```

---

## 两条工作流

### Path A：日常素材积累 → 出稿

```
日常对话中自动记录有料瞬间 → 说"出稿" → 自动写文章 → 排版 → 封面 → 朋友圈文案
```

CC 在和你聊天的过程中会自动识别"有料时刻"（踩坑、意外发现、突破、搞笑）并记录。攒够了说一句"出稿"，一键生成完整文章。

### Path B：微信文章 → 多平台内容

```
微信链接 → 抓取文章 → 自动生成小红书/即刻/播客/视频 → manifest → 一键分发
```

一篇公众号文章，自动转为 5 种平台内容：

1. 小红书轮播图 HTML（8-10 张卡片）
2. 小红书发布文案
3. 即刻发布文案
4. 小宇宙播客（脚本 + AI 语音 + 封面）
5. manifest.json（供一键发布使用）

---

## 播客功能详解

### 两种模式

| 模式 | 触发词 | 时长 | 风格 |
|------|--------|------|------|
| 标准 | `转播客` | 5-8 分钟 | AI 搭档聊天风 |
| 百家讲坛 | `/podcast`、`做播客` | 15 分钟 | 讲书人，抑扬顿挫 |

### AI 语音生成

支持两种 TTS 引擎：

| | Fish Audio | IndexTTS2 |
|---|---|---|
| 费用 | 按量付费 API | 免费，本地运行 |
| 网络 | 必须联网 | 离线可用 |
| 速度 | 快（云端 GPU） | 慢（Apple Silicon ~10x RTF） |
| 克隆 | 需上传训练 | 2-10 秒参考即可 |
| 配置 | `local/.env` 中的 `FISH_API_KEY` | 本地安装 [IndexTTS2](https://github.com/index-tts/index-tts) |

### 子栏目支持

可以为特定内容系列创建子栏目品牌（如"史记罗生门"），独立的视觉风格、脚本模板、标题规范。参见 `references/shiji-luoshengmen.md` 作为示例。

---

## 项目结构

```
content-pipeline/
├── SKILL.md                       # 主技能定义（Claude Code 读取）
├── README.md                      # 本文件
├── .env.example                   # 环境变量模板
├── .gitignore                     # 排除 local/ 和 .env
│
├── local/                         # 🔒 私有配置（不上传 GitHub）
│   ├── SKILL.local.md             #    个人覆盖（路径、微信号、品牌色）
│   └── .env                       #    API 密钥
│
├── references/                    # 模板和规范文档
│   ├── writing-style.md           #    写作风格指南（逆向工程自真实文章）
│   ├── tutorial-framework.md      #    教程类文章框架
│   ├── manual-framework.md        #    说明书类文章框架
│   ├── cover-template.md          #    封面图设计规范
│   ├── cover-vertical-spec.md     #    竖版封面转换规范
│   ├── xiaohongshu-format.md      #    小红书轮播图 HTML 模板
│   ├── platform-copy.md           #    各平台文案规范
│   ├── tts-config.md              #    Fish Audio TTS 配置
│   ├── xiaoyuzhou-podcast.md      #    小宇宙播客脚本规范（百家讲坛风格）
│   ├── podcast-cover-template.md  #    播客封面 HTML 模板
│   ├── shiji-luoshengmen.md       #    史记罗生门栏目品牌设定（子栏目示例）
│   ├── distribute-platforms.md    #    多平台分发配置
│   ├── video-canvas-template.md   #    录屏画布模板
│   └── xiaohongshu-examples/      #    小红书范例文件
│
└── scripts/                       # 自动化脚本
    ├── fetch_wechat_article.py    #    微信文章抓取
    └── distribute/                #    多平台分发
        ├── distribute.ts          #    分发主编排器
        ├── cdp-utils.ts           #    Chrome DevTools Protocol 工具
        ├── wechat-api.ts          #    公众号 API 客户端
        └── platforms/             #    各平台发布模块
            ├── wechat.ts
            ├── xiaohongshu.ts
            ├── jike.ts
            ├── xiaoyuzhou.ts
            ├── douyin.ts
            └── shipinhao.ts
```

---

## 隐私安全

以下内容 **不会** 上传到 GitHub：

| 内容 | 位置 | 保护方式 |
|------|------|---------|
| API 密钥（Fish Audio、微信） | `local/.env` | `.gitignore` 排除 `local/` |
| 个人信息（微信号、路径） | `local/SKILL.local.md` | `.gitignore` 排除 `local/` |
| 声音模型 ID | `local/.env` | `.gitignore` 排除 `local/` |
| Token 缓存 | `token-cache.json` | `.gitignore` 单独排除 |

`references/` 目录中的模板使用 `YOUR_VOICE_ID_HERE` 等占位符，不含实际密钥。

---

## 自定义品牌

默认使用 01fish 品牌色作为示例。你可以替换为自己的品牌：

1. 修改 `references/cover-template.md` 中的色值
2. 修改 `references/xiaohongshu-format.md` 中的卡片样式
3. 在 `local/SKILL.local.md` 中指定你的品牌色文档路径

---

## 许可

MIT
