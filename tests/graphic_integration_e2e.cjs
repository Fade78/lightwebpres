const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const [article, bundle, destination] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [url, combined] of [[article, false], [bundle, true]]) {
        const page = await browser.newPage({viewport: {width: 900, height: 700}});
        await page.addInitScript(() => {
          window.graphicInputTrace = [];
          window.graphicMouseEvents = [];
          for (const type of ['mousedown', 'mouseup', 'click', 'auxclick', 'contextmenu',
                              'pointerlockchange', 'pointerlockerror', 'fullscreenchange',
                              'fullscreenerror', 'selectionchange', 'blur', 'focus']) {
            addEventListener(type, event => {
              const target = event.target;
              const entry = [type, event.button, event.detail,
                event.timeStamp, performance.now(), target?.tagName || 'window', target?.id || '',
                !!document.pointerLockElement, !!document.fullscreenElement, String(getSelection())];
              window.graphicInputTrace.push(entry);
              if (type === 'mousedown' || type === 'mouseup') window.graphicMouseEvents.push(entry);
              if (window.graphicInputTrace.length > 160) window.graphicInputTrace.shift();
            }, true);
          }
        });
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        const route = '#lwp/a/' + encodeURIComponent(destination) + '/grid';
        await page.goto(url + (combined ? route : '#grid'));
        const settle = async () => {
          await page.evaluate(() => document.fonts.ready);
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        };
        const ready = async () => {
          await page.locator('#grid:not([hidden])').waitFor();
          await page.waitForFunction(() => {
            const graphics = document.querySelector('#grid .lwp-graphic-host')?.shadowRoot.querySelectorAll('.graphic');
            return graphics?.length === 2 && [...graphics].every(mark => {
              const image = mark.querySelector('.rotor > span')?.shadowRoot.querySelector('img');
              return mark.style.visibility === 'visible' && image?.complete && image.naturalWidth > 0;
            });
          }, null, {timeout: 5000});
          await page.locator('#grid .fact-box img').evaluateAll(images => Promise.all(images.map(image => image.decode())));
          await settle();
        };
        const check = async (state, printing = false) => {
          await settle();
          const value = await page.locator('#grid').evaluate(slide => {
            const table = slide.querySelector('table'), box = slide.getBoundingClientRect();
            const viewport = slide.querySelector('.lwp-table-viewport').getBoundingClientRect();
            const mark = slide.querySelector('.lwp-graphic-host').shadowRoot.querySelector('.graphic').getBoundingClientRect();
            const assetTable = slide.querySelector('.lwp-graphic-host').shadowRoot.querySelector(
              '[data-element="assettable"] .rotor > span').shadowRoot.querySelector('table');
            return {cells: [...table.rows].map(row => [...row.cells].map(cell => [cell.colSpan, cell.rowSpan])),
              assetCells: [...assetTable.rows].map(row => [...row.cells].map(cell => [cell.colSpan, cell.rowSpan])),
              height: box.height, scroll: slide.scrollHeight, screen: innerHeight,
              markWidth: mark.width, markRight: mark.right, right: box.right,
              images: [...table.querySelectorAll('img')].map(image => {
                const b = image.getBoundingClientRect();
                return {width: b.width, height: b.height, ratio: image.naturalWidth / image.naturalHeight,
                  left: b.left - viewport.left, right: b.right - viewport.right};
              })};
          });
          assert.deepEqual(value.cells, [[[2, 2], [1, 2]], [], [[2, 1], [1, 1]]], `${name} ${state}: merged grid`);
          assert.deepEqual(value.assetCells, [[[2, 2]], []], `${name} ${state}: same merge grammar inside an HTML asset`);
          assert.ok(Math.abs(value.markWidth - 64) < 1.5 && Math.abs(value.markRight - value.right + 20) < 1.5,
            `${name} ${state}: decoration remains independently anchored: ${JSON.stringify(value)}`);
          assert.ok(value.images.length === 2 && value.images.every(image => image.width > 0 && image.height > 0
            && Math.abs(image.width / image.height - image.ratio) < .025), `${name} ${state}: image integrity`);
          if (!printing) assert.ok(value.height <= value.screen + 1 && value.scroll <= value.screen + 1
            && value.images.every(image => image.left >= -1 && image.right <= 1.1),
          `${name} ${state}: decorations do not disrupt table fitting: ${JSON.stringify(value)}`);
        };
        await ready(); await check('initial');
        const waitState = async (label, condition) => {
          try { await page.waitForFunction(condition, null, {timeout: 5000}); }
          catch (error) {
            const state = await page.evaluate(() => ({trace: window.graphicInputTrace,
              pointerLock: !!document.pointerLockElement, fullscreen: !!document.fullscreenElement,
              cursor: document.body.style.cursor, selection: String(getSelection()),
              active: document.activeElement?.outerHTML.slice(0, 400)}));
            const scratch = fs.mkdtempSync(path.join(path.resolve(__dirname, '../work/tmp'), 'graphic-input-failure-'));
            const file = path.join(scratch, 'trace.json');
            fs.writeFileSync(file, JSON.stringify({browser: name, combined, label, state}, null, 2));
            throw new Error(`${name} ${combined ? 'combined' : 'multipage'} ${label}: `
              + JSON.stringify(state) + `; trace: ${file}`, {cause: error});
          }
        };
        const sequence = async button => {
          const box = await page.locator('#grid h2').boundingBox();
          const point = {x: box.x + Math.min(24, box.width / 2), y: box.y + box.height / 2};
          await page.mouse.move(point.x, point.y);
          const start = await page.evaluate(() => window.graphicMouseEvents.length);
          // Queue ordered native input together: a renderer acknowledgement
          // between clicks can itself exceed 900ms under browser contention.
          await Promise.all([
            page.mouse.down({button: 'middle', clickCount: 1}),
            page.mouse.up({button: 'middle', clickCount: 1}),
            page.mouse.down({button, clickCount: 1}),
            page.mouse.up({button, clickCount: 1}),
          ]);
          // Firefox may drop the suffix's mouseup when that press exits native
          // fullscreen. Both presses and the prefix release must still arrive.
          await page.waitForFunction(start => window.graphicMouseEvents.slice(start).filter(
            event => event[0] === 'mousedown').length >= 2,
            start, {timeout: 5000});
          const events = await page.evaluate(start => window.graphicMouseEvents.slice(start), start);
          const suffix = button === 'left' ? 0 : 2;
          const presses = events.filter(event => event[0] === 'mousedown');
          assert.deepEqual(presses.map(event => event[1]), [1, suffix], `${name}: both native presses arrive in order`);
          assert.ok(events.slice(events.indexOf(presses[0]) + 1, events.indexOf(presses[1])).some(
            event => event[0] === 'mouseup' && event[1] === 1), `${name}: release the prefix before the suffix, not a chord`);
          assert.ok(presses[1][3] >= presses[0][3] && presses[1][3] - presses[0][3] < 900,
            `${name}: the fixture must actually generate a rapid native sequence: ${JSON.stringify(events)}`);
        };
        for (let cycle = 0; cycle < 3; cycle++) {
          await sequence('right');
          await waitState(`cycle ${cycle} MD acquire`, () => !!document.pointerLockElement);
          await sequence('left');
          await waitState(`cycle ${cycle} MG enter`, () => !!document.fullscreenElement);
          await check('MG fullscreen');
          await sequence('right');
          await waitState(`cycle ${cycle} MD release after fullscreen`, () => !document.pointerLockElement);
          await sequence('right');
          await waitState(`cycle ${cycle} MD reacquire`, () => !!document.pointerLockElement);
          await sequence('left');
          await waitState(`cycle ${cycle} MG exit after reacquisition`, () => !document.fullscreenElement && !document.pointerLockElement);
          await check('reacquisition then MG exit');
        }
        await page.setViewportSize({width: 390, height: 844}); await check('mobile');
        await page.keyboard.press('d'); await page.locator('#readingMenu.open').waitFor();
        for (let n = 0; n < 5; n++) await page.locator('[data-menu-action="zoom-in"]').click();
        await check('150% zoom');
        await page.emulateMedia({media: 'print'});
        await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
        await check('print', true);
        await page.emulateMedia({media: 'screen'});
        await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
        await check('print restoration');
        await page.locator('[data-menu-action="zoom-reset"]').click(); await page.keyboard.press('Escape');
        if (combined) {
          await page.evaluate(() => { location.hash = '#lwp/a/b.html/other'; });
          await page.locator('#other').waitFor();
          assert.equal(await page.locator('.lwp-graphic-host').count(), 0, 'unmatched tags do not receive automatic layers');
          await page.evaluate(route => { location.hash = route; }, route);
          await ready(); await check('combined remount');
        }
        assert.deepEqual(errors, [], `${name}: browser errors`);
        await page.close();
      }
      console.log(`${name}: graphic/table/reader integration passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
