const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable'); process.exit(77); }

(async () => {
  const [indexURL, bundleURL, namesText] = process.argv.slice(2);
  const names = JSON.parse(namesText);
  for (const [engineName, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    let browser;
    try { browser = await engine.launch({timeout: 15000}); }
    catch (error) {
      if (/executable doesn't exist/i.test(String(error))) {
        console.error(engineName + ' unavailable'); process.exitCode = 77; return;
      }
      throw error;
    }
    try {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      for (const [url, combined] of [[indexURL, false], [bundleURL, true]]) {
        for (const [index, name] of names.entries()) {
          await page.goto(url);
          await page.locator('.article-card').nth(index).click();
          await page.waitForFunction(title => document.title === title, 'Page ' + index,
            {timeout: 5000});
          assert.equal(await page.locator('.slide-cover h1').textContent(), 'Page ' + index);
          if (combined) {
            assert.equal(new URL(page.url()).pathname, new URL(bundleURL).pathname);
            assert.equal(decodeURIComponent(new URL(page.url()).hash.split('/')[2]), name);
          } else {
            const expected = new URL(encodeURIComponent(name), indexURL);
            assert.equal(decodeURIComponent(new URL(page.url()).pathname),
              decodeURIComponent(expected.pathname));
          }
          // Generated inter-article links exercise the same boundary as cards.
          const target = (index + 1) % names.length;
          const links = page.locator('.series-link');
          const targetPosition = target > index ? target - 1 : target;
          await links.nth(targetPosition).click();
          await page.waitForFunction(title => document.title === title, 'Page ' + target,
            {timeout: 5000});
        }
      }
      assert.deepEqual(errors, []);
      await page.close();
      console.log(engineName + ': output links preserve filename identities');
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
