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
  const [indexUrl, articleUrl, frenchOnlyUrl] = process.argv.slice(2);
  if (!indexUrl || !articleUrl || !frenchOnlyUrl) {
    console.error('usage: article_tags_e2e.cjs <indexUrl> <articleUrl> <frenchOnlyUrl>');
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

    // `default` remains in the vocabulary even when no index card carries
    // it. The runtime must fall back to the first tag that publishes cards
    // instead of showing an empty index.
    await page.evaluate(() => localStorage.setItem('lwp-active-tag', 'default'));
    await page.reload();
    await page.waitForSelector('.article-card[data-lwp-article-card]');
    await expectVisible(page, ['a.html', 'c.html']);
    const indexFallback = await page.evaluate(() => ({
      tag: localStorage.getItem('lwp-active-tag'),
      empty: !document.getElementById('tagEmptyState').hidden,
    }));
    if (indexFallback.tag !== 'fr' || indexFallback.empty) {
      throw new Error('an unavailable index tag was not replaced: '
        + JSON.stringify(indexFallback));
    }

    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const activeDefault = await page.locator('#tagMenuCurrent').textContent();
    if (!activeDefault.includes('fr')) throw new Error('active tag is not visible: ' + activeDefault);
    const unavailableDefault = await page.locator('#tagMenuList .tag-option[data-tag="default"]')
      .evaluate((button) => ({
        disabled: button.getAttribute('aria-disabled'),
        reason: document.getElementById(button.getAttribute('aria-describedby'))?.textContent,
      }));
    if (unavailableDefault.disabled !== 'true'
        || !(unavailableDefault.reason.includes('No published article')
          || unavailableDefault.reason.includes('fiche publiée'))) {
      throw new Error('unavailable index tag has no explanation: '
        + JSON.stringify(unavailableDefault));
    }
    const defaultPreview = await page.locator('#tagMenuPreview').textContent();
    if (!defaultPreview.includes('A') || !defaultPreview.includes('C')) {
      throw new Error('default preview does not list displayed articles: ' + defaultPreview);
    }
    await page.click('#tagMenuList .tag-option[data-tag="en"]');
    await expectVisible(page, ['b.html']);
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

    // `en` exists in the series vocabulary but is unavailable on article A
    // because its article-level tags restrict it to `fr`. Keep the choice
    // visible in the menu, disabled, and explain the gate instead of silently
    // accepting a click and falling back.
    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const unavailableEnglish = page.locator('#tagMenuList .tag-option[data-tag="en"]');
    const englishReason = await unavailableEnglish.evaluate((button) => ({
      disabled: button.getAttribute('aria-disabled'),
      descriptionId: button.getAttribute('aria-describedby'),
      description: document.getElementById(button.getAttribute('aria-describedby'))?.textContent,
      opacity: getComputedStyle(button).opacity,
    }));
    if (englishReason.disabled !== 'true'
        || !(englishReason.description.includes('article')
          || englishReason.description.includes('fiche'))
        || !englishReason.description.includes('fr')
        || !englishReason.descriptionId
        || Number(englishReason.opacity) >= 1) {
      throw new Error('article-gated tag has no accessible explanation: '
        + JSON.stringify(englishReason));
    }
    await unavailableEnglish.focus();
    const tooltip = await unavailableEnglish.evaluate((button) => {
      const description = document.getElementById(button.getAttribute('aria-describedby'));
      return {
        content: description.textContent,
        display: getComputedStyle(description).display,
      };
    });
    if (!(tooltip.content.includes('article') || tooltip.content.includes('fiche'))
        || tooltip.display === 'none') {
      throw new Error('focused unavailable tag has no visible tooltip: '
        + JSON.stringify(tooltip));
    }
    // The option is aria-disabled rather than natively disabled so that it
    // remains focusable and its reason can be announced; its handler must
    // still make activation a no-op.
    await unavailableEnglish.evaluate((button) => button.click());
    const selectedFallback = await page.evaluate(() => ({
      tag: localStorage.getItem('lwp-active-tag'),
      visibleSlides: Array.prototype.filter.call(
        document.querySelectorAll('section.slide'),
        (slide) => getComputedStyle(slide).display !== 'none').length,
      menuOpen: document.getElementById('tagMenu').classList.contains('open'),
    }));
    if (selectedFallback.tag !== 'fr' || selectedFallback.visibleSlides === 0
        || !selectedFallback.menuOpen) {
      throw new Error('activating an unavailable tag changed the page: '
        + JSON.stringify(selectedFallback));
    }

    // A tag that is allowed at article level can still have no matching slide.
    await page.goto(frenchOnlyUrl);
    await page.keyboard.press('l');
    await page.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const noSlideEnglish = await page.locator('#tagMenuList .tag-option[data-tag="en"]')
      .evaluate((button) => ({
        disabled: button.getAttribute('aria-disabled'),
        reason: document.getElementById(button.getAttribute('aria-describedby'))?.textContent,
      }));
    if (noSlideEnglish.disabled !== 'true'
        || !(noSlideEnglish.reason.includes('no slides')
          || noSlideEnglish.reason.includes('Aucune slide'))) {
      throw new Error('tag without matching slides has no explanation: '
        + JSON.stringify(noSlideEnglish));
    }

    // `default` is present in the runtime vocabulary even when this article
    // has no default slide. It must not leave the article blank: the series
    // default `fr` is the first publishable choice here.
    await page.evaluate(() => localStorage.setItem('lwp-active-tag', 'default'));
    await page.reload();
    await page.waitForSelector('section.slide', { state: 'attached' });
    const fallback = await page.evaluate(() => ({
      tag: localStorage.getItem('lwp-active-tag'),
      visibleSlides: Array.prototype.filter.call(
        document.querySelectorAll('section.slide'),
        (slide) => getComputedStyle(slide).display !== 'none').length,
      empty: !document.getElementById('tagEmptyState').hidden,
    }));
    if (fallback.tag !== 'fr' || fallback.visibleSlides === 0 || fallback.empty) {
      throw new Error('an unavailable tag left the article empty: '
        + JSON.stringify(fallback));
    }

    const frenchContext = await browser.newContext({locale: 'fr-FR'});
    const frenchPage = await frenchContext.newPage();
    await frenchPage.goto(articleUrl);
    await frenchPage.keyboard.press('l');
    await frenchPage.waitForFunction(() => document.getElementById('tagMenu').classList.contains('open'));
    const frenchReason = await frenchPage.locator('#tagMenuList .tag-option[data-tag="en"]')
      .evaluate((button) => document.getElementById(
        button.getAttribute('aria-describedby')).textContent);
    if (!frenchReason || !(frenchReason.includes('métadonnées')
        || frenchReason.includes('champ tags'))
        || !frenchReason.includes('fr')) {
      throw new Error('unavailable-tag explanation is not localized: ' + frenchReason);
    }
    await frenchContext.close();

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
