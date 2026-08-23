// Renders generated/themes-gallery.html to generated/themes-gallery.png,
// the snapshot the README embeds. Maintenance script — not part of the
// test suite, and not something a user of lightwebpres ever needs to run.
//
//   node tools/screenshot-gallery.cjs [in.html] [out.png] [--full]
//
// Requires Playwright. In this repo's container:
//   NODE_PATH=/opt/node22/lib/node_modules \
//   PW_CHROMIUM_PATH=/opt/pw-browsers/chromium \
//   node tools/screenshot-gallery.cjs
//
// Why this exists rather than "just take a screenshot": each preview is
// an <iframe loading="lazy">, which is right for the live page and fatal
// for a full-page capture — a headless full-page screenshot never paints
// the off-screen iframe compositor tiles reliably. The README picked up
// exactly that image once. The contact sheet is therefore assembled from a
// blank page capture plus one row screenshot at a time, with the row
// scrolled into view before it is captured.
//
// It also rearranges the page before capturing, because the gallery has
// outgrown a straight screenshot: see CONTACT SHEET below.
//
// The frames are sandboxed, so the page itself cannot look inside them
// (contentDocument is null across an opaque origin). Playwright can,
// through the debugger protocol, which is how the blank-preview check
// below is possible at all. It reaches them through the elements that
// own them rather than through page.frames() — see the wait loop for the
// measurement that forced that.

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const REPO = path.resolve(__dirname, '..');
const args = process.argv.slice(2).filter((a) => a !== '--full');
const FULL = process.argv.includes('--full');
const IN = path.resolve(args[0] || path.join(REPO, 'generated', 'themes-gallery.html'));
const OUT = path.resolve(args[1] || path.join(REPO, 'generated', 'themes-gallery.png'));

// CONTACT SHEET is the default, and the page's own layout is the reason.
// The gallery gives each theme a ROW of four panels — cover, card,
// article, notes — and a panel is a real viewport at a real rendering
// width, 560px tall at 340 wide. Captured as the page lays itself out,
// the whole catalogue is one column of rows: measured at 1280 wide, that
// came to 57,197 pixels of height and 8.5 MB, which is not an image a
// README can carry.
//
// So this mode keeps the FIRST panel of each theme — the cover, the one
// that shows a palette fastest — and lays the rows four across. Nothing
// is redrawn or imitated: the same page, the same iframes, the same
// sheet, with panels hidden and the row container turned into a grid.
// `--gal-panel` is pinned rather than left to its `clamp()` so every
// panel is the same rendering width, which is the property the whole
// gallery is built on.
//
// `--full` captures the page as it stands, every panel, for anyone who
// wants the long strip.
const PANEL = 340;                 // the clamp's own floor
const COLUMNS = 4;
const ROW = PANEL + 38;            // + .panels padding (2x18) and the row's border
const VIEWPORT = FULL
  ? { width: 1280, height: 1400 }
  : { width: COLUMNS * ROW + (COLUMNS - 1) * 18 + 56 + 24, height: 1400 };
const TIMEOUT = 120000;

// Applied before the frames are re-navigated, so each preview renders at
// the width it will be captured at rather than being resized after paint.
const CONTACT_CSS = `
  :root { --gal-panel: ${PANEL}px !important; }
  .wrap { max-width: none !important; padding-left: 28px; padding-right: 28px; }
  .masthead, .facets, .facet-count, .theme-note, .fact-treatment { display: none !important; }
  .grid {
    display: grid !important;
    grid-template-columns: repeat(${COLUMNS}, max-content) !important;
    gap: 18px !important;
  }
  /* One track, not four. The page's own rule reserves a column per
     panel, and a grid track is reserved whether or not anything is in
     it — with three panels gone the rows still measured 1460px wide,
     four fifths of it empty. */
  .panels {
    overflow-x: visible !important;
    grid-template-columns: ${PANEL}px !important;
  }
  .panel:nth-of-type(n+2) { display: none !important; }
  /* The base page is captured with frames hidden, then each row is painted
     and composited back into it while that row is in the viewport. */
  .preview { visibility: hidden !important; }
`;

async function main() {
  if (!fs.existsSync(IN)) {
    console.error(`missing ${IN} — run ./lightwebpres theme gallery first`);
    process.exit(2);
  }
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: 1 });

  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('file://' + IN, { waitUntil: 'load' });

  if (!FULL) await page.addStyleTag({ content: CONTACT_CSS });

  const expected = await page.evaluate((contact) => {
    if (contact) {
      // Drop the hidden panels' frames outright rather than leaving them
      // display:none. A hidden iframe still attaches and still has to
      // paint before the capture is allowed to proceed, so keeping them
      // would cost three quarters of the wait for pixels nobody sees.
      [].slice.call(document.querySelectorAll('.panel:nth-of-type(n+2)'))
        .forEach(function (p) { p.remove(); });
    }
    const frames = [].slice.call(document.querySelectorAll('iframe.preview'));
    frames.forEach(function (f) {
      f.removeAttribute('loading');
      f.srcdoc = f.srcdoc;   // re-assigning navigates the frame, lazy or not
    });
    return frames.length;
  }, !FULL);
  if (expected === 0) throw new Error('no iframe.preview found — is this the themes gallery?');

  // The frames are reached through the elements that own them, not
  // through page.frames(). Removing a panel does not take its frame out
  // of that list — measured: with 171 panels removed, page.frames() went
  // on reporting all 228, `isDetached()` false on every one, and waiting
  // on one of the dead ones fails with "target closed", which names the
  // wrong problem entirely and cost an afternoon. An element handle can
  // only give back the frame it actually owns.
  const deadline = Date.now() + TIMEOUT;
  const handles = await page.$$('iframe.preview');
  if (handles.length !== expected) {
    throw new Error(`${handles.length} preview elements, expected ${expected}`);
  }

  async function frameFor(handle) {
    let frame = null;
    while (!frame) {
      frame = await handle.contentFrame();
      if (frame) break;
      if (Date.now() > deadline) throw new Error('a preview never attached');
      await page.waitForTimeout(200);
    }
    return frame;
  }

  await page.evaluate(() => document.fonts && document.fonts.ready);

  let outputWidth = VIEWPORT.width;
  if (FULL) {
    // The long-strip mode is kept for inspection, not for the README. It
    // retains the old shape and only needs the DOM guard.
    for (const handle of handles) {
      const frame = await frameFor(handle);
      await frame.waitForSelector('.slide', { state: 'attached', timeout: TIMEOUT });
    }
    await page.screenshot({ path: OUT, fullPage: true });
  } else {
    // A full-page screenshot does not retain the painted contents of
    // off-screen iframes, even after their DOM has loaded. Capture a blank
    // layout first, then replace each row's hidden preview with a screenshot
    // taken while that row is in the viewport.
    const rows = await page.$$('.theme-row');
    if (rows.length !== expected) {
      throw new Error(`${rows.length} theme rows, expected ${expected}`);
    }
    const positions = await page.evaluate(() => (
      [...document.querySelectorAll('.theme-row')].map((row) => {
        const rect = row.getBoundingClientRect();
        return {
          x: rect.left + window.scrollX,
          y: rect.top + window.scrollY,
          width: rect.width,
          height: rect.height,
        };
      })
    ));
    const base = await page.screenshot({ fullPage: true });
    const captures = [];

    for (let index = 0; index < rows.length; index += 1) {
      await page.evaluate((current) => {
        document.querySelectorAll('.theme-row .preview').forEach((frame) => {
          frame.style.setProperty('visibility', 'hidden', 'important');
        });
        document.querySelectorAll('.theme-row')[current]
          .querySelectorAll('.preview')
          .forEach((frame) => {
            frame.style.setProperty('visibility', 'visible', 'important');
          });
      }, index);
      await rows[index].scrollIntoViewIfNeeded();
      const handle = await rows[index].$('iframe.preview');
      const frame = await frameFor(handle);
      await frame.waitForSelector('.slide', { state: 'attached', timeout: TIMEOUT });
      await page.waitForTimeout(20);
      captures.push({
        ...positions[index],
        data: (await rows[index].screenshot()).toString('base64'),
      });
    }

    const composed = await page.evaluate(async ({ base64, captures }) => {
      const load = (source) => new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = source;
      });
      const baseImage = await load(`data:image/png;base64,${base64}`);
      const canvas = document.createElement('canvas');
      canvas.width = baseImage.naturalWidth;
      canvas.height = baseImage.naturalHeight;
      const context = canvas.getContext('2d');
      context.drawImage(baseImage, 0, 0);
      for (const capture of captures) {
        const image = await load(`data:image/png;base64,${capture.data}`);
        context.drawImage(image, capture.x, capture.y);
      }
      return {
        data: canvas.toDataURL('image/png'),
        width: canvas.width,
      };
    }, { base64: base.toString('base64'), captures });
    fs.writeFileSync(OUT, Buffer.from(composed.data.split(',')[1], 'base64'));
    outputWidth = composed.width;
  }
  await browser.close();

  if (errors.length) {
    console.error('page errors:\n  ' + errors.join('\n  '));
    process.exit(1);
  }
  console.log(`wrote ${OUT} (${expected} previews, ${outputWidth}px wide, ` +
              `${(fs.statSync(OUT).size / 1024).toFixed(0)} kB)`);
}

main().catch((e) => { console.error(e); process.exit(1); });
