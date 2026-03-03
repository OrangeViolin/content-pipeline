/**
 * Douyin (抖音) publisher via Chrome CDP.
 * Opens creator.douyin.com, uploads video, fills description.
 * EXPERIMENTAL: Douyin has aggressive anti-automation.
 */

import fs from 'node:fs';
import {
  launchChrome, getPageSession, clickElement, typeText, evaluate,
  waitForSelector, uploadFile, sleep, randomDelay,
  type Manifest, type PublishResult, type ChromeSession,
} from '../cdp-utils.ts';

const DOUYIN_URL = 'https://creator.douyin.com/creator-micro/content/upload';

const SELECTORS = {
  videoUpload: 'input[type="file"][accept*="video"]',
  titleInput: 'input[placeholder*="标题"], input[class*="title"]',
  descriptionEditor: '[contenteditable="true"], textarea[placeholder*="描述"], div[class*="editor"]',
  tagInput: 'input[placeholder*="话题"], input[class*="topic"]',
  publishBtn: 'button:has-text("发布"), button[class*="publish"]',
  loginIndicator: 'img[class*="avatar"]',
};

export async function publishToDouyin(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const douyinData = manifest.outputs.douyin;
  if (!douyinData) {
    return { platform: 'douyin', status: 'skipped', message: 'No Douyin content in manifest' };
  }

  if (!fs.existsSync(douyinData.video)) {
    return {
      platform: 'douyin',
      status: 'manual',
      message: `Video file not found: ${douyinData.video}. Upload manually.`,
    };
  }

  let launchResult;
  try {
    launchResult = await launchChrome(DOUYIN_URL, 'douyin');
  } catch (err) {
    return {
      platform: 'douyin',
      status: 'manual',
      message: `Chrome launch failed. Upload ${douyinData.video} to Douyin manually.`,
    };
  }

  const { cdp, chrome } = launchResult;

  try {
    await sleep(5000); // Douyin loads slowly

    let session: ChromeSession;
    try {
      session = await getPageSession(cdp, 'douyin.com');
    } catch {
      return {
        platform: 'douyin',
        status: 'assisted',
        message: 'Page opened. Please log in to Douyin creator, then retry.',
      };
    }

    // Check login
    const currentUrl = await evaluate<string>(session, 'window.location.href');
    if (currentUrl.includes('login')) {
      return {
        platform: 'douyin',
        status: 'assisted',
        message: 'Login required. Please scan QR to log in to Douyin, then run /distribute again.',
      };
    }

    // Upload video
    const hasUpload = await waitForSelector(session, SELECTORS.videoUpload, 8_000);
    if (hasUpload) {
      await uploadFile(session, SELECTORS.videoUpload, douyinData.video);
      console.log(`  Video uploaded: ${douyinData.video}`);
      await sleep(10000); // Video processing takes time
    }

    // Fill title
    const hasTitle = await waitForSelector(session, SELECTORS.titleInput, 5_000);
    if (hasTitle) {
      await clickElement(session, SELECTORS.titleInput);
      await randomDelay(300, 600);
      await typeText(session, douyinData.copy.title);
    }

    await randomDelay(300, 600);

    // Fill description
    const hasDesc = await waitForSelector(session, SELECTORS.descriptionEditor, 5_000);
    if (hasDesc) {
      await clickElement(session, SELECTORS.descriptionEditor);
      await randomDelay();
      await typeText(session, douyinData.copy.description);
    }

    // Add tags
    for (const tag of douyinData.copy.tags) {
      const hasTag = await waitForSelector(session, SELECTORS.tagInput, 3_000);
      if (hasTag) {
        await clickElement(session, SELECTORS.tagInput);
        await randomDelay(100, 300);
        await typeText(session, tag.replace(/^#/, ''));
        await sleep(500);
        await session.cdp.send('Input.dispatchKeyEvent', {
          type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
        }, { sessionId: session.sessionId });
        await session.cdp.send('Input.dispatchKeyEvent', {
          type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
        }, { sessionId: session.sessionId });
        await randomDelay(300, 600);
      }
    }

    if (!preview) {
      const hasPublish = await waitForSelector(session, SELECTORS.publishBtn, 5_000);
      if (hasPublish) {
        await randomDelay(500, 1000);
        await clickElement(session, SELECTORS.publishBtn);
        await sleep(5000);
        return { platform: 'douyin', status: 'success', message: 'Published to Douyin' };
      }
      return { platform: 'douyin', status: 'assisted', message: 'Content filled, publish manually.' };
    }

    return { platform: 'douyin', status: 'assisted', message: 'Content pre-filled in Douyin editor.' };
  } catch (err) {
    return {
      platform: 'douyin',
      status: 'manual',
      message: `CDP error (Douyin anti-automation likely): ${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    cdp.close();
  }
}
