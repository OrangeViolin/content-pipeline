const patch = () => {
  // 1. webdriver标记（最核心）
  Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
  });

  // 2. plugins列表（真实浏览器有2–5个，Headless为0）
  const mockPlugins = [
    { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" },
    { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" }
  ];
  Object.defineProperty(navigator, 'plugins', {
    get: () => mockPlugins,
  });

  // 3. mimeTypes（必须与plugins数量一致）
  const mockMimeTypes = [
    { type: "application/pdf", suffixes: "pdf", description: "" }
  ];
  Object.defineProperty(navigator, 'mimeTypes', {
    get: () => mockMimeTypes,
  });

  // 4. 外部窗口尺寸（需与实际屏幕匹配，否则触发二次验证）
  const screenWidth = window.screen.width;
  const screenHeight = window.screen.height;
  Object.defineProperty(window, 'outerWidth', {
    get: () => screenWidth,
  });
  Object.defineProperty(window, 'outerHeight', {
    get: () => screenHeight,
  });

  // 5. documentMode（IE遗留，但Cloudflare仍检查）
  Object.defineProperty(document, 'documentMode', {
    get: () => undefined,
  });

  // 6. chrome对象（Headless Chrome无此对象）
  window.chrome = { runtime: {} };
};

// 确保在所有上下文执行
if (typeof window !== 'undefined') {
  patch();
} else if (typeof self !== 'undefined') {
  self.patch = patch;
  self.patch();
}

const wasmBytes = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, // magic header
  0x01, 0x00, 0x00, 0x00, // version
  // ... 省略具体字节，实际需生成合法WASM二进制
]);
const wasmModule = new WebAssembly.Module(wasmBytes);
const wasmInstance = new WebAssembly.Instance(wasmModule);

// 模拟原模块的导出函数
wasmInstance.exports._calculate_hash = (input_ptr, input_len, output_ptr) => {
  // 输入是内存地址，需从wasm memory中读取
  const memory = wasmInstance.exports.memory;
  const inputArray = new Uint8Array(memory.buffer, input_ptr, input_len);
  const inputStr = new TextDecoder().decode(inputArray);
  
  // 执行JS版SHA256（使用crypto.subtle或第三方库）
  const hashBuffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(inputStr));
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  
  // 写回output_ptr指向的内存
  const outputArray = new Uint8Array(memory.buffer, output_ptr, 32);
  outputArray.set(hashArray);
};