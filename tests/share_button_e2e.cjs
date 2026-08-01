// Playwright driver for the article-page share button (§9.2.1): a single
// "share" icon in the nav-buttons cluster that opens a floating popover
// with a copy-link / QR-code matrix scoped to the series index, the
// current article, or the current fiche (slide). Invoked by
// tests/test_share_button.py — not a standalone entry point.
//
// argv: <pageUrl> <expectedArticleUrl> <expectedSeriesUrl>

const { chromium } = require('playwright');

function fail(msg) {
  console.error('E2E failure: ' + msg);
  process.exitCode = 1;
}

async function main() {
  const [pageUrl, expectedArticleUrl, expectedSeriesUrl] = process.argv.slice(2);
  if (!pageUrl || !expectedArticleUrl || !expectedSeriesUrl) {
    console.error('usage: share_button_e2e.cjs <pageUrl> <expectedArticleUrl> <expectedSeriesUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext();
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const page = await context.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

  try {
    await page.goto(pageUrl);
    await page.waitForSelector('#navShare');

    // 1. Opening the popover on the cover slide (current === 0): the
    // "Fiche" column has no meaningful target (no per-slide anchor other
    // than the article itself) and must be disabled.
    await page.click('#navShare');
    const popoverOpenOnCover = await page.evaluate(() => document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverOpenOnCover) fail('popover did not open on share button click');

    const ficheDisabledOnCover = await page.evaluate(() =>
      Array.prototype.every.call(document.querySelectorAll('[data-scope="fiche"]'), (b) => b.disabled));
    if (!ficheDisabledOnCover) fail('fiche column must be disabled while on the cover slide');

    // Escape closes the popover.
    await page.keyboard.press('Escape');
    const popoverClosedByEscape = await page.evaluate(() => !document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverClosedByEscape) fail('Escape must close the share popover');

    // 2. Move to the next slide, then the fiche column must be enabled.
    await page.click('#navNext');
    await page.waitForTimeout(800); // matches nav.js's own scroll-settle timeout
    await page.click('#navShare');
    const ficheEnabledOnSlide2 = await page.evaluate(() =>
      Array.prototype.every.call(document.querySelectorAll('[data-scope="fiche"]'), (b) => !b.disabled));
    if (!ficheEnabledOnSlide2) fail('fiche column must be enabled once past the cover slide');

    // 3. Copy the article-scope link and verify the real clipboard content.
    await page.click('[data-action="copy"][data-scope="article"]');
    const clipboardArticle = await page.evaluate(() => navigator.clipboard.readText());
    if (clipboardArticle !== expectedArticleUrl) {
      fail('article copy-link mismatch: got ' + clipboardArticle + ' expected ' + expectedArticleUrl);
    }

    // 4. Show the QR code for the series scope and sanity-check the SVG.
    // (The popover is still open from step 2/3 — clicking #navShare again
    // here would toggle it closed instead.)
    await page.click('[data-action="qr"][data-scope="series"]');
    const qrOpen = await page.evaluate(() => document.getElementById('shareQrModal').classList.contains('open'));
    if (!qrOpen) fail('QR modal did not open');
    const qrUrlText = await page.textContent('#shareQrModalUrl');
    if (qrUrlText !== expectedSeriesUrl) {
      fail('QR modal URL mismatch: got ' + qrUrlText + ' expected ' + expectedSeriesUrl);
    }
    const rectCount = await page.evaluate(() =>
      document.querySelectorAll('#shareQrModalContent svg rect').length);
    if (rectCount < 10) fail('QR SVG has implausibly few rects: ' + rectCount);

    // 5. Closing the QR modal via its close button.
    await page.click('.share-qr-close');
    const qrClosed = await page.evaluate(() => !document.getElementById('shareQrModal').classList.contains('open'));
    if (!qrClosed) fail('QR modal did not close via its close button');

    if (consoleErrors.length) fail('unexpected console errors: ' + JSON.stringify(consoleErrors));

    if (process.exitCode) {
      process.exit(process.exitCode);
    }
    console.log('OK');
    process.exit(0);
  } catch (err) {
    console.error('E2E failure: ' + err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
