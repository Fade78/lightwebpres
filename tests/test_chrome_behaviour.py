"""End-to-end tests for three behaviours of the page chrome, all three
reported from the field and none of them expressible against the
generated HTML — what is under test is what the script DOES, in a real
browser, with real pointer events:

  - Releasing the mouse after highlighting text must not advance the
    deck. A drag-select ends in an ordinary click; whether the handler
    acts on it is a runtime decision.
  - The cursor hidden in fullscreen must come back only after sustained
    movement, not after a twitch. The condition is a matter of event
    timing and nothing else.
  - F must enter fullscreen on the index, as it does on an article page.

Requires Node.js with the `playwright` package (and its Chromium
browser); skips cleanly if either is missing, like the other e2e tests.

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
SCRIPT = Path(__file__).resolve().parent / 'chrome_behaviour_e2e.cjs'


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
class ChromeBehaviour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        parent = Path(cls.tmpdir.name)
        served = parent / 'served'
        served.mkdir()

        # Two articles, so the index carries cards and the deck has a
        # slide to advance TO — a one-slide deck cannot show the
        # difference between "did not advance" and "had nowhere to go".
        root = parent / 'series'
        (root / 'articles').mkdir(parents=True)
        (root / 'series.json').write_text(json.dumps({
            'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'},
                {'page_dest': 'b.html', 'page_source': 'b.md',
                 'nav_title': 'B', 'nav_desc': 'B'},
            ],
        }), encoding='utf-8')
        # A cover with a summary long enough to drag across, then two more
        # slides to advance into.
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Chrome test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: C\n# Chrome test\n'
            'summary: A summary long enough that a pointer can be dragged '
            'across it from one side to the other and take a real selection '
            'with it on the way.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: S1\n## Second slide\n'
            'summary: Somewhere to advance to.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: S2\n## Third slide\n'
            'summary: And somewhere after that.\n\n---\n\n'
            # A card the default filter HIDES. It is the only way to
            # tell the page's own hash handling apart from the
            # browser's: a filtered card has no layout box, so a
            # native fragment jump cannot reach it, and only a script
            # that reads the fragment, selects the card's tag and
            # then goes there will land the reader on it.
            '<!-- lwp:slide -->\nkicker: S3\ntags: avance\n'
            '## Fourth slide\nsummary: Behind a tag filter.\n',
            encoding='utf-8',
        )
        (root / 'articles' / 'b.md').write_text(
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\n'
            'nav_title: B\nnav_desc: B\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: C\n# Article B\n'
            'summary: Cover slide.\n',
            encoding='utf-8',
        )
        result = subprocess.run(
            ['python3', str(LWP), 'build', str(root),
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

    def test_selection_cursor_and_the_index_fullscreen_key(self):
        base = 'http://127.0.0.1:%d/site' % self.port
        result = subprocess.run(
            ['node', str(SCRIPT), base + '/a.html', base + '/index.html'],
            capture_output=True, text=True, timeout=180,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
        )
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
