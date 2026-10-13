// Real Display settings on an ordinary Markdown image, in both browser engines.
const assert = require('node:assert/strict');
let chromium, firefox;
try { ({ chromium, firefox } = require('playwright')); }
catch (error) { console.error('Playwright is unavailable in the supplied environment'); process.exit(77); }

(async () => {
  const url = process.argv[2];
  if (!url) throw Error('usage: image_reading_browser.cjs <built-page-URL>');
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    let browser;
    try { browser = await engine.launch({ timeout: 15000 }); }
    catch (error) {
      if (/executable doesn't exist/i.test(String(error))) {
        console.error(name + ' is unavailable in the supplied environment');
        process.exitCode = 77;
        return;
      }
      throw error;
    }
    try {
      const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto(url);
      await page.locator('#image figure img').evaluate(image => image.decode());
      await page.locator('#medium figure img').evaluate(image => image.decode());
      await page.locator('#giant figure img').evaluate(image => image.decode());
      const geometry = () => page.locator('#image figure img').evaluate(image => ({
        width: image.getBoundingClientRect().width,
        height: image.getBoundingClientRect().height,
        style: image.getAttribute('style'),
      }));
      const slideHeight = id => page.locator('#' + id).evaluate(slide => ({
        rendered: slide.getBoundingClientRect().height,
        scroll: slide.scrollHeight,
        viewport: window.innerHeight,
      }));
      const near = (actual, expected, message) => {
        assert.ok(Math.abs(actual - expected) < 2,
          `${name} ${message}: ${actual} instead of ${expected}`);
      };
      const settle = () => page.evaluate(() => new Promise(resolve =>
        requestAnimationFrame(() => requestAnimationFrame(resolve))));
      await page.keyboard.press('d');
      await page.waitForSelector('#readingMenu.open');
      await page.locator('[data-reading-option="object_shrink_horizontal"]').uncheck();
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      const baseline = await geometry();
      assert.ok(baseline.height > 700, `${name}: image does not exceed viewport`);
      for (const [button, times, factor] of [
        ['zoom-out', 5, .5], ['zoom-in', 15, 2], ['zoom-reset', 1, 1],
      ]) {
        for (let i = 0; i < times; i++) {
          await page.locator(`#readingMenu [data-menu-action="${button}"]`).click();
        }
        await settle();
        const image = await geometry();
        near(image.width, baseline.width * factor, `${button} width`);
        near(image.height, baseline.height * factor, `${button} height`);
        if (factor === 1) assert.deepEqual(image, baseline, `${name}: reset restores authored markup`);
      }
      await page.locator('[data-reading-option="object_shrink_vertical"]').check();
      await settle();
      const fitted = await geometry();
      assert.ok(fitted.height < baseline.height * .5,
        `${name}: tall image needs a factor below the former 0.5 minimum: ${JSON.stringify({baseline, fitted})}`);
      const tallSlide = await slideHeight('image');
      assert.ok(tallSlide.rendered <= tallSlide.viewport + 1
        && tallSlide.scroll <= tallSlide.viewport + 1,
      `${name}: tall image and slide must fit with title and padding: ${JSON.stringify(tallSlide)}`);
      await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
      assert.deepEqual(await geometry(), baseline, `${name}: print restores authored image`);
      await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
      await settle();
      near((await geometry()).height, fitted.height, `${name}: return from print`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      assert.deepEqual(await geometry(), baseline, `${name}: disabled fit restores source`);

      const mediumBaseline = await page.locator('#medium figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      const mixedImageStyles = await page.locator('#mixed-image-table img').evaluateAll(images =>
        images.map(image => image.getAttribute('style')));
      const mixedBaseline = await slideHeight('mixed-table');
      const tableTextSize = await page.locator('#mixed-image-table td').first().evaluate(cell =>
        getComputedStyle(cell).fontSize);
      assert.ok(mixedBaseline.rendered > 700, `${name}: the mixed-orientation table must overflow before fitting`);
      const captionBaseline = await page.locator('#medium figcaption').evaluate(caption =>
        caption.getBoundingClientRect().height);
      const giantBaseline = await page.locator('#giant figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      assert.equal(await page.locator('#medium .slide-chrome-header').count(), 1,
        `${name}: the header is actually rendered in the slide`);
      assert.equal(await page.locator('#medium .slide-chrome-footer').count(), 1,
        `${name}: the footer is actually rendered in the slide`);
      assert.ok(mediumBaseline < 700 && (await slideHeight('medium')).rendered > 700,
        `${name}: medium image alone fits but its title/summary/footer do not`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').check();
      await settle();
      const mediumFit = await slideHeight('medium');
      assert.ok(mediumFit.rendered <= mediumFit.viewport + 1
        && mediumFit.scroll <= mediumFit.viewport + 1,
      `${name}: medium image must leave room for header, title, summary and footer: ${JSON.stringify(mediumFit)}`);
      near(await page.locator('#medium figcaption').evaluate(caption =>
        caption.getBoundingClientRect().height), captionBaseline, 'image fitting keeps caption readable');
      const mixedFit = await slideHeight('mixed-table');
      const fittedImages = await page.locator('#mixed-image-table img').evaluateAll(images =>
        images.map(image => ({width: image.getBoundingClientRect().width,
          height: image.getBoundingClientRect().height})));
      assert.ok(mixedFit.rendered <= mixedFit.viewport + 1
        && mixedFit.scroll <= mixedFit.viewport + 1
        && fittedImages[1].height > fittedImages[0].height
        && Math.abs(fittedImages[0].width / fittedImages[0].height - 3840 / 2160) < .03
        && Math.abs(fittedImages[1].width / fittedImages[1].height - 900 / 1600) < .03,
      `${name}: portrait and landscape inside a table must fit the whole slide: `
        + JSON.stringify({mixedFit, fittedImages}));
      near(await page.locator('#mixed-image-table td').first().evaluate(cell =>
        parseFloat(getComputedStyle(cell).fontSize)), parseFloat(tableTextSize),
      'image fitting leaves table text unchanged');
      await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
      assert.deepEqual(await page.locator('#mixed-image-table img').evaluateAll(images =>
        images.map(image => image.getAttribute('style'))), mixedImageStyles,
      `${name}: print restores authored dimensions in the table`);
      await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
      await settle();
      const returnedMixed = await slideHeight('mixed-table');
      assert.ok(returnedMixed.rendered <= returnedMixed.viewport + 1
        && returnedMixed.scroll <= returnedMixed.viewport + 1,
      `${name}: the fitted table images return after print: ${JSON.stringify(returnedMixed)}`);
      await page.setViewportSize({width: 1280, height: 720});
      await settle();
      const wideMixed = await slideHeight('mixed-table');
      assert.ok(wideMixed.rendered <= wideMixed.viewport + 1
        && wideMixed.scroll <= wideMixed.viewport + 1,
      `${name}: mixed table images also fit a wider viewport: ${JSON.stringify(wideMixed)}`);
      await page.setViewportSize({width: 900, height: 700});
      await settle();
      const chromeFit = await slideHeight('chrome-tall');
      const chromeVisible = await page.locator('#chrome-tall').evaluate(slide => {
        const origin = slide.getBoundingClientRect().top;
        return ['.slide-chrome-header', 'h2', '.summary', 'figure', '.slide-chrome-footer']
          .map(selector => {
            const rect = slide.querySelector(selector).getBoundingClientRect();
            return {selector, top: rect.top - origin, bottom: rect.bottom - origin};
          });
      });
      assert.ok(chromeFit.rendered <= chromeFit.viewport + 1
        && chromeFit.scroll <= chromeFit.viewport + 1
        && chromeVisible.every(rect => rect.top >= -1 && rect.bottom <= chromeFit.viewport + 1),
      `${name}: large image, title, header, summary, caption and footer must all remain visible: `
        + JSON.stringify({chromeFit, chromeVisible}));
      const chromeImageAt100 = await page.locator('#chrome-tall figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      const titleSizeAt100 = await page.locator('#chrome-tall h2').evaluate(title =>
        parseFloat(getComputedStyle(title).fontSize));
      const chromeLogosAt100 = await page.locator('#chrome-tall .slide-chrome-header img').evaluateAll(images =>
        images.map(image => image.getBoundingClientRect().height));
      for (let i = 0; i < 5; i++) {
        await page.locator('#readingMenu [data-menu-action="zoom-in"]').click();
      }
      await settle();
      const zoomedChrome = await slideHeight('chrome-tall');
      const zoomedImage = await page.locator('#chrome-tall figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      near(await page.locator('#chrome-tall h2').evaluate(title =>
        parseFloat(getComputedStyle(title).fontSize)), titleSizeAt100 * 1.5,
      'capping the image does not cancel the chosen text zoom');
      assert.deepEqual(await page.locator('#chrome-tall .slide-chrome-header img').evaluateAll(images =>
        images.map(image => image.getBoundingClientRect().height)), chromeLogosAt100,
      `${name}: a header logo is chrome, not an image to shrink with the slide`);
      assert.ok(zoomedChrome.rendered <= zoomedChrome.viewport + 1
        && zoomedChrome.scroll <= zoomedChrome.viewport + 1
        && zoomedImage > 0 && zoomedImage < chromeImageAt100 * 1.5 - 2,
      `${name}: at 150% the image stops growing before pushing title/header/footer out: `
        + JSON.stringify({zoomedChrome, zoomedImage, chromeImageAt100}));
      const zoomedMixed = await slideHeight('mixed-table');
      assert.ok(zoomedMixed.rendered <= zoomedMixed.viewport + 1
        && zoomedMixed.scroll <= zoomedMixed.viewport + 1,
      `${name}: zoomed landscape/portrait table images leave room for the slide: ${JSON.stringify(zoomedMixed)}`);
      await page.locator('#readingMenu [data-menu-action="zoom-reset"]').click();
      await settle();
      await page.locator('[data-reading-option="object_shrink_vertical"]').uncheck();
      await settle();
      near((await slideHeight('mixed-table')).rendered, mixedBaseline.rendered,
        'disabling height fit restores the original table geometry');
      assert.deepEqual(await page.locator('#mixed-image-table img').evaluateAll(images =>
        images.map(image => image.getAttribute('style'))), mixedImageStyles,
      `${name}: disabling fit restores the authored table image styles`);
      await page.locator('[data-reading-option="object_shrink_vertical"]').check();
      await settle();
      const giantFit = await page.locator('#giant figure img').evaluate(image =>
        image.getBoundingClientRect().height);
      assert.ok(giantFit / giantBaseline < .1 && (await slideHeight('giant')).rendered <= 701,
        `${name}: vertical fit must work below 10%: ${JSON.stringify({giantBaseline, giantFit})}`);
      const impossible = await slideHeight('impossible');
      assert.ok(impossible.rendered > impossible.viewport
        && await page.locator('#impossible').getAttribute('data-lwp-fit-overflow') === 'true',
      `${name}: prose too long without image must still scroll`);
      assert.ok(await page.locator('#impossible figure img').evaluate(image =>
        image.getBoundingClientRect().height) > 500,
      `${name}: do not hide an image when reducing it cannot make the text fit`);

      await page.keyboard.press('Escape');
      await page.keyboard.press('Escape');
      await page.locator('#image figure img').click();
      await page.waitForFunction(() => Math.abs(document.getElementById('medium').getBoundingClientRect().top) < 2,
        null, {timeout: 5000});
      await page.locator('#medium figure img').evaluate(image => {
        const link = document.createElement('a');
        link.href = '#image';
        link.addEventListener('click', event => {
          event.preventDefault();
          window.linkedImageClicks = (window.linkedImageClicks || 0) + 1;
        });
        image.replaceWith(link);
        link.appendChild(image);
      });
      await page.locator('#medium figure img').click();
      assert.equal(await page.evaluate(() => window.linkedImageClicks), 1,
        `${name}: linked images retain their own click action`);
      assert.ok(Math.abs(await page.locator('#medium').evaluate(slide => slide.getBoundingClientRect().top)) < 2,
        `${name}: clicking a linked image does not advance the deck`);
      await page.locator('#giant').evaluate(slide => slide.scrollIntoView({behavior: 'instant'}));
      await page.locator('#giant figure').evaluate(figure => {
        figure.onclick = () => { window.authoredImageClicks = (window.authoredImageClicks || 0) + 1; };
      });
      await page.locator('#giant figure img').click();
      assert.equal(await page.evaluate(() => window.authoredImageClicks), 1,
        `${name}: an authored figure click handler retains its own action`);
      assert.ok(Math.abs(await page.locator('#giant').evaluate(slide => slide.getBoundingClientRect().top)) < 2,
        `${name}: an authored figure action must not advance the deck`);
      assert.deepEqual(errors, [], `${name}: browser errors`);
      await page.close();

      const touch = await browser.newPage({viewport: {width: 900, height: 700}, hasTouch: true});
      await touch.goto(url);
      await touch.locator('#image figure img').evaluate(image => image.decode());
      const box = await touch.locator('#image figure img').boundingBox();
      await touch.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2);
      assert.ok(Math.abs(await touch.locator('#image').evaluate(slide => slide.getBoundingClientRect().top)) < 2,
        `${name}: native touch on an image must not become a mouse navigation click`);
      await touch.close();

      // A 16:9 photo nested inside a fact box resembles a real landscape
      // article. Its intrinsic ratio must not make the wide viewport spill.
      for (const [width, height, dpr] of [[1096, 1214, 1], [1800, 1214, 1], [1800, 1214, 2]]) {
        const ratioPage = await browser.newPage({viewport: {width, height}, deviceScaleFactor: dpr});
        try {
          await ratioPage.goto(url + '#ratio');
          await ratioPage.locator('#ratio .figure img').evaluate(image => image.decode());
          await ratioPage.evaluate(() => new Promise(resolve =>
            requestAnimationFrame(() => requestAnimationFrame(resolve))));
          const geometry = () => ratioPage.locator('#ratio').evaluate(slide => {
            const origin = slide.getBoundingClientRect().top;
            const image = slide.querySelector('.figure img');
            return {viewport: document.documentElement.clientHeight,
              slide: slide.getBoundingClientRect().height, scroll: slide.scrollHeight,
              naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight,
              elements: ['.slide-chrome-header', 'h2', '.summary', '.fact-box',
                '.figure img', '.slide-chrome-footer'].map(selector => {
                const rect = slide.querySelector(selector).getBoundingClientRect();
                return {selector, top: rect.top - origin, bottom: rect.bottom - origin};
              })};
          });
          await ratioPage.keyboard.press('d');
          await ratioPage.waitForSelector('#readingMenu.open');
          for (const zoom of [1, .8, 1.5]) {
            await ratioPage.locator('#readingMenu [data-menu-action="zoom-reset"]').click();
            for (let n = 0; n < Math.round(Math.abs(zoom - 1) * 10); n++) {
              await ratioPage.locator(`#readingMenu [data-menu-action="zoom-${zoom < 1 ? 'out' : 'in'}"]`).click();
            }
            await ratioPage.evaluate(() => new Promise(resolve =>
              requestAnimationFrame(() => requestAnimationFrame(resolve))));
            const actual = await geometry();
            assert.equal(actual.naturalWidth, 3840, `${name}: real 16:9 image width`);
            assert.equal(actual.naturalHeight, 2160, `${name}: real 16:9 image height`);
            assert.ok(actual.slide <= actual.viewport + 1 && actual.scroll <= actual.viewport + 1
              && actual.elements.every(rect => rect.top >= -1 && rect.bottom <= actual.viewport + 1),
            `${name} ${width}x${height} @${dpr} zoom ${zoom}: entire fact-box slide must fit: `
              + JSON.stringify(actual));
          }
          await ratioPage.keyboard.press('Escape');
          await ratioPage.keyboard.press('Escape');
          await ratioPage.locator('#ratio .figure img').click();
          await ratioPage.waitForFunction(() => Math.abs(document.getElementById('mixed-table').getBoundingClientRect().top) < 2,
            null, {timeout: 5000});
        } finally { await ratioPage.close(); }
      }
      console.log(`${name}: responsive image controls passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
