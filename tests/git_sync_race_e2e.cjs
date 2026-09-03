// Playwright driver for the Pull/Build/Push concurrency regression test.
// The mock GitLab endpoint holds the tree response while this script tries a
// second Pull. A safe UI must keep the whole Git operation locked.

const { chromium } = require('playwright');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getState(gitlabBaseUrl) {
  const response = await fetch(gitlabBaseUrl + '/control/state');
  if (!response.ok) throw new Error('control/state returned ' + response.status);
  return response.json();
}

async function waitForState(gitlabBaseUrl, predicate, timeout = 30000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const state = await getState(gitlabBaseUrl);
    if (predicate(state)) return state;
    await sleep(50);
  }
  throw new Error('timed out waiting for mock GitLab state');
}

async function main() {
  const [pageBaseUrl, gitlabBaseUrl, projectId, branch, token] = process.argv.slice(2);
  if (!pageBaseUrl || !gitlabBaseUrl || !projectId || !branch || !token) {
    console.error('usage: git_sync_race_e2e.cjs <page> <gitlab> <project> <branch> <token>');
    process.exitCode = 2;
    return;
  }

  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  let treeHeld = false;

  async function waitForStatus(pattern, timeout = 30000) {
    await page.waitForFunction(
      (pat) => document.getElementById('status').textContent.includes(pat),
      pattern, { timeout },
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
    await waitForStatus('Ready to build');
    await page.click('#gitBuildBtn');
    await waitForStatus('Ready to push');

    await page.click('#pushBtn');
    await waitForState(gitlabBaseUrl, (state) => state.treeStarted);
    treeHeld = true;

    const pullDisabled = await page.$eval('#pullBtn', (button) => button.disabled);
    if (!pullDisabled) {
      await page.evaluate(() => {
        document.getElementById('pullBtn').dispatchEvent(
          new MouseEvent('click', { bubbles: true, cancelable: true, view: window }),
        );
      });
      await waitForState(gitlabBaseUrl, (state) => state.archiveCount >= 2, 10000);
    }

    await fetch(gitlabBaseUrl + '/control/release-tree');
    treeHeld = false;
    await waitForStatus('Pushed');
    const state = await getState(gitlabBaseUrl);
    const actions = state.commits.flatMap((commit) => commit.actions);
    const source = actions.find((action) => action.file_path === 'sources/a.md');
    const sourceContent = source
      ? Buffer.from(source.content, 'base64').toString('utf8')
      : '';
    console.log(JSON.stringify({
      pullDisabled,
      archiveCount: state.archiveCount,
      commitCount: state.commits.length,
      actionPaths: actions.map((action) => action.file_path),
      sourceContent,
    }));
  } catch (err) {
    console.error('E2E failure: ' + err);
    process.exitCode = 1;
  } finally {
    if (treeHeld) {
      await fetch(gitlabBaseUrl + '/control/release-tree').catch(() => {});
    }
    await browser.close();
  }
}

main();
