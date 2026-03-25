# 视频画布模板参考（录屏 + 露脸 + 提词器）

> cc 生成视频画布 HTML 时读取此文件。模板是一个纯粹的网页演示录制工具：
> 全屏 iframe 演示网页 + 角落摄像头露脸 + 提词器看脚本 + 一键录制。
> cc 根据用户提供的网址列表预填 URL，并为每个网站生成一段提词器脚本。

---

## 输入

用户提供：
1. **要演示的网址列表**（1-N 个 URL）
2. **简短主题**（用于文件命名和提词器脚本主题）

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

2. **let 变量 TDZ**：所有 `let` 变量声明必须在函数调用之前，否则触发 Temporal Dead Zone 错误。

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
    <title>{{TITLE}} - 录屏画布</title>
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

## CSS 框架

```css
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; background: #E8E3D9; }

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

/* === 录制状态 === */
body.recording .toolbar { display: none !important; }
body.recording .hint { display: none !important; }

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

/* 提示 */
.hint { position: fixed; top: 20px; left: 28px; font-size: 13px; color: #7A8C80; z-index: 300; transition: opacity 0.5s; }
.hint.hide { opacity: 0; pointer-events: none; }

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
.modal .info-box {
    background: #f8f8f8; border-radius: 10px; padding: 14px 16px;
    margin-bottom: 20px; font-size: 13px; color: #666; line-height: 1.6;
}
.modal .info-box strong { color: #1A3328; }
.modal .start-rec-btn {
    width: 100%; padding: 14px; border-radius: 12px; border: none;
    background: #C44536; color: white; font-size: 16px; font-weight: 700;
    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
}
.modal .start-rec-btn:hover { background: #a33828; }

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

/* === 网站演示层（全屏） === */
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

/* === 导航栏 === */
.nav-bar {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 6px; z-index: 300;
    background: rgba(26,51,40,0.9); padding: 8px 16px; border-radius: 28px;
    backdrop-filter: blur(12px);
}
body.recording .nav-bar { display: none !important; }
.nav-dot-web {
    width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(242,237,227,0.3);
    background: transparent; color: #F2EDE3; font-size: 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.3s;
}
.nav-dot-web:hover { border-color: #F2EDE3; background: rgba(242,237,227,0.1); }
.nav-dot-web.active { background: #C44536; border-color: #C44536; }

/* === 欢迎页（无网站时显示） === */
.welcome {
    position: fixed; inset: 0; z-index: 50;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #F2EDE3; text-align: center;
}
.welcome.hide { display: none; }
.welcome h1 { font-size: 36px; color: #1A3328; font-weight: 900; margin-bottom: 12px; }
.welcome p { font-size: 16px; color: #7A8C80; margin-bottom: 32px; }
.welcome .start-btn {
    padding: 14px 36px; border-radius: 12px; border: none;
    background: #1A3328; color: #F2EDE3; font-size: 16px; font-weight: 700;
    cursor: pointer;
}
.welcome .start-btn:hover { background: #2a4a3a; }

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
    <div class="hint" id="hint">🌐 导航点切换网站 · ← → 翻页 · 📋 提词器</div>

    <!-- 欢迎页（无网站时显示） -->
    <div class="welcome" id="welcome">
        <h1>录屏画布</h1>
        <p>添加要演示的网站，开始录制</p>
        <button class="start-btn" id="welcomeStartBtn">选择网站</button>
    </div>

    <!-- 摄像头 -->
    <div class="webcam-wrap off" id="webcam"><video id="camVideo" autoplay playsinline muted></video></div>

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

    <!-- 网站演示层（全屏 iframe） -->
    <div class="web-layer" id="webLayer">
        <div class="web-bar">
            <span class="web-bar-url" id="webBarUrl">—</span>
            <button class="web-bar-btn" id="webBarManage" title="管理网站">管理网站</button>
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

    <!-- 录制确认面板 -->
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

    <!-- 导航栏（只有网站导航点，由 JS 动态渲染） -->
    <div class="nav-bar" id="navBar"></div>
</body>
```

---

## 提词器脚本规范

cc 为每个网站生成一段口播文案，存入 `SCRIPTS` 对象。格式要求：

- 每段对应一个网站（key 为 URL）
- 用 `\n` 换行
- `[提示]` 标记会渲染为灰色小字（给主播看的 cue，不念出来）
- 口语化，像跟朋友说话，不要播音腔
- 每段 30-60 秒的量（约 80-150 字）

**示例格式**：

```js
const SCRIPTS = {
    'https://example.com': `这是第一个要演示的网站...\n\n[打开首页，展示主功能]`,
    'https://app.example.com': `接下来看看实际的应用...\n\n[切换到仪表盘页面]`,
};
```

---

## JS 框架

**重要：以下 JS 原样使用，cc 只需替换 `WEB_URLS` 数组（预填网址）和 `SCRIPTS` 对象（提词器脚本）。**

```js
// ========================
// 预填网址（cc 替换此数组）
// ========================
const WEB_URLS = [
    // cc 预填用户提供的网址
];

// ========================
// 提词器脚本（cc 替换此对象）
// ========================
const SCRIPTS = {
    // cc 生成每个网站对应的口播文案
    // key: URL, value: 脚本文本
};

// ========================
// DOM 引用
// ========================
const webLayer = document.getElementById('webLayer');
const webIframe = document.getElementById('webIframe');
const webBarUrl = document.getElementById('webBarUrl');
const webModal = document.getElementById('webModal');
const webUrlInput = document.getElementById('webUrlInput');
const webUrlList = document.getElementById('webUrlList');
const navBar = document.getElementById('navBar');
const welcome = document.getElementById('welcome');
const hint = document.getElementById('hint');

// 提前声明（避免 TDZ 错误）
let prompterWin = null;
let prompterDoc = null;
let prompterScrolling = false;
let prompterScrollTimer = null;

let currentWebIdx = -1;

// ========================
// 网站导航
// ========================
function goWebsite(idx) {
    if (idx < 0 || idx >= WEB_URLS.length) return;
    currentWebIdx = idx;
    welcome.classList.add('hide');
    webLayer.classList.add('show');
    webIframe.src = WEB_URLS[idx];
    webBarUrl.textContent = WEB_URLS[idx];
    renderWebNavDots();
    updateTeleprompter();
}

function updateWelcome() {
    if (WEB_URLS.length > 0) {
        // 有网站时直接显示第一个
        if (currentWebIdx === -1) goWebsite(0);
    } else {
        welcome.classList.remove('hide');
        webLayer.classList.remove('show');
    }
}

document.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        if (currentWebIdx < WEB_URLS.length - 1) goWebsite(currentWebIdx + 1);
    }
    if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (currentWebIdx > 0) goWebsite(currentWebIdx - 1);
    }
});

setTimeout(() => hint.classList.add('hide'), 5000);

// ========================
// 网站管理
// ========================
function addWebUrl(url) {
    url = url.trim();
    if (!url) return;
    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
    WEB_URLS.push(url);
    renderWebUrlList();
    renderWebNavDots();
    updateWelcome();
}

function removeWebUrl(idx) {
    WEB_URLS.splice(idx, 1);
    renderWebUrlList();
    renderWebNavDots();
    if (WEB_URLS.length === 0) {
        currentWebIdx = -1;
        webLayer.classList.remove('show');
        webIframe.src = 'about:blank';
        welcome.classList.remove('hide');
    } else if (currentWebIdx >= WEB_URLS.length) {
        goWebsite(WEB_URLS.length - 1);
    }
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
    navBar.innerHTML = '';
    WEB_URLS.forEach((u, i) => {
        const btn = document.createElement('button');
        btn.className = 'nav-dot-web' + (i === currentWebIdx ? ' active' : '');
        btn.dataset.webIdx = i;
        btn.textContent = '🌐';
        btn.title = u;
        btn.addEventListener('click', () => goWebsite(i));
        navBar.appendChild(btn);
    });
}

document.getElementById('welcomeStartBtn').addEventListener('click', () => webModal.classList.add('show'));
document.getElementById('webBarManage').addEventListener('click', () => webModal.classList.add('show'));
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

// ========================
// 摄像头
// ========================
const webcam = document.getElementById('webcam');
const camVideo = document.getElementById('camVideo');
const btnCamToggle = document.getElementById('btnCamToggle');
let camOn = false;

async function startCam() {
    try {
        camVideo.srcObject = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        camOn = true;
        btnCamToggle.classList.add('active');
        webcam.classList.remove('off');
    } catch(e) { webcam.classList.add('off'); }
}
function stopCam() {
    if (camVideo.srcObject) camVideo.srcObject.getTracks().forEach(t => t.stop());
    camOn = false;
    btnCamToggle.classList.remove('active');
    webcam.classList.add('off');
}
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
        <span class="page-label" id="pLabel">—</span>
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
        <div class="script-text" id="scriptText">选择网站开始...</div>
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
        if (currentWebIdx >= 0 && currentWebIdx < WEB_URLS.length) {
            const url = WEB_URLS[currentWebIdx];
            label = `网站 ${currentWebIdx + 1} / ${WEB_URLS.length}`;
            rawText = SCRIPTS[url] || `正在演示：${url}\n\n[自由演示]`;
        } else {
            label = '—';
            rawText = '选择网站开始...\n提词器会自动同步当前网站的脚本';
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
    a.download = `录屏-${ts}.webm`;
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

// ========================
// 初始化：渲染预填网址并显示第一个
// ========================
renderWebUrlList();
renderWebNavDots();
updateWelcome();
```

---

## cc 生成流程

1. **获取输入** — 用户提供：要演示的网址列表 + 简短主题
2. **生成提词器脚本** — 每个网址对应一段口播（80-150 字）
3. **输出提词器脚本 md** — `[主题]-提词器脚本.md`，用户可直接编辑
4. **组装 HTML** — 网址预填 `WEB_URLS` + 提词器脚本填入 `SCRIPTS` + CSS/JS 框架
5. **输出文件** — `[主题]-视频画布.html`
6. **生成封面图** — `[主题]-封面.html`（规范见下方）
7. **提示用户** — 先检查提词器脚本 md，再在浏览器中打开 HTML 录制

> **用户修改提词器脚本后**：告诉 cc "更新提词器"，cc 读取修改后的 md，重新写入 HTML 的 SCRIPTS 对象。

### 输出文件命名

- 默认路径：用户指定目录，或 `/tmp/`
- 视频画布：`[简短主题]-视频画布.html`
- 提词器脚本：`[简短主题]-提词器脚本.md`
- 封面图：`[简短主题]-封面.html`
- 示例：`AI产品演示-视频画布.html` + `AI产品演示-提词器脚本.md` + `AI产品演示-封面.html`

---

## 提词器脚本 md 格式

cc 输出的 md 文件格式如下，用户可直接编辑后让 cc 更新到 HTML：

```markdown
# {{主题}} — 提词器脚本

> 每个网站对应一段口播文案。`[方括号]` 内是给自己看的提示，不念出来。
> 修改后告诉 cc "更新提词器"，会自动同步到视频画布 HTML。

---

## 网站 1 · {{网站名/简述}}

{{URL}}

{{口播文案}}

[打开首页，展示主功能]

---

## 网站 2 · {{网站名/简述}}

{{URL}}

{{口播文案}}

[切换到关键页面]

---

（每个网站一段，数量与网址列表一致）
```

### cc 解析规则

读取用户修改后的 md 时：
1. 按 `## 网站 N` 分割为 N 段
2. 每段第一行非空行作为 URL（匹配 `https?://`）
3. 其余内容（去掉标题行和分隔线）作为 `SCRIPTS[URL]` 的值
4. `\n` 保留原始换行
5. `[方括号内容]` 保留，HTML 中会渲染为灰色提示

### 录制文件命名

HTML 内部自动命名下载文件为 `录屏-{{时间戳}}.webm`。固定 16:9 比例，各平台都可直接上传。

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
        <div class="tag">{{TAG英文，如 PRODUCT DEMO × AI}}</div>
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

- `.tag`：用英文关键词组合（如 `PRODUCT DEMO × AI`），全大写，与文章封面一致
- `.title`：标题前半用白色，核心爆点用 `.mega`（110px 鱼红）
- `.subtitle`：一句话补充说明，24px 半透明白
- `.stats`：1-2 组核心数据（数字鱼红 + 单位半透明），可选
- `.bottom-tags`：3-4 个技术/主题标签，与文章封面底部标签一致
- 封面要在手机小图上也能看清标题，不要放太多文字
