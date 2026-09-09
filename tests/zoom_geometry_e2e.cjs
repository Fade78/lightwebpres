// Exercise actual native, documentation and composed-kit builds, not mock frames.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = fs.mkdtempSync(path.join(root, 'work/tmp/zoom-geometry-'));
  const measureOnly = process.argv.includes('--measure');
  const env = { ...process.env, HOME: scratch, TMPDIR: path.join(root, 'work/tmp'),
    XDG_DATA_HOME: path.join(scratch, 'data'), XDG_CONFIG_HOME: path.join(scratch, 'config'),
    LWP_IDENTITY_KITS_DIR: path.join(scratch, 'kits'),
    LWP_THEMES_DIR: path.join(scratch, 'themes'), LWP_COMMONS_DIR: path.join(scratch, 'commons') };
  const cli = (...args) => execFileSync(process.env.PYTHON || 'python3',
    [path.join(root, 'lightwebpres'), ...args], { env, cwd: scratch, stdio: 'pipe' });
  fs.cpSync(path.join(root, 'examples/kits/lightwebpres-docs'),
    path.join(env.LWP_IDENTITY_KITS_DIR, 'lightwebpres-docs'), { recursive: true });
  cli('kit', 'compose', path.join(root, 'examples/kit-composition/recipe.json'),
    '--output', env.LWP_IDENTITY_KITS_DIR);
  let browser;
  try {
    browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  const records = [];
  try {
    for (const [name, preset] of [['native', 'builtin/standard'],
      ['docs', 'lightwebpres-docs@0.1.0/docs'], ['field', 'field-notes@1.0.0/brief']]) {
      const series = path.join(scratch, name);
      cli('init', series, '--preset', preset);
      fs.copyFileSync(path.join(root, 'examples/first-article/series.json'), path.join(series, 'series.json'));
      fs.copyFileSync(path.join(root, 'examples/first-article/sources/first-page.md'),
        path.join(series, 'sources/first-page.md'));
      cli('series', 'preset', 'set', series, '--preset', preset, '--use-preset-theme');
      cli('build', series, '--lang', 'en', '--scroll-duration', '0');
      for (const viewport of [{ width: 390, height: 844 }, { width: 1280, height: 720 }]) {
        const page = await browser.newPage({ viewport });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const settle = () => page.evaluate(() => new Promise(resolve =>
          requestAnimationFrame(() => requestAnimationFrame(resolve))));
        await page.goto(pathToFileURL(path.join(series, 'public/first-page.html')).href);
        await page.evaluate(() => document.fonts.ready);
        await settle();
        const geometry = () => page.$eval('#travels-with-the-page', slide => {
          const frame = slide.querySelector('.lwp-doc-frame, .field-sheet') || slide;
          const box = slide.querySelector('.fact-box');
          const font = slide.querySelector('h2');
          const properties = node => {
            const cs = getComputedStyle(node);
            return Object.fromEntries(['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
              'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth', 'minHeight']
              .map(key => [key, cs[key]]));
          };
          const range = document.createRange();
          range.selectNodeContents(font);
          return { slideWidth: slide.getBoundingClientRect().width,
            slideHeight: slide.getBoundingClientRect().height,
            frameWidth: frame.getBoundingClientRect().width, frame: properties(frame),
            slide: properties(slide), factWidth: box.getBoundingClientRect().width,
            fact: properties(box), font: parseFloat(getComputedStyle(font).fontSize),
            glyphHeight: range.getClientRects()[0].height,
            rootZoom: document.documentElement.style.zoom };
        });
        const baseline = await geometry();
        for (const factor of [.5, 1, 2]) {
          await page.keyboard.press('=');
          for (let n = 0; n < Math.round(Math.abs(factor - 1) * 10); n++) {
            await page.keyboard.press(factor < 1 ? '-' : 'Shift+=');
          }
          await settle();
          const actual = await geometry();
          records.push({ name, viewport, factor, ...actual });
          if (!measureOnly) {
            for (const key of ['slideWidth', 'frameWidth', 'factWidth']) {
              assert.ok(Math.abs(actual[key] - baseline[key]) < 1,
                `${name} ${viewport.width} ${factor} ${key}: ${actual[key]} != ${baseline[key]}`);
            }
            for (const key of ['frame', 'slide', 'fact']) assert.deepEqual(actual[key], baseline[key]);
            assert.ok(actual.slideHeight >= viewport.height - 1, JSON.stringify(actual));
            if (factor <= 1 && baseline.slideHeight <= viewport.height + 1) {
              assert.ok(Math.abs(actual.slideHeight - baseline.slideHeight) < 1);
            }
            assert.ok(Math.abs(actual.font - baseline.font * factor) < .01);
            assert.ok(Math.abs(actual.glyphHeight / baseline.glyphHeight - factor) < .08);
            assert.equal(actual.rootZoom, baseline.rootZoom);
          }
        }
        // Reset restores exact authored geometry and typography without accumulation.
        await page.keyboard.press('=');
        await settle();
        if (!measureOnly) assert.deepEqual(await geometry(), baseline);
        await page.goto(pathToFileURL(path.join(series, 'public/index.html')).href);
        await settle();
        const indexType = () => page.$eval('.article-title',
          el => ({ font: parseFloat(getComputedStyle(el).fontSize),
            width: el.closest('.article-card').getBoundingClientRect().width }));
        const indexBaseline = await indexType();
        for (let n = 0; n < 5; n++) await page.keyboard.press('-');
        await settle();
        if (!measureOnly) {
          const small = await indexType();
          assert.ok(Math.abs(small.font - indexBaseline.font * .5) < .01);
          assert.ok(Math.abs(small.width - indexBaseline.width) < 1);
        }
        assert.deepEqual(errors, []);
        await page.close();
      }
    }
    fs.writeFileSync(path.join(scratch, 'measurements.json'), JSON.stringify(records, null, 2));
    console.log(JSON.stringify({ scratch, records }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
