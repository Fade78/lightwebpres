// Mouse screen steps use the deck's timed glide, and reverse entry lands at
// the bottom of a tall previous slide, without changing keyboard navigation.
const assert = require('node:assert/strict');
const {chromium, firefox} = require('playwright');

(async () => {
  const [articleURL, combinedURL] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [url, combined] of [[articleURL, false], [combinedURL, true]]) {
        const page = await browser.newPage({viewport: {width: 900, height: 700}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url + (combined ? '#lwp/a/a.html/after' : '#after'));
        // The initial hash can start a real slide glide. Wait for that route
        // to land instead of racing it with a synthetic scrollIntoView.
        try {
          await page.waitForFunction(() => {
            const after = document.getElementById('after');
            return after && Math.abs(after.getBoundingClientRect().top) < 2;
          }, null, {timeout: 5000});
        } catch (error) {
          throw new Error(`${name} ${combined ? 'combined' : 'article'} initial route failed: `
            + JSON.stringify(await page.evaluate(() => ({
              hash: location.hash, scrollY, viewport: innerHeight,
              tall: document.getElementById('tall')?.getBoundingClientRect().toJSON(),
              after: document.getElementById('after')?.getBoundingClientRect().toJSON(),
              fitOverflow: document.getElementById('tall')?.dataset.lwpFitOverflow,
            }))), {cause: error});
        }
        const geometry = () => page.evaluate(() => ({
          tallTop: document.getElementById('tall').getBoundingClientRect().top,
          tallBottom: document.getElementById('tall').getBoundingClientRect().bottom,
          afterTop: document.getElementById('after').getBoundingClientRect().top,
          viewport: innerHeight,
          y: scrollY,
        }));
        await page.evaluate(() => {
          window.scrollCalls = [];
          const original = window.scrollTo.bind(window);
          window.scrollTo = function (options) {
            if (options && typeof options === 'object') {
              scrollCalls.push({top: options.top, behavior: options.behavior});
            }
            return original(options);
          };
        });
        const initial = await geometry();
        assert.ok(initial.tallBottom <= 2 && Math.abs(initial.afterTop) < 2,
          `${name}: the next slide begins at its top: ${JSON.stringify(initial)}`);
        await page.mouse.click(18, 400, {button: 'right'});
        await page.waitForFunction(() => Math.abs(
          document.getElementById('tall').getBoundingClientRect().bottom - innerHeight) < 2,
        null, {timeout: 3000});
        const entered = await geometry();
        assert.ok(entered.tallTop < -700, `${name}: enter previous tall slide at its last screen`);

        await page.evaluate(() => { scrollCalls.length = 0; });
        await page.mouse.click(18, 400, {button: 'right'});
        try {
          await page.waitForFunction(bottom =>
            document.getElementById('tall').getBoundingClientRect().bottom > bottom + 100,
          entered.tallBottom, {timeout: 3000});
        } catch (error) {
          throw new Error(`${name} second reverse click did not move: `
            + JSON.stringify({entered, after: await geometry(),
              calls: await page.evaluate(() => scrollCalls)}), {cause: error});
        }
        const previous = await geometry();
        assert.ok(previous.y < entered.y - 100 && entered.y - previous.y <= 700,
          `${name}: reverse click moves one screen up: ${JSON.stringify({entered, previous})}`);
        const calls = await page.evaluate(() => scrollCalls);
        assert.ok(calls.filter(call => call.behavior === 'instant').length >= 2
          && calls.every(call => call.behavior !== 'smooth'),
        `${name}: internal steps use the deck glide, not native smooth scrolling: ${JSON.stringify(calls)}`);

        await page.evaluate(hash => { location.hash = hash; },
          combined ? '#lwp/a/a.html/tall' : '#tall');
        await page.waitForFunction(() => Math.abs(document.getElementById('tall').getBoundingClientRect().top) < 2);
        const shifted = await page.evaluate(() => new Promise(resolve => {
          const next = document.getElementById('after');
          const table = document.getElementById('image-table');
          const before = next.getBoundingClientRect().top + scrollY;
          document.getElementById('navNext').click();
          // Change the preceding slide between animation frames, as image
          // fitting can do when a table image finishes loading.
          requestAnimationFrame(() => {
            table.style.marginBottom = '80px';
            resolve({before, after: next.getBoundingClientRect().top + scrollY});
          });
        }));
        assert.ok(shifted.after > shifted.before + 40,
          `${name}: the preceding slide actually grew during the glide: ${JSON.stringify(shifted)}`);
        await page.waitForFunction(() => Math.abs(document.getElementById('after').getBoundingClientRect().top) < 2,
          null, {timeout: 3000});
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();
      }
      console.log(`${name}: timed mouse reading checks passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
