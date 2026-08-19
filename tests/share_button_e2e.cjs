// Playwright driver for the article-page share button (§9.2.1): a single
// "share" icon in the nav-buttons cluster that opens a floating popover
// with a copy-link / QR-code matrix scoped to the series index, the
// current article, or the current fiche (slide). Invoked by
// tests/test_share_button.py — not a standalone entry point.
//
// argv: <pageUrl> <expectedArticleUrl> <expectedSeriesUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

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
  collectConsoleErrors(page, consoleErrors);
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

  try {
    await page.goto(pageUrl);
    await page.waitForSelector('#navShare');

    // 0. Keyboard operability: the share button is a role=button div with
    // tabindex=0; focusing it and pressing Enter must open the popover
    // (it has no other keyboard entry point). Then Escape closes it.
    await page.focus('#navShare');
    const shareFocused = await page.evaluate(() => document.activeElement && document.activeElement.id === 'navShare');
    if (!shareFocused) fail('share button is not keyboard-focusable (missing tabindex?)');
    await page.keyboard.press('Enter');
    const openedByKeyboard = await page.evaluate(() => document.getElementById('sharePopover').classList.contains('open'));
    if (!openedByKeyboard) fail('Enter on the focused share button must open the popover');
    await page.keyboard.press('Escape');

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

    // 6. Fiche-scope copy on the standard slide: the clipboard URL must
    // anchor to the slide itself, not just the article — and to the
    // slide's OWN id, read off the page. It used to be `#s2`, written out
    // here as a literal; a card's id is now derived from what the author
    // wrote (§12.1.1), so the rank is no longer the answer and a literal
    // would only pin what this test happens to build today. What is under
    // test is that the copied link names the card the reader is on.
    const ficheId = await page.evaluate(() => {
      const mid = window.innerHeight / 2;
      const here = Array.prototype.slice.call(
        document.querySelectorAll('section.slide')).find((s) => {
          const r = s.getBoundingClientRect();
          return r.top <= mid && r.bottom >= mid;
        });
      return here ? here.id : null;
    });
    if (!ficheId) fail('could not tell which card the reader is on');
    await page.click('#navShare');
    await page.click('[data-action="copy"][data-scope="fiche"]');
    const clipboardFiche = await page.evaluate(() => navigator.clipboard.readText());
    if (clipboardFiche !== expectedArticleUrl + '#' + ficheId) {
      fail('fiche copy-link mismatch: got ' + clipboardFiche + ' expected '
           + expectedArticleUrl + '#' + ficheId);
    }
    await page.keyboard.press('Escape');

    // 7. Move to the series-nav slide: the fiche column must be disabled
    // again — the scope follows the slide TYPE (§9.2.1), and series-nav
    // is not a reading position.
    await page.click('#navNext');
    await page.waitForTimeout(800);
    const onSeriesNav = await page.evaluate(() => {
      const s = document.querySelectorAll('section.slide');
      return s[s.length - 1].getBoundingClientRect().top < window.innerHeight / 2;
    });
    if (!onSeriesNav) fail('did not reach the series-nav slide after navNext');
    await page.click('#navShare');
    const ficheDisabledOnSeriesNav = await page.evaluate(() =>
      Array.prototype.every.call(document.querySelectorAll('[data-scope="fiche"]'), (b) => b.disabled));
    if (!ficheDisabledOnSeriesNav) fail('fiche column must be disabled on the series-nav slide');

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
