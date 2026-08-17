// Playwright driver for the themes-gallery facet filters (§11.7/§9.5.3).
// Invoked by test_web.py — not a standalone entry point.
//
// This exists because the filter can be entirely broken while every
// cheaper check passes. The script hides a card by setting its `hidden`
// property; that relies on the browser default [hidden] { display: none },
// which a class rule with a `display` of its own silently outranks. When
// that happened, the counter read "14 palettes sur 33" and the facet
// buttons enabled and disabled correctly — while all 33 cards stayed on
// screen. Nothing short of measuring real layout catches it, so this
// driver counts cards with a non-null offsetParent, never the attribute
// and never the counter text.
//
// argv: <fileUrl>

const { chromium } = require('playwright');
const { collectConsoleErrors } = require('./console_errors.cjs');

async function main() {
  const [fileUrl] = process.argv.slice(2);
  if (!fileUrl) {
    console.error('usage: themes_gallery_facets_e2e.cjs <fileUrl>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();

  const consoleErrors = [];
  collectConsoleErrors(page, consoleErrors);
  page.on('pageerror', (err) => consoleErrors.push(String(err)));

  // Actually laid out, not merely un-flagged.
  const visible = () => page.$$eval('.theme-row',
    (els) => els.filter((e) => e.offsetParent !== null).length);

  try {
    await page.goto(fileUrl);

    // The bar ships hidden and is revealed by the script, so its being
    // visible is also the proof that the script ran at all.
    if (await page.isHidden('#facets')) {
      throw new Error('The facet bar is still hidden: the inline script did not run.');
    }

    const total = await visible();
    if (total < 2) throw new Error('Expected a gallery of several cards, saw ' + total);

    await page.click('[data-facet="polarity"][data-value="dark"]');
    const dark = await visible();
    if (dark === 0 || dark >= total) {
      throw new Error('polarity=dark should hide some but not all cards; ' +
                      dark + ' of ' + total + ' still visible');
    }

    // The counter has to agree with what is actually on screen — it was
    // right while the page was wrong, which is how the bug survived.
    const countText = await page.textContent('#facetCount');
    if (!countText.includes(String(dark))) {
      throw new Error('Counter says "' + countText + '" but ' + dark + ' cards are visible');
    }

    // Every visible card really carries the facet asked for.
    const wrong = await page.$$eval('.theme-row',
      (els) => els.filter((e) => e.offsetParent !== null)
                  .filter((e) => e.getAttribute('data-polarity') !== 'dark')
                  .map((e) => e.getAttribute('data-name')));
    if (wrong.length) {
      throw new Error('Cards visible that are not dark: ' + wrong.join(', '));
    }

    // A second facet narrows further rather than replacing the first.
    await page.click('[data-facet="family"][data-value="light"]');
    const both = await visible();
    if (both === 0 || both > dark) {
      throw new Error('Adding family=light should narrow ' + dark + ', got ' + both);
    }

    // A facet leading nowhere is disabled, so no click can empty the page.
    const deadEnabled = await page.$$eval('.facet:not([disabled])',
      (els, ctx) => els.filter((b) => {
        const v = b.getAttribute('data-value');
        if (!v) return false;
        const trial = { polarity: 'dark', family: 'light', hue: '' };
        trial[b.getAttribute('data-facet')] = v;
        return !ctx.some((c) => Object.keys(trial).every(
          (k) => !trial[k] || c[k] === trial[k]));
      }).map((b) => b.getAttribute('data-facet') + '=' + b.getAttribute('data-value')),
      await page.$$eval('.theme-row', (els) => els.map((e) => ({
        polarity: e.getAttribute('data-polarity'),
        family: e.getAttribute('data-family'),
        hue: e.getAttribute('data-hue'),
      }))));
    if (deadEnabled.length) {
      throw new Error('Facets that lead to an empty page are still clickable: ' +
                      deadEnabled.join(', '));
    }

    // No swatch label is clipped. The v0.15.0 role names are longer than
    // the colour names they replaced, and the first layout truncated
    // '--ink-muted' to '--ink-mu…' — an elided variable name is worse
    // than none, because it cannot be typed. Only real layout catches
    // this; the HTML contains the full string either way.
    // Every text line of a swatch, not just the ones that happen to be
    // there today: a selector that misses the truncated element passes
    // as happily as one that finds nothing wrong.
    const clipped = await page.$$eval('.swatch-text > *',
      (els) => els.filter((e) => e.scrollWidth > e.clientWidth + 1)
                  .map((e) => e.textContent));
    if (clipped.length) {
      throw new Error('Swatch labels truncated: ' +
                      [...new Set(clipped)].join(', '));
    }

    // "All" restores the full gallery: no card is lost along the way.
    await page.click('[data-facet="polarity"][data-value=""]');
    await page.click('[data-facet="family"][data-value=""]');
    const restored = await visible();
    if (restored !== total) {
      throw new Error('Resetting the facets should show all ' + total +
                      ' cards again, got ' + restored);
    }

    if (consoleErrors.length) {
      console.error('Browser console errors:\n' + consoleErrors.join('\n'));
      process.exit(1);
    }

    console.log('OK');
    process.exit(0);
  } catch (err) {
    console.error('E2E failure: ' + err);
    if (consoleErrors.length) {
      console.error('Browser console errors:\n' + consoleErrors.join('\n'));
    }
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
