<div align="center">

<!-- Replace with actual banner image -->
<img src="./static/image/content-pipeline-banner.png" alt="01fish Content Pipeline" width="75%"/>

<br/>

**一句话给 AI，从素材到全平台发布，全自动。**

<em>One prompt to AI — from raw material to multi-platform publishing, fully automated.</em>

<br/>

[![GitHub Stars](https://img.shields.io/github/stars/OrangeViolin/content-pipeline?style=flat-square&color=1A3328)](https://github.com/OrangeViolin/content-pipeline/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/OrangeViolin/content-pipeline?style=flat-square)](https://github.com/OrangeViolin/content-pipeline/network)
[![License](https://img.shields.io/github/license/OrangeViolin/content-pipeline?style=flat-square&color=C44536)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-8A2BE2?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-Scripts-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)

[![WeChat](https://img.shields.io/badge/公众号-可用-07C160?style=flat-square&logo=wechat&logoColor=white)](#-支持平台)
[![Xiaohongshu](https://img.shields.io/badge/小红书-可用-FF2442?style=flat-square)](#-支持平台)
[![Jike](https://img.shields.io/badge/即刻-可用-FFE411?style=flat-square)](#-支持平台)
[![Podcast](https://img.shields.io/badge/播客-可用-8B5CF6?style=flat-square)](#-支持平台)

[English](./README-EN.md) | [中文文档](./README.md)

</div>

---

## ⚡ 概览

**Content Pipeline** 是 [01fish](https://github.com/OrangeViolin) 开源的**自媒体内容生产管线**，基于 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill 架构构建。

它将内容创作中最耗时的重复工作自动化——你只需要提供素材或一个链接，AI 帮你完成从写稿、排版、封面设计到多平台分发的全流程。

> **你只需要**：积累素材说一句"出稿"，或者丢一个微信链接
>
> **Pipeline 返回**：完整的多平台内容包 + 一键发布到所有渠道

### 设计理念

- **🎯 一条命令，五个平台** — 一篇内容自动适配公众号、小红书、即刻、播客、视频号
- **🔌 即插即用** — 作为 Claude Code Skill 安装，无需额外学习成本
- **🎨 品牌一致性** — 内置品牌色系统，所有产出物风格统一
- **🤖 诚实标注** — AI 参与创作的部分透明标注，不装人类
- **🔒 隐私安全** — API 密钥和个人信息通过 `local/` 目录隔离，永不上传

---

## 🔄 工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Path A: 素材积累                       Path B: 微信文章转载      │
│  ┌───────────┐                        ┌───────────┐            │
│  │  日常对话   │                        │  微信链接   │            │
│  │  自动记录   │                        │  自动抓取   │            │
│  └─────┬─────┘                        └─────┬─────┘            │
│        │                                    │                   │
│        └──────────────┬─────────────────────┘                   │
│                       ▼                                         │
│        ┌──────────────────────────────┐                         │
│        │      AI 内容生成引擎           │                         │
│        │  写稿 → 排版 → 封面 → 适配     │                         │
│        └──────────────┬───────────────┘                         │
│                       ▼                                         │
│        ┌──────┬──────┬──────┬──────┬───────┐                   │
│        │公众号 │小红书 │ 即刻  │ 播客  │ 视频  │                   │
│        └──────┴──────┴──────┴──────┴───────┘                   │
│                       │                                         │
│                       ▼                                         │
│                 manifest.json                                   │
│                       │                                         │
│                       ▼                                         │
│              /distribute 一键发布                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ 功能一览

<table>
<tr>
<td width="50%">

### 📝 内容生产

| 功能 | 触发词 |
|------|--------|
| 素材自动出稿 | `出稿` |
| 说明书 / 教程 / 深度长文 | 三种框架自动匹配 |
| 微信文章总结 | `/read-gzh` + 链接 |

</td>
<td width="50%">

### 🎨 排版设计

| 功能 | 触发词 |
|------|--------|
| 公众号排版 | `排版` |
| 头图 / 配图生成 | `做头图`、`做配图` |
| 竖版封面 | `做竖版封面` |

</td>
</tr>
<tr>
<td>

### 🔄 多平台转换

| 功能 | 触发词 |
|------|--------|
| → 小红书轮播图 | `/xiaohongshu` + 链接 |
| → 即刻文案 | `转即刻` + 链接 |
| → 播客（AI 语音） | `/podcast` + 链接 |
| → 录屏画布 | `做视频画布` |

</td>
<td>

### 🚀 自动分发

| 功能 | 触发词 |
|------|--------|
| 全平台一键发布 | `/distribute` |
| 单平台发布 | `发布到小红书` |
| 预览模式 | `--preview` |

</td>
</tr>
</table>

---

## 📱 支持平台

| 平台 | 方式 | 状态 | 说明 |
|:----:|:----:|:----:|:-----|
| 🟢 公众号 | API 直推 | **可用** | 草稿箱直推，无需打开浏览器 |
| 🟢 小红书 | Chrome CDP | **可用** | 自动上传轮播图 + 填写文案 |
| 🟢 即刻 | Chrome CDP | **可用** | 自动发布动态 |
| 🟢 小宇宙 | Chrome CDP | **可用** | 播客上传 + 节目信息填写 |
| 🟡 抖音 | Chrome CDP | **实验性** | 视频发布 |
| ⚪ 视频号 | — | **待开发** | 规划中 |

> **四级降级策略**：L0 API 直推 → L1 CDP 全自动 → L2 辅助填写 → L3 手动模式。确保任何情况下都能完成发布。

---

## 🎙️ 播客引擎

内置 AI 播客全流程——从文字到成品音频，一条龙：

| 模式 | 触发词 | 时长 | 风格 |
|------|--------|------|------|
| 标准模式 | `转播客` | 5-8 分钟 | AI 搭档聊天风 |
| 百家讲坛 | `/podcast` | 15 分钟 | 讲书人，抑扬顿挫 |
| 史记罗生门 | `/shiji` | 15 分钟 | AI 侦探 × 史源追踪 |

**AI 语音**：基于 [IndexTTS2](https://github.com/index-tts/index-tts)（MIT 协议），2-10 秒参考音频即可克隆声音，完全本地运行，零费用。

| 特性 | 说明 |
|------|------|
| 💰 费用 | 免费，完全开源 |
| 🌐 网络 | 离线可用 |
| 🎤 声音克隆 | 2-10 秒参考音频即可 |
| ⚡ 速度 | ~10x RTF（15 分钟播客约 27 分钟生成） |

---

## 🚀 快速开始

### 前置条件

| 工具 | 版本 | 说明 | 检查安装 |
|------|------|------|---------|
| **Claude Code** | 最新 | AI 代理运行时 | `claude --version` |
| **Python** | 3.10+ | 微信抓取脚本 | `python3 --version` |
| **Node.js** | 18+ | 分发脚本运行时 | `node -v` |
| **Chrome** | 最新 | CDP 自动化发布（可选） | — |

### 1️⃣ 安装

```bash
git clone https://github.com/OrangeViolin/content-pipeline.git ~/.claude/skills/content-pipeline
```

### 2️⃣ 配置

```bash
# 创建私有配置目录（不会上传 GitHub）
mkdir -p ~/.claude/skills/content-pipeline/local

# 复制环境变量模板
cp ~/.claude/skills/content-pipeline/.env.example \
   ~/.claude/skills/content-pipeline/local/.env
```

编辑 `local/.env`：

```env
# 公众号 API（可选，用于自动推送草稿箱）
WECHAT_APPID=your_appid
WECHAT_APPSECRET=your_secret

# 播客语音生成（IndexTTS2，本地运行）
INDEXTTS_DIR=~/index-tts
VOICE_REF=/path/to/voice_ref.wav

# 排版工具路径
MD_FORMATTER_DIR=/path/to/md-formatter
```

### 3️⃣ 个性化（可选）

创建 `local/SKILL.local.md` 覆盖默认设定：

```markdown
## 个人信息
- 微信号：your_wechat_id
- 品牌色文档路径：/path/to/brand-colors.md
- 默认输出目录：~/content-output/
```

### 4️⃣ 开始使用

在 Claude Code 中直接说：

```
"出稿"              → 从积累的素材生成文章
"排版"              → Markdown 转公众号 HTML
"/podcast" + 文章    → 生成 15 分钟播客
"/distribute"       → 一键发布到所有平台
```

---

## 📂 项目结构

```
content-pipeline/
├── SKILL.md                       # 主技能定义（Claude Code 读取）
├── README.md                      # 本文件
├── .env.example                   # 环境变量模板
│
├── local/                         # 🔒 私有配置（.gitignore 排除）
│   ├── SKILL.local.md             #    个人设定覆盖
│   └── .env                       #    API 密钥
│
├── references/                    # 📚 模板和规范文档
│   ├── writing-style.md           #    写作风格指南
│   ├── tutorial-framework.md      #    教程类文章框架
│   ├── manual-framework.md        #    说明书类文章框架
│   ├── cover-template.md          #    封面图设计规范
│   ├── cover-vertical-spec.md     #    竖版封面转换规范
│   ├── xiaohongshu-format.md      #    小红书轮播图模板
│   ├── platform-copy.md           #    各平台文案规范
│   ├── tts-config.md              #    TTS 语音配置
│   ├── xiaoyuzhou-podcast.md      #    播客脚本规范
│   ├── podcast-cover-template.md  #    播客封面模板
│   ├── shiji-luoshengmen.md       #    史记罗生门栏目设定
│   ├── distribute-platforms.md    #    分发平台配置
│   ├── video-canvas-template.md   #    录屏画布模板
│   └── xiaohongshu-examples/      #    小红书范例
│
├── scripts/                       # ⚙️ 自动化脚本
│   ├── fetch_wechat_article.py    #    微信文章抓取
│   └── distribute/                #    多平台分发引擎
│       ├── distribute.ts          #       编排器
│       ├── cdp-utils.ts           #       Chrome CDP 工具
│       ├── wechat-api.ts          #       公众号 API
│       └── platforms/             #       各平台模块
│
└── static/                        # 🖼️ 静态资源
    └── image/                     #    Logo、截图等
```

---

## 🔒 隐私安全

所有敏感信息通过 `local/` 目录隔离，**永不上传到 GitHub**：

| 内容 | 位置 | 保护方式 |
|:-----|:-----|:---------|
| API 密钥 | `local/.env` | `.gitignore` |
| 个人信息 | `local/SKILL.local.md` | `.gitignore` |
| Token 缓存 | `token-cache.json` | `.gitignore` |

`references/` 中的模板使用占位符（如 `YOUR_API_KEY`），不含任何实际密钥。

---

## 🎨 自定义品牌

默认使用 **01fish** 品牌色（墨绿 `#1A3328` + 鱼红 `#C44536` + 宣纸底 `#F2EDE3`）。

替换为你自己的品牌只需三步：

1. 修改 `references/cover-template.md` 中的色值
2. 修改 `references/xiaohongshu-format.md` 中的卡片样式
3. 在 `local/SKILL.local.md` 中指定品牌色文档路径

---

## 🤝 核心原则：全然诚实

AI 生成的内容必须诚实标注，不装人类，展现真实的创作过程。

```
✅ "本文由 AI 调研分析并撰写，人类主导审校"
✅ "素材收集 5 分钟，写作 3 分钟"
❌ "我们花了两周时间调研"
❌ "经过深入访谈"
```

> 诚实是长期个人品牌的基石。AI 快速高质量创作本身就是价值，不需要掩饰。

---

## 🗺️ 路线图

- [x] 公众号写稿 + 排版（说明书 / 教程 / 深度长文三种框架）
- [x] 封面图生成（头图 / 配图 / 竖版封面）
- [x] 微信 → 小红书轮播图（8-10 张卡片 + 发布文案）
- [x] 微信 → 即刻文案
- [x] 播客全流程（脚本 + AI 语音克隆 + 封面 + 发布信息）
- [x] 录屏画布（网页演示 + 摄像头 + 提词器 + 录制）
- [x] 多平台一键分发（Chrome CDP + WeChat API）
- [x] 卖书 + AI APP 组合内容管线
- [ ] 视频号发布支持
- [ ] 更多 TTS 引擎集成
- [ ] Web UI 管理面板
- [ ] 各平台数据分析仪表盘

---

## 📄 许可

[MIT License](./LICENSE) — 自由使用，自由修改，自由分发。

---

## 📈 Star History

<a href="https://www.star-history.com/#OrangeViolin/content-pipeline&type=Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=OrangeViolin/content-pipeline&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=OrangeViolin/content-pipeline&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=OrangeViolin/content-pipeline&type=Date" />
 </picture>
</a>

---

<div align="center">

**[01fish](https://github.com/OrangeViolin)** · 用 AI 做自媒体，诚实地。

</div>
