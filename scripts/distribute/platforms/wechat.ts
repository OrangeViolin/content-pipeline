/**
 * WeChat Official Account (公众号) publisher.
 *
 * Degradation strategy:
 *   L0: WeChat API → create a new draft (no browser needed). This is not publish.
 *   L3: Manual → output the file path. Do not open Chrome when the API was
 *       configured and failed, unless the user explicitly asks for a browser.
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
      console.log('  [wechat] Staying on manual (L3). Not opening a browser.');
    }
  }

  // L3: Manual fallback. A connected API failure does not continue into CDP.
  const filePath = hasHtml ? wechatData.html : wechatData.markdown;
  const why = preview ? 'Preview mode keeps the editor manual.' : 'API draft was not created.';
  return {
    platform: 'wechat',
    status: 'manual',
    message: `${why} Not switching to a browser. File: ${filePath}`,
  };
}
