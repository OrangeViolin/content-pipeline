# 视频画布模板参考（手账拼贴风格）

> cc 生成视频画布 HTML 时读取此文件。模板包含完整的 CSS、HTML 骨架和 JS 框架。
> cc 根据文章内容填充 9 张卡片内容 + 9 段提词器脚本，其余部分原样复用。

---

## 输入素材类型

cc 接受任意素材输入，自动识别并提取内容：

| 输入类型 | 处理方式 |
|---------|---------|
| 微信链接 | 调用 `scripts/fetch_wechat_article.py` 抓取 |
| Markdown 文件 | 直接读取 |
| PDF 文件 | 读取并提取文本 |
| HTML 文件 | 读取并提取正文 |
| 纯文本 | 直接使用 |
| 用户口述/粘贴内容 | 直接使用 |

提取内容后，分析结构 → 拆分为 9 张卡片 + 9 段提词器脚本。

---

## 关键技术陷阱

**必须遵守，否则 HTML 会崩溃：**

1. **`</script>` 拆分**：模板字符串或 innerHTML 中出现 `</script>` 会终止外层 script 块。必须拆开写：
   ```js
   // ❌ 错误
   doc.body.innerHTML = '<script>...</script>';
   // ✅ 正确
   doc.body.innerHTML = '<scr' + 'ipt>...</scr' + 'ipt>';
   ```

2. **let 变量 TDZ**：所有 `let` 变量声明必须在 `goOverview()` 调用之前，否则触发 Temporal Dead Zone 错误。

3. **瘦脸 scale**：使用 `scale(-(1.2*slimFactor), 1.2)` 实现镜像+瘦脸。不要用 `scale(-slimFactor, 1)`，会导致摄像头画面不填满圆框。

4. **`</style>` 安全**：如果 CSS 中有内联模板，同样注意 `</style>` 标签不要意外闭合。

---

## 完整 HTML 模板

### 文档头

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>01fish #{{NUMBER}} - {{TITLE}}</title>
    <style>
        /* === 完整 CSS 见下方 === */
    </style>
</head>
<body>
    <!-- === 完整 HTML 骨架见下方 === -->
    <script>
        // === 完整 JS 见下方 ===
    </script>
</body>
</html>
```

---

## CSS 框架（~320行）

```css
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; background: #E8E3D9; cursor: grab; }
body.dragging { cursor: grabbing; }
body.dragging .world { transition: none !important; }

/* 方格纸底 */
.world {
    position: absolute; width: 3600px; height: 2000px;
    background: #F2EDE3;
    background-image:
        linear-gradient(rgba(26,51,40,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(26,51,40,0.05) 1px, transparent 1px);
    background-size: 24px 24px;
    transform-origin: 0 0;
    transition: transform 0.7s cubic-bezier(0.25, 0.1, 0.25, 1);
    will-change: transform;
}

/* 卡片通用 */
.card {
    position: absolute; cursor: pointer;
    transition: box-shadow 0.3s, filter 0.3s;
}
.card:hover { filter: brightness(1.02); box-shadow: 8px 8px 0 rgba(26,51,40,0.15) !important; }
.card.active { z-index: 50 !important; }

/* 胶带 */
.tape { position: absolute; height: 26px; z-index: 10; pointer-events: none; }
.tape-tl { top: -13px; left: 28px; transform: rotate(-4deg); }
.tape-tr { top: -13px; right: 28px; transform: rotate(3deg); }
.tape-bl { bottom: -13px; left: 36px; transform: rotate(3deg); }
.tape-br { bottom: -13px; right: 28px; transform: rotate(-2deg); }
.tape-w80 { width: 80px; } .tape-w100 { width: 100px; }
.tape-red { background: rgba(196,69,54,0.13); }
.tape-green { background: rgba(26,51,40,0.09); }

/* 便签 */
.sticky {
    position: absolute; padding: 10px 14px; font-family: 'Caveat', cursive; font-size: 16px;
    line-height: 1.4; z-index: 10; box-shadow: 2px 2px 5px rgba(0,0,0,0.07); pointer-events: none;
}
.sticky-y { background: #FFF8DC; color: #1A3328; }
.sticky-p { background: #FFE4E1; color: #C44536; }
.sticky-g { background: #E8EDEA; color: #1A3328; }

/* 连线 */
.connector { position: absolute; pointer-events: none; z-index: 5; }
.connector path { fill: none; stroke: #1A3328; stroke-width: 2; stroke-dasharray: 8 6; opacity: 0.2; }

/* === c1: 标题卡（墨绿底） === */
.c1 { left:80px;top:200px;width:500px;height:460px;background:#1A3328;padding:44px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;transform:rotate(-1.2deg);box-shadow:6px 6px 0 rgba(26,51,40,0.15);z-index:10; }
.c1 .logo { font-family:'Caveat',cursive;font-size:22px;color:#7A8C80;margin-bottom:20px; }
.c1 h1 { font-size:44px;color:#F2EDE3;line-height:1.35;font-weight:900;margin-bottom:16px; }
.c1 h1 em { font-style:normal;display:inline-block;background:#C44536;padding:2px 10px;transform:rotate(-1deg); }
.c1 .sub { font-family:'Caveat',cursive;font-size:22px;color:#7A8C80; }

/* === c2: 数据卡（白底） === */
.c2 { left:680px;top:80px;width:380px;height:420px;background:white;padding:40px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;transform:rotate(1deg);border:2px solid #1A3328;box-shadow:5px 5px 0 rgba(26,51,40,0.1);z-index:10; }
.c2 .num { font-family:'Caveat',cursive;font-size:120px;font-weight:700;color:#C44536;line-height:1; }
.c2 .lbl { font-size:26px;color:#1A3328;font-weight:800;margin-bottom:12px; }
.c2 .det { font-size:15px;color:#7A8C80;line-height:2; }
.c2 .stamp { margin-top:16px;padding:6px 18px;border:2px solid #C44536;border-radius:3px;font-family:'Caveat',cursive;font-size:20px;color:#C44536;transform:rotate(-4deg); }

/* === c3: 痛点/问题卡（白底+条纹） === */
.c3 { left:680px;top:540px;width:440px;height:400px;background:white;padding:36px;display:flex;flex-direction:column;justify-content:center;transform:rotate(-0.5deg);border:2px solid #1A3328;box-shadow:5px 5px 0 rgba(26,51,40,0.1);z-index:10; }
.c3 h2 { font-size:26px;color:#1A3328;font-weight:900;margin-bottom:20px; }
.c3 .strip { background:#FFE4E1;padding:12px 16px;margin-bottom:8px;border-left:4px solid #C44536;font-size:15px;color:#333;line-height:1.5; }
.c3 .strip:nth-child(odd) { transform:rotate(0.3deg); }
.c3 .strip:nth-child(even) { transform:rotate(-0.3deg); }
.c3 .punchline { margin-top:16px;padding:16px;background:#1A3328;color:#F2EDE3;border-radius:3px;font-size:18px;font-weight:800;line-height:1.5;text-align:center;transform:rotate(0.5deg); }
.c3 .punchline span { color:#C44536; }

/* === c4: 步骤卡（墨绿底+ticket） === */
.c4 { left:1200px;top:140px;width:460px;height:460px;background:#1A3328;padding:40px;display:flex;flex-direction:column;justify-content:center;transform:rotate(0.7deg);box-shadow:5px 5px 0 rgba(26,51,40,0.2);z-index:10; }
.c4 h2 { font-family:'Caveat',cursive;font-size:34px;color:#F2EDE3;font-weight:700;margin-bottom:24px; }
.c4 .ticket { background:white;padding:16px 20px;margin-bottom:12px;border-left:5px solid #C44536;display:flex;align-items:flex-start;gap:14px; }
.c4 .ticket:nth-child(odd) { transform:rotate(-0.3deg); }
.c4 .ticket:nth-child(even) { transform:rotate(0.4deg); }
.c4 .tnum { font-family:'Caveat',cursive;font-size:30px;font-weight:700;color:#C44536;min-width:28px;line-height:1; }
.c4 .tbody h3 { font-size:17px;color:#1A3328;font-weight:700;margin-bottom:2px; }
.c4 .tbody p { font-size:12px;color:#7A8C80;line-height:1.4; }
.c4 .foot { text-align:center;color:#7A8C80;font-size:14px;margin-top:12px; }

/* === c5: 架构卡（白底+流程框） === */
.c5 { left:1220px;top:660px;width:480px;height:400px;background:white;padding:36px;display:flex;flex-direction:column;justify-content:center;transform:rotate(-0.6deg);border:2px solid #1A3328;box-shadow:5px 5px 0 rgba(26,51,40,0.1);z-index:10; }
.c5 h2 { font-size:26px;color:#1A3328;font-weight:900;margin-bottom:20px; }
.c5 .abox { background:#F2EDE3;border:1.5px solid #1A3328;padding:14px 18px;margin-bottom:6px;position:relative; }
.c5 .abox h3 { font-size:16px;color:#1A3328;font-weight:800;margin-bottom:3px; }
.c5 .abox p { font-size:12px;color:#7A8C80;line-height:1.5; }
.c5 .abox .mt { position:absolute;top:-7px;right:14px;width:56px;height:16px;transform:rotate(2deg); }
.c5 .abox .mt.red { background:rgba(196,69,54,0.15); }
.c5 .abox .mt.grn { background:rgba(26,51,40,0.1); }
.c5 .aconn { text-align:center;font-family:'Caveat',cursive;font-size:18px;color:#7A8C80;padding:1px 0; }

/* === c6: 数据/对比卡（白底+小票） === */
.c6 { left:1780px;top:100px;width:400px;height:440px;background:white;padding:36px;display:flex;flex-direction:column;justify-content:center;transform:rotate(0.5deg);border:2px solid #1A3328;box-shadow:5px 5px 0 rgba(26,51,40,0.1);z-index:10; }
.c6 h2 { font-size:26px;color:#1A3328;font-weight:900;margin-bottom:20px; }
.c6 .receipt { background:#F2EDE3;padding:18px;border:1px dashed rgba(26,51,40,0.3);font-family:monospace; }
.c6 .rrow { display:flex;justify-content:space-between;padding:7px 0;font-size:14px;color:#333;border-bottom:1px dotted rgba(26,51,40,0.15); }
.c6 .rrow .v { font-weight:700;color:#1A3328; } .c6 .rrow .v.r { color:#C44536; }
.c6 .rtotal { display:flex;justify-content:space-between;padding:10px 0 0;font-size:16px;font-weight:800;color:#C44536; }
.c6 .fnote { margin-top:14px;font-family:'Caveat',cursive;font-size:17px;color:#7A8C80;text-align:center;transform:rotate(-1deg); }

/* === c7: 金句卡（墨绿底+大引号） === */
.c7 { left:1800px;top:600px;width:440px;height:400px;background:#1A3328;padding:48px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;transform:rotate(-0.8deg);box-shadow:5px 5px 0 rgba(26,51,40,0.2);z-index:10; }
.c7 .qm { font-family:'Caveat',cursive;font-size:72px;color:#C44536;line-height:0.5;margin-bottom:20px; }
.c7 .qt { font-size:30px;color:#F2EDE3;font-weight:900;line-height:1.6;margin-bottom:20px; }
.c7 .qt em { font-style:normal;display:inline-block;background:#C44536;padding:2px 8px; }
.c7 .qs { font-family:'Caveat',cursive;font-size:19px;color:#7A8C80;line-height:1.8; }

/* === c8: 闭环/特色卡（白底+标签流） === */
.c8 { left:2340px;top:180px;width:500px;height:400px;background:white;padding:36px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;transform:rotate(0.4deg);border:2px solid #1A3328;box-shadow:5px 5px 0 rgba(26,51,40,0.1);z-index:10; }
.c8 h2 { font-size:26px;color:#1A3328;font-weight:900;margin-bottom:24px; }
.c8 .trk { display:flex;align-items:center;gap:6px;margin-bottom:10px; }
.c8 .tag { padding:10px 16px;border-radius:5px;font-size:14px;font-weight:700;border:2px solid #1A3328;background:white;color:#1A3328; }
.c8 .tag.hot { background:#C44536;border-color:#C44536;color:white;transform:rotate(-1deg); }
.c8 .tag.em { font-size:17px;padding:8px 10px; }
.c8 .arr { font-family:'Caveat',cursive;font-size:20px;color:#7A8C80; }
.c8 .ins { margin-top:16px;font-size:15px;color:#7A8C80;line-height:1.8; }

/* === c9: CTA卡（墨绿底+品牌） === */
.c9 { left:2380px;top:640px;width:380px;height:380px;background:#1A3328;padding:44px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;transform:rotate(-0.6deg);box-shadow:5px 5px 0 rgba(26,51,40,0.2);z-index:10; }
.c9 .fish { font-size:52px;margin-bottom:12px; }
.c9 .brand { font-family:'Caveat',cursive;font-size:40px;color:#F2EDE3;font-weight:700;margin-bottom:6px; }
.c9 .sl { font-size:15px;color:#7A8C80;line-height:1.7;margin-bottom:20px; }
.c9 .cta { display:inline-block;background:#C44536;color:white;padding:12px 32px;font-size:16px;font-weight:700;border-radius:3px;transform:rotate(-1.5deg);box-shadow:3px 3px 0 rgba(0,0,0,0.12); }

/* === 导航栏 === */
.nav-bar {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 6px; z-index: 300;
    background: rgba(26,51,40,0.9); padding: 8px 16px; border-radius: 28px;
    backdrop-filter: blur(12px);
}
.nav-dot {
    width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(242,237,227,0.3);
    background: transparent; color: #F2EDE3; font-family: 'Caveat', cursive;
    font-size: 15px; font-weight: 700; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.3s;
}
.nav-dot:hover { border-color: #F2EDE3; background: rgba(242,237,227,0.1); }
.nav-dot.active { background: #C44536; border-color: #C44536; }
.nav-overview {
    width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(242,237,227,0.3);
    background: transparent; color: #F2EDE3; font-size: 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.3s; margin-right: 8px;
}
.nav-overview:hover { border-color: #F2EDE3; }
.nav-overview.active { background: rgba(242,237,227,0.15); border-color: #F2EDE3; }

/* === 摄像头（可拖拽） === */
.webcam-wrap {
    position: fixed; bottom: 80px; right: 32px; width: 160px; height: 160px;
    border-radius: 50%; overflow: hidden; border: 3px solid #1A3328;
    box-shadow: 4px 4px 0 rgba(26,51,40,0.15); z-index: 200; background: #1A3328; transform: rotate(-2deg);
    cursor: grab; user-select: none;
}
.webcam-wrap.dragging { cursor: grabbing; }
.webcam-wrap video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
.webcam-wrap.off { display: none; }

/* === 工具栏（左下角） === */
.toolbar {
    position: fixed; bottom: 24px; left: 24px;
    display: flex; gap: 6px; z-index: 300;
    background: rgba(255,255,255,0.95); padding: 6px 10px; border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1); border: 1px solid rgba(26,51,40,0.1);
}
.tb-btn {
    width: 44px; height: 44px; border-radius: 10px; border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center; font-size: 18px;
    background: transparent; transition: all 0.2s;
}
.tb-btn:hover { background: rgba(26,51,40,0.06); }
.tb-btn.active { background: #1A3328; color: white; }
.tb-rec {
    background: #C44536 !important; color: white; font-size: 14px; font-weight: 700;
    width: auto; padding: 0 18px; gap: 6px; border-radius: 22px;
}
.tb-rec:hover { background: #a33828 !important; }
.tb-rec .dot { width: 10px; height: 10px; border-radius: 50%; background: white; }

/* === 录制状态（保留导航栏和页码） === */
body.recording .hint,
body.recording .cam-toggle { display: none !important; }

.rec-indicator {
    position: fixed; top: 20px; left: 20px; z-index: 400;
    display: none; align-items: center; gap: 8px;
    background: rgba(196,69,54,0.9); color: white;
    padding: 8px 18px; border-radius: 24px; font-size: 14px; font-weight: 700;
    cursor: pointer; backdrop-filter: blur(8px);
    animation: rec-pulse 1.5s ease-in-out infinite;
}
.rec-indicator .rec-dot { width: 10px; height: 10px; border-radius: 50%; background: white; }
body.recording .rec-indicator { display: flex; }
@keyframes rec-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.rec-timer { font-family: 'Caveat', cursive; font-size: 18px; font-variant-numeric: tabular-nums; }

/* 页码 / 提示 */
.page-num { position: fixed; top: 20px; right: 28px; font-family: 'Caveat', cursive; font-size: 22px; color: #7A8C80; z-index: 300; }
.hint { position: fixed; top: 20px; left: 28px; font-size: 13px; color: #7A8C80; z-index: 300; transition: opacity 0.5s; }
.hint.hide { opacity: 0; pointer-events: none; }
.cam-toggle {
    position: fixed; bottom: 80px; right: 200px;
    background: rgba(26,51,40,0.85); color: #F2EDE3; border: none;
    padding: 8px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; z-index: 200;
}
.cam-toggle:hover { background: #1A3328; }
.cam-toggle.on { background: #C44536; }

/* === 设置面板 === */
.modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.4);
    z-index: 500; display: none; align-items: center; justify-content: center;
    backdrop-filter: blur(4px);
}
.modal-overlay.show { display: flex; }
.modal {
    background: white; border-radius: 16px; padding: 32px;
    width: 480px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
    position: relative;
}
.modal h2 { font-size: 24px; font-weight: 900; color: #1A3328; margin-bottom: 24px; }
.modal .close-btn {
    position: absolute; top: 16px; right: 16px; width: 36px; height: 36px;
    border-radius: 50%; border: none; background: #f0f0f0; cursor: pointer;
    font-size: 18px; display: flex; align-items: center; justify-content: center;
}
.modal .close-btn:hover { background: #e0e0e0; }
.modal .section-label { font-size: 13px; color: #999; margin-bottom: 12px; }
.modal .start-rec-btn {
    width: 100%; padding: 14px; border-radius: 12px; border: none;
    background: #C44536; color: white; font-size: 16px; font-weight: 700;
    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
}
.modal .start-rec-btn:hover { background: #a33828; }
.modal .info-box {
    background: #f8f8f8; border-radius: 10px; padding: 14px 16px;
    margin-bottom: 20px; font-size: 13px; color: #666; line-height: 1.6;
}
.modal .info-box strong { color: #1A3328; }

/* === 美颜面板 === */
.beauty-panel {
    position: fixed; bottom: 80px; left: 24px;
    background: rgba(255,255,255,0.97); border-radius: 14px;
    padding: 16px 20px; z-index: 350; width: 220px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.12); border: 1px solid rgba(26,51,40,0.1);
    display: none;
}
.beauty-panel.show { display: block; }
.bp-title { font-size: 14px; font-weight: 700; color: #1A3328; margin-bottom: 12px; }
.bp-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.bp-row:last-child { margin-bottom: 0; }
.bp-label { font-size: 12px; color: #666; min-width: 32px; }
.bp-row input[type=range] { flex: 1; accent-color: #1A3328; }
body.recording .beauty-panel { display: none !important; }

/* === 网站演示层 === */
.web-layer {
    position: fixed; inset: 0; z-index: 100;
    display: none; flex-direction: column;
    background: #E8E3D9;
}
.web-layer.show { display: flex; }
.web-bar {
    height: 40px; background: rgba(26,51,40,0.95); display: flex; align-items: center;
    padding: 0 12px; gap: 8px; flex-shrink: 0;
}
body.recording .web-bar { display: none; }
.web-bar-url {
    flex: 1; font-size: 13px; color: #F2EDE3; font-family: monospace;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.web-bar-btn {
    background: none; border: 1px solid rgba(242,237,227,0.3); color: #F2EDE3;
    border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer;
}
.web-bar-btn:hover { background: rgba(242,237,227,0.1); }
.web-iframe {
    flex: 1; border: none; width: 100%; background: white;
}

/* 网站管理弹窗 */
.web-modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.4);
    z-index: 500; display: none; align-items: center; justify-content: center;
    backdrop-filter: blur(4px);
}
.web-modal-overlay.show { display: flex; }
.web-modal {
    background: white; border-radius: 16px; padding: 32px;
    width: 520px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
    position: relative; max-height: 80vh; display: flex; flex-direction: column;
}
.web-modal h2 { font-size: 24px; font-weight: 900; color: #1A3328; margin-bottom: 20px; }
.web-modal .close-btn {
    position: absolute; top: 16px; right: 16px; width: 36px; height: 36px;
    border-radius: 50%; border: none; background: #f0f0f0; cursor: pointer;
    font-size: 18px; display: flex; align-items: center; justify-content: center;
}
.web-modal .close-btn:hover { background: #e0e0e0; }
.web-url-input-row {
    display: flex; gap: 8px; margin-bottom: 16px;
}
.web-url-input {
    flex: 1; padding: 10px 14px; border: 2px solid #ddd; border-radius: 10px;
    font-size: 14px; outline: none;
}
.web-url-input:focus { border-color: #1A3328; }
.web-url-add-btn {
    padding: 10px 20px; border-radius: 10px; border: none;
    background: #1A3328; color: white; font-size: 14px; font-weight: 700;
    cursor: pointer; white-space: nowrap;
}
.web-url-add-btn:hover { background: #2a4a3a; }
.web-url-list {
    flex: 1; overflow-y: auto; min-height: 60px;
}
.web-url-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border-radius: 8px; margin-bottom: 6px; background: #f8f8f8;
}
.web-url-item:hover { background: #f0f0f0; }
.web-url-item .idx {
    width: 24px; height: 24px; border-radius: 50%; background: #1A3328; color: white;
    font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.web-url-item .url-text {
    flex: 1; font-size: 13px; color: #333; word-break: break-all;
}
.web-url-item .go-btn {
    padding: 4px 12px; border-radius: 6px; border: 1px solid #1A3328;
    background: white; color: #1A3328; font-size: 12px; cursor: pointer;
}
.web-url-item .go-btn:hover { background: #1A3328; color: white; }
.web-url-item .del-btn {
    padding: 4px 8px; border-radius: 6px; border: 1px solid #ddd;
    background: white; color: #999; font-size: 12px; cursor: pointer;
}
.web-url-item .del-btn:hover { background: #C44536; color: white; border-color: #C44536; }
.web-url-empty {
    text-align: center; color: #999; font-size: 13px; padding: 24px 0;
}

/* 导航栏网站分隔 + 网站导航点 */
.nav-web-sep {
    width: 1px; height: 20px; background: rgba(242,237,227,0.2);
    margin: 6px 4px; display: none;
}
.nav-web-sep.show { display: block; }
.nav-dot-web {
    width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(242,237,227,0.3);
    background: transparent; color: #F2EDE3; font-size: 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.3s;
}
.nav-dot-web:hover { border-color: #F2EDE3; background: rgba(242,237,227,0.1); }
.nav-dot-web.active { background: #C44536; border-color: #C44536; }

/* === 实时字幕 === */
.subtitle-bar {
    position: fixed; bottom: 72px; left: 50%; transform: translateX(-50%);
    z-index: 250; pointer-events: none;
    max-width: 70vw; text-align: center;
    display: none;
}
.subtitle-bar.show { display: block; }
.subtitle-text {
    display: inline-block; background: rgba(0,0,0,0.7); color: white;
    padding: 10px 24px; border-radius: 8px; font-size: 22px; font-weight: 600;
    line-height: 1.6; backdrop-filter: blur(4px);
    max-width: 100%; word-break: break-word;
}
.subtitle-text:empty { display: none; }
```

---

## HTML 骨架

```html
<body>
    <div class="page-num" id="pageNum">全景</div>
    <div class="hint" id="hint">点击卡片放大 · ← → 翻页 · ESC 回全景</div>

    <!-- 摄像头 -->
    <div class="webcam-wrap off" id="webcam"><video id="camVideo" autoplay playsinline muted></video></div>
    <button class="cam-toggle" id="camBtn">📷</button>

    <!-- 录制指示器 -->
    <div class="rec-indicator" id="recIndicator" title="点击停止录制">
        <div class="rec-dot"></div>
        <span>REC</span>
        <span class="rec-timer" id="recTimer">00:00</span>
    </div>

    <!-- 实时字幕 -->
    <div class="subtitle-bar" id="subtitleBar">
        <span class="subtitle-text" id="subtitleText"></span>
    </div>

    <!-- 网站演示层 -->
    <div class="web-layer" id="webLayer">
        <div class="web-bar">
            <span class="web-bar-url" id="webBarUrl">—</span>
            <button class="web-bar-btn" id="webBarBack" title="返回画布">✕ 退出</button>
        </div>
        <iframe class="web-iframe" id="webIframe" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allowfullscreen></iframe>
    </div>

    <!-- 网站管理弹窗 -->
    <div class="web-modal-overlay" id="webModal">
        <div class="web-modal">
            <button class="close-btn" id="closeWebModal">&times;</button>
            <h2>网站演示</h2>
            <div class="web-url-input-row">
                <input class="web-url-input" id="webUrlInput" type="url" placeholder="输入网址，如 https://example.com">
                <button class="web-url-add-btn" id="webUrlAddBtn">添加</button>
            </div>
            <div class="web-url-list" id="webUrlList">
                <div class="web-url-empty">还没有添加网站</div>
            </div>
        </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
        <button class="tb-btn" id="btnTeleprompter" title="提词器">📋</button>
        <button class="tb-btn" id="btnCamToggle" title="摄像头开关">📷</button>
        <button class="tb-btn" id="btnBeauty" title="美颜">✨</button>
        <button class="tb-btn" id="btnSubtitle" title="实时字幕">💬</button>
        <button class="tb-btn" id="btnWebsite" title="网站演示">🌐</button>
        <button class="tb-btn tb-rec" id="btnRecord" title="开始录制">
            <div class="dot"></div>
            <span>录制</span>
        </button>
    </div>

    <!-- 美颜面板 -->
    <div class="beauty-panel" id="beautyPanel">
        <div class="bp-title">美颜</div>
        <div class="bp-row"><span class="bp-label">美白</span><input type="range" min="0" max="100" value="25" id="sliderWhiten"></div>
        <div class="bp-row"><span class="bp-label">瘦脸</span><input type="range" min="0" max="100" value="12" id="sliderSlim"></div>
        <div class="bp-row"><span class="bp-label">美牙</span><input type="range" min="0" max="100" value="20" id="sliderTeeth"></div>
        <div class="bp-row"><span class="bp-label">磨皮</span><input type="range" min="0" max="100" value="10" id="sliderSmooth"></div>
    </div>

    <!-- 录制确认面板（16:9 固定） -->
    <div class="modal-overlay" id="settingsModal">
        <div class="modal">
            <button class="close-btn" id="closeSettings">&times;</button>
            <h2>开始录制</h2>
            <div class="info-box">
                <strong>16:9 全屏录制</strong><br>
                点击开始后选择当前标签页。录完自动下载 webm 文件。<br>
                各平台（视频号/小红书/抖音）都支持 16:9 横屏上传。
            </div>
            <button class="start-rec-btn" id="startRecBtn">
                <div style="width:10px;height:10px;border-radius:50%;background:white;"></div>
                开始录制
            </button>
        </div>
    </div>

    <!-- 导航栏 -->
    <div class="nav-bar">
        <button class="nav-overview active" id="navOverview" title="全景">⊞</button>
        <!-- cc 生成 9 个导航点 -->
        <button class="nav-dot" data-idx="0">1</button>
        <button class="nav-dot" data-idx="1">2</button>
        <button class="nav-dot" data-idx="2">3</button>
        <button class="nav-dot" data-idx="3">4</button>
        <button class="nav-dot" data-idx="4">5</button>
        <button class="nav-dot" data-idx="5">6</button>
        <button class="nav-dot" data-idx="6">7</button>
        <button class="nav-dot" data-idx="7">8</button>
        <button class="nav-dot" data-idx="8">9</button>
        <div class="nav-web-sep" id="navWebSep"></div>
        <!-- 动态网站导航点由 JS 插入此处 -->
    </div>

    <!-- 画布 -->
    <div class="world" id="world">
        <!-- 连接线（固定，不用改） -->
        <div class="connector" style="left:540px;top:400px;"><svg width="180" height="60"><path d="M0,30 C40,10 80,50 160,20"/></svg></div>
        <div class="connector" style="left:820px;top:480px;"><svg width="60" height="100"><path d="M30,0 C10,30 50,70 30,100"/></svg></div>
        <div class="connector" style="left:1050px;top:280px;"><svg width="180" height="60"><path d="M0,40 C50,10 100,50 170,20"/></svg></div>
        <div class="connector" style="left:1370px;top:580px;"><svg width="60" height="120"><path d="M30,0 C50,40 10,80 30,110"/></svg></div>
        <div class="connector" style="left:1640px;top:300px;"><svg width="180" height="60"><path d="M0,30 C50,5 100,55 160,25"/></svg></div>
        <div class="connector" style="left:1860px;top:520px;"><svg width="60" height="120"><path d="M30,0 C10,40 50,80 30,110"/></svg></div>
        <div class="connector" style="left:2200px;top:350px;"><svg width="180" height="60"><path d="M0,35 C50,5 100,55 160,20"/></svg></div>
        <div class="connector" style="left:2540px;top:560px;"><svg width="60" height="120"><path d="M30,0 C50,40 10,80 30,110"/></svg></div>

        <!-- ========== 9 张卡片（cc 根据文章内容填充） ========== -->
        <!-- 下方是每张卡片的 HTML 结构示例 -->
    </div>
</body>
```

---

## 9 张卡片内容规范

cc 根据文章内容选择每张卡片的内容。以下是每种卡片的 HTML 结构和适用场景。

### c1 — 标题卡（墨绿底，大字，红色强调）

**适用**：主标题 + hook，必须有冲击力

```html
<div class="card c1" data-idx="0">
    <div class="tape tape-tl tape-w100 tape-green"></div>
    <div class="tape tape-tr tape-w80 tape-red"></div>
    <div class="logo">01fish · #{{NUMBER}}</div>
    <h1>{{标题第一行}}<br>{{标题第二行}}<br><em>{{红色强调词}}</em></h1>
    <div class="sub">{{副标题/数据摘要}}</div>
    <div class="sticky sticky-y" style="bottom:-18px;right:-8px;transform:rotate(4deg);font-size:15px;">{{便签文字}} →</div>
</div>
```

### c2 — 数据卡（白底，大数字，印章）

**适用**：核心数据展示，用一个大数字震撼

```html
<div class="card c2" data-idx="1">
    <div class="tape tape-tl tape-w80 tape-green"></div>
    <div class="tape tape-br tape-w80 tape-red"></div>
    <div class="num">{{核心数字}}</div>
    <div class="lbl">{{单位/标签}}</div>
    <div class="det">{{补充数据}}<br>{{补充数据}}</div>
    <div class="stamp">{{印章文字}}</div>
    <div class="sticky sticky-p" style="bottom:-14px;left:-8px;font-size:13px;transform:rotate(-3deg);">{{便签}}</div>
</div>
```

### c3 — 痛点/问题卡（白底，条纹列表，金句底栏）

**适用**：为什么？痛点列举 + 一句话总结

```html
<div class="card c3" data-idx="2">
    <div class="tape tape-tl tape-w100 tape-red"></div>
    <div class="tape tape-tr tape-w80 tape-green"></div>
    <h2>{{问题标题}}</h2>
    <div class="strip">✗ {{痛点1}}</div>
    <div class="strip">✗ {{痛点2}}</div>
    <div class="strip">✗ {{痛点3}}</div>
    <div class="punchline">{{总结}}<br>是 <span>「{{核心洞察}}」</span> 的不够</div>
    <div class="sticky sticky-g" style="bottom:-12px;right:-6px;font-size:13px;transform:rotate(3deg);">{{便签}}</div>
</div>
```

### c4 — 步骤卡（墨绿底，ticket列表）

**适用**：怎么做？操作流程，3-4步

```html
<div class="card c4" data-idx="3">
    <div class="tape tape-tl tape-w80" style="background:rgba(242,237,227,0.08);"></div>
    <h2>{{步骤标题}}</h2>
    <div class="ticket"><span class="tnum">1</span><div class="tbody"><h3>{{步骤1标题}}</h3><p>{{步骤1描述}}</p></div></div>
    <div class="ticket"><span class="tnum">2</span><div class="tbody"><h3>{{步骤2标题}}</h3><p>{{步骤2描述}}</p></div></div>
    <div class="ticket"><span class="tnum">3</span><div class="tbody"><h3>{{步骤3标题}}</h3><p>{{步骤3描述}}</p></div></div>
    <div class="foot" style="color:#7A8C80;">{{底部小字}}</div>
    <div class="sticky sticky-y" style="bottom:-16px;right:-6px;font-size:13px;transform:rotate(3deg);">{{便签}}</div>
</div>
```

### c5 — 架构卡（白底，流程框+胶带）

**适用**：技术原理、架构拆解，2-3个流程框

```html
<div class="card c5" data-idx="4">
    <div class="tape tape-tl tape-w100 tape-green"></div>
    <div class="tape tape-br tape-w80 tape-red"></div>
    <h2>{{架构标题}}</h2>
    <div class="abox"><div class="mt red"></div><h3>① {{层级1}}</h3><p>{{描述}}</p></div>
    <div class="aconn">↓</div>
    <div class="abox"><div class="mt grn"></div><h3>② {{层级2}}</h3><p>{{描述}}</p></div>
    <div class="aconn">↓</div>
    <div class="abox"><div class="mt red"></div><h3>③ {{层级3}}</h3><p>{{描述}}</p></div>
    <div class="sticky sticky-y" style="bottom:-14px;right:-6px;font-size:12px;transform:rotate(3deg);">{{便签}}</div>
</div>
```

### c6 — 数据/对比卡（白底，小票 receipt）

**适用**：算账、成本对比、数据拆解

```html
<div class="card c6" data-idx="5">
    <div class="tape tape-tl tape-w80 tape-red"></div>
    <h2>{{对比标题}} 🧾</h2>
    <div class="receipt">
        <div class="rrow"><span>{{项目1}}</span><span class="v r">{{数据1}}</span></div>
        <div class="rrow"><span>{{项目2}}</span><span class="v">{{数据2}}</span></div>
        <div class="rrow"><span>{{项目3}}</span><span class="v">{{数据3}}</span></div>
        <div class="rtotal"><span>TOTAL</span><span>{{总结}}</span></div>
    </div>
    <div class="fnote">{{脚注}}</div>
</div>
```

### c7 — 金句卡（墨绿底，大引号）

**适用**：核心金句、洞察、类比

```html
<div class="card c7" data-idx="6">
    <div class="tape tape-tl tape-w80" style="background:rgba(242,237,227,0.08);"></div>
    <div class="tape tape-br tape-w80 tape-red"></div>
    <div class="qm">"</div>
    <div class="qt">{{金句上半}}<br><em>{{红色强调部分}}</em></div>
    <div class="qs">{{金句解读/类比}}</div>
</div>
```

### c8 — 闭环/特色卡（白底，标签流）

**适用**：亮点展示、结果闭环、特色功能

```html
<div class="card c8" data-idx="7">
    <div class="tape tape-tl tape-w100 tape-green"></div>
    <div class="tape tape-tr tape-w80 tape-red"></div>
    <h2>{{闭环标题}}</h2>
    <div class="trk"><div class="tag em">{{emoji}}</div><span class="arr">→</span><div class="tag hot">{{核心动作}}</div><span class="arr">→</span><div class="tag">{{结果}}</div></div>
    <div class="trk"><div class="tag em">{{emoji}}</div><span class="arr">→</span><div class="tag hot">{{核心动作}}</div><span class="arr">→</span><div class="tag">{{结果}}</div></div>
    <div class="trk"><div class="tag em">{{emoji}}</div><span class="arr">→</span><div class="tag hot">{{核心动作}}</div><span class="arr">→</span><div class="tag">{{结果}}</div></div>
    <div class="ins">{{一句话总结}}</div>
</div>
```

### c9 — CTA卡（墨绿底，品牌）

**适用**：固定结尾，关注 01fish。内容基本不变，只改预告。

```html
<div class="card c9" data-idx="8">
    <div class="tape tape-tl tape-w80" style="background:rgba(242,237,227,0.08);"></div>
    <div class="tape tape-br tape-w80 tape-red"></div>
    <div class="fish">🐟</div>
    <div class="brand">01fish</div>
    <div class="sl">造东西的人<br>记录造东西的故事</div>
    <div class="cta">关注 01fish</div>
    <div class="sticky sticky-y" style="bottom:-14px;left:-8px;font-size:13px;transform:rotate(-4deg);">{{下期预告}}</div>
</div>
```

---

## 提词器脚本规范

cc 为每张卡片生成一段口播文案，存入 `SCRIPTS` 数组。格式要求：

- 每段对应一张卡片（共 9 段）
- 用 `\n` 换行
- `[提示]` 标记会渲染为灰色小字（给主播看的 cue，不念出来）
- 口语化，像跟朋友说话，不要播音腔
- 每段 30-60 秒的量（约 80-150 字）

**示例格式**：

```js
const SCRIPTS = [
    `{{第1张卡片的口播文案}}\n\n[看镜头，停一拍]`,
    `{{第2张卡片的口播文案}}\n\n[让数字沉一下]`,
    `{{第3张卡片的口播文案}}\n\n[语气坚定]`,
    `{{第4张卡片的口播文案}}\n\n[轻松语气]`,
    `{{第5张卡片的口播文案}}\n\n[节奏稍慢，讲清楚]`,
    `{{第6张卡片的口播文案}}\n\n[强调重点数字]`,
    `{{第7张卡片的口播文案}}\n\n[让金句落地]`,
    `{{第8张卡片的口播文案}}\n\n[语气从平到燃]`,
    `{{第9张卡片的口播文案}}\n\n[看镜头，干脆收]`
];
```

---

## JS 框架（~520行）

**重要：以下 JS 原样使用，cc 只需替换 `SCRIPTS` 数组和 `title` 中的编号/标题。**

```js
// ========================
// 提词器脚本（cc 替换此数组）
// ========================
const SCRIPTS = [
    // cc 生成 9 段口播文案
];

// ========================
// 画布导航
// ========================
const world = document.getElementById('world');
const cards = document.querySelectorAll('.card');
const dots = document.querySelectorAll('.nav-dot');
const navOverview = document.getElementById('navOverview');
const pageNum = document.getElementById('pageNum');
const hint = document.getElementById('hint');

let currentIdx = -1;

// 网站演示状态（提前声明避免 TDZ）
let webMode = false;
let currentWebIdx = -1;
const WEB_URLS = [];
const webLayer = document.getElementById('webLayer');
const webIframe = document.getElementById('webIframe');
const webBarUrl = document.getElementById('webBarUrl');
const webModal = document.getElementById('webModal');
const webUrlInput = document.getElementById('webUrlInput');
const webUrlList = document.getElementById('webUrlList');
const navWebSep = document.getElementById('navWebSep');
const navBar = document.querySelector('.nav-bar');

// 提前声明（避免 TDZ 错误）
let prompterWin = null;
let prompterDoc = null;
let prompterScrolling = false;
let prompterScrollTimer = null;

const vw = window.innerWidth, vh = window.innerHeight;
const worldW = 2900, worldH = 1100;
const overviewScale = Math.min(vw / worldW, vh / worldH) * 0.85;
const overviewX = (vw - worldW * overviewScale) / 2;
const overviewY = (vh - worldH * overviewScale) / 2;

let worldTx = overviewX, worldTy = overviewY, worldScale = overviewScale;

function setWorldTransform(tx, ty, s, animate) {
    worldTx = tx; worldTy = ty; worldScale = s;
    if (animate) world.style.transition = 'transform 0.7s cubic-bezier(0.25, 0.1, 0.25, 1)';
    world.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
}

function goOverview() {
    if (webMode) exitWebMode(true);
    currentIdx = -1;
    setWorldTransform(overviewX, overviewY, overviewScale, true);
    cards.forEach(c => c.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    clearWebNavActive();
    navOverview.classList.add('active');
    pageNum.textContent = '全景';
    updateTeleprompter();
}

function goCard(idx) {
    if (idx < 0 || idx >= cards.length) return;
    if (webMode) exitWebMode(true);
    currentIdx = idx;
    const card = cards[idx];
    const cl = parseFloat(card.style.left || card.offsetLeft);
    const ct = parseFloat(card.style.top || card.offsetTop);
    const cw = card.offsetWidth, ch = card.offsetHeight;
    const scale = Math.min(vw * 0.75 / cw, vh * 0.75 / ch);
    const tx = vw / 2 - (cl + cw / 2) * scale;
    const ty = vh / 2 - (ct + ch / 2) * scale;
    setWorldTransform(tx, ty, scale, true);
    cards.forEach(c => c.classList.remove('active'));
    card.classList.add('active');
    dots.forEach(d => d.classList.remove('active'));
    clearWebNavActive();
    dots[idx].classList.add('active');
    navOverview.classList.remove('active');
    pageNum.textContent = (idx + 1) + ' / ' + cards.length;
    updateTeleprompter();
}

cards.forEach(card => {
    card.addEventListener('click', () => {
        const idx = parseInt(card.dataset.idx);
        currentIdx === idx ? goOverview() : goCard(idx);
    });
});
dots.forEach(dot => dot.addEventListener('click', () => goCard(parseInt(dot.dataset.idx))));
navOverview.addEventListener('click', goOverview);

goOverview();

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { goOverview(); return; }
    if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        if (webMode) {
            if (currentWebIdx < WEB_URLS.length - 1) goWebsite(currentWebIdx + 1);
            else goOverview();
        } else if (currentIdx === cards.length - 1 && WEB_URLS.length > 0) {
            goWebsite(0);
        } else {
            currentIdx < cards.length - 1 ? goCard(currentIdx + 1) : goOverview();
        }
    }
    if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (webMode) {
            if (currentWebIdx > 0) goWebsite(currentWebIdx - 1);
            else goCard(cards.length - 1);
        } else {
            currentIdx > 0 ? goCard(currentIdx - 1) : currentIdx === 0 ? goOverview() : (WEB_URLS.length > 0 ? goWebsite(WEB_URLS.length - 1) : goCard(cards.length - 1));
        }
    }
});

setTimeout(() => hint.classList.add('hide'), 5000);

// ========================
// 画布拖拽
// ========================
let isDragging = false, dragStartX, dragStartY, dragStartTx, dragStartTy;
let dragMoved = false;

document.addEventListener('mousedown', e => {
    if (e.target.closest('.card, .toolbar, .nav-bar, .nav-dot, .nav-overview, .modal-overlay, .web-modal-overlay, .beauty-panel, .webcam-wrap, .cam-toggle, .rec-indicator, .web-layer, button')) return;
    isDragging = true;
    dragMoved = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragStartTx = worldTx;
    dragStartTy = worldTy;
    document.body.classList.add('dragging');
    e.preventDefault();
});

document.addEventListener('mousemove', e => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragMoved = true;
    worldTx = dragStartTx + dx;
    worldTy = dragStartTy + dy;
    world.style.transform = `translate(${worldTx}px, ${worldTy}px) scale(${worldScale})`;
});

document.addEventListener('mouseup', () => {
    if (!isDragging) return;
    isDragging = false;
    document.body.classList.remove('dragging');
});

// ========================
// 摄像头
// ========================
const webcam = document.getElementById('webcam');
const camVideo = document.getElementById('camVideo');
const camBtn = document.getElementById('camBtn');
const btnCamToggle = document.getElementById('btnCamToggle');
let camOn = false;

async function startCam() {
    try {
        camVideo.srcObject = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        camOn = true; camBtn.classList.add('on'); camBtn.textContent = '📷 ON';
        btnCamToggle.classList.add('active');
        webcam.classList.remove('off');
    } catch(e) { webcam.classList.add('off'); }
}
function stopCam() {
    if (camVideo.srcObject) camVideo.srcObject.getTracks().forEach(t => t.stop());
    camOn = false; camBtn.classList.remove('on'); camBtn.textContent = '📷';
    btnCamToggle.classList.remove('active');
    webcam.classList.add('off');
}
camBtn.addEventListener('click', () => camOn ? stopCam() : startCam());
btnCamToggle.addEventListener('click', () => camOn ? stopCam() : startCam());

startCam();

// 摄像头拖拽
(function initWebcamDrag() {
    let dragging = false, offsetX, offsetY;
    webcam.addEventListener('mousedown', e => {
        dragging = true;
        const rect = webcam.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;
        webcam.classList.add('dragging');
        e.preventDefault();
        e.stopPropagation();
    });
    document.addEventListener('mousemove', e => {
        if (!dragging) return;
        webcam.style.left = (e.clientX - offsetX) + 'px';
        webcam.style.top = (e.clientY - offsetY) + 'px';
        webcam.style.right = 'auto';
        webcam.style.bottom = 'auto';
    });
    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        webcam.classList.remove('dragging');
    });
})();

// ========================
// 提词器（Document PiP + 降级弹窗）
// ========================
const TELEPROMPTER_CSS = `
    * { margin:0; padding:0; box-sizing:border-box; }
    html, body { height:100%; }
    body { font-family:-apple-system,sans-serif; background:rgba(250,250,250,0.96); color:#333; display:flex; flex-direction:column; }
    .header { padding:12px 16px; background:white; border-bottom:1px solid #eee; display:flex; align-items:center; justify-content:space-between; }
    .header h2 { font-size:14px; color:#333; display:flex; align-items:center; gap:6px; }
    .page-label { font-size:13px; font-weight:700; color:#1A3328; }
    .controls { padding:10px 16px; background:white; border-bottom:1px solid #eee; }
    .ctrl-row { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
    .ctrl-row:last-child { margin-bottom:0; }
    .ctrl-label { font-size:12px; color:#666; min-width:50px; }
    .ctrl-row input[type=range] { flex:1; accent-color:#1A3328; }
    .play-btn { width:30px; height:30px; border-radius:50%; border:2px solid #1A3328; background:white; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:12px; }
    .play-btn:hover { background:#1A3328; color:white; }
    .script-area { padding:16px; flex:1; overflow-y:auto; }
    .script-text { font-size:20px; line-height:2.0; color:#222; white-space:pre-wrap; font-weight:500; }
    .script-text .cue { color:#999; font-size:14px; font-weight:400; }
    .note { padding:8px 16px; font-size:11px; color:#999; border-top:1px solid #eee; text-align:center; }
`;

const TELEPROMPTER_HTML = `
    <div class="header">
        <h2>📋 提词器</h2>
        <span class="page-label" id="pLabel">全景</span>
    </div>
    <div class="controls">
        <div class="ctrl-row">
            <button class="play-btn" id="playBtn">▶</button>
            <span class="ctrl-label">滚动</span>
            <input type="range" id="speedSlider" min="0" max="100" value="30">
        </div>
        <div class="ctrl-row">
            <span class="ctrl-label" style="margin-left:40px;">透明度</span>
            <input type="range" id="opacitySlider" min="20" max="100" value="85">
        </div>
    </div>
    <div class="script-area" id="scriptArea">
        <div class="script-text" id="scriptText">点击卡片开始...</div>
    </div>
    <div class="note">始终置顶 · 不会出现在录制中</div>
`;

async function openTeleprompter() {
    if (prompterWin && !prompterWin.closed) { prompterWin.focus(); return; }
    try {
        if ('documentPictureInPicture' in window) {
            prompterWin = await documentPictureInPicture.requestWindow({ width: 380, height: 480 });
            prompterDoc = prompterWin.document;
        } else { throw new Error('fallback'); }
    } catch(e) {
        prompterWin = window.open('', 'teleprompter', 'width=380,height=480,top=50,left=50');
        prompterDoc = prompterWin.document;
    }
    const style = prompterDoc.createElement('style');
    style.textContent = TELEPROMPTER_CSS;
    prompterDoc.head.appendChild(style);
    prompterDoc.body.innerHTML = TELEPROMPTER_HTML;
    setupTeleprompterEvents();
    updateTeleprompter();
}

function setupTeleprompterEvents() {
    if (!prompterDoc) return;
    const opacitySlider = prompterDoc.getElementById('opacitySlider');
    const playBtn = prompterDoc.getElementById('playBtn');
    const speedSlider = prompterDoc.getElementById('speedSlider');
    const scriptArea = prompterDoc.getElementById('scriptArea');
    if (opacitySlider) {
        opacitySlider.addEventListener('input', () => {
            prompterDoc.body.style.opacity = opacitySlider.value / 100;
        });
        prompterDoc.body.style.opacity = opacitySlider.value / 100;
    }
    if (playBtn) {
        playBtn.addEventListener('click', () => {
            prompterScrolling = !prompterScrolling;
            playBtn.textContent = prompterScrolling ? '⏸' : '▶';
            if (prompterScrolling) {
                prompterScrollTimer = setInterval(() => {
                    if (scriptArea) scriptArea.scrollTop += (parseInt(speedSlider.value) / 50);
                }, 16);
            } else { clearInterval(prompterScrollTimer); }
        });
    }
}

function updateTeleprompter() {
    if (!prompterDoc) return;
    try {
        let label, rawText;
        if (webMode) {
            label = `网站 ${currentWebIdx + 1} / ${WEB_URLS.length}`;
            rawText = `网站演示中\n\n${WEB_URLS[currentWebIdx] || ''}\n\n[自由演示，按 → 下一页，ESC 回全景]`;
        } else if (currentIdx === -1) {
            label = '全景';
            rawText = '点击卡片进入对应页面\n提词器会自动同步';
        } else {
            label = `第 ${currentIdx + 1} / ${cards.length}`;
            rawText = SCRIPTS[currentIdx] || '';
        }
        const html = rawText.replace(/\[([^\]]+)\]/g, '<span class="cue">[$1]</span>');
        const textEl = prompterDoc.getElementById('scriptText');
        const labelEl = prompterDoc.getElementById('pLabel');
        const areaEl = prompterDoc.getElementById('scriptArea');
        if (textEl) textEl.innerHTML = html;
        if (labelEl) labelEl.textContent = label;
        if (areaEl) areaEl.scrollTop = 0;
        if (prompterScrolling) {
            prompterScrolling = false;
            const btn = prompterDoc.getElementById('playBtn');
            if (btn) btn.textContent = '▶';
            clearInterval(prompterScrollTimer);
        }
    } catch(e) {}
}

document.getElementById('btnTeleprompter').addEventListener('click', openTeleprompter);

// ========================
// 网站演示
// ========================
function goWebsite(idx) {
    if (idx < 0 || idx >= WEB_URLS.length) return;
    webMode = true;
    currentWebIdx = idx;
    currentIdx = -1;
    world.style.display = 'none';
    webLayer.classList.add('show');
    webIframe.src = WEB_URLS[idx];
    webBarUrl.textContent = WEB_URLS[idx];
    cards.forEach(c => c.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    navOverview.classList.remove('active');
    clearWebNavActive();
    const webDots = navBar.querySelectorAll('.nav-dot-web');
    if (webDots[idx]) webDots[idx].classList.add('active');
    pageNum.textContent = `🌐 ${idx + 1} / ${WEB_URLS.length}`;
    updateTeleprompter();
}

function exitWebMode(silent) {
    webMode = false;
    currentWebIdx = -1;
    webLayer.classList.remove('show');
    webIframe.src = 'about:blank';
    world.style.display = '';
    clearWebNavActive();
}

function clearWebNavActive() {
    navBar.querySelectorAll('.nav-dot-web').forEach(d => d.classList.remove('active'));
}

function addWebUrl(url) {
    url = url.trim();
    if (!url) return;
    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
    WEB_URLS.push(url);
    renderWebUrlList();
    renderWebNavDots();
}

function removeWebUrl(idx) {
    WEB_URLS.splice(idx, 1);
    renderWebUrlList();
    renderWebNavDots();
    if (webMode && currentWebIdx >= WEB_URLS.length) goOverview();
}

function renderWebUrlList() {
    if (WEB_URLS.length === 0) {
        webUrlList.innerHTML = '<div class="web-url-empty">还没有添加网站</div>';
        return;
    }
    webUrlList.innerHTML = WEB_URLS.map((u, i) => `
        <div class="web-url-item">
            <span class="idx">${i + 1}</span>
            <span class="url-text">${u}</span>
            <button class="go-btn" data-go="${i}">前往</button>
            <button class="del-btn" data-del="${i}">✕</button>
        </div>
    `).join('');
    webUrlList.querySelectorAll('.go-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            webModal.classList.remove('show');
            goWebsite(parseInt(btn.dataset.go));
        });
    });
    webUrlList.querySelectorAll('.del-btn').forEach(btn => {
        btn.addEventListener('click', () => removeWebUrl(parseInt(btn.dataset.del)));
    });
}

function renderWebNavDots() {
    navBar.querySelectorAll('.nav-dot-web').forEach(d => d.remove());
    navWebSep.classList.toggle('show', WEB_URLS.length > 0);
    WEB_URLS.forEach((u, i) => {
        const btn = document.createElement('button');
        btn.className = 'nav-dot-web';
        btn.dataset.webIdx = i;
        btn.textContent = '🌐';
        btn.title = u;
        btn.addEventListener('click', () => goWebsite(i));
        navBar.appendChild(btn);
    });
}

document.getElementById('btnWebsite').addEventListener('click', () => webModal.classList.add('show'));
document.getElementById('closeWebModal').addEventListener('click', () => webModal.classList.remove('show'));
document.getElementById('webUrlAddBtn').addEventListener('click', () => {
    addWebUrl(webUrlInput.value);
    webUrlInput.value = '';
});
webUrlInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addWebUrl(webUrlInput.value);
        webUrlInput.value = '';
    }
});
document.getElementById('webBarBack').addEventListener('click', goOverview);

// ========================
// 录制面板
// ========================
const settingsModal = document.getElementById('settingsModal');
const btnRecord = document.getElementById('btnRecord');
const recIndicator = document.getElementById('recIndicator');
const recTimer = document.getElementById('recTimer');

btnRecord.addEventListener('click', () => settingsModal.classList.add('show'));
document.getElementById('closeSettings').addEventListener('click', () => settingsModal.classList.remove('show'));

document.getElementById('startRecBtn').addEventListener('click', () => {
    settingsModal.classList.remove('show');
    actualStartRecording();
});

recIndicator.addEventListener('click', stopRecording);

// ========================
// 录制功能
// ========================
let mediaRecorder = null;
let recordedChunks = [];
let recStartTime = 0;
let recTimerInterval = null;

async function actualStartRecording() {
    try {
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
            video: { displaySurface: 'browser' },
            audio: false,
            preferCurrentTab: true,
            selfBrowserSurface: 'include',
            systemAudio: 'exclude'
        });
        let micStream = null;
        try {
            micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        } catch(e) { console.warn('麦克风不可用，仅录制画面'); }
        const tracks = [...displayStream.getVideoTracks()];
        if (micStream) tracks.push(...micStream.getAudioTracks());
        const combinedStream = new MediaStream(tracks);
        recordedChunks = [];
        const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
            ? 'video/webm;codecs=vp9,opus' : 'video/webm';
        mediaRecorder = new MediaRecorder(combinedStream, { mimeType });
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
        mediaRecorder.onstop = saveRecording;
        displayStream.getVideoTracks()[0].onended = () => stopRecording();
        mediaRecorder.start(100);
        document.body.classList.add('recording');
        recStartTime = Date.now();
        recTimerInterval = setInterval(updateRecTimer, 200);
    } catch(e) {
        if (e.name !== 'NotAllowedError') alert('录制启动失败: ' + e.message);
    }
}

function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    document.body.classList.remove('recording');
    clearInterval(recTimerInterval);
}

function saveRecording() {
    const blob = new Blob(recordedChunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().slice(0,19).replace(/[T:]/g, '-');
    a.href = url;
    a.download = `01fish-{{NUMBER}}-${ts}.webm`;
    a.click();
    URL.revokeObjectURL(url);
    recordedChunks = [];
}

function updateRecTimer() {
    const elapsed = Math.floor((Date.now() - recStartTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    recTimer.textContent = `${m}:${s}`;
}

// ========================
// 美颜滤镜
// ========================
const beautyPanel = document.getElementById('beautyPanel');
const sliderWhiten = document.getElementById('sliderWhiten');
const sliderSlim = document.getElementById('sliderSlim');
const sliderTeeth = document.getElementById('sliderTeeth');
const sliderSmooth = document.getElementById('sliderSmooth');

document.getElementById('btnBeauty').addEventListener('click', () => {
    beautyPanel.classList.toggle('show');
});

function applyBeauty() {
    const w = parseInt(sliderWhiten.value);
    const t = parseInt(sliderTeeth.value);
    const sm = parseInt(sliderSmooth.value);
    const sl = parseInt(sliderSlim.value);
    const brightness = 1 + w * 0.004;
    const saturate = Math.max(0.65, 1 - w * 0.0035);
    const contrast = 1 + t * 0.006;
    const blur = sm * 0.03;
    // 瘦脸：视频始终放大 1.2x 撑满圆框，靠 X/Y 比例差实现瘦脸
    const slimFactor = 1 - sl * 0.0015;
    const base = 1.2;
    const sx = -(base * slimFactor);  // 镜像 + 横向压缩
    const sy = base;                   // 纵向不变
    camVideo.style.filter = `brightness(${brightness}) saturate(${saturate}) contrast(${contrast}) blur(${blur}px)`;
    camVideo.style.transform = `scale(${sx}, ${sy})`;
}

[sliderWhiten, sliderSlim, sliderTeeth, sliderSmooth].forEach(s => {
    s.addEventListener('input', applyBeauty);
});
applyBeauty();

// ========================
// 实时字幕（Web Speech API）
// ========================
const subtitleBar = document.getElementById('subtitleBar');
const subtitleText = document.getElementById('subtitleText');
const btnSubtitle = document.getElementById('btnSubtitle');
let subtitleOn = false;
let recognition = null;
let subtitleClearTimer = null;

function startSubtitle() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('当前浏览器不支持语音识别，请使用 Chrome'); return; }
    recognition = new SR();
    recognition.lang = 'zh-CN';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = e => {
        let interim = '', final = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
            const t = e.results[i][0].transcript;
            if (e.results[i].isFinal) final += t;
            else interim += t;
        }
        subtitleText.textContent = final || interim;
        clearTimeout(subtitleClearTimer);
        if (final) {
            subtitleClearTimer = setTimeout(() => { subtitleText.textContent = ''; }, 3000);
        }
    };
    recognition.onerror = e => {
        if (e.error === 'no-speech') return;
        console.warn('语音识别错误:', e.error);
    };
    recognition.onend = () => {
        if (subtitleOn) recognition.start();
    };
    recognition.start();
    subtitleOn = true;
    subtitleBar.classList.add('show');
    btnSubtitle.classList.add('active');
}

function stopSubtitle() {
    subtitleOn = false;
    if (recognition) { recognition.abort(); recognition = null; }
    subtitleBar.classList.remove('show');
    subtitleText.textContent = '';
    btnSubtitle.classList.remove('active');
    clearTimeout(subtitleClearTimer);
}

btnSubtitle.addEventListener('click', () => subtitleOn ? stopSubtitle() : startSubtitle());

```

---

## cc 生成流程

1. **读取素材**：根据输入类型获取文章内容
2. **分析结构**：提取标题、核心数据、痛点、步骤、原理、对比、金句、亮点
3. **填充 9 张卡片**：根据文章内容选择每张卡片类型中的具体内容
4. **生成 9 段提词器脚本**：口语化，每段 80-150 字
5. **输出提词器脚本 md**：`[简短主题]-提词器脚本.md`，用户可直接编辑修改
6. **组装 HTML**：CSS 框架 + HTML 骨架 + 卡片内容 + JS 框架（SCRIPTS 数组内容与 md 一致）
7. **输出文件**：`[简短主题]-视频画布.html`
8. **生成封面图**：`[简短主题]-封面.html`，浏览器打开后可截图/下载为 PNG
9. **提示用户**：先检查提词器脚本 md，再在浏览器中打开 HTML 录制

> **用户修改提词器脚本后**：告诉 cc "更新提词器"，cc 读取修改后的 md，重新写入 HTML 的 SCRIPTS 数组。

### 输出文件命名

- 默认路径：文章同目录，或 `/tmp/`
- 视频画布：`[简短主题]-视频画布.html`
- 提词器脚本：`[简短主题]-提词器脚本.md`
- 封面图：`[简短主题]-封面.html`
- 示例：`AI印书厂-视频画布.html` + `AI印书厂-提词器脚本.md` + `AI印书厂-封面.html`

---

## 提词器脚本 md 格式

cc 输出的 md 文件格式如下，用户可直接编辑后让 cc 更新到 HTML：

```markdown
# {{主题}} — 提词器脚本

> 每张卡片对应一段口播文案。`[方括号]` 内是给自己看的提示，不念出来。
> 修改后告诉 cc "更新提词器"，会自动同步到视频画布 HTML。

---

## 第 1 页 · 标题卡

{{口播文案}}

[看镜头，停一拍]

---

## 第 2 页 · 数据卡

{{口播文案}}

[让数字沉一下]

---

## 第 3 页 · 痛点卡

{{口播文案}}

[语气坚定]

---

## 第 4 页 · 步骤卡

{{口播文案}}

[轻松语气]

---

## 第 5 页 · 架构卡

{{口播文案}}

[节奏稍慢，讲清楚]

---

## 第 6 页 · 对比卡

{{口播文案}}

[强调重点数字]

---

## 第 7 页 · 金句卡

{{口播文案}}

[让金句落地]

---

## 第 8 页 · 闭环卡

{{口播文案}}

[语气从平到燃]

---

## 第 9 页 · CTA卡

{{口播文案}}

[看镜头，干脆收]
```

### cc 解析规则

读取用户修改后的 md 时：
1. 按 `## 第 N 页` 分割为 9 段
2. 每段内容（去掉标题行和分隔线）作为 `SCRIPTS[N-1]` 的值
3. `\n` 保留原始换行
4. `[方括号内容]` 保留，HTML 中会渲染为灰色提示

### 录制文件命名

HTML 内部自动命名下载文件为 `01fish-{{NUMBER}}-{{时间戳}}.webm`，cc 生成时把 `{{NUMBER}}` 替换为实际期号。固定 16:9 比例，各平台都可直接上传。

---

## 封面图规范（与文章封面统一风格）

cc 同时生成一个独立的封面 HTML 文件（3:4 竖版，1080x1440），适合小红书/视频号封面。风格与文章封面（900x383 横版）保持一致：暗底 + 渐变遮罩 + 左对齐排版 + 品牌角标 + 底部标签。

### 设计要素

| 要素 | 规范 |
|------|------|
| **尺寸** | 1080x1440 (3:4 竖版) |
| **底色** | `#111` 暗底（与文章封面一致），叠加微弱方格纸底纹 |
| **渐变遮罩** | 顶部红色光晕 `radial-gradient` + 上下暗角 `linear-gradient`（与文章封面渐变手法一致） |
| **标签 .tag** | 左上方，`rgba(196,69,54,0.3)` 底 + 粉白字，15px，全大写英文 |
| **标题 .title** | 左对齐，72px 白色 + `.mega` 110px 鱼红 `#ff5a43`，带 `text-shadow` 发光 |
| **副标题 .subtitle** | 24px，`rgba(255,255,255,0.55)`，标题下方 |
| **数据行 .stats** | `.stat-num` 48px 鱼红 + `.stat-unit` 18px 半透明白，斜杠分隔 |
| **品牌角标 .brand** | 左上角 01fish SVG + 文字，`rgba(255,255,255,0.4)` |
| **人像区 .portrait** | 右下角圆框（180px），`rgba(255,255,255,0.15)` 边框，暗底占位 |
| **底部标签 .bottom-tags** | 左下角 `.btag` 标签组，`rgba(255,255,255,0.06)` 底，13px |
| **下载方式** | html2canvas，scale: 2，输出 PNG |

### 封面 HTML 模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{{主题}} - 封面</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            width: 1080px; height: 1440px; overflow: hidden;
            background: #111;
            font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            position: relative;
        }

        /* 方格纸底纹（轻手绘感） */
        .grid-bg {
            position: absolute; inset: 0;
            background-image:
                linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px);
            background-size: 28px 28px;
        }

        /* 渐变遮罩（与文章封面一致的暗角处理） */
        .overlay {
            position: absolute; inset: 0; z-index: 2;
            background:
                radial-gradient(ellipse at 50% 30%, rgba(196,69,54,0.12) 0%, transparent 60%),
                linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.4) 100%);
        }

        /* 品牌角标（与文章封面一致） */
        .brand {
            position: absolute; top: 40px; left: 55px;
            display: flex; align-items: center; gap: 10px; z-index: 20;
        }
        .brand svg { width: 28px; height: 28px; }
        .brand-text {
            font-size: 15px; font-weight: 600;
            color: rgba(255,255,255,0.4); letter-spacing: 1.5px;
        }

        /* 内容区（左对齐，与文章封面统一） */
        .content {
            position: absolute; inset: 0; z-index: 10;
            display: flex; flex-direction: column; justify-content: center;
            padding: 0 0 0 70px;
        }

        /* 标签（与文章封面 .tag 一致） */
        .tag {
            display: inline-block; width: fit-content;
            font-size: 15px; font-weight: 700; letter-spacing: 3px;
            padding: 6px 16px; border-radius: 5px;
            background: rgba(196,69,54,0.3); color: rgba(255,200,190,0.9);
            margin-bottom: 28px;
        }

        /* 主标题（放大版文章封面 .title，爆炸感） */
        .title {
            font-size: 72px; font-weight: 900; color: #fff; line-height: 1.15;
            max-width: 780px;
        }
        .title .red { color: #ff5a43; }
        .title .mega {
            font-size: 110px; display: block; font-weight: 900;
            color: #ff5a43;
            text-shadow: 0 0 40px rgba(196,69,54,0.4);
            margin: 8px 0 4px;
        }

        /* 副标题（与文章封面 .subtitle 一致） */
        .subtitle {
            font-size: 24px; color: rgba(255,255,255,0.55);
            margin-top: 20px; font-weight: 400;
        }

        /* 数据行（与文章封面 .stats 一致） */
        .stats {
            display: flex; gap: 28px; margin-top: 28px; align-items: baseline;
        }
        .stat-num {
            font-size: 48px; font-weight: 900; color: #ff5a43;
            text-shadow: 0 0 20px rgba(196,69,54,0.4);
        }
        .stat-unit {
            font-size: 18px; color: rgba(255,255,255,0.5);
            font-weight: 500; margin-left: 4px;
        }
        .stat-sep {
            color: rgba(255,255,255,0.2); font-size: 28px;
        }

        /* 人像圆框 */
        .portrait {
            position: absolute; bottom: 100px; right: 80px; z-index: 20;
            width: 180px; height: 180px; border-radius: 50%;
            border: 3px solid rgba(255,255,255,0.15); overflow: hidden;
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
            background: #1a1a1a;
            display: flex; align-items: center; justify-content: center;
        }
        .portrait .placeholder { font-size: 64px; }
        .portrait img { width: 100%; height: 100%; object-fit: cover; }

        /* 底部标签（与文章封面 .bottom-tags 一致） */
        .bottom-tags {
            position: absolute; bottom: 40px; left: 55px;
            display: flex; gap: 10px; z-index: 20;
        }
        .btag {
            font-size: 13px; color: rgba(255,255,255,0.3);
            padding: 5px 12px;
            background: rgba(255,255,255,0.06); border-radius: 4px;
        }

        /* 下载栏 */
        .download-bar {
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(0,0,0,0.85); padding: 12px;
            text-align: center; z-index: 100;
        }
        .download-bar button {
            background: #C44536; color: white; border: none;
            padding: 10px 32px; border-radius: 8px;
            font-size: 14px; font-weight: 700; cursor: pointer;
        }
        .download-bar button:hover { background: #d95545; }
    </style>
</head>
<body>
    <div class="grid-bg"></div>
    <div class="overlay"></div>

    <!-- 品牌角标（与文章封面一致） -->
    <div class="brand">
        <svg viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="rgba(255,255,255,0.3)" stroke-width="1.5" fill="none"/>
            <text x="16" y="21" text-anchor="middle" font-size="16" fill="rgba(255,255,255,0.5)">🐟</text>
        </svg>
        <span class="brand-text">01fish</span>
    </div>

    <!-- 主内容（左对齐层次结构） -->
    <div class="content">
        <div class="tag">{{TAG英文，如 AUTO WRITER × OPENCLAW}}</div>
        <div class="title">
            {{标题前半}}
            <span class="mega">{{爆炸核心词}}</span>
        </div>
        <div class="subtitle">{{副标题描述}}</div>
        <div class="stats">
            <span class="stat-num">{{数据1}}</span><span class="stat-unit">{{单位1}}</span>
            <span class="stat-sep">/</span>
            <span class="stat-num">{{数据2}}</span><span class="stat-unit">{{单位2}}</span>
        </div>
    </div>

    <!-- 人像出镜 -->
    <div class="portrait">
        <div class="placeholder">🐟</div>
        <!-- 有照片时: <img src="portrait.jpg" alt=""> -->
    </div>

    <!-- 底部标签 -->
    <div class="bottom-tags">
        <span class="btag">{{标签1}}</span>
        <span class="btag">{{标签2}}</span>
        <span class="btag">{{标签3}}</span>
        <span class="btag">{{标签4}}</span>
    </div>

    <div class="download-bar">
        <button onclick="downloadCover()">下载封面 PNG (1080×1440)</button>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
    <script>
        async function downloadCover() {
            const bar = document.querySelector('.download-bar');
            bar.style.display = 'none';
            const canvas = await html2canvas(document.body, { scale: 2, width: 1080, height: 1440 });
            bar.style.display = '';
            const a = document.createElement('a');
            a.download = '{{简短主题}}-封面.png';
            a.href = canvas.toDataURL('image/png');
            a.click();
        }
    </script>
</body>
</html>
```

### 人像处理

| 情况 | 处理 |
|------|------|
| 用户提供了照片路径 | `<img src="照片路径">` 填入 `.portrait`，删掉 `.placeholder` |
| 用户没提供照片 | 保留 `.placeholder`（🐟 占位），提示用户后续替换 |
| 用户说"用摄像头截图" | 提示在视频画布中开摄像头截一张 |

### 封面文字规则

- `.tag`：用英文关键词组合（如 `AUTO WRITER × OPENCLAW`），全大写，与文章封面一致
- `.title`：标题前半用白色，核心爆点用 `.mega`（110px 鱼红），与 c1（标题卡）内容一致
- `.subtitle`：一句话补充说明，24px 半透明白
- `.stats`：1-2 组核心数据（数字鱼红 + 单位半透明），可选
- `.bottom-tags`：3-4 个技术/主题标签，与文章封面底部标签一致
- 封面要在手机小图上也能看清标题，不要放太多文字
