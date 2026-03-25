# 播客节目封面模板

> 小宇宙播客节目封面，3000 × 3000 正方形，01fish 墨绿体系。

---

## 尺寸规格

| 参数 | 值 |
|------|-----|
| 画布 | 3000 × 3000 px（1:1 正方形） |
| HTML 预览 | 600 × 600 px（5x 缩放导出） |
| 导出 | html2canvas SCALE=5，输出 3000 × 3000 PNG |
| 圆角 | 0（平台会自己加圆角） |

---

## 设计规范

### 布局结构（自上而下）

```
┌──────────────────────────┐
│  [品牌角标]    [期号标签] │  ← 顶部栏
│                          │
│                          │
│     [主视觉区域]          │  ← 中心 60%
│     主题相关的视觉元素     │
│                          │
│                          │
│  ┌──────────────────┐    │
│  │  [主标题]         │    │  ← 下部 30%
│  │  [副标题/金句]    │    │
│  │  [01fish播客]     │    │
│  └──────────────────┘    │
│                          │
│  [底部标签栏]             │  ← 底部
└──────────────────────────┘
```

### 背景

- **主背景**：墨绿 `#1A3328`
- **渐变纹理**：从中心向四角的径向渐变 `radial-gradient(ellipse at center, #1A3328 0%, #0F1F18 100%)`
- **可选：主题装饰**：与播客主题相关的低透明度（0.08-0.12）几何图形或 SVG 图标

### 文字层

| 元素 | 字号(HTML) | 颜色 | 说明 |
|------|-----------|------|------|
| 期号标签 | 16px | `rgba(255,255,255,0.4)` | 右上角，`EP01` |
| 主标题 | 48-56px | `#F2EDE3` | font-weight 900，居中，最多 2 行 |
| 副标题/金句 | 20-24px | `rgba(255,255,255,0.6)` | 主标题下方，1 行 |
| 播客系列名 | 14px | `rgba(255,255,255,0.35)` | 底部，`01fish · 播客` |
| 底部标签 | 12px | `rgba(255,255,255,0.3)` | 关键词标签，间距 8px |

### 品牌角标

左上角，与公众号头图同款 01fish logo SVG（→ 见 `cover-template.md` 四、视觉组件速查）。

### 鱼红点缀

**克制使用**（5% 比例）：
- 期号数字可用鱼红 `#C44536`
- 主标题中的关键数字可用鱼红
- 底部可选一条极细鱼红分割线（`1px solid rgba(196,69,54,0.3)`）

### 主视觉区域（可选风格）

根据播客主题选择：

| 主题类型 | 视觉风格 | 实现方式 |
|---------|---------|---------|
| 技术/AI | 极简几何线条 | SVG 电路/节点图，opacity 0.1 |
| 人物故事 | 大号引号装饰 | `"` 字符 200px，opacity 0.08 |
| 方法论 | 编号/数字突出 | 大号数字居中，鱼红色 |
| 书评/读书 | 书页翻动效果 | CSS 倾斜矩形模拟书页 |
| 行业观察 | 趋势线/箭头 | SVG 上升曲线，opacity 0.12 |

---

## HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>播客封面 - [标题]</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #111;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 20px 80px;
    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  }
  .toolbar {
    position: fixed; top: 0; left: 0; right: 0;
    background: rgba(0,0,0,0.9);
    padding: 12px 20px;
    display: flex; gap: 12px; justify-content: center;
    z-index: 100;
  }
  .toolbar button {
    padding: 8px 20px; border-radius: 6px; border: none;
    background: #C44536; color: white; font-size: 14px;
    cursor: pointer; font-weight: 600;
  }
  .toolbar button:hover { background: #a83828; }

  .cover {
    width: 600px;
    height: 600px;
    position: relative;
    overflow: hidden;
  }
  .bg {
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center, #1A3328 0%, #0F1F18 100%);
  }
  .content {
    position: absolute; inset: 0;
    display: flex; flex-direction: column;
    justify-content: flex-end;
    padding: 40px;
    z-index: 2;
  }

  /* 品牌角标 */
  .brand {
    position: absolute; top: 28px; left: 28px; z-index: 3;
    display: flex; align-items: center; gap: 6px;
  }
  .brand svg { width: 28px; height: 28px; }
  .brand span { font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.5); letter-spacing: 1px; }

  /* 期号标签 */
  .ep-tag {
    position: absolute; top: 28px; right: 28px; z-index: 3;
    font-size: 16px; font-weight: 800;
    color: rgba(255,255,255,0.4);
    letter-spacing: 2px;
  }
  .ep-tag .num { color: #C44536; }

  /* 主视觉区域 */
  .visual {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -60%);
    z-index: 1;
    opacity: 0.08;
  }

  /* 文字区域 */
  .title {
    font-size: 48px; font-weight: 900;
    color: #F2EDE3;
    line-height: 1.25;
    margin-bottom: 12px;
  }
  .subtitle {
    font-size: 20px; font-weight: 400;
    color: rgba(255,255,255,0.6);
    line-height: 1.5;
    margin-bottom: 24px;
  }
  .series {
    font-size: 14px; font-weight: 600;
    color: rgba(255,255,255,0.35);
    letter-spacing: 2px;
  }
  .divider {
    width: 40px; height: 1px;
    background: rgba(196,69,54,0.4);
    margin-bottom: 12px;
  }
  .tags {
    position: absolute; bottom: 28px; right: 28px; z-index: 3;
    display: flex; gap: 8px;
  }
  .tag {
    font-size: 11px; padding: 3px 10px; border-radius: 3px;
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.3);
    letter-spacing: 1px;
  }
</style>
</head>
<body>
  <div class="toolbar">
    <button onclick="downloadCover()">下载封面 (3000×3000)</button>
  </div>

  <div class="cover" id="cover">
    <div class="bg"></div>

    <!-- 品牌角标（复用 cover-template.md 的 SVG） -->
    <div class="brand">
      <svg viewBox="0 0 32 32" fill="none">
        <circle cx="13" cy="16" r="10" stroke="rgba(255,255,255,0.5)" stroke-width="2.2" fill="none"/>
        <ellipse cx="13" cy="8.5" rx="7" ry="1.5" stroke="rgba(255,255,255,0.3)" stroke-width="1.2" fill="none"/>
        <ellipse cx="14" cy="17" rx="3.5" ry="2" fill="#C44536"/>
        <polygon points="10,17 7.5,14.5 7.5,19.5" fill="#C44536"/>
        <circle cx="16" cy="16.3" r="0.7" fill="#F2EDE3"/>
        <line x1="26" y1="4" x2="26" y2="16" stroke="rgba(255,255,255,0.5)" stroke-width="2" stroke-linecap="round"/>
        <path d="M26 16 Q26 22 22 22" stroke="rgba(255,255,255,0.5)" stroke-width="2" fill="none" stroke-linecap="round"/>
        <circle cx="26" cy="4" r="2" stroke="rgba(255,255,255,0.5)" stroke-width="1.5" fill="none"/>
      </svg>
      <span>01fish</span>
    </div>

    <!-- 期号 -->
    <div class="ep-tag">EP<span class="num">01</span></div>

    <!-- 主视觉（按主题替换） -->
    <div class="visual">
      <!-- 默认：大引号装饰 -->
      <div style="font-size:200px;color:#F2EDE3;font-weight:900;">"</div>
    </div>

    <!-- 文字内容 -->
    <div class="content">
      <div class="title">主标题在这里</div>
      <div class="subtitle">副标题或金句</div>
      <div class="divider"></div>
      <div class="series">01FISH · 播客</div>
    </div>

    <!-- 底部标签 -->
    <div class="tags">
      <span class="tag">AI</span>
      <span class="tag">效率</span>
      <span class="tag">方法论</span>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js"></script>
  <script>
    async function downloadCover() {
      const el = document.getElementById('cover');
      const canvas = await html2canvas(el, { scale: 5, useCORS: true, backgroundColor: null });
      canvas.toBlob(blob => saveAs(blob, '播客封面.png'), 'image/png');
    }
  </script>
</body>
</html>
```

---

## 使用方式

生成封面时：
1. 复制上方 HTML 模板
2. 替换：期号、主标题、副标题、底部标签、主视觉元素
3. 保存为 `[标题]-播客封面.html`
4. 浏览器打开 → 点击"下载封面"按钮 → 获得 3000×3000 PNG
5. 上传到小宇宙作为节目封面
