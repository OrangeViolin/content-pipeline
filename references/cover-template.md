# 01fish 风格排版规范

> 公众号头图、文章配图、排版的统一规范。
> 所有图片产出为 HTML 文件，浏览器打开后点击下载按钮导出 PNG。

---

## 一、排版（Markdown → 公众号 HTML）

使用 md-formatter 排版工具，01fish 主题：

```bash
cd "$MD_FORMATTER_DIR"
python3 md2wechat_formatter.py [文章路径] --theme 01fish --font-size medium -o [输出HTML路径]
```

> `$MD_FORMATTER_DIR` 需在 `local/.env` 或环境变量中配置。

产出 `_preview.html`，浏览器打开 → 全选复制 → 粘贴到公众号编辑器。

---

## 二、公众号头图（HTML 可下载）

### 尺寸

- 主头图：`900 x 383 px`（2.35:1），2x 导出 `1800 x 766`
- 次头图：从主图中心裁出 `200 x 200` 正方形

### 设计规范

- **背景**：墨绿暗底 `#1A3328`，带微弱径向渐变纹理
- **主标题**：不超过 15 字，宣纸白 `#F2EDE3`，72px，font-weight 900，居中
- **副标题**：20px，`rgba(255,255,255,0.5)`，主标题下方
- **产品名/关键词**：鱼红 `#C44536`，带鱼红边框框住，居中
- **品牌角标**：左上角 01fish logo SVG + 文字
- **底部标签**：右下角，小字标签（工具名、特性），`rgba(255,255,255,0.35)`
- **装饰元素**：左右两侧可放低透明度（0.12）的主题相关 SVG 图标

### HTML 结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  body { background: #111; display: flex; flex-direction: column; align-items: center; padding: 70px 20px 80px; }
  .cover { width: 900px; height: 383px; position: relative; overflow: hidden; border-radius: 8px; }
  .bg-dark { position: absolute; inset: 0; background: #1A3328; }
  .content { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 2; }
  /* 工具栏同小红书模板 */
</style>
</head>
<body>
  <div class="toolbar">
    <button onclick="downloadCover('main')">下载头图 (900x383)</button>
    <button onclick="downloadCover('secondary')">下载次图 (200x200)</button>
  </div>
  <div class="cover" id="cover-main">
    <div class="bg-dark"></div>
    <!-- 品牌角标 -->
    <!-- 主标题 + 副标题 + 产品名 -->
    <!-- 底部标签 -->
  </div>
  <!-- html2canvas + FileSaver 下载脚本 -->
</body>
</html>
```

下载脚本：用 `html2canvas` 渲染 cover div，SCALE=2，主图直接导出，次图从中心裁正方形。

---

## 三、文章配图（HTML 可下载）

### 尺寸

- 宽度固定 `800px`，高度按内容 `380-500px`
- 导出 2x（`1600px` 宽）

### 设计规范

- **暗底页和浅底页交替出现**
- 暗底：`#1A3328` 背景，宣纸白文字
- 浅底：`#F2EDE3` 背景，墨绿文字
- 每张图左上角品牌角标，右下角页码 `N/N`
- 每张图顶部有 section-tag 标签（英文大写，letter-spacing: 2px）
- 鱼红仅用于：强调数字、标签分类名、关键箭头

### 常用配图类型

| 类型 | 适用场景 | 布局 |
|------|---------|------|
| 流程图 | 展示 Pipeline / 工作流 | 横向箭头连接的卡片行 |
| 对比图 | A vs B | 左右双栏，暗/浅对比 |
| 链路图 | 从输入到产出的完整路径 | 横向大卡片 + 箭头 |
| 网格卡片 | 分类展示多个项目 | 3列 grid，墨绿小卡片 on 浅底 |
| 星级评分 | 适配度 / 推荐度 | 列表行，左侧星级右侧说明 |

### HTML 结构

```html
<body>
  <div class="toolbar">
    <button onclick="downloadAll()">全部下载 (ZIP)</button>
    <button onclick="downloadOne()">下载当前</button>
  </div>

  <div class="slide-label">配图 N · 放在「xxx」之后</div>
  <div class="slide" style="height:420px;">
    <div class="bg-dark"></div>  <!-- 或 bg-light -->
    <div class="brand light"></div>  <!-- 或 brand dark -->
    <div class="page-num light">1/N</div>
    <div class="content">
      <div class="section-tag on-dark">ENGLISH TAG</div>
      <div class="title-dark" style="font-size:22px;">中文标题</div>
      <!-- 具体内容 -->
    </div>
  </div>

  <!-- html2canvas + JSZip + FileSaver -->
</body>
```

下载脚本用 `html2canvas` 渲染每个 `.slide`，打包为 ZIP。每张图命名 `配图-序号-描述.png`。

### 配图命名和位置标注

每张 `.slide` 上方必须有 `.slide-label` 标注：
```
配图 N · 放在「文章中的哪个小节」之后
```

---

## 四、视觉组件速查（暗底版）

### 品牌角标 SVG

```html
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
```

浅底版：将 `rgba(255,255,255,...)` 替换为 `rgba(26,51,40,...)`。

### Section Tag

```html
<div style="display:inline-block;font-size:11px;font-weight:700;letter-spacing:2px;padding:4px 12px;border-radius:4px;background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);">PIPELINE</div>
```

### 流程卡片

```html
<div style="width:110px;height:80px;border-radius:10px;background:rgba(196,69,54,0.15);display:flex;flex-direction:column;align-items:center;justify-content:center;border:1.5px solid rgba(196,69,54,0.3);">
  <div style="font-size:13px;font-weight:800;color:#F2EDE3;">标题</div>
  <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:4px;">说明文字</div>
</div>
```

箭头：`<div style="color:rgba(255,255,255,0.25);font-size:20px;padding:0 8px;">→</div>`

### 大数字

```html
<div style="font-size:64px;font-weight:900;color:#C44536;">22</div>
<div style="font-size:22px;font-weight:800;color:#F2EDE3;">个 Skill</div>
```

### 信息行

```html
<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
  <div style="width:6px;height:6px;border-radius:50%;background:#C44536;flex-shrink:0;"></div>
  <div style="font-size:13px;color:rgba(255,255,255,0.8);">内容文字</div>
</div>
```

---

## 五、色板速查

| 名称 | 色值 | 用途 |
|------|------|------|
| 墨绿主色 | `#1A3328` | 暗底背景 |
| 宣纸底 | `#F2EDE3` | 浅底背景、暗底上的主文字 |
| 鱼红 | `#C44536` | 强调色（仅点睛：数字、箭头、标签名、边框） |
| 半透白 | `rgba(255,255,255,0.5)` | 暗底上的品牌名 |
| 半透墨绿 | `rgba(26,51,40,0.4)` | 浅底上的品牌名 |
| 苔灰 | `#7A8C80` | 次要文字 |
| 深墨 | `#0F1F18` | 更深背景 |

**比例法则**：墨绿 85% : 鱼红 5% : 其余 10%

---

## 六、CDN 依赖

所有下载功能用这三个库：

```html
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/file-saver@2.0.5/dist/FileSaver.min.js"></script>
```
