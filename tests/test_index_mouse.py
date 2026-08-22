"""End-to-end test for the index page as a card deck (§8.4): with the
two skeletons unified, the index carries the article's navigation engine
and the cards ARE the journey. In a real browser, with real pointer
events:

  - a left click on the ground focuses the next card;
  - a right click on the ground focuses the previous card;
  - a click on a card follows it (the card is a link, and a click on it
    is interactive — the deck must not steal it);
  - Enter on a focused card follows it (the browser's own default);
  - the share button opens the popover, copies the series/article links,
    and keeps the fiche scope disabled — the index has no fiche (§9.3.4);
  - middle-then-left asks for fullscreen (stubbed, like the other e2e);
  - Home returns to the top of the page.

Requires Node.js with the `playwright` package (and its Chromium browser)
available; skips cleanly if either is missing, same as the other e2e.

Run with: python3 tests/run_tests.py
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LWP = REPO_ROOT / 'lightwebpres'
INDEX_MOUSE_SCRIPT = Path(__file__).resolve().parent / 'index_mouse_e2e.cjs'


def _node_playwright_available():
    if shutil.which('node') is None:
        return False, 'node not found on PATH'
    npm_root = subprocess.run(
        ['npm', 'root', '-g'], capture_output=True, text=True,
    ).stdout.strip()
    check = subprocess.run(
        ['node', '-e', "require('playwright')"],
        capture_output=True, text=True,
        env={**os.environ, 'NODE_PATH': npm_root},
    )
    if check.returncode != 0:
        return False, 'playwright not resolvable via npm root -g'
    return True, npm_root


AVAILABLE, NPM_ROOT_OR_REASON = _node_playwright_available()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class IndexMouse(unittest.TestCase):
    """A three-article series, so the index carries cards to step through
    and the card link has somewhere real to land."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name)
        served = root / 'served'
        served.mkdir()

        series = root / 'series'
        (series / 'sources').mkdir(parents=True)
        (series / 'series.json').write_text(json.dumps({
            'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'},
                {'page_dest': 'b.html', 'page_source': 'b.md',
                 'nav_title': 'B', 'nav_desc': 'B'},
                {'page_dest': 'c.html', 'page_source': 'c.md',
                 'nav_title': 'C', 'nav_desc': 'C'},
            ],
        }), encoding='utf-8')
        for letter in ('a', 'b', 'c'):
            (series / 'sources' / ('%s.md' % letter)).write_text(
                '<!-- lwp:meta -->\npage_dest: %s.html\npage_title: Article %s\n'
                'nav_title: %s\nnav_desc: %s\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: c%s\nkicker: C\n# Article %s\n'
                'summary: Cover slide.\n' % (
                    letter, letter.upper(), letter.upper(), letter.upper(),
                    letter.upper(), letter.upper()),
                encoding='utf-8',
            )
        result = subprocess.run(
            ['python3', str(LWP), 'build', str(series),
             '--output', str(served / 'site')],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        cls.httpd = HTTPServer(('127.0.0.1', 0),
                               lambda *a: _QuietHandler(*a, directory=str(served)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_index_mouse_navigation_share_and_home(self):
        base = 'http://127.0.0.1:%d/site' % self.port
        result = subprocess.run(
            ['node', str(INDEX_MOUSE_SCRIPT), base + '/index.html'],
            capture_output=True, text=True, timeout=90,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
