// Passive single-document fitting: no authored widget is activated to measure it.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  process.env.TMPDIR = scratch;
  let chromium, browser;
  try {
    chromium = require('playwright').chromium;
    process.env.PW_CHROMIUM_PATH = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(scratch, 'measurement-xdg-cache');
    browser = await chromium.launch({executablePath: process.env.PW_CHROMIUM_PATH});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  const work = fs.mkdtempSync(path.join(scratch, 'single-document-passive-'));
  try {
    const series = path.join(work, 'series');
    function cli(...args) {
      const result = spawnSync(process.env.PYTHON || 'python3', [path.join(root, 'lightwebpres'), ...args],
        {env: process.env, cwd: root, encoding: 'utf8', timeout: 120000});
      assert.equal(result.status, 0, result.stdout + result.stderr);
    }
    cli('init', series);
    const widgets = [
      '<iframe srcdoc="<script>parent.inactiveRuns++</script><img src=\'https://widget.invalid/srcdoc\'>"></iframe>',
      '<iframe src="https://widget.invalid/frame"></iframe>',
      '<object data="https://widget.invalid/object" type="text/html"></object>',
      '<embed src="https://widget.invalid/embed">',
      '<video autoplay src="https://widget.invalid/video"></video>',
      '<audio autoplay src="https://widget.invalid/audio"></audio>',
      '<fit-unseen-widget></fit-unseen-widget>',
      '<img src="https://widget.invalid/event" onload="window.inactiveRuns++" onerror="window.inactiveRuns++">',
      '<script>window.inactiveRuns++</script>',
      '<button is="fit-unseen-button">Custom button</button>',
    ];
    const names = ['sparse', 'dense', 'delayed'].concat(widgets.map((_, i) => 'bad' + i));
    fs.writeFileSync(path.join(series, 'series.json'), JSON.stringify({
      series_meta: {title: 'Passive measurement', reading: {text_fit: 'uniform'}},
      articles: names.map(name => ({page_source: name + '.md', page_dest: name + '.html'})),
    }));
    function source(name, tags, body) {
      fs.writeFileSync(path.join(series, 'sources', name + '.md'), `<!-- lwp:meta -->
page_title: ${name}
${tags ? 'tags: ' + tags : ''}
---
<!-- lwp:slide -->
slug: intro
## ${name}

${body}
`);
    }
    source('sparse', '', 'Short text. <a id="active-link" href="#intro">Active link</a>');
    // The earlier dense view hits the floor. Unsupported later views must
    // still be checked, not skipped by a numeric early-out.
    source('dense', widgets.map((_, i) => 'bad' + i).join(' '), 'Dense text. '.repeat(400));
    widgets.forEach((widget, i) => source('bad' + i, 'bad' + i, widget));
    source('delayed', 'images', `<p id="menuFitScope" style="font-size:30px;line-height:36px">One<br>Two<br>Three<br>Four</p>

<img alt="Delayed static SVG" src="https://measurement.invalid/late.svg">
`);
    cli('build', series, '--lang', 'en', '--scroll-duration', '0', '--single-page', 'series.html');
    const page = await browser.newPage({viewport: {width: 1100, height: 700}});
    const errors = [], widgetRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {
      if (request.url().includes('widget.invalid')) widgetRequests.push(request.url());
    });
    await page.context().setOffline(true);
    let releaseImage, imageRequested = false, imageReleased = false;
    const imageBody = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="420"><rect width="300" height="420" fill="navy"/></svg>';
    await page.route(/^https?:/, async route => {
      if (route.request().url() !== 'https://measurement.invalid/late.svg') return route.abort();
      imageRequested = true;
      if (!imageReleased) await new Promise(resolve => { releaseImage = resolve; });
      await route.fulfill({contentType: 'image/svg+xml', body: imageBody});
    });
    await page.addInitScript(() => {
      window.inactiveRuns = 0;
      customElements.define('fit-unseen-widget', class extends HTMLElement {
        constructor() { super(); window.inactiveRuns++; }
        connectedCallback() { window.inactiveRuns++; }
      });
      customElements.define('fit-unseen-button', class extends HTMLButtonElement {
        constructor() { super(); window.inactiveRuns++; }
      }, {extends: 'button'});
    });
    await page.goto(pathToFileURL(path.join(series, 'public/series.html')).href + '#lwp/a/sparse.html');
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const scope = async value => {
      await page.locator('select[data-reading-option="fit_scope"]').evaluate((node, value) => {
        node.value = value; node.dispatchEvent(new Event('change'));
      }, value);
      await settle();
    };
    const tag = async value => {
      await page.locator(`[data-tag="${value}"]`).evaluate(node => node.click());
      await settle();
    };
    await settle();
    await page.evaluate(() => { window.originalIntro = document.getElementById('intro'); });
    for (let i = 0; i < widgets.length; i++) {
      await tag('bad' + i);
      await scope('series');
      assert.equal(await page.locator('#menuFitScope').inputValue(), 'article', 'explicit refusal of widget ' + i);
      assert.match(await page.locator('#menuFitScopeStatus').textContent(), /Entire-series fit is unavailable: "bad\d+".*Using current-article fit/);
      assert.equal(await page.locator('#menuFitScopeStatus').getAttribute('role'), 'status');
      assert.equal(await page.locator('#menuFitScope').getAttribute('aria-describedby'), 'menuFitScopeStatus');
      assert.equal(await page.locator('#intro').getAttribute('data-lwp-text-scale'), '1', 'refusal never silently applies a partial-series factor');
      assert.equal(await page.evaluate(() => document.getElementById('intro') === originalIntro && window.inactiveRuns === 0), true);
      assert.equal(await page.locator('[data-lwp-fit-measurement]').count(), 0, 'preflight happens before creating measurement documents');
    }
    assert.deepEqual(widgetRequests, [], 'inactive widgets must not even request a subresource');
    await tag('images');
    await scope('series');
    assert.equal(await page.locator('#menuFitScope').inputValue(), 'series');
    assert.equal(await page.locator('#menuFitScopeStatus').textContent(), '');
    assert.equal(await page.locator('#intro').getAttribute('data-lwp-text-scale'), '1');
    for (let i = 0; !imageRequested && i < 100; i++) await page.waitForTimeout(10);
    assert.equal(imageRequested, true, 'a passive image is allowed to load its intrinsic size');
    assert.equal(await page.locator('#menuFitScope').count(), 1, 'snapshot IDs cannot collide with active controls');
    const surface = page.locator('[data-lwp-fit-measurement]');
    assert.equal(await surface.getAttribute('sandbox'), 'allow-same-origin');
    assert.equal(await surface.getAttribute('aria-hidden'), 'true');
    assert.equal(await surface.evaluate(node => node.inert), true);
    assert.deepEqual(await surface.evaluate(node => ({
      width: node.contentDocument.documentElement.clientWidth,
      height: node.contentDocument.documentElement.clientHeight,
      mode: node.contentDocument.compatMode,
      scripts: node.contentDocument.scripts.length,
      runtime: typeof node.contentWindow.qrEncode,
    })), {width: 1100, height: 700, mode: 'CSS1Compat', scripts: 0, runtime: 'undefined'});
    imageReleased = true;
    releaseImage();
    await page.waitForFunction(() => Number(document.getElementById('intro').getAttribute('data-lwp-text-scale')) < 1);
    await settle();
    const factor = await page.locator('#intro').getAttribute('data-lwp-text-scale');
    assert(Number(factor) >= .75 && Number(factor) < 1, 'intrinsic image dimensions invalidate the prior factor');
    await page.evaluate(() => { location.hash = '#lwp/a/delayed.html'; });
    await settle();
    await page.waitForFunction(() => document.querySelector('#lwp-series-view img').naturalWidth === 300);
    await scope('article');
    assert.equal(await page.locator('#intro').getAttribute('data-lwp-text-scale'), factor,
      'the passive image measurement equals the real mounted article, not an estimate');
    assert.deepEqual(widgetRequests, []);
    assert.deepEqual(errors, []);
    console.log('Passive measurement: all widget preflights refused without execution/requests; isolated IDs, sandbox, delayed SVG dimensions and mounted-factor equality passed.');
  } finally {
    await browser.close();
    console.log('Passive probe fixtures: ' + path.relative(root, work));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
