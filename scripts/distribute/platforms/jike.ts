/**
 * Jike (即刻) publisher via Chrome CDP.
 * Opens web.okjike.com, fills in post content.
 */

import {
  launchChrome, getPageSession, clickElement, typeText, evaluate,
  waitForSelector, sleep, randomDelay,
  type Manifest, type PublishResult, type ChromeSession,
} from '../cdp-utils.ts';

const JIKE_URL = 'https://web.okjike.com/';

const SELECTORS = {
  composeBtn: 'button[class*="compose"], a[href*="compose"], div[class*="ComposeButton"]',
  contentEditor: '[contenteditable="true"], textarea[placeholder*="分享"], .ql-editor',
  publishBtn: 'button[class*="submit"], button[class*="publish"], button:has-text("发布")',
  loginIndicator: 'img[class*="avatar"], div[class*="Avatar"]',
};

export async function publishToJike(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const jikeData = manifest.outputs.jike;
  if (!jikeData) {
    return { platform: 'jike', status: 'skipped', message: 'No Jike content in manifest' };
  }

  let launchResult;
  try {
    launchResult = await launchChrome(JIKE_URL, 'jike');
  } catch (err) {
    return {
      platform: 'jike',
      status: 'manual',
      message: `Chrome launch failed. Copy your Jike post manually:\n${jikeData.copy.body.substring(0, 100)}...`,
    };
  }

  const { cdp, chrome } = launchResult;

  try {
    await sleep(4000); // Jike loads slowly

    let session: ChromeSession;
    try {
      session = await getPageSession(cdp, 'okjike.com');
    } catch {
      return {
        platform: 'jike',
        status: 'assisted',
        message: 'Page opened. Please log in to Jike, then retry.',
      };
    }

    // Check login
    const isLoggedIn = await evaluate<boolean>(session, `!!document.querySelector('${SELECTORS.loginIndicator}')`);
    if (!isLoggedIn) {
      const currentUrl = await evaluate<string>(session, 'window.location.href');
      if (currentUrl.includes('login')) {
        return {
          platform: 'jike',
          status: 'assisted',
          message: 'Login required. Please log in to Jike, then run /distribute again.',
        };
      }
    }

    // Click compose button to open editor
    const hasCompose = await waitForSelector(session, SELECTORS.composeBtn, 5_000);
    if (hasCompose) {
      await clickElement(session, SELECTORS.composeBtn);
      await sleep(1500);
    }

    // Fill content
    const hasEditor = await waitForSelector(session, SELECTORS.contentEditor, 5_000);
    if (hasEditor) {
      await clickElement(session, SELECTORS.contentEditor);
      await randomDelay();
      await typeText(session, jikeData.copy.body);
      console.log(`  Content filled (${jikeData.copy.body.length} chars)`);
    } else {
      return {
        platform: 'jike',
        status: 'assisted',
        message: 'Editor not found. Jike is open, paste manually.',
      };
    }

    if (!preview) {
      const hasPublish = await waitForSelector(session, SELECTORS.publishBtn, 5_000);
      if (hasPublish) {
        await randomDelay(500, 1000);
        await clickElement(session, SELECTORS.publishBtn);
        await sleep(3000);
        return { platform: 'jike', status: 'success', message: 'Published to Jike' };
      }
      return { platform: 'jike', status: 'assisted', message: 'Content filled, publish button not found. Please publish manually.' };
    }

    return {
      platform: 'jike',
      status: 'assisted',
      message: `Content pre-filled in Jike editor. Circles: ${jikeData.copy.circles.join(', ')}`,
    };
  } catch (err) {
    return {
      platform: 'jike',
      status: 'manual',
      message: `CDP error: ${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    cdp.close();
  }
}
