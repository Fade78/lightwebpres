/* Real generated tall tables; CDP touch is browser emulation, not a phone. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

(async () => {
  const scratch = path.resolve(__dirname, '../work/tmp');
  process.env.TMPDIR = scratch;
  const work = fs.mkdtempSync(path.join(scratch, 'table-gestures-'));
  const executablePath = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
  process.env.XDG_CACHE_HOME = path.join(work, 'cache');
  process.env.XDG_CONFIG_HOME = path.join(work, 'config');
  let browser;
  try {
    browser = await chromium.launch({executablePath});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  try {
    for (const mobile of [false, true]) {
      for (const url of process.argv.slice(2)) {
        const context = await browser.newContext({viewport: {width: mobile ? 390 : 1024, height: 844},
          isMobile: mobile, hasTouch: mobile});
        const page = await context.newPage();
        await context.route('https://example.invalid/**', route => route.fulfill({body: 'Native link opened'}));
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        const combined = url.endsWith('all.html');
        await page.goto(url + (combined ? '#lwp/a/gestures.html/tall' : '#tall'));
        await page.keyboard.press('m');
        await page.locator('#menuReading').click();
        await page.locator('#menuTableMode').selectOption('scroll');
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
        const settle = () => page.waitForTimeout(550);
        const state = () => page.evaluate(() => ({y: scrollY,
          active: document.querySelector('.nav-dots a.active')?.getAttribute('href')}));
        const activate = async point => {
          if (mobile) await page.touchscreen.tap(point.x, point.y);
          else await page.mouse.click(point.x, point.y);
          await settle();
        };
        for (const id of ['tall', 'prose']) {
          const slide = page.locator('#' + id);
          const viewport = slide.locator('.lwp-table-viewport');
          const reset = async () => {
            await page.evaluate(id => {
              window.getSelection().removeAllRanges();
              document.activeElement.blur();
              const el = document.getElementById(id);
              el.querySelector('.lwp-table-viewport').scrollTo({left: 0, top: 0, behavior: 'instant'});
              scrollTo({top: scrollY + el.getBoundingClientRect().top, behavior: 'instant'});
            }, id);
            await settle();
          };
          const point = async () => {
            const box = await viewport.boundingBox();
            const p = {x: box.x + 45, y: Math.min(650, Math.max(200, box.y + 90), box.y + box.height - 25)};
            assert(await page.evaluate(p => !!document.elementFromPoint(p.x, p.y)?.closest('td, th'), p),
              'input must hit a real table cell');
            return p;
          };
          const unchanged = async (before, label) => {
            await settle();
            const after = await state();
            assert.equal(after.active, before.active, label);
            assert(Math.abs(after.y - before.y) < 2, `${label}: ${JSON.stringify({before, after})}`);
          };
          await reset();
          assert(await viewport.evaluate(el => el.clientHeight > innerHeight && el.scrollWidth > el.clientWidth));
          const before = await state();
          await page.keyboard.press('ArrowDown');
          await settle();
          const expected = await state();
          await reset();
          await activate(await point());
          const after = await state();
          assert(after.y > before.y + 100 && after.y - before.y <= 844,
            `plain table ${mobile ? 'tap' : 'click'} must make one bounded step: ${before.y} -> ${after.y}`);
          assert.deepEqual(after, expected, 'table activation must share the normal bounded journey');
          await page.evaluate(p => document.elementFromPoint(p.x, p.y).dispatchEvent(
            new MouseEvent('click', {bubbles: true, detail: 1, clientX: p.x, clientY: p.y})), await point());
          await unchanged(after, 'one pointer gesture must never step twice');
          let previous = after, reachedBottom = false, reachedNext = false;
          for (let i = 0; i < 20; i++) {
            const bottom = await slide.evaluate(el => el.getBoundingClientRect().bottom);
            if (bottom <= 846) reachedBottom = true;
            await activate(await point());
            const next = await state();
            if (next.active !== previous.active) {
              assert(reachedBottom, 'read the table bottom before entering the next slide');
              reachedNext = true;
              break;
            }
            assert(next.y > previous.y && next.y - previous.y <= 844, 'each tap stays bounded');
            previous = next;
          }
          assert(reachedNext, 'repeated taps must eventually enter the next slide');
          assert.equal(await viewport.locator('tbody tr').count(), 40, 'no rows truncated');

          await reset();
          let stable = await state();
          let p = await point();
          // A programmatic/assistive activation intentionally has no pointer state.
          await page.evaluate(p => document.elementFromPoint(p.x, p.y).click(), p);
          await settle();
          assert.deepEqual(await state(), expected, 'coordinate-free activation must work');
          await reset();
          p = await point();
          stable = await state();
          for (const modifiers of [['Control'], ['Meta'], ['Shift'], ['Alt']]) {
            await page.keyboard.down(modifiers[0]);
            await page.mouse.click(p.x, p.y);
            await page.keyboard.up(modifiers[0]);
            await unchanged(stable, 'modified clicks stay native');
          }
          await page.mouse.click(p.x, p.y, {button: 'right'});
          await unchanged(stable, 'table right-click must not step backward');
          await page.keyboard.press('Escape');
          await page.mouse.move(p.x, p.y);
          await page.mouse.down();
          await page.waitForTimeout(550);
          await page.mouse.up();
          await unchanged(stable, 'long hold must not advance');
          // Maximum displacement, not just the endpoints: even an out-and-back
          // mouse drag on an empty part of a cell is not a tap.
          await page.mouse.move(p.x, p.y);
          await page.mouse.down();
          await page.mouse.move(p.x + 30, p.y);
          await page.mouse.move(p.x, p.y);
          await page.mouse.up();
          await unchanged(stable, 'out-and-back drag must not advance');
          const textPoint = await viewport.evaluate(el => {
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
              if (!node.textContent.trim() || node.parentElement.closest('a, button')) continue;
              const range = document.createRange();
              range.selectNodeContents(node);
              const rect = range.getBoundingClientRect();
              if (rect.top > 0 && rect.bottom < innerHeight && rect.left > 0 && rect.left + 100 < innerWidth) {
                return {x: rect.left + 2, y: (rect.top + rect.bottom) / 2};
              }
            }
          });
          assert(textPoint, 'native selection needs visible text');
          await page.mouse.move(textPoint.x, textPoint.y);
          await page.mouse.down();
          await page.mouse.move(textPoint.x + 100, textPoint.y, {steps: 10});
          await page.mouse.up();
          assert(await page.evaluate(() => !!String(getSelection())), 'mouse drag must really select table text');
          await unchanged(stable, 'native text selection must not advance');
          await reset();
          p = await point();
          stable = await state();
          await page.mouse.move(p.x, p.y);
          await page.mouse.down();
          await viewport.evaluate(el => { el.scrollLeft += 30; });
          await page.waitForTimeout(50);
          await page.mouse.up();
          await unchanged(stable, 'scroll during a press must not become a click step');
          await reset();
          p = await point();
          await page.mouse.move(p.x, p.y);
          await page.mouse.down();
          await page.evaluate(() => scrollBy({top: 80, behavior: 'instant'}));
          await page.waitForTimeout(50);
          const scrolled = await state();
          await page.mouse.up();
          await unchanged(scrolled, 'page scrolling during a press must not become a click step');
          await reset();
          p = await point();
          stable = await state();
          await page.evaluate(p => {
            const range = document.createRange();
            range.selectNodeContents(document.elementFromPoint(p.x, p.y));
            getSelection().removeAllRanges(); getSelection().addRange(range);
          }, p);
          await activate(p);
          await unchanged(stable, 'dismissing a selection must not advance');
          await reset();
          p = await point();
          stable = await state();
          await page.mouse.move(p.x, p.y);
          await page.mouse.wheel(300, 200);
          await unchanged(stable, 'wheel remains local');
          assert(await viewport.evaluate(el => el.scrollLeft > 0));
          await reset();
          for (const selector of ['a', 'button', 'label span', 'input', 'img']) {
            const control = viewport.locator(selector).first();
            await control.scrollIntoViewIfNeeded();
            await settle();
            const controlBefore = await state();
            const popup = selector === 'a' ? page.waitForEvent('popup') : null;
            if (mobile) await control.tap();
            else await control.click();
            if (popup) {
              const opened = await popup;
              await opened.waitForLoadState();
              assert.equal(opened.url(), 'https://example.invalid/');
              await opened.close();
            }
            if (selector === 'button') assert.equal(await control.getAttribute('data-clicked'), 'yes');
            if (selector === 'label span' || selector === 'input') {
              const input = viewport.locator('input').first();
              assert.equal(await input.isChecked(), selector === 'label span',
                'label child checks the input; direct input click unchecks it');
              assert(await input.evaluate(el => document.activeElement === el),
                `${selector} must retain native input focus`);
            }
            await unchanged(controlBefore, `native table ${selector}`);
          }
          if (id === 'tall' && !combined) {
            for (const role of ['button', 'checkbox', 'switch', 'slider', 'textbox']) {
              const control = viewport.locator(`[role="${role}"]`);
              await control.scrollIntoViewIfNeeded();
              await settle();
              const controlBefore = await state();
              if (mobile) await control.locator('span').tap();
              else await control.locator('span').click();
              assert.equal(await control.getAttribute('data-clicked'), 'yes',
                `the authored ${role} handler must still run`);
              assert(await control.evaluate(el => document.activeElement === el),
                `the authored ${role} must retain focus`);
              await unchanged(controlBefore, `table ${role} child stays local`);
            }
          }
          await reset();

          if (mobile) {
            const session = await context.newCDPSession(page);
            const send = (type, points) => session.send('Input.dispatchTouchEvent', {type, touchPoints: points});
            p = await point();
            stable = await state();
            // A sub-pan-threshold wobble remains a brief tap.
            await send('touchStart', [{...p, id: 1}]);
            await send('touchMove', [{x: p.x + 6, y: p.y + 2, id: 1}]);
            await send('touchEnd', []);
            await settle();
            assert.deepEqual(await state(), expected, 'tiny touch jitter must advance once');
            await reset();
            stable = await state();
            await send('touchStart', [{x: 5, y: 600, id: 1}]);
            for (let i = 1; i <= 8; i++) {
              await send('touchMove', [{x: 5, y: 600 - i * 25, id: 1}]);
              await page.waitForTimeout(35);
            }
            await send('touchEnd', []);
            await settle();
            assert((await state()).y > stable.y, 'native vertical page drag outside the table must still scroll');
            assert.equal((await state()).active, stable.active);
            await reset();
            p = await point();
            stable = await state();
            await send('touchStart', [{...p, id: 1}]);
            await page.waitForTimeout(600);
            await send('touchEnd', []);
            await unchanged(stable, 'native touch long press');
            await reset();
            // An authored height constraint gives the table a real vertical
            // range. Native pan and wheel must still move it, never the deck.
            await viewport.evaluate(el => { el.style.maxHeight = '500px'; el.style.overflowY = 'auto'; });
            await reset();
            p = await point();
            stable = await state();
            assert(await viewport.evaluate(el => el.scrollHeight > el.clientHeight));
            await send('touchStart', [{x: p.x, y: p.y + 180, id: 1}]);
            for (let i = 1; i <= 8; i++) {
              await send('touchMove', [{x: p.x, y: p.y + 180 - i * 20, id: 1}]);
              await page.waitForTimeout(35);
            }
            await send('touchEnd', []);
            await unchanged(stable, 'native vertical table scrolling');
            assert(await viewport.evaluate(el => el.scrollTop > 0), 'vertical touch drag must really scroll the table');
            await viewport.evaluate(el => { el.scrollTop = 0; });
            await settle();
            await page.mouse.move(p.x, p.y);
            await page.mouse.wheel(0, 150);
            await unchanged(stable, 'vertical table wheel');
            assert(await viewport.evaluate(el => el.scrollTop > 0));
            await viewport.evaluate(el => {
              el.style.removeProperty('max-height'); el.style.removeProperty('overflow-y');
            });
            await reset();
            p = await point();
            stable = await state();
            const drag = async (start, end) => {
              await send('touchStart', [{x: start, y: p.y, id: 1}]);
              for (let i = 1; i <= 8; i++) {
                await send('touchMove', [{x: start + (end - start) * i / 8, y: p.y, id: 1}]);
                await page.waitForTimeout(35);
              }
              await send('touchEnd', []);
              await unchanged(stable, 'native horizontal drag stays local');
            };
            await drag(290, 80);
            const left = await viewport.evaluate(el => el.scrollLeft);
            assert(left > 0, 'leftward touch drag must actually scroll right');
            await drag(80, 250);
            assert(await viewport.evaluate(el => el.scrollLeft) < left, 'rightward drag must scroll left');
            await viewport.evaluate(el => { el.scrollLeft = 0; });
            await settle();
            await drag(80, 290);
            assert.equal(await viewport.evaluate(el => el.scrollLeft), 0, 'drag at the left edge');
            await viewport.evaluate(el => { el.scrollLeft = el.scrollWidth; });
            await settle();
            const rightEdge = await viewport.evaluate(el => el.scrollLeft);
            await drag(290, 80);
            assert.equal(await viewport.evaluate(el => el.scrollLeft), rightEdge, 'drag at the right edge');
            // Compatibility click after a canceled native pan must not become a step.
            await page.evaluate(p => document.elementFromPoint(p.x, p.y).dispatchEvent(
              new MouseEvent('click', {bubbles: true, detail: 1, clientX: p.x, clientY: p.y})), p);
            await unchanged(stable, 'late click after edge drag');
            await page.evaluate(({id, p}) => document.getElementById(id).dispatchEvent(
              new MouseEvent('click', {bubbles: true, detail: 2, clientX: p.x, clientY: p.y})), {id, p});
            await unchanged(stable, 'retargeted compatibility click must not escape the table guard');
            await reset();
            p = await point();
            stable = await state();
            await send('touchStart', [{...p, id: 1}]);
            await send('touchCancel', []);
            await page.evaluate(p => document.elementFromPoint(p.x, p.y).click(), p);
            await unchanged(stable, 'cancel must suppress a ghost click');
            await reset();
            p = await point();
            stable = await state();
            await send('touchStart', [{x: 140, y: p.y, id: 1}, {x: 220, y: p.y, id: 2}]);
            for (const distance of [50, 65, 80, 95]) {
              await send('touchMove', [{x: 180 - distance, y: p.y, id: 1},
                {x: 180 + distance, y: p.y, id: 2}]);
              await page.waitForTimeout(50);
            }
            await send('touchEnd', []);
            assert(await page.evaluate(() => visualViewport.scale > 1.1), 'native table pinch must zoom');
            await page.evaluate(p => document.elementFromPoint(p.x, p.y).dispatchEvent(
              new MouseEvent('click', {bubbles: true, detail: 1})), p);
            await unchanged(stable, 'pinch and compatibility click must not advance');
            await session.send('Emulation.setPageScaleFactor', {pageScaleFactor: 1});
            await session.detach();
          }
          console.log(`${mobile ? 'mobile' : 'desktop'} ${combined ? 'single-html' : 'per-unit'} ${id}: table gestures passed`);
        }
        assert.deepEqual(errors, []);
        await context.close();
      }
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
