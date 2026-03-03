# 分发平台配置

> 来源：distribute skill 全文

---

## 平台列表

| 缩写 | 平台 | 状态 |
|------|------|------|
| `wechat` | 公众号 | 可用 |
| `xhs` | 小红书 | 可用 |
| `jike` | 即刻 | 可用 |
| `xiaoyuzhou` | 小宇宙 | 可用 |
| `douyin` | 抖音 | 实验性 |
| `shipinhao` | 视频号 | 待开发（无 web 后台） |

---

## manifest.json 格式

由内容生成流程（Path A 或 Path B）自动输出。

```json
{
  "version": "1.0",
  "created": "2026-02-15T10:00:00Z",
  "source": "https://mp.weixin.qq.com/s/xxx",
  "title": "文章标题",
  "outputs": {
    "xiaohongshu": {
      "html": "/path/to/xxx-小红书版.html",
      "images_dir": "/path/to/images/",
      "copy": {
        "title": "小红书标题",
        "body": "正文内容...",
        "tags": ["#AI工具", "#ClaudeCode"]
      }
    },
    "jike": {
      "copy": {
        "body": "即刻正文...",
        "circles": ["#Claude Code", "#AI工具"]
      }
    },
    "xiaoyuzhou": {
      "audio": "/path/to/podcast.mp3",
      "script": "/path/to/podcast-script.txt",
      "copy": {
        "title": "播客标题",
        "description": "简介...",
        "show_notes": "完整 show notes..."
      }
    },
    "wechat": {
      "markdown": "/path/to/article.md",
      "html": "/path/to/article_preview.html",
      "cover_image": "/path/to/cover.png",
      "title": "文章标题",
      "author": "01fish",
      "digest": "文章摘要（120字内）",
      "images": ["/path/to/illustration1.png"]
    },
    "video": {
      "intro": "/path/to/intro.mp4",
      "outro": "/path/to/outro.mp4",
      "prompts": "/path/to/video-prompts.md"
    },
    "douyin": {
      "video": "/path/to/video.mp4",
      "copy": {
        "title": "标题",
        "description": "描述",
        "tags": ["#标签"]
      }
    }
  }
}
```

---

## 执行流程

### 第 1 步：读取 manifest

解析 manifest.json，验证文件路径存在，列出可发布平台。

### 第 2 步：确认发布计划

展示将要发布的平台和内容摘要，等待用户确认。

### 第 3 步：顺序执行

**执行顺序（避免 Chrome 端口冲突）：**

1. **公众号**（wechat）→ 调用 baoyu-post-to-wechat
2. **小红书**（xhs）→ Chrome CDP 自动发布
3. **即刻**（jike）→ Chrome CDP 自动发布
4. **小宇宙**（xiaoyuzhou）→ Chrome CDP 自动发布
5. **抖音**（douyin）→ Chrome CDP 自动发布
6. **视频号**（shipinhao）→ Chrome CDP 自动发布

每个平台完成后关闭 Chrome，再启动下一个。

### 第 4 步：汇报结果

输出每个平台的发布状态（成功/失败/跳过），附上发布链接（如有）。

---

## 四级降级策略

| 级别 | 模式 | 说明 |
|------|------|------|
| L0 | API 直推 | 微信公众号 API 直接推送草稿箱，无需 Chrome（仅公众号） |
| L1 | 自动发布 | Chrome CDP 完全自动化，预填内容并提交 |
| L2 | 辅助发布 | 打开创作者页面，预填内容，用户手动确认提交 |
| L3 | 手动模式 | 输出文件路径和文案，用户自行复制粘贴 |

**公众号执行策略：** 优先 L0（API），API 凭证缺失或调用失败时降级 L1（CDP）

**降级触发条件：**
- API 凭证未配置 → L0 降级为 L1
- API 调用失败 → L0 降级为 L1
- 登录态失效 → L2（打开登录页，等待用户登录后重试）
- 选择器失效（平台 UI 改版）→ L2
- CDP 连接失败 → L3
- `--preview` 参数 → 强制 L2

---

## Chrome Profile 管理

每个平台独立 Chrome profile，避免 session 冲突：

| 平台 | Profile 路径 |
|------|-------------|
| 公众号 | `~/.local/share/wechat-browser-profile` |
| 小红书 | `~/.local/share/xiaohongshu-browser-profile` |
| 即刻 | `~/.local/share/jike-browser-profile` |
| 小宇宙 | `~/.local/share/xiaoyuzhou-browser-profile` |
| 抖音 | `~/.local/share/douyin-browser-profile` |
| 视频号 | `~/.local/share/shipinhao-browser-profile` |

首次使用每个平台需手动登录一次，后续复用 session。

---

## 反自动化对策

- Chrome 启动参数：`--disable-blink-features=AutomationControlled`
- 操作间随机延迟：200-800ms
- 模拟真实鼠标移动和键盘输入
- 使用真实 Chrome profile（非无头模式）

---

## 选择器配置

各平台 CSS 选择器抽取为常量，便于平台 UI 改版时快速修复。每个平台模块顶部定义 `SELECTORS` 对象。

---

## 故障处理

| 问题 | 处理 |
|------|------|
| manifest.json 不存在 | 提示用户先运行内容生成 |
| 某平台文件缺失 | 跳过该平台，继续其他 |
| Chrome 启动失败 | 检查 Chrome 安装，降级 L3 |
| 登录态失效 | 打开登录页，等待用户登录 |
| 发布失败 | 记录错误，继续下一平台 |
| 网络超时 | 重试 1 次，失败则降级 |
