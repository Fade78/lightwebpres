// Playwright driver for the file:// early-exit guard in web/index.html and
// web/git-sync.html. Invoked by test_web.py — not a standalone entry point.
// Opens the given page via a file:// URL (exactly how a user who downloads
// and double-clicks the page would open it) and checks that init() bails
// out early with a clear, actionable, copyable command instead of Pyodide
// failing with a raw, confusing browser error (blocked module/asset
// fetches under the file:// origin — see specifications.md §23.6).
// Also clicks the guard's Copy button and reads the clipboard back, to
// verify the command is actually copyable, not just displayed as text.
//
// argv: <fileUrl> <expectedCommand>  (exact command text, not a substring)

const { chromium } = require('playwright');

async function main() {
  const [fileUrl, expectedSubstring] = process.argv.slice(2);
  if (!fileUrl || !expectedSubstring) {
    console.error('usage: file_protocol_guard_e2e.cjs <fileUrl> <expectedStatusSubstring>');
    process.exit(2);
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const context = await browser.newContext();
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const page = await context.newPage();

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

    // The command must be in its own <code> element (exactly what the
    // Copy button copies) and match the full expected command exactly,
    // not just appear as a substring somewhere in the surrounding prose.
    const codeText = await page.textContent('.guard-cmd-row code');
    if (codeText !== expectedSubstring) {
      throw new Error('<code> block did not match expected command exactly.\nGot: ' + codeText);
    }

    // The whole point of a copy button is that it actually copies: click
    // it and read the clipboard back.
    await page.click('.guard-cmd-row button');
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    if (clipboardText !== expectedSubstring) {
      throw new Error('Clipboard did not contain the expected command after clicking Copy.\nGot: ' + clipboardText);
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
