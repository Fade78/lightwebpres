/* Instrument 2: contrast measured on the RENDERED page.
 *
 * `theme show` reports contrast from the property registry — resolved
 * values, composited grounds, computed by the same engine that emits the
 * sheet. That is the right way to check a theme, and it is structurally
 * unable to see three things:
 *
 *   - an element with no registry property of its own (the speaker
 *     counter measured 1.00:1 on 15 themes and the report could not say
 *     so, because there was nothing for it to read);
 *   - a ground that arrives from an ancestor rather than from the
 *     element (a transparent background inherits whatever is behind it,
 *     which the registry does not model);
 *   - a card variant an AUTHOR defines, which the registry has never
 *     heard of.
 *
 * So this walks the DOM. For every element with its own visible text it
 * resolves the ink, composites the grounds upward until an opaque one is
 * found, and reports the ratio with the size and weight that decide which
 * threshold applies (WCAG 1.4.3: 3:1 for large text, 4.5:1 otherwise).
 *
 * Usage: node contrast_e2e.cjs <file:// URL of a built page>
 * Prints one JSON object; the Python side does the asserting.
 */
const { chromium } = require('playwright');

const URL = process.argv[2];

(async () => {
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(URL);

  const out = await page.evaluate(() => {
    const parse = (s) => {
      const n = (s.match(/[\d.]+/g) || []).map(Number);
      if (n.length < 3) return null;
      return { r: n[0], g: n[1], b: n[2], a: n.length > 3 ? n[3] : 1 };
    };
    const over = (fg, bg) => ({
      r: fg.r * fg.a + bg.r * (1 - fg.a),
      g: fg.g * fg.a + bg.g * (1 - fg.a),
      b: fg.b * fg.a + bg.b * (1 - fg.a),
      a: 1,
    });
    const lum = (c) => {
      const f = (v) => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
      };
      return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
    };
    const ratio = (a, b) => {
      const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
      return (hi + 0.05) / (lo + 0.05);
    };

    // Every colour a gradient paints under the text. A gradient's
    // `backgroundColor` is transparent, so an instrument that reads only
    // that walks straight past the cover and lands on the page behind it
    // -- and on a light theme the page ground IS the cover's ink, so it
    // reports 1.00:1 for text that is perfectly legible. Text over a
    // gradient has to clear the bar at every stop it crosses, so each
    // stop becomes a candidate ground and the WORST one is the answer.
    const stopsOf = (cs) => {
      const img = cs.backgroundImage;
      if (!img || img === 'none' || !/gradient/.test(img)) return [];
      return (img.match(/rgba?\([^)]*\)/g) || []).map(parse).filter(Boolean);
    };

    // The grounds an element is actually painted on: walk up compositing
    // every semi-transparent layer until an opaque one closes it. The
    // canvas is white, which is what a browser paints behind <html>.
    // Returns a list, because a gradient anywhere in the chain makes the
    // answer several colours rather than one.
    // What is BEHIND a floating element, which its ancestors do not say.
    // `.slide-counter` is position:fixed, so its DOM parent is <body> --
    // and the thing it is actually painted over is whichever slide is
    // scrolled under it. Reading the ancestor chain reported the page
    // ground and called the counter legible; the defect that made this
    // instrument necessary was the counter at 1.00:1 over the COVER's
    // gradient. elementsFromPoint gives the real paint stack at a point,
    // which is the only place that answer exists.
    const stackUnder = (el) => {
      const b = el.getBoundingClientRect();
      const x = b.left + b.width / 2;
      const y = b.top + b.height / 2;
      if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return null;
      const stack = document.elementsFromPoint(x, y);
      const at = stack.indexOf(el);
      // From the element itself downward. Starting BELOW it drops its
      // own background, which for the counter is the whole fix -- an
      // opaque ground of its own is precisely what stops the cover's
      // gradient deciding whether it can be read.
      return at < 0 ? null : stack.slice(at);
    };

    const groundsOf = (el) => {
      const layers = [];
      const pos = getComputedStyle(el).position;
      const chain = (pos === 'fixed' || pos === 'sticky')
        ? stackUnder(el) : null;
      for (const n of (chain || [])) {
        const cs = getComputedStyle(n);
        const stops = stopsOf(cs);
        if (stops.length) {
          layers.push(stops);
          if (stops.every((s) => s.a === 1)) break;
          continue;
        }
        const bg = parse(cs.backgroundColor);
        if (!bg || bg.a === 0) continue;
        layers.push([bg]);
        if (bg.a === 1) break;
      }
      for (let n = chain ? null : el; n; n = n.parentElement) {
        const cs = getComputedStyle(n);
        const stops = stopsOf(cs);
        if (stops.length) {
          layers.push(stops);
          if (stops.every((s) => s.a === 1)) break;
          continue;
        }
        const bg = parse(cs.backgroundColor);
        if (!bg || bg.a === 0) continue;
        layers.push([bg]);
        if (bg.a === 1) break;
      }
      let grounds = [{ r: 255, g: 255, b: 255, a: 1 }];
      for (let i = layers.length - 1; i >= 0; i--) {
        const next = [];
        for (const g of grounds) for (const l of layers[i]) next.push(over(l, g));
        grounds = next;
      }
      return grounds;
    };

    // Its OWN text: a <section> whose children carry the words is not
    // painting text itself, and counting it reports the same string once
    // per ancestor.
    const ownText = (el) => Array.prototype.some.call(
      el.childNodes,
      (n) => n.nodeType === 3 && n.textContent.trim().length > 0);

    const results = [];
    const seen = new Set();
    for (const el of document.querySelectorAll('body *')) {
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      if (parseFloat(cs.opacity) === 0) continue;
      if (!ownText(el)) continue;
      const box = el.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) continue;

      const fgRaw = parse(cs.color);
      if (!fgRaw) continue;
      const grounds = groundsOf(el);
      // The ink itself may be semi-transparent -- several themes quiet a
      // line that way rather than with a second colour -- so it is
      // composited over each candidate ground before it is measured.
      let worst = Infinity;
      let onGround = null;
      for (const g of grounds) {
        const r = ratio(over(fgRaw, g), g);
        if (r < worst) { worst = r; onGround = g; }
      }

      const size = parseFloat(cs.fontSize);
      const weight = parseInt(cs.fontWeight, 10) || 400;
      // WCAG 1.4.3 "large text": 18pt (24px), or 14pt (18.66px) bold.
      const large = size >= 24 || (size >= 18.66 && weight >= 700);

      // One row per (selector signature, rounded ratio): the same rule
      // painting forty list items is one finding, not forty.
      const sig = el.tagName.toLowerCase()
        + (el.className && typeof el.className === 'string'
           ? '.' + el.className.trim().split(/\s+/).join('.') : '');
      const key = sig + '|' + Math.round(worst * 100);
      if (seen.has(key)) continue;
      seen.add(key);

      results.push({
        sig,
        ratio: +worst.toFixed(2),
        grounds: grounds.length,
        onGround: onGround
          ? [Math.round(onGround.r), Math.round(onGround.g), Math.round(onGround.b)]
          : null,
        size: +size.toFixed(1),
        weight,
        large,
        threshold: large ? 3.0 : 4.5,
        sample: (el.textContent || '').trim().slice(0, 40),
      });
    }
    return { measured: results.length, results };
  });

  await page.close();
  await browser.close();
  console.log(JSON.stringify(out, null, 1));
})().catch((err) => { console.error(err); process.exit(1); });
