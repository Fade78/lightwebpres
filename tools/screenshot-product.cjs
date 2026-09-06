// Build the tracked first article, then capture its real content card.
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
      const file = `generated/product-${view.name}.png`;
      await page.screenshot({ path: path.join(root, file) });
      manifest.captures.push({ ...view, deviceScaleFactor: 1, file, sha256: digest(file) });
      await page.close();
      console.log(`Captured ${file}: ${view.width}x${view.height}, complete card text`);
    }
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  } finally {
    if (browser) await browser.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
