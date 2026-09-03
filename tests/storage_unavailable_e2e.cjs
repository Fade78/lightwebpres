// Playwright driver for the storage-disabled bootstrap regression test.

const { chromium } = require('playwright');

async function main() {
  const pageBaseUrl = process.argv[2];
  if (!pageBaseUrl) {
    console.error('usage: storage_unavailable_e2e.cjs <page>');
    process.exitCode = 2;
    return;
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext();
  await context.addInitScript(() => {
    const blocked = () => {
      throw new DOMException('Access denied', 'SecurityError');
    };
    Object.defineProperty(window, 'sessionStorage', { configurable: true, get: blocked });
    Object.defineProperty(window, 'localStorage', { configurable: true, get: blocked });
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (error) => errors.push(String(error)));

  try {
    await page.goto(pageBaseUrl + '/web/index.html');
    await page.waitForFunction(
      () => document.getElementById('status').textContent.includes('Ready.'),
      { timeout: 60000 },
    );
    await page.click('#tabGit');
    await page.fill('#baseUrl', 'http://127.0.0.1:1');
    await page.check('#rememberToken');
    await page.click('#clearConnectionBtn');
    const result = await page.evaluate(() => ({
      status: document.getElementById('status').textContent,
      zipDisabled: document.getElementById('zipBuildBtn').disabled,
      pullDisabled: document.getElementById('pullBtn').disabled,
    }));
    console.log(JSON.stringify({ ...result, errors }));
  } catch (error) {
    console.error('E2E failure: ' + error);
    console.error('Page errors: ' + errors.join('\n'));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
