/* Real mouse, keyboard and emulated touch input. No physical-device claim. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

async function run() {
  let browser;
  const scratch = path.resolve(__dirname, '../work/tmp');
  process.env.TMPDIR = scratch;
  const work = fs.mkdtempSync(path.join(scratch, 'reading-browser-'));
  const executablePath = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
  process.env.XDG_CACHE_HOME = path.join(work, 'cache');
  process.env.XDG_CONFIG_HOME = path.join(work, 'config');
  try {
    browser = await chromium.launch({executablePath});
  } catch (error) {
    if (/Executable doesn't exist/.test(String(error))) {
      console.error('Browser check blocked: existing Chromium unavailable');
      process.exitCode = 77;
      return;
    }
    throw error;
  }
  try {
    for (const [articleURL, otherURL] of [[process.argv[2], process.argv[3]],
      [process.argv[4], process.argv[5]]]) {
      const context = await browser.newContext({viewport: {width: 1100, height: 800}});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      const keyFor = url => 'lwp-reading:' + new URL('.', url).pathname;
      const key = keyFor(articleURL);
      const otherKey = keyFor(otherURL);
      assert.notEqual(key, otherKey);
      const readControls = async () => {
        await page.keyboard.press('m');
        await page.locator('#menuReading').click();
        return page.evaluate(() => ({
          table_mode: document.getElementById('menuTableMode').value,
          text_fit: document.getElementById('menuTextFit').value,
          table_shrink: document.querySelector('[data-reading-option="table_shrink"]').checked,
          object_shrink: document.querySelector('[data-reading-option="object_shrink"]').checked,
          presentationZoom: Number(document.getElementById('menuZoomValue').textContent.replace('%', '')) / 100,
        }));
      };
      const expected = {table_mode: 'scroll', text_fit: 'per-slide',
        table_shrink: true, object_shrink: false, presentationZoom: 1.3};
      const defaults = {table_mode: 'clip', text_fit: 'fixed',
        table_shrink: false, object_shrink: false, presentationZoom: 1};
      const author = {table_mode: 'overflow', text_fit: 'uniform',
        table_shrink: false, object_shrink: true, presentationZoom: 1};
      await page.goto(articleURL);
      assert.deepEqual(await readControls(), defaults);
      assert.equal(await page.evaluate(key => localStorage.getItem(key), key), null,
        'reading author defaults must not create an override');
      await page.locator('#menuTableMode').selectOption(expected.table_mode);
      await page.locator('#menuTextFit').selectOption(expected.text_fit);
      await page.locator('[data-reading-option="table_shrink"]').check();
      for (let i = 0; i < 3; i++) await page.locator('[data-menu-action="zoom-in"]').click();
      assert.deepEqual(await page.evaluate(key => JSON.parse(localStorage.getItem(key)), key),
        {v: 1, ...expected}, 'save exactly the four reader options and zoom, never author floors');
      for (const destination of [null, new URL('next.html', articleURL).href,
        new URL('index.html', articleURL).href]) {
        if (destination) await page.goto(destination);
        else await page.reload();
        await page.waitForFunction(() => document.documentElement.dataset.lwpTableMode === 'scroll');
        assert.equal(await page.evaluate(() =>
          document.documentElement.style.getPropertyValue('--lwp-presentation-zoom')), '1.3');
        assert.deepEqual(await readControls(), expected, 'reload, next article and index share preferences');
      }
      await page.goto(otherURL);
      assert.deepEqual(await readControls(), author, 'another series starts with its author defaults');
      assert.equal(await page.evaluate(key => localStorage.getItem(key), otherKey), null);
      await page.goto(articleURL);
      assert.deepEqual(await readControls(), expected, 'visiting another series must not overwrite this one');

      // The whole versioned record is validated before applying any field.
      await page.goto(otherURL);
      const valid = {v: 1, ...expected};
      const invalid = ['{', 'null', '[]', 'true', '1', '{}',
        ...[{...valid, v: 2}, {...valid, v: '1'}, {...valid, table_mode: 'auto'},
          {...valid, text_fit: 'grow'}, {...valid, table_shrink: 1},
          {...valid, object_shrink: 'false'}, {...valid, presentationZoom: '1.3'},
          {...valid, presentationZoom: 0.49}, {...valid, presentationZoom: 2.01},
          {...valid, presentationZoom: null}, {...valid, min_text_scale: 0.1},
          {...expected}].map(value => JSON.stringify(value)),
        JSON.stringify(valid).replace('1.3', '1e999')];
      for (const raw of invalid) {
        await page.evaluate(({key, raw}) => localStorage.setItem(key, raw), {key: otherKey, raw});
        await page.reload();
        assert.deepEqual(await readControls(), author, `invalid saved override: ${raw}`);
      }
      for (const zoom of [0.5, 2]) {
        await page.evaluate(({key, value}) => localStorage.setItem(key, JSON.stringify(value)),
          {key: otherKey, value: {...valid, presentationZoom: zoom}});
        await page.reload();
        assert.deepEqual(await readControls(), {...expected, presentationZoom: zoom});
        await page.waitForFunction(() => Number(document.querySelector('#long').dataset.lwpTextScale) >= 0.93);
        const payload = await page.locator('#lwp-reading-data').textContent();
        assert.equal(JSON.parse(payload).min_text_scale, 0.93);
        assert.equal(JSON.parse(payload).min_table_scale, 0.94);
        assert.equal(JSON.parse(payload).min_object_scale, 0.95);
      }
      assert.deepEqual(errors, []);
      await context.close();
    }
    const blocked = await browser.newContext();
    await blocked.addInitScript(() => {
      Object.defineProperty(window, 'localStorage', {get() { throw new Error('Storage blocked'); }});
    });
    const blockedPage = await blocked.newPage();
    const blockedErrors = [];
    blockedPage.on('pageerror', error => blockedErrors.push(String(error)));
    await blockedPage.goto(process.argv[2]);
    await blockedPage.keyboard.press('m');
    await blockedPage.locator('#menuReading').click();
    await blockedPage.locator('#menuTableMode').selectOption('scroll');
    await blockedPage.locator('[data-menu-action="zoom-in"]').click();
    assert.equal(await blockedPage.locator('#menuTableMode').inputValue(), 'scroll');
    assert.equal(await blockedPage.locator('#menuZoomValue').textContent(), '110%');
    await blockedPage.reload();
    await blockedPage.keyboard.press('m');
    await blockedPage.locator('#menuReading').click();
    assert.equal(await blockedPage.locator('#menuTableMode').inputValue(), 'clip');
    assert.equal(await blockedPage.locator('#menuZoomValue').textContent(), '100%');
    assert.deepEqual(blockedErrors, []);
    await blocked.close();
    console.log('preferences: HTTP and file directory scopes passed');
    for (const mobile of [true, false]) {
      const width = mobile ? 390 : 768;
      const context = await browser.newContext({
        viewport: { width, height: 844 }, isMobile: mobile, hasTouch: mobile,
        locale: mobile ? 'fr-FR' : 'en-US',
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto(process.argv[2]);
      await page.waitForSelector('.lwp-table-viewport');
      const settle = () => page.waitForTimeout(350);
      const state = () => page.evaluate(() => ({
        hash: location.hash, y: scrollY,
        active: document.querySelector('.nav-dots a.active')?.getAttribute('href'),
        idle: document.documentElement.classList.contains('nav-idle'),
      }));
      const activate = async selector => {
        if (mobile) await page.locator(selector).tap();
        else await page.locator(selector).click();
      };
      const openMainMenu = async () => {
        if (await page.locator('#readingMenu').isVisible()) await page.keyboard.press('Escape');
        if (!await page.locator('#presenterMenu').isVisible()) await page.keyboard.press('m');
        await page.waitForSelector('#presenterMenu.open');
      };
      const openMenu = async () => {
        await openMainMenu();
        await activate('[data-menu-action="reading"]');
        await page.waitForSelector('#readingMenu.open');
      };
      const closeMenu = async () => {
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
      };
      const value = () => page.locator('#menuZoomValue').textContent();
      const zoomIn = '[data-menu-action="zoom-in"]';
      const zoomOut = '[data-menu-action="zoom-out"]';
      const zoomReset = '[data-menu-action="zoom-reset"]';
      await openMenu();
      assert.equal(await page.locator('#readingMenuTitle').textContent(),
        mobile ? 'Affichage' : 'Display settings');
      assert.equal(await page.locator('#presenterMenu .reading-controls').count(), 0);
      assert.equal(await page.locator('#presenterMenu [data-menu-action="reading"]').count(), 1);
      assert.equal(await page.locator('#presenterMenu [data-menu-action^="zoom-"]').count(), 0);
      assert.equal(await page.locator('#readingMenu .reading-controls').count(), 1);
      assert.equal(await page.locator('#presenterMenu').isVisible(), false);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'readingMenuBack');
      await page.keyboard.press('Shift+Tab');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.readingOption), 'object_shrink');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'readingMenuBack');
      await activate('#readingMenuBack');
      assert.equal(await page.locator('#readingMenu').isVisible(), false);
      assert.equal(await page.locator('#presenterMenu').isVisible(), true);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'menuReading');
      await page.keyboard.press('Enter');
      await page.keyboard.press('Escape');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'menuReading');
      await page.keyboard.press('Escape');
      await activate('#navMenu');
      await activate('#menuReading');
      const beforeBackdrop = await state();
      await page.locator('#readingMenu').click({position: {x: 2, y: 2}});
      assert.equal(await page.locator('#readingMenu.open, #presenterMenu.open').count(), 0);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'navMenu');
      assert.equal((await state()).active, beforeBackdrop.active);
      await openMenu();
      assert.equal(await value(), '100%');
      assert.equal(await page.locator('#menuZoomLabel').textContent(),
        mobile ? 'Zoom de pr\u00e9sentation' : 'Presentation zoom');
      const initialZoomButton = await page.locator(zoomIn).boundingBox();
      await activate(zoomIn);
      await activate(zoomIn);
      await activate(zoomIn);
      const repeatedZoomButton = await page.locator(zoomIn).boundingBox();
      assert(Math.abs(initialZoomButton.x - repeatedZoomButton.x) < 1
        && Math.abs(initialZoomButton.y - repeatedZoomButton.y) < 1,
      'repeated zoom taps must keep the button under the finger');
      assert.equal(await value(), '130%');
      assert.equal(await page.locator('#readingMenu.open').count(), 1);
      await page.keyboard.press('-');
      assert.equal(await value(), '120%');
      await page.keyboard.press('Shift+=');
      assert.equal(await value(), '130%');
      await page.keyboard.press('=');
      assert.equal(await value(), '100%');
      for (let i = 0; i < 5; i++) await activate(zoomOut);
      assert.equal(await value(), '50%');
      assert.equal(await page.locator(zoomOut).isDisabled(), true);
      await activate(zoomReset);
      for (let i = 0; i < 10; i++) await activate(zoomIn);
      assert.equal(await value(), '200%');
      assert.equal(await page.locator(zoomIn).isDisabled(), true);
      assert.equal(await page.locator(zoomOut).isDisabled(), false);
      assert(await page.locator('.reading-controls').evaluate(el =>
        el.getBoundingClientRect().right <= innerWidth + 1), 'controls must fit at maximum zoom');
      await activate(zoomReset);
      await activate(zoomIn);
      await page.keyboard.press('Escape');
      await openMenu();
      assert.equal(await value(), '110%');
      // Browser/OS shortcuts must not become deck zoom, including in the menu.
      const modified = await page.evaluate(() => ['Control', 'Meta'].map(modifier => {
        const event = new KeyboardEvent('keydown', { key: '+', bubbles: true,
          cancelable: true, ctrlKey: modifier === 'Control', metaKey: modifier === 'Meta' });
        document.activeElement.dispatchEvent(event);
        return event.defaultPrevented;
      }));
      assert.deepEqual(modified, [false, false]);
      assert.equal(await value(), '110%');
      await activate(zoomReset);
      assert.equal(await page.locator('#menuTableMode').inputValue(), 'clip');
      assert.equal(await page.locator('#menuTextFit').inputValue(), 'fixed');
      for (const expected of ['overflow', 'scroll', 'clip']) {
        await page.keyboard.press('o');
        assert.equal(await page.locator('#menuTableMode').inputValue(), expected);
      }
      for (const expected of ['uniform', 'per-slide', 'fixed']) {
        await page.keyboard.press('a');
        assert.equal(await page.locator('#menuTextFit').inputValue(), expected);
      }
      await page.locator('#menuTableMode').focus();
      await page.keyboard.press('ArrowDown');
      assert.equal(await page.locator('#menuTableMode').inputValue(), 'overflow');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'menuTextFit');
      await page.locator('#menuTableMode').selectOption('scroll');
      await page.locator('#menuTextFit').selectOption('per-slide');
      await activate('[data-reading-option="table_shrink"]');
      assert.equal(await page.locator('[data-reading-option="object_shrink"]').isChecked(), false);
      await activate('[data-reading-option="object_shrink"]');
      await activate('[data-reading-option="table_shrink"]');
      assert.equal(await page.locator('[data-reading-option="object_shrink"]').isChecked(), true);
      await page.keyboard.press('Escape');
      await openMenu();
      assert.equal(await page.locator('#menuTableMode').inputValue(), 'scroll');
      assert.equal(await page.locator('#menuTextFit').inputValue(), 'per-slide');
      assert.equal(await page.locator('[data-reading-option="table_shrink"]').isChecked(), false);
      await page.locator('#menuTextFit').selectOption('fixed');
      await page.keyboard.press('Escape');
      await page.keyboard.press('t');
      assert.equal(await page.locator('#pauseOverlay.open').count(), 1);
      await page.keyboard.press('t');
      await page.keyboard.press('o');
      await openMenu();
      assert.equal(await page.locator('#menuTableMode').inputValue(), 'clip');
      await page.locator('#menuTableMode').selectOption('scroll');
      await closeMenu();
      await page.evaluate(() => document.activeElement.blur());
      await page.keyboard.press('2');
      await page.keyboard.press('Enter');
      await settle();
      const viewport = page.locator('#wide .lwp-table-viewport');
      assert(await viewport.evaluate(el => el.scrollWidth > el.clientWidth + 100),
        'wide table fixture must actually overflow');
      await viewport.focus();
      const tableBefore = await state();
      await page.keyboard.press('ArrowRight');
      await settle();
      assert(await viewport.evaluate(el => el.scrollLeft > 0), JSON.stringify({
        errors, state: await state(), table: await viewport.evaluate(el => ({
          focus: document.activeElement.outerHTML.slice(0, 200),
          mode: document.documentElement.dataset.lwpTableMode,
          overflow: getComputedStyle(el).overflowX, left: el.scrollLeft,
          width: el.clientWidth, content: el.scrollWidth,
        })),
      }));
      await viewport.evaluate(el => { el.scrollLeft = el.scrollWidth; });
      for (const key of ['ArrowRight', 'ArrowDown', 'PageDown', 'End', ' ']) {
        await page.keyboard.press(key);
      }
      await settle();
      assert.equal((await state()).active, tableBefore.active);
      assert(Math.abs((await state()).y - tableBefore.y) < 2,
        JSON.stringify({before: tableBefore, after: await state()}));
      await viewport.hover();
      await page.mouse.wheel(800, 800);
      await settle();
      assert(Math.abs((await state()).y - tableBefore.y) < 2, 'table wheel must not chain');
      await viewport.evaluate(el => { el.scrollLeft = 0; });
      await settle();
      await activate('#wide tbody tr:first-child td:first-child');
      await settle();
      assert.notEqual((await state()).active, tableBefore.active, 'plain table tap advances');
      await page.keyboard.press('2');
      await page.keyboard.press('Enter');
      await settle();
      await viewport.focus();
      if (mobile) {
        const session = await context.newCDPSession(page);
        await viewport.evaluate(el => el.scrollTo({left: 0, behavior: 'instant'}));
        const box = await viewport.boundingBox();
        const y = Math.max(30, box.y + 30);
        await session.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [
          {x: 280, y, id: 1},
        ]});
        for (const x of [240, 200, 160, 120, 80]) {
          await session.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x, y, id: 1}]});
          await page.waitForTimeout(50);
        }
        await session.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
        await settle();
        assert(await viewport.evaluate(el => el.scrollLeft > 0), 'native swipe must scroll the table');
        assert.equal((await state()).active, tableBefore.active);
        assert(Math.abs((await state()).y - tableBefore.y) < 2, 'native table swipe must not move the deck');
        await session.detach();
      }
      // Synthetic touch sequences cover mixed lifetimes, missing starts and
      // cancellation. They test navigation isolation, not native zoom itself.
      const touchResults = await page.evaluate(() => {
        const target = document.querySelector('#wide td');
        const send = (type, points, changed = points, destination = target) => {
          const touches = points.map(([identifier, clientX, clientY]) => new Touch({
            identifier, clientX, clientY, target: destination }));
          const changedTouches = changed.map(([identifier, clientX, clientY]) => new Touch({
            identifier, clientX, clientY, target: destination }));
          const event = new TouchEvent(type, { bubbles: true, cancelable: true,
            touches, targetTouches: touches, changedTouches });
          destination.dispatchEvent(event);
          return event.defaultPrevented;
        };
        const canceled = [];
        canceled.push(send('touchstart', [[1, 300, 200]]));
        canceled.push(send('touchmove', [[1, 80, 200]]));
        canceled.push(send('touchend', [], [[1, 80, 200]]));
        const deck = document.querySelector('#wide h2');
        for (const end of ['touchend', 'touchcancel']) {
          canceled.push(send('touchstart', [[1, 300, 200]], undefined, deck));
          canceled.push(send('touchstart', [[1, 300, 200], [2, 200, 200]], undefined, deck));
          const click = new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1});
          document.getElementById('navNext').dispatchEvent(click);
          if (!click.defaultPrevented) throw new Error('multi-touch must suppress control clicks too');
          canceled.push(send('touchmove', [[1, 70, 200], [2, 330, 200]], undefined, deck));
          canceled.push(send('touchend', [[1, 70, 200]], [[2, 330, 200]], deck));
          canceled.push(send(end, [], [[1, 70, 200]], deck));
          deck.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}));
          deck.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, detail: 2}));
        }
        canceled.push(send('touchmove', [[1, 70, 200], [2, 330, 200]], undefined, deck));
        canceled.push(send('touchcancel', [], [[1, 70, 200], [2, 330, 200]], deck));
        return canceled;
      });
      assert(touchResults.every(result => result === false), 'touch handlers must not cancel native pinch');
      await settle();
      assert.equal((await state()).active, tableBefore.active);
      assert.equal((await state()).idle, tableBefore.idle);
      await page.waitForTimeout(500);
      await page.keyboard.press('Home'); // Still focused in the table: no edge navigation.
      assert.equal((await state()).active, tableBefore.active);
      await page.keyboard.press('3');
      await page.keyboard.press('Enter');
      await settle();
      const ratio = () => page.locator('#long').evaluate(el => {
        const rect = el.getBoundingClientRect();
        return -rect.top / rect.height;
      });
      await page.locator('#long').evaluate(el => {
        const rect = el.getBoundingClientRect();
        scrollTo({top: scrollY + rect.top + rect.height * 0.4, behavior: 'instant'});
      });
      await settle();
      const beforeZoom = await ratio();
      await page.keyboard.press('Shift+=');
      await settle();
      assert(Math.abs(await ratio() - beforeZoom) < 0.015, 'deck zoom must preserve long-article offset');
      await page.keyboard.press('=');
      await settle();
      await page.setViewportSize({width, height: 740});
      await settle();
      assert(Math.abs(await ratio() - beforeZoom) < 0.015, 'height-only resize must preserve reading position');
      if (!mobile) {
        await page.setViewportSize({width: 1100, height: 700});
        await settle();
        await page.locator('#long').evaluate(el => {
          const rect = el.getBoundingClientRect();
          scrollTo({top: scrollY + rect.top + rect.height * 0.4, behavior: 'instant'});
        });
        await settle();
      }
      const beforeWidth = await ratio();
      assert(Math.abs(beforeWidth - 0.4) < 0.015, 'resize fixture must start midway through the article');
      await page.setViewportSize(mobile ? {width: 740, height: 390} : {width: 700, height: 700});
      await settle();
      assert.equal((await state()).active, '#long');
      assert(Math.abs(await ratio() - beforeWidth) < 0.015,
        `width/orientation resize lost the reading position: ${beforeWidth} -> ${await ratio()}`);
      await page.setViewportSize({width, height: 740});
      await settle();
      assert(Math.abs(await ratio() - beforeWidth) < 0.015, 'return orientation must preserve the position too');
      if (mobile) {
        const session = await context.newCDPSession(page);
        const beforeNative = await state();
        await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1.5});
        await settle();
        assert(await page.evaluate(() => visualViewport.scale > 1.4));
        assert.equal((await state()).active, beforeNative.active);
        assert(Math.abs(await ratio() - beforeZoom) < 0.015, 'native scale must not reanchor at section top');
        assert.equal(await page.evaluate(() => document.documentElement.style.zoom), '');
        await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1});
        await session.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [
          {x: width / 2 - 30, y: 300, id: 1}, {x: width / 2 + 30, y: 300, id: 2},
        ]});
        for (const distance of [40, 50, 60, 75, 90]) {
          await session.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [
            {x: width / 2 - distance, y: 300, id: 1},
            {x: width / 2 + distance, y: 300, id: 2},
          ]});
          await page.waitForTimeout(50);
        }
        await session.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
        await settle();
        assert(await page.evaluate(() => visualViewport.scale > 1.2), 'CDP native pinch must zoom');
        assert.equal((await state()).active, beforeNative.active);
        assert.equal(await page.evaluate(() => document.documentElement.style.zoom), '');
        await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1});
        await page.waitForTimeout(500);
        await session.detach();
      }
      // A real generated note link, not a manually inserted anchor.
      await page.keyboard.press('3');
      await page.keyboard.press('Enter');
      await settle();
      const noteLink = page.locator('#long a[href^="#note-"]').first();
      const noteHash = await noteLink.getAttribute('href');
      assert(noteHash, 'fixture must expose a source note link');
      await noteLink.click();
      await settle();
      const note = await page.locator(noteHash).evaluate(el => ({
        top: el.getBoundingClientRect().top,
        sectionTop: el.closest('.slide').getBoundingClientRect().top,
        focus: document.activeElement === el,
      }));
      assert(note.top >= -2 && note.top < 740, JSON.stringify(note));
      assert(note.sectionTop < -1000, 'note navigation must not go to section top');
      assert(note.focus, 'note target should receive focus');
      assert.equal(new URL(page.url()).hash, noteHash);
      await page.reload();
      await settle();
      assert(await page.locator(noteHash).evaluate(el =>
        el.getBoundingClientRect().top >= -2 && el.getBoundingClientRect().top < innerHeight),
      'a note fragment must survive initial layout on reload');
      await page.keyboard.press('h');
      await page.locator('#helpModeToggle').check();
      const helpText = await page.locator('#helpList').innerText();
      assert(helpText.includes(mobile ? 'pincement' : 'Pinching'));
      assert.equal(await page.locator('#helpList > [data-help-variant="keyboard"]:visible').count(), 0,
        'touch help must omit unsupported Home/End/number-jump menu actions');
      await page.keyboard.press('Escape');
      await openMenu();
      assert.equal(await page.locator('[data-reading-option="object_shrink"]').isChecked(), true,
        'reloading a note fragment must preserve the object preference too');
      await page.locator('[data-reading-option="object_shrink"]').uncheck();
      await settle();
      const status = page.locator('#menuReadingStatus');
      assert.equal(await status.getAttribute('aria-live'), 'polite');
      assert.equal(await status.isVisible(), false, 'fixed-size reading must not show an autofit notice');
      await page.locator('#menuTextFit').selectOption('per-slide');
      await settle();
      assert.equal(await page.locator('#long').getAttribute('data-lwp-fit-overflow'), 'true',
        'the real long-form fixture must exceed the fit floor');
      assert.equal(await status.isVisible(), true);
      const filter = async tag => {
        await openMainMenu();
        await page.keyboard.press('l');
        await activate(`#tagMenu [data-tag="${tag}"]`);
        await settle();
        await openMenu();
      };
      await filter('solo');
      const singular = mobile ? '1 slide n\u00e9cessite encore de faire d\u00e9filer.'
        : '1 slide still needs scrolling.';
      const plural = mobile ? '2 slides n\u00e9cessitent encore de faire d\u00e9filer.'
        : '2 slides still need scrolling.';
      assert.equal(await status.textContent(), singular);
      await page.evaluate(() => {
        window.readingStatusMutations = 0;
        const observer = new MutationObserver(records => { window.readingStatusMutations += records.length; });
        observer.observe(document.getElementById('menuReadingStatus'), {
          childList: true, characterData: true, attributes: true, subtree: true,
        });
        window.readingStatusObserver = observer;
      });
      await page.setViewportSize({width, height: 720});
      await settle();
      await page.setViewportSize({width, height: 740});
      await settle();
      assert.equal(await status.textContent(), singular);
      assert.equal(await page.evaluate(() => window.readingStatusMutations), 0,
        'unchanged counts must not churn the live region on resize');
      await page.evaluate(() => window.readingStatusObserver.disconnect());
      await page.locator('#menuTextFit').selectOption('fixed');
      await settle();
      assert.equal(await status.isVisible(), false);
      for (const option of ['table_shrink', 'object_shrink']) {
        await activate(`[data-reading-option="${option}"]`);
        await settle();
        assert.equal(await status.textContent(), singular, `${option} must enable the residual-overflow notice`);
        assert.equal(await status.isVisible(), true);
        await activate(`[data-reading-option="${option}"]`);
        await settle();
        assert.equal(await status.isVisible(), false);
      }
      await page.locator('#menuTextFit').selectOption('uniform');
      await filter('double');
      assert.equal(await page.locator('.slide[data-lwp-fit-overflow="true"]:not([hidden])').count(), 2);
      assert.equal(await status.textContent(), plural);
      // Keep a real residual flag while changing visibility, without a new fit
      // pass clearing it: menu reopening must independently exclude that card.
      await page.keyboard.press('Escape');
      await page.locator('#other-long').evaluate(el => { el.hidden = true; });
      await openMenu();
      assert.equal(await status.textContent(), singular);
      await page.keyboard.press('Escape');
      await page.locator('#other-long').evaluate(el => { el.hidden = false; el.style.display = 'none'; });
      await openMenu();
      assert.equal(await status.textContent(), singular);
      await page.locator('#other-long').evaluate(el => { el.style.removeProperty('display'); });
      await page.locator('#menuTextFit').selectOption('fixed');
      await activate('[data-reading-option="object_shrink"]');
      await filter('brief');
      assert.equal(await page.locator('.slide[data-lwp-fit-overflow="true"]:not([hidden])').count(), 0,
        JSON.stringify(await page.locator('#cover').evaluate(el => ({
          height: el.getBoundingClientRect().height, viewport: innerHeight,
          clientHeight: document.documentElement.clientHeight, scale: el.dataset.lwpTextScale,
          width: el.getBoundingClientRect().width, scrollWidth: el.scrollWidth,
          flagged: Array.from(document.querySelectorAll('.slide[data-lwp-fit-overflow="true"]'),
            slide => ({id: slide.id, hidden: slide.hidden, display: getComputedStyle(slide).display})),
        }))));
      assert.equal(await status.isVisible(), false, 'a fitting selection must clear the notice');
      assert.equal(await status.textContent(), '');
      await filter('solo');
      assert.equal(await status.isVisible(), true);
      assert.equal(await page.locator('.slide #menuReadingStatus').count(), 0);
      await page.emulateMedia({media: 'print'});
      assert.equal(await status.isVisible(), false, 'the menu notice must not appear in print');
      await page.emulateMedia({media: 'screen'});
      await filter('main');
      await closeMenu();
      await page.evaluate(() => document.activeElement.blur());
      await page.keyboard.press('4');
      await page.keyboard.press('Enter');
      await settle();
      assert.equal((await state()).active, '#after');
      await page.setViewportSize(mobile ? {width: 740, height: 390} : {width: 1100, height: 700});
      await settle();
      assert.equal((await state()).active, '#after', 'ordinary cards must remain current after preceding text reflows');
      assert(await page.locator('#after').evaluate(el => Math.abs(el.getBoundingClientRect().top) < 2),
        'ordinary presentation cards must still anchor at the top');
      // Foreground chrome shares a coordinate system at every deck zoom.
      // Measure text runs as well as panel boxes: an in-bounds dialog can
      // still clip its labels inside an overflowing grid.
      const checkForeground = async selector => {
        const panel = page.locator(selector);
        await panel.waitFor({state: 'visible'});
        const measured = await panel.evaluate(root => {
          const issues = [];
          const box = root.getBoundingClientRect();
          if (box.left < -1 || box.right > innerWidth + 1
              || box.top < -1 || box.bottom > innerHeight + 1) {
            issues.push({panel: root.id, left: box.left, right: box.right, top: box.top, bottom: box.bottom});
          }
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
          for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            if (!node.textContent.trim() || node.parentElement.closest('select, script, style, .share-status')) continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            let left = Math.max(0, box.left), right = Math.min(innerWidth, box.right);
            for (let parent = node.parentElement; parent && parent !== root; parent = parent.parentElement) {
              if (getComputedStyle(parent).overflowX !== 'visible') {
                const clip = parent.getBoundingClientRect();
                left = Math.max(left, clip.left);
                right = Math.min(right, clip.right);
              }
            }
            for (const rect of range.getClientRects()) {
              if (rect.width && (rect.left < left - 1 || rect.right > right + 1)) {
                issues.push({text: node.textContent.trim().slice(0, 70),
                  left: rect.left, right: rect.right, bounds: [left, right]});
              }
            }
          }
          return {issues, font: getComputedStyle(root).fontSize};
        });
        assert.deepEqual(measured.issues, [], `${selector} text/bounds at ${await value()}`);
        for (const control of await panel.locator('button:visible, input:visible, select:visible').all()) {
          await control.evaluate(el => el.scrollIntoView({block: 'center', behavior: 'instant'}));
          const box = await control.boundingBox();
          const screen = page.viewportSize();
          assert(box && box.x >= -1 && box.x + box.width <= screen.width + 1
            && box.y >= -1 && box.y + box.height <= screen.height + 1,
          `${selector} control must be reachable without clipping: ${JSON.stringify(box)}`);
        }
        return measured.font;
      };
      for (const screen of [{width: 390, height: 844}, {width: 844, height: 390}]) {
        await page.setViewportSize(screen);
        await settle();
        const panelFonts = {};
        let sourceFont, navWidth;
        for (const zoom of [100, 200, 100]) {
          await openMenu();
          const currentZoom = Number((await value()).replace('%', ''));
          for (let i = 0; i < Math.abs(zoom - currentZoom) / 10; i++) {
            await activate(zoom > currentZoom ? zoomIn : zoomOut);
          }
          assert.equal(await value(), `${zoom}%`);
          await settle();
          const rawFont = await page.locator('#after h2').evaluate(el => parseFloat(getComputedStyle(el).fontSize));
          if (!sourceFont) sourceFont = rawFont;
          assert(Math.abs(rawFont / sourceFont - zoom / 100) < .02,
            'reading zoom must resize content, not shrink source type to fit foreground controls');
          const buttonWidth = await page.locator('#navMenu').evaluate(el => el.getBoundingClientRect().width);
          if (!navWidth) navWidth = buttonWidth;
          assert(Math.abs(buttonWidth / navWidth - 1) < .02, 'reading zoom must not resize navigation controls');
          await checkForeground('#readingMenu');
          await openMainMenu();
          await checkForeground('#presenterMenu');
          for (const [action, selector] of [['share', '#sharePopover'], ['theme', '#themeMenu'],
            ['tags', '#tagMenu'], ['presenter', '#presenterPanel'], ['help', '#helpOverlay']]) {
            if (!await page.locator('#presenterMenu').isVisible()) await openMainMenu();
            await activate(`[data-menu-action="${action}"]`);
            const font = await checkForeground(selector);
            if (!panelFonts[selector]) panelFonts[selector] = font;
            assert.equal(font, panelFonts[selector], 'panel font sizes must not be reduced to hide overflow');
            if (action === 'theme') {
              assert(await page.locator('#themeMenu .identity-option').count() >= 2,
                'appearance checks must exercise the real identity/preset picker');
            }
            if (action === 'presenter') {
              assert((await page.locator('#presenterNotes').textContent()).includes('Speaker notes remain readable'),
                'presenter bounds must be measured with actual notes');
            }
            if (action === 'share') {
              await activate('#sharePopover [data-action="qr"][data-scope="article"]');
              await checkForeground('#shareQrModal');
              await activate('#shareQrModal .share-qr-close');
            } else if (action === 'help') {
              await activate('#helpAbout');
              await checkForeground('#aboutOverlay');
              await activate('#aboutClose');
              await page.keyboard.press('Escape');
            } else {
              await page.keyboard.press('Escape');
            }
          }
          if (mobile && zoom === 200) {
            await openMainMenu();
            await activate('[data-menu-action="share"]');
            const session = await context.newCDPSession(page);
            await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1.5});
            assert(await page.evaluate(() => visualViewport.scale > 1.4));
            assert.equal(await page.locator('#sharePopover').evaluate(el => Number(getComputedStyle(el).zoom)), 1,
              'foreground needs no inverse zoom when only content is resized');
            await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1});
            await session.detach();
            await page.keyboard.press('Escape');
          }
        }
      }
      for (const theme of ['kit:lightwebpres-docs@0.1.0/docs', 'monochrome-night', 'print-ink']) {
        await openMainMenu();
        await activate('[data-menu-action="theme"]');
        await page.locator('#themeSource').selectOption('all');
        await page.locator('#themeFilter').fill('');
        await activate(`#themeOptions [data-theme="${theme}"]`);
        await settle();
        await openMenu();
        const surfaces = await page.evaluate(() => {
          const panel = getComputedStyle(document.querySelector('#readingMenu .presenter-menu-card'));
          return [...document.querySelectorAll('#readingMenu select, #readingMenu option')].map(node => {
            const style = getComputedStyle(node);
            return {element: node.id || node.textContent, background: style.backgroundColor,
              color: style.color, expectedBackground: panel.backgroundColor, expectedColor: panel.color};
          });
        });
        for (const surface of surfaces) {
          assert.equal(surface.background, surface.expectedBackground, `${theme}: ${surface.element} background`);
          assert.equal(surface.color, surface.expectedColor, `${theme}: ${surface.element} text`);
          assert.notEqual(surface.background, 'rgba(0, 0, 0, 0)');
          assert.notEqual(surface.background, surface.color);
        }
        const back = await page.locator('#readingMenuBack').evaluate(button => {
          const range = document.createRange();
          range.selectNodeContents(button);
          const rect = button.getBoundingClientRect();
          return {lines: range.getClientRects().length, left: rect.left, right: rect.right,
            height: rect.height, viewport: innerWidth};
        });
        assert.equal(back.lines, 1, `${theme}: Back must not wrap inside an icon-sized column`);
        assert(back.left >= 0 && back.right <= back.viewport && back.height >= 44);
        await activate('#readingMenuBack');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'menuReading');
        await activate('[data-menu-action="theme"]');
        const source = await page.locator('#themeSource').evaluate(select => {
          const panel = getComputedStyle(select.closest('.theme-menu-card'));
          return [...select.options].map(option => ({background: getComputedStyle(option).backgroundColor,
            color: getComputedStyle(option).color, expectedBackground: panel.backgroundColor,
            expectedColor: panel.color}));
        });
        for (const option of source) {
          assert.equal(option.background, option.expectedBackground);
          assert.equal(option.color, option.expectedColor);
        }
        await page.keyboard.press('Escape');
      }
      assert.deepEqual(errors, []);
      console.log(`${width} ${mobile ? 'mobile' : 'desktop'}: controls, gestures and reading anchors passed`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
