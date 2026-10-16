const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable'); process.exit(77); }

(async () => {
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    let browser;
    try { browser = await engine.launch({timeout: 15000}); }
    catch (error) {
      if (/executable doesn't exist/i.test(String(error))) {
        console.error(name + ' unavailable'); process.exitCode = 77; return;
      }
      throw error;
    }
    try {
      for (const url of process.argv.slice(2)) {
        const page = await browser.newPage({viewport: {width: 1280, height: 720}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url);
        await page.evaluate(() => document.fonts.ready);
        await page.keyboard.press('m');
        await page.locator('#presenterMenu.open').waitFor();
        await page.locator('#menuFullscreen').focus();
        for (const [width, height] of [[1280, 720], [390, 844], [320, 700],
          [3840, 2160], [1920, 1080], [1280, 720], [390, 844]]) {
          await page.setViewportSize({width, height});
          const actual = await page.locator('#presenterMenu').evaluate(menu => {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            return {lang: document.documentElement.lang,
              columns: getComputedStyle(menu.querySelector('.presenter-menu-row')).gridTemplateColumns.split(' ').length,
              focused: document.activeElement.id,
              labels: [...menu.querySelectorAll('.presenter-menu-label')].map(label => {
                const rect = label.getBoundingClientRect();
                const style = getComputedStyle(label);
                context.font = style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily;
                const longest = Math.max(...label.textContent.trim().split(/\s+/).map(word => context.measureText(word).width));
                return {text: label.textContent.trim(), width: rect.width, height: rect.height,
                  font: style.fontSize, longest, button: label.parentElement.getBoundingClientRect().height};
              }).filter(label => label.height > 0)};
          });
          assert.equal(actual.focused, 'menuFullscreen', name + ': resizing preserves keyboard focus');
          assert.ok(actual.labels.length > 10 && actual.labels.every(label =>
            label.width >= label.longest - 1),
          name + ' ' + width + 'x' + height + ': do not chop fitting words into single letters: ' + JSON.stringify(actual));
          if (width === 1280) assert.equal(actual.columns, 3, 'ordinary desktop keeps its three columns');
          if (width <= 390 || width === 3840) assert.equal(actual.columns, 1,
            'narrow cards and enlarged 4K type use one readable column');
        }
        await page.keyboard.press('ArrowDown');
        assert.notEqual(await page.evaluate(() => document.activeElement.id), 'menuFullscreen');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#presenterMenu.open').count(), 0);
        assert.deepEqual(errors, []);
        await page.close();
      }
      console.log(name + ': responsive presenter menu checks passed');
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
