const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout:15000});
    try {
      const page = await browser.newPage({viewport:{width:1100,height:850}});
      const errors=[]; page.on('pageerror',e=>errors.push(String(e)));
      await page.addInitScript(() => {
        window.graphicErrors=[];
        window.addEventListener('lwp:graphic-error',e=>window.graphicErrors.push(e.detail));
      });
      await page.goto(process.argv[2]);
      await page.evaluate(() => document.fonts.ready);
      const shared=['slide','screen','viewport','main','title','draft-banner'];
      const chrome=['header','header-text','header-group','footer','footer-text','slide-number'];
      const expected={
        cover:[...shared,...chrome,'kicker','summary','build-stamp'],
        fact:[...shared,...chrome,'kicker','summary','highlight','highlight-caption','highlight-group',
          'fact','fact-label','fact-content','body','source','local'],
        body:[...shared,...chrome,'body'],
        index:[...shared,...chrome,'summary','body','unit-index'],
        series:[...shared,...chrome.filter(ref=>ref!=='slide-number'),'body','series-list'],
        article:[...shared,...chrome,'kicker','body'],
        notes:[...shared,'notes','body','article-footer','byline','license'],
      };
      for(const [slug,visible] of Object.entries(expected)) {
        await page.evaluate(slug=>document.getElementById(slug).scrollIntoView({behavior:'instant'}),slug);
        await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
        const actual=await page.locator('#'+slug).evaluate(slide=>{
          const result={};
          for(const host of slide.querySelectorAll('.lwp-graphic-host')) {
            for(const element of host.shadowRoot.querySelectorAll('.graphic')) {
              result[element.dataset.element]=getComputedStyle(element).visibility;
            }
          }
          return result;
        });
        assert.ok(Object.keys(actual).length>25,`${name}: mounted registry for ${slug}`);
        for(const [ref,visibility] of Object.entries(actual)) {
          assert.equal(visibility,visible.includes(ref) ? 'visible' : 'hidden',`${name} ${slug} ${ref}`);
        }
        if(slug==='fact') {
          const position=()=>page.locator('#fact').evaluate(slide=>({
            target:slide.querySelector('#local-target').getBoundingClientRect().top,
            graphic:slide.querySelector('.lwp-graphic-host').shadowRoot
              .querySelector('[data-element="local"]').getBoundingClientRect().top,
          }));
          const before=await position();
          await page.locator('#local-scroller').evaluate(node=>{node.scrollTop=50;});
          await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
          const after=await position();
          assert.ok(Math.abs(after.target-before.target+50)<1,`${name}: target moves inside local scroller`);
          assert.ok(Math.abs(after.graphic-after.target)<1,`${name}: graphic follows a non-bubbling local scroll`);
        }
      }
      assert.ok(await page.evaluate(()=>window.graphicErrors.some(e=>e.element==='refs/strict')),
        `${name}: missing error policy is an observable event, not an uncaught exception`);
      assert.deepEqual(errors,[],`${name}: no page errors`);
      await page.close();
      console.log(`${name}: native graphic references passed`);
    } finally {await browser.close();}
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
