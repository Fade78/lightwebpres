"""Counts the rendered font sizes that do NOT change when the screen doubles.

The instrument three audits went without. Each of them found the same
defect wearing a different costume — a component that disagreed with its
neighbours, a size with no scale, a length pinned against a glyph — and
each time the measurement that would have caught it was a column nobody
had thought to add:

  §9  did the components agree with each other?
  §11 how many sizes are there, and did all of them get a scale?
  §13 is this length drawn against the text?
  §5.1 how many sizes are written as literals, outside the registry?

They are four phrasings of one question, and this file asks it directly:
render a real page at 1920 and at 3840, and name every element whose text
is the same number of pixels in both. On a deck shown full screen, a size
that does not move is a size that shrinks relative to everything around
it, and the bigger the screen the worse it reads.

The check is an EXACT match against `STILL_FLAT`, not a subset. A new flat
element fails it, which is the point; but so does fixing one and leaving
it listed, which is what keeps the list honest as the remaining lots land.

Walks the DOM rather than a list of selectors, deliberately: a list only
ever covers the components someone remembered, and the last two instances
of this defect were in components added after the list was written.

Requires Node.js with the `playwright` package; skips cleanly if either is
missing, same as tests/test_web.py.

Run with: python3 tests/run_tests.py
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LWP = REPO_ROOT / 'lightwebpres'
SCRIPT = Path(__file__).resolve().parent / 'type_scale_e2e.cjs'


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


# Known blind spot, stated rather than papered over: the probe's `.refs`
# block renders its line as direct text, so `.full-article .refs p` — a
# second declaration on a paragraph inside it — is never matched here. The
# block itself (`refs.size`) IS measured and does scale. Reaching the inner
# rule needs a fixture whose raw-HTML div wraps its content in a <p>, and
# an instrument that quietly covers less than it looks like it does is the
# failure this whole file exists to name.

# Everything still pinned to pixels, with the lot that owns it.
#
# Remove an entry when its lot lands. Leaving one here after fixing it
# fails this test, which is deliberate: a stale exemption is how a guard
# quietly stops guarding.
#
# The list is EMPTY as of lot 5.8. It held twelve entries — the whole
# navigation chrome, the help overlay, the share popover and its QR modal
# — and the pattern behind all twelve was the same: a root box with no
# font-size of its own, so its `em` children were `em` of a body that
# never grows. Giving each root the size it was already implying, in the
# `max(floor, N vmin)` form the rest of the design uses, moved eleven of
# them at once. Keep it empty: an entry added here is a promise to come
# back, and this comment is the record of how long the last batch waited.
STILL_FLAT = set()


_ARTICLE = """<!-- lwp:meta -->
page_dest: a.html
page_title: Type scale probe
nav_title: A
nav_desc: A
---

<!-- lwp:slide:cover -->
kicker: PROBE
# Type scale probe
summary: A cover, so the page is a real page.

---

<!-- lwp:slide -->
kicker: FIGURE
## A card with a key figure and a fact box
summary: The summary line, which is prose and scales with the column.
highlight: 42 / 70
highlight-caption: what the key figure counts
source: A source line, 2026.
fact-label: THE FACT
The fact box body, **with a marked run** and a [link](https://example.org).

---

<!-- lwp:slide -->
kicker: FREE
## A card whose body is free Markdown
summary: No fact-label on this one, so the body is a .slide-body.

A bare paragraph, which is the same prose as the fact box above and must
not render at a different size for that reason alone.

#### A body heading

![A figure](img/probe.png "The caption under a figure")

---

<!-- lwp:slide:full-article -->
article: a_article.md
"""

_LONG = """# The article's own title

Body prose in the long-form piece.

## A section heading

More prose, so the heading above has something to be larger than.

### A sub-section

| Column | Other |
| --- | --- |
| cell | cell |

> A block quote.

```
a code block
```

<div class="refs">

A reference line, the apparatus block at the foot of the article.

</div>
"""


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class EveryRenderedSizeMovesWithTheScreen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name) / 'series'
        (root / 'articles' / 'img').mkdir(parents=True)
        (root / 'series.json').write_text(json.dumps({'articles': [
            {'page_dest': 'a.html', 'page_source': 'a.md',
             'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
        (root / 'articles' / 'a.md').write_text(_ARTICLE, encoding='utf-8')
        (root / 'articles' / 'a_article.md').write_text(_LONG, encoding='utf-8')
        (root / 'articles' / 'img' / 'probe.png').write_bytes(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
        built = Path(cls.tmpdir.name) / 'public'
        result = subprocess.run(
            ['python3', str(LWP), 'build', str(root), '--output', str(built)],
            capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        measured = subprocess.run(
            ['node', str(SCRIPT), (built / 'a.html').as_uri()],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
        assert measured.returncode == 0, measured.stdout + measured.stderr
        cls.sizes = json.loads(measured.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_the_probe_actually_rendered_something(self):
        """An empty measurement makes every assertion below vacuous — the
        failure mode that let a theme property go unexercised for months.
        The count is a floor, not a pin: adding a component must not have
        to touch this line."""
        self.assertGreater(len(self.sizes), 25,
                           'the probe page rendered almost no text: the '
                           'measurement, not the design, is what failed')
        scaling = [k for k, v in self.sizes.items() if v['a'] != v['b']]
        self.assertGreater(len(scaling), 15,
                           'nothing scaled at all — check the instrument '
                           'before believing the design regressed')

    def test_no_rendered_size_stays_put_when_the_screen_doubles(self):
        flat = {k for k, v in self.sizes.items() if v['a'] == v['b']}
        new = sorted(flat - STILL_FLAT)
        fixed = sorted(STILL_FLAT - flat)
        self.assertEqual(new, [], 'these sizes do not grow with the screen, '
                         'so they shrink against everything around them:\n  '
                         + '\n  '.join(f'{k} = {self.sizes[k]["a"]}px'
                                       for k in new))
        self.assertEqual(fixed, [], 'these are listed as still flat but do '
                         'scale now — drop them from STILL_FLAT:\n  '
                         + '\n  '.join(fixed))

    def test_a_heading_is_larger_than_the_text_it_heads(self):
        """The defect that made this file necessary. The article's own
        headings were literals in the skeleton while its body text was a
        registry property with a scale, so at 3840 an h2 rendered at 22px
        over a 40.5px body — a heading a little over half the size of the
        prose beneath it. The inversion had already started at 1920.

        Reads SCOPED keys on purpose: `h2` alone is the slide title as
        well, it comes first in the DOM, and comparing that one proves
        nothing about the article."""
        scope = 'section.full-article.slide'
        body = f'{scope} p'
        self.assertIn(body, self.sizes, 'the probe grew no article prose')
        for level in ('h1', 'h2', 'h3'):
            key = f'{scope} {level}'
            self.assertIn(key, self.sizes, f'the probe grew no {level}')
            for slot, width in (('a', 1920), ('b', 3840)):
                self.assertGreater(
                    self.sizes[key][slot], self.sizes[body][slot],
                    f'{level} is not larger than the body it heads at '
                    f'{width}: {self.sizes[key][slot]}px over '
                    f'{self.sizes[body][slot]}px')
