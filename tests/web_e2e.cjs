// Playwright driver for the web/ E2E test. Invoked by test_web.py — not a
// standalone entry point. Loads web/index.html in headless Chromium,
// uploads a series zip, clicks Build, and saves the resulting download.
//
// argv: <baseUrl> <zipPath> <lang> <downloadOutPath>

const { chromium } = require('playwright');

async function main() {
  const [baseUrl, zipPath, lang, downloadOutPath] = process.argv.slice(2);
  if (!baseUrl || !zipPath || !lang || !downloadOutPath) {
    console.error('usage: web_e2e.cjs <baseUrl> <zipPath> <lang> <downloadOutPath>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(String(err)));

  try {
    await page.goto(baseUrl + '/web/index.html');

    // Pyodide + lightwebpres + app.py load; give it a generous timeout.
    await page.waitForFunction(
      () => document.getElementById('status').textContent.includes('Ready.'),
      { timeout: 60000 },
    );

    await page.setInputFiles('#zipInput', zipPath);
    await page.selectOption('#langSelect', lang);

    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });
    await page.click('#buildBtn');
    const download = await downloadPromise;
    await download.saveAs(downloadOutPath);

    const status = await page.textContent('#status');
    if (!status.includes('Build complete')) {
      throw new Error('Unexpected status after build: ' + status);
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
    try {
      console.error('Final status: ' + (await page.textContent('#status')));
      console.error('Final log: ' + (await page.textContent('#log')));
    } catch (_) {}
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
