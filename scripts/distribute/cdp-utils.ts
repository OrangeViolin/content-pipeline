/**
 * Shared CDP utilities for distribute skill.
 * Based on baoyu-post-to-wechat/scripts/cdp.ts and baoyu-post-to-x/scripts/x-utils.ts.
 */

import { spawn, type ChildProcess } from 'node:child_process';
import fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

// ─── Sleep ───

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Random delay between min and max ms (anti-detection) */
export function randomDelay(min = 200, max = 800): Promise<void> {
  return sleep(min + Math.random() * (max - min));
}

// ─── Port ───

export async function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close(() => reject(new Error('Unable to allocate a free TCP port.')));
        return;
      }
      const port = address.port;
      server.close((err) => {
        if (err) reject(err);
        else resolve(port);
      });
    });
  });
}

// ─── Chrome Discovery ───

export function findChromeExecutable(): string | undefined {
  const override = process.env.DISTRIBUTE_CHROME_PATH?.trim();
  if (override && fs.existsSync(override)) return override;

  const candidates: string[] = [];
  switch (process.platform) {
    case 'darwin':
      candidates.push(
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
      );
      break;
    case 'win32':
      candidates.push(
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      );
      break;
    default:
      candidates.push('/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser');
      break;
  }

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return undefined;
}

// ─── Profile ───

export function getProfileDir(platform: string): string {
  const base = process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share');
  return path.join(base, `${platform}-browser-profile`);
}

// ─── JSON Fetch ───

async function fetchJson<T = unknown>(url: string): Promise<T> {
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

async function waitForChromeDebugPort(port: number, timeoutMs: number): Promise<string> {
  const start = Date.now();
  let lastError: unknown = null;

  while (Date.now() - start < timeoutMs) {
    try {
      const version = await fetchJson<{ webSocketDebuggerUrl?: string }>(`http://127.0.0.1:${port}/json/version`);
      if (version.webSocketDebuggerUrl) return version.webSocketDebuggerUrl;
      lastError = new Error('Missing webSocketDebuggerUrl');
    } catch (error) {
      lastError = error;
    }
    await sleep(200);
  }

  throw new Error(`Chrome debug port not ready: ${lastError instanceof Error ? lastError.message : String(lastError)}`);
}

// ─── CDP Connection ───

type PendingRequest = {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout> | null;
};

export class CdpConnection {
  private ws: WebSocket;
  private nextId = 0;
  private pending = new Map<number, PendingRequest>();
  private eventHandlers = new Map<string, Set<(params: unknown) => void>>();
  private defaultTimeoutMs: number;

  private constructor(ws: WebSocket, options?: { defaultTimeoutMs?: number }) {
    this.ws = ws;
    this.defaultTimeoutMs = options?.defaultTimeoutMs ?? 15_000;

    this.ws.addEventListener('message', (event) => {
      try {
        const data = typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data as ArrayBuffer);
        const msg = JSON.parse(data) as {
          id?: number; method?: string; params?: unknown;
          result?: unknown; error?: { message?: string };
        };

        if (msg.method) {
          const handlers = this.eventHandlers.get(msg.method);
          if (handlers) handlers.forEach((h) => h(msg.params));
        }

        if (msg.id) {
          const pending = this.pending.get(msg.id);
          if (pending) {
            this.pending.delete(msg.id);
            if (pending.timer) clearTimeout(pending.timer);
            if (msg.error?.message) pending.reject(new Error(msg.error.message));
            else pending.resolve(msg.result);
          }
        }
      } catch {}
    });

    this.ws.addEventListener('close', () => {
      for (const [, pending] of this.pending.entries()) {
        if (pending.timer) clearTimeout(pending.timer);
        pending.reject(new Error('CDP connection closed.'));
      }
      this.pending.clear();
    });
  }

  static async connect(url: string, timeoutMs: number, options?: { defaultTimeoutMs?: number }): Promise<CdpConnection> {
    const ws = new WebSocket(url);
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('CDP connection timeout.')), timeoutMs);
      ws.addEventListener('open', () => { clearTimeout(timer); resolve(); });
      ws.addEventListener('error', () => { clearTimeout(timer); reject(new Error('CDP connection failed.')); });
    });
    return new CdpConnection(ws, options);
  }

  on(method: string, handler: (params: unknown) => void): void {
    if (!this.eventHandlers.has(method)) this.eventHandlers.set(method, new Set());
    this.eventHandlers.get(method)!.add(handler);
  }

  async send<T = unknown>(
    method: string,
    params?: Record<string, unknown>,
    options?: { sessionId?: string; timeoutMs?: number },
  ): Promise<T> {
    const id = ++this.nextId;
    const message: Record<string, unknown> = { id, method };
    if (params) message.params = params;
    if (options?.sessionId) message.sessionId = options.sessionId;

    const timeoutMs = options?.timeoutMs ?? this.defaultTimeoutMs;

    const result = await new Promise<unknown>((resolve, reject) => {
      const timer = timeoutMs > 0
        ? setTimeout(() => { this.pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, timeoutMs)
        : null;
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify(message));
    });

    return result as T;
  }

  close(): void {
    try { this.ws.close(); } catch {}
  }
}

// ─── Chrome Session ───

export interface ChromeSession {
  cdp: CdpConnection;
  sessionId: string;
  targetId: string;
}

export interface LaunchResult {
  cdp: CdpConnection;
  chrome: ChildProcess;
}

export async function launchChrome(url: string, platform: string): Promise<LaunchResult> {
  const chromePath = findChromeExecutable();
  if (!chromePath) throw new Error('Chrome not found. Set DISTRIBUTE_CHROME_PATH env var.');

  const profile = getProfileDir(platform);
  await mkdir(profile, { recursive: true });

  const port = await getFreePort();
  console.log(`[distribute][${platform}] Launching Chrome (profile: ${profile})`);

  const chrome = spawn(chromePath, [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-blink-features=AutomationControlled',
    '--start-maximized',
    url,
  ], { stdio: 'ignore' });

  const wsUrl = await waitForChromeDebugPort(port, 30_000);
  const cdp = await CdpConnection.connect(wsUrl, 30_000, { defaultTimeoutMs: 20_000 });

  return { cdp, chrome };
}

export async function getPageSession(cdp: CdpConnection, urlPattern: string): Promise<ChromeSession> {
  const targets = await cdp.send<{ targetInfos: Array<{ targetId: string; url: string; type: string }> }>('Target.getTargets');
  const pageTarget = targets.targetInfos.find((t) => t.type === 'page' && t.url.includes(urlPattern));

  if (!pageTarget) throw new Error(`Page not found: ${urlPattern}`);

  const { sessionId } = await cdp.send<{ sessionId: string }>('Target.attachToTarget', {
    targetId: pageTarget.targetId,
    flatten: true,
  });

  await cdp.send('Page.enable', {}, { sessionId });
  await cdp.send('Runtime.enable', {}, { sessionId });
  await cdp.send('DOM.enable', {}, { sessionId });

  return { cdp, sessionId, targetId: pageTarget.targetId };
}

// ─── Interaction Helpers ───

export async function clickElement(session: ChromeSession, selector: string): Promise<void> {
  const posResult = await session.cdp.send<{ result: { value: string } }>('Runtime.evaluate', {
    expression: `
      (function() {
        const el = document.querySelector('${selector.replace(/'/g, "\\'")}');
        if (!el) return 'null';
        el.scrollIntoView({ block: 'center' });
        const rect = el.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 });
      })()
    `,
    returnByValue: true,
  }, { sessionId: session.sessionId });

  if (posResult.result.value === 'null') throw new Error(`Element not found: ${selector}`);
  const pos = JSON.parse(posResult.result.value);

  await session.cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed', x: pos.x, y: pos.y, button: 'left', clickCount: 1,
  }, { sessionId: session.sessionId });
  await randomDelay(30, 80);
  await session.cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased', x: pos.x, y: pos.y, button: 'left', clickCount: 1,
  }, { sessionId: session.sessionId });
}

export async function typeText(session: ChromeSession, text: string): Promise<void> {
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length > 0) {
      await session.cdp.send('Input.insertText', { text: lines[i] }, { sessionId: session.sessionId });
    }
    if (i < lines.length - 1) {
      await session.cdp.send('Input.dispatchKeyEvent', {
        type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
      }, { sessionId: session.sessionId });
      await session.cdp.send('Input.dispatchKeyEvent', {
        type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
      }, { sessionId: session.sessionId });
    }
    await randomDelay(20, 60);
  }
}

export async function pasteFromClipboard(session: ChromeSession): Promise<void> {
  const modifiers = process.platform === 'darwin' ? 4 : 2; // Meta for Mac, Ctrl for others
  await session.cdp.send('Input.dispatchKeyEvent', {
    type: 'keyDown', key: 'v', code: 'KeyV', modifiers, windowsVirtualKeyCode: 86,
  }, { sessionId: session.sessionId });
  await session.cdp.send('Input.dispatchKeyEvent', {
    type: 'keyUp', key: 'v', code: 'KeyV', modifiers, windowsVirtualKeyCode: 86,
  }, { sessionId: session.sessionId });
}

export async function evaluate<T = unknown>(session: ChromeSession, expression: string): Promise<T> {
  const result = await session.cdp.send<{ result: { value: T } }>('Runtime.evaluate', {
    expression,
    returnByValue: true,
  }, { sessionId: session.sessionId });
  return result.result.value;
}

export async function waitForSelector(session: ChromeSession, selector: string, timeoutMs = 10_000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const found = await evaluate<boolean>(session, `!!document.querySelector('${selector.replace(/'/g, "\\'")}')`);
    if (found) return true;
    await sleep(500);
  }
  return false;
}

export async function uploadFile(session: ChromeSession, selector: string, filePath: string): Promise<void> {
  const { root } = await session.cdp.send<{ root: { nodeId: number } }>('DOM.getDocument', {}, { sessionId: session.sessionId });
  const { nodeId } = await session.cdp.send<{ nodeId: number }>('DOM.querySelector', {
    nodeId: root.nodeId,
    selector,
  }, { sessionId: session.sessionId });

  if (!nodeId) throw new Error(`Upload input not found: ${selector}`);

  await session.cdp.send('DOM.setFileInputFiles', {
    nodeId,
    files: [filePath],
  }, { sessionId: session.sessionId });
}

// ─── Manifest Types ───

export interface Manifest {
  version: string;
  created: string;
  source: string;
  title: string;
  outputs: {
    xiaohongshu?: {
      html: string;
      images_dir?: string;
      copy: { title: string; body: string; tags: string[] };
    };
    jike?: {
      copy: { body: string; circles: string[] };
    };
    xiaoyuzhou?: {
      audio: string;
      script: string;
      copy: { title: string; description: string; show_notes: string };
    };
    wechat?: {
      markdown?: string;
      images?: string[];
      html?: string;
      title?: string;
      author?: string;
      digest?: string;
      cover_image?: string;
    };
    video?: {
      intro?: string;
      outro?: string;
      prompts?: string;
    };
    douyin?: {
      video: string;
      copy: { title: string; description: string; tags: string[] };
    };
  };
}

export type PlatformId = 'wechat' | 'xhs' | 'jike' | 'xiaoyuzhou' | 'douyin' | 'shipinhao';

export interface PublishResult {
  platform: PlatformId;
  status: 'success' | 'assisted' | 'manual' | 'skipped' | 'error';
  message: string;
  url?: string;
}

export function loadManifest(manifestPath: string): Manifest {
  if (!fs.existsSync(manifestPath)) {
    throw new Error(`manifest.json not found: ${manifestPath}`);
  }
  return JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
}
