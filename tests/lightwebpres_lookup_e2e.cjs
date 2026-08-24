// Playwright driver for the lightwebpres-executable lookup in
// web/index.html (fetchLightwebpresSource: tries ./lightwebpres, then
// ../lightwebpres). Invoked by test_web.py — not a standalone entry
// point. Used for two scenarios:
//   - neither location has the executable: the page must explain the
//     real cause instead of a bare "Failed to fetch ../lightwebpres: 404"
//     (MissingSiblingExecutableGuard)
//   - only ./lightwebpres has it (the "flat" deployment layout): the
//     page must still reach Ready. (FlatDeploymentFindsCurrentDirExecutable)
//
// argv: <pageUrl> <expectedStatusSubstring>

const { chromium } = require('playwright');

async function main() {
  const [pageUrl, expectedSubstring] = process.argv.slice(2);
  if (!pageUrl || !expectedSubstring) {
    console.error('usage: lightwebpres_lookup_e2e.cjs <pageUrl> <expectedStatusSubstring>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();

  try {
    await page.goto(pageUrl);
    await page.waitForFunction(
      (expected) => document.getElementById('status').textContent.includes(expected),
      expectedSubstring,
      { timeout: 20000 },
    );

    console.log('OK');
    process.exitCode = 0;
  } catch (err) {
    console.error('E2E failure: ' + err);
    try {
      console.error('Final status: ' + (await page.textContent('#status')));
    } catch (_) {}
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main();
