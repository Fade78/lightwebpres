"""End-to-end test for web/index.html (the Pyodide-in-the-browser build).

Real browser, real Pyodide, real zip upload/download — this exercises the
actual deliverable, not a simulation. Requires Node.js with the `playwright`
package (and its Chromium browser) available; skips cleanly if either is
missing, since this is a heavier dependency than the rest of the suite (the
core lightwebpres tool itself stays stdlib-only, see specifications.md §13.4
— only this optional browser wrapper depends on Node/Playwright/Pyodide).

Run with: python3 tests/run_tests.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_E2E_SCRIPT = Path(__file__).resolve().parent / 'web_e2e.cjs'
FILE_PROTOCOL_GUARD_SCRIPT = Path(__file__).resolve().parent / 'file_protocol_guard_e2e.cjs'


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


def _make_test_zip(zip_path):
    """A minimal but complete series: one article, one full-article body."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'articles').mkdir()
        (root / 'series.json').write_text(json.dumps({
            'articles': [{
                'file': 'a.html', 'source': 'a.md',
                'series_title': 'A', 'series_desc': 'A',
            }],
        }), encoding='utf-8')
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\nfile: a.html\nh1: Web test\n'
            'series_title: A\nseries_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Web build test\n'
            'summary: Built entirely in the browser.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: a_article.md\n',
            encoding='utf-8',
        )
        (root / 'articles' / 'a_article.md').write_text(
            '# Full article\n\nBuilt via Pyodide, in-browser.\n',
            encoding='utf-8',
        )
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in root.rglob('*'):
                if f.is_file():
                    zf.write(f, f.relative_to(root))


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class WebBuild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(REPO_ROOT)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)

    def _build(self, lang):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / 'series.zip'
            out_path = Path(tmp) / 'public.zip'
            _make_test_zip(zip_path)

            result = subprocess.run(
                ['node', str(WEB_E2E_SCRIPT), 'http://127.0.0.1:%d' % self.port,
                 str(zip_path), lang, str(out_path)],
                capture_output=True, text=True,
                env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(out_path.exists(), 'no file was downloaded')

            with zipfile.ZipFile(out_path) as zf:
                names = zf.namelist()
                self.assertIn('a.html', names)
                self.assertIn('index.html', names)
                html = zf.read('a.html').decode('utf-8')
            return html

    def test_build_in_browser_french(self):
        html = self._build('fr')
        self.assertIn('Built entirely in the browser.', html)
        self.assertIn('Planche précédente', html)

    def test_build_in_browser_english(self):
        html = self._build('en')
        self.assertIn('Built entirely in the browser.', html)
        self.assertIn('Previous slide', html)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class FileProtocolGuard(unittest.TestCase):
    """§23.6: opening index.html or git-sync.html as a local file:// page
    (the natural thing to do with a self-contained static page) can never
    actually load Pyodide — browsers block its module/asset fetches under
    the file:// origin. init() must detect this up front and show a clear,
    actionable, one-click-copyable command instead of letting Pyodide fail
    with a raw, confusing browser error."""

    def _check(self, html_filename):
        # The expected command pins down the exact, complete, copyable
        # command — naming the real repo root computed from the file's own
        # path, not a vague "serve this directory" that would silently
        # serve whatever directory happens to be the shell's cwd (e.g. a
        # cluttered Downloads folder) instead of the one that actually has
        # the sibling files this page needs. The driver script also clicks
        # the Copy button and reads the clipboard back, so this exercises
        # copyability end to end, not just that the text is present.
        file_url = 'file://' + str(REPO_ROOT / 'web' / html_filename)
        expected = 'python3 -m http.server 8000 --directory "%s"' % REPO_ROOT
        result = subprocess.run(
            ['node', str(FILE_PROTOCOL_GUARD_SCRIPT), file_url, expected],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_index_html_shows_guard_when_opened_as_local_file(self):
        self._check('index.html')

    def test_git_sync_html_shows_guard_when_opened_as_local_file(self):
        self._check('git-sync.html')


if __name__ == '__main__':
    unittest.main()
