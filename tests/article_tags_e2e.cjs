// Playwright driver for article-tag filtering on the series index and nav.
// Invoked by tests/test_web.py -- not a standalone entry point.
// argv: <indexUrl> <articleUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

async function visibleArticleHrefs(page) {
  return page.locator('[data-lwp-article-card]').evaluateAll((cards) => cards
    .filter((card) => getComputedStyle(card).display !== 'none')
    .map((card) => card.getAttribute('href') || card.querySelector('.series-title')?.textContent.trim()));
}

async function expectVisible(page, expected) {
  try {
    await page.waitForFunction(
      (wanted) => Array.from(document.querySelectorAll('[data-lwp-article-card]'))
        .filter((card) => getComputedStyle(card).display !== 'none')
        .map((card) => card.getAttribute('href') || card.querySelector('.series-title')?.textContent.trim())
        .join('|') === wanted,
      expected.join('|'),
      { timeout: 5000 },
    );
  } catch (err) {
    throw new Error('expected ' + expected.join('|') + ', got '
      + JSON.stringify(await visibleArticleHrefs(page)));
  }
}

async function main() {
  const [indexUrl, articleUrl] = process.argv.slice(2);
  if (!indexUrl || !articleUrl) {
    console.error('usage: article_tags_e2e.cjs <indexUrl> <articleUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  const consoleErrors = [];
  collectConsoleErrors(page, consoleErrors);
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

  try {
    await page.goto(indexUrl);
    await page.waitForSelector('.article-card[data-lwp-article-card]');
    await expectVisible(page, ['a.html', 'c.html']);
    const defaultTag = await page.locator('body').getAttribute('data-lwp-default-tag');
    if (defaultTag !== 'fr') throw new Error('unexpected default tag: ' + defaultTag);

    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const activeDefault = await page.locator('#tagMenuCurrent').textContent();
    if (!activeDefault.includes('fr')) throw new Error('active tag is not visible: ' + activeDefault);
    const defaultPreview = await page.locator('#tagMenuPreview').textContent();
    if (!defaultPreview.includes('A') || !defaultPreview.includes('C')) {
      throw new Error('default preview does not list displayed articles: ' + defaultPreview);
    }
    await page.click('#tagMenuList .tag-option[data-tag="en"]');
    await expectVisible(page, ['b.html', 'c.html']);
    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const activeEnglish = await page.locator('#tagMenuCurrent').textContent();
    if (!activeEnglish.includes('en')) throw new Error('English tag is not visible: ' + activeEnglish);
    const englishPreview = await page.locator('#tagMenuPreview').textContent();
    if (!englishPreview.includes('B') || !englishPreview.includes('C')) {
      throw new Error('English preview does not list displayed articles: ' + englishPreview);
    }
    await page.keyboard.press('Escape');

    await page.goto(indexUrl);
    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    await page.click('#tagMenuList .tag-option[data-tag="fr"]');
    await page.goto(articleUrl);
    await page.waitForSelector('.series-item[data-lwp-article-card]');
    await expectVisible(page, ['A', 'c.html']);

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
