const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable'); process.exit(77); }

(async () => {
  const urls = process.argv.slice(2);
  for (const [name, engine, scales] of [
    ['chromium', chromium, [1.25, 1.5]], ['firefox', firefox, [1.5, 1.75]],
  ]) {
    let fractional = false;
    for (const scale of scales) {
      const options = {timeout: 15000, args: name === 'chromium'
        ? ['--window-size=1423,913', '--force-device-scale-factor=' + scale]
        : ['--width=1423', '--height=913']};
      if (name === 'firefox') options.firefoxUserPrefs = {'layout.css.devPixelsPerPx': String(scale)};
      let browser;
      try { browser = await engine.launch(options); }
      catch (error) {
        if (/executable doesn't exist/i.test(String(error))) {
          console.error(name + ' unavailable'); process.exitCode = 77; return;
        }
        throw error;
      }
      try {
        // Do not force an integer Playwright viewport: it conceals the bug.
        const context = await browser.newContext({viewport: null});
        for (const [index, url] of urls.entries()) {
          const page = await context.newPage();
          const errors = [];
          page.on('pageerror', error => errors.push(String(error)));
          await page.goto(url + (index ? '#lwp/a/a.html/figure' : '#figure'));
          await page.locator('#figure img').waitFor();
          await page.evaluate(async () => {
            await document.fonts.ready;
            await Promise.all([...document.images].map(image => image.decode()));
          });
          const settle = () => page.evaluate(() => new Promise(resolve =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))));
          const measure = () => page.evaluate(() => ({
            viewport: document.documentElement.clientHeight, dpr: devicePixelRatio,
            slides: [...document.querySelectorAll('.slide')].map(slide => ({
              id: slide.id, minimum: parseFloat(getComputedStyle(slide).minHeight),
              height: slide.getBoundingClientRect().height, scroll: slide.scrollHeight,
              overflow: slide.getAttribute('data-lwp-fit-overflow'),
              images: [...slide.querySelectorAll('img')].map(image => ({
                width: image.getBoundingClientRect().width, height: image.getBoundingClientRect().height,
                ratio: image.naturalWidth / image.naturalHeight})),
            })),
          }));
          const check = async (state, allowTextOverflow = false) => {
            await settle();
            const actual = await measure();
            if (allowTextOverflow) {
              // At high native DPI a 150% text zoom can exceed this small
              // window even without an image. Preserve that scrolling contract,
              // but prove the non-image floor rather than accepting any overflow.
              const floors = await page.locator('.slide').evaluateAll(slides => slides.map(slide => {
                const originals = [...slide.querySelectorAll('img')].map(image => [image, image.getAttribute('style')]);
                for (const [image] of originals) for (const [property, value] of Object.entries({
                  width: '0px', height: '0px', 'min-width': '0px', 'min-height': '0px',
                  'max-width': 'none', 'max-height': 'none', zoom: '1',
                })) image.style.setProperty(property, value, 'important');
                const floor = Math.max(slide.getBoundingClientRect().height, slide.scrollHeight);
                for (const [image, style] of originals) {
                  if (style === null) image.removeAttribute('style'); else image.setAttribute('style', style);
                }
                return floor;
              }));
              actual.slides.forEach((slide, index) => { slide.nonImageFloor = floors[index]; });
            }
            fractional ||= actual.slides.some(slide => slide.minimum > actual.viewport + .05
              && slide.minimum < actual.viewport + 1);
            assert.ok(actual.slides.length === 3 && actual.slides.every(slide =>
              ((slide.height <= actual.viewport + 1 && slide.scroll <= actual.viewport + 1)
                || (allowTextOverflow && slide.nonImageFloor > actual.viewport + 1 && slide.overflow === 'true'))
              && slide.images.every(image => image.width > 0 && image.height > 0
                && Math.abs(image.width / image.height - image.ratio) < .03)),
            name + ' ' + scale + ' ' + state + ': ' + JSON.stringify(actual));
          };
          await check('initial native window');
          await page.keyboard.press('f');
          await page.waitForFunction(() => !!document.fullscreenElement);
          await check('native fullscreen');
          await page.keyboard.press('f');
          await page.waitForFunction(() => !document.fullscreenElement);
          await check('native window after fullscreen');
          await page.keyboard.press('d');
          await page.locator('#readingMenu.open').waitFor();
          for (let n = 0; n < 5; n++) await page.locator('[data-menu-action="zoom-in"]').click();
          await check('reader zoom 150%', true);
          assert.deepEqual(errors, []);
          await page.close();
        }
        await context.close();
      } finally { await browser.close(); }
    }
    assert.ok(fractional, name + ': fixture must exercise a positive fractional viewport remainder');
    console.log(name + ': native fractional viewport fitting passed');
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
