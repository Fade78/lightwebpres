"""End-to-end test for arrow-key navigation on an article page: a real
browser keyboard-driven walk (not just string assertions against the
generated HTML), covering two behaviors added on top of the plain
slide-to-slide arrow navigation:

  - A slide taller than the viewport (typically a long full-article) gets
    scrolled down in increments before an arrow key advances past it.
  - On the series-nav slide, arrow keys step through its cards one by
    one (instead of skipping straight past the whole slide), and Enter
    on a focused card jumps to that article — like Tab, but confined to
    the natural slide/card/scroll journey instead of leaving the page.

Two independent series (built separately, served side by side): 'tall'
is a single-article series with nothing to link to, so its full-article
slide is the only thing that can overflow the viewport; 'nav' is a
three-article series (nav, b, c) whose series-nav slide has exactly the
two sibling cards + the back-to-index link the e2e script expects —
sharing one series.json between both fixtures would give the nav
article's series-nav slide an extra card for the unrelated 'tall'
article too (every OTHER article gets a card, not just later ones),
which doesn't serve either behavior under test.

Requires Node.js with the `playwright` package (and its Chromium browser)
available; skips cleanly if either is missing, same as tests/test_web.py.

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
KEYBOARD_NAV_SCRIPT = Path(__file__).resolve().parent / 'keyboard_nav_e2e.cjs'


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


def _build(series_root, output_dir):
    result = subprocess.run(
        ['python3', str(LWP), 'build', str(series_root), '--output', str(output_dir)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class KeyboardNav(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        parent = Path(cls.tmpdir.name)
        served = parent / 'served'
        served.mkdir()

        # --- 'tall' series: a single article, cover + an overloaded
        # full-article slide + a trailing standard slide only reachable
        # once the overflowing slide has been scrolled through. ---------
        tall_root = parent / 'tall_series'
        (tall_root / 'articles').mkdir(parents=True)
        (tall_root / 'series.json').write_text(json.dumps({
            'articles': [{'file': 'tall.html', 'source': 'tall.md', 'series_title': 'Tall', 'series_desc': 'Tall'}],
        }), encoding='utf-8')
        # Long enough to push the slide's rendered height well past any
        # realistic viewport (~700px in the e2e script).
        long_body = '\n\n'.join(
            '## Section %d\n\nParagraph %d with enough text to take up real '
            'vertical space on the page, repeated many times over so the '
            'whole slide genuinely overflows a normal browser window.' % (i, i)
            for i in range(1, 41)
        )
        (tall_root / 'articles' / 'tall_article.md').write_text(long_body, encoding='utf-8')
        (tall_root / 'articles' / 'tall.md').write_text(
            '<!-- lwp:meta -->\nfile: tall.html\nh1: Tall test\n'
            'series_title: Tall\nseries_desc: Tall\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Tall test\n'
            'summary: Cover slide.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: tall_article.md\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T2\n## Trailing slide\n'
            'summary: Reachable only once the overflowing slide before it has been scrolled through.\n',
            encoding='utf-8',
        )
        _build(tall_root, served / 'tall')

        # --- 'nav' series: nav (cover + standard + series-nav) plus two
        # minimal sibling articles the series-nav slide links to, so its
        # cards are exactly [b.html, c.html, index.html]. ----------------
        nav_root = parent / 'nav_series'
        (nav_root / 'articles').mkdir(parents=True)
        (nav_root / 'series.json').write_text(json.dumps({
            'articles': [
                {'file': 'nav.html', 'source': 'nav.md', 'series_title': 'Nav', 'series_desc': 'Nav'},
                {'file': 'b.html', 'source': 'b.md', 'series_title': 'B', 'series_desc': 'B'},
                {'file': 'c.html', 'source': 'c.md', 'series_title': 'C', 'series_desc': 'C'},
            ],
        }), encoding='utf-8')
        (nav_root / 'articles' / 'nav.md').write_text(
            '<!-- lwp:meta -->\nfile: nav.html\nh1: Nav test\n'
            'series_title: Nav\nseries_desc: Nav\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Nav test\n'
            'summary: Cover slide.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T2\n## Standard slide\n'
            'summary: One ordinary slide before the series-nav slide.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n',
            encoding='utf-8',
        )
        for letter in ('b', 'c'):
            (nav_root / 'articles' / ('%s.md' % letter)).write_text(
                '<!-- lwp:meta -->\nfile: %s.html\nh1: Article %s\n'
                'series_title: %s\nseries_desc: %s\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Article %s\n'
                'summary: Cover slide.\n' % (letter, letter.upper(), letter.upper(), letter.upper(), letter.upper()),
                encoding='utf-8',
            )
        _build(nav_root, served / 'nav')

        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(served)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_tall_slide_scroll_and_series_nav_card_stepping(self):
        base = 'http://127.0.0.1:%d' % self.port
        result = subprocess.run(
            ['node', str(KEYBOARD_NAV_SCRIPT), base + '/tall/tall.html', base + '/nav/nav.html'],
            capture_output=True, text=True,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
