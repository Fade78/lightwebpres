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
      series_meta: {title: 'Space navigation', default_tag: 'technical',
        reading: {table_mode: 'scroll'}},
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
        `<!-- lwp:meta -->\n${name === 'b' ? 'tags: technical\n' : ''}`
          + `page_title: Article ${name}\n---\n\n` + slides.join('\n\n---\n\n') + '\n');
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
    async function open(file = 'a.html', hash = '', tag = null) {
      // A fragment-only goto can retain the preceding card cursor.
      await page.goto('about:blank');
      await page.goto(`${base}/${file}${hash}`);
      await settle();
      if (tag) {
        await press('l');
        await page.locator(`.tag-option[data-tag="${tag}"]`).click();
        await settle();
      }
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
    for (const kind of ['PageDown', 'next']) {
      await open();
      forward[kind] = [];
      // PageDown and the buttons are direct slide navigation. They must not
      // inherit the bounded Space journey when the target is a long slide.
      for (let i = 0; i < 7; i++) {
        await action(kind);
        const {focus, ...geometry} = await state();
        forward[kind].push(geometry);
      }
    }
    console.log('Forward geometry: ' + JSON.stringify(forward));
    for (const kind of ['next']) {
      assert.deepEqual(forward[kind], forward.PageDown, kind + ' must share settled PageDown geometry');
    }
    assert.equal(forward.PageDown[0].top, 0, 'first PageDown aligns the next slide');
    assert.equal(forward.PageDown[3].active, 4, 'fourth PageDown enters the long slide');
    assert.equal(forward.PageDown[4].active, 5, 'PageDown leaves the long slide directly');

    await open();
    const arrowStart = await state();
    await page.keyboard.press('ArrowDown');
    await settle();
    const arrowDown = await state();
    assert.equal(arrowDown.active, arrowStart.active, 'ArrowDown must scroll, not change the slide');
    assert(arrowDown.y > arrowStart.y, 'ArrowDown must scroll the document');
    await page.keyboard.press('ArrowUp');
    await settle();
    const arrowUp = await state();
    assert.equal(arrowUp.active, arrowStart.active, 'ArrowUp must scroll, not change the slide');
    assert.equal(arrowUp.y, arrowStart.y, 'ArrowUp must return to the starting position');
    await page.mouse.wheel(0, 400);
    await settle();
    const wheel = await state();
    assert.equal(wheel.active, arrowStart.active, 'wheel must scroll, not change the slide');
    assert(wheel.y > arrowStart.y, 'wheel must scroll the document');

    await open();
    const space = [];
    for (let i = 0; i < 7; i++) {
      await action('Space');
      space.push(await state());
    }
    assert.equal(space[0].active, 1, 'Space keeps its first reading step');
    assert.equal(space[3].active, 4, 'Space enters the long slide');
    assert(space[4].y > space[3].y, 'Space keeps bounded reading within long content');

    const backward = {};
    for (const key of ['PageUp', 'Shift+Space']) {
      await open('a.html', '#trailing');
      backward[key] = [];
      for (let i = 0; i < 3; i++) { await press(key); backward[key].push(await state()); }
    }
    assert.deepEqual(backward['Shift+Space'], backward.PageUp);
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
      for (const key of ['Space']) {
        await open(file, hash);
        const hrefs = await page.locator(selector).evaluateAll(cards => cards.map(c => c.getAttribute('href')));
        assert.ok(hrefs.length >= 3);
        walks[key] = [];
        for (let i = 0; i < 3; i++) {
          await press(key);
          assert.equal((await state()).focus, hrefs[i], key + ' ' + selector + ' step ' + i + ' must focus the next card');
          walks[key].push(await state());
        }
         await press('Shift+Space');
         assert.equal((await state()).focus, hrefs[1]);
       }
      const target = await page.locator(selector).nth(1).evaluate(card => card.href);
      await press('Enter');
      assert.equal(page.url(), target, 'Enter follows the actual focused card target');
      console.log('Card journey OK: ' + selector);
    }

    // The wheel has a narrow card-cursor role only while it is over a card
    // list. It chooses one link at a time without following it, and native
    // page scrolling resumes at the first and last card.
    async function wheelOnCard(locator, deltaY, deltaX = 0) {
      await locator.scrollIntoViewIfNeeded();
      const box = await locator.boundingBox();
      assert.ok(box, 'the wheel target must be visible');
      await page.mouse.move(box.x + Math.min(20, box.width / 2),
        box.y + Math.min(20, box.height / 2));
      await page.mouse.wheel(deltaX, deltaY);
      await settle();
    }
    async function moveToCard(locator) {
      await locator.scrollIntoViewIfNeeded();
      const box = await locator.boundingBox();
      assert.ok(box, 'the pointer target must be visible');
      const point = {x: box.x + Math.min(20, box.width / 2),
        y: box.y + Math.min(20, box.height / 2)};
      await page.mouse.move(point.x, point.y);
      return {box, point};
    }
    async function selectedCard() {
      return page.evaluate(() => {
        const card = document.querySelector('.lwp-card-selected');
        return {
          href: card && card.getAttribute('href'),
          focused: card === document.activeElement,
          outlined: card && getComputedStyle(card).outlineStyle,
        };
      });
    }
    async function wheelDefaultPrevented(locator, deltaY, modifier, deltaX = 0) {
      await page.evaluate(() => {
        window.__lwpWheelDefaultPrevented = null;
        document.addEventListener('wheel', event => {
          window.__lwpWheelDefaultPrevented = event.defaultPrevented;
        }, {once: true});
      });
      if (modifier) await page.keyboard.down(modifier);
      await wheelOnCard(locator, deltaY, deltaX);
      if (modifier) await page.keyboard.up(modifier);
      return page.evaluate(() => window.__lwpWheelDefaultPrevented);
    }
    for (const [file, hash, selector] of [['index.html', '', '.article-card'],
      ['a.html', '#series', '.series-list a.series-link'],
      ['a.html', '#contents', '.lwp-unit-index-link']]) {
      await open(file, hash);
      const cards = page.locator(selector);
      const hrefs = await cards.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
      assert.ok(hrefs.length >= 3, 'wheel fixture needs three cards: ' + selector);
      const beforeUrl = page.url();
      await wheelOnCard(cards.nth(0), 400);
      assert.deepEqual(await selectedCard(), {href: hrefs[0], focused: true, outlined: 'solid'},
        'wheel selects, but does not activate, the first ' + selector + ' card');
      assert.equal(page.url(), beforeUrl, 'wheel must not follow the selected card');
      await wheelOnCard(cards.nth(0), 400);
      assert.deepEqual(await selectedCard(), {href: hrefs[1], focused: true, outlined: 'solid'},
        'wheel moves one ' + selector + ' card forward');
      await wheelOnCard(cards.nth(1), -400);
      assert.deepEqual(await selectedCard(), {href: hrefs[0], focused: true, outlined: 'solid'},
        'reverse wheel moves one ' + selector + ' card backward');
    }
    // A mouse-only reader can follow the card selected by the wheel without
    // needing Enter. The pointer deliberately stays over the first card while
    // the wheel has selected the second one, so the long press must follow the
    // selection rather than the link under the pointer.
    for (const [file, hash, selector] of [['index.html', '', '.article-card'],
      ['a.html', '#series', '.series-list a.series-link'],
      ['a.html', '#contents', '.lwp-unit-index-link']]) {
      await open(file, hash);
      const cards = page.locator(selector);
      const hrefs = await cards.evaluateAll(nodes => nodes.map(node => node.href));
      await wheelOnCard(cards.nth(0), 400);
      await wheelOnCard(cards.nth(0), 400);
      const target = hrefs[1];
      const navigation = page.waitForURL(target, {timeout: 5000});
      await page.mouse.down();
      await page.waitForTimeout(550);
      await page.mouse.up();
      await navigation;
      assert.equal(page.url(), target,
        'long left press must follow the wheel-selected ' + selector + ' card');
    }
    console.log('Mouse-only long press follows the wheel selection OK');
    // A filtered-out series-navigation card must leave both the wheel cursor
    // and the long press path; only visible cards remain in the journey.
    await open('a.html', '#series');
    const filteredCards = page.locator('.series-list a.series-link');
    await filteredCards.nth(0).evaluate(card => card.setAttribute('data-lwp-article-tags', 'technical'));
    await press('l');
    await page.locator('.tag-option[data-tag="default"]').click();
    await settle();
    const visibleCards = page.locator('.series-list a.series-link:not([hidden])');
    const visibleHrefs = await visibleCards.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
    assert.equal(await filteredCards.nth(0).getAttribute('aria-hidden'), 'true');
    assert.equal(visibleHrefs.length, 2, 'the filtered card list keeps its visible back link');
    await wheelOnCard(visibleCards.nth(0), 400);
    assert.deepEqual(await selectedCard(), {href: visibleHrefs[0], focused: true, outlined: 'solid'},
      'wheel starts at the first visible series-navigation card');
    await wheelOnCard(visibleCards.nth(0), 400);
    assert.deepEqual(await selectedCard(), {href: visibleHrefs[1], focused: true, outlined: 'solid'},
      'wheel skips the filtered series-navigation card');
    const filteredTarget = await visibleCards.nth(1).evaluate(card => card.href);
    const filteredNavigation = page.waitForURL(filteredTarget, {timeout: 5000});
    await page.mouse.down();
    await page.waitForTimeout(550);
    await page.mouse.up();
    await filteredNavigation;
    assert.equal(page.url(), filteredTarget, 'long press follows a visible filtered-list selection');

    // Changing the filter after a wheel selection cancels a pending hold,
    // including when the selected card is the one hidden.
    await open('a.html', '#series', 'technical');
    const reFilteredCards = page.locator('.series-list a.series-link');
    await wheelOnCard(reFilteredCards.nth(0), 400);
    await moveToCard(reFilteredCards.nth(0));
    await page.evaluate(() => {
      window.__filteredCardClicks = 0;
      document.querySelector('.series-list a.series-link').addEventListener('click', () => {
        window.__filteredCardClicks += 1;
      });
    });
    await page.mouse.down();
    await page.waitForTimeout(100);
    await page.keyboard.press('l');
    await page.evaluate(() => document.querySelector('.tag-option[data-tag="default"]').click());
    await page.waitForTimeout(550);
    await page.mouse.up();
    await settle();
    assert.equal(await page.evaluate(() => window.__filteredCardClicks), 0,
      'changing the filter cancels the pending hold');
    assert.deepEqual(await selectedCard(), {href: null, focused: false, outlined: null},
      'changing the filter clears a wheel-selected card');

    // The first wheel in the new filtered context is accepted immediately:
    // the filter transition must reset both the cursor and its debounce.
    await open('a.html', '#series', 'technical');
    const immediateFilterCards = page.locator('.series-list a.series-link');
    await page.evaluate(() => {
      const first = document.querySelector('.series-list a.series-link');
      first.dispatchEvent(new WheelEvent('wheel', {
        bubbles: true, cancelable: true, deltaX: 0, deltaY: 400,
      }));
      document.dispatchEvent(new KeyboardEvent('keydown', {
        bubbles: true, cancelable: true, key: 'l', code: 'KeyL', keyCode: 76,
      }));
      first.setAttribute('data-lwp-article-tags', 'technical');
      document.querySelector('.tag-option[data-tag="default"]').click();
      const visible = [...document.querySelectorAll('.series-list a.series-link')]
        .filter(card => !card.hidden && card.getAttribute('aria-hidden') !== 'true');
      visible[0].dispatchEvent(new WheelEvent('wheel', {
        bubbles: true, cancelable: true, deltaX: 0, deltaY: 400,
      }));
    });
    await settle();
    const immediateVisibleHrefs = await page.locator(
      '.series-list a.series-link:not([hidden])').evaluateAll(
        nodes => nodes.map(node => node.getAttribute('href')));
    assert.deepEqual(await selectedCard(), {
      href: immediateVisibleHrefs[0], focused: true, outlined: 'solid',
    }, 'the first wheel after filtering is accepted immediately');
    await press('l');
    await page.locator('.tag-option[data-tag="technical"]').click();
    await settle();

    // A card selected by Space has the same visual class, but must not arm
    // the mouse-only shortcut. The native click therefore follows the link
    // under the pointer, not the keyboard-selected card.
    await open('a.html', '#series');
    const keyboardCards = page.locator('.series-list a.series-link');
    const keyboardHrefs = await keyboardCards.evaluateAll(nodes => nodes.map(node => node.href));
    await press('Space');
    await moveToCard(keyboardCards.nth(1));
    const keyboardTarget = keyboardHrefs[1];
    const keyboardNavigation = page.waitForURL(keyboardTarget, {timeout: 5000});
    await page.mouse.down();
    await page.waitForTimeout(550);
    await page.mouse.up();
    await keyboardNavigation;
    assert.equal(page.url(), keyboardTarget,
      'a long press after Space must keep the native pointer target');

    async function wheelSelectSecondSeriesCard() {
      await open('a.html', '#series');
      const cards = page.locator('.series-list a.series-link');
      const hrefs = await cards.evaluateAll(nodes => nodes.map(node => node.href));
      await wheelOnCard(cards.nth(0), 400);
      await wheelOnCard(cards.nth(0), 400);
      return {cards, hrefs};
    }
    // Wheel input owns its own debounce window: a wheel immediately after a
    // Space step must still move the card cursor.
    {
      await open('a.html', '#series');
      const cards = page.locator('.series-list a.series-link');
      const hrefs = await cards.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
      await page.keyboard.press('Space');
      await cards.nth(0).dispatchEvent('wheel', {
        bubbles: true, cancelable: true, deltaX: 0, deltaY: 400,
      });
      await settle();
      assert.deepEqual(await selectedCard(), {href: hrefs[1], focused: true, outlined: 'solid'},
        'wheel input is not dropped after a Space step');
    }
    // A burst of wheel events still owns the gesture, but advances only once
    // during the 150ms debounce window.
    {
      await open('a.html', '#series');
      const cards = page.locator('.series-list a.series-link');
      const hrefs = await cards.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
      await page.evaluate(() => {
        const card = document.querySelector('.series-list a.series-link');
        const init = {bubbles: true, cancelable: true, deltaX: 0, deltaY: 400};
        card.dispatchEvent(new WheelEvent('wheel', init));
        card.dispatchEvent(new WheelEvent('wheel', init));
      });
      await settle();
      assert.deepEqual(await selectedCard(), {href: hrefs[0], focused: true, outlined: 'solid'},
        'a rapid wheel burst advances only once');
    }
    // A later focus handoff owns the cursor. A stale wheel selection must not
    // override the card that received keyboard or programmatic focus.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await cards.nth(0).focus();
      const {point} = await moveToCard(cards.nth(0));
      const navigation = page.waitForURL(hrefs[0], {timeout: 5000});
      await page.mouse.down();
      await page.waitForTimeout(550);
      await page.mouse.up();
      await navigation;
      assert.equal(page.url(), hrefs[0], 'focus handoff clears the stale wheel selection');
    }
    // Short clicks remain ordinary link activation even after the wheel has
    // selected a different card.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      const {point} = await moveToCard(cards.nth(0));
      const navigation = page.waitForURL(hrefs[0], {timeout: 5000});
      await page.mouse.click(point.x, point.y);
      await navigation;
      assert.equal(page.url(), hrefs[0], 'a short click follows its own card');
    }
    // Moving beyond the radial press slop cancels the timer, even when the
    // pointer returns to its original card before release. Each axis stays
    // below 4px so this also protects the total-distance interpretation.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      const {point} = await moveToCard(cards.nth(0));
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.mouse.move(point.x + 3, point.y + 3);
      await page.mouse.move(point.x, point.y);
      await page.waitForTimeout(500);
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'movement cancels the long press');
    }
    // A modifier pressed and released during the hold must cancel too; the
    // pointer-up event alone cannot be the only place that checks it.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await moveToCard(cards.nth(0));
      const navigation = page.waitForURL(hrefs[0], {timeout: 5000});
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.keyboard.down('Shift');
      await page.waitForTimeout(500);
      await page.keyboard.up('Shift');
      await page.mouse.up();
      await navigation;
      assert.equal(page.url(), hrefs[0], 'a modifier cancels the long press');
    }
    // Opening help during the hold cancels the pending card action instead of
    // letting the release activate the card behind the overlay.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await moveToCard(cards.nth(0));
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.keyboard.press('h');
      await page.waitForTimeout(550);
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'help cancels the long press');
      await page.keyboard.press('h');
      await settle();
    }
    // F is another competing presentation gesture and must have the same
    // cancellation behavior. Escape restores the pre-test fullscreen state.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await moveToCard(cards.nth(0));
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.keyboard.press('f');
      await page.waitForTimeout(550);
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'fullscreen entry cancels the long press');
      await page.keyboard.press('Escape');
      await settle();
    }
    // A middle-button gesture can arm fullscreen while the left button is
    // still held. It must invalidate the pending card activation immediately.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await moveToCard(cards.nth(0));
      await page.mouse.down({button: 'left'});
      await page.waitForTimeout(100);
      await page.mouse.down({button: 'middle'});
      await page.mouse.up({button: 'middle'});
      await page.waitForTimeout(550);
      await page.mouse.up({button: 'left'});
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'middle-button intent cancels the long press');
    }
    // Pointer cancellation is a terminal gesture event, not a delayed click.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      await moveToCard(cards.nth(0));
      await page.evaluate(() => {
        window.__lwpLongPressPointerId = null;
        document.addEventListener('pointerdown', event => {
          if (event.pointerType === 'mouse') window.__lwpLongPressPointerId = event.pointerId;
        }, {capture: true, once: true});
      });
      await page.mouse.down();
      const pointerId = await page.evaluate(() => window.__lwpLongPressPointerId);
      assert.ok(pointerId !== null, 'the cancellation probe must observe the mouse pointer');
      await page.evaluate(id => document.dispatchEvent(new PointerEvent('pointercancel', {
        bubbles: true, cancelable: true, isPrimary: true, pointerId: id,
        pointerType: 'mouse', button: 0, buttons: 0,
      })), pointerId);
      await page.waitForTimeout(550);
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'pointer cancellation cancels the long press');
    }
    // The release coordinates are checked too: a terminal event can arrive
    // without a preceding move notification after the pointer crossed the
    // radial slop.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      const {point} = await moveToCard(cards.nth(0));
      await page.evaluate(() => {
        window.__lwpLongPressPointerId = null;
        document.addEventListener('pointerdown', event => {
          if (event.pointerType === 'mouse') window.__lwpLongPressPointerId = event.pointerId;
        }, {capture: true, once: true});
      });
      await page.mouse.down();
      const pointerId = await page.evaluate(() => window.__lwpLongPressPointerId);
      assert.ok(pointerId !== null, 'the release probe must observe the mouse pointer');
      await page.waitForTimeout(550);
      await page.evaluate(({id, point}) => document.dispatchEvent(new PointerEvent('pointerup', {
        bubbles: true, cancelable: true, isPrimary: true, pointerId: id,
        pointerType: 'mouse', button: 0, buttons: 0,
        clientX: point.x + 3, clientY: point.y + 3,
      })), {id: pointerId, point});
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'release displacement cancels the long press');
    }
    // A table remains a local reading surface even while a card selection is
    // present elsewhere on the page.
    {
      await wheelSelectSecondSeriesCard();
      const before = page.url();
      await page.evaluate(() => {
        const viewport = document.createElement('div');
        viewport.id = 'long-press-table';
        viewport.className = 'lwp-table-viewport';
        viewport.style.cssText = 'position:fixed;top:20px;left:20px;z-index:99999;'
          + 'width:240px;height:80px;overflow:auto;background:white';
        viewport.innerHTML = '<table><tbody><tr><td>Local table</td></tr></tbody></table>';
        document.body.append(viewport);
      });
      const tableCell = page.locator('#long-press-table td');
      await moveToCard(tableCell);
      await page.mouse.down();
      await page.waitForTimeout(550);
      await page.mouse.up();
      await settle();
      assert.equal(page.url(), before, 'a table hold stays local');
    }
    // Selection cancels activation instead of following either card. This is
    // intentionally kept selected until pointer-up to exercise the release
    // guard as well as selectionchange.
    {
      const {cards, hrefs} = await wheelSelectSecondSeriesCard();
      const {point} = await moveToCard(cards.nth(0));
      await page.mouse.down();
      await page.waitForTimeout(100);
      await page.evaluate(() => {
        const card = document.querySelector('.series-list a.series-link');
        const range = document.createRange();
        range.selectNodeContents(card);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      });
      await page.waitForTimeout(50);
      assert.ok(await page.evaluate(() => String(window.getSelection())),
        'the cancellation probe must create a text selection');
      await page.waitForTimeout(550);
      await page.mouse.move(point.x, point.y);
      await page.mouse.up();
      await settle();
      assert.notEqual(page.url(), hrefs[1], 'text selection cancels the long press');
    }
    // A touch pointer never arms the mouse-only timer, even if a wheel
    // selection is still present.
    {
      const {cards} = await wheelSelectSecondSeriesCard();
      const before = page.url();
      await cards.nth(0).evaluate(card => {
        const rect = card.getBoundingClientRect();
        const init = {bubbles: true, cancelable: true, isPrimary: true,
          pointerId: 91, pointerType: 'touch', button: 0,
          clientX: rect.left + 10, clientY: rect.top + 10};
        card.dispatchEvent(new PointerEvent('pointerdown', init));
      });
      await page.waitForTimeout(550);
      await cards.nth(0).evaluate(card => {
        const rect = card.getBoundingClientRect();
        card.dispatchEvent(new PointerEvent('pointerup', {bubbles: true, cancelable: true,
          isPrimary: true, pointerId: 91, pointerType: 'touch', button: 0, buttons: 0,
          clientX: rect.left + 10, clientY: rect.top + 10}));
      });
      assert.equal(page.url(), before, 'touch must not activate the mouse long press');
    }
    for (const [file, hash, selector] of [['index.html', '', '.article-card'],
      ['a.html', '#series', '.series-list a.series-link'],
      ['a.html', '#contents', '.lwp-unit-index-link']]) {
      await open(file, hash);
      const cards = page.locator(selector);
      const count = await cards.count();
      await cards.nth(0).focus();
      assert.equal(await wheelDefaultPrevented(cards.nth(0), -400), false,
        'wheel above a keyboard-focused first ' + selector + ' card must remain native');
      await cards.nth(count - 1).focus();
      assert.equal(await wheelDefaultPrevented(cards.nth(count - 1), 400), false,
        'wheel below a keyboard-focused last ' + selector + ' card must remain native');
    }
    for (const [file, hash, selector] of [['index.html', '', '.article-card'],
      ['a.html', '#series', '.series-list a.series-link'],
      ['a.html', '#contents', '.lwp-unit-index-link']]) {
      await open(file, hash);
      const cards = page.locator(selector);
      for (const modifier of ['Control', 'Meta', 'Shift', 'Alt']) {
        assert.equal(await wheelDefaultPrevented(cards.nth(0), 400, modifier), false,
          modifier + ' wheel over ' + selector + ' must remain native');
        assert.deepEqual(await selectedCard(), {href: null, focused: false, outlined: null},
          modifier + ' wheel over ' + selector + ' must not select a card');
      }
    }
    await open('index.html');
    const diagonalCards = page.locator('.article-card');
    const diagonalPrevented = await diagonalCards.nth(0).evaluate(card => {
      const event = new WheelEvent('wheel', {
        bubbles: true, cancelable: true, deltaX: 400, deltaY: 100,
      });
      card.dispatchEvent(event);
      return event.defaultPrevented;
    });
    assert.equal(diagonalPrevented, false,
      'a horizontally dominant wheel over a card must remain native');
    assert.deepEqual(await selectedCard(), {href: null, focused: false, outlined: null},
      'a horizontally dominant wheel must not select a card');

    async function spaceStartsCurrentCardJourney(changeSlide) {
      await open('a.html', '#contents');
      const contentsCards = page.locator('.lwp-unit-index-link');
      await wheelOnCard(contentsCards.nth(0), 400);
      if (changeSlide) await press('PageDown');
      else await page.evaluate(() => {
        const slide = document.getElementById('series');
        scrollTo({top: scrollY + slide.getBoundingClientRect().top, behavior: 'instant'});
      });
      await settle();
      const seriesCards = page.locator('.series-list a.series-link');
      const firstHref = await seriesCards.nth(0).getAttribute('href');
      await press('Space');
      assert.deepEqual(await selectedCard(), {href: firstHref, focused: true, outlined: 'solid'},
        'Space must start the card journey after its former card loses focus');
    }
    await spaceStartsCurrentCardJourney(true);
    await spaceStartsCurrentCardJourney(false);
    await open('index.html');
    let indexCards = page.locator('.article-card');
    await indexCards.nth(1).focus();
    assert.equal(await page.locator('#navPrev').getAttribute('aria-disabled'), 'false',
      'native focus on an interior index card enables Previous');
    assert.equal(await page.locator('#navNext').getAttribute('aria-disabled'), 'false',
      'native focus on an interior index card keeps Next enabled');
    await indexCards.nth((await indexCards.count()) - 1).focus();
    assert.equal(await page.locator('#navNext').getAttribute('aria-disabled'), 'true',
      'native focus on the final index card disables Next');
    console.log('Wheel card cursor and native boundaries OK');

    await open();
    await page.evaluate(() => {
      for (let i = 0; i < 8; i++) document.body.dispatchEvent(new KeyboardEvent('keydown', {
        key: ' ', code: 'Space', repeat: i > 0, bubbles: true, cancelable: true,
      }));
    });
    await settle();
    const held = await state();
    assert.equal(held.active, 1, 'a held Space burst must use the 150ms cooldown: ' + JSON.stringify(held));
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
      const keys = overflowing
        ? ['Space']
        : ['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft',
           'PageDown', 'PageUp', 'Home', 'End', 'Space'];
      for (const key of keys) await press(key);
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
