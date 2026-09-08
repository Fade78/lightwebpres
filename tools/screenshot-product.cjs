// Build the tracked first article, capture its real content card in two
// viewports, then compose the captures into one comparison illustration.
// node tools/screenshot-product.cjs [--check]
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
function sourceFiles(directory) {
  return fs.readdirSync(path.join(root, directory), { withFileTypes: true })
    .flatMap((entry) => entry.isDirectory()
      ? sourceFiles(`${directory}/${entry.name}`) : [`${directory}/${entry.name}`]);
}
const inputs = [
  'lightwebpres', 'tools/screenshot-product.cjs',
  'examples/first-article/series.json',
  ...sourceFiles('examples/first-article/sources').sort(),
  ...sourceFiles('examples/first-article/templates').sort(),
];
const views = [
  { name: 'landscape', width: 960, height: 540, isMobile: false, hasTouch: false },
  { name: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true },
];
const MONTAGE = { width: 1280, height: 760 };
const OUTPUT = 'generated/product-responsive.png';
const digest = (name) => createHash('sha256')
  .update(fs.readFileSync(path.join(root, name))).digest('hex');
const inputHashes = () => Object.fromEntries(inputs.map((name) => [name, digest(name)]));
const manifestPath = path.join(root, 'generated/product-captures.json');

async function main() {
  const args = process.argv.slice(2);
  if (args.length && (args.length !== 1 || args[0] !== '--check')) {
    throw new Error('Usage: node tools/screenshot-product.cjs [--check]');
  }
  if (args[0] === '--check') {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (JSON.stringify(manifest.inputs) !== JSON.stringify(inputHashes())) {
      throw new Error('Product captures are stale; run node tools/screenshot-product.cjs');
    }
    for (const capture of manifest.captures) {
      if (digest(capture.file) !== capture.sha256) throw new Error(`Changed ${capture.file}`);
    }
    console.log('Product capture inputs and PNG hashes match.');
    return;
  }

  const { chromium } = require('playwright');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'lwp-product-'));
  let browser;
  try {
    const series = path.join(tmp, 'series');
    fs.cpSync(path.join(root, 'examples/first-article'), series, { recursive: true });
    // External catalogues must not change a documented built-in theme.
    const env = { ...process.env };
    for (const key of Object.keys(env)) if (key.startsWith('LWP_')) delete env[key];
    env.LWP_THEMES_DIR = path.join(tmp, 'no-user-themes');
    execFileSync(process.env.PYTHON || 'python3', [
      path.join(root, 'lightwebpres'), 'build', series, '--lang', 'en',
    ], { env, stdio: 'pipe' });
    browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
    const manifest = { inputs: inputHashes(), browser: browser.version(), captures: [] };
    const url = pathToFileURL(path.join(series, 'public/first-page.html')).href;
    const frames = [];
    for (const view of views) {
      const page = await browser.newPage({
        viewport: { width: view.width, height: view.height },
        deviceScaleFactor: 1, isMobile: view.isMobile, hasTouch: view.hasTouch,
        locale: 'en-US', reducedMotion: 'reduce',
      });
      const errors = [];
      page.on('pageerror', (error) => errors.push(String(error)));
      page.on('requestfailed', (request) => errors.push(request.url()));
      await page.goto(`${url}#travels-with-the-page`, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      // Let the real navigation settle and its ordinary idle chrome fade.
      await page.waitForTimeout(3600);
      const bounds = await page.locator('#travels-with-the-page').evaluate((slide) => {
        const rects = [];
        const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          const node = walker.currentNode;
          if (!node.textContent.trim() || !node.parentElement.checkVisibility()) continue;
          const range = document.createRange();
          range.selectNodeContents(node);
          for (const r of range.getClientRects()) {
            rects.push({ left: r.left, top: r.top, right: r.right, bottom: r.bottom });
          }
        }
        return {
          text: slide.innerText, rects,
          width: window.innerWidth, height: window.innerHeight,
          overflow: document.documentElement.scrollWidth > window.innerWidth,
        };
      });
      if (errors.length) throw new Error(errors.join('\n'));
      if (!bounds.text.includes('The runtime travels with the page') || !bounds.rects.length) {
        throw new Error(`${view.name}: missing content card`);
      }
      if (bounds.width !== view.width || bounds.height !== view.height || bounds.overflow) {
        throw new Error(`${view.name}: unexpected viewport or horizontal overflow`);
      }
      if (bounds.rects.some((r) => r.left < -1 || r.top < -1 ||
          r.right > view.width + 1 || r.bottom > view.height + 1)) {
        throw new Error(`${view.name}: card text is cut off: ${JSON.stringify(bounds.rects)}`);
      }
      frames.push({ ...view, deviceScaleFactor: 1,
        data: (await page.screenshot()).toString('base64') });
      await page.close();
      console.log(`Captured ${view.name}: ${view.width}x${view.height}, complete card text`);
    }
    const landscape = frames.find((frame) => frame.name === 'landscape');
    const mobile = frames.find((frame) => frame.name === 'mobile');
    const montage = await browser.newPage({
      viewport: MONTAGE, deviceScaleFactor: 1, locale: 'en-US', reducedMotion: 'reduce',
    });
    await montage.setContent(`<!doctype html>
      <html><head><meta charset="utf-8"><style>
        :root { color-scheme: light; }
        * { box-sizing: border-box; }
        html, body { margin: 0; width: 1280px; height: 760px; }
        body { background: #F5F1FA; color: #241A35;
          font-family: ui-sans-serif, system-ui, sans-serif; }
        main { padding: 34px 48px 28px; }
        h1 { margin: 0 0 6px; font-size: 25px; line-height: 1.15;
          letter-spacing: -0.02em; }
        .subtitle { margin: 0 0 24px; color: #625870; font-size: 15px; }
        .row { display: flex; align-items: flex-start; gap: 32px; }
        figure { margin: 0; }
        figcaption { margin: 0 0 9px; color: #625870; font-size: 13px;
          font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
        img { display: block; background: #fff; border: 1px solid #D7CEE4;
          border-radius: 8px; box-shadow: 0 8px 24px #241A351F; }
        .landscape img, .mobile img { width: auto; height: 500px; }
        .footer { margin: 22px 0 0; color: #625870; font-size: 13px; }
      </style></head><body><main>
        <h1>One page, two uses</h1>
        <p class="subtitle">The same LightWebPres content card in the Nebula theme</p>
        <div class="row">
          <figure class="landscape">
            <figcaption>Landscape · 960 × 540 CSS pixels</figcaption>
            <img src="data:image/png;base64,${landscape.data}" alt="">
          </figure>
          <figure class="mobile">
            <figcaption>Portrait · 390 × 844 CSS pixels</figcaption>
            <img src="data:image/png;base64,${mobile.data}" alt="">
          </figure>
        </div>
        <p class="footer">Same source · same page · real Chromium viewports, not device photographs</p>
      </main></body></html>`);
    await montage.evaluate(() => Promise.all(
      [...document.images].map((image) => image.decode())));
    await montage.screenshot({ path: path.join(root, OUTPUT) });
    await montage.close();
    manifest.captures.push({
      name: 'responsive', width: MONTAGE.width, height: MONTAGE.height,
      file: OUTPUT, viewports: frames.map(({ data, ...view }) => view),
      sha256: digest(OUTPUT),
    });
    console.log(`Wrote ${OUTPUT}: ${MONTAGE.width}x${MONTAGE.height}, two real viewports`);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  } finally {
    if (browser) await browser.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
