// Playwright driver for the themes-gallery's four panels (§11.7).
// Invoked by test_web.py — not a standalone entry point.
//
// This exists because the panel's central claim is a LAYOUT claim, and no
// cheaper check can reach it. A panel is an iframe with a real viewport:
// asserting that the note markup is in the document proves nothing about
// whether the reader can see it, because the card is taller than the
// window and the overflow is hidden. Shrinking the panel back to the
// height it had before the note existed left every offline test green
// while the note fell out of the frame — which is the one thing the
// "card, with a note" panel is there to show.
//
// So this measures, inside the frame: the note block's bottom edge
// against the frame's own height. Same for the notes section's top rule,
// which is what the second panel is for.
//
// argv: <fileUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

function fail(msg) { console.error('FAIL: ' + msg); process.exitCode = 1; }

async function main() {
  const [fileUrl] = process.argv.slice(2);
  if (!fileUrl) {
    console.error('usage: gallery_panels_e2e.cjs <fileUrl>');
    process.exit(2);
  }
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const consoleErrors = [];
  collectConsoleErrors(page, consoleErrors);

  await page.goto(fileUrl);
  // The frames are lazy; only the first rows are ever needed here.
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1500);

  const rows = await page.$$('.theme-row');
  if (rows.length < 1) fail('no .theme-row on the page');

  const panels = await rows[0].$$('.panel');
  if (panels.length !== 4) fail(`row 0 has ${panels.length} panels, expected 4`);

  // Panel 2: the note must be INSIDE the window, not merely in the markup.
  const cardFrame = await (await panels[1].$('iframe')).contentFrame();
  const cardGeom = await cardFrame.evaluate(() => {
    const block = document.querySelector('.notes-local');
    if (!block) return null;
    const r = block.getBoundingClientRect();
    return { top: r.top, bottom: r.bottom, viewport: window.innerHeight,
             body: document.querySelector('.note-body li') ? 1 : 0 };
  });
  if (!cardGeom) {
    fail('the card panel renders no .notes-local at all');
  } else {
    if (!cardGeom.body) fail('the card panel has a note block with no body in it');
    if (cardGeom.bottom > cardGeom.viewport) {
      fail(`the note falls out of the card panel: bottom ${cardGeom.bottom.toFixed(0)}px ` +
           `in a ${cardGeom.viewport}px window`);
    }
    if (cardGeom.top < 0) fail('the note block starts above the card panel');
  }

  // Panel 3: the section's own top rule has to be visible, which is why
  // there is a strip of bare page above it.
  const notesFrame = await (await panels[2].$('iframe')).contentFrame();
  const notesGeom = await notesFrame.evaluate(() => {
    const s = document.querySelector('.notes-section');
    if (!s) return null;
    const r = s.getBoundingClientRect();
    return { top: r.top,
             rule: parseFloat(getComputedStyle(s).borderTopWidth),
             items: document.querySelectorAll('.note-body li').length };
  });
  if (!notesGeom) {
    fail('the notes panel renders no .notes-section');
  } else {
    if (notesGeom.top <= 0) fail('the notes section starts at or above the panel edge — its rule is clipped');
    if (!(notesGeom.rule > 0)) fail('the notes section draws no top rule');
    if (notesGeom.items < 2) fail(`the notes panel shows ${notesGeom.items} bodies, expected 2`);
  }

  if (consoleErrors.length) fail('console errors: ' + consoleErrors.join(' | '));
  await browser.close();
  if (!process.exitCode) console.log('OK: four panels, note inside the card, rule inside the section');
}

main().catch((e) => { console.error(e); process.exit(1); });
