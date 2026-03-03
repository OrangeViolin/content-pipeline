/**
 * WeChat Official Account (公众号) publisher.
 *
 * Degradation strategy:
 *   L0: WeChat API → push directly to drafts (no browser needed)
 *   L1: CDP automation → Chrome-based (existing logic)
 *   L3: Manual → output file path for copy-paste
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import type { Manifest, PublishResult } from '../cdp-utils.ts';
import { publishViaApi } from '../wechat-api.ts';

const BAOYU_WECHAT_SKILL_DIR = process.env.BAOYU_WECHAT_SKILL_DIR || '';

export async function publishToWechat(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const wechatData = manifest.outputs.wechat;
  if (!wechatData) {
    return { platform: 'wechat', status: 'skipped', message: 'No WeChat content in manifest' };
  }

  if (!wechatData.markdown || !fs.existsSync(wechatData.markdown)) {
    return { platform: 'wechat', status: 'manual', message: `Markdown file not found: ${wechatData.markdown}` };
  }

  // L0: Try WeChat API direct push (skip in preview mode — user wants the editor)
  if (!preview) {
    try {
      const result = await publishViaApi(manifest);
      return {
        platform: 'wechat',
        status: 'success',
        message: `Article pushed to drafts via API (media_id: ${result.mediaId})`,
      };
    } catch (err) {
      const reason = err instanceof Error ? err.message : String(err);
      console.log(`  [wechat] API mode failed, falling back to CDP: ${reason}`);
    }
  }

  // L1: CDP automation fallback
  const scriptPath = path.join(BAOYU_WECHAT_SKILL_DIR, 'scripts', 'wechat-article.ts');
  if (!fs.existsSync(scriptPath)) {
    return { platform: 'wechat', status: 'manual', message: `baoyu-post-to-wechat script not found: ${scriptPath}` };
  }

  const args = [scriptPath, wechatData.markdown, '--theme', 'grace'];
  if (!preview) {
    args.push('--submit');
  }

  console.log(`  Running: npx -y bun ${args.join(' ')}`);

  const result = spawnSync('npx', ['-y', 'bun', ...args], {
    stdio: 'inherit',
    timeout: 120_000,
  });

  if (result.status === 0) {
    return {
      platform: 'wechat',
      status: preview ? 'assisted' : 'success',
      message: preview ? 'Article opened in WeChat editor' : 'Article published to WeChat',
    };
  }

  // L3: Manual fallback
  return {
    platform: 'wechat',
    status: 'manual',
    message: `Script failed (exit ${result.status}). Markdown file: ${wechatData.markdown}`,
  };
}
