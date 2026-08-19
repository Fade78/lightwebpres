/* The build stamp, measured against what is painted UNDER it.
 *
 * Instrument 2 (contrast_e2e.cjs) walks the DOM: it takes an element's
 * ground from its ancestors. That is right for text inside a card and
 * blind to an overlay, because an overlay's ground is not its parent —
 * it is whichever sibling the painter drew there first.
 *
 * The stamp is exactly that case, and the blindness is not academic. It
 * used to sit beside the cards, as a child of `body`, inheriting the
 * body's ink; on a light theme the cover paints its ground with the
 * page's INK, so the stamp painted #2E3440 onto #2E3440 — 1.00:1,
 * invisible — while an ancestor walk read the body's own background and
 * reported it legible. Moving the stamp into the first card fixed the
 * page and this file is what can tell the difference.
 *
 * `document.elementsFromPoint` is the painter's answer: hit testing skips
 * `pointer-events: none`, which the stamp carries, so the list it returns
 * IS the stack underneath. Gradient stops are read like the other
 * instrument reads them — a gradient's `backgroundColor` is transparent,
 * and text over one must clear the bar at every stop it crosses.
 *
 * Usage: node build_stamp_e2e.cjs <file:// URL of a built page>
 * Prints one JSON object; the Python side does the asserting.
 */
const { chromium } = require('playwright');

const URL = process.argv[2];

(async () => {
  const browser = await chromium.launch();
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
    // Every colour an element paints behind text: its background colour,
    // plus each stop of any gradient it carries.
    const paints = (el) => {
      const cs = getComputedStyle(el);
      const list = [];
      const bg = parse(cs.backgroundColor);
      if (bg && bg.a > 0) list.push(bg);
      for (const m of (cs.backgroundImage || '').matchAll(
             /rgba?\([^)]*\)/g)) {
        const stop = parse(m[0]);
        if (stop && stop.a > 0) list.push(stop);
      }
      return list;
    };

    const el = document.querySelector('.build-stamp');
    if (!el) return { found: false };

    const box = el.getBoundingClientRect();
    const cx = box.left + Math.min(8, box.width / 2);
    const cy = box.top + box.height / 2;
    const cs = getComputedStyle(el);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);

    // The stack UNDER the stamp. Hit testing skips pointer-events:none,
    // so the stamp is not in this list; the first entry is what the
    // painter put there.
    const stack = document.elementsFromPoint(cx, cy);
    const under = stack.filter((n) => n !== el && !el.contains(n));

    // Composite upward through the stack until an opaque colour closes
    // it. Each candidate stop is carried forward, because text over a
    // gradient has to clear the bar on all of them.
    let grounds = [{ r: 255, g: 255, b: 255, a: 1 }];   // the canvas
    for (let i = under.length - 1; i >= 0; i--) {
      for (const layer of paints(under[i])) {
        grounds = grounds.map((g) => over(layer, g));
        if (layer.a >= 1) grounds = [grounds[grounds.length - 1]];
      }
      const extra = paints(under[i]);
      if (extra.length > 1) {
        // A gradient: keep every stop as its own candidate ground.
        grounds = extra.map((stop) => over(stop, grounds[0]));
      }
    }

    // The ink. `opacity` composites the whole element over its ground, so
    // it is part of the ink, not a separate step.
    const alpha = parseFloat(cs.opacity);
    const declared = parse(cs.color) || { r: 0, g: 0, b: 0, a: 1 };
    const inks = grounds.map((g) =>
      over({ ...declared, a: declared.a * (isNaN(alpha) ? 1 : alpha) }, g));

    let worst = Infinity, worstGround = null, worstInk = null;
    for (let i = 0; i < grounds.length; i++) {
      const r = ratio(inks[i], grounds[i]);
      if (r < worst) { worst = r; worstGround = grounds[i]; worstInk = inks[i]; }
    }

    const round = (c) => [Math.round(c.r), Math.round(c.g), Math.round(c.b)];
    return {
      found: true,
      ratio: +worst.toFixed(2),
      ink: round(worstInk),
      ground: round(worstGround),
      grounds: grounds.length,
      under: under.length ? (under[0].className || under[0].tagName) : null,
      size: +size.toFixed(1),
      weight,
      large,
      threshold: large ? 3.0 : 4.5,
      sample: (el.textContent || '').trim().slice(0, 40),
    };
  });

  console.log(JSON.stringify(out));
  await browser.close();
})();
