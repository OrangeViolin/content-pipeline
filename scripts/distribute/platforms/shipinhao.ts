/**
 * Shipinhao (视频号) publisher.
 * Currently NOT supported - no web creator backend.
 * Falls back to manual mode with file paths.
 */

import type { Manifest, PublishResult } from '../cdp-utils.ts';

export async function publishToShipinhao(manifest: Manifest, _preview: boolean): Promise<PublishResult> {
  // 视频号 currently has no web-based creator platform.
  // Future: consider mobile-based automation or API integration.

  const videoData = manifest.outputs.video;
  if (!videoData) {
    return { platform: 'shipinhao', status: 'skipped', message: 'No video content in manifest' };
  }

  const paths: string[] = [];
  if (videoData.intro) paths.push(`Intro: ${videoData.intro}`);
  if (videoData.outro) paths.push(`Outro: ${videoData.outro}`);
  if (videoData.prompts) paths.push(`Prompts: ${videoData.prompts}`);

  return {
    platform: 'shipinhao',
    status: 'manual',
    message: `视频号 has no web creator backend. Upload via mobile app.\n  ${paths.join('\n  ')}`,
  };
}
