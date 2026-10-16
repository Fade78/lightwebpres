const assert = require('node:assert/strict');
let chromium;
try { ({chromium} = require('playwright')); }
catch (error) { console.error('Playwright unavailable'); process.exit(77); }

(async () => {
  let browser;
  try { browser = await chromium.launch({timeout:15000}); }
  catch (error) {
    if (/executable doesn't exist/i.test(String(error))) {
      console.error('Chromium unavailable'); process.exitCode = 77; return;
    }
    throw error;
  }
  try {
    for (const [index, url] of process.argv.slice(2).entries()) {
      const context = await browser.newContext({viewport:{width:390,height:844},
        hasTouch:true, isMobile:true, deviceScaleFactor:3});
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      await page.goto(url);
      if (index) await page.locator('.article-card').first().click();
      await page.keyboard.press('PageDown');
      // This fixture compares the saved position exactly: do not sample the
      // last pixel of an unfinished glide as the first tap's starting point.
      await page.waitForFunction(() => Math.abs(document.getElementById('c2').getBoundingClientRect().top) < .01);
      await page.evaluate(() => {
        window.touchTimes = [];
        window.blockNextTouch = false;
        document.addEventListener('touchend', () => {
          if (!window.blockNextTouch) return;
          window.blockNextTouch = false;
          // A deterministic long task stands for delayed event delivery. It
          // does not forge touch timestamps or replace any browser API.
          setTimeout(() => { const start = performance.now(); while (performance.now() - start < 450) {} }, 0);
        }, {passive:true});
        window.addEventListener('touchend', event => touchTimes.push({
          timestamp:event.timeStamp, now:Date.now(), trusted:event.isTrusted}), {passive:true});
      });
      const state = () => page.evaluate(() => ({
        idle:document.documentElement.classList.contains('nav-idle'),
        scrollX, scrollY, hash:location.hash,
        active:document.querySelector('.nav-dots a.active')?.getAttribute('href')}));
      const session = await context.newCDPSession(page);
      const down = () => session.send('Input.dispatchTouchEvent',
        {type:'touchStart', touchPoints:[{x:195,y:400,id:1}]});
      const up = () => session.send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]});
      for (const action of ['hide','reveal']) {
        const before = await state();
        await page.evaluate(() => { window.touchTimes = []; window.blockNextTouch = true; });
        await down();
        const first = up();
        // Submit both ends independently of renderer acknowledgements: these
        // are two short native taps even while JavaScript is busy.
        await new Promise(resolve => setTimeout(resolve,60));
        const second = down();
        await new Promise(resolve => setTimeout(resolve,10));
        const third = up();
        await Promise.all([first,second,third]);
        const times = await page.evaluate(() => touchTimes);
        assert.equal(times.length,2);
        assert.ok(times.every(event => event.trusted));
        const inputGap = times[1].timestamp-times[0].timestamp;
        const dispatchGap = times[1].now-times[0].now;
        assert.ok(inputGap >= 0 && inputGap < 350 && dispatchGap > 350,
          'fixture must deliver valid native taps with delayed handlers: ' + JSON.stringify(times));
        const after = await state();
        assert.deepEqual(after, {...before,idle:!before.idle},
          action + ' restores the first tap position and changes visibility only: ' + JSON.stringify(times));
        await page.waitForTimeout(600);
        assert.deepEqual(await state(), after, 'queued compatibility clicks cannot navigate after restoration');
      }
      assert.deepEqual(errors, []);
      await context.close();
    }
    console.log('Queued native touch checks passed');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
