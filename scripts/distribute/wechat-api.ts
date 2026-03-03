/**
 * WeChat Official Account API client.
 * Pushes articles directly to drafts via the WeChat MP API,
 * bypassing Chrome CDP automation entirely.
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Manifest } from './cdp-utils.ts';

// ─── Constants ───

const WECHAT_API_BASE = 'https://api.weixin.qq.com';
// Bun's TLS stack rejects WeChat API certs on POST multipart uploads;
// this option bypasses certificate verification for these API calls.
const BUN_FETCH_OPTS = { tls: { rejectUnauthorized: false } } as const;
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 3000;
const CONFIG_DIR = path.join(os.homedir(), '.config', 'wechat-api');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const TOKEN_CACHE_FILE = path.join(CONFIG_DIR, 'token-cache.json');
const TOKEN_LIFETIME_MS = 2 * 60 * 60 * 1000; // 2 hours
const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000; // refresh 5 min early

const MD_TO_WECHAT_SCRIPT = process.env.MD_TO_WECHAT_SCRIPT || path.join(import.meta.dirname, '../../baoyu-post-to-wechat/scripts/md-to-wechat.ts');

// ─── Types ───

interface Credentials {
  appId: string;
  appSecret: string;
}

interface TokenCache {
  accessToken: string;
  expiresAt: number; // epoch ms
}

interface MdToWechatOutput {
  title: string;
  author?: string;
  summary?: string;
  htmlPath: string;
  contentImages: Array<{
    placeholder: string;
    localPath: string;
    originalPath: string;
  }>;
}

// ─── Retry helper ───

async function fetchWithRetry(url: string, init?: RequestInit & { tls?: { rejectUnauthorized: boolean } }): Promise<Response> {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await fetch(url, init);
    } catch (err) {
      if (attempt < MAX_RETRIES) {
        const msg = err instanceof Error ? err.message : String(err);
        console.log(`  [wechat-api] Request failed (${msg}), retrying in ${RETRY_DELAY_MS / 1000}s... (${attempt + 1}/${MAX_RETRIES})`);
        await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
      } else {
        throw err;
      }
    }
  }
  throw new Error('unreachable');
}

// ─── Credentials ───

export function loadCredentials(): Credentials | null {
  const appId = process.env.WECHAT_APPID?.trim();
  const appSecret = process.env.WECHAT_APPSECRET?.trim();
  if (appId && appSecret) {
    return { appId, appSecret };
  }

  if (fs.existsSync(CONFIG_FILE)) {
    try {
      const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf-8'));
      if (config.appId && config.appSecret) {
        return { appId: config.appId, appSecret: config.appSecret };
      }
    } catch {}
  }

  return null;
}

// ─── Access Token ───

function readTokenCache(): TokenCache | null {
  if (!fs.existsSync(TOKEN_CACHE_FILE)) return null;
  try {
    const cache = JSON.parse(fs.readFileSync(TOKEN_CACHE_FILE, 'utf-8')) as TokenCache;
    if (cache.accessToken && cache.expiresAt > Date.now() + TOKEN_REFRESH_BUFFER_MS) {
      return cache;
    }
  } catch {}
  return null;
}

function writeTokenCache(token: string, expiresIn: number): void {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  const cache: TokenCache = {
    accessToken: token,
    expiresAt: Date.now() + expiresIn * 1000,
  };
  fs.writeFileSync(TOKEN_CACHE_FILE, JSON.stringify(cache, null, 2));
}

export async function getAccessToken(creds: Credentials): Promise<string> {
  const cached = readTokenCache();
  if (cached) return cached.accessToken;

  const url = `${WECHAT_API_BASE}/cgi-bin/token?grant_type=client_credential&appid=${encodeURIComponent(creds.appId)}&secret=${encodeURIComponent(creds.appSecret)}`;
  const res = await fetchWithRetry(url, { ...BUN_FETCH_OPTS });
  if (!res.ok) throw new Error(`Failed to get access_token: HTTP ${res.status}`);

  const data = await res.json() as { access_token?: string; expires_in?: number; errcode?: number; errmsg?: string };
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`WeChat API error ${data.errcode}: ${data.errmsg}`);
  }
  if (!data.access_token || !data.expires_in) {
    throw new Error('Invalid access_token response');
  }

  writeTokenCache(data.access_token, data.expires_in);
  console.log('  [wechat-api] Access token obtained');
  return data.access_token;
}

// ─── Image Upload ───

export async function uploadContentImage(token: string, imagePath: string): Promise<string> {
  const fileData = fs.readFileSync(imagePath);
  const ext = path.extname(imagePath).slice(1) || 'png';
  const mimeType = ext === 'jpg' ? 'image/jpeg' : `image/${ext}`;
  const fileName = path.basename(imagePath);

  const form = new FormData();
  form.append('media', new Blob([fileData], { type: mimeType }), fileName);

  const url = `${WECHAT_API_BASE}/cgi-bin/media/uploadimg?access_token=${token}`;
  const res = await fetchWithRetry(url, { method: 'POST', body: form, ...BUN_FETCH_OPTS });
  if (!res.ok) throw new Error(`uploadimg failed: HTTP ${res.status}`);

  const data = await res.json() as { url?: string; errcode?: number; errmsg?: string };
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`uploadimg error ${data.errcode}: ${data.errmsg}`);
  }
  if (!data.url) throw new Error('uploadimg: no URL returned');

  return data.url;
}

export async function uploadCoverImage(token: string, imagePath: string): Promise<string> {
  const fileData = fs.readFileSync(imagePath);
  const ext = path.extname(imagePath).slice(1) || 'png';
  const mimeType = ext === 'jpg' ? 'image/jpeg' : `image/${ext}`;
  const fileName = path.basename(imagePath);

  const form = new FormData();
  form.append('media', new Blob([fileData], { type: mimeType }), fileName);

  const url = `${WECHAT_API_BASE}/cgi-bin/material/add_material?access_token=${token}&type=image`;
  const res = await fetchWithRetry(url, { method: 'POST', body: form, ...BUN_FETCH_OPTS });
  if (!res.ok) throw new Error(`add_material failed: HTTP ${res.status}`);

  const data = await res.json() as { media_id?: string; errcode?: number; errmsg?: string };
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`add_material error ${data.errcode}: ${data.errmsg}`);
  }
  if (!data.media_id) throw new Error('add_material: no media_id returned');

  return data.media_id;
}

// ─── Markdown Conversion ───

export function convertMarkdown(markdownPath: string): MdToWechatOutput {
  console.log('  [wechat-api] Converting markdown to HTML...');

  const scriptDir = path.dirname(MD_TO_WECHAT_SCRIPT);
  const result = spawnSync('npx', ['-y', 'bun', MD_TO_WECHAT_SCRIPT, markdownPath, '--theme', 'grace'], {
    cwd: scriptDir,
    timeout: 60_000,
    encoding: 'utf-8',
  });

  if (result.status !== 0) {
    const stderr = result.stderr?.trim() || '';
    throw new Error(`md-to-wechat failed (exit ${result.status})${stderr ? `: ${stderr}` : ''}`);
  }

  const stdout = result.stdout?.trim();
  if (!stdout) throw new Error('md-to-wechat produced no output');

  // The script outputs JSON to stdout
  const output = JSON.parse(stdout) as MdToWechatOutput;
  if (!output.htmlPath || !fs.existsSync(output.htmlPath)) {
    throw new Error(`HTML file not found: ${output.htmlPath}`);
  }

  return output;
}

// ─── HTML Processing ───

export function extractArticleContent(htmlPath: string): { content: string; styles: string } {
  const html = fs.readFileSync(htmlPath, 'utf-8');

  // Extract <style> blocks
  const styleMatches = html.match(/<style[^>]*>([\s\S]*?)<\/style>/gi) || [];
  const styles = styleMatches.map(s => {
    const inner = s.replace(/<\/?style[^>]*>/gi, '');
    return inner.trim();
  }).join('\n');

  // Priority: #output → .content → <body>

  // 1. Extract #output content (md-to-wechat output)
  const outputMatch = html.match(/<div[^>]*id=["']output["'][^>]*>([\s\S]*?)<\/div>\s*(?:<\/body>|<script|$)/i);
  if (outputMatch) {
    return { content: stripTipElements(outputMatch[1].trim()), styles };
  }

  // 2. Extract .content container (md2wechat_formatter _preview.html)
  const contentMatch = html.match(/<div[^>]*class=["'][^"']*\bcontent\b[^"']*["'][^>]*>([\s\S]*?)<\/div>\s*(?:<\/body>|<script|$)/i);
  if (contentMatch) {
    return { content: stripTipElements(contentMatch[1].trim()), styles };
  }

  // 3. Fallback: extract <body> content
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  if (bodyMatch) {
    return { content: stripTipElements(bodyMatch[1].trim()), styles };
  }

  throw new Error('Could not extract article content from HTML');
}

/** Remove .tip elements (e.g. "全选复制粘贴到公众号编辑器" hint bars) */
function stripTipElements(html: string): string {
  return html.replace(/<div[^>]*class=["'][^"']*\btip\b[^"']*["'][^>]*>[\s\S]*?<\/div>/gi, '').trim();
}

export function processHtmlWithImages(
  content: string,
  styles: string,
  imageMap: Map<string, string>,
): string {
  let processed = content;

  // Replace [[IMAGE_PLACEHOLDER_N]] with <img> tags pointing to WeChat CDN
  for (const [placeholder, cdnUrl] of imageMap) {
    processed = processed.replaceAll(
      placeholder,
      `<img src="${cdnUrl}" style="max-width: 100%; height: auto;" />`,
    );
  }

  // Wrap with styles if present
  if (styles) {
    return `<style>${styles}</style>\n${processed}`;
  }
  return processed;
}

// ─── Draft Creation ───

export async function createDraft(
  token: string,
  article: {
    title: string;
    content: string;
    author?: string;
    digest?: string;
    thumb_media_id: string;
  },
): Promise<{ media_id: string }> {
  const url = `${WECHAT_API_BASE}/cgi-bin/draft/add?access_token=${token}`;

  const body = {
    articles: [
      {
        title: article.title,
        author: article.author || '',
        digest: article.digest || '',
        content: article.content,
        thumb_media_id: article.thumb_media_id,
        content_source_url: '',
        need_open_comment: 0,
        only_fans_can_comment: 0,
      },
    ],
  };

  const res = await fetchWithRetry(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    ...BUN_FETCH_OPTS,
  });

  if (!res.ok) throw new Error(`draft/add failed: HTTP ${res.status}`);

  const data = await res.json() as { media_id?: string; errcode?: number; errmsg?: string };
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`draft/add error ${data.errcode}: ${data.errmsg}`);
  }
  if (!data.media_id) throw new Error('draft/add: no media_id returned');

  return { media_id: data.media_id };
}

// ─── Main Orchestrator ───

export async function publishViaApi(manifest: Manifest): Promise<{ mediaId: string }> {
  const wechatData = manifest.outputs.wechat;
  if (!wechatData?.markdown) throw new Error('No wechat markdown in manifest');

  // 1. Load credentials
  const creds = loadCredentials();
  if (!creds) throw new Error('No WeChat API credentials configured');

  console.log('  [wechat-api] Starting API publish flow...');

  // 2. Get access token
  const token = await getAccessToken(creds);

  // 3. Convert markdown to HTML (unless pre-rendered HTML provided)
  let title: string;
  let author: string | undefined;
  let digest: string | undefined;
  let htmlContent: string;
  let styles = '';
  let contentImages: MdToWechatOutput['contentImages'] = [];

  if (wechatData.html && fs.existsSync(wechatData.html)) {
    // Use pre-rendered HTML — all styles are already inline on elements,
    // page-level <style> (body/max-width/.tip) is irrelevant for WeChat
    console.log('  [wechat-api] Using pre-rendered HTML');
    const extracted = extractArticleContent(wechatData.html);
    htmlContent = extracted.content;
    // styles stays '' — pre-rendered HTML needs no <style> wrapper
    title = wechatData.title || manifest.title;
    author = wechatData.author;
    digest = wechatData.digest;
  } else {
    // Convert markdown
    const mdOutput = convertMarkdown(wechatData.markdown);
    const extracted = extractArticleContent(mdOutput.htmlPath);
    htmlContent = extracted.content;
    styles = extracted.styles;
    title = wechatData.title || mdOutput.title || manifest.title;
    author = wechatData.author || mdOutput.author;
    digest = wechatData.digest || mdOutput.summary;
    contentImages = mdOutput.contentImages || [];
  }

  // 4. Upload content images and build placeholder→URL map
  const imageMap = new Map<string, string>();
  if (contentImages.length > 0) {
    console.log(`  [wechat-api] Uploading ${contentImages.length} content image(s)...`);
    for (const img of contentImages) {
      if (!fs.existsSync(img.localPath)) {
        console.warn(`  [wechat-api] Image not found, skipping: ${img.localPath}`);
        continue;
      }
      try {
        const cdnUrl = await uploadContentImage(token, img.localPath);
        imageMap.set(img.placeholder, cdnUrl);
        console.log(`  [wechat-api]   ✓ ${path.basename(img.localPath)}`);
      } catch (err) {
        console.warn(`  [wechat-api]   ✗ ${path.basename(img.localPath)}: ${err instanceof Error ? err.message : err}`);
      }
    }
  }

  // 5. Process HTML with uploaded image URLs
  const finalContent = processHtmlWithImages(htmlContent, styles, imageMap);

  // 6. Upload cover image (required for draft)
  let thumbMediaId: string;
  const coverPath = wechatData.cover_image;

  if (coverPath && fs.existsSync(coverPath)) {
    console.log('  [wechat-api] Uploading cover image...');
    thumbMediaId = await uploadCoverImage(token, coverPath);
  } else if (wechatData.images && wechatData.images.length > 0 && fs.existsSync(wechatData.images[0])) {
    // Fallback: use first content image as cover
    console.log('  [wechat-api] No cover image specified, using first content image...');
    thumbMediaId = await uploadCoverImage(token, wechatData.images[0]);
  } else if (contentImages.length > 0 && fs.existsSync(contentImages[0].localPath)) {
    console.log('  [wechat-api] No cover image specified, using first article image...');
    thumbMediaId = await uploadCoverImage(token, contentImages[0].localPath);
  } else {
    throw new Error('No cover image available. Provide cover_image in manifest or ensure article has images.');
  }

  // 7. Create draft
  console.log('  [wechat-api] Creating draft...');
  const draft = await createDraft(token, {
    title,
    content: finalContent,
    author,
    digest,
    thumb_media_id: thumbMediaId,
  });

  console.log(`  [wechat-api] Draft created successfully (media_id: ${draft.media_id})`);
  return { mediaId: draft.media_id };
}
