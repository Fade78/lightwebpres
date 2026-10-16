// Exercise Markdown-generated spans, not a separately authored HTML table.
const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [combined, url] of process.argv.slice(2).entries()) {
        const page = await browser.newPage({viewport: {width: 900, height: 700}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url + (combined ? '#lwp/a/a.html/auto' : '#auto'));
        await page.locator('.slide img').evaluateAll(images => Promise.all(images.map(image => image.decode())));
        const settle = () => page.evaluate(() => new Promise(resolve =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const structure = () => page.locator('.comparison-table').evaluateAll(tables =>
          tables.map(table => [...table.rows].map(row => [...row.cells].map(cell =>
            [cell.tagName, cell.colSpan, cell.rowSpan, cell.textContent.trim(), cell.querySelectorAll('img').length]))));
        const expected = [
          [[['TD', 2, 2, '', 1], ['TD', 1, 2, '', 1]], [],
            [['TD', 2, 1, 'Landscape', 0], ['TD', 1, 1, 'Portrait', 0]]],
          [[['TH', 2, 1, 'Pictures', 0], ['TH', 1, 1, 'Portrait', 0]],
            [['TD', 2, 2, '', 1], ['TD', 1, 2, '', 1]], [],
            [['TD', 2, 1, 'Landscape', 0], ['TD', 1, 1, 'Portrait', 0]]],
        ];
        assert.deepEqual(await structure(), expected, `${name}: native merged grid`);
        const check = async state => {
          await settle();
          assert.deepEqual(await structure(), expected, `${name} ${state}: spans and content stay intact`);
          const slides = await page.locator('.slide').evaluateAll(slides => slides.map(slide => {
            const viewport = slide.querySelector('.lwp-table-viewport').getBoundingClientRect();
            return {slug: slide.id, height: slide.getBoundingClientRect().height,
              scroll: slide.scrollHeight, viewport: innerHeight, budget: viewport.width,
              images: [...slide.querySelectorAll('img')].map(image => {
                const box = image.getBoundingClientRect();
                return {width: box.width, height: box.height, left: box.left - viewport.left,
                  right: box.right - viewport.left, ratio: image.naturalWidth / image.naturalHeight};
              })};
          }));
          for (const slide of slides) {
            assert.ok(slide.height <= slide.viewport + 1 && slide.scroll <= slide.viewport + 1
              && slide.images.every(image => image.width > 0 && image.height > 0
                && image.left >= -1 && image.right <= slide.budget + 1.1
                && Math.abs(image.width / image.height - image.ratio) < .025),
            `${name} ${state}: merged images fit without distortion: ${JSON.stringify(slide)}`);
          }
        };
        await page.keyboard.press('d');
        await page.locator('#readingMenu.open').waitFor();
        for (const option of ['object_shrink_horizontal', 'object_shrink_vertical']) {
          await page.locator(`[data-reading-option="${option}"]`).uncheck();
        }
        await settle();
        const authored = await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style')));
        for (const option of ['object_shrink_horizontal', 'object_shrink_vertical']) {
          await page.locator(`[data-reading-option="${option}"]`).check();
        }
        await page.keyboard.press('Escape');
        await check('initial');
        await page.setViewportSize({width: 1800, height: 700});
        await check('wide window');
        await page.keyboard.press('f');
        await page.waitForFunction(() => !!document.fullscreenElement, null, {timeout: 5000});
        await check('native fullscreen');
        await page.keyboard.press('f');
        await page.waitForFunction(() => !document.fullscreenElement, null, {timeout: 5000});
        await check('fullscreen exit');
        for (const viewport of [{width: 390, height: 844}, {width: 1280, height: 720},
                                {width: 900, height: 700}]) {
          await page.setViewportSize(viewport);
          await check(`${viewport.width}x${viewport.height}`);
        }
        await page.keyboard.press('d');
        await page.locator('#readingMenu.open').waitFor();
        for (let n = 0; n < 5; n++) await page.locator('[data-menu-action="zoom-in"]').click();
        await check('reader zoom 150%');
        await page.emulateMedia({media: 'print'});
        await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
        assert.deepEqual(await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style'))), authored,
        `${name}: print restores authored image dimensions`);
        assert.deepEqual(await structure(), expected, `${name}: print retains the merged grid`);
        await page.emulateMedia({media: 'screen'});
        await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
        await check('return from print');
        await page.locator('[data-menu-action="zoom-reset"]').click();
        for (const option of ['object_shrink_horizontal', 'object_shrink_vertical']) {
          await page.locator(`[data-reading-option="${option}"]`).uncheck();
        }
        await settle();
        assert.deepEqual(await page.locator('.slide img').evaluateAll(images =>
          images.map(image => image.getAttribute('style'))), authored,
        `${name}: disabled fitting restores authored image dimensions`);
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();
      }
      console.log(`${name}: Markdown table spans passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
