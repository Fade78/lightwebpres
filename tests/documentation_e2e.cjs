const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let chromium;
try { ({ chromium } = require('playwright')); }
catch (error) { console.error(error.message); process.exit(77); }

(async () => {
  const browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
    ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
  try {
    for (const width of [390, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 844 } });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      page.on('requestfailed', request => errors.push(request.url()));
      const guide = path.resolve(__dirname, '../generated/guide/guide.html');
      await page.goto(pathToFileURL(guide).href, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      const link = page.locator('.full-article a[href="#2-make-your-first-personal-article"]');
      await link.scrollIntoViewIfNeeded();
      await link.focus();
      await page.keyboard.press('Enter');
      // Wait beyond the normal slide glide: a hash handler must not pull us back.
      await page.waitForTimeout(500);
      const chapter = page.locator('[id="2-make-your-first-personal-article"]');
      const bounds = await chapter.boundingBox();
      assert(bounds.y >= -1 && bounds.y < 200, `chapter not in view at ${width}: ${bounds.y}`);
      assert.equal(await chapter.evaluate(
        element => element === document.activeElement), true, 'chapter must receive keyboard focus');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      assert.deepEqual(await page.evaluate(() => [...document.images]
        .filter(image => !image.complete || !image.naturalWidth).map(image => image.src)), []);
      assert.deepEqual(errors, []);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
