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
  // The click is instant now (no 250ms single-click timer), so this wait
  // only lets a stray immediate advance land if one were armed.
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
  // And back at the top, the address bar names the PAGE again, not the
  // first card (§8.4): whoever reaches the top of the page is looking at
  // the page, and the URL without a fragment is the one worth copying by
  // hand. The reader leaves the same way they arrived.
  await scrollPage.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await scrollPage.waitForTimeout(800);
  const home = await scrollPage.evaluate(() => ({
    hash: location.hash,
    active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
      .findIndex((d) => d.classList.contains('active')),
    entries: history.length,
  }));
  if (home.active !== 0) {
    fail('scrolling back to the top did not settle on the first card: '
         + JSON.stringify(home));
  }
  if (home.hash !== '') {
    fail('the address bar kept a fragment at the top of the page: '
         + JSON.stringify(home));
  }
  if (home.entries !== atRest.entries) {
    fail('returning to the top pushed a history entry instead of replacing: '
         + atRest.entries + ' -> ' + home.entries);
  }
  await scrollPage.close();

  // --- 4c. A link to a card lands, and the address bar says that card ---
  // A card's id is what its author declared (§12.1.1), so it survives an
  // edit and a link written against it stays valid. This is the only
  // place that can say whether a browser agrees: what the page ships is
  // a `<section>`, and whether a fragment reaches it is the browser's
  // answer, not the HTML's.
  const linkPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  collectConsoleErrors(linkPage, errors);
  await linkPage.goto(articleUrl + '#c3', { waitUntil: 'load' });
  await linkPage.waitForTimeout(1200);
  const landed = await linkPage.evaluate(() => {
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
    };
  });
  // Non-vacuity: the name in the link has to be the name the fixture
  // declared, or a pass says nothing about anything.
  if (landed.ids[2] !== 'c3') {
    fail('the third card is not the one the fixture named, so nothing '
         + 'here is under test: ' + JSON.stringify(landed));
  }
  if (landed.visible !== 2) {
    fail('a #c3 link did not land on the third card: '
         + JSON.stringify(landed));
  }
  // And the reader leaves with the name they arrived by: the scroll
  // observer must not rewrite a fragment that is already correct.
  if (landed.hash !== '#c3') {
    fail('the address bar no longer names the card the link named: '
         + JSON.stringify(landed));
  }
  await linkPage.close();

  // 4d. And a link to a card the reader's own tag filter is HIDING.
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
  await filtered.goto(articleUrl + '#c4', { waitUntil: 'load' });
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
    fail('a link to a filtered card left it hidden: '
         + JSON.stringify(behindTag));
  }
  if (!behindTag.onScreen) {
    fail('a link to a filtered card did not put it in front of the '
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
    // Inside DOUBLE_TAP_MS (350ms), which is what makes it one gesture
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

  // 5e. The deck does not touch selection at all.
  //
  // It did, briefly: `user-select: none` while the chrome was down, so
  // that the double tap which brings the navigation back would not lose
  // to the system's own word-selection. It was withdrawn on the owner's
  // call — the deck should not be re-teaching a phone what a long press
  // means — and this asserts the withdrawal rather than leaving it to be
  // re-invented by someone reading the double-tap code and reasoning
  // their way back to the same idea.
  const untouched = await phone.evaluate(() => {
    const slide = document.querySelector('section.slide');
    const root = document.documentElement;
    // The root class is what the double-tap switch READS, so this probe
    // has to put it back exactly as it found it. Measured the hard way:
    // clearing it here flipped the next section's double tap into hiding
    // the chrome instead of showing it.
    const was = root.classList.contains('nav-idle');
    const before = getComputedStyle(slide).webkitUserSelect
                || getComputedStyle(slide).userSelect;
    root.classList.add('nav-idle');
    const idle = getComputedStyle(slide).webkitUserSelect
              || getComputedStyle(slide).userSelect;
    root.classList.toggle('nav-idle', was);
    return { before, idle };
  });
  if (untouched.before === 'none' || untouched.idle === 'none') {
    fail('the deck is switching text selection off. On a phone that takes '
         + 'the long press — the way anyone selects a word and reaches the '
         + 'copy menu — away from the reader: ' + JSON.stringify(untouched));
  }

  // 5f. A long press belongs to the reader.
  //
  // Reported from a phone: pressing and holding — which is how anyone
  // selects a word and reaches the copy callout — threw the reader back a
  // card, and left them unable to select anything at all. A long press
  // fires `contextmenu`, the same event a mouse's second button fires,
  // and the deck bound that to "previous slide" with a `preventDefault()`
  // that takes the native gesture with it. The event cannot tell the two
  // apart; the pointer can.
  const beforePress = await phone.evaluate(() => {
    const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
    return dots.findIndex((d) => d.classList.contains('active'));
  });
  const pressed = await phone.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const target = slide.querySelector('h2, p') || slide;
    const evt = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    target.dispatchEvent(evt);
    return evt.defaultPrevented;
  });
  await phone.waitForTimeout(900);
  const afterPress = await phone.evaluate(() => {
    const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
    return dots.findIndex((d) => d.classList.contains('active'));
  });
  if (pressed) {
    fail('a long press was swallowed on a touch screen, which is what takes '
         + 'the selection callout away from the reader');
  }
  if (afterPress !== beforePress) {
    fail('a long press moved the deck: card ' + beforePress + ' -> '
         + afterPress);
  }

  // And the mouse keeps its second button, which is the whole point of
  // guarding on the pointer rather than dropping the binding.
  const deskBefore = await currentSlide(page);
  const deskPrevented = await page.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const evt = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    (slide.querySelector('h2, p') || slide).dispatchEvent(evt);
    return evt.defaultPrevented;
  });
  await page.waitForTimeout(900);
  if (!deskPrevented) {
    fail('right-click no longer goes back on a mouse, so the guard took the '
         + 'binding away instead of scoping it');
  }
  const deskAfter = await currentSlide(page);
  if (deskAfter === deskBefore && deskBefore !== 0) {
    fail('right-click did not move the deck on a mouse: ' + deskBefore
         + ' -> ' + deskAfter);
  }

  // 5f2. Right-click on a SELECTION belongs to the reader. A highlighted
  // passage is the reader's own text, and the right button on it asks
  // for the browser's menu — copy, copy link, search. Reported from the
  // field: it went back a card instead, the same theft the left-button
  // drag guard prevents on the way in. With no selection, right-click
  // keeps its deck meaning — asserted above, and still true.
  await page.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const target = slide.querySelector('h2, p') || slide;
    const range = document.createRange();
    range.selectNodeContents(target);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  });
  const selectionPrevented = await page.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const target = slide.querySelector('h2, p') || slide;
    const evt = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
    target.dispatchEvent(evt);
    return evt.defaultPrevented;
  });
  if (selectionPrevented) {
    fail('right-click on a selection was swallowed, so the browser copy '
         + 'menu never appeared');
  }
  const selectionKeptPlace = await currentSlide(page);
  if (selectionKeptPlace !== deskAfter) {
    fail('right-click on a selection moved the deck: ' + deskAfter
         + ' -> ' + selectionKeptPlace);
  }
  await page.evaluate(() => window.getSelection().removeAllRanges());

  // 5f3. A left-click on a SELECTION dismisses it, and only that. The
  // browser clears the selection on mousedown — before our click event
  // arrives — so the click must be judged at press time, or every
  // deselect reads as an advance.
  const beforeDeselect = await currentSlide(page);
  await page.evaluate(() => {
    const slide = document.querySelectorAll('section.slide')[1];
    const target = slide.querySelector('h2, p') || slide;
    const range = document.createRange();
    range.selectNodeContents(target);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  });
  const hadSel = await page.evaluate(() => String(window.getSelection()).length);
  if (!hadSel) fail('nothing was selected for the deselect click to dismiss');
  await page.mouse.click(640, 300);
  await page.waitForTimeout(400);
  const deselected = await page.evaluate(() => String(window.getSelection()).length);
  const afterDeselect = await currentSlide(page);
  if (deselected !== 0) {
    fail('a click did not dismiss the selection: ' + deselected);
  }
  if (afterDeselect !== beforeDeselect) {
    fail('deselecting advanced the deck: ' + beforeDeselect
         + ' -> ' + afterDeselect);
  }

  // 5f4. And a plain click still takes effect at once — the deck marks
  // the next card immediately and glides to it over 200ms. The old
  // 250ms timer (which delayed every click to guess at a double-click)
  // is gone; there is no double-click gesture anymore, only a click
  // while the deck is gliding, which jumps straight to its target.
  const instantBefore = await currentSlide(page);
  await page.mouse.click(640, 400);
  await page.waitForTimeout(120); // well inside the old 250ms window
  const instantAfter = await currentSlide(page);
  if (instantAfter === instantBefore) {
    fail('a plain click no longer advances instantly: stayed on '
         + instantBefore);
  }

  // 5f5. A click that lands WHILE the deck glides jumps straight to
  // its target: a click in the same direction during the glide lands
  // one more page on, a right-click during the glide returns instantly
  // to the card the reader left. There is no double-click gesture —
  // only clicks that land while the deck moves.
  //
  // The deck is walked back to the first card first: the fixture shows
  // three cards (the fourth is behind the tag filter), so the pair of
  // clicks needs headroom in the direction it tests.
  while ((await currentSlide(page)) > 0) {
    await page.mouse.click(640, 400, { button: 'right' });
    await page.waitForTimeout(400);
  }
  const glideStart = await currentSlide(page);
  await page.mouse.dblclick(640, 400);
  await page.waitForTimeout(400); // jump is instant; let dots settle
  const twoPages = await currentSlide(page);
  if (twoPages !== glideStart + 2) {
    fail('a click during the glide did not land one more page on: '
         + glideStart + ' -> ' + twoPages);
  }
  // Same test in the other direction, from the first card again: the
  // forward glide must be back-stopped by the right-click while it
  // runs, landing on the card the reader never left. (The dblclick
  // above left the deck at 2, so it is walked back first.)
  while ((await currentSlide(page)) > 0) {
    await page.mouse.click(640, 400, { button: 'right' });
    await page.waitForTimeout(400);
  }
  await page.mouse.click(640, 400); // one forward glide (0 -> 1)
  await page.waitForTimeout(40); // mid-glide
  await page.mouse.click(640, 400, { button: 'right' }); // back during glide
  await page.waitForTimeout(400);
  const backDuringGlide = await currentSlide(page);
  if (backDuringGlide !== 0) {
    fail('right-click during the glide did not return to the card left: '
         + 'expected 0, got ' + backDuringGlide);
  }

  // 5g. Revealed chrome still fades on its own afterwards, so the switch
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

  // 5h. The middle BUTTON toggles fullscreen, in AND out. The entry
  // used to be silent: the toggle lived on `auxclick`, which is not a
  // user-activation gesture, so the browser refused the request
  // fullscreen that needs one — the exit worked (it needs none), and
  // the entry never did. The toggle now lives on `mousedown`, which
  // IS a gesture. Stubbed, like the F test above, so the calls are
  // observable without a real fullscreen grant.
  await page.evaluate(() => {
    window.__fs = 0;
    window.__inFs = false;
    Object.defineProperty(document, 'fullscreenElement', {
      get: () => window.__inFs ? document.documentElement : null,
    });
    document.documentElement.requestFullscreen = function () {
      window.__fs++; window.__inFs = true; return Promise.resolve();
    };
    document.exitFullscreen = function () {
      window.__exit++; window.__inFs = false; return Promise.resolve();
    };
    window.__exit = 0;
  });
  await page.mouse.click(640, 400, { button: 'middle' });
  await page.waitForTimeout(200);
  const midIn = await page.evaluate(() => window.__fs);
  if (midIn !== 1) {
    fail('the middle button did not ENTER fullscreen: fs asked '
         + midIn + ' times');
  }
  await page.mouse.click(640, 400, { button: 'middle' });
  await page.waitForTimeout(200);
  const midOut = await page.evaluate(() => window.__exit);
  if (midOut !== 1) {
    fail('the middle button did not EXIT fullscreen: exit asked '
         + midOut + ' times');
  }

  // 5i. The two-click selection still belongs to the browser. The
  // deck must not swallow the platform's own double-click word
  // selection — the second click of a pair is exempted from the drag
  // guards precisely so the browser keeps doing what it does.
  await page.mouse.dblclick(300, 300);
  await page.waitForTimeout(200);
  const wordSel = await page.evaluate(() => String(window.getSelection()).length);
  if (wordSel === 0) {
    fail('a double-click no longer selects the word under the pointer: '
         + 'the deck swallowed the browser gesture');
  }

  await browser.close();
  if (errors.length) {
    fail('console errors: ' + errors.join(' | '));
  }
}

main().catch((e) => { fail(e.message); process.exit(1); });
