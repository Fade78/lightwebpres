// Real publication: no blank navigation slide, dangling Home or sharing URL.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
let chromium, firefox;
try { ({chromium, firefox} = require('playwright')); }
catch (error) { console.error('Playwright unavailable in supplied environment'); process.exit(77); }

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  const work = fs.mkdtempSync(path.join(scratch, 'output-defaults-browser-'));
  const env = {...process.env, TMPDIR: scratch,
    LWP_IDENTITY_KITS_DIR: path.join(work, 'unused-kits'),
    LWP_THEMES_DIR: path.join(work, 'unused-themes'),
    LWP_COMMONS_DIR: path.join(work, 'unused-commons')};
  let server;
  try {
    const cases = [];
    for (const [name, count, index, nav, flags] of [
      ['single', 1, false, false, []], ['several', 2, true, true, []],
      ['forced', 1, true, true, ['--make-index', '--make-nav']],
      ['nav-only', 1, false, true, ['--make-nav']],
      ['no-index', 2, false, true, ['--no-index']],
    ]) {
      const series = path.join(work, name);
      fs.mkdirSync(path.join(series, 'sources'), {recursive: true});
      const articles = ['a', 'b'].slice(0, count).map(unit => ({
        page_source: unit + '.md', page_dest: unit === 'a' ? 'a #%.html' : 'b.html',
      }));
      fs.writeFileSync(path.join(series, 'series.json'), JSON.stringify({
        series_meta: {title: 'A collection', scroll_duration: 0}, articles,
      }));
      for (const unit of ['a', 'b'].slice(0, count)) {
        fs.writeFileSync(path.join(series, 'sources', unit + '.md'), `<!-- lwp:meta -->
page_title: Unit ${unit}
---
<!-- lwp:slide:cover -->
slug: intro
# Unit ${unit}
---
<!-- lwp:slide:series-nav -->
slug: collection
---
<!-- lwp:slide -->
slug: detail
## Detail ${unit}

Body.
`);
      }
      for (const combined of [false, true]) {
        const output = combined ? 'combined' : 'public';
        const options = ['--output', path.join(series, output), '--lang', 'en',
          '--unit-index', 'on', '--slides-page-numbers', 'on', ...flags,
          ...(combined ? ['--single-html', 'series.html'] : [])];
        for (const command of ['build', 'verify']) {
          const result = spawnSync(process.env.PYTHON || 'python3',
            [path.join(root, 'lightwebpres'), command, series, ...options],
            {cwd: root, env, encoding: 'utf8', timeout: 30000});
          assert.equal(result.status, 0, result.stdout + result.stderr);
        }
        cases.push({name, index, nav, combined,
          relative: name + '/' + output + '/' + (combined ? 'series.html' : 'a #%.html')});
      }
    }
    server = http.createServer((request, response) => {
      const file = path.join(work, decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
      if (!file.startsWith(work + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        response.writeHead(404); response.end(); return;
      }
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    for (const [browserName, engine] of [['chromium', chromium], ['firefox', firefox]]) {
      const browser = await engine.launch({timeout: 15000});
      try {
        for (const item of cases) {
          const page = await browser.newPage({viewport: {width: 1000, height: 720}});
          const errors = [];
          page.on('pageerror', error => errors.push(String(error)));
          page.on('response', response => {
            if (response.status() >= 400 && !response.url().endsWith('/favicon.ico')) errors.push(response.url());
          });
          const base = 'http://127.0.0.1:' + server.address().port + '/' +
            item.relative.split('/').map(encodeURIComponent).join('/');
          const route = item.combined ? '#lwp/a/a%20%23%25.html/detail' : '#detail';
          await page.goto(base + route);
          await page.locator('#detail').waitFor();
          await page.evaluate(() => document.fonts.ready);
          assert.equal(await page.locator('#collection').count(), +item.nav, JSON.stringify(item));
          assert.equal(await page.locator('#lwp-index a[href*="collection"]').count(), +item.nav);
          assert.equal(await page.locator('.slide').count(), item.nav ? 4 : 3);
          assert.equal(await page.locator('#menuHome .presenter-menu-label').textContent(),
            item.index ? 'Back to index' : 'Start of series');
          const home = item.combined ? base + (item.index ? '#lwp/index' : '')
            : new URL(item.index ? 'index.html' : 'a%20%23%25.html', base).href;
          await page.evaluate(() => {
            window.copied = '';
            navigator.clipboard.writeText = async text => {window.copied = text;};
          });
          await page.keyboard.press('s');
          await page.locator('[data-action="copy"][data-scope="series"]').click();
          assert.equal(await page.evaluate(() => window.copied), home);
          await page.keyboard.press('Escape');
          await page.keyboard.press('Control+Home');
          if (item.index) await page.locator('body.index-page').waitFor();
          else await page.waitForFunction(() => Math.abs(window.scrollY) < 2);
          assert.equal(await page.locator('body.index-page').count(), +item.index);
          if (!item.combined) assert.equal(page.url().split('#')[0], home);
          assert.deepEqual(errors, [], browserName + ': ' + JSON.stringify(item));
          await page.close();
        }
      } finally {await browser.close();}
    }
    console.log('Output defaults browser checks passed');
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    fs.rmSync(work, {recursive: true, force: true});
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
