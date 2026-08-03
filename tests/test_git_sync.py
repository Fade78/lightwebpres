"""End-to-end test for the "Sync with GitLab" tab of web/index.html
(pull/build/push against a GitLab instance's REST API v4, from inside the
browser).

Real browser, real Pyodide — same philosophy as test_web.py. There is no
real GitLab server here: a minimal mock of the three API v4 endpoints this
page uses (repository/archive.zip, repository/tree, repository/commits) is
served on its own port, so the browser genuinely crosses origins and the
CORS headers this page depends on are exercised for real, not assumed.

Requires Node.js with the `playwright` package; skips cleanly if either is
missing (see test_web.py for the rationale — this is a dependency of the
optional browser wrapper, not of lightwebpres itself, spec §13.4).

Run with: python3 tests/run_tests.py
"""

import base64
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO_ROOT = Path(__file__).resolve().parent.parent
E2E_SCRIPT = Path(__file__).resolve().parent / 'git_sync_e2e.cjs'

TOKEN = 'test-token-abc123'
PROJECT_ID = '42'
BRANCH = 'main'

ARTICLE_MD = (
    '<!-- lwp:meta -->\npage_title: Git sync test\nnav_title: A\n'
    'nav_desc: A\n---\n\n'
    '<!-- lwp:slide:cover -->\ntag: T\n# Git sync test\n'
    'summary: Built by pulling from a mock GitLab repository.\n\n---\n\n'
    '<!-- lwp:slide -->\ntag: Fact\n## A highlighted fact\n'
    'highlight: 100 %\nhighlight-caption: pulled, built and pushed in one browser tab\n'
)


def _node_playwright_available():
    if shutil.which('node') is None:
        return False, 'node not found on PATH'
    npm_root = subprocess.run(
        ['npm', 'root', '-g'], capture_output=True, text=True,
    ).stdout.strip()
    check = subprocess.run(
        ['node', '-e', "require('playwright')"],
        capture_output=True, text=True,
        env={**__import__('os').environ, 'NODE_PATH': npm_root},
    )
    if check.returncode != 0:
        return False, 'playwright not resolvable via npm root -g'
    return True, npm_root


AVAILABLE, NPM_ROOT_OR_REASON = _node_playwright_available()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def _make_archive_zip():
    """A GitLab-shaped archive.zip: everything wrapped in one top-level
    folder, as the real endpoint produces. Includes articles/old.md, an
    already-remote file the "never deletes" test removes locally before
    pushing (spec §24.4)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        prefix = 'series-main-abc1234/'
        zf.writestr(prefix + 'series.json', json.dumps({
            'articles': [{'page_source': 'a.md'}],
        }))
        zf.writestr(prefix + 'articles/a.md', ARTICLE_MD)
        zf.writestr(prefix + 'articles/old.md', '# An old, unrelated file\n')
    return buf.getvalue()


class _MockGitLabHandler(BaseHTTPRequestHandler):
    """Minimal mock of the three GitLab API v4 endpoints git_sync.py calls.
    Shared state (received commit actions) lives on the class so the test
    can inspect it after the browser-driven run completes."""

    received_commits = []
    remote_tree = [
        {'path': 'series.json', 'type': 'blob'},
        {'path': 'articles/a.md', 'type': 'blob'},
        {'path': 'articles/old.md', 'type': 'blob'},
    ]

    def log_message(self, fmt, *args):
        pass

    def _cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type, PRIVATE-TOKEN')

    def _check_token(self):
        return self.headers.get('PRIVATE-TOKEN') == TOKEN

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self._check_token():
            self.send_response(401)
            self._cors_headers()
            self.end_headers()
            return

        if self.path.startswith('/api/v4/projects/%s/repository/archive.zip' % PROJECT_ID):
            data = _make_archive_zip()
            self.send_response(200)
            self._cors_headers()
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path.startswith('/api/v4/projects/%s/repository/tree' % PROJECT_ID):
            query = parse_qs(urlparse(self.path).query)
            page = int(query.get('page', ['1'])[0])
            body = json.dumps(self.remote_tree if page == 1 else []).encode('utf-8')
            self.send_response(200)
            self._cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if not self._check_token():
            self.send_response(401)
            self._cors_headers()
            self.end_headers()
            return

        if self.path.startswith('/api/v4/projects/%s/repository/commits' % PROJECT_ID):
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            self.__class__.received_commits.append(payload)
            body = json.dumps({'id': 'fakecommitsha%d' % len(self.received_commits)}).encode('utf-8')
            self.send_response(201)
            self._cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self._cors_headers()
        self.end_headers()


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class GitSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.page_httpd = ThreadingHTTPServer(
            ('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(REPO_ROOT)),
        )
        cls.page_port = cls.page_httpd.server_address[1]
        cls.page_thread = threading.Thread(target=cls.page_httpd.serve_forever, daemon=True)
        cls.page_thread.start()

        _MockGitLabHandler.received_commits = []
        cls.gitlab_httpd = ThreadingHTTPServer(('127.0.0.1', 0), _MockGitLabHandler)
        cls.gitlab_port = cls.gitlab_httpd.server_address[1]
        cls.gitlab_thread = threading.Thread(target=cls.gitlab_httpd.serve_forever, daemon=True)
        cls.gitlab_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.page_httpd.shutdown()
        cls.page_thread.join(timeout=5)
        cls.gitlab_httpd.shutdown()
        cls.gitlab_thread.join(timeout=5)

    def setUp(self):
        _MockGitLabHandler.received_commits = []

    def test_pull_build_push_round_trip(self):
        page_base = 'http://127.0.0.1:%d' % self.page_port
        gitlab_base = 'http://127.0.0.1:%d' % self.gitlab_port

        result = subprocess.run(
            ['node', str(E2E_SCRIPT), page_base, gitlab_base, PROJECT_ID, BRANCH, TOKEN],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        commits = _MockGitLabHandler.received_commits
        self.assertEqual(len(commits), 1, 'expected exactly one commit (all 4 files fit in one chunk)')
        commit = commits[0]
        self.assertEqual(commit['branch'], BRANCH)

        actions_by_path = {a['file_path']: a for a in commit['actions']}
        # series.json and articles/a.md already exist remotely -> update.
        self.assertEqual(actions_by_path['series.json']['action'], 'update')
        self.assertEqual(actions_by_path['articles/a.md']['action'], 'update')
        # public/*.html did not exist remotely -> create.
        self.assertEqual(actions_by_path['public/a.html']['action'], 'create')
        self.assertEqual(actions_by_path['public/index.html']['action'], 'create')

        # The pushed public/a.html must be the actually-built HTML, not the
        # source markdown -- decode it and check for build-produced content.
        pushed_html = base64.b64decode(actions_by_path['public/a.html']['content']).decode('utf-8')
        self.assertIn('Git sync test', pushed_html)
        self.assertIn('pulled, built and pushed in one browser tab', pushed_html)
        self.assertIn('<div class="highlight">', pushed_html)

    def test_push_never_deletes_a_file_removed_locally(self):
        """Spec §24.4: a file removed locally after pull (here,
        articles/old.md, which still exists in the mock's remote_tree)
        must never turn into a 'delete' action — push() only ever
        create/updates the files it finds locally."""
        page_base = 'http://127.0.0.1:%d' % self.page_port
        gitlab_base = 'http://127.0.0.1:%d' % self.gitlab_port

        result = subprocess.run(
            ['node', str(E2E_SCRIPT), page_base, gitlab_base, PROJECT_ID, BRANCH, TOKEN, 'articles/old.md'],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        commits = _MockGitLabHandler.received_commits
        all_actions = [a for commit in commits for a in commit['actions']]

        self.assertFalse(
            any(a['action'] == 'delete' for a in all_actions),
            'push() must never emit a delete action',
        )
        self.assertNotIn(
            'articles/old.md', [a['file_path'] for a in all_actions],
            'a file removed locally must simply be absent from the push, not deleted remotely',
        )


if __name__ == '__main__':
    unittest.main()
