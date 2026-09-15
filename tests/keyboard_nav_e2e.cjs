// Playwright driver for keyboard navigation on an article page (nav.js,
// TEMPLATE_NAV_JS): arrow keys and the wheel retain native reading scroll;
// PageUp/PageDown and the navigation buttons change slides. Space keeps the
// natural editorial journey for cards and long slides. Invoked by
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

// nav.js throttles the deliberate Space journey to one step per 150ms
// (STEP_COOLDOWN_MS). 200ms here, comfortably over that threshold, so each
// press in this script is guaranteed to register as its own step.
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
    await press(cardVisibilityPage, 'PageDown'); // cover -> standard
    await press(cardVisibilityPage, 'PageDown'); // standard -> series-nav
    const cardViewportMargin = 24;
    const visibleCardHrefs = ['b.html', 'c.html', 'index.html'];
    for (let i = 0; i < 3; i++) {
      await cardVisibilityPage.keyboard.press('Space');
      const cardBounds = await cardVisibilityPage.evaluate(() => {
        const card = document.activeElement;
        const rect = card.getBoundingClientRect();
        return {
          isCard: card.classList.contains('series-link'),
          href: card.getAttribute('href'),
          top: rect.top,
          bottom: rect.bottom,
          viewport: window.innerHeight,
        };
      });
      if (!cardBounds.isCard || cardBounds.href !== visibleCardHrefs[i]
          || cardBounds.top < cardViewportMargin - 1
          || cardBounds.bottom > cardBounds.viewport - cardViewportMargin + 1) {
        fail('series-nav Space #' + (i + 1) + ' expected ' + visibleCardHrefs[i]
             + ' focused and fully visible with a margin: '
             + JSON.stringify(cardBounds));
      }
      await cardVisibilityPage.waitForTimeout(200);
    }
    await cardVisibilityPage.keyboard.press('Shift+Space');
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

    // A previous glide's safety timeout must not unlock a newer glide.
    // Use a separate context for the clock and drop the second glide's frames
    // so scroll detection observes the old slide when that timeout expires.
    const glidePage = await browser.newPage({ viewport: { width: 1024, height: 500 } });
    collectConsoleErrors(glidePage, consoleErrors);
    glidePage.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await glidePage.clock.install({ time: new Date('2026-01-01T00:00:00Z') });
    await glidePage.goto(navArticleUrl);
    await glidePage.waitForSelector('.nav-dots a');
    await glidePage.clock.pauseAt(new Date('2026-01-01T00:01:00Z'));
    await glidePage.keyboard.press('PageDown');
    await glidePage.clock.runFor(220); // glide finished, 260ms safety timeout still pending
    await glidePage.evaluate(() => { window.requestAnimationFrame = () => 0; });
    await glidePage.keyboard.press('PageDown');
    await glidePage.evaluate(() => window.dispatchEvent(new Event('scroll')));
    await glidePage.clock.runFor(80); // old timeout at 260ms, scroll detection at 300ms
    const glideTarget = await activeDotIndex(glidePage);
    if (glideTarget !== 2) {
      fail('an earlier glide timeout released the current glide: expected slide 2, got ' + glideTarget);
    }
    await glidePage.clock.runFor(180); // the current glide's own safety timeout at 480ms
    await glidePage.evaluate(() => window.dispatchEvent(new Event('scroll')));
    await glidePage.clock.runFor(80);
    const unlockedSlide = await activeDotIndex(glidePage);
    if (unlockedSlide !== 1) {
      fail('the current glide safety timeout did not release dropped frames: got slide ' + unlockedSlide);
    }
    if (glideTarget === 2 && unlockedSlide === 1) {
      console.log('glide safety timeout belongs only to the current transition OK');
    }
    await glidePage.close();

    // --- 1. Arrow keys and the wheel scroll without changing slides; page
    // keys and buttons change slides directly ----------------------------
    let page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'ArrowDown');
    let idx = await activeDotIndex(page);
    const arrowDownY = await page.evaluate(() => window.scrollY);
    if (idx !== 0 || arrowDownY <= 0) {
      fail('ArrowDown must scroll the cover without changing slides: ' + JSON.stringify({idx, arrowDownY}));
    }
    await press(page, 'ArrowUp');
    const arrowUpState = await page.evaluate(() => ({
      y: window.scrollY,
      active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
        .findIndex((d) => d.classList.contains('active')),
    }));
    if (arrowUpState.active !== 0 || arrowUpState.y !== 0) {
      fail('ArrowUp must return the cover to its start without changing slides: '
        + JSON.stringify(arrowUpState));
    }
    await page.mouse.wheel(0, 400);
    await page.waitForTimeout(700);
    const wheelState = await page.evaluate(() => ({
      y: window.scrollY,
      active: Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
        .findIndex((d) => d.classList.contains('active')),
    }));
    if (wheelState.active !== 0 || wheelState.y <= 0) {
      fail('wheel must scroll the cover without changing slides: ' + JSON.stringify(wheelState));
    }

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'PageDown');
    idx = await activeDotIndex(page);
    if (idx !== 1) fail('PageDown did not change to the tall full-article: ' + idx);
    const tallTop = await page.evaluate(() => window.scrollY);
    await press(page, 'PageDown');
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('PageDown did not leave the long slide directly: ' + idx);
    if ((await page.evaluate(() => window.scrollY)) <= tallTop) {
      fail('PageDown did not move to the following slide');
    }

    // A following slide can be partially visible after native scrolling.
    // PageDown and the next button select it and align its top.
    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'PageDown');
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
    await press(page, 'PageDown');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    let alignedY = await page.evaluate(() => window.scrollY);
    if (idx !== 2) fail('PageDown on a partially visible slide skipped to slide ' + idx + ' instead of aligning slide 2');
    if (Math.abs(alignedY - partial.followingTop) > 2) {
      fail('PageDown on a partially visible slide did not align its top (expected ' + partial.followingTop + ', got ' + alignedY + ')');
    }

    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'PageDown');
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
    await press(page, 'PageDown');
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

    // PageUp is the direct reverse of PageDown, including from a long slide.
    await page.goto(tallArticleUrl);
    await page.waitForSelector('.nav-dots a');
    await press(page, 'PageDown');
    await page.waitForTimeout(600);
    await press(page, 'PageUp');
    idx = await activeDotIndex(page);
    if (idx !== 0) fail('PageUp did not move back from the long slide: ' + idx);
    console.log('native reading scroll and direct page navigation OK');

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
    const zoomHeadingSize = () => page.$eval('.slide h1, .slide h2', el => parseFloat(getComputedStyle(el).fontSize));
    const originalHeadingSize = await zoomHeadingSize();
    await page.keyboard.press('Shift+=');
    await page.waitForTimeout(100);
    let pageZoom = await page.evaluate(() => document.documentElement.style.getPropertyValue('--lwp-presentation-zoom'));
    if (pageZoom !== '1.1') fail('plus should increase page zoom to 1.1, got ' + pageZoom);
    if (Math.abs(await zoomHeadingSize() - originalHeadingSize * 1.1) > .01) {
      fail('plus should enlarge actual content typography by 1.1');
    }
    const zoomedSlide = await page.evaluate(() => {
      const rect = document.querySelector('.slide').getBoundingClientRect();
      return { height: rect.height, viewport: window.innerHeight };
    });
    if (Math.abs(zoomedSlide.height - zoomedSlide.viewport) > 2) {
      fail('presentation zoom must keep a normal slide at viewport height, got '
           + JSON.stringify(zoomedSlide));
    }
    await press(page, 'PageDown');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) {
      fail('PageDown after presentation zoom should enter slide 1, got ' + idx);
    } else {
      console.log('presentation zoom keeps slide sizing and PageDown navigation OK');
    }
    await page.keyboard.press('-');
    await page.waitForTimeout(100);
    pageZoom = await page.evaluate(() => document.documentElement.style.getPropertyValue('--lwp-presentation-zoom'));
    if (pageZoom !== '1') fail('minus should reduce page zoom to 1, got ' + pageZoom);
    if (Math.abs(await zoomHeadingSize() - originalHeadingSize) > .01) fail('minus should restore content typography');
    await page.keyboard.press('Shift+=');
    await page.keyboard.press('=');
    await page.waitForTimeout(100);
    pageZoom = await page.evaluate(() => document.documentElement.style.getPropertyValue('--lwp-presentation-zoom'));
    if (pageZoom !== '1') fail('equals should reset page zoom to 1, got ' + pageZoom);
    if (Math.abs(await zoomHeadingSize() - originalHeadingSize) > .01) fail('equals should restore content typography');
    console.log('page zoom shortcuts OK: + / - / =');

    // Changing the viewport changes every slide's min-height. The active
    // slide must be put back at the top rather than left at its old document
    // coordinate, which would expose the middle of it after a resize.
    await page.setViewportSize({ width: 1024, height: 600 });
    await page.waitForTimeout(200);
    const resizedSlide = await page.evaluate(() => {
      const slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
      const active = Array.prototype.slice.call(document.querySelectorAll('.nav-dots a'))
        .findIndex((d) => d.classList.contains('active'));
      const rect = slides[1].getBoundingClientRect();
      return { active, top: rect.top, bottom: rect.bottom, scrollY: window.scrollY };
    });
    if (resizedSlide.active !== 1) {
      fail('viewport resize changed the active slide, got ' + resizedSlide.active);
    }
    if (Math.abs(resizedSlide.top) > 2) {
      fail('viewport resize should realign the active slide to the top, got '
           + JSON.stringify(resizedSlide));
    } else {
      console.log('viewport resize keeps the active slide aligned OK');
    }
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
    // bottom when the native ArrowDown scroll has nowhere to go. --------
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(lastArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'PageDown'); // cover (0) -> full-article (1)
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) fail('expected slide 1 (the last full-article) after one PageDown, got ' + idx);

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

    // --- 3. Series-nav: Space moves through the cards one by one, then
    // exhausting them on the last slide stays put and clears focus,
    // then one more PageUp (no card was ever focused-and-released, so
    // there's nothing to step back through) leaves the slide backward --
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(navArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'PageDown'); // cover (0) -> standard (1)
    await page.waitForTimeout(600);
    await press(page, 'PageDown'); // standard (1) -> series-nav (2)
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('expected the series-nav slide (2) after two PageDown presses, got ' + idx);

    let active = await activeElementInfo(page);
    if (active.tag === 'A') fail('arriving at the series-nav slide must not auto-focus a card — the next Space press should be the one that does');

    const forwardHrefs = [];
    for (let i = 0; i < 3; i++) {
      await press(page, 'Space');
      active = await activeElementInfo(page);
      if (active.tag !== 'A') fail('Space #' + (i + 1) + ' on the series-nav slide should focus a card link, focused a ' + active.tag + ' instead');
      forwardHrefs.push(active.href);
      idx = await activeDotIndex(page);
      if (idx !== 2) fail('stepping through series-nav cards must not itself change the active slide (moved to ' + idx + ')');
    }
    if (JSON.stringify(forwardHrefs) !== JSON.stringify(['b.html', 'c.html', 'index.html'])) {
      fail('series-nav card focus order should be [b.html, c.html, index.html] (document order), got ' + JSON.stringify(forwardHrefs));
    }
    console.log('series-nav card-by-card Space OK: ' + forwardHrefs.join(' -> '));

    // Cards exhausted, and this article's series-nav slide is also the
    // LAST slide — one more Space must stay put (nothing to advance
    // to) and clear focus off the last card, not error out or leave a
    // stale focused link behind.
    await press(page, 'Space');
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('Space past the last series-nav card on the last slide should stay on slide 2, moved to ' + idx);
    active = await activeElementInfo(page);
    if (active.tag === 'A') fail('exhausting the series-nav cards on the last slide should clear focus off the last card, still focused ' + active.href);
    console.log('series-nav exhaustion-on-last-slide OK: stays put, focus cleared');

    // No card was left "mid-walk" (focusedCard was just reset above) —
    // PageUp from here has nothing to step back through and should
    // leave the slide backward directly, same as any ordinary slide.
    await press(page, 'PageUp');
    await page.waitForTimeout(600);
    idx = await activeDotIndex(page);
    if (idx !== 1) fail('PageUp with no card mid-walk should leave the series-nav slide backward to slide 1, got ' + idx);
    console.log('series-nav PageUp-with-nothing-to-step-back-through OK: left the slide backward');
    await page.close();

    // --- 4. Backward through the cards from mid-walk, then Enter jumps
    // to the focused article — fresh page, so focusedCard is still
    // genuinely mid-walk (not reset by an exhausting extra press) -----
    page = await context.newPage();
    collectConsoleErrors(page, consoleErrors);
    page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err));
    await page.goto(navArticleUrl);
    await page.waitForSelector('.nav-dots a');

    await press(page, 'PageDown');
    await page.waitForTimeout(600);
    await press(page, 'PageDown');
    await page.waitForTimeout(600);
    for (let i = 0; i < 3; i++) await press(page, 'Space'); // walk forward to the last card (index.html)
    active = await activeElementInfo(page);
    if (active.href !== 'index.html') fail('setup for the backward-walk test did not land on the last card (index.html), got ' + active.href);

    await press(page, 'Shift+Space');
    active = await activeElementInfo(page);
    if (active.href !== 'c.html') fail('first Shift+Space from the last card should step back to c.html, got ' + active.href);
    idx = await activeDotIndex(page);
    if (idx !== 2) fail('stepping backward through series-nav cards must not itself change the active slide (moved to ' + idx + ')');

    await press(page, 'Shift+Space');
    active = await activeElementInfo(page);
    if (active.href !== 'b.html') fail('second Shift+Space should step back to b.html, got ' + active.href);
    console.log('series-nav card-by-card Shift+Space OK: index.html -> c.html -> b.html');

    // Enter on the focused card jumps to the article — native browser
    // behavior once the link genuinely has focus, no extra JS required;
    // prove it actually works end to end.
    await page.keyboard.press('Enter');
    await page.waitForURL('**/b.html', { timeout: 5000 });
    console.log('Enter-on-focused-card jump OK: navigated to ' + page.url());
    await page.close();

    // --- 5. Regression: holding Space (native auto-repeat
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
      await page.keyboard.press('Space');
      await page.waitForTimeout(30);
    }
    await page.waitForTimeout(400);
    idx = await activeDotIndex(page);
    if (idx >= 3) fail('holding Space raced all the way past the series-nav slide\'s cards to slide ' + idx + ' — the step cooldown is not throttling fast repeated presses');
    else console.log('held-Space regression OK: rapid repeated Space did not skip past the series-nav cards (slide ' + idx + ')');
    await page.close();

    if (consoleErrors.length) {
      fail('unexpected console errors:\n' + consoleErrors.join('\n'));
    }

    if (process.exitCode !== 1) {
      console.log('OK — native reading scroll, direct page navigation and Space card navigation work.');
    }
  } catch (err) {
    fail(String((err && err.stack) || err));
  } finally {
    await browser.close();
  }
}

main();
