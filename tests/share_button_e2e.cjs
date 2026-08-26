// Playwright driver for the article-page share button (§9.3.4): a single
// "share" action in the presenter menu that opens a floating popover with a
// copy-link / QR-code matrix scoped to the series index, the current article,
// or the current fiche (slide). Invoked by
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
    await page.waitForSelector('#navMenu');

    const openShare = async () => {
      await page.click('#navMenu');
      await page.waitForSelector('#presenterMenu.open');
      await page.click('#menuShare');
      await page.waitForSelector('#sharePopover.open');
    };

    // 0. Keyboard operability: the share action is a native button in the
    // presenter menu. Focusing it and pressing Enter must open the popover.
    await page.click('#navMenu');
    await page.focus('#menuShare');
    const shareFocused = await page.evaluate(() => document.activeElement && document.activeElement.id === 'menuShare');
    if (!shareFocused) fail('share action is not keyboard-focusable');
    await page.keyboard.press('Enter');
    const openedByKeyboard = await page.evaluate(() => ({
      open: document.getElementById('sharePopover').classList.contains('open'),
      role: document.getElementById('sharePopover').getAttribute('role'),
      modal: document.getElementById('sharePopover').getAttribute('aria-modal'),
      focus: document.activeElement && document.activeElement.getAttribute('data-scope'),
    }));
    if (!openedByKeyboard.open || openedByKeyboard.role !== 'dialog'
        || openedByKeyboard.modal !== 'true' || openedByKeyboard.focus !== 'series') {
      fail('Enter did not open an accessible share dialog: ' + JSON.stringify(openedByKeyboard));
    }
    await page.keyboard.press('Escape');
    const focusAfterShareEscape = await page.evaluate(() => document.activeElement && document.activeElement.id);
    if (focusAfterShareEscape !== 'navMenu') fail('share Escape did not restore nav focus');

    // S is the direct keyboard entry point for the same action. It must work
    // after the menu has closed, without requiring a pointer or focus on the
    // menu button.
    await page.keyboard.press('s');
    const openedByShortcut = await page.evaluate(() => document.getElementById('sharePopover').classList.contains('open'));
    if (!openedByShortcut) fail('S must open the share popover');
    const shortcutFocus = await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-scope'));
    if (shortcutFocus !== 'series') fail('S did not move focus into the share dialog');
    await page.keyboard.press('Escape');
    const focusAfterShortcutEscape = await page.evaluate(() => document.activeElement && document.activeElement.id);
    if (focusAfterShortcutEscape !== 'navMenu') fail('S dialog Escape did not restore nav focus');

    // 1. Opening the popover on the cover slide (current === 0): the
    // "Fiche" column must be ENABLED — a cover is a card with an id of
    // its own, shareable like any other (§9.3.4). The address bar hides
    // its fragment at the top of the page (§8.4), the share matrix does
    // not.
    await openShare();
    const popoverOpenOnCover = await page.evaluate(() => document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverOpenOnCover) fail('popover did not open on share button click');

    await page.keyboard.press('Shift+Tab');
    const shareLastFocus = await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-scope'));
    await page.keyboard.press('Tab');
    const shareFirstFocus = await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-scope'));
    if (shareLastFocus !== 'fiche' || shareFirstFocus !== 'series') {
      fail('share dialog Tab focus did not wrap: '
        + JSON.stringify({ shareLastFocus, shareFirstFocus }));
    }

    const ficheEnabledOnCover = await page.evaluate(() =>
      Array.prototype.every.call(document.querySelectorAll('[data-scope="fiche"]'), (b) => !b.disabled));
    if (!ficheEnabledOnCover) fail('fiche column must be enabled on the cover slide');

    // And the cover's own id is what the copied link carries.
    const coverId = await page.evaluate(() => {
      const here = document.querySelector('section.slide');
      return here ? here.id : null;
    });
    if (!coverId) fail('the cover slide has no id to share');
    await page.click('[data-action="copy"][data-scope="fiche"]');
    const clipboardCover = await page.evaluate(() => navigator.clipboard.readText());
    if (clipboardCover !== expectedArticleUrl + '#' + coverId) {
      fail('cover copy-link mismatch: got ' + clipboardCover + ' expected '
           + expectedArticleUrl + '#' + coverId);
    }
    const copyStatus = await page.evaluate(() => document.getElementById('shareStatus').textContent);
    if (!copyStatus) fail('copy completion was not announced to assistive technology');

    // Escape closes the popover.
    await page.keyboard.press('Escape');
    const popoverClosedByEscape = await page.evaluate(() => !document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverClosedByEscape) fail('Escape must close the share popover');

    // 1b. A click on the GROUND while the popover is open closes it and
    // does NOT advance the deck: closing the window you opened is not a
    // navigation. The click that would have moved the reader a card on
    // their way out is the same one they used to ask for nothing.
    const onFirstSlide = () => page.evaluate(() => {
      const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
      return dots.findIndex((d) => d.classList.contains('active'));
    });
    await openShare();
    const popoverOpenBeforeGroundClick = await page.evaluate(() => document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverOpenBeforeGroundClick) fail('popover did not open before the ground click');
    const slideBeforeGroundClick = await onFirstSlide();
    // The centre of the cover, far from the popover (bottom-right) and
    // from the nav buttons.
    await page.mouse.click(640, 400);
    await page.waitForTimeout(500); // a stray advance would have landed by now
    const popoverClosedByGroundClick = await page.evaluate(() => !document.getElementById('sharePopover').classList.contains('open'));
    if (!popoverClosedByGroundClick) fail('a ground click did not close the share popover');
    const slideAfterGroundClick = await onFirstSlide();
    if (slideAfterGroundClick !== slideBeforeGroundClick) {
      fail('a ground click that closes the popover advanced the deck: slide '
           + slideBeforeGroundClick + ' -> ' + slideAfterGroundClick);
    }
    // And the click is spent: a second ground click, popover now closed,
    // must navigate as usual — without this, the guard above passes on a
    // page where clicking does nothing at all.
    await page.mouse.click(640, 400);
    await page.waitForTimeout(500);
    const slideAfterSecondGroundClick = await onFirstSlide();
    if (slideAfterSecondGroundClick === slideBeforeGroundClick) {
      fail('a ground click with no popover open no longer advances the deck');
    }
    // Back to the cover for the steps that follow.
    await page.click('.nav-dots a:first-of-type');
    await page.waitForTimeout(800);

    // 2. Move to the next slide, then the fiche column stays enabled.
    await page.click('#navNext');
    await page.waitForTimeout(800); // matches nav.js's own scroll-settle timeout
    await openShare();
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
    // (The popover is still open from step 2/3 — opening the menu again
    // here would toggle it closed instead.)
    await page.click('[data-action="qr"][data-scope="series"]');
    const qrOpen = await page.evaluate(() => {
      const modal = document.getElementById('shareQrModal');
      return {
        open: modal.classList.contains('open'),
        role: modal.getAttribute('role'),
        modal: modal.getAttribute('aria-modal'),
        labelledby: modal.getAttribute('aria-labelledby'),
        focus: document.activeElement && document.activeElement.className,
      };
    });
    if (!qrOpen.open || qrOpen.role !== 'dialog' || qrOpen.modal !== 'true'
        || qrOpen.labelledby !== 'shareQrModalTitle'
        || qrOpen.focus !== 'share-qr-close') {
      fail('QR modal did not open as an accessible dialog: ' + JSON.stringify(qrOpen));
    }
    const qrUrlText = await page.textContent('#shareQrModalUrl');
    if (qrUrlText !== expectedSeriesUrl) {
      fail('QR modal URL mismatch: got ' + qrUrlText + ' expected ' + expectedSeriesUrl);
    }
    const rectCount = await page.evaluate(() =>
      document.querySelectorAll('#shareQrModalContent svg rect').length);
    if (rectCount < 10) fail('QR SVG has implausibly few rects: ' + rectCount);

    // 5. Closing the QR modal via its close button.
    await page.click('.share-qr-close');
    const qrClosed = await page.evaluate(() => ({
      closed: !document.getElementById('shareQrModal').classList.contains('open'),
      focus: document.activeElement && document.activeElement.id,
    }));
    if (!qrClosed.closed || qrClosed.focus !== 'navMenu') {
      fail('QR modal did not close and restore nav focus: ' + JSON.stringify(qrClosed));
    }

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
    await openShare();
    await page.click('[data-action="copy"][data-scope="fiche"]');
    const clipboardFiche = await page.evaluate(() => navigator.clipboard.readText());
    if (clipboardFiche !== expectedArticleUrl + '#' + ficheId) {
      fail('fiche copy-link mismatch: got ' + clipboardFiche + ' expected '
           + expectedArticleUrl + '#' + ficheId);
    }
    await page.keyboard.press('Escape');

    // 7. Move to the series-nav slide: the fiche column must be disabled
    // again — the scope follows the slide TYPE (§9.3.4), and series-nav
    // is not a reading position.
    await page.click('#navNext');
    await page.waitForTimeout(800);
    const onSeriesNav = await page.evaluate(() => {
      const s = document.querySelectorAll('section.slide');
      return s[s.length - 1].getBoundingClientRect().top < window.innerHeight / 2;
    });
    if (!onSeriesNav) fail('did not reach the series-nav slide after navNext');
    await openShare();
    const ficheDisabledOnSeriesNav = await page.evaluate(() =>
      Array.prototype.every.call(document.querySelectorAll('[data-scope="fiche"]'), (b) => b.disabled));
    if (!ficheDisabledOnSeriesNav) fail('fiche column must be disabled on the series-nav slide');

    if (consoleErrors.length) fail('unexpected console errors: ' + JSON.stringify(consoleErrors));

    if (process.exitCode) {
      return;
    }
    console.log('OK');
    process.exitCode = 0;
  } catch (err) {
    console.error('E2E failure: ' + err);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
