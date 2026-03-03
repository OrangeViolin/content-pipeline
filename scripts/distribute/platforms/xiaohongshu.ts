/**
 * Xiaohongshu (小红书) publisher via Chrome CDP.
 * Opens creator.xiaohongshu.com, uploads images, fills in copy.
 */

import fs from 'node:fs';
import path from 'node:path';
import {
  launchChrome, getPageSession, clickElement, typeText, evaluate,
  waitForSelector, uploadFile, sleep, randomDelay,
  type Manifest, type PublishResult, type ChromeSession,
} from '../cdp-utils.ts';

const CREATOR_URL = 'https://creator.xiaohongshu.com/publish/publish';

// Selectors (extracted for easy update when UI changes)
const SELECTORS = {
  uploadInput: 'input[type="file"]',
  titleInput: '.titleInput input, input[placeholder*="标题"], .c-input_inner[placeholder*="标题"]',
  contentEditor: '.ql-editor, [contenteditable="true"].content, div[data-placeholder*="正文"]',
  tagInput: '.tag-input input, input[placeholder*="话题"]',
  publishBtn: 'button.publishBtn, button.css-k0vba7, button[class*="publish"]',
  loginIndicator: '.avatar, .user-avatar, img[class*="avatar"]',
};

async function findAndUploadImages(session: ChromeSession, imagesDir: string): Promise<boolean> {
  const imageFiles = fs.readdirSync(imagesDir)
    .filter((f) => /\.(png|jpg|jpeg|webp)$/i.test(f))
    .sort()
    .map((f) => path.join(imagesDir, f));

  if (imageFiles.length === 0) return false;

  // Wait for upload area
  const hasUpload = await waitForSelector(session, SELECTORS.uploadInput, 10_000);
  if (!hasUpload) return false;

  // Upload all images at once via file input
  const { root } = await session.cdp.send<{ root: { nodeId: number } }>('DOM.getDocument', {}, { sessionId: session.sessionId });
  const { nodeId } = await session.cdp.send<{ nodeId: number }>('DOM.querySelector', {
    nodeId: root.nodeId,
    selector: SELECTORS.uploadInput,
  }, { sessionId: session.sessionId });

  if (!nodeId) return false;

  await session.cdp.send('DOM.setFileInputFiles', {
    nodeId,
    files: imageFiles,
  }, { sessionId: session.sessionId });

  console.log(`  Uploaded ${imageFiles.length} images`);
  await sleep(3000); // Wait for upload processing

  return true;
}

async function fillContent(session: ChromeSession, title: string, body: string, tags: string[]): Promise<void> {
  // Fill title
  const hasTitle = await waitForSelector(session, SELECTORS.titleInput, 5_000);
  if (hasTitle) {
    await clickElement(session, SELECTORS.titleInput);
    await randomDelay();
    await typeText(session, title);
    console.log(`  Title filled: ${title.substring(0, 30)}...`);
  }

  await randomDelay(300, 600);

  // Fill body content
  const hasContent = await waitForSelector(session, SELECTORS.contentEditor, 5_000);
  if (hasContent) {
    await clickElement(session, SELECTORS.contentEditor);
    await randomDelay();
    await typeText(session, body);
    console.log(`  Content filled (${body.length} chars)`);
  }

  await randomDelay(300, 600);

  // Add tags
  for (const tag of tags) {
    const cleanTag = tag.replace(/^#/, '');
    const hasTagInput = await waitForSelector(session, SELECTORS.tagInput, 3_000);
    if (hasTagInput) {
      await clickElement(session, SELECTORS.tagInput);
      await randomDelay(100, 300);
      await typeText(session, cleanTag);
      await randomDelay(500, 1000);
      // Press Enter to confirm tag
      await session.cdp.send('Input.dispatchKeyEvent', {
        type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
      }, { sessionId: session.sessionId });
      await session.cdp.send('Input.dispatchKeyEvent', {
        type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13,
      }, { sessionId: session.sessionId });
      await randomDelay(300, 600);
    }
  }
}

export async function publishToXiaohongshu(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const xhsData = manifest.outputs.xiaohongshu;
  if (!xhsData) {
    return { platform: 'xhs', status: 'skipped', message: 'No Xiaohongshu content in manifest' };
  }

  let launchResult;
  try {
    launchResult = await launchChrome(CREATOR_URL, 'xiaohongshu');
  } catch (err) {
    return {
      platform: 'xhs',
      status: 'manual',
      message: `Chrome launch failed: ${err instanceof Error ? err.message : String(err)}. Copy: ${xhsData.copy.title}`,
    };
  }

  const { cdp, chrome } = launchResult;

  try {
    await sleep(8000); // Wait for page load + potential redirects

    // Retry session acquisition (page may still be navigating)
    let session: ChromeSession | null = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        session = await getPageSession(cdp, 'xiaohongshu.com');
        break;
      } catch {
        await sleep(3000);
      }
    }
    if (!session) {
      return {
        platform: 'xhs',
        status: 'assisted',
        message: 'Page opened. Please log in to Xiaohongshu creator platform, then retry.',
      };
    }

    const isLoggedIn = await evaluate<boolean>(session, `!!document.querySelector('${SELECTORS.loginIndicator}')`);
    if (!isLoggedIn) {
      // Check if we're on login page
      const currentUrl = await evaluate<string>(session, 'window.location.href');
      if (currentUrl.includes('login')) {
        return {
          platform: 'xhs',
          status: 'assisted',
          message: 'Login required. Please log in to Xiaohongshu, then run /distribute again.',
        };
      }
    }

    // Upload images if available
    if (xhsData.images_dir && fs.existsSync(xhsData.images_dir)) {
      await findAndUploadImages(session, xhsData.images_dir);
    }

    // Fill content
    await fillContent(session, xhsData.copy.title, xhsData.copy.body, xhsData.copy.tags);

    if (!preview) {
      // Click publish
      const hasPublish = await waitForSelector(session, SELECTORS.publishBtn, 5_000);
      if (hasPublish) {
        await randomDelay(500, 1000);
        await clickElement(session, SELECTORS.publishBtn);
        await sleep(3000);
        return { platform: 'xhs', status: 'success', message: 'Published to Xiaohongshu' };
      }
      return { platform: 'xhs', status: 'assisted', message: 'Content filled, publish button not found. Please publish manually.' };
    }

    return { platform: 'xhs', status: 'assisted', message: 'Content pre-filled in Xiaohongshu editor. Review and publish manually.' };
  } catch (err) {
    return {
      platform: 'xhs',
      status: 'manual',
      message: `CDP error: ${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    cdp.close();
    // Don't kill Chrome - let user review
  }
}
