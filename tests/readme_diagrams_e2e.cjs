// The README embeds real SVGs through picture, not browser-only diagram code.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
let chromium;
try { ({ chromium } = require('playwright')); }
catch (error) { console.error(error.message); process.exit(77); }

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  fs.mkdirSync(scratch, { recursive: true });
  const captures = fs.mkdtempSync(path.join(scratch, 'readme-diagrams-'));
  const pictures = fs.readFileSync(path.join(root, 'README.md'), 'utf8')
    .match(/<picture>[\s\S]*?<\/picture>/g) || [];
  assert.equal(pictures.length, 2);
  console.log(`Diagram captures: ${captures}`);
  const browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
    ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
  try {
    for (const width of [390, 832]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      page.on('requestfailed', request => errors.push(request.url()));
      for (const [index, scene] of ['authoring-workflow', 'publishing-roles'].entries()) {
        // Keep the README's actual media query, sources and fallback intact.
        const preview = path.join(captures, `${width}-${scene}.html`);
        fs.writeFileSync(preview, `<!doctype html><html lang="en"><head>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <base href="${pathToFileURL(root + path.sep).href}">
          <style>body{margin:0;padding:16px;background:white}img{display:block;width:100%;height:auto}</style>
          </head><body>${pictures[index]}</body></html>`);
        await page.goto(pathToFileURL(preview).href);
        const image = page.locator('img');
        await image.evaluate(async node => { await node.decode(); });
        const expected = `${scene}${width <= 600 ? '-mobile' : ''}.svg`;
        assert((await image.evaluate(node => node.currentSrc)).endsWith(expected));
        assert((await image.getAttribute('alt')).length > 100);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        await page.screenshot({ path: path.join(captures, `${width}-${scene}-embedded.png`), fullPage: true });

        // Measure the SVG text itself; checking the enclosing image cannot find
        // text that spills outside a node box or the SVG viewBox.
        await page.goto(pathToFileURL(path.join(root, 'generated', expected)).href);
        await page.evaluate(() => document.fonts.ready);
        const violations = await page.evaluate(() => {
          const svg = document.documentElement;
          const view = svg.viewBox.baseVal;
          const bad = [];
          for (const text of svg.querySelectorAll('text')) {
            const box = text.getBBox();
            const owner = text.closest('[data-node]');
            const frame = owner && owner.querySelector('rect').getBBox();
            const bounds = frame || view;
            if (box.x < bounds.x || box.y < bounds.y ||
                box.x + box.width > bounds.x + bounds.width ||
                box.y + box.height > bounds.y + bounds.height) {
              bad.push({ text: text.textContent, owner: owner && owner.id,
                box: { x: box.x, y: box.y, width: box.width, height: box.height },
                bounds: { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height } });
            }
          }
          return bad;
        });
        assert.deepEqual(violations, [], `${expected}: text must remain inside its own node`);
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
