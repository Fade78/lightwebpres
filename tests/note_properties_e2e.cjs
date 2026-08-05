// Playwright driver: every note axis must LAND, in all three contexts.
// Invoked by test_web.py — not a standalone entry point.
//
// A theme axis that is emitted but loses is worse than one that does not
// exist: settings.conf lists it, audit counts it, and it does nothing.
// `note.size` shipped that way — `article.size` drives `.full-article ol`
// at (0,1,1), which beat `.note-body` at (0,1,0), so the axis was inert
// on the notes at the foot of the long-form article, where the default
// placement puts them. Declared 14px, computed 15px.
//
// This cannot be settled on paper. Whether one selector beats another
// depends on the markup: `.fact-content h2` outranks `.note-back` by
// specificity and can never select it. So the check is the only one that
// is actually sound — resolve the declared value, resolve the computed
// value, compare.
//
// argv: <cardUrl> <articleUrl> <notesUrl>

const { chromium } = require('playwright');

// axis -> [selector, computed-style property, kind]
const LANDS = {
  'note.fg':               ['.note-body li',     'color',           'color'],
  'note.marker.fg':        ['.note-num',         'color',           'color'],
  'note.back.fg':          ['.note-back',        'color',           'color'],
  'note.local.rule-fg':    ['.notes-local',      'borderTopColor',  'color'],
  'note.local.rule-width': ['.notes-local',      'borderTopWidth',  'length'],
  'note.local.size':       ['.notes-local .note-body', 'fontSize',  'length'],
  'note.page.bg':          ['.notes-section',    'backgroundColor', 'color'],
  'note.page.rule-fg':     ['.notes-section',    'borderTopColor',  'color'],
  'note.page.rule-width':  ['.notes-section',    'borderTopWidth',  'length'],
  'note.page.title.fg':    ['.notes-section h2', 'color',           'color'],
  'note.page.title.size':  ['.notes-section h2', 'fontSize',        'length'],
};
// note.size governs the notes SECTION; in a card or an article the more
// specific note.local.size is meant to win, which is the whole point.
const SECTION_ONLY = { 'note.size': ['.notes-section .note-body', 'fontSize', 'length'] };

function fail(m) { console.error('FAIL: ' + m); process.exitCode = 1; }

function argbToRgb(v) {
  const h = v.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  const a = h.length >= 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1;
  return a >= 0.999 ? `rgb(${r}, ${g}, ${b})` : { r, g, b, a };
}

async function checkPage(page, url, table, label) {
  await page.goto(url);
  for (const [axis, [sel, prop, kind]] of Object.entries(table)) {
    const got = await page.evaluate(([s, p, v]) => {
      const e = document.querySelector(s);
      if (!e) return null;
      return [getComputedStyle(e)[p],
              getComputedStyle(document.documentElement).getPropertyValue(v).trim()];
    }, [sel, prop, '--' + axis.replace(/\./g, '-')]);
    if (got === null) continue;          // that surface is not on this page
    const [computed, declared] = got;
    if (!declared) { fail(`${label}: ${axis} declares nothing at :root`); continue; }
    if (kind === 'length') {
      if (computed !== declared) {
        fail(`${label}: ${axis} declared ${declared} but computed ${computed} — the axis is inert`);
      }
    } else {
      const want = argbToRgb(declared);
      if (typeof want === 'string') {
        if (computed !== want) {
          fail(`${label}: ${axis} declared ${declared} (${want}) but computed ${computed}`);
        }
      } else {
        const m = computed.match(/rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)/);
        if (!m) { fail(`${label}: ${axis} computed unparseable ${computed}`); continue; }
        const near = Math.abs(+m[1] - want.r) <= 1 && Math.abs(+m[2] - want.g) <= 1
          && Math.abs(+m[3] - want.b) <= 1 && Math.abs((+m[4] || 1) - want.a) <= 0.01;
        if (!near) fail(`${label}: ${axis} declared ${declared} but computed ${computed}`);
      }
    }
  }
}

async function main() {
  const [cardUrl, articleUrl, notesUrl] = process.argv.slice(2);
  if (!notesUrl) { console.error('usage: note_properties_e2e.cjs <card> <article> <notes>'); process.exit(2); }
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 } });

  await checkPage(page, cardUrl, LANDS, 'card');
  await checkPage(page, articleUrl, LANDS, 'article');
  await checkPage(page, notesUrl, { ...LANDS, ...SECTION_ONLY }, 'notes section');

  // The block must also be free of the article list rule it used to
  // inherit: a 24px indent and a bottom margin nobody asked for.
  await page.goto(articleUrl);
  const box = await page.evaluate(() => {
    const s = getComputedStyle(document.querySelector('.note-body'));
    return { pad: s.paddingLeft, mb: s.marginBottom, list: s.listStyleType };
  });
  if (box.pad !== '0px') fail(`the article's note list is indented ${box.pad}`);
  if (box.mb !== '0px') fail(`the article's note list carries a ${box.mb} bottom margin`);
  if (box.list !== 'none') fail(`the article's note list shows its own markers (${box.list})`);

  await browser.close();
  if (!process.exitCode) console.log('OK: every note axis lands in all three contexts');
}

main().catch((e) => { console.error(e); process.exit(1); });
