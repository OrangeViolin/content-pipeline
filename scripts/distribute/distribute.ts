#!/usr/bin/env bun
/**
 * distribute.ts — Main orchestrator for multi-platform content distribution.
 *
 * Usage:
 *   npx -y bun distribute.ts --manifest /path/to/manifest.json [--platforms xhs,jike] [--preview]
 */

import { parseArgs } from 'node:util';
import { execSync } from 'node:child_process';
import { loadManifest, sleep, type PlatformId, type PublishResult } from './cdp-utils.ts';
import { publishToWechat } from './platforms/wechat.ts';
import { publishToXiaohongshu } from './platforms/xiaohongshu.ts';
import { publishToJike } from './platforms/jike.ts';
import { publishToXiaoyuzhou } from './platforms/xiaoyuzhou.ts';
import { publishToDouyin } from './platforms/douyin.ts';
import { publishToShipinhao } from './platforms/shipinhao.ts';

// ─── Parse Args ───

const { values } = parseArgs({
  options: {
    manifest: { type: 'string', short: 'm' },
    platforms: { type: 'string', short: 'p' },
    preview: { type: 'boolean', default: false },
  },
  strict: false,
});

if (!values.manifest) {
  console.error('Usage: distribute.ts --manifest <path> [--platforms xhs,jike] [--preview]');
  process.exit(1);
}

// ─── Platform Registry ───

const PLATFORM_ORDER: PlatformId[] = ['wechat', 'xhs', 'jike', 'xiaoyuzhou', 'douyin', 'shipinhao'];

const PLATFORM_NAMES: Record<PlatformId, string> = {
  wechat: '公众号',
  xhs: '小红书',
  jike: '即刻',
  xiaoyuzhou: '小宇宙',
  douyin: '抖音',
  shipinhao: '视频号',
};

const PLATFORM_HANDLERS: Record<PlatformId, (manifest: ReturnType<typeof loadManifest>, preview: boolean) => Promise<PublishResult>> = {
  wechat: publishToWechat,
  xhs: publishToXiaohongshu,
  jike: publishToJike,
  xiaoyuzhou: publishToXiaoyuzhou,
  douyin: publishToDouyin,
  shipinhao: publishToShipinhao,
};

// ─── Main ───

async function main() {
  const manifest = loadManifest(values.manifest!);
  const preview = values.preview ?? false;

  // Determine which platforms to publish
  let selectedPlatforms: PlatformId[];
  if (values.platforms) {
    selectedPlatforms = values.platforms.split(',').map((p) => p.trim() as PlatformId);
    // Validate
    for (const p of selectedPlatforms) {
      if (!PLATFORM_ORDER.includes(p)) {
        console.error(`Unknown platform: ${p}. Available: ${PLATFORM_ORDER.join(', ')}`);
        process.exit(1);
      }
    }
  } else {
    // Auto-detect from manifest
    selectedPlatforms = PLATFORM_ORDER.filter((p) => {
      switch (p) {
        case 'wechat': return !!manifest.outputs.wechat;
        case 'xhs': return !!manifest.outputs.xiaohongshu;
        case 'jike': return !!manifest.outputs.jike;
        case 'xiaoyuzhou': return !!manifest.outputs.xiaoyuzhou;
        case 'douyin': return !!manifest.outputs.douyin;
        case 'shipinhao': return false; // Not yet supported
        default: return false;
      }
    });
  }

  if (selectedPlatforms.length === 0) {
    console.log('No platforms to publish to. Check manifest.json outputs.');
    process.exit(0);
  }

  // Show plan
  console.log(`\n📋 Distribution Plan${preview ? ' (PREVIEW MODE)' : ''}`);
  console.log(`   Source: ${manifest.title}`);
  console.log(`   Platforms: ${selectedPlatforms.map((p) => PLATFORM_NAMES[p]).join(' → ')}\n`);

  // Execute sequentially
  const results: PublishResult[] = [];

  for (const platform of selectedPlatforms) {
    console.log(`\n${'─'.repeat(50)}`);
    console.log(`▶ ${PLATFORM_NAMES[platform]}`);

    try {
      const result = await PLATFORM_HANDLERS[platform](manifest, preview);
      results.push(result);

      const icon = result.status === 'success' ? '✅' :
                   result.status === 'assisted' ? '🔵' :
                   result.status === 'manual' ? '📋' :
                   result.status === 'skipped' ? '⏭️' : '❌';
      console.log(`${icon} ${PLATFORM_NAMES[platform]}: ${result.message}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      results.push({ platform, status: 'error', message });
      console.log(`❌ ${PLATFORM_NAMES[platform]}: ${message}`);
    }

    // Kill Chrome between platforms to avoid port/profile conflicts
    try { execSync('pkill -f "remote-debugging-port" 2>/dev/null', { stdio: 'ignore' }); } catch {}
    await sleep(3000);
  }

  // Summary
  console.log(`\n${'═'.repeat(50)}`);
  console.log('📊 Distribution Summary\n');

  for (const r of results) {
    const icon = r.status === 'success' ? '✅' :
                 r.status === 'assisted' ? '🔵' :
                 r.status === 'manual' ? '📋' :
                 r.status === 'skipped' ? '⏭️' : '❌';
    console.log(`  ${icon} ${PLATFORM_NAMES[r.platform]}: ${r.message}${r.url ? ` → ${r.url}` : ''}`);
  }

  const successCount = results.filter((r) => r.status === 'success' || r.status === 'assisted').length;
  console.log(`\n  ${successCount}/${results.length} platforms published successfully.`);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
