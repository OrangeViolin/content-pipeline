/**
 * WeChat Official Account (公众号) publisher.
 *
 * Degradation strategy:
 *   L0: WeChat API → push directly to drafts (no browser needed)
 *   L3: Manual → output file path for copy-paste
 */

import fs from 'node:fs';
import type { Manifest, PublishResult } from '../cdp-utils.ts';
import { publishViaApi } from '../wechat-api.ts';

export async function publishToWechat(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const wechatData = manifest.outputs.wechat;
  if (!wechatData) {
    return { platform: 'wechat', status: 'skipped', message: 'No WeChat content in manifest' };
  }

  // Check for usable content: prefer html, then markdown
  const hasHtml = wechatData.html && fs.existsSync(wechatData.html);
  const hasMarkdown = wechatData.markdown && fs.existsSync(wechatData.markdown);

  if (!hasHtml && !hasMarkdown) {
    return {
      platform: 'wechat',
      status: 'manual',
      message: 'No HTML or Markdown file found in manifest. Provide wechat.html (排版后的 _preview.html) or wechat.markdown.',
    };
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
      console.log(`  [wechat] API mode failed: ${reason}`);
    }
  }

  // L3: Manual fallback — no more CDP automation
  const filePath = hasHtml ? wechatData.html : wechatData.markdown;
  return {
    platform: 'wechat',
    status: 'manual',
    message: `API publish failed or preview mode. File: ${filePath}`,
  };
}
