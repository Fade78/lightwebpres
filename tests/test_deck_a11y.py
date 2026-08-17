"""Three promises a built deck makes that nothing measured.

Each was found by rendering a page and looking, and each had passed every
existing test because the existing tests read the stylesheet rather than
the result:

  - The slide-variant dialog carried `role="dialog"` and real buttons and
    could not be reached by keyboard at all. Five Tab presses left the
    focus on BODY, so the whole feature was mouse-only (WCAG 2.1.1).
  - The speaker counter measured EXACTLY 1.00:1 against its own ground on
    15 of the 34 built-in themes: `background: none` let the cover's
    gradient through, and on a light theme the page ink and the gradient's
    first stop are both `color.ink`, so the counter's ink WAS its ground.
    `theme show`'s contrast report cannot see this — the element has no
    registry property for it to read.
  - Print promised one slide per sheet and delivered one extra sheet on
    every page ever built: `.slide:last-child` matched nothing, because a
    <footer> and a <script> follow the last slide.

All three are measured on the rendered page, deliberately. A string check
on the emitted CSS would have called the print rule fine — the rule was
present and correct and simply selected nothing.

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
SCRIPT = Path(__file__).resolve().parent / 'deck_a11y_e2e.cjs'

# Light themes where the counter measured 1.00:1. `high-contrast` is the
# worst case and the one a reader with low vision would actually pick.
THEMES = ('high-contrast', 'newsprint', 'vaporwave', 'nord', 'terminal')


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

_ARTICLE = """<!-- lwp:meta -->
page_dest: a.html
page_title: Deck probe
nav_title: A
nav_desc: A
---

<!-- lwp:slide:cover -->
kicker: PROBE
# Deck probe
summary: A cover, whose gradient is what the counter sits on.
note: THE-SPEAKER-NOTE-MARKER, which only the presenter panel may show.

---

<!-- lwp:slide -->
tags: alpha
kicker: ALPHA
## A card tagged alpha
summary: Two distinct tags, so the variant menu has something to offer.

---

<!-- lwp:slide -->
tags: beta
kicker: BETA
## A card tagged beta
summary: The second tag.
"""


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class ADeckIsUsableWithoutAMouse(unittest.TestCase):

    measured = {}

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name) / 'series'
        (root / 'articles').mkdir(parents=True)
        # `series theme set` writes templates/settings.conf and needs the
        # directory to exist.
        (root / 'templates').mkdir()
        # series_meta gives the page a real footer. Without one there is
        # nothing to spill onto the extra sheet a forced break creates, so
        # the print defect hides: the probe must carry the thing that made
        # it visible, or the test passes against the bug.
        (root / 'series.json').write_text(json.dumps({
            'series_meta': {'title': 'Deck probe series',
                            'author': 'Probe author',
                            'license': 'Probe licence line.'},
            'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
        (root / 'articles' / 'a.md').write_text(_ARTICLE, encoding='utf-8')
        for theme in THEMES:
            out = Path(cls.tmpdir.name) / ('public-' + theme)
            # The theme is APPLIED to the series and then built, because
            # `build` takes no --theme. This used to pass `--theme` to
            # build and fall back to a plain build when that failed --
            # which it always did, so all five names measured the default
            # theme and the counter test covered one theme while reporting
            # five. A fallback that quietly measures something else is
            # exactly the failure this file was written to name.
            settheme = subprocess.run(
                ['python3', str(LWP), 'series', 'theme', 'set', str(root),
                 '--theme', theme],
                capture_output=True, text=True, timeout=60)
            assert settheme.returncode == 0, settheme.stdout + settheme.stderr
            # --slides-page-numbers: the engraved number is off by default
            # and its alignment is one of the things measured below.
            build = subprocess.run(
                ['python3', str(LWP), 'build', str(root),
                 '--output', str(out), '--slides-page-numbers', 'yes'],
                capture_output=True, text=True, timeout=60)
            assert build.returncode == 0, build.stdout + build.stderr
            run = subprocess.run(
                ['node', str(SCRIPT), (out / 'a.html').as_uri()],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON})
            assert run.returncode == 0, run.stdout + run.stderr
            cls.measured[theme] = json.loads(run.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_the_probe_measured_every_theme(self):
        """An empty measurement makes everything below vacuous. So does a
        measurement of the same theme five times, which is what this
        fixture did for as long as it passed `--theme` to a command that
        does not take it and fell back to a plain build. The grounds have
        to be DISTINCT, or the counter test reports five themes and covers
        one."""
        self.assertEqual(sorted(self.measured), sorted(THEMES))
        for theme, m in self.measured.items():
            self.assertTrue(m['menuOpens'], f'{theme}: no variant menu to test')
            self.assertGreater(m['slideCount'], 1, theme)
        grounds = {theme: tuple(m['counter']['bg'])
                   for theme, m in self.measured.items()}
        self.assertEqual(
            len(set(grounds.values())), len(THEMES),
            f'themes sharing a ground -- the theme was not applied: {grounds}')

    def test_the_variant_dialog_takes_focus_and_keeps_it(self):
        """Focus must move IN on open, stay in across Tab and Shift+Tab,
        and come back to the button that opened it. It did none of the
        three: the global keydown handler preventDefault()s every key
        whose target is not already inside .tag-menu, and a prevented Tab
        cancels the focus move, so focus could never get in to begin
        with."""
        m = self.measured['high-contrast']
        self.assertTrue(m['focusOnOpen']['inMenu'],
                        f"focus landed on {m['focusOnOpen']['tag']}, "
                        f"not inside the dialog")
        self.assertIn('tag-option', m['focusOnOpen']['tag'])
        self.assertTrue(m['focusStaysInMenu'],
                        'Tab walked out of an open modal dialog')
        self.assertTrue(m['menuClosesOnEnter'], 'Enter did not apply and close')
        self.assertIn('nav-btn', m['focusReturnedTo'],
                      f"focus was left on {m['focusReturnedTo']} rather than "
                      f"returned to the control that opened the dialog")
        self.assertTrue(m['menuClosesOnEscape'])

    def test_the_speaker_counter_is_legible_on_its_own_ground(self):
        """1.00:1 is not a near miss, it is invisible. AA for text this
        small is 4.5:1; the fix takes it to the page's own ink-on-ground,
        which every theme is already designed around."""
        for theme, m in self.measured.items():
            self.assertIsNotNone(
                m['counterContrast'],
                f'{theme}: the counter has no background of its own, so '
                f'whatever is behind it decides whether it can be read '
                f'(raw: {m["counter"]["bgRaw"] if m["counter"] else None})')
            self.assertGreaterEqual(
                m['counterContrast'], 4.5,
                f'{theme}: counter contrast {m["counterContrast"]:.2f}:1')

    def test_the_presenter_panel_reads_the_speaker_note(self):
        """`note:` exists so a speaker can see something the audience
        cannot, and the panel is the only place it surfaces. Nothing
        checked that it ever gets there: the Python tests prove the note
        is emitted hidden and stays invisible on the card -- both true,
        both satisfied by a panel that never reads it. Mutating the read
        to a literal dash left the whole suite green."""
        # The note sits on the COVER, which is the current slide at load.
        # The panel shows the CURRENT slide's note, so putting it anywhere
        # else would measure the navigation rather than the panel -- and a
        # dash would be the correct answer.
        m = self.measured['high-contrast']
        self.assertTrue(m['presenter']['open'],
                        'the N key did not open the presenter panel')
        self.assertIn('THE-SPEAKER-NOTE-MARKER', m['presenter']['notes'],
                      f'the panel shows {m["presenter"]["notes"]!r} instead '
                      f'of the slide\'s note')

    def test_the_presenter_panel_is_reachable_and_announces(self):
        """The panel is a labelled, scrollable, live region.

        It had none of that: no role, no label, no aria-live, and no way
        into it from the keyboard. `overflow: auto` with `max-height: 44vh`
        makes it scrollable, and a scrollable region that cannot take
        focus cannot be scrolled without a mouse (WCAG 2.1.1) -- on the one
        panel whose whole purpose is a note too long to fit.

        Escape reached every other overlay on the page and not this one."""
        p = self.measured['high-contrast']['presenter']
        self.assertEqual(p['role'], 'region',
                         'the panel is an unnamed div to a screen reader')
        self.assertTrue(p['label'], 'a region with no accessible name')
        self.assertEqual(p['tabindex'], '0',
                         'a scrollable panel that cannot take focus')
        self.assertEqual(p['live'], 'polite',
                         'the note changes with the slide and says nothing')
        self.assertTrue(p['closesOnEscape'],
                        'Escape closes every other overlay and not this one')

    def test_the_navigation_glyph_stays_inside_its_own_button(self):
        """`nav-btn.size` is a theme property and grows with the screen;
        the button was 44x44 at every width. Measured at 3840 the glyph
        was 54px inside a 44px circle -- 10px of it outside the shape it
        is centred in. The home glyph, stated flat at 17px, was 3.2x
        smaller than its neighbours on the same screen."""
        w = self.measured['high-contrast']['wide']
        self.assertIsNotNone(w['navBtnBox'], 'no navigation button rendered')
        self.assertGreater(w['navBtnBox'], w['navBtnGlyph'],
                           f"a {w['navBtnGlyph']}px glyph in a "
                           f"{w['navBtnBox']}px button")
        # The house glyph is smaller than the arrows on purpose -- but by a
        # ratio, not by standing still while they grow.
        self.assertGreater(
            w['navHomeGlyph'], 0.5 * w['navBtnGlyph'],
            f"the home glyph is "
            f"{w['navBtnGlyph'] / w['navHomeGlyph']:.1f}x smaller than "
            f"its neighbours")
        self.assertLess(w['navHomeGlyph'], w['navBtnGlyph'])

    def test_the_slide_number_sits_over_the_column_not_the_card(self):
        """`right: 32px` measured the number from the CARD edge while every
        line of text starts at the padding the card computes from
        --page-content-max. Measured, the number's right edge was 275px
        past the column's at 3840 and 122px at 1920, and the sign inverted
        on a phone -- so the one width where it looked right was the one
        nobody presents on."""
        w = self.measured['high-contrast']['wide']
        self.assertIsNotNone(w['numRight'],
                             'the probe built no slide number to measure')
        self.assertAlmostEqual(
            w['numRight'], w['columnRight'], delta=1.0,
            msg=f"the number is {w['numRight'] - w['columnRight']:.0f}px "
                f"off the column's right edge")

    def test_the_panel_a_speaker_reads_grows_with_the_screen(self):
        """15.2px at 375 and 15.2px at 3840, measured: the panel's three
        children are all `em` of a body that never grew, so the one part of
        the page written FOR the person running the deck was the flattest
        thing on it."""
        w = self.measured['high-contrast']['wide']
        self.assertGreater(w['panelNote'], 16.0,
                           f'the speaker note is {w["panelNote"]}px on a '
                           f'3840px screen')

    def test_one_slide_prints_on_one_sheet(self):
        """Counts pages in a real PDF, not the presence of a CSS rule.
        The rule was present, correct, and selected nothing."""
        for theme, m in self.measured.items():
            self.assertEqual(
                m['pdfPages'], m['slideCount'],
                f'{theme}: {m["slideCount"]} slides printed '
                f'{m["pdfPages"]} sheets')
