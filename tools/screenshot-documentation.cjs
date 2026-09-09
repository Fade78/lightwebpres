// Real example builds, with editorial labels outside the untouched screenshots.
// node tools/screenshot-documentation.cjs [--check]
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const manifestPath = path.join(root, 'generated/documentation-captures.json');
const viewport = { width: 1280, height: 720 };
const slideId = 'travels-with-the-page';
const outputs = [
  { file: 'generated/appearance-choices.png', width: 1600, height: 1440 },
  { file: 'generated/identity-composition.png', width: 1600, height: 1080 },
];
function sourceFiles(directory) {
  return fs.readdirSync(path.join(root, directory), { withFileTypes: true })
    .flatMap((entry) => entry.isDirectory() ? sourceFiles(`${directory}/${entry.name}`)
      : entry.name === 'README.md' ? [] : [`${directory}/${entry.name}`]);
}
const inputs = ['lightwebpres', 'tools/screenshot-documentation.cjs',
  ...sourceFiles('examples/first-article'),
  ...sourceFiles('examples/kits/lightwebpres-docs'),
  ...sourceFiles('examples/kit-composition')].sort();
const digest = (file) => createHash('sha256')
  .update(fs.readFileSync(path.join(root, file))).digest('hex');
const inputHashes = () => Object.fromEntries(inputs.map((file) => [file, digest(file)]));
function pngSize(file) {
  const data = fs.readFileSync(path.join(root, file));
  if (!data.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex')) ||
      data.toString('ascii', 12, 16) !== 'IHDR') throw new Error(`Not a PNG: ${file}`);
  return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) };
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length && (args.length !== 1 || args[0] !== '--check')) {
    throw new Error('Usage: node tools/screenshot-documentation.cjs [--check]');
  }
  if (args[0] === '--check') {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (JSON.stringify(manifest.inputs) !== JSON.stringify(inputHashes())) {
      throw new Error('Documentation captures are stale; run node tools/screenshot-documentation.cjs');
    }
    if (manifest.captures.length !== outputs.length) throw new Error('Missing capture records');
    for (const [index, expected] of outputs.entries()) {
      const capture = manifest.captures[index];
      const size = pngSize(expected.file);
      if (capture.file !== expected.file || capture.width !== expected.width ||
          capture.height !== expected.height || size.width !== expected.width ||
          size.height !== expected.height || digest(expected.file) !== capture.sha256) {
        throw new Error(`Changed capture or dimensions: ${expected.file}`);
      }
    }
    console.log('Documentation capture inputs, PNG dimensions and hashes match.');
    return;
  }

  const { chromium } = require('playwright');
  const scratch = path.join(root, 'work/tmp');
  fs.mkdirSync(scratch, { recursive: true });
  const tmp = fs.mkdtempSync(path.join(scratch, 'lwp-documentation-'));
  let browser;
  try {
    const env = Object.fromEntries(Object.entries(process.env)
      .filter(([key]) => !key.startsWith('LWP_')));
    Object.assign(env, {
      HOME: tmp, XDG_DATA_HOME: path.join(tmp, 'data'),
      XDG_CONFIG_HOME: path.join(tmp, 'config'), APPDATA: path.join(tmp, 'data'),
      LWP_IDENTITY_KITS_DIR: path.join(tmp, 'kits'),
      LWP_THEMES_DIR: path.join(tmp, 'themes'), LWP_COMMONS_DIR: path.join(tmp, 'commons'),
      LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8',
      TMPDIR: scratch,
    });
    const cli = (...command) => execFileSync(process.env.PYTHON || 'python3',
      [path.join(root, 'lightwebpres'), ...command], { cwd: tmp, env, stdio: 'pipe' });
    fs.cpSync(path.join(root, 'examples/kits/lightwebpres-docs'),
      path.join(env.LWP_IDENTITY_KITS_DIR, 'lightwebpres-docs'), { recursive: true });
    cli('kit', 'compose', path.join(root, 'examples/kit-composition/recipe.json'),
      '--output', env.LWP_IDENTITY_KITS_DIR);
    for (const name of ['frames', 'marks', 'ink']) {
      fs.cpSync(path.join(root, `examples/kit-composition/sources/field-${name}`),
        path.join(env.LWP_IDENTITY_KITS_DIR, `field-${name}`), { recursive: true });
    }
    browser = await chromium.launch(process.env.PW_CHROMIUM_PATH
      ? { executablePath: process.env.PW_CHROMIUM_PATH } : {});
    const manifest = { inputs: inputHashes(), browser: browser.version(),
      source: 'examples/first-article/sources/first-page.md', slide: slideId,
      viewport, deviceScaleFactor: 1, locale: 'en-US', pages: [], captures: [] };
    const frames = {};
    const selections = [
      ['native', 'builtin/standard'], ['official', 'lightwebpres-docs@0.1.0/docs'],
      ['composed', 'field-notes@1.0.0/brief'], ['frames', 'field-frames@1.0.0/sheet'],
      ['marks', 'field-marks@1.0.0/compass'],
      ['ink', 'field-ink@1.0.0/paper'],
    ];
    for (const [name, selector] of selections) {
      const series = path.join(tmp, name);
      cli('init', series, '--preset', selector);
      fs.copyFileSync(path.join(root, 'examples/first-article/series.json'),
        path.join(series, 'series.json'));
      fs.copyFileSync(path.join(root, manifest.source), path.join(series, 'sources/first-page.md'));
      cli('series', 'preset', 'set', series, '--preset', selector, '--use-preset-theme');
      cli('build', series, '--lang', 'en');
      cli('verify', series, '--lang', 'en');
      const page = await browser.newPage({ viewport, deviceScaleFactor: 1,
        locale: 'en-US', reducedMotion: 'reduce' });
      const errors = [];
      page.on('pageerror', (error) => errors.push(String(error)));
      page.on('console', (message) => {
        if (message.type() === 'error') errors.push(message.text());
      });
      page.on('requestfailed', (request) => errors.push(request.url()));
      page.on('response', (response) => {
        if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
      });
      await page.route(/^https?:/, (route) => {
        errors.push(`Unexpected network dependency: ${route.request().url()}`);
        return route.abort();
      });
      await page.goto(`${pathToFileURL(path.join(series, 'public/first-page.html')).href}#${slideId}`,
        { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(3600);
      const measured = await page.locator(`#${slideId}`).evaluate((slide) => {
        const failures = [];
        const text = [];
        let textRects = 0;
        const walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
          const node = walker.currentNode;
          if (!node.textContent.trim() || !node.parentElement.checkVisibility()) continue;
          // The compass name is deliberately screen-reader-only in the real kit.
          if (getComputedStyle(node.parentElement).clipPath === 'inset(50%)') continue;
          text.push(node.textContent.trim());
          const range = document.createRange();
          range.selectNodeContents(node);
          for (const r of range.getClientRects()) {
            textRects++;
            if (r.left < -1 || r.top < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1) {
              failures.push(`Outside viewport: ${node.textContent.trim()}`);
            }
            for (let ancestor = node.parentElement; ancestor; ancestor = ancestor.parentElement) {
              const style = getComputedStyle(ancestor);
              const a = ancestor.getBoundingClientRect();
              if ((/(hidden|clip|auto|scroll)/.test(style.overflowX) &&
                   (r.left < a.left - 1 || r.right > a.right + 1)) ||
                  (/(hidden|clip|auto|scroll)/.test(style.overflowY) &&
                   (r.top < a.top - 1 || r.bottom > a.bottom + 1))) {
                failures.push(`Clipped by ${ancestor.className}: ${node.textContent.trim()}`);
              }
            }
          }
        }
        const images = [...slide.querySelectorAll('img')].filter((img) => img.checkVisibility());
        for (const image of images) {
          const r = image.getBoundingClientRect();
          if (!image.complete || !image.naturalWidth || r.width < 1 || r.height < 1 ||
              r.left < 0 || r.top < 0 || r.right > innerWidth || r.bottom > innerHeight) {
            failures.push(`Missing or clipped image: ${image.src}`);
          }
        }
        if (document.documentElement.scrollWidth > innerWidth) failures.push('Horizontal overflow');
        return { failures, text: text.join(' '), textRects, visibleImages: images.length,
          headingFont: getComputedStyle(slide.querySelector('h1, h2')).fontFamily };
      });
      for (const expected of ['The runtime travels with the page', '1 HTML', 'Keep the assets too',
        'Local images stay beside the page', 'directory, not just its index.']) {
        if (!measured.text.includes(expected)) measured.failures.push(`Missing text: ${expected}`);
      }
      if (['official', 'composed'].includes(name) && !measured.visibleImages) {
        measured.failures.push('Missing identity mark');
      }
      if (errors.length || measured.failures.length) {
        throw new Error(`${name}: ${[...errors, ...measured.failures].join('\n')}`);
      }
      frames[name] = (await page.screenshot()).toString('base64');
      manifest.pages.push({ name, selector, ...measured });
      await page.close();
      console.log(`Captured ${name}: ${viewport.width}x${viewport.height}, complete content and marks`);
    }

    const compass = 'examples/kit-composition/sources/field-marks/1.0.0/assets/compass.svg';
    manifest.assetPreviews = [compass];
    const image = (name) => name === 'marks'
      ? `<img class="compass" src="data:image/svg+xml;base64,${fs.readFileSync(path.join(root, compass)).toString('base64')}" alt="">`
      : `<img src="data:image/png;base64,${frames[name]}" alt="">`;
    const common = `* { box-sizing: border-box; } html, body { margin: 0; }
      body { background: #f3f1eb; color: #202e35; font-family: Arial, sans-serif; }
      h1, h2, p, figure { margin: 0; } h1 { font-size: 52px; letter-spacing: -1.5px; }
      h2 { font-size: 44px; letter-spacing: -1px; } p { font-size: 28px; line-height: 1.4; }
      .eyebrow { font-size: 25px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; }
      .muted { color: #52616a; } img { display: block; width: 100%; height: auto; }
      code { font: 23px monospace; }`;
    const appearance = `<header><p class="eyebrow">One article / three identities</p>
      <h1>Same words. Different presence.</h1></header>
      <main>${[
        ['native', '01', 'LightWebPres', 'Light theme', 'Native layouts. Nothing to install.', 'builtin/standard'],
        ['official', '02', 'Official Docs', 'Blue documentation kit', 'Branded rail, logo and footer.', 'lightwebpres-docs@0.1.0/docs'],
        ['composed', '03', 'Field Notes', 'Composed paper identity', 'Ruled frame. Compass. Typewriter type.', 'field-notes@1.0.0/brief'],
      ].map(([name, number, title, theme, description, selector]) => `<section>
        <div class="label"><p class="eyebrow muted">${number} / ${theme}</p><h2>${title}</h2>
        <p>${description}</p><code>${selector}</code></div><figure>${image(name)}</figure>
        </section>`).join('')}</main>
      <footer>Real builds of first-page.md &nbsp; / &nbsp; Same ${viewport.width} x ${viewport.height} viewport</footer>`;
    const appearanceCSS = `header { padding: 36px 48px 24px; height: 150px; }
      header .eyebrow { margin-bottom: 10px; } main { padding: 0 48px; }
      section { display: grid; grid-template-columns: 1fr 736px; gap: 32px;
        align-items: center; height: 413px; border-top: 1px solid #c7cecd; }
      section figure { border: 1px solid #c7cecd; } .label h2 { margin: 16px 0 12px; }
      .label code { display: block; margin-top: 24px; color: #52616a; }
      footer { margin: 15px 48px 0; font-size: 24px; color: #52616a; }`;
    const composition = `<header><p class="eyebrow">Sources / assembly / result</p>
      <h1>Compose an identity. Keep it self-contained.</h1>
      <p class="muted">Three source kits supply selected files to one independent kit.</p></header>
      <main><div class="sources"><p class="eyebrow muted">Source resources</p>
      ${[['frames', 'Frames', 'Layout + structure CSS'],
        ['marks', 'Marks', 'Chrome + compass SVG'],
        ['ink', 'Ink', 'Paper theme + typography']].map(([name, title, role]) =>
        `<section><figure class="${name}">${image(name)}</figure><h2>${title}</h2><p>${role}</p></section>`).join('')}
      </div><div class="assembly"><span>Selected<br>files</span><b>&rarr;</b><code>recipe.json</code></div>
      <div class="result"><p class="eyebrow">Result / Field Notes</p><figure>${image('composed')}</figure>
      <h2>One kit. No source dependencies.</h2><code>field-notes@1.0.0/brief</code>
      <p class="muted">Same article, built with the composed preset.<br>The source kits need not ship with it.</p></div></main>
      <footer>Assembly diagram + untouched browser captures &nbsp; / &nbsp; No mock interface</footer>`;
    const compositionCSS = `header { padding: 38px 48px 0; } header h1 { margin: 12px 0; }
      main { display: grid; grid-template-columns: 360px 170px minmax(0, 1fr); gap: 20px;
        align-items: center; padding: 30px 48px 0; }
      .sources>.eyebrow { font-size: 22px; margin-bottom: 12px; }
      .sources section { margin-bottom: 18px; }
      .sources figure { width: 256px; border: 1px solid #b8c1c2; }
      .sources figure.marks { height: 144px; display: grid; place-items: center; background: #fff; }
      .sources img.compass { width: 112px; height: 112px; }
      .sources h2 { font-size: 28px; margin-top: 6px; letter-spacing: 0; }
      .sources section p { font-size: 23px; }
      .assembly { text-align: center; color: #52616a; font-size: 27px; }
      .assembly b { display: block; font-size: 72px; font-weight: normal; }
      .assembly code { font-size: 21px; } .result>.eyebrow { margin-bottom: 18px; }
      .result figure { border: 1px solid #b8c1c2; }
      .result h2 { margin: 26px 0 14px; font-size: 36px; }
      .result>p.muted { margin-top: 20px; font-size: 26px; }
      footer { margin: 8px 48px 0; font-size: 24px; color: #52616a; }`;
    for (const [index, output] of outputs.entries()) {
      const page = await browser.newPage({ viewport: { width: output.width, height: output.height },
        deviceScaleFactor: 1, locale: 'en-US', reducedMotion: 'reduce' });
      await page.setContent(`<!doctype html><html lang="en"><head><meta charset="utf-8">
        <style>${common}${index ? compositionCSS : appearanceCSS}</style></head>
        <body>${index ? composition : appearance}</body></html>`);
      await page.evaluate(() => Promise.all([...document.images].map((img) => img.decode())));
      const size = await page.evaluate(() => ({ width: document.documentElement.scrollWidth,
        height: document.documentElement.scrollHeight }));
      if (size.width > output.width || size.height > output.height) {
        throw new Error(`Montage overflow: ${output.file}: ${JSON.stringify(size)}`);
      }
      await page.screenshot({ path: path.join(root, output.file) });
      manifest.captures.push({ ...output, sha256: digest(output.file) });
      await page.close();
      console.log(`Wrote ${output.file}: ${output.width}x${output.height}`);
    }
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  } finally {
    if (browser) await browser.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
