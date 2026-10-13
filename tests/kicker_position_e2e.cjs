// Read real rendered geometry, including pre-rendered Identity Kit alternatives.
const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const [articleURL, combinedURL, placement] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [url, combined] of [[articleURL, false], [combinedURL, true]]) {
        const page = await browser.newPage({viewport: {width: 1000, height: 800}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url + (combined ? '#lwp/a/a.html/inherited' : '#inherited'));
        const settle = () => page.evaluate(() => new Promise(resolve =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await settle();
        const measure = slug => page.locator('#' + slug).evaluate(slide => {
          const box = node => {
            const rect = node.getBoundingClientRect();
            return {top: rect.top, bottom: rect.bottom, height: rect.height};
          };
          const kicker = slide.querySelector('.slide-kicker');
          const header = slide.querySelector('.slide-chrome-header');
          return {slide: box(slide), header: header ? box(header) : null,
            kicker: box(kicker), heading: box(slide.querySelector('h1, h2')),
            region: !!kicker.closest('.slide-header-region'),
            inChrome: !!kicker.closest('.slide-chrome'),
            count: slide.querySelectorAll('.slide-kicker').length,
            viewport: innerHeight, scroll: slide.scrollHeight};
        });
        const check = async (slug, afterHeader, edge) => {
          const actual = await measure(slug);
          assert.equal(actual.count, 1, `${name} ${slug}: one kicker, not a copy`);
          assert.equal(actual.region, afterHeader, `${name} ${slug}: resolved position`);
          assert.equal(actual.inChrome, false, `${name}: kicker is not header content`);
          assert.ok(actual.slide.height <= actual.viewport + 1 && actual.scroll <= actual.viewport + 1,
            `${name} ${slug}: the whole slide fits: ${JSON.stringify(actual)}`);
          if (afterHeader) {
            if (actual.header) {
              assert.ok(actual.kicker.top >= actual.header.bottom - 1
                && actual.kicker.top - actual.header.bottom < 25,
              `${name}: kicker stays immediately below header: ${JSON.stringify(actual)}`);
            }
            if (edge) assert.ok(actual.kicker.top - actual.slide.top < 150,
              `${name}: header-attached kicker stays at the upper edge: ${JSON.stringify(actual)}`);
          } else {
            assert.ok(actual.heading.top >= actual.kicker.bottom - 1
              && actual.heading.top - actual.kicker.bottom < 25,
            `${name}: title-attached kicker stays immediately above title: ${JSON.stringify(actual)}`);
          }
        };
        const choose = async selector => {
          await page.keyboard.press('c');
          await page.locator('#themeMenu.open').waitFor();
          const identity = selector === 'builtin/standard' ? 'builtin' : 'kicker-test@1.0.0';
          await page.locator(`#identityOptions [data-identity="${identity}"]`).click();
          await page.locator(`#presentationOptions [data-presentation="${selector}"]`).click();
          await settle();
        };
        await check('inherited', false, true);
        for (const viewport of [{width: 1000, height: 800}, {width: 390, height: 844}]) {
          await choose('kicker-test@1.0.0/test');
          await page.setViewportSize(viewport);
          await settle();
          await check('inherited', true, placement === 'edge');
          await check('pinned', false, placement === 'edge');
          await check('no-header', true, placement === 'edge');
          for (const slug of ['cover', 'contents', 'long']) {
            await check(slug, true, placement === 'edge');
          }
          assert.equal(await page.locator('#long .slide-header-region [data-lwp-i18n="full_article_kicker"]').count(), 1,
            `${name}: relocating a generated kicker retains localization`);
          await page.emulateMedia({media: 'print'});
          assert.equal(await page.locator('#inherited .slide-header-region .slide-kicker').count(), 1,
            `${name}: print retains the semantic placement`);
          await page.emulateMedia({media: 'screen'});
          await settle();
          await page.keyboard.press('d');
          await page.locator('#readingMenu.open').waitFor();
          for (let n = 0; n < 5; n++) {
            await page.locator('#readingMenu [data-menu-action="zoom-in"]').click();
          }
          await settle();
          await check('inherited', true, placement === 'edge');
          await page.locator('#readingMenu [data-menu-action="zoom-reset"]').click();
          await page.keyboard.press('Escape');
          await page.keyboard.press('Escape');
          await choose('builtin/standard');
          await check('inherited', false, true);
        }
        if (combined) {
          await choose('kicker-test@1.0.0/test');
          await page.evaluate(() => { location.hash = '#lwp/a/b.html/second'; });
          await page.locator('#second').waitFor();
          await settle();
          await check('second', false, placement === 'edge');
        }
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();
      }
      console.log(`${name}: kicker placement checks passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
