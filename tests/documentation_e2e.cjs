const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let chromium;
try { ({ chromium } = require('playwright')); }
catch (error) { console.error(error.message); process.exit(77); }

(async () => {
  const temporary = path.resolve(__dirname, '../work/tmp');
  fs.mkdirSync(temporary, { recursive: true });
  const screenshots = fs.mkdtempSync(path.join(temporary, 'documentation-'));
  console.log(`Documentation screenshots: ${screenshots}`);
  const browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
    ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
  try {
    for (const width of [390, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 844 },
        isMobile: width === 390, hasTouch: width === 390, deviceScaleFactor: 1 });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      page.on('requestfailed', request => errors.push(request.url()));
      page.on('console', message => {
        if (message.type() === 'error') errors.push(message.text());
      });
      const guide = path.resolve(process.env.LWP_DOCUMENTATION_GUIDE ||
        path.join(__dirname, '../generated/guide/guide.html'));
      const url = pathToFileURL(guide).href;
      const chapters = [
        '1-create-content', '2-organize-a-documentary-collection',
        '3-design-and-compose-identities', '4-read-present-and-share',
        '5-publish-and-maintain', '6-integrate-and-automate',
      ];
      async function visibleTarget(id) {
        // Wait beyond a normal slide glide: applyHash must not pull us back.
        await page.waitForTimeout(500);
        const element = page.locator(`[id="${id}"]`);
        // The long manual's frame can settle by a few pixels after load.
        // Its title, not the enclosing border, is the useful entry landmark.
        const landmark = id === 'guide-complet' ? element.locator('h1').first() : element;
        const bounds = await landmark.boundingBox();
        const topLimit = id === 'guide-complet' ? 422 : 200;
        assert(bounds && bounds.y >= -1 && bounds.y < topLimit &&
          bounds.y + bounds.height <= 844,
          `${id} not in view at ${width}: ${bounds && bounds.y}`);
        assert.equal(await element.evaluate(node => node === document.activeElement),
          true, `${id} must receive keyboard focus at ${width}`);
        assert.equal(await page.evaluate(() =>
          document.documentElement.scrollWidth > innerWidth), false,
        `horizontal overflow at ${width}: ${id}`);
      }
      async function capture(name) {
        await page.screenshot({ path: path.join(screenshots, `${width}-${name}.png`) });
      }
      try {
        // An external link with a malformed escape is not a script error.
        await page.goto(`${url}#%`, { waitUntil: 'load' });
        await page.evaluate(() => { location.hash = '%E0%A4%A'; });
        await page.waitForTimeout(100);
        assert.deepEqual(errors, [], `malformed fragment at ${width}`);

        // The manual is an entry point, not a reward for traversing every card.
        await page.goto(`${url}#guide-complet`, { waitUntil: 'load' });
        await page.evaluate(() => document.fonts.ready);
        await visibleTarget('guide-complet');
        await capture('manual-entry');

        await page.goto(url, { waitUntil: 'load' });
        await page.evaluate(() => document.fonts.ready);
        const coverLink = page.locator('.slide-cover a[href="#guide-complet"]');
        assert.equal(await coverLink.count(), 1);
        assert.equal(await coverLink.evaluate(link => getComputedStyle(link).color ===
          getComputedStyle(link.parentElement).color), true,
        'the cover link must not use browser-default blue on the dark cover');
        const coverBounds = await coverLink.boundingBox();
        assert(coverBounds && coverBounds.y >= 0 && coverBounds.y + coverBounds.height <= 844,
          `manual link must be immediately visible at ${width}`);
        await capture('cover');
        await coverLink.focus();
        await page.keyboard.press('Enter');
        await visibleTarget('guide-complet');

        const targets = await page.locator('.full-article a[href^="#"]').evaluateAll(links =>
          [...new Set(links.map(link => link.getAttribute('href').slice(1)).filter(id => {
            const element = document.getElementById(id);
            return element && element.matches('h2, h3');
          }))]);
        assert.deepEqual(targets.filter(id => /^\d+-/.test(id)).sort(), chapters);
        const subsections = targets.filter(id => !/^\d+-/.test(id));
        assert(subsections.length > 0, 'the guide must exercise subsection links');
        for (const id of targets) {
          const link = page.locator(`.full-article a[href="#${id}"]`).first();
          await link.scrollIntoViewIfNeeded();
          await link.focus();
          await page.keyboard.press('Enter');
          await visibleTarget(id);
          if (chapters.includes(id)) await capture(id);
        }
        // Route references on cards use the same inner-article navigation.
        for (const id of chapters) {
          const link = page.locator(`.source a[href="#${id}"]`);
          assert.equal(await link.count(), 1, `missing deck route: ${id}`);
          await link.scrollIntoViewIfNeeded();
          await link.click();
          await visibleTarget(id);
        }
        for (const id of [chapters[2], subsections[0]]) {
          await page.goto('about:blank');
          await page.goto(`${url}#${id}`, { waitUntil: 'load' });
          await page.evaluate(() => document.fonts.ready);
          await visibleTarget(id);
        }
        await page.goto(`${url}#${chapters[4]}`, { waitUntil: 'load' });
        await visibleTarget(chapters[4]);
        for (const name of ['product-responsive', 'appearance-choices', 'identity-composition']) {
          const image = page.locator(`.full-article img[src="img/${name}.png"]`);
          assert.equal(await image.count(), 1);
          await image.scrollIntoViewIfNeeded();
          const bounds = await image.boundingBox();
          assert(bounds && bounds.width > 100 && bounds.height > 50 &&
            bounds.x >= -1 && bounds.x + bounds.width <= width + 1,
          `${name} must be readable and fit at ${width}: ${JSON.stringify(bounds)}`);
          await capture(name);
        }
        assert.deepEqual(await page.evaluate(() => [...document.images]
          .filter(image => !image.complete || !image.naturalWidth).map(image => image.src)), []);
        assert.deepEqual(errors, []);
      } catch (error) {
        await capture('failure');
        throw error;
      } finally { await page.close(); }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
