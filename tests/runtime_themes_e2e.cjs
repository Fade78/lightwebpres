// Browser probe for the opt-in runtime theme payload, the C picker and the
// global M menu. Invoked by tests/test_runtime_themes.py.

const { chromium } = require('playwright');

function fail(message) {
  console.error('E2E failure: ' + message);
  process.exitCode = 1;
}

async function main() {
  const [base] = process.argv.slice(2);
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));
  await page.goto(base + '/index.html', { waitUntil: 'load' });

  const initial = await page.evaluate(() => ({
    payload: !!document.getElementById('lwp-theme-data'),
    primary: JSON.parse(document.getElementById('lwp-theme-data').textContent).primary,
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
  }));
  if (!initial.payload || initial.primary !== 'print-oldpress') {
    fail('the index did not load the effective primary theme: ' + JSON.stringify(initial));
  }

  await page.keyboard.press('c');
  const picker = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    focused: document.activeElement && document.activeElement.id,
    options: document.querySelectorAll('.theme-option').length,
  }));
  if (!picker.open || picker.focused !== 'themeFilter' || picker.options !== 2) {
    fail('C did not open the theme picker correctly: ' + JSON.stringify(picker));
  }

  // The filter is focused first; two Tab presses reach the alternate theme.
  await page.keyboard.press('Tab');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  const switched = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    font: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
    stored: sessionStorage.length,
  }));
  if (switched.open || switched.stored !== 1
      || switched.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the alternate theme did not apply while keeping the pinned ink: '
      + JSON.stringify(switched));
  }
  if (switched.font.indexOf('Charter') === -1) {
    fail('the alternate theme did not change the runtime font: ' + JSON.stringify(switched));
  }

  const articleHref = await page.locator('a.article-card').first().getAttribute('href');
  await page.goto(new URL(articleHref, base + '/index.html').href, { waitUntil: 'load' });
  const carried = await page.evaluate(() => ({
    font: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
  }));
  if (carried.font.indexOf('Charter') === -1
      || carried.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the theme choice did not persist to the article page: ' + JSON.stringify(carried));
  }

  await page.keyboard.press('c');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  const restored = await page.evaluate(() => ({
    open: document.getElementById('themeMenu').classList.contains('open'),
    inline: document.documentElement.style.getPropertyValue('--font-text'),
    ink: getComputedStyle(document.documentElement).getPropertyValue('--color-ink').trim(),
    stored: sessionStorage.length,
  }));
  if (restored.open || restored.inline || restored.stored !== 0
      || restored.ink.toLowerCase().indexOf('#123456') !== 0) {
    fail('the primary theme did not restore cleanly: ' + JSON.stringify(restored));
  }

  await page.keyboard.press('m');
  const menu = await page.evaluate(() => ({
    open: document.getElementById('presenterMenu').classList.contains('open'),
    visibleActions: Array.prototype.filter.call(
      document.querySelectorAll('.presenter-menu-action'),
      (button) => getComputedStyle(button).display !== 'none'
    ).length,
  }));
  if (!menu.open || menu.visibleActions !== 11) {
    fail('M did not expose the complete presenter menu: ' + JSON.stringify(menu));
  }
  await page.keyboard.press('Escape');

  await browser.close();
  if (errors.length) fail('page errors: ' + errors.join(' | '));
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
