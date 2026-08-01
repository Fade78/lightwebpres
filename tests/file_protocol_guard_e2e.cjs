// Playwright driver for the file:// early-exit guard in web/index.html and
// web/git-sync.html. Invoked by test_web.py — not a standalone entry point.
// Opens the given page via a file:// URL (exactly how a user who downloads
// and double-clicks the page would open it) and checks that init() bails
// out early with a clear, actionable status message instead of Pyodide
// failing with a raw, confusing browser error (blocked module/asset
// fetches under the file:// origin — see specifications.md §23.6).
//
// argv: <fileUrl> <expectedStatusSubstring>

const { chromium } = require('playwright');

async function main() {
  const [fileUrl, expectedSubstring] = process.argv.slice(2);
  if (!fileUrl || !expectedSubstring) {
    console.error('usage: file_protocol_guard_e2e.cjs <fileUrl> <expectedStatusSubstring>');
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
    await page.goto(fileUrl);
    await page.waitForFunction(
      () => document.getElementById('status').textContent.length > 0,
      { timeout: 10000 },
    );

    const status = await page.textContent('#status');
    if (!status.includes(expectedSubstring)) {
      throw new Error('Status did not contain expected guard message.\nGot: ' + status);
    }

    // The whole point of the early exit is to never reach Pyodide's own
    // failing fetches/imports, so there must be zero console errors here.
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
    } catch (_) {}
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
