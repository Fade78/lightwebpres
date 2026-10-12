// Real Display settings on an ordinary Markdown image, in both browser engines.
const assert = require('node:assert/strict');
let chromium, firefox;
try { ({ chromium, firefox } = require('playwright')); }
catch (error) { console.error('Playwright is unavailable in the supplied environment'); process.exit(77); }

(async () => {
  const url = process.argv[2];
  if (!url) throw Error('usage: image_reading_browser.cjs <built-page-URL>');
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    let browser;
    try { browser = await engine.launch({ timeout: 15000 }); }
    catch (error) {
      if (/executable doesn't exist/i.test(String(error))) {
        console.error(name + ' is unavailable in the supplied environment');
        process.exitCode = 77;
        return;
      }
      throw error;
    }
    try {
      const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto(url);
      await page.locator('#image figure img').evaluate(image => image.decode());
      const geometry = () => page.locator('#image figure img').evaluate(image => ({
        width: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
        style: image.getAttribute('style'),
      }));
      const near = (actual, expected, message) => {
        assert.ok(Math.abs(actual - expected) < 2,
          `${name} ${message}: ${actual} instead of ${expected}`);
      };
      const settle = () => page.evaluate(() => new Promise(resolve =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.keyboard.press('d');
      await page.waitForSelector('#readingMenu.open');
      await page.locator('[data-reading-option="object_shrink_horizontal"]').uncheck();
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      const baseline = await geometry();
      assert.ok(baseline.height > 700, `${name}: image does not exceed viewport`);
      for (const [button, times, factor] of [
        ['zoom-out', 5, .5], ['zoom-in', 15, 2], ['zoom-reset', 1, 1],
      ]) {
        for (let i = 0; i < times; i++) {
          await page.locator(`#readingMenu [data-menu-action="${button}"]`).click();
        }
        await settle();
        const image = await geometry();
        near(image.width, baseline.width * factor, `${button} width`);
        near(image.height, baseline.height * factor, `${button} height`);
        if (factor === 1) assert.deepEqual(image, baseline, `${name}: reset restores authored markup`);
      }
      await page.locator('[data-reading-option="object_shrink_vertical"]').check();
      await settle();
      const fitted = await geometry();
      assert.ok(fitted.height < baseline.height - 20
        && fitted.height >= baseline.height * .5 - 2, `${name}: height fit ${JSON.stringify({baseline, fitted})}`);
      await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
      assert.deepEqual(await geometry(), baseline, `${name}: print restores authored image`);
      await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
      await settle();
      near((await geometry()).height, fitted.height, `${name}: return from print`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      assert.deepEqual(await geometry(), baseline, `${name}: disabled fit restores source`);
      assert.deepEqual(errors, [], `${name}: browser errors`);
      await page.close();
      console.log(`${name}: responsive image controls passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
