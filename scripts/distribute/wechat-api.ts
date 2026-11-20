/**
 * WeChat Official Account API client.
 * Pushes articles directly to drafts via the WeChat MP API,
 * bypassing Chrome CDP automation entirely.
 */

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

// ─── Types ───

interface Credentials {
  appId: string;
  appSecret: string;
}

interface TokenCache {
  accessToken: string;
  expiresAt: number; // epoch ms
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

// ─── HTML Processing ───

const OFFICIAL_CDN_HOSTS = new Set(['mmbiz.qpic.cn', 'mmbiz.qlogo.cn']);

/** True only for https URLs on the official WeChat image hosts. */
export function isOfficialWechatCdn(src: string): boolean {
  try {
    const url = new URL(src);
    return url.protocol === 'https:' && OFFICIAL_CDN_HOSTS.has(url.hostname);
  } catch {
    return false;
  }
}

/** Image src values that cannot count as an uploaded draft image. */
export function findNonCdnImages(html: string): string[] {
  const out: string[] = [];
  const re = /<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["'][^>]*>/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(html)) !== null) {
    if (!isOfficialWechatCdn(match[1])) out.push(match[1]);
  }
  return out;
}

/** Paragraph anchors are HTML comments. Missing anchors must not fall through to list order. */
export function planImageInsertions(html: string, fileNames: string[]): { missing: string[] } {
  const missing = fileNames.filter((name) => {
    const base = name.replace(/\.[^.]+$/, '');
    return !html.includes(`<!-- IMAGE:${name} -->`) && !html.includes(`<!-- IMAGE:${base} -->`);
  });
  return { missing };
}

/** Fix HTML structures that WeChat cannot render properly */
export function fixHtmlForWechat(html: string): string {
  let fixed = html;

  // Fix <p><figure>...</figure></p> nesting — WeChat cannot render block elements inside <p>
  // Extract <figure> out of <p> and convert to <section> for WeChat compatibility
  fixed = fixed.replace(/<p[^>]*>\s*(<figure[\s\S]*?<\/figure>)\s*<\/p>/gi, (_match, figureContent: string) => {
    // Convert <figure> to <section> to avoid WeChat's block-in-inline issues
    return figureContent
      .replace(/<figure/gi, '<section')
      .replace(/<\/figure>/gi, '</section>');
  });

  // Also handle standalone <figure> tags — convert to <section>
  fixed = fixed.replace(/<figure([^>]*)>/gi, '<section$1>');
  fixed = fixed.replace(/<\/figure>/gi, '</section>');

  // Normalize <img> styles for WeChat compatibility
  fixed = fixed.replace(/<img([^>]*?)>/gi, (_match, attrs: string) => {
    // Remove existing style attribute
    const cleanAttrs = attrs.replace(/\s*style="[^"]*"/gi, '').replace(/\s*style='[^']*'/gi, '');
    const wechatStyle = 'style="max-width:100%;height:auto;display:block;margin:0 auto;border-radius:8px;"';
    return `<img${cleanAttrs} ${wechatStyle}>`;
  });

  return fixed;
}

/** Scan HTML for local image paths (src="/Users/...") and upload them to WeChat CDN */
export async function uploadLocalImagesInHtml(html: string, token: string): Promise<string> {
  // Match src attributes with local file paths (absolute paths starting with /)
  const localImgRegex = /src=["'](\/(Users|home|tmp|var)[^"']+\.(?:png|jpg|jpeg|gif|webp|bmp))["']/gi;
  const matches: Array<{ full: string; localPath: string }> = [];

  let match: RegExpExecArray | null;
  while ((match = localImgRegex.exec(html)) !== null) {
    matches.push({ full: match[0], localPath: match[1] });
  }

  if (matches.length === 0) return html;

  console.log(`  [wechat-api] Found ${matches.length} local image(s) to upload...`);

  let processed = html;
  let uploaded = 0;
  let failed = 0;

  for (const { full, localPath } of matches) {
    // Handle URL-encoded paths (e.g. Chinese filenames)
    let decodedPath: string;
    try {
      decodedPath = decodeURIComponent(localPath);
    } catch {
      decodedPath = localPath;
    }

    if (!fs.existsSync(decodedPath)) {
      console.warn(`  [wechat-api]   ✗ Not found: ${decodedPath}`);
      failed++;
      continue;
    }

    try {
      const cdnUrl = await uploadContentImage(token, decodedPath);
      const newSrc = `src="${cdnUrl}"`;
      processed = processed.replace(full, newSrc);
      uploaded++;
      console.log(`  [wechat-api]   ✓ ${path.basename(decodedPath)}`);
    } catch (err) {
      console.warn(`  [wechat-api]   ✗ ${path.basename(decodedPath)}: ${err instanceof Error ? err.message : err}`);
      failed++;
    }
  }

  console.log(`  [wechat-api] Local images: ${uploaded} uploaded, ${failed} failed`);
  return processed;
}

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
  // Fix HTML structures for WeChat compatibility first
  let processed = fixHtmlForWechat(content);

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

/** Create one new draft. This does not update an existing draft and does not publish. */
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
        // Keep a blank byline when the caller did not supply one. Do not invent an AI author.
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
  if (!wechatData) throw new Error('No wechat data in manifest');

  // Validate: need at least html (or markdown), cover_image, and title
  const hasHtml = wechatData.html && fs.existsSync(wechatData.html);
  const hasMarkdown = wechatData.markdown && fs.existsSync(wechatData.markdown);

  if (!hasHtml && hasMarkdown) {
    throw new Error(
      'Markdown-only mode is no longer supported in wechat-api.ts.\n' +
      'Please convert markdown to HTML first using md2wechat_formatter.py:\n' +
      '  cd "$MD_FORMATTER_DIR"\n' +
      '  python3 md2wechat_formatter.py [article.md] --theme 01fish --font-size medium\n' +
      'Then set wechat.html in the manifest to the generated _preview.html path.'
    );
  }

  if (!hasHtml) {
    throw new Error('No wechat HTML file in manifest. Provide wechat.html pointing to a _preview.html file.');
  }

  // 1. Load credentials
  const creds = loadCredentials();
  if (!creds) throw new Error('No WeChat API credentials configured');

  console.log('  [wechat-api] Starting API publish flow...');

  // 2. Get access token
  const token = await getAccessToken(creds);

  // 3. Extract content from pre-rendered HTML
  console.log('  [wechat-api] Using pre-rendered HTML');
  const extracted = extractArticleContent(wechatData.html!);
  let htmlContent = extracted.content;
  // styles stays '' — pre-rendered HTML needs no <style> wrapper
  const title = wechatData.title || manifest.title;
  const author = wechatData.author;
  const digest = wechatData.digest;

  // 4. Process HTML with placeholder images (if any from old workflow)
  const imageMap = new Map<string, string>();
  const finalContent = processHtmlWithImages(htmlContent, '', imageMap);

  // 5. Upload local images referenced in HTML to WeChat CDN
  let contentWithCdnImages = await uploadLocalImagesInHtml(finalContent, token);

  // 5.5 Upload manifest images at paragraph anchors. Never append by list order.
  if (wechatData.images && wechatData.images.length > 0) {
    const missingFiles = wechatData.images.filter((imgPath) => !fs.existsSync(imgPath));
    if (missingFiles.length > 0) {
      throw new Error(
        `Image file missing. Refusing to shift later images forward: ${missingFiles.join(', ')}`,
      );
    }
    const names = wechatData.images.map((imgPath) => path.basename(imgPath));
    const anchorPlan = planImageInsertions(contentWithCdnImages, names);
    if (anchorPlan.missing.length > 0) {
      throw new Error(
        `Refusing to insert images by list order. No paragraph anchor for: ${anchorPlan.missing.join(', ')}. ` +
        'Add <!-- IMAGE:filename --> beside the paragraph. An API failure does not switch to a browser.',
      );
    }

    console.log(`  [wechat-api] Uploading ${wechatData.images.length} article image(s)...`);
    const uploadedImages: Array<{ cdnUrl: string; fileName: string }> = [];

    for (const imgPath of wechatData.images) {
      try {
        const cdnUrl = await uploadContentImage(token, imgPath);
        uploadedImages.push({ cdnUrl, fileName: path.basename(imgPath) });
        console.log(`  [wechat-api]   ✓ ${path.basename(imgPath)}`);
      } catch (err) {
        throw new Error(
          `uploadimg failed for ${path.basename(imgPath)}: ${err instanceof Error ? err.message : err}. ` +
          'file/data preview is not draft success.',
        );
      }
    }

    for (const { cdnUrl, fileName } of uploadedImages) {
      const imgTag = `<section style="text-align:center;margin:20px 0;"><img src="${cdnUrl}" style="max-width:100%;height:auto;display:block;margin:0 auto;" /></section>`;
      const placeholder = `<!-- IMAGE:${fileName} -->`;
      const baseName = fileName.replace(/\.[^.]+$/, '');
      const altPlaceholder = `<!-- IMAGE:${baseName} -->`;
      if (contentWithCdnImages.includes(placeholder)) {
        contentWithCdnImages = contentWithCdnImages.replace(placeholder, imgTag);
      } else if (contentWithCdnImages.includes(altPlaceholder)) {
        contentWithCdnImages = contentWithCdnImages.replace(altPlaceholder, imgTag);
      } else {
        throw new Error(`Anchor disappeared before insert: ${fileName}`);
      }
    }
  }

  const nonCdn = findNonCdnImages(contentWithCdnImages);
  if (nonCdn.length > 0) {
    throw new Error(
      'Draft image success requires an official WeChat CDN URL (https://mmbiz.qpic.cn or https://mmbiz.qlogo.cn). ' +
      `Still not uploaded: ${nonCdn.join(', ')}. file/data URLs are local preview only.`,
    );
  }

  // 6. Upload cover image (required for draft)
  let thumbMediaId: string;
  const coverPath = wechatData.cover_image;

  if (coverPath && fs.existsSync(coverPath)) {
    console.log('  [wechat-api] Uploading cover image...');
    thumbMediaId = await uploadCoverImage(token, coverPath);
  } else {
    throw new Error(
      'No cover image available. Provide wechat.cover_image already cropped near 2.35:1. ' +
      'A square thumbnail is a separate crop. This client does not reuse a content image by list position and does not stretch either crop.',
    );
  }

  // 7. Create draft
  console.log('  [wechat-api] Creating draft...');
  const draft = await createDraft(token, {
    title,
    content: contentWithCdnImages,
    author,
    digest,
    thumb_media_id: thumbMediaId,
  });

  console.log(`  [wechat-api] Draft created successfully (media_id: ${draft.media_id})`);
  return { mediaId: draft.media_id };
}
