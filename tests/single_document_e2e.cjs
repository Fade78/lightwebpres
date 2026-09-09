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

${name === 'b' ? '<table id="scroll-table" style="min-width: 1600px"><tr><td>Wide table</td><td>Second cell</td></tr></table>' : ''}
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
    assert.equal(await page.locator('#menuFitScope').inputValue(), 'article');
    assert.equal(await page.locator('#menuFitScopeLabel').evaluate(node => node.hidden), false);
    assert.equal(await page.locator('#menuFitScopeLabel span').textContent(), 'Port\u00e9e de la r\u00e9duction uniforme');
    async function scope(value) {
      await page.evaluate(value => {
        const control = document.getElementById('menuFitScope');
        control.value = value;
        control.dispatchEvent(new Event('change', {bubbles: true}));
      }, value);
      await settle();
    }
    await page.evaluate(() => {
      const control = document.getElementById('menuTableMode');
      control.value = 'scroll'; control.dispatchEvent(new Event('change'));
    });
    await settle();
    await page.evaluate(() => {
      window.fitOriginalSlide = document.getElementById('intro');
      window.fitOriginalLink = document.getElementById('other');
      fitOriginalLink.focus({preventScroll: true});
      window.fitOriginalHash = location.hash;
      window.fitOriginalTable = document.getElementById('scroll-table').parentElement;
      fitOriginalTable.scrollLeft = 120;
      window.fitLifecycle = {connect: 0, disconnect: 0, focus: 0, blur: 0, iframe: 0};
      customElements.define('fit-lifecycle-probe', class extends HTMLElement {
        connectedCallback() { fitLifecycle.connect++; }
        disconnectedCallback() { fitLifecycle.disconnect++; }
      });
      const widget = document.createElement('fit-lifecycle-probe');
      widget.id = 'active-fit-widget';
      fitOriginalSlide.appendChild(widget);
      const frame = document.createElement('iframe');
      frame.id = 'active-fit-frame'; frame.srcdoc = '<p>Active frame</p>';
      frame.style.cssText = 'position:absolute;width:20px;height:20px';
      frame.addEventListener('load', () => fitLifecycle.iframe++);
      widget.appendChild(frame);
      fitOriginalLink.addEventListener('focus', () => fitLifecycle.focus++);
      fitOriginalLink.addEventListener('blur', () => fitLifecycle.blur++);
      const selection = getSelection();
      selection.setBaseAndExtent(fitOriginalLink.firstChild, 1, fitOriginalLink.firstChild, 5);
      window.fitSelection = {anchor: selection.anchorNode, anchorOffset: selection.anchorOffset,
        focus: selection.focusNode, focusOffset: selection.focusOffset, text: selection.toString()};
    });
    await page.waitForFunction(() => fitLifecycle.iframe === 1);
    await scope('series');
    async function unchangedLiveView() {
      assert.deepEqual(await page.evaluate(() => fitLifecycle), {connect: 1, disconnect: 0, focus: 0, blur: 0, iframe: 1});
      assert.equal(await page.evaluate(() => {
        const selection = getSelection();
        return selection.anchorNode === fitSelection.anchor && selection.anchorOffset === fitSelection.anchorOffset
          && selection.focusNode === fitSelection.focus && selection.focusOffset === fitSelection.focusOffset
          && selection.toString() === fitSelection.text && document.activeElement === fitOriginalLink;
      }), true, 'measurement must preserve live selection endpoints and focus without repairing them');
    }
    await unchangedLiveView();
    await page.setViewportSize({width: 1090, height: 710});
    await settle();
    await unchangedLiveView();
    await page.setViewportSize({width: 1100, height: 700});
    await settle();
    await unchangedLiveView();
    await page.evaluate(() => document.getElementById('active-fit-widget').remove());
    const seriesScale = await page.locator('#detail').getAttribute('data-lwp-text-scale');
    assert.equal(seriesScale, denseState.scale, 'series fit uses the dense sibling real layout');
    assert.equal(await page.evaluate(() => document.getElementById('intro') === fitOriginalSlide
      && document.getElementById('other') === fitOriginalLink && document.activeElement === fitOriginalLink
      && location.hash === fitOriginalHash), true, 'measurement restores exact active DOM, focus and route');
    assert.equal(await page.evaluate(() => fitOriginalTable.scrollLeft), 120,
      'measurement preserves the active table scroll position');
    assert.equal(await page.locator('section.slide').evaluateAll(nodes =>
      new Set(nodes.filter(n => !n.hidden).map(n => n.getAttribute('data-lwp-text-scale'))).size), 1);
    await navigate('a.html');
    assert.equal(await page.locator('#detail').getAttribute('data-lwp-text-scale'), seriesScale,
      'all articles in the scope receive exactly the same factor');
    await navigate('b.html');
    await scope('article');
    assert.equal(await page.locator('#detail').getAttribute('data-lwp-text-scale'), '1');
    await scope('series');
    await page.reload();
    await settle();
    assert.equal(await page.locator('#menuFitScope').inputValue(), 'series');
    assert.equal(await page.locator('#detail').getAttribute('data-lwp-text-scale'), seriesScale);
    const beforePrint = await page.locator('#lwp-series-view').textContent();
    const beforePrintStyles = await page.locator('#lwp-series-view [style]').evaluateAll(nodes => nodes.map(node => node.getAttribute('style')));
    await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.locator('[data-lwp-fit-measurement]').evaluateAll(nodes =>
      nodes.every(node => getComputedStyle(node).display === 'none')), true, 'passive documents are excluded from print');
    await page.emulateMedia({media: 'print'});
    assert.equal(await page.locator('#lwp-series-view').textContent(), beforePrint);
    assert.equal(await page.locator('#lwp-series-view').textContent().then(text => text.includes('Note from A')), false);
    assert.equal(await page.locator('#navMenu').isVisible(), false);
    await page.emulateMedia({media: 'screen'});
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
    await settle();
    assert.equal(await page.locator('#menuZoomValue').textContent(), '110%');
    assert.deepEqual(await page.locator('#lwp-series-view [style]').evaluateAll(nodes => nodes.map(node => node.getAttribute('style'))), beforePrintStyles);
    await scope('article');
    assert.equal(await page.locator('#detail').getAttribute('data-lwp-text-scale'), '1');
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
    await scope('series');
    assert.equal(await page.evaluate(() => document.fullscreenElement === document.documentElement), true,
      'measuring other views preserves real fullscreen');
    await scope('article');
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
      await offline.evaluate(() => {
        for (const [id, value] of [['menuTextFit', 'uniform'], ['menuFitScope', 'series']]) {
          const n = document.getElementById(id); n.value = value; n.dispatchEvent(new Event('change'));
        }
      });
      await offline.waitForFunction(() => {
        const value = document.getElementById('detail').getAttribute('data-lwp-text-scale');
        return value !== null && Number(value) < 1;
      });
      assert.equal(await offline.locator('#static-svg').evaluate(img => img.complete && img.naturalWidth > 0), true,
        'series measurements retain static SVG images even when storage is denied');
      await offline.keyboard.press('Control+Home');
      assert.equal(await offline.locator('section.slide').count(), 0);
      assert.equal(await offline.locator('#lwp-series-view').evaluate(node => getComputedStyle(node).outlineStyle), 'none',
        'route focus must not draw a frame around contents');
      const card = offline.locator('#lwp-series-view a.article-card').first();
      if (mobile) await card.tap();
      else await card.click();
      assert.equal(await offline.title(), 'Article A');
      assert.equal(await offline.locator('section.slide').first().evaluate(node => getComputedStyle(node).outlineStyle), 'none',
        'route focus must not draw a separator around the first slide');
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
    // A second real build distinguishes slide visibility from article gates,
    // and a measurable intermediate factor from merely hitting the floor.
    const fitting = path.join(work, 'fit-scope');
    cli('init', fitting);
    fs.writeFileSync(path.join(fitting, 'series.json'), JSON.stringify({
      series_meta: {title: 'Scope and frame', reading: {text_fit: 'uniform'}},
      presentation_presets: ['lightwebpres-docs@0.1.0/docs'],
      articles: ['sparse', 'measured', 'gated'].map(name => ({page_source: name + '.md', page_dest: name + '.html'})),
    }));
    fs.writeFileSync(path.join(fitting, 'sources/sparse.md'), `<!-- lwp:meta -->
page_title: Sparse
style.page.bg: #ffffff
---
<!-- lwp:slide:cover -->
slug: cover
# Sparse cover
summary: Short summary.
---
<!-- lwp:slide -->
slug: short
## A standard card

Short text. <a id="focus-link" href="#cover">Cover</a>
`);
    fs.writeFileSync(path.join(fitting, 'sources/measured.md'), `<!-- lwp:meta -->
page_title: Measured
style.page.bg: #eeeeee
style.page.content-max: 500px
---
<!-- lwp:slide -->
slug: short
## Short

Short text.
---
<!-- lwp:slide -->
slug: measured
tags: technical
## Measured

<p style="font-size: 30px; line-height: 36px">${Array(16).fill('Measured line.').join('<br>')}</p>
`);
    fs.writeFileSync(path.join(fitting, 'sources/gated.md'), `<!-- lwp:meta -->
page_title: Gated
tags: restricted
---
<!-- lwp:slide:full-article -->
slug: long
article: long.md
`);
    fs.writeFileSync(path.join(fitting, 'sources/long.md'), '# Long form\n\n' + 'Long paragraph.\n\n'.repeat(80));
    cli('build', fitting, '--lang', 'en', '--themes', 'print-ink,dracula', '--scroll-duration', '0', '--output', path.join(fitting, 'multi'));
    cli('build', fitting, '--lang', 'en', '--themes', 'print-ink,dracula', '--scroll-duration', '0', '--single-page', 'series.html');
    for (const mobile of [false, true]) {
      const probe = await browser.newPage(mobile
        ? {viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}
        : {viewport: {width: 1100, height: 700}});
      const probeErrors = [];
      probe.on('pageerror', e => probeErrors.push(e.message));
      await probe.context().setOffline(true);
      await probe.route(/^https?:/, r => r.abort());
      const settled = () => probe.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const setOption = async (name, value) => {
        await probe.evaluate(({name, value}) => {
          const n = document.querySelector(`[data-reading-option="${name}"]`);
          n.value = value; n.dispatchEvent(new Event('change', {bubbles: true}));
        }, {name, value});
        await settled();
      };
      const go = async key => {
        await probe.evaluate(key => {location.hash = key ? '#lwp/a/' + key + '.html' : '#lwp/index';}, key);
        await settled();
      };
      const tag = async value => {
        await probe.locator(`[data-tag="${value}"]`).evaluate(n => n.click());
        await settled();
      };
      const scale = () => probe.locator('section.slide:not([hidden])').first().getAttribute('data-lwp-text-scale').then(Number);
      await probe.goto(pathToFileURL(path.join(fitting, 'multi/sparse.html')).href);
      await settled();
      assert.equal(await probe.locator('#menuFitScopeLabel').evaluate(n => n.hidden), true, 'multipage never offers bundle scope');
      await probe.goto(pathToFileURL(path.join(fitting, 'public/series.html')).href);
      await settled();
      await probe.screenshot({path: path.join(work, `frame-${mobile ? 'mobile' : 'desktop'}-contents.png`)});
      assert.equal(await probe.locator('#lwp-series-view').evaluate(n => getComputedStyle(n).outlineStyle), 'none');
      await go('sparse');
      await probe.waitForTimeout(300);
      const geometry = await probe.evaluate(() => {
        const cover = document.getElementById('cover'), short = document.getElementById('short');
        return {gap: short.getBoundingClientRect().top - cover.getBoundingClientRect().bottom,
          left: cover.getBoundingClientRect().left, right: cover.getBoundingClientRect().right,
          width: document.documentElement.clientWidth, outline: getComputedStyle(cover).outlineStyle,
          top: cover.getBoundingClientRect().top,
          bodyPadding: getComputedStyle(document.body).padding,
          background: getComputedStyle(document.body).backgroundColor};
      });
      assert.deepEqual(geometry, {gap: 0, left: 0, right: mobile ? 390 : 1100, width: mobile ? 390 : 1100,
        top: 0, outline: 'none', bodyPadding: '0px', background: 'rgb(255, 255, 255)'});
      await probe.evaluate(() => scrollTo({top: innerHeight - 150, behavior: 'instant'}));
      await settled();
      await probe.screenshot({path: path.join(work, `frame-${mobile ? 'mobile' : 'desktop'}-boundary.png`)});
      await setOption('fit_scope', 'series');
      assert.equal(await scale(), 1, 'tag-hidden dense slide and gated long form do not reduce the series');
      await tag('technical');
      const technical = await scale();
      if (!mobile) assert(technical > .75 && technical < 1, 'exercise a real bisection, not just the floor: ' + technical);
      await go('measured');
      assert.equal(await scale(), technical, 'the measured view and the sparse view receive exactly the same factor');
      await setOption('fit_scope', 'article');
      assert.equal(await scale(), technical, 'series measurement equals the actual mounted view solver');
      await go('sparse');
      assert.equal(await scale(), 1);
      await setOption('fit_scope', 'series');
      assert.equal(await scale(), technical);
      await probe.setViewportSize({width: 800, height: 1000});
      await settled();
      assert.equal(await scale(), 1, 'viewport changes invalidate the series factor');
      await probe.setViewportSize(mobile ? {width: 390, height: 844} : {width: 1100, height: 700});
      await settled();
      assert.equal(await scale(), technical);
      await probe.keyboard.press('c');
      await probe.locator('[data-identity="lightwebpres-docs@0.1.0"]').click();
      await probe.locator('[data-presentation="lightwebpres-docs@0.1.0/docs"]').click();
      await settled();
      const presetScale = await scale();
      assert.equal(await probe.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(255, 255, 255)',
        'measuring another page restores active page pins');
      await go('measured');
      await setOption('fit_scope', 'article');
      assert.equal(await scale(), presetScale, 'alternate preset measurement matches its mounted variant and pins');
      await go('sparse');
      await setOption('fit_scope', 'series');
      await tag('restricted');
      assert.equal(await scale(), .75, 'a tag-visible long form still constrains uniform fitting');
      await tag('default');
      assert.equal(await scale(), 1, 'tag changes invalidate earlier factors');
      await setOption('text_fit', 'per-slide');
      assert.equal(await probe.locator('#menuFitScopeLabel').evaluate(n => n.hidden), true);
      await setOption('text_fit', 'uniform');
      await probe.keyboard.press('m');
      await probe.locator('#menuReading').click();
      const scopeControl = probe.getByRole('combobox', {name: 'Uniform fit scope', exact: true});
      assert.equal(await scopeControl.isVisible(), true);
      await scopeControl.focus();
      await scopeControl.selectOption('article');
      await settled();
      assert.equal(await probe.locator('#menuFitScope').evaluate(n => document.activeElement === n), true);
      assert.deepEqual(probeErrors, []);
      await probe.close();
    }
    const passive = spawnSync(process.execPath, [path.join(__dirname, 'single_document_measurement_e2e.cjs')],
      {env: process.env, cwd: root, encoding: 'utf8', timeout: 120000});
    assert.equal(passive.status, 0, passive.stdout + passive.stderr);
    console.log(passive.stdout.trim());
    console.log('Single-document runtime: real CLI builds, routes/history/tags, notes, presets/pins, article/series fitting, live selection/widget isolation, stale events, print, real fullscreen, and offline desktop/mobile geometry checks passed.');
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    await browser.close();
    // Retain this run's fixtures under work/tmp for failed-check diagnostics.
    console.log('Runtime probe fixtures: ' + path.relative(root, work));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
