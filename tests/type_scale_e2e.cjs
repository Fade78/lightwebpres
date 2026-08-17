/* Renders one built page at two viewport widths and reports, for every
 * element that carries its own text, whether its computed font-size
 * changed between them.
 *
 * The instrument this project kept not having. Three separate audits found
 * the same defect wearing three costumes -- a component disagreeing with
 * its neighbours, a size with no scale, a length pinned against a glyph --
 * and each time the measurement that would have caught it was a column
 * nobody had thought to add. This is that column: how many rendered sizes
 * do not move when the screen doubles.
 *
 * Walks the DOM rather than a list of selectors, deliberately. A list only
 * ever covers the components someone remembered; the walk covers the ones
 * added later, which is where the last two instances came from.
 *
 * Usage: node type_scale_e2e.cjs <file:// URL of a built page>
 * Prints JSON: { "tag.class1.class2": {"a": <px at 1920>, "b": <px at 3840>} }
 */
const { chromium } = require('playwright');

const URL = process.argv[2];
const WIDE = { width: 1920, height: 1080 };
const WIDER = { width: 3840, height: 2160 };

function collect() {
  // A signature must be stable between the two runs and must not
  // distinguish two instances of the same component, or the diff below
  // compares things that are not the same thing.
  const out = {};
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('style, script, head')) continue;
    // Only elements with their OWN text: a wrapper inherits its size from
    // whatever it wraps, so reporting it would double-count and, worse,
    // report a wrapper as "flat" when the text inside it scales fine.
    const ownText = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim())
      .join('');
    if (!ownText) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const own = (el) => {
      const cls = Array.from(el.classList).sort().join('.');
      return cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase();
    };
    // Scope by the nearest CLASSED ancestor, or a bare tag collides across
    // components: a slide's `h2` and the long-form article's `h2` are both
    // "h2", the slide's comes first in the DOM, and first-instance-wins
    // then hides the second one entirely. That is not hypothetical — it
    // masked the exact inversion this file was written to catch, and the
    // first run of this instrument passed against a reintroduced defect.
    let scope = el.parentElement;
    while (scope && scope !== document.body && !scope.classList.length) {
      scope = scope.parentElement;
    }
    const key = (scope && scope !== document.body)
      ? `${own(scope)} ${own(el)}` : own(el);
    // First instance wins; siblings of one component share a signature.
    if (!(key in out)) out[key] = Math.round(parseFloat(cs.fontSize) * 100) / 100;
  }
  return out;
}

(async () => {
  const browser = await chromium.launch();
  const sizes = {};
  for (const [slot, viewport] of [['a', WIDE], ['b', WIDER]]) {
    const page = await browser.newPage({ viewport });
    await page.goto(URL);
    const got = await page.evaluate(collect);
    for (const [k, v] of Object.entries(got)) {
      (sizes[k] = sizes[k] || {})[slot] = v;
    }
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(sizes, null, 1));
})().catch(err => { console.error(err); process.exit(1); });
