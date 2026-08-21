"""Instrument 2: contrast measured on the rendered page, every theme.

`theme show` reports contrast from the property registry, which is the
right way to check a theme and is structurally unable to see three
things:

  - an element with no registry property of its own. The speaker counter
    measured EXACTLY 1.00:1 on 15 of the 34 built-in themes and the
    report could not say so, because there was nothing for it to read.
  - a ground that arrives from an ancestor. A transparent background
    takes whatever is behind it, which the registry does not model.
  - a card variant an AUTHOR defines, which the registry has never heard
    of. Nothing reads it, so nothing can report on the text sitting on
    it — the one case the registry report is structurally blind to.

So this walks the DOM of a built page: for every element that paints its
own text it resolves the ink, composites the grounds upward until an
opaque one closes the chain, and reports the ratio with the size and
weight that decide the threshold (WCAG 1.4.3 — 3:1 for large text, 4.5:1
otherwise).

Gradients are the reason a first version of this reported four failures
that were not real. A gradient's `backgroundColor` is transparent, so
reading only that walks past the cover and lands on the page behind it —
and on a light theme the page ground IS the cover's ink, so it announced
1.00:1 for text that is perfectly legible. Text over a gradient must
clear the bar at every stop it crosses, so each stop is a candidate
ground and the worst one is the answer.

A DOM walk has a blind spot of its own, and the build stamp fell into
it: an OVERLAY's ground is not its ancestor's background, it is whichever
sibling the painter drew there first. The stamp used to sit beside the
cards and inherit the body's ink, which on a light theme is the very
colour the cover paints its ground with — 1.00:1, on a page the ancestor
walk called legible. So a second instrument runs over the same builds
(build_stamp_e2e.cjs), taking the ground from `elementsFromPoint`, which
is the painter's own answer.

Requires Node.js with the `playwright` package; skips cleanly if either
is missing, same as tests/test_web.py.

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
SCRIPT = Path(__file__).resolve().parent / 'contrast_e2e.cjs'
STAMP_SCRIPT = Path(__file__).resolve().parent / 'build_stamp_e2e.cjs'


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

# A card variant the AUTHOR defines, which no registry property covers.
# A variant paints nothing by design: the engine emits the class and the
# author supplies the colours, so the registry has no property to read.
# Here is a CAREFUL one -- ground and both inks -- measured like
# everything else.
_CUSTOM_CSS = """
.fact-box.fact--warn { background: #FFF3CD; }
.fact-box.fact--warn .fact-content { color: #4A3D14; }
.fact-box.fact--warn .fact-label { color: #4A3D14; }
"""

# The same variant written carelessly: a ground, and only the body ink
# recoloured. The label keeps whatever the theme gave it, over a colour
# the theme has never seen. This is the case the registry cannot see,
# and it is the first thing the instrument found -- on twelve of the
# thirteen themes the
# registry reports as AA, because a careful author is not what the
# registry is checking.
_CARELESS_CSS = """
.fact-box.fact--warn { background: #FFF3CD; }
.fact-box.fact--warn .fact-content { color: #4A3D14; }
"""

_ARTICLE = """<!-- lwp:meta -->
page_dest: a.html
page_title: Contrast probe
nav_title: A
nav_desc: A
---

<!-- lwp:slide:cover -->
slug: c1
kicker: PROBE
# Contrast probe
summary: A cover, whose ground is a gradient rather than one colour.

---

<!-- lwp:slide -->
slug: c2
kicker: FIGURE
## A card with a key figure and a fact box
summary: The summary line, which is prose over the card's own ground.
highlight: 42 / 70
highlight-caption: what the key figure counts
source: A source line, 2026.
fact-label: THE FACT
The fact box body, **with a marked run** and a [link](https://example.org).

---

<!-- lwp:slide -->
slug: c3
kicker: VARIANT
## A card carrying an author-defined variant
summary: Nothing in the registry knows this variant exists.
fact-variant: warn
fact-label: THE WARNING
Body text on a ground the author chose, which is the case the registry
report cannot reach at all.

---

<!-- lwp:slide -->
slug: c4
kicker: FREE
## A card whose body is free Markdown
summary: No fact-label, so the body is a .slide-body.

A bare paragraph, a **bold run**, and `some code`.

#### A body heading

| Column | Verdict |
| --- | --- |
| a cell | <span class="yes">yes</span> |
| another | <span class="no">no</span> |
| a third | <span class="partial">partial</span> |

---

<!-- lwp:slide:full-article -->
slug: c5
article: a_article.md
"""

_LONG = """# The article's own title

Body prose in the long-form piece, with a [link](https://example.org)
and a **bold run**.

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

A paragraph with a footnote call.[^1]

[^1]: The footnote text, which is apparatus.

<div class="refs">

A reference line, the apparatus block at the foot of the article.

</div>
"""

# Every built-in theme. The counter defect showed on 15 of 34, so a
# sample of five would have had a real chance of missing it.
def _all_theme_slugs():
    # From the tool, not from a list restated here: a catalogue that grows
    # must widen this sweep without anyone remembering to.
    result = subprocess.run(
        ['python3', str(LWP), 'theme', 'show', '--all', '--format', 'json'],
        capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return []
    return sorted(entry['target']['theme']
                  for entry in json.loads(result.stdout))


THEMES = _all_theme_slugs()


# The sweep used to be ONE class over every theme: one setUpClass, 57
# themes, each theme a `theme set` + `build` + two browser probes in
# sequence — 155 s of wall-clock measured on this machine, during which
# the other workers sat idle. Nothing about it had to be sequential:
# each theme's pipeline is independent (its own build, its own probes),
# and the results land in dicts keyed by theme.
#
# So the sweep is now SHARDED BY THEME, three classes, each owning about
# a third of the catalogue, each with its own setUpClass — and the test
# runner's pool hands the three classes to three different workers.
# The assertions are unchanged and still run over every theme; only the
# theme each instance measures differs. THEMES is kept whole: the
# catalogue is a property of the program, and the shards are a property
# of the machine running the tests.
#
# The shard is by ROUND-ROBIN over the sorted slugs, not by contiguous
# slices: the AA-reporting themes are a minority scattered through the
# alphabetical order, and contiguous slices could hand one class all of
# them (the AA contract test below would have nothing to check) or none
# (nothing to test its verdict against). Round-robin spreads them.
def _theme_shards(n):
    return [[t for i, t in enumerate(THEMES) if i % n == k] for k in range(n)]


class _ContrastSweep:
    """The probe suite, theme-agnostic. A concrete class below names its
    own theme shard and inherits the tests — which read `cls.themes`,
    never the whole catalogue. Not a TestCase itself, so the runner
    never discovers it empty."""
    measured = {}
    stamp = {}
    levels = {}
    themes = ()

    @classmethod
    def setUpClass(cls):
        assert cls.themes, cls.__name__ + ': no themes in this shard'
        # Fresh dicts per CLASS, not inherited ones: the mixin's empty
        # dicts are shared, and filling them with [] would make every
        # shard's measurements leak into the other two.
        cls.measured = {}
        cls.stamp = {}
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name) / 'series'
        (root / 'articles').mkdir(parents=True)
        (root / 'templates').mkdir()
        (root / 'templates' / 'custom.css').write_text(
            _CUSTOM_CSS, encoding='utf-8')
        (root / 'series.json').write_text(json.dumps({
            'series_meta': {'title': 'Contrast probe series',
                            'author': 'Probe author',
                            'license': 'Probe licence line.'},
            'articles': [{'page_dest': 'a.html', 'page_source': 'a.md',
                          'nav_title': 'A', 'nav_desc': 'A'}]}),
            encoding='utf-8')
        (root / 'articles' / 'a.md').write_text(_ARTICLE, encoding='utf-8')
        (root / 'articles' / 'a_article.md').write_text(_LONG, encoding='utf-8')
        for theme in cls.themes:
            settheme = subprocess.run(
                ['python3', str(LWP), 'series', 'theme', 'set', str(root),
                 '--theme', theme],
                capture_output=True, text=True, timeout=60)
            assert settheme.returncode == 0, settheme.stdout + settheme.stderr
            out = Path(cls.tmpdir.name) / ('public-' + theme)
            build = subprocess.run(
                # --build-stamp so the marker is on the page and swept
                # like everything else. It paints text and had no property
                # in the registry, which is the exact blind spot this
                # instrument exists for: it hard-coded a grey at 0.75
                # opacity and cleared 4.5:1 on none of the 57 themes,
                # bottoming out at 1.27:1 on pop-red, and was reported as
                # invisible by someone who used it.
                ['python3', str(LWP), 'build', str(root), '--output', str(out),
                 '--slides-page-numbers', 'yes', '--build-stamp'],
                capture_output=True, text=True, timeout=60)
            assert build.returncode == 0, build.stdout + build.stderr
            run = subprocess.run(
                ['node', str(SCRIPT), (out / 'a.html').as_uri()],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
            assert run.returncode == 0, run.stdout + run.stderr
            cls.measured[theme] = json.loads(run.stdout)
            # Second instrument, same builds: the stamp is an OVERLAY, and
            # the walk above takes its ground from its ancestors. See
            # build_stamp_e2e.cjs -- an ancestor walk cannot see the card
            # painted under a sibling, and read the stamp as legible on
            # the very page where it was painting its own colour.
            cls.stamp[theme] = {}
            for page in ('a.html', 'index.html'):
                probe = subprocess.run(
                    ['node', str(STAMP_SCRIPT), (out / page).as_uri()],
                    capture_output=True, text=True, timeout=120,
                    env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
                assert probe.returncode == 0, probe.stdout + probe.stderr
                cls.stamp[theme][page] = json.loads(probe.stdout)
        # The registry's own verdict per theme -- the contract the page is
        # held to, read from the tool rather than restated here.
        info = subprocess.run(
            ['python3', str(LWP), 'theme', 'show', '--all', '--format', 'json'],
            capture_output=True, text=True, timeout=120)
        assert info.returncode == 0, info.stderr
        cls.levels = {e['target']['theme']: e['accessibility']['body_text']['level']
                      for e in json.loads(info.stdout)}

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_the_probe_measured_a_real_page(self):
        """An empty measurement makes everything below vacuous, and a
        thin one nearly so: the first fixture this instrument ran against
        offered ten elements and every theme passed it."""
        self.assertGreaterEqual(len(THEMES), 30,
                                'the theme catalogue was not read')
        self.assertEqual(sorted(self.measured), sorted(self.themes))
        for theme, m in self.measured.items():
            self.assertGreater(
                m['measured'], 25,
                f'{theme}: the probe page painted almost no text — the '
                f'measurement, not the design, is what failed')
        # The author-defined variant is on the page and was measured. It
        # is the one case the registry report cannot reach, so a fixture
        # that quietly stopped producing it would leave that case
        # uncovered while looking covered.
        #
        # Checked by its GROUND, not by its class: the variant class sits
        # on `.fact-box`, which paints no text of its own, so it never
        # appears in a signature. #FFF3CD arriving as a measured ground is
        # proof that custom.css reached the page AND that the walk
        # composited a colour down from an ancestor.
        for theme, m in self.measured.items():
            self.assertTrue(
                any(r['onGround'] == [255, 243, 205] for r in m['results']),
                f'{theme}: nothing was measured on the ground the author '
                f'defined -- the variant did not reach the page')

    def test_the_build_stamp_is_on_the_page_and_was_measured(self):
        """Non-vacuity for the stamp, which the AA test below then holds
        to the same 4.5:1 as everything else.

        Without this, dropping `--build-stamp` from the build command
        above would leave the sweep green while measuring nothing: the
        marker would simply not be there. That is how it went unmeasured
        for its whole life -- an element the registry has no property for,
        on a page nothing built with the flag."""
        for theme, m in self.measured.items():
            stamp = [r for r in m['results'] if r['sig'] == 'div.build-stamp']
            self.assertTrue(
                stamp, f'{theme}: the build stamp was not measured -- the '
                       f'page was not built with --build-stamp, or the '
                       f'marker stopped being emitted')
        for theme, pages in self.stamp.items():
            for page, m in pages.items():
                self.assertTrue(m['found'],
                                f'{theme}/{page}: no build stamp on the page')
                self.assertTrue(
                    m['sample'].startswith('Compiled'),
                    f"{theme}/{page}: the stamp says {m['sample']!r}")

    def test_the_build_stamp_can_be_read_where_it_is_painted(self):
        """The report, and the defect that produced it: "le stamp est
        invisible".

        Measured against what the PAINTER put under it, not against its
        ancestors -- see build_stamp_e2e.cjs. The stamp is an overlay, so
        the two answers differ, and on the page as it shipped they
        differed by everything: the ancestor walk called it legible while
        the painter had it at 1.00:1.

        Every theme, both pages, at the 4.5:1 the marker's 11px asks for,
        with no exemption. This is not the theme contract of the test
        below -- a theme is allowed to report `fail` for its own body text
        -- because the stamp's ink is not a theme choice: it inherits
        whatever the card gives it, and a stamp that cannot be read is the
        tool's defect on every theme alike."""
        self.assertTrue(self.stamp, 'nothing was measured')
        failures = []
        for theme in sorted(self.stamp):
            for page, m in sorted(self.stamp[theme].items()):
                if m['ratio'] < m['threshold']:
                    failures.append(
                        f"{theme}/{page}: {m['ratio']}:1 needs "
                        f"{m['threshold']} ({m['size']}px weight "
                        f"{m['weight']}), ink {m['ink']} on ground "
                        f"{m['ground']}, painted over {m['under']!r}")
        self.assertEqual(
            failures, [],
            'the build stamp cannot be read where it is painted:\n  '
            + '\n  '.join(failures))

    def test_the_instrument_sees_through_a_gradient(self):
        """The cover's ground is a gradient, and a gradient's
        `backgroundColor` is transparent. An instrument that reads only
        that walks past the cover onto the page behind it and reports
        1.00:1 for a legible title — which is exactly what the first
        version of this file did, on four elements, before the stops were
        read. `grounds > 1` is the evidence it looked."""
        for theme, m in self.measured.items():
            over_gradient = [r for r in m['results'] if r['grounds'] > 1]
            self.assertTrue(
                over_gradient,
                f'{theme}: nothing was measured against a gradient, so the '
                f'stop reader is not running')

    def test_a_theme_that_reports_AA_reaches_AA_on_the_page(self):
        """The contract, and the only threshold this file may enforce.

        specifications.md §11.9.1 is explicit that NOT every theme has to
        reach the high standard -- `terminal`'s phosphor halo and
        `synthwave`'s saturations are choices, and making them AAA would
        destroy them. What is required is double: all stay legible, and
        the author must KNOW which reaches which level. Thirteen themes
        report AA for body text; twenty-one report `fail`, on purpose,
        and the report is how the author knows.

        So the assertion is not "everything is AA". It is: a theme whose
        registry report says AA must actually deliver AA on the page. A
        report that says AA over a page that does not is the one outcome
        the design does not allow, because it is the report itself
        lying."""
        promised = {t for t, level in self.levels.items() if level != 'fail'}
        # The shard's share of the AA-reporting themes — the catalogue
        # itself is divided across the three sweep classes, and a theme
        # outside this shard has no measurement here to be held to.
        promised &= set(self.themes)
        self.assertGreater(len(promised), 5,
                           'no theme claims AA -- the report was not read')
        failures = []
        for theme in sorted(promised):
            for r in self.measured[theme]['results']:
                if r['ratio'] < r['threshold']:
                    failures.append(
                        f"{theme} (reports {self.levels[theme]}): {r['sig']} "
                        f"{r['ratio']}:1 needs {r['threshold']} "
                        f"({r['size']}px weight {r['weight']}) {r['sample']!r}")
        self.assertEqual(
            failures, [],
            'themes whose report promises AA and whose page does not '
            'deliver it:\n  ' + '\n  '.join(failures))

    def test_the_registry_report_is_not_optimistic_about_the_page(self):
        """A theme reported `fail` is allowed to fail -- but the page must
        not be WORSE than the report says. The report names its own worst
        pair; the page's worst rendered ratio is recorded beside it, and a
        page materially below the report means the registry is measuring
        something the browser does not paint.

        Recorded, not policed at a fixed number: the two measure
        overlapping but different sets (the report covers pairs no probe
        page instantiates, the page covers elements with no property at
        all), so an exact match would be a coincidence, not a contract."""
        report = []
        for theme in sorted(self.measured):
            worst = min((r['ratio'] for r in self.measured[theme]['results']),
                        default=None)
            report.append((theme, self.levels[theme], worst))
        # Nothing anywhere is INVISIBLE. 1.5:1 is far below AA and far
        # below the "stays legible" floor the spec asks of every theme;
        # it is here to catch the class of defect that produced 1.00:1 on
        # fifteen themes, not to relitigate the AA decision.
        invisible = [(t, lvl, w) for t, lvl, w in report if w is not None and w < 1.5]
        self.assertEqual(
            invisible, [],
            'text at or near its own ground -- not a near miss, '
            f'invisible: {invisible}')

    def test_a_careless_author_variant_is_caught_here_and_nowhere_else(self):
        """The blind spot, demonstrated rather than asserted in the
        abstract.

        A variant is a ground the author paints and the registry has
        never heard of, so `theme show` cannot say a word about the text
        on it. Build the same page with a variant that recolours the body
        and forgets the label -- an ordinary omission -- and the label
        keeps the theme's ink over a colour the theme has never seen.

        Measured: it lands below AA on twelve of the thirteen themes that
        report AA. This is what instrument 2 is FOR; the careful variant
        in the main fixture is what a correct one looks like."""
        promised = sorted(t for t, level in self.levels.items()
                          if level != 'fail')[:3]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            (root / 'articles').mkdir(parents=True)
            (root / 'templates').mkdir()
            (root / 'templates' / 'custom.css').write_text(
                _CARELESS_CSS, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
            (root / 'articles' / 'a.md').write_text(_ARTICLE, encoding='utf-8')
            (root / 'articles' / 'a_article.md').write_text(
                _LONG, encoding='utf-8')
            caught = []
            for theme in promised:
                subprocess.run(
                    ['python3', str(LWP), 'series', 'theme', 'set', str(root),
                     '--theme', theme], capture_output=True, timeout=60)
                out = Path(tmp) / ('public-' + theme)
                subprocess.run(
                    ['python3', str(LWP), 'build', str(root),
                     '--output', str(out)],
                    capture_output=True, text=True, timeout=60)
                run = subprocess.run(
                    ['node', str(SCRIPT), (out / 'a.html').as_uri()],
                    capture_output=True, text=True, timeout=120,
                    env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
                self.assertEqual(run.returncode, 0, run.stderr)
                results = json.loads(run.stdout)['results']
                on_variant = [r for r in results
                              if r['onGround'] == [255, 243, 205]]
                self.assertTrue(on_variant,
                                f'{theme}: the careless variant did not paint')
                if any(r['ratio'] < r['threshold'] for r in on_variant):
                    caught.append(theme)
            self.assertEqual(
                sorted(caught), promised,
                'the instrument did not see a careless author variant on '
                f'{sorted(set(promised) - set(caught))} -- which is the one '
                f'thing the registry report cannot see either')


# The three shards of the theme sweep. Same tests, third of the
# catalogue each; the runner's pool runs them on three workers. The
# shard classes are deliberately trivial — the split is load, not
# semantics — so their names say only where each one starts.
@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class EveryLineOnAPageCanBeReadA(_ContrastSweep, unittest.TestCase):
    """Themes 0, 3, 6, ... of the sorted catalogue."""
    themes = _theme_shards(3)[0]


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class EveryLineOnAPageCanBeReadB(_ContrastSweep, unittest.TestCase):
    """Themes 1, 4, 7, ... of the sorted catalogue."""
    themes = _theme_shards(3)[1]


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class EveryLineOnAPageCanBeReadC(_ContrastSweep, unittest.TestCase):
    """Themes 2, 5, 8, ... of the sorted catalogue."""
    themes = _theme_shards(3)[2]
