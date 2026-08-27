/* Measures three things a built deck promises and no test checked:
 *   keyboard  — can the slide-variant dialog be operated without a mouse?
 *   contrast  — is the speaker counter legible against its own ground?
 *   print     — does one slide really get one sheet?
 *
 * All three are measured on the RENDERED page, never on the stylesheet.
 * The project's own record (ETUDE-VIEWPORT §12) is a themeable property
 * that had never once worked while its test asserted only that the value
 * reached the sheet; the print rule here was the same shape of mistake —
 * `.slide:last-child` matched nothing on any page ever built, and a
 * string check on the emitted CSS would have called that fine.
 *
 * Usage: node deck_a11y_e2e.cjs <file:// URL of a built page>
 * Prints one JSON object; the Python side does the asserting.
 */
const { chromium } = require('playwright');

const URL = process.argv[2];

function relativeLuminance([r, g, b]) {
  const f = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const [R, G, B] = [f(r), f(g), f(b)];
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

function contrast(fg, bg) {
  const [hi, lo] = [relativeLuminance(fg), relativeLuminance(bg)]
    .sort((a, b) => b - a);
  return (hi + 0.05) / (lo + 0.05);
}

(async () => {
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const out = {};

  // --- keyboard: the slide-variant dialog -------------------------------
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(URL);
  const where = () => page.evaluate(() => {
    const a = document.activeElement;
    if (!a) return { tag: 'none', inMenu: false };
    return {
      tag: a.tagName + (a.className ? '.' + a.className : ''),
      inMenu: !!(a.closest && a.closest('.tag-menu')),
    };
  });
  const menuOpen = () => page.evaluate(
    () => !!document.querySelector('.tag-menu.open'));

  await page.keyboard.press('l');
  out.menuOpens = await menuOpen();
  out.focusOnOpen = await where();
  const walk = [];
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    walk.push((await where()).inMenu);
  }
  await page.keyboard.press('Shift+Tab');
  walk.push((await where()).inMenu);
  // Every step of the walk must still be inside the dialog: Tab out of an
  // open modal is the one place a focus ring must not go.
  out.focusStaysInMenu = walk.every(Boolean);
  await page.keyboard.press('Enter');
  out.menuClosesOnEnter = !(await menuOpen());
  out.focusReturnedTo = (await where()).tag;
  await page.keyboard.press('l');
  await page.keyboard.press('Escape');
  out.menuClosesOnEscape = !(await menuOpen());

  // --- presenter panel: does it READ the note? ---------------------------
  // Nothing measured this. The Python side proves a `note:` is emitted
  // hidden and never visible on the card -- both true, both useless if
  // the panel that is supposed to surface it never looks. Mutating
  // `presenterNotes.textContent = noteEl ? ... : '—'` to a bare '—' left
  // the whole suite green: the word "presenter" appeared in the test tree
  // only inside three comments.
  await page.keyboard.press('n');
  out.presenter = await page.evaluate(() => {
    const panel = document.getElementById('presenterPanel');
    const notes = document.getElementById('presenterNotes');
    return {
      open: !!(panel && panel.classList.contains('open')),
      notes: notes ? notes.textContent.trim() : null,
      next: (document.querySelector('.pp-next') || {}).textContent || '',
      // A scrollable region (overflow:auto + max-height) that cannot take
      // focus cannot be scrolled from the keyboard at all: the panel is
      // capped at 44vh and a long note is exactly what it is for.
      role: panel ? panel.getAttribute('role') : null,
      label: panel ? panel.getAttribute('aria-label') : null,
      tabindex: panel ? panel.getAttribute('tabindex') : null,
      live: notes ? notes.getAttribute('aria-live') : null,
    };
  });
  // Escape reached every other overlay -- help, the variant dialog, the
  // share popover, the QR modal -- and not this one.
  await page.keyboard.press('Escape');
  out.presenter.closesOnEscape = !(await page.evaluate(() => {
    const p = document.getElementById('presenterPanel');
    return !!(p && p.classList.contains('open'));
  }));
  if (!out.presenter.closesOnEscape) await page.keyboard.press('n');

  // --- contrast: the speaker counter on slide 1 (the cover gradient) ----
  out.counter = await page.evaluate(() => {
    const el = document.querySelector('.slide-counter');
    if (!el) return null;
    const cs = getComputedStyle(el);
    const nums = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
    // The element's own resolved background, which is the whole point:
    // `background: none` used to let the cover's gradient through and the
    // counter's ink WAS that gradient's first stop on a light theme.
    return { fg: nums(cs.color), bg: nums(cs.backgroundColor),
             bgRaw: cs.backgroundColor };
  });
  if (out.counter && out.counter.bg.length === 3) {
    out.counterContrast = contrast(out.counter.fg, out.counter.bg);
  } else {
    out.counterContrast = null;  // transparent: nothing to measure against
  }

  // --- geometry: is the chrome drawn against what it holds? -------------
  // Both measured at 3840, where a length stated flat has drifted
  // furthest from the type it was drawn against.
  // Its OWN context, not just its own page. The keyboard walk above
  // applied a tag with Enter, and that selection is remembered in
  // localStorage -- which a second page on the same file:// origin
  // inherits, so the card measured here came back hidden, with a
  // zero-size rect and a padding that resolves to nothing. Measuring a
  // display:none element is how a geometry probe reports 0px of drift
  // while the page is as wrong as it ever was.
  const wideCtx = await browser.newContext({
    viewport: { width: 3840, height: 2160 } });
  const wide = await wideCtx.newPage();
  await wide.goto(URL);
  out.wide = await wide.evaluate(() => {
    const val = (el, prop) => parseFloat(getComputedStyle(el)[prop]);
    const btn = document.querySelector('.nav-btn');
    const home = document.querySelector('.nav-btn-home');
    // A VISIBLE section card, not the cover: the cover has its own
    // number component and the point here is the ordinary case. Visible
    // because a hidden card has no geometry to compare.
    const slide = Array.prototype.filter.call(
      document.querySelectorAll('.slide'),
      (s) => getComputedStyle(s).display !== 'none'
             && !s.classList.contains('slide-cover'))[0]
      || document.querySelector('.slide');
    const num = slide.querySelector('.slide-num');
    const cs = getComputedStyle(slide);
    const box = slide.getBoundingClientRect();
    return {
      // The glyph inside its own circle: `nav-btn.size` is a theme
      // property that grows, the 44x44 button was not, and at 4K the
      // glyph stood outside the circle it is centred in.
      navBtnBox: btn ? btn.getBoundingClientRect().width : null,
      navBtnGlyph: btn ? val(btn, 'fontSize') : null,
      navHomeGlyph: home ? val(home, 'fontSize') : null,
      // The number over the COLUMN, not over the card: `right: 32px`
      // measured it from the card edge while the text starts at the
      // padding, and the two drifted apart as the screen grew.
      numRight: num ? num.getBoundingClientRect().right : null,
      columnRight: box.right - parseFloat(cs.paddingRight),
      panelNote: (() => {
        const n = document.getElementById('presenterNotes');
        return n ? val(n, 'fontSize') : null;
      })(),
    };
  });
  await wide.close();
  await wideCtx.close();

  // --- print: one slide, one sheet --------------------------------------
  // VISIBLE slides. The variant filter hides the cards that do not carry
  // the active tag, and a hidden card prints no sheet — counting all of
  // them would compare a printed page against a card nobody asked to see.
  out.slideCount = await page.evaluate(() => Array.prototype.filter.call(
    document.querySelectorAll('.slide'),
    (s) => getComputedStyle(s).display !== 'none').length);
  const pdf = await page.pdf({
    format: 'A4',
    margin: { top: '1.5cm', bottom: '1.5cm', left: '1.5cm', right: '1.5cm' },
  });
  out.pdfPages = (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length;

  await page.close();
  await browser.close();
  console.log(JSON.stringify(out, null, 1));
})().catch((err) => { console.error(err); process.exit(1); });
