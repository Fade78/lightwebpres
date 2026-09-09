// Real Pyodide and builds; every non-local request is intercepted, never sent.
// argv: <pageBaseUrl> <projectAArchiveBase64> <projectBArchiveBase64>
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

async function main() {
  const [pageBaseUrl, archiveA, archiveB] = process.argv.slice(2);
  const baseUrl = 'https://gitlab-a.invalid/gitlab';
  const otherBaseUrl = 'https://gitlab-b.invalid/gitlab';
  const token = 'test-private-token-never-in-status-or-keys';
  const executablePath = process.env.PW_CHROMIUM_PATH || undefined;
  const browser = await chromium.launch(executablePath ? { executablePath } : {});
  const page = await browser.newPage();
  const requests = [];
  const commits = [];
  const errors = [];
  let heldResponse = null;
  page.on('pageerror', (error) => errors.push(String(error)));

  function holdNext(endpoint) {
    let release, started;
    const gate = {
      endpoint,
      waiting: new Promise((resolve) => { started = resolve; }),
      resume: new Promise((resolve) => { release = resolve; }),
      started: () => started(),
      release: () => release(),
    };
    heldResponse = gate;
    return gate;
  }

  async function idle() {
    await page.waitForFunction(() => gitOperation === null);
  }

  async function status(text) {
    await page.waitForFunction((text) =>
      document.getElementById('status').textContent.includes(text), text);
    await idle();
  }

  async function pullBuild() {
    await page.click('#pullBtn');
    await status('Ready to build');
    await page.click('#gitBuildBtn');
    await status('Ready to push');
  }

  async function assertBlocked() {
    assert.equal(await page.isDisabled('#gitBuildBtn'), true);
    assert.equal(await page.isDisabled('#pushBtn'), true);
    const message = await page.textContent('#status');
    assert.match(message, /Pull again before Build or Push/);
    assert.match(message, /Local files remain/);
    assert.equal(message.includes(token), false);
    const before = requests.length;
    // Disabled buttons are not a security boundary; invoke their handlers too.
    await page.evaluate(() => {
      for (const id of ['gitBuildBtn', 'pushBtn']) {
        document.getElementById(id).dispatchEvent(new MouseEvent('click'));
      }
    });
    await idle();
    assert.equal(requests.length, before, 'stale snapshot must not call any API');
  }

  async function localFiles() {
    return page.evaluate(() => {
      const fs = window.__lwp_pyodide.FS;
      return ['sources/a.md', 'public/a.html'].map((path) =>
        fs.readFile(window.__lwp_series_dir + '/' + path, { encoding: 'utf8' }));
    });
  }

  try {
    await page.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin === pageBaseUrl) return route.continue();
      const match = url.pathname.match(/^\/gitlab\/api\/v4\/projects\/([^/]+)\/repository\/(archive\.zip|tree|commits)$/);
      if (!match || ![new URL(baseUrl).origin, new URL(otherBaseUrl).origin].includes(url.origin)) {
        errors.push('Unexpected external request: ' + url.origin + url.pathname);
        return route.abort();
      }
      const project = decodeURIComponent(match[1]);
      const endpoint = match[2];
      const headers = { 'Access-Control-Allow-Origin': '*' };
      requests.push({ url: request.url(), method: request.method() });
      if (heldResponse && heldResponse.endpoint === endpoint) {
        const gate = heldResponse;
        heldResponse = null;
        gate.started();
        await gate.resume;
      }
      if (!['team/a', 'team/b'].includes(project)) {
        return route.fulfill({ status: 404, headers, body: 'Unknown project' });
      }
      if (endpoint === 'archive.zip') {
        return route.fulfill({ status: 200, headers, contentType: 'application/zip',
          body: Buffer.from(project === 'team/a' ? archiveA : archiveB, 'base64') });
      }
      if (endpoint === 'tree') {
        return route.fulfill({ status: 200, headers, contentType: 'application/json', body: '[]' });
      }
      assert.equal(request.method(), 'POST');
      commits.push({ baseUrl: url.origin + '/gitlab', project, ...request.postDataJSON() });
      return route.fulfill({ status: 201, headers, contentType: 'application/json', body: '{"id":"intercepted"}' });
    });
    await page.goto(pageBaseUrl + '/web/index.html');
    await status('Ready.');
    await page.click('#tabGit');
    assert.match(await page.textContent('label[for="token"]'), /api scope for Push; read_api for read-only Pull/);
    await page.fill('#baseUrl', baseUrl);
    await page.fill('#projectId', 'team/a');
    await page.fill('#token', token);
    await pullBuild();

    // Cosmetic edits normalize to the same target; credentials are not its identity.
    await page.fill('#baseUrl', ' https://GITLAB-A.invalid:443/gitlab/ ');
    await page.fill('#projectId', ' team/a ');
    await page.fill('#branch', '');
    await page.fill('#token', token + '-rotated');
    assert.equal(await page.isDisabled('#pushBtn'), false);
    assert.deepEqual(await page.evaluate(() => snapshotTarget), {
      baseUrl, projectId: 'team/a', branch: 'main',
    });
    await page.click('#pushBtn');
    await status('Pushed');
    assert.equal(commits.length, 1);
    assert.equal(commits[0].baseUrl, baseUrl);
    assert.equal(commits[0].project, 'team/a');
    assert.equal(commits[0].branch, 'main');

    // Each target field invalidates immediately, retains files, and stays invalid
    // when restored. A new Pull, not returning to the old text, restores readiness.
    for (const [field, changed, original] of [
      ['projectId', 'team/b', 'team/a'],
      ['baseUrl', otherBaseUrl, baseUrl],
      ['branch', 'release', 'main'],
    ]) {
      const files = await localFiles();
      await page.fill('#' + field, changed);
      await assertBlocked();
      assert.deepEqual(await localFiles(), files);
      await page.fill('#' + field, original);
      await assertBlocked();
      await pullBuild();
    }

    // DOM/programmatic edits can bypass input/change listeners entirely.
    for (const [field, changed, original] of [
      ['projectId', 'team/b', 'team/a'],
      ['baseUrl', otherBaseUrl, baseUrl],
      ['branch', 'release', 'main'],
    ]) {
      const before = requests.length;
      await page.evaluate(({ field, changed }) => {
        document.getElementById(field).value = changed;
        document.getElementById('pushBtn').dispatchEvent(new MouseEvent('click'));
      }, { field, changed });
      await idle();
      await assertBlocked();
      assert.equal(requests.length, before);
      await page.fill('#' + field, original);
      await pullBuild();
    }

    const beforeBuild = requests.length;
    await page.evaluate(() => {
      document.getElementById('projectId').value = 'team/b';
      document.getElementById('gitBuildBtn').dispatchEvent(new MouseEvent('click'));
    });
    await idle();
    await assertBlocked();
    assert.equal(requests.length, beforeBuild);
    await page.fill('#projectId', 'team/a');
    await pullBuild();

    // A pending pull must retain its captured origin, not acquire the new target.
    // Exercise both a silent DOM edit and an edit-and-restore during the await.
    for (const restore of [false, true]) {
      const gate = holdNext('archive.zip');
      await page.click('#pullBtn');
      await gate.waiting;
      if (restore) {
        await page.fill('#projectId', 'team/b');
        await page.fill('#projectId', 'team/a');
      } else {
        await page.evaluate(() => { document.getElementById('projectId').value = 'team/b'; });
      }
      gate.release();
      await idle();
      await assertBlocked();
      assert.equal(await page.evaluate(() => snapshotTarget.projectId), 'team/a');
      await page.fill('#projectId', 'team/a');
      await pullBuild();
    }

    // Delay delivery of a real Pyodide build result to exercise completion checks.
    await page.evaluate(() => {
      window.__bindingBuildGate = new Promise((resolve) => { window.__releaseBindingBuild = resolve; });
      window.__bindingBuildStarted = false;
      window.__lwp_pyodide.runPython(`
import js
_binding_real_build = build
async def build(series_dir, lang):
    result = _binding_real_build(series_dir, lang)
    js.window.__bindingBuildStarted = True
    await js.window.__bindingBuildGate
    return result
`);
    });
    await page.click('#gitBuildBtn');
    await page.waitForFunction(() => window.__bindingBuildStarted);
    await page.evaluate(() => { document.getElementById('projectId').value = 'team/b'; });
    await page.evaluate(() => window.__releaseBindingBuild());
    await idle();
    await assertBlocked();
    await page.evaluate(() => window.__lwp_pyodide.runPython('build = _binding_real_build'));
    await page.fill('#projectId', 'team/a');
    await pullBuild();

    // Once Push has started it may finish, but only at its captured target.
    const gate = holdNext('tree');
    await page.click('#pushBtn');
    await gate.waiting;
    await page.fill('#projectId', 'team/b');
    await page.fill('#baseUrl', otherBaseUrl);
    await page.fill('#branch', 'release');
    gate.release();
    await idle();
    await assertBlocked();
    assert.equal(commits.length, 2);
    assert.equal(commits[1].project, 'team/a');
    assert.equal(commits[1].baseUrl, baseUrl);
    assert.equal(commits[1].branch, 'main');

    // Pulling B explicitly replaces the binding; only B's own content goes to B.
    await pullBuild();
    await page.click('#pushBtn');
    await status('Pushed');
    assert.equal(commits.length, 3);
    assert.equal(commits[2].project, 'team/b');
    assert.equal(commits[2].baseUrl, otherBaseUrl);
    assert.equal(commits[2].branch, 'release');
    for (const commit of commits) {
      const label = commit.project === 'team/a' ? 'Project A snapshot' : 'Project B snapshot';
      for (const path of ['sources/a.md', 'public/a.html']) {
        const action = commit.actions.find((action) => action.file_path === path);
        assert.ok(action, 'missing source or real build output');
        const content = Buffer.from(action.content, 'base64').toString('utf8');
        assert.ok(content.includes(label));
        assert.equal(content.includes(commit.project === 'team/a'
          ? 'Project B snapshot' : 'Project A snapshot'), false);
      }
    }
    const keys = await page.evaluate(() => [...Object.keys(sessionStorage), ...Object.keys(localStorage)]);
    assert.deepEqual(keys, ['lwp_git_sync_connection']);
    assert.equal((await page.textContent('#status')).includes(token), false);
    const files = await localFiles();
    await page.click('#clearConnectionBtn');
    await assertBlocked();
    assert.deepEqual(await localFiles(), files);

    // A failed replacement Pull must not revive the previous built snapshot.
    await page.fill('#baseUrl', baseUrl);
    await page.fill('#projectId', 'team/missing');
    await page.fill('#token', token);
    await page.click('#pullBtn');
    await status('Pull failed');
    assert.equal(await page.isDisabled('#gitBuildBtn'), true);
    assert.equal(await page.isDisabled('#pushBtn'), true);
    assert.equal(await page.evaluate(() => snapshotTarget), null);
    assert.deepEqual(errors, []);
    console.log('OK');
  } finally {
    if (heldResponse) heldResponse.release();
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
