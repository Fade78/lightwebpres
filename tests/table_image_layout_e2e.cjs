const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const urls = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [index, url] of urls.entries()) {
        const page = await browser.newPage({viewport: {width: 900, height: 700}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url + (index ? '#lwp/a/a.html/fixed' : '#fixed'));
        await page.locator('.slide img').evaluateAll(images => Promise.all(images.map(image => image.decode())));
        assert.equal(await page.locator('#fixed h2 strong').textContent(), 'Mixed');
        assert.equal(await page.locator('#fixed .summary em').textContent(), 'ratios');
        const settle = () => page.evaluate(() => new Promise(resolve =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await settle();
        assert.equal(await page.locator('#raw-blank thead').evaluate(node => node.getBoundingClientRect().height), 0);
        assert.notEqual(await page.locator('#raw-labelled thead').evaluate(node => getComputedStyle(node).display), 'none');
        const geometry = () => page.locator('.slide').evaluateAll(slides => slides.map(slide => {
          const viewport = slide.querySelector('.lwp-table-viewport').getBoundingClientRect();
          return {slug: slide.id, height: slide.getBoundingClientRect().height,
            scroll: slide.scrollHeight, viewport: innerHeight, budget: viewport.width,
            images: [...slide.querySelectorAll('img')].map(image => {
              const rect = image.getBoundingClientRect();
              return {width: rect.width, height: rect.height, left: rect.left - viewport.left,
                right: rect.right - viewport.left, ratio: image.naturalWidth / image.naturalHeight};
            })};
        }));
        const check = async state => {
          const slides = await geometry();
          for (const slide of slides) {
            assert.ok(slide.height <= slide.viewport + 1 && slide.scroll <= slide.viewport + 1
              && slide.images.every(image => image.left >= -1 && image.right <= slide.budget + 1.1
                && Math.abs(image.width / image.height - image.ratio) < .025),
            `${name} ${state}: entire row fits, with intact ratios: ${JSON.stringify(slide)}`);
          }
        };
        await page.keyboard.press('d');
        await page.locator('#readingMenu.open').waitFor();
        await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
        await page.locator('[data-reading-option="object_shrink_horizontal"]').uncheck();
        await settle();
        const baseline = await geometry();
        const authoredStyles = await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style')));
        await page.locator('[data-reading-option="object_shrink_horizontal"]').check();
        await page.locator('[data-reading-option="object_shrink_vertical"]').check();
        await settle();
        await check('initial');
        const fitted = await geometry();
        assert.ok(fitted[0].images[0].width >= baseline[0].images[0].width * .98,
          `${name}: the wide image must use its own available cell, not the portrait's factor: `
            + JSON.stringify({baseline: baseline[0], fitted: fitted[0]}));
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
        await page.setViewportSize({width: 1800, height: 700});
        await settle();
        await check('wide window');
        await page.keyboard.press('f');
        await page.waitForFunction(() => !!document.fullscreenElement, null, {timeout: 5000});
        await settle();
        await check('native fullscreen');
        await page.keyboard.press('f');
        await page.waitForFunction(() => !document.fullscreenElement, null, {timeout: 5000});
        await settle();
        await check('fullscreen exit');
        for (const viewport of [{width: 1280, height: 720}, {width: 1920, height: 1080},
                                {width: 900, height: 700}]) {
          await page.setViewportSize(viewport);
          await settle();
          await check(`${viewport.width}x${viewport.height}`);
        }
        await page.keyboard.press('d');
        await page.locator('#readingMenu.open').waitFor();
        for (let n = 0; n < 5; n++) await page.locator('[data-menu-action="zoom-in"]').click();
        await settle();
        await check('reader zoom 150%');
        await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
        assert.deepEqual(await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style'))), authoredStyles,
        `${name}: print restores authored dimensions`);
        await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
        await settle();
        await check('return from print');
        await page.locator('[data-menu-action="zoom-reset"]').click();
        await page.locator('[data-reading-option="object_shrink_horizontal"]').uncheck();
        await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
        await settle();
        assert.deepEqual(await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style'))), authoredStyles,
        `${name}: disabled fitting restores authored dimensions`);
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();
      }
      console.log(`${name}: independent table image checks passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
