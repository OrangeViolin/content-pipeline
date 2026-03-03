# 公众号封面 → 竖版封面转换规范

> 从已有的公众号头图 HTML（900×383 横版）生成 3:4 竖版封面（1080×1440），适合小红书/视频号。
> 内容完全不变（标题、图片、标签），只换比例 + 适配竖版布局。

## 操作流程

1. **复制**原公众号封面 HTML → `[主题]_cover_vertical.html`
2. **应用下方 CSS 转换表**
3. 浏览器打开，确认效果，下载 PNG

## CSS 转换表

### 尺寸

| 选择器 | 横版（原） | 竖版（改） |
|--------|-----------|-----------|
| `.cover` | `width: 900px; height: 383px` | `width: 1080px; height: 1440px` |

### 背景图

| 选择器 | 横版（原） | 竖版（改） |
|--------|-----------|-----------|
| `.bg-img img` | `object-position: center 40%` | `object-position: center center` |

### 渐变遮罩

横版用左→右渐变（文字在左），竖版改为底→顶渐变（文字在底部）。

| 选择器 | 横版（原） | 竖版（改） |
|--------|-----------|-----------|
| `.overlay` | `linear-gradient(90deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.7) 45%, rgba(0,0,0,0.15) 75%, rgba(0,0,0,0.05) 100%)` | `linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.8) 35%, rgba(0,0,0,0.3) 55%, rgba(0,0,0,0.05) 80%, rgba(0,0,0,0.15) 100%)` |
| `.overlay-bottom` | `height: 80px` | `height: 200px` |

### 内容布局

竖版文字区移到底部。

| 选择器 | 横版（原） | 竖版（改） |
|--------|-----------|-----------|
| `.content` | `justify-content: center` | `justify-content: flex-end` |
| `.content` | `padding: 0 0 0 55px` | `padding: 0 60px 180px 60px` |

### 字号放大

竖版画布更大，字号需等比放大，确保视觉冲击力。

| 元素 | 横版 | 竖版 |
|------|------|------|
| `.tag` font-size | 11px | 18px |
| `.tag` letter-spacing | 2px | 4px |
| `.tag` padding | 4px 12px | 6px 16px |
| `.tag` margin-bottom | 14px | 20px |
| `.title` font-size | 46px | **136px** |
| `.title` | — | 添加 `white-space: nowrap`（防止换行） |
| `.title` max-width | 450px | 900px |
| `.subtitle` font-size | 16px | 44px |
| `.stat-num` font-size | 32px | 56px |
| `.stat-unit` font-size | 13px | 20px |
| `.stat-sep` font-size | 20px | 26px |

### 品牌角标放大

| 元素 | 横版 | 竖版 |
|------|------|------|
| `.brand` position | `top: 16px; left: 20px` | `top: 36px; left: 45px` |
| `.brand svg` | `width: 20px; height: 20px` | `width: 56px; height: 56px` |
| `.brand-text` font-size | 11px | 32px |

### 底部标签放大

| 元素 | 横版 | 竖版 |
|------|------|------|
| `.bottom-tags` position | `bottom: 14px; left: 20px` | `bottom: 36px; left: 45px` |
| `.btag` font-size | 10px | 13px |
| `.btag` padding | 3px 8px | 5px 12px |

### 工具栏更新

| 元素 | 横版（原） | 竖版（改） |
|------|-----------|-----------|
| 主按钮文案 | `下载头图 (900x383)` | `下载竖版封面 (1080×1440)` |
| 下载文件名 | `xxx-头图-900x383.png` | `xxx-竖版封面-1080x1440.png` |

## 注意事项

- **内容不改**：标题、副标题、数据、标签、背景图、品牌 SVG 全部保持原样
- **标题不换行**：竖版标题加 `white-space: nowrap`，确保一行显示
- **渐变方向**：横版是左→右（文字左侧），竖版是底→顶（文字底部），这是最关键的布局区别
- **底部留白**：`.content` 底部 padding 180px，给 bottom-tags 留空间
