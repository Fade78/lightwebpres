"""End-to-end test for the article-page share button (§9.2.1): a real
browser click-through of the popover matrix (copy-link / QR code, scoped
to series/article/fiche), including a real clipboard read and a real QR
SVG render — not just string assertions against the generated HTML.

Requires Node.js with the `playwright` package (and its Chromium browser)
available; skips cleanly if either is missing, same as tests/test_web.py.

Run with: python3 tests/run_tests.py
"""

import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LWP = REPO_ROOT / 'lightwebpres'
SHARE_BUTTON_SCRIPT = Path(__file__).resolve().parent / 'share_button_e2e.cjs'


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


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class ShareButton(unittest.TestCase):
    """A built article with three slides (cover + one standard slide +
    series-nav), so the "fiche" scope can be exercised disabled (on the
    cover), enabled (standard slide, with a real #s2 clipboard check),
    and disabled again (series-nav — §9.2.1 says the scope follows the
    slide TYPE, and this slide type was previously absent from the
    fixture entirely)."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name)
        (root / 'articles').mkdir()
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}],
        }), encoding='utf-8')
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Share button test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Share button test\n'
            'summary: Cover slide.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T2\n## Second slide\n'
            'summary: A second slide, to leave the cover behind.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n',
            encoding='utf-8',
        )
        output_dir = root / 'public'
        result = subprocess.run(
            ['python3', str(LWP), 'build', str(root), '--output', str(output_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(output_dir)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_share_matrix_copy_and_qr(self):
        base = 'http://127.0.0.1:%d' % self.port
        result = subprocess.run(
            ['node', str(SHARE_BUTTON_SCRIPT), base + '/a.html', base + '/a.html', base + '/index.html'],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
