// Standalone browser probe of the real --single-page --inline-images build.
// Resolve the supplied browser before redirecting XDG scratch. Callers that
// already redirected XDG must pass their previously resolved PW_CHROMIUM_PATH.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  process.env.TMPDIR = scratch;
  let chromium, browser;
  try {
    chromium = require('playwright').chromium;
    process.env.PW_CHROMIUM_PATH = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(scratch, 'xdg-cache');
    browser = await chromium.launch({executablePath: process.env.PW_CHROMIUM_PATH});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  let server;
  const work = fs.mkdtempSync(path.join(scratch, 'single-document-runtime-'));
  try {
    const series = path.join(work, 'series');
    const env = {...process.env, LWP_IDENTITY_KITS_DIR: path.join(root, 'examples/kits')};
    function cli(...args) {
      const result = spawnSync(process.env.PYTHON || 'python3', [path.join(root, 'lightwebpres'), ...args],
        {env, cwd: root, encoding: 'utf8', timeout: 120000});
      assert.equal(result.status, 0, result.stdout + result.stderr);
    }
    cli('init', series);
    fs.writeFileSync(path.join(series, 'series.json'), JSON.stringify({
      series_meta: {title: 'Single document probe'},
      presentation_presets: ['lightwebpres-docs@0.1.0/docs'],
      articles: [{page_source: 'a.md', page_dest: 'a.html'},
        {page_source: 'b.md', page_dest: 'b.html'}],
    }));
    for (const name of ['a', 'b']) {
      fs.writeFileSync(path.join(series, `sources/${name}.md`), `<!-- lwp:meta -->
page_title: Article ${name.toUpperCase()}
notes_placement: page
${name === 'b' ? 'tags: technical' : ''}
style.page.bg: ${name === 'a' ? '#ffeedd' : '#ddeeff'}
${name === 'a' ? 'style.color.ink: #123456' : ''}
---
<!-- lwp:slide -->
slug: intro
## Article ${name.toUpperCase()}
note: Presenter ${name.toUpperCase()}

Shared local ID, distinct article.[^one]

<a id="other" href="${name === 'a' ? 'b' : 'a'}.html">Other article</a>
<a id="home-link" href="index.html">Contents</a>
<a id="target-link" href="#detail">Local detail</a>
<a id="download-link" href="b.html" download>Download</a>
<a id="new-tab-link" href="b.html" target="_blank">New tab</a>
<a id="encoded-link" href="#caf%C3%A9%20%2F%20%25">Encoded target</a>

[^one]: Note from ${name.toUpperCase()}.

---
<!-- lwp:slide -->
slug: detail
## Detail ${name.toUpperCase()}
note: Detail presenter ${name.toUpperCase()}

${name === 'a' ? 'Dense text. '.repeat(300) : 'Short readable text.'}

<img id="static-svg" alt="Static mark" width="40" height="40" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='40' height='40'%3E%3Crect width='40' height='40' fill='red'/%3E%3C/svg%3E">

<p id="caf\u00e9 / %">An anchor with encoded punctuation.</p>
`);
    }
    cli('build', series, '--themes', 'print-ink,dracula', '--scroll-duration', '200',
      '--single-page', 'series.html', '--inline-images');
    const publicDir = path.join(series, 'public');
    server = http.createServer((request, response) => {
      const file = path.join(publicDir, decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
      if (!file.startsWith(publicDir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        response.writeHead(404); response.end(); return;
      }
      response.setHeader('Content-Type', file.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream');
      response.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}/series.html`;
    const page = await browser.newPage({viewport: {width: 1100, height: 700}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const route = (key, target = '') => key ? `#lwp/a/${encodeURIComponent(key)}${target ? '/' + encodeURIComponent(target) : ''}` : '#lwp/index';
    async function navigate(key, target = '') {
      await page.evaluate(hash => { location.hash = hash; }, route(key, target));
      await page.waitForFunction(title => document.title === title, key ? `Article ${key[0].toUpperCase()}` : 'Single document probe');
      await settle();
    }
    await page.goto(base);
    await settle();
    await page.evaluate(() => {
      window.originalDocument = document;
      window.originalRoot = document.documentElement;
      window.originalMenu = document.getElementById('navMenu');
    });
    await page.locator('#lwp-series-view a.article-card').first().click();
    await settle();
    assert.equal(await page.title(), 'Article A');
    assert.equal(new URL(page.url()).hash, route('a.html'));
    assert.equal(await page.locator('#intro').count(), 1);
    assert.equal(await page.locator('#other').getAttribute('href'), route('b.html'));
    assert.equal(await page.locator('#target-link').getAttribute('href'), route('a.html', 'detail'));
    assert.equal(await page.locator('#download-link').getAttribute('href'), 'b.html');
    assert.equal(await page.locator('#new-tab-link').getAttribute('href'), route('b.html'));
    assert.equal(await page.locator('#encoded-link').getAttribute('href'), route('a.html', 'caf\u00e9 / %'));
    const popupPromise = page.waitForEvent('popup');
    await page.locator('#new-tab-link').click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    assert.equal(await popup.title(), 'Article B');
    assert.equal(await page.title(), 'Article A');
    await popup.close();
    const modifiedClicks = await page.evaluate(() => ['ctrlKey', 'metaKey', 'shiftKey', 'altKey'].map(modifier => {
      let prevented;
      const stop = event => { prevented = event.defaultPrevented; event.preventDefault(); };
      document.addEventListener('click', stop, {once: true});
      document.getElementById('other').dispatchEvent(new MouseEvent('click',
        {bubbles: true, cancelable: true, button: 0, [modifier]: true}));
      return prevented;
    }));
    assert.deepEqual(modifiedClicks, [false, false, false, false]);
    await page.keyboard.press('n');
    assert.match(await page.locator('#presenterNotes').textContent(), /Presenter A/);
    await page.locator('#other').click();
    await settle();
    assert.equal(await page.title(), 'Article B');
    assert.equal(await page.evaluate(() => localStorage.getItem('lwp-active-tag')), 'technical');
    assert.match(await page.locator('#presenterNotes').textContent(), /Presenter B/);
    assert.equal(await page.evaluate(() => document === originalDocument && document.documentElement === originalRoot
      && document.getElementById('navMenu') === originalMenu), true);
    await page.goBack();
    await settle();
    assert.equal(await page.title(), 'Article A');
    await page.goForward();
    await settle();
    assert.equal(await page.title(), 'Article B');

    // A local note target must select its owning article before resolving IDs.
    const noteId = await page.locator('.note-call a').first().getAttribute('href');
    await page.locator('.note-call a').first().click();
    await settle();
    assert.equal(new URL(page.url()).hash, noteId);
    assert.match(await page.locator('li[id^="note-"]').first().textContent(), /Note from B/);
    await page.reload();
    await settle();
    assert.equal(new URL(page.url()).hash, noteId);
    assert.equal(await page.title(), 'Article B');
    assert.equal(await page.evaluate(() => document.activeElement.id.startsWith('note-')), true);
    await page.locator('.note-back').first().click();
    await settle();
    assert.match(new URL(page.url()).hash, /noteref-/);
    await page.locator('#encoded-link').click();
    await settle();
    assert.equal(new URL(page.url()).hash, route('b.html', 'caf\u00e9 / %'));
    assert.equal(await page.evaluate(() => document.activeElement.id), 'caf\u00e9 / %');

    // Appearance is shared, but article pins and full CSS baselines are not.
    await navigate('a.html');
    await page.keyboard.press('c');
    await page.locator('[data-theme="dracula"]').click();
    const aInk = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim());
    assert.match(aInk.toLowerCase(), /^#123456/);
    await navigate('b.html');
    const bInk = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim());
    assert.notEqual(bInk, aInk);
    assert.match(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim()), /^#ddeeff/i);
    await page.keyboard.press('c');
    await page.locator('[data-identity="lightwebpres-docs@0.1.0"]').click();
    await page.locator('[data-presentation="lightwebpres-docs@0.1.0/docs"]').click();
    await settle();
    assert.equal(await page.locator('#other').getAttribute('href'), route('a.html'));
    await navigate('a.html', 'detail');
    assert.equal(await page.locator('.lwp-presentation--lightwebpres-docs').count() > 0, true);
    assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim()), aInk);
    assert.match(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--page-bg').trim()), /^#ffeedd/i);
    await page.keyboard.press('End');
    await page.keyboard.press('ArrowRight');
    await settle();
    assert.equal(await page.title(), 'Article A', 'end-of-article stepping never activates B');
    await page.keyboard.press('Home');
    await page.keyboard.press('ArrowLeft');
    await settle();
    assert.equal(await page.title(), 'Article A');
    assert.equal(new URL(page.url()).hash, route('a.html'));

    await page.locator('.note-call a').first().click();
    await settle();
    const presetNoteHash = new URL(page.url()).hash;
    await page.keyboard.press('c');
    await page.locator('[data-identity="builtin"]').click();
    await page.locator('[data-presentation="builtin/standard"]').click();
    await settle();
    assert.equal(new URL(page.url()).hash, presetNoteHash, 'preset replacement keeps an inner note route');
    assert.equal(await page.locator('.note-back').first().getAttribute('href'), route('a.html', 'noteref-p-1'));
    await navigate('a.html');

    // Pending numeric jumps and in-flight glides cannot cross activation.
    await page.keyboard.press('2');
    await page.locator('#other').click();
    await page.keyboard.press('Enter');
    await page.waitForTimeout(300);
    assert.equal(await page.locator('#slideCounter').textContent(), '1 / 3');
    await page.locator('#navNext').click();
    await navigate('a.html');
    await page.waitForTimeout(300);
    assert.equal(new URL(page.url()).hash, route('a.html'));

    // Fit/zoom only the mounted article; printing restores its authored sizes.
    await page.keyboard.press('a');
    await page.keyboard.press('+');
    await settle();
    const denseState = await page.locator('#detail').evaluate(slide => ({
      scale: slide.getAttribute('data-lwp-text-scale'), height: slide.getBoundingClientRect().height,
      viewport: innerHeight, mode: document.getElementById('menuTextFit').value,
    }));
    await navigate('b.html');
    assert.equal(await page.locator('#menuZoomValue').textContent(), '110%');
    assert.equal(await page.locator('#menuTextFit').inputValue(), 'uniform');
    assert(Number(denseState.scale) < 1, 'the dense article exercises automatic fitting: ' + JSON.stringify(denseState));
    assert.equal(await page.locator('#detail').getAttribute('data-lwp-text-scale'), '1',
      'a different article must not inherit the dense article uniform factor');
    const beforePrint = await page.locator('#lwp-series-view').textContent();
    const beforePrintStyles = await page.locator('#lwp-series-view [style]').evaluateAll(nodes => nodes.map(node => node.getAttribute('style')));
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
    await page.emulateMedia({media: 'print'});
    assert.equal(await page.locator('#lwp-series-view').textContent(), beforePrint);
    assert.equal(await page.locator('#lwp-series-view').textContent().then(text => text.includes('Note from A')), false);
    assert.equal(await page.locator('#navMenu').isVisible(), false);
    await page.emulateMedia({media: 'screen'});
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await settle();
    assert.equal(await page.locator('#menuZoomValue').textContent(), '110%');
    assert.deepEqual(await page.locator('#lwp-series-view [style]').evaluateAll(nodes => nodes.map(node => node.getAttribute('style'))), beforePrintStyles);
    await page.evaluate(() => {
      window.dispatchEvent(new Event('beforeprint'));
      location.hash = '#lwp/a/a.html';
    });
    await settle();
    assert.equal(await page.title(), 'Article B', 'article activation is deferred while printing');
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await settle();
    assert.equal(await page.title(), 'Article A');
    await navigate('');
    assert.equal(await page.locator('section.slide').count(), 0);
    assert.equal(await page.locator('#presenterNotes').textContent(), '');
    await page.emulateMedia({media: 'print'});
    assert.equal(await page.locator('section.slide').count(), 0, 'contents printing never mounts an article');
    await page.emulateMedia({media: 'screen'});

    // Exercise the actual fullscreen API when this supplied browser supports it.
    await page.keyboard.press('f');
    const fullscreen = await page.evaluate(() => document.fullscreenElement === document.documentElement);
    assert.equal(fullscreen, true, 'real fullscreen entry, not a stub');
    await page.locator('#lwp-series-view a.article-card').first().click();
    await settle();
    assert.equal(await page.evaluate(() => document.fullscreenElement === document.documentElement), true);
    await page.keyboard.press('Control+Home');
    await settle();
    assert.equal(await page.evaluate(() => document.fullscreenElement === document.documentElement), true);
    await page.evaluate(() => document.exitFullscreen());
    assert.deepEqual(errors, []);

    // Move only the artifact into a new empty directory: no old public/assets
    // tree can satisfy a missing resource, on either desktop or a touch phone.
    const moved = path.join(work, 'moved');
    fs.mkdirSync(moved);
    fs.copyFileSync(path.join(publicDir, 'series.html'), path.join(moved, 'series.html'));
    assert.deepEqual(fs.readdirSync(moved), ['series.html']);
    for (const mobile of [false, true]) {
      const offline = await browser.newPage(mobile
        ? {viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true}
        : {viewport: {width: 1100, height: 700}});
      const offlineErrors = [];
      const resourceRequests = [];
      offline.on('pageerror', error => offlineErrors.push(error.message));
      offline.on('request', request => {
        if (request.resourceType() !== 'document' && !request.url().startsWith('data:')) resourceRequests.push(request.url());
      });
      await offline.context().setOffline(true);
      await offline.route(/^https?:/, request => request.abort());
      await offline.addInitScript(() => {
        for (const name of ['localStorage', 'sessionStorage']) Object.defineProperty(window, name,
          {get() { throw new DOMException('Denied', 'SecurityError'); }});
      });
      await offline.goto(pathToFileURL(path.join(moved, 'series.html')).href + route('b.html', 'detail'));
      assert.equal(await offline.title(), 'Article B');
      assert.equal(await offline.locator('#static-svg').evaluate(img => img.complete && img.naturalWidth > 0), true);
      await offline.keyboard.press('Control+Home');
      assert.equal(await offline.locator('section.slide').count(), 0);
      const card = offline.locator('#lwp-series-view a.article-card').first();
      if (mobile) await card.tap();
      else await card.click();
      assert.equal(await offline.title(), 'Article A');
      await offline.keyboard.press('c');
      const identity = offline.locator('[data-identity="lightwebpres-docs@0.1.0"]');
      if (mobile) await identity.tap();
      else await identity.click();
      const preset = offline.locator('[data-presentation="lightwebpres-docs@0.1.0/docs"]');
      if (mobile) await preset.tap();
      else await preset.click();
      await offline.locator('.note-call a').first()[mobile ? 'tap' : 'click']();
      await offline.waitForFunction(() => document.activeElement.id.startsWith('note-'));
      assert.equal(await offline.locator('#lwp-series-view').evaluate(host => host.scrollWidth <= document.documentElement.clientWidth + 1), true);
      assert.equal(await offline.locator('img').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0)), true);
      assert.deepEqual(resourceRequests, [], 'all rendering resources remain embedded after moving the artifact');
      assert.deepEqual(offlineErrors, []);
      await offline.close();
    }
    console.log('Single-document runtime: real CLI build, routes/history/tags, notes, presets/pins, isolated fitting, stale events, print, real fullscreen, and moved offline desktop/mobile checks passed.');
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    await browser.close();
    // Retain this run's fixtures under work/tmp for failed-check diagnostics.
    console.log('Runtime probe fixtures: ' + path.relative(root, work));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
