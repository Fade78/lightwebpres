// Playwright driver for arrow-key navigation on an article page (nav.js,
// TEMPLATE_NAV_JS): the natural keyboard journey is slide-to-slide, then
// — on the series-nav slide — card-to-card with Enter jumping to the
// linked article, then, for a slide taller than the viewport (typically
// a long full-article), scrolling it down in bounded increments before
// moving on, with a final overflowing slide staying at its bottom when
// there is no next slide. A partially visible adjacent slide is aligned
// before the next transition, in both directions. Invoked by
// tests/test_keyboard_nav.py — not a standalone entry point.
//
// argv: <tallArticleUrl> <lastArticleUrl> <navArticleUrl> <heldArticleUrl>

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

async function exposeFollowingSlide(page) {
  return page.evaluate(() => {
    const slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
    const following = slides[2];
    const followingTop = following.getBoundingClientRect().top + window.scrollY;
    // Put the following slide's top above the viewport midpoint, but leave
    // it visibly below the viewport top. This is the exact state in which
    // midpoint-based current-slide detection used to count it as complete.
    const targetY = Math.max(0, followingTop - window.innerHeight * 0.4);
    window.scrollTo({ top: targetY, behavior: 'instant' });
    return { followingTop, targetY };
  });
}

async function main() {
  const [tallArticleUrl, lastArticleUrl, navArticleUrl, heldArticleUrl] = process.argv.slice(2);
  if (!tallArticleUrl || !lastArticleUrl || !navArticleUrl || !heldArticleUrl) {
    console.error('usage: keyboard_nav_e2e.cjs <tallArticleUrl> <lastArticleUrl> <navArticleUrl> <heldArticleUrl>');
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
    // --- 0. A card selected on a series-nav slide must be fully visible
    // immediately, even when the slide is taller than this small viewport.
    // This exercises the same instant reveal as the index, in both directions
    // through the card list, without changing the exhaustion scenario below.
    let cardVisibilityPage = await context.newPage();
    await cardVisibilityPage.setViewportSize({ width: 1024, height: 500 });
    collectConsoleErrors(cardVisibilityPage, consoleErrors);
    cardVisibilityPage.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await cardVisibilityPage.goto(navArticleUrl);
    await cardVisibilityPage.waitForSelector('.nav-dots a');
    await press(cardVisibilityPage, 'ArrowDown'); // cover -> standard
    await press(cardVisibilityPage, 'ArrowDown'); // standard -> series-nav
    const cardViewportMargin = 24;
    for (let i = 0; i < 3; i++) {
      await cardVisibilityPage.keyboard.press('ArrowDown');
      const cardBounds = await cardVisibilityPage.evaluate(() => {
        const card = document.activeElement;
        const rect = card.getBoundingClientRect();
        return {
          isCard: card.classList.contains('series-link'),
          top: rect.top,
          bottom: rect.bottom,
          viewport: window.innerHeight,
        };
      });
      if (!cardBounds.isCard || cardBounds.top < cardViewportMargin - 1
          || cardBounds.bottom > cardBounds.viewport - cardViewportMargin + 1) {
        fail('the selected series-nav card is not fully visible with a margin: '
             + JSON.stringify(cardBounds));
      }
      await cardVisibilityPage.waitForTimeout(200);
    }
    await cardVisibilityPage.keyboard.press('ArrowUp');
    const backwardCardBounds = await cardVisibilityPage.evaluate(() => {
      const card = document.activeElement;
      const rect = card.getBoundingClientRect();
      return {
        isCard: card.classList.contains('series-link'),
        top: rect.top,
        bottom: rect.bottom,
        viewport: window.innerHeight,
      };
    });
    if (!backwardCardBounds.isCard || backwardCardBounds.top < cardViewportMargin - 1
        || backwardCardBounds.bottom > backwardCardBounds.viewport - cardViewportMargin + 1) {
      fail('the series-nav card selected while moving backward is not fully visible with a margin: '
           + JSON.stringify(backwardCardBounds));
    }
    console.log('series-nav card visibility OK in both directions');
    await cardVisibilityPage.close();

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

    // A following slide can become the midpoint-visible slide before its
    // top reaches the viewport top. Advancing from that partial view must
    // first align it, not skip to slide 3. Exercise keyboard, content click,
    // and the visible next button because all are forward-entry points.
    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    let partial = await exposeFollowingSlide(page);
    await page.waitForTimeout(200);
    let partialState = await page.evaluate(() => {
      const following = document.querySelectorAll('.slide')[2].getBoundingClientRect();
      return {
        active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
          .findIndex((d) => d.classList.contains('active')),
        top: following.top,
      };
    });
    if (partialState.top <= 1 || partialState.top >= 800) {
      fail('partial-slide setup did not leave the following slide visible below the top (top ' + partialState.top + ')');
    }
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    let alignedY = await page.evaluate(() => window.scrollY);
    if (idx !== 2) fail('ArrowDown on a partially visible slide skipped to slide ' + idx + ' instead of aligning slide 2');
    if (Math.abs(alignedY - partial.followingTop) > 2) {
      fail('ArrowDown on a partially visible slide did not align its top (expected ' + partial.followingTop + ', got ' + alignedY + ')');
    }

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    partial = await exposeFollowingSlide(page);
    await page.waitForTimeout(200);
    await page.mouse.click(500, 100);
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    alignedY = await page.evaluate(() => window.scrollY);
    if (idx !== 2) fail('left click on a partially visible slide skipped to slide ' + idx + ' instead of aligning slide 2');
    if (Math.abs(alignedY - partial.followingTop) > 2) {
      fail('left click on a partially visible slide did not align its top (expected ' + partial.followingTop + ', got ' + alignedY + ')');
    }

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    partial = await exposeFollowingSlide(page);
    await page.waitForTimeout(200);
    await page.locator('#navNext').click();
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    alignedY = await page.evaluate(() => window.scrollY);
    if (idx !== 2) fail('next button on a partially visible slide skipped to slide ' + idx + ' instead of aligning slide 2');
    if (Math.abs(alignedY - partial.followingTop) > 2) {
      fail('next button on a partially visible slide did not align its top (expected ' + partial.followingTop + ', got ' + alignedY + ')');
    }
    console.log('partially visible following slide aligns before advancing OK');

    // The same boundary must hold in the other direction: the last upward
    // movement inside the tall slide must stop at its top, without exposing
    // the previous slide. Only the following ArrowUp may leave the slide.
    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    const tallBounds = await page.evaluate(() => {
      const tall = document.querySelectorAll('.slide')[1];
      const scrollY = window.scrollY;
      const rect = tall.getBoundingClientRect();
      const top = rect.top + scrollY;
      const bottom = rect.bottom + scrollY;
      window.scrollTo({ top: bottom - window.innerHeight, behavior: 'instant' });
      return { top, bottom };
    });
    await page.waitForTimeout(200);
    let reachedTallTop = false;
    for (let i = 0; i < 10; i++) {
      await press(page, 'ArrowUp');
      await page.waitForTimeout(300);
      const upwardState = await page.evaluate(() => {
        const slides = document.querySelectorAll('.slide');
        const previous = slides[0].getBoundingClientRect();
        const tall = slides[1].getBoundingClientRect();
        return {
          active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
            .findIndex((d) => d.classList.contains('active')),
          previousBottom: previous.bottom,
          tallTop: tall.top,
        };
      });
      if (upwardState.active !== 1) {
        fail('ArrowUp left the tall slide before its top was aligned (active slide ' + upwardState.active + ')');
        break;
      }
      if (upwardState.previousBottom > 1) {
        fail('ArrowUp exposed the previous slide before the tall slide reached its top (previous bottom ' + upwardState.previousBottom + ')');
        break;
      }
      if (upwardState.tallTop >= -1) {
        reachedTallTop = true;
        break;
      }
    }
    if (!reachedTallTop) {
      fail('ArrowUp never reached the top of the tall slide without exposing the previous slide');
    } else {
      await press(page, 'ArrowUp');
      await page.waitForTimeout(600);
      idx = await activeDotIndex(page);
      if (idx !== 0) fail('ArrowUp after the tall slide reached its top should move to the previous slide, got ' + idx);
      else console.log('tall-slide upward boundary stays inside before moving back OK');
    }

    await page.keyboard.press('End');
    await page.waitForTimeout(300);
    idx = await activeDotIndex(page);
    if (idx !== 3) fail('End should jump to the last slide, got ' + idx);
    await page.keyboard.press('Home');
    await page.waitForTimeout(300);
    idx = await activeDotIndex(page);
    const articleHome = await page.evaluate(() => ({
      y: window.pageYOffset || document.documentElement.scrollTop,
    }));
    if (idx !== 0) fail('Home should return to the first slide, got ' + idx);
    if (articleHome.y > 2) fail('Home should return to the beginning of the article, got scrollY ' + articleHome.y);
    console.log('article Home returns to the beginning of the page OK');

    await page.keyboard.press('Control+Home');
    await page.waitForURL('**/tall/index.html', { timeout: 5000 });
    const articleIndexPath = await page.evaluate(() => location.pathname);
    if (!/\/tall\/index\.html$/.test(articleIndexPath)) {
      fail('Control+Home should return to the series index, got ' + articleIndexPath);
    }
    console.log('article Control+Home returns to the series index OK');
    await page.close();

    // Re-open the article after the index shortcut so Ctrl+End remains tested
    // on an article rather than on the index page.
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await page.keyboard.press('Control+End');
    await page.waitForTimeout(300);
    idx = await activeDotIndex(page);
    if (idx !== 3) fail('Control+End should jump to the last slide, got ' + idx);
    console.log('keyboard edge shortcuts OK: End / Home / Control+Home / Control+End');

    await page.keyboard.press('Home');
    await page.waitForTimeout(300);
    await page.keyboard.press('Shift+=');
    await page.waitForTimeout(100);
    let pageZoom = await page.evaluate(() => document.documentElement.style.zoom);
    if (pageZoom !== '1.1') fail('plus should increase page zoom to 1.1, got ' + pageZoom);
    const zoomedSlide = await page.evaluate(() => {
      const rect = document.querySelector('.slide').getBoundingClientRect();
      return { height: rect.height, viewport: window.innerHeight };
    });
    if (Math.abs(zoomedSlide.height - zoomedSlide.viewport) > 2) {
      fail('presentation zoom must keep a normal slide at viewport height, got '
           + JSON.stringify(zoomedSlide));
    }
    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) {
      fail('ArrowDown after presentation zoom should enter slide 1, got ' + idx);
    } else {
      console.log('presentation zoom keeps slide sizing and ArrowDown navigation OK');
    }
    await page.keyboard.press('-');
    await page.waitForTimeout(100);
    pageZoom = await page.evaluate(() => document.documentElement.style.zoom);
    if (pageZoom !== '1') fail('minus should reduce page zoom to 1, got ' + pageZoom);
    await page.keyboard.press('Shift+=');
    await page.keyboard.press('=');
    await page.waitForTimeout(100);
    pageZoom = await page.evaluate(() => document.documentElement.style.zoom);
    if (pageZoom !== '1') fail('equals should reset page zoom to 1, got ' + pageZoom);
    console.log('page zoom shortcuts OK: + / - / =');
    await page.close();

    // The index uses the same edge shortcuts, with article cards as its
    // journey rather than slides.
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(new URL('index.html', navArticleUrl).href);
    await page.waitForSelector('.article-card');
    await press(page, 'End');
    let indexEdge = await page.evaluate(() => ({
      href: document.activeElement.getAttribute('href'),
      scrollY: window.scrollY,
    }));
    if (!indexEdge.href || indexEdge.href === 'index.html') {
      fail('End on the index should focus the last article card, got ' + JSON.stringify(indexEdge));
    }
    await press(page, 'Control+Home');
    indexEdge = await page.evaluate(() => ({
      tag: document.activeElement.tagName,
      scrollY: window.scrollY,
    }));
    if (indexEdge.scrollY > 2) fail('Control+Home on the index should remain at the top, got scrollY ' + indexEdge.scrollY);
    if (indexEdge.tag === 'A') fail('Control+Home on the index should clear the card focus');
    await press(page, 'End');
    await press(page, 'Home');
    const indexHome = await page.evaluate(() => ({
      tag: document.activeElement.tagName,
      scrollY: window.scrollY,
    }));
    if (indexHome.scrollY > 2) fail('Home on the index should return to the top, got scrollY ' + indexHome.scrollY);
    if (indexHome.tag === 'A') fail('Home on the index should clear the card focus');
    console.log('index edge shortcuts OK: End / Home / Control+Home return to top');
    await page.close();

    // --- 2. A tall full-article that is the LAST slide stays at its
    // bottom when ArrowDown has no next slide to enter. -----------------
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(lastArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'ArrowDown'); // cover (0) -> full-article (1)
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) fail('expected slide 1 (the last full-article) after one ArrowDown, got ' + idx);

    const bottomY = await page.evaluate(() => {
      const maxY = Math.max(0, document.scrollingElement.scrollHeight - window.innerHeight);
      window.scrollTo({ top: maxY, behavior: 'instant' });
      return maxY;
    });
    await page.waitForTimeout(120);
    const scrollYAtBottom = await page.evaluate(() => window.scrollY);
    if (bottomY <= 0 || scrollYAtBottom < bottomY - 2) {
      fail('setup did not reach the bottom of the last full-article (expected ' + bottomY + ', got ' + scrollYAtBottom + ')');
    }

    await press(page, 'ArrowDown');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    const scrollYAfterEnd = await page.evaluate(() => window.scrollY);
    if (idx !== 1) fail('ArrowDown at the bottom of the last full-article moved to slide ' + idx);
    if (scrollYAfterEnd < scrollYAtBottom - 20) {
      fail('ArrowDown at the bottom of the last full-article moved back to its top (scrollY ' + scrollYAtBottom + ' -> ' + scrollYAfterEnd + ')');
    } else {
      console.log('last full-article bottom ArrowDown stays at the bottom OK');
    }
    await page.close();

    // --- 3. Series-nav: forward through the cards one by one, then
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

    // --- 4. Backward through the cards from mid-walk, then Enter jumps
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

    // --- 5. Regression: holding an arrow key down (native auto-repeat
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
