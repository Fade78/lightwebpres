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
      await page.locator('#medium figure img').evaluate(image => image.decode());
      await page.locator('#giant figure img').evaluate(image => image.decode());
      const geometry = () => page.locator('#image figure img').evaluate(image => ({
        width: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
        style: image.getAttribute('style'),
      }));
      const slideHeight = id => page.locator('#' + id).evaluate(slide => ({
        rendered: slide.getBoundingClientRect().height,
        scroll: slide.scrollHeight,
        viewport: window.innerHeight,
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
      assert.ok(fitted.height < baseline.height * .5,
        `${name}: tall image needs a factor below the former 0.5 minimum: ${JSON.stringify({baseline, fitted})}`);
      const tallSlide = await slideHeight('image');
      assert.ok(tallSlide.rendered <= tallSlide.viewport + 1
        && tallSlide.scroll <= tallSlide.viewport + 1,
      `${name}: tall image and slide must fit with title and padding: ${JSON.stringify(tallSlide)}`);
      await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
      assert.deepEqual(await geometry(), baseline, `${name}: print restores authored image`);
      await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
      await settle();
      near((await geometry()).height, fitted.height, `${name}: return from print`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      assert.deepEqual(await geometry(), baseline, `${name}: disabled fit restores source`);

      const mediumBaseline = await page.locator('#medium figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      const captionBaseline = await page.locator('#medium figcaption').evaluate(caption =>
        caption.getBoundingClientRect().height);
      const giantBaseline = await page.locator('#giant figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      assert.equal(await page.locator('#medium .slide-chrome-footer').count(), 1,
        `${name}: the footer is actually rendered in the slide`);
      assert.ok(mediumBaseline < 700 && (await slideHeight('medium')).rendered > 700,
        `${name}: medium image alone fits but its title/summary/footer do not`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').check();
      await settle();
      const mediumFit = await slideHeight('medium');
      assert.ok(mediumFit.rendered <= mediumFit.viewport + 1
        && mediumFit.scroll <= mediumFit.viewport + 1,
      `${name}: medium image must leave room for title, summary and footer: ${JSON.stringify(mediumFit)}`);
      near(await page.locator('#medium figcaption').evaluate(caption =>
        caption.getBoundingClientRect().height), captionBaseline, 'image fitting keeps caption readable');
      const giantFit = await page.locator('#giant figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      assert.ok(giantFit / giantBaseline < .1 && (await slideHeight('giant')).rendered <= 701,
        `${name}: vertical fit must work below 10%: ${JSON.stringify({giantBaseline, giantFit})}`);
      const impossible = await slideHeight('impossible');
      assert.ok(impossible.rendered > impossible.viewport
        && await page.locator('#impossible').getAttribute('data-lwp-fit-overflow') === 'true',
      `${name}: prose too long without image must still scroll`);
      assert.ok(await page.locator('#impossible figure img').evaluate(image =>
        image.getBoundingClientRect().height) > 500,
      `${name}: do not hide an image when reducing it cannot make the text fit`);
      assert.deepEqual(errors, [], `${name}: browser errors`);
      await page.close();
      console.log(`${name}: responsive image controls passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
