// Playwright driver for slide-tag filtering on a generated article page.
// Invoked by tests/test_web.py — not a standalone entry point.
// argv: <pageUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

// VISIBLE means the browser is not painting it, not `section.hidden`.
//
// `hidden` is the property the filter's own script sets, so reading it
// back only proves the script ran. What makes a filtered card disappear
// is the stylesheet's `.slide[hidden] { display: none }` override --
// needed because an author-origin `.slide { display: flex }` beats the
// UA rule for [hidden]. Measured: neutralising that override with a
// later, equal-specificity `.slide[hidden] { display: flex }` left this
// driver green and every filtered card fully on screen. The one thing
// the feature promises was the one thing nothing checked.
async function visibleTags(page) {
  return page.locator('section.slide').evaluateAll((sections) =>
    sections.filter((section) => getComputedStyle(section).display !== 'none')
      .map((section) => section.getAttribute('data-tags')),
  );
}

async function expectVisibleTags(page, expected) {
  await page.waitForFunction(
    (wanted) => Array.from(document.querySelectorAll('section.slide'))
      .filter((section) => getComputedStyle(section).display !== 'none')
      .map((section) => section.getAttribute('data-tags'))
      .join('|') === wanted,
    expected.join('|'),
  );
}

async function main() {
  const [pageUrl] = process.argv.slice(2);
  if (!pageUrl) {
    console.error('usage: slide_tags_e2e.cjs <pageUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  const consoleErrors = [];
  collectConsoleErrors(page, consoleErrors);
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

  try {
    await page.goto(pageUrl);
    await page.waitForSelector('section.slide[data-tags]');
    await expectVisibleTags(page, ['default', 'default']);

    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const options = await page.locator('#tagMenuList .tag-option').evaluateAll(
      (buttons) => buttons.map((button) => button.getAttribute('data-tag')),
    );
    if (options.join('|') !== 'default|en|fr') {
      throw new Error('unexpected tag menu: ' + options.join('|'));
    }

    // A click on the GROUND while the menu is open closes it and does
    // NOT advance the deck (§4.3.1): closing the dialog you opened is
    // not a navigation.
    const activeSlide = () => page.evaluate(() => {
      const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
      return dots.findIndex((d) => d.classList.contains('active'));
    });

    // Overlay controls are deliberate transitions, not covered navigation:
    // leaving the tag menu through the presenter menu must reach the menu's
    // own handler, then share and tags must be reachable from that path.
    await page.click('#navMenu');
    await page.waitForFunction(() => document.getElementById('presenterMenu').classList.contains('open'));
    await page.click('#menuShare');
    await page.waitForFunction(() => document.getElementById('sharePopover').classList.contains('open'));
    await page.click('#navMenu');
    await page.waitForFunction(() =>
      document.getElementById('presenterMenu').classList.contains('open')
      && !document.getElementById('sharePopover').classList.contains('open'));
    await page.click('#menuTags');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    await page.keyboard.press('Escape');

    // The QR modal is the same modal boundary as the other share surfaces:
    // a navigation click while it is open closes it without moving the deck.
    await page.click('#navMenu');
    await page.waitForFunction(() => document.getElementById('presenterMenu').classList.contains('open'));
    await page.click('#menuShare');
    await page.waitForFunction(() => document.getElementById('sharePopover').classList.contains('open'));
    await page.click('[data-action="qr"][data-scope="series"]');
    await page.waitForFunction(() => document.getElementById('shareQrModal').classList.contains('open'));
    const beforeQrNav = await activeSlide();
    await page.evaluate(() => document.getElementById('navNext').click());
    await page.waitForFunction(() => !document.getElementById('shareQrModal').classList.contains('open'));
    await page.waitForTimeout(500);
    const afterQrNav = await activeSlide();
    if (afterQrNav !== beforeQrNav) {
      throw new Error('a navigation click that closed the QR modal advanced the deck: '
        + beforeQrNav + ' -> ' + afterQrNav);
    }

    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const beforeGround = await activeSlide();
    await page.mouse.click(640, 300);
    await page.waitForFunction(() => !document.getElementById('tagMenu').classList.contains('open'));
    await page.waitForTimeout(500); // a stray advance would have landed by now
    const afterGround = await activeSlide();
    if (afterGround !== beforeGround) {
      throw new Error('a ground click that closed the tag menu advanced the deck: '
        + beforeGround + ' -> ' + afterGround);
    }
    // And the click is spent: with the menu closed the same ground click
    // navigates as usual.
    await page.mouse.click(640, 300);
    await page.waitForTimeout(500);
    const afterSecondGround = await activeSlide();
    if (afterSecondGround === afterGround) {
      throw new Error('a ground click with no menu open no longer advances the deck');
    }
    // Back to the first card before the filter steps below.
    await page.click('.nav-dots a:first-of-type');
    await page.waitForTimeout(800);

    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    await page.click('#tagMenuList .tag-option[data-tag="en"]');
    await expectVisibleTags(page, ['default', 'en', 'default']);
    const selected = await page.evaluate(() => localStorage.getItem('lwp-active-tag'));
    if (selected !== 'en') throw new Error('tag was not persisted: ' + selected);

    // Clicking a navigation control while the menu is open closes the dialog
    // without activating the control underneath it.
    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const beforeCoveredNav = await activeSlide();
    await page.click('#navNext');
    await page.waitForFunction(() => !document.getElementById('tagMenu').classList.contains('open'));
    await page.waitForTimeout(500);
    const afterCoveredNav = await activeSlide();
    if (afterCoveredNav !== beforeCoveredNav) {
      throw new Error('a navigation click that closed the tag menu advanced the deck: '
        + beforeCoveredNav + ' -> ' + afterCoveredNav);
    }

    // Reopening the menu must not clear the selection: the "en" card
    // stays visible after a reload below, and the menu must still offer
    // the same three tags.
    await page.reload();
    await page.waitForSelector('section.slide[data-tags]');
    await expectVisibleTags(page, ['default', 'en', 'default']);

    if (consoleErrors.length) {
      throw new Error('unexpected console errors: ' + JSON.stringify(consoleErrors));
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
