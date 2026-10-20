const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable'); process.exit(77); }

(async () => {
  const [mode, ...urls] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    let browser;
    try { browser = await engine.launch({timeout: 15000}); }
    catch (error) {
      if (/executable doesn't exist/i.test(String(error))) {
        console.error(name + ' unavailable'); process.exitCode = 77; return;
      }
      throw error;
    }
    try {
      for (const [index, url] of urls.entries()) {
        const context = await browser.newContext();
        await context.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
          configurable: true, value: {writeText(text) { window.copiedSeries = text; return Promise.resolve(); }},
        }));
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url);
        if (mode === 'tags') {
          assert.equal(await page.locator('section.slide:not([hidden])').count(), 2,
            name + ': a legal prototype-name tag must not hide the article');
          assert.equal(await page.locator('#tagEmptyState').evaluate(node => node.hidden), true);
          await page.keyboard.press('l');
          const option = page.locator('#tagMenuList .tag-option[data-tag="constructor"]');
          assert.equal(await option.count(), 1);
          assert.equal(await option.getAttribute('aria-pressed'), 'true');
          assert.equal(await option.getAttribute('aria-disabled'), null);
          await option.click();
          await page.reload();
          assert.equal(await page.locator('section.slide:not([hidden])').count(), 2,
            'saved constructor choice remains readable after reload');
        } else {
          const home = index ? new URL('#lwp/index', url).href : new URL('Index.html', url).href;
          if (index) {
            assert.equal(await page.locator('.series-link').last().getAttribute('href'), '#lwp/index',
              'combined contents stay distinct from an Index.html article key');
          } else {
            assert.equal(await page.locator('.series-link').count(), 0,
              'no-index publication does not invent a back-to-index link');
          }
          await page.keyboard.press('s');
          await page.locator('.share-action[data-action="copy"][data-scope="series"]').click();
          assert.equal(await page.evaluate(() => window.copiedSeries), home, 'series sharing reaches the actual home');
          await page.keyboard.press('Escape');
          await page.keyboard.press('PageDown');
          if (index) {
            await page.keyboard.press('Control+Home');
            await page.waitForFunction(() => document.body.classList.contains('index-page'));
            assert.equal(page.url(), home);
            assert.ok((await page.locator('.article-card').first().getAttribute('href')).includes('/Index.html'));
          } else {
            await Promise.all([page.waitForEvent('domcontentloaded'), page.keyboard.press('Control+Home')]);
            assert.equal(page.url().split('#')[0], home);
          }
        }
        assert.deepEqual(errors, []);
        await context.close();
      }
      console.log(name + ': ' + mode + ' regression passed');
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
