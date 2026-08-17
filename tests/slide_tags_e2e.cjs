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

    await page.click('#tagMenuList .tag-option[data-tag="en"]');
    await expectVisibleTags(page, ['default', 'en', 'default']);
    const selected = await page.evaluate(() => localStorage.getItem('lwp-active-tag'));
    if (selected !== 'en') throw new Error('tag was not persisted: ' + selected);

    await page.reload();
    await page.waitForSelector('section.slide[data-tags]');
    await expectVisibleTags(page, ['default', 'en', 'default']);

    if (consoleErrors.length) {
      throw new Error('unexpected console errors: ' + JSON.stringify(consoleErrors));
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
