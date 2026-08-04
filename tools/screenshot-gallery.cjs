// Renders themes-gallery.html to themes-gallery.png, the snapshot the
// README embeds. Maintenance script — not part of the test suite, and
// not something a user of lightwebpres ever needs to run.
//
//   node tools/screenshot-gallery.cjs [in.html] [out.png]
//
// Requires Playwright. In this repo's container:
//   NODE_PATH=/opt/node22/lib/node_modules \
//   PW_CHROMIUM_PATH=/opt/pw-browsers/chromium \
//   node tools/screenshot-gallery.cjs
//
// Why this exists rather than "just take a screenshot": each card's
// preview is an <iframe loading="lazy">, which is right for the live
// page (33 nested browsing contexts) and fatal for a full-page capture —
// a headless full-page screenshot never scrolls, so every iframe below
// the first viewport stays unloaded and shoots blank. The README picked
// up exactly that image once. So the script drops the lazy attribute,
// re-navigates every frame, waits for all 33 to paint a real slide, and
// only then captures.
//
// The frames are sandboxed, so the page itself cannot look inside them
// (contentDocument is null across an opaque origin). Playwright can:
// page.frames() reaches them through the debugger protocol, which is how
// the blank-preview check below is possible at all.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const REPO = path.resolve(__dirname, '..');
const IN = path.resolve(process.argv[2] || path.join(REPO, 'themes-gallery.html'));
const OUT = path.resolve(process.argv[3] || path.join(REPO, 'themes-gallery.png'));

// 1280 leaves the .wrap (max-width: 1180px) room to breathe at its full
// width, which is a three-column grid — the widest the page ever gets.
const VIEWPORT = { width: 1280, height: 1400 };
const TIMEOUT = 120000;

async function main() {
  if (!fs.existsSync(IN)) {
    console.error(`missing ${IN} — run ./lightwebpres themes-gallery first`);
    process.exit(2);
  }
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 1 });

  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('file://' + IN, { waitUntil: 'load' });

  const expected = await page.evaluate(() => {
    const frames = [].slice.call(document.querySelectorAll('iframe.preview'));
    frames.forEach(function (f) {
      f.removeAttribute('loading');
      f.srcdoc = f.srcdoc;   // re-assigning navigates the frame, lazy or not
    });
    return frames.length;
  });
  if (expected === 0) throw new Error('no iframe.preview found — is this the themes gallery?');

  const deadline = Date.now() + TIMEOUT;
  while (page.frames().length < expected + 1) {
    if (Date.now() > deadline) {
      throw new Error(`only ${page.frames().length - 1}/${expected} previews attached`);
    }
    await page.waitForTimeout(200);
  }

  // A frame that attached can still be blank. Assert a real painted
  // slide in every single one before spending a capture on it.
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    await frame.waitForSelector('.slide', { state: 'attached', timeout: TIMEOUT });
  }

  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.screenshot({ path: OUT, fullPage: true });
  await browser.close();

  if (errors.length) {
    console.error('page errors:\n  ' + errors.join('\n  '));
    process.exit(1);
  }
  console.log(`wrote ${OUT} (${expected} previews, ${VIEWPORT.width}px wide, ` +
              `${(fs.statSync(OUT).size / 1024).toFixed(0)} kB)`);
}

main().catch((e) => { console.error(e); process.exit(1); });
