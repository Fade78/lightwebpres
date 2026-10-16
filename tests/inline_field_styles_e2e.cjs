const assert = require('node:assert/strict');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const [articleURL, bundleURL] = process.argv.slice(2);
  for (const [name, engine] of [['chromium', chromium], ['firefox', firefox]]) {
    const browser = await engine.launch({timeout:15000});
    try {
      for (const [url, combined] of [[articleURL,false],[bundleURL,true]]) {
        const page = await browser.newPage({viewport:{width:1200,height:850}});
        const errors=[];page.on('pageerror',e=>errors.push(String(e)));
        await page.goto(url+(combined ? '#lwp/a/a.html/detail' : '#detail'));
        const settle=async()=>{
          await page.evaluate(()=>document.fonts.ready);
          await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
        };
        const check=async colour=>{
          await settle();
          const result=await page.evaluate(()=>{
            const selectors={title1:'#cover h1',title2:'#detail h2',
              summary:'#detail .summary','cover.summary':'#cover .summary'};
            const values={};
            for(const [field,selector] of Object.entries(selectors)) {
              const parent=document.querySelector(selector);values[field]={};
              for(const [role,tag] of Object.entries({strong:'strong',em:'em',code:'code',link:'a'})) {
                const style=getComputedStyle(parent.querySelector(tag));
                values[field][role]={fg:style.color,bg:style.backgroundColor,weight:style.fontWeight,
                  style:style.fontStyle,decoration:style.textDecorationLine,
                  ratio:parseFloat(style.fontSize)/parseFloat(getComputedStyle(parent).fontSize),
                  pad:style.paddingInlineStart,radius:style.borderRadius};
              }
            }
            values.body=getComputedStyle(document.querySelector('#detail .fact-content strong')).color;
            return values;
          });
          for(const field of ['title1','title2','summary','cover.summary']) {
            for(const role of ['strong','em','code','link']) {
              const expected=field==='title2' && role==='link' ? 'rgb(171, 205, 239)' : colour;
              assert.equal(result[field][role].fg,expected,`${name} ${field}.${role}: foreground`);
            }
          }
          assert.equal(result.title2.strong.weight,'400',`${name}: semantic strong can use normal weight`);
          assert.equal(result.title2.strong.style,'italic',`${name}: strong can be italic`);
          assert.equal(result.summary.em.style,'normal',`${name}: em is a semantic role, not a forced font`);
          assert.equal(result.summary.link.decoration,'line-through',`${name}: link decoration is typed`);
          assert.equal(result.summary.strong.bg,'rgb(255, 240, 170)');
          assert.equal(result.summary.strong.pad,'4px');
          assert.equal(result.summary.strong.radius,'3px');
          assert.ok(Math.abs(result.title2.code.ratio-.7)<.025,`${name}: code size remains relative after fitting/zoom`);
          assert.equal(result.body,'rgb(26, 26, 46)',`${name}: field roles cannot restyle body strong`);
        };
        const theme=async slug=>{
          await page.keyboard.press('c');await page.locator('#themeMenu.open').waitFor();
          await page.locator(`[data-theme="${slug}"]`).click();await page.keyboard.press('Escape');
          await settle();
        };
        const preset=async selector=>{
          await page.keyboard.press('c');await page.locator('#themeMenu.open').waitFor();
          await page.locator(`[data-identity="${selector==='builtin/standard' ? 'builtin' : 'lightwebpres-docs@0.1.0'}"]`).click();
          await page.locator(`[data-presentation="${selector}"]`).click();await page.keyboard.press('Escape');
          await settle();
        };
        await check('rgb(18, 52, 86)');
        await theme('inline-b');await check('rgb(101, 67, 33)');
        await preset('lightwebpres-docs@0.1.0/docs');await check('rgb(101, 67, 33)');
        await page.setViewportSize({width:390,height:844});await check('rgb(101, 67, 33)');
        await page.keyboard.press('d');await page.locator('#readingMenu.open').waitFor();
        for(let n=0;n<3;n++)await page.locator('[data-menu-action="zoom-in"]').click();
        await page.keyboard.press('Escape');await check('rgb(101, 67, 33)');
        await page.emulateMedia({media:'print'});
        await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
        await check('rgb(101, 67, 33)');
        await page.emulateMedia({media:'screen'});
        await page.evaluate(()=>window.dispatchEvent(new Event('afterprint')));
        await check('rgb(101, 67, 33)');
        await preset('builtin/standard');await theme('inline-a');await check('rgb(18, 52, 86)');
        if(combined) {
          await page.evaluate(()=>{location.hash='#lwp/a/b.html/second';});
          await page.locator('#second').waitFor();await settle();
          const ink=await page.locator('#second h2 strong').evaluate(node=>getComputedStyle(node).color);
          assert.equal(ink,'rgb(18, 52, 86)',`${name}: field styles survive combined-view replacement`);
        }
        assert.deepEqual(errors,[],`${name}: no browser errors`);await page.close();
      }
      console.log(`${name}: inline field styles passed`);
    } finally {await browser.close();}
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
