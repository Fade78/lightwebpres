// Playwright driver for comparing the series-tags report with the rendered
// index cards and article slides.
// Invoked by tests/test_web.py -- not a standalone entry point.
// argv: <indexUrl> <reportJson> <articleUrl...>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

async function visibleArticleCount(page) {
  return page.locator('[data-lwp-article-card]').evaluateAll((cards) => cards
    .filter((card) => getComputedStyle(card).display !== 'none').length);
}

async function visibleSlideCount(page) {
  return page.locator('section.slide').evaluateAll((slides) => slides
    .filter((slide) => getComputedStyle(slide).display !== 'none').length);
}

async function selectTag(page, indexUrl, tag) {
  await page.goto(indexUrl);
  await page.evaluate(() => localStorage.removeItem('lwp-active-tag'));
  await page.reload();
  await page.keyboard.press('l');
  await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
  const clicked = await page.locator('#tagMenuList .tag-option').evaluateAll(
    (buttons, wanted) => {
      const button = buttons.find((candidate) => candidate.getAttribute('data-tag') === wanted);
      if (button) button.click();
      return !!button;
    }, tag,
  );
  if (!clicked) throw new Error('tag is missing from the runtime menu: ' + tag);
}

async function main() {
  const [indexUrl, reportJson, ...articleUrls] = process.argv.slice(2);
  if (!indexUrl || !reportJson || !articleUrls.length) {
    console.error('usage: tag_report_e2e.cjs <indexUrl> <reportJson> <articleUrl...>');
    process.exit(2);
  }

  let rows;
  try {
    rows = JSON.parse(reportJson);
  } catch (err) {
    console.error('invalid report JSON: ' + err);
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

    for (const row of rows) {
      await selectTag(page, indexUrl, row.tag);
      const articleCount = await visibleArticleCount(page);
      if (articleCount !== row.output.articles) {
        throw new Error(row.tag + ': report has ' + row.output.articles
          + ' active article(s), browser shows ' + articleCount);
      }

      let slideCount = 0;
      for (const articleUrl of articleUrls) {
        await page.goto(articleUrl);
        await page.waitForSelector('section.slide', { state: 'attached' });
        slideCount += await visibleSlideCount(page);
      }
      if (slideCount !== row.output.slides) {
        throw new Error(row.tag + ': report has ' + row.output.slides
          + ' active slide(s), browser shows ' + slideCount);
      }
    }

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
