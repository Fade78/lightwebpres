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

  // --- 3. The cursor comes back only on sustained movement ------------
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
      // The mousemove listener is attached only in fullscreen, and
      // headless Chromium will not grant it without a user gesture. So
      // the page is told it IS in fullscreen and the event it listens
      // for is fired: the handler under test is the one the real
      // transition would install, reached the only way it can be here.
      Object.defineProperty(document, 'fullscreenElement', {
        value: document.documentElement, configurable: true,
      });
      document.dispatchEvent(new Event('fullscreenchange'));
      document.body.style.cursor = 'none';
      // A twitch: two events one frame apart, then nothing.
      send();
      setTimeout(() => {
        send();
        setTimeout(() => {
          const afterTwitch = document.body.style.cursor;
          // A real movement: events every 30ms for 400ms.
          const started = Date.now();
          const timer = setInterval(() => {
            send();
            if (Date.now() - started > 400) {
              clearInterval(timer);
              resolve({ afterTwitch, afterMoving: document.body.style.cursor });
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

  await browser.close();
  if (errors.length) {
    fail('console errors: ' + errors.join(' | '));
  }
}

main().catch((e) => { fail(e.message); process.exit(1); });
