// Reads the reading measure of an index page and of an article page at a
// list of viewports, so a test can assert they are the same everywhere.
const { chromium } = require('playwright');
(async () => {
  const [indexUrl, articleUrl] = process.argv.slice(2);
  const b = await chromium.launch();
  const out = [];
  for (const width of [390, 600, 900, 1440, 1920, 2560, 3840]) {
    const p = await b.newPage({ viewport: { width, height: 900 } });
    await p.goto(indexUrl);
    const index = await p.evaluate(() => {
      const cs = getComputedStyle(document.body);
      return {
        left: Math.round(parseFloat(cs.paddingLeft)),
        top: Math.round(parseFloat(cs.paddingTop)),
        column: Math.round(document.body.clientWidth
          - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)),
      };
    });
    await p.goto(articleUrl);
    const article = await p.evaluate(() => {
      const s = document.querySelector('.slide');
      const cs = getComputedStyle(s);
      return {
        left: Math.round(parseFloat(cs.paddingLeft)),
        top: Math.round(parseFloat(cs.paddingTop)),
        column: Math.round(s.getBoundingClientRect().width
          - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)),
      };
    });
    out.push({ width, index, article });
    await p.close();
  }
  await b.close();
  process.stdout.write(JSON.stringify(out));
})();
