const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) {console.error('Playwright unavailable in supplied environment'); process.exit(77);}
(async () => {
  const [article, authorArticle, bundle, hashes] = process.argv.slice(2);
  const imageHashes = JSON.parse(hashes);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [url, combined] of [[article, false], [bundle, true]]) {
        const page = await browser.newPage({viewport: {width: 1000, height: 800}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        page.on('requestfailed', request => errors.push(request.url()));
        page.on('console', message => {if (message.type() === 'warning') errors.push(message.text());});
        await page.goto(url + (combined ? '#lwp/a/a.html/detail' : '#detail'));
        const settle = async () => {
          await page.evaluate(() => document.fonts.ready);
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        };
        const snapshot = slug => page.locator('#' + slug).evaluate(slide => {
          const result = [];
          for (const host of slide.querySelectorAll('.lwp-graphic-host')) {
            for (const layer of host.shadowRoot.querySelectorAll('.layer')) {
              const graphic = layer.querySelector('.graphic'), payload = graphic.querySelector('.rotor > span');
              const b = graphic.getBoundingClientRect(), s = slide.getBoundingClientRect();
              result.push({id: layer.dataset.layer, text: payload.shadowRoot.querySelector('span').textContent,
                visible: graphic.style.visibility, colour: getComputedStyle(payload).color,
                width: b.width, rightGap: s.right - b.right,
                images: [...layer.querySelectorAll('.graphic')].flatMap(node => {
                  const image = node.querySelector('.rotor > span').shadowRoot.querySelector('img');
                  if (!image) return [];
                  const box = image.getBoundingClientRect();
                  return [{src: image.src, width: box.width, height: box.height, naturalWidth: image.naturalWidth}];
                })});
            }
          }
          return result;
        });
        const check = async (slug, expected) => {
          await page.waitForFunction(({slug, count}) => {
            const hosts = [...document.getElementById(slug).querySelectorAll('.lwp-graphic-host')];
            const layers = hosts.flatMap(host => [...host.shadowRoot.querySelectorAll('.layer')]);
            const graphics = hosts.flatMap(host => [...host.shadowRoot.querySelectorAll('.graphic')]);
            return layers.length === count && graphics.every(node => node.style.visibility === 'visible');
          }, {slug, count: expected.length}, {timeout: 5000});
          await settle();
          const result = await snapshot(slug);
          assert.deepEqual(result.map(item => [item.id, item.text]), expected, `${name}: ${slug} plan and asset ownership`);
          for (const item of result) if (item.id === 'frame') {
            assert.ok(Math.abs(item.width - 80) < 1.5 && Math.abs(item.rightGap - 20) < 1.5,
              `${name}: kit geometry remains independent: ${JSON.stringify(item)}`);
            assert.equal(item.images.length, 1, 'the selected identity owns one picture');
            const image = item.images[0], expectedHash = imageHashes[item.text];
            assert.ok(image.naturalWidth === 80 && image.width > 0 && Math.abs(image.width / image.height - 2) < .025,
              `${name}: actual alternative media loads without distortion`);
            if (image.src.startsWith('data:')) {
              assert.equal(createHash('sha256').update(Buffer.from(image.src.split(',')[1], 'base64')).digest('hex').slice(0, 24), expectedHash);
            } else assert.ok(image.src.includes(expectedHash + '.svg'), `${name}: copied image belongs to the selected kit`);
          }
          return result;
        };
        const choose = async selector => {
          await page.keyboard.press('c'); await page.locator('#themeMenu.open').waitFor();
          const identity = selector === 'builtin/standard' ? 'builtin' : selector.split('/')[0];
          await page.locator(`#identityOptions [data-identity="${identity}"]`).click();
          await page.locator(`#presentationOptions [data-presentation="${selector}"]`).click();
          await page.keyboard.press('Escape'); await settle();
        };
        await check('detail', []);
        await choose('red@1.0.0/decorated');
        const initial = await check('detail', [['frame', 'RED']]);
        assert.equal(await page.locator('#cover .lwp-graphic-host').count(), 0, 'preset type exception');
        assert.equal(await page.locator('#disabled .lwp-graphic-host').count(), 0, 'slide-local [] overrides every kit');
        await page.keyboard.press('c'); await page.locator('#themeMenu.open').waitFor();
        await page.locator('[data-theme="monochrome-night"]').click();
        await page.keyboard.press('Escape');
        const dark = await check('detail', [['frame', 'RED']]);
        assert.notEqual(dark[0].colour, initial[0].colour, 'palette changes style, not resource selection');
        await choose('red@1.0.0/plain'); await check('detail', []);
        await choose('blue@1.0.0/decorated'); await check('detail', [['frame', 'BLUE']]);
        await choose('builtin/standard'); await check('detail', []);
        await choose('red@1.0.0/decorated'); await check('detail', [['frame', 'RED']]);
        await page.setViewportSize({width: 390, height: 844}); await check('detail', [['frame', 'RED']]);
        await page.keyboard.press('d'); await page.locator('#readingMenu.open').waitFor();
        for (let i = 0; i < 5; i++) await page.locator('[data-menu-action="zoom-in"]').click();
        await page.keyboard.press('Escape'); await check('detail', [['frame', 'RED']]);
        await page.keyboard.press('f'); await page.waitForFunction(() => !!document.fullscreenElement, null, {timeout: 5000});
        await check('detail', [['frame', 'RED']]);
        await page.keyboard.press('f'); await page.waitForFunction(() => !document.fullscreenElement, null, {timeout: 5000});
        await page.locator('#detail').scrollIntoViewIfNeeded();
        await check('detail', [['frame', 'RED']]);
        await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
        await page.emulateMedia({media: 'print'});
        await check('detail', [['frame', 'RED']]);
        await page.emulateMedia({media: 'screen'});
        await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
        await page.locator('#detail').scrollIntoViewIfNeeded();
        await check('detail', [['frame', 'RED']]);
        await choose('blue@1.0.0/decorated');
        if (combined) {
          await page.evaluate(() => {location.hash = '#lwp/a/b.html/author-card';});
        } else await page.goto(authorArticle + '#author-card');
        await page.locator('#author-card').waitFor(); await settle();
        await check('author-card', [['frame', 'BLUE'], ['author', 'AUTHOR']]);
        await choose('red@1.0.0/plain'); await check('author-card', [['author', 'AUTHOR']]);
        await choose('red@1.0.0/decorated'); await check('author-card', [['frame', 'RED'], ['author', 'AUTHOR']]);
        await choose('builtin/standard'); await check('author-card', [['author', 'AUTHOR']]);
        assert.deepEqual(errors, [], `${name}: no missing alternative payload or browser error`);
        await page.close();
      }
      console.log(`${name}: kit graphic layers passed`);
    } finally {await browser.close();}
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
