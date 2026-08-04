#!/usr/bin/env python3
"""Measure the rendered typographic measure across a portrait/landscape matrix.

Renders a built series in Chromium at fifteen real viewports and reports,
per text-bearing component, the characters per line *actually rendered* —
not the CSS that was meant to produce them. Also reports vertical overflow
per card, which is the axis every width-keyed breakpoint is blind to.

Two configurations are measured so the numbers can be compared:
  baseline    the sheet as built
  candidate   the sheet plus the CANDIDATE overrides below

Demo copy is far too short to fill a line box, so each component is
saturated with filler prose before measuring: otherwise the number
returned is the length of the text, not the capacity of the container.
Overflow is read *before* saturation, on the real copy.

Requires playwright (`pip install playwright`) and a Chromium binary;
pass its path with --chromium if it is not at /opt/pw-browsers/chromium.

    python3 tools/viewport_measure.py path/to/series/public
"""
import argparse
import json
import pathlib
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - developer tool
    sys.exit('playwright is required: pip install playwright')

# (label, width, height). Each phone and tablet appears in both rotations:
# the pair is the point of the exercise.
VIEWPORTS = [
    ('iPhone SE  portrait',   375,  667),
    ('iPhone SE  landscape',  667,  375),
    ('iPhone 15  portrait',   393,  852),
    ('iPhone 15  landscape',  852,  393),
    ('Pixel 8    portrait',   412,  915),
    ('Pixel 8    landscape',  915,  412),
    ('iPad mini  portrait',   744, 1133),
    ('iPad mini  landscape', 1133,  744),
    ('iPad Pro11 portrait',   834, 1194),
    ('iPad Pro11 landscape', 1194,  834),
    ('Projector 4:3',        1024,  768),
    ('Laptop 16:10',         1440,  900),
    ('Desktop 1080p',        1920, 1080),
    ('Ultrawide',            2560, 1080),
    ('Monitor portrait',     1080, 1920),
]

TARGETS = [
    ('h1',                   'cover title'),
    ('h2',                   'slide title'),
    ('.summary',             'cover summary'),
    ('.fact-content',        'fact body'),
    ('.comparison-table td', 'table cell'),
    ('.full-article p',      'article paragraph'),
]

# The configuration under test. Kept here rather than in the sheet so the
# measurement can be re-run against a future sheet to check it still holds.
CANDIDATE = """
:root { --content-max: 50ch !important; }
@media (max-width: 600px) { :root { --content-max: 50ch !important; } }

h1 { font-size: clamp(28px, 4.5vmin, 52px) !important; }
h2 { font-size: clamp(24px, 3.5vmin, 40px) !important; }
.summary { font-size: clamp(16px, 2vmin, 22px) !important; }
.fact-content { font-size: clamp(15px, 1.6vmin, 18px) !important; }
.comparison-table { font-size: clamp(13px, 1.4vmin, 16px) !important; }
.highlight-figure { font-size: clamp(2.1rem, 8vmin, 3.4rem) !important; }

.highlight-caption { max-width: var(--content-max) !important; }
.full-article p, .full-article ul, .full-article ol, .full-article table {
  max-width: var(--content-max) !important; }

@media (max-height: 520px) {
  .slide { padding: 24px 6vw !important; }
  .fact-box { padding: 14px 18px !important; }
  .highlight { margin: 8px 0 10px !important; }
}
"""

OVERFLOW_JS = r"""
() => {
  const slides = Array.from(document.querySelectorAll('.slide'));
  return {
    over: slides.filter(s => s.scrollHeight > window.innerHeight + 1).length,
    total: slides.length,
    worst: Math.max(0, ...slides.map(s => s.scrollHeight - window.innerHeight)),
    hoverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  };
}
"""

MEASURE_JS = r"""
(targets) => {
  const FILLER = ('The measure of a column is the number of characters it '
    + 'carries on one line, and it is the single typographic decision that '
    + 'most affects whether a reader finishes the paragraph or abandons it '
    + 'halfway through the third line of an overlong sentence. ').repeat(6);
  for (const [sel] of targets) {
    for (const el of document.querySelectorAll(sel)) {
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n, first = true;
      while ((n = w.nextNode())) {
        if (n.textContent.trim().length < 2) continue;
        n.textContent = first ? FILLER : '';
        first = false;
      }
    }
  }
  const out = [];
  for (const [sel, label] of targets) {
    let chars = 0, lines = 0, fontSize = null, boxWidth = null;
    for (const el of document.querySelectorAll(sel)) {
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        const text = n.textContent.replace(/\s+/g, ' ').trim();
        if (text.length < 2) continue;
        const r = document.createRange();
        r.selectNodeContents(n);
        // One client rect per line box: the browser's own line breaking,
        // which is the only authority on how many characters actually fit.
        const rects = Array.from(r.getClientRects()).filter(x => x.width > 1);
        if (!rects.length) continue;
        chars += text.length;
        lines += rects.length;
      }
      if (fontSize === null) {
        fontSize = parseFloat(getComputedStyle(el).fontSize);
        boxWidth = el.getBoundingClientRect().width;
      }
    }
    if (lines) out.push({label, cpl: chars / lines,
                         fontSize: round(fontSize), boxWidth: round(boxWidth)});
  }
  function round(x) { return x === null ? null : Math.round(x); }
  return out;
}
"""


def run(public, chromium, override=None):
    pages = sorted(p for p in public.glob('*.html') if p.name != 'index.html')
    if not pages:
        sys.exit(f'no built pages in {public}')
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium)
        for label, w, h in VIEWPORTS:
            page = browser.new_page(viewport={'width': w, 'height': h})
            acc = {'targets': {}, 'over': 0, 'total': 0, 'worst': 0,
                   'hoverflow': False}
            for f in pages[:2]:
                page.goto(f.as_uri())
                if override:
                    page.add_style_tag(content=override)
                page.wait_for_timeout(120)
                ovf = page.evaluate(OVERFLOW_JS)
                for t in page.evaluate(MEASURE_JS, TARGETS):
                    acc['targets'].setdefault(t['label'], t)
                acc['over'] += ovf['over']
                acc['total'] += ovf['total']
                acc['worst'] = max(acc['worst'], ovf['worst'])
                acc['hoverflow'] = acc['hoverflow'] or ovf['hoverflow']
            results[label] = acc
            page.close()
        browser.close()
    return results


def report(before, after):
    keys = ['cover summary', 'fact body', 'article paragraph', 'cover title']
    print('## Characters per line (before -> after)\n')
    print('| viewport | ' + ' | '.join(keys) + ' |')
    print('|---' * (len(keys) + 1) + '|')
    for vp in before:
        cells = []
        for k in keys:
            b, a = before[vp]['targets'].get(k), after[vp]['targets'].get(k)
            cells.append(f'{b["cpl"]:.0f} → **{a["cpl"]:.0f}**' if b and a else '—')
        print(f'| {vp.strip()} | ' + ' | '.join(cells) + ' |')
    print('\n## Cards taller than the viewport (before -> after)\n')
    print('| viewport | cards | worst overshoot |')
    print('|---|---|---|')
    for vp in before:
        b, a = before[vp], after[vp]
        print(f'| {vp.strip()} | {b["over"]}/{b["total"]} → **{a["over"]}/{a["total"]}** '
              f'| {b["worst"]:.0f}px → **{a["worst"]:.0f}px** |')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('public', type=pathlib.Path, help='built public/ directory')
    ap.add_argument('--chromium', default='/opt/pw-browsers/chromium')
    ap.add_argument('--json', type=pathlib.Path, help='also dump raw measurements')
    args = ap.parse_args()

    before = run(args.public, args.chromium)
    after = run(args.public, args.chromium, CANDIDATE)
    report(before, after)
    if args.json:
        args.json.write_text(json.dumps({'before': before, 'after': after}, indent=1))


if __name__ == '__main__':
    main()
