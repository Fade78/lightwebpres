// Test generated files as portable documents; never prototype a second runtime.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const work = path.resolve(process.argv[2]);
  assert(work.startsWith(path.join(root, 'work/tmp') + path.sep));
  // Keep Chromium's Unix-socket paths short while remaining repository-local.
  process.env.TMPDIR = path.join(root, 'work/tmp');
  let browser;
  try {
    const chromium = require('playwright').chromium;
    const executablePath = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(work, 'browser-cache');
    process.env.XDG_CONFIG_HOME = path.join(work, 'browser-config');
    browser = await chromium.launch({executablePath});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  try {
    const native = await browser.newContext({javaScriptEnabled: false, offline: true});
    const primary = await native.newPage();
    await primary.goto(pathToFileURL(path.join(work, 'multi/a.html')).href);
    assert.equal(await primary.locator('section.slide img').count(), 11);
    assert(await primary.locator('section.slide img').evaluateAll(images =>
      images.every(image => image.complete && image.naturalWidth > 0 && image.hasAttribute('src'))));
    await native.close();

    for (const viewport of [{width: 1280, height: 800}, {width: 390, height: 844}]) {
      const context = await browser.newContext({viewport, offline: true});
      const page = await context.newPage();
      const errors = [], requests = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => requests.push(request.url()));
      const url = pathToFileURL(path.join(work, 'copied/renamed.html')).href;
      await page.goto(url + '#lwp/a/a.html');
      const loaded = async count => {
        await page.waitForFunction(count => {
          const images = [...document.querySelectorAll('#lwp-series-view section.slide img')];
          return images.length === count && images.every(image => image.complete && image.naturalWidth > 0
            && image.src.startsWith('data:') && !image.hasAttribute('data-lwp-image'));
        }, count);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      };
      await loaded(11);
      const opaqueContexts = JSON.parse(fs.readFileSync(path.join(work, 'opaque-contexts.json'), 'utf8'));
      for (const [name, opening, closing] of opaqueContexts) {
        await page.evaluate(({name, opening, closing}) => {
          const pool = JSON.parse(document.getElementById('lwp-resource-data').textContent);
          const key = Object.keys(pool.images)[0];
          // Use the same inert document boundary as passive measurement. No widget is activated.
          const doc = document.implementation.createHTMLDocument('');
          doc.body.innerHTML = opening + '<img data-lwp-image="foreign-reference" alt="Foreign marker">' + closing
            + '<img data-eligible data-lwp-image="' + key + '">';
          const eligible = doc.querySelector('img[data-eligible]');
          const before = doc.body.innerHTML;
          lwpHydrateImages(doc.body);
          if (eligible.getAttribute('src') !== pool.images[key]) throw new Error(name + ': eligible image not hydrated');
          // Undo only the expected eligible mutation to compare all opaque markup byte-for-byte.
          eligible.removeAttribute('src');
          eligible.setAttribute('data-lwp-image', key);
          if (doc.body.innerHTML !== before) throw new Error(name + ': opaque markup changed');
          if (document.getElementById('lwp-resource-error')) throw new Error(name + ': false resource failure');
        }, {name, opening, closing});
      }
      const eligibleFailure = await page.evaluate(() => {
        const doc = document.implementation.createHTMLDocument('');
        doc.body.innerHTML = '<img data-lwp-image="missing-eligible">';
        try { lwpHydrateImages(doc.body); } catch (error) {
          const notice = document.getElementById('lwp-resource-error');
          const controlled = !!notice && notice.getAttribute('role') === 'alert' && !doc.images[0].hasAttribute('src');
          if (notice) notice.remove();
          return controlled;
        }
        return false;
      });
      assert(eligibleFailure, 'Missing eligible references must still fail visibly without a request');

      let unit = 'a';
      async function styles(selector, passive = false) {
        const actual = await page.evaluate(passive => {
          const docs = passive ? [...document.querySelectorAll('iframe[data-lwp-fit-measurement]')]
            .map(frame => frame.contentDocument) : [document];
          return docs.map(doc => {
            const view = doc.defaultView;
            return {background: view.getComputedStyle(doc.body).backgroundColor,
              foreground: view.getComputedStyle(doc.body).color,
              ink: view.getComputedStyle(doc.documentElement).getPropertyValue('--color-ink').trim().toLowerCase(),
              caption: view.getComputedStyle(doc.querySelector('section.slide figcaption')).color};
          });
        }, passive);
        assert(actual.length > 0, 'Expected a computed style sample');
        const owner = passive ? 'a' : unit; // While b is active, passive a and c share a's pooled CSS.
        for (const sample of actual) {
          assert.equal(sample.background, owner === 'b' ? 'rgb(221, 238, 255)' : 'rgb(255, 238, 221)');
          assert.equal(sample.foreground, owner === 'b' ? 'rgb(101, 67, 33)' : 'rgb(18, 52, 86)');
          assert.match(sample.ink, owner === 'b' ? /^#654321(?:ff)?$/ : /^#123456(?:ff)?$/);
          if (selector !== 'builtin/standard') {
            assert.equal(sample.caption, selector.endsWith('/compact') ? 'rgb(170, 34, 85)' : 'rgb(17, 102, 51)');
          }
        }
      }
      await styles('lightwebpres-docs@0.1.0/docs');
      async function preset(selector, count) {
        const identity = selector === 'builtin/standard' ? 'builtin' : 'lightwebpres-docs@0.1.0';
        await page.locator(`[data-identity="${identity}"]`).evaluate(node => node.click());
        await page.locator(`[data-presentation="${selector}"]`).evaluate(node => node.click());
        await loaded(count);
        await styles(selector);
      }
      await preset('builtin/standard', 8);
      await preset('lightwebpres-docs@0.1.0/compact', 11);
      await preset('lightwebpres-docs@0.1.0/docs', 11);
      const svg = await page.locator('img[alt="Left"], img[alt="Right"]').evaluateAll(images => images.map(image => {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 96;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(image, 0, 0, 128, 96);
        return {alt: image.alt, fragment: image.src.split('#')[1], color: [...ctx.getImageData(64, 48, 1, 1).data]};
      }));
      assert.deepEqual(svg.map(image => [image.alt, image.fragment]), [['Left', 'left'], ['Right', 'right']]);
      assert.deepEqual(svg.map(image => image.color), [[255, 0, 0, 255], [0, 0, 255, 255]]);
      await page.evaluate(() => { location.hash = '#lwp/a/b.html'; });
      await page.waitForFunction(() => document.title === 'Unit b');
      await loaded(11);
      unit = 'b';
      await styles('lightwebpres-docs@0.1.0/docs');
      async function option(key, value) {
        await page.locator(`select[data-reading-option="${key}"]`).evaluate((node, value) => {
          node.value = value; node.dispatchEvent(new Event('change'));
        }, value);
      }
      await option('text_fit', 'uniform');
      await option('fit_scope', 'series');
      await page.waitForFunction(() => {
        const frames = [...document.querySelectorAll('iframe[data-lwp-fit-measurement]')];
        return frames.length && frames.every(frame => frame.contentDocument.images.length === 11
          && [...frame.contentDocument.images].every(image => image.complete && image.naturalWidth > 0));
      });
      await styles('lightwebpres-docs@0.1.0/docs', true);
      await preset('lightwebpres-docs@0.1.0/compact', 11);
      await styles('lightwebpres-docs@0.1.0/compact', true);
      await preset('builtin/standard', 8);
      await page.waitForFunction(() => [...document.querySelectorAll('iframe[data-lwp-fit-measurement]')]
        .some(frame => frame.contentDocument.images.length === 8));
      await styles('builtin/standard', true);
      await preset('lightwebpres-docs@0.1.0/docs', 11);
      await page.waitForFunction(() => [...document.querySelectorAll('iframe[data-lwp-fit-measurement]')]
        .some(frame => frame.contentDocument.images.length === 11));
      await styles('lightwebpres-docs@0.1.0/docs', true);
      assert(await page.locator('iframe[data-lwp-fit-measurement]').evaluateAll(frames =>
        frames.every(frame => frame.getAttribute('sandbox') === 'allow-same-origin' && frame.contentDocument.scripts.length === 0)));
      await page.pdf({path: path.join(work, `resources-${viewport.width}.pdf`)});
      await loaded(11);
      await styles('lightwebpres-docs@0.1.0/docs');
      for (const name of ['c', 'a', 'b']) {
        await page.evaluate(name => { location.hash = '#lwp/a/' + name + '.html'; }, name);
        await page.waitForFunction(name => document.title === 'Unit ' + name, name);
        await loaded(11);
        unit = name;
        await styles('lightwebpres-docs@0.1.0/docs');
        await preset('lightwebpres-docs@0.1.0/compact', 11);
        await preset('lightwebpres-docs@0.1.0/docs', 11);
      }
      assert.deepEqual(errors, []);
      assert(requests.every(request => request.startsWith(url) || request.startsWith('data:')), requests.join('\n'));
      // A missing pool must produce a visible controlled failure, never a URL fetch.
      const broken = fs.readFileSync(path.join(work, 'copied/renamed.html'), 'utf8')
        .replace(/<script id="lwp-resource-data"[^>]*>.*?<\/script>\n/s, '');
      fs.writeFileSync(path.join(work, 'copied/broken.html'), broken);
      await page.goto(pathToFileURL(path.join(work, 'copied/broken.html')).href + '#lwp/a/a.html');
      await page.locator('#lwp-resource-error[role="alert"]').waitFor();
      assert.equal(await page.locator('img[src^="blob:"]').count(), 0);
      await context.close();
    }
    console.log('Resource factoring: opaque contexts, computed unit/preset CSS, primary no-JS, copied file offline, SVG, passive fit and print passed');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
