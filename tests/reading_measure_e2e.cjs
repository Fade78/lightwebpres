// Reads the reading measure of an index page and of an article page at a
// list of viewports, so a test can assert they are the same everywhere.
const { chromium } = require('playwright');
(async () => {
  const [indexUrl, articleUrl] = process.argv.slice(2);
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const b = await chromium.launch(executablePath ? { executablePath } : {});
  const out = [];
  for (const width of [390, 600, 900, 1440, 1920, 2560, 3840]) {
    const p = await b.newPage({ viewport: { width, height: 900 } });
    await p.goto(indexUrl);
    const index = await p.evaluate(() => {
      const cs = getComputedStyle(document.body);
      // The TEXT's own gaps, not the container's padding. The padding was
      // symmetric all along; what is capped at `--page-content-max` is the
      // child, and a capped child that is not centred puts the whole
      // leftover on one side. That is the difference this measures.
      const t = document.querySelector('h1, h2, .article-title');
      const r = t ? t.getBoundingClientRect() : null;
      return {
        left: Math.round(parseFloat(cs.paddingLeft)),
        top: Math.round(parseFloat(cs.paddingTop)),
        column: Math.round(document.body.clientWidth
          - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)),
        textLeft: r ? Math.round(r.left) : null,
        textRight: r ? Math.round(innerWidth - r.right) : null,
      };
    });
    await p.goto(articleUrl);
    const article = await p.evaluate(() => {
      const s = document.querySelector('.slide');
      const cs = getComputedStyle(s);
      const t = s.querySelector('h1, h2');
      const r = t ? t.getBoundingClientRect() : null;
      return {
        left: Math.round(parseFloat(cs.paddingLeft)),
        top: Math.round(parseFloat(cs.paddingTop)),
        column: Math.round(s.getBoundingClientRect().width
          - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)),
        textLeft: r ? Math.round(r.left) : null,
        textRight: r ? Math.round(innerWidth - r.right) : null,
      };
    });
    out.push({ width, index, article });
    await p.close();
  }
  await b.close();
  process.stdout.write(JSON.stringify(out));
})();
