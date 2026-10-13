// Plain images in a two-column fact table and the slide ground share reading steps.
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
        await page.goto(url + (combined ? '#lwp/a/a.html/tall' : '#tall'));
        await page.locator('#plain-table-image').evaluate(image => image.decode());
        if (combined) assert.equal(await page.locator('#tall').getAttribute('tabindex'), '-1',
          'the deep-linked slide is focusable without making its plain image interactive');
        const settle = () => page.evaluate(() => new Promise(resolve =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const state = () => page.evaluate(() => ({
          scroll: window.scrollY,
          tallTop: document.getElementById('tall').getBoundingClientRect().top,
          afterTop: document.getElementById('after').getBoundingClientRect().top,
        }));
        const top = async () => {
          await page.locator('#tall').evaluate(slide => {
            getSelection().removeAllRanges();
            slide.scrollIntoView({behavior: 'instant'});
          });
          await settle();
        };
        await page.locator('#linked-image').evaluate(link => {
          link.addEventListener('click', event => {
            event.preventDefault();
            window.linkedTableImageClicks = (window.linkedTableImageClicks || 0) + 1;
          });
        });
        for (const mode of ['clip', 'scroll']) {
          if (mode === 'scroll') {
            await page.keyboard.press('d');
            await page.locator('#readingMenu.open').waitFor();
            await page.locator('#menuTableMode').selectOption('scroll');
            await page.keyboard.press('Escape');
            await page.keyboard.press('Escape');
          }
          await top();
          const start = await state();
          assert.ok((await page.locator('#tall').evaluate(slide => slide.getBoundingClientRect().height)) > 1400,
            `${name} ${mode}: fixture must exceed two screens`);
          await page.locator('#plain-table-image').click();
          await settle();
          const image = await state();
          assert.ok(image.scroll > start.scroll + 100 && image.scroll - start.scroll <= 700
            && image.afterTop > 0,
          `${name} ${mode}: plain table image must advance one screen: ${JSON.stringify({start, image})}`);

          await top();
          await page.mouse.click(18, 400);
          await settle();
          const ground = await state();
          assert.ok(ground.scroll > start.scroll + 100 && ground.scroll - start.scroll <= 700
            && ground.afterTop > 0,
          `${name} ${mode}: background must advance one screen: ${JSON.stringify({start, ground})}`);
          await page.mouse.click(18, 400, {button: 'right'});
          await settle();
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: right click goes back one screen`);
          await page.mouse.click(18, 400);
          await settle();
          await page.keyboard.press('r');
          await page.mouse.click(18, 400);
          await settle();
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: R reverses the mouse reading direction`);
          await page.keyboard.press('r');

          await top();
          await page.locator('#linked-image img').click();
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: a linked table image does not change the slide`);
          assert.equal(await page.evaluate(() => window.linkedTableImageClicks), mode === 'clip' ? 1 : 2);
          await page.locator('#plain-table-image').evaluate(image => {
            image.onclick = () => { window.authoredTableClicks = (window.authoredTableClicks || 0) + 1; };
          });
          await page.locator('#plain-table-image').click();
          assert.equal(await page.evaluate(() => window.authoredTableClicks), mode === 'clip' ? 1 : 2);
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: authored image actions remain interactive`);
          await page.locator('#plain-table-image').evaluate(image => { image.onclick = null; });
          await page.locator('#plain-table-image').click({modifiers: ['Control']});
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: modified image clicks do not navigate`);
          const box = await page.locator('#plain-table-image').boundingBox();
          await page.mouse.move(box.x + 10, box.y + 10);
          await page.mouse.down();
          await page.mouse.move(box.x + 45, box.y + 10, {steps: 4});
          await page.mouse.up();
          assert.ok(Math.abs((await state()).scroll - start.scroll) < 2,
            `${name} ${mode}: dragging an image is not a click step`);
        }
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();

        const touch = await browser.newPage({viewport: {width: 900, height: 700},
          hasTouch: true, ...(name === 'chromium' ? {isMobile: true} : {})});
        try {
          await touch.goto(url + (combined ? '#lwp/a/a.html/tall' : '#tall'));
          await touch.locator('#plain-table-image').evaluate(image => image.decode());
          const box = await touch.locator('#plain-table-image').boundingBox();
          const touchBefore = await touch.evaluate(() => window.scrollY);
          await touch.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
          assert.ok(Math.abs(await touch.evaluate(() => window.scrollY) - touchBefore) < 2,
            `${name}: touch on an image retains its native action`);
          await touch.locator('#plain-table-image').click();
          assert.ok(await touch.evaluate(() => window.scrollY) > touchBefore + 100,
            `${name}: a connected mouse owns a later click on the same image`);
        } finally { await touch.close(); }
      }
      console.log(`${name}: bounded mouse reading checks passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
