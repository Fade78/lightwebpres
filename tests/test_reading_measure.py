"""Every page of a series adapts to the screen the same way.

A series is one document in two shapes — an index that lists it and the
articles that are it — and a reader moves between them by clicking. When
the two shapes answer to the screen differently, the reader sees the
column jump on every click, and no single page looks wrong enough for
anyone to file a defect.

They did answer differently, at both ends of the scale, and for one
cause: the index carried its layout INLINE, in an attribute the theme
engine cannot reach and no media query can override.

  Wide: `max-width: 1200px` beside `padding: 8vw` — a fixed cap next to a
  padding that grows with the viewport, so the index got NARROWER as the
  screen got wider while the slide got wider. Measured before the fix,
  index against slide: 970 against 1210 at 1440, 893 against 1613 at
  1920, 790 against 2150 at 2560.

  Narrow: the mobile breakpoint turns `.slide` down to `40px 24px`, and
  an inline style outranks it, so on a 390-wide phone the index sat at
  31px of side padding against the slide's 24.

Both now resolve `page.content-max` through one rule in the composed
sheet, and both turn at the same breakpoint. This file asserts the
equality directly, at seven viewports from a phone to 4K, because the
property being shared is not the same statement as the pages rendering
alike — the first is readable in the source, the second is what a reader
gets.

Requires Node.js with the `playwright` package; skips cleanly if either
is missing, same as tests/test_web.py.

Run with: python3 tests/run_tests.py
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LWP = ROOT / 'lightwebpres'
SCRIPT = ROOT / 'tests' / 'reading_measure_e2e.cjs'


def _node_playwright_available():
    try:
        npm_root = subprocess.run(
            ['npm', 'root', '-g'], capture_output=True, text=True, timeout=30)
        if npm_root.returncode != 0:
            return False, 'npm root -g failed'
        root = npm_root.stdout.strip()
        probe = subprocess.run(
            ['node', '-e', "require('playwright')"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, 'NODE_PATH': root})
        if probe.returncode != 0:
            return False, 'playwright not resolvable via npm root -g'
        return True, root
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


AVAILABLE, NPM_ROOT_OR_REASON = _node_playwright_available()


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class TheIndexAndTheArticlesShareOneMeasure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name) / 'series'
        for step in (['init', str(root)], ['demo', str(root)]):
            done = subprocess.run(['python3', str(LWP), *step],
                                  capture_output=True, text=True, timeout=120)
            assert done.returncode == 0, done.stdout + done.stderr
        built = root / 'public'
        done = subprocess.run(
            ['python3', str(LWP), 'build', str(root), '--output', str(built)],
            capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stdout + done.stderr
        measured = subprocess.run(
            ['node', str(SCRIPT), (built / 'index.html').as_uri(),
             (built / 'first.html').as_uri()],
            capture_output=True, text=True, timeout=180,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
        assert measured.returncode == 0, measured.stdout + measured.stderr
        cls.rows = json.loads(measured.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_the_probe_actually_measured_something(self):
        """An empty measurement makes every assertion below vacuous, which
        is how a guard comes to pass for months over a page it never
        loaded."""
        self.assertGreaterEqual(len(self.rows), 7)
        for row in self.rows:
            self.assertGreater(row['index']['column'], 0, row)
            self.assertGreater(row['article']['column'], 0, row)

    def test_the_column_is_the_same_width_on_both_at_every_viewport(self):
        """The reader's statement, and the one a shared property does not
        by itself make: what lands on screen is the same width on the page
        that lists the series and on the page that is it."""
        for row in self.rows:
            self.assertEqual(
                row['index']['column'], row['article']['column'],
                f"at {row['width']}px the index column is "
                f"{row['index']['column']}px and the article column is "
                f"{row['article']['column']}px")

    def test_both_turn_at_the_same_breakpoint(self):
        """The narrow end, which the width comparison alone would miss: an
        index that matched the article's WIDTH could still keep desktop
        padding on a phone. The padding is the assertion here."""
        for row in self.rows:
            self.assertEqual(
                (row['index']['left'], row['index']['top']),
                (row['article']['left'], row['article']['top']),
                f"at {row['width']}px the index pads "
                f"{row['index']['left']}/{row['index']['top']} and the "
                f"article pads {row['article']['left']}/"
                f"{row['article']['top']}")

    def test_a_wider_screen_never_gives_less_text(self):
        """The defect underneath the divergence, and the one that would
        survive making the two pages agree with each other: a fixed cap
        beside a viewport-relative padding shrinks the column as the
        window grows. Stated on its own so it fails even if both pages
        ever shrink together."""
        for page in ('index', 'article'):
            widths = [(r['width'], r[page]['column']) for r in self.rows]
            for (w1, c1), (w2, c2) in zip(widths, widths[1:]):
                self.assertGreaterEqual(
                    c2, c1,
                    f'{page}: {w1}px gives {c1}px of column and the wider '
                    f'{w2}px gives {c2}px — a bigger screen gave less text')
