// Real geometry, not a duplicate implementation of the composition solver.
const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const [articleURL, bundleURL] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout: 15000});
    try {
      for (const [url, combined] of [[articleURL, false], [bundleURL, true]]) {
        const page = await browser.newPage({viewport: {width: 1000, height: 800}});
        const errors = [];
        page.on('pageerror', error => errors.push(String(error)));
        await page.goto(url + (combined ? '#lwp/a/a.html/detail' : '#detail'));
        const settle = async () => {
          await page.evaluate(() => document.fonts.ready);
          await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        };
        await settle();
        const measure = slug => page.locator('#' + slug).evaluate(slide => {
          const box = node => { const b = node.getBoundingClientRect();
            return {left:b.left, top:b.top, right:b.right, bottom:b.bottom, width:b.width, height:b.height}; };
          const elements = {};
          for (const host of slide.querySelectorAll('.lwp-graphic-host')) {
            for (const graphic of host.shadowRoot.querySelectorAll('.graphic')) {
              const payload = graphic.querySelector('.rotor > span');
              elements[graphic.dataset.element] = {...box(graphic), visible:getComputedStyle(graphic).visibility,
                payloadVisible:getComputedStyle(payload).visibility,
                font:getComputedStyle(payload).fontSize, color:getComputedStyle(payload).color,
                case:getComputedStyle(payload).fontVariant,
                tint:getComputedStyle(graphic.querySelector('.rotor')).backgroundColor,
                layoutWidth:payload.style.width};
            }
          }
          const kicker = slide.querySelector('.slide-kicker');
          const range = document.createRange(); if (kicker) range.selectNodeContents(kicker);
          return {slide:box(slide), elements, kicker:kicker ? box(range) : null,
            heading:box(slide.querySelector('h1,h2')),
            summary:slide.querySelector('.summary') ? box(slide.querySelector('.summary')) : null,
            scroll:slide.scrollHeight, client:slide.clientHeight,
            title:slide.querySelector('h1,h2').textContent,
            kickerCount:slide.querySelectorAll('.slide-kicker').length,
            fitted:slide.getAttribute('data-lwp-text-scale')};
        });
        const near = (a,b,message) => assert.ok(Math.abs(a-b)<1.5, `${name} ${message}: ${a} versus ${b}`);
        const check = async slug => {
          await settle(); const m = await measure(slug);
          assert.ok(m.elements.stamp.width>0, `${name} mounted ${slug}: ${JSON.stringify(m)}`);
          near(m.elements.stamp.width,120,'post-rotation width');
          near(m.elements.stamp.left,m.kicker.right+8,'content-bound attachment');
          near(m.elements.stamp.top+m.elements.stamp.height/2,m.kicker.top+m.kicker.height/2,'middle attachment');
          near(m.elements.dependent.top,m.elements.stamp.bottom+6,'element dependency');
          if(m.elements.cross) {
            near(m.elements.cross.left,m.elements.dependent.right+4,'cross-layer dependency x');
            near(m.elements.cross.top,m.elements.dependent.bottom+4,'cross-layer dependency y');
          }
          assert.equal(m.elements.stamp.font,'28px','fixed text does not borrow fitting');
          near(m.elements.before.width,Math.SQRT1_2*(120+28),'before-rotation width');
          assert.equal(m.elements.before.tint,'rgb(255, 0, 0)','alpha-mask tint follows the rotated image');
          near(m.elements.wrapped.width,180,'uniformly scaled wrapped layout');
          assert.equal(m.elements.wrapped.layoutWidth,'90px','wrapping width stays independent');
          assert.ok(m.elements.wrapped.height>60,'text wraps before scaling');
          assert.equal(m.elements.fixed.color,'rgb(18, 52, 86)','fixed ink stays fixed');
          assert.equal(m.elements.variant.color,'rgb(255, 0, 0)','screen style overrides asset default');
          assert.equal(m.elements.variant.case,'small-caps','typed small-caps renders as font variant');
          assert.equal(m.kickerCount,1,'asset headings/kickers remain inside isolated DOM');
          assert.ok(m.scroll<=m.client+1,'graphic transforms do not enlarge slide scroll metrics');
          return m;
        };
        assert.equal(await page.locator('#cover .lwp-graphic-host').count(),0);
        assert.equal(await page.locator('#disabled .lwp-graphic-host').count(),0);
        await check('detail');
        const originalInk = (await measure('detail')).elements.stamp.color;
        await page.keyboard.press('c'); await page.locator('#themeMenu.open').waitFor();
        await page.locator('[data-theme="monochrome-night"]').click();
        await page.keyboard.press('Escape'); await settle();
        assert.notEqual((await measure('detail')).elements.stamp.color,originalInk,'theme-linked ink follows theme');
        await check('detail');
        const localLink = page.locator('#detail .lwp-graphic-host .graphic[data-element="link"] a');
        const oldHash = await page.evaluate(() => location.hash);
        await localLink.click();
        assert.equal(await page.evaluate(() => location.hash),oldHash,'asset IDs do not become article routes');
        await page.evaluate(() => document.activeElement.blur());
        const gap = await measure('detail');
        near(gap.elements.region.top+gap.elements.region.height/2,
          (gap.heading.bottom+gap.summary.top)/2,'derived region');
        await page.evaluate(() => {
          document.documentElement.style.scrollBehavior='auto';
          document.documentElement.style.scrollSnapType='none';
          window.scrollTo(0,document.getElementById('edge').offsetTop-innerHeight/2);
        });
        await settle();
        for(const slug of ['detail','edge']) {
          const partial=await measure(slug);
          const height=Math.min(partial.slide.bottom,800)-Math.max(partial.slide.top,0);
          near(partial.elements.fragment.height,height*.2,`${slug}: own screen fragment height`);
          assert.ok(height>0 && height<600,'two cards each own a partial screen');
        }
        await page.locator('#detail').scrollIntoViewIfNeeded();await settle();
        await page.keyboard.press('f');
        await page.waitForFunction(() => !!document.fullscreenElement);
        await check('detail');
        await page.keyboard.press('f');
        await page.waitForFunction(() => !document.fullscreenElement);
        await settle();
        await page.locator('#detail').scrollIntoViewIfNeeded();
        await settle();
        const choose = async selector => {
          await page.keyboard.press('c'); await page.locator('#themeMenu.open').waitFor();
          const identity = selector==='builtin/standard' ? 'builtin' : 'graphics-test@1.0.0';
          await page.locator(`#identityOptions [data-identity="${identity}"]`).click();
          await page.locator(`#presentationOptions [data-presentation="${selector}"]`).click();
          await page.keyboard.press('Escape'); await settle();
        };
        for (const viewport of [{width:1000,height:800},{width:390,height:844}]) {
          await page.setViewportSize(viewport); await choose('graphics-test@1.0.0/test');
          await check('detail');
          await page.keyboard.press('d'); await page.locator('#readingMenu.open').waitFor();
          for(let n=0;n<4;n++) await page.locator('[data-menu-action="zoom-in"]').click();
          await page.keyboard.press('Escape'); await check('detail');
          await page.keyboard.press('d'); await page.locator('[data-menu-action="zoom-reset"]').click();
          await page.keyboard.press('Escape'); await settle();
          await page.evaluate(() => {
            document.documentElement.style.scrollBehavior='auto';
            document.documentElement.style.scrollSnapType='none';
            window.scrollTo(0,document.getElementById('tall').offsetTop+350);
          });
          await settle();
          const tall = await check('tall');
          near(tall.elements.screen.bottom,viewport.height-10,'screen follows visible fragment bottom');
          near(tall.elements.screen.width,viewport.width*.2,'screen width percentage');
          near(tall.elements.viewport.height,viewport.height*.1,'viewport height is not fragment height');
          await page.emulateMedia({media:'print'});
          await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
          await settle();
          const printed = await measure('tall');
          near(printed.elements.screen.bottom,printed.slide.bottom-10,'print uses full slide, not old screen');
          assert.equal(printed.elements.viewport.visible,'hidden','screen-only graphic does not print');
          assert.equal(printed.elements.viewport.payloadVisible,'hidden','hidden graphic content cannot escape through shadow reset');
          assert.equal(printed.elements.variant.color,'rgb(0, 0, 0)','screen ink does not leak into print');
          assert.equal(printed.elements.variant.case,'normal','screen casing does not leak into print');
          await page.emulateMedia({media:'screen'});
          await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
          await settle();
          await page.evaluate(() => document.getElementById('detail').scrollIntoView());
          await settle(); await choose('builtin/standard'); await check('detail');
        }
        if(combined) {
          await page.evaluate(() => { location.hash='#lwp/a/b.html/other'; });
          await page.locator('#other').waitFor(); await settle(); await check('other');
          await page.evaluate(() => { location.hash='#lwp/a/a.html/detail'; });
          await page.locator('#detail').waitFor(); await settle(); await check('detail');
        }
        assert.deepEqual(errors,[],`${name}: no browser errors`);
        await page.close();
      }
      console.log(`${name}: graphic checks passed`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode=1; });
