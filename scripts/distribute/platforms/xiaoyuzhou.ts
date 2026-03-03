/**
 * Xiaoyuzhou (小宇宙) publisher via Chrome CDP.
 * Opens podcasters.xiaoyuzhoufm.com, uploads audio, fills show notes.
 */

import fs from 'node:fs';
import {
  launchChrome, getPageSession, clickElement, typeText, evaluate,
  waitForSelector, uploadFile, sleep, randomDelay,
  type Manifest, type PublishResult, type ChromeSession,
} from '../cdp-utils.ts';

const XIAOYUZHOU_URL = 'https://podcasters.xiaoyuzhoufm.com/';

const SELECTORS = {
  newEpisodeBtn: 'a[href*="episode/new"], button:has-text("新建节目"), a:has-text("新建")',
  audioUpload: 'input[type="file"][accept*="audio"], input[type="file"][accept*="mp3"]',
  titleInput: 'input[placeholder*="标题"], input[name="title"]',
  descriptionEditor: 'textarea[placeholder*="简介"], [contenteditable="true"], textarea[name="description"]',
  showNotesEditor: 'textarea[placeholder*="文稿"], textarea[name="shownotes"]',
  publishBtn: 'button:has-text("发布"), button[type="submit"]',
  loginIndicator: 'img[class*="avatar"], div[class*="Avatar"]',
};

export async function publishToXiaoyuzhou(manifest: Manifest, preview: boolean): Promise<PublishResult> {
  const xyData = manifest.outputs.xiaoyuzhou;
  if (!xyData) {
    return { platform: 'xiaoyuzhou', status: 'skipped', message: 'No Xiaoyuzhou content in manifest' };
  }

  if (!fs.existsSync(xyData.audio)) {
    return {
      platform: 'xiaoyuzhou',
      status: 'manual',
      message: `Audio file not found: ${xyData.audio}. Upload manually.`,
    };
  }

  let launchResult;
  try {
    launchResult = await launchChrome(XIAOYUZHOU_URL, 'xiaoyuzhou');
  } catch (err) {
    return {
      platform: 'xiaoyuzhou',
      status: 'manual',
      message: `Chrome launch failed. Upload ${xyData.audio} to Xiaoyuzhou manually.`,
    };
  }

  const { cdp, chrome } = launchResult;

  try {
    await sleep(8000); // Wait for page load + potential redirects

    let session: ChromeSession | null = null;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        session = await getPageSession(cdp, 'xiaoyuzhoufm.com');
        break;
      } catch {
        await sleep(3000);
      }
    }
    if (!session) {
      return {
        platform: 'xiaoyuzhou',
        status: 'assisted',
        message: 'Page opened. Please log in to Xiaoyuzhou, then retry.',
      };
    }

    // Navigate to new episode
    const hasNewBtn = await waitForSelector(session, SELECTORS.newEpisodeBtn, 5_000);
    if (hasNewBtn) {
      await clickElement(session, SELECTORS.newEpisodeBtn);
      await sleep(2000);
    }

    // Upload audio
    const hasAudioUpload = await waitForSelector(session, SELECTORS.audioUpload, 5_000);
    if (hasAudioUpload) {
      await uploadFile(session, SELECTORS.audioUpload, xyData.audio);
      console.log(`  Audio uploaded: ${xyData.audio}`);
      await sleep(5000); // Wait for audio processing
    }

    // Fill title
    const hasTitle = await waitForSelector(session, SELECTORS.titleInput, 5_000);
    if (hasTitle) {
      await clickElement(session, SELECTORS.titleInput);
      await randomDelay();
      await typeText(session, xyData.copy.title);
      console.log(`  Title: ${xyData.copy.title}`);
    }

    await randomDelay(300, 600);

    // Fill description
    const hasDesc = await waitForSelector(session, SELECTORS.descriptionEditor, 3_000);
    if (hasDesc) {
      await clickElement(session, SELECTORS.descriptionEditor);
      await randomDelay();
      await typeText(session, xyData.copy.description);
    }

    // Fill show notes
    const hasNotes = await waitForSelector(session, SELECTORS.showNotesEditor, 3_000);
    if (hasNotes) {
      await clickElement(session, SELECTORS.showNotesEditor);
      await randomDelay();
      await typeText(session, xyData.copy.show_notes);
      console.log(`  Show notes filled`);
    }

    if (!preview) {
      const hasPublish = await waitForSelector(session, SELECTORS.publishBtn, 5_000);
      if (hasPublish) {
        await randomDelay(500, 1000);
        await clickElement(session, SELECTORS.publishBtn);
        await sleep(5000);
        return { platform: 'xiaoyuzhou', status: 'success', message: 'Episode published to Xiaoyuzhou' };
      }
      return { platform: 'xiaoyuzhou', status: 'assisted', message: 'Content filled, publish button not found. Publish manually.' };
    }

    return {
      platform: 'xiaoyuzhou',
      status: 'assisted',
      message: 'Episode pre-filled in Xiaoyuzhou editor. Review and publish manually.',
    };
  } catch (err) {
    return {
      platform: 'xiaoyuzhou',
      status: 'manual',
      message: `CDP error: ${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    cdp.close();
  }
}
