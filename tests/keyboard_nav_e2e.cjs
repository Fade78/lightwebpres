// Playwright driver for arrow-key navigation on an article page (nav.js,
// TEMPLATE_NAV_JS): the natural keyboard journey is slide-to-slide, then
// — on the series-nav slide — card-to-card with Enter jumping to the
// linked article, then, for a slide taller than the viewport (typically
// a long full-article), scrolling it down in increments before moving
// on. Invoked by tests/test_keyboard_nav.py — not a standalone entry
// point.
//
// argv: <tallArticleUrl> <navArticleUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

function fail(msg) {
  console.error('E2E failure: ' + msg);
  process.exitCode = 1;
}

async function activeDotIndex(page) {
  return page.evaluate(() => {
    const dots = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'));
    return dots.findIndex((d) => d.classList.contains('active'));
  });
}

async function activeElementInfo(page) {
  return page.evaluate(() => ({
    tag: document.activeElement.tagName,
    href: document.activeElement.getAttribute('href'),
  }));
}

// nav.js throttles ArrowDown/ArrowUp processing to one step per 150ms
// (STEP_COOLDOWN_MS) — otherwise holding the key down fires native
// auto-repeat keydown events fast enough to blow straight through every
// intermediate card-focus state before a human (or a script pressing
// keys back-to-back with no delay) could ever land on one. 200ms here,
// comfortably over that threshold, so each press in this script is
// guaranteed to actually register as its own step.
async function press(page, key) {
  await page.keyboard.press(key);
  await page.waitForTimeout(200);
}

async function main() {
  const [tallArticleUrl, navArticleUrl, heldArticleUrl] = process.argv.slice(2);
  if (!tallArticleUrl || !navArticleUrl || !heldArticleUrl) {
    console.error('usage: keyboard_nav_e2e.cjs <tallArticleUrl> <navArticleUrl> <heldArticleUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  // 800px, not a rounder/smaller number: the series-nav fixture's own
  // heading + 3 cards measure ~727px tall — comfortably under 800 (so
  // the "no cards left to step through, plain slide-to-slide" scenario
  // stays clean) while still well under the 40-paragraph full-article
  // fixture used for the overflow scenario, which needs to overflow
  // regardless of viewport height.
  const context = await browser.newContext({ viewport: { width: 1024, height: 800 } });
  const consoleErrors = [];

  try {
    // --- 1. A slide taller than the viewport gets scrolled in
    // increments before the arrow key advances to the next slide ------
    let page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'ArrowDown'); // cover (0) -> full-article (1)
    await page.waitForTimeout(600);
    let idx = await activeDotIndex(page);
    if (idx !== 1) fail('expected slide 1 (the tall full-article) after one ArrowDown, got ' + idx);

    const scrollYAfterArrival = await page.evaluate(() => window.scrollY);
    await press(page, 'ArrowDown'); // must scroll WITHIN slide 1, not advance
    await page.waitForTimeout(600);
    const scrollYAfterOnePress = await page.evaluate(() => window.scrollY);
    idx = await activeDotIndex(page);
    let scrollStepOk = true;
    if (idx !== 1) { fail('a single ArrowDown on an overflowing slide must not skip past it — advanced to slide ' + idx + ' instead of scrolling within slide 1'); scrollStepOk = false; }
    if (scrollYAfterOnePress <= scrollYAfterArrival) {
      fail('ArrowDown on an overflowing slide did not scroll the page (scrollY ' + scrollYAfterArrival + ' -> ' + scrollYAfterOnePress + ')');
      scrollStepOk = false;
    }
    if (scrollStepOk) console.log('tall-slide incremental scroll OK: scrollY ' + scrollYAfterArrival + ' -> ' + scrollYAfterOnePress + ', still on slide 1');

    // Keep pressing until it eventually reaches slide 2 (bounded, so a
    // regression that never advances fails loudly instead of hanging).
    let reachedSlide2 = false;
    for (let i = 0; i < 40 && !reachedSlide2; i++) {
      await press(page, 'ArrowDown');
      await page.waitForTimeout(300);
      idx = await activeDotIndex(page);
      if (idx === 2) reachedSlide2 = true;
    }
    if (!reachedSlide2) fail('never advanced to slide 2 after repeatedly pressing ArrowDown through the tall slide');
    else console.log('tall-slide eventually advances to the next slide OK');
    await page.close();

    // --- 2. Series-nav: forward through the cards one by one, then
    // exhausting them on the last slide stays put and clears focus,
    // then one more ArrowUp (no card was ever focused-and-released, so
    // there's nothing to step back through) leaves the slide backward --
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(navArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'ArrowDown'); // cover (0) -> standard (1)
    await page.waitForTimeout(600);
    await press(page, 'ArrowDown'); // standard (1) -> series-nav (2)
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('expected the series-nav slide (2) after two ArrowDown presses, got ' + idx);

    let active = await activeElementInfo(page);
    if (active.tag === 'A') fail('arriving at the series-nav slide must not auto-focus a card — the next ArrowDown press should be the one that does');

    const forwardHrefs = [];
    for (let i = 0; i < 3; i++) {
      await press(page, 'ArrowDown');
      active = await activeElementInfo(page);
      if (active.tag !== 'A') fail('ArrowDown #' + (i + 1) + ' on the series-nav slide should focus a card link, focused a ' + active.tag + ' instead');
      forwardHrefs.push(active.href);
      idx = await activeDotIndex(page);
      if (idx !== 2) fail('stepping through series-nav cards must not itself change the active slide (moved to ' + idx + ')');
    }
    if (JSON.stringify(forwardHrefs) !== JSON.stringify(['b.html', 'c.html', 'index.html'])) {
      fail('series-nav card focus order should be [b.html, c.html, index.html] (document order), got ' + JSON.stringify(forwardHrefs));
    }
    console.log('series-nav card-by-card ArrowDown OK: ' + forwardHrefs.join(' -> '));

    // Cards exhausted, and this article's series-nav slide is also the
    // LAST slide — one more ArrowDown must stay put (nothing to advance
    // to) and clear focus off the last card, not error out or leave a
    // stale focused link behind.
    await press(page, 'ArrowDown');
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('ArrowDown past the last series-nav card on the last slide should stay on slide 2, moved to ' + idx);
    active = await activeElementInfo(page);
    if (active.tag === 'A') fail('exhausting the series-nav cards on the last slide should clear focus off the last card, still focused ' + active.href);
    console.log('series-nav exhaustion-on-last-slide OK: stays put, focus cleared');

    // No card was left "mid-walk" (focusedCard was just reset above) —
    // ArrowUp from here has nothing to step back through and should
    // leave the slide backward directly, same as any ordinary slide.
    await press(page, 'ArrowUp');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) fail('ArrowUp with no card mid-walk should leave the series-nav slide backward to slide 1, got ' + idx);
    console.log('series-nav ArrowUp-with-nothing-to-step-back-through OK: left the slide backward');
    await page.close();

    // --- 3. Backward through the cards from mid-walk, then Enter jumps
    // to the focused article — fresh page, so focusedCard is still
    // genuinely mid-walk (not reset by an exhausting extra press) -----
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(navArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    for (let i = 0; i < 3; i++) await press(page, 'ArrowDown'); // walk forward to the last card (index.html)
    active = await activeElementInfo(page);
    if (active.href !== 'index.html') fail('setup for the backward-walk test did not land on the last card (index.html), got ' + active.href);

    await press(page, 'ArrowUp');
    active = await activeElementInfo(page);
    if (active.href !== 'c.html') fail('first ArrowUp from the last card should step back to c.html, got ' + active.href);
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('stepping backward through series-nav cards must not itself change the active slide (moved to ' + idx + ')');

    await press(page, 'ArrowUp');
    active = await activeElementInfo(page);
    if (active.href !== 'b.html') fail('second ArrowUp should step back to b.html, got ' + active.href);
    console.log('series-nav card-by-card ArrowUp OK: index.html -> c.html -> b.html');

    // Enter on the focused card jumps to the article — native browser
    // behavior once the link genuinely has focus, no extra JS required;
    // prove it actually works end to end.
    await page.keyboard.press('Enter');
    await page.waitForURL('**/b.html', { timeout: 5000 });
    console.log('Enter-on-focused-card jump OK: navigated to ' + page.url());
    await page.close();

    // --- 4. Regression: holding an arrow key down (native auto-repeat
    // fires keydown much faster than a human can perceive, ~20-30ms
    // apart) must not race straight through the card-focus states — the
    // exact bug a real user hit before nav.js's step cooldown existed.
    // Uses the 'held' fixture, not 'nav': its series-nav slide has a
    // real slide AFTER it (index 3), so "raced all the way through" and
    // "the cooldown only let it get partway" land on genuinely different
    // final states — with 'nav' (series-nav as the very last slide),
    // both converge on the identical "slide 2, nothing focused" once
    // everything settles, making the regression unobservable after the
    // fact. Reaching slide 3 takes 6 real steps (cover->standard->nav,
    // then 3 cards, then exhaust->next); ~240ms of raw event firing
    // against a 150ms cooldown can only register 1-2 of those. No
    // explicit waits between presses: deliberately as fast as Playwright
    // can fire them. --------------------------------------------------
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(heldArticleUrl);
    await page.waitForSelector('.nav-dots a');

    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(30);
    }
    await page.waitForTimeout(400);
    idx = await activeDotIndex(page);
    if (idx >= 3) fail('holding ArrowDown down raced all the way past the series-nav slide\'s cards to slide ' + idx + ' — the step cooldown is not throttling fast repeated presses');
    else console.log('held-key-down regression OK: rapid repeated ArrowDown did not skip past the series-nav cards (slide ' + idx + ')');
    await page.close();

    if (consoleErrors.length) {
      fail('unexpected console errors:\n' + consoleErrors.join('\n'));
    }

    if (process.exitCode !== 1) {
      console.log('OK — tall-slide incremental scroll and series-nav card-by-card keyboard navigation both work.');
    }
  } catch (err) {
    fail(String((err && err.stack) || err));
  } finally {
    await browser.close();
  }
}

main();
