// Playwright driver for the "Sync with GitLab" tab of web/index.html.
// Invoked by test_git_sync.py — not a standalone entry point. Loads the
// page in headless Chromium, switches to the GitLab tab, fills in
// connection fields pointing at a local mock GitLab API, and drives
// Pull -> Build -> Push. The mock server (run by the Python test, on a
// different port so the browser genuinely crosses origins) records what
// it received; this script only reports whether the UI flow itself
// succeeded.
//
// argv: <pageBaseUrl> <gitlabBaseUrl> <projectId> <branch> <token> [deleteFileBeforePush]
//
// The optional 6th argument names a file (relative to the series dir, e.g.
// "articles/old.md") to delete from the local working directory after
// Build and before Push, so the test can verify push() never turns that
// into a "delete" action against a file that still exists remotely
// (spec §24.4 — push only ever creates/updates, never deletes).

const { chromium } = require('playwright');

async function main() {
  const [pageBaseUrl, gitlabBaseUrl, projectId, branch, token, deleteFileBeforePush] = process.argv.slice(2);
  if (!pageBaseUrl || !gitlabBaseUrl || !projectId || !branch || !token) {
    console.error('usage: git_sync_e2e.cjs <pageBaseUrl> <gitlabBaseUrl> <projectId> <branch> <token> [deleteFileBeforePush]');
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

  async function waitForStatus(pattern, timeout) {
    await page.waitForFunction(
      (pat) => document.getElementById('status').textContent.includes(pat),
      pattern, { timeout: timeout || 30000 },
    );
  }

  try {
    await page.goto(pageBaseUrl + '/web/index.html');
    await waitForStatus('Ready.', 60000);
    await page.click('#tabGit');

    await page.fill('#baseUrl', gitlabBaseUrl);
    await page.fill('#projectId', projectId);
    await page.fill('#branch', branch);
    await page.fill('#token', token);

    await page.click('#pullBtn');
    await waitForStatus('Ready to build', 30000);

    await page.click('#gitBuildBtn');
    await waitForStatus('Ready to push', 30000);

    if (deleteFileBeforePush) {
      await page.evaluate((relPath) => {
        const fullPath = window.__lwp_series_dir + '/' + relPath;
        window.__lwp_pyodide.FS.unlink(fullPath);
      }, deleteFileBeforePush);
    }

    await page.click('#pushBtn');
    await waitForStatus('Pushed', 30000);

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
