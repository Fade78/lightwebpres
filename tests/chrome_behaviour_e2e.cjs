// Playwright driver for three behaviours of the page chrome that only a
// real browser can settle, all three reported from the field and all
// three invisible to a string assertion against the generated HTML:
//
//   - Releasing the mouse after highlighting text must NOT advance the
//     deck. The click handler sees an ordinary click at the end of a
//     drag-select; nothing in the markup says whether it acts on it.
//   - The cursor, hidden in fullscreen, must come back only after
//     sustained movement. The old code armed a timer on the second move
//     and let it fire whether or not anything kept moving, so a knock
//     against the desk revealed it 250ms later — a delay, not a
//     condition.
//   - F must enter fullscreen on the index, as it does on an article
//     page. The index simply never bound it.
//
// Invoked by tests/test_chrome_behaviour.py — not a standalone entry
// point.
//
// argv: <articleUrl> <indexUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

function fail(msg) {
  console.error('E2E failure: ' + msg);
  process.exitCode = 1;
}

async function currentSlide(page) {
  return page.evaluate(() => {
    const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
    return dots.findIndex((d) => d.classList.contains('active'));
  });
}

// A drag over a paragraph, in real pointer events: press inside the text,
// move across it in steps, release. The `steps` option is not
// decoration: a bare move teleports the pointer and Chromium takes no
// selection from it, so the drag under test never happens. Measured.
async function dragAcross(page, selector) {
  const box = await page.locator(selector).first().boundingBox();
  if (!box) throw new Error('no box for ' + selector);
  // The FIRST line, not the vertical middle. Measured: a two-line
  // summary is 67px tall and its middle runs along the gap between the
  // lines, where there is no text to take — the drag then selects
  // nothing and the case under test never happens.
  const y = box.y + 8;
  await page.mouse.move(box.x + 6, y);
  await page.mouse.down();
  for (let i = 1; i <= 6; i++) {
    await page.mouse.move(box.x + 6 + (box.width - 12) * (i / 6), y,
                          { steps: 4 });
  }
  await page.mouse.up();
}

async function main() {
  const [articleUrl, indexUrl] = process.argv.slice(2);
  // The full browser when the environment names one. Measured: the
  // headless shell build takes no text selection from synthetic pointer
  // events, so the drag under test silently becomes a click and the
  // assertion that would have caught a regression never runs.
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(
    executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  collectConsoleErrors(page, errors);

  // --- 1. A drag-select does not advance the deck ---------------------
  await page.goto(articleUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  const before = await currentSlide(page);
  await dragAcross(page, '.slide-cover .summary');
  // Well past CLICK_DELAY (250ms), so a pending single-click timer would
  // have fired by now if one had been armed.
  await page.waitForTimeout(600);
  const selected = await page.evaluate(() => String(window.getSelection()).length);
  const after = await currentSlide(page);
  if (selected === 0) {
    fail('the drag selected nothing, so the case under test never happened');
  }
  if (after !== before) {
    fail('a drag-select advanced the deck: slide ' + before + ' -> ' + after);
  }

  // --- 2. A plain click still advances -------------------------------
  // Without this, test 1 passes on a page where clicking does nothing at
  // all, which is the failure mode a guard against advancing invites.
  await page.evaluate(() => window.getSelection().removeAllRanges());
  const box = await page.locator('.slide').first().boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height - 40);
  await page.waitForTimeout(900);
  const advanced = await currentSlide(page);
  if (advanced === before) {
    fail('an ordinary click no longer advances the deck');
  }

  // --- 3. The cursor AND the buttons come back only on sustained
  //        movement, together ------------------------------------------
  // Both halves of one gesture, on one clock. The buttons used to come
  // back on the first move while the cursor held for a quarter of a
  // second, so a knock against the desk put the chrome back on the wall
  // and the protection was half a protection.
  // Driven through the page's own listener with synthetic events, so the
  // timing is the script's and not the harness's. Headless Chromium will
  // not grant fullscreen without a gesture, so the handler is exercised
  // directly: what is under test is the reveal condition, not the
  // fullscreen API.
  const cursorVerdict = await page.evaluate(() => {
    return new Promise((resolve) => {
      const send = () => document.dispatchEvent(new MouseEvent('mousemove', {
        clientX: 100, clientY: 100, bubbles: true,
      }));
      // No fullscreen anywhere in this test, deliberately: the cursor
      // answers to the same clock as the navigation chrome now, in
      // every mode, and it used to answer only in fullscreen — which is
      // the report this covers.
      const nav = document.querySelector('.nav-buttons');
      const idle = () => (nav ? nav.classList.contains('idle') : null);
      // The scroll bar answers to the same class, on the root: read the
      // COMPUTED colour, not the class, so the CSS rule is under test
      // and not just the toggle that arms it.
      const bar = () => getComputedStyle(document.documentElement).scrollbarColor;
      document.body.style.cursor = 'none';
      if (nav) nav.classList.add('idle');
      document.documentElement.classList.add('nav-idle');
      // A twitch: two events one frame apart, then nothing.
      send();
      setTimeout(() => {
        send();
        setTimeout(() => {
          const afterTwitch = document.body.style.cursor;
          const navAfterTwitch = idle();
          const barAfterTwitch = bar();
          // A real movement: events every 30ms for 400ms.
          const started = Date.now();
          const timer = setInterval(() => {
            send();
            if (Date.now() - started > 400) {
              clearInterval(timer);
              resolve({
                afterTwitch, navAfterTwitch, barAfterTwitch,
                afterMoving: document.body.style.cursor,
                navAfterMoving: idle(),
                barAfterMoving: bar(),
              });
            }
          }, 30);
        }, 400);
      }, 16);
    });
  });
  if (cursorVerdict.afterTwitch !== 'none') {
    fail('a two-event twitch revealed the cursor: ' + JSON.stringify(cursorVerdict));
  }
  if (cursorVerdict.afterMoving !== '') {
    fail('sustained movement did not reveal the cursor: ' + JSON.stringify(cursorVerdict));
  }
  if (cursorVerdict.navAfterTwitch !== true) {
    fail('a two-event twitch brought the navigation back: ' + JSON.stringify(cursorVerdict));
  }
  if (cursorVerdict.navAfterMoving !== false) {
    fail('sustained movement did not bring the navigation back: ' + JSON.stringify(cursorVerdict));
  }
  // The scroll bar is navigation: transparent while idle, painted again
  // once the movement has earned it. Compared as "did the value change",
  // because the resting value is the theme's and not this test's to name.
  if (!/rgba\(0, 0, 0, 0\)/.test(cursorVerdict.barAfterTwitch)) {
    fail('a two-event twitch repainted the scroll bar: ' + JSON.stringify(cursorVerdict));
  }
  if (/rgba\(0, 0, 0, 0\)/.test(cursorVerdict.barAfterMoving)) {
    fail('sustained movement did not repaint the scroll bar: ' + JSON.stringify(cursorVerdict));
  }

  // --- 3b. And it hides again on its own, outside fullscreen ---------
  // The chrome's idle delay is 3s off fullscreen, so 4s of stillness is
  // past it with room to spare.
  await page.waitForTimeout(4000);
  const restingCursor = await page.evaluate(() => document.body.style.cursor);
  if (restingCursor !== 'none') {
    fail('the cursor did not hide outside fullscreen: ' + JSON.stringify(restingCursor));
  }

  // --- 4. F is bound on the index ------------------------------------
  // Headless Chromium refuses the fullscreen request itself, so what is
  // asserted is that the key REACHES a handler: the page calls
  // requestFullscreen. Stubbing it is the only way to see the call
  // without a user gesture, and it is the whole of what was missing —
  // the index bound no handler at all.
  const indexPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await indexPage.goto(indexUrl, { waitUntil: 'load' });
  await indexPage.evaluate(() => {
    window.__askedForFullscreen = 0;
    document.documentElement.requestFullscreen = function () {
      window.__askedForFullscreen++;
      return Promise.resolve();
    };
  });
  await indexPage.keyboard.press('f');
  await indexPage.waitForTimeout(200);
  const asked = await indexPage.evaluate(() => window.__askedForFullscreen);
  if (asked !== 1) {
    fail('F on the index did not ask for fullscreen (asked ' + asked + ' times)');
  }
  const hasButton = await indexPage.locator('#navFullscreen').count();
  if (hasButton !== 1) {
    fail('the index has no fullscreen button');
  }

  // --- 4b. Scrolling moves the address bar with the reader ------------
  // Reported from the field: the fragment was written only by goTo, so a
  // reader who SCROLLED to a card kept whatever `#id` their last jump had
  // left behind. Press F5 and the page obeys that stale fragment — the
  // reader is teleported to a card they left minutes ago. A page that
  // lies about where you are, and lies worst at the moment you ask it to
  // remember.
  //
  // Scrolled with the wheel rather than with goTo: what is under test is
  // the path that does NOT go through the jump.
  const scrollPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  collectConsoleErrors(scrollPage, errors);
  await scrollPage.goto(articleUrl, { waitUntil: 'load' });
  await scrollPage.waitForTimeout(300);
  const atRest = await scrollPage.evaluate(
    () => ({ hash: location.hash, entries: history.length }));
  if (atRest.hash !== '') {
    fail('a freshly loaded page already carries a fragment: ' + atRest.hash);
  }
  // Two cards down, then let the 80ms scroll debounce settle.
  await scrollPage.mouse.wheel(0, 1700);
  await scrollPage.waitForTimeout(800);
  const scrolled = await scrollPage.evaluate(() => ({
    hash: location.hash,
    // What the page itself says is the current card, read from the dot
    // it marks active — so this compares the URL against the page's own
    // answer rather than against a number this test guessed.
    active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
      .findIndex((d) => d.classList.contains('active')),
    ids: Array.prototype.slice.call(document.querySelectorAll('section.slide'))
      .map((s) => s.id),
    entries: history.length,
  }));
  if (!scrolled.hash) {
    fail('scrolling left the address bar behind: no fragment after scrolling to card '
         + scrolled.active + ' of ' + JSON.stringify(scrolled.ids));
  }
  if (scrolled.active < 1) {
    fail('the wheel did not reach another card, so nothing here is under test: '
         + JSON.stringify(scrolled));
  }
  if (scrolled.hash !== '#' + scrolled.ids[scrolled.active]) {
    fail('the fragment names a card the reader is not on: ' + JSON.stringify(scrolled));
  }
  // And it replaced rather than pushed. One history entry per card
  // scrolled past would turn Back — the one way out of a deck — into a
  // slow rewind of the article the reader has just read.
  if (scrolled.entries !== atRest.entries) {
    fail('scrolling pushed history entries instead of replacing: '
         + atRest.entries + ' -> ' + scrolled.entries);
  }
  await scrollPage.close();

  // --- 4c. An old `sN` link lands, and the address bar is corrected ----
  // A card's id is now derived from what the author wrote (§12.1.1), so it
  // survives an edit. Every link ALREADY shared says `sN`, and none of them
  // can be recalled — a printed QR code least of all. The empty span
  // carrying the old name is what keeps them landing, and this is the only
  // place that can say whether a browser agrees: an element with no layout
  // box is not a fragment target, so "it is in the HTML" proves nothing.
  const aliasPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  collectConsoleErrors(aliasPage, errors);
  await aliasPage.goto(articleUrl + '#s3', { waitUntil: 'load' });
  await aliasPage.waitForTimeout(1200);
  const landed = await aliasPage.evaluate(() => {
    const sections = Array.prototype.slice.call(
      document.querySelectorAll('section.slide'));
    const mid = window.innerHeight / 2;
    return {
      visible: sections.findIndex((s) => {
        const r = s.getBoundingClientRect();
        return r.top <= mid && r.bottom >= mid;
      }),
      ids: sections.map((s) => s.id),
      hash: location.hash,
      aliases: Array.prototype.slice.call(
        document.querySelectorAll('span[id]')).map((s) => s.id),
    };
  });
  // Non-vacuity, both ways: no alias means the case never happened, and an
  // id still called s3 means the alias was never exercised.
  if (!landed.aliases.includes('s3')) {
    fail('this page carries no s3 alias, so the case never happened: '
         + JSON.stringify(landed));
  }
  if (landed.ids.includes('s3')) {
    fail('the third card is still called s3, so the alias is not exercised: '
         + JSON.stringify(landed));
  }
  if (landed.visible !== 2) {
    fail('an old #s3 link did not land on the third card: '
         + JSON.stringify(landed));
  }
  // And the reader who arrives by the old name leaves with the new one, so
  // the link they copy out of the address bar is the durable one.
  if (landed.hash !== '#' + landed.ids[2]) {
    fail('the address bar was not corrected to the card own id: '
         + JSON.stringify(landed));
  }
  await aliasPage.close();

  // 4d. And an old link to a card the reader's own tag filter is HIDING.
  // This is the one case the browser cannot handle for us, which is what
  // makes it the guard for the page's own hash handling: a filtered card
  // is display:none, has no layout box, and a native fragment jump lands
  // nowhere at all. Only a script that reads the fragment, notices the
  // card is filtered out, selects that card's tag and then goes there
  // will put the reader in front of what the link named.
  //
  // Everything above this line passes with the page's own applyHash
  // removed entirely — measured, by mutation — because the browser does
  // the scrolling and the scroll observer corrects the URL afterwards.
  const filtered = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  collectConsoleErrors(filtered, errors);
  await filtered.goto(articleUrl, { waitUntil: 'load' });
  await filtered.evaluate(() => localStorage.setItem('lwp-active-tag', 'default'));
  await filtered.goto(articleUrl + '#s4', { waitUntil: 'load' });
  await filtered.waitForTimeout(1200);
  const behindTag = await filtered.evaluate(() => {
    const sections = Array.prototype.slice.call(
      document.querySelectorAll('section.slide'));
    const fourth = sections[3];
    const mid = window.innerHeight / 2;
    const r = fourth ? fourth.getBoundingClientRect() : null;
    return {
      count: sections.length,
      tags: fourth ? fourth.getAttribute('data-tags') : null,
      shown: !!(r && r.width && r.height),
      onScreen: !!(r && r.top <= mid && r.bottom >= mid),
      hash: location.hash,
      id: fourth ? fourth.id : null,
    };
  });
  if (behindTag.count !== 4 || behindTag.tags !== 'avance') {
    fail('the fixture no longer carries a tag-filtered fourth card, so '
         + 'nothing here is under test: ' + JSON.stringify(behindTag));
  }
  if (!behindTag.shown) {
    fail('an old link to a filtered card left it hidden: '
         + JSON.stringify(behindTag));
  }
  if (!behindTag.onScreen) {
    fail('an old link to a filtered card did not put it in front of the '
         + 'reader: ' + JSON.stringify(behindTag));
  }
  await filtered.close();

  // --- 5. The phone: the chrome fades, and the double tap is its switch
  // Reported from the field: on a phone the navigation never went away.
  // It was exempt by design — `@media (pointer: coarse)` pinned every
  // piece to opacity 1 and the idle timer was not even armed — and the
  // reason recorded was that there is no cursor to wake it again. True
  // of the mechanism, and it left the one device where the buttons sit
  // permanently over the text as the one device that could not put them
  // away.
  //
  // A real touch context, because every assertion below rests on the
  // page seeing a coarse pointer: emulate it wrong and the whole section
  // measures the desktop path and passes for the wrong reason.
  const touch = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true,
    deviceScaleFactor: 3,
  });
  const phone = await touch.newPage();
  collectConsoleErrors(phone, errors);
  await phone.goto(articleUrl, { waitUntil: 'load' });

  // Non-vacuity first, and it comes before anything else: the script
  // branches on `(pointer: fine)`, so if this context reports a fine
  // pointer then everything after it is a desktop test wearing a phone's
  // viewport.
  const pointerKind = await phone.evaluate(() => ({
    coarse: matchMedia('(pointer: coarse)').matches,
    fine: matchMedia('(pointer: fine)').matches,
  }));
  if (!pointerKind.coarse || pointerKind.fine) {
    fail('this context is not a touch device, so nothing below is under '
         + 'test: ' + JSON.stringify(pointerKind));
  }

  // Read the class AND the computed style. The class alone would pass on
  // a page where the `(pointer: coarse)` override is still pinning the
  // opacity back to 1, which is precisely the defect being fixed.
  const chromeState = () => phone.evaluate(() => {
    const nav = document.querySelector('.nav-buttons');
    const style = nav ? getComputedStyle(nav) : null;
    return {
      idle: document.documentElement.classList.contains('nav-idle'),
      opacity: style ? style.opacity : null,
      pointerEvents: style ? style.pointerEvents : null,
      fullscreenAsked: window.__askedForFullscreen,
    };
  });
  await phone.evaluate(() => {
    window.__askedForFullscreen = 0;
    document.documentElement.requestFullscreen = function () {
      window.__askedForFullscreen++;
      return Promise.resolve();
    };
  });

  // 5a. It goes away on its own, on the same 3s the desk gets. 4s of
  // stillness is past it with room to spare.
  await phone.waitForTimeout(4000);
  let state = await chromeState();
  if (!state.idle || state.opacity !== '0') {
    fail('the navigation never faded on a touch screen: '
         + JSON.stringify(state));
  }
  // And a faded button must not still answer the finger. `opacity: 0`
  // hides a thing without disarming it; with no hover to bring it back
  // first, the reader who touches the corner of their own text would
  // fire whatever is invisible under it.
  if (state.pointerEvents !== 'none') {
    fail('a faded button still takes touches: ' + JSON.stringify(state));
  }

  const tapAt = async (x, y) => { await phone.touchscreen.tap(x, y); };
  const doubleTap = async () => {
    // Inside CLICK_DELAY (250ms), which is what makes it one gesture
    // rather than two taps that each advance the deck.
    await tapAt(195, 400);
    await phone.waitForTimeout(60);
    await tapAt(195, 400);
    // Past the 0.4s opacity transition, so the reads below are of a
    // settled value. Measured: at 300ms they land mid-fade (0.94, 0.04)
    // and the assertions fail on a behaviour that is correct.
    await phone.waitForTimeout(600);
  };

  // 5b. A single tap does not bring it back. That is the whole point of
  // asking for a deliberate gesture: an ordinary tap advances the deck,
  // and a reader tapping through an article would otherwise re-raise the
  // chrome on every card.
  await tapAt(195, 400);
  await phone.waitForTimeout(700);
  state = await chromeState();
  if (!state.idle) {
    fail('a single tap brought the navigation back: ' + JSON.stringify(state));
  }

  // 5c. The double tap does, and it spends itself doing only that.
  await doubleTap();
  state = await chromeState();
  if (state.idle || state.opacity !== '1') {
    fail('a double tap did not bring the navigation back: '
         + JSON.stringify(state));
  }
  if (state.fullscreenAsked !== 0) {
    fail('the double tap also asked for fullscreen, which is a second '
         + 'change the reader did not ask for: ' + JSON.stringify(state));
  }

  // 5d. And it is a switch, not a wake-up: tapping twice again puts the
  // chrome away AT ONCE, without waiting out the countdown. Asserted
  // well inside the 3s delay, so a pass here cannot be the timer firing.
  await doubleTap();
  state = await chromeState();
  if (!state.idle || state.opacity !== '0') {
    fail('a double tap on visible chrome did not put it away: '
         + JSON.stringify(state));
  }

  // 5e. Selection is gated on the chrome's state, and a selection holds
  // the chrome up.
  //
  // Reported from a phone: the double tap that is supposed to bring the
  // navigation back is also the system's gesture for selecting a word,
  // and the system wins — so the reader has no way back at all. This
  // harness does NOT reproduce that: synthetic taps in headless Chromium
  // take no selection, which is why the reveal above passes here and
  // failed on a real device. What can be asserted is the MECHANISM that
  // separates the two, and that is what this does.
  // Read WITHOUT doubleTap()'s 600ms settle: that wait is for the opacity
  // transition, and it is longer than the gate this is about. Observing
  // the mid-gesture state means observing it mid-gesture.
  await tapAt(195, 400);
  await phone.waitForTimeout(60);
  await tapAt(195, 400);
  await phone.waitForTimeout(150);
  // The gate outlives the reveal. Reported from a phone: a SLOW double tap
  // brought the chrome back and a FAST one selected a word instead — and
  // the cause is the reveal itself, which handed selection back while the
  // browser's own double-tap gesture was still in flight. Read right after
  // the taps, before the gate is due to lift.
  const midGesture = await phone.evaluate(() => {
    const slide = document.querySelector('section.slide');
    return {
      gated: document.documentElement.classList.contains('no-select'),
      idle: document.documentElement.classList.contains('nav-idle'),
      computed: getComputedStyle(slide).webkitUserSelect
             || getComputedStyle(slide).userSelect,
    };
  });
  if (midGesture.idle) {
    fail('the chrome did not come up, so the gate timing is not under test: '
         + JSON.stringify(midGesture));
  }
  if (!midGesture.gated || midGesture.computed !== 'none') {
    fail('selection was handed back the instant the chrome came up, which '
         + 'is what lets the browser finish the word-selection it had '
         + 'already started: ' + JSON.stringify(midGesture));
  }
  // And it does lift, or a reader could never select anything again.
  await phone.waitForTimeout(700);
  const working = await phone.evaluate(() => {
    const slide = document.querySelector('section.slide');
    return getComputedStyle(slide).webkitUserSelect
        || getComputedStyle(slide).userSelect;
  });
  if (working === 'none') {
    fail('selection is off while the chrome is UP, so a reader can never '
         + 'select anything at all: ' + working);
  }
  await doubleTap();          // chrome down
  const reading = await phone.evaluate(() => {
    const slide = document.querySelector('section.slide');
    return getComputedStyle(slide).webkitUserSelect
        || getComputedStyle(slide).userSelect;
  });
  if (reading !== 'none') {
    fail('selection is still on while the chrome is down, so the system '
         + 'takes the double tap and the reader has no way back: ' + reading);
  }

  // And a selection keeps the chrome from fading out from under it —
  // which on a touch screen would drop the selection with it.
  await doubleTap();          // chrome up again
  await phone.evaluate(() => {
    const target = document.querySelector('section.slide h1, section.slide h2');
    const range = document.createRange();
    range.selectNodeContents(target);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  });
  const held = await phone.evaluate(() => String(window.getSelection()).length);
  if (!held) {
    fail('the harness could not make a selection, so nothing below is under test');
  }
  await phone.waitForTimeout(4500);
  state = await chromeState();
  if (state.idle) {
    fail('the chrome faded while text was selected, taking the selection '
         + 'with it: ' + JSON.stringify(state));
  }
  await phone.evaluate(() => window.getSelection().removeAllRanges());
  // Put it back down, so the next section starts from the state it
  // expects. Each of these sections leaves the switch where it found it.
  await doubleTap();

  // 5f. Revealed chrome still fades on its own afterwards, so the switch
  // has not replaced the countdown with a latch.
  await doubleTap();
  if ((await chromeState()).idle) {
    fail('the chrome did not come back for the fade test');
  }
  await phone.waitForTimeout(4000);
  state = await chromeState();
  if (!state.idle) {
    fail('once revealed by a double tap the chrome never faded again: '
         + JSON.stringify(state));
  }

  await browser.close();
  if (errors.length) {
    fail('console errors: ' + errors.join(' | '));
  }
}

main().catch((e) => { fail(e.message); process.exit(1); });
