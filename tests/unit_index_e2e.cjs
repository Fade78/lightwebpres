// Real publication fixtures. No dependency/cache discovery or installation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');
const {collectConsoleErrors} = require('./console_errors.cjs');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  process.env.TMPDIR = scratch;
  const work = fs.mkdtempSync(path.join(scratch, 'unit-index-browser-'));
  let browser, server;
  try {
    const {chromium} = require('playwright');
    // Ask the supplied API before redirecting XDG. An explicit executable is
    // a fallback, not permission to inspect an external installation.
    const executablePath = chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(work, 'cache');
    process.env.XDG_CONFIG_HOME = path.join(work, 'config');
    try {
      browser = await chromium.launch({executablePath});
    } catch (error) {
      if (!process.env.PW_CHROMIUM_PATH || process.env.PW_CHROMIUM_PATH === executablePath) throw error;
      browser = await chromium.launch({executablePath: process.env.PW_CHROMIUM_PATH});
    }
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  try {
    const series = path.join(work, 'series');
    fs.mkdirSync(path.join(series, 'sources'), {recursive: true});
    const env = {...process.env, LWP_IDENTITY_KITS_DIR: path.join(root, 'examples/kits'),
      LWP_THEMES_DIR: path.join(work, 'unused-themes'), LWP_COMMONS_DIR: path.join(work, 'unused-commons')};
    delete env.LWP_LANG;
    const articles = ['a', 'b'].map(name => ({page_source: name + '.md', page_dest: name + '.html', author: 'Entry'}));
    fs.writeFileSync(path.join(series, 'series.json'), JSON.stringify({
      series_meta: {title: 'Unit index browser probe', author: 'Series', default_tag: 'expert-fr',
        reading: {table_mode: 'scroll'}},
      presentation_presets: ['lightwebpres-docs@0.1.0/docs'], articles,
    }));
    const slides = [
      '<!-- lwp:slide:cover -->\nslug: cover\n# Index field notes\nsummary: A compact directory of the published material.',
      '<!-- lwp:slide:unit-index -->\nslug: overview\nkicker: Field guide\nsummary: Every published slide, in source order.\nnote: Keep the selected route; follow a link deliberately.',
      '<!-- lwp:slide:unit-index -->\nslug: french\n## French route\nindex-max-columns: 2\nindex-selector: unit:author:Entry series:author:Series slide:tags:expert-fr',
      '<!-- lwp:slide:unit-index -->\nslug: english\n## English route\nindex-max-columns: 3\nindex-selector: slide:title:/^English/ slide:tags:expert-en',
      '<!-- lwp:slide:unit-index -->\nslug: empty\nindex-selector: slide:title:/^Absent$/',
      '<!-- lwp:slide -->\nslug: shared\n## Shared introduction\nsummary: No language semantics are assigned to the tag names.\n\nA source[^one].\n\n[^one]: A published endnote.',
    ];
    for (let i = 0; i < 38; i++) {
      const lang = i % 2 ? 'English' : 'French';
      slides.push(`<!-- lwp:slide -->\nslug: item-${i}\ntags: expert-${i % 2 ? 'en' : 'fr'}\n`
        + `## ${lang} item ${String(i).padStart(2, '0')}: ${i === 1 ? 'UnbrokenTitle'.repeat(8) : 'A practical explanation of evidence and its limits'}\n`
        + 'summary: A deliberately authored title, never translated by the interface.');
    }
    slides.push('<!-- lwp:slide -->\nslug: table\ntags: expert-fr\n## Wide comparison\n\n'
      + '| ' + Array.from({length: 10}, (_, i) => 'UnbreakableColumnHeading' + i).join(' | ')
      + ' |\n| ' + Array(10).fill('---').join(' | ') + ' |\n| ' + Array(10).fill('Evidence').join(' | ') + ' |');
    slides.push('<!-- lwp:slide:series-nav -->\nslug: series');
    for (const name of ['a', 'b']) {
      fs.writeFileSync(path.join(series, `sources/${name}.md`), `<!-- lwp:meta -->\npage_title: Unit ${name.toUpperCase()}\n`
        + 'author: Meta\nslug_prefix: p-\nnotes_placement: page\n---\n\n'
        + slides.join('\n\n---\n\n') + '\n');
    }
    for (const mode of ['multi', 'single']) {
      const result = spawnSync(process.env.PYTHON || 'python3', [path.join(root, 'lightwebpres'), 'build', series,
        '--output', path.join(work, mode), '--themes', 'print-ink,dracula',
        '--scroll-duration', '0', ...(mode === 'single' ? ['--single-html', 'series.html'] : [])],
      {env, cwd: root, encoding: 'utf8', timeout: 120000});
      assert.equal(result.status, 0, result.stdout + result.stderr);
    }
    server = http.createServer((request, response) => {
      const file = path.join(work, decodeURIComponent(new URL(request.url, 'http://localhost').pathname));
      if (!file.startsWith(work + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        response.writeHead(404); response.end(); return;
      }
      response.setHeader('Content-Type', ({'.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml',
        '.png': 'image/png', '.css': 'text/css', '.js': 'text/javascript'})[path.extname(file)] || 'application/octet-stream');
      response.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    const errors = [];
    const measurements = [];
    for (const mode of ['multi', 'single']) {
      const context = await browser.newContext({viewport: {width: 1100, height: 700}, locale: 'en-US'});
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(error.message));
      collectConsoleErrors(page, errors);
      const route = (id, unit = 'a') => mode === 'single' ? `#lwp/a/${unit}.html/${id}` : `#${id}`;
      const url = base + (mode === 'single' ? '/single/series.html' : '/multi/a.html');
      const settle = async () => { await page.waitForTimeout(220); };
      async function go(id) {
        await page.evaluate(({hash, id}) => {
          if (location.hash === hash) document.getElementById(id).scrollIntoView({behavior: 'instant'});
          else location.hash = hash;
        }, {hash: route(id), id});
        await page.waitForFunction(id => !!document.getElementById(id), id);
        await settle();
        // Geometry probes start at the top, not at a saved reading ratio from
        // the preceding viewport/preset change. Link activation tests below
        // deliberately do not use this setup helper.
        await page.locator('#' + id).evaluate(node => node.scrollIntoView({behavior: 'instant'}));
        await settle();
      }
      async function press(key) { await page.keyboard.press(key); await settle(); }
      async function preset(selector) {
        await press('c');
        await page.locator(`[data-identity="${selector.split('/')[0]}"]`).click();
        await page.locator(`[data-presentation="${selector}"]`).click();
        await settle();
      }
      await page.goto(url + route('p-overview'));
      await page.waitForSelector('#p-overview .lwp-unit-index-link');
      await settle();
      const published = await page.locator('section.slide').evaluateAll(nodes => nodes.map(node => node.id));
      const targets = () => page.locator('#p-overview .lwp-unit-index-link').evaluateAll(nodes => nodes.map(node => node.dataset.lwpIndexTarget));
      assert.deepEqual(await targets(), published, 'wildcard must include self, other indexes, cover and notes');
      assert.ok(published.includes('notes'));
      assert.equal(await page.locator('#p-french .lwp-unit-index-link').count(), 20, 'scoped source selector');
      assert.equal(await page.locator('#p-english .lwp-unit-index-link').count(), 19, 'regex selector');
      assert.equal(await page.locator('#p-empty .lwp-unit-index-empty').textContent(), 'No matching slides.');
      assert.equal(await page.locator('#p-item-1').isVisible(), false);
      assert.equal(await page.locator('#p-shared').isVisible(), true);
      assert.equal(await page.locator('#p-overview h2').textContent(), 'Contents');
      assert.equal(await page.locator('#p-overview nav').getAttribute('aria-label'), 'Contents');

      for (const choice of ['builtin/standard', 'lightwebpres-docs@0.1.0/docs']) {
        await preset(choice);
        await page.waitForFunction(() => [...document.querySelectorAll('section.slide img')]
          .every(image => image.complete && image.naturalWidth > 0));
        assert.deepEqual(await targets(), published, 'preset keeps IDs and selected entries');
        for (const viewport of [{width: 1100, height: 700}, {width: 390, height: 844}]) {
          await page.setViewportSize(viewport);
          await settle();
          for (const [id, maximum] of [['p-overview', 1], ['p-french', 2], ['p-english', 3]]) {
            await go(id);
            const measure = await page.locator('#' + id).evaluate(slide => {
              const nav = slide.querySelector('nav');
              const list = nav.querySelector('ol');
              const links = [...list.querySelectorAll('a')];
              const bounds = links.map(link => link.getBoundingClientRect());
              return {columns: new Set(bounds.map(box => Math.round(box.left))).size,
                minHeight: Math.min(...bounds.map(box => box.height)), width: nav.getBoundingClientRect().width,
                font: getComputedStyle(nav).fontFamily, uiFont: getComputedStyle(document.body).getPropertyValue('--font-ui').trim(),
                overflow: document.documentElement.scrollWidth - innerWidth,
                linkOverflow: links.some(link => link.scrollWidth > link.clientWidth + 1),
                grid: getComputedStyle(list).display, color: getComputedStyle(links[0]).color,
                ink: getComputedStyle(slide).color, list: list.tagName, label: nav.getAttribute('aria-label')};
            });
            assert.equal(measure.columns, viewport.width === 390 ? 1 : maximum, JSON.stringify({choice, id, viewport, measure}));
            assert.ok(measure.minHeight >= 44, JSON.stringify(measure));
            assert.ok(measure.overflow <= 1 && !measure.linkOverflow, JSON.stringify(measure));
            assert.equal(measure.color, measure.ink);
            assert.equal(measure.list, 'OL');
            assert.ok(measure.label && measure.uiFont);
            measurements.push({mode, choice, viewport, id, ...measure});
          }
          if (mode === 'multi') {
            await page.screenshot({path: path.join(work, `${choice === 'builtin/standard' ? 'native' : 'docs'}-${viewport.width}.png`)});
          }
        }
        await page.setViewportSize({width: 1100, height: 700});
      }
      await preset('builtin/standard');
      await go('p-overview');
      await press('ArrowDown');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-cover',
        JSON.stringify(await page.evaluate(() => ({focus: document.activeElement.outerHTML.slice(0, 300),
          hash: location.hash, top: document.getElementById('p-overview').getBoundingClientRect().top,
          counter: document.getElementById('slideCounter').textContent}))));
      await press('ArrowRight');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-overview');
      await press('ArrowLeft');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-cover');
      // A background click moves focus only; a real link retains anchor behavior.
      await page.mouse.click(12, 250);
      await settle();
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-overview');
      await page.mouse.click(12, 250, {button: 'right'});
      await settle();
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-cover');
      assert.equal(new URL(page.url()).hash, route('p-overview'));
      await press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-overview');
      await press('ArrowDown');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.lwpIndexTarget), 'p-french',
        'arrow stepping must resume from a link reached with Tab');
      // Walk the long index rather than skipping to its tail: every step is
      // focus-only, and each selected entry is revealed with breathing room.
      for (const target of published.slice(3)) {
        await press('ArrowDown');
        const selected = await page.evaluate(() => {
          const box = document.activeElement.getBoundingClientRect();
          return {target: document.activeElement.dataset.lwpIndexTarget,
            top: box.top, bottom: box.bottom, height: innerHeight};
        });
        assert.equal(selected.target, target);
        assert.ok(selected.top >= 23 && selected.bottom <= selected.height - 23, JSON.stringify(selected));
        assert.equal(new URL(page.url()).hash, route('p-overview'), 'steps must never follow index entries');
      }
      await press('ArrowDown');
      // The frame's bottom padding can require one final bounded scroll.
      if (new URL(page.url()).hash === route('p-overview')) await press('ArrowDown');
      assert.equal(new URL(page.url()).hash, route('p-french'), 'exhaustion advances to the next slide, not the last linked target');
      await go('p-overview');
      const hiddenLink = page.locator('#p-overview [data-lwp-index-target="p-item-1"]');
      await hiddenLink.focus();
      await press('Enter');
      assert.equal(await page.locator('#p-item-1').isVisible(), true, 'normal anchor policy reveals hidden target');
      assert.equal(await page.evaluate(() => localStorage.getItem('lwp-active-tag')), 'expert-en');
      await go('p-overview');
      assert.deepEqual(await targets(), published, 'reading tag cannot refilter selected entries');
      await page.locator('#p-overview [data-lwp-index-target="p-item-0"]').click();
      await page.waitForTimeout(700);
      assert.equal(new URL(page.url()).hash, route('p-item-0'), JSON.stringify(await page.evaluate(() => ({
        tag: localStorage.getItem('lwp-active-tag'), hidden: document.getElementById('p-item-0').hidden,
        target: document.getElementById('p-item-0').getBoundingClientRect().top,
        focus: document.activeElement.outerHTML.slice(0, 300), scroll: scrollY,
        href: document.querySelector('#p-overview [data-lwp-index-target="p-item-0"]').getAttribute('href')}))));
      assert.equal(await page.evaluate(() => localStorage.getItem('lwp-active-tag')), 'expert-fr');
      await go('p-overview');
      await press('ArrowDown');
      const focusStyle = await page.evaluate(() => {
        const css = getComputedStyle(document.activeElement);
        return {style: css.outlineStyle, width: parseFloat(css.outlineWidth)};
      });
      assert.equal(focusStyle.style, 'solid');
      assert.ok(focusStyle.width >= 2);
      await press('n');
      assert.match(await page.locator('#presenterNotes').textContent(), /Keep the selected route/);
      await press('n');
      await page.locator('#navMenu').click();
      assert.equal(new URL(page.url()).hash, route('p-overview'), 'control click must not step');
      await press('Escape');

      // Generated headings, navigation labels and their self/other-index links
      // change UI language together. Authored titles do not.
      await page.evaluate(() => lwpSetLanguage('fr'));
      assert.equal(await page.locator('#p-overview nav').getAttribute('aria-label'), 'Sommaire');
      assert.equal(await page.locator('#p-overview [data-lwp-index-target="p-empty"] .lwp-unit-index-title').textContent(), 'Sommaire');
      assert.equal(await page.locator('#p-overview [data-lwp-index-target="p-french"] .lwp-unit-index-title').textContent(), 'French route');
      assert.equal(await page.locator('#p-empty .lwp-unit-index-empty').textContent(), 'Aucune fiche correspondante.');
      await preset('lightwebpres-docs@0.1.0/docs');
      assert.equal(await page.locator('#p-overview nav').getAttribute('aria-label'), 'Sommaire');
      assert.equal(await page.locator('#p-overview [data-lwp-index-target="p-empty"] .lwp-unit-index-title').textContent(), 'Sommaire');
      await preset('builtin/standard');
      await page.evaluate(() => lwpSetLanguage('en'));

      await go('p-table');
      const table = page.locator('#p-table .lwp-table-viewport');
      await table.focus();
      const beforeTable = new URL(page.url()).hash;
      await press('ArrowRight');
      assert.equal(new URL(page.url()).hash, beforeTable, 'table arrow cannot enter index navigation');
      assert.ok(await table.evaluate(node => node.scrollLeft > 0));

      await go('p-english');
      await press('c');
      await page.locator('[data-theme="dracula"]').click();
      await settle();
      const dark = await page.locator('#p-english .lwp-unit-index-link').first().evaluate(link => ({
        ink: getComputedStyle(link).color, pageInk: getComputedStyle(document.body).color,
        ground: getComputedStyle(link).backgroundColor, pageGround: getComputedStyle(document.body).backgroundColor,
      }));
      assert.equal(dark.ink, dark.pageInk);
      assert.equal(dark.ground, 'rgba(0, 0, 0, 0)', 'the list has no fixed light card ground');
      assert.notEqual(dark.pageGround, 'rgb(255, 255, 255)');
      if (mode === 'multi') await page.screenshot({path: path.join(work, 'native-dark-1100.png')});
      await press('c');
      await page.locator('[data-theme="print-ink"]').click();
      await settle();

      if (mode === 'single') {
        await go('notes');
        await press('End');
        await press('ArrowDown');
        assert.equal(await page.title(), 'Unit A', 'bounded navigation cannot enter the next unit');
        await go('p-overview');
        await press('f');
        assert.equal(await page.evaluate(() => !!document.fullscreenElement), true);
        await preset('lightwebpres-docs@0.1.0/docs');
        const link = page.locator('#p-overview [data-lwp-index-target="p-item-1"]');
        assert.equal(await link.getAttribute('href'), route('p-item-1'), 'preset replacement remaps links');
        await link.click();
        await settle();
        assert.equal(await page.evaluate(() => !!document.fullscreenElement), true);
        await page.goBack(); await settle();
        assert.equal(new URL(page.url()).hash, route('p-overview'));
        await page.goForward(); await settle();
        assert.equal(new URL(page.url()).hash, route('p-item-1'));
        await page.evaluate(hash => { location.hash = hash; }, route('p-overview', 'b'));
        await settle();
        assert.equal(await page.title(), 'Unit B');
        assert.equal(await page.locator('#p-overview [data-lwp-index-target="p-item-1"]').getAttribute('href'), route('p-item-1', 'b'));
        assert.deepEqual(await targets(), published, 'same local IDs belong to the active unit');
        assert.equal(await page.evaluate(() => !!document.fullscreenElement), true);
        assert.equal(await page.locator('#p-overview').evaluate(node => getComputedStyle(node).outlineStyle), 'none');
        await press('f');
      } else {
        // Print the real long index alone to isolate its page fragmentation.
        // Text extraction, when supplied, proves continuation on actual PDF
        // sheets rather than merely the screen's emulated print stylesheet.
        await go('p-overview');
        await page.emulateMedia({media: 'print'});
        await page.addStyleTag({content: '.slide:not(#p-overview), .page-footer { display:none !important; }'});
        assert.equal(await page.locator('#p-overview ol').evaluate(node => getComputedStyle(node).display), 'block');
        const printOrder = await targets();
        assert.deepEqual(printOrder, published);
        const pdf = path.join(work, 'index-continuation.pdf');
        await page.pdf({path: pdf, format: 'A4', printBackground: true});
        const extracted = spawnSync('pdftotext', ['-layout', pdf, '-'], {encoding: 'utf8', env: process.env});
        if (extracted.error && extracted.error.code === 'ENOENT') {
          console.log('PDF generated; paper text/order unverified: pdftotext unavailable');
        } else {
          assert.equal(extracted.status, 0, extracted.stderr);
          const sheets = extracted.stdout.split('\f').filter(text => text.trim());
          assert.ok(sheets.length >= 2, 'long native list must continue over paper sheets');
          const text = sheets.join(' ').replace(/\s+/g, ' ');
          let previous = -1;
          for (let i = 0; i < 38; i++) {
            const marker = `${i % 2 ? 'English' : 'French'} item ${String(i).padStart(2, '0')}:`;
            const position = text.indexOf(marker);
            assert.ok(position > previous, `missing/reordered PDF entry ${marker}`);
            assert.equal(text.indexOf(marker, position + marker.length), -1, `duplicated PDF entry ${marker}`);
            previous = position;
          }
          console.log(`native PDF: ${sheets.length} sheets, all 38 long-list entries in source order`);
        }
      }
      await context.close();
    }
    const french = await browser.newContext({locale: 'fr-FR'});
    const frenchPage = await french.newPage();
    frenchPage.on('pageerror', error => errors.push(error.message));
    collectConsoleErrors(frenchPage, errors);
    await frenchPage.goto(base + '/multi/a.html#p-overview');
    await frenchPage.waitForSelector('#p-overview .lwp-unit-index-link');
    assert.equal(await frenchPage.locator('#p-overview nav').getAttribute('aria-label'), 'Sommaire');
    assert.equal(await frenchPage.locator('#p-overview [data-lwp-index-target="p-empty"] .lwp-unit-index-title').textContent(), 'Sommaire');
    assert.equal(await frenchPage.locator('#p-item-1').isVisible(), false,
      'browser language must not assign meaning to expert-fr/expert-en tags');
    await french.close();
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(work, 'measurements.json'), JSON.stringify(measurements, null, 2));
    console.log('unit-index browser checks passed; captures and measurements: ' + work);
  } finally {
    if (server) await new Promise(resolve => server.close(resolve));
    await browser.close();
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
