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
    if (msg.type() === 'error') consoleErrors.push({ text: msg.text(), url: msg.location().url });
  });
  page.on('pageerror', (err) => consoleErrors.push({ text: String(err), url: '' }));

  // fetchLightwebpresSource() tries ./lightwebpres before ../lightwebpres
  // (§23.8): a 404 on ./lightwebpres is expected, not a bug, whenever the
  // repo's own layout (lightwebpres one level above web/) is what's
  // actually being served — exactly this test's setup. The browser still
  // logs it to the console regardless of the page's own try/catch, so
  // filter that one specific, expected entry out before judging the run.
  const isExpectedLightwebpresProbe404 = (e) => e.url.endsWith('/lightwebpres') && /404/.test(e.text);

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

    const unexpectedErrors = consoleErrors.filter((e) => !isExpectedLightwebpresProbe404(e));
    if (unexpectedErrors.length) {
      console.error('Browser console errors:\n' + unexpectedErrors.map((e) => e.text).join('\n'));
      process.exit(1);
    }

    console.log('OK');
    process.exit(0);
  } catch (err) {
    console.error('E2E failure: ' + err);
    const unexpectedErrors = consoleErrors.filter((e) => !isExpectedLightwebpresProbe404(e));
    if (unexpectedErrors.length) {
      console.error('Browser console errors:\n' + unexpectedErrors.map((e) => e.text).join('\n'));
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
