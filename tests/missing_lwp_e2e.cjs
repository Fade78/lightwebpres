// Playwright driver for the "sibling lightwebpres executable missing"
// diagnostic in web/index.html and web/git-sync.html. Invoked by
// test_web.py — not a standalone entry point. Points at a page served
// with ONLY web/ as the HTTP root (no ../lightwebpres reachable), which
// reproduces the real-world mistake of deploying just web/'s contents
// without the rest of the repository, and checks the page explains it
// clearly instead of showing a bare "Failed to fetch ../lightwebpres: 404".
//
// argv: <pageUrl> <expectedStatusSubstring>

const { chromium } = require('playwright');

async function main() {
  const [pageUrl, expectedSubstring] = process.argv.slice(2);
  if (!pageUrl || !expectedSubstring) {
    console.error('usage: missing_lwp_e2e.cjs <pageUrl> <expectedStatusSubstring>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();

  try {
    await page.goto(pageUrl);
    await page.waitForFunction(
      () => document.getElementById('status').textContent.includes('Failed'),
      { timeout: 15000 },
    );

    const status = await page.textContent('#status');
    if (!status.includes(expectedSubstring)) {
      throw new Error('Status did not contain expected explanation.\nGot: ' + status);
    }

    console.log('OK');
    process.exit(0);
  } catch (err) {
    console.error('E2E failure: ' + err);
    try {
      console.error('Final status: ' + (await page.textContent('#status')));
    } catch (_) {}
    process.exit(1);
  } finally {
    await browser.close();
  }
}

main();
