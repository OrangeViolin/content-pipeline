<div align="center">

<!-- Replace with actual banner image -->
<img src="./static/image/content-pipeline-banner.png" alt="01fish Content Pipeline" width="75%"/>

<br/>

**One prompt to AI — from raw material to multi-platform publishing, fully automated.**

<br/>

[![GitHub Stars](https://img.shields.io/github/stars/OrangeViolin/content-pipeline?style=flat-square&color=1A3328)](https://github.com/OrangeViolin/content-pipeline/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/OrangeViolin/content-pipeline?style=flat-square)](https://github.com/OrangeViolin/content-pipeline/network)
[![License](https://img.shields.io/github/license/OrangeViolin/content-pipeline?style=flat-square&color=C44536)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-8A2BE2?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-Scripts-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)

[English](./README-EN.md) | [中文文档](./README.md)

</div>

---

## ⚡ Overview

**Content Pipeline** is an open-source **content production pipeline for creators**, built as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill by [01fish](https://github.com/OrangeViolin).

It automates the most time-consuming parts of content creation — just provide raw materials or a link, and AI handles everything from writing, formatting, cover design to multi-platform distribution.

> **You provide**: Raw materials and say "publish", or paste a WeChat article link
>
> **Pipeline returns**: Complete multi-platform content package + one-click publishing

### Design Principles

- **🎯 One command, five platforms** — One piece of content auto-adapted for WeChat, Xiaohongshu, Jike, Podcast, and more
- **🔌 Plug and play** — Install as a Claude Code Skill, zero learning curve
- **🎨 Brand consistency** — Built-in brand color system, unified visual style across all outputs
- **🤖 Honest labeling** — AI-generated content is transparently attributed
- **🔒 Privacy first** — API keys and personal info isolated in `local/` directory, never uploaded

---

## 🔄 Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Path A: Material Collection        Path B: Article Conversion  │
│  ┌───────────┐                     ┌───────────┐               │
│  │  Daily     │                     │  WeChat   │               │
│  │  Chats     │                     │  Link     │               │
│  └─────┬─────┘                     └─────┬─────┘               │
│        │                                 │                      │
│        └──────────────┬──────────────────┘                      │
│                       ▼                                         │
│        ┌──────────────────────────────┐                         │
│        │    AI Content Engine          │                         │
│        │  Write → Format → Cover →    │                         │
│        │  Multi-platform Adaptation   │                         │
│        └──────────────┬───────────────┘                         │
│                       ▼                                         │
│        ┌───────┬──────┬──────┬────────┬───────┐                │
│        │WeChat │ XHS  │ Jike │Podcast │ Video │                │
│        └───────┴──────┴──────┴────────┴───────┘                │
│                       │                                         │
│                       ▼                                         │
│                 manifest.json                                   │
│                       │                                         │
│                       ▼                                         │
│            /distribute one-click publish                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 📝 Content Production

| Feature | Trigger |
|---------|---------|
| Auto-generate articles from materials | `出稿` |
| Manual / Tutorial / Long-form | 3 frameworks, auto-matched |
| WeChat article summary | `/read-gzh` + link |

</td>
<td width="50%">

### 🎨 Design & Layout

| Feature | Trigger |
|---------|---------|
| WeChat formatting | `排版` |
| Header / Inline images | `做头图`, `做配图` |
| Vertical cover | `做竖版封面` |

</td>
</tr>
<tr>
<td>

### 🔄 Multi-platform Conversion

| Feature | Trigger |
|---------|---------|
| → Xiaohongshu carousel | `/xiaohongshu` + link |
| → Jike post | `转即刻` + link |
| → Podcast (AI voice) | `/podcast` + link |
| → Screen canvas | `做视频画布` |

</td>
<td>

### 🚀 Auto Distribution

| Feature | Trigger |
|---------|---------|
| Publish to all platforms | `/distribute` |
| Single platform | `发布到小红书` |
| Preview mode | `--preview` |

</td>
</tr>
</table>

---

## 📱 Supported Platforms

| Platform | Method | Status | Notes |
|:--------:|:------:|:------:|:------|
| 🟢 WeChat Official | API Push | **Available** | Direct draft push, no browser needed |
| 🟢 Xiaohongshu | Chrome CDP | **Available** | Auto-upload carousel + copy |
| 🟢 Jike | Chrome CDP | **Available** | Auto-publish posts |
| 🟢 Xiaoyuzhou | Chrome CDP | **Available** | Podcast upload + show notes |
| 🟡 Douyin | Chrome CDP | **Experimental** | Video publishing |
| ⚪ Shipinhao | — | **Planned** | Coming soon |

> **Four-level fallback**: L0 API push → L1 CDP auto → L2 assisted fill → L3 manual. Publishing succeeds no matter what.

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Purpose | Check |
|------|---------|---------|-------|
| **Claude Code** | Latest | AI agent runtime | `claude --version` |
| **Python** | 3.10+ | WeChat scraping | `python3 --version` |
| **Node.js** | 18+ | Distribution scripts | `node -v` |
| **Chrome** | Latest | CDP automation (optional) | — |

### 1️⃣ Install

```bash
git clone https://github.com/OrangeViolin/content-pipeline.git ~/.claude/skills/content-pipeline
```

### 2️⃣ Configure

```bash
mkdir -p ~/.claude/skills/content-pipeline/local
cp ~/.claude/skills/content-pipeline/.env.example \
   ~/.claude/skills/content-pipeline/local/.env
```

Edit `local/.env` with your credentials. See [.env.example](.env.example) for all options.

### 3️⃣ Use

In Claude Code, just say:

```
"出稿"              → Generate article from materials
"排版"              → Format Markdown → WeChat HTML
"/podcast" + article → Generate 15-min podcast
"/distribute"       → One-click publish everywhere
```

---

## 📄 License

[MIT License](./LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**[01fish](https://github.com/OrangeViolin)** · AI-powered content creation, honestly.

</div>
