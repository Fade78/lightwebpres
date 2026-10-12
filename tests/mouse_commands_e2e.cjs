// Native browser input/API checks. Multi-monitor hardware remains a manual check.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const playwright = require('playwright');

(async () => {
  const [engineName, articleURL, combinedURL] = process.argv.slice(2);
  const engine = playwright[engineName];
  const scratch = path.resolve(__dirname, '../work/tmp');
  const work = fs.mkdtempSync(path.join(scratch, 'mouse-browser-'));
  process.env.TMPDIR = scratch;
  process.env.XDG_CACHE_HOME = path.join(work, 'cache');
  process.env.XDG_CONFIG_HOME = path.join(work, 'config');
  let browser;
  try {
    browser = await engine.launch({executablePath: engineName === 'chromium'
      && process.env.PW_CHROMIUM_PATH ? process.env.PW_CHROMIUM_PATH : engine.executablePath(),
      downloadsPath: path.join(work, 'downloads')});
  } catch (error) {
    if (/executable doesn't exist|Executable doesn't exist/.test(String(error))) {
      console.error('Browser check blocked: supplied ' + engineName + ' unavailable');
      process.exitCode = 77;
      return;
    }
    throw error;
  }
  try {
    for (const [url, combined] of [[articleURL, false], [combinedURL, true]]) {
      const page = await browser.newPage({viewport: {width: 1100, height: 800}});
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      const press = button => page.mouse.click(8, 8, {button});
      const sequence = async buttons => {
        for (const button of buttons) await press({M: 'middle', G: 'left', D: 'right'}[button]);
      };
      const fullscreenTransition = () => page.evaluate(() => new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(Error('no fullscreenchange in 5 seconds')), 5000);
        document.addEventListener('fullscreenchange', () => {
          clearTimeout(timeout); resolve();
        }, {once: true});
      }));
      const pauseOpen = () => page.locator('#pauseOverlay').evaluate(node => node.classList.contains('open'));
      const current = () => page.evaluate(() => [...document.querySelectorAll('.nav-dots a')]
        .findIndex(node => node.classList.contains('active')));
      const openArticle = async () => {
        await page.goto(url);
        if (combined) await page.locator('.article-card').first().click();
        await page.waitForFunction(() => !document.body.classList.contains('index-page'));
        await page.keyboard.press('Home');
      };
      await openArticle();
      await sequence('MMM');
      await press('left');
      assert.equal(await current(), 1, '3M cancels without a new pending prefix');
      await page.keyboard.press('Home');
      await sequence('M');
      await page.waitForTimeout(950);
      await press('left');
      assert.equal(await current(), 1, 'an expired M leaves normal click navigation');
      await page.keyboard.press('Home');
      await sequence('M');
      await page.keyboard.press('Shift');
      await press('left');
      assert.equal(await current(), 1, 'a modifier cancels pending M');
      await page.keyboard.press('Home');
      await sequence('M');
      await page.mouse.wheel(0, 60);
      await press('left');
      assert.equal(await page.evaluate(() => !!document.fullscreenElement), false, 'wheel cancels M');
      await page.keyboard.press('Home');
      await sequence('M');
      await page.locator('input').first().evaluate(node => node.focus());
      await page.keyboard.press('q');
      await page.locator('input').first().evaluate(node => node.blur());
      await press('left');
      assert.equal(await page.evaluate(() => !!document.fullscreenElement), false,
        'input-owned keyboard events still cancel M');
      await page.keyboard.press('Home');
      await sequence('M');
      await page.waitForTimeout(650);
      await sequence('M');
      await page.waitForTimeout(650);
      await sequence('D');
      assert.equal(await pauseOpen(), true, '2M renews the deadline and D pauses');
      await page.keyboard.press('m');
      assert.equal(await page.locator('#presenterMenu.open').count(), 1);
      assert.equal(await pauseOpen(), true, 'opening the menu preserves theme pause');
      await page.keyboard.press('Escape');
      assert.equal(await pauseOpen(), true, 'closing the menu preserves theme pause');
      await page.keyboard.press('PageDown');
      assert.equal(await pauseOpen(), false, 'keyboard navigation cancels pause');
      await sequence('MMD');
      await press('right');
      assert.equal(await pauseOpen(), false, 'mouse navigation cancels pause');
      await sequence('MMD');
      await page.keyboard.press('t');
      assert.equal(await pauseOpen(), false, 'T shares the theme-pause toggle');
      await page.keyboard.press('Home');
      await page.evaluate(() => window.scrollTo({top: 120, behavior: 'instant'}));
      await sequence('MMG');
      assert.equal(await page.evaluate(() => document.body.classList.contains('index-page')), false,
        'a scrolled first slide returns to its own beginning');
      assert.ok(await page.locator('.slide').first().evaluate(node => node.getBoundingClientRect().top >= -1));
      await sequence('MMG');
      await page.waitForFunction(() => document.body.classList.contains('index-page'));
      await openArticle();
      let transition = fullscreenTransition();
      await sequence('MG');
      await transition;
      await page.waitForFunction(() => !!document.fullscreenElement);
      transition = fullscreenTransition();
      await sequence('MG');
      await transition;
      try {
        await page.waitForFunction(() => !document.fullscreenElement, null, {timeout: 3000});
      } catch (error) {
        throw new Error('MG did not leave fullscreen: ' + JSON.stringify(await page.evaluate(() => ({
          fullscreen: !!document.fullscreenElement, lock: !!document.pointerLockElement,
          menu: !!document.querySelector('.presenter-menu.open'),
          focus: document.activeElement.tagName, cursor: document.body.style.cursor,
        }))));
      }
      assert.equal(await current(), 0, 'fullscreen suffix clicks do not navigate');
      // Call the actual API from real input, not a success stub.
      transition = fullscreenTransition();
      await sequence('MG');
      await transition;
      try {
        await page.waitForFunction(() => !!document.fullscreenElement, null, {timeout: 3000});
      } catch (error) {
        throw new Error('MG did not re-enter fullscreen: ' + JSON.stringify(await page.evaluate(() => ({
          fullscreen: !!document.fullscreenElement, lock: !!document.pointerLockElement,
          focus: document.hasFocus(), menu: !!document.querySelector('.presenter-menu.open'),
        }))));
      }
      await sequence('MD');
      await page.waitForFunction(() => document.pointerLockElement === document.documentElement,
        null, {timeout: 5000});
      await page.waitForFunction(() => document.getElementById('menuPointerLock')
        .getAttribute('aria-pressed') === 'true', null, {timeout: 5000});
      for (let i = 0; i < 8; i++) {
        await page.mouse.move(1200 + i * 100, 1000 + i * 50);
        await page.waitForTimeout(50);
      }
      assert.equal(await page.evaluate(() => document.documentElement.classList.contains('nav-idle')), true,
        'sustained captured movement never reveals chrome');
      const before = await current();
      await press('left');
      assert.equal(await current(), before + 1, 'captured left clicks navigate');
      await press('right');
      assert.equal(await current(), before, 'captured right clicks navigate exactly once');
      await sequence('MMD');
      assert.equal(await pauseOpen(), true);
      assert.equal(await page.evaluate(() => !!document.pointerLockElement), true,
        'theme pause preserves mouse capture');
      await page.keyboard.press('m');
      await page.waitForFunction(() => !document.pointerLockElement);
      assert.equal(await pauseOpen(), true, 'menu releases the pointer without dismissing pause');
      await page.keyboard.press('Escape');
      await page.keyboard.press('t');
      await sequence('MD');
      await page.waitForFunction(() => !!document.pointerLockElement);
      if (combined) {
        await sequence('MMG');
        await sequence('MMG');
        await page.waitForFunction(() => document.body.classList.contains('index-page'));
        assert.equal(await page.evaluate(() => document.pointerLockElement === document.documentElement), true,
          'the stable combined-document root retains capture across view replacement');
      }
      await sequence('MD');
      await page.waitForFunction(() => !document.pointerLockElement
        && document.body.style.cursor !== 'none');
      assert.equal(await page.evaluate(() => document.body.style.cursor), '', 'unlock reveals immediately');
      await sequence('MD');
      await page.waitForFunction(() => !!document.pointerLockElement);
      // Firefox may leave fullscreen on the Escape that closes the menu.
      // Capture does not imply fullscreen: toggle from the actual state.
      const fullscreenBefore = await page.evaluate(() => !!document.fullscreenElement);
      transition = fullscreenTransition();
      await sequence('MG');
      await transition;
      try {
        await page.waitForFunction(before =>
          !!document.fullscreenElement !== before && !document.pointerLockElement,
          fullscreenBefore, {timeout: 5000});
      } catch (error) {
        const state = await page.evaluate(() => ({
          fullscreen: !!document.fullscreenElement,
          pointerLock: !!document.pointerLockElement,
          menuOpen: !!document.querySelector('.presenter-menu.open'),
          activeView: document.body.className,
        }));
        throw new Error('MG did not toggle fullscreen and release capture: '
          + JSON.stringify({state, combined, fullscreenBefore}));
      }
      if (!fullscreenBefore) {
        transition = fullscreenTransition();
        await sequence('MG');
        await transition;
        await page.waitForFunction(() => !document.fullscreenElement);
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    // Touch emulation with real mouse input on the same page. This exercises
    // event ownership; it does not claim physical tablet/phone verification.
    const context = await browser.newContext({hasTouch: true,
      ...(engineName === 'chromium' ? {isMobile: true} : {}),
      viewport: {width: 900, height: 700}});
    const page = await context.newPage();
    await page.goto(articleURL);
    if (engineName === 'chromium') {
      assert.equal(await page.evaluate(() => matchMedia('(pointer: fine)').matches), false);
    }
    const current = () => page.evaluate(() => [...document.querySelectorAll('.nav-dots a')]
      .findIndex(node => node.classList.contains('active')));
    const middle = () => page.mouse.click(8, 8, {button: 'middle'});
    await page.keyboard.press('PageDown');
    assert.equal(await current(), 1);
    await middle();
    await page.touchscreen.tap(8, 8);
    await page.waitForTimeout(450);
    assert.equal(await current(), 2, 'touch keeps its navigation and cancels pending M');
    assert.equal(await page.evaluate(() => !!document.fullscreenElement), false);
    await page.keyboard.press('PageUp');
    await page.touchscreen.tap(8, 8);
    await page.waitForTimeout(60);
    await page.touchscreen.tap(8, 8);
    await page.waitForTimeout(450);
    assert.equal(await current(), 1, 'touch double tap keeps its restore-and-visibility behavior');
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains('mouse-input')), false);
    assert.equal(await page.evaluate(() => {
      const event = new PointerEvent('contextmenu', {bubbles: true, cancelable: true,
        pointerType: 'touch', button: 2});
      document.querySelector('.slide').dispatchEvent(event);
      return event.defaultPrevented;
    }), false, 'touch context menus remain native');
    await middle();
    await page.mouse.click(8, 8);
    await page.waitForFunction(() => !!document.fullscreenElement);
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains('mouse-input')), true,
      'mouse commands work without changing primary touch capability');
    await middle();
    await page.mouse.click(8, 8, {button: 'right'});
    await page.waitForFunction(() => !!document.pointerLockElement);
    await page.touchscreen.tap(8, 8);
    await page.waitForFunction(() => !document.pointerLockElement);
    assert.equal(await page.evaluate(() => document.documentElement.classList.contains('mouse-input')), false,
      'switching back to touch releases capture');
    assert.equal(await page.evaluate(() => document.body.classList.contains('fs-noselect')), false,
      'fullscreen retains native touch selection');
    await context.close();
    console.log('Mouse command browser checks passed (' + engineName + ')');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
