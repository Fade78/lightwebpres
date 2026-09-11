// Real source builds: omitted series contents are not an invisible index view.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  process.env.TMPDIR = scratch;
  let browser;
  try {
    const {chromium} = require('playwright');
    const executablePath = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(scratch, 'xdg-cache');
    browser = await chromium.launch({executablePath});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  const work = fs.mkdtempSync(path.join(scratch, 'no-index-runtime-'));
  let server;
  try {
    const env = {...process.env, LWP_IDENTITY_KITS_DIR: path.join(root, 'examples/kits'),
      LWP_COMMONS_DIR: path.join(work, 'unused-commons'), LWP_THEMES_DIR: path.join(work, 'unused-themes')};
    function cli(...args) {
      const result = spawnSync(process.env.PYTHON || 'python3', [path.join(root, 'lightwebpres'), ...args],
        {env, cwd: root, encoding: 'utf8', timeout: 120000});
      assert.equal(result.status, 0, result.stdout + result.stderr);
    }
    server = http.createServer((request, response) => {
      const file = path.join(work, decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
      if (!file.startsWith(work + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        response.writeHead(404); response.end(); return;
      }
      response.setHeader('Content-Type', file.endsWith('.html') ? 'text/html; charset=utf-8' : 'image/svg+xml');
      response.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const route = (key, target = '') => '#lwp/a/' + key + '.html' + (target ? '/' + target : '');
    for (const count of [1, 2]) {
      const series = path.join(work, 'units-' + count);
      cli('init', series);
      if (count === 2) {
        const kit = 'lightwebpres-docs/0.1.0';
        const local = path.join(series, 'templates/kits', kit);
        fs.cpSync(path.join(root, 'examples/kits', kit), local, {recursive: true});
        const manifest = JSON.parse(fs.readFileSync(path.join(local, 'manifest.json'), 'utf8'));
        manifest.presets.compact = {...manifest.presets.docs, label: 'Compact'};
        fs.writeFileSync(path.join(local, 'manifest.json'), JSON.stringify(manifest));
      }
      fs.mkdirSync(path.join(series, 'sources/img'), {recursive: true});
      fs.writeFileSync(path.join(series, 'sources/img/mark.svg'),
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
        + '<rect width="40" height="40" fill="red"/>'.repeat(120) + '</svg>');
      fs.writeFileSync(path.join(series, 'series.json'), JSON.stringify({
        series_meta: {title: 'No contents', default_tag: 'default'},
        presentation_presets: count === 2
          ? ['lightwebpres-docs@0.1.0/docs', 'lightwebpres-docs@0.1.0/compact'] : ['builtin/standard'],
        articles: ['a', 'b'].slice(0, count).map(name => ({page_source: name + '.md', page_dest: name + '.html'})),
      }));
      for (const name of ['a', 'b'].slice(0, count)) {
        fs.writeFileSync(path.join(series, `sources/${name}.md`), `<!-- lwp:meta -->
page_title: Unit ${name}
${name === 'a' ? 'tags: technical' : ''}
style.page.bg: ${name === 'a' ? '#ffeedd' : '#ddeeff'}
${name === 'a' ? 'style.color.ink: #123456' : ''}
---
<!-- lwp:slide:cover -->
slug: intro
# Unit ${name}
summary: First visible unit ${name}.
---
<!-- lwp:slide -->
slug: detail
## Detail ${name}

![Mark](img/mark.svg)

${count === 2 ? `<a id="other" href="${name === 'a' ? 'b' : 'a'}.html#detail">Other unit</a>` : ''}
---
<!-- lwp:slide:full-article -->
slug: prose
article: prose-${name}.md
---
<!-- lwp:slide:series-nav -->
slug: collection
`);
        fs.writeFileSync(path.join(series, `sources/prose-${name}.md`), `# Supporting unit ${name}\n\nOnly prose ${name}.\n`);
      }
      fs.writeFileSync(path.join(series, 'templates/index_extra.html'), '<p>Unused index sentinel</p>');
      const options = ['--single-html', 'series.html', '--no-index', '--no-readme',
        '--unit-index', 'on', '--scroll-duration', '0', '--themes', 'print-ink,dracula'];
      // A single native view has no profitable inert pool; two preset-enabled
      // views exercise CSS and image references before home validation.
      if (count === 2) options.push('--inline-images');
      cli('build', series, '--lang', 'en', ...options);
      cli('verify', series, '--lang', 'en', ...options);
      const artifact = path.join(series, 'public/series.html');
      const html = fs.readFileSync(artifact, 'utf8');
      const payload = JSON.parse(html.match(/<script id="lwp-series-data"[^>]*>(.*?)<\/script>/s)[1]);
      assert.equal(payload.home, 'a.html');
      assert.deepEqual(payload.views.map(view => view.key), ['a.html', 'b.html'].slice(0, count));
      assert.equal(html.includes('id="lwp-resource-data"'), count === 2);
      if (count === 2) {
        const pool = JSON.parse(html.match(/<script id="lwp-resource-data"[^>]*>(.*?)<\/script>/s)[1]);
        assert(Object.keys(pool.css).length > 0);
        assert(Object.keys(pool.images).length > 0);
      }
      assert.equal(html.includes('Unused index sentinel'), false);
      for (const mobile of [false, true]) {
        const page = await browser.newPage(mobile
          ? {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}
          : {viewport: {width: 1100, height: 700}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        const base = `http://127.0.0.1:${server.address().port}/units-${count}/public/series.html`;
        await page.goto(base);
        await settle();
        assert.equal(await page.title(), 'Unit a');
        assert.equal(new URL(page.url()).hash, route('a'));
        assert.equal(await page.locator('body.index-page, #lwp-presentation-index').count(), 0);
        assert.equal(await page.locator('.slide-unit-index').count(), 1);
        assert.equal(await page.locator('[data-lwp-i18n="series_back_to_index"]').count(), 0);
        assert.equal(await page.locator('#menuHome .presenter-menu-label').textContent(), 'Start of series');
        assert.equal(await page.evaluate(() => localStorage.getItem('lwp-active-tag')), 'technical');
        assert.match(await page.locator('#lwp-series-view').textContent(), /Only prose a/);
        await page.evaluate(() => { window.originalRoot = document.documentElement; });
        if (count === 2) {
          await page.locator('#other').click();
          await settle();
          assert.equal(await page.title(), 'Unit b');
          assert.equal(new URL(page.url()).hash, route('b', 'detail'));
          await page.goBack(); await settle();
          assert.equal(await page.title(), 'Unit a');
          await page.goForward(); await settle();
          assert.equal(await page.title(), 'Unit b');
          await page.keyboard.press('Home'); await settle();
          assert.equal(new URL(page.url()).hash, route('b'));
          await page.keyboard.press('f');
          assert.equal(await page.evaluate(() => !!document.fullscreenElement), true);
          await page.keyboard.press('Control+Home'); await settle();
          assert.equal(await page.title(), 'Unit a');
          assert.equal(await page.evaluate(() => document.fullscreenElement === originalRoot), true);
          await page.evaluate(() => document.exitFullscreen());
          const sibling = page.locator('.series-list a[href="' + route('b') + '"]');
          assert.equal(await sibling.count(), 1, 'generated series navigation keeps the other unit reachable');
          await sibling.click(); await settle();
          assert.equal(await page.title(), 'Unit b');
          await page.goto(base + route('b')); await settle();
          assert.equal(await page.title(), 'Unit b');
          await page.goto(base + route('b', 'detail')); await settle();
          assert.equal(await page.title(), 'Unit b');
          assert.equal(await page.evaluate(() => document.activeElement.id), 'detail');
          await page.keyboard.press('m');
          await page.locator('#menuHome').click(); await settle();
          assert.equal(await page.title(), 'Unit a');
          await page.keyboard.press('c');
          await page.locator('[data-theme="dracula"]').click();
          assert.match(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--color-ink')), /#123456/i);
          await page.keyboard.press('c');
          await page.locator('[data-identity="lightwebpres-docs@0.1.0"]').click();
          await page.locator('[data-presentation="lightwebpres-docs@0.1.0/docs"]').click(); await settle();
          assert.equal(await page.locator('.lwp-presentation--lightwebpres-docs').count() > 0, true);
          assert.equal(await page.locator('[data-lwp-i18n="series_back_to_index"]').count(), 0);
          assert.match(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--page-bg')), /#ffeedd/i);
          await page.locator('#other').click(); await settle();
          assert.match(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--page-bg')), /#ddeeff/i);
          assert.equal(await page.locator('img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), true);
          await page.emulateMedia({media: 'print'});
          assert.doesNotMatch(await page.locator('#lwp-series-view').textContent(), /Only prose a/);
          assert.match(await page.locator('#lwp-series-view').textContent(), /Only prose b/);
          await page.emulateMedia({media: 'screen'});
          // Keep this stage's share coverage to URL semantics, not QR encoding.
          await page.evaluate(() => { window.copied = ''; navigator.clipboard.writeText = async text => { window.copied = text; }; });
          await page.keyboard.press('s');
          await page.locator('[data-action="copy"][data-scope="series"]').click();
          assert.equal(await page.evaluate(() => window.copied), base);
          await page.goto(pathToFileURL(artifact).href + route('b', 'detail')); await settle();
          assert.equal(await page.title(), 'Unit b');
          assert.equal(await page.locator('img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), true);
        } else {
          await page.keyboard.press('End');
          await page.keyboard.press('Control+Home'); await settle();
          assert.equal(new URL(page.url()).hash, route('a'));
        }
        await page.goto(base + '#lwp/index'); await settle();
        assert.equal(await page.title(), 'Unit a');
        assert.equal(new URL(page.url()).hash, route('a'));
        assert.equal(await page.locator('body.index-page, #lwp-presentation-index').count(), 0);
        assert.deepEqual(errors, []);
        await page.close();
      }
      if (count === 2) {
        // Equal unit sheets pool pageCss itself, not just preset structure CSS.
        // Bootstrap must resolve that reference before validating the home view.
        const second = path.join(series, 'sources/b.md');
        fs.writeFileSync(second, fs.readFileSync(second, 'utf8').replace(
          'style.page.bg: #ddeeff', 'style.page.bg: #ffeedd\nstyle.color.ink: #123456'));
      }
      cli('build', series, '--lang', 'fr', ...options);
      cli('verify', series, '--lang', 'fr', ...options);
      if (count === 2) {
        const pooled = JSON.parse(fs.readFileSync(artifact, 'utf8').match(
          /<script id="lwp-series-data"[^>]*>(.*?)<\/script>/s)[1]);
        assert.equal(typeof pooled.views[0].pageCss.lwpCss, 'string');
        assert.deepEqual(pooled.views[0].pageCss, pooled.views[1].pageCss);
      }
      const french = await browser.newPage();
      await french.goto(pathToFileURL(artifact).href);
      assert.equal(await french.title(), 'Unit a');
      assert.equal(await french.locator('#menuHome .presenter-menu-label').textContent(), 'D\u00e9but de la s\u00e9rie');
      if (count === 2) {
        await french.goto(pathToFileURL(artifact).href + route('b', 'detail'));
        assert.equal(await french.title(), 'Unit b');
        assert.match(await french.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--color-ink')), /#123456/i);
      }
      await french.close();
    }
    console.log('No-index runtime: one/multiple units, pooled/plain resources, desktop/mobile, routes/history, Home/menu/fullscreen, tags, presets/pins, print and series share URL passed.');
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    await browser.close();
    console.log('No-index fixtures: ' + path.relative(root, work));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
