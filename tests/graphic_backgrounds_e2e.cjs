// Screenshot pixels verify paint order; rectangles alone cannot prove a background.
const assert=require('node:assert/strict');
let chromium,firefox;
try {({chromium,firefox}=require('playwright'));}
catch(error){console.error('Playwright unavailable in supplied environment');process.exit(77);}

(async()=>{
  for(const [name,engine] of [['chromium',chromium],['firefox',firefox]]) {
    const browser=await engine.launch({timeout:15000});
    try {
      const page=await browser.newPage({viewport:{width:1200,height:800}});
      await page.goto(process.argv[2]+'#cover');
      const settle=async()=>{
        await page.evaluate(()=>document.fonts.ready);
        await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      };
      for(const viewport of [{width:1200,height:800},{width:390,height:844}]) {
        await page.setViewportSize(viewport);await settle();
        await page.locator('#cover').scrollIntoViewIfNeeded();await settle();
        await page.waitForFunction(()=>{
          const host=document.querySelector('#cover .lwp-graphic-host');
          const image=host && host.shadowRoot.querySelector('.rotor > span');
          return image && image.shadowRoot.querySelector('img').complete;
        });
        await settle();
        const geometry=await page.locator('#cover').evaluate(slide=>{
          const nodes={};
          for(const host of slide.querySelectorAll('.lwp-graphic-host')) {
            for(const element of host.shadowRoot.querySelectorAll('.graphic')) {
              const rect=element.getBoundingClientRect();
              nodes[element.dataset.element]={left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom,
                width:rect.width,height:rect.height,plane:getComputedStyle(host).zIndex};
            }
          }
          const rect=slide.getBoundingClientRect();
          return {nodes,slide:{left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom,
            width:rect.width,height:rect.height},scroll:slide.scrollHeight,client:slide.clientHeight,
            documentWidth:document.documentElement.scrollWidth,viewport:innerWidth};
        });
        const {background,front}=geometry.nodes,slide=geometry.slide;
        assert.ok(background.left<=slide.left+1 && background.right>=slide.right-1);
        assert.ok(background.top<=slide.top+1 && background.bottom>=slide.bottom-1);
        assert.equal(background.plane,'-1');assert.equal(front.plane,'10');
        assert.ok(geometry.scroll<=geometry.client+1,`${name}: cover fit creates no native overflow`);
        assert.ok(geometry.documentWidth<=geometry.viewport+1,`${name}: clipped image creates no horizontal scrolling`);
        const screenshot=await page.screenshot({type:'png'});
        const colours=await page.evaluate(async({bytes,x,y})=>{
          const bitmap=await createImageBitmap(new Blob([new Uint8Array(bytes)],{type:'image/png'}));
          const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
          const context=canvas.getContext('2d');context.drawImage(bitmap,0,0);bitmap.close();
          const rgb=(px,py)=>Array.from(context.getImageData(Math.round(px),Math.round(py),1,1).data).slice(0,3);
          return {background:rgb(10,10),front:rgb(x,y),
            intercepted:!!document.elementFromPoint(x,y).closest('.lwp-graphic-host')};
        },{bytes:Array.from(screenshot),x:front.left+front.width/2,y:front.top+front.height/2});
        assert.deepEqual(colours.background,[219,239,255],`${name}: image paints above opaque cover fill`);
        assert.deepEqual(colours.front,[192,32,48],`${name}: foreground paints above native content`);
        assert.equal(colours.intercepted,false,`${name}: decorative image passes gestures through`);
      }
      await page.close();console.log(`${name}: graphic background/foreground pixels passed`);
    }finally{await browser.close();}
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
