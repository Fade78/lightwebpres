// Build real decks and compare settled navigation, not just active-dot state.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {spawnSync} = require('node:child_process');

(async () => {
  const root = path.resolve(__dirname, '..');
  const scratch = path.join(root, 'work/tmp');
  process.env.TMPDIR = scratch;
  const work = fs.mkdtempSync(path.join(scratch, 'space-nav-'));
  let browser, server;
  try {
    const {chromium} = require('playwright');
    const executablePath = process.env.PW_CHROMIUM_PATH || chromium.executablePath();
    process.env.XDG_CACHE_HOME = path.join(work, 'cache');
    process.env.XDG_CONFIG_HOME = path.join(work, 'config');
    browser = await chromium.launch({executablePath});
  } catch (error) {
    console.error('Browser check blocked in supplied environment: ' + error.message);
    process.exitCode = 77;
    return;
  }
  try {
    const source = path.join(work, 'series');
    fs.mkdirSync(path.join(source, 'sources'), {recursive: true});
    fs.writeFileSync(path.join(source, 'series.json'), JSON.stringify({
      series_meta: {title: 'Space navigation', reading: {table_mode: 'scroll'}},
      articles: ['a', 'b', 'c'].map(name => ({page_source: name + '.md', page_dest: name + '.html'})),
    }));
    const long = Array.from({length: 8}, (_, i) => `## Long heading ${i}\n\n`
      + 'A paragraph that requires real vertical space while the reader advances through the long article. '.repeat(3)).join('\n\n');
    fs.writeFileSync(path.join(source, 'sources/long.md'), long);
    const slides = [
      '<!-- lwp:slide:cover -->\nslug: cover\nkicker: Navigation\n# Cover heading\nsummary: Read from the cover, without losing alignment.',
      ...[1, 2, 3].map(i => `<!-- lwp:slide -->\nslug: short-${i}\nkicker: Step ${i}\n## Ordinary heading ${i}\nsummary: A short slide with a heading and summary.`),
      '<!-- lwp:slide:full-article -->\nslug: long\narticle: long.md',
      '<!-- lwp:slide -->\nslug: trailing\n## After the long article\nsummary: Enter only after the long slide ends.',
      '<!-- lwp:slide:unit-index -->\nslug: contents',
      '<!-- lwp:slide:series-nav -->\nslug: series',
      '<!-- lwp:slide:full-article -->\nslug: last\narticle: long.md',
    ];
    for (const name of ['a', 'b', 'c']) {
      fs.writeFileSync(path.join(source, `sources/${name}.md`),
        `<!-- lwp:meta -->\npage_title: Article ${name}\n---\n\n` + slides.join('\n\n---\n\n') + '\n');
    }
    const output = path.join(work, 'public');
    const build = spawnSync(process.env.PYTHON || 'python3', [path.join(root, 'lightwebpres'),
      'build', source, '--output', output], {cwd: root, encoding: 'utf8', timeout: 30000,
      env: {...process.env, LWP_IDENTITY_KITS_DIR: path.join(work, 'unused-kits'),
        LWP_THEMES_DIR: path.join(work, 'unused-themes'), LWP_COMMONS_DIR: path.join(work, 'unused-commons')}});
    assert.equal(build.status, 0, build.stdout + build.stderr);
    server = http.createServer((req, res) => {
      const file = path.join(output, decodeURIComponent(new URL(req.url, 'http://localhost').pathname));
      if (!file.startsWith(output + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        res.writeHead(404); res.end(); return;
      }
      res.setHeader('Content-Type', ({'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
        '.svg': 'image/svg+xml'})[path.extname(file)] || 'application/octet-stream');
      res.end(fs.readFileSync(file));
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    const context = await browser.newContext({viewport: {width: 1024, height: 800}});
    await context.route('**/*', route => route.request().url().startsWith(base + '/')
      ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const settle = () => page.waitForTimeout(700);
    async function open(file = 'a.html', hash = '') {
      // A fragment-only goto can retain the preceding card cursor.
      await page.goto('about:blank');
      await page.goto(`${base}/${file}${hash}`);
      await settle();
    }
    async function press(key) { await page.keyboard.press(key); await settle(); }
    async function state() {
      return page.evaluate(() => {
        const slides = [...document.querySelectorAll('.slide')];
        const active = [...document.querySelectorAll('.nav-dots a')].findIndex(d => d.classList.contains('active'));
        const rect = slides[active]?.getBoundingClientRect();
        return {y: window.scrollY, active, top: rect?.top, bottom: rect?.bottom,
          focus: document.activeElement.getAttribute('href')};
      });
    }
    async function action(kind) {
      if (kind === 'click') await page.mouse.click(20, 100);
      else if (kind === 'next') await page.locator('#navNext').click();
      else await page.keyboard.press(kind);
      await settle();
    }
    const forward = {};
    for (const kind of ['ArrowDown', 'Space', 'click', 'next']) {
      await open();
      forward[kind] = [];
      // Covers repeated short-slide transitions and entry/steps within long content.
      for (let i = 0; i < 7; i++) {
        await action(kind);
        const {focus, ...geometry} = await state();
        forward[kind].push(geometry);
      }
    }
    console.log('Forward geometry: ' + JSON.stringify(forward));
    for (const kind of ['Space', 'click', 'next']) {
      assert.deepEqual(forward[kind], forward.ArrowDown, kind + ' must share settled ArrowDown geometry');
    }
    assert.equal(forward.Space[0].top, 0, 'first step aligns the next heading slide');
    assert.equal(forward.Space[3].active, 4, 'fourth step enters the long slide');
    assert.ok(forward.Space[4].y > forward.Space[3].y, 'Space reads within long content');

    const backward = {};
    for (const key of ['ArrowUp', 'Shift+Space']) {
      await open('a.html', '#trailing');
      backward[key] = [];
      for (let i = 0; i < 3; i++) { await press(key); backward[key].push(await state()); }
    }
    assert.deepEqual(backward['Shift+Space'], backward.ArrowUp);
    console.log('Backward geometry: ' + JSON.stringify(backward['Shift+Space']));

    // The last internal step must reach each edge before any adjacent slide.
    for (const [hash, key, edge] of [['#long', 'Space', 'bottom'], ['#last', 'Space', 'bottom'],
      ['#long', 'Shift+Space', 'top']]) {
      await open('a.html', hash);
      const bounds = await page.locator(hash).evaluate((slide, edge) => {
        const rect = slide.getBoundingClientRect();
        const top = rect.top + scrollY, bottom = rect.bottom + scrollY;
        scrollTo({top: edge === 'bottom' ? bottom - innerHeight - 50 : top + 50, behavior: 'instant'});
        return {top, bottom, height: innerHeight};
      }, edge);
      await settle();
      await press(key);
      const atEdge = await state();
      assert.ok(Math.abs(atEdge.y - (edge === 'bottom' ? bounds.bottom - bounds.height : bounds.top)) <= 1,
        'internal step must stop at ' + hash + ' ' + edge + ': ' + JSON.stringify(atEdge));
      if (hash === '#last') { await press(key); assert.deepEqual(await state(), atEdge); }
    }
    await open();
    await press('Shift+Space');
    assert.equal((await state()).y, 0, 'backward at cover stays at the start');

    for (const [file, hash, selector] of [['index.html', '', '.article-card'],
      ['a.html', '#series', '.series-list a.series-link'],
      ['a.html', '#contents', '.lwp-unit-index-link']]) {
      const walks = {};
      for (const key of ['ArrowDown', 'Space']) {
        await open(file, hash);
        const hrefs = await page.locator(selector).evaluateAll(cards => cards.map(c => c.getAttribute('href')));
        assert.ok(hrefs.length >= 3);
        walks[key] = [];
        for (let i = 0; i < 3; i++) {
          await press(key);
          assert.equal((await state()).focus, hrefs[i], key + ' ' + selector + ' step ' + i + ' must focus the next card');
          walks[key].push(await state());
        }
        await press(key === 'Space' ? 'Shift+Space' : 'ArrowUp');
        assert.equal((await state()).focus, hrefs[1]);
      }
      assert.deepEqual(walks.Space, walks.ArrowDown, selector + ' card journey');
      const target = await page.locator(selector).nth(1).evaluate(card => card.href);
      await press('Enter');
      assert.equal(page.url(), target, 'Enter follows the actual focused card target');
      console.log('Card journey OK: ' + selector);
    }

    await open();
    for (let i = 0; i < 8; i++) {
      await page.keyboard.down('Space'); // repeated down while held sets KeyboardEvent.repeat
      await page.waitForTimeout(30);
    }
    await page.keyboard.up('Space');
    await settle();
    const held = await state();
    assert.ok(held.active >= 1 && held.active <= 2, 'held Space must use the 150ms cooldown: ' + JSON.stringify(held));
    console.log('Held Space: ' + JSON.stringify(held));

    await open();
    await page.evaluate(() => document.body.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Spacebar', bubbles: true, cancelable: true})));
    await settle();
    assert.equal((await state()).active, 1, 'legacy Spacebar advances');
    await page.evaluate(() => document.body.dispatchEvent(new KeyboardEvent('keydown',
      {key: 'Spacebar', shiftKey: true, bubbles: true, cancelable: true})));
    await settle();
    assert.equal((await state()).active, 0, 'legacy Shift+Spacebar goes back');

    // Real controls exercise native activation and default scrolling with trusted keys.
    await open();
    await page.evaluate(() => {
      const box = document.createElement('div');
      box.id = 'probe-controls';
      box.style.cssText = 'position:fixed;top:0;left:0;z-index:99999';
      box.innerHTML = '<button id="probe-button">Activate</button><input id="probe-input">'
        + '<textarea id="probe-textarea"></textarea><select id="probe-select"><option>Choice</option></select>'
        + '<div id="probe-editable" contenteditable="true">edit</div>'
        + '<a id="probe-link" href="#trailing">Ordinary link</a>';
      document.body.append(box);
      window.probeClicks = 0;
      document.getElementById('probe-button').onclick = () => window.probeClicks++;
      window.spaceEvents = [];
      document.addEventListener('keydown', e => {
        if (e.key === ' ') window.spaceEvents.push({prevented: e.defaultPrevented, target: e.target.id});
      });
    });
    await page.locator('#probe-button').focus();
    await press('Space');
    assert.equal(await page.evaluate(() => window.probeClicks), 1);
    assert.equal((await state()).y, 0, 'native button does not also navigate');
    for (const id of ['probe-input', 'probe-textarea', 'probe-editable']) {
      await page.locator('#' + id).focus();
      await press('Space');
      assert.equal(await page.evaluate(() => window.spaceEvents.at(-1).prevented), false, id + ' retains Space');
      assert.equal((await state()).y, 0);
    }
    assert.equal(await page.locator('#probe-input').inputValue(), ' ');
    assert.equal(await page.locator('#probe-textarea').inputValue(), ' ');
    await page.locator('#probe-select').focus();
    await press('Space');
    await press('Escape');
    assert.equal((await state()).y, 0, 'select does not navigate');
    await page.locator('#probe-link').focus();
    await press('Space');
    assert.equal(await page.evaluate(() => window.spaceEvents.at(-1).prevented), false);
    assert.ok((await state()).y > 0, 'ordinary link keeps native Space scrolling');
    assert.equal((await state()).focus, '#trailing', 'Space does not activate ordinary links');
    await press('Shift+Space');
    assert.equal((await state()).y, 0, 'ordinary link retains native reverse scrolling');
    await page.locator('#navNext').focus();
    await press('Space');
    assert.equal((await state()).active, 1, 'role button activates once, not twice');

    for (const key of ['Control+Space', 'Meta+Space', 'Alt+Space']) {
      await open();
      await press(key);
      assert.equal((await state()).active, 0, key + ' is not a deck shortcut');
    }

    for (const overflowing of [false, true]) {
      await open();
      await press('n');
      await page.locator('#presenterPanel').evaluate((panel, overflowing) => {
        panel.style.height = '150px';
        panel.style.maxHeight = '150px';
        panel.innerHTML = '<div style="height:' + (overflowing ? 1000 : 30) + 'px">Speaker notes</div>';
        panel.tabIndex = 0;
        panel.focus({preventScroll: true});
      }, overflowing);
      const before = await state();
      await press('Space');
      assert.deepEqual(await state(), before, 'focused speaker notes own Space even without overflow');
      const panelY = await page.locator('#presenterPanel').evaluate(p => p.scrollTop);
      assert.equal(panelY > 0, overflowing);
      await press('Shift+Space');
      assert.equal(await page.locator('#presenterPanel').evaluate(p => p.scrollTop), 0);
      assert.deepEqual(await state(), before);
    }
    for (const [key, selector] of [['h', '#helpOverlay'], ['m', '#presenterMenu']]) {
      await open();
      await press(key);
      await page.locator(selector).evaluate(panel => {
        panel.tabIndex = 0; panel.focus({preventScroll: true});
      });
      const before = await state();
      await press('Space');
      await press('Shift+Space');
      assert.deepEqual(await state(), before, selector + ' retains Space');
    }
    // Existing table isolation stays unchanged, even without overflow.
    await open();
    await page.evaluate(() => {
      const table = document.createElement('div');
      table.className = 'lwp-table-viewport';
      table.tabIndex = 0;
      table.textContent = 'Local table viewport';
      document.querySelector('.slide').append(table);
      table.focus({preventScroll: true});
    });
    const tableBefore = await state();
    await press('Space'); await press('Shift+Space');
    assert.deepEqual(await state(), tableBefore, 'table consumes Space at an edge');
    assert.deepEqual(errors, []);
    console.log('Space navigation checks passed');
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
