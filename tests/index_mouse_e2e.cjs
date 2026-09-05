// Playwright driver for the index page as a card deck (§8.4): with the
// two skeletons unified, the index carries the article's navigation
// engine and the cards ARE the journey. Invoked by
// tests/test_index_mouse.py — not a standalone entry point.
//
// What is under test, in a real browser, with real pointer events:
//   - a left click on the ground focuses the next card;
//   - a right click on the ground focuses the previous card;
//   - a click on a card follows it (the card is a link, and a click on
//     it is interactive — the deck must not steal it);
//   - Enter on a focused card follows it (the browser's own default);
//   - the share action in the presenter menu opens the popover, copies the
//     series and article links, and keeps the fiche scope disabled — the index has no
//     fiche (§9.3.4);
//   - middle-then-left asks for fullscreen (stubbed, like the other
//     e2e: headless Chromium refuses the request without a gesture);
//   - Home returns to the top of the page.
//
// argv: <indexUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

function fail(msg) {
  console.error('E2E failure: ' + msg);
  process.exitCode = 1;
}

async function main() {
  const [indexUrl] = process.argv.slice(2);
  if (!indexUrl) {
    console.error('usage: index_mouse_e2e.cjs <indexUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(
    executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  collectConsoleErrors(page, errors);

  await page.goto(indexUrl, { waitUntil: 'load' });
  await page.waitForTimeout(300);
  const openShare = async () => {
    await page.click('#navMenu');
    await page.waitForSelector('#presenterMenu.open');
    await page.click('#menuShare');
    await page.waitForSelector('#sharePopover.open');
  };

  // Non-vacuity first: the fixture must carry cards for the journey to
  // exist at all.
  const cardCount = await page.locator('.article-card').count();
  if (cardCount < 3) {
    fail('the fixture index carries fewer than three cards, so the focus '
         + 'journey has nowhere to go: ' + cardCount);
  }

  const focusedCard = () => page.evaluate(() => {
    const a = document.activeElement;
    return a && a.classList && a.classList.contains('article-card')
      ? Array.prototype.indexOf.call(document.querySelectorAll('.article-card'), a)
      : -1;
  });

  // --- 0. Focusing a card must reveal the whole card immediately --------
  // The page uses smooth scrolling for deliberate deck moves. A bare
  // focus() inherits that setting in Chromium and leaves a newly selected
  // card clipped at the viewport edge while the native animation runs.
  const visibilityPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  collectConsoleErrors(visibilityPage, errors);
  await visibilityPage.goto(indexUrl, { waitUntil: 'load' });
  await visibilityPage.waitForSelector('.article-card');
  await visibilityPage.evaluate(() => {
    document.querySelectorAll('.article-card').forEach((card) => {
      card.style.minHeight = '320px';
    });
    window.scrollTo({ top: document.scrollingElement.scrollHeight,
      behavior: 'instant' });
  });
  await visibilityPage.keyboard.press('ArrowDown');
  await visibilityPage.waitForTimeout(200);
  let selectedBounds = await visibilityPage.evaluate(() => {
    const card = document.activeElement;
    const rect = card.getBoundingClientRect();
    return {
      isCard: card.classList.contains('article-card'),
      top: rect.top,
      bottom: rect.bottom,
      viewport: window.innerHeight,
    };
  });
  if (!selectedBounds.isCard || selectedBounds.top < -1
      || selectedBounds.bottom > selectedBounds.viewport + 1) {
    fail('the selected first index card is not fully visible: '
         + JSON.stringify(selectedBounds));
  }
  await visibilityPage.keyboard.press('ArrowDown');
  selectedBounds = await visibilityPage.evaluate(() => {
    const card = document.activeElement;
    const rect = card.getBoundingClientRect();
    return {
      isCard: card.classList.contains('article-card'),
      top: rect.top,
      bottom: rect.bottom,
      viewport: window.innerHeight,
    };
  });
  if (!selectedBounds.isCard || selectedBounds.top < -1
      || selectedBounds.bottom > selectedBounds.viewport + 1) {
    fail('the selected index card is not fully visible: '
         + JSON.stringify(selectedBounds));
  }
  await visibilityPage.close();

  // --- 1. A left click on the ground focuses the next card -----------
  // The "ground" is the page's own margin: the cards fill the content
  // column (a click on one of them would follow it, which is test 3),
  // so the click lands in the left margin, away from every card and
  // from the nav chrome.
  const groundX = 50;
  const groundY = 400;
  await page.mouse.click(groundX, groundY);
  await page.waitForTimeout(300);
  const afterLeft = await focusedCard();
  if (afterLeft !== 0) {
    fail('a ground click did not focus the first card: ' + afterLeft);
  }

  // --- 2. A right click on the ground focuses the previous card ------
  // From the first card there is nowhere to go back to — focus the
  // second card first, then right-click.
  await page.keyboard.press('ArrowDown');
  await page.waitForTimeout(200);
  await page.mouse.click(groundX, groundY, { button: 'right' });
  await page.waitForTimeout(300);
  const afterRight = await focusedCard();
  if (afterRight !== 0) {
    fail('a right-click did not focus the previous card: ' + afterRight);
  }

  // --- 3. A click on a card follows it --------------------------------
  // The click target is the card's own link (isInteractive), so the
  // deck must let the native default through. The landing is asserted
  // by the article's own chrome: the page has slides and a dot.
  await page.locator('.article-card').nth(0).click();
  await page.waitForTimeout(1200);
  const onArticle = await page.evaluate(() => ({
    slides: document.querySelectorAll('section.slide').length,
    dots: document.querySelectorAll('.nav-dots a').length,
  }));
  if (onArticle.slides < 1 || onArticle.dots < 1) {
    fail('a click on a card did not follow it to the article: '
         + JSON.stringify(onArticle));
  }
  await page.goBack();
  await page.waitForTimeout(600);

  // --- 4. Enter on a focused card follows it --------------------------
  await page.keyboard.press('ArrowDown');
  await page.waitForTimeout(200);
  const focusedBeforeEnter = await focusedCard();
  if (focusedBeforeEnter !== 0) {
    fail('the arrow did not focus the first card for the Enter test: '
         + focusedBeforeEnter);
  }
  await page.keyboard.press('Enter');
  await page.waitForTimeout(1200);
  const landedByEnter = await page.evaluate(
    () => document.querySelectorAll('section.slide').length);
  if (landedByEnter < 1) {
    fail('Enter on a focused card did not follow it: ' + landedByEnter);
  }
  await page.goBack();
  await page.waitForTimeout(600);

  // --- 5. The share popover works on the index, fiche disabled --------
  await openShare();
  const popoverOpen = await page.evaluate(
    () => document.getElementById('sharePopover').classList.contains('open'));
  if (!popoverOpen) {
    fail('the share popover does not open on the index');
  }
  const ficheState = await page.evaluate(() => ({
    disabled: Array.prototype.every.call(
      document.querySelectorAll('[data-scope="fiche"]'), (b) => b.disabled),
    headDisabled: document.getElementById('shareHeadFiche')
      .classList.contains('share-cell-head-disabled'),
  }));
  if (!ficheState.disabled || !ficheState.headDisabled) {
    fail('the fiche scope must be disabled on the index: '
         + JSON.stringify(ficheState));
  }
  // The copy action with a stubbed clipboard, so the URL is under test
  // and not the clipboard plumbing.
  await page.evaluate(() => {
    window.__copied = null;
    navigator.clipboard.writeText = function (text) {
      window.__copied = text;
      return Promise.resolve();
    };
  });
  await page.click('[data-action="copy"][data-scope="article"]');
  const articleLink = await page.evaluate(() => window.__copied);
  if (articleLink !== indexUrl) {
    fail('the article link copied on the index is not the index URL: '
         + articleLink + ' expected ' + indexUrl);
  }
  await page.click('[data-action="copy"][data-scope="series"]');
  const seriesLink = await page.evaluate(() => window.__copied);
  if (seriesLink !== indexUrl) {
    fail('the series link copied on the index is not the index URL: '
         + seriesLink + ' expected ' + indexUrl);
  }
  await page.keyboard.press('Escape');

  // --- 6. Middle-then-left asks for fullscreen (two-step entry) -------
  // The same stub as chrome_behaviour_e2e: the middle button alone can
  // only EXIT (browsers refuse requestFullscreen from a non-left
  // event), so the entry is a middle press then a LEFT click within the
  // window — on the index exactly as on an article (B37).
  await page.evaluate(() => {
    window.__fs = 0;
    window.__inFs = false;
    Object.defineProperty(document, 'fullscreenElement', {
      get: () => window.__inFs ? document.documentElement : null,
    });
    document.documentElement.requestFullscreen = function () {
      window.__fs++; window.__inFs = true; return Promise.resolve();
    };
  });
  await page.mouse.click(groundX, groundY, { button: 'middle' });
  await page.waitForTimeout(50);
  await page.mouse.click(groundX, groundY);
  await page.waitForTimeout(300);
  const fsAsked = await page.evaluate(() => window.__fs);
  if (fsAsked !== 1) {
    fail('middle-then-left on the index did not ENTER fullscreen: fs asked '
         + fsAsked + ' times');
  }

  // --- 7. Home returns to the top of the page ------------------------
  await page.evaluate(() => window.scrollTo({ top: 99999, behavior: 'instant' }));
  await page.waitForTimeout(300);
  await page.keyboard.press('Home');
  await page.waitForTimeout(600);
  const homeState = await page.evaluate(() => ({
    y: window.pageYOffset || document.documentElement.scrollTop,
    focused: document.activeElement && document.activeElement.classList
      && document.activeElement.classList.contains('article-card'),
  }));
  if (homeState.y > 5) {
    fail('Home did not return to the top of the index: y=' + homeState.y);
  }
  if (homeState.focused) {
    fail('Home left a card focused on the index');
  }

  if (errors.length) {
    fail('console errors: ' + errors.join(' | '));
  }

  await browser.close();
  if (process.exitCode) process.exit(process.exitCode);
  console.log('OK');
}

main().catch((e) => { fail(e.message); process.exit(1); });
