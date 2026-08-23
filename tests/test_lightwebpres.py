"""Regression test battery for the lightwebpres executable.

Black box: each test runs `lightwebpres` as a subprocess against a
throwaway series (tempfile) and checks the exit code / generated HTML.
No test depends on the private/ directory (not versioned) — every series
used here is a minimal fixture invented for the occasion.

Tests marked @unittest.expectedFailure document known bugs (see the fix
list): the suite stays green as long as they are not fixed. Once a bug is
fixed, removing the decorator "graduates" the test into a normal
regression that must never break again.

Run with: python3 tests/run_tests.py
"""

import time
import base64
import ast
import contextlib
import io
import json
import os
import inspect
import re
import shlex
import shutil
import subprocess
from html import escape as html_escape
import sys
import tempfile
import unittest
from pathlib import Path

EXECUTABLE = Path(__file__).resolve().parent.parent / 'lightwebpres'


def run(*args, cwd=None, env=None):
    """Runs lightwebpres <args> and returns the CompletedProcess."""
    full_env = {**os.environ, **env} if env else None
    return subprocess.run(
        [sys.executable, str(EXECUTABLE), *args],
        capture_output=True, text=True, cwd=cwd, env=full_env,
    )


def contrast_ratio(hex_a, hex_b):
    """WCAG relative-luminance contrast between two sRGB hex colours.

    Used to assert that a palette choice is legible rather than merely
    present — "the variable is set" has passed several times over a
    result nobody could actually read."""
    def luminance(value):
        channels = [int(value.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                    for c in channels]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    lighter, darker = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def scaffold(tmp, article_md, series_extra=None, source_name='a.md', file_name='a.html'):
    """Creates a minimal single-article series and returns its path."""
    root = Path(tmp)
    (root / 'sources').mkdir(parents=True, exist_ok=True)
    (root / 'sources' / source_name).write_text(article_md, encoding='utf-8')
    entry = {'page_dest': file_name, 'page_source': source_name, 'nav_title': 'A', 'nav_desc': 'A'}
    if series_extra:
        entry.update(series_extra)
    (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
    return root


class BuildGoldenPath(unittest.TestCase):
    """Behaviors that already work — must never regress."""

    def test_build_smoke(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k1\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())
            self.assertTrue((root / 'public' / 'index.html').exists())

    def test_check_reports_no_drift_after_build(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k2\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('up to date', result.stdout)

    def test_install_refuses_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'dummy.txt').write_text('x', encoding='utf-8')
            result = run('init', str(root))
            self.assertNotEqual(result.returncode, 0)

    def test_typography_nbsp_before_double_punctuation(self):
        # This one intentionally uses French content: it tests the French
        # typography engine's own rule (nbsp before "?").
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k3\nkicker: T\n# Titre\nsummary: Une question ?\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('question\xa0?', html)


class SlideTags(unittest.TestCase):
    """`tags:` is the article's variant axis: validated at build time,
    compacted before numbering, and exposed to the page runtime."""

    def _tagged_article(self):
        return (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Tags\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k4\nkicker: Shared\n# Shared\n'
            'summary: Common content.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k5\ntags: EN Français_v2\n'
            'kicker: English\n## Variant\nsummary: Variant content.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k6\ntags: excluded\n## Removed\n'
            'summary: This must never be emitted.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k7\ntags: EXCLUDED\n'
        )

    def test_tags_are_canonicalized_default_is_added_and_excluded_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._tagged_article())
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')

        self.assertIn('data-tags="default"', html)
        self.assertIn('data-tags="en français_v2"', html)
        self.assertNotIn('This must never be emitted', html)
        self.assertNotIn('Removed', html)
        self.assertNotIn('data-tags="excluded"', html)
        # The ids are what the fixture declares, not ranks: `s1` was an
        # identity while a card's id WAS its rank, and nothing derives
        # one any more.
        # The ids are what the fixture declares, not ranks: `s1` was an
        # identity while a card's id WAS its rank, and nothing derives one
        # any more. k6 and k7 are the two `excluded` cards — they produce
        # no section at all, which is the point of the assertion.
        self.assertIn('id="k4"', html)
        self.assertIn('id="k5"', html)
        self.assertNotIn('id="k6"', html)
        self.assertNotIn('id="k7"', html)

    def test_excluded_invalid_full_article_is_not_compiled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._tagged_article())
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_tag_is_fatal(self):
        for value in ('_internal', 'has/slash'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                root = scaffold(tmp, self._tagged_article().replace(
                    'tags: EN Français_v2', f'tags: {value}'))
                result = run('build', str(root), '--output', str(root / 'public'))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('invalid tag', result.stderr)

    def test_runtime_menu_and_filter_use_visible_slide_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._tagged_article())
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')

        for fragment in (
                'id="navTags"', 'id="tagMenu"', 'id="tagMenuList"',
                'var allSlides', 'var selectedTag', 'localStorage',
                'slides = allSlides.filter', "e.key === 'l' || e.key === 'L'",
                'data-tags="default"'):
            self.assertIn(fragment, html, fragment)

    def test_generated_css_hides_filtered_slides_and_tag_button(self):
        """The runtime filter sets slide.hidden; an author-origin
        .slide { display: flex } beats the UA rule [hidden] { display:
        none }, so the skeleton must carry its own override — the same
        defeat the themes gallery once had for .theme-row, and the same
        fix."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._tagged_article())
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')

        self.assertIn('.slide[hidden], .nav-btn[hidden] { display: none; }',
                      html)

    def test_lang_tag_selects_a_different_typography_pack_per_slide(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Tags\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k8\n# Cover\nsummary: English.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k9\ntags: EN\n## English\nsummary: English.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data = {'series_meta': {'lang_tags': {'EN': 'en'}},
                    'articles': data['articles']}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            (root / 'language').mkdir()
            (root / 'language' / 'en.json').write_text(json.dumps({
                'rules': [{'name': 'marker', 'pattern': 'English',
                           'replacement': 'ENGLISH'}],
            }), encoding='utf-8')
            result = run('build', str(root), '--lang', 'fr',
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')

        self.assertIn('<p class="summary">English.</p>', html)
        self.assertIn('<p class="summary">ENGLISH.</p>', html)


class ParagraphHandling(unittest.TestCase):
    """Spec §4.1/§6.1: one line = one field, but real Markdown paragraphs
    (separated by a blank line) must be respected, and a paragraph broken
    without a blank line must be re-joined."""

    def test_two_real_paragraphs_in_factbox_stay_separate(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k10\nkicker: T\n## Title\nfact-label: The fact\n'
            'First paragraph.\n\nSecond paragraph, clearly distinct.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="fact-content">', html)
            self.assertIn('<p>First paragraph.</p>', html)
            self.assertIn('<p>Second paragraph, clearly distinct.</p>', html)

    def test_hardwrap_without_blank_line_is_joined_into_one_paragraph(self):
        # Standard Markdown rule (spec §6.1): consecutive lines with no
        # blank line between them merge into a single paragraph.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k11\nkicker: T\n## Title\nfact-label: The fact\n'
            'A sentence broken\nby mistake across two physical lines.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn(
                '<p>A sentence broken by mistake across two physical lines.</p>',
                html,
            )


class FatalErrorCases(unittest.TestCase):
    """Spec §22: cases that must make the build fail (non-zero exit code),
    not produce a corrupted or silently wrong result."""

    def test_full_article_missing_article_field_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k12\nkicker: T\n## Title\nContent.\n\n---\n\n<!-- lwp:slide:full-article -->\nslug: k13\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_help_states_the_cardinality_the_build_actually_enforces(self):
        """The behaviour below was fixed, tested, and written up in the
        specification (§22.8) — and every surface a user reads went on
        saying the opposite for releases afterwards. `--help` was the
        worst of them, because its slide-type text comes from SLIDE_TYPES,
        the table whose own comment calls it "the only place that list is
        written": the one description that cannot be dismissed as a stale
        copy said `at most one such slide per article` while the build
        rendered two quite happily.

        Asserted in both directions, because a limit dropped from the text
        is as wrong as one invented in it — and asserted on the table AND
        on the rendered help, since a summary that is right in the table
        and never printed would leave the reader exactly where they were.
        `test_duplicate_series_nav_slides_is_fatal` above is the
        behavioural half for series-nav; the one below is full-article's."""
        types = {t.name: t.summary
                 for t in load_lightwebpres_module().SLIDE_TYPES}
        limit_words = ('at most one', 'only one', '0 or 1', 'a single')
        text = run('--help').stdout

        for word in limit_words:
            self.assertNotIn(
                word, types['full-article'].lower(),
                f'SLIDE_TYPES limits how many full-article slides a page may '
                f'carry ({word!r}); the build does not (§22.8)')
        self.assertTrue(
            any(word in types['series-nav'].lower() for word in limit_words),
            'SLIDE_TYPES does not say a page carries one series-nav, and the '
            'build refuses a second one fatally — an author meets that error '
            'with nothing to have warned them')

        # And the help really is that table talking. Compared on the first
        # sentence: --help re-wraps, so the whole summary never survives
        # as one line.
        for name, summary in types.items():
            first = summary.split('. ')[0]
            self.assertIn(' '.join(first.split()), ' '.join(text.split()),
                          f'--help does not print SLIDE_TYPES\' summary for '
                          f'{name}, so the table can be right and the help wrong')

    def test_two_full_article_slides_each_carry_their_own_file(self):
        """A page may hold more than one long-form piece. It could not,
        and the reason was never a rule about the format: the renderer
        wrote ONE shared placeholder and substituted it globally, so the
        first article landed in every slot and the rest were dropped in
        silence. That is what the old fatal error was guarding.

        The failure it guarded against is the assertion here — CONTENT ONE
        exactly once, CONTENT TWO exactly once, and no marker left in the
        page. Duplicating the first over the second passes a test that
        only asks whether both strings appear."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k14\narticle: art1.md\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k15\narticle: art2.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art1.md').write_text('CONTENT ONE\n', encoding='utf-8')
            (root / 'sources' / 'art2.md').write_text('CONTENT TWO\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertEqual(html.count('CONTENT ONE'), 1, html.count('CONTENT ONE'))
            self.assertEqual(html.count('CONTENT TWO'), 1, html.count('CONTENT TWO'))
            self.assertNotIn('FULL_ARTICLE_PLACEHOLDER', html)
            self.assertEqual(html.count('class="slide full-article"'), 2)

    def test_two_long_form_pieces_do_not_share_note_anchors(self):
        """The second thing that made one article per page an assumption
        rather than a rule. A note's anchor id is scoped by its locality's
        prefix precisely so two localities cannot both emit `note-1`, and
        the long-form prefix was the fixed word `article` — unique only
        while there was one of them. Two pieces each carrying a note would
        have put two `id="note-article-1"` in one document, and every
        return link would have landed on the first."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k16\narticle: art1.md\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k17\narticle: art2.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art1.md').write_text(
                'One[^a].\n\n[^a]: First body.\n', encoding='utf-8')
            (root / 'sources' / 'art2.md').write_text(
                'Two[^b].\n\n[^b]: Second body.\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            ids = re.findall(r'id="(note-[a-z0-9-]+)"', html)
            self.assertEqual(len(ids), len(set(ids)), ids)
            self.assertEqual(len(ids), 2, ids)

    def test_one_long_form_piece_keeps_the_anchors_it_always_had(self):
        """And the other side of it. The prefix is disambiguated by slide
        ONLY when the page carries several pieces, because `#note-article-3`
        is a URL someone may have been sent: moving every one of them to
        buy a uniqueness a single-article page does not need would break
        inbound links for a capability that page is not using."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k18\narticle: art1.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art1.md').write_text(
                'One[^a].\n\n[^a]: First body.\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('id="note-article-1"', html)

    def test_duplicate_series_nav_slides_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k19\n\n---\n\n<!-- lwp:slide:series-nav -->\nslug: k20\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_unknown_slide_type_is_fatal_even_when_excluded(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:bogus -->\nslug: k21\ntags: excluded\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unknown type "bogus"', result.stderr)

    def test_md_must_start_with_meta_block(self):
        md = '---\n\n<!-- lwp:slide:cover -->\nslug: k22\nkicker: T\n# Title\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_empty_md_file_is_fatal(self):
        md = '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_cover_with_unexpected_trailing_content_is_fatal(self):
        # Spec §22.12: a cover slide has no fact-box, so unexpected
        # content after its fields must be rejected, not silently dropped.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k23\nkicker: T\n# Title\nsummary: Summary.\n'
            'This text should never appear nor be silently ignored.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_series_json_rejects_duplicate_file_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k24\nkicker: T\n# Title\n'
            )
            (root / 'sources' / 'a1.md').write_text(md, encoding='utf-8')
            (root / 'sources' / 'a2.md').write_text(md, encoding='utf-8')
            series = {'articles': [
                {'page_dest': 'a.html', 'page_source': 'a1.md', 'nav_title': 'A1', 'nav_desc': 'A1'},
                {'page_dest': 'a.html', 'page_source': 'a2.md', 'nav_title': 'A2', 'nav_desc': 'A2'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)


class LanguageStrings(unittest.TestCase):
    """§7.3/§7.4: interface strings follow --lang, and a language/{lang}.json
    override only needs to define the keys it wants to change."""

    def _series(self, tmp):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k25\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        return scaffold(tmp, md)

    def test_lang_en_uses_english_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            run('build', str(root), '--lang', 'en', '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="Previous slide"', html)
            self.assertIn('title="Next slide"', html)
            self.assertIn("Copy link", html)

    def test_lang_fr_uses_french_chrome(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            run('build', str(root), '--lang', 'fr', '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="Planche précédente"', html)
            self.assertIn('title="Planche suivante"', html)
            self.assertIn('Copier le lien', html)

    def test_partial_override_falls_back_to_builtin_for_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(
                json.dumps({'lang': 'fr', 'strings': {'nav_prev': 'CUSTOM-PREV'}}),
                encoding='utf-8',
            )
            run('build', str(root), '--lang', 'fr', '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="CUSTOM-PREV"', html)
            # nav_next wasn't overridden: must fall back to the built-in French default.
            self.assertIn('title="Planche suivante"', html)

    def test_unknown_lang_without_override_falls_back_to_english(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            run('build', str(root), '--lang', 'zz', '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="Previous slide"', html)

    def test_lang_value_is_validated_before_it_reaches_markup(self):
        # A --lang value reaches <html lang="..."> and language/{lang}.json;
        # an unvalidated value could break out of the attribute. Letters,
        # digits, "-" and "_" only.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            result = run('build', str(root),
                         '--lang', 'x"><script>alert(1)</script>',
                         '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('invalid language value', result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_pack_strings_cannot_break_out_of_html_attributes(self):
        # A language pack string lands in HTML attributes (title=,
        # aria-label=) via the page template: JSON-style \" is not an HTML
        # escape, so the HTML context needs entity escaping (&quot;).
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(json.dumps({
                'strings': {'nav_prev': '"><img src=x onerror=alert(1)>'},
            }), encoding='utf-8')
            result = run('build', str(root), '--lang', 'fr',
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"',
                          html)
            self.assertNotIn('"><img src=x onerror', html)


class ResolveSlidePageNumbers(unittest.TestCase):
    """slide_page_numbers resolves per article (§3.3.5) — `resolve` must
    not reject it (it once did: the name was absent from
    _ARTICLE_LEVEL_NAMES)."""

    def test_resolve_reports_the_slide_page_numbers_cascade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('resolve', str(root), 'slide_page_numbers',
                         '--article', 'a.md')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('slide_page_numbers', result.stdout)
            self.assertIn('off', result.stdout)


class InstallForce(unittest.TestCase):

    def test_install_force_flag_overwrites_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'dummy.txt').write_text('x', encoding='utf-8')
            result = run('init', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'series.json').exists())


class AuditCommand(unittest.TestCase):
    """The audit command (§11.5): never blocking, warns about editorial
    conventions that are not respected."""

    def test_audit_clean_series_no_warnings(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k26\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No warnings', result.stdout)

    def test_audit_names_a_meta_key_nothing_reads(self):
        """The asymmetry this closes: a misspelled SLIDE field becomes free
        text and is a fatal build error naming the field, while a misspelled
        META key was accepted in total silence — no error, no warning, no
        effect — and the page shipped with a title that had fallen back.
        `audit --strict` answered "all editorial conventions are respected".

        Four cases in one fixture, because it is the pairing that matters:
        a typo near a real name gets that name offered, a key resembling
        nothing is still named but invents no suggestion, and the two keys
        that are legitimately unresolved — `comment`, a review note nothing
        reads, and the `style.*` article layer, which has its own vocabulary
        and its own fatal errors — must stay silent."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage-title: ignored\n'
            'nav_titel: also ignored\nzzz_unlike_anything: no near match\n'
            'comment: a review note\nstyle.kicker.fg: ink\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k27\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            # audit never blocks: an unrecognized key does not stop the tool
            # working, it only fails to do what its author meant (§9.5.6).
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('`page-title:` is not a meta field', result.stderr)
            self.assertIn('Did you mean `page_title:`?', result.stderr)
            self.assertIn('`nav_titel:` is not a meta field', result.stderr)
            self.assertIn('Did you mean `nav_title:`?', result.stderr)
            # named, but no suggestion invented for it
            self.assertIn('`zzz_unlike_anything:` is not a meta field',
                          result.stderr)
            zzz = next(l for l in result.stderr.splitlines()
                       if 'zzz_unlike_anything' in l)
            self.assertNotIn('Did you mean', zzz)
            # the two that are unresolved on purpose stay quiet
            self.assertNotIn('`comment:` is not a meta field', result.stderr)
            self.assertNotIn('style.kicker.fg', result.stdout)

            # and the build itself says nothing and still succeeds: the
            # warning belongs to audit, not to the build path.
            built = run('build', str(root))
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertNotIn('page-title', built.stdout)

    def test_audit_warns_when_no_cover(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k28\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stderr)

    def test_audit_warns_when_cover_not_first(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k29\nkicker: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k30\nkicker: T2\n# Cover title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('is not a cover', result.stderr)

    def test_audit_reports_bad_tags_and_missing_language_pack_without_blocking(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k31\ntags: _private xx\n# Title\n'
            'summary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data['series_meta'] = {'lang_tags': {'xx': 'missing-pack'}}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, 'audit must never block')
            self.assertIn("invalid tag '_private'", result.stderr)
            self.assertIn("points to missing language pack 'missing-pack'", result.stderr)
            self.assertIn("uses language tag 'xx'", result.stderr)

    def test_audit_names_the_scaffold_theme_drift_after_a_set_theme(self):
        """§9 rewrite: set-theme changes the theme line and leaves the
        commented values showing the OLD theme — by design, since the
        file is the author's. The remedy for that aging is to SAY it, and
        audit is where it is said: uncommenting a line would pin a value
        from a theme the series has left."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp, '--theme', 'nord').returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            clean = run('audit', tmp)
            self.assertNotIn('scaffold', clean.stdout.lower())

            self.assertEqual(run('series', 'theme', 'set', tmp, '--theme', 'evergreen').returncode, 0)
            result = run('audit', tmp)
            self.assertEqual(result.returncode, 0, 'audit must never block')
            self.assertIn("generated for theme 'nord'", result.stderr)
            self.assertIn("declares 'evergreen'", result.stderr)

    def test_audit_reports_invalid_settings_without_blocking(self):
        """A mistyped key in settings.conf is a named error at build
        time; audit surfaces the same message without failing, so the
        author hears about it before the next build does. The silent
        no-op this replaces was the most expensive failure of the CSS
        surface."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            settings.write_text(settings.read_text(encoding='utf-8')
                                + 'summary.color: #000000\n', encoding='utf-8')
            result = run('audit', tmp)
            self.assertEqual(result.returncode, 0, 'audit must never block')
            self.assertIn('summary.color', result.stderr)
            self.assertIn('unknown property', result.stderr)

    def test_audit_does_not_crash_when_series_json_omits_file(self):
        """§20.3.1: series.json needs only `source` — audit must resolve
        `file` (resolve_article_fields()) before reading entry['file'],
        not assume it's always explicitly present like pre-v0.5.0. Uses a
        cover-less article so the warning path (the one that actually
        reads entry['file']) is exercised, not just the "no warnings" one
        where it's never dereferenced."""
        md = (
            '<!-- lwp:meta -->\npage_title: Test\n---\n\n'
            '<!-- lwp:slide -->\nslug: k32\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir(parents=True)
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(
                json.dumps({'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('a.html', result.stderr)
            self.assertIn('no cover slide', result.stderr)


class HighlightField(unittest.TestCase):
    """§4.3: the highlight/highlight-caption fields (renamed from the former
    'mesure' naming) must actually render, and must be omitted when absent."""

    def test_highlight_renders_figure_and_caption(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k33\nkicker: T\n## Title\nhighlight: 42 %\n'
            'highlight-caption: the answer\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn(
                '<div class="highlight">'
                '<span class="highlight-figure">42\xa0%</span>'
                '<span class="highlight-caption">the answer</span></div>',
                html,
            )

    def test_standard_slide_without_highlight_omits_block(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k34\nkicker: T\n## Title\nsummary: No highlight here.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="highlight"', html)


_MINIMAL_MD = (
    '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
    '<!-- lwp:slide:cover -->\nslug: k35\nkicker: T\n# Title\nsummary: Summary.\n'
)


class VendoredPyodideIntegrity(unittest.TestCase):
    """Security (supply chain): web/vendor/pyodide/SHA256SUMS must stay in
    sync with the vendored runtime files, so a tampered or accidentally
    modified asset is caught in review/CI. These files run the code that
    handles a user's series and GitLab token."""

    def test_sha256sums_matches_vendored_files(self):
        import hashlib
        vendor = EXECUTABLE.parent / 'web' / 'vendor' / 'pyodide'
        sums = vendor / 'SHA256SUMS'
        if not sums.exists():
            self.skipTest('vendored Pyodide not present in this checkout')
        for line in sums.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            expected, name = line.split(None, 1)
            digest = hashlib.sha256((vendor / name).read_bytes()).hexdigest()
            self.assertEqual(digest, expected,
                             f'{name} does not match its recorded SHA-256')


class TagStripReDoS(unittest.TestCase):
    """Security: the tag-strip re.sub(r'<[^>]+>') feeding <title> and
    <meta> was quadratic on a run of '<' (200k '<' -> ~20s). Bounded now."""

    def test_long_angle_run_in_title_is_linear(self):
        import time
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: ' + ('<' * 120000) +
            '\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k36\nkicker: T\n# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            start = time.time()
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(time.time() - start, 5.0)


class JsonTypeConfusion(unittest.TestCase):
    """Security/robustness (§20.3/§19.2): a wrong-typed JSON leaf value in
    the semi-trusted series.json / language file must produce a clean
    [ERROR], never a raw Python traceback."""

    def _build_series(self, tmp, series_obj):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'sources' / 'a.md').write_text(_MINIMAL_MD, encoding='utf-8')
        (root / 'series.json').write_text(json.dumps(series_obj), encoding='utf-8')
        return run('build', str(root), '--output', str(root / 'public'))

    def test_non_string_page_source_is_clean_error(self):
        for bad in (123, True, 1.5, ['a.md'], {'x': 1}):
            with tempfile.TemporaryDirectory() as tmp:
                r = self._build_series(tmp, {'articles': [{'page_source': bad}]})
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn('Traceback', r.stderr)
                self.assertIn('[ERROR]', r.stderr)

    def test_non_string_editorial_field_is_clean_error(self):
        for field, bad in (('author', {'x': 1}), ('license', 42),
                           ('page_title', [1]), ('card_desc', {'a': 1})):
            with tempfile.TemporaryDirectory() as tmp:
                r = self._build_series(
                    tmp, {'articles': [{'page_source': 'a.md', field: bad}]})
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn('Traceback', r.stderr)

    def test_non_dict_series_meta_is_clean_error(self):
        for bad in ([], 'str', 123):
            with tempfile.TemporaryDirectory() as tmp:
                r = self._build_series(
                    tmp, {'series_meta': bad, 'articles': [{'page_source': 'a.md'}]})
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn('Traceback', r.stderr)

    def test_non_string_series_meta_leaf_is_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._build_series(
                tmp, {'series_meta': {'version': 123}, 'articles': [{'page_source': 'a.md'}]})
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('Traceback', r.stderr)

    def test_deeply_nested_json_is_clean_error_not_recursionerror(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text('[' * 100000 + ']' * 100000, encoding='utf-8')
            r = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('Traceback', r.stderr)
            self.assertIn('invalid JSON', r.stderr)

    def test_non_string_language_rule_is_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            lang = root / 'l.json'
            lang.write_text(json.dumps({'rules': [{'pattern': 123, 'replacement': 'x'}]}),
                            encoding='utf-8')
            r = run('build', str(root), '--output', str(root / 'public'),
                    '--language-file', str(lang))
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('Traceback', r.stderr)

    def test_non_string_language_string_value_is_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            lang = root / 'l.json'
            lang.write_text(json.dumps({'strings': {'nav_prev': 123}}), encoding='utf-8')
            r = run('build', str(root), '--output', str(root / 'public'),
                    '--language-file', str(lang))
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('Traceback', r.stderr)


class PlaceholderNotSubstitutedInAuthorContent(unittest.TestCase):
    """Security (§18.4): a literal template placeholder written in author
    content must stay literal — the single-pass fill must not substitute
    a {{css}}/{{js_nav}} an author typed into page_title/page_desc/a
    fact-box, which used to dump the stylesheet into the escaped
    <title>/<meta> sinks (bypassing their guard)."""

    def test_placeholder_in_title_meta_and_factbox_stays_literal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\n'
            'page_title: {{css}}TITLE\npage_desc: {{css}}DESC\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k37\nkicker: T\n## S\nfact-label: F\n'
            'Body with {{js_nav}} literal.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<title>{{css}}TITLE</title>', html)
            self.assertIn('content="{{css}}DESC"', html)
            self.assertIn('{{js_nav}}', html)
            # The real stylesheet must never be dumped into the title/meta:
            # the <title> content is exactly the literal placeholder text.
            title = html.split('<title>')[1].split('</title>')[0]
            self.assertNotIn('--color-mark', title)
            self.assertNotIn('box-sizing', title)

    def test_index_series_title_placeholder_stays_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data['series_meta'] = {'title': 'T{{cards}}X'}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('T{{cards}}X', html)


# RefreshTemplatesDuplicateMarker was retired with the customization marker
# itself: refresh-templates no longer writes author-owned files, so there is
# no marker to duplicate and no rfind/find split to defend.


class SlideCounter(unittest.TestCase):
    """The engraved top-right slide number (.slide-num) is opt-in and OFF by
    default (the live bottom-left counter already shows current/total)."""

    _MD = (
        '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
        '<!-- lwp:slide:cover -->\nslug: k38\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
        '<!-- lwp:slide -->\nslug: k39\nkicker: T\n## Two\nsummary: S.\n\n---\n\n'
        '<!-- lwp:slide -->\nslug: k40\nkicker: T\n## Three\nsummary: S.\n'
    )

    def test_num_absent_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<span class="slide-num">', html)

    def test_num_present_with_cli_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--slides-page-numbers', 'on')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<span class="slide-num">01 / 03</span>', html)
            self.assertIn('<span class="slide-num">02 / 03</span>', html)
            self.assertIn('<span class="slide-num">03 / 03</span>', html)

    def test_num_absent_with_cli_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--slides-page-numbers', 'off')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<span class="slide-num">', html)

    def test_num_present_with_front_matter(self):
        md = self._MD.replace(
            '<!-- lwp:meta -->\npage_dest: a.html\n',
            '<!-- lwp:meta -->\npage_dest: a.html\nslide_page_numbers: true\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<span class="slide-num">01 / 03</span>', html)

    def test_front_matter_off_wins_over_cli_on(self):
        md = self._MD.replace(
            '<!-- lwp:meta -->\npage_dest: a.html\n',
            '<!-- lwp:meta -->\npage_dest: a.html\nslide_page_numbers: false\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--slides-page-numbers', 'on')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<span class="slide-num">', html)

    def test_front_matter_on_wins_over_cli_off(self):
        md = self._MD.replace(
            '<!-- lwp:meta -->\npage_dest: a.html\n',
            '<!-- lwp:meta -->\npage_dest: a.html\nslide_page_numbers: true\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--slides-page-numbers', 'off')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<span class="slide-num">01 / 03</span>', html)

    def test_series_json_enables_when_no_cli_or_fm(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._MD)
            series = {'articles': [{'page_dest': 'a.html',
                                    'page_source': 'a.md',
                                    'nav_title': 'A', 'nav_desc': 'A'}],
                      'series_meta': {'slide_page_numbers': True}}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<span class="slide-num">01 / 03</span>', html)

    def test_invalid_value_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--slides-page-numbers', 'maybe')
            self.assertEqual(result.returncode, 1)
            self.assertIn('slide_page_numbers', result.stderr)


class OnlyAcceptsPageSourceForm(unittest.TestCase):
    """§11.3.1: --only matches by page_dest OR page_source — the .md form
    was documented but never exercised."""

    def test_only_with_md_name_takes_incremental_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--only', 'a.md')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Incremental build', result.stdout)
            self.assertTrue((root / 'public' / 'a.html').exists())


class CheckIncludeDrafts(unittest.TestCase):
    """§11.3/§20.6: --include-drafts applies to check too — a
    drafts-included build must be checkable with the same flag, and a
    plain check over it must report the index drift."""

    def _series_with_draft(self, tmp):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'sources' / 'a.md').write_text(_MINIMAL_MD, encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(
            _MINIMAL_MD.replace('a.html', 'b.html'), encoding='utf-8')
        (root / 'series.json').write_text(json.dumps({'articles': [
            {'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
            {'page_source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B', 'status': 'draft'},
        ]}), encoding='utf-8')
        return root

    def test_check_include_drafts_is_green_after_matching_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_draft(tmp)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--include-drafts')
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run('verify', str(root), '--output', str(root / 'public'),
                         '--include-drafts')
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn('[OK] b.html', result.stdout)

    def test_plain_check_after_drafts_build_reports_index_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_draft(tmp)
            run('build', str(root), '--output', str(root / 'public'),
                '--include-drafts')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT] index.html', result.stdout)


class LanguagePackMergeSemantics(unittest.TestCase):
    """§19.2: an override file's `rules`, when present, replaces the
    built-in rules EN BLOC ('rules': [] kills all built-in typography);
    a strings-only override keeps the built-in rules active. A silent
    regression here would change published typography for every
    override user."""

    def _build_with_pack(self, tmp, pack):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k41\nkicker: T\n# Title\nsummary: Magnifique !\n'
        )
        root = scaffold(tmp, md)
        pack_file = root / 'custom.json'
        pack_file.write_text(json.dumps(pack), encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'),
                     '--language-file', str(pack_file))
        return root, result

    def test_empty_rules_override_disables_builtin_typography(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build_with_pack(tmp, {'rules': []})
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Magnifique !', html)
            self.assertNotIn('Magnifique !', html)

    def test_strings_only_override_keeps_builtin_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build_with_pack(
                tmp, {'strings': {'nav_prev': 'Custom prev'}})
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Magnifique !', html)
            self.assertIn('Custom prev', html)


class EnglishTypographyPack(unittest.TestCase):
    """§7.5: the English pack upgrades an EXISTING normal space (U+0020) to a
    non-breaking space (U+00A0) for SI/metric units, unit words, initials and
    math operators. It never inserts a space that wasn't there. Black-box:
    build with --lang en and assert the U+00A0 reached the generated HTML."""

    def _build_en(self, tmp, body):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k42\nkicker: T\n# Title\nsummary: ' + body + '\n'
        )
        root = scaffold(tmp, md)
        result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
        self.assertEqual(result.returncode, 0, result.stderr)
        return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_en_metric_unit_space_is_non_breaking(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_en(
                tmp, 'The rover travelled 5 km and weighed 10 kg at 20 °C, 3 mL used.')
            self.assertIn('5\xa0km', html)
            self.assertIn('10\xa0kg', html)
            self.assertIn('20\xa0°C', html)
            self.assertIn('3\xa0mL', html)

    def test_en_unit_word_space_is_non_breaking(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_en(
                tmp, 'It earned 3 million and cost 5 dollars, 2 thousand sold.')
            self.assertIn('3\xa0million', html)
            self.assertIn('5\xa0dollars', html)
            self.assertIn('2\xa0thousand', html)

    def test_en_initials_bound_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_en(tmp, 'J. K. Rowling wrote the book.')
            self.assertIn('J.\xa0K. Rowling', html)

    def test_en_operator_space_is_non_breaking(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_en(
                tmp, 'The formula gives 2 × 4 and ≈ 5 results.')
            self.assertIn('2 ×\xa04', html)
            self.assertIn('≈\xa05', html)


class Axis4MarkdownGaps(unittest.TestCase):
    """Axis-4 sweep: Markdown-converter contracts that had no coverage."""

    def _html(self, body):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k43\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art.md').write_text(body, encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            assert result.returncode == 0, result.stderr
            return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_ordered_list(self):
        html = self._html('1. First step\n2. Second step\n')
        self.assertIn('<ol>', html)
        self.assertIn('<li>First step</li>', html)
        self.assertIn('<li>Second step</li>', html)

    def test_table_carries_comparison_table_class_and_structure(self):
        html = self._html('| A | B |\n|:---|---:|\n| a | b |\n')
        self.assertIn('<table class="comparison-table">', html)
        self.assertIn('<thead>', html)
        self.assertIn('<tbody>', html)
        # Alignment colons are accepted but ignored: no align/style attr
        self.assertNotIn('align=', html.split('<table')[1].split('</table>')[0])

    def test_h4_renders_as_bold_font_paragraph(self):
        html = self._html('#### Not a heading\n')
        self.assertIn('<p class="h4">Not a heading</p>', html)
        self.assertNotIn('<h4>', html)
        # Not rendered as markdown <strong> emphasis around the text
        self.assertNotIn('<strong>Not a heading</strong>', html)

    def test_relative_link_stays_literal(self):
        html = self._html('See [other](other.html) page.\n')
        self.assertIn('[other](other.html)', html)
        self.assertNotIn('<a href="other.html"', html)

    def test_hand_written_entity_is_neutralized_in_paragraph(self):
        html = self._html('A &rarr; B\n')
        self.assertIn('A &amp;rarr; B', html)

    def test_midline_escaped_gt_is_cleaned(self):
        html = self._html('a \\> b\n')
        self.assertIn('<p>a > b</p>', html)

    def test_midline_bare_gt_is_literal_no_blockquote(self):
        html = self._html('la valeur est > 10\n')
        self.assertIn('<p>la valeur est > 10</p>', html)
        self.assertNotIn('<blockquote>', html)

    def test_lone_backtick_is_literal_no_code_span(self):
        html = self._html('un backtick ` isolé\n')
        self.assertIn('un backtick ` isolé', html)
        self.assertNotIn('<code>', html)

    def test_indented_heading_and_list_are_plain_paragraphs(self):
        html = self._html('  # Indented\n\n  - item\n')
        self.assertIn('<p>  # Indented</p>', html)
        self.assertIn('<p>  - item</p>', html)
        self.assertNotIn('<h1>Indented</h1>', html)
        self.assertNotIn('<li>', html)


class Axis4CommandGaps(unittest.TestCase):
    """Axis-4 sweep: command contracts that had no coverage."""

    def test_lwp_lang_env_var_selects_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         env={'LWP_LANG': 'en'})
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Read the article', html)

    def test_html_lang_attribute_follows_lang(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<html lang="en">', html)

    def test_help_lists_every_command(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0)
        # The new canonical names must appear in --help.
        for command in ('init', 'demo', 'build', 'verify', 'audit',
                        'template update', 'theme list', 'theme show',
                        'theme gallery', 'status', 'series theme set'):
            self.assertIn(command, result.stdout,
                           f'--help does not mention {command!r}')

    def test_demo_without_install_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run('demo', tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('init', result.stderr)

    def test_demo_writes_svg_and_editorial_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root), '--lang', 'en')
            result = run('demo', str(root), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'sources' / 'img' / 'demo-figure.svg').exists())
            first = (root / 'sources' / 'first.md').read_text(encoding='utf-8')
            self.assertIn('date:', first)
            self.assertIn('comment:', first)
            self.assertIn('Demo site generated in public/', result.stdout)

    def test_check_exit_code_is_exactly_one_with_diff_hunk(self):
        md = _MINIMAL_MD.replace('Summary.', 'Original.')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            (root / 'sources' / 'a.md').write_text(
                md.replace('Original.', 'Changed.'), encoding='utf-8')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertTrue(any(line.strip().startswith('+') and 'Changed.' in line
                                for line in result.stdout.splitlines()))

    def test_audit_numeric_summary_and_drafts_audited(self):
        # A draft article with no cover: audit must still inspect it and
        # count its warning — audit never excludes drafts (§11.5).
        md_no_cover = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            'page_desc: Has one.\nstatus: draft\n---\n\n'
            '<!-- lwp:slide -->\nslug: k44\nkicker: T\n## Standard only\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'sources' / 'b.md').write_text(md_no_cover, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_source': 'b.md'},
            ]}), encoding='utf-8')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stderr)
            self.assertIn('1 warning(s).', result.stdout)

    def test_corrupt_nav_cache_falls_back_to_full_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            (root / '.lwp-cache' / 'nav.json').write_text('{garbage', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[INFO]', result.stderr)

    def test_gitlab_ci_content_pins_image_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            result = run('init', str(root), '--gitlab-ci')
            self.assertEqual(result.returncode, 0, result.stderr)
            ci = (root / '.gitlab-ci.yml').read_text(encoding='utf-8')
            self.assertIn('python:3.12-slim', ci)
            self.assertIn('public/', ci)
            # install --lang is baked into the CI build command (its one
            # persistent effect); fr by default (§11.1).
            self.assertIn('build . --lang fr', ci)

    def test_gitlab_ci_build_command_carries_install_lang(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            result = run('init', str(root), '--gitlab-ci', '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            ci = (root / '.gitlab-ci.yml').read_text(encoding='utf-8')
            self.assertIn('build . --lang en', ci)

    def test_demo_lang_produces_english_ui(self):
        # The README quickstart passes --lang to demo (not install, where
        # it is inert for local builds) — the UI chrome must be English.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            self.assertEqual(run('init', str(root)).returncode, 0)
            self.assertEqual(run('demo', str(root), '--lang', 'en').returncode, 0)
            index = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Read the article', index)
            self.assertNotIn("Lire l'article", index)

    def test_empty_string_page_source_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_source': ''},
            ]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_a_status_is_read_case_insensitively(self):
        # The predecessor boolean accepted 'TRUE'; the closed vocabulary
        # that replaced it keeps the same tolerance, so a value typed in
        # a capitalised style is a status and not a fatal error.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD, series_extra={'status': 'Draft'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_share_button_is_on_the_index_too(self):
        """The share matrix belongs to both pages: since the two skeletons
        were unified, the index carries the same nav buttons as the
        articles — share included, with the fiche scope disabled (the
        index has no fiche, §9.3.4)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            index = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('id="navShare"', index)
            self.assertIn('id="sharePopover"', index)
            article = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('id="navShare"', article)

    def test_series_nav_status_strings_reach_output(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k45\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k46\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('This series', html)
            self.assertIn('Currently reading', html)
            self.assertIn('Back to index', html)


class DuplicateFieldLastWins(unittest.TestCase):
    """§4.3: a duplicated field in the same header is deliberate override
    semantics (CSS/Make-style) — the LAST occurrence wins, silently — so
    a build system can assemble a slide by concatenating a base fragment
    and an overriding one. Headings keep first-captured (§22.2)."""

    def test_last_slide_field_wins(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k47\nkicker: Base tag\nkicker: Override tag\n'
            '# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Override tag', html)
            self.assertNotIn('Base tag', html)

    def test_last_meta_field_wins(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Base title\n'
            'page_title: Override title\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k48\nkicker: T\n# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<title>Override title</title>', html)


class CheckCoversIndexAndReadme(unittest.TestCase):
    """§11.4: check compares index.html and README.md too — a series_meta
    change alters only those, and check used to stay green over them."""

    def test_series_meta_change_is_caught_via_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data['series_meta'] = {'title': 'A brand new title'}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT] index.html', result.stdout)

    def test_readme_drift_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            (root / 'README.md').write_text('Hand-edited.', encoding='utf-8')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT] README.md', result.stdout)


class ShareSlideScopeByType(unittest.TestCase):
    """§9.3.4: the share matrix's slide scope is disabled by slide TYPE
    (series-nav), not by position — slide order is free (§4.4). A cover
    is shareable, including in first position: only the address bar
    hides its fragment (§8.4), never the share matrix."""

    def test_nav_js_tests_series_nav_class_not_cover_or_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn("classList.contains('slide-series-nav')", html)
            self.assertNotIn("classList.contains('slide-cover')", html)


class CoverIgnoredFieldsWarn(unittest.TestCase):
    """A cover renders only tag/#/summary(+comment). The other standard
    fields are accepted with a WARNING, not an error: toggling a slide
    between standard and cover while drafting is a normal workflow."""

    def test_standard_fields_on_cover_warn_but_build(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k49\nkicker: T\n# Title\nsummary: S.\n'
            'highlight: 42 %\nfact-label: FACT\nsource: Someone, 2020.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARNING]', result.stderr)
            self.assertIn('highlight', result.stderr)
            self.assertIn('never rendered on a cover', result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('42 %', html)

    def test_every_field_the_cover_does_not_take_is_named(self):
        """The warning is computed from the cover's own entry in
        SLIDE_TYPES, so it names every field the type does not take —
        `fact-variant` included, which the hand-written list it replaced
        left out for no reason anyone recorded."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k50\nkicker: T\n# Title\nsummary: S.\n'
            'fact-label: FACT\nfact-variant: warm\nsource: Someone, 2020.\n'
            'highlight: 42 %\nhighlight-caption: C\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ('fact-label', 'fact-variant', 'source',
                         'highlight', 'highlight-caption'):
                self.assertIn(name, result.stderr)


class SlideTypesAreARegistry(unittest.TestCase):
    """SLIDE_TYPES is the one place the four slide types are written, and
    both the validator and `--help` read it.

    Why it had to become a registry: `render_slide()` treats everything
    that is not cover / series-nav / full-article as a standard slide, and
    nothing validated the token. `<!-- lwp:slide:covre -->` therefore
    published — no error, no warning, and a page whose opening slide was
    silently the wrong kind. A typo in a marker is the single most likely
    mistake in this format, and it was the one mistake the engine did not
    report."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_a_misspelled_slide_type_is_fatal_and_says_what_the_types_are(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k51\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide:covre -->\nslug: k52\n## Second\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('[ERROR]', result.stderr)
            self.assertIn('covre', result.stderr)
            self.assertIn('slide 2', result.stderr)
            # The message has to carry the answer, not just the verdict:
            # someone who mistyped `cover` cannot look up a list that is
            # only in the source.
            for name in ('cover', 'standard', 'series-nav', 'full-article'):
                self.assertIn(name, result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists(),
                             'a page was published from an article the engine refused')

    def test_all_four_known_types_still_build(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k53\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide -->\nslug: k54\n## Standard\nFree text.\n\n'
            '---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k55\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k56\narticle: a_article.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'a_article.md').write_text(
                '## Long form\n\nA paragraph.\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_describes_every_type_the_parser_accepts(self):
        """A help text listing three of four types, or describing one the
        parser stopped accepting, is worse than none — it is read as the
        answer. Generated from the registry, so this holds by
        construction; the test is what proves the generation is wired."""
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for slide_type in self.lwp.SLIDE_TYPES:
            self.assertIn(slide_type.name, result.stdout)
            # A distinctive run of the summary, not the whole thing: the
            # help wraps, so the full sentence is never on one line.
            self.assertIn(slide_type.summary.split('.')[0][:40], result.stdout)

    def test_the_registry_describes_fields_that_exist(self):
        """Every field a type claims to take must be a field something
        actually parses, and must have a Slide attribute behind it. A
        registry that names a field the parser never reads would be a
        second, wrong grammar — the exact failure mode it exists to
        prevent, relocated one file up."""
        slide = self.lwp.Slide()
        for slide_type in self.lwp.SLIDE_TYPES:
            for name in slide_type.fields:
                self.assertIn(name, self.lwp._SLIDE_FIELD_ATTRS,
                              f'{slide_type.name} claims field {name!r}')
                self.assertTrue(
                    hasattr(slide, self.lwp._SLIDE_FIELD_ATTRS[name]),
                    f'{name!r} maps to no Slide attribute')
            self.assertIn(slide_type.title_marker, ('#', '##', None))
        self.assertEqual(
            set(self.lwp.SLIDE_TYPES_BY_NAME),
            {t.name for t in self.lwp.SLIDE_TYPES},
            'the lookup table and the tuple disagree')
        # `comment` is on every type on purpose (GLOSSARY.md): parsed
        # everywhere, rendered nowhere.
        for slide_type in self.lwp.SLIDE_TYPES:
            self.assertIn('comment', slide_type.fields, slide_type.name)


class AnAutolinkIsRefusedByName(unittest.TestCase):
    """`<https://x.test>` and `<contact@x.test>` are CommonMark's autolink
    syntax, and this format does not read one: §6.2 gives `<...>` to raw
    inline HTML, and the two syntaxes want the same two characters.

    Refusing is right — nothing false is published. Blaming the wrong
    thing is not: the build used to answer "unbalanced raw HTML in the
    source (an unclosed or mismatched tag, e.g. a <div> in a fact-box
    that is never closed)", which sends an author who wrote ordinary
    Markdown hunting for a tag they never typed."""

    def _build(self, tmp, body):
        root = Path(tmp) / 'series'
        (root / 'sources').mkdir(parents=True)
        (root / 'series.json').write_text(json.dumps(
            {'series_meta': {'title': 'T'},
             'articles': [{'page_dest': 'a.html', 'page_source': 'a.md',
                           'nav_title': 'A', 'nav_desc': 'A'}]}),
            encoding='utf-8')
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k57\nkicker: K\n# T\nsummary: S\n\n'
            '---\n\n'
            '<!-- lwp:slide -->\nslug: k58\nkicker: K\n## H\nsummary: S\n'
            'fact-label: F\n\n' + body + '\n',
            encoding='utf-8')
        return run('build', str(root), '--output', str(Path(tmp) / 'public'))

    def test_a_url_autolink_is_named_and_a_working_remedy_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build(tmp, 'See <https://x.test/a> for more.')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('`<https://x.test/a>` is a Markdown autolink',
                          result.stderr)
            self.assertIn('[https://x.test/a](https://x.test/a)',
                          result.stderr)
            # And it must NOT reach for the old explanation, which named
            # a tag the author never wrote.
            self.assertNotIn('unbalanced raw HTML', result.stderr)

    def test_an_email_autolink_gets_the_remedy_that_actually_works(self):
        """A Markdown link takes an http(s) address and nothing else, so
        `[a@b](mailto:a@b)` renders as literal text — measured. Advising
        it would be advice that does not work, which is the very defect
        this test exists to close, one level down."""
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build(tmp, 'Write to <hi@x.test> for more.')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('`<hi@x.test>` is a Markdown autolink',
                          result.stderr)
            self.assertIn('<a href="hi@x.test">', result.stderr)
            self.assertNotIn('[hi@x.test](mailto:', result.stderr)

    def test_the_remedy_it_offers_for_a_url_builds(self):
        """Run what the message tells the author to type. A message that
        recommends something the tool then refuses is worse than no
        message."""
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build(
                tmp, 'See [https://x.test/a](https://x.test/a) for more.')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('href="https://x.test/a"', html)

    def test_real_unbalanced_html_still_gets_the_old_explanation(self):
        """The autolink message replaces the generic one only when there
        IS an autolink. An actual unclosed div must still be told it is
        an unclosed div."""
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build(tmp, 'Text with <div>no closing tag.')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unbalanced raw HTML', result.stderr)
            self.assertNotIn('autolink', result.stderr)

    def test_prose_with_a_stray_angle_bracket_is_not_called_an_autolink(self):
        """`3 < 4` is arithmetic. The pattern is narrow on purpose — a
        scheme is letters then a colon, an address has an `@`, and
        neither may contain a space."""
        lwp = load_lightwebpres_module()
        for text in ('3 < 4 and 5 > 2', 'a < b > c', '<div>', '</p>',
                     '< https://x.test >'):
            self.assertEqual(lwp._AUTOLINK_RE.findall(text), [], text)
        for text in ('<https://x.test>', '<hi@x.test>', '<ftp://x.test/f>'):
            self.assertTrue(lwp._AUTOLINK_RE.findall(text), text)


class OneRuleForTheAmpersand(unittest.TestCase):
    """§6.2: an `&` outside a tag is escaped; what is inside one is left
    alone. One rule, both grammars.

    There used to be two, and each was wrong at one end. A structural
    field escaped nothing, so `source:
    https://x.test/rechercher?q=marks&copy=1&reg=2` reached the reader as
    `…?q=marks©=1®=2` — `&copy` and `&reg` without a semicolon are in
    HTML5's legacy character-reference list, and nobody made a mistake
    typing that URL. The body escaped every `&`, including inside the
    author's own raw HTML, so a hand-written `<a href="?a=1&amp;b=2">`
    became `&amp;amp;` and the link died.

    The sweep below is the shape of the test, not a list of needles: it
    puts a payload in EVERY field the format has and then reads the built
    pages back looking for any `&` that is not a well-formed reference.
    A list of the fields to check would only ever cover the ones somebody
    thought of; the whole point is the field nobody thought of."""

    # Every `&` a built page may legitimately carry, and nothing else.
    # The four escapes, numeric references, and the arrows the INTERFACE
    # strings emit (`&rarr;` on a navigation card, `&larr;` on the back
    # link) — those come out of the tool's own language packs, never out
    # of an author's field. Named on purpose rather than allowing
    # `&[a-z]+;` wholesale: a fifth one appearing means the tool started
    # emitting an entity somewhere new, and that is worth a failing test
    # rather than a silent pass.
    _BARE_AMP = re.compile(
        r'&(?!amp;|lt;|gt;|quot;|rarr;|larr;|#39;|#\d+;|#x[0-9a-fA-F]+;)')
    # <script> and <style> are the tool's own, not an author's, and JS
    # says `&&` for reasons that have nothing to do with HTML escaping.
    _NOT_CONTENT = re.compile(r'<(script|style)\b.*?</\1>', re.S)

    PAYLOAD = 'Marks & Spencer &sect; &copy'

    def _series(self, tmp):
        root = Path(tmp) / 'series'
        (root / 'sources').mkdir(parents=True)
        meta = {'title': f'T {self.PAYLOAD}', 'subtitle': f'S {self.PAYLOAD}',
                'intro': f'I {self.PAYLOAD}', 'author': f'A {self.PAYLOAD}',
                'license': f'L {self.PAYLOAD}', 'version': 'v1'}
        entry = {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': f'NT {self.PAYLOAD}',
                 'nav_desc': f'ND {self.PAYLOAD}',
                 'card_label': f'CL {self.PAYLOAD}',
                 'card_title': f'CT {self.PAYLOAD}',
                 'card_desc': f'CD {self.PAYLOAD}'}
        second = dict(entry, page_dest='b.html', page_source='b.md')
        (root / 'series.json').write_text(json.dumps(
            {'series_meta': meta, 'articles': [entry, second]}),
            encoding='utf-8')
        # Every slide field that renders, on the types that render it.
        for name in ('a.md', 'b.md'):
            (root / 'sources' / name).write_text(
                f'<!-- lwp:meta -->\n'
                f'page_dest: {name[0]}.html\n'
                f'page_title: PT {self.PAYLOAD}\n'
                f'page_desc: PD {self.PAYLOAD}\n'
                f'author: AU {self.PAYLOAD}\n'
                f'license: LI {self.PAYLOAD}\n'
                f'nav_title: NT {self.PAYLOAD}\n'
                f'nav_desc: ND {self.PAYLOAD}\n'
                f'---\n\n'
                f'<!-- lwp:slide:cover -->\nslug: k59\n'
                f'kicker: KC {self.PAYLOAD}\n'
                f'# H1 {self.PAYLOAD}\n'
                f'summary: SC {self.PAYLOAD}\n\n'
                f'---\n\n'
                f'<!-- lwp:slide -->\nslug: k60\n'
                f'kicker: K {self.PAYLOAD}\n'
                f'## H2 {self.PAYLOAD}\n'
                f'summary: S {self.PAYLOAD}\n'
                f'fact-label: FL {self.PAYLOAD}\n'
                f'highlight: HI {self.PAYLOAD}\n'
                f'highlight-caption: HC {self.PAYLOAD}\n'
                f'source: https://x.test/r?q=marks&copy=1&reg=2\n'
                f'note: N {self.PAYLOAD}\n\n'
                f'Body {self.PAYLOAD}.\n\n'
                f'---\n\n'
                f'<!-- lwp:slide:series-nav -->\nslug: k61\n',
                encoding='utf-8')
        return root

    def _built(self, root, tmp):
        out = Path(tmp) / 'public'
        result = run('build', str(root), '--output', str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        return {p.name: p.read_text(encoding='utf-8')
                for p in sorted(out.glob('*.html'))}

    def test_no_field_anywhere_leaves_a_bare_ampersand_on_a_page(self):
        """The sweep. A bare `&` on a page is either invalid markup or a
        legacy reference the browser silently converts — the second is
        what destroyed the query string."""
        with tempfile.TemporaryDirectory() as tmp:
            pages = self._built(self._series(tmp), tmp)
            self.assertEqual(sorted(pages), ['a.html', 'b.html', 'index.html'])
            for name, html in pages.items():
                content = self._NOT_CONTENT.sub('', html)
                stray = self._BARE_AMP.findall(content)
                self.assertEqual(
                    stray, [],
                    f'{name}: {len(stray)} bare ampersand(s) — '
                    + repr([content[m.start():m.start() + 40]
                            for m in self._BARE_AMP.finditer(content)][:6]))

    def test_the_query_string_reaches_the_reader_intact(self):
        """The reported harm, stated on its own so it cannot be lost in a
        sweep that a future exemption might narrow. `&copy=1` is the one
        that bites: with no semicolon it is still a legacy reference."""
        with tempfile.TemporaryDirectory() as tmp:
            pages = self._built(self._series(tmp), tmp)
            self.assertIn('https://x.test/r?q=marks&amp;copy=1&amp;reg=2',
                          pages['a.html'])

    def test_a_hand_written_entity_stays_literal_and_a_raw_tag_is_untouched(self):
        """The two ends of the one rule, in one document. `&sect;` is the
        author's text and must READ as `&sect;` rather than render as a
        section sign (the position §6.2 already states: write the Unicode
        character). A raw `<a href="…&amp;…">` is the author's own HTML
        and must reach the page byte for byte — it used to come out
        `&amp;amp;`, which is a dead link."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            (root / 'sources').mkdir(parents=True)
            (root / 'series.json').write_text(json.dumps(
                {'series_meta': {'title': 'T'},
                 'articles': [{'page_dest': 'a.html', 'page_source': 'a.md',
                               'nav_title': 'A', 'nav_desc': 'A'}]}),
                encoding='utf-8')
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k62\nkicker: K\n# T\nsummary: S\n\n'
                '---\n\n'
                '<!-- lwp:slide -->\nslug: k63\nkicker: K\n## H\nsummary: S\n'
                'fact-label: F\n\n'
                'Text &sect; and <a href="https://x.test/?a=1&amp;b=2">link</a>.\n',
                encoding='utf-8')
            html = self._built(root, tmp)['a.html']
            self.assertIn('Text &amp;sect; and', html)
            self.assertIn('<a href="https://x.test/?a=1&amp;b=2">link</a>', html)

    def test_the_split_is_the_one_the_typography_engine_uses(self):
        """Two mechanisms that disagreed about where a tag begins would
        protect different halves of the same document. Read from the
        module, both of them, so a future edit to either has to move
        both."""
        lwp = load_lightwebpres_module()
        self.assertEqual(
            lwp._TAG_SPLIT_RE.pattern, r'(</?[a-zA-Z][^<>]*>)',
            'the escape split is no longer the typography engine\'s')
        source = inspect.getsource(lwp.TypoEngine.apply)
        self.assertIn(r"re.split(r'(</?[a-zA-Z][^<>]*>)', text)", source,
                      'the typography engine no longer splits the same way')

    def test_prose_that_looks_like_a_tag_is_not_one(self):
        """`3 < 4 … > 2 & 6` is arithmetic, not a tag spanning the middle
        of the sentence — the exact trap the shared pattern was written
        to avoid, asserted here so a "simpler" `<[^>]+>` cannot come
        back."""
        lwp = load_lightwebpres_module()
        self.assertEqual(lwp.escape_amps('3 < 4 and 5 > 2 & 6'),
                         '3 < 4 and 5 > 2 &amp; 6')


class SeriesNavFullArticleStrictContent(unittest.TestCase):
    """§22.8/§22.9: series-nav and full-article slides render none of
    their own content beyond their directives — unrecognized lines are
    fatal (they used to vanish silently). comment: is recognized on
    every slide type, these two included."""

    def _build(self, tmp, slide_block, extra_files=None):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k64\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            + slide_block
        )
        root = scaffold(tmp, md)
        for name, content in (extra_files or {}).items():
            (root / 'sources' / name).write_text(content, encoding='utf-8')
        return root, run('build', str(root), '--output', str(root / 'public'))

    def test_stray_text_in_series_nav_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(tmp, '<!-- lwp:slide:series-nav -->\nslug: k65\nSome stray text.\n')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('never renders', result.stderr)
            self.assertIn('Some stray text.', result.stderr)

    def test_stray_field_in_full_article_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(
                tmp, '<!-- lwp:slide:full-article -->\nslug: k66\narticle: art.md\nkicker: Oops\n',
                extra_files={'art.md': '# Art\n\nBody.\n'})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('never renders', result.stderr)

    def test_article_directive_on_series_nav_is_fatal(self):
        # article: only means something on a full-article slide.
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(tmp, '<!-- lwp:slide:series-nav -->\nslug: k67\narticle: art.md\n')
            self.assertNotEqual(result.returncode, 0)

    def test_comment_is_recognized_and_never_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build(
                tmp,
                '<!-- lwp:slide:series-nav -->\nslug: k68\ncomment: nav review note\n\n---\n\n'
                '<!-- lwp:slide:full-article -->\nslug: k69\narticle: art.md\ncomment: article review note\n',
                extra_files={'art.md': '# Art\n\nBody.\n'})
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('review note', html)


class LanguageRuleFlags(unittest.TestCase):
    """§19.2: rules[].flags is honored — 'g' global (default), 'i'
    case-insensitive, anything else fatal. It used to be parsed and
    silently ignored."""

    def _build_with_rules(self, tmp, rules, body='cat Cat cat.\n'):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k70\narticle: art.md\n'
        )
        root = scaffold(tmp, md)
        (root / 'sources' / 'art.md').write_text('# T\n\n' + body, encoding='utf-8')
        lang_file = root / 'custom.json'
        lang_file.write_text(json.dumps({'rules': rules}), encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'),
                     '--language-file', str(lang_file))
        return root, result

    def test_i_flag_is_case_insensitive(self):
        rules = [{'name': 'r', 'pattern': 'cat', 'replacement': 'dog', 'flags': 'gi'}]
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build_with_rules(tmp, rules)
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('dog dog dog.', html)

    def test_without_g_only_first_occurrence_is_replaced(self):
        rules = [{'name': 'r', 'pattern': 'cat', 'replacement': 'dog', 'flags': ''}]
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build_with_rules(tmp, rules)
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('dog Cat cat.', html)

    def test_unknown_flag_is_fatal(self):
        rules = [{'name': 'r', 'pattern': 'cat', 'replacement': 'dog', 'flags': 'gx'}]
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build_with_rules(tmp, rules)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unknown flag', result.stderr)


class AuthorContentStrKeyStaysLiteral(unittest.TestCase):
    """§18.4: interface strings are applied to the page skeleton before
    author content is injected — a literal {{str_KEY}} written in an
    article stays literal instead of being substituted."""

    def test_str_key_in_fact_box_stays_literal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k71\nkicker: T\n## Slide\nfact-label: FACT\n'
            'The engine replaces {{str_copy_link}} in its own templates.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # The author's literal placeholder survives...
            self.assertIn('{{str_copy_link}}', html)
            # ...while the skeleton's own placeholders were substituted.
            self.assertIn('title="Previous slide"', html)


class CliStrictParsing(unittest.TestCase):
    """The CLI parser knows which options each command accepts and which
    take a value: typos and out-of-place options are fatal instead of
    silent no-ops, --opt=value is accepted, and a boolean flag never
    swallows the positional argument that follows it."""

    def _root(self, tmp):
        return scaffold(tmp, _MINIMAL_MD)

    def test_unknown_option_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', str(root), '--typo-off')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unknown option', result.stderr)

    def test_option_of_another_command_is_fatal(self):
        # --force exists (install) but is not a build option.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', str(root), '--force')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unknown option', result.stderr)

    def test_equals_form_is_accepted(self):
        # --lang=en used to be silently ignored (site built in French).
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', str(root), '--lang=en',
                         '--output=' + str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Read the article', html)

    def test_boolean_flag_does_not_swallow_the_positional(self):
        # `build --no-typography <dir>` used to parse <dir> as the flag's
        # value and build the current directory instead.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', '--no-typography', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_value_option_without_value_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', str(root), '--lang')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('requires a value', result.stderr)

    def test_boolean_option_with_value_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            result = run('build', str(root), '--include-drafts=yes')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('takes no value', result.stderr)


class CliVersionAndShortcuts(unittest.TestCase):
    """Phase 1 of the CLI refonte (DECISION-CLI.md / PLAN-CLI.md):
    --version, subcommand shortcuts, and legacy aliases with a [WARN]."""

    def test_version_prints_version_and_exits_zero(self):
        # The whole line, not the prefix. `assertIn('LightWebPres v', ...)`
        # matched every string the emitter could possibly produce -- the
        # executable could have answered v0.0.0-wrong and been called
        # correct. The one thing --version exists to say is the number.
        lwp = load_lightwebpres_module()
        result = run('--version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(),
                         f'LightWebPres v{lwp.VERSION}')
        # Version is not buried in help: --version prints only the version.
        self.assertNotIn('COMMANDS', result.stdout)

    def test_the_number_the_tool_says_is_the_number_it_was_released_as(self):
        """The test above asks whether the tool agrees with itself, which
        it always will. This one asks whether it agrees with the RELEASE,
        which is the thing a reader actually downloads.

        Measured, and it is why this exists: v0.42.0 was tagged on a tree
        whose VERSION still read 0.41.2, so the published executable
        announced the previous release — `--version` said 0.41.2, and the
        browser GUI printed "Loaded lightwebpres v0.41.2" for a 0.42.0
        vendor. Nothing in the suite could see it, because every guard
        compared the tool to itself.

        Two states, both checked:

          - HEAD IS the newest tag: this is a cut release, and it must
            announce itself.
          - HEAD is AHEAD of it: the work is unreleased, and VERSION must
            be strictly greater — a number that has not been released is
            allowed, a number that has been is not.

        It cannot fire before the tag exists: nothing can know which
        number the owner will choose. It fires on the first run after the
        tag, which is the earliest moment the answer is knowable.

        Local refs, and that is a real limit rather than a detail: a clone
        that has not fetched cannot see a tag the owner has just pushed,
        and this test is silent for exactly as long as that lasts. It
        happened -- v0.42.1 was cut and the tree kept announcing 0.42.1
        through six further commits with a green suite, because the clone
        those commits were written in had never fetched the tag. So
        `git fetch --tags` belongs to cutting a release, before the suite
        is believed. Reading the remote here instead would put a network
        call in a unit test and make it fail where there is no network,
        which is a worse trade than a documented blind spot."""
        root = Path(__file__).resolve().parent.parent
        def git(*args):
            return subprocess.run(['git', '-C', str(root), *args],
                                  capture_output=True, text=True)
        described = git('describe', '--tags', '--abbrev=0', '--match', 'v*')
        if described.returncode != 0 or not described.stdout.strip():
            self.skipTest('no tag reachable from HEAD to compare against')
        tag = described.stdout.strip()
        released = git('show', f'{tag}:lightwebpres')
        if released.returncode != 0:
            self.skipTest(f'{tag} carries no executable to read')
        match = re.search(r'^VERSION = "([^"]+)"', released.stdout, re.M)
        self.assertIsNotNone(match, f'{tag} has no VERSION line')

        def parts(value):
            return tuple(int(n) for n in value.split('.'))

        tagged = parts(tag.lstrip('v'))
        here = parts(load_lightwebpres_module().VERSION)
        at_tag = git('rev-list', '-n', '1', tag).stdout.strip()
        head = git('rev-parse', 'HEAD').stdout.strip()

        if at_tag == head:
            self.assertEqual(
                parts(match.group(1)), tagged,
                f'{tag} was cut from a tree announcing '
                f'{match.group(1)}: the released tool says it is a version '
                f'it is not, and every reader who runs --version is told so')
        else:
            self.assertGreater(
                here, tagged,
                f'this tree announces {".".join(str(n) for n in here)} and '
                f'{tag} is already released under that number or a later '
                f'one. An unreleased number is fine; a released one is a '
                f'second thing claiming to be the first')

    def test_the_version_it_announces_has_a_changelog_entry(self):
        """The number is in the tool; what changed is in CHANGELOG.md.

        The two live in different files and nothing but this test makes
        them meet. The failure it prevents is not exotic: a version ships,
        the entry is written next week from memory, and the entry is a
        summary of a diff rather than the text the release was announced
        in. CHANGELOG.md says the entry IS the release body, written once
        at bump time — a rule that only holds if forgetting is caught.

        Matched on the heading, not on prose, and both spellings count: a
        version that is tagged is `## v0.43.1` (no date — the date lives
        on the git tag), one that is not yet is `## Unreleased — 0.43.2`.
        Which of the two is correct is the tag guard's business, not this
        one's; here the question is only whether the number appears at
        all. Earlier entries (v0.43.1 and before) carry a date in their
        heading; they were written before the rule changed and are not
        rewritten.

        Deliberately not checking the entry's length or shape. A guard
        that demanded three paragraphs would be satisfied by three
        paragraphs of nothing, and this project's release texts are
        written to be read rather than to clear a counter."""
        root = Path(__file__).resolve().parent.parent
        changelog = root / 'CHANGELOG.md'
        self.assertTrue(changelog.exists(),
                        'CHANGELOG.md is gone: the tool can say which '
                        'version it is and nothing can say what that '
                        'version changed')
        version = load_lightwebpres_module().VERSION
        headings = re.findall(r'^## +(.+)$', changelog.read_text(encoding='utf-8'),
                              re.M)
        self.assertTrue(
            any(re.search(r'(?:^|\s|v)' + re.escape(version) + r'(?:$|\s|—|-)',
                          heading) for heading in headings),
            f'CHANGELOG.md has no section for {version}, the version this '
            f'tree announces. Write the entry when you bump VERSION, not '
            f'when you cut the release: it IS the release body, and a text '
            f'written twice is a text that disagrees with itself. '
            f'Headings found: {headings}')

    def test_the_decisions_index_matches_the_file(self):
        """`DECISIONS.md` may have an index because this refuses to let it
        drift.

        The register carried a rule for a long time forbidding an index,
        and the rule was earned: the block that used to sit at its top
        listed B15, B16 and B17 among the open entries long after all
        three were fixed. That argument is right about the danger and
        wrong about the remedy — a second place to be wrong is only
        dangerous while nothing checks it.

        So the index is derived from the field line under each entry, by
        `tools/decisions_index.py`, and this recomputes it and compares.
        The comparison is on the whole file rather than on the block,
        because a splice that lands in the wrong place is the same defect
        as a stale list.

        This also rejects an entry whose field line is missing or names a
        state outside the six: the generator raises rather than skipping
        it, since an entry silently absent from an index is exactly the
        failure the rule was written against."""
        root = Path(__file__).resolve().parent.parent
        script = root / 'tools' / 'decisions_index.py'
        register = root / 'DECISIONS.md'
        if not script.exists() or not register.exists():
            self.skipTest('no decisions_index.py or DECISIONS.md in this checkout')
        r = subprocess.run([sys.executable, str(script), '--check'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         (r.stdout + r.stderr).strip() or
                         'the index of DECISIONS.md is stale')

    def test_no_section_reference_points_at_nothing(self):
        """A `§N.N` that resolves to no section is a document lying about
        itself, and it is the cheapest lie to tell: nothing breaks when a
        section is renumbered, so nobody finds out.

        Measured when this was written: 1 359 references across the
        repository, of which five pointed at a section 9.2.1 — the share
        matrix, moved to §9.3.4 by the §9 rewrite months earlier — in
        three test files that had been green the whole time.

        Note the shape of the sentence above: a dead reference is written
        WITHOUT the section sign, because `§` means "go there" and this
        one goes nowhere. That is the convention, and this test is what
        made it necessary — its first draft cited both dead references
        with the sign, in these docstrings, and failed on itself.

        Unqualified means `specifications.md`, which is how the whole
        repository uses it. A reference qualified by the sibling project
        is skipped: `lightwebpres-gui` has its own numbering and a reader
        can open it.

        Dated records and the doomed tree are out of scope by §1.1: an
        audit says the state of its day and is not maintained."""
        root = Path(__file__).resolve().parent.parent
        script = root / 'tools' / 'check_refs.py'
        if not script.exists() or not (root / 'specifications.md').exists():
            self.skipTest('no check_refs.py or specifications.md in this checkout')
        r = subprocess.run([sys.executable, str(script)],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0,
                         'dangling section references:\n' + r.stdout + r.stderr)

    def test_the_shipped_executable_cites_only_what_a_reader_can_reach(self):
        """The executable is the deliverable: people get this tool by
        downloading one file.

        It carried 31 citations of the CLI refonte's design documents —
        DECISION 1 Phase 2, PROPOSITION 5.10, DECISION-CLI.md 4 — which
        live in `delete-before-1.0/`, are not distributed, and whose
        directory name promises they will be deleted. Someone reading the
        file they downloaded had no way to resolve any of them, ever.

        None of the 31 was load-bearing: each sat beside a comment that
        already explained the decision, so the address went and the
        reasoning stayed. `specifications.md` references are a different
        matter and stay — that document ships with the repository."""
        root = Path(__file__).resolve().parent.parent
        text = (root / 'lightwebpres').read_text(encoding='utf-8')
        unreachable = ('DECISION-CLI', 'PLAN-CLI.md', 'PROPOSITION-CLI',
                       'JOURNAL-1.0', 'RELECTURE.md', 'delete-before-1.0')
        found = [name for name in unreachable if name in text]
        self.assertEqual(
            found, [],
            f'the executable cites {found}, which lives in '
            f'delete-before-1.0/ and is never distributed. Put the reason '
            f'in the comment; an address a reader cannot reach is not one')

    def test_no_document_tells_a_reader_to_type_a_retired_command(self):
        """A document that teaches a retired name teaches a warning.

        Thirteen names have a canonical replacement — `install` → `init`,
        `themes-gallery` → `theme gallery`, `refresh-templates` →
        `template update` — kept as aliases for one MAJOR, each printing
        a `[WARNING]` that `--quiet` swallows. So a reader who follows
        such a document gets working output today and a broken command at
        the next MAJOR, with nothing in between to warn them.

        The class has bitten: the sibling project taught retired names for
        months. Measured here when this was written: zero sites, and this
        is what keeps it there.

        Matched on the INVOCATION, never on the word. `check`, `install`
        and `themes` are ordinary English, and the sourced-presentation
        skill says "check" a dozen times about verifying a fact. Only
        `lightwebpres <verb>` counts."""
        root = Path(__file__).resolve().parent.parent
        lwp = load_lightwebpres_module()
        retired = {k: v for k, v in lwp._CANONICAL_NAME.items() if v != k}
        for legacy in ('install', 'check', 'themes'):
            retired.setdefault(legacy, lwp.canonical(legacy))
        pattern = re.compile(r'(?:\./)?(?:python3 )?`?lightwebpres`? '
                             r'([a-z][a-z-]+)')
        skip = ('delete-before-1.0/', 'docs/AUDIT', 'generated/')
        listed = subprocess.run(['git', '-C', str(root), 'ls-files'],
                                capture_output=True, text=True, timeout=30)
        bad = []
        for name in listed.stdout.split('\n'):
            if not name or name.startswith(skip) or name.endswith(('.png', '.pyc')):
                continue
            try:
                text = (root / name).read_text(encoding='utf-8')
            except (OSError, UnicodeDecodeError):
                continue
            for i, line in enumerate(text.split('\n'), 1):
                for verb in pattern.findall(line):
                    if verb in retired:
                        bad.append(f'{name}:{i}: `{verb}` is now '
                                   f'`{retired[verb]}` — {line.strip()[:70]}')
        self.assertEqual(bad, [], 'documents teaching a retired command:\n'
                                  + '\n'.join(bad))

    def test_every_format_field_is_in_the_glossary(self):
        """`GLOSSARY.md` indexes every `key: value` of the format (§1.1),
        and it is the vocabulary contract the sibling project binds itself
        to (§1.2). A field the code accepts and the glossary never names
        is a field the GUI has no reason to know exists.

        Read from the code's own tables rather than from a list written
        here: a list in a test is a third place to be wrong."""
        root = Path(__file__).resolve().parent.parent
        glossary = root / 'GLOSSARY.md'
        if not glossary.exists():
            self.skipTest('no GLOSSARY.md in this checkout')
        lwp = load_lightwebpres_module()
        fields = (set(lwp.ARTICLE_META_KEYS) | set(lwp.SLIDE_FIELD_NAMES)
                  | set(lwp._SERIES_STRING_FIELDS)
                  | set(lwp._SERIES_META_STRING_FIELDS)
                  | set(lwp._SLIDE_FIELD_ATTRS))
        named = set(re.findall(r'`([a-z][a-z0-9_.-]*)`',
                               glossary.read_text(encoding='utf-8')))
        missing = sorted(fields - named)
        self.assertEqual(
            missing, [],
            f'the format accepts {missing} and GLOSSARY.md never names '
            f'them, which is the contract lightwebpres-gui reads')

    def test_the_spec_index_matches_the_file(self):
        """`specifications.md` may have a table of contents for the same
        reason `DECISIONS.md` may have an index: it is derived, and this
        fails if it drifts.

        The document went 23 sections and 7 000 lines without one. The
        only way in was to already know that the format is §4, the
        commands §11, the themes §9 and the `series.json` schema §20 —
        knowledge you get by having read the thing you are trying to find
        your way into.

        The generator is fence-aware and that is load-bearing rather than
        tidy: §4.2 carries a complete example article, and its slide
        headings are `#` and `##` like any other. Read without tracking
        fences, "La température change tout" is a section of this
        specification, sitting between §4 and §5."""
        root = Path(__file__).resolve().parent.parent
        script = root / 'tools' / 'spec_index.py'
        spec = root / 'specifications.md'
        if not script.exists() or not spec.exists():
            self.skipTest('no spec_index.py or specifications.md in this checkout')
        r = subprocess.run([sys.executable, str(script), '--check'],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         (r.stdout + r.stderr).strip() or
                         'the table of contents of specifications.md is stale')

    def test_every_decision_entry_declares_one_of_the_six_states(self):
        """A register whose entries do not declare a state is a register
        that cannot be counted, which is how the old one decayed: an entry
        fixed in a lot named after something else kept saying `NOTED`
        because nothing ever asked it.

        The states are a closed set on purpose. `DONE`, `FIXED`,
        `SETTLED`, `CLOSED`, `NOTED`, `OPEN`, `EXCLU`, `HALF FIXED` and
        `IMPLEMENTÉ ET TESTÉ EN NAVIGATEUR` all meant something once and
        between them said nothing you could sort by."""
        root = Path(__file__).resolve().parent.parent
        register = root / 'DECISIONS.md'
        if not register.exists():
            self.skipTest('no DECISIONS.md in this checkout')
        text = register.read_text(encoding='utf-8')
        states = {'à étudier', 'à faire', 'en cours', 'terminé',
                  'abandonné', 'sans objet'}
        lines = text.split('\n')
        titles = [(i, ln) for i, ln in enumerate(lines)
                  if re.match(r'^## [BC]\d+ — ', ln)]
        self.assertTrue(titles, 'DECISIONS.md has no entries')
        for i, title in titles:
            field = next((ln for ln in lines[i + 1:i + 4]
                          if ln.startswith('**État :**')), None)
            self.assertIsNotNone(
                field, f'{title!r} has no field line under its title')
            state = re.match(r'^\*\*État :\*\* ([^·\n]+?)(?: ·|$)', field)
            self.assertIsNotNone(
                state, f'{title!r}: unreadable field line {field!r}')
            self.assertIn(
                state.group(1).strip(), states,
                f'{title!r} declares a state outside the six')

    def test_help_contains_version_in_header(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LightWebPres v', result.stdout)

    def test_a_retired_spelling_is_refused_and_nothing_is_written(self):
        """They were deprecated aliases: a [WARNING], then the command ran
        anyway. That taught the old spelling rather than the new one —
        completion offered `install` beside `init` with nothing to say
        which was which, and a command that works after complaining is a
        command people keep typing.

        Refused now, and nothing happens: `install` wrote a whole series
        before, so the directory is the assertion that matters."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 's'
            result = run('install', str(target))
            self.assertEqual(result.returncode, 1)
            self.assertIn('[ERROR]', result.stderr)
            self.assertIn('`lightwebpres init`', result.stderr)
            self.assertFalse(target.exists(), 'the refused command still ran')

    def test_shortcut_init_works_without_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / 's')
            result = run('init', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            # The shortcut is the new name — no deprecation warning.
            self.assertNotIn('[WARN]', result.stderr)

    def test_shortcut_verify_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_series_build_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('series', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_canonical_theme_list_works(self):
        result = run('theme', 'list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('built-in themes', result.stdout)

    def test_canonical_theme_gallery_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'gallery.html'
            result = run('theme', 'gallery', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())

    def test_canonical_status_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root))
            scaffold(str(root), _MINIMAL_MD)
            result = run('status', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_template_update_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            # init creates the templates/ directory that template update needs.
            run('init', str(root))
            # scaffold overwrites series.json/articles with a minimal fixture
            # so the series is valid for template update to inspect.
            scaffold(str(root), _MINIMAL_MD)
            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_series_theme_set_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root))
            scaffold(str(root), _MINIMAL_MD)
            result = run('series', 'theme', 'set', str(root),
                         '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_theme_set_as_root_shortcut_is_rejected(self):
        # `theme set` is NOT a root shortcut (DECISION §3): the theme node
        # never touches a series. Must exit 1 with a helpful message.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root))
            scaffold(str(root), _MINIMAL_MD)
            result = run('theme', 'set', str(root), '--theme', 'nord')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('series theme set', result.stderr)

    def test_lone_template_is_rejected(self):
        result = run('template')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('template update', result.stderr)

    def test_global_lang_before_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--lang', 'en', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Read the article', html)

    def test_global_lang_nearest_to_command_wins(self):
        # `--lang en build --lang fr` → fr (DECISION §2: nearest wins).
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--lang', 'en', 'build', str(root), '--lang', 'fr',
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            # French UI strings: the CTA on the index card is in French.
            self.assertIn('Lire l', html)
            # English would have said "Read" instead.
            self.assertNotIn('Read the article', html)

    def test_quiet_suppresses_info_messages(self):
        # --quiet suppresses [INFO] progress messages (DECISION §4).
        # The --only fallback emits an [INFO] line; with --quiet it is gone.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            # Build once so the cache exists, then corrupt it to force the
            # fallback path that emits the [INFO] message.
            run('build', str(root), '--output', str(root / 'public'))
            (root / '.lwp-cache' / 'nav.json').write_text('{garbage',
                                                           encoding='utf-8')
            loud = run('build', str(root), '--output', str(root / 'public'),
                       '--only', 'a.html')
            quiet = run('--quiet', 'build', str(root), '--output',
                         str(root / 'public'), '--only', 'a.html')
            self.assertEqual(loud.returncode, 0, loud.stderr)
            self.assertEqual(quiet.returncode, 0, quiet.stderr)
            self.assertIn('[INFO]', loud.stderr)
            self.assertNotIn('[INFO]', quiet.stderr)

    def test_timestamp_prefixes_log_lines(self):
        # --timestamp prepends an RFC 3339 timestamp to each log line.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            (root / '.lwp-cache' / 'nav.json').write_text('{garbage',
                                                           encoding='utf-8')
            result = run('--timestamp', 'build', str(root), '--output',
                         str(root / 'public'), '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            # The [INFO] line now starts with a timestamp like
            # 2026-08-09T18:50:00+02:00 [INFO] ...
            import re
            self.assertRegex(result.stderr,
                              r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2} \[INFO\]')

    def test_no_color_is_accepted(self):
        # --no-color is a no-op for now (no ANSI codes in the codebase) but
        # must be accepted without error (DECISION §2 global).
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--no-color', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_verbose_names_every_file_the_build_writes(self):
        """`--help` promises "each file written". For a whole release the
        flag was parsed, stored, and given its own branch in log() -- and
        NOTHING ever called log('verbose', ...), so `--verbose build` was
        byte-identical to `build`. The plumbing was complete and no one
        was speaking into it.

        Every write already passes through _write_file/_mkdir/_copy/
        _copytree/_remove, which is exactly the set --dry-run journals, so
        naming the files is four words per helper rather than a new
        traversal of the program."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            out = root / 'public'
            quiet_run = run('build', str(root), '--output', str(out))
            self.assertEqual(quiet_run.returncode, 0, quiet_run.stderr)
            self.assertNotIn('[DEBUG]', quiet_run.stderr,
                             'verbose output leaked without the flag')
            loud = run('--verbose', 'build', str(root), '--output', str(out))
            self.assertEqual(loud.returncode, 0, loud.stderr)
            debug = [l for l in loud.stderr.splitlines() if '[DEBUG]' in l]
            self.assertGreater(len(debug), 1,
                               'the flag is parsed but nothing speaks at '
                               'that level:\n' + loud.stderr)
            # Not merely "some output": the page it wrote has to be named.
            self.assertTrue(any('a.html' in l for l in debug),
                            'no [DEBUG] line names the file that was '
                            'written:\n' + '\n'.join(debug))

    def test_a_global_option_works_on_either_side_of_the_command(self):
        """`build s --quiet` exited 1 while `--quiet build s` worked, and
        --lang -- which IS a global -- worked in both. Meanwhile a global
        the target command cannot use was silently accepted in leading
        position. Inconsistent in both directions at once; one rule now."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(scaffold(tmp, _MINIMAL_MD))
            out = str(Path(tmp) / 'public')
            loud = run('build', root, '--output', out)
            self.assertGreater(len(loud.stdout), 0)
            for argv in ((root, '--output', out, '--quiet'),
                         ('--quiet', root, '--output', out)):
                result = run('build', *argv)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, '',
                                 f'--quiet parsed but did nothing in '
                                 f'`build {" ".join(argv)}`')
            # And a postfix --verbose reaches the logger, not just the parser.
            v = run('build', root, '--output', out, '--verbose')
            self.assertIn('[DEBUG]', v.stderr, v.stderr)

    def test_double_dash_ends_the_options(self):
        """There was no way to name a directory that starts with a dash or
        collides with a verb, and `--` itself was reported as an unknown
        option -- the least helpful answer to someone reaching for exactly
        this."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', '--', str(root), '--output',
                         str(root / 'public'))
            # Everything after `--` is positional, so --output is one too:
            # what matters is that `--` is accepted and the directory read.
            self.assertNotIn('Unknown option: --', result.stderr)

    def test_a_language_with_no_pack_says_so(self):
        """The fallback to the built-in English pack is deliberate and
        documented. Saying nothing about it was not: `--lang de` with no
        de.json produced a page carrying lang="de" over English strings,
        exit 0, in silence. A pipeline cannot see that; a screen reader
        can."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            out = str(root / 'public')
            odd = run('build', str(root), '--output', out, '--lang', 'xx')
            self.assertEqual(odd.returncode, 0, odd.stderr)
            self.assertIn('no language pack', odd.stderr)
            self.assertIn('[WARNING]', odd.stderr)
            for known in ('fr', 'en'):
                quiet = run('build', str(root), '--output', out,
                            '--lang', known)
                self.assertNotIn('no language pack', quiet.stderr,
                                 f'--lang {known} warned about itself')

    def test_theme_gallery_refuses_a_directory_without_a_traceback(self):
        """The legacy positional took any non-slug word as an output path
        with no writability check, so a directory reached write_text() and
        came back as a raw Python traceback -- the only failure in this
        program that did."""
        with tempfile.TemporaryDirectory() as tmp:
            result = run('theme', 'gallery', tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertNotIn('Traceback', result.stdout)

    def test_theme_show_never_reads_a_series_however_it_is_asked(self):
        """`theme show <dir> nord dracula` used to print the series\'
        effective theme, exit 0, and say nothing about the two slugs —
        known-good slugs, which the spec requires be reported when they
        cannot be honoured. The mixed form was caught first; the plain
        `theme show <dir>` kept working, as the last shape of the old
        `theme-info` that did both jobs.

        Neither reads a series now. `theme show` is the catalogue, full
        stop, and both refusals name `series theme`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / 's')
            self.assertEqual(run('init', root).returncode, 0)
            for argv in ((root,), (root, 'nord', 'dracula')):
                refused = run('theme', 'show', *argv)
                self.assertNotEqual(refused.returncode, 0, refused.stdout)
                self.assertIn('series theme', refused.stderr,
                              f'`theme show {" ".join(argv)}`')
            # The catalogue reading is untouched, and so is the series
            # reading under the command that owns it.
            self.assertEqual(run('theme', 'show', 'nord', 'dracula').returncode, 0)
            self.assertEqual(run('series', 'theme', root).returncode, 0)

    def test_every_command_and_node_answers_its_own_help(self):
        """`build --help` exited 1 with "Unknown option: --help", because
        --help was honoured only in leading position. A refactor whose
        headline feature is nested subcommands shipped with no subcommand
        help at all, and the most reflexive keystroke in the new grammar
        was the one that failed."""
        for argv in (('build', '--help'), ('build', '-h'),
                     ('theme', 'show', '--help'),
                     ('series', 'build', '--help'),
                     ('clean', '--help'), ('resolve', '--help')):
            result = run(*argv)
            self.assertEqual(result.returncode, 0,
                             f'`{" ".join(argv)}`:\n{result.stderr}')
            self.assertIn('lightwebpres', result.stdout)
            self.assertIn('GLOBAL OPTIONS', result.stdout)
        # A NODE is not a command: `theme --help` answered "Unknown theme
        # verb: `theme --help`", which reads as a typo nobody made.
        for node in ('theme', 'series'):
            result = run(node, '--help')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('VERBS', result.stdout)
            self.assertNotIn('Unknown', result.stderr)

    def test_command_help_promises_the_shape_the_parser_accepts(self):
        """The synopsis is derived from the same table that enforces the
        argument count, so help cannot advertise a form the parser
        refuses. theme show takes slugs, not a directory."""
        for argv, shape in ((('build',), '[directory]'),
                            (('resolve',), '[directory] <name>'),
                            (('theme', 'show'), '<slug>...'),
                            (('theme', 'gallery'), '<slug>...')):
            first = run(*argv, '--help').stdout.splitlines()[0]
            self.assertIn(shape, first, f'`{" ".join(argv)} --help`: {first}')
        # theme list takes no positional at all, so it promises none.
        first = run('theme', 'list', '--help').stdout.splitlines()[0]
        self.assertNotIn('directory', first, first)
        self.assertNotIn('<slug>', first, first)

    def test_an_error_names_the_command_the_user_typed(self):
        """_COMMAND_OPTIONS is keyed by the LEGACY token, so a message that
        echoed a key recommended the command the same program tells you not
        to use: `status --strict` answered "not an option of `series-info`"
        for eight of the thirteen commands, and `series theme` answered
        "series-theme", which is not a CLI token at all."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(scaffold(tmp, _MINIMAL_MD))
            cases = (
                (('status', root, '--strict'), 'status', 'series-info'),
                (('theme', 'list', '--format', 'json'), 'theme list', 'themes'),
                (('verify', root, '--strict'), 'verify', 'check'),
                (('init', root, '--strict'), 'init', 'install'),
                (('series', 'theme', root, '--strict'),
                 'series theme', 'series-theme'),
            )
            for argv, wanted, forbidden in cases:
                result = run(*argv)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(f'`{wanted}`', result.stderr,
                              f'`{" ".join(argv)}`:\n{result.stderr}')
                self.assertNotIn(f'`{forbidden}`', result.stderr,
                                 f'the error names a spelling this tool '
                                 f'does not accept:\n{result.stderr}')

    def test_an_unusable_argument_is_fatal_not_discarded(self):
        """`init A B` created A, printed "Installed: A", and never
        mentioned B -- a write command ignoring half of what it was given,
        exit 0, no word about it. specifications.md §2.4 already promises
        an unknown option is fatal and "never a silent no-op"; an argument
        the command cannot use is that same promise from the other side.

        `-x` is in here on purpose: a single-dash typo is not recognised
        as an option at all, so it silently became a positional and was
        then silently dropped -- two silences stacked."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            a, b = str(Path(tmp) / 'A'), str(Path(tmp) / 'B')
            for argv, label in (
                (('init', a, b), 'a second directory'),
                (('status', str(root), 'extra'), 'a stray word'),
                (('theme', 'list', 'junk'), 'an argument on a listing'),
                (('build', str(root), '-x'), 'a single-dash typo'),
                (('resolve', str(root), 'page_title', 'b', 'c'), 'two extras'),
            ):
                result = run(*argv)
                self.assertNotEqual(
                    result.returncode, 0,
                    f'{label} was accepted silently: `{" ".join(argv)}`\n'
                    f'{result.stdout}')
                self.assertIn('takes', result.stderr, result.stderr)
            # The refusal must happen BEFORE any work: nothing on disk.
            self.assertFalse(Path(a).exists(),
                             'init did its work before refusing the '
                             'arguments it could not use')
            self.assertFalse(Path(b).exists())

    def test_the_forms_that_take_several_arguments_still_do(self):
        """The arity check must not become a straitjacket: theme show and
        theme gallery take a list of slugs, and resolve takes a directory
        and a name."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            out = str(Path(tmp) / 'g.html')
            for argv in (
                ('theme', 'show', 'nord', 'crimson'),
                ('theme', 'gallery', 'nord', 'crimson', '--output', out),
                ('resolve', str(root), 'page_title', '--article', 'a.md'),
                ('init', str(Path(tmp) / 'ok')),
            ):
                result = run(*argv)
                self.assertEqual(result.returncode, 0,
                                 f'`{" ".join(argv)}`:\n{result.stderr}')

    def test_version_is_refused_after_a_command_not_swallowed(self):
        """`--version` sat in the same table as `--quiet` and `--lang`, and
        §2.4.1 promised all eight worked before or after the command. Seven
        did. `build s --version` built the series and printed nothing;
        `theme gallery --version` wrote a 13 MB file. Measured: the flag was
        accepted by the post-command parser and never read.

        The table conflated two natures. A modifier changes how a command
        runs, so either position is a real convenience. An action replaces
        the command — honouring `--version` after one would silently
        discard the request the user typed, which is not better than
        ignoring it. `--help` is the exception: after a command it means
        the help OF that command, so it earns its place. `--version` has no
        contextual meaning, so it is refused by name (BACKLOG B22)."""
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / 's')
            self.assertEqual(run('init', target).returncode, 0)

            # Head of line: it reports and exits, whatever follows.
            lead = run('--version', 'build', target)
            self.assertEqual(lead.returncode, 0, lead.stderr)
            self.assertIn('LightWebPres v', lead.stdout)
            self.assertFalse((Path(target) / 'public' / 'index.html').exists(),
                             'the short-circuit built the series anyway')

            # After a command: refused, and the message says what to type.
            for argv in (('build', target, '--version'),
                         ('status', target, '--version'),
                         ('theme', 'list', '--version')):
                with self.subTest(argv=argv):
                    result = run(*argv)
                    self.assertEqual(result.returncode, 1,
                                     f'`{" ".join(argv)}` was not refused:\n'
                                     + result.stdout)
                    self.assertIn('--version', result.stderr)
                    self.assertIn('lightwebpres --version', result.stderr,
                                  'the error does not say what to run instead')
                    self.assertNotIn('LightWebPres v', result.stdout,
                                     'it printed the version after refusing it')

            # The six modifiers keep working on both sides — the split must
            # not have cost them anything.
            for argv in (('--quiet', 'status', target),
                         ('status', target, '--quiet'),
                         ('--lang', 'en', 'status', target),
                         ('status', target, '--lang', 'en')):
                with self.subTest(argv=argv):
                    self.assertEqual(run(*argv).returncode, 0,
                                     f'`{" ".join(argv)}` broke')

    def test_the_double_dash_terminator_covers_the_action_flags(self):
        """`--` means everything after it is a positional, whatever it
        looks like. The `--help` check scanned the whole tail, so
        `status -- --help` answered with help for a directory literally
        named `--help` — the one reading the terminator exists to rule
        out."""
        with tempfile.TemporaryDirectory() as tmp:
            for flag in ('--help', '--version'):
                with self.subTest(flag=flag):
                    result = run('status', '--', flag, cwd=tmp)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(flag, result.stderr,
                                  'the terminator was ignored and the flag '
                                  f'was acted on instead of named:\n{result.stderr}')
                    self.assertNotIn('LightWebPres v', result.stdout)

    def test_no_retired_spelling_is_shadowed_by_a_live_command(self):
        """`_SHORTCUTS` is consulted BEFORE `_RETIRED_SPELLINGS` in
        `_resolve_command`, so a live command sharing a name with a
        retired one makes the refusal unreachable — dead code that still
        reads as a live promise, and a table entry nobody would think to
        remove.

        The tables are disjoint today. This fails the day they are not,
        which forces the choice to be made on purpose: either the name is
        a command again and its entry goes, or it is not and the new
        command needs another word."""
        lwp = load_lightwebpres_module()
        retired = set(lwp._RETIRED_SPELLINGS)
        for label, live in (('_SHORTCUTS', lwp._SHORTCUTS),
                            ('_SERIES_VERBS', lwp._SERIES_VERBS),
                            ('_THEME_VERBS', lwp._THEME_VERBS),
                            ('_TEMPLATE_VERBS', lwp._TEMPLATE_VERBS)):
            self.assertEqual(
                sorted(retired & set(live)), [],
                f'{label} shares a name with a retired spelling, whose '
                f'refusal is now unreachable')

    def test_every_retired_spelling_is_refused_and_names_its_replacement(self):
        """They used to warn and then run, and this test used to prove
        each one dispatched to the right command. It proves the other
        thing now: that none of them runs, and that each says what to
        type instead.

        Driven off `_RETIRED_SPELLINGS`, so a spelling added to that
        table without a case here fails, and a case left behind after its
        entry is gone fails too. The replacement each one names must be a
        form the tool actually accepts — checked by running it with
        `--help`, which no retired spelling survives."""
        lwp = load_lightwebpres_module()
        self.assertEqual(
            sorted(lwp._RETIRED_SPELLINGS),
            ['check', 'install', 'refresh-templates', 'series-info',
             'set-theme', 'theme-info', 'themes', 'themes-gallery'],
            'a retired spelling was added or removed without a case here')
        for spelling, sentence in sorted(lwp._RETIRED_SPELLINGS.items()):
            with tempfile.TemporaryDirectory() as tmp:
                r = run(spelling, cwd=tmp)
                self.assertEqual(r.returncode, 1, f'{spelling}: {r.stdout}')
                self.assertIn('is not a command', r.stderr, spelling)
                self.assertEqual(sorted(Path(tmp).iterdir()), [],
                                 f'{spelling} still did something')
                # Every command the message names must be one the tool
                # answers to. A refusal that recommends a second refusal
                # is worse than the alias it replaced.
                for named in re.findall(r'`lightwebpres ([a-z ]+?)[`<]',
                                        sentence):
                    helped = run(*named.split(), '--help')
                    self.assertEqual(helped.returncode, 0,
                                     f'{spelling} recommends `{named}`, '
                                     f'which the tool refuses: {helped.stderr}')

    def test_quiet_suppresses_progress_and_keeps_warnings(self):
        """--quiet was exactly inverted, in the direction that matters
        least at a terminal and most in CI. Progress went out through bare
        print() calls the flag could not see; diagnostics came through
        log(), where it could. So it removed the warnings and left every
        line of progress. Measured on one build before the fix: without
        the flag, 1 warning and 645 bytes of progress; with it, 0 warnings
        and the same 645 bytes.

        The fix does not move progress to stderr. Progress has always been
        stdout, the GUI and any script read it there, and the defect was
        never the stream -- it was that print() has no valve."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            # A cover carrying `highlight` is parsed and never rendered:
            # the build warns, which is what must survive --quiet.
            '<!-- lwp:slide:cover -->\nslug: k72\nkicker: T\nhighlight: 42\n'
            '# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            out = str(root / 'public')
            loud = run('build', str(root), '--output', out)
            self.assertEqual(loud.returncode, 0, loud.stderr)
            self.assertGreater(len(loud.stdout), 0, 'no progress to suppress')
            self.assertIn('[WARNING]', loud.stderr,
                          'the fixture stopped producing a warning, so the '
                          'assertion below would prove nothing')
            hushed = run('--quiet', 'build', str(root), '--output', out)
            self.assertEqual(hushed.returncode, 0, hushed.stderr)
            self.assertEqual(hushed.stdout, '',
                             '--quiet left progress on stdout:\n'
                             + hushed.stdout)
            self.assertIn('[WARNING]', hushed.stderr,
                          '--quiet suppressed a warning, which is the one '
                          'thing an unattended run needs to reach a human')

    def test_quiet_never_suppresses_the_answer(self):
        """Asking for less chatter must not delete the value you asked the
        tool to compute. These commands' output IS their product, so they
        keep bare print() and --quiet does not reach them."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            answers = (
                ('resolve', str(root), 'page_title', '--article', 'a.md'),
                ('status', str(root), '--format', 'json'),
                ('theme', 'show', 'nord'),
                ('theme', 'list'),
                ('audit', str(root)),
            )
            for argv in answers:
                result = run('--quiet', *argv)
                self.assertGreater(
                    len(result.stdout.strip()), 0,
                    f'--quiet ate the answer of `{" ".join(argv[:2])}`:\n'
                    f'{result.stderr}')

    def test_quiet_does_not_swallow_verbose(self):
        """The two flags answer different questions -- how much progress,
        and how much detail -- so --quiet must not silence a level the
        operator asked for explicitly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--quiet', '--verbose', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[DEBUG]', result.stderr)

    def test_the_ansi_strip_is_not_wired_to_no_color(self):
        """--no-color looks inert because this codebase emits no colour,
        and the ANSI strip in log() is a SECURITY control, not a colour
        feature: author-controlled strings pass through it, and a hostile
        series must not be able to paint the operator's terminal or forge
        log lines. Making the strip conditional on --no-color would turn
        every run without the flag into that hole, so the wiring the flag
        appears to be missing is wiring it must never get."""
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        log_fn = [n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == 'log']
        self.assertEqual(len(log_fn), 1, 'log() moved or was duplicated')
        body = ast.dump(log_fn[0])
        self.assertIn('_ANSI_RE', body, 'the ANSI strip left log()')
        # The strip must not sit under any test of no_color.
        for node in ast.walk(log_fn[0]):
            if isinstance(node, ast.If) and 'no_color' in ast.dump(node.test):
                self.fail('the ANSI strip is now conditional on --no-color')

    def test_strict_audit_fails_on_warnings(self):
        # --strict makes audit exit 1 when warnings are emitted (DECISION §1
        # Phase 2). A series with no cover slide triggers a warning.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_source: a.md\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:standard -->\nslug: k73\n# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md, source_name='a.md', file_name='a.html')
            no_strict = run('audit', str(root))
            strict = run('audit', str(root), '--strict')
            self.assertEqual(no_strict.returncode, 0, no_strict.stderr)
            self.assertNotEqual(strict.returncode, 0)
            self.assertIn('warning', strict.stdout.lower())

    def test_strict_audit_passes_when_no_warnings(self):
        # A clean series: --strict still exits 0 (no warnings).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root))
            # The demo series is clean by construction.
            run('demo', str(root))
            result = run('audit', str(root), '--strict')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_series_theme_reads_effective_theme(self):
        # `series theme [dir]` reads the effective theme of an installed
        # series (DECISION §1 Phase 2, ex-theme-info [dir]).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root), '--theme', 'nord')
            scaffold(str(root), _MINIMAL_MD)
            result = run('series', 'theme', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('nord', result.stdout)

    def test_series_theme_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('init', str(root), '--theme', 'nord')
            scaffold(str(root), _MINIMAL_MD)
            result = run('series', 'theme', str(root), '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['target']['kind'], 'series')

    def test_theme_show_all_describes_every_theme(self):
        # `theme show --all` describes every built-in theme (DECISION §1 P2).
        result = run('theme', 'show', '--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        # The output mentions every theme slug.
        for slug in ('nord', 'dracula', 'solarized'):
            self.assertIn(slug, result.stdout)

    def test_theme_show_multiple_slugs(self):
        # `theme show <slug> [<slug>…]` compares several themes (DECISION §1).
        result = run('theme', 'show', 'nord', 'dracula')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('nord', result.stdout)
        self.assertIn('dracula', result.stdout)

    def test_theme_show_unknown_slug_is_fatal(self):
        result = run('theme', 'show', 'nonexistent')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not a built-in theme', result.stderr)

    def test_theme_show_no_args_without_all_is_error(self):
        # `theme show` with no slug and no --all is an error (needs at least
        # one slug or --all).
        result = run('theme', 'show')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('slug', result.stderr.lower())

    def test_theme_gallery_restricts_to_slugs(self):
        # `theme gallery <slug>` generates a gallery with only that theme.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'gallery.html'
            result = run('theme', 'gallery', 'nord', '--output', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            html = out.read_text(encoding='utf-8')
            # The gallery contains nord but not dracula.
            self.assertIn('nord', html)
            # Only one card row for a single-theme gallery.
            self.assertEqual(html.count('class="theme-row"'), 1)

    def test_theme_gallery_output_option(self):
        # `--output` sets the gallery file path (DECISION §2).
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'custom.html'
            result = run('theme', 'gallery', '--output', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())

    def test_no_nav_leaves_empty_container(self):
        """--no-nav must remove the links and keep the container.

        The version this replaces could not fail. It sliced on the FIRST
        occurrence of `series-list`, which is in the inline <style> block
        at offset ~32000, then cut at the first `</div>` -- so it examined
        17370 characters of CSS, byte-identical with and without the flag,
        and looked for `<a href` in it. Measured: the examined slice
        contained no anchor in either case. Making --no-nav a complete
        no-op (`if include_nav:` -> `if True:`) left all 742 tests green.

        Two changes: slice the BODY, and carry a positive control, so the
        test also fails if the fixture stops producing links at all."""
        meta = ('<!-- lwp:meta -->\npage_dest: {dest}\npage_title: {t}\n'
                'nav_title: {t}\nnav_desc: {t}\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k74\nkicker: K\n# {t}\nsummary: S.\n'
                '\n---\n\n<!-- lwp:slide:series-nav -->\nslug: k75\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            for dest, src, title in (('a.html', 'a.md', 'A'),
                                     ('b.html', 'b.md', 'B')):
                (root / 'sources' / src).write_text(
                    meta.format(dest=dest, t=title), encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'},
                {'page_dest': 'b.html', 'page_source': 'b.md',
                 'nav_title': 'B', 'nav_desc': 'B'},
            ]}), encoding='utf-8')

            def body_of(page):
                html = (root / page).read_text(encoding='utf-8')
                # The <style> block also names .series-list, so anchor on
                # the markup: the OPENING TAG, not the bare class name.
                marker = '<div class="series-list">'
                self.assertIn(marker, html, 'no series-list in the body')
                return html.split(marker, 1)[1].split('</section>', 1)[0]

            # Positive control first: without the flag there ARE links, so
            # the assertion below is about the flag and not about an empty
            # fixture.
            self.assertEqual(run('build', str(root), '--output',
                                 str(root / 'with')).returncode, 0)
            with_nav = body_of('with/a.html')
            # `class="series-item series-link"`: match the token, not a
            # whole attribute I guessed at.
            self.assertIn('series-link', with_nav)

            self.assertEqual(run('build', str(root), '--output',
                                 str(root / 'without'), '--no-nav').returncode,
                             0)
            without = body_of('without/a.html')
            self.assertNotIn('series-link', without,
                             'the nav links survived --no-nav:\n' + without)
            self.assertNotIn('<a href', without,
                             'an anchor survived --no-nav:\n' + without)

    def test_no_index_skips_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--no-index')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'public' / 'index.html').exists())
            # The article page is still built.
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_no_readme_skips_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            # Build once to create the README, then rebuild with --no-readme
            # after deleting it, to prove the second build did not write it.
            run('build', str(root), '--output', str(root / 'public'))
            self.assertTrue((root / 'README.md').exists())
            (root / 'README.md').unlink()
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--no-readme')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'README.md').exists())

    def test_drafts_only_builds_only_drafts(self):
        # --drafts-only (DECISION §4): only status: draft articles are built.
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_source: a.md\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k76\nkicker: T\n# Title A\nsummary: S.\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_source: b.md\n'
            'nav_title: B\nnav_desc: B\nstatus: draft\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k77\nkicker: T\n# Title B\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
            (root / 'sources' / 'b.md').write_text(md_b, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'},
                {'page_dest': 'b.html', 'page_source': 'b.md',
                 'nav_title': 'B', 'nav_desc': 'B', 'status': 'draft'},
            ]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--drafts-only')
            self.assertEqual(result.returncode, 0, result.stderr)
            # b.html (draft) is built; a.html (published) is not.
            self.assertTrue((root / 'public' / 'b.html').exists())
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_drafts_only_with_no_drafts_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--drafts-only')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No draft', result.stderr)

    def test_open_opens_browser_after_build(self):
        """--open (DECISION §1 Phase 3) opens the browser on the result.

        The browser is a recording wrapper, not /bin/true. Pointing BROWSER
        at a no-op and asserting the exit code proved only that the build
        succeeded: `if args.get('--open'):` -> `if False:` left this green,
        which is to say nothing here ever observed a browser being opened.
        The wrapper writes its argv to a file, so the assertion is that a
        URL reached it -- and that the URL is the page just built."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            record = Path(tmp) / 'opened.txt'
            fake = Path(tmp) / 'fake-browser'
            fake.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "$@" >> {record}\n',
                encoding='utf-8')
            fake.chmod(0o755)
            env = {'BROWSER': str(fake)}
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--open', env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(record.exists(),
                            'the browser was never invoked')
            opened = record.read_text(encoding='utf-8').strip()
            self.assertEqual(
                opened, (root / 'public' / 'index.html').resolve().as_uri(),
                'the browser was opened on something other than the build')

    def test_a_build_without_open_opens_nothing(self):
        # The negative half: without the flag, no browser. Without this the
        # test above is satisfied by a build that always opens one.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            record = Path(tmp) / 'opened.txt'
            fake = Path(tmp) / 'fake-browser'
            fake.write_text(
                f'#!/bin/sh\nprintf "%s\\n" "$@" >> {record}\n',
                encoding='utf-8')
            fake.chmod(0o755)
            result = run('build', str(root), '--output', str(root / 'public'),
                         env={'BROWSER': str(fake)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(record.exists(),
                             'a build with no --open opened a browser')

    def test_inline_images_embeds_base64_and_skips_img_dir(self):
        # --inline-images: images are embedded as base64 data URIs, and
        # the img/ directory is not copied to the output.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k78\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k79\nkicker: F\n## Fiche\nfact-label: L\n\n'
            'Inline ![red](img/red.png) and standalone:\n\n'
            '![Red](img/red.png "Cap")\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            # Create a minimal 1x1 PNG in sources/img/.
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'red.png').write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
                b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
                b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--inline-images')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # Both images are embedded as data URIs.
            self.assertEqual(html.count('data:image/png;base64,'), 2,
                             f'expected 2 inlined images, got '
                             f'{html.count("data:image/png;base64,")}')
            # No img/ directory in the output.
            self.assertFalse((root / 'public' / 'img').exists(),
                             'img/ was copied despite --inline-images')

    def test_inline_images_reaches_an_included_article_file(self):
        """The option promises "a single self-contained HTML file" (§8.4),
        and for an image written in a slide it delivered. For an image
        inside a file pulled in by a `full-article` slide it did not:
        `build_article` called `convert_markdown` without `inline_images=`
        or `sources_dir=` while every other call site passed both.

        Measured on the shipped demo, built clean: 0 `data:image` URIs, 1
        relative `src="img/…"`, and no `public/img/` — a broken page, exit
        0. Worse, an earlier ordinary build leaves `public/img/` behind and
        the image keeps showing, so the breakage only surfaces on a clean
        deploy, which is when this option is reached for (BACKLOG B23).

        The whole suite passed with the fix reverted, which is why this
        test exists: the defect had no guard at all."""
        png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
               b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
               b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
               b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k80\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k81\narticle: long.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(str(Path(tmp) / 'series'), md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'fig.png').write_bytes(png)
            # The image lives ONLY in the included file, never in a slide.
            (root / 'sources' / 'long.md').write_text(
                'Body paragraph.\n\n![figure](img/fig.png)\n\nAfter.\n',
                encoding='utf-8')

            result = run('build', str(root), '--output', str(root / 'public'),
                         '--inline-images')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')

            self.assertIn('data:image/png;base64,', html,
                          "the included article's image was not inlined")
            self.assertNotIn('src="img/', html,
                             'a relative src survived --inline-images')
            self.assertFalse((root / 'public' / 'img').exists(),
                             'img/ was copied despite --inline-images — the '
                             'page would look fine and hide the defect')

    def test_inline_images_refuses_to_ship_a_page_that_is_not_self_contained(self):
        """Raw HTML is passed through unconverted by design (§6.2), so an
        `<img>` written that way is never inlined. Under --inline-images
        the image directory is not copied either, so such a page shipped
        with a dangling reference and exit 0 — the promise broken in
        silence, which is the shape of defect this option most needs
        protecting from."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k82\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k83\nkicker: F\n## Fiche\nfact-label: L\n\n'
            '<img src="img/raw.png" alt="raw">\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(str(Path(tmp) / 'series'), md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'raw.png').write_bytes(b'\x89PNG\r\n\x1a\n')

            hard = run('build', str(root), '--output', str(root / 'public'),
                       '--inline-images')
            self.assertEqual(hard.returncode, 1, hard.stdout)
            self.assertIn('img/raw.png', hard.stderr,
                          'the error does not name the offending src')
            self.assertIn('--inline-images', hard.stderr)

            # And the guard is scoped to the option: the same series builds
            # green without it, because then img/ IS copied.
            soft = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(soft.returncode, 0, soft.stderr)
            self.assertTrue((root / 'public' / 'img' / 'raw.png').exists())

    def test_inline_images_never_reads_outside_the_article_dir(self):
        """--inline-images read ANY file the build user could open and
        base64'd it into the published page. `src` is attacker-reachable
        (an LLM-authored article, a CMS export, a cloned series repo), the
        extractor permits a leading `/` and `..`, and `Path(dir) / '/etc/
        passwd'` discards the left side — so `![](../../secret/id_rsa)`
        published the key. It also walked past copy_images' symlink guard:
        the same series warned and skipped on a plain build, and inlined
        the secret with the flag.

        Three vectors, one barrier. The legitimate image must still be
        inlined in the same build, or the fix is just a break."""
        secret = None
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k84\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k85\nkicker: F\n## Fiche\nfact-label: L\n\n'
            '![up](../../secret/id_rsa)\n\n'
            '![abs](/etc/hostname)\n\n'
            '![sym](img/leak.png)\n\n'
            '![ok](img/red.png)\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / 'secret'
            secret.mkdir()
            (secret / 'id_rsa').write_bytes(b'ROOT-SECRET-PRIVATE-KEY-MATERIAL')
            root = scaffold(str(Path(tmp) / 'series'), md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'red.png').write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
                b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
                b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
            try:
                (root / 'sources' / 'img' / 'leak.png').symlink_to(
                    secret / 'id_rsa')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable on this filesystem')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--inline-images')
            # Each refusal is reported, not silent -- that is this test's
            # subject and it is unchanged.
            self.assertEqual(result.stderr.count('escaping the article'), 3,
                             result.stderr)
            # Since v0.38.0 the build then fails rather than shipping a page
            # whose three refused images are still relative `src` while
            # `public/img/` is deliberately absent (BACKLOG B23). Exiting 0
            # there meant publishing a page with three dangling references
            # under the one option whose contract is that the file travels
            # alone. Nothing is written, so nothing can leak.
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists(),
                             'the page was written despite the refusal')
            # Belt and braces: if a future change does write it, the secret
            # must still be in none of its data URIs.
            if (root / 'public' / 'a.html').exists():
                html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
                for m in re.finditer(r'data:[^;]+;base64,([A-Za-z0-9+/=]+)', html):
                    self.assertNotIn(b'SECRET', base64.b64decode(m.group(1)),
                                     'a file outside sources/ was published')

    def test_inline_images_still_inlines_the_legitimate_image(self):
        """The other half of the guard above, on its own fixture: barring
        the escaping paths must not cost the ordinary ones. Kept separate
        because the escaping build now fails, and a test that asserts both
        a refusal and a success on one build can only assert one of them."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k86\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k87\nkicker: F\n## Fiche\nfact-label: L\n\n'
            '![ok](img/red.png)\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(str(Path(tmp) / 'series'), md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'red.png').write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
                b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
                b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--inline-images')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('data:image/png;base64,', html)
            self.assertNotIn('src="img/', html)

    def test_inline_images_off_by_default(self):
        # Without --inline-images: images stay as relative paths and
        # img/ is copied to the output (the standard behaviour).
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k88\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k89\nkicker: F\n## Fiche\nfact-label: L\n\n'
            'Inline ![red](img/red.png) in text.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'red.png').write_bytes(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
                b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
                b'\x8d\xa5K>\x00\x00\x00\x00IEND\xaeB`\x82')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('src="img/red.png"', html)
            self.assertNotIn('data:image', html)
            self.assertTrue((root / 'public' / 'img' / 'red.png').exists())

    def test_dry_run_writes_nothing(self):
        # --dry-run (DECISION §4): journal the writes without touching disk.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--dry-run', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            # Nothing was written: public/ does not exist.
            self.assertFalse((root / 'public').exists())
            # The journal mentions the would-be writes on stderr.
            self.assertIn('would write', result.stderr)

    def test_dry_run_init_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / 's')
            result = run('--dry-run', 'init', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(Path(target).exists())
            self.assertIn('would mkdir', result.stderr)

    def test_dry_run_theme_gallery_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'gallery.html'
            result = run('--dry-run', 'theme', 'gallery', '--output', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(out.exists())
            self.assertIn('would write', result.stderr)

    @staticmethod
    def _orphan_series(tmp):
        """Builds once, renames the article's output, builds again — so
        `a.html` is a REAL orphan: a file a previous build declared and
        this one no longer does. Returns the series root.

        Dropping a hand-written file into public/ and calling it an orphan
        is what these tests used to do, and it hid the defect: under that
        reading `clean --force` removed CNAME, .nojekyll, robots.txt,
        404.html and a whole .git/ from a published site, because a build
        declares none of those. An orphan is defined by the manifest pair,
        not by absence from the current one."""
        root = scaffold(tmp, _MINIMAL_MD)
        run('build', str(root), '--output', str(root / 'public'))
        entry = json.loads((root / 'series.json').read_text(encoding='utf-8'))
        entry['articles'][0]['page_dest'] = 'renamed.html'
        (root / 'series.json').write_text(json.dumps(entry), encoding='utf-8')
        run('build', str(root), '--output', str(root / 'public'))
        return root

    def test_clean_dry_run_lists_orphans(self):
        # `clean` (DECISION §3): dry-run by default, lists orphans.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._orphan_series(tmp)
            result = run('clean', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('a.html', result.stdout)
            self.assertIn('would be removed', result.stdout)
            # Dry-run: the orphan is still there.
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_clean_force_removes_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._orphan_series(tmp)
            result = run('clean', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists())
            # The page this build DOES declare survives.
            self.assertTrue((root / 'public' / 'renamed.html').exists())

    def test_clean_never_removes_what_no_build_made(self):
        """The deployment sidecars of a published static site. Every one of
        these was deleted by the previous rule, measured, including the
        `.git/` of a gh-pages worktree — the layout the shipped
        `.gitlab-ci.yml` encourages. `rglob('*')` does not skip dotfiles,
        which is why the hidden ones went too."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._orphan_series(tmp)
            pub = root / 'public'
            (pub / 'CNAME').write_text('example.org', encoding='utf-8')
            (pub / '.nojekyll').write_text('', encoding='utf-8')
            (pub / 'robots.txt').write_text('User-agent: *', encoding='utf-8')
            (pub / '404.html').write_text('<p>gone', encoding='utf-8')
            (pub / '.git').mkdir()
            (pub / '.git' / 'HEAD').write_text('ref: x', encoding='utf-8')
            (pub / 'css').mkdir()
            (pub / 'css' / 'site.css').write_text('body{}', encoding='utf-8')
            result = run('clean', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            for kept in ('CNAME', '.nojekyll', 'robots.txt', '404.html',
                         '.git/HEAD', 'css/site.css'):
                self.assertTrue((pub / kept).exists(),
                                f'clean removed {kept}, which no build made')
            # ... and the real orphan still goes.
            self.assertFalse((pub / 'a.html').exists())

    def test_clean_under_dry_run_removes_nothing(self):
        """`--dry-run clean --force` deleted for real: the unlink was the
        one filesystem call outside the helper layer, and the guard test's
        verb alphabet held only creation verbs, so nothing caught it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._orphan_series(tmp)
            before = sorted(p.name for p in (root / 'public').rglob('*'))
            result = run('--dry-run', 'clean', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())
            self.assertEqual(
                before, sorted(p.name for p in (root / 'public').rglob('*')))
            # And it says so, rather than reporting a removal that
            # did not happen.
            self.assertIn('would remove', result.stdout + result.stderr)
            self.assertNotIn('  removed ', result.stdout)

    def test_clean_refuses_a_series_directory(self):
        """`build --output <series root>` is accepted, which puts a manifest
        at the root; a clean aimed there by --output or LWP_OUTPUT_DIR then
        had the sources in scope. Measured before the guard: 24 files gone,
        including series.json, every article, the templates, the language
        packs and the bundled executable."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root))
            env = dict(os.environ, LWP_OUTPUT_DIR=str(root))
            result = subprocess.run(
                [sys.executable, str(EXECUTABLE), 'clean', str(root), '--force'],
                capture_output=True, text=True, env=env)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('series.json', result.stderr)
            self.assertTrue((root / 'series.json').exists())
            self.assertTrue((root / 'sources' / 'a.md').exists())

    def test_clean_without_manifest_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            # No build yet → no manifest.
            result = run('clean', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('manifest', result.stderr.lower())

    def test_clean_with_no_orphans_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('clean', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No orphan', result.stdout)

    def test_clean_takes_the_output_it_was_built_with(self):
        """cmd_clean has always read --output; the parser refused it.

        A site built with `build --output dist` could only be cleaned by
        setting LWP_OUTPUT_DIR, because the option table for `clean` did
        not list the option the command's own body reads. The branch was
        unreachable from the command line."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            dist = Path(tmp) / 'dist'
            run('build', str(root), '--output', str(dist))
            entry = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            entry['articles'][0]['page_dest'] = 'renamed.html'
            (root / 'series.json').write_text(json.dumps(entry), encoding='utf-8')
            run('build', str(root), '--output', str(dist))
            result = run('clean', str(root), '--output', str(dist), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((dist / 'a.html').exists())
            self.assertTrue((dist / 'renamed.html').exists())

    def test_an_image_deleted_from_the_source_stops_being_published(self):
        """The manifest lists what the build MADE, not what is lying about.

        `_write_manifest` used to rescan output/img and list whatever it
        found there, so every rebuild re-declared an image whose source had
        been deleted. Being declared, it was never an orphan; never an
        orphan, `clean` never offered it; and a photograph withdrawn on
        purpose stayed on the published site for as long as the site
        lived. Measured, then fixed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            (root / 'sources' / 'img').mkdir()
            png = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8'
                'z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
            (root / 'sources' / 'img' / 'doomed.png').write_bytes(png)
            (root / 'sources' / 'img' / 'kept.png').write_bytes(png)
            pub = root / 'public'
            run('build', str(root), '--output', str(pub))
            self.assertTrue((pub / 'img' / 'doomed.png').exists())

            (root / 'sources' / 'img' / 'doomed.png').unlink()
            run('build', str(root), '--output', str(pub))
            manifest = json.loads(
                (pub / '.lwp-manifest.json').read_text(encoding='utf-8'))
            self.assertNotIn('img/doomed.png', manifest['files'],
                             'a rebuild re-declared an image that is gone '
                             'from the source')
            self.assertIn('img/kept.png', manifest['files'])

            result = run('clean', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((pub / 'img' / 'doomed.png').exists())
            self.assertTrue((pub / 'img' / 'kept.png').exists(),
                            'clean took the image the source still has')

    def test_watch_rebuilds_on_change_and_serves_the_result(self):
        """The two existing watch tests prove the INITIAL build runs and
        the option table accepts the flags. Gutting the rebuild loop and
        disabling --serve left the whole suite green: the feature is
        rebuild-on-change, and nothing measured it. `--port` and `--serve`
        appeared zero times in the test tree.

        This drives the real thing: edit a source, wait for the rebuild,
        read the new text out of the built page AND over HTTP."""
        import signal
        import socket
        import subprocess as sp
        import threading as _threading
        import time as _time
        import urllib.request

        with socket.socket() as probe:          # a port nothing else holds
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]

        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            out = root / 'public'
            proc = sp.Popen(
                [sys.executable, str(EXECUTABLE), 'watch', str(root),
                 '--output', str(out), '--serve', '--port', str(port)],
                stdout=sp.PIPE, stderr=sp.PIPE, text=True,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            lines = []
            _threading.Thread(target=lambda: lines.extend(proc.stdout),
                              daemon=True).start()

            def wait_for(needle, seconds=20):
                end = _time.time() + seconds
                while _time.time() < end:
                    if any(needle in l for l in lines):
                        return True
                    if proc.poll() is not None:
                        return False
                    _time.sleep(0.1)
                return False

            try:
                self.assertTrue(wait_for('[watch] polling'),
                                'watch never reached its polling loop:\n'
                                + ''.join(lines))
                self.assertTrue(any('serving' in l for l in lines),
                                '--serve started no server:\n' + ''.join(lines))

                # Edit a source and wait for the loop to notice.
                marker = 'REBUILT-BY-WATCH-MARKER'
                article = root / 'sources' / 'a.md'
                article.write_text(
                    article.read_text(encoding='utf-8').replace(
                        '# Title', '# ' + marker), encoding='utf-8')
                self.assertTrue(wait_for('[watch] rebuilt.'),
                                'watch never rebuilt after a source changed:\n'
                                + ''.join(lines))
                self.assertIn(marker,
                              (out / 'a.html').read_text(encoding='utf-8'),
                              'watch reported a rebuild that did not happen')

                # And the server hands back that same page.
                with urllib.request.urlopen(
                        f'http://127.0.0.1:{port}/a.html', timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertIn(marker, resp.read().decode('utf-8'))
            finally:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=10)
                except sp.TimeoutExpired:
                    proc.kill()

    def test_watch_is_a_known_command(self):
        # `watch` is recognized and builds once before polling. We can't
        # test the infinite loop in CI, but we can check the initial build
        # runs by sending SIGINT immediately after.
        import signal
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            import subprocess as sp
            import threading as _threading
            proc = sp.Popen([sys.executable, str(EXECUTABLE), 'watch',
                             str(root), '--output', str(root / 'public')],
                            stdout=sp.PIPE, stderr=sp.PIPE, text=True,
                            env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            import time as _time
            output = []
            reader = _threading.Thread(target=lambda: output.extend(proc.stdout),
                                       daemon=True)
            reader.start()
            # Wait for the actual polling loop, not an intermediate file. A
            # busy parallel runner can pause between the initial build and
            # cmd_watch's KeyboardInterrupt handler.
            deadline = _time.time() + 15
            while (_time.time() < deadline and
                   not any('[watch] polling' in line for line in output)):
                if proc.poll() is not None:
                    break
                _time.sleep(0.1)
            self.assertTrue(any('[watch] polling' in line for line in output),
                            'watch did not enter its polling loop')
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=10)
            err = proc.stderr.read()
            reader.join(timeout=2)
            out = ''.join(output)
            proc.stdout.close()
            proc.stderr.close()
            self.assertEqual(proc.returncode, 0, err)
            self.assertIn('[watch]', out)
            # The initial build wrote the page.
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_watch_accepts_the_build_output_switches(self):
        # README/GUIDE promise that watch takes the same output switches as
        # build; the option table must agree (it used to reject them
        # fatally as "Unknown option"). --drafts-only needs a draft in the
        # series, or the initial build stops before the polling loop.
        import signal
        draft_md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\nstatus: draft\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k90\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, draft_md)
            import subprocess as sp
            import threading as _threading
            proc = sp.Popen([sys.executable, str(EXECUTABLE), 'watch',
                             str(root), '--output', str(root / 'public'),
                             '--no-nav', '--no-index', '--no-readme',
                             '--drafts-only'],
                            stdout=sp.PIPE, stderr=sp.PIPE, text=True,
                            env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            import time as _time
            output = []
            reader = _threading.Thread(target=lambda: output.extend(proc.stdout),
                                       daemon=True)
            reader.start()
            deadline = _time.time() + 15
            while (_time.time() < deadline and
                   not any('[watch] polling' in line for line in output)):
                if proc.poll() is not None:
                    break
                _time.sleep(0.1)
            self.assertTrue(any('[watch] polling' in line for line in output),
                            'watch did not enter its polling loop')
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=10)
            err = proc.stderr.read()
            reader.join(timeout=2)
            out = ''.join(output)
            proc.stdout.close()
            proc.stderr.close()
            self.assertEqual(proc.returncode, 0, err)
            self.assertNotIn('Unknown option', out + err)

    def test_a_filesystem_refusal_is_an_error_line_not_a_traceback(self):
        """Every refusal this tool decides for itself prints `[ERROR]`.

        A refusal the filesystem decides -- read-only output, disk full, a
        directory where a file belongs -- came out as eleven frames of
        pathlib. The one class of failure the user cannot control was the
        one reported in a language about the program's insides, and it is
        the class most likely to be read by whoever is on call."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            pub = root / 'public'
            run('build', str(root), '--output', str(pub))
            # A directory where index.html goes: the write cannot succeed
            # and nothing in the tool anticipates it.
            (pub / 'index.html').unlink()
            (pub / 'index.html').mkdir()
            result = run('build', str(root), '--output', str(pub))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback (most recent call last)',
                             result.stderr)
            self.assertIn('[ERROR]', result.stderr)
            # It names the file the build was asked to write, not the
            # temporary this tool renames from.
            self.assertIn('index.html', result.stderr)
            self.assertNotIn('.tmp', result.stderr)
            # And it is reported as what it is. A disk the tool cannot
            # write to is not an "internal error": that wording sends the
            # reader to the bug tracker instead of to `df`.
            self.assertNotIn('internal error', result.stderr)

    def test_a_page_is_never_left_half_written(self):
        """Writes go to a sibling temporary and are renamed into place.

        In-place `write_text` truncates first: a build interrupted between
        truncate and flush leaves a served page that is half a document,
        and the reader on the other end of `watch --serve` gets it. The
        rename is atomic within a filesystem, which is why the temporary
        is a sibling."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            pub = root / 'public'
            run('build', str(root), '--output', str(pub))
            # The inode is the evidence, not the word `os.replace` in the
            # source: a rename creates a new file and unlinks the old, an
            # in-place write keeps the same one. The first version of this
            # test read the source and was satisfied by the docstring
            # that explains the rename.
            before = (pub / 'index.html').stat().st_ino
            run('build', str(root), '--output', str(pub))
            self.assertNotEqual(before, (pub / 'index.html').stat().st_ino,
                                'the page was truncated and rewritten in '
                                'place, so a reader can see half of it')
            # No fragment survives a SUCCESSFUL build either: a temporary
            # left behind is a file no manifest declares, so `clean` will
            # never offer to remove it.
            strays = [p.name for p in pub.rglob('*') if p.name.endswith('.tmp')]
            self.assertEqual(strays, [])

    def test_no_bare_filesystem_write_outside_helpers(self):
        """--dry-run relies on every filesystem write going through the
        _write_file/_mkdir/_copy/_copytree/_remove helpers. This AST test
        guards that no bare call exists outside them in the executable.

        THE ALPHABET IS THE TEST. An earlier version listed only creation
        verbs — write_text, mkdir, shutil.copy* — so when `clean` arrived
        with a bare Path.unlink() it walked straight through a guard built
        for what writes, and `--dry-run clean --force` deleted files for a
        whole release. A guard is only as wide as its verb list, so the
        list below covers both sides: what creates, and what destroys.

        Uses a parent-tracking walk so the check is by function name, not
        by line number — robust against the helpers moving in the file."""
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        HELPER_NAMES = {'_write_file', '_mkdir', '_copy', '_copytree', '_remove'}
        # The one allowed bare print to stderr is inside log() itself.
        # validate_page_scripts is the one documented exception: it writes a
        # temp .js under $TMPDIR to run `node --check` and unlinks it in a
        # finally. It never touches a path the user named, so --dry-run has
        # nothing to journal there.
        ALLOWED_IN = HELPER_NAMES | {'log', 'validate_page_scripts'}
        # Methods on a Path (or anything else) that create or destroy.
        PATH_METHODS = {
            'write_text', 'write_bytes', 'mkdir', 'touch',   # create
            'unlink', 'rmdir',                               # destroy
        }
        # Module-level functions, by module.
        MODULE_FUNCS = {
            'shutil': {'copy', 'copy2', 'copyfile', 'copytree', 'copymode',
                       'copystat', 'move', 'rmtree'},
            'os': {'remove', 'unlink', 'rmdir', 'removedirs', 'makedirs',
                   'mkdir', 'rename', 'replace', 'truncate', 'symlink',
                   'link'},
        }
        violations = []

        # Walk the tree tracking the enclosing function name. ast.walk
        # doesn't give parents, so we do our own recursive walk with a stack.
        def walk_with_scope(node, enclosing):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef):
                    walk_with_scope(child, child.name)
                else:
                    walk_with_scope(child, enclosing)
            # Now check this node itself
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    mod = (func.value.id
                           if isinstance(func.value, ast.Name) else None)
                    if mod in MODULE_FUNCS and func.attr in MODULE_FUNCS[mod]:
                        if enclosing not in ALLOWED_IN:
                            violations.append(
                                f'line {node.lineno}: {mod}.{func.attr}() '
                                f'in {enclosing}')
                    elif mod not in MODULE_FUNCS and func.attr in PATH_METHODS:
                        if enclosing not in ALLOWED_IN:
                            violations.append(
                                f'line {node.lineno}: .{func.attr}() in {enclosing}')
                # A bare open(path, 'w') bypasses every helper too. Mode is
                # the second positional or the `mode` keyword; a mode that
                # is not a literal is reported rather than assumed safe.
                elif isinstance(func, ast.Name) and func.id == 'open':
                    mode = None
                    if len(node.args) > 1:
                        mode = node.args[1]
                    for kw in node.keywords:
                        if kw.arg == 'mode':
                            mode = kw.value
                    if mode is not None:
                        writes = (not isinstance(mode, ast.Constant)
                                  or any(c in str(mode.value)
                                         for c in 'wxa+'))
                        if writes and enclosing not in ALLOWED_IN:
                            violations.append(
                                f'line {node.lineno}: open(..., write mode) '
                                f'in {enclosing}')
        walk_with_scope(tree, None)
        self.assertFalse(violations,
                         f'Bare filesystem writes outside helpers found:\n'
                         + '\n'.join(violations))

    @staticmethod
    def _complete(script, words, cword):
        """Sources an emitted completion script in bash, calls the function
        the way the shell would, and returns what it offered.

        Reading the script as a string proves it was printed. This runs it."""
        prog = (
            script + '\n'
            'COMP_WORDS=(' + ' '.join(shlex.quote(w) for w in words) + ')\n'
            f'COMP_CWORD={cword}\n'
            '_lightwebpres_completion\n'
            'printf "%s\\n" "${COMPREPLY[@]}"\n'
        )
        r = subprocess.run(['bash', '-c', prog], capture_output=True,
                           text=True)
        return [line for line in r.stdout.splitlines() if line]

    def test_completion_bash_generates_valid_script(self):
        # `completion --shell bash` prints a bash completion script.
        result = run('completion', '--shell', 'bash')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('_lightwebpres_completion', result.stdout)
        self.assertIn('complete -F _lightwebpres_completion lightwebpres',
                     result.stdout)
        # The script lists the root commands.
        self.assertIn('init', result.stdout)
        self.assertIn('build', result.stdout)
        self.assertIn('verify', result.stdout)

    def test_completion_zsh_generates_valid_script(self):
        """The zsh output is the bash function with a different footer, and
        that is legitimate ONLY with bashcompinit in front of it.

        zsh has no COMP_WORDS, no COMPREPLY and no compgen; `compdef` over
        a function written in that dialect binds a widget that fails on its
        first line. The emitted script shipped exactly that. What the two
        string assertions here used to check -- a function name and a
        compdef line -- were both present the whole time it was broken.

        The function body is exercised under bash (same text, and bash is
        what bashcompinit emulates); no zsh is installed in this
        environment, so the ORDER of the bootstrap is checked as text."""
        result = run('completion', '--shell', 'zsh')
        self.assertEqual(result.returncode, 0, result.stderr)
        script = result.stdout
        self.assertIn('_lightwebpres_completion', script)
        self.assertIn('compdef _lightwebpres_completion lightwebpres', script)
        self.assertIn('bashcompinit', script,
                      'a bash-dialect function bound in zsh with no shims')
        self.assertLess(script.index('bashcompinit'),
                        script.index('compdef _lightwebpres_completion'),
                        'compdef binds the widget before the dialect exists')
        # The body is the bash dialect, so it has to work in the bash
        # dialect. `compdef` is not a bash builtin and errors harmlessly;
        # the function is defined by then.
        self.assertEqual(self._complete(script, ['lightwebpres', 'bu'], 1),
                         ['build'])

    def test_completion_unknown_shell_is_fatal(self):
        result = run('completion', '--shell', 'fish')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('bash', result.stderr)
        self.assertIn('zsh', result.stderr)

    def test_completion_lists_options(self):
        result = run('completion', '--shell', 'bash')
        self.assertEqual(result.returncode, 0, result.stderr)
        # The script must list the global options.
        for opt in ('--lang', '--quiet', '--verbose', '--dry-run',
                    '--version', '--help'):
            self.assertIn(opt, result.stdout)

    def test_completion_stays_in_sync_with_command_tables(self):
        """The completion script is generated from _SHORTCUTS,
        _SERIES_VERBS, _THEME_VERBS, _TEMPLATE_VERBS and
        _COMMAND_OPTIONS. A command or option added to those tables and
        not to the script must fail here, so an evolution of the CLI
        cannot silently break completion.

        BY RUNNING IT, not by searching the text. This test used to
        assert `name in script` for each table entry, which a
        seventy-line shell script satisfies by accident: `demo` appears
        in the root list, in a comment, and inside `--demo`-ish option
        names, so the check passed on a script that offered none of it.
        Measured: replacing the whole series-verb list with the single
        word `build` left this test green, and so did dropping
        `template show`/`write` when they arrived. It was decorative for
        every table it named.

        Now it compares the offered SET against the table, both
        directions, so a missing entry and a stray one both fail.

        The commands, here. The options moved out to the three tests
        further down, because there is no such thing as "the option
        list": every command has its own, and the single list this test
        used to assert was the union that put `--polarity` in front of
        someone typing `build --`."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        self.assertEqual(
            sorted(self._complete(script, ['lightwebpres', ''], 1)),
            sorted(set(lwp._SHORTCUTS) | {'series', 'theme', 'template'}),
            'the root command list is not what the tables say')

    def test_completion_offers_nothing_the_tool_refuses(self):
        """The lists are derived from the tables in BOTH directions.

        The sync test above walks the tables and looks for each name in
        the script, so anything appended by hand is invisible to it. Two
        things had been appended: `theme set`, which the tool refuses by
        name -- "the theme node is the catalogue and never modifies a
        series" -- and a second `theme` under `series`, where the verb
        table already has one. A completion that offers a refused command
        is the program telling you to type what it will reject."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        self.assertEqual(
            sorted(self._complete(script, ['lightwebpres', 'theme', ''], 2)),
            sorted(lwp._THEME_VERBS))
        self.assertEqual(
            sorted(self._complete(script, ['lightwebpres', 'series', ''], 2)),
            sorted(lwp._SERIES_VERBS))
        self.assertEqual(
            sorted(self._complete(script, ['lightwebpres', 'template', ''], 2)),
            sorted(lwp._TEMPLATE_VERBS))
        # `template show <TAB>` offers the three files and not the
        # directory listing, which is what a closed set deserves.
        for verb in ('show', 'write'):
            self.assertEqual(
                sorted(self._complete(
                    script, ['lightwebpres', 'template', verb, ''], 3)),
                sorted(lwp.tool_owned_files()), verb)
        # And the offer is real: every verb offered must be one the tool
        # accepts. `theme set` exits non-zero with a message that names
        # the right spelling.
        for verb in self._complete(script, ['lightwebpres', 'theme', ''], 2):
            result = run('theme', verb, '--help')
            self.assertEqual(result.returncode, 0,
                             f'completion offers `theme {verb}`, which the '
                             f'tool refuses: {result.stderr}')

    @staticmethod
    def _command_paths(lwp):
        """Every option-taking path a user can type, paired with the
        dispatch key the tool's OWN resolver gives it.

        Built by asking `_resolve_command`, not by a second copy of the
        verb tables: a path the completion offers and the resolver reads
        differently is exactly the bug this file is here to catch."""
        typed = list(lwp._SHORTCUTS)
        typed += [f'series {v}' for v in lwp._SERIES_VERBS]
        typed += [f'theme {v}' for v in lwp._THEME_VERBS]
        typed += [f'template {v}' for v in lwp._TEMPLATE_VERBS]
        typed += ['series theme set', 'series slug set']
        paths = []
        for path in typed:
            key, _rest = lwp._resolve_command(path.split() + ['x'])
            paths.append((path, key))
        return paths

    def test_completion_offers_only_options_the_command_accepts(self):
        """Reported from a real shell: `build --<TAB>` put `--polarity`,
        `--hue`, `--family`, `--shell` and `--format` in front of someone,
        and `build --polarity dark` then answered "Unknown option:
        --polarity (not an option of `build`)". The script emitted
        `all_opts` -- the UNION of every command's options -- for every
        command, so the completion was the program telling you to type
        what the program will reject.

        Both directions, against the table the parser refuses against:
        nothing offered that the command refuses, and nothing withheld
        that it accepts. The second half is what catches a command
        dropping out of the case block and falling to the default arm,
        which is a narrower lie but a lie all the same.

        `--version` is the one global that is NOT offered after a command,
        because it is the one global a command refuses -- see the postfix
        test below, which runs the tool rather than reading a table."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        for path, key in self._command_paths(lwp):
            words = ['lightwebpres'] + path.split() + ['--']
            offered = set(self._complete(script, words, len(words) - 1))
            self.assertTrue(offered, f'`{path} --` offers nothing at all')
            accepted = lwp._COMMAND_OPTIONS[key] | lwp._GLOBAL_OPTIONS
            self.assertFalse(
                offered - accepted,
                f'completion offers {sorted(offered - accepted)} for '
                f'`{path}`, which `{lwp.canonical(key)}` refuses')
            withheld = accepted - offered - {'--version'}
            self.assertFalse(
                withheld,
                f'completion withholds {sorted(withheld)} from `{path}`, '
                f'which `{lwp.canonical(key)}` accepts')

    def test_completion_offers_nothing_before_a_command_but_globals(self):
        """`lightwebpres --polarity dark theme list` never reaches
        parse_cli_options: the first word IS the command, and the answer
        is "Unknown command: --polarity". Only the globals are read in
        that position, so only the globals belong in the offer.

        A bare node is the same case one word later: `series --quiet
        build` is read as the verb `--quiet` and refused by name."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        self.assertEqual(
            sorted(self._complete(script, ['lightwebpres', '--'], 1)),
            sorted(lwp._GLOBAL_OPTIONS))
        for node in ('series', 'theme', 'template'):
            self.assertEqual(
                self._complete(script, ['lightwebpres', node, '--'], 2),
                ['--help'], node)
        # And the refusal is real, not a reading of the table.
        result = run('--polarity', 'dark', 'theme', 'list')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unknown command', result.stderr)

    def test_every_option_the_completion_offers_survives_the_parser(self):
        """The test above compares two tables. This one runs the parser
        on every single word the completion offers, for every command,
        and fails if any of them exits.

        `parse_cli_options` is the function that prints "Unknown option"
        and calls sys.exit(1); calling it directly is the refusal itself,
        not a description of it. Each option is given a value, which a
        flag simply leaves as a positional and a value option consumes."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        refused = []
        for path, key in self._command_paths(lwp):
            words = ['lightwebpres'] + path.split() + ['--']
            for opt in self._complete(script, words, len(words) - 1):
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        lwp.parse_cli_options(key, [opt, 'x'])
                except SystemExit:
                    refused.append(f'{path} {opt}')
        self.assertFalse(refused,
                         'the completion offers words the parser refuses: '
                         + ', '.join(refused))

    def test_the_only_global_refused_after_a_command_is_not_offered(self):
        """`verify --version` is fatal (B22: --version reports the version
        and exits, it does not modify a command), and it is the sole
        reason the offer is the globals MINUS one rather than the globals.
        Measured by running the tool, so the day that decision is reversed
        this test says so instead of the completion quietly disagreeing
        with the parser."""
        lwp = load_lightwebpres_module()
        result = run('verify', '--version')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('--version', result.stderr)
        script = run('completion', '--shell', 'bash').stdout
        self.assertNotIn(
            '--version',
            self._complete(script, ['lightwebpres', 'verify', '--'], 2))
        # ... and it IS offered where it works.
        self.assertIn('--version',
                      self._complete(script, ['lightwebpres', '--'], 1))

    def test_the_module_docstring_lists_every_command(self):
        """The usage block at the top of the source -- what a reader of
        the file sees first, and what `pydoc` prints -- knew nothing
        about `clean`, `watch` or `completion`. `print_help()` was
        complete the whole time, so nothing noticed.

        Canonical names only: the docstring is not the place to teach a
        deprecated alias."""
        lwp = load_lightwebpres_module()
        usage = lwp.__doc__
        for name in sorted({lwp.canonical(v) for v in lwp._SHORTCUTS.values()}):
            self.assertIn(f'lightwebpres {name}', usage,
                          f'the usage block does not mention {name!r}')
        for opt in sorted(lwp._GLOBAL_OPTIONS):
            self.assertIn(opt, usage,
                          f'the usage block does not mention {opt!r}')

    def test_help_names_every_command_a_user_can_type(self):
        """Structural, from the tables, because a needle list only ever
        catches what someone thought to add to it. `template show` and
        `template write` were absent from --help for a whole release and
        the suite was green: measured, deleting both entries changed no
        test result. --help is the "Full reference" the README promises,
        and a command missing from it is a command nobody finds."""
        lwp = load_lightwebpres_module()
        text = run('--help').stdout
        keys = (set(lwp._SHORTCUTS.values()) | set(lwp._SERIES_VERBS.values())
                | set(lwp._THEME_VERBS.values())
                | set(lwp._TEMPLATE_VERBS.values()))
        for name in sorted({lwp.canonical(k) for k in keys}):
            self.assertIn(f'lightwebpres {name}', text,
                          f'--help never names `{name}`')

    def test_helps_series_layout_is_the_layout_init_writes(self):
        """--help's SERIES DIRECTORY block is prose, and prose about a
        file list is the part that rots: it named `templates/nav.js` and
        `language/fr.json` as things `init` creates for a whole release
        after `init` stopped creating them, and nothing failed. The
        listing is a claim about the disk, so it is checked against a
        disk: scaffold a series and compare the two sets."""
        text = run('--help').stdout
        block = text.split('Written by `init`:', 1)[1].split(
            'Written by `build`:', 1)[0]
        named = {m.group(1).rstrip('/') for m in
                 re.finditer(r'^  (\S+)\s{2,}\S', block, re.M)}
        with tempfile.TemporaryDirectory() as tmp:
            series = os.path.join(tmp, 'series')
            result = run('init', series)
            self.assertEqual(result.returncode, 0, result.stderr)
            on_disk = set(os.listdir(series))
        self.assertEqual(
            named, on_disk,
            '--help says `init` writes %s; it writes %s'
            % (sorted(named), sorted(on_disk)))

    def test_every_command_is_wired_into_every_table(self):
        """A verb reaches the dispatcher through one table and is then
        governed by three others: which options it accepts, how many
        positionals it can use, and what a user should be told to type.
        A verb added to the first and forgotten in the rest still runs —
        it simply refuses every option, or answers with an internal key.

        Checked here rather than trusted, because each of those tables
        has a silent default: `.get(command, ...)`."""
        lwp = load_lightwebpres_module()
        keys = (set(lwp._SHORTCUTS.values()) | set(lwp._SERIES_VERBS.values())
                | set(lwp._THEME_VERBS.values())
                | set(lwp._TEMPLATE_VERBS.values()))
        self.assertEqual(sorted(keys - set(lwp._COMMAND_OPTIONS)), [])
        self.assertEqual(sorted(keys - set(lwp._MAX_POSITIONAL)), [])
        # And every canonical name is a form the dispatcher accepts:
        # `--help` on it must succeed, which no internal key does.
        for key in sorted(keys):
            words = lwp.canonical(key).split()
            r = run(*words, '--help')
            self.assertEqual(r.returncode, 0,
                             f'canonical(`{key}`) = `{" ".join(words)}`, '
                             f'which the tool refuses: {r.stderr}')

    def test_help_names_each_option_against_a_command_that_takes_it(self):
        """Every option in the OPTIONS block is introduced by the commands
        it belongs to -- `build:`, `demo/build/verify/watch:`,
        `init/series theme set:`. Those prefixes are data, and nothing
        checked them against the dispatcher.

        `--no-typography` was documented as `(build/check)` -- `check` is
        the retired spelling the program itself prints a [WARNING] about,
        so the help recommended the command the program tells you not to
        use. Two more of the same kind sat beside it: `SERIES DIRECTORY
        (created by install)` and `set-theme touches only the theme:
        line`.

        Checked here: the name is a canonical command, and the option is
        one that command actually accepts."""
        lwp = load_lightwebpres_module()
        help_text = run('--help').stdout
        block = help_text.split('OPTIONS', 1)[1]
        # The block ends at the next all-caps heading in column 0.
        block = re.split(r'\n[A-Z][A-Z /()]+\n', block)[0]
        canonical_names = ({lwp.canonical(v) for v in lwp._SHORTCUTS.values()}
                           | {'series theme set', 'series theme',
                              'template update', 'theme list', 'theme show',
                              'theme gallery'})
        checked = 0
        lines = block.splitlines()
        for i, line in enumerate(lines):
            m = re.match(r'^  (--[a-z-]+)', line)
            if not m or i + 1 >= len(lines):
                continue
            opt = m.group(1)
            intro = re.match(r'^    ([a-z][a-z /-]*(?:/[a-z][a-z /-]*)*):',
                             lines[i + 1])
            if not intro:
                continue  # "Global:", "Print the version" -- not a command list
            for name in intro.group(1).split('/'):
                # `build --only:` qualifies a command by the flag it is
                # used with; the command is the part before the flag.
                name = name.split(' --')[0].strip()
                if name in ('Global', 'For theme gallery'):
                    continue
                checked += 1
                self.assertIn(
                    name, canonical_names,
                    f'{opt} is documented against {name!r}, which is not a '
                    f'command a user should type')
                takes = lwp._COMMAND_OPTIONS.get(
                    lwp._SHORTCUTS.get(name, name), set())
                if takes:
                    self.assertIn(
                        opt, takes | lwp._GLOBAL_OPTIONS,
                        f'the help says {opt} belongs to {name!r}, which '
                        f'does not accept it')
        self.assertGreater(checked, 10,
                           'the OPTIONS block was not parsed -- its shape '
                           'changed and this test stopped reading it')

    def test_completion_function_produces_correct_completions(self):
        """Sources the bash completion script and tests the actual
        completion function with simulated COMP_WORDS. This verifies
        that the generated script is syntactically valid bash and that
        the completion logic works (not just that the words are listed
        in a comment)."""
        import subprocess
        script = run('completion', '--shell', 'bash').stdout
        # Build a test harness: source the script, set COMP_WORDS,
        # call the function, print COMPREPLY.
        test_cases = [
            # (COMP_CWORD, COMP_WORDS, expected_substring)
            (1, ['lightwebpres', ''], 'init'),  # root: 'in' prefix not needed
            (1, ['lightwebpres', 'b'], 'build'),
            (2, ['lightwebpres', 'series', ''], 'build'),
            (2, ['lightwebpres', 'theme', ''], 'list'),
            (2, ['lightwebpres', 'template', ''], 'update'),
            (2, ['lightwebpres', 'series', 'th'], 'theme'),
            (3, ['lightwebpres', 'series', 'theme', ''], 'set'),
        ]
        for cword, words, expected in test_cases:
            harness = (
                script
                + '\n'
                + f'COMP_WORDS=({" ".join(repr(w) for w in words)})\n'
                + f'COMP_CWORD={cword}\n'
                + '_lightwebpres_completion\n'
                + 'echo "${COMPREPLY[@]}"\n'
            )
            result = subprocess.run(
                ['bash', '-c', harness], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0,
                             f'bash failed for {words!r}:\n{result.stderr}')
            self.assertIn(expected, result.stdout,
                           f'completion of {words!r} (cword={cword}) '
                           f'did not include {expected!r}; got: {result.stdout!r}')


class MissingReferencedFilesAreFatal(unittest.TestCase):
    """§20.3/§22.8: a series.json entry whose page_source doesn't exist,
    or a full-article slide whose article: file doesn't exist, is a fatal
    build error — never dead links or a page published with the literal
    placeholder text, never exit 0."""

    def test_missing_full_article_file_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k91\narticle: missing_article.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('article file not found', result.stderr)
            # The corrupted page must not have been written
            written = (root / 'public' / 'a.html')
            if written.exists():
                self.assertNotIn('FULL_ARTICLE_PLACEHOLDER',
                                 written.read_text(encoding='utf-8'))


class ContentBeforeMetaBlockIsFatal(unittest.TestCase):
    """§22.7: only blank lines may precede <!-- lwp:meta -->. Stray
    content used to be silently discarded — invisible data loss."""

    def test_stray_content_before_meta_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, 'A stray first line\n' + _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('content found before', result.stderr)
            self.assertIn('A stray first line', result.stderr)

    def test_blank_lines_before_meta_are_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, '\n\n' + _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)


class DemoRefusesRealSeriesJson(unittest.TestCase):
    """§11.2: demo rewrites series.json wholesale, so it must refuse when
    the file already lists articles — the no-clobber guarantee covers the
    author's series list, not just the demo article filenames."""

    def test_demo_refuses_when_series_json_lists_articles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            result = run('init', str(root), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            (root / 'sources' / 'mine.md').write_text(_MINIMAL_MD, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps(
                {'articles': [{'page_source': 'mine.md'}]}), encoding='utf-8')
            result = run('demo', str(root), '--lang', 'en')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already lists', result.stderr)
            # The user's series.json is untouched
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            self.assertEqual(data['articles'][0]['page_source'], 'mine.md')

    def test_demo_still_works_on_a_fresh_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            result = run('init', str(root), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run('demo', str(root), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)


class NoEmptyDecorativeElements(unittest.TestCase):
    """Optional decorative elements are omitted when empty, not emitted
    as empty tags: the highlight caption span, the index version pill,
    the index card label and the series-nav label."""

    def test_highlight_without_caption_emits_no_caption_span(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k92\nkicker: T\n## Slide\nsummary: S.\nhighlight: 42 %\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('highlight-figure', html)
            self.assertNotIn('<span class="highlight-caption">', html)

    def test_index_without_series_version_emits_no_pill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('<span class="version-tag">', html)

    def test_series_nav_without_label_emits_no_label_div(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k93\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k94\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<div class="series-label">', html)


class ImageFiguresAndCaptions(unittest.TestCase):
    """§6.1: `![alt](src)` alone on a line renders as a <figure>; an
    optional quoted title after the path becomes a small centered
    <figcaption>. Mid-paragraph images render as plain <img> (no
    caption). Before this feature, `![alt](src)` rendered broken —
    a literal `!` followed by the link rules' output."""

    def _build_article_html(self, article_body, slide_body=None):
        slide = slide_body or '<!-- lwp:slide:full-article -->\nslug: k95\narticle: art.md\n'
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            + slide
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art.md').write_text(article_body or '', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_standalone_image_with_caption(self):
        html = self._build_article_html(
            '![A pie](img/pie.png "The finished pie")\n'
        )
        self.assertIn(
            '<figure class="figure"><img src="img/pie.png" alt="A pie">'
            '<figcaption class="figure-caption">The finished pie</figcaption></figure>',
            html,
        )

    def test_standalone_image_without_caption_has_no_figcaption(self):
        html = self._build_article_html('![A pie](img/pie.png)\n')
        self.assertIn(
            '<figure class="figure"><img src="img/pie.png" alt="A pie"></figure>', html
        )
        self.assertNotIn('<figcaption', html)

    def test_all_four_image_positions_at_once(self):
        """The four combinations of (alone on its line | mid-paragraph) x
        (no title | title), in ONE article. Case D — mid-paragraph WITH a
        title — used to survive into the page as raw Markdown: the inline
        pattern had no title group and its src class stops at the first
        space, so it matched nothing at all. Each case had a test; the
        combination did not, which is exactly how the gap slipped in, so
        this asserts all four together."""
        html = self._build_article_html(
            '![A](img/a.png)\n\n'
            '![B](img/b.png "Cap B")\n\n'
            'Before ![C](img/c.png) after.\n\n'
            'Before ![D](img/d.png "Tip D") after.\n'
        )
        # A and B: block figures, B captioned.
        self.assertIn('<figure class="figure"><img src="img/a.png" alt="A"></figure>', html)
        self.assertIn(
            '<figure class="figure"><img src="img/b.png" alt="B">'
            '<figcaption class="figure-caption">Cap B</figcaption></figure>',
            html,
        )
        # C and D: inline images, never a figure or a caption. D's title
        # becomes a tooltip, not a <figcaption> (§6.1: an inline image has
        # no caption).
        self.assertIn('<img src="img/c.png" alt="C">', html)
        self.assertIn('<img src="img/d.png" alt="D" title="Tip D">', html)
        self.assertNotIn('<figure class="figure"><img src="img/c.png"', html)
        self.assertNotIn('<figure class="figure"><img src="img/d.png"', html)
        self.assertNotIn('<figcaption class="figure-caption">Tip D</figcaption>', html)
        # Nothing left literal. The tell-tale of the old bug was the
        # typography engine treating the "!" of "![D]" as high
        # punctuation and slipping a non-breaking space in front of it.
        self.assertNotIn('![', html)
        self.assertNotIn(' ![', html)

    def test_heading_levels_4_5_6_in_fact_box(self):
        slide = ('<!-- lwp:slide -->\nslug: k96\nkicker: T\n## Title\nfact-label: The fact\n\n'
                 '#### Level four\n\n##### Level five\n\n###### Level six\n')
        html = self._build_article_html('', slide_body=slide)
        self.assertIn('<p class="h4">Level four</p>', html)
        self.assertNotIn('<h4>', html)
        self.assertNotIn('<strong>Level four</strong>', html)
        self.assertIn('<p>Level five</p>', html)
        self.assertIn('<p>Level six</p>', html)

    def test_no_literal_bang_leaks(self):
        # The historical broken rendering: "!" left behind before the
        # link output. Neither form may leak a literal "![" anywhere.
        for body in ('![A pie](img/pie.png)\n',
                     '![Photo](https://example.org/p.png "Cap")\n',
                     'Inline ![icon](img/i.png) here.\n'):
            html = self._build_article_html(body)
            self.assertNotIn('![', html)

    def test_inline_image_in_paragraph(self):
        html = self._build_article_html('Text with ![icon](img/i.png) inline.\n')
        self.assertIn('<p>Text with <img src="img/i.png" alt="icon"> inline.</p>', html)

    def test_image_line_not_merged_into_preceding_paragraph(self):
        # No blank line between a paragraph and the image line: the image
        # still becomes its own <figure> block (it is a block starter,
        # like a heading or a list — not a paragraph continuation).
        html = self._build_article_html('Before.\n![pie](img/pie.png "Cap")\nAfter.\n')
        self.assertIn('<p>Before.</p>', html)
        self.assertIn('<figure class="figure">', html)
        self.assertIn('<p>After.</p>', html)

    def test_caption_supports_inline_markdown_and_escaping(self):
        html = self._build_article_html(
            '![alt "q"](img/a&b.png "With **bold** & a [link](https://x.org)")\n'
        )
        self.assertIn('src="img/a&amp;b.png"', html)
        self.assertIn('alt="alt &quot;q&quot;"', html)
        self.assertIn('<figcaption class="figure-caption">With <strong>bold</strong> '
                      '&amp; a <a href="https://x.org" target="_blank" rel="noopener">link</a>'
                      '</figcaption>', html)

    def test_caption_gets_typography(self):
        # French typography: NBSP before "!" inside the caption text.
        html = self._build_article_html('![p](img/p.png "Magnifique !")\n')
        self.assertIn('Magnifique !', html)

    def test_figure_works_in_fact_box(self):
        html = self._build_article_html(
            None,
            slide_body=(
                '<!-- lwp:slide -->\nslug: k97\n## Card\nfact-label: FACT\n'
                'Some intro text.\n\n![pie](img/pie.png "In a fact box")\n'
            ),
        )
        self.assertIn('<figure class="figure">', html)
        self.assertIn('<figcaption class="figure-caption">In a fact box</figcaption>', html)

    def test_figure_css_present_in_default_stylesheet(self):
        # The caption's ink is a component property now (caption.fg,
        # defaulting to the quiet ink) — the page must carry its rule.
        html = self._build_article_html('![p](img/p.png "Cap")\n')
        self.assertIn('.figure-caption', html)
        self.assertIn('color: var(--caption-fg)', html)

    def test_linked_figure_is_a_figure_and_wraps_only_the_image(self):
        # §6.1: `[![alt](src "Cap")](url)` alone on its line. Before this,
        # the line fell through to the inline rules and produced
        # <p><a><img title="Cap"></a></p> — no figure, no figcaption, the
        # caption silently demoted to a tooltip.
        html = self._build_article_html(
            '[![A page](img/p.png "The caption")](https://example.org/comic)\n')
        self.assertIn(
            '<figure class="figure"><a href="https://example.org/comic" '
            'target="_blank" rel="noopener"><img src="img/p.png" alt="A page">'
            '</a><figcaption class="figure-caption">The caption</figcaption></figure>',
            html)
        # The caption must sit OUTSIDE the anchor: wrapping it too would make
        # the link's accessible name the alt text plus the whole caption.
        self.assertNotIn('The caption</a>', html)

    def test_linked_figure_without_a_caption(self):
        html = self._build_article_html(
            '[![A page](img/p.png)](https://example.org/comic)\n')
        self.assertIn('<figure class="figure"><a href="https://example.org/comic" '
                      'target="_blank" rel="noopener"><img src="img/p.png" '
                      'alt="A page"></a></figure>', html)
        self.assertNotIn('<figcaption', html)

    def test_linked_figure_caption_gets_typography_and_inline_markup(self):
        # The two things the raw-HTML workaround lost. A caption is real
        # block content, so it runs through md_inline() and the typography
        # engine exactly as an unlinked figure's does — a tooltip could
        # never have either, since neither belongs in an attribute value.
        html = self._build_article_html(
            '[![P](img/p.png "Double sign ! and [a link](https://example.org/x) inside")]'
            '(https://example.org/comic)\n',
            slide_body='<!-- lwp:slide:full-article -->\nslug: k98\narticle: art.md\n')
        self.assertIn('Double sign\xa0!', html)
        self.assertIn('<a href="https://example.org/x"', html)

    def test_linked_figure_is_not_swallowed_by_the_paragraph_above_it(self):
        html = self._build_article_html(
            'A paragraph immediately above.\n'
            '[![P](img/p.png "Cap")](https://example.org/comic)\n')
        self.assertIn('<figure class="figure">', html)

    def test_a_non_http_target_is_not_a_linked_figure(self):
        # §6.3 restricts link targets to http(s); the href reaches an
        # attribute. A javascript: target must not become one by way of a
        # figure, so the line simply is not a linked figure.
        html = self._build_article_html(
            '[![P](img/p.png "Cap")](javascript:alert(1))\n')
        self.assertNotIn('javascript:alert(1)"', html)
        self.assertNotIn('<figure class="figure"><a', html)


class MarkdownConversion(unittest.TestCase):
    """§3.2/§6: the full-article body goes through convert_markdown() and
    must support standard Markdown, not just paragraphs."""

    def _build_article_html(self, article_body):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k99\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art.md').write_text(article_body, encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_headings(self):
        html = self._build_article_html('# H1 title\n\n## H2 title\n\n### H3 title\n')
        self.assertIn('<h1>H1 title</h1>', html)
        self.assertIn('<h2>H2 title</h2>', html)
        self.assertIn('<h3>H3 title</h3>', html)

    def test_heading_levels_4_5_6_in_full_article(self):
        html = self._build_article_html(
            '#### Level four\n\n##### Level five\n\n###### Level six\n')
        # h4: bold-font paragraph (not <strong> markdown emphasis)
        self.assertIn('<p class="h4">Level four</p>', html)
        self.assertNotIn('<h4>', html)
        self.assertNotIn('<strong>Level four</strong>', html)
        # h5/h6: plain paragraphs
        self.assertIn('<p>Level five</p>', html)
        self.assertIn('<p>Level six</p>', html)
        self.assertNotIn('<h5>', html)
        self.assertNotIn('<h6>', html)

    def test_bold_and_italic(self):
        html = self._build_article_html('A **bold** word and an *italic* word.\n')
        self.assertIn('<strong>bold</strong>', html)
        self.assertIn('<em>italic</em>', html)

    def test_link(self):
        # Spec §6: links open in a new tab (target="_blank" rel="noopener").
        html = self._build_article_html('See [the source](https://example.org/page).\n')
        self.assertIn(
            '<a href="https://example.org/page" target="_blank" rel="noopener">the source</a>',
            html,
        )

    def test_footnote(self):
        # A note is a note: the call is a link to its body, the body is a
        # link back, and the reader sees a POSITION -- never the author's
        # label, which stays a key in the source (specifications.md §6.5).
        html = self._build_article_html(
            'A claim with a footnote[^kwh].\n\n[^kwh]: Some source, 2020.\n'
        )
        self.assertIn(
            'A claim with a footnote<sup class="note-call">'
            '<a id="noteref-article-1" href="#note-article-1" '
            'role="doc-noteref">1</a></sup>.', html)
        self.assertIn(
            '<li id="note-article-1" role="doc-footnote">'
            '<span class="note-num">1</span>Some source, 2020.', html)
        self.assertIn('href="#noteref-article-1" role="doc-backlink"', html)
        # The label never reaches the page, and neither does the literal
        # marker the old rendering shipped.
        self.assertNotIn('[^kwh]', html)
        self.assertNotIn('<sup>[^', html)

    def test_unordered_list(self):
        html = self._build_article_html('- First item\n- Second item\n')
        self.assertIn('<li>First item</li>', html)
        self.assertIn('<li>Second item</li>', html)
        self.assertIn('<ul>', html)

    def test_table(self):
        html = self._build_article_html(
            '| Column 1 | Column 2 |\n|---|---|\n| Cell A | Cell B |\n'
        )
        self.assertIn('<table', html)
        self.assertIn('<th>Column 1</th>', html)
        self.assertIn('<td>Cell A</td>', html)

    def test_raw_html_passthrough(self):
        html = self._build_article_html('Some text with a <br> line break.\n')
        self.assertIn('<br>', html)

    def test_block_level_tag_at_line_start_is_raw_passthrough(self):
        # A line starting with a block-level tag is untouched raw HTML,
        # not wrapped in <p> and not merged with the next line.
        html = self._build_article_html(
            '<div class="callout">A block.</div>\nA separate paragraph.\n'
        )
        self.assertIn('<div class="callout">A block.</div>', html)
        self.assertIn('<p>A separate paragraph.</p>', html)

    def test_inline_tag_at_line_start_stays_ordinary_paragraph_text(self):
        # A line starting with an *inline* tag (<strong>, <em>, <a>, <sup>...)
        # is ordinary paragraph text, not raw-HTML passthrough: it still
        # gets wrapped in <p> and still merges with the following line
        # per normal paragraph-continuation rules (spec §6.1/§6.2).
        html = self._build_article_html(
            '<strong>Bold start</strong> of a sentence.\n'
            'A second physical line, no blank line before it.\n'
        )
        self.assertIn(
            '<p><strong>Bold start</strong> of a sentence. '
            'A second physical line, no blank line before it.</p>',
            html,
        )

    def test_inline_tag_paragraph_still_separated_by_blank_line(self):
        html = self._build_article_html(
            '<em>First</em> paragraph.\n\n<a href="https://example.org">Second</a> paragraph.\n'
        )
        self.assertIn('<p><em>First</em> paragraph.</p>', html)
        self.assertIn(
            '<p><a href="https://example.org">Second</a> paragraph.</p>',
            html,
        )

    def test_multiline_raw_html_block_opened_by_an_inline_tag(self):
        # A hand-written multi-line block wrapped in an *inline*-level tag
        # (<a>, not <div>) -- e.g. a card linking to an image, one real
        # use case being an <a class="comic-teaser"> wrapping an <img>
        # and a <span> caption -- must stay untouched raw HTML on every
        # line, including inner lines that would look like a self-
        # contained inline usage (<span>...</span>) in isolation. Only
        # the unclosed opening line decides raw-HTML mode; once inside,
        # every line belongs to the block until the matching close.
        html = self._build_article_html(
            '<a href="https://example.org/x" class="teaser">\n'
            '<img src="x.jpg" alt="x">\n'
            '<span class="caption">Read more &rarr;</span>\n'
            '</a>\n'
        )
        self.assertIn(
            '<a href="https://example.org/x" class="teaser">\n'
            '<img src="x.jpg" alt="x">\n'
            '<span class="caption">Read more &rarr;</span>\n'
            '</a>',
            html,
        )
        self.assertNotIn('<p>', html)

    def test_blockquote_single_line(self):
        html = self._build_article_html('> A single-line quote.\n')
        self.assertIn('<blockquote><p>A single-line quote.</p></blockquote>', html)

    def test_blockquote_merges_consecutive_lines(self):
        html = self._build_article_html('> First line of the quote.\n> Second line, same quote.\n')
        self.assertIn(
            '<blockquote><p>First line of the quote. Second line, same quote.</p></blockquote>',
            html,
        )

    def test_blockquote_ends_at_blank_line(self):
        html = self._build_article_html('> The quote.\n\nOrdinary paragraph after.\n')
        self.assertIn('<blockquote><p>The quote.</p></blockquote>', html)
        self.assertIn('<p>Ordinary paragraph after.</p>', html)

    def test_blockquote_supports_inline_formatting(self):
        html = self._build_article_html('> A quote with **bold** and a [link](https://example.org).\n')
        self.assertIn('<strong>bold</strong>', html)
        self.assertIn('<a href="https://example.org"', html)
        self.assertIn('<blockquote>', html)

    def test_inline_code_span(self):
        html = self._build_article_html('Run `make build` to compile.\n')
        self.assertIn('<code>make build</code>', html)

    def test_inline_code_escapes_angle_brackets_and_ampersand(self):
        html = self._build_article_html('Example: `<div class="a & b">`.\n')
        self.assertIn('<code>&lt;div class="a &amp; b"&gt;</code>', html)

    def test_inline_code_content_not_reprocessed_as_markdown(self):
        html = self._build_article_html('Literally `**not bold**` here.\n')
        self.assertIn('<code>**not bold**</code>', html)
        self.assertNotIn('<strong>not bold</strong>', html)

    def test_fenced_code_block_basic(self):
        html = self._build_article_html('```\nplain code\n```\n')
        self.assertIn('<pre><code>\nplain code\n  </code></pre>', html)

    def test_fenced_code_block_with_language_class(self):
        html = self._build_article_html('```python\nprint("hi")\n```\n')
        self.assertIn('<pre><code class="language-python">', html)
        self.assertIn('print("hi")', html)

    def test_fenced_code_block_escapes_html(self):
        html = self._build_article_html('```\n<script>alert(1)</script>\n```\n')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)

    def test_fenced_code_block_preserves_blank_lines_and_dashes(self):
        html = self._build_article_html('```\nline one\n\n---\nline two\n```\n')
        self.assertIn('line one\n\n---\nline two', html)

    def test_unterminated_fenced_code_block_is_a_fatal_error(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k100\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art.md').write_text('```\nnever closed\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not well-formed', result.stderr)

    def test_escaped_gt_at_line_start_is_literal_not_a_blockquote(self):
        html = self._build_article_html('\\> Not a quote, just text starting with a >.\n')
        self.assertNotIn('<blockquote>', html)
        self.assertIn('<p>> Not a quote, just text starting with a >.</p>', html)

    def test_escaped_backtick_is_literal_not_a_code_span(self):
        html = self._build_article_html('A literal \\` backtick, no code span.\n')
        self.assertNotIn('<code>', html)
        self.assertIn('A literal ` backtick, no code span.', html)

    def test_escaped_fence_is_literal_not_a_code_block(self):
        html = self._build_article_html('\\```\nJust text, not a code block.\n')
        self.assertNotIn('<pre>', html)
        self.assertIn('```', html)

    def test_code_content_is_protected_from_typography(self):
        # §6.3/§19.3: a non-breaking space silently inserted before a
        # literal % inside a code sample would corrupt the example.
        html = self._build_article_html('Inline `50 %` and:\n\n```\ncurl "x?limit=50 %"\n```\n')
        self.assertIn('<code>50 %</code>', html)
        self.assertIn('curl "x?limit=50 %"', html)
        self.assertNotIn('50\u00a0%', html)

    def test_blockquote_still_receives_typography(self):
        # Unlike code, a blockquote is ordinary prose and keeps the
        # normal non-breaking-space treatment (§6.3).
        html = self._build_article_html('> Le taux atteint 80 % des cas.\n')
        self.assertIn('80\u00a0%', html)


class MultiArticleSeries(unittest.TestCase):
    """§3.1/§20: with more than one article, series-nav and the index page
    are computed from series.json, not just a single-article passthrough."""

    def _build_series(self, tmp):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k101\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k102\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k103\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k104\n'
        )
        (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(md_b, encoding='utf-8')
        series = {
            'series_meta': {
                'title': 'The series title',
                'subtitle': 'The series subtitle',
                'version': 'v0.1',
                'intro': 'An intro paragraph.',
            },
            'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'Article A',
                 'nav_desc': 'Desc A', 'card_label': 'Article 1',
                 'card_title': 'Custom card title A', 'card_desc': 'Custom card desc A'},
                {'page_dest': 'b.html', 'page_source': 'b.md', 'nav_title': 'Article B',
                 'nav_desc': 'Desc B'},
            ],
        }
        (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
        return root

    def test_series_nav_marks_current_article_and_links_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # In a.html, article A is "current" (no link) and B is a link.
            self.assertIn('Article A', html_a)
            self.assertIn('href="b.html"', html_a)
            self.assertNotIn('href="a.html"', html_a)

    def test_index_uses_series_meta_and_per_entry_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('The series title', index_html)
            self.assertIn('The series subtitle', index_html)
            self.assertIn('v0.1', index_html)
            self.assertIn('An intro paragraph.', index_html)
            # Article A has explicit card_title/card_desc/card_label overrides.
            self.assertIn('Custom card title A', index_html)
            self.assertIn('Custom card desc A', index_html)
            self.assertIn('Article 1', index_html)
            # Article B has no card_title/card_desc override: those fall
            # back to page_title and the cover slide's own summary — NOT
            # to nav_desc ("Desc B"), which is a separate field for the
            # in-article navigation card, not the index card.
            self.assertIn('Article B', index_html)
            self.assertIn('Summary B.', index_html)
            self.assertNotIn('Desc B', index_html)
            # ...while "Desc B" (nav_desc) is exactly what DOES show up in
            # the OTHER article's own page, in the cross-navigation card —
            # proving the two fields are genuinely independent, not just
            # differently named.
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Desc B', html_a)


class AnArticleThatClaimsTheIndexName(unittest.TestCase):
    """§11.3.3. `build` always wrote a series index at index.html, so an
    article whose page_dest was that same name got written first and
    buried under the index — exit code 0, no warning, and a series
    declaring three articles shipped two.

    The rule depends on the number of articles because that is what the
    index is worth in each case: with more than one it carries the list
    and overwriting it is a loss (fatal), with exactly one it would list
    a single entry and adds nothing (the article takes the name, no index
    is produced, and the build says so).
    """

    ARTICLE = ('<!-- lwp:meta -->\npage_title: {title}\n---\n\n'
               '<!-- lwp:slide:cover -->\nslug: k105\nkicker: T\n# {title}\n'
               'summary: Summary of {title}.\n')

    def series(self, tmp, entries):
        """entries: list of (page_source, page_dest[, extra dict])."""
        root = Path(tmp)
        (root / 'sources').mkdir(parents=True, exist_ok=True)
        articles = []
        for source, dest, *rest in entries:
            title = source[:-3].upper()
            (root / 'sources' / source).write_text(
                self.ARTICLE.format(title=title), encoding='utf-8')
            entry = {'page_source': source, 'page_dest': dest,
                     'nav_title': title, 'nav_desc': f'Desc {title}'}
            if rest:
                entry.update(rest[0])
            articles.append(entry)
        (root / 'series.json').write_text(
            json.dumps({'series_meta': {'title': 'The series title'},
                        'articles': articles}), encoding='utf-8')
        return root

    def test_several_articles_and_one_claims_the_index_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html'),
                                     ('b.md', 'b.html'),
                                     ('c.md', 'c.html')])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('collides with the series index', result.stderr)
            # Named: the author has to know which line to change, and the
            # source filename is the one thing every entry always carries
            # (page_dest can come from the meta block or be derived).
            self.assertIn('"a.md"', result.stderr)
            self.assertIn('"index.html"', result.stderr)
            # Fatal before anything is written, like every other build
            # error of this class — no half-built output to clean up.
            self.assertFalse((root / 'public').exists())

    def test_the_fatal_case_is_decided_on_the_name_not_the_filesystem(self):
        """'Index.html' and 'index.html' are two URLs but one file on
        Windows and default macOS — same reasoning as the duplicate
        page_dest check, so the verdict cannot depend on the platform the
        build happens to run on."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'Index.html'), ('b.md', 'b.html')])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn('collides with the series index', result.stderr)

    def test_a_lone_article_takes_the_name_and_no_index_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html')])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            written = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            # It is the ARTICLE that survived, not the index: the article's
            # own cover text is there, and the series index's header is not.
            self.assertIn('Summary of A.', written)
            self.assertNotIn('The series title', written)
            self.assertEqual(sorted(p.name for p in (root / 'public').iterdir()
                                    if not p.name.startswith('.lwp-')),
                             ['index.html'])

    def test_the_build_says_it_did_not_generate_an_index(self):
        """Someone whose index stopped being generated has to see why
        without reading the specification."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html')])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertIn('[no index]', result.stdout)
            self.assertIn('a.md', result.stdout)
            # ...and the closing line must not still claim an index.
            self.assertIn('Build complete: 1 articles ->', result.stdout)
            self.assertNotIn('+ index', result.stdout)

    def test_an_ordinary_series_still_gets_its_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'a.html'), ('b.md', 'b.html')])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('[no index]', result.stdout)
            self.assertIn('Build complete: 2 articles + index ->', result.stdout)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('The series title', index_html)
            self.assertTrue((root / 'public' / 'a.html').exists())
            self.assertTrue((root / 'public' / 'b.html').exists())

    def test_check_is_green_on_a_series_the_article_holds_the_index_of(self):
        """The measured regression this guards: check compared a freshly
        rendered series index against the article page sitting at that
        name and reported [DRIFT] — a red CI gate on a correctly built
        series, that no rebuild could ever settle."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html')])
            run('build', str(root), '--output', str(root / 'public'))
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('[DRIFT]', result.stdout)
            self.assertIn('All files are up to date.', result.stdout)
            # One article + README, and no phantom index slot.
            self.assertIn('2 file(s) OK, 0 file(s) different.', result.stdout)

    def test_check_refuses_exactly_what_build_refuses(self):
        """A series build declines to produce must not be reported as
        ordinary drift by the command whose whole job is 'is public/ what
        a build would make'."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html'), ('b.md', 'b.html')])
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertIn('collides with the series index', result.stderr)

    def test_the_incremental_path_does_not_bury_the_article_either(self):
        """`build --only` writes index.html too (it is cheap, so it is
        always redone) — the branch has to exist on that path as well."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html')])
            run('build', str(root), '--output', str(root / 'public'))
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--only', 'index.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[no index]', result.stdout)
            written = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Summary of A.', written)
            self.assertNotIn('The series title', written)

    def test_what_counts_here_is_the_series_not_the_build(self):
        """§20.6 decides the tally, and it is deliberately NOT the list of
        pages this particular run will write.

        A draft is an article of the series — it is only kept out of the
        output — so a two-entry series with one draft has an index worth
        protecting and the collision is fatal, with or without
        --include-drafts. Counting the built list instead would make the
        very same series.json legal or illegal depending on a build flag.

        An `ignored` entry is not an article of the series at all, so what
        remains really is a series of one, and the index name is free."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html'),
                                     ('b.md', 'b.html', {'status': 'draft'})])
            for flags in ((), ('--include-drafts',)):
                with self.subTest(flags=flags):
                    result = run('build', str(root), '--output',
                                 str(root / 'public'), *flags)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn('collides with the series index', result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            root = self.series(tmp, [('a.md', 'index.html'),
                                     ('b.md', 'b.html', {'status': 'ignored'})])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[no index]', result.stdout)


class SeriesNavTypography(unittest.TestCase):
    """Regression: build_series_nav() used to render card_label/nav_title/
    nav_desc with no typography applied at all — a plain space instead of
    a non-breaking one before ':'/'!'/'?', while the exact same fields on
    build_index()'s cards were correctly processed. Confirmed independently
    by a user after the v0.5.0 card_/nav_ split touched this exact
    function and didn't fix it."""

    def _build_series(self, tmp, article_a_extra_meta=''):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            f'nav_desc: Desc A\n{article_a_extra_meta}---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k106\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k107\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\n'
            'nav_title: Question ? Titre\nnav_desc: Alerte !\ncard_label: Numéro :\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k108\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k109\n'
        )
        (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(md_b, encoding='utf-8')
        # The nbsp is typed with a plain space here on purpose — series.json
        # values go through the exact same build_series_nav() typography
        # path as the meta-block ones, so a plain " ?"/" !"/" :" here must
        # also come out as "\xa0?"/"\xa0!"/"\xa0:" once built.
        series = {'articles': [
            {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'Article A', 'nav_desc': 'Desc A'},
            {'page_dest': 'b.html', 'page_source': 'b.md'},
        ]}
        (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
        return root

    def test_nav_title_desc_and_card_label_get_nbsp_typography(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            # Article B's nav_title/nav_desc/card_label, as they appear in
            # the series-nav block embedded on article A's own page.
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Question\xa0? Titre', html_a)
            self.assertIn('Alerte\xa0!', html_a)
            self.assertIn('Numéro\xa0:', html_a)
            self.assertNotIn('Question ? Titre', html_a)
            self.assertNotIn('Alerte !', html_a)
            self.assertNotIn('Numéro :', html_a)

    def test_series_nav_typography_uses_build_wide_engine_not_hosting_articles_typo_off(self):
        """§4.5: typo: off on the HOSTING article (A) must not silently
        also turn off typography for the OTHER articles' entries shown in
        A's own series-nav block — those aren't "A's own page content",
        same rule as build_index()'s cards."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp, article_a_extra_meta='typo: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Question\xa0? Titre', html_a)
            self.assertIn('Alerte\xa0!', html_a)
            self.assertIn('Numéro\xa0:', html_a)


class IncrementalBuildOnly(unittest.TestCase):
    """§11.3.1: `build --only <file>` rebuilds a single article instead of
    the whole series, but only when nothing that affects index.html/
    series-nav changed since the last build — checked via a fingerprint
    cache (--nav-cache, default .lwp-cache/nav.json)."""

    def _build_series(self, tmp):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k110\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k111\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k112\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k113\n'
        )
        (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(md_b, encoding='utf-8')
        series = {
            'series_meta': {'title': 'The series', 'subtitle': '', 'intro': ''},
            'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'Article A', 'nav_desc': 'Desc A'},
                {'page_dest': 'b.html', 'page_source': 'b.md', 'nav_title': 'Article B', 'nav_desc': 'Desc B'},
            ],
        }
        (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
        return root

    def test_only_without_prior_cache_falls_back_to_full_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no usable cache found', result.stderr)
            self.assertIn('Build complete:', result.stdout)
            self.assertTrue((root / 'public' / 'b.html').exists())
            self.assertTrue((root / '.lwp-cache' / 'nav.json').exists())

    def test_only_with_unchanged_nav_fields_rebuilds_just_that_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))
            b_before = (root / 'public' / 'b.html').read_text(encoding='utf-8')

            # Add a brand-new standard slide to article A's body — none of
            # page_title/card_title/card_desc/card_label/nav_title/
            # nav_desc (the fields the safety check watches, §11.3.1) are
            # touched: the cover's own h1/summary — which page_title/
            # card_desc can fall back to, §20.3.1 — stay exactly as they
            # were.
            md_a2 = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
                'nav_desc: Desc A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k114\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: k115\nkicker: New\n## A brand-new slide\nsummary: New body content.\n\n'
                '---\n\n<!-- lwp:slide:series-nav -->\nslug: k116\n'
            )
            (root / 'sources' / 'a.md').write_text(md_a2, encoding='utf-8')

            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Incremental build', result.stdout)
            self.assertIn('A brand-new slide', (root / 'public' / 'a.html').read_text(encoding='utf-8'))
            # b.html was never touched by the incremental path.
            self.assertEqual(b_before, (root / 'public' / 'b.html').read_text(encoding='utf-8'))

    def test_only_with_changed_nav_field_falls_back_and_fixes_other_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))

            # Change article A's nav_title — this DOES feed the
            # series-nav block embedded in b.html, so skipping b.html
            # would leave a stale title there.
            md_a2 = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A Renamed\n'
                'nav_desc: Desc A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k117\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: k118\n'
            )
            (root / 'sources' / 'a.md').write_text(md_a2, encoding='utf-8')
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'][0]['nav_title'] = 'Article A Renamed'
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')

            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('nav/index-affecting metadata changed', result.stderr)
            self.assertIn('Build complete:', result.stdout)
            html_b = (root / 'public' / 'b.html').read_text(encoding='utf-8')
            self.assertIn('Article A Renamed', html_b)

    def test_only_detects_a_newly_added_article_even_if_unrelated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))

            md_c = (
                '<!-- lwp:meta -->\npage_dest: c.html\npage_title: Article C\nnav_title: Article C\n'
                'nav_desc: Desc C\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k119\nkicker: T\n# Article C\nsummary: Summary C.\n\n---\n\n'
            )
            (root / 'sources' / 'c.md').write_text(md_c, encoding='utf-8')
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'].append({'page_dest': 'c.html', 'page_source': 'c.md',
                                        'nav_title': 'Article C', 'nav_desc': 'Desc C'})
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')

            # Ask to rebuild only b.html, unrelated to the new article C —
            # the fingerprint mismatch (new key) must still be caught.
            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'b.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('nav/index-affecting metadata changed', result.stderr)
            self.assertTrue((root / 'public' / 'c.html').exists())

    def test_only_unknown_file_is_a_fatal_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'nope.html')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('matches no article', result.stderr)

    def test_nav_cache_flag_overrides_default_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            custom_cache = root / 'elsewhere' / 'cache.json'
            run('build', str(root), '--output', str(root / 'public'), '--nav-cache', str(custom_cache))
            self.assertTrue(custom_cache.exists())
            self.assertFalse((root / '.lwp-cache' / 'nav.json').exists())

            result = run('build', str(root), '--output', str(root / 'public'),
                         '--only', 'a.html', '--nav-cache', str(custom_cache))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Incremental build', result.stdout)

    def test_nav_cache_content_is_small_fingerprints_not_raw_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_series(tmp)
            run('build', str(root), '--output', str(root / 'public'))
            cache = json.loads((root / '.lwp-cache' / 'nav.json').read_text(encoding='utf-8'))
            self.assertEqual(set(cache.keys()), {'a.html', 'b.html'})
            for fingerprint in cache.values():
                self.assertRegex(fingerprint, r'^[0-9a-f]{64}$')
                self.assertNotIn('Article', fingerprint)


class DemoCommand(unittest.TestCase):
    """§11.2: `demo` must produce a series that builds cleanly."""

    def test_demo_builds_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_result = run('init', str(root))
            self.assertEqual(install_result.returncode, 0, install_result.stderr)
            demo_result = run('demo', str(root))
            self.assertEqual(demo_result.returncode, 0, demo_result.stderr)
            build_result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(build_result.returncode, 0, build_result.stderr)
            self.assertTrue((root / 'public' / 'first.html').exists())
            self.assertTrue((root / 'public' / 'middle.html').exists())
            self.assertTrue((root / 'public' / 'last.html').exists())
            self.assertTrue((root / 'public' / 'index.html').exists())


class InstallContent(unittest.TestCase):
    """§11.1: install must actually create the documented scaffold, not
    just refuse/accept an empty directory."""

    def test_install_creates_expected_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'series.json').exists())
            self.assertTrue((root / 'sources').is_dir())
            # The author surface, and ONLY the author surface: values and
            # rules. No style.css — the stylesheet is composed at build
            # time and owns no file. No nav.js and no language pack
            # either, since v0.40.0: those are the tool's, they live in
            # the executable, and a copy of them in the series was never
            # a customisation — only a snapshot that froze the series at
            # the version of the day (BACKLOG B32).
            self.assertTrue((root / 'templates' / 'settings.conf').exists())
            self.assertTrue((root / 'templates' / 'custom.css').exists())
            self.assertFalse((root / 'templates' / 'style.css').exists())
            self.assertFalse((root / 'templates' / 'nav.js').exists())
            self.assertFalse((root / 'language' / 'fr.json').exists())
            self.assertFalse((root / 'language' / 'en.json').exists())


class ToolOwnedFilesSayWhenTheyHaveFallenBehind(unittest.TestCase):
    """A series holds copies of two files the tool wrote — `nav.js` and
    the language packs — and the build uses the copies. So a behaviour
    the tool fixes never reaches a page that was made before the fix,
    and the only thing standing between an author and that is what the
    build says.

    It said the wrong amount. `nav.js` got an `[INFO]`, which `--quiet`
    silences — and `--quiet` is what a pipeline runs. The language packs
    got nothing at all. Three behaviour fixes shipped in v0.39.0 reached
    no existing series, and the line that would have explained it was
    the one nobody saw."""

    def _series(self, tmp):
        root = Path(tmp) / 'series'
        self.assertEqual(run('init', str(root)).returncode, 0)
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k120\nkicker: T\n# A\nsummary: S.\n',
            encoding='utf-8')
        (root / 'series.json').write_text(json.dumps({'articles': [
            {'page_dest': 'a.html', 'page_source': 'a.md',
             'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
        return root

    def test_a_current_series_is_told_nothing(self):
        """The other half, and the one that decides whether the warning
        is worth having: a series that is up to date must stay silent, or
        the warning becomes noise every author learns to skip."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            r = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('differs', r.stderr)

    def test_a_stale_nav_js_warns_even_under_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            # Taken deliberately, which is the only way to have one now
            # (`init` stopped handing it out), then aged by a line.
            self.assertEqual(
                run('template', 'write', 'nav.js', str(root)).returncode, 0)
            nav = root / 'templates' / 'nav.js'
            nav.write_text('// from an older version\n' + nav.read_text(),
                           encoding='utf-8')
            r = run('build', str(root), '--quiet',
                    '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('nav.js differs', r.stderr)
            self.assertIn('template update', r.stderr)

    def test_a_stale_language_pack_warns_even_under_quiet(self):
        """It used to say nothing whatsoever, on any command. A pack
        carries the typography rules AND the interface strings, so a
        stale one keeps an old vocabulary as well as an old spacing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            self.assertEqual(
                run('template', 'write', 'fr.json', str(root)).returncode, 0)
            pack = root / 'language' / 'fr.json'
            data = json.loads(pack.read_text(encoding='utf-8'))
            for rule in data['rules']:
                rule.pop('category', None)
            pack.write_text(json.dumps(data, indent=2), encoding='utf-8')
            r = run('build', str(root), '--quiet',
                    '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('language/fr.json differs', r.stderr)
            # And it names what to RUN. The first wording said "copy the
            # built-in one over it" without saying with what, at a moment
            # when three commands could do it — so the one person who hit
            # this worked the remedy out by hand, from a message that did
            # not contain it. Deletion first: it is the state the tool
            # now wants a series to be in.
            self.assertIn('delete it', r.stderr)
            self.assertIn('template show fr.json', r.stderr)
            self.assertIn('template write fr.json', r.stderr)

    def test_a_pack_the_tool_does_not_ship_is_the_authors_business(self):
        """A language the tool has never heard of is not stale, it is
        someone's work. Warning about it would be the tool complaining
        that a file it did not write is not the file it did not write."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'language').mkdir(exist_ok=True)
            (root / 'language' / 'de.json').write_text(
                json.dumps({'lang': 'de', 'rules': []}), encoding='utf-8')
            r = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('de.json', r.stderr)


class LogRefusesALevelItDoesNotKnow(unittest.TestCase):
    """The level is spelt `warn`. `log('warning', ...)` printed nothing
    and told nobody, which has now cost something three times — the
    docstring above the function has warned about it since the second.

    A trap that is only documented is a trap. The level set is closed and
    known when the call is written, so an unknown one is a typo in this
    file and nothing else: no input can reach it, and there is nothing to
    degrade gracefully for."""

    def test_an_unknown_level_raises_instead_of_vanishing(self):
        lwp = load_lightwebpres_module()
        with self.assertRaises(ValueError) as ctx:
            lwp.log('warning', 'a message nobody would ever see')
        self.assertIn("'warn'", str(ctx.exception))

    def test_every_level_the_code_uses_is_one_log_knows(self):
        """Every CALL, found through the AST rather than by matching
        text. A regex reads the prose too, and the docstring on `log`
        quotes `log(\'warning\', ...)` on purpose, as the mistake to
        avoid — so a textual scan fails on the very sentence that exists
        to prevent the failure. The tree knows a call from a quotation.

        Read off the source rather than trusted at runtime, because a
        miswritten level is invisible until the line it guards matters,
        which is exactly the moment nobody is looking."""
        source = (Path(__file__).resolve().parent.parent
                  / 'lightwebpres').read_text(encoding='utf-8')
        used = set()
        for node in ast.walk(ast.parse(source)):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == 'log' and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                used.add(node.args[0].value)
        self.assertTrue(used, 'no log() call found — the scan is broken')
        self.assertEqual(used - {'error', 'warn', 'info', 'verbose'}, set())


class TheToolKeepsItsOwnFilesAndHandsThemOverOnRequest(unittest.TestCase):
    """The repair to the CAUSE of B32, the warning having only treated the
    symptom. `init` wrote nav.js and both language packs into every
    series, byte for byte identical to what the executable already held —
    so the copy was never a customisation, only a snapshot the build then
    preferred to the executable's own. Three fixes shipped in v0.39.0
    reached nobody who already had a series.

    They stay reachable, because not being able to get at them would be a
    real loss and `template update` never created a missing nav.js — it
    only replaced an existing one, so removing the scaffold with nothing
    else would have left no way to obtain the file at all. `show` prints
    one, `write` installs one where the build reads it.

    Both exist, and not for symmetry: `show >` would leave the PATH to
    the author, and a path one directory off is a file that sits there
    doing nothing, silently. `write` makes the act explicit and the path
    the tool's business."""

    OWNED = ('nav.js', 'fr.json', 'en.json')

    def _series(self, tmp, *extra):
        root = Path(tmp) / 'series'
        self.assertEqual(run('init', str(root), *extra).returncode, 0)
        return root

    def test_a_new_series_holds_none_of_the_tools_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            self.assertFalse((root / 'templates' / 'nav.js').exists())
            self.assertFalse((root / 'language' / 'fr.json').exists())
            self.assertFalse((root / 'language' / 'en.json').exists())

    def test_init_names_the_way_to_reach_the_files_it_no_longer_writes(self):
        """The whole discoverability mechanism for three files that are
        no longer in the directory. Before, an author saw `nav.js` in a
        listing and opened it; now there is nothing to see, so the only
        thing standing between them and a file they do not know exists is
        this line — and `init` is where someone reads what a series is
        made of.

        It is the `custom.css` lesson applied the other way round:
        guidance goes where guidance belongs, which makes the guidance
        itself load-bearing. Measured before this guard: silencing the
        announcement changed no test result."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            r = run('init', str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            said = r.stdout + r.stderr
            self.assertIn('template show nav.js', said)
            self.assertIn('template write nav.js', said)
            # And it says why taking one is a decision, not a freebie.
            self.assertIn('stops following', said)

    def test_a_page_is_the_same_with_the_copies_and_without(self):
        """The measurement the whole change rests on. If a page built
        from a series holding the copies differed from one built without
        them, removing them would be a behaviour change rather than the
        removal of a redundancy — and this would be the wrong lot."""
        md = ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
              'nav_title: A\nnav_desc: A\n---\n\n'
              '<!-- lwp:slide:cover -->\nslug: k121\nkicker: K\n# T\nsummary: S.\n')
        with tempfile.TemporaryDirectory() as tmp:
            pages = []
            for name, take_copies in (('bare', False), ('copied', True)):
                root = Path(tmp) / name
                self.assertEqual(run('init', str(root)).returncode, 0)
                (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
                (root / 'series.json').write_text(json.dumps({'articles': [
                    {'page_dest': 'a.html', 'page_source': 'a.md',
                     'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
                if take_copies:
                    for f in self.OWNED:
                        self.assertEqual(
                            run('template', 'write', f, str(root)).returncode,
                            0)
                r = run('build', str(root), '--output', str(root / 'public'))
                self.assertEqual(r.returncode, 0, r.stderr)
                pages.append((root / 'public' / 'a.html').read_bytes())
            self.assertEqual(pages[0], pages[1])

    def test_show_prints_the_file_whole_and_touches_nothing(self):
        """It needs no series at all — the answer is inside the program —
        which is the case `write` cannot serve: someone wanting to know
        what a key does should not have to scaffold a series to find out,
        nor end up owning a frozen copy for having asked.

        WHOLE, compared against what `write` puts on disk. A size check
        was the first version of this, and it let a `show` truncated to
        2000 bytes pass — measured, not supposed. A reader who pipes this
        into a file gets what the other command would have written, or
        the command is worse than useless."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            for name in self.OWNED:
                r = run('template', 'show', name, cwd=tmp)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(
                    run('template', 'write', name, str(root)).returncode, 0)
                written = (root / ('templates' if name.endswith('.js')
                                   else 'language') / name)
                self.assertEqual(r.stdout,
                                 written.read_text(encoding='utf-8'), name)
            # And it wrote nothing of its own: the series above is the
            # only thing in tmp, put there by `init` rather than by show.
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),
                             ['series'])

    def test_show_refuses_a_file_that_is_not_the_tools(self):
        """settings.conf and custom.css are the AUTHOR's. Handing them
        out here would blur the one line this whole lot draws."""
        for name in ('settings.conf', 'custom.css', 'style.css', 'nothing'):
            r = run('template', 'show', name)
            self.assertEqual(r.returncode, 1, name)
            self.assertIn('nav.js', r.stderr)

    def test_write_puts_each_file_where_the_build_reads_it(self):
        """The reason `write` exists next to `show`: the LAYOUT is the
        tool's knowledge, not the author's. nav.js goes under templates/,
        a pack under language/, and a redirect to the wrong one of those
        would leave a file that does nothing, with no error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            for name in self.OWNED:
                self.assertEqual(
                    run('template', 'write', name, str(root)).returncode, 0)
            self.assertTrue((root / 'templates' / 'nav.js').exists())
            self.assertTrue((root / 'language' / 'fr.json').exists())
            self.assertTrue((root / 'language' / 'en.json').exists())
            # And what it wrote is what the executable holds, so a fresh
            # copy raises no staleness warning.
            r = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotIn('differs', r.stderr)

    def test_write_says_what_the_copy_costs(self):
        """The whole lesson of B32 in one line. The trap was never the
        copy — it was that nobody knew they had one. Asked for by name
        and told the price at the moment it is taken on, it is a choice."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            r = run('template', 'write', 'nav.js', str(root))
            said = r.stdout + r.stderr
            self.assertIn('not follow', said)
            self.assertIn('every build will say so', said)

    def test_the_error_for_too_many_arguments_names_a_typable_command(self):
        """The dispatch keys are internal: `series-info`, `themes`,
        `template-show`. `_CANONICAL_NAME` exists so no message echoes
        one, and this call site was missed when that table was written —
        `status a b` answered "`series-info` takes...", recommending a
        word the program refuses. This lot made it visible by adding a
        key that is not a token at all.

        Every command with a positional limit, driven off the tables, so
        a command added later cannot reintroduce it."""
        lwp = load_lightwebpres_module()
        for command, limit in sorted(lwp._MAX_POSITIONAL.items()):
            if limit is None:
                continue
            typable = lwp.canonical(command)
            r = run(*typable.split(), *[f'a{i}' for i in range(limit + 1)])
            self.assertEqual(r.returncode, 1, f'{typable}: {r.stderr}')
            self.assertIn(f'`{typable}`', r.stderr,
                          f'{command}: the error names a key, not a command')
            self.assertNotIn(f'`{command}`' if command != typable else '\0',
                             r.stderr, command)

    def test_write_refuses_a_directory_that_is_not_a_series(self):
        """It used to scaffold `templates/nav.js` into an empty directory
        and announce that the build would use it — a promise about a
        build that cannot happen there. `template update` has always
        refused the same way, and the two write to the same directory."""
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / 'not-a-series'
            r = run('template', 'write', 'nav.js', str(empty))
            self.assertEqual(r.returncode, 1)
            self.assertIn('init', r.stderr)
            self.assertFalse(empty.exists())

    def test_neither_command_claims_a_dry_run_did_something(self):
        """--dry-run journals every write and removal through the
        helpers, so a summary in the past tense contradicts the journal
        three lines above it — and the summary is the half a reader
        believes. Both verbs, since `update` had the same wart before
        this lot touched it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            nav = root / 'templates' / 'nav.js'
            r = run('template', 'write', 'nav.js', str(root), '--dry-run')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(nav.exists())
            self.assertIn('Would write', r.stdout + r.stderr)
            self.assertNotIn('Wrote ', r.stdout + r.stderr)

            self.assertEqual(
                run('template', 'write', 'nav.js', str(root)).returncode, 0)
            r = run('template', 'update', str(root), '--dry-run')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(nav.exists(), 'a dry run removed a file')
            self.assertIn('Would remove', r.stdout + r.stderr)

    def test_update_looks_where_the_build_looks(self):
        """Both directories through the build's own resolver. It read
        `templates/` directly while the language half honoured
        LWP_LANGUAGE_DIR — one function reading one of the two variables,
        which is worse than reading neither: it works until someone moves
        the other directory."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            elsewhere = Path(tmp) / 'tpl'
            (root / 'templates').rename(elsewhere)
            self.assertEqual(
                run('template', 'write', 'nav.js', str(root),
                    env={'LWP_TEMPLATES_DIR': str(elsewhere)}).returncode, 0)
            self.assertTrue((elsewhere / 'nav.js').exists())
            r = run('template', 'update', str(root),
                    env={'LWP_TEMPLATES_DIR': str(elsewhere)})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((elsewhere / 'nav.js').exists())

    def test_write_refuses_to_replace_a_file_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            nav = root / 'templates' / 'nav.js'
            self.assertEqual(
                run('template', 'write', 'nav.js', str(root)).returncode, 0)
            nav.write_text('// mine\n', encoding='utf-8')
            r = run('template', 'write', 'nav.js', str(root))
            self.assertEqual(r.returncode, 1)
            self.assertEqual(nav.read_text(encoding='utf-8'), '// mine\n')
            r = run('template', 'write', 'nav.js', str(root), '--force')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotEqual(nav.read_text(encoding='utf-8'), '// mine\n')

    def test_write_follows_the_environment_the_build_follows(self):
        """Through the build's own path resolution, so what it writes
        cannot land where the build does not look. LWP_LANGUAGE_DIR moves
        the packs, and a `write` that ignored it would produce exactly
        the silent no-op this command exists to prevent."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            elsewhere = Path(tmp) / 'packs'
            r = run('template', 'write', 'fr.json', str(root),
                    env={'LWP_LANGUAGE_DIR': str(elsewhere)})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((elsewhere / 'fr.json').exists())
            self.assertFalse((root / 'language' / 'fr.json').exists())

    def test_update_removes_a_copy_identical_to_the_built_in_one(self):
        """Lossless by construction: identical, the copy changes nothing
        about the build except which side of the comparison the bytes
        come from, and its only remaining effect is to freeze the series
        the day the executable moves on. This is how a series scaffolded
        before this version repairs itself."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            for name in self.OWNED:
                self.assertEqual(
                    run('template', 'write', name, str(root)).returncode, 0)
            r = run('template', 'update', str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((root / 'templates' / 'nav.js').exists())
            self.assertFalse((root / 'language' / 'fr.json').exists())
            self.assertFalse((root / 'language' / 'en.json').exists())
            self.assertNotIn('nav.js.bak',
                             [p.name for p in (root / 'templates').iterdir()])

    def test_update_keeps_a_language_pack_that_differs(self):
        """The build cannot tell "customised" from "stale", so neither
        can this command, and the one that guesses wrong destroys work.
        A pack's `rules` replace the base set wholesale, so overwriting
        one erases whatever the author added — it is reported instead."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            self.assertEqual(
                run('template', 'write', 'fr.json', str(root)).returncode, 0)
            pack = root / 'language' / 'fr.json'
            data = json.loads(pack.read_text(encoding='utf-8'))
            data['rules'] = data['rules'][:1]
            pack.write_text(json.dumps(data, indent=2), encoding='utf-8')
            r = run('template', 'update', str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(pack.exists())
            self.assertEqual(len(json.loads(
                pack.read_text(encoding='utf-8'))['rules']), 1)
            self.assertIn('may be yours', r.stdout + r.stderr)

    def test_update_saves_a_customised_nav_js_before_removing_it(self):
        """The outcome `template update` has always produced — the build
        runs the tool's navigation, the author's version preserved beside
        it — reached by having no file rather than by holding a copy. The
        difference is the whole point: a copy goes stale again."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            self.assertEqual(
                run('template', 'write', 'nav.js', str(root)).returncode, 0)
            nav = root / 'templates' / 'nav.js'
            nav.write_text(nav.read_text(encoding='utf-8') + '\n// mine\n',
                           encoding='utf-8')
            r = run('template', 'update', str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(nav.exists())
            bak = root / 'templates' / 'nav.js.bak'
            self.assertTrue(bak.exists())
            self.assertIn('// mine', bak.read_text(encoding='utf-8'))


class CheckDrift(unittest.TestCase):
    """§11.3: check must actually detect drift, not just report its absence."""

    def test_check_reports_drift_after_source_change(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k122\nkicker: T\n# Title\nsummary: Original summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            changed_md = md.replace('Original summary.', 'Changed summary.')
            (root / 'sources' / 'a.md').write_text(changed_md, encoding='utf-8')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT]', result.stdout)


class TheNonBreakingSpaceIsWrittenSoItCannotBeLost(unittest.TestCase):
    """The typography engine is the tool's strong suit, and its whole
    effect rides on one character nobody can see.

    §19.3.1 required U+00A0 to be written as an escape and claimed both
    built-in packs did so "for this reason, learned by losing it".
    Measured before this lot: 0 occurrences of the escape in the
    executable, 18 of the literal character. The rule was stated and not
    applied, which is worse than either — so both packs were converted and
    these two guards were written, because the rule without a guard is how
    it drifted the first time (BACKLOG B25)."""

    def test_no_literal_non_breaking_space_survives_in_the_source(self):
        """A literal U+00A0 is indistinguishable from a space on screen.
        It does not show in a diff, an editor can normalise it away, a
        copy through a terminal or a web form can drop it. If one is lost,
        the rule still runs, the build stays green, and the typography
        simply stops working — a `50 %` that breaks across a line, a `?`
        that starts one alone. Nothing else would notice."""
        source = EXECUTABLE.read_text(encoding='utf-8')
        stray = [i + 1 for i, line in enumerate(source.split('\n'))
                 if ' ' in line]
        self.assertEqual(stray, [],
                         'literal U+00A0 in the executable at line(s) '
                         f'{stray} — write it as the six-character escape '
                         'so a diff can show it')

    def test_every_nbsp_rule_actually_emits_a_non_breaking_space(self):
        """The escape guard above protects the writing; this one protects
        the effect. Between them a rule cannot become a no-op unnoticed:
        one catches a character silently lost, the other a rule that stops
        producing what its name promises."""
        lwp = load_lightwebpres_module()
        cases = {
            'nbsp_before_double_punctuation': 'Vraiment ?',
            'nbsp_after_opening_quote': '« bonjour',
            'nbsp_inside_dash_incise': 'Paris — capitale — France',
            'nbsp_before_lone_dash': 'word — rest',
            'nbsp_before_percent': '50 %',
            'nbsp_thousands_separator': '170 000 vues',
            'nbsp_before_unit': '170 millions',
            'nbsp_after_operator': '≈ 5',
            'nbsp_before_metric_unit': '5 km',
            'nbsp_before_unit_word': '20 dollars',
            'nbsp_between_initials': 'J. R. R. Tolkien',
        }
        seen = set()
        for pack_json in (lwp.LANG_FR, lwp.LANG_EN):
            pack = json.loads(pack_json)
            for rule in pack['rules']:
                name = rule['name']
                if not name.startswith('nbsp_'):
                    continue
                seen.add(name)
                self.assertIn(name, cases,
                              f'{name} has no control string here — add one '
                              'rather than leave the rule unguarded')
                engine = lwp.TypoEngine({'rules': [rule]})
                out = engine.apply(cases[name])
                self.assertIn(' ', out,
                              f'{name} produced no non-breaking space on '
                              f'{cases[name]!r}: got {out!r}')
        self.assertGreaterEqual(len(seen), 8,
                                'the scan found too few nbsp rules to be '
                                f'measuring anything real: {sorted(seen)}')


class AuditSeesWhatABuildSees(unittest.TestCase):
    """`audit` read the syntax tree and never composed a page, so a whole
    class of fault was invisible to it — while `--strict` was documented
    as a CI gate. A pipeline could be green while a build of the same
    series printed a real warning (BACKLOG B19/B24).

    The partition was measured before the fix rather than recalled: the
    register claimed ten warning sites "in the build path", when ten is
    the count in the whole executable and most belong to other commands.
    Four are what a series can actually raise without audit seeing it, and
    each has a case here."""

    def _series(self, tmp):
        root = str(Path(tmp) / 's')
        self.assertEqual(run('init', root).returncode, 0)
        self.assertEqual(run('demo', root).returncode, 0)
        return root

    def _audit(self, root, *extra):
        plain = run('audit', root, *extra)
        strict = run('audit', root, '--strict', *extra)
        return plain, strict

    def test_a_clean_series_stays_clean(self):
        """The guard that stops every other case here from being vacuous.
        A gate that fires on a healthy series is noise, and noise is how a
        gate gets switched off."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            plain, strict = self._audit(root)
            self.assertEqual(plain.returncode, 0, plain.stderr)
            self.assertEqual(strict.returncode, 0,
                             'a healthy series failed --strict:\n'
                             + plain.stdout + plain.stderr)
            self.assertIn('No warnings', plain.stdout)

    def test_a_missing_language_pack_reaches_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            plain, strict = self._audit(root, '--lang', 'xx')
            self.assertIn('no language pack', plain.stderr)
            self.assertEqual(plain.returncode, 0,
                             'audit blocked — it must report and continue')
            self.assertEqual(strict.returncode, 1,
                             '--strict passed on a warning the build prints')

    def test_fields_parsed_on_a_cover_reach_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            first = Path(root) / 'sources' / 'first.md'
            first.write_text(
                first.read_text(encoding='utf-8').replace(
                    '<!-- lwp:slide:cover -->',
                    '<!-- lwp:slide:cover -->\nslug: k123\nfact-label: X', 1),
                encoding='utf-8')
            plain, strict = self._audit(root)
            self.assertIn('never rendered', plain.stderr)
            self.assertEqual(strict.returncode, 1)

    def test_an_escaping_image_symlink_reaches_audit(self):
        """This one needed more than rendering. The refusal lives in
        copy_images, a write step audit never reaches — but the finding is
        about the sources an author committed, not about the act of
        copying. The rule is shared with the copier rather than restated;
        a security rule written twice is one that will diverge."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            img = Path(root) / 'sources' / 'img'
            img.mkdir(exist_ok=True)
            try:
                (img / 'leak.png').symlink_to('/etc/hostname')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable on this filesystem')
            plain, strict = self._audit(root)
            self.assertIn('escaping the image directory', plain.stderr)
            self.assertEqual(strict.returncode, 1)
            # That audit wrote nothing is asserted on its own fixture
            # below, not here: `demo` builds, so public/img already
            # exists and checking it here would assert the fixture.

    def test_a_series_that_cannot_build_is_not_reported_clean(self):
        """The worst of the four, and the one that reads as a bug even
        without the gate: audit printed an [ERROR] and then concluded
        "No warnings: all editorial conventions are respected", exiting 0,
        on a series no build could produce. A summary contradicting a
        message three lines above it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            settings = Path(root) / 'templates' / 'settings.conf'
            settings.write_text(
                settings.read_text(encoding='utf-8') + '\npage.zzz: #000000\n',
                encoding='utf-8')
            self.assertEqual(run('build', root).returncode, 1,
                             'the premise changed: this still has to be fatal')
            plain, strict = self._audit(root)
            self.assertNotIn('No warnings', plain.stdout,
                             'audit called a series clean that cannot build:\n'
                             + plain.stdout)
            self.assertIn('does not build', plain.stderr)
            # The count, and not only the sentence. Mutation found that
            # every other assertion here is held up by audit_presentation,
            # which reports the unknown property on its own: the fatal
            # render could stop being counted entirely and this test stayed
            # green. The sibling below covers the same ground from the
            # other side; this makes the test hold its own claim.
            counted = re.search(r'(\d+) warning\(s\)', plain.stdout)
            self.assertIsNotNone(counted, plain.stdout)
            self.assertGreaterEqual(
                int(counted.group(1)), 2,
                'the fatal render is no longer counted — the property '
                'warning alone is holding this test up:\n' + plain.stdout)
            self.assertEqual(plain.returncode, 0,
                             'audit blocked — it must report and continue')
            self.assertEqual(strict.returncode, 1,
                             '--strict passed on a series that cannot build')

    def test_a_fatal_render_counts_even_when_it_warns_about_nothing(self):
        """The case above is not enough on its own, and measuring said so:
        an unknown property emits a warning AND the fatal error, so the
        collected count is non-zero whether or not the fatal itself is
        counted. Mutating the count away left that test green.

        A fatal that warns about nothing is the case that pins it — an
        unclosed tag is exactly that, measured: build exits 1, and the
        only warning audit prints is the one saying the series does not
        build. Remove the count and `--strict` goes green on a series
        that produces no page at all."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            first = Path(root) / 'sources' / 'first.md'
            first.write_text(
                first.read_text(encoding='utf-8')
                + '\n\n---\n\n<!-- lwp:slide -->\nslug: k124\n## T\n\n<div>never closed\n',
                encoding='utf-8')
            self.assertEqual(run('build', root).returncode, 1,
                             'the premise changed: this still has to be fatal')
            plain, strict = self._audit(root)
            # The premise is that the RENDER warns about nothing, so the
            # only finding is the one saying the series does not build.
            # That used to be written `stderr has no [WARNING]`, which
            # worked only while audit's own warnings went to stdout: the
            # proxy died when they moved (B26), and what it stood for is
            # asserted directly.
            others = [line for line in plain.stderr.split('\n')
                      if '[WARNING]' in line and 'does not build' not in line]
            self.assertEqual(others, [],
                             'the premise changed: this fatal now warns too, '
                             'so it no longer pins the count:\n' + plain.stderr)
            self.assertIn('does not build', plain.stderr)
            self.assertEqual(strict.returncode, 1,
                             '--strict passed on a series that cannot build '
                             'and warned about nothing else')

    def test_audit_writes_nothing_while_rendering(self):
        """Rendering to judge must not become building. The promise is not
        `--dry-run`'s: there is nothing to suppress, because no write is
        ever attempted."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            shutil.rmtree(Path(root) / 'public', ignore_errors=True)
            before = sorted(p.relative_to(root).as_posix()
                            for p in Path(root).rglob('*'))
            self.assertEqual(run('audit', root).returncode, 0)
            after = sorted(p.relative_to(root).as_posix()
                           for p in Path(root).rglob('*'))
            self.assertEqual(before, after,
                             'audit created or removed files: '
                             f'{set(after) ^ set(before)}')

    def test_templates_only_audit_skips_the_render(self):
        """`--templates` restricts audit to the presentation layer
        (DECISION-CLI §3). Rendering there would contradict the option's
        whole purpose, and would drag per-article faults into a run that
        was asked not to look at articles."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            first = Path(root) / 'sources' / 'first.md'
            first.write_text(
                first.read_text(encoding='utf-8').replace(
                    '<!-- lwp:slide:cover -->',
                    '<!-- lwp:slide:cover -->\nslug: k125\nfact-label: X', 1),
                encoding='utf-8')
            scoped = run('audit', root, '--templates')
            self.assertNotIn('never rendered', scoped.stderr,
                             '--templates rendered the articles anyway')
            self.assertEqual(scoped.returncode, 0)

    def test_the_collector_hooks_the_funnel_not_the_sites(self):
        """The design claim, asserted rather than trusted: warnings are
        captured because log() is hooked, so a warning added tomorrow is
        collected tomorrow. An enumeration of sites is what drifted in the
        register in the first place.

        Also pins the reentrancy refusal: one consumer, and an outer sink
        silently swallowed by an inner one is the defect this exists to
        stop."""
        lwp = load_lightwebpres_module()
        with lwp.collect_warnings() as sink:
            lwp.log('warn', 'a warning nobody enumerated')
            lwp.log('error', 'an error, which is not collected')
            lwp.log('info', 'progress, which is not collected')
        self.assertEqual(sink.messages, ['a warning nobody enumerated'])
        self.assertIsNone(lwp._WARN_SINK, 'the sink outlived its block')

        with self.assertRaises(RuntimeError):
            with lwp.collect_warnings():
                with lwp.collect_warnings():
                    pass
        self.assertIsNone(lwp._WARN_SINK,
                          'a refused nesting left the sink installed')


class AuditJudgesTheResolvedSheet(unittest.TestCase):
    """The engine validated FORM and never MEANING. An unknown property, a
    reference cycle, an invalid colour, an unknown unit: all fatal. Text
    the exact colour of its ground, a progress dot painted its own rail, a
    note at 3px: all exit 0, from build, from audit, and from
    `audit --strict` (BACKLOG B21, and the D3 decision — it warns).

    The thresholds are derived from the delivered catalogue, not chosen,
    and that is what these tests are really pinning. B5 and B18 decided a
    theme is NOT required to reach AA, so warning on "below AA" would
    harass shipped themes and contradict a written decision. A
    threshold that makes any delivered theme warn is a wrong threshold."""

    def _series(self, tmp, theme=None):
        root = str(Path(tmp) / 's')
        args = ['init', root] + (['--theme', theme] if theme else [])
        self.assertEqual(run(*args).returncode, 0)
        self.assertEqual(run('demo', root).returncode, 0)
        return root

    def _pin(self, root, text):
        conf = Path(root) / 'templates' / 'settings.conf'
        conf.write_text(conf.read_text(encoding='utf-8') + '\n' + text + '\n',
                        encoding='utf-8')

    def test_no_delivered_theme_triggers_the_judgement(self):
        """The load-bearing test of the whole pass, and the one that would
        catch a threshold set too high. Every shipped theme, plus the
        default sheet an author gets from a bare `init` — which is the one
        the first version of this pass got wrong, because it was only ever
        tried with --theme."""
        lwp = load_lightwebpres_module()
        slugs = sorted(lwp.THEMES)
        self.assertGreater(len(slugs), 50,
                           'the catalogue shrank; this sweep is not '
                           'measuring what it claims to')
        noisy = []
        with tempfile.TemporaryDirectory() as tmp:
            for slug in slugs + [None]:
                root = Path(tmp) / (slug or '_default')
                args = ['init', str(root)] + (['--theme', slug] if slug else [])
                self.assertEqual(run(*args).returncode, 0)
                self.assertEqual(run('demo', str(root)).returncode, 0)
                result = run('audit', str(root))
                # Both streams: the judgement pass prints on stdout, the
                # render's warnings reach stderr through log(). Reading one
                # of the two is how a sweep comes back clean without having
                # looked (BACKLOG B26).
                if '[WARNING]' in result.stdout + result.stderr:
                    noisy.append((slug or '(default sheet)',
                                  result.stdout + result.stderr))
        self.assertEqual([n for n, _ in noisy], [],
                         'a delivered theme warns, so the threshold is wrong '
                         'and the report is noise:\n'
                         + '\n'.join(o for _, o in noisy[:2]))

    def test_text_the_colour_of_its_ground_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            self._pin(root, 'page.fg: page.bg')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('page.fg', report)
            self.assertIn('1.00:1', report)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)
            # And the build still succeeds: audit warns, it does not forbid.
            self.assertEqual(run('build', root).returncode, 0)

    def test_an_invisible_progress_dot_is_named_as_a_broken_control(self):
        """§9.5.6 is explicit that this one is not a matter of taste: a
        control nobody can see is broken, not bold. It is the only hard
        floor the project states, and it was checked on the delivered
        themes by a test and never on what an author writes."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            self._pin(root, 'nav-dot.bg-active: #C6C9CD')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('nav-dot.bg-active', report)
            # `under 3:1`, not `3:1` — a bare `3:1` is also a substring of
            # a measured ratio ending in 3, so the loose form would pass on
            # a report that never mentioned the floor.
            self.assertIn('under 3:1', report)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)

    def test_a_size_under_the_readability_floor_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            self._pin(root, 'note.size: 3px')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('note.size', report)
            self.assertIn('under the 12px readability floor', report)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)

    def test_a_relative_size_is_not_judged_against_pixels(self):
        """`footnote-call.size` is `0.72em` on all built-in themes. Resolving em
        against an assumed 16px root reads 11.52px, so a naive pixel floor
        warns on the entire catalogue for a size that renders fine. The
        sweep above would catch it; this says why, so the next person to
        touch the floor knows what they are about to break."""
        lwp = load_lightwebpres_module()
        resolved = lwp.resolve_theme_properties(lwp.theme_property_layer('nord'))
        self.assertTrue(resolved['footnote-call.size'].endswith('em'),
                        'the premise changed: this size is no longer relative, '
                        'so it no longer guards the em/px distinction')
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            plain = run('audit', root)
            self.assertNotIn('footnote-call.size',
                             plain.stdout + plain.stderr)

    def test_a_fault_the_author_never_wrote_is_still_reported(self):
        """`footnote-call.fg-marked` defaults to `fact.strong.fg`. Kill the
        latter and the former follows it into invisibility — a fault only a
        judgement of the RESOLVED sheet can see, since nobody typed it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            self._pin(root, 'fact.strong.fg: fact.strong.bg')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('fact.strong.fg', report)
            self.assertIn('footnote-call.fg-marked', report,
                          'the inherited fault was not reported, so the pass '
                          'is reading what was written rather than what '
                          'resolves')

    def test_a_malformed_sheet_leaves_the_judgement_silent(self):
        """A sheet that cannot resolve is already fatal, with a precise
        message. Adding a vague judgement on top of it would bury the one
        line that says what to fix."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'nord')
            self._pin(root, 'page.zzz: #000000')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('unknown property', report)
            self.assertNotIn(':1 against', report,
                             'the judgement competed with the fatal error')
            # Silent, not absent: the pass has to stand aside, not die on
            # the way past. Mutation found that narrowing the except which
            # guards the composition leaves audit dying with an internal
            # error on this very fixture, with this test still green — the
            # `unknown property` line above is a premise, not a guard, and
            # audit_presentation prints it either way.
            self.assertEqual(plain.returncode, 0,
                             'audit did not survive a sheet that cannot '
                             'resolve:\n' + plain.stderr)
            self.assertNotIn('internal error', plain.stderr,
                             'the resolution failure escaped the judgement '
                             'pass instead of silencing it:\n' + plain.stderr)


class AuditNamesAFootnoteLabelTheEngineWillNotRead(unittest.TestCase):
    """The one defect in this format that reached the READER in silence.
    A misspelled slide field becomes free text, and on a cover says so
    fatally; an unknown meta key is named. But `[^a-b]` is neither an error
    nor a note: both note patterns spell the label `\\w+`, so a hyphen, a
    space or a dot drops the whole construct through as ordinary text — the
    call ships inside the sentence and the body renders as a paragraph,
    build and audit both silent, both exit 0 (BACKLOG B24)."""

    def _series(self, tmp):
        root = str(Path(tmp) / 's')
        self.assertEqual(run('init', root).returncode, 0)
        self.assertEqual(run('demo', root).returncode, 0)
        return root

    def test_a_label_outside_the_pattern_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            article = Path(root) / 'sources' / 'first_article.md'
            article.write_text(
                article.read_text(encoding='utf-8').replace('[^1]', '[^a-b]'),
                encoding='utf-8')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertIn('[^a-b]', report)
            self.assertIn('is not a note call', report)
            self.assertIn('is not a note body', report,
                          'a call and a body fail differently on the page '
                          'and want different advice')
            self.assertEqual(run('audit', root, '--strict').returncode, 1)
            # It reaches the reader, which is the whole point.
            self.assertEqual(run('build', root).returncode, 0)
            page = (Path(root) / 'public' / 'first.html').read_text(encoding='utf-8')
            self.assertIn('[^a-b]', page)

    def test_what_the_converter_would_not_read_as_a_note_is_left_alone(self):
        """The false positives that would make this unusable, each one
        measured against what the converter actually does rather than
        assumed: a regex class in code, a fenced block, raw HTML passed
        through verbatim, and `[^a-b](url)` — which md_inline's link rule
        claims before its note rule ever sees it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            article = Path(root) / 'sources' / 'first_article.md'
            article.write_text(
                article.read_text(encoding='utf-8') + '\n\n'
                'A class `[^a-z]+` in code, and `[^\\]]` too.\n\n'
                'A link [^a-b](https://example.org) and '
                'an image ![^a-b](img/demo-figure.svg).\n\n'
                '```regex\n[^a-b]\n[^a-b]: not a body\n```\n\n'
                '<div>\n[^a-b] and [^ab] in raw HTML\n</div>\n',
                encoding='utf-8')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            self.assertNotIn('is not a note', report,
                             'the guard invented a warning about text the '
                             'converter leaves alone:\n' + report)
            self.assertEqual(run('audit', root, '--strict').returncode, 0)


class RemainingTypographyRules(unittest.TestCase):
    """§7.2: the two French rules not already covered by
    test_typography_nbsp_before_double_punctuation."""

    def test_typography_nbsp_after_opening_quote(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k126\nkicker: T\n# Titre\nsummary: « Une citation.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('«\xa0Une citation.', html)

    def test_typography_nbsp_before_percent(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k127\nkicker: T\n## Title\nhighlight: 50 %\nhighlight-caption: half\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('50\xa0%', html)


class NbspUnitsAndThousands(unittest.TestCase):
    """§7.5: the three newer French rules — thousands grouping, number
    before a unit word/$, and ×/≈ before a number — each only upgrade an
    existing ASCII space next to a digit, never insert new spacing."""

    def _build_summary(self, summary):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k128\nkicker: T\n# Titre\nsummary: {summary}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            m = re.search(r'<p class="summary">(.*?)</p>', html)
            self.assertIsNotNone(m)
            return m.group(1)

    def test_thousands_separator_upgrades_existing_spaces(self):
        out = self._build_summary('170 000 000 vues.')
        self.assertIn('170\xa0000\xa0000', out)

    def test_thousands_separator_does_not_group_unspaced_number(self):
        out = self._build_summary('170000 vues.')
        self.assertIn('170000', out)
        self.assertNotIn('\xa0', out)

    def test_thousands_separator_leaves_4_digit_year_alone(self):
        out = self._build_summary('En 1998 ou en 2024.')
        self.assertNotIn('\xa0', out)

    def test_number_before_unit_words_and_dollar_sign(self):
        out = self._build_summary('170 millions, 20 dollars, 5 $.')
        self.assertIn('170\xa0millions', out)
        self.assertIn('20\xa0dollars', out)
        self.assertIn('5\xa0$', out)

    def test_informal_word_after_number_is_not_a_recognized_unit(self):
        out = self._build_summary('68 likes seulement.')
        self.assertIn('68 likes', out)
        self.assertNotIn('\xa0', out)

    def test_operator_before_number(self):
        out = self._build_summary('Environ ≈ 5 et × 4 la dose.')
        self.assertIn('≈\xa05', out)
        self.assertIn('×\xa04', out)


class NbspPreservedFromSource(unittest.TestCase):
    """§7.6: a non-breaking space already present in the author's source
    must reach the generated HTML unchanged, whether it sits at the
    START or the END of a field value, at every location the parser
    recognizes a value — str.strip()/str.rstrip() (and the \\s* in a
    field regex, which matches U+00A0 exactly like they do) would
    otherwise eat one sitting at the edge."""

    NBSP = '\xa0'

    def _wrap(self, s):
        return f'{self.NBSP}{s}{self.NBSP}'

    def _both_ends(self, value):
        self.assertTrue(value.startswith(self.NBSP), repr(value))
        self.assertTrue(value.endswith(self.NBSP), repr(value))

    def _build(self, tmp, article_md, extra_articles=None, series_meta=None, second_entry=None):
        root = scaffold(tmp, article_md, series_extra={'card_label': self._wrap('Carte')})
        if extra_articles:
            for name, content in extra_articles.items():
                (root / 'sources' / name).write_text(content, encoding='utf-8')
        if series_meta or second_entry:
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            if series_meta:
                data = {'series_meta': series_meta, 'articles': data if isinstance(data, list) else data['articles']}
            if second_entry:
                articles = data if isinstance(data, list) else data['articles']
                articles.append(second_entry)
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        return root

    def test_cover_slide_tag_h1_summary(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k129\nkicker: {w("Tag")}\n# {w("Titre")}\nsummary: {w("Résumé")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<span class="slide-kicker">(.*?)</span>', html).group(1))
            self._both_ends(re.search(r'<h1>(.*?)</h1>', html).group(1))
            self._both_ends(re.search(r'<p class="summary">(.*?)</p>', html).group(1))

    def test_standard_slide_all_fields(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k130\n'
            f'kicker: {w("Tag")}\n'
            f'## {w("Titre")}\n'
            f'summary: {w("Résumé")}\n'
            f'fact-label: {w("Label")}\n'
            f'highlight: {w("42")}\n'
            f'highlight-caption: {w("Légende")}\n'
            f'source: {w("Réf")}\n\n'
            f'{w("Corps de la fiche")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<span class="slide-kicker">(.*?)</span>', html).group(1))
            self._both_ends(re.search(r'<h2>(.*?)</h2>', html).group(1))
            self._both_ends(re.search(r'<p class="summary">(.*?)</p>', html).group(1))
            self._both_ends(re.search(r'<div class="fact-label">(.*?)</div>', html).group(1))
            self._both_ends(re.search(r'<span class="highlight-figure">(.*?)</span>', html).group(1))
            self._both_ends(re.search(r'<span class="highlight-caption">(.*?)</span>', html).group(1))
            # source is rendered as "Source : {value}" (§4.3), so only
            # the value's own edges are checked, via substring containment.
            self.assertIn(w('Réf'), re.search(r'<p class="source">(.*?)</p>', html).group(1))
            self._both_ends(re.search(r'<div class="fact-content">\s*<p>(.*?)</p>', html).group(1))

    def test_leading_nbsp_in_field_value_is_not_swallowed_by_regex(self):
        """Regression: the field regex used `key:\\s*(.*)`, and \\s
        matches U+00A0 exactly like str.strip() does — a leading nbsp
        right after the colon was silently dropped even after strip_ws()
        started protecting the rest of the pipeline."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide -->\nslug: k131\nkicker: T\n## Titre\nsummary:{self.NBSP}Résumé\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            summary = re.search(r'<p class="summary">(.*?)</p>', html).group(1)
            self.assertTrue(summary.startswith(self.NBSP), repr(summary))

    def test_page_title_survives(self):
        md = (
            f'<!-- lwp:meta -->\npage_dest: a.html\npage_title: {self._wrap("Titre de page")}\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k132\nkicker: T\n# Titre\nsummary: Résumé.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<title>(.*?)</title>', html).group(1))

    def test_meta_block_value_survives(self):
        """card_desc (rendered as <div class="article-desc"> on the
        index) falls back to the cover slide's own summary when neither
        series.json nor the article's meta block set card_desc directly
        (§20.3.1) — this exercises that fallback path and checks the
        nbsp in the cover's summary survives through it."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k133\nkicker: T\n# Titre\nsummary: {self._wrap("Description")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir(parents=True, exist_ok=True)
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': 'a.html', 'page_source': 'a.md'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<div class="article-desc">(.*?)</div>', index_html).group(1))

    def test_full_article_headings_paragraph_table_and_footnote(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k134\nkicker: T\n# Titre\nsummary: Résumé.\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k135\narticle: a_article.md\n'
        )
        article_md = (
            f'# {w("Titre article")}\n\n'
            f'## {w("Sous-titre")}\n\n'
            f'### {w("Sous-sous-titre")}\n\n'
            f'{w("Un paragraphe")}\n\n'
            '| A | B |\n| --- | --- |\n'
            f'| {w("Cellule")} | Autre |\n\n'
            f'Un appel de note[^1].\n\n'
            f'[^1]: {w("Corps de la note")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md, extra_articles={'a_article.md': article_md})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # Two <h1>s exist on the page (the cover slide's, and the
            # full-article's own) — scope the search past the opening tag
            # of the full-article <section> so <h1> below matches the
            # right one, not the cover's. (The bare string 'full-article'
            # appears earlier still, inside the <style> block's own
            # ".full-article" selector.)
            article_html = html[html.index('<section class="slide full-article"'):]
            self._both_ends(re.search(r'<h1>(.*?)</h1>', article_html).group(1))
            self._both_ends(re.search(r'<h2>(.*?)</h2>', article_html).group(1))
            self._both_ends(re.search(r'<h3>(.*?)</h3>', article_html).group(1))
            self._both_ends(re.search(r'<p>(.*?)</p>', article_html).group(1))
            self._both_ends(re.search(r'<td>(.*?)</td>', article_html).group(1))

    def test_leading_nbsp_in_footnote_definition_is_not_swallowed_by_regex(self):
        """Regression: the footnote-definition regex used `\\]:\\s*(.*)`,
        same \\s-matches-U+00A0 issue as the slide-field regex."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k136\nkicker: T\n# Titre\nsummary: Résumé.\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k137\narticle: a_article.md\n'
        )
        article_md = f'Un appel[^1].\n\n[^1]:{self.NBSP}Corps de la note.\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md, extra_articles={'a_article.md': article_md})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            m = re.search(r'<span class="note-num">1</span>(.*?)<a class="note-back"', html)
            self.assertIsNotNone(m, html)
            self.assertTrue(m.group(1).startswith(self.NBSP), repr(m.group(1)))

    def test_index_series_meta_and_card_fields_survive(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n'
            f'card_title: {w("Carte titre")}\ncard_desc: {w("Carte desc")}\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k138\nkicker: T\n# Titre\nsummary: Résumé.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, md,
                series_meta={'title': w('Titre série'), 'subtitle': w('Sous-titre série'), 'intro': w('Intro série')},
            )
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<h1>(.*?)</h1>', index_html).group(1))
            self._both_ends(re.search(r'class="subtitle">(.*?)</p>', index_html).group(1))
            self._both_ends(re.search(r'class="intro">\s*<p>(.*?)</p>', index_html, re.DOTALL).group(1))
            self._both_ends(re.search(r'<div class="article-number">(.*?)</div>', index_html).group(1))
            self._both_ends(re.search(r'<div class="article-title">(.*?)</div>', index_html).group(1))
            self._both_ends(re.search(r'<div class="article-desc">(.*?)</div>', index_html).group(1))


class DashesAreNeverOrphaned(unittest.TestCase):
    """A dash left with breakable spaces on both sides can end a line or
    begin one, alone. The French pack had six rules and not one of them
    touched a dash. Imprimerie nationale: the spaces INSIDE a paired incise
    are non-breaking, the outer ones stay breakable."""

    NB = '\u00a0'

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()
        cls.fr = cls.lwp.TypoEngine(json.loads(cls.lwp.LANG_FR))

    def _typo(self, text):
        return self.lwp.apply_typo(self.fr, text, None)

    def test_a_paired_incise_binds_inward_and_stays_breakable_outward(self):
        out = self._typo('Le sujet — celui-ci — est clair.')
        self.assertEqual(out, f'Le sujet —{self.NB}celui-ci{self.NB}— est clair.')

    def test_an_unpaired_dash_binds_to_the_word_before_it(self):
        # So it can never begin a line, which in French reads as dialogue.
        out = self._typo('Le fait est simple — et il est mesuré.')
        self.assertEqual(out, f'Le fait est simple{self.NB}— et il est mesuré.')

    def test_the_en_dash_follows_the_same_rule(self):
        out = self._typo('Un cas – plus court – ici.')
        self.assertEqual(out, f'Un cas –{self.NB}plus court{self.NB}– ici.')

    def test_a_hyphen_is_not_a_dash(self):
        # The one thing these rules must never touch: a compound word or a
        # page range. Nothing here is spaced, so nothing matches.
        for text in ('pages 12-15 et Marie-Claire', 'c-à-d', 'sous-jacent'):
            self.assertEqual(self._typo(text), text)

    def test_a_dialogue_dash_opening_a_line_is_left_alone(self):
        # Nothing precedes it, so binding it backwards would be meaningless.
        self.assertEqual(self._typo('— Bonjour, dit-il.'), '— Bonjour, dit-il.')

    def test_several_incises_pair_correctly(self):
        out = self._typo('Trois — une — puis — deux — ici.')
        n = self.NB
        self.assertEqual(out, f'Trois —{n}une{n}— puis —{n}deux{n}— ici.')

    def test_english_gets_the_same_protection(self):
        # First written asserting English was left alone, on the belief that
        # it sets the dash closed up. Both styles are in use: Chicago closes
        # it up (word—word), AP and most web writing space it (word — word),
        # and the spaced form orphans exactly as readily as in French. The
        # rule is about layout, not language — it protects a space that is
        # already there and never changes what is written.
        en = self.lwp.TypoEngine(json.loads(self.lwp.LANG_EN))
        f = lambda t: self.lwp.apply_typo(en, t, None)
        n = self.NB
        self.assertEqual(f('The point — this one — is clear.'),
                         f'The point —{n}this one{n}— is clear.')
        # Inert where there is no space to bind.
        self.assertEqual(f('The point—this one—is clear.'),
                         'The point—this one—is clear.')
        self.assertEqual(f('pages 12-15'), 'pages 12-15')


class TypographyDisableSwitches(unittest.TestCase):
    """§4.5/§19.6: typo_units/typo_thousands/typo meta fields and
    --no-typography each turn off part or all of the typography engine,
    scoped exactly as documented — per-rule, per-article, or global."""

    def test_a_switch_with_nothing_to_disable_says_so(self):
        """Resolving the opt-outs through categories fixed one silent
        no-op and opened another. A pack whose rules carry no `category`
        — hand-written, or copied into a series by an `init` older than
        v0.40.0 — yields an empty set, so the field is read, accepted,
        and ignored.

        Measured on a real series before this warning: with a v0.39.0
        pack in `language/`, `typo_units: off` still produced
        `170<nbsp>millions`; with the pack deleted, it produced
        `170 millions`. Nothing said a word. §2.4's promise that nothing
        is a silent no-op is not a promise about options only."""
        md = ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
              'nav_title: A\nnav_desc: A\ntypo_units: off\n---\n\n'
              '<!-- lwp:slide:cover -->\nslug: k139\nkicker: K\n# T\n'
              'summary: Environ 170 millions de personnes.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            self.assertEqual(
                run('template', 'write', 'fr.json', str(root)).returncode, 0)
            pack = root / 'language' / 'fr.json'
            data = json.loads(pack.read_text(encoding='utf-8'))
            for rule in data['rules']:
                rule.pop('category', None)
            pack.write_text(json.dumps(data, indent=2), encoding='utf-8')
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
            r = run('build', str(root), '--quiet',
                    '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('typo_units: off has nothing to disable', r.stderr)
            self.assertIn('a.md', r.stderr)
            # And the switch really is inert, which is what makes the
            # warning worth printing rather than a nicety.
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('170\u00a0millions', html)

    def test_the_switch_is_silent_when_it_has_something_to_disable(self):
        """The other half. A warning that fires on a healthy series is
        noise every author learns to skip past."""
        md = ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
              'nav_title: A\nnav_desc: A\ntypo_units: off\n---\n\n'
              '<!-- lwp:slide:cover -->\nslug: k140\nkicker: K\n# T\n'
              'summary: Environ 170 millions de personnes.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
            r = run('build', str(root), '--quiet',
                    '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('nothing to disable', r.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('170 millions', html)

    def test_the_warning_is_said_once_a_build_not_once_an_article(self):
        """The cause is the pack in force, not the article. A series that
        sets the field on every article would otherwise print the same
        line once per article — twenty-eight times on the series this was
        found in, which is how a real warning becomes wallpaper."""
        meta = ('<!-- lwp:meta -->\npage_dest: {d}.html\npage_title: T\n'
                'nav_title: {d}\nnav_desc: {d}\ntypo_units: off\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k141\nkicker: K\n# T\n'
                'summary: Environ 170 millions de gens.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            self.assertEqual(
                run('template', 'write', 'fr.json', str(root)).returncode, 0)
            pack = root / 'language' / 'fr.json'
            data = json.loads(pack.read_text(encoding='utf-8'))
            for rule in data['rules']:
                rule.pop('category', None)
            pack.write_text(json.dumps(data, indent=2), encoding='utf-8')
            entries = []
            for name in ('a', 'b', 'c'):
                (root / 'sources' / f'{name}.md').write_text(
                    meta.format(d=name), encoding='utf-8')
                entries.append({'page_dest': f'{name}.html',
                                'page_source': f'{name}.md',
                                'nav_title': name, 'nav_desc': name})
            (root / 'series.json').write_text(
                json.dumps({'articles': entries}), encoding='utf-8')
            r = run('build', str(root), '--quiet',
                    '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.count('has nothing to disable'), 1,
                             r.stderr)

    def _two_article_series(self, tmp, meta_extra_b=''):
        root = Path(tmp)
        (root / 'sources').mkdir(parents=True, exist_ok=True)
        summary = 'Environ ≈ 5 $ pour 170 000 000 vues, × 4 la dose, 170 millions de gens, 20 dollars.'
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k142\nkicker: T\n# Titre A\nsummary: {summary}\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            f'{meta_extra_b}---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k143\nkicker: T\n# Titre B\nsummary: {summary}\n'
        )
        (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(md_b, encoding='utf-8')
        entries = [
            {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
            {'page_dest': 'b.html', 'page_source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B'},
        ]
        (root / 'series.json').write_text(json.dumps({'articles': entries}), encoding='utf-8')
        return root

    def _summary_of(self, root, output, filename):
        html = (root / output / filename).read_text(encoding='utf-8')
        m = re.search(r'<p class="summary">(.*?)</p>', html)
        return m.group(1)

    def test_the_opt_outs_reach_the_language_pack_actually_in_force(self):
        """They used to name three French rule names. All three exist in
        the French pack and one of them in the English, which calls its
        unit rules `nbsp_before_metric_unit` and `nbsp_before_unit_word`
        and has no thousands rule at all — so under `--lang en`,
        `typo_units: off` left both unit rules running and
        `typo_thousands: off` was a silent no-op. Measured: "3 kW" and
        "5 million" both kept their non-breaking space with the field
        set.

        The opt-out reads the pack's own categories now, so it reaches a
        pack this repository has never seen."""
        for lang in ('fr', 'en'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'series'
                self.assertEqual(run('init', str(root)).returncode, 0)
                (root / 'sources' / 't.md').write_text(
                    '<!-- lwp:meta -->\npage_dest: t.html\npage_title: T\n'
                    'nav_title: T\nnav_desc: T\ntypo_units: off\n---\n\n'
                    '<!-- lwp:slide:cover -->\nslug: k144\nkicker: T\n# T\n'
                    'summary: 3 kW and 5 million and 20 dollars.\n',
                    encoding='utf-8')
                (root / 'series.json').write_text(json.dumps({'articles': [
                    {'page_dest': 't.html', 'page_source': 't.md',
                     'nav_title': 'T', 'nav_desc': 'T'}]}), encoding='utf-8')
                r = run('build', str(root), '--lang', lang,
                        '--output', str(root / 'public'))
                self.assertEqual(r.returncode, 0, r.stderr)
                summary = self._summary_of(root, 'public', 't.html')
                self.assertNotIn('\u00a0', summary,
                                 f'{lang}: a unit rule survived typo_units: off')

    def test_every_shipped_rule_says_what_it_is_for(self):
        """The category is what an opt-out names, so a rule without one
        is a rule no opt-out can reach — which is exactly the state the
        English pack was in. A rule may legitimately carry none (a custom
        pack written before the field is still valid), but none of the
        rules shipped here may."""
        lwp = load_lightwebpres_module()
        known = {'punctuation', 'dash', 'unit', 'thousands', 'operator'}
        for pack_name in ('LANG_FR', 'LANG_EN'):
            pack = json.loads(getattr(lwp, pack_name))
            for rule in pack['rules']:
                self.assertIn('category', rule,
                              f'{pack_name}: {rule["name"]} has no category')
                self.assertIn(rule['category'], known,
                              f'{pack_name}: {rule["name"]}')

    def test_typo_units_off_disables_only_units_for_that_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp, meta_extra_b='typo_units: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertIn('170\xa0millions', a)
            self.assertIn('170 millions', b)
            # Thousands separator is untouched by typo_units: off.
            self.assertIn('170\xa0000\xa0000', b)

    def test_typo_thousands_off_disables_only_thousands_for_that_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp, meta_extra_b='typo_thousands: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertIn('170\xa0000\xa0000', a)
            self.assertIn('170 000 000', b)
            # Units rule is untouched by typo_thousands: off.
            self.assertIn('170\xa0millions', b)

    def test_typo_off_disables_every_rule_for_that_article_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp, meta_extra_b='typo: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertIn('\xa0', a)
            self.assertNotIn('\xa0', b)
            self.assertIn(
                'Environ ≈ 5 $ pour 170 000 000 vues, × 4 la dose, 170 millions de gens, 20 dollars.',
                b,
            )

    def test_typo_off_also_disables_the_page_title(self):
        """title_clean (<title>...</title>) goes through article_typo_engine
        + disabled_rules like every other field in build_article — not a
        separate, easy-to-forget code path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir(parents=True, exist_ok=True)
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Titre à 50 % fini\nnav_title: A\n'
                'nav_desc: A\ntypo: off\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k145\nkicker: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            title = re.search(r'<title>(.*?)</title>', html).group(1)
            self.assertEqual(title, 'Titre à 50 % fini')
            self.assertNotIn('\xa0', title)

    def test_no_typography_flag_disables_index_page_typography_too(self):
        """--no-typography passes typo_engine=None into build_index() as
        well as build_article() — the index's own title/subtitle/intro
        and article cards are not a separate, easy-to-forget code path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir(parents=True, exist_ok=True)
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k146\nkicker: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
            series = {
                'series_meta': {'title': 'Titre à 50 % fini', 'subtitle': '', 'intro': ''},
                'articles': [entry],
            }
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'), '--no-typography')
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            title = re.search(r'<h1>(.*?)</h1>', index_html).group(1)
            self.assertEqual(title, 'Titre à 50 % fini')
            self.assertNotIn('\xa0', title)

    def test_no_typography_flag_disables_every_rule_for_whole_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp)
            result = run('build', str(root), '--output', str(root / 'public'), '--no-typography')
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertNotIn('\xa0', a)
            self.assertNotIn('\xa0', b)

    def test_no_typography_flag_works_on_check_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp)
            result = run('verify', str(root), '--no-typography')
            # Nothing built yet under this flag's semantics, so everything
            # is [NEW] — the point is the flag is accepted and check runs.
            self.assertIn(result.returncode, (0, 1))
            self.assertNotIn('Traceback', result.stderr)


class TemplateOverride(unittest.TestCase):
    """§9/§12/§18: the author's surface must actually reach the page —
    values through templates/settings.conf, rules through
    templates/custom.css. Behaviour is the third surface and is not in
    the series by default: the navigation script lives in the executable
    and `template write nav.js` puts a copy under `templates/` for
    whoever wants to change it (§9.4.5).

    The old whole-file style.css override is gone — the sheet is
    composed in memory — and its guarantee splits into the tests below,
    one per author file, plus the one that keeps `custom.css` from
    publishing anything the tool put there."""

    def test_custom_css_rules_are_appended_after_the_composed_sheet(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k147\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'templates').mkdir()
            (root / 'templates' / 'custom.css').write_text(
                '/* CUSTOM-MARKER-CSS */\n.mine { color: red; }\n', encoding='utf-8',
            )
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('/* CUSTOM-MARKER-CSS */', html)
            # Order is the author's win condition: their rules come after
            # the composed sheet, so they beat it at equal specificity.
            self.assertGreater(html.index('/* CUSTOM-MARKER-CSS */'),
                               html.index('--color-page:'))

    def test_the_file_init_creates_contributes_nothing_to_the_page(self):
        """The test above is the reason this one has to exist. custom.css
        is appended verbatim, so anything the tool writes into it as
        advice to the author is advice published to every reader.

        It was: `init` wrote 227 bytes of prose explaining what the file
        was for, and every page built from a scaffolded series carried
        the sentence "lightwebpres never writes this file". The contrast
        that makes it plain is settings.conf, which carries five hundred
        comment lines that reach nothing — because settings.conf is
        parsed and this file is not.

        Asserted as a byte comparison rather than a search for the old
        wording, which would pass again the moment someone writes
        different prose."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k148\nkicker: T\n# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.md',
                 'nav_title': 'A', 'nav_desc': 'A'}]}), encoding='utf-8')
            custom = root / 'templates' / 'custom.css'
            self.assertTrue(custom.exists())
            out = root / 'public'
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            with_file = (out / 'a.html').read_text(encoding='utf-8')
            custom.unlink()
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            without_file = (out / 'a.html').read_text(encoding='utf-8')
            self.assertEqual(with_file, without_file)

    def test_settings_conf_values_reach_the_page(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k149\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'templates').mkdir()
            # A hand-written settings file, not a scaffold: the surface is
            # plain `key: value`, so a file of one line is legitimate.
            (root / 'templates' / 'settings.conf').write_text(
                'color.mark: #123456\n', encoding='utf-8',
            )
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--color-mark: #123456FF;', html)

    def test_custom_nav_js_is_used(self):
        """templates/nav.js REPLACES the built-in engine, it does not join it.

        The old test asserted only that the author's marker appeared. A
        build that emits both scripts satisfies that and is the failure
        worth catching: two engines on one page bind every keyboard
        listener twice, so one press of `n` opens the presenter panel and
        closes it again. The built-in's signature has to be gone."""
        lwp = load_lightwebpres_module()
        signature = 'function qrEncode'
        self.assertIn(signature, lwp.TEMPLATE_NAV_JS,
                      'the signature line moved -- pick another')
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k150\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'templates').mkdir()
            (root / 'templates' / 'nav.js').write_text(
                '/* CUSTOM-MARKER-JS */', encoding='utf-8',
            )
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('/* CUSTOM-MARKER-JS */', html)
            self.assertNotIn(signature, html,
                             'the built-in engine shipped alongside the '
                             'override instead of standing aside')

        # Positive control: the signature IS there when nothing overrides
        # it. Without this the assertion above passes against a build that
        # stopped emitting nav.js at all.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn(signature, html)

    def test_index_extra_html_is_inserted_before_body_close(self):
        """§9.3: templates/index_extra.html, if present, is inserted as-is
        just before </body> on the index page only (not article pages)."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k151\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'templates').mkdir()
            (root / 'templates' / 'index_extra.html').write_text(
                '<div id="qr-share">CUSTOM-INDEX-EXTRA</div>\n'
                '<script>console.log("extra");</script>',
                encoding='utf-8',
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('CUSTOM-INDEX-EXTRA', index_html)
            self.assertIn(
                '<div id="qr-share">CUSTOM-INDEX-EXTRA</div>\n<script>console.log("extra");</script>\n</body>',
                index_html,
            )
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('CUSTOM-INDEX-EXTRA', article_html)

    def test_no_index_extra_html_leaves_index_unaffected(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k152\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            # The extra placeholder sits between the script and </body>
            # ({{index_extra}}), so with no file to insert it the page
            # must end cleanly — nothing of its own after the script.
            self.assertIn('</script>\n\n</body>', index_html)


class RefreshTemplates(unittest.TestCase):
    """§11.6: what the command does to the AUTHOR's surface — create
    `settings.conf` or `custom.css` when they are missing, regenerate the
    commented scaffold under `--scaffold`, report a legacy `style.css`
    without migrating it. The stylesheet is composed at build time, so it
    is fresh by construction and no file of it can go stale; the marker
    machinery, with its [SKIP] and exit-1 paths, went with the shared
    file that required it.

    What the command does to the TOOL's files — removing a copy of
    `nav.js` or a language pack that a series should no longer be
    holding — is in
    `TheToolKeepsItsOwnFilesAndHandsThemOverOnRequest`, with the reason
    it does so."""

    def test_requires_install_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('template', 'update', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('init', result.stderr.lower())

    def test_it_says_so_when_there_is_nothing_to_do(self):
        """A freshly scaffolded series holds nothing this command owns —
        since v0.40.0 that is the normal state, not an unusual one — and
        saying nothing at all would read as a command that failed
        quietly. The author's two files are named as untouched, because
        "nothing to do" has to mean nothing was done."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            before = {name: (root / 'templates' / name).read_text(encoding='utf-8')
                      for name in ('settings.conf', 'custom.css')}
            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Nothing to update', result.stdout)
            for name, text in before.items():
                self.assertEqual((root / 'templates' / name).read_text(encoding='utf-8'),
                                 text, name)

    def test_missing_settings_and_custom_are_created_and_reported(self):
        """A series scaffolded before the rewrite has neither file:
        writing a file that does not exist breaks no ownership promise,
        and each creation is named so the author knows the surface
        appeared."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            (root / 'templates' / 'settings.conf').unlink()
            (root / 'templates' / 'custom.css').unlink()

            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('settings.conf (new, default theme)', result.stdout)
            self.assertIn('custom.css (new, empty)', result.stdout)
            settings = (root / 'templates' / 'settings.conf').read_text(encoding='utf-8')
            self.assertIn('# theme: <slug>', settings)
            self.assertTrue((root / 'templates' / 'custom.css').exists())

    def test_an_edited_settings_conf_is_never_rewritten(self):
        """The ownership rule itself, on a file that LOOKS stale: an
        author's uncommented value and their own comment must survive
        refresh byte for byte — signalling drift is audit's job, not an
        excuse to write."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'nord').returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            edited = settings.read_text(encoding='utf-8').replace(
                '# color.mark: #EBCB8B', 'color.mark: #EBCB8B', 1,
            ) + '# my own note\n'
            settings.write_text(edited, encoding='utf-8')

            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_text(encoding='utf-8'), edited)

    def test_a_legacy_style_css_warns_but_never_fails(self):
        """The pre-rewrite exit-1-without-marker path is gone: a leftover
        style.css is the author's file holding the author's values, so it
        is reported (it is silently unread otherwise) and left exactly in
        place — refresh must still succeed at its own job."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            legacy = '/* old scaffold */\n.old-custom { color: blue; }\n'
            style_path = root / 'templates' / 'style.css'
            style_path.write_text(legacy, encoding='utf-8')

            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARNING]', result.stderr)
            self.assertNotIn('[ERROR]', result.stderr, result.stderr)
            self.assertIn('style.css is no longer read', result.stderr)
            self.assertEqual(style_path.read_text(encoding='utf-8'), legacy)


class ScaffoldRegeneration(unittest.TestCase):
    """refresh-templates --scaffold — the action audit points to when the
    commented values drift from the declared theme, and the only supported
    way to see a new version's properties without hand-merging. It refreshes
    the commented surface for the current theme and keeps every uncommented
    pin. Before it existed, the docs pointed at an action with no command."""

    def _settings(self, root):
        return (root / 'templates' / 'settings.conf').read_text(encoding='utf-8')

    def test_it_realigns_scaffold_for_and_keeps_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--theme', 'evergreen', '--force')
            root = Path(tmp)
            conf = root / 'templates' / 'settings.conf'
            conf.write_text(self._settings(root)
                            .replace('# kicker.fg: ink-quiet', 'kicker.fg: call'),
                            encoding='utf-8')
            run('series', 'theme', 'set', tmp, '--theme', 'crimson')
            self.assertIn('# scaffold-for: evergreen', self._settings(root))

            r = run('template', 'update', tmp, '--scaffold')
            self.assertEqual(r.returncode, 0, r.stderr)
            after = self._settings(root)
            self.assertIn('# scaffold-for: crimson', after)   # realigned
            self.assertIn('\ntheme: crimson', after)
            self.assertIn('\nkicker.fg: call', after)            # pin kept
            self.assertIn('2 pinned value(s) kept'
                          if '2 pinned' in r.stdout else 'pinned value', r.stdout)

    def test_the_pin_still_wins_in_the_build_after_regen(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--theme', 'crimson', '--force')
            root = Path(tmp)
            conf = root / 'templates' / 'settings.conf'
            conf.write_text(self._settings(root)
                            .replace('# kicker.fg: ink-quiet', 'kicker.fg: call'),
                            encoding='utf-8')
            run('template', 'update', tmp, '--scaffold')
            scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                          'slug: r221\n# Cover\n\nsummary: s\n')
            self.assertEqual(run('build', tmp).returncode, 0)
            page = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--kicker-fg: #B00020FF;', page)   # crimson's call

    def test_a_retired_pin_survives_repeated_regenerations(self):
        # The quiet-data-loss case: a pinned property a future version
        # dropped is moved to the retired section commented — and must
        # still be there after a SECOND and THIRD regen, not silently gone.
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--theme', 'nord', '--force')
            root = Path(tmp)
            conf = root / 'templates' / 'settings.conf'
            conf.write_text(self._settings(root) + '\nphantom.axis: #123456\n',
                            encoding='utf-8')
            r = run('template', 'update', tmp, '--scaffold')
            self.assertIn('no longer exist', r.stderr)
            for _ in range(3):
                run('template', 'update', tmp, '--scaffold')
            after = self._settings(root)
            self.assertIn('# phantom.axis: #123456', after)
            self.assertIn('no longer recognized', after)
            # and it does not break the build
            scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                          'slug: r221\n# Cover\n\nsummary: s\n')
            self.assertEqual(run('build', tmp).returncode, 0)

    def test_scaffold_regen_needs_an_existing_settings_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            (Path(tmp) / 'templates' / 'settings.conf').unlink()
            r = run('template', 'update', tmp, '--scaffold')
            self.assertEqual(r.returncode, 1)
            self.assertIn('nothing to regenerate', r.stderr)

    def test_regen_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--theme', 'sage', '--force')
            run('template', 'update', tmp, '--scaffold')  # no pins, no drift
            r = run('template', 'update', tmp, '--scaffold')
            self.assertIn('already current', r.stdout)


class BuildStamp(unittest.TestCase):
    """§11.3.2: --build-stamp is opt-in (off by default) and, when
    passed, embeds a "Compiled at <date/time> with lightwebpres
    v<version>" marker on every generated page — but is invisible to
    `check`, which must keep comparing real content, not a timestamp
    that's different on every single run by design."""

    STAMP_RE = re.compile(
        # style="..." is inline (deliberately not dependent on a
        # .build-stamp rule in style.css, which a series with its own
        # templates/style.css might not have) — [^>]* between the class
        # and the closing > tolerates that without hardcoding its exact
        # value here.
        r'<div class="build-stamp"[^>]*>Compiled at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) '
        r'with lightwebpres v([\d.]+)\.</div>'
    )

    def _md(self):
        return (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k153\nkicker: T\n# Title\nsummary: Summary.\n'
        )

    def test_absent_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            # Not a plain "build-stamp" substring check: the .build-stamp
            # CSS rule itself is always in the stylesheet, flag or not —
            # only the actual <div> element is conditional.
            self.assertIsNone(self.STAMP_RE.search(article_html), article_html)
            self.assertIsNone(self.STAMP_RE.search(index_html), index_html)

    def test_present_on_every_page_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            result = run('build', str(root), '--output', str(root / 'public'), '--build-stamp')
            self.assertEqual(result.returncode, 0, result.stderr)
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')

            article_match = self.STAMP_RE.search(article_html)
            index_match = self.STAMP_RE.search(index_html)
            self.assertIsNotNone(article_match, article_html)
            self.assertIsNotNone(index_match, index_html)

            # Same build run -> same timestamp everywhere, not a fresh
            # one per file (which would just be noise: the point is "when
            # did THIS build happen", one answer for the whole run).
            self.assertEqual(article_match.group(1), index_match.group(1))

            version = run('help').stdout.split('LightWebPres v', 1)[1].split(' ', 1)[0]
            self.assertEqual(article_match.group(2), version)

    def test_check_ignores_the_stamp_no_false_drift(self):
        """A series built with --build-stamp must still `check` clean —
        the marker's live timestamp is deliberately excluded from check's
        own comparison (cmd_check strips it from the on-disk copy first),
        or every check on a stamped series would report permanent,
        meaningless drift purely because time moved on since the build."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            build_result = run('build', str(root), '--output', str(root / 'public'), '--build-stamp')
            self.assertEqual(build_result.returncode, 0, build_result.stderr)

            check_result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(check_result.returncode, 0, check_result.stdout + check_result.stderr)
            self.assertIn('[OK] a.html', check_result.stdout)
            self.assertNotIn('[DRIFT]', check_result.stdout)

    def test_build_only_also_stamps(self):
        """The --only fast path (§11.3.1) writes real output too — it
        must not silently skip the stamp just because it takes a
        different code path than a full build."""
        md_a = self._md()
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md_a)
            (root / 'sources' / 'b.md').write_text(
                '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k154\nkicker: T\n# B\nsummary: Summary.\n',
                encoding='utf-8',
            )
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'].append({'page_dest': 'b.html', 'page_source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B'})
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')

            first = run('build', str(root), '--output', str(root / 'public'), '--nav-cache', str(root / 'nav.json'))
            self.assertEqual(first.returncode, 0, first.stderr)

            only = run(
                'build', str(root), '--output', str(root / 'public'),
                '--nav-cache', str(root / 'nav.json'), '--only', 'a.html', '--build-stamp',
            )
            self.assertEqual(only.returncode, 0, only.stderr)
            self.assertIn('Incremental build', only.stdout)

            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIsNotNone(self.STAMP_RE.search(article_html))
            self.assertIsNotNone(self.STAMP_RE.search(index_html))

    def test_stays_discreet_with_a_custom_style_css_lacking_the_rule(self):
        """Regression: the marker's positioning/color used to live only
        in a `.build-stamp` CSS rule inside the built-in stylesheet — a
        series with its own templates/style.css (customized, or just
        scaffolded before this option existed) has no such rule and no
        way to pick one up short of refresh-templates (§9.4), so the
        marker rendered as a plain full-width block-flow line pushing the
        first slide down, not the intended small fixed corner overlay.
        The fix carries its own styling inline; assert that's still true
        so this can't silently regress back to depending on style.css."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            (root / 'templates').mkdir()
            # No .build-stamp anywhere in this custom stylesheet — the
            # exact shape of the series that triggered the original bug.
            (root / 'templates' / 'style.css').write_text(
                '/* a custom stylesheet with no build-stamp rule at all */\n'
                'body { background: white; }\n',
                encoding='utf-8',
            )
            result = run('build', str(root), '--output', str(root / 'public'), '--build-stamp')
            self.assertEqual(result.returncode, 0, result.stderr)
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            match = self.STAMP_RE.search(article_html)
            self.assertIsNotNone(match, article_html)
            style_attr = re.search(r'<div class="build-stamp" style="([^"]*)"', article_html)
            self.assertIsNotNone(style_attr, article_html)
            self.assertIn('position:absolute', style_attr.group(1))

    def test_minimal_variant_has_no_date_or_version(self):
        """--build-stamp-minimal (§11.3.2): a build date/time is data
        that may or may not be safe to publish (it can reveal when a
        document was prepared) — the minimal marker drops it entirely,
        along with the version, rather than a half-measure."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            result = run('build', str(root), '--output', str(root / 'public'), '--build-stamp-minimal')
            self.assertEqual(result.returncode, 0, result.stderr)
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="build-stamp" style="', article_html)
            self.assertIn('>Compiled with lightwebpres.</div>', article_html)
            self.assertIn('>Compiled with lightwebpres.</div>', index_html)
            # No leftover date/version anywhere near the marker.
            self.assertIsNone(self.STAMP_RE.search(article_html), article_html)
            self.assertNotIn('lightwebpres v', article_html.split('build-stamp')[1][:120])

    def test_minimal_wins_if_both_flags_passed(self):
        """A privacy choice must never be silently overridden by the
        richer flag also being present, however that happened (a stray
        flag left over from a script, a copy-pasted command...)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            result = run(
                'build', str(root), '--output', str(root / 'public'),
                '--build-stamp', '--build-stamp-minimal',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            article_html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('>Compiled with lightwebpres.</div>', article_html)
            self.assertIsNone(self.STAMP_RE.search(article_html), article_html)

    def test_minimal_variant_ignored_by_check_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, self._md())
            build_result = run('build', str(root), '--output', str(root / 'public'), '--build-stamp-minimal')
            self.assertEqual(build_result.returncode, 0, build_result.stderr)
            check_result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertEqual(check_result.returncode, 0, check_result.stdout + check_result.stderr)
            self.assertIn('[OK] a.html', check_result.stdout)


class Themes(unittest.TestCase):
    """§9/§11.1/§11.7: install --theme writes a settings.conf scaffold that
    DECLARES the theme (`theme: <slug>` plus every property commented at
    that theme's value), and build composes the themed stylesheet in memory
    into every page. The substituted style.css, its theme marker and the
    marker-reading upgrade path are gone: a theme is one line in a file the
    author owns, so there is nothing left to re-substitute or misread."""

    def test_install_without_theme_leaves_the_theme_line_commented(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            settings = (root / 'templates' / 'settings.conf').read_text(encoding='utf-8')
            # No theme chosen is a state, not an omission: the placeholder
            # stays commented and the scaffold says whose values it shows.
            self.assertIn('# theme: <slug>', settings)
            self.assertIn('# scaffold-for: default', settings)
            self.assertIn('# color.mark: #FFFC00', settings)
            self.assertNotRegex(settings, re.compile(r'^theme:', re.MULTILINE))

    def test_install_with_valid_theme_declares_it_in_the_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root), '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Nord', result.stdout)
            settings = (root / 'templates' / 'settings.conf').read_text(encoding='utf-8')
            self.assertIn('\ntheme: nord\n', settings)
            self.assertIn('# scaffold-for: nord', settings)
            # Commented values show the CHOSEN theme's palette, so the
            # author uncomments what they see, not the default's leftovers.
            self.assertIn('# color.mark: #EBCB8B', settings)
            self.assertNotIn('#FFFC00', settings)
            # The author surface ships whole even with a theme: custom.css
            # is where rules go, and no style.css exists to be edited.
            self.assertTrue((root / 'templates' / 'custom.css').exists())
            self.assertFalse((root / 'templates' / 'style.css').exists())

    def test_install_with_unknown_theme_is_a_fatal_error_listing_valid_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root), '--theme', 'not-a-real-theme')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not-a-real-theme', result.stderr)
            self.assertIn('nord', result.stderr)
            self.assertFalse((root / 'templates').exists())

    def test_refresh_templates_never_touches_the_declared_theme(self):
        """What the marker-reapply tests protected — an upgrade must not
        lose the theme choice — holds by construction now: the choice
        lives in settings.conf and refresh-templates never writes an
        existing settings.conf. Pinned on bytes, not on re-derivation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'dracula').returncode, 0)
            settings_path = root / 'templates' / 'settings.conf'
            before = settings_path.read_text(encoding='utf-8')
            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings_path.read_text(encoding='utf-8'), before)

    def test_themes_gallery_default_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('theme', 'gallery', cwd=str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            gallery = root / 'themes-gallery.html'
            self.assertTrue(gallery.exists())

    def test_themes_gallery_explicit_path_documents_every_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'gallery.html'
            result = run('theme', 'gallery', str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = out.read_text(encoding='utf-8')
            for label in ('Nord', 'Dracula', 'Solarized Light', 'Gruvbox Light',
                          'Catppuccin Latte', 'Tokyo Night', 'Monokai', 'Everforest',
                          'Rosé Pine Dawn'):
                self.assertIn(f'<h2>{label}</h2>', html)
            # The palette reaches the preview through its own composed
            # stylesheet (ARGB-normalised), not through an inline style
            # attribute the gallery assembled itself.
            self.assertIn('--color-mark: #EBCB8BFF;', html)
            self.assertIn('lightwebpres init my-series --theme nord', html)
            # One card per theme, whatever the count — asserting a literal
            # number here just means editing the test every time a palette
            # is added, which tests nothing.
            expected = len(load_lightwebpres_module().THEMES)
            # Prefix, not the exact tag: cards carry data-* facet
            # attributes (§9.5.3), so an exact-string count silently
            # dropped to zero when those were added.
            open_tags = html.count('<article class="theme-row"')
            close_tags = html.count('</article>')
            self.assertEqual(open_tags, expected)
            self.assertEqual(open_tags, close_tags)
            # Every card must be filterable, or the facet bar lies.
            for facet in ('data-polarity=', 'data-hue=', 'data-family='):
                self.assertEqual(html.count(facet), expected)

    def test_themed_build_actually_uses_the_declared_theme(self):
        """Declaring a theme and painting with it are two different code
        paths; only the built page proves they are connected. Both the
        article page and the index carry the composed sheet inline."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'nord').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            for page in ('a.html', 'index.html'):
                html = (root / 'public' / page).read_text(encoding='utf-8')
                self.assertIn('--color-mark: #EBCB8BFF;', html, page)


_SIZE_RE = re.compile(r'^max\(\s*([0-9.]+)(px|rem)\s*,\s*([0-9.]+)vmin\s*\)$')


def _floor_px(value):
    """The px a size falls back to on a small screen. Every font size in
    the design reads `max(<floor>, <n>vmin)`; a bare `<n>px` or `<n>rem`
    is one that has not been given a scale yet, and an em is relative to
    a parent that already has one."""
    m = _SIZE_RE.match(value.strip())
    if m:
        n, unit = float(m.group(1)), m.group(2)
        return n * 16 if unit == 'rem' else n
    if value.endswith('rem'):
        return float(value[:-3]) * 16
    if value.endswith('px'):
        return float(value[:-2])
    return None


def _coefficient(value):
    """The vmin coefficient of a size -- what governs it on a big screen.
    Zero for a size with no scale at all, which is what makes a missing
    one sort below every real one instead of raising."""
    m = _SIZE_RE.match(value.strip())
    return float(m.group(3)) if m else 0.0


def load_lightwebpres_module():
    """Imports the executable as a module, for the few things that can
    only be checked from the inside. Safe: everything below `if __name__
    == '__main__'` stays unrun, so importing has no side effect."""
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('lightwebpres_under_test', str(EXECUTABLE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class DarkBackgroundThemes(unittest.TestCase):
    """§9.5.2 -> §9 rewrite: what dark_background used to switch behind
    the theme's back (SURFACE_PRESETS) is now stated by the theme's own
    property layer — DARK_FURNITURE_PROPS is the ex-preset dissolved into
    ordinary component colours. This test guards the renderer invariant: a
    white surface veil must not turn a card into an unreadable pale block over
    a dark page. It does not guarantee the readability of every palette
    value."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_a_dark_layer_carries_the_furniture_a_light_layer_does_not(self):
        """The flag/preset mapping, restated as layers. This mapping once
        caught a real bug (the flag was first called `dark`, ALSO a
        palette key, so theme.get('dark') was a truthy colour string and
        every theme silently went dark), so it stays pinned per slug
        rather than as 'all are light'."""
        for slug, theme in self.lwp.THEMES.items():
            layer = self.lwp.theme_property_layer(slug)
            # Minus what the theme states for itself. The furniture is a
            # DEFAULT for a polarity, not a lock: a theme that names its
            # own value for one of these axes is doing the ordinary
            # layering the whole system is built on, and computing the
            # exemption from the tables keeps this honest when they grow
            # rather than pinning a list that goes stale.
            own = (set(self.lwp.THEME_NOTE_PROPS.get(slug, {}))
                   | set(self.lwp.THEME_PROPERTY_OVERRIDES.get(slug, {})))
            expected = {k: v for k, v in self.lwp.DARK_FURNITURE_PROPS.items()
                        if k not in own}
            if theme.get('dark_background'):
                self.assertTrue(expected.items() <= layer.items(),
                                f'{slug} is dark but its layer lacks the dark furniture')
            else:
                for key in expected:
                    self.assertNotIn(key, layer,
                                     f'{slug} is light but its layer overrides {key}')
        # Both polarities must actually be represented, or the mapping
        # above is only ever exercised in one direction.
        polarities = {bool(t.get('dark_background')) for t in self.lwp.THEMES.values()}
        self.assertEqual(polarities, {True, False})
        # The one that actually broke: a dark surface must stay a white
        # veil, only a faint one (alpha 0E = 5.5%), never a heavy wash.
        self.assertEqual(self.lwp.DARK_FURNITURE_PROPS['fact.bg'], '#FFFFFF0E')

    def test_a_dark_themed_build_paints_the_dark_furniture(self):
        """End to end through the real install/build path: the inverted
        veil reaches the page a reader loads, not just the layer dict."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'terminal').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('build', str(root)).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--fact-bg: #FFFFFF0E;', html)

    def test_a_light_themed_build_keeps_the_light_furniture(self):
        """The registry defaults ARE the light set — a light theme must
        not drag the dark veils in, which is the inverse silent failure
        of the `dark` flag bug."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'nord').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('build', str(root)).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--fact-bg: #FFFFFFB8;', html)

    def test_the_fact_highlight_gets_readable_ink_on_a_dark_theme(self):
        """The fact-box marker sets a BACKGROUND from the palette's
        bright tone. Setting no ink alongside it silently assumes the
        text over it is dark — true on a light theme, false on a dark
        one, where the ink is the LIGHT text colour. Measured in a
        browser on a real dark build before this: contrast ratio 1.00,
        i.e. the figure was invisible. On a dark theme the page IS the
        dark ground, so it is the ink this needs."""
        dark = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('terminal'))
        self.assertEqual(dark['fact.strong.bg'], dark['color.mark'])
        self.assertEqual(dark['fact.strong.fg'], dark['color.page'])

        light = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('nord'))
        self.assertEqual(light['fact.strong.fg'], light['color.ink'])

        # No marker means no marker to sit on: the text keeps the body
        # ink, or a dark theme would paint it dark-on-dark. `fact_highlight:
        # None` is a stated absence — the first port run turned those five
        # themes yellow by treating it as 'nothing said'.
        bare = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('solarized'))
        self.assertEqual(bare['fact.strong.bg'], '#00000000')
        self.assertEqual(bare['fact.strong.fg'], bare['color.ink'])


class ThePrintFamilyKeepsPaperWhiteAndNamesItsInkTreatment(unittest.TestCase):
    SURFACES = (
        'page.bg', 'cover.bg.from', 'cover.bg.to',
        'fact.bg', 'code.bg', 'note.page.bg', 'article.bg',
        'table.col-signal.bg', 'table.col-snap.bg',
        'series-nav.current.bg', 'series-nav.link.bg',
        'nav-btn.bg', 'nav-btn.bg-soft', 'share.bg', 'share.bg-hover',
        'card.bg', 'version-tag.bg',
    )

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def _resolved(self, slug):
        return self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer(slug))

    def test_the_print_family_has_the_three_original_themes_and_print_boss(self):
        self.assertEqual(
            [slug for slug, theme in self.lwp.THEMES.items()
             if theme.get('family') == 'print'],
            ['print-ink', 'print-grey', 'print-color', 'print-boss'])

    def test_every_print_surface_is_opaque_white(self):
        for slug, theme in self.lwp.THEMES.items():
            if theme.get('family') != 'print':
                continue
            resolved = self._resolved(slug)
            for prop in self.SURFACES:
                self.assertEqual(resolved[prop], '#FFFFFFFF', f'{slug}: {prop}')
            self.assertEqual(resolved['cover.fg'], resolved['color.ink'], slug)
            self.assertEqual(resolved['cover.summary.fg'], resolved['color.ink'], slug)
            self.assertEqual(resolved['cover.kicker.fg'], resolved['color.ink'], slug)

    def test_print_ink_is_bold_without_a_highlight_and_print_boss_is_regular_on_yellow(self):
        ink = self._resolved('print-ink')
        self.assertEqual(ink['fact.strong.weight'], 'bold')
        self.assertEqual(ink['fact.strong.bg'], '#00000000')

        boss = self._resolved('print-boss')
        self.assertEqual(boss['fact.strong.weight'], 'normal')
        self.assertEqual(boss['fact.strong.bg'], '#FFF200FF')
        self.assertEqual(self.lwp.THEMES['print-boss']['fact_highlight'], 'marker')

    def test_print_ink_and_grey_keep_a_low_ink_table_header(self):
        for slug in ('print-ink', 'print-grey'):
            self.assertEqual(self._resolved(slug)['table.head.bg'], '#F4F4F4FF', slug)
        for slug in ('print-color', 'print-boss'):
            self.assertEqual(self._resolved(slug)['table.head.bg'], '#FFFFFFFF', slug)


class EveryNeutralVeilIsMeasuredOnEveryThemeItLandsOn(unittest.TestCase):
    """The dark-furniture omission, caught by measurement instead of by
    membership. It has now happened twice — the notes plate and its two
    rules, then `share.bg-hover`, `share.rule-fg` and `article.rule-fg` —
    and both times the table LOOKED complete to anyone reading it. So
    nothing here reads `DARK_FURNITURE_PROPS`: the veils are DISCOVERED
    from the registry (a colour property whose default is pure black or
    pure white plus an alpha carries no palette information — it only
    lightens or darkens whatever is under it), resolved per theme, and
    composited.

    A forgotten veil is caught whichever way it points. A white one kept
    from the light set becomes a pale slab in the middle of a dark page —
    `note.page.bg` measured 1.02:1 on pop-fuchsia, `share.bg-hover` 1.00:1
    on everforest, both times with the heading exactly invisible. A black
    one drawn on a near-black page is a rule nobody can see —
    `share.rule-fg` measured 1.01:1 on dread.

    Neither criterion carries a tuned threshold, because a threshold
    tuned to today's catalogue is a threshold that will be wrong for the
    thirty-fourth theme. Each is a statement about which side of the
    page/ink axis the composited veil lands on."""

    # A literal that is pure black or pure white plus an alpha: a veil,
    # not a colour. `#FFFFFF00` and `#000000FF` are both in the family;
    # what matters is that the RGB carries nothing.
    NEUTRAL = re.compile(r'^#(?:000000|FFFFFF)[0-9A-Fa-f]{2}$')

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    @staticmethod
    def _rgba(value):
        h = value.lstrip('#')
        h = h + 'FF' if len(h) == 6 else h
        return [int(h[i:i + 2], 16) for i in (0, 2, 4, 6)]

    @classmethod
    def _over(cls, fg, bg):
        a = fg[3] / 255
        return [round(fg[i] * a + bg[i] * (1 - a)) for i in range(3)] + [255]

    @staticmethod
    def _lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return .2126 * ch(c[0]) + .7152 * ch(c[1]) + .0722 * ch(c[2])

    @classmethod
    def _ratio(cls, a, b):
        la, lb = cls._lum(a), cls._lum(b)
        return (max(la, lb) + .05) / (min(la, lb) + .05)

    def _veils(self):
        """(surfaces, rules) discovered from the registry, by key."""
        surfaces, rules = [], []
        for key, prop in self.lwp.PROPERTY_REGISTRY.items():
            if prop.type is not self.lwp.PROP_COLOR:
                continue
            if not isinstance(prop.default, str) or not self.NEUTRAL.match(prop.default):
                continue
            if prop.css == 'background':
                surfaces.append(key)
            elif prop.css and 'border' in prop.css:
                rules.append(key)
        return sorted(surfaces), sorted(rules)

    def test_the_scan_reaches_every_veil_the_dark_table_decides_about(self):
        """The non-vacuity guard, and the only place the table is read.
        Every key someone thought worth inverting must be a key this scan
        finds — otherwise a regex that stopped matching would empty both
        buckets and the two tests below would pass by measuring nothing.
        The reverse containment is deliberately NOT asserted: a veil the
        table does not mention is exactly what these tests exist to
        judge on the numbers rather than on the list."""
        surfaces, rules = self._veils()
        found = set(surfaces) | set(rules)
        self.assertTrue(surfaces and rules, 'the veil scan found nothing to measure')
        missed = sorted(set(self.lwp.DARK_FURNITURE_PROPS) - found)
        self.assertEqual(missed, [], 'the dark table inverts veils the scan cannot see')

    def test_a_surface_veil_stays_a_veil_of_the_page_on_every_dark_theme(self):
        """A surface veil is a departure FROM the page — a card raised off
        it, a code block sunk into it. Composited, it must therefore still
        be nearer the page than the ink; the day it is nearer the ink it
        has stopped being a veil and become a slab, which is the shape
        both occurrences of this bug took.

        Dark themes only, and not out of timidity: the registry defaults
        ARE the light set, so on a light theme this asks whether the
        defaults are their own inverse. `share.scrim` — which darkens the
        whole viewport behind the QR modal and is meant to be far from the
        page — would fail it there, correctly and uselessly."""
        for slug, theme in self.lwp.THEMES.items():
            if not theme.get('dark_background'):
                continue
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug), {})
            page, ink = self._rgba(r['color.page']), self._rgba(r['color.ink'])
            for key in self._veils()[0]:
                surface = self._over(self._rgba(r[key]), page)
                to_page = self._ratio(surface, page)
                to_ink = self._ratio(surface, ink)
                self.assertGreater(
                    to_ink, to_page,
                    f'{slug}: {key} composites to a surface nearer the ink '
                    f'({to_ink:.2f}:1) than the page ({to_page:.2f}:1) — it is '
                    f'a slab, not a veil')

    def test_a_rule_veil_departs_from_the_page_toward_the_ink(self):
        """A rule exists to be seen against the page, so it has to move
        away from it, and the only direction with room is the one the ink
        already went: darker on a light theme, lighter on a dark one. A
        veil left un-inverted moves the wrong way and lands on the page's
        own floor — measured at 1.01:1 for `share.rule-fg` on dread.

        The whole catalogue, both polarities, because stated this way the
        constraint is the same sentence on each."""
        for slug in self.lwp.THEMES:
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug), {})
            page, ink = self._rgba(r['color.page']), self._rgba(r['color.ink'])
            ink_is_lighter = self._lum(ink) > self._lum(page)
            for key in self._veils()[1]:
                painted = self._over(self._rgba(r[key]), page)
                moved = self._lum(painted) - self._lum(page)
                went_right_way = moved > 0 if ink_is_lighter else moved < 0
                self.assertTrue(
                    went_right_way,
                    f'{slug}: {key} composites to {painted[:3]} against a page of '
                    f'{page[:3]} — it moves away from the ink, so it has the '
                    f'page floor to be seen against and nothing else')


class ThemeFacets(unittest.TestCase):
    """§9.5.3: past a dozen palettes the gallery stops being a thing you
    read and becomes a thing you search. Two of the three facets are
    derived rather than declared, so they can never contradict the
    palette they describe."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_hue_is_named_from_perception_not_from_rgb(self):
        """Hue is computed in CIELAB. RGB cannot tell a pale cream from a
        full orange — both sit at the same angle — and naming from it
        labelled Solarized's paper 'orange', which no reader would say.
        Boundaries were calibrated by measuring references, since
        CIELAB's angles are not the ones RGB intuition suggests (a full
        blue sits near 297 degrees, not 240)."""
        cases = [
            ('#9E1128', 'red'), ('#FF9500', 'orange'), ('#FFD400', 'yellow'),
            ('#075C26', 'green'), ('#075B6E', 'cyan'), ('#1B3FBF', 'blue'),
            ('#5B1DB8', 'violet'), ('#94105F', 'magenta'),
            # Paper and ink: a hue angle exists but no reader would name it.
            ('#FDF6E3', 'neutral'), ('#F8F8F2', 'neutral'), ('#0B0B0D', 'neutral'),
        ]
        for hex_colour, expected in cases:
            self.assertEqual(
                self.lwp.theme_hue_family({'page': hex_colour}), expected,
                f'{hex_colour} should read as {expected}',
            )

    def test_every_theme_declares_a_family_from_the_closed_vocabulary(self):
        """Family is the one facet that is DECLARED, not measured.

        Polarity and hue are read off the palette, so a theme cannot lie
        about them and a colour change moves the facet with it.
        "This is the register of work" is an editorial statement no amount
        of CIELAB recovers from seven hex values — so it is declared, and
        therefore fenced: the vocabulary is closed and every theme must
        name one of its members.

        `theme_facets` returns None for a theme that declares nothing,
        deliberately: a silent default would file a new theme under `desk`
        and nobody would see it happen. This test is what makes the
        absence loud instead."""
        families = self.lwp.THEME_FAMILIES
        self.assertEqual(tuple(families), self.lwp.FACET_VALUES['family'],
                         'the facet vocabulary and the family table differ')
        for slug, theme in self.lwp.THEMES.items():
            fam = theme.get('family')
            self.assertIsNotNone(fam, f'{slug} declares no family')
            self.assertIn(fam, families, f'{slug} declares an unknown family')
        # Every family earns its place: one that names no theme is a word
        # in a table, and the next reader cannot tell whether it is
        # aspirational or dead.
        used = {t.get('family') for t in self.lwp.THEMES.values()}
        self.assertEqual(used, set(families),
                         f'families with no theme: {set(families) - used}')

    def test_the_family_filter_narrows_the_listing(self):
        """`--family` is not special-cased anywhere: `_facet_filters` is
        generic over FACET_VALUES, so adding a facet there gives it a
        working filter. That is worth a test precisely because nothing
        was written to make it work."""
        lwp = load_lightwebpres_module()
        expected = sum(1 for t in lwp.THEMES.values()
                       if t.get('family') == 'ported')
        self.assertGreater(expected, 1, 'no ported theme to filter for')
        result = run('theme', 'list', '--family', 'ported')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'{expected} of {len(lwp.THEMES)} themes match',
                      result.stdout)
        # And it really excludes: a theme from another family must be gone.
        other = next(s for s, t in lwp.THEMES.items()
                     if t.get('family') != 'ported')
        self.assertNotIn(f'  {other}  ', result.stdout)
        # An unknown family is refused by name, not answered with silence.
        bad = run('theme', 'list', '--family', 'bogus')
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn('Unknown --family', bad.stderr)

    def test_the_neutral_threshold_follows_lightness(self):
        """A fixed chroma bar is wrong at both ends of the scale. These
        three were each misfiled by one: a cream with real chroma that
        still reads as paper, and two near-blacks that keep their hue at
        chroma a light colour would not even show."""
        for slug, expected in (('gruvbox', 'neutral'),      # cream, C=21.8
                               ('blueprint-night', 'blue'),  # navy, C=12.6
                               ('evergreen', 'green')):      # near-black green
            self.assertEqual(self.lwp.theme_hue_family(self.lwp.THEMES[slug]),
                             expected, slug)
        # The bar rises with lightness and never falls below its floor.
        self.assertGreater(self.lwp.neutral_chroma_threshold(95),
                           self.lwp.neutral_chroma_threshold(10))
        self.assertEqual(self.lwp.neutral_chroma_threshold(0),
                         self.lwp.NEUTRAL_CHROMA_FLOOR)

    def test_every_theme_carries_every_facet_FACET_VALUES_declares(self):
        """Driven by FACET_VALUES rather than by a list written here.

        This used to be `..._the_three_facets` and checked exactly three,
        so `family` arriving made the name wrong and the body blind on the
        same day. A retired facet or a new one now moves this test on its
        own."""
        for key, theme in self.lwp.THEMES.items():
            facets = self.lwp.theme_facets(theme)
            self.assertEqual(set(facets), set(self.lwp.FACET_VALUES), key)
            for name, allowed in self.lwp.FACET_VALUES.items():
                self.assertIn(facets[name], allowed, (key, name))

    def test_polarity_facet_agrees_with_the_furniture_actually_applied(self):
        """The facet is a label; the property layer drives real CSS. If
        they ever disagreed the gallery would file a theme under the
        wrong heading while rendering it the other way."""
        for key, theme in self.lwp.THEMES.items():
            dark_facet = self.lwp.theme_facets(theme)['polarity'] == 'dark'
            # Same exemption as above: a theme naming its own value for a
            # furniture axis has not changed polarity.
            own = (set(self.lwp.THEME_NOTE_PROPS.get(key, {}))
                   | set(self.lwp.THEME_PROPERTY_OVERRIDES.get(key, {})))
            expected = {k: v for k, v in self.lwp.DARK_FURNITURE_PROPS.items()
                        if k not in own}
            dark_css = expected.items() <= self.lwp.theme_property_layer(key).items()
            self.assertEqual(dark_facet, dark_css, key)

    def test_the_gallery_preview_receives_the_dark_furniture(self):
        """Without it a dark-backgrounded theme previews with the light
        defaults' surfaces — a white card on a black page — so the
        gallery would misrepresent exactly the themes hardest to judge.
        The furniture reaches the preview the only way it should: inside
        the preview document's own composed stylesheet; the gallery no
        longer injects a single variable by hand."""
        for slug, theme in self.lwp.THEMES.items():
            doc = self.lwp.build_theme_preview_document(slug)
            expected = ('#FFFFFF0E' if theme.get('dark_background')
                        else '#FFFFFFB8')
            self.assertIn(f'--fact-bg: {expected};', doc, slug)


class GalleryPreviewIsARealCard(unittest.TestCase):
    """§11.7: the gallery preview is not an imitation of a card, it IS
    one — same parser, same renderer, same stylesheet, in an iframe so the
    stylesheet's viewport-relative sizes resolve against the preview.

    It used to be a hand-written mock with its own .preview-* rules, and
    a copy kept in step by hand was not: it painted every dark theme with
    a light page's overlays (a highlight measured at 1.00:1, invisible),
    and it laid the key figure out as a left-aligned row with an arrow
    between figure and caption that render_slide() has never emitted.
    Both were invisible to a suite that checked the copy against itself.

    So these tests assert IDENTITY rather than correspondence. There is no
    mapping left to drift."""

    @property
    def EMPHASIS_VARS(self):
        # Derived from the registry: a static list held the OLD names
        # (-highlight/-ink) after the rename to -bg/-fg, so the realistic
        # regression — hand-injecting the new names — was invisible to it.
        return tuple(p.var for p in self.lwp.PROPERTY_REGISTRY.values()
                     if p.key.startswith('fact.strong.'))

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_the_preview_stylesheet_is_the_themed_stylesheet_itself(self):
        """Not "equivalent to": the exact string a real series on that
        theme gets composed at build time. Nothing can be missing from
        it, because it is not assembled a second time."""
        for slug in ('nord', 'graphite', 'pop-lemon'):
            doc = self.lwp.build_theme_preview_document(slug)
            sheet = self.lwp.compose_stylesheet(
                self.lwp.resolve_theme_properties(
                    self.lwp.theme_property_layer(slug)))
            self.assertIn(sheet, doc, slug)

    def test_the_preview_markup_is_what_render_slide_produces(self):
        """Byte-for-byte the renderer's own output, for each slide the
        mock carries — itself written in the real article format and put
        through the real parser."""
        _, slides, _, _ = self.lwp.parse_markdown_extended(
            self.lwp.TEMPLATE_THEMES_GALLERY_MOCK)
        self.assertGreaterEqual(len(slides), 2, 'the mock lost its slides')
        pack = self.lwp.load_language(None, 'en')
        engine = self.lwp.TypoEngine(pack)
        # absorb_punct must match what build_theme_preview_document computes
        # for nord (which carries a ground), or the comma/point after a bold
        # run is absorbed on one side and not the other.
        resolved = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('nord'))
        absorb = (resolved.get('fact.strong.absorb-punct') == 'on'
                  and not resolved.get('fact.strong.bg', '').endswith('00'))
        # The panels are not a page and their cards are not an author's,
        # so the gallery names them itself rather than reading a `slug:`
        # out of the mock. Named here too, with the same values: the
        # comparison is byte for byte, and an id is bytes.
        for i, (slide, panel) in enumerate(zip(slides, ('cover', 'card')), 1):
            rendered = self.lwp.render_slide(slide, i, len(slides), engine,
                                             pack.get('strings', {}),
                                             absorb_punct=absorb,
                                             show_slide_num=True,
                                             slide_id=f'preview-{panel}')
            self.assertIn(rendered,
                          self.lwp.build_theme_preview_document('nord', panel),
                          f'{panel} panel')

    def test_the_four_panels_show_four_different_surfaces(self):
        """A row whose panels all showed the same thing would be four
        times the weight for one panel's worth of information."""
        docs = {p: self.lwp.build_theme_preview_document('nord', p)
                for p, _ in self.lwp.THEMES_GALLERY_PANELS}
        self.assertEqual(len(docs), 4)
        bodies = [d.split('<body>', 1)[1] for d in docs.values()]
        self.assertEqual(len(set(bodies)), 4, 'two panels render the same body')
        self.assertIn('class="slide slide-cover"', docs['cover'])
        # The card panel must show the note AT ITS FOOT, not just the
        # call: a body scrolled out of a 560px window is the one thing
        # this panel exists to disprove.
        self.assertIn('class="notes-local"', docs['card'])
        self.assertIn('role="doc-footnote"', docs['card'])
        self.assertIn('class="slide notes-section"', docs['notes'])
        self.assertIn('role="doc-endnote"', docs['notes'])
        self.assertIn('class="slide full-article"', docs['article'])
        # No panel may ship an unresolved note marker.
        for name, doc in docs.items():
            self.assertNotIn('\x02', doc, name)

    def test_the_panels_render_at_their_true_size(self):
        """The previous gallery rendered at 1100px and scaled 0.34, which
        put 14px note text under 5 screen pixels. A transform reappearing
        on .preview means the notes became unreadable again.

        The width was the literal 340px and is now the shared
        `--gal-panel`, so the gallery can use a wide screen instead of
        sitting in a fixed column. Both sides are asserted: the width IS
        that variable -- one number for every row, or two rows are two
        renderings -- and the height is that same variable through the
        ratio it was measured at. A height stated any other way distorts
        the aspect, and the sheet inside sets its type in vmin, so a
        distorted aspect is a different rendering rather than the same one
        at another size."""
        head = self.lwp.TEMPLATE_THEMES_GALLERY_HEAD
        preview = head.split('.preview {', 1)[1].split('}', 1)[0]
        self.assertNotIn('transform', preview)
        self.assertIn('width: var(--gal-panel);', preview)
        self.assertRegex(
            preview,
            r'height:\s*calc\(var\(--gal-panel\) \* (\d+) / (\d+)\);')
        ratio = re.search(
            r'height:\s*calc\(var\(--gal-panel\) \* (\d+) / (\d+)\);', preview)
        # The denominator is the width the panels were composed against,
        # which is also the clamp's floor: at that width the panel is
        # exactly the 340 x 560 it was measured as.
        self.assertEqual(ratio.group(2), '340')
        self.assertEqual(ratio.group(1), '560')

    def test_the_mock_exercises_the_parts_a_theme_actually_changes(self):
        """A preview that shows no fact-box says nothing about the
        emphasis axes; one with no verdict cell says nothing about the
        shape markers."""
        # Across the four panels together: the verdict table moved to the
        # article panel when the card had to make room for its note.
        doc = ''.join(self.lwp.build_theme_preview_document('nord', p)
                      for p, _ in self.lwp.THEMES_GALLERY_PANELS)
        self.assertIn('class="slide slide-cover"', doc)
        for cls in ('slide-kicker', 'summary', 'highlight-figure',
                    'highlight-caption', 'fact-box', 'fact-label',
                    'comparison-table', 'note-body', 'note-call', 'refs'):
            self.assertIn(f'class="{cls}"', doc, cls)
        self.assertIn('<strong>', doc, 'nothing exercises the emphasis axes')

    def test_no_imitation_of_the_stylesheet_survives_in_the_gallery(self):
        """The whole point of the refactor. A `.preview-*` rule
        reappearing means someone started keeping a second copy again."""
        gallery = self.lwp.TEMPLATE_THEMES_GALLERY_HEAD
        # .preview-frame is the card's own scaled window onto the iframe;
        # anything else prefixed .preview- is a rule imitating the real
        # stylesheet, which is exactly what this refactor removed.
        imitations = {c for c in re.findall(r'\.preview-[a-z-]+', gallery)
                      if c != '.preview-frame'}
        self.assertEqual(imitations, set())
        for var in self.EMPHASIS_VARS:
            self.assertNotIn(f'{var}:{{', self.lwp.TEMPLATE_THEMES_GALLERY_CARD,
                             f'{var} is being injected by hand again')

    def test_every_theme_gets_its_own_rendered_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        self.assertEqual(html.count('<iframe class="preview"'),
                         len(self.lwp.THEMES) * len(self.lwp.THEMES_GALLERY_PANELS))
        # srcdoc, so the page stays self-contained: no src= fetch anywhere.
        self.assertNotIn('<iframe src=', html)
        # The theme marker is gone; each preview is told apart by its own
        # palette instead — the one thing two themes cannot share.
        for slug in ('nord', 'graphite'):
            page = self.lwp.THEMES[slug]['page'].upper() + 'FF'
            self.assertIn(f'--color-page: {page};', html, slug)

    def test_the_composed_stylesheet_resolves_every_emphasis_property(self):
        """The DECLARATION has to be checked in the sheet a page actually
        gets. Deleting the two decoration declarations from :root once
        killed the underline on every generated page of every theme with
        the suite green — under the engine the :root block is derived
        from the registry, and this pins that each of the six emphasis
        axes lands there at its theme-resolved value."""
        axes = ('weight', 'style', 'bg', 'fg', 'decoration', 'decoration-color', 'pad', 'absorb-punct')
        for slug in ('monochrome', 'graphite', 'nord'):
            resolved = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug))
            css = self.lwp.emit_theme_css(resolved)
            root = css[:css.index('\n}')]
            for axis in axes:
                value = resolved[f'fact.strong.{axis}']
                self.assertIn(f'--fact-strong-{axis}: {value};', root,
                              f'{slug}: fact.strong.{axis}')

    def test_the_settings_scaffold_is_the_complete_property_surface(self):
        """Replaces the recipe comment block: the scaffold is where an
        author now discovers what can be set, so it must show EVERY
        registry key (a missing line is a decision confiscated from the
        series), and any line they uncomment must be a valid pin — the
        scaffold is generated from the registry precisely so its values
        cannot drift into something the type checker rejects."""
        scaffolded = self.lwp.build_settings_scaffold('nord')
        uncommented = []
        for key in self.lwp.PROPERTY_REGISTRY:
            self.assertIn(f'\n# {key}: ', scaffolded, key)
        for line in scaffolded.splitlines():
            m = re.match(r'# ([a-z][\w.-]*): (.*)$', line)
            if m and m.group(1) in self.lwp.PROPERTY_REGISTRY:
                uncommented.append(f'{m.group(1)}: {m.group(2)}')
        theme, props = self.lwp.parse_settings_text(
            'theme: nord\n' + '\n'.join(uncommented))
        self.assertEqual(len(props), len(self.lwp.PROPERTY_REGISTRY))
        # Every scaffolded value goes through the real cascade and type
        # check without an error — uncommenting can never be a trap.
        self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer(theme), props)

    def test_help_documents_the_emphasis_property_and_derived_count(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        # The help speaks the settings vocabulary now; the dead CSS names
        # must not be advertised (--fact-strong-highlight/-ink were renamed
        # to -bg/-fg, and audit maps them).
        self.assertIn('fact.strong.weight', result.stdout)
        self.assertNotIn('--fact-strong-highlight', result.stdout)
        # The property count shown is derived from the registry (G6), so
        # the twenty-one-variables drift can never recur.
        self.assertIn(str(len(self.lwp.PROPERTY_REGISTRY)), result.stdout)

    def _resolved(self, slug):
        return self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer(slug))

    def test_underline_is_an_independent_axis(self):
        # The guarantee the old translation-layer test carried: default is
        # no underline with the rule taking the text's own colour; a theme
        # can underline INSTEAD of a ground, or AS WELL AS one.
        r = self.lwp.resolve_theme_properties()
        self.assertEqual(r['fact.strong.decoration'], 'none')
        # decoration-color defaults to the strong ink itself (the engine's
        # spelling of currentColor), so an underline can never be a colour
        # the text does not already carry unless a theme says so.
        self.assertEqual(r['fact.strong.decoration-color'], r['fact.strong.fg'])

    def test_the_catalogue_demonstrates_both_ways_of_using_the_underline(self):
        instead, as_well = [], []
        for slug in self.lwp.THEMES:
            r = self._resolved(slug)
            if r['fact.strong.decoration'] != 'underline':
                continue
            (instead if r['fact.strong.bg'] == '#00000000' else as_well).append(slug)
        self.assertTrue(instead, 'no theme shows an underline replacing the ground')
        self.assertTrue(as_well, 'no theme shows an underline alongside the ground')
        for slug in instead + as_well:
            r = self._resolved(slug)
            self.assertGreaterEqual(
                contrast_ratio(r['fact.strong.decoration-color'][:7],
                               r['color.page'][:7]), 3.0,
                f'{slug}: the underline is too faint against the page')

    def test_the_default_ground_references_a_shared_colour(self):
        prop = self.lwp.PROPERTY_REGISTRY['fact.strong.bg']
        self.assertEqual(prop.default, 'mark')
        r = self.lwp.resolve_theme_properties()
        self.assertEqual(r['fact.strong.bg'], r['color.mark'])

    def test_each_swatch_names_the_role_before_the_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        roles = re.findall(r'<div class="swatch-role">([^<]*)</div>', html)
        self.assertEqual(len(roles), len(self.lwp.PALETTE_ROLES) * len(self.lwp.THEMES))
        for name in self.lwp.PALETTE_ROLES:
            self.assertNotIn(name, roles, f'{name!r} is a variable name, not a role')
        # The swatch shows the settings.conf property name — the one an
        # author can actually type — never a CSS variable that no longer
        # exists in the emitted sheet.
        for prop in self.lwp.PROPERTY_NAME_OF_ROLE.values():
            self.assertIn(f'<div class="swatch-var">{prop}</div>', html, prop)

    def test_each_card_states_its_fact_box_emphasis_treatment(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        stated = re.findall(r'class="fact-treatment"><span>[^<]*</span>(.*?)</p>', html)
        self.assertEqual(len(stated), len(self.lwp.THEMES))
        for slug, theme in self.lwp.THEMES.items():
            label = self.lwp.fact_treatment_label(theme)
            self.assertIn(label, stated, slug)
            resolved = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug))
            self.assertEqual('underlined' in label,
                             resolved['fact.strong.decoration'] == 'underline',
                             slug)
        self.assertGreaterEqual(len(set(stated)), 5)


class TheMitNoticeTravelsWithEveryCopyItIsRequiredTo(unittest.TestCase):
    """THIRD-PARTY-NOTICES.md makes a legal claim, and until now the only
    thing keeping it true was a sentence asking a human not to delete a
    comment.

    The QR encoder is Kazuhiko Arase's, under MIT, and MIT requires the
    copyright and permission notice to travel with every copy. This code is
    copied twice over by ordinary use: `init` writes it into the series as
    `templates/nav.js`, and every build inlines it into every page. A notice
    kept only in THIRD-PARTY-NOTICES.md would be left behind by the very act
    of using the tool — which is exactly why that file says the notice lives
    in the template instead, and asks whoever edits `TEMPLATE_NAV_JS` not to
    move it.

    An instruction in prose is not a guarantee. This is the guarantee: the
    three places the document promises, checked where the copy actually
    lands."""

    ATTRIBUTION = 'Kazuhiko Arase'
    MARKER = 'qrEncode'   # the encoder itself, not its notice

    def test_the_notice_is_in_the_template_the_executable_ships(self):
        self.assertIn(self.ATTRIBUTION, EXECUTABLE.read_text(encoding='utf-8'),
                      'the MIT attribution left the executable')

    def test_the_notice_reaches_a_scaffolded_series_and_a_built_page(self):
        """Through the real `init` and the real `demo`, not the test
        fixture: what MIT asks is that the notice travel with the CODE,
        and a fixture writes neither of the two places it travels to.

        Those two places changed shape when `init` stopped writing
        `templates/nav.js` (BACKLOG B32), and the obligation did not: the
        series still receives the encoder, inside the copy of the
        executable that `init` puts there, and every built page that
        inlines the encoder still carries it. A file fewer, the same two
        conveyances, checked here where they actually land — and
        `template write nav.js` is a third, covered by the first
        assertion since it writes TEMPLATE_NAV_JS verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            done = run('init', str(root))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertFalse((root / 'templates' / 'nav.js').exists(),
                             'init is writing nav.js again — if that is '
                             'deliberate, this test wants the notice '
                             'checked in it too')
            bundled = root / 'lightwebpres'
            self.assertTrue(bundled.exists(), 'init bundled no executable')
            self.assertIn(self.ATTRIBUTION,
                          bundled.read_text(encoding='utf-8'),
                          'the notice does not travel into a scaffolded '
                          'series')
            taken = run('template', 'write', 'nav.js', str(root))
            self.assertEqual(taken.returncode, 0, taken.stderr)
            self.assertIn(self.ATTRIBUTION,
                          (root / 'templates' / 'nav.js')
                          .read_text(encoding='utf-8'),
                          'the notice does not travel with a copy handed '
                          'out by `template write`')
            done = run('demo', str(root))
            self.assertEqual(done.returncode, 0, done.stderr)
            pages = sorted((root / 'public').glob('*.html'))
            self.assertTrue(pages, 'demo built no page')
            # The invariant is that the CODE and the NOTICE travel
            # together, which is what MIT asks. Since the two skeletons
            # were unified, the index inlines the same script as the
            # articles — encoder and notice included — so every built
            # page carries the encoder, and the loop below checks each
            # one of them. Stated this way the check stays right if the
            # encoder ever reaches more pages or fewer.
            carrying = 0
            for page in pages:
                text = page.read_text(encoding='utf-8')
                if self.MARKER not in text:
                    continue
                carrying += 1
                self.assertIn(self.ATTRIBUTION, text,
                              f'{page.name} carries the encoder without its '
                              f'MIT notice')
            self.assertGreater(carrying, 0,
                               'no built page carries the encoder -- the '
                               'marker is wrong, not the licensing')

    def test_the_notices_file_still_names_the_work_and_its_licence(self):
        """If the encoder is ever replaced, this fails and the notices file
        is revisited on purpose rather than left describing code that has
        gone."""
        notices = (EXECUTABLE.parent / 'THIRD-PARTY-NOTICES.md').read_text(
            encoding='utf-8')
        self.assertIn(self.ATTRIBUTION, notices)
        self.assertIn('MIT', notices)


class SkillDocumentsWhatTheCodeAccepts(unittest.TestCase):
    """agent/skills/lightwebpres/SKILL.md is the only reference an agent
    reads before writing an article. Anything reachable from the Markdown
    that the skill does not name is unreachable in practice.

    An audit found eighteen such gaps at once, the loudest being the
    comparison-table verdict classes: the stylesheet shipped them, the
    spec and the README documented them, and the skill never mentioned
    them, so no agent could produce a colour-coded table. This test
    derives its list FROM THE CODE rather than restating it, so adding a
    field to the executable fails here until the skill catches up."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()
        self.skill = (Path(__file__).resolve().parent.parent /
                      'agent' / 'skills' / 'lightwebpres' / 'SKILL.md'
                      ).read_text(encoding='utf-8')

    def test_every_recognized_slide_field_is_named(self):
        names = self.lwp.SLIDE_FIELD_NAMES
        self.assertIn('highlight-caption', names, 'the field list moved')
        for field in names:
            self.assertIn(field, self.skill, field)

    def test_every_article_level_field_is_named(self):
        for field in self.lwp._SERIES_STRING_FIELDS:
            self.assertIn(field, self.skill, field)
        for field in self.lwp._SERIES_META_STRING_FIELDS:
            self.assertIn(field, self.skill, f'series_meta.{field}')
        # Not just the word: --include-drafts contains it, which is how a
        # first version of this line survived its own mutation. The status
        # values are a closed vocabulary, so the skill has to carry all
        # three — an agent shown only `draft` cannot set an article aside.
        for value in self.lwp.ARTICLE_STATUSES:
            self.assertIn(f'status: {value}', self.skill, value)

    def test_every_styling_hook_reachable_only_by_hand_is_named(self):
        """A class the stylesheet defines and the Markdown cannot
        produce is reachable only if the skill says it exists.

        Read off the COMPOSED sheet — the only one a page gets. The old
        anchor was the source constant, which could name a class the
        composition never shipped."""
        css = self.lwp.compose_stylesheet(
            self.lwp.resolve_theme_properties({}))
        for cls in ('yes', 'no', 'partial', 'col-signal', 'col-snap'):
            self.assertIn(f'.{cls}', css, f'{cls} left the stylesheet')
            self.assertIn(f'`{cls}`', self.skill, cls)
        self.assertIn('comparison-table', self.skill)

    def test_every_slide_type_and_its_own_fields_are_named(self):
        """The four type names and the split of fields between them are
        the skill's most load-bearing table, and nothing read SLIDE_TYPES.

        The class derived its lists from SLIDE_FIELD_NAMES,
        _SERIES_STRING_FIELDS and the composed stylesheet, so the fields
        were all covered SOMEWHERE -- and which type accepts which was
        covered nowhere. An agent that puts `highlight:` on a cover gets
        a fatal build error the skill would have been correct to prevent.

        Read per row: each type's row must name each field that type
        takes. The rows are matched by the type name, so reordering the
        table is free and dropping a row is not."""
        types = self.lwp.SLIDE_TYPES
        self.assertEqual(len(types), 4, 'the type list moved')
        rows = [line for line in self.skill.splitlines()
                if line.startswith('|') and line.count('|') >= 4]
        for t in types:
            self.assertIn(f'`{t.name}`' if t.name != 'standard' else 'standard',
                          self.skill, f'slide type {t.name} is not named')
            row = next((r for r in rows if t.name in r.split('|')[1]), None)
            self.assertIsNotNone(
                row, f'the slide-types table has no row for {t.name!r}')
            for field in t.fields:
                # `article` or `article: filename.md` -- the row may show
                # the value form, so the name is matched up to the closing
                # backtick or the colon.
                self.assertRegex(
                    row, r'`' + re.escape(field) + r'[`:]',
                    f'{t.name} takes `{field}` and its row does not say so')
        # The marker spelling itself, which is what an agent types.
        for t in types:
            if t.name == 'standard':
                self.assertIn('<!-- lwp:slide -->', self.skill)
            else:
                self.assertIn(f'<!-- lwp:slide:{t.name} -->', self.skill,
                              f'the marker for {t.name} is never shown')

    def test_the_skill_does_not_promise_that_nothing_is_fatal(self):
        """It said so twice, and page_dest has three fatal paths."""
        self.assertNotIn('Nothing in this chain is fatal', self.skill)
        self.assertNotIn('Nothing here is ever a fatal build error', self.skill)

    def test_the_skill_names_no_field_the_parser_does_not_know(self):
        """The other direction, and it used to be a single string.

        The rest of this class checks that the skill names everything the
        engine accepts. This one checks the reverse — that it invents
        nothing — and for a long time it did so by asserting the absence of
        one historical name, `slide_title:`, advertised in the frontmatter
        though it never existed. A test whose name promises a rule and
        whose body pins one past case is the shape that lets the next case
        through: adding a fabricated field to the skill left it green.

        Scanned inside FENCED BLOCKS only. That is what an agent copies,
        and it is what makes the check possible at all — prose legitimately
        names retired fields (`tag:` has a migration note) and deliberate
        error examples, so scanning the whole file would report the skill
        for doing its job. Measured on the current text: eleven fields are
        written in blocks and every one is real.

        The vocabulary is the union of the global field list, the article
        meta keys, and each slide type's OWN fields — `article:` belongs
        only to `full-article` and is in none of the first two, so a check
        built on the global list alone reports a real field as an
        invention."""
        known = (set(self.lwp.SLIDE_FIELD_NAMES)
                 | set(self.lwp.ARTICLE_META_KEYS)
                 | {f for st in self.lwp.SLIDE_TYPES for f in (st.fields or ())})
        blocks = re.findall(r'```[a-z]*\n(.*?)```', self.skill, re.S)
        self.assertGreater(len(blocks), 5,
                           'no fenced blocks found -- the scan is broken, '
                           'not the skill')
        invented = {}
        for block in blocks:
            for line in block.split('\n'):
                m = re.match(r'^([a-z][a-z0-9_-]*):(?:\s|$)', line)
                if m and m.group(1) not in known \
                        and not m.group(1).startswith('style.'):
                    invented[m.group(1)] = line.strip()[:60]
        self.assertEqual(invented, {},
                         'the skill writes a field the parser never heard of')
        # The case that started it, kept by name: it was in the
        # frontmatter, which is not a fenced block and which the scan above
        # therefore does not reach.
        self.assertNotIn('slide_title', self.skill)

    def test_the_skill_says_where_the_tool_is_downloaded_from(self):
        """A skill is installed into an environment, not into a clone.
        It already told an agent to ask when the executable isn't there,
        and to read GUIDE.md and specifications.md if they're beside it
        — three pointers, no address, to a reader whose whole problem is
        that none of the three is present.

        Read off HOMEPAGE rather than restated, so moving the project
        fails here instead of leaving a skill that sends agents to an
        address nobody owns any more."""
        self.assertIn(self.lwp.HOMEPAGE, self.skill)

    def test_the_help_says_it_too(self):
        """`--help` ended on "Full reference: specifications.md" — a file
        that does not travel with the executable a release publishes."""
        out = run('--help').stdout
        self.assertIn(self.lwp.HOMEPAGE, out)


class ContrastFloors(unittest.TestCase):
    """Guards for measured catalogue decisions and renderer invariants.
    They were found by rendering real pages under the built-in themes, after
    defects survived checks that looked only at the gallery preview. Each
    test pins the value at its source, not its rendering, because rendering
    is the consequence. These tests do not design or retune palettes."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    @staticmethod
    def _lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    @classmethod
    def _lum(cls, rgb):
        r, g, b = rgb
        return 0.2126 * cls._lin(r) + 0.7152 * cls._lin(g) + 0.0722 * cls._lin(b)

    @classmethod
    def _ratio(cls, a, b):
        la, lb = cls._lum(a), cls._lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    @staticmethod
    def _rgb(hex_colour):
        h = hex_colour.lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _over(fg, alpha, bg):
        return tuple(fg[i] * alpha + bg[i] * (1 - alpha) for i in range(3))

    def _cover_ground(self, resolved):
        """What the cover slide actually paints under its own text, READ
        FROM THE RESOLVED LAYER. It was transcribed from the
        implementation — the #00000073 veil written out by hand — which
        made one of the two operands of a contrast ratio dead data:
        repaint the cover ground white and the counter still measured
        "readable" at 1.09:1. Exactly the defect this class exists to
        prevent, in the class that exists to prevent it."""
        frm = resolved['cover.bg.from']
        return self._over(self._rgb(frm[:7]), int(frm[7:9], 16) / 255,
                          self._rgb(resolved['color.page'][:7]))

    def test_the_cover_slide_counter_is_readable_on_every_theme(self):
        """The counter's colour (cover.num.fg, ex --cover-fg-faint) was
        once a fixed rgba(255,255,255,.34) that had never been measured
        against the ground it sits on: 2.37:1 at worst, and below AA on
        every theme AND on the default palette. 'Faint' is a look, not
        a licence to be unreadable. Now an explicit ARGB in the resolved
        layer, so the alpha is read from the value the engine emits."""
        for slug, theme in self.lwp.THEMES.items():
            resolved = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug))
            faint = resolved['cover.num.fg']
            self.assertRegex(faint, r'^#[0-9A-F]{8}$', slug)
            fg, alpha = self._rgb(faint[:7]), int(faint[7:9], 16) / 255
            ground = self._cover_ground(resolved)
            ratio = self._ratio(self._over(fg, alpha, ground), ground)
            self.assertGreaterEqual(round(ratio, 2), 4.5, f'{slug}: {ratio:.2f}:1')

    # A text rule may fade itself only if the faded result has been
    # measured against the ground it actually sits on. Each entry would
    # name what that ground is. It is EMPTY on purpose: the one allowance
    # that ever existed (.slide-cover .summary, measured at 0.78) is now
    # carried by the alpha of cover.summary.fg, which
    # test_the_cover_summary_alpha_clears_aa_on_every_theme re-measures on
    # every theme. The dict stays as the only door a future fade may
    # come through.
    MEASURED_FADES = {}

    def test_a_text_rule_fades_itself_only_where_it_was_measured(self):
        """The two worst failures in the render sweep were both an
        `opacity` on a block of text: the 'currently reading' card at
        1.62:1 on 33/33 themes, and the 'no' verdict at 1.99:1 on 32/33.
        Both read as a style choice and were a contrast failure. An
        opacity on a text-bearing rule now has to be justified here.

        Scanned on the COMPOSED sheet of every theme, not on a source
        constant: an opacity can now arrive from the skeleton OR from an
        emitted rule, and only the composition sees both."""
        offenders = []
        for slug in (None, *self.lwp.THEMES):
            layer = {} if slug is None else self.lwp.theme_property_layer(slug)
            sheet = self.lwp.compose_stylesheet(
                self.lwp.resolve_theme_properties(layer))
            css = re.sub(r'/\*.*?\*/', '', sheet, flags=re.DOTALL)
            for block in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
                selector, body = block.group(1).strip(), block.group(2)
                m = re.search(r'(?<![-\w])opacity:\s*([\d.]+)', body)
                if not m or float(m.group(1)) >= 1:
                    continue
                if not re.search(r'(?<![-\w])(color|font-size|font-weight):', body):
                    continue      # paints a ground or a glyph, not running text
                if selector in self.MEASURED_FADES:
                    continue
                offenders.append(
                    f'{selector} (opacity {m.group(1)}) on {slug or "defaults"}')
        self.assertEqual(offenders, [], 'a text rule may not fade itself unmeasured')

    def test_the_cover_summary_alpha_clears_aa_on_every_theme(self):
        """The measured 0.78 became an explicit alpha in cover.summary.fg,
        restated per theme by the converter. An earlier version of this
        guard read the opacity out of the STRIPPED declaration in the old
        sheet — auditing a value that no longer ships, so the live alpha
        could have drifted below AA while the guard kept passing."""
        for slug in self.lwp.THEMES:
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug))
            fg8 = r['cover.summary.fg']
            fg, alpha = self._rgb(fg8[:7]), int(fg8[7:9], 16) / 255
            from8 = r['cover.bg.from']
            ground = self._over(self._rgb(from8[:7]), int(from8[7:9], 16) / 255,
                                self._rgb(r['color.page'][:7]))
            ratio = self._ratio(self._over(fg, alpha, ground), ground)
            self.assertGreaterEqual(round(ratio, 2), 4.5,
                                    f'cover summary on {slug}: {ratio:.2f}:1')

    # A body link's treatment is now split across the seam: `color:
    # inherit` and the underline itself are skeleton (architecture, B3),
    # its tint is a registry property. Only the composed sheet sees both.
    LINK_SELECTOR = frozenset({'.fact-content a', '.full-article a'})

    def _link_declarations(self, css):
        """Every declaration the composed sheet lands on the body-link
        selector, skeleton rule and emitted rule alike."""
        bodies = []
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
        for block in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            parts = {p.strip() for p in block.group(1).split(',') if p.strip()}
            if parts == self.LINK_SELECTOR:
                bodies.append(block.group(2))
        return ' '.join(bodies)

    def test_a_body_link_keeps_the_ink_around_it(self):
        """§9.1/BACKLOG B3. The link had no rule at all and took the
        browser blue, measured at 1.03:1 on pop-violet and below AA on
        fifteen themes. Ink-on-page is the pair every theme is admitted
        on, so inheriting is the only treatment that cannot fail."""
        css = self.lwp.compose_stylesheet(
            self.lwp.resolve_theme_properties({}))
        body = self._link_declarations(css)
        self.assertTrue(body, 'the body-link rule is gone')
        self.assertRegex(body, r'color:\s*inherit')
        self.assertRegex(body, r'text-decoration:\s*underline')
        self.assertIn('var(--link-decoration-color)', body)

    def test_the_link_rule_never_reaches_navigation(self):
        """Underlining every <a> would have underlined the series-nav
        cards, the index cards and the slide-progress dots. The rule is
        scoped to the two containers the Markdown converter writes into,
        and nothing else."""
        css = re.sub(r'/\*.*?\*/', '', self.lwp.compose_stylesheet(
            self.lwp.resolve_theme_properties({})), flags=re.DOTALL)
        # Both halves of the treatment, wherever the seam put them: the
        # underline itself (skeleton) and its tint (emitted from the
        # registry). Either selector widening is the defect.
        selectors = [m.group(1) for m in re.finditer(
            r'([^{}]*)\{[^{}]*(?:text-decoration:\s*underline'
            r'|text-decoration-color:\s*var\(--link-decoration-color\))', css)]
        self.assertEqual(len(selectors), 2,
                         'the body-link treatment moved: ' + repr(selectors))
        # Checked part by part, not by looking for names that must be
        # absent: a bare `a` reaches every one of those containers
        # without naming any of them, which is how the first version of
        # this guard passed its own mutation.
        allowed = ('.fact-content ', '.full-article ')
        for selector in selectors:
            for part in (p.strip() for p in selector.split(',')):
                if not part:
                    continue
                self.assertTrue(part.startswith(allowed),
                                f'{part!r} is not scoped to a prose container')

    def test_the_registered_link_component_is_scoped_to_prose(self):
        """The same guard on the registry side of the seam. The tint is
        now a registry property, so widening `link`'s selector — to a
        bare `a`, say — would put the underline's colour on every
        navigation card in the site, and the sheet-side guard above
        would pass, because the skeleton's own selector never moved."""
        comp = next(c for c in self.lwp.THEME_COMPONENTS if c.key == 'link')
        selectors = [comp.selector] + [p.selector for p in comp.props
                                       if p.selector]
        for selector in selectors:
            for part in (p.strip() for p in selector.split(',')):
                self.assertTrue(part.startswith(('.fact-content ',
                                                 '.full-article ')),
                                f'{part!r} is not scoped to a prose container')

    def test_the_underline_tint_defaults_to_the_ink_and_is_theme_settable(self):
        """§9.1/BACKLOG B3: the body link inherits the ink around it and
        only its underline's tint is exposed. The default must BE the ink
        (currentColor's replacement under the engine — a reference, so it
        follows the theme), and a layer must be able to move it without
        touching the link colour itself."""
        r = self.lwp.resolve_theme_properties({})
        self.assertEqual(r['link.decoration-color'], r['color.ink'])
        tinted = self.lwp.resolve_theme_properties({'link.decoration-color': 'call'})
        self.assertEqual(tinted['link.decoration-color'], tinted['color.call'])
        # The composed sheet must resolve it, whatever the theme.
        for slug in list(self.lwp.THEMES)[:4]:
            themed = self.lwp.emit_theme_css(self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug)))
            self.assertRegex(themed, r'--link-decoration-color:\s*#[0-9A-F]{8};', slug)

    @staticmethod
    def _rgba8(value):
        h = value.lstrip('#')
        h = h + 'FF' if len(h) == 6 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))

    @classmethod
    def _composite(cls, value, ground):
        """`value` (an 8-digit ARGB literal) painted over an opaque ground.

        Rounded to 8-bit channels, which `_over` above deliberately is
        not. A browser has nowhere to keep the fraction, and the
        difference decides a case: monokai's first candidate ring
        measures 3.0009:1 on a ground carried at full float precision and
        2.9970:1 on the one the screen actually shows. The rounded number
        is the one a reader gets."""
        r, g, b, a = cls._rgba8(value)
        return tuple(round(c) for c in cls._over((r, g, b), a / 255, ground))

    def _ring_sites(self):
        """(ring key, [fill keys]) for every focus ring in the registry.

        Discovered, not listed: a ring is a `*.ring` property, and the
        fills it can land on are the backgrounds of its OWN component —
        `.nav-btn` has two of them, the plain button and the softer home
        one. A ring added to a third component is measured the day it
        exists, with nothing to remember to update."""
        sites = []
        for comp in self.lwp.THEME_COMPONENTS:
            rings = [p.key for p in comp.props if p.key.endswith('.ring')]
            fills = [p.key for p in comp.props if p.css == 'background']
            for ring in rings:
                sites.append((ring, fills))
        return sites

    def test_every_focus_ring_clears_the_non_text_bar_on_every_theme(self):
        """A focus ring is drawn OUTSIDE the control's border edge, so it
        has two neighbours and must be seen against both: `color.page` on
        the outside, the control's own fill on the inside. Checking only
        the page is how four rings shipped below 3:1 — dread's `#C1121F`
        measured 2.30:1 against `nav-btn.bg` while clearing 3.17:1
        against the page, which is the ground nobody was looking at.

        3:1 is WCAG 1.4.11: this is the only thing on the page that says
        where the keyboard is."""
        short = []
        for slug in self.lwp.THEMES:
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug), {})
            page = self._rgb(r['color.page'][:7])
            for ring, fills in self._ring_sites():
                grounds = [('color.page', page)]
                grounds += [(f, self._composite(r[f], page)) for f in fills]
                for name, ground in grounds:
                    ratio = self._ratio(self._composite(r[ring], ground), ground)
                    # Compared raw, printed to four places: the closest
                    # call in the catalogue is 3.0002:1 and the value
                    # rejected for it was 2.9970:1, and "3.00 is not 3.00"
                    # is not a failure message anyone can act on.
                    if ratio < 3.0:
                        short.append(f'{slug} {ring} vs {name}: {ratio:.4f}:1')
        self.assertEqual(short, [], 'a focus ring below the non-text bar')

    def test_the_ring_scan_finds_more_than_one_ring_and_more_than_one_fill(self):
        """The guard on the guard. `_ring_sites` derives its work from the
        registry, so a renamed suffix or a component that stops declaring
        a background would quietly leave the test above measuring an empty
        list of sites — passing, and covering nothing."""
        sites = self._ring_sites()
        self.assertGreater(len(sites), 1, 'the ring scan found fewer than two rings')
        for ring, fills in sites:
            self.assertTrue(fills, f'{ring}: no fill found for the control it outlines')

    def test_the_palettes_we_draw_keep_bold_fact_text_above_aa(self):
        """Our own bar as theme AUTHORS, applied to the themes we author.

        Nothing in this program asks a theme to reach a level, and this
        test does not either — it is not about the software. Shipping a
        catalogue means taking on the job of drawing themes, and this is
        the floor we hold OURSELVES to at one rendered site: bold fact
        text on its own highlight, where `fact.strong.bg` is the palette's
        `mark` and `fact.strong.fg` the tone chosen for text on it.

        Scoped to `source: 'lightwebpres'`, and the scope is the point.
        The nine borrowed palettes ship as their authors drew them, for
        fidelity; measuring them is fine and reporting the measurement is
        the whole service, but holding them to a bar we set for our own
        work would be arrogating a competence over someone else's design.
        Measured 2026-08-20 at this site: our 48 entries run 5.02:1
        (`pop-lagoon`) to 18.66:1, the nine borrowed ones 4.51:1
        (`catppuccin`) to 14.70:1 — so under the old whole-catalogue form
        this guard sat one hundredth away from failing the suite over a
        palette decision that was never ours to make.

        This does not derive or retune anything: a value that drops below
        is a value we go and repaint by hand, in the theme we drew."""
        for slug, theme in self.lwp.THEMES.items():
            if theme.get('source') != 'lightwebpres':
                continue
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug), {})
            page = self._rgb(r['color.page'][:7])
            ground = self._composite(r['fact.strong.bg'],
                                     self._composite(r['fact.bg'], page))
            ratio = self._ratio(self._composite(r['fact.strong.fg'], ground), ground)
            self.assertGreaterEqual(round(ratio, 2), 4.5,
                                    f'fact.strong.fg on {slug}: {ratio:.2f}:1')

    # Measured while fixing catppuccin's mark, and NOT part of that fix:
    # three palettes put the cover tag below AA on the cover's own ground,
    # for a reason that has nothing to do with the highlight. Pinned as an
    # exact set, the way the note surfaces are — a new entry is a
    # regression, and a missing one means a palette was fixed and its
    # exemption leaves with it. pop-tangerine measures 2.19:1, pop-lemon
    # 3.22:1, rose-pine 4.24:1. The tag is 12px bold, which is not large
    # text, so 4.5:1 is the right bar for all three.
    COVER_TAG_BELOW_AA = {'pop-tangerine', 'pop-lemon', 'rose-pine'}

    def test_the_cover_tag_is_measured_on_the_ground_the_cover_paints(self):
        """The other half of what catppuccin's `color.mark` fixed. On a
        light theme the cover ground IS `color.ink`, so `cover.kicker.fg`
        (the mark) and `fact.strong.fg` (the ink on the mark) are the same
        two colours the other way round and measure the same 3.05:1 — but
        only on a light theme, and only where the highlight is the mark.
        Deriving one from the other would therefore be wrong on 18 themes,
        so the cover site is composited for itself."""
        short = set()
        for slug in self.lwp.THEMES:
            r = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug), {})
            page = self._rgb(r['color.page'][:7])
            cover = self._composite(r['cover.bg.from'], page)
            ratio = self._ratio(self._composite(r['cover.kicker.fg'], cover), cover)
            if round(ratio, 2) < 4.5:
                short.add(slug)
        self.assertEqual(
            short, self.COVER_TAG_BELOW_AA,
            'the measured cover-tag failures changed. New entries are '
            'regressions; a MISSING one means the palette was fixed and its '
            'exemption must go with it.')


class ACardIsCalledWhatItsAuthorDeclared(unittest.TestCase):
    """§12.1.1: one rule. The author writes `slug:`, and a card without
    one stops the build.

    The identity used to be DERIVED — from the heading, from a long-form
    file's name, from the rank — through a normalisation and a truncated
    hash. That answered a question nobody should have to ask: an identity
    derived from a title moves when the title is edited, which is not a
    defect of the derivation but the whole of what a derivation is. The
    `sN` alias, the collision suffix and the audit finding about
    non-durable identities all existed to soften that, and all three went
    with it."""

    def _series(self, tmp, body, prefix=None):
        root = Path(tmp) / 'series'
        (root / 'sources').mkdir(parents=True)
        meta = {'title': 'T'}
        if prefix:
            meta['slug_prefix'] = prefix
        (root / 'series.json').write_text(json.dumps(
            {'series_meta': meta,
             'articles': [{'page_dest': 'a.html', 'page_source': 'a.md',
                           'nav_title': 'A', 'nav_desc': 'A'}]}),
            encoding='utf-8')
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n' + body, encoding='utf-8')
        return root

    COVER = ('<!-- lwp:slide:cover -->\nslug: ouverture\nkicker: K\n'
             '# Titre\nsummary: S\n')

    def _build(self, root, tmp):
        return run('build', str(root), '--output', str(Path(tmp) / 'public'))

    def test_the_declared_slug_is_the_id_on_the_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.COVER)
            self.assertEqual(self._build(root, tmp).returncode, 0)
            html = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<section class="slide slide-cover" id="ouverture"',
                          html)

    def test_a_card_without_a_slug_stops_the_build_and_names_the_command(self):
        """The error has to carry the remedy: someone meeting this for the
        first time has a series that will not build and no way to guess
        that a command exists to fix it in one pass."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(
                tmp, '<!-- lwp:slide:cover -->\nkicker: K\n# T\nsummary: S\n')
            result = self._build(root, tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('slide 1 has no `slug:`', result.stderr)
            self.assertIn('series slug set', result.stderr)

    def test_editing_a_title_does_not_move_the_anchor(self):
        """The whole point, stated as a reader would meet it: the link
        someone shared still lands after the article is rewritten."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.COVER)
            self.assertEqual(self._build(root, tmp).returncode, 0)
            source = root / 'sources' / 'a.md'
            source.write_text(source.read_text(encoding='utf-8')
                              .replace('# Titre', '# Un tout autre titre'),
                              encoding='utf-8')
            self.assertEqual(self._build(root, tmp).returncode, 0)
            html = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('id="ouverture"', html)
            self.assertIn('Un tout autre titre', html)

    def test_two_cards_with_one_slug_is_an_error_not_a_suffix(self):
        """A derived identity could collide innocently — two cards with
        the same heading. Two DECLARED ones are a typing mistake, and a
        `-2` appended in silence would publish an anchor nobody wrote
        while the card they meant to reach keeps the other."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(
                tmp, self.COVER + '\n---\n\n<!-- lwp:slide -->\n'
                'slug: ouverture\nkicker: K\n## H\nsummary: S\n'
                'fact-label: F\n\nCorps.\n')
            result = self._build(root, tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("takes the id 'ouverture'", result.stderr)

    def test_a_slug_cannot_take_a_name_the_page_skeleton_holds(self):
        """`notes`, `navPrev` and the rest are minted by the renderer.
        Two things with one id means the reader lands on whichever the
        browser picks."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(
                tmp, self.COVER.replace('slug: ouverture', 'slug: navPrev'))
            result = self._build(root, tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already used on this page', result.stderr)

    def test_an_unusable_slug_is_refused_with_the_alphabet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(
                tmp, self.COVER.replace('slug: ouverture', 'slug: a b/c'))
            result = self._build(root, tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not usable as an anchor', result.stderr)

    def test_the_prefix_still_applies(self):
        """`slug_prefix` survives the simplification: a series whose pages
        reuse card names (`intro`, `sources`) needs a namespace, and it is
        now the only thing left that can change what an author wrote."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.COVER, prefix='p1-')
            self.assertEqual(self._build(root, tmp).returncode, 0)
            html = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('id="p1-ouverture"', html)

    def test_nothing_derives_an_identity_any_more(self):
        """Structural, and it is the deletion itself: the normalisation,
        the hash and the fallbacks are gone from the module. A test that
        only checked behaviour would pass just as well on a copy still
        carrying 184 lines of engine nothing calls."""
        lwp = load_lightwebpres_module()
        for name in ('_fold_latin_marks', 'normalise_for_identity',
                     'identity_hash', 'derive_slide_identity',
                     'audit_slide_identities', 'IDENTITY_HASH_LENGTH'):
            self.assertFalse(hasattr(lwp, name),
                             f'{name} is still in the module')

    def test_no_card_carries_an_alias_span(self):
        """Every card used to carry an empty span holding the `sN` name it
        had before v0.42. There is nothing to alias when the id is what
        the author typed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.COVER)
            self.assertEqual(self._build(root, tmp).returncode, 0)
            html = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<span id="s1">', html)
            self.assertNotIn('-series"></span>', html)


class SlugSetWritesIntoTheAuthorsFiles(unittest.TestCase):
    """`series slug set` — the one command in this tool that edits an
    author's articles.

    Everything else reads sources and writes to `public/`; `demo` creates
    files and refuses to overwrite. It is a verb someone types on purpose
    and never a step of the build, because a build that rewrote its own
    inputs would surprise a read-only CI, a version-controlled tree that
    comes back dirty, and an encrypted series in the browser GUI."""

    def _demo(self, tmp):
        root = Path(tmp) / 'series'
        for step in (['init', str(root)], ['demo', str(root)]):
            self.assertEqual(run(*step).returncode, 0)
        return root

    def _stripped(self, root):
        """The demo with every `slug:` line taken back out — the state of
        an article somebody wrote by hand."""
        for source in (root / 'sources').glob('*.md'):
            text = source.read_text(encoding='utf-8')
            source.write_text('\n'.join(
                l for l in text.split('\n') if not l.startswith('slug:')),
                encoding='utf-8')
        return root

    def test_it_gives_every_card_a_slug_and_the_series_then_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._stripped(self._demo(tmp))
            self.assertNotEqual(
                run('build', str(root), '--output', str(root / 'public')
                    ).returncode, 0, 'the stripped series was expected to fail')
            self.assertEqual(run('series', 'slug', 'set', str(root)).returncode, 0)
            self.assertEqual(
                run('build', str(root), '--output', str(root / 'public')
                    ).returncode, 0)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._stripped(self._demo(tmp))
            before = {p: p.read_text(encoding='utf-8')
                      for p in (root / 'sources').glob('*.md')}
            result = run('series', 'slug', 'set', str(root), '--dry-run')
            self.assertEqual(result.returncode, 0)
            self.assertIn('would write', result.stderr)
            for path, text in before.items():
                self.assertEqual(path.read_text(encoding='utf-8'), text, path)

    def test_it_never_touches_a_card_that_already_has_one(self):
        """Including a `slug:` line left empty, which is a decision in
        progress rather than an absence."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._demo(tmp)
            first = root / 'sources' / 'first.md'
            before = first.read_text(encoding='utf-8')
            self.assertEqual(run('series', 'slug', 'set', str(root)).returncode, 0)
            self.assertEqual(first.read_text(encoding='utf-8'), before)

    def test_what_it_writes_is_unique_within_the_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._stripped(self._demo(tmp))
            self.assertEqual(run('series', 'slug', 'set', str(root)).returncode, 0)
            # The series' own articles, not every .md in the directory:
            # a long-form piece pulled in by `article:` holds no cards, so
            # it has no slug to carry and must not have gained one.
            for name in ('first.md', 'middle.md', 'last.md'):
                source = root / 'sources' / name
                slugs = re.findall(r'^slug: (.+)$',
                                   source.read_text(encoding='utf-8'), re.M)
                self.assertTrue(slugs, source)
                self.assertEqual(len(slugs), len(set(slugs)), source)
            for name in ('first_article.md', 'middle_article.md',
                         'last_article.md'):
                text = (root / 'sources' / name).read_text(encoding='utf-8')
                self.assertNotIn('slug: ', text,
                                 f'{name} is prose, not a page of cards')

    def test_it_writes_nothing_but_the_slug_lines(self):
        """A writer that reformats what it did not come for is a writer
        nobody trusts twice. The only difference between before and after
        must be the added lines."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._stripped(self._demo(tmp))
            before = (root / 'sources' / 'first.md').read_text(encoding='utf-8')
            self.assertEqual(run('series', 'slug', 'set', str(root)).returncode, 0)
            after = (root / 'sources' / 'first.md').read_text(encoding='utf-8')
            self.assertEqual(
                [l for l in after.split('\n') if not l.startswith('slug: ')],
                before.split('\n'))

    def test_the_inventory_lists_every_card_and_says_which_have_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._stripped(self._demo(tmp))
            result = run('series', 'slug', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no slug', result.stdout)
            self.assertIn('series slug set', result.stdout)
            self.assertEqual(run('series', 'slug', 'set', str(root)).returncode, 0)
            again = run('series', 'slug', str(root))
            self.assertNotIn('no slug', again.stdout)

    def test_the_inventory_has_a_json_shape_the_gui_can_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._demo(tmp)
            result = run('series', 'slug', str(root), '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['schema'], 'lightwebpres.series-slug/1')
            self.assertEqual(len(report['articles']), 3)
            for article in report['articles']:
                self.assertTrue(article['source_read'])
                self.assertTrue(article['slides'])
                for slide in article['slides']:
                    self.assertTrue(slide['slug'], article['page_source'])

    def test_the_demo_it_ships_builds_without_running_anything_first(self):
        """`demo` writes readable slugs of its own. A demonstration series
        that will not build is not one, and the field is worth showing at
        its best rather than as eight hex characters."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._demo(tmp)
            self.assertEqual(
                run('build', str(root), '--output', str(root / 'public')
                    ).returncode, 0)
            html = (root / 'public' / 'first.html').read_text(encoding='utf-8')
            self.assertIn('id="ouverture"', html)



class MeasurementReportsItDoesNotPolice(unittest.TestCase):
    """§9.5 / §11.9.1. The tool measures a theme's contrast and prints the
    level with the offending pairs. It stops there. No palette value is
    rewritten, no theme is rejected, demoted, reordered or withheld
    because of what it measures.

    That is the direct corollary of "a theme is a stance": a command that
    refused `terminal` over its phosphor halo would have decided, in the
    author's place, what a good theme is — which is exactly the competence
    this tool does not have. `audit` is the other side of the line and it
    is not the same thing: its thresholds sit BELOW everything the
    catalogue measures, so no shipped theme can trip them, and it warns
    rather than refusing.

    Written as a guard because the rule is one sentence and its violation
    would be one line: a `if level == 'fail': continue` in the listing, a
    check in `--theme`. Nothing else in the suite would notice."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def _below_aa(self):
        """The shipped themes measuring below AA in at least one category,
        by the executable's own report — the very themes the rule is about,
        and the reason this class is not vacuous."""
        out = []
        for slug in self.lwp.THEMES:
            measured = self.lwp.measure_contrast(self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug)))
            if any(cat['level'] == 'fail' for cat in measured.values()):
                out.append(slug)
        return out

    def test_the_catalogue_really_does_contain_themes_below_aa(self):
        """Non-vacuity, and it comes first. Every assertion below says
        `and it is offered anyway`; if the catalogue were uniformly AA or
        better, all of them would pass while proving nothing at all."""
        below = self._below_aa()
        self.assertGreater(
            len(below), 0,
            'no shipped theme measures below AA, so every "offered anyway" '
            'assertion in this class asserts nothing. Re-derive this guard.')

    def test_theme_list_offers_every_theme_whatever_it_measures(self):
        """The listing is the catalogue, not a filtered view of it."""
        listed = run('theme', 'list')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        for slug in sorted(self.lwp.THEMES):
            self.assertIn(slug, listed.stdout,
                          f'`theme list` does not offer {slug}')

    def test_a_theme_below_aa_is_applied_whatever_it_measures(self):
        """`init --theme` and `series theme set` take any theme in the
        catalogue, and record the choice.

        What is forbidden is DECIDING: refusing, substituting, silently
        altering, or dropping a theme from what can be applied. Informing
        is not — a warning or a note is allowed, and this guard does not
        forbid one. The line is between telling the author something and
        taking the choice away from them.

        (An earlier draft did assert that nothing is printed at warning
        level here. That was stricter than the rule and would have blocked
        a legitimate future warning; it is the refusal that is the
        violation, not the sentence.)"""
        below = sorted(self._below_aa())
        self.assertTrue(below, 'no below-AA theme to try — see the guard above')
        # EVERY one of them, not a representative. Written as one theme
        # first, and a mutation showed why that was not enough: a refusal
        # aimed at any theme other than the alphabetically first went
        # straight through a green suite. A rule that holds for the whole
        # catalogue has to be asked of the whole catalogue.
        for slug in below:
            with tempfile.TemporaryDirectory() as tmp:
                series = os.path.join(tmp, 'series')
                made = run('init', series, '--theme', slug)
                self.assertEqual(made.returncode, 0,
                                 f'`init --theme {slug}` was refused: {made.stderr}')
                settings = Path(series) / 'templates' / 'settings.conf'
                self.assertIn(f'theme: {slug}', settings.read_text(encoding='utf-8'))
                changed = run('series', 'theme', 'set', series, '--theme', slug)
                self.assertEqual(changed.returncode, 0,
                                 f'`series theme set --theme {slug}` was refused: '
                                 f'{changed.stderr}')

    def test_the_measured_level_never_reaches_a_built_page(self):
        """The reader of a presentation is not told the contrast level of
        the theme chosen for them: it is tooling data, not publication
        data. Checked on a page built from a theme that measures below AA,
        which is the one case where a well-meaning marker would be most
        tempting to add.

        CSS comments are stripped first, and that is not a convenience:
        the composed sheet carries the engine's own design notes, and some
        of them discuss contrast in these very words — measured on a demo
        page, 115 comment blocks, 19634 bytes, 14.4% of the page. Those
        are a separate matter (they ship to every reader, which is worth
        its own decision) and matching them here would make this guard
        fail for a reason it is not about."""
        below = sorted(self._below_aa())
        self.assertTrue(below, 'no below-AA theme to try — see the guard above')
        slug = below[0]
        with tempfile.TemporaryDirectory() as tmp:
            series = os.path.join(tmp, 'series')
            self.assertEqual(run('init', series, '--theme', slug).returncode, 0)
            self.assertEqual(run('demo', series).returncode, 0)
            out = Path(series) / 'public'
            self.assertTrue(list(out.glob('*.html')), 'demo built no pages')
            for page in sorted(out.glob('*.html')):
                text = re.sub(r'/\*.*?\*/', '', page.read_text(encoding='utf-8'),
                              flags=re.S)
                # The vocabulary of the REPORT, not of the subject. A page
                # that named a level, a threshold or a measured pair would
                # be telling its reader something only the author was ever
                # meant to see.
                for marker in ('below AA', 'threshold_aa', 'threshold_aaa',
                               'pairs_measured', 'accessibility',
                               'contrast-level', 'data-contrast', 'WCAG'):
                    self.assertNotIn(
                        marker, text,
                        f'{page.name} tells its reader {marker!r} — the '
                        f'measured level is tooling data and must not ship')


class ThemeInfoMeasuresRatherThanDeclares(unittest.TestCase):
    """§11.9.1. The accessibility level of a theme is COMPUTED from the
    property registry, never written into a THEMES entry. A hand-written
    label is right on the day it is typed and silent about every palette
    tweak afterwards, because nothing connects it to the colour it claims
    to qualify. The report is diagnostic only; it never rewrites or rejects
    the theme.

    So the arithmetic is redone here, independently: this class does not
    call the executable's compositing or its luminance, it writes its own
    and compares. A test that borrowed the code under test could not
    catch an error in it."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    # --- independent arithmetic, owing nothing to the executable ---

    @staticmethod
    def _channels(value):
        h = value.lstrip('#')
        if len(h) == 6:
            h += 'FF'
        return [int(h[i:i + 2], 16) for i in (0, 2, 4, 6)]

    @classmethod
    def _over(cls, value, ground):
        """source-over, quantised to 8 bits — what the screen shows."""
        r, g, b, a = cls._channels(value)
        alpha = a / 255
        return [round(c * alpha + ground[i] * (1 - alpha))
                for i, c in enumerate((r, g, b))]

    @staticmethod
    def _lum(rgb):
        def channel(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = (channel(c) for c in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @classmethod
    def _ratio(cls, a, b):
        la, lb = cls._lum(a), cls._lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    def _ground(self, resolved, stack):
        ground = self._over(resolved['page.bg'], [255, 255, 255])
        for key in stack:
            ground = self._over(resolved[key], ground)
        return ground

    def _report(self, *args):
        """The theme report's JSON, through the CLI, as the GUI gets it.

        Two commands produce it and the caller says which by what it
        passes: a slug reads the catalogue (`theme show`), a directory
        reads a series (`series theme`). They were one verb once and the
        directory form of `theme show` is refused now, so the split is
        made here rather than left to a command that no longer guesses."""
        reads_a_series = bool(args) and Path(args[0]).is_dir()
        verb = ('series', 'theme') if reads_a_series else ('theme', 'show')
        result = run(*verb, *args, '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_the_primitives_agree_with_arithmetic_done_by_hand(self):
        """Two numbers nobody has to trust the rest of the module for.
        Black on white is 21:1 exactly, and a 20%-alpha grey over a
        near-black ground lands on 33.6, which the screen shows as 34 —
        the rounding that decides whether a focus ring clears 3:1."""
        self.assertAlmostEqual(
            self.lwp.contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0, places=10)
        self.assertEqual(self.lwp.composite_over('#80808033', (10, 10, 10)),
                         (34, 34, 34))
        # Unrounded, that composite is 33.6 and the ratio it produces
        # differs in the third decimal. The engine must not keep it.
        self.assertNotEqual(self.lwp.composite_over('#80808033', (10, 10, 10)),
                            (33.6, 33.6, 33.6))

    def test_every_reported_ratio_survives_being_recomputed_from_scratch(self):
        """The whole claim, on the whole catalogue at once: for the pair the
        command NAMES as deciding each category, the ratio it reports is
        the one this class's own compositing and luminance produce. The
        executable chooses which pairs the page really superposes; the
        arithmetic on them is checked here."""
        for slug in self.lwp.THEMES:
            resolved = self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug))
            measured = self.lwp.measure_contrast(resolved)
            for name, category in measured.items():
                worst = category['worst']
                self.assertIsNotNone(worst, f'{slug}: {name} measured nothing')
                ground = self._ground(resolved, worst['ground'])
                mine = self._ratio(self._over(worst['foreground_color'], ground),
                                   ground)
                self.assertEqual(round(mine, 4), worst['ratio'],
                                 f'{slug} {name} {worst["foreground"]}')
                self.assertEqual(
                    '#%02X%02X%02X' % tuple(ground), worst['ground_color'],
                    f'{slug} {name}: composited ground differs')

    def test_the_level_is_the_verdict_of_the_worst_pair_and_nothing_else(self):
        """The grading rule, re-derived from the numbers rather than
        taken from the module: a category is AAA only if its WORST pair
        clears the AAA bar, and non-text says pass/fail because WCAG
        defines no AAA level for it."""
        for slug in self.lwp.THEMES:
            measured = self.lwp.measure_contrast(self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer(slug)))
            for name, category in measured.items():
                low = category['worst']['ratio']
                if low < category['threshold_aa']:
                    expected = 'fail'
                elif category['threshold_aaa'] is None:
                    expected = 'pass'
                elif low < category['threshold_aaa']:
                    expected = 'AA'
                else:
                    expected = 'AAA'
                self.assertEqual(category['level'], expected,
                                 f'{slug} {name} at {low}')
                self.assertEqual(
                    bool(category['failures']), category['level'] == 'fail',
                    f'{slug} {name}: failures and level disagree')
                for pair in category['failures']:
                    self.assertLess(pair['ratio'], category['threshold_aa'])

    # Two measured facts, pinned as exact values rather than as
    # inequalities: a change here is a real change in the catalogue or in
    # what the command measures, and either one is worth being told about.
    # graphite is the reference for "clears AA on the measured text sites"; nord is a
    # borrowed palette whose green accent sits at 1.79:1 on its own
    # near-white card, which §9.5.2 already records in its own words.
    # nord's non-text was `fail` here until its active navigation dot --
    # `mark` on a near-white card, 1.06:1 -- was given the theme's ink. The
    # body text still fails and that is the palette; the dot was not the
    # palette, it was a default that suited almost none of it.
    PINNED_LEVELS = {
        'graphite': ('AA', 'AAA', 'pass'),
        'nord': ('fail', 'AAA', 'pass'),
    }

    def test_the_levels_of_two_named_themes_are_what_was_measured(self):
        for slug, expected in self.PINNED_LEVELS.items():
            report = self._report(slug)
            got = tuple(report['accessibility'][name]['level'] for name in
                        ('body_text', 'large_text', 'non_text'))
            self.assertEqual(got, expected, slug)

    def test_a_failing_category_names_the_pairs_that_made_it_fail(self):
        """A level without counter-examples is not actionable. nord's
        body text fails, so the command owes the reader the offending
        pairs, their measured ratio and the bar they missed."""
        report = self._report('nord')
        failures = report['accessibility']['body_text']['failures']
        self.assertTrue(failures, 'a failing category reported no pair')
        self.assertEqual(failures, sorted(failures, key=lambda p: p['ratio']),
                         'the worst pair is not first')
        self.assertIn('verdict.yes.fg', {p['foreground'] for p in failures})
        for pair in failures:
            self.assertEqual(pair['required'], 4.5)
            self.assertLess(pair['ratio'], 4.5)
        # And the text format carries the same evidence, not just a word.
        text = run('theme', 'show', 'nord')
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn('verdict.yes.fg', text.stdout)
        self.assertRegex(text.stdout, r'Body text\s+fail')

    # --- the two targets ---

    def test_a_series_that_pins_a_colour_gets_a_different_answer(self):
        """§11.9.1's whole reason for taking a directory. graphite as
        shipped clears AA on body text; the same series with one quieter
        `color.ink-quiet` pinned does not — and nothing but measuring the
        EFFECTIVE theme could say so. The pin is a colour the author had
        every reason to think was a small darkening."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root), '--theme', 'graphite')
                             .returncode, 0)
            shipped = self._report('graphite')
            before = self._report(str(root))
            self.assertEqual(before['target']['kind'], 'series')
            self.assertEqual(before['target']['theme'], 'graphite')
            self.assertEqual(before['target']['pinned'], [])
            self.assertEqual(before['accessibility']['body_text']['level'],
                             shipped['accessibility']['body_text']['level'])

            settings = root / 'templates' / 'settings.conf'
            settings.write_text(settings.read_text(encoding='utf-8')
                                + '\ncolor.ink-quiet: #6A6A6A\n', encoding='utf-8')
            after = self._report(str(root))
            self.assertEqual(after['target']['pinned'], ['color.ink-quiet'])
            self.assertEqual(after['palette']['ink-quiet'], '#6A6A6AFF')
            self.assertEqual(shipped['accessibility']['body_text']['level'], 'AA')
            self.assertEqual(after['accessibility']['body_text']['level'], 'fail',
                             'the pinned colour did not move the answer')
            self.assertTrue(after['accessibility']['body_text']['failures'])

    def test_a_directory_target_needs_no_theme_line_at_all(self):
        """A series installed without a theme runs on the registry's own
        defaults. That is an answer, not an error: `theme` is null and
        the family facet — the one that is declared and cannot be
        derived (§9.5.2) — is null with it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            settings.write_text(
                '\n'.join(line for line in settings.read_text(encoding='utf-8')
                          .splitlines() if not line.startswith('theme:')) + '\n',
                encoding='utf-8')
            report = self._report(str(root))
            self.assertIsNone(report['target']['theme'])
            self.assertIsNone(report['facets']['family'])
            self.assertIsNone(report['label'])
            self.assertIn(report['facets']['polarity'], ('light', 'dark'))

    def test_custom_css_is_reported_as_unmeasured_only_once_it_has_rules(self):
        """custom.css is free CSS, outside the typed surface, so it is
        not measured — and saying nothing about that would be the
        hand-written label all over again. `init` creates the file empty
        — everything in it is published verbatim, so the tool puts
        nothing there — and existence alone must not raise the flag or it
        would be raised on every series."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root), '--theme', 'nord')
                             .returncode, 0)
            custom = root / 'templates' / 'custom.css'
            self.assertTrue(custom.exists())
            self.assertFalse(self._report(str(root))['target']['custom_css'])
            custom.write_text(custom.read_text(encoding='utf-8')
                              + '\n.slide { color: red; }\n', encoding='utf-8')
            self.assertTrue(self._report(str(root))['target']['custom_css'])
            self.assertIn('NOT', run('series', 'theme', str(root)).stdout)

    # --- the JSON contract with lightwebpres-gui (§1.2, §11.9.1) ---

    ROOT_KEYS = {'schema', 'lightwebpres_version', 'target', 'label', 'note',
                 'source', 'facets', 'palette', 'fonts', 'accessibility'}
    TARGET_KEYS = {'kind', 'theme', 'directory', 'pinned', 'custom_css'}
    CATEGORY_KEYS = {'level', 'threshold_aa', 'threshold_aaa',
                     'pairs_measured', 'worst', 'failures'}
    PAIR_KEYS = {'site', 'foreground', 'foreground_color', 'ground',
                 'ground_color', 'ratio', 'required'}

    def test_the_json_parses_and_carries_exactly_the_documented_keys(self):
        """The key names are a public surface: renaming one breaks the
        GUI's theme picker and nothing goes red here. Checked as an EXACT
        set, both ways — an added key is as much a contract change as a
        removed one, and the GUI is entitled to know which it is from the
        `schema` string."""
        report = self._report('nord')
        self.assertEqual(report['schema'], 'lightwebpres.theme-info/4')
        self.assertEqual(report['lightwebpres_version'],
                         self.lwp.VERSION)
        self.assertEqual(set(report), self.ROOT_KEYS)
        self.assertEqual(set(report['target']), self.TARGET_KEYS)
        self.assertEqual(set(report['facets']),
                         {'polarity', 'hue', 'family'})
        self.assertEqual(set(report['palette']),
                         {'page', 'ink', 'ink-quiet', 'mark', 'call', 'affirm',
                          'nav'})
        self.assertEqual(set(report['fonts']),
                         {'text', 'display', 'ui', 'mono'})
        self.assertEqual(set(report['accessibility']),
                         {'body_text', 'large_text', 'non_text'})
        for name, category in report['accessibility'].items():
            self.assertEqual(set(category), self.CATEGORY_KEYS, name)
            self.assertGreater(category['pairs_measured'], 0, name)
            for pair in [category['worst'], *category['failures']]:
                self.assertEqual(set(pair), self.PAIR_KEYS, name)
                self.assertIsInstance(pair['ground'], list)
                self.assertRegex(pair['ground_color'], r'^#[0-9A-F]{6}$')
                self.assertRegex(pair['foreground_color'], r'^#[0-9A-F]{8}$')
        self.assertIsNone(report['accessibility']['non_text']['threshold_aaa'],
                          'WCAG defines no AAA level for non-text')
        self.assertIn(report['accessibility']['non_text']['level'],
                      ('pass', 'fail'))

    def test_the_palette_and_fonts_come_from_the_registry_not_from_a_list(self):
        """A seventh shared value must appear in the output the day it
        exists, without anyone remembering to add it. Derived here from
        THEME_SHARED_PROPS, which is what the command does too — the
        guard is that the two agree, so a hard-coded list in either would
        show up as a disagreement."""
        report = self._report('nord')
        shared = {p.key for p in self.lwp.THEME_SHARED_PROPS}
        self.assertEqual({f'color.{k}' for k in report['palette']},
                         {k for k in shared if k.startswith('color.')})
        self.assertEqual({f'font.{k}' for k in report['fonts']},
                         {k for k in shared if k.startswith('font.')})
        resolved = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('nord'))
        for role, value in report['palette'].items():
            self.assertEqual(value, resolved[f'color.{role}'])

    def test_a_slugs_facets_are_the_same_ones_themes_prints(self):
        """§9.5.2: one function feeds every surface, so a terminal
        picker and this one cannot disagree about the same entry."""
        listing = run('theme', 'list')
        self.assertEqual(listing.returncode, 0, listing.stderr)
        printed = {m[0]: (m[1], m[2]) for m in re.findall(
            r'^  (\S+)  \[(\S+)\]  (\S+)$', listing.stdout, re.MULTILINE)}
        self.assertEqual(len(printed), len(self.lwp.THEMES))
        for slug in ('nord', 'graphite', 'terminal', 'pop-fuchsia'):
            facets = self._report(slug)['facets']
            trio, family = printed[slug]
            self.assertEqual(
                '/'.join(facets[k] for k in ('polarity', 'hue')),
                trio, slug)
            # The declared facet has to agree across surfaces too -- more
            # so than the measured three, since nothing recomputes it.
            self.assertEqual(facets['family'], family, slug)

    # --- errors ---

    def test_an_unknown_slug_is_a_named_error_listing_the_valid_ones(self):
        """The `themes` idiom for an unknown facet value: name what was
        rejected and list what is accepted. Answering "no such theme" and
        stopping would send a reader hunting for something that exists, a
        typo away."""
        result = run('theme', 'show', 'nrod')
        self.assertEqual(result.returncode, 1)
        self.assertIn('nrod', result.stderr)
        self.assertEqual(result.stdout, '')
        for slug in self.lwp.THEMES:
            self.assertIn(slug, result.stderr, f'{slug} missing from the list')
        # Whole, not split across a line break: a slug a reader cannot
        # copy in one piece is a slug the listing did not give them.
        listed = result.stderr[result.stderr.index('valid slugs'):]
        for slug in self.lwp.THEMES:
            self.assertIn(f' {slug} ', ' ' + listed.replace('\n', ' ') + ' ')

    def test_a_directory_that_was_never_installed_points_at_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run('series', 'theme', tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn('init', result.stderr)

    def test_theme_show_refuses_a_directory_and_names_the_series_reading(self):
        """`theme show <dir>` was the last shape of the old `theme-info`,
        which read the catalogue and a series with one verb. The two are
        not the same question, and a form kept working for compatibility
        is a form people keep learning — so it is refused, and the refusal
        names `series theme`.

        `theme show` with NO argument inside a series still reads that
        series: that is not the inherited form, it is the habit every
        other command already follows."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            self.assertEqual(run('init', str(root)).returncode, 0)
            refused = run('theme', 'show', str(root))
            self.assertEqual(refused.returncode, 1)
            self.assertIn('series theme', refused.stderr)
            named = run('series', 'theme', str(root))
            self.assertEqual(named.returncode, 0, named.stderr)
            standing = run('theme', 'show', cwd=str(root))
            self.assertEqual(standing.returncode, 0, standing.stderr)
            self.assertEqual(standing.stdout, named.stdout)

    def test_an_unknown_format_is_a_named_error(self):
        result = run('theme', 'show', 'nord', '--format', 'yaml')
        self.assertEqual(result.returncode, 1)
        self.assertIn('text', result.stderr)
        self.assertIn('json', result.stderr)

    def test_the_command_takes_no_option_it_does_not_own(self):
        result = run('theme', 'show', 'nord', '--theme', 'graphite')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Unknown option', result.stderr)


class ContrastSitesAreDiscoveredNotRemembered(unittest.TestCase):
    """The guard on the guard. A measurement is only as good as its
    inventory, and this project's recorded failure mode is an inventory
    that LOOKS complete: the dark-furniture table read as exhaustive
    twice while two veils were missing from it.

    So every colour property in the registry must be either measured at a
    real site or exempted with a written reason. Adding a dispensation is
    a decision someone makes; forgetting one is not possible."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def _mentioned(self):
        keys = set()
        for site in self.lwp.CONTRAST_SITES:
            keys.add(site.fg)
            keys.update(*site.grounds) if site.grounds else None
            for stack in site.grounds:
                keys.update(stack)
        return keys

    def test_no_colour_property_escapes_both_the_sites_and_the_exemptions(self):
        colours = {k for k, p in self.lwp.PROPERTY_REGISTRY.items()
                   if p.type is self.lwp.PROP_COLOR}
        uncovered = sorted(colours - self._mentioned()
                           - set(self.lwp.CONTRAST_UNMEASURED))
        self.assertEqual(uncovered, [],
                         'colour properties neither measured nor exempted')

    def test_no_exemption_outlives_the_property_it_excused(self):
        """A dispensation for a property that no longer exists is a
        reason nobody will ever re-read, and it hides the day the same
        name comes back meaning something else."""
        colours = {k for k, p in self.lwp.PROPERTY_REGISTRY.items()
                   if p.type is self.lwp.PROP_COLOR}
        stale = sorted(set(self.lwp.CONTRAST_UNMEASURED) - colours)
        self.assertEqual(stale, [], 'exemptions for properties that are gone')

    def test_every_exemption_carries_a_reason_someone_wrote(self):
        for key, reason in self.lwp.CONTRAST_UNMEASURED.items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason.split()), 3,
                               f'{key}: that is not a reason')

    def test_each_category_actually_measures_something(self):
        """The non-vacuity guard. A site table that stopped producing
        pairs in a category would report a level for it anyway, and the
        level of nothing reads exactly like the level of something."""
        measured = self.lwp.measure_contrast(
            self.lwp.resolve_theme_properties({}))
        for name, category in measured.items():
            self.assertGreater(category['pairs_measured'], 1, name)
            self.assertNotEqual(category['level'], 'n/a', name)
        self.assertGreater(len(self.lwp.CONTRAST_SITES), 40,
                           'the site inventory collapsed')

    def test_the_category_of_a_site_follows_the_type_size_the_theme_sets(self):
        """The WCAG category is computed from the resolved axes, not
        written next to the site: enlarge a summary and the summary is
        judged as large text, with nothing to remember to update. Proved
        by moving one axis and watching a pair change bucket."""
        base = self.lwp.measure_contrast(
            self.lwp.resolve_theme_properties({}))
        grown = self.lwp.measure_contrast(self.lwp.resolve_theme_properties(
            {'source.size': '30px'}))
        self.assertEqual(grown['large_text']['pairs_measured'],
                         base['large_text']['pairs_measured'] + 1)
        self.assertEqual(grown['body_text']['pairs_measured'],
                         base['body_text']['pairs_measured'] - 1)
        # And the bold rule, which is the other half of the WCAG bar.
        self.assertEqual(
            self.lwp.length_px('clamp(19px, 4vmin, 40px)', 16.0), 19.0,
            'a clamp must be read at its smallest, which is what renders')

    def test_a_treatment_a_theme_does_not_paint_is_not_measured(self):
        """Most themes leave the fact-box underline at `none`. Measuring
        the colour of a line nobody draws would invent a failure."""
        painted = self.lwp.measure_contrast(self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('graphite')))
        plain = self.lwp.measure_contrast(self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('nord')))
        self.assertEqual(self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer('nord'))['fact.strong.decoration'],
            'none')
        self.assertEqual(painted['non_text']['pairs_measured'],
                         plain['non_text']['pairs_measured'] + 1)


class NothingAboutContrastReachesABuiltPage(unittest.TestCase):
    """§11.9.1's hard boundary: the information stops at the author. No
    tag, no class, no mention — the reader of a presentation is never
    told the contrast level of the theme chosen for them, and `build`
    does not change."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    # Vocabulary that exists in this executable ONLY because of
    # theme-info -- each one verified absent from the version before it.
    # `WCAG`, `contrast ratio` and `threshold` are deliberately NOT here:
    # the skeleton and the hue calculation used all three before this
    # command existed, and a guard that fails on what it did not
    # introduce teaches people to edit the guard.
    FORBIDDEN = (r'theme-info', r'threshold_aa', r'pairs measured',
                 r'CONTRAST_', r'Large text', r'Non-text')

    def test_no_file_build_writes_mentions_a_contrast_level(self):
        """Built under two themes of opposite polarity, over a demo that
        exercises every slide type — so the sweep sees a cover, a fact
        box, a comparison table, a notes section and a full article."""
        for theme in ('graphite', 'pop-lemon'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'series'
                self.assertEqual(run('init', str(root), '--theme', theme)
                                 .returncode, 0)
                self.assertEqual(run('demo', str(root)).returncode, 0)
                out = root / 'public'
                self.assertEqual(run('build', str(root), '--output', str(out))
                                 .returncode, 0)
                written = sorted(p for p in out.rglob('*') if p.is_file())
                self.assertTrue(written, 'build wrote nothing to sweep')
                for path in written:
                    try:
                        text = path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        continue          # an image copied verbatim
                    for pattern in self.FORBIDDEN:
                        self.assertNotRegex(
                            text, pattern,
                            f'{path.name} under {theme} mentions {pattern}')

    # Every function in the executable whose body reaches the contrast
    # API. Pinned as an exact set: the day `build_article` or
    # `compose_stylesheet` grows a call, this fails, and the sweep above
    # would not necessarily — a level computed and merely not printed is
    # still a level the build path now depends on.
    CONTRAST_API = {'measure_contrast', 'CONTRAST_SITES', 'CONTRAST_LEVELS',
                    'CONTRAST_UNMEASURED', 'theme_info_report',
                    'contrast_ratio', 'composite_over', 'ground_colour',
                    'relative_luminance'}
    CONTRAST_CALLERS = {'contrast_ratio', 'ground_colour', 'measure_contrast',
                        '_theme_info_facets', 'theme_info_report',
                        'cmd_theme_info', 'cmd_series_theme',
                        'navigation_contrast_sites', 'judge_resolved_theme'}

    def test_the_contrast_engine_is_reachable_from_nothing_but_theme_info(self):
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        callers = set()
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id in self.CONTRAST_API:
                    callers.add(node.name)
        self.assertEqual(callers, self.CONTRAST_CALLERS)

    def test_a_built_page_is_render_identical_to_the_previous_version_s(self):
        """The direct evidence, not a word list: the same series built
        by the executable as it stood at the last tagged release (v0.42.3),
        and by this one, compared byte for byte after CSS comments are
        removed from ``<style>`` blocks. Comments are not rendering, while
        every other byte remains covered. --build-stamp is off by default,
        so there is no timestamp to excuse a difference.

        Repoint this test at the newest tag whenever a release
        intentionally changes the output, keeping it green between
        releases — the repoint IS the acknowledgement that the drift is
        deliberate, not a regression.

        Skipped, loudly, when the previous version cannot be reached --
        outside a git checkout there is nothing to compare against, and
        a comparison with nothing is not a pass."""
        previous = subprocess.run(
            ['git', 'show', 'v0.42.3:lightwebpres'], capture_output=True,
            cwd=str(EXECUTABLE.parent))
        if previous.returncode != 0:
            self.skipTest('no v0.42.3 tag to read the previous version from')
        with tempfile.TemporaryDirectory() as tmp:
            before_exe = Path(tmp) / 'lightwebpres-before'
            before_exe.write_bytes(previous.stdout)
            outputs = []
            for name, executable in (('before', before_exe),
                                     ('after', EXECUTABLE)):
                root = Path(tmp) / name
                # `init`, not the `install` this used to type: the
                # spelling was retired, and the guard runs the CURRENT
                # executable as well as the tagged one. Both accept
                # `init`, which is what the canonical form is for.
                for step in (['init', str(root), '--theme', 'pop-lemon'],
                             ['demo', str(root)]):
                    done = subprocess.run(
                        [sys.executable, str(executable), *step],
                        capture_output=True, text=True)
                    self.assertEqual(done.returncode, 0, done.stderr)
                pages = {}
                for path in sorted((root / 'public').rglob('*')):
                    if path.is_file() and not path.name.startswith('.lwp-'):
                        pages[path.name] = path.read_bytes()
                outputs.append(pages)
            self.assertTrue(outputs[0], 'the previous version built nothing')
            self.assertEqual(sorted(outputs[0]), sorted(outputs[1]),
                             'build writes a different set of files')
            def without_css_comments(page):
                def strip_style_comments(match):
                    body = re.sub(rb'/\*.*?\*/', b'', match.group(2),
                                  flags=re.DOTALL)
                    # And the line the comment was alone on. A comment-only
                    # line otherwise leaves an indent behind, and that
                    # residue is a line: the :root block writes `/* key */`
                    # above each component's variables, so a component
                    # entering the registry shifts every later line even
                    # though the comparison already ignores what the
                    # comment said. Dropping the residue happens to both
                    # pages by the same rule, and the arrival of the
                    # component is still declared -- by its variables, in
                    # `added`, where a reader can see what it brought.
                    body = b'\n'.join(line for line in body.split(b'\n')
                                      if line.strip())
                    return match.group(1) + body + match.group(3)

                def strip_script_comments(match):
                    # The same rule for the script, and it was missing for
                    # no reason but the order the two blocks were written
                    # in. A comment cannot change what a page renders, in
                    # JavaScript exactly as in CSS, and the shipped script
                    # carries long ones — rewriting the paragraph above a
                    # function read here as thirty-five changed lines and
                    # buried the four that were real.
                    #
                    # Whole-line comments only. A `//` mid-line can be
                    # inside a string (`'https://…'`), and this test is
                    # not the place to write a JavaScript lexer.
                    body = b'\n'.join(
                        line for line in match.group(2).split(b'\n')
                        if line.strip() and not line.strip().startswith(b'//'))
                    return match.group(1) + body + match.group(3)
                page = re.sub(rb'(<style\b[^>]*>)(.*?)(</style>)',
                              strip_style_comments, page,
                              flags=re.IGNORECASE | re.DOTALL)
                page = re.sub(rb'(<script\b[^>]*>)(.*?)(</script>)',
                              strip_script_comments, page,
                              flags=re.IGNORECASE | re.DOTALL)
                # And then the script itself, replaced by a marker. Not a
                # blind spot: the page's script is the tool's template
                # verbatim, and `test_the_page_carries_exactly_the_script_
                # the_tool_ships` compares the two directly — a stronger
                # statement than "it is what it was last release", since
                # it holds for every build rather than for the diff.
                #
                # What forced it: the declaration tables name whole lines,
                # and a rewritten function is mostly braces. Declaring the
                # cursor fix would have meant declaring `}` (346
                # occurrences in the page), `});` (28) and `} else {`
                # (13), and a declared line strips EVERY occurrence of
                # itself — so covering four real lines would have blinded
                # this test on three hundred. A guard you have to disable
                # to change anything is not a guard.
                page = re.sub(rb'(<script\b[^>]*>)(.*?)(</script>)',
                              rb'\1[script]\3', page,
                              flags=re.IGNORECASE | re.DOTALL)
                # And a card's IDENTITY, replaced by its position. Same
                # reasoning as the script above, and forced by the same
                # arithmetic: a card's id is what its author declared in
                # `slug:` (§12.1.1), so it moves whenever a demo article's
                # slug is edited — the section's own id, every navigation
                # dot's href, every note anchor and every return link, 132
                # lines across four pages when it was first measured.
                # Declaring 132 lines is not a declaration anyone can read,
                # and a guard nobody reads is a guard nobody trusts.
                #
                # Not a blind spot, and the substitute is stronger than
                # what it replaces: `ACardIsCalledWhatItsAuthorDeclared`
                # asserts the rule the identity follows, on every build
                # rather than against one tagged release, and
                # `test_every_id_in_the_page_is_unique` catches the one
                # thing a positional marker could hide — two cards given
                # one name — before this normalisation ever runs.
                #
                # What survives here is the STRUCTURE: a dot still has to
                # point at the card it belongs to, a note body still has to
                # be named after its card, and any of that coming apart
                # still shows up as a diff, because the marker is the
                # card's position and every reference is rewritten with it.
                #
                # Rewritten only where the value is an ANCHOR, never as a
                # bare string. Measured: the series-nav's identity is the
                # word `series-nav`, and a blunt replace turned every
                # `--series-nav-current-bg` in the stylesheet into a
                # marker — a normalisation that quietly eats the thing it
                # is meant to leave alone.
                for index, value in enumerate(
                        re.findall(rb'<section class="[^"]*" id="([^"]+)"', page)):
                    page = re.sub(
                        rb'(id="|href="#)((?:note-|noteref-)?)'
                        + re.escape(value) + rb'(?=["-])',
                        rb'\1\2[slide-%d]' % index, page)
                # A navigation button is reduced to its identity. What it
                # contains is an icon and what it carries is a TRANSLATED
                # title, and comparing the two together as bytes makes a
                # language pack's wording part of the render check while
                # burying the icon inside a 400-character line. The icons
                # have a table test of their own -- the same division of
                # labour the elevation selectors needed, and for the same
                # reason: where this guard is the wrong instrument for a
                # statement, the answer is a test that can make it, not a
                # declaration nobody can read.
                return re.sub(
                    rb'<div class="nav-btn[^>]*?id="(nav\w+)"[^>]*>.*?</div>',
                    rb'<div class="nav-btn" id="\1"></div>', page)

            # Deliberate drift since the tag, declared line for line, and
            # empty at the start of a release cycle -- which is where it
            # is now, freshly repointed at v0.42.3.
            #
            # It exists because the docstring's instruction has a gap.
            # Repointing at the newest tag is the acknowledgement that a
            # release changed the output on purpose, but BETWEEN releases
            # there is no newer tag to point at, and a version number that
            # has not been released is not one this file may invent. So a
            # deliberate change is named here instead: everything outside
            # these lines is still compared byte for byte, and the set of
            # lines that actually differ has to be exactly the set declared
            # here. A second unannounced change fails on the last assertion
            # even once the first one is covered.
            #
            # Each entry is one CSS custom-property line, before and after,
            # e.g.  b'--nav-dot-bg-active: #7A6A00FF;':
            #       b'--nav-dot-bg-active: #8F0049FF;'
            drift = {
                # B9's typography pass, on the theme this guard builds
                # with. `pop-lemon` is a poster palette and the catalogue
                # revision put the pop family in sans: its text and
                # display faces become the UI stack, and its kicker opens
                # from 2px to 3px. Three lines, and they are the whole
                # visible effect of the pass on this page — the other 96
                # values land on the 30 other themes.
                (b"--font-display: Charter, 'Bitstream Charter', "
                 b"'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--font-display: Inter, Roboto, 'Helvetica Neue', "
                     b"'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--font-text: Charter, 'Bitstream Charter', "
                 b"'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--font-text: Inter, Roboto, 'Helvetica Neue', "
                     b"'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                b'--kicker-tracking: 2px;': b'--kicker-tracking: 3px;',
                # Six more variables take the text face by reference,
                # so one decision moves seven lines. That is the point
                # of the reference and not a defect in it.
                (b"--page-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--page-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--title1-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--title1-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--title2-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--title2-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--highlight-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--highlight-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--header-title-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--header-title-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                (b"--note-page-title-font: "
                 b"Charter, 'Bitstream Charter', 'Sitka Text', Cambria, Georgia, serif;"):
                    (b"--note-page-title-font: "
                     b"Inter, Roboto, 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', Arial, sans-serif;"),
                # The skeleton unification: article and index are one
                # template now, and the article body carries the same
                # `class=""` the index template fills with `index-page`.
                # One page, one body tag.
                b'<body>': b'<body class="">',
            }

            # Deliberate ADDITIONS since the tag, declared by property
            # name, and likewise empty at the start of a cycle.
            #
            # A new registry key inserts a line rather than replacing one,
            # which the substitution table above cannot express: the line
            # counts stop matching, the per-line diff is skipped, and every
            # later line reads as changed. Naming the property lets the
            # comparison resume on everything else. A property added
            # without being named here still fails, and a name left here
            # after its property is gone fails too -- both directions are
            # proved by mutation.
            #
            # Entries are variable-name prefixes, e.g. b'--color-nav'.
            added = set()

            # Deliberate RULE-level drift, and the third thing the two
            # tables above cannot say. `drift` substitutes a line for a
            # line and `added` inserts a `--var:` line; neither can express
            # a DECLARATION that leaves one part of the sheet and reappears
            # in another. That happens when a value stops being a literal
            # in the skeleton and becomes a property the engine emits: the
            # old page loses `box-shadow: 0 1px 8px rgba(0,0,0,0.06);` and
            # the new one gains `box-shadow: 0 var(--card-elevation-dy)
            # ...;` somewhere else entirely.
            #
            # The mechanical escape -- putting `box-shadow` in `added` --
            # is refused on purpose: strip_added() runs over BOTH pages, so
            # it would blind this test on exactly the lines the change
            # touches. These two name the whole stripped line instead, one
            # by one, on the side it belongs to. Everything else is still
            # compared byte for byte, and a second, unannounced change
            # fails on the last assertion even once the first is covered.
            # One caution, learned by mutating this test rather than by
            # reasoning about it: a declared line strips EVERY occurrence
            # of itself. `box-shadow: 0 1px 8px rgba(0,0,0,0.06);` sits on
            # both .fact-box and .article-card, so declaring it covers both
            # and a change to only one of them fails here — correctly, but
            # for a reason that reads as a false alarm until you count the
            # occurrences. Declare a line that is unique, or accept that
            # you are declaring all of its twins with it.
            # Both tables are empty at a fresh repoint, and that is the
            # healthy state: every drift they used to declare is inside
            # the tag this test now reads. A line goes back in only for
            # drift introduced AFTER v0.42.3.
            gone = {          # lines the OLD page had and the new one does not
                # The rank aliases. While a card's identity was DERIVED,
                # the page carried a second, empty anchor per card whose
                # name was its position -- `s1`, `s2`, ... plus
                # `sN-series` for the series-nav -- so that a link written
                # against an older release still landed. Nothing derives
                # an identity any more: the author declares one, it does
                # not move when the title is edited, and an alias for a
                # name that cannot drift has nothing left to catch. The
                # anchors the cards themselves carry are compared, under
                # their normalised `[slide-N]` form; only these empty
                # spans are gone.
                b'<span id="s1"></span>',
                b'<span id="s2"></span>',
                b'<span id="s3"></span>',
                b'<span id="s3-series"></span>',
                b'<span id="s4"></span>',
            }
            arrived = set()   # lines the NEW page has and the old one did not
            # The index-card focus ring became a registry property at the
            # same time the index gained card-by-card arrow navigation:
            # two --var: lines and the two declarations that read them,
            # all new to the page and all on the theme this guard builds.
            arrived |= {
                b'--card-ring: #8F0049FF;',
                b'--card-ring-width: 3px;',
                b'outline-color: var(--card-ring);',
                b'outline-width: var(--card-ring-width);',
                b'.article-card:focus-visible { outline-style: solid; outline-offset: 2px; }',
            }
            # Arrivals and departures that belong to ONE page. The tables
            # above are global, and a global declaration cannot say "the
            # index gained a button the article pages always had" --
            # named globally, such a line is refused as stale, correctly,
            # because the released version does carry it elsewhere.
            #
            # The skeleton unification moved the whole of the article
            # chrome onto the index: the nav buttons (6, where the old
            # index carried 4), the share popover and QR modal, the tag
            # menu, the help overlay, the presenter panel, the dots, the
            # pause overlay and the counter. The old index's nav block
            # (navUp/navDown/navHome/navFullscreen) is gone, and its
            # script becomes the same TEMPLATE_NAV_JS the articles ship,
            # neutralised to `[script]` like every other. A declared line
            # strips EVERY occurrence of itself (strip_declared compares
            # `line.strip()`), and the whole index block is unique to the
            # index — no twin lines to blind the comparison elsewhere.
            # The blank line is declared per page too: the template's
            # extra placeholder shifts the whitespace before </body> on
            # the articles as well, and a blank line compares as any
            # other byte.
            index_arrived = {
                b'',
                b'<nav class="nav-dots"></nav>',
                b'<div class="pause-overlay" id="pauseOverlay"></div>',
                b'<div class="slide-counter" id="slideCounter"></div>',
                b'<div class="presenter-panel" id="presenterPanel" role="region"',
                'aria-label="Panneau du présentateur" tabindex="0">'.encode(),
                b'<div class="pp-head" id="presenterHead"></div>',
                b'<div class="pp-notes" id="presenterNotes" aria-live="polite"></div>',
                b'<div class="pp-next" id="presenterNext"></div>',
                b'</div>',
                b'<div class="help-overlay" id="helpOverlay">',
                b'<div class="help-card">',
                '<div class="help-title">Raccourcis clavier</div>'.encode(),
                b'<ul class="help-list" id="helpList"></ul>',
                '<div class="help-foot">H ou Échap pour fermer</div>'.encode(),
                b'</div>',
                b'</div>',
                b'<div class="nav-buttons">',
                b'<div class="nav-btn" id="navPrev"></div>',
                b'<div class="nav-btn" id="navHome"></div>',
                b'<div class="nav-btn" id="navNext"></div>',
                b'<div class="nav-btn" id="navShare"></div>',
                b'<div class="nav-btn" id="navFullscreen"></div>',
                b'<div class="nav-btn" id="navTags"></div>',
                b'</div>',
                b'<div class="tag-menu" id="tagMenu" role="dialog" aria-label="Filtrer les slides">',
                b'<div class="tag-menu-title" id="tagMenuTitle">Filtrer les slides</div>',
                b'<div class="tag-menu-list" id="tagMenuList"></div>',
                b'</div>',
                b'<div class="share-popover" id="sharePopover">',
                b'<div class="share-matrix">',
                b'<div class="share-cell"></div>',
                '<div class="share-cell share-cell-head">Série</div>'.encode(),
                '<div class="share-cell share-cell-head">Article</div>'.encode(),
                '<div class="share-cell share-cell-head" id="shareHeadFiche">Fiche</div>'.encode(),
                '<div class="share-cell share-cell-label">Copier le lien</div>'.encode(),
                '<button type="button" class="share-action" data-action="copy" data-scope="series" title="Copier le lien — Série">&#128279;</button>'.encode(),
                '<button type="button" class="share-action" data-action="copy" data-scope="article" title="Copier le lien — Article">&#128279;</button>'.encode(),
                '<button type="button" class="share-action" data-action="copy" data-scope="fiche" title="Copier le lien — Fiche">&#128279;</button>'.encode(),
                '<div class="share-cell share-cell-label">Afficher le QR code</div>'.encode(),
                '<button type="button" class="share-action" data-action="qr" data-scope="series" title="Afficher le QR code — Série">&#9638;</button>'.encode(),
                '<button type="button" class="share-action" data-action="qr" data-scope="article" title="Afficher le QR code — Article">&#9638;</button>'.encode(),
                '<button type="button" class="share-action" data-action="qr" data-scope="fiche" title="Afficher le QR code — Fiche">&#9638;</button>'.encode(),
                b'</div>',
                b'</div>',
                b'<div class="share-qr-modal" id="shareQrModal">',
                b'<div class="share-qr-modal-content">',
                '<div class="share-qr-modal-title">QR code du lien</div>'.encode(),
                b'<div id="shareQrModalContent"></div>',
                b'<div class="share-qr-modal-url" id="shareQrModalUrl"></div>',
                '<button type="button" class="share-qr-close">Fermer</button>'.encode(),
                b'</div>',
                b'</div>',
                b'<script defer>[script]</script>',
            }
            index_gone = {
                b'',
                b'<div class="nav-buttons">',
                b'<div class="nav-btn" id="navUp"></div>',
                b'<div class="nav-btn" id="navHome"></div>',
                b'<div class="nav-btn" id="navDown"></div>',
                b'<div class="nav-btn" id="navFullscreen"></div>',
                b'</div>',
                b'<script>[script]</script>',
            }
            arrived_in = {'index.html': index_arrived}
            gone_in = {'index.html': index_gone}
            # The same blank-line shift on the article pages, which gained
            # a line before </body> with the unified template.
            for page in ('first.html', 'last.html', 'middle.html'):
                arrived_in[page] = {b''}
                gone_in[page] = {b''}
            # ...and with no extra file inserted on the index, the
            # placeholder leaves the same whitespace differences there.

            def strip_added(page):
                return b'\n'.join(
                    line for line in page.split(b'\n')
                    if not any(line.strip().startswith(name + b':')
                               for name in added))

            def strip_declared(page, declared):
                lines = [line for line in page.split(b'\n')
                         if line.strip() not in declared]
                # And then any rule left with nothing in it. A declaration
                # moving out of the skeleton and into the registry does not
                # only change where it is written, it changes what wraps
                # it: it leaves a rule that still has other declarations
                # and arrives in one the engine opened for it alone. Naming
                # the declaration in `gone` and `arrived` covers the line;
                # the braces around the new one would otherwise read as an
                # undeclared difference. `.foo {}` paints nothing, so
                # dropping it costs the comparison nothing -- and a rule
                # that lost every declaration for a reason nobody declared
                # still fails, on those declarations.
                out, i = [], 0
                while i < len(lines):
                    if (lines[i].rstrip().endswith(b'{')
                            and i + 1 < len(lines)
                            and lines[i + 1].strip() == b'}'):
                        i += 2
                        continue
                    out.append(lines[i])
                    i += 1
                return b'\n'.join(out)

            def normalise(page, declared):
                page = without_css_comments(page)
                for was, now in drift.items():
                    page = page.replace(was, now)
                return strip_declared(strip_added(page), declared)

            seen = set()
            for name in outputs[0]:
                gone_here = gone | gone_in.get(name, set())
                arrived_here = arrived | arrived_in.get(name, set())
                before_lines = strip_declared(
                    without_css_comments(outputs[0][name]), gone_here).split(b'\n')
                after_lines = strip_declared(
                    strip_added(without_css_comments(outputs[1][name])),
                    arrived_here).split(b'\n')
                if len(before_lines) == len(after_lines):
                    seen.update((a.strip(), b.strip())
                                for a, b in zip(before_lines, after_lines)
                                if a != b)
                self.assertEqual(normalise(outputs[0][name], gone_here),
                                 normalise(outputs[1][name], arrived_here),
                                 f'{name} is not the page it was')
            for name in added:
                self.assertTrue(
                    any(name + b':' in page for page in outputs[1].values()),
                    f'{name.decode()} is declared as added and is in none of '
                    f'the built files: the declaration is stale')
            # Both directions, so a declaration cannot outlive what it
            # excused: a line named `gone` that the new page still carries
            # was not removed, and one named `arrived` that it does not
            # carry was never added.
            # Compared against the NORMALISED pages, not the raw ones.
            # The tables declare lines of the text this test actually
            # compares, and once a card's identity is rewritten to its
            # position the two are no longer the same string — a
            # declaration naming `[slide-2]` would be refused as stale
            # while describing a real, present line. Measured, on exactly
            # that line.
            after_all = b'\n'.join(without_css_comments(page)
                                   for page in outputs[1].values())
            before_all = b'\n'.join(without_css_comments(page)
                                    for page in outputs[0].values())
            for line in gone:
                self.assertNotIn(line, after_all,
                                 f'{line.decode()!r} is declared gone and the '
                                 f'built page still carries it')
                self.assertIn(line, before_all,
                              f'{line.decode()!r} is declared gone and the '
                              f'released version never had it')
            for line in arrived:
                self.assertIn(line, after_all,
                              f'{line.decode()!r} is declared arrived and is '
                              f'in none of the built files: it is stale')
                self.assertNotIn(line, before_all,
                                 f'{line.decode()!r} is declared arrived and '
                                 f'the released version already had it')
            self.assertEqual(seen, set(drift.items()),
                             'the drift since v0.42.0 is not the drift this '
                             'test declares')

    def test_the_page_carries_exactly_the_script_the_tool_ships(self):
        """What the render guard hands off when it sets the script aside.
        Stronger than the line diff it replaces: that one asked whether
        the script is what it was at the last release, this one asks
        whether it is what the tool means to ship, which holds for every
        build and not only across a diff.

        Since the skeleton unification, the INDEX carries the same
        script as the articles — one engine for both pages — so the
        identity is asserted on both."""
        lwp = load_lightwebpres_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root)).returncode, 0)
            self.assertEqual(run('demo', str(root)).returncode, 0)
            self.assertEqual(run('build', str(root)).returncode, 0)
            article = (root / 'public' / 'first.html').read_text(encoding='utf-8')
            index = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            strings = lwp.load_language(root / 'language', 'fr')['strings']
            expected = lwp.apply_strings(lwp.TEMPLATE_NAV_JS, strings)
        # EQUALS, not contains. Containment was the first form of this
        # test and it did not bite: an extra statement appended after
        # `{{js_nav}}` left the template a substring of the page, so the
        # assertion passed while the page shipped a line nobody wrote.
        # With the render guard setting the whole script aside, that line
        # would have had nothing else looking at it.
        blocks = re.findall(r'<script\b[^>]*>(.*?)</script>', article, re.S)
        self.assertEqual(len(blocks), 1, f'{len(blocks)} script blocks')
        self.assertEqual(blocks[0].strip(), expected.strip(),
                         'the page is not carrying exactly the tool\'s nav.js')
        index_blocks = re.findall(r'<script\b[^>]*>(.*?)</script>', index, re.S)
        self.assertEqual(len(index_blocks), 1,
                         f'{len(index_blocks)} script blocks on the index')
        self.assertEqual(index_blocks[0].strip(), expected.strip(),
                         'the index is not carrying exactly the tool\'s nav.js')
        self.assertEqual(index_blocks[0].strip(), blocks[0].strip(),
                         'the index and the article do not carry the same script')

    # Every navigation button and the icon it must carry, by the first
    # path of its shape. Written down rather than read off NAV_ICON_PATHS:
    # deriving it would make this table agree with any icon at all, and
    # the whole point is that a button cannot quietly change what it
    # shows.
    NAV_ICON_FIRST_PATH = {
        'navPrev': 'M12 20V5',
        'navNext': 'M12 4v15',
        'navHome': 'M3 11L12 3l9 8',
        'navShare': 'M12 15V4',
        'navFullscreen': 'M8 3H5a2 2 0 0 0-2 2v3',
        'navTags': 'M20.6 13.4l-7.2 7.2',
    }

    def test_every_navigation_button_carries_its_own_icon(self):
        """One idiom for the whole column. It took four to notice: two
        text glyphs, a colour emoji, two SVGs pinned at 19px, and the
        letter L. Nothing there was a set, the emoji was the one element
        of the page no theme could colour, and the pinned SVGs did not
        follow the button while the glyphs did.

        Both directions, on the one template: every button holds the icon
        named here, and no button holds text."""
        lwp = load_lightwebpres_module()
        for match in re.finditer(
                    r'<div class="nav-btn[^>]*?id="(nav\w+)"[^>]*>(.*?)</div>',
                    lwp.TEMPLATE_PAGE):
                button, body = match.group(1), match.group(2)
                self.assertIn(button, self.NAV_ICON_FIRST_PATH, button)
                self.assertTrue(body.startswith('<svg '),
                                f'{button} does not hold an icon: {body[:40]}')
                self.assertIn(f'd="{self.NAV_ICON_FIRST_PATH[button]}',
                              body, f'{button} holds the wrong icon')
                self.assertIn('width="1em"', body,
                              f'{button}: the icon does not follow the button')
                self.assertIn('stroke="currentColor"', body,
                              f'{button}: the icon is not the theme\'s ink')
                self.assertNotRegex(body, r'>[^<]*[A-Za-z0-9]',
                                    f'{button} still carries text')

    def test_the_composed_stylesheet_is_identical_with_and_without_the_reader(self):
        """The narrower statement the sweep cannot make: measuring a
        theme must not perturb it. The sheet is composed, measured, and
        composed again — resolution mutates nothing, so the two are the
        same bytes."""
        for slug in ('nord', 'terminal'):
            layer = self.lwp.theme_property_layer(slug)
            first = self.lwp.compose_stylesheet(
                self.lwp.resolve_theme_properties(layer))
            self.lwp.measure_contrast(self.lwp.resolve_theme_properties(layer))
            again = self.lwp.compose_stylesheet(
                self.lwp.resolve_theme_properties(layer))
            self.assertEqual(first, again, slug)


class PaletteRoleNames(unittest.TestCase):
    """§9.1: the palette variables are named for what they DO. Until
    v0.12.0 they were named for the values they happened to hold in the
    very first theme, so the names lied on every theme that moved away
    from it. Renamed with no compatibility aliases — a deliberate choice,
    which is what makes `audit` responsible for keeping the break
    audible."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_no_palette_variable_is_named_after_a_colour(self):
        """The whole point. A colour name in this tuple is a name that
        will be wrong for some theme in the table — which is how
        --yellow came to hold a dark olive."""
        colours = set(self.lwp.FACET_VALUES['hue']) | {
            'white', 'black', 'grey', 'gray', 'light', 'dark'}
        offenders = [r for r in self.lwp.PALETTE_ROLES
                     if any(part in colours for part in r.split('-'))]
        self.assertEqual(offenders, [], f'colour names among the roles: {offenders}')

    def test_every_theme_defines_exactly_the_declared_roles(self):
        """Every palette role present, and nothing colour-shaped beyond
        them. The fact_* emphasis keys are matched by prefix rather than
        listed: an axis added later is legitimately new metadata, but a
        stray colour key still has to fail here."""
        meta_keys = {'label', 'source', 'note', 'note_good', 'family',
                     'dark_background', 'family'}
        for slug, theme in self.lwp.THEMES.items():
            colour_keys = [k for k in theme
                           if k not in meta_keys and not k.startswith('fact_')]
            self.assertEqual(sorted(colour_keys), sorted(self.lwp.PALETTE_ROLES), slug)

    def test_a_fact_highlight_only_ever_names_a_role_that_exists(self):
        for slug, theme in self.lwp.THEMES.items():
            role = theme.get('fact_highlight')
            if role is not None:
                self.assertIn(role, self.lwp.PALETTE_ROLES, slug)

    def test_the_composed_stylesheet_declares_every_role_and_no_old_name(self):
        """The sheet a page gets declares the seven --color-* roles and not
        one of the retired names. Substring traps abound here: --page: is
        a suffix of --color-page:, so absence is asserted on the start of
        a declaration line (regex anchored MULTILINE), and consumption on
        the exact var(--old) form."""
        css = self.lwp.compose_stylesheet(self.lwp.resolve_theme_properties({}))
        for new in ('--color-page', '--color-ink', '--color-ink-quiet',
                    '--color-mark', '--color-call', '--color-affirm',
                    '--color-nav'):
            self.assertIn(f'{new}: ', css, new)
        for old in ('--page', '--ink', '--ink-muted', '--marker', '--accent',
                    '--positive', '--rule', '--rule-strong', '--surface',
                    '--sunken', '--cover-bg', '--control', '--control-soft'):
            self.assertNotRegex(
                css, re.compile(r'^\s*' + re.escape(old) + r':', re.MULTILINE),
                f'{old} is still declared')
            self.assertNotIn(f'var({old})', css, f'{old} is still consumed')

    def test_audit_reports_old_names_left_in_the_authors_own_rules(self):
        """There are no aliases, so var(--yellow) does not fall back to
        anything: the declaration is invalid and the property keeps its
        inherited value. Neither the browser nor the build says a word.
        This is what stops the rename from breaking in silence — the
        author's own rules live in custom.css now, and that is the file
        audit reads."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            custom = Path(tmp) / 'templates' / 'custom.css'

            clean = run('audit', tmp)
            self.assertNotIn('no longer exist', clean.stdout)

            custom.write_text(custom.read_text(encoding='utf-8') +
                              '\n.mine { color: var(--yellow); border-color: var(--grey); }\n',
                              encoding='utf-8')
            flagged = run('audit', tmp)
            self.assertEqual(flagged.returncode, 0, 'audit must never block')
            self.assertIn('--yellow -> --color-mark', flagged.stdout)
            self.assertIn('--grey -> --color-ink-quiet', flagged.stdout)

    def test_audit_catches_a_redeclared_legacy_variable_too(self):
        """Redeclaring the palette was the standard way to recolour a
        series before the renames. It breaks as silently as a use does —
        the composed CSS reads var(--color-call) now, so the override
        applies to nothing — and the check once looked only for uses.
        --accent is also the §9-rewrite generation of rename, so this
        doubles as the guard that the new table entries are served."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            custom = Path(tmp) / 'templates' / 'custom.css'
            custom.write_text(custom.read_text(encoding='utf-8') +
                              '\n:root { --accent: #ff0000; }\n', encoding='utf-8')
            result = run('audit', tmp)
            self.assertEqual(result.returncode, 0, 'audit must never block')
            self.assertIn('--accent -> --color-call', result.stdout)

    def test_audit_flags_a_legacy_style_css_with_the_rename_table(self):
        """style.css is no longer read at all, which fails even more
        silently than a retired name: every value in it is ignored. audit
        must say so, and name the replacement for each old variable the
        file still touches so the move to settings.conf is mechanical."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            (Path(tmp) / 'templates' / 'style.css').write_text(
                ':root { --marker: #ff0000; }\n', encoding='utf-8')
            result = run('audit', tmp)
            self.assertEqual(result.returncode, 0, 'audit must never block')
            self.assertIn('no longer read', result.stderr)
            self.assertIn('--marker -> --color-mark', result.stdout)


class ThemesCommand(unittest.TestCase):
    """§11.9: the facets have to be reachable from the terminal, not only
    from the generated gallery page. lightwebpres is a standalone tool —
    if choosing a theme requires opening a browser, the CLI cannot do its
    own job."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    # Every command that takes a directory defaults to the one you are
    # standing in. Read off the help text rather than listed twice: a
    # command whose usage line writes `[directory]` promises that default,
    # and the promise is what this pair of tests holds it to.
    def test_the_help_offers_a_default_directory_on_every_such_command(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('theme show <slug>', result.stdout,
                         '`theme show` still demands a slug in the help')
        self.assertIn('theme show [<slug>...]', result.stdout)

    def test_reading_the_effective_theme_needs_no_directory_from_inside(self):
        """The habit every other command already keeps: build, verify,
        audit, status, clean and `series theme` all default to the
        directory you are in. `theme show` was the single exception — and
        the one place it broke was the place you are most likely to be
        standing inside the series when you ask, so it cost a `cd ..` and
        a name to get an answer about the series under your feet."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'content'
            self.assertEqual(run('init', str(root)).returncode, 0)
            bare = run('theme', 'show', cwd=str(root))
            self.assertEqual(bare.returncode, 0, bare.stderr)
            self.assertIn('effective theme', bare.stdout)
            # And it is the same answer the command that owns the series
            # reading gives, from inside and by name alike.
            canonical = run('series', 'theme', cwd=str(root))
            self.assertEqual(canonical.stdout, bare.stdout)
            named = run('series', 'theme', str(root))
            self.assertEqual(named.stdout, bare.stdout)

    def test_a_slug_still_wins_over_the_series_you_are_standing_in(self):
        """The default may not shadow the command's own subject. Standing
        in a series, `theme show nord` still describes nord."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'content'
            self.assertEqual(run('init', str(root)).returncode, 0)
            slug = run('theme', 'show', 'nord', cwd=str(root))
            self.assertEqual(slug.returncode, 0, slug.stderr)
            self.assertIn('Theme: nord', slug.stdout)
            self.assertNotIn('effective theme', slug.stdout)
            every = run('theme', 'show', '--all', cwd=str(root))
            self.assertEqual(every.returncode, 0, every.stderr)
            self.assertGreater(every.stdout.count('Theme: '), 1)

    def test_outside_a_series_the_bare_form_says_what_it_wanted(self):
        """Falling through to the usage error is deliberate: someone who
        typed `theme show` in an ordinary directory meant to name a slug
        and forgot, and "this is not a series" would answer a question
        they did not ask. The message names both ways out, and no longer
        tells anyone to pass a directory `series theme` does not need."""
        with tempfile.TemporaryDirectory() as tmp:
            result = run('theme', 'show', cwd=tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('needs at least one slug', result.stderr)
            self.assertIn('from inside the series', result.stderr)

    def test_a_note_is_plain_text_at_the_source(self):
        """Reported from the field: `themes` printed &ldquo; at the reader
        on eight themes. The notes were stored as gallery HTML and cleaned
        on the way to the terminal, and the cleaning stripped tags only —
        entities were the other half of the markup and went straight
        through. Cleaning enumerates what it already knows about, so the
        next markup added would have leaked too. Storage is plain text
        now and the conversion happens where markup is wanted, so this
        test guards the SOURCE, not the printout."""
        for slug, theme in self.lwp.THEMES.items():
            note = theme['note']
            self.assertNotIn('<', note, slug)
            self.assertNotIn('>', note, slug)
            self.assertNotRegex(note, r'&[a-zA-Z]+;|&#\d+;', slug)

    def test_the_terminal_listing_shows_no_markup_of_any_kind(self):
        result = run('theme', 'list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotRegex(result.stdout, r'&[a-zA-Z]+;|&#\d+;')
        self.assertNotIn('<code>', result.stdout)
        # The property names a note quotes must survive, or stripping the
        # markup would have taken the content with it.
        self.assertIn('color.page', result.stdout)

    def test_the_gallery_still_gets_the_markup_the_page_needs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        self.assertIn('<code>color.ink</code>', html)
        self.assertIn('<code>color.page</code>', html)

    def test_a_note_cannot_smuggle_html_into_the_gallery(self):
        """note_to_html escapes before it converts, so a note is content
        and never markup — the only tag it can produce is the <code> its
        own backticks ask for."""
        f = self.lwp.note_to_html
        self.assertEqual(f('a < b & c > d'), 'a &lt; b &amp; c &gt; d')
        self.assertEqual(f('<script>x</script>'),
                         '&lt;script&gt;x&lt;/script&gt;')
        self.assertEqual(f('set `--page` first'),
                         'set <code>--page</code> first')
        self.assertEqual(f('`<b>`'), '<code>&lt;b&gt;</code>')

    def test_bare_listing_names_every_theme_with_its_facets(self):
        result = run('theme', 'list')
        self.assertEqual(result.returncode, 0, result.stderr)
        for slug, theme in self.lwp.THEMES.items():
            facets = self.lwp.theme_facets(theme)
            trio = '/'.join((facets['polarity'], facets['hue']))
            self.assertIn(f'{slug}  [{trio}]', result.stdout, slug)

    def test_a_facet_filter_narrows_the_list_to_exactly_the_matching_themes(self):
        expected = [s for s, t in self.lwp.THEMES.items()
                    if self.lwp.theme_facets(t)['polarity'] == 'dark']
        self.assertTrue(expected, 'no dark theme to filter on')
        self.assertNotEqual(len(expected), len(self.lwp.THEMES))

        result = run('theme', 'list', '--polarity', 'dark')
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = re.findall(r'^  (\S+)  \[', result.stdout, re.MULTILINE)
        self.assertEqual(sorted(listed), sorted(expected))

    def test_filters_combine_and_agree_with_the_gallery_data_attributes(self):
        """One function feeds both surfaces (theme_facets), so a terminal
        picker and a browser picker cannot drift apart. Pinned, because
        the whole point of computing the facets is that nothing has to be
        kept in step by hand."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')

        cards = re.findall(
            r'data-polarity="([^"]*)" data-hue="([^"]*)" data-family="([^"]*)" '
            r'data-name="(\S+) ', html)
        self.assertEqual(len(cards), len(self.lwp.THEMES))

        for polarity, hue, family in {(c[0], c[1], c[2]) for c in cards}:
            from_gallery = sorted(c[3] for c in cards
                                  if (c[0], c[1], c[2]) == (polarity, hue, family))
            result = run('theme', 'list', '--polarity', polarity,
                         '--hue', hue, '--family', family)
            self.assertEqual(result.returncode, 0, result.stderr)
            from_cli = sorted(re.findall(r'^  (\S+)  \[', result.stdout, re.MULTILINE))
            self.assertEqual(from_cli, from_gallery, (polarity, hue, family))

    def test_an_unknown_facet_value_is_a_fatal_error_that_lists_the_valid_ones(self):
        """Not an empty result: 'rouge' is a typo for 'red', and quietly
        answering "no theme is like that" would send the reader looking
        for a theme that is right there."""
        result = run('theme', 'list', '--hue', 'rouge')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Unknown --hue', result.stderr)
        self.assertIn('red', result.stderr)

    def test_an_empty_but_legitimate_combination_says_so_and_succeeds(self):
        """The combination is derived, not named. This test used to ask for
        dark + orange, and adding one candlelit theme filled that cell and
        broke a test that was never about oranges -- so it now asks the
        catalogue which cell is empty and probes that one. If the catalogue
        ever covers every cell the empty branch becomes unreachable, and
        the test says so rather than passing on nothing."""
        filled = set()
        for theme in self.lwp.THEMES.values():
            f = self.lwp.theme_facets(theme)
            filled.add((f['polarity'], f['hue']))
        empty = [(p, h)
                 for p in self.lwp.FACET_VALUES['polarity']
                 for h in self.lwp.FACET_VALUES['hue']
                 if (p, h) not in filled]
        self.assertTrue(empty, 'every polarity x hue cell is filled -- the '
                               'empty-result message can no longer be reached')
        polarity, hue = empty[0]
        result = run('theme', 'list', '--polarity', polarity, '--hue', hue)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No theme matches', result.stdout, (polarity, hue))

    def test_help_no_longer_dumps_the_flat_slug_list(self):
        """At nine themes it was a reminder; past thirty it is the same
        unusable flat list the facets exist to replace, only relocated
        into the terminal."""
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [s for s in self.lwp.THEMES if s in result.stdout]
        self.assertLessEqual(len(listed), 2, f'help still enumerates themes: {listed}')
        self.assertIn('lightwebpres theme list', result.stdout)


class SetThemeCommand(unittest.TestCase):
    """§11.10 under the §9 rewrite: changing theme is changing one word.
    set-theme rewrites THE `theme:` line of settings.conf and nothing
    else. Everything the old implementation guarded against — half
    recoloured files, markers claiming themes a file does not carry,
    --force — existed only because the tool wrote into the file the
    author edits; those tests are retired with the mechanisms, and what
    they ultimately protected (never destroy the author's work) is now
    asserted directly, byte for byte."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def _uncomment(self, settings_path, commented, uncommented):
        """Author gesture: pin a value by uncommenting (or editing) a
        scaffold line."""
        text = settings_path.read_text(encoding='utf-8')
        self.assertIn(commented, text)
        settings_path.write_text(text.replace(commented, uncommented, 1),
                                 encoding='utf-8')

    def test_set_theme_rewrites_the_theme_line_and_nothing_else(self):
        """The one write the tool is allowed in an author-owned file.
        Asserted line by line on a file carrying an author's uncommented
        value: everything but the `theme:` line must survive byte for
        byte — including that pinned line."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            self._uncomment(settings, '# color.mark: #EBCB8B', 'color.mark: #EBCB8B')
            before = settings.read_text(encoding='utf-8').splitlines()

            result = run('series', 'theme', 'set', tmp, '--theme', 'evergreen')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Theme changed: nord -> evergreen', result.stdout)

            after = settings.read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(before), len(after))
            changed = [(a, b) for a, b in zip(before, after) if a != b]
            self.assertEqual(changed, [('theme: nord', 'theme: evergreen')])

    def test_setting_the_theme_already_in_place_writes_nothing(self):
        """Idempotence is a promise about the disk, not the message, so
        both are pinned: bytes and mtime untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            before_text = settings.read_text(encoding='utf-8')
            before_mtime = settings.stat().st_mtime_ns
            result = run('series', 'theme', 'set', tmp, '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Theme unchanged: already nord. Nothing written.', result.stdout)
            self.assertEqual(settings.read_text(encoding='utf-8'), before_text)
            self.assertEqual(settings.stat().st_mtime_ns, before_mtime)

    def test_repeated_theme_changes_keep_the_file_stable(self):
        """The old rewrite accumulated a blank line per run until
        set-theme demanded --force against its own output. The new one
        replaces a line in place, so any number of round trips must come
        back to the exact installed file."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            original = settings.read_text(encoding='utf-8')
            for slug in ('synthwave', 'crimson', 'sage', 'nord'):
                result = run('series', 'theme', 'set', tmp, '--theme', slug)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_text(encoding='utf-8'), original)

    def test_a_series_that_was_never_installed_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run('series', 'theme', 'set', tmp, '--theme', 'nord')
            self.assertEqual(result.returncode, 1)
            self.assertIn('Run init first', result.stderr)

    def test_templates_without_settings_gets_a_fresh_scaffold(self):
        """A series installed before the rewrite has templates/ but no
        settings.conf: nothing to preserve, so a full scaffold for the
        chosen theme is written — the same file install --theme writes."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'templates').mkdir()
            result = run('series', 'theme', 'set', tmp, '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('fresh settings.conf written', result.stdout)
            written = (Path(tmp) / 'templates' / 'settings.conf').read_text(encoding='utf-8')
            self.assertEqual(written, self.lwp.build_settings_scaffold('nord'))

    def test_a_missing_theme_option_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            missing = run('series', 'theme', 'set', tmp)
            self.assertEqual(missing.returncode, 1)
            self.assertIn('requires --theme', missing.stderr)

    def test_an_unknown_slug_is_fatal_and_names_the_catalogue_count(self):
        """The count is derived from THEMES (G6): an error message that
        says how many valid slugs exist cannot drift from the table."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            unknown = run('series', 'theme', 'set', tmp, '--theme', 'nope')
            self.assertEqual(unknown.returncode, 1)
            self.assertIn('Unknown theme', unknown.stderr)
            self.assertIn(f'{len(self.lwp.THEMES)} valid slugs', unknown.stderr)

    def test_the_default_theme_is_named_default_in_that_message(self):
        """A file with no theme line is on the default theme, which is an
        answer to "replaced by what" — not a missing value to elide."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            result = run('series', 'theme', 'set', tmp, '--theme', 'crimson')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Theme changed: default -> crimson', result.stdout)

    def test_the_commented_placeholder_is_uncommented_in_place(self):
        """On a default install the scaffold carries `# theme: <slug>`.
        set-theme must turn THAT line into the declaration rather than
        prepend a second one — otherwise the file grows a line per first
        change and the placeholder keeps advertising a choice already
        made. Line-diffed against the scaffold, same discipline as the
        themed case."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp).returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            before = settings.read_text(encoding='utf-8').splitlines()
            self.assertEqual(run('series', 'theme', 'set', tmp, '--theme', 'crimson').returncode, 0)
            after = settings.read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(before), len(after))
            changed = [(a, b) for a, b in zip(before, after) if a != b]
            self.assertEqual(len(changed), 1)
            self.assertTrue(changed[0][0].startswith('# theme: <slug>'), changed)
            self.assertEqual(changed[0][1], 'theme: crimson')

    def test_build_after_set_theme_emits_the_new_palette(self):
        """Changing the word must change the pages: the sheet is composed
        at build time from the declared theme, so no refresh step exists
        between set-theme and the new colours."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'nord').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('series', 'theme', 'set', tmp, '--theme', 'gruvbox').returncode, 0)
            self.assertEqual(run('build', tmp).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--color-mark: #D79921FF;', html)
            self.assertNotIn('#EBCB8B', html)

    def test_uncommented_values_survive_a_theme_change_and_still_win(self):
        """The CDC's dracula->nord scenario, correct by construction now:
        an author pins dracula's yellow-green mark, later moves the
        series to nord, and the pinned value still applies on top of the
        new theme — kept semantics, no longer silent (audit names it)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root), '--theme', 'dracula').returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            self._uncomment(settings, '# color.mark: #F1FA8C', 'color.mark: #F1FA8C')
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('series', 'theme', 'set', tmp, '--theme', 'nord').returncode, 0)
            self.assertEqual(run('build', tmp).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--color-mark: #F1FA8CFF;', html,
                          'the pinned value must beat the new theme')
            self.assertNotIn('#EBCB8B', html)

    def test_the_change_message_says_commented_values_show_the_old_theme(self):
        """The scaffold's comments age when the theme changes, and the
        remedy is to SAY so, never to rewrite the author's file — the
        message is that promise, made audible at the moment it starts
        being true."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('init', tmp, '--theme', 'nord').returncode, 0)
            result = run('series', 'theme', 'set', tmp, '--theme', 'evergreen')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Commented values still show the previous theme', result.stdout)
            self.assertIn('uncommented values are untouched', result.stdout.lower())


class DefaultStylesheetCoverage(unittest.TestCase):
    """§9/§9.5: the composed stylesheet is a maintained artifact, not a
    leftover of the article the first sheet was extracted from. Three
    properties, none of which held before the sheet was audited — ported
    from the installed style.css to the engine's own emission, which is
    what every page now inlines."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def resolve(self, *layers):
        return self.lwp.resolve_theme_properties(*layers)

    def test_the_engine_emits_no_literal_content_colour(self):
        """Any fixed colour in an emitted rule silently survives theming.
        That is how rules, table headers, card backgrounds and the
        cover's greys used to keep a default-palette cast on every one of
        the nine themes. Under the engine every rule must read a var();
        colours live only in :root. The skeleton is layout by definition
        (its rgba box-shadows paint depth, not content) and is guarded
        separately: no hex there either."""
        css = self.lwp.emit_theme_css(self.resolve(self.lwp.theme_property_layer('solarized')))
        rules = css[css.index('\n}') + 2:]        # everything after :root
        leftovers = re.findall(r'#[0-9a-fA-F]{3,8}\b', rules)
        self.assertEqual(leftovers, [],
                         'fixed colours in emitted rules survive theming: '
                         + ', '.join(sorted(set(leftovers))))
        self.assertNotIn('rgba(', rules)
        self.assertNotIn(': white', rules)
        skeleton = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_SKELETON, flags=re.S)
        self.assertEqual(re.findall(r'#[0-9a-fA-F]{3,8}\b', skeleton), [],
                         'the skeleton is layout-only and may not carry a content colour')

    def test_the_three_verdict_classes_look_different(self):
        """.yes/.no/.partial are the documented hook for a comparison
        table's verdict cells (§6.1). .yes and .partial used to carry
        byte-identical declarations, so a three-way comparison only ever
        showed two states — which defeats the entire point of colouring
        them. Under the engine the difference is two-channel by design:
        distinct inks AND distinct shape marks (the marks alone must
        differ too, because weight no longer separates partial from yes —
        only normal/bold survive a generic family)."""
        r = self.resolve({})
        fgs = {name: r[f'verdict.{name}.fg'] for name in ('yes', 'no', 'partial')}
        self.assertEqual(len(set(fgs.values())), 3, fgs)
        marks = {name: r[f'verdict.{name}.mark'] for name in ('yes', 'no', 'partial')}
        self.assertEqual(marks, {'yes': '"\\25CF"', 'partial': '"\\25D0"',
                                 'no': '"\\25CB"'})
        # And the emission actually consumes them: an ink on the cell, a
        # mark generated before it.
        css = self.lwp.emit_theme_css(r)
        for name in ('yes', 'no', 'partial'):
            self.assertIn(f'.comparison-table .{name}::before {{ '
                          f'content: var(--verdict-{name}-mark); }}', css, name)
            self.assertIn(f'var(--verdict-{name}-fg)', css, name)

    def test_every_markdown_construct_the_converter_emits_is_styled(self):
        """The converter has always produced blockquotes, code spans,
        fenced code blocks and footnote markers, and the stylesheet had
        no rule for any of them: a quotation rendered exactly like a
        paragraph. A feature added without a registry component ships
        invisible, so this pins the tags rather than the look — on the
        composed sheet, the only one a page gets."""
        css = self.lwp.compose_stylesheet(self.resolve({}))
        for selector in ('blockquote', 'code', 'pre', 'sup'):
            self.assertRegex(
                css, r'(^|[\s,])' + selector + r'\s*[,{]',
                f'{selector} is emitted by the converter but has no rule',
            )


class FactStrongEmphasis(unittest.TestCase):
    """§9.1 -> §9 rewrite: fact.strong.weight/style/bg/fg independently
    control a fact-box's Markdown **bold** rendering (weight, italic, and
    mark-style ground with its own ink), decoupled from each other and
    from the semantic <strong> markup itself. The refresh-templates
    reapply test is retired with its mechanism: the sheet is composed at
    build time, so there is no stale on-disk copy left to reapply a
    theme's emphasis into."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def resolve(self, *layers):
        return self.lwp.resolve_theme_properties(*layers)

    def test_engine_defaults_match_the_prior_look(self):
        r = self.resolve({})
        self.assertEqual(r['fact.strong.weight'], 'bold')
        self.assertEqual(r['fact.strong.style'], 'normal')
        self.assertEqual(r['fact.strong.bg'], '#FFFC00FF')     # the mark
        self.assertEqual(r['fact.strong.fg'], '#1A1A2EFF')     # the ink

    def test_themes_set_distinct_fact_strong_treatments(self):
        """The same three catalogue witnesses as before the rewrite, read
        through their property layers. Solarized also pins the None
        highlight: `fact_highlight: None` means NO ground (#00000000) and
        the body ink — not 'nothing said'; the first port run turned the
        five highlight-less themes yellow by conflating the two."""
        sol = self.resolve(self.lwp.theme_property_layer('solarized'))
        self.assertEqual(sol['fact.strong.weight'], 'bold')
        self.assertEqual(sol['fact.strong.style'], 'italic')
        self.assertEqual(sol['fact.strong.bg'], '#00000000')
        self.assertEqual(sol['fact.strong.fg'], sol['color.ink'])

        dra = self.resolve(self.lwp.theme_property_layer('dracula'))
        self.assertEqual(dra['fact.strong.bg'], dra['color.affirm'])

        cat = self.resolve(self.lwp.theme_property_layer('catppuccin'))
        self.assertEqual(cat['fact.strong.weight'], 'normal')
        self.assertEqual(cat['fact.strong.style'], 'italic')

    def test_user_can_keep_highlight_and_drop_bold_via_settings(self):
        """The exact motivating use case: highlight kept, bold dropped,
        without hand-writing a full replacement rule — one uncommented
        line in settings.conf of a real series, verified in the page a
        reader loads."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            text = settings.read_text(encoding='utf-8')
            settings.write_text(text.replace('# fact.strong.weight: bold',
                                             'fact.strong.weight: normal', 1),
                                encoding='utf-8')
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('build', tmp).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--fact-strong-weight: normal;', html)
            self.assertIn('--fact-strong-bg: #FFFC00FF;', html,
                          'the highlight must survive the weight override')

    def test_themes_gallery_shows_a_bolded_word_styled_per_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'gallery.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
            # The bolded word comes from the real renderer, inside the
            # preview document's srcdoc, and the emphasis properties from
            # that document's own composed stylesheet — not from an inline
            # style attribute the gallery assembled itself.
            self.assertIn('&lt;strong&gt;', html)
            for declaration in ('--fact-strong-weight: normal;',
                                '--fact-strong-style: italic;',
                                '--fact-strong-bg: #00000000;'):
                self.assertIn(declaration, html, declaration)


class CoverCardinalityFreedom(unittest.TestCase):
    """§4.4/§22.13: build must never block on the number or position of
    cover slides — that's audit's job, purely editorial."""

    def test_build_succeeds_with_no_cover(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k158\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_succeeds_with_multiple_covers(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k159\nkicker: T1\n# First cover\nsummary: S1.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k160\nkicker: T2\n# Second cover\nsummary: S2.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('First cover', html)
            self.assertIn('Second cover', html)

    def test_build_succeeds_with_cover_not_first(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k161\nkicker: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k162\nkicker: T2\n# Cover title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)


class SeriesJsonRequiredFields(unittest.TestCase):
    """§20.3: `source` is the only field required directly in
    series.json — `file` is optional (derives from `source` if absent
    everywhere, §20.3.1); a missing source file is a warning, not a
    fatal error. nav_title/nav_desc requiredness is covered by
    DisplayFieldOverrides (§20.3.1) — they're no longer required to be
    typed into series.json specifically, only to resolve to a non-empty
    value somewhere (series.json, the article's own meta block, or a
    content-derived fallback)."""

    def _series_missing_field(self, tmp, field):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k163\nkicker: T\n# Title\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
        del entry[field]
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_missing_file_field_derives_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_missing_field(tmp, 'page_dest')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_missing_source_field_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_missing_field(tmp, 'page_source')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_nonexistent_source_file_is_fatal_before_any_output(self):
        # §20.3: a listed page_source that doesn't exist is a fatal error,
        # checked up front — the entry used to keep its index card,
        # series-nav entries and README line pointing at a page that was
        # never built (dead links shipped with exit code 0).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            series = {'articles': [
                {'page_dest': 'a.html', 'page_source': 'missing.md', 'nav_title': 'A', 'nav_desc': 'A'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Source not found', result.stderr)
            # Fatal before writing anything: no partial output directory
            self.assertFalse((root / 'public' / 'index.html').exists())

    def test_missing_series_meta_falls_back_to_untitled_string(self):
        """§20.5: series_meta (and title within it) is optional — despite
        the schema table once (wrongly) marking title required, the code
        has always read it with a fallback string, never a fatal error."""
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, (
                '<!-- lwp:meta -->\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k164\nkicker: T\n# Title\nsummary: Summary.\n'
            ))
            # A plain-array series.json (no series_meta key at all, §20.4's
            # backward-compatible format) — the strictest case for "series_meta
            # is optional", since there isn't even an empty {} to fall back on.
            (root / 'series.json').write_text(json.dumps([
                {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
            ]), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Article series', index_html)


class SeriesJsonExtensionValidation(unittest.TestCase):
    """§20.3: file/source must carry the right extension — otherwise the
    build silently writes rendered HTML to a file named e.g. a.md, or
    reads a non-Markdown file as if it were the article source. Fatal,
    same severity as the existing safe-filename check, checked
    case-insensitively."""

    def _series_with(self, tmp, file_value, source_value):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k165\nkicker: T\n# Title\n',
            encoding='utf-8',
        )
        series = {'articles': [
            {'page_dest': file_value, 'page_source': source_value, 'nav_title': 'A', 'nav_desc': 'A'},
        ]}
        (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
        return root

    def test_file_without_html_extension_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with(tmp, 'a.md', 'a.md')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('.html or .htm', result.stderr)

    def test_source_without_md_extension_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with(tmp, 'a.html', 'a.txt')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('.md', result.stderr)

    def test_htm_extension_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with(tmp, 'a.htm', 'a.md')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.htm').exists())

    def test_file_extension_check_is_case_insensitive(self):
        # Only the extension check itself is under test here — an uppercase
        # "file" value with the real, correctly-cased source must pass
        # validation and actually build (not just avoid the fatal error).
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with(tmp, 'a.HTML', 'a.md')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.HTML').exists())

    def test_source_extension_check_is_case_insensitive(self):
        # Source lookup on disk is itself case-sensitive on most
        # filesystems, so the article file is written with a matching
        # uppercase .MD extension here — this isolates the extension
        # *validation* being case-insensitive from that unrelated concern.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'sources' / 'a.MD').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k166\nkicker: T\n# Title\n',
                encoding='utf-8',
            )
            series = {'articles': [
                {'page_dest': 'a.html', 'page_source': 'a.MD', 'nav_title': 'A', 'nav_desc': 'A'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())


class DisplayFieldOverrides(unittest.TestCase):
    """§20.3.1: page_dest/page_title/card_title/card_desc/card_label/
    nav_title/nav_desc all resolve as series.json entry > article's own
    meta block field of the same name > a content-derived fallback, most
    specific to least specific:

      page_dest   : derived from `page_source` (.md -> .html)
      page_title  : the cover slide's own h1 -> the resolved page_dest
      card_title  : page_title (resolved)
      card_desc   : the cover slide's own summary
      card_label  : '' (nothing to extrapolate)
      nav_title   : card_title (resolved)
      nav_desc    : card_desc (resolved)

    Written in the retired `file`/`source` vocabulary until this was
    caught — the suite was documenting a surface its own
    LegacyFieldMigrationErrors tests make fatal. And it claimed nothing
    in the chain is ever fatal, the exact sentence
    SkillDocumentsWhatTheCodeAccepts bans from SKILL.md on the grounds
    that page_dest has three fatal paths. The display fields resolve to
    something; page_dest and page_source do not, and series.json still
    requires page_source."""

    def _build(self, tmp, meta_extra, series_entry_extra, cover_extra=''):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            '<!-- lwp:meta -->\n' + meta_extra + '\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k167\nkicker: T\n# Cover H1\n' + cover_extra + '\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_source': 'a.md'}
        entry.update(series_entry_extra)
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    # --- file --------------------------------------------------------

    def test_file_absent_everywhere_derives_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Test', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_file_from_meta_used_when_series_json_omits_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_dest: renamed.html\npage_title: Test', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'renamed.html').exists())
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_series_json_file_overrides_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, 'page_dest: from-meta.html\npage_title: Test',
                {'page_dest': 'from-series-json.html'},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'from-series-json.html').exists())
            self.assertFalse((root / 'public' / 'from-meta.html').exists())

    # --- page_title ----------------------------------------------------

    def test_page_title_from_meta_used_on_own_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Meta title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<title>Meta title</title>', html)

    def test_series_json_page_title_overrides_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Meta title', {'page_title': 'Override title'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<title>Override title</title>', html)
            self.assertNotIn('Meta title', html)

    def test_page_title_absent_everywhere_falls_back_to_cover_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, '', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<title>Cover H1</title>', html)

    # --- card_title / card_desc -----------------------------------------

    def test_card_title_desc_from_meta_used_on_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp,
                'page_title: Page title\ncard_title: Card title\ncard_desc: Card desc',
                {},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Card title', html)
            self.assertIn('Card desc', html)

    def test_series_json_card_title_desc_override_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp,
                'page_title: Page title\ncard_title: Meta card title\ncard_desc: Meta card desc',
                {'card_title': 'Override card title', 'card_desc': 'Override card desc'},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Override card title', html)
            self.assertIn('Override card desc', html)
            self.assertNotIn('Meta card title', html)

    def test_card_title_absent_everywhere_falls_back_to_page_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Page title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-title">Page title</div>', html)

    def test_card_desc_absent_everywhere_falls_back_to_cover_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, 'page_title: Page title', {},
                cover_extra='summary: Cover summary text.',
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-desc">Cover summary text.</div>', html)

    def test_card_desc_absent_everywhere_and_no_cover_summary_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Page title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-desc"></div>', html)

    # --- card_label ------------------------------------------------------

    def test_card_label_from_meta_used_on_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, 'page_title: Page title\ncard_label: Meta label', {},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-number">Meta label</div>', html)

    def test_series_json_card_label_overrides_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, 'page_title: Page title\ncard_label: Meta label',
                {'card_label': 'Override label'},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-number">Override label</div>', html)
            self.assertNotIn('Meta label', html)

    def test_card_label_absent_everywhere_is_not_an_error(self):
        # No label anywhere: still no error — and no empty
        # <div class="article-number"></div> is emitted either.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Page title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('<div class="article-number">', html)

    # --- nav_title / nav_desc, and card_label reused in series-nav -----

    def _build_with_series_nav(self, tmp, meta_extra, series_entry_extra, cover_extra=''):
        # Unlike _build() above, this article includes a series-nav slide
        # so the "Cette série" block actually renders on its own page.
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            '<!-- lwp:meta -->\n' + meta_extra + '\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k168\nkicker: T\n# Cover H1\n' + cover_extra + '\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k169\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_source': 'a.md'}
        entry.update(series_entry_extra)
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_nav_title_desc_from_meta_used_in_series_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(
                tmp,
                'page_title: Page title\nnav_title: Nav title\nnav_desc: Nav desc',
                {},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Nav title', html)
            self.assertIn('Nav desc', html)

    def test_series_json_nav_title_desc_override_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(
                tmp,
                'page_title: Page title\nnav_title: Meta nav title\nnav_desc: Meta nav desc',
                {'nav_title': 'Override nav title', 'nav_desc': 'Override nav desc'},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Override nav title', html)
            self.assertIn('Override nav desc', html)
            self.assertNotIn('Meta nav title', html)

    def test_nav_title_desc_absent_everywhere_falls_back_to_card_title_desc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(
                tmp,
                'page_title: Page title\ncard_title: Card title\ncard_desc: Card desc',
                {},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Card title', html)
            self.assertIn('Card desc', html)

    def test_nav_title_desc_absent_everywhere_falls_back_all_the_way_to_page_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(tmp, 'page_title: Page title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Page title', html)

    def test_card_label_from_meta_appears_in_series_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(
                tmp,
                'page_title: Page title\ncard_label: Meta label',
                {},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="series-label">Meta label</div>', html)

    def test_series_json_card_label_override_appears_in_series_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build_with_series_nav(
                tmp,
                'page_title: Page title\ncard_label: Meta label',
                {'card_label': 'Override label'},
            )
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="series-label">Override label</div>', html)
            self.assertNotIn('Meta label', html)


class ImageCopySafety(unittest.TestCase):
    """§P2: copy_images must merge into an existing public/img/, never wipe
    it — a mistyped --output pointing at an unrelated directory must not
    delete content that build didn't put there."""

    def test_existing_unrelated_file_in_output_img_survives_build(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k170\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'photo.jpg').write_bytes(b'fake-photo')
            output_dir = root / 'public'
            (output_dir / 'img').mkdir(parents=True)
            (output_dir / 'img' / 'unrelated.png').write_bytes(b'pre-existing')

            result = run('build', str(root), '--output', str(output_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / 'img' / 'unrelated.png').exists())
            self.assertTrue((output_dir / 'img' / 'photo.jpg').exists())


class DemoOverwriteProtection(unittest.TestCase):
    """§P2: demo must refuse to silently overwrite existing article files."""

    def test_demo_twice_is_fatal_on_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            first = run('demo', str(root))
            self.assertEqual(first.returncode, 0, first.stderr)
            second = run('demo', str(root))
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('already has demo file', second.stderr)


class HelpDocumentsTypographyControls(unittest.TestCase):
    """The typography engine alters generated content (§4.5/§7.5/§19.6),
    so --help must document its rules and every way to turn it off —
    not just specifications.md."""

    def test_help_mentions_meta_opt_outs_and_no_typography_flag(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0)
        for needle in ('typo_units', 'typo_thousands', '--no-typography'):
            self.assertIn(needle, result.stdout)


class HelpDoesNotDocumentRemovedH1H2FieldSyntax(unittest.TestCase):
    """GLOSSARY.md: h1:/h2: as an explicit slide field was removed — #/##
    is the only way to set a slide's own heading (slide_title). --help
    used to say "h1 or # Title" / "h2 or ## Title", still implying the
    removed field form was valid."""

    def test_help_does_not_mention_h1_or_h2_field_form(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('h1 or', result.stdout)
        self.assertNotIn('h2 (or', result.stdout)
        self.assertIn('# Title', result.stdout)


class HelpListsEveryAcceptedOption(unittest.TestCase):
    """--help is the "Full reference" README promises (§11): an option the
    tables accept must not be invisible there. These five drifted out
    over time while the tables stayed authoritative."""

    def test_help_names_the_options_the_tables_accept(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for needle in (
                '--slides-page-numbers on|off',
                '--templates',
                'build/watch/verify: do not generate the series navigation',
                'build/watch: build only status: draft articles',
                'restrict the audit to the presentation/template layer'):
            self.assertIn(needle, result.stdout, needle)
        self.assertIn('## Title', result.stdout)


class TypographyTagProtection(unittest.TestCase):
    """§P2/§19.3: typography rules must never be able to corrupt HTML tag
    syntax in already-assembled HTML (fact-box content, full articles),
    regardless of what a language/*.json override file's rules do."""

    def test_custom_rule_does_not_corrupt_link_tag_attribute(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k171\nkicker: T\n## Title\nfact-label: The fact\n'
            'See [the source](https://example.org/page).\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(json.dumps({
                'lang': 'fr',
                'rules': [{
                    'name': 'adversarial', 'description': 'test',
                    'pattern': 'href=', 'replacement': 'data-href=', 'flags': 'g',
                }],
            }), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'fr')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('href="https://example.org/page"', html)
            self.assertNotIn('data-href=', html)


class SeriesDirEnvVar(unittest.TestCase):
    """§P3: LWP_SERIES_DIR must be used as the default series directory
    when no positional [directory] argument is given."""

    def test_series_dir_env_var_used_when_no_positional_arg(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k172\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as series_tmp, tempfile.TemporaryDirectory() as cwd_tmp:
            root = scaffold(series_tmp, md)
            result = run(
                'build', '--output', str(root / 'public'),
                cwd=cwd_tmp, env={'LWP_SERIES_DIR': str(root)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())


class LanguageFileOption(unittest.TestCase):
    """§P3/§19.5: --language-file is the highest-priority language source,
    overriding even a conventional language/{lang}.json file that's also
    present."""

    def test_language_file_option_takes_priority(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k173\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(
                json.dumps({'lang': 'fr', 'strings': {'nav_prev': 'FROM-CONVENTIONAL-FILE'}}),
                encoding='utf-8',
            )
            explicit = root / 'custom-lang.json'
            explicit.write_text(
                json.dumps({'lang': 'fr', 'strings': {'nav_prev': 'FROM-EXPLICIT-FLAG'}}),
                encoding='utf-8',
            )
            result = run(
                'build', str(root), '--output', str(root / 'public'),
                '--lang', 'fr', '--language-file', str(explicit),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="FROM-EXPLICIT-FLAG"', html)
            self.assertNotIn('FROM-CONVENTIONAL-FILE', html)

    def test_language_file_option_missing_file_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k174\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run(
                'build', str(root), '--output', str(root / 'public'),
                '--language-file', str(root / 'nope.json'),
            )
            self.assertNotEqual(result.returncode, 0)


class CheckSummaryLine(unittest.TestCase):
    """§P3/§11.4: check must print a numeric "N OK, M different" summary."""

    def test_summary_line_reflects_ok_and_drift_counts(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k175\nkicker: T\n# Title\nsummary: Original.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            clean = run('verify', str(root), '--output', str(root / 'public'))
            # 3 files: the article page, index.html and README.md (§11.4)
            self.assertIn('3 file(s) OK, 0 file(s) different.', clean.stdout)

            changed_md = md.replace('Original.', 'Changed.')
            (root / 'sources' / 'a.md').write_text(changed_md, encoding='utf-8')
            drifted = run('verify', str(root), '--output', str(root / 'public'))
            # The cover summary cascades to the index card's card_desc
            # (§20.3.1), so the page AND the index drift — exactly the
            # kind of index staleness check now catches (§11.4).
            self.assertIn('1 file(s) OK, 2 file(s) different.', drifted.stdout)


class InstallCopiesExecutable(unittest.TestCase):
    """§P3/§11.1: install copies lightwebpres itself into the target
    directory, so the series directory is usable standalone."""

    def test_install_copies_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            copied = root / 'lightwebpres'
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_bytes(), EXECUTABLE.read_bytes())
            self.assertTrue(os.access(copied, os.X_OK))


class ReadmeGeneration(unittest.TestCase):
    """§P3/§8.3: build generates README.md from series.json — a numbered
    list of articles, linked to their built HTML file."""

    def test_readme_contains_title_and_numbered_article_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md_a = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: Article A\n'
                'nav_desc: Desc A\n---\n\n<!-- lwp:slide:cover -->\nslug: k176\nkicker: T\n# A\n'
            )
            (root / 'sources' / 'a.md').write_text(md_a, encoding='utf-8')
            series = {
                'series_meta': {'title': 'My Series', 'subtitle': 'A subtitle'},
                'articles': [
                    {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'Article A', 'nav_desc': 'Desc A'},
                ],
            }
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')

            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            self.assertIn('# My Series', readme)
            self.assertIn('A subtitle', readme)
            self.assertIn('1. [Article A](public/a.html) — Desc A', readme)


class PathTraversalSafety(unittest.TestCase):
    """Security: series.json (LLM/CI-editable, spec §13.5) and article:
    are joined into real filesystem paths with Path(dir) / value — an
    absolute path or ../ value must be rejected, not silently resolved
    outside sources/public (Path(dir) / '/etc/passwd' == '/etc/passwd')."""

    def _series_with_file_value(self, tmp, field, value):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k177\nkicker: T\n# Title\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
        entry[field] = value
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_absolute_file_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_file_value(tmp, 'page_dest', '/tmp/evil.html')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)

    def test_traversal_source_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_file_value(tmp, 'page_source', '../../etc/passwd')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)

    def test_traversal_article_field_is_rejected(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k178\narticle: ../../../etc/passwd\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)

    def test_bare_dotdot_article_is_rejected_not_crash(self):
        # `article: ..` passes a name-shape check (Path('..').name == '..')
        # yet is a directory — it used to raise an uncaught IsADirectoryError.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k179\narticle: ..\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)


class SymlinkContainment(unittest.TestCase):
    """Security: the name-shape guard cannot see that a bare filename is a
    symlink into an outside file/dir. A git repo can carry such symlinks,
    so an unattended build of an attacker-authored series would otherwise
    exfiltrate host files. Realpath containment refuses them."""

    def _secret(self, tmp):
        secret = Path(tmp) / 'SECRET.txt'
        secret.write_text('TOP-SECRET-CONTENTS', encoding='utf-8')
        return secret

    def test_full_article_symlink_escaping_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = self._secret(tmp)
            root = Path(tmp) / 'proj'
            (root / 'sources').mkdir(parents=True)
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:full-article -->\nslug: k180\narticle: leak.md\n', encoding='utf-8')
            (root / 'sources' / 'leak.md').symlink_to(secret)
            (root / 'series.json').write_text(json.dumps(
                {'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('resolves outside', result.stderr)
            if (root / 'public' / 'a.html').exists():
                self.assertNotIn('TOP-SECRET-CONTENTS',
                                 (root / 'public' / 'a.html').read_text(encoding='utf-8'))

    def test_img_symlink_escaping_is_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = self._secret(tmp)
            root = Path(tmp) / 'proj'
            (root / 'sources' / 'img').mkdir(parents=True)
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k181\nkicker: T\n# Title\n', encoding='utf-8')
            (root / 'sources' / 'img' / 'leak.png').symlink_to(secret)
            (root / 'series.json').write_text(json.dumps(
                {'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            leaked = root / 'public' / 'img' / 'leak.png'
            if leaked.exists():
                self.assertNotIn('TOP-SECRET-CONTENTS', leaked.read_text(encoding='utf-8'))
            self.assertIn('skipped symlink', result.stderr)

    def test_internal_img_symlink_is_kept(self):
        # A symlink pointing WITHIN img/ is harmless and must still copy.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'proj'
            (root / 'sources' / 'img').mkdir(parents=True)
            (root / 'sources' / 'img' / 'real.png').write_text('PNGDATA', encoding='utf-8')
            (root / 'sources' / 'img' / 'alias.png').symlink_to(
                root / 'sources' / 'img' / 'real.png')
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k182\nkicker: T\n# Title\n', encoding='utf-8')
            (root / 'series.json').write_text(json.dumps(
                {'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                (root / 'public' / 'img' / 'alias.png').read_text(encoding='utf-8'),
                'PNGDATA')


class LinkHrefEscaping(unittest.TestCase):
    """Security: the Markdown link URL goes into an href="..." attribute
    and must be attribute-escaped — the http(s)-only restriction is not a
    containment guarantee. A `"` used to close the attribute and inject a
    live event handler; a `>` used to close the <a> and open a new tag."""

    def _html(self, body):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: k183\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'sources' / 'art.md').write_text(body, encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            assert result.returncode == 0, result.stderr
            return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_quote_in_url_cannot_break_the_attribute(self):
        html = self._html('[x](https://a" onmouseover="alert(1)) end\n')
        self.assertNotIn('" onmouseover="', html)
        self.assertIn('&quot; onmouseover=&quot;', html)

    def test_angle_in_url_cannot_close_the_anchor(self):
        html = self._html('[x](https://a><img src=y onerror=alert(1) ) end\n')
        self.assertNotIn('<img src=y onerror', html)
        self.assertIn('&gt;&lt;img', html)

    def test_ampersand_in_url_is_single_escaped(self):
        html = self._html('[x](https://a.org/p?q=1&r=2)\n')
        self.assertIn('href="https://a.org/p?q=1&amp;r=2"', html)
        self.assertNotIn('&amp;amp;', html)


class NoQuadraticBacktracking(unittest.TestCase):
    """Security: the converter's own regexes run over attacker-influenced
    input text (article bodies, and in the browser flow the whole thing is
    attacker-supplied and single-threaded). A line of '<a'×N or '['×N used
    to be O(n²) — 40 KB took tens of seconds. Bounded now: a large
    pathological line must convert in well under a second."""

    def test_repeated_open_tag_and_bracket_are_linear(self):
        import time
        import importlib.machinery, importlib.util
        loader = importlib.machinery.SourceFileLoader('lwp_perf', str(EXECUTABLE))
        spec = importlib.util.spec_from_loader('lwp_perf', loader)
        lwp = importlib.util.module_from_spec(spec)
        loader.exec_module(lwp)
        for payload in ('<a' * 40000, '[' * 40000):
            start = time.time()
            lwp.convert_markdown(payload)
            elapsed = time.time() - start
            self.assertLess(elapsed, 1.0,
                            'converter went superlinear on a pathological line (%.2fs)' % elapsed)


class IndexTitleXssProtection(unittest.TestCase):
    """Security: series_meta.title lands both in <title> (RCDATA, always
    tag-stripped) and in the visible {{series_title}} body (raw HTML
    allowed by design, like an article's h1). A payload with a stray
    </title> is now caught two ways: the <title> tag itself is stripped,
    AND the same raw payload in the body makes the page as a whole
    unbalanced, which validate_html() (§13.6) now refuses to publish —
    belt and suspenders, tested as the end-to-end outcome that matters:
    the build must never silently ship this."""

    def _build_with_nav_title(self, tmp, malicious_title):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k184\nkicker: T\n# A\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        series = {
            'series_meta': {'title': malicious_title},
            'articles': [{'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}],
        }
        (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
        return run('build', str(root), '--output', str(root / 'public'))

    def test_stray_closing_title_tag_is_never_silently_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build_with_nav_title(tmp, 'x</title><script>alert(1)</script>')
            # validate_html() catches the resulting page-wide imbalance
            # (the same raw payload also lands, by design, in the visible
            # h1) and refuses to write anything rather than publish it.
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not well-formed', result.stderr)

    def test_well_formed_nav_title_with_angle_brackets_still_builds(self):
        # Sanity/non-regression companion: legitimate, self-contained
        # markup in series_meta.title (matching the documented h1 <br>
        # allowance) must still build fine — validate_html() only rejects
        # genuine imbalance, not the mere presence of tags.
        with tempfile.TemporaryDirectory() as tmp:
            result = self._build_with_nav_title(tmp, 'My series<br>a subtitle-ish line')
            self.assertEqual(result.returncode, 0, result.stderr)


class HrefAttributeEscaping(unittest.TestCase):
    """Security: entry['file'] is interpolated into href="..." attributes;
    a quote character in it must not break out of the attribute even
    though the path-safety check (no slash) alone wouldn't catch it."""

    def test_quote_in_file_value_does_not_break_out_of_href(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a".html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k185\nkicker: T\n# A\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            series = {'articles': [
                {'page_dest': 'a".html', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('href="a&quot;.html"', index_html)
            self.assertNotIn('href="a".html"', index_html)


class MalformedInputHandling(unittest.TestCase):
    """Reliability: malformed/wrong-type JSON must fail with a clean
    [ERROR] message and non-zero exit, not a raw Python traceback."""

    def test_invalid_json_series_file_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text('{not valid json', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_articles_not_a_list_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({'articles': 'oops'}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_invalid_json_language_file_is_a_clean_error(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k186\nkicker: T\n# Title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text('{not valid json', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'fr')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_rules_not_a_list_is_a_clean_error(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k187\nkicker: T\n# Title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(
                json.dumps({'lang': 'fr', 'rules': 'oops'}), encoding='utf-8',
            )
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'fr')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_invalid_regex_pattern_in_language_rule_is_a_clean_error(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k188\nkicker: T\n# Title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'language').mkdir()
            (root / 'language' / 'fr.json').write_text(json.dumps({
                'lang': 'fr',
                'rules': [{'name': 'bad', 'description': 'x', 'pattern': '(unclosed', 'replacement': 'x'}],
            }), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'fr')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)


class ParserFieldTextSwitch(unittest.TestCase):
    """§22.1/§22.2: once free text starts, --- inside it is a thematic
    break (slide separator via the normal split), not literal content, and
    a key:-value-shaped line inside free text is not re-parsed as a field."""

    def test_dashes_inside_factbox_free_text_split_the_slide(self):
        # A bare `---` line always separates slides (§4.1); if authored
        # inside a fact-box's free text, it splits that slide in two
        # rather than becoming literal content — this is a hard rule, not
        # a bug, but the split must actually happen as documented.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k189\nkicker: T\n## Title\nfact-label: The fact\n'
            'Before the break.\n\n---\n\nslug: k189b\nAfter the break.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Before the break.', html)
            self.assertIn('After the break.', html)
            self.assertEqual(html.count('class="slide"'), 2)

    def test_field_like_line_inside_free_text_is_not_reparsed_as_a_field(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k190\nkicker: T\n## Title\nfact-label: The fact\n'
            'A first paragraph starts free text.\n\n'
            'kicker: this looks like a field but is not one.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('this looks like a field but is not one', html)


class OptionalFieldOmission(unittest.TestCase):
    """§22.3/§22.4: a slide without kicker: or a cover without summary: must
    build successfully, simply omitting that element — not fatal, not a
    silent corruption."""

    def test_slide_without_tag_omits_tag_span(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k191\n## Title without a tag\nsummary: Summary here.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="slide-kicker"', html)
            self.assertIn('Title without a tag', html)

    def test_cover_without_summary_builds_successfully(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k192\nkicker: T\n# Cover without summary\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="summary"', html)
            self.assertIn('Cover without summary', html)


class SourceFieldRendering(unittest.TestCase):
    """§4.3: the source: field renders as a labeled source line."""

    def test_source_field_renders(self):
        # English has no nbsp-before-colon typography rule, so the plain
        # space is the correct, unambiguous assertion here; the French
        # nbsp case is covered separately below.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k193\nkicker: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
            'Fact content.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<p class="source">Source : Some Author, 2024.</p>', html)

    def test_source_label_colon_gets_nbsp_typography(self):
        """The 'Source :' prefix must go through typography like any other
        text: a non-breaking space before the colon in French, not a
        plain space — the label+value string must be built before
        typo_engine.apply(), not after."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k194\nkicker: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
            'Fact content.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'fr')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<p class="source">Source : Some Author, 2024.</p>', html)


class LanguageDirEnvVar(unittest.TestCase):
    """§19.5 priority level 2: LWP_LANGUAGE_DIR overrides the conventional
    {series_dir}/language directory."""

    def test_language_dir_env_var_is_used(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k195\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as lang_tmp:
            root = scaffold(tmp, md)
            lang_dir = Path(lang_tmp)
            (lang_dir / 'fr.json').write_text(
                json.dumps({'lang': 'fr', 'strings': {'nav_prev': 'FROM-ENV-VAR-DIR'}}),
                encoding='utf-8',
            )
            result = run(
                'build', str(root), '--output', str(root / 'public'), '--lang', 'fr',
                env={'LWP_LANGUAGE_DIR': str(lang_dir)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('title="FROM-ENV-VAR-DIR"', html)


class ArticlesArrayOrder(unittest.TestCase):
    """§20.3: the articles array is ordered — that order must actually
    drive nav/index/README output order, not just be assumed."""

    def _series(self, tmp, order):
        root = Path(tmp)
        (root / 'sources').mkdir()
        entries = []
        for name in order:
            md = (
                f'<!-- lwp:meta -->\npage_dest: {name}.html\npage_title: {name}\nnav_title: {name}\n'
                f'nav_desc: D\n---\n\n<!-- lwp:slide:cover -->\nslug: k196\nkicker: T\n# {name}\n'
            )
            (root / 'sources' / f'{name}.md').write_text(md, encoding='utf-8')
            entries.append({'page_dest': f'{name}.html', 'page_source': f'{name}.md',
                             'nav_title': name, 'nav_desc': 'D'})
        (root / 'series.json').write_text(json.dumps({'articles': entries}), encoding='utf-8')
        return root

    def test_index_card_order_follows_array_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, ['zzz', 'aaa'])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertLess(index_html.index('href="zzz.html"'), index_html.index('href="aaa.html"'))

    def test_readme_order_follows_array_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, ['zzz', 'aaa'])
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            self.assertLess(readme.index('1. [zzz]'), readme.index('2. [aaa]'))


class H1H2FieldFormRemoved(unittest.TestCase):
    """§4.3: `#`/`##` is the only way to set a slide's own heading — a
    literal `h1:`/`h2:` key-value field used to be an accepted synonym,
    but that redundant spelling was removed (GLOSSARY.md): an unrecognized
    key flips the one-way field->free-text switch (§4.1/§22.2) like any
    other typo would, it doesn't silently become a heading."""

    def test_h2_field_form_is_not_a_heading_anymore(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k197\nkicker: T\nh2: Title via field\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<h2>Title via field</h2>', html)
            # The one-way switch already flipped on the unrecognized `h2:`
            # line, so `summary:` right after it is text too, not a field.
            self.assertIn('h2: Title via field', html)
            self.assertIn('summary: Summary.', html)

    def test_h1_field_form_is_fatal_on_a_cover_slide(self):
        """A cover slide has no fact-box (§22.12) — free text after its
        recognized fields is a fatal error, and `h1:` no longer counts as
        one of those fields."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k198\nkicker: T\nh1: Title via field\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_cover_unknown_field_error_lists_cover_fields(self):
        """A field-shaped typo on a cover gets an actionable migration hint
        instead of only the generic no-fact-box error."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k199\ntag: Visible label\n# Title\n'
            'summary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unrecognized field "tag:"', result.stderr)
            self.assertIn(
                'kicker:, tags:, summary:, comment:, note:', result.stderr)
            self.assertIn(
                'Use "kicker:" for a visible label or "tags:" for variant filtering.',
                result.stderr,
            )

    def test_cover_generic_unknown_field_error_lists_cover_fields(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k200\nmystery: value\n# Title\n'
            'summary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unrecognized field "mystery:"', result.stderr)
            self.assertIn(
                'kicker:, tags:, summary:, comment:, note:', result.stderr)
            self.assertNotIn('Use "kicker:" for a visible label', result.stderr)


class FactLabelOptional(unittest.TestCase):
    """§4.3: free text after a standard slide's fields goes into the
    fact-box when fact-label: is present, or a bare <p> paragraph
    (no fact-box wrapper) when it's absent."""

    def test_fact_label_present_produces_fact_box(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k201\nkicker: T\n## Title\nfact-label: The takeaway\nContent with a fact-label.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="fact-box">', html)
            self.assertIn('<div class="fact-label">The takeaway</div>', html)
            self.assertIn('<div class="fact-content">', html)
            self.assertIn('<p>Content with a fact-label.</p>', html)

    def test_fact_label_absent_produces_bare_paragraph(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k202\nkicker: T\n## Title\nContent without a fact-label.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="fact-box"', html)
            self.assertNotIn('class="fact-label"', html)
            self.assertNotIn('class="fact-content"', html)
            self.assertIn('<p>Content without a fact-label.</p>', html)

    def test_fact_label_absent_multi_paragraph(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k203\nkicker: T\n## Title\nFirst paragraph.\n\nSecond paragraph.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="fact-box"', html)
            self.assertIn('<p>First paragraph.</p>', html)
            self.assertIn('<p>Second paragraph.</p>', html)

    def test_heading_in_no_label_body_is_scoped_smaller_than_slide_title(self):
        # A `#` in a standard slide's free text (no fact-label) is body
        # content (§22.2), not the slide's title. It used to render as a
        # bare <h1> at cover-title size (bigger than the slide's own `##`
        # title); it must now be wrapped in .slide-body and scoped down.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k204\nkicker: T\n## Slide title\n# Body heading\n\nBody.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="slide-body">', html)
            self.assertIn('<h1>Body heading</h1>', html)
            self.assertIn('.slide-body h1 { font-size: 1.3em; }', html)


class FactBoxBlockquoteAndCode(unittest.TestCase):
    """§6.3: fact-box free text shares convert_markdown() with the
    full-article body, so blockquotes and code must work there too, not
    just in a full-article file."""

    def test_fact_box_supports_blockquote_and_inline_code(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k205\nkicker: T\n## Title\nfact-label: Source\n'
            '> A quoted sentence.\n\nRun `lightwebpres build`.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<blockquote><p>A quoted sentence.</p></blockquote>', html)
            self.assertIn('<code>lightwebpres build</code>', html)


class CheckNewMarker(unittest.TestCase):
    """§11.4: check must print [NEW] for an article in series.json that
    was never built (missing from public/) — distinct from [DRIFT]."""

    def test_check_reports_new_for_unbuilt_article(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k206\nkicker: T\n# Title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[NEW] a.html', result.stdout)


class SeriesJsonEmptyStringRejected(unittest.TestCase):
    """§20.3/§20.3.1: an empty string, not just an absent key, must be
    treated the same as "no value" everywhere requiredness is checked.
    For `source` (never overridable, always required directly in
    series.json) that means fatal outright — same for `file` if it's
    explicitly given as an empty string rather than simply omitted. For
    nav_title/nav_desc/card_title/card_desc/card_label/page_title
    (all overridable, §20.3.1) an empty string in series.json is
    correctly treated the same as an absent key: "no override", falls
    back down the resolution chain — nothing in that chain is ever fatal,
    it always bottoms out at a content-derived value."""

    def test_empty_string_file_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k207\nkicker: T\n# Title\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': '', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_empty_string_nav_title_falls_back_to_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: Meta title\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k208\nkicker: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: k209\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': '', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            # nav_title only ever renders in the series-nav card, on the
            # article's OWN page (a.html) — never on index.html.
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Meta title', html)

    def test_empty_string_nav_title_falls_back_through_card_title_when_meta_also_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k210\nkicker: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: k211\n'
            )
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': 'a.html', 'page_source': 'a.md', 'nav_title': '', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            # nav_title falls through to card_title, which falls through
            # to page_title ("Test") — nothing here is fatal anymore.
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Test', html)


class InstallGitlabCi(unittest.TestCase):
    """§11.1(6)/§10: .gitlab-ci.yml is opt-in via --gitlab-ci, never
    written by a plain install — install must never presuppose a GitLab
    deployment on its own."""

    def test_install_without_flag_does_not_create_gitlab_ci_yml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / '.gitlab-ci.yml').exists())

    def test_install_with_flag_creates_gitlab_ci_yml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('init', str(root), '--gitlab-ci')
            self.assertEqual(result.returncode, 0, result.stderr)
            ci = (root / '.gitlab-ci.yml').read_text(encoding='utf-8')
            self.assertIn('lightwebpres build', ci)


class GeneratedHtmlValidation(unittest.TestCase):
    """§13.6: every generated page is checked for tag balance before being
    written — an unclosed/mismatched tag (raw HTML passthrough, per §6.2,
    is exactly how an author could introduce one) must be a fatal build
    error, not a silently-published broken page."""

    def test_unclosed_div_in_raw_html_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k212\nkicker: T\n## Title\nfact-label: The fact\n'
            '<div>This div is never closed.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not well-formed', result.stderr)

    def test_mismatched_closing_tag_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k213\nkicker: T\n## Title\nfact-label: The fact\n'
            '<div><span>Mismatched.</div></span>\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not well-formed', result.stderr)

    def test_void_elements_and_script_content_do_not_false_positive(self):
        # br/hr/img (no closing tag expected) and a <script> tag containing
        # comparison operators (< / >) must NOT be mistaken for broken markup.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k214\nkicker: T\n## Title\nfact-label: The fact\n'
            'A line<br>with a break, then <hr> and '
            '<script>if (1 < 2 && 3 > 2) { void 0; }</script> inline.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)


class CommentField(unittest.TestCase):
    """GLOSSARY.md: `comment` is a review-note field, recognized wherever
    other fields are (series.json entry, article meta block, cover/
    standard slide header) but never read by any renderer — parsed and
    discarded, never reaching the built output anywhere."""

    def test_comment_recognized_everywhere_never_leaks_into_output(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\n'
            'nav_desc: A\ncomment: META-BLOCK-SECRET\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k215\nkicker: T\ncomment: COVER-SECRET\n'
            '# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k216\nkicker: T2\ncomment: STANDARD-SECRET\n'
            '## Standard title\nsummary: Summary 2.\nfact-label: The fact\n'
            'Body text.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({
                'articles': [{'page_source': 'a.md', 'comment': 'SERIES-JSON-SECRET'}],
            }), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            for secret in ('META-BLOCK-SECRET', 'COVER-SECRET', 'STANDARD-SECRET',
                           'SERIES-JSON-SECRET'):
                self.assertNotIn(secret, html_a)
                self.assertNotIn(secret, index_html)

    def test_comment_on_cover_slide_is_not_a_fatal_unexpected_content_error(self):
        """A cover slide has no fact-box (§22.12) — comment: must be
        recognized as a real field there, not fall through to content."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k217\nkicker: T\ncomment: a note\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_comment_on_standard_slide_does_not_become_fact_box_content(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k218\nkicker: T\n'
            'comment: STANDARD-COMMENT-SECRET\n## Title\nsummary: Summary.\n'
            'fact-label: The fact\nReal fact-box body.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Real fact-box body.', html)
            # A distinctive needle, like the other tests in this
            # class use. `a note` matched a sentence in nav.js's own
            # comments and failed on a page the comment never
            # reached -- a needle short enough to occur in the
            # furniture tests the furniture, not the field.
            self.assertNotIn('STANDARD-COMMENT-SECRET', html)


class HeadingInBodyIsContentNotRetitle(unittest.TestCase):
    """§22.2: the field->free-text switch applies to # / ## lines exactly
    like key: value fields — a heading appearing after body content has
    already started is fact-box content (rendered as a real heading by
    convert_markdown), not a silent overwrite of the slide's own h1/h2."""

    def test_heading_after_body_content_does_not_overwrite_slide_h2(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k219\nkicker: T\n## Real title\nfact-label: The fact\n\n'
            'First paragraph of body text.\n\n'
            '## This looks like a heading in the body\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # The slide's own title must survive untouched...
            self.assertIn('<h2>Real title</h2>', html)
            # ...and the in-body heading must render as fact-box content.
            self.assertIn(
                '<p>First paragraph of body text.</p>',
                html,
            )
            self.assertIn('<h2>This looks like a heading in the body</h2>', html)
            # Only one <h2> may be the slide title; the second is nested
            # inside the fact-box, not a sibling slide title.
            self.assertEqual(html.count('<h2>'), 2)


class FactBoxOpensWithHeadingOrList(unittest.TestCase):
    """A fact-box whose free text starts directly with a heading or a
    list (no leading plain paragraph) is a legitimate, common shape —
    the parser must not mistake that opening heading for a second
    assignment of the slide's own title, and the wrapper around the
    content must be a <div> (valid regardless of what block-level
    element opens it), not a <p> (invalid once anything but plain text
    is inside)."""

    def test_heading_as_first_fact_box_line_does_not_overwrite_slide_title(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k220\nkicker: T\n## The real slide title\nfact-label: The fact\n\n'
            '## Sub-heading opening the fact-box\n\n'
            'Body text after the sub-heading.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # Exactly one <h2> is the slide's own title...
            self.assertIn('<h2>The real slide title</h2>', html)
            # ...and the fact-box's own opening heading is real content,
            # nested inside .fact-content, not a second slide title.
            self.assertIn('<div class="fact-content">', html)
            self.assertIn('<h2>Sub-heading opening the fact-box</h2>', html)
            self.assertIn('<p>Body text after the sub-heading.</p>', html)
            self.assertEqual(html.count('<h2>'), 2)

    def test_second_h1_on_a_cover_is_content_and_therefore_fatal(self):
        """Same trap, on a cover slide (its own title is h1, not h2) — a
        second `#` before any content must fall through to content, same
        rule as the h2/standard case, NOT silently overwrite the cover's
        real title. Unlike a standard slide, a cover has no fact-box
        (§22.12), so that content is a fatal error, not silently
        rendered — this test's job is to prove it reaches THAT correct
        error (content detected), not a wrong h1 in the output."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k221\nkicker: T\n# The real cover title\nsummary: Summary.\n\n'
            '# This is body text, not a retitle\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('has no fact-box', result.stderr)

    def test_hash_heading_on_standard_slide_is_content_not_silently_dropped(self):
        """The deeper trap: `#` (not `##`) opening a standard slide's
        fact-box used to be captured into slide.h1 — an attribute a
        standard slide's renderer never reads — vanishing with no error
        and no trace, worse than the h2-on-h2 case (which at least
        produced a visibly wrong title)."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k222\nkicker: T\n## Real title\nfact-label: The fact\n\n'
            '# A heading using single hash\n\n'
            'Body text.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h2>Real title</h2>', html)
            self.assertIn('<h1>A heading using single hash</h1>', html)
            self.assertIn('<p>Body text.</p>', html)

    def test_list_as_first_fact_box_line_wraps_in_div_not_p(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k223\nkicker: T\n## Title\nfact-label: The fact\n\n'
            '- First item\n- Second item\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="fact-content">', html)
            self.assertNotIn('<p class="fact-content">', html)
            self.assertIn('<ul>', html)
            self.assertIn('<li>First item</li>', html)
            self.assertIn('<li>Second item</li>', html)
            # A <p> can never validly contain a <ul> — the fix must not
            # produce that invalid nesting, only the correct <div> wrapper.
            self.assertNotIn('<p><ul>', html)

    def test_stylesheet_scopes_fact_content_headings_smaller_than_slide_title(self):
        """CSS-only guarantee: nested headings inside a fact-box must not
        inherit the giant global slide-title sizing — a scoped rule for
        .fact-content h1/h2/h3 must exist in the generated stylesheet."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k224\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('.fact-content h1, .fact-content h2, .fact-content h3', html)


class EditorialFields(unittest.TestCase):
    """§20.3.1/GLOSSARY.md: author/license/date — the article→series
    cascade (series.json entry > meta block > series_meta default) and
    their displayed renderings (page footer + <meta name="author">,
    series-wide footer on the index)."""

    def _build(self, tmp, meta_extra='', entry_extra=None, series_meta=None):
        root = Path(tmp)
        (root / 'sources').mkdir()
        md = (
            f'<!-- lwp:meta -->\npage_title: Test\n{meta_extra}---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k225\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_source': 'a.md'}
        entry.update(entry_extra or {})
        data = {'articles': [entry]}
        if series_meta:
            data['series_meta'] = series_meta
        (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        assert result.returncode == 0, result.stderr
        return root

    def test_author_from_series_meta_default_reaches_footer_and_meta_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, series_meta={'title': 'S', 'author': 'Alice Martin'})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<meta name="author" content="Alice Martin">', html)
            self.assertIn('<div class="footer-byline">Alice Martin</div>', html)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="footer-byline">Alice Martin</div>', index_html)

    def test_meta_block_author_overrides_series_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, meta_extra='author: Bob Ley\n',
                               series_meta={'title': 'S', 'author': 'Alice Martin'})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('content="Bob Ley"', html)
            self.assertNotIn('content="Alice Martin"', html)

    def test_series_json_entry_author_overrides_meta_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, meta_extra='author: Bob Ley\n',
                               entry_extra={'author': 'Carol Diaz'})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('content="Carol Diaz"', html)
            self.assertNotIn('Bob Ley', html)

    def test_license_shown_on_article_and_index_footers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, series_meta={'title': 'S', 'license': 'CC BY-SA 4.0'})
            for page in ('a.html', 'index.html'):
                html = (root / 'public' / page).read_text(encoding='utf-8')
                self.assertIn('<div class="footer-license">CC BY-SA 4.0</div>', html)

    def test_date_joined_to_author_in_byline_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, meta_extra='author: Alice\ndate: mars 2026\n')
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="footer-byline">Alice — mars 2026</div>', html)

    def test_no_editorial_fields_means_no_footer_and_no_meta_author(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('page-footer">', html)
            self.assertNotIn('<meta name="author"', html)


class PageDescMetaDescription(unittest.TestCase):
    """§20.3.1: page_desc feeds <meta name="description"> (series.json >
    meta block > cover summary > tag omitted), and is deliberately NOT
    chained with card_desc — invisible metadata never leaks into the
    visible index cards."""

    def _build(self, tmp, meta_extra='', entry_extra=None, summary='Cover summary.'):
        root = Path(tmp)
        (root / 'sources').mkdir()
        summary_line = f'summary: {summary}\n' if summary else ''
        md = (
            f'<!-- lwp:meta -->\npage_title: Test\n{meta_extra}---\n\n'
            f'<!-- lwp:slide:cover -->\nslug: k226\nkicker: T\n# Title\n{summary_line}'
        )
        (root / 'sources' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'page_source': 'a.md'}
        entry.update(entry_extra or {})
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        assert result.returncode == 0, result.stderr
        return root

    def test_page_desc_falls_back_to_cover_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<meta name="description" content="Cover summary.">', html)

    def test_explicit_page_desc_wins_but_never_leaks_into_index_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, meta_extra='page_desc: SEO-tuned text.\n')
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('content="SEO-tuned text."', html)
            # The visible index card must keep the cover summary, NOT the
            # invisible SEO description (the unchained-branches rule).
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('Cover summary.', index_html)
            self.assertNotIn('SEO-tuned text.', index_html)

    def test_no_description_anywhere_omits_the_tag_and_audit_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, summary='')
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('<meta name="description"', html)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no description anywhere', result.stderr)


class ArticleStatus(unittest.TestCase):
    """§20.6: an article is `active`, `draft` or `ignored`, and the three
    are three degrees of participation in the series.

    `draft` is the old boolean's behaviour: out of the OUTPUT unless
    --include-drafts, which builds it with a banner, but still an article
    of the series for anything that counts. `ignored` is the new one, and
    the reason the field exists: out of the chain entirely, whatever the
    flags, so an article can be set aside without deleting the entry that
    carries all its settings."""

    def _series(self, tmp, b_meta_extra='', b_entry_extra=None):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Live article\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k227\nkicker: T\n# Live\nsummary: Live summary.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: k228\n', encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(
            f'<!-- lwp:meta -->\npage_title: Draft article\n{b_meta_extra}---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k229\nkicker: T\n# Draft\nsummary: Draft summary.\n', encoding='utf-8')
        entry_b = {'page_source': 'b.md'}
        entry_b.update(b_entry_extra or {})
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}, entry_b],
        }), encoding='utf-8')
        return root

    def test_draft_excluded_from_page_index_and_nav_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='status: draft\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[draft] b.html skipped', result.stdout)
            self.assertFalse((root / 'public' / 'b.html').exists())
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('b.html', index_html)
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('b.html', html_a)

    def test_include_drafts_builds_the_page_with_a_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='status: draft\n')
            result = run('build', str(root), '--output', str(root / 'public'), '--include-drafts')
            self.assertEqual(result.returncode, 0, result.stderr)
            html_b = (root / 'public' / 'b.html').read_text(encoding='utf-8')
            self.assertIn('class="draft-banner"', html_b)
            self.assertIn('Brouillon', html_b)
            # The live article gets no banner, ever.
            html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('draft-banner', html_a)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('b.html', index_html)

    def test_series_json_overrides_the_meta_block(self):
        """The priority §20.6 fixes, and the case the boolean needed a
        special rule for: series.json turning a declared draft back on.
        With three named words it is an ordinary cascade — `active` is a
        value, not an absence — which is why nothing here has to
        distinguish "written false" from "not written"."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='status: draft\n',
                                b_entry_extra={'status': 'active'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'b.html').exists())
            html_b = (root / 'public' / 'b.html').read_text(encoding='utf-8')
            self.assertNotIn('draft-banner', html_b)

    def test_an_unknown_status_is_a_fatal_error_naming_the_article(self):
        """Not silently treated as the default: an author reading a series
        that ignores what they asked for, with nothing to say why, is the
        outcome every other typed value here is protected from."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='status: publised\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('b.md', result.stderr)
            self.assertIn('active | draft | ignored', result.stderr)

    def test_absent_status_means_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'b.html').exists())

    # --- ignored: the reason the field exists ------------------------------

    def test_ignored_is_out_of_the_chain_whatever_the_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_entry_extra={'status': 'ignored'})
            for flags in ((), ('--include-drafts',)):
                with self.subTest(flags=flags):
                    shutil.rmtree(root / 'public', ignore_errors=True)
                    result = run('build', str(root), '--output',
                                 str(root / 'public'), *flags)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('[ignored] b.html', result.stdout)
                    self.assertFalse(
                        (root / 'public' / 'b.html').exists(),
                        'an ignored article was built — --include-drafts must '
                        'not reach it, or `ignored` is just a second `draft`')
                    index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
                    self.assertNotIn('b.html', index_html)
                    html_a = (root / 'public' / 'a.html').read_text(encoding='utf-8')
                    self.assertNotIn('b.html', html_a)

    def test_the_entry_survives_being_ignored(self):
        """The point of the status over deleting the entry: every field it
        carries is still there afterwards, and one word brings it back."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_entry_extra={
                'status': 'ignored', 'card_label': 'Part 2', 'nav_title': 'Second'})
            run('build', str(root), '--output', str(root / 'public'))
            entry = json.loads((root / 'series.json').read_text(encoding='utf-8'))['articles'][1]
            self.assertEqual(entry['card_label'], 'Part 2')
            self.assertEqual(entry['nav_title'], 'Second')

    def test_audit_names_every_ignored_article(self):
        """The one place that mentions them. Everything else in the tool
        is silent about an ignored article by construction, which is what
        it is for and also how it gets forgotten."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_entry_extra={'status': 'ignored'})
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('b.md', result.stdout)
            self.assertIn('ignored', result.stdout)

    # --- what each status is worth to the index tally (§11.3.3) ------------

    def _claiming(self, tmp, b_status):
        """A two-entry series whose SECOND article takes the index name."""
        root = self._series(tmp, b_entry_extra={
            'status': b_status, 'page_dest': 'index.html'})
        return root

    def test_a_draft_still_counts_for_the_index_name(self):
        """A draft is an article of the series, so the collision is decided
        identically with and without --include-drafts. Counting the built
        list instead would make a series.json legal or illegal depending on
        a build flag."""
        for flags in ((), ('--include-drafts',)):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
                root = self._claiming(tmp, 'draft')
                result = run('build', str(root), '--output', str(root / 'public'), *flags)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('collides with the series index', result.stderr)

    def test_an_ignored_article_does_not_count_for_the_index_name(self):
        """It is not an article of the series at all, so what is left is a
        one-article series — which may take the index name."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_entry_extra={'status': 'ignored'})
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_source': 'a.md', 'page_dest': 'index.html'},
                {'page_source': 'b.md', 'status': 'ignored'},
            ]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[no index]', result.stdout)


class LegacyFieldMigrationErrors(unittest.TestCase):
    """v1.0 freeze (JOURNAL-1.0.md §2.1): the retired series.json keys
    `source`/`file` produce an explicit renamed-in-v1.0 error, not a
    mystifying missing-required-field one."""

    def _series_with_keys(self, tmp, entry):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: T\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k230\nkicker: T\n# T\nsummary: S.\n', encoding='utf-8')
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_legacy_source_key_gets_migration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_keys(tmp, {'source': 'a.md'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('renamed to "page_source" in v0.7.0', result.stderr)

    def test_legacy_file_key_gets_migration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_keys(tmp, {'page_source': 'a.md', 'file': 'a.html'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('renamed to "page_dest" in v0.7.0', result.stderr)


class DegenerateInputRobustness(unittest.TestCase):
    """1.0 review axis 1 (JOURNAL-1.0.md §3): BOM, CRLF, empty files and
    invalid encodings must produce either a correct build or a clean
    [ERROR] — never a raw traceback, never silent corruption."""

    def _series(self, tmp):
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'series.json').write_text(
            json.dumps({'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
        return root

    MD = ('<!-- lwp:meta -->\npage_title: Test\n---\n\n'
          '<!-- lwp:slide:cover -->\nslug: k231\nkicker: T\n# Title\nsummary: Summary.\n')

    def test_bom_in_series_json_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'sources' / 'a.md').write_text(self.MD, encoding='utf-8')
            raw = (root / 'series.json').read_bytes()
            (root / 'series.json').write_bytes(b'\xef\xbb\xbf' + raw)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_bom_in_full_article_does_not_leak_or_break_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'sources' / 'a.md').write_text(
                self.MD + '\n---\n\n<!-- lwp:slide:full-article -->\nslug: k232\narticle: a_article.md\n',
                encoding='utf-8')
            (root / 'sources' / 'a_article.md').write_bytes(
                b'\xef\xbb\xbf# Full article heading\n\nBody.\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h1>Full article heading</h1>', html)
            self.assertNotIn('\ufeff', html)

    def test_crlf_article_parses_identically(self):
        crlf_md = (
            '<!-- lwp:meta -->\npage_title: Test\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k233\nkicker: T\n# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k234\nkicker: T2\n## Second\nsummary: S2.\nfact-label: F\n\nBody.\n'
        ).replace('\n', '\r\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'sources' / 'a.md').write_bytes(crlf_md.encode('utf-8'))
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h1>Title</h1>', html)
            self.assertIn('<h2>Second</h2>', html)
            self.assertEqual(html.count('<section class="slide'), 2)

    def test_invalid_utf8_article_gets_clean_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'sources' / 'a.md').write_bytes(
                b'<!-- lwp:meta -->\npage_title: T\n---\n\n'
                b'<!-- lwp:slide:cover -->\nslug: k235\nkicker: T\n# Broken \xff\xfe\nsummary: S.\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not valid UTF-8', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_empty_article_file_gets_clean_meta_block_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'sources' / 'a.md').write_text('', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must start with a <!-- lwp:meta --> block', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_empty_articles_array_builds_an_empty_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({'articles': []}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'index.html').exists())




class BuildDeterminism(unittest.TestCase):
    """1.0 review axis 3 (JOURNAL-1.0.md §3): without --build-stamp, two
    builds of the same sources are byte-identical across every output
    file (articles, index, README) — the property `check` (§11.4)
    structurally depends on. datetime.now() lives only in
    build_stamp_html(); nothing else in the build path reads the clock,
    randomness, locale, or directory enumeration order."""

    def test_two_builds_are_byte_identical_across_all_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            for name in ('a', 'b'):
                (root / 'sources' / f'{name}.md').write_text(
                    f'<!-- lwp:meta -->\npage_title: Article {name}\ndate: 2026\n---\n\n'
                    f'<!-- lwp:slide:cover -->\nslug: k236\nkicker: T\n# Article {name}\nsummary: Résumé : test.\n\n---\n\n'
                    f'<!-- lwp:slide -->\nslug: k237\nkicker: F\n## Fiche\nsummary: S.\nfact-label: Fait\n\nCorps **gras**.\n\n---\n\n'
                    f'<!-- lwp:slide:series-nav -->\nslug: k238\n', encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'S', 'author': 'A', 'license': 'L'},
                'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}],
            }), encoding='utf-8')
            for out in ('pub1', 'pub2'):
                result = run('build', str(root), '--output', str(root / out))
                self.assertEqual(result.returncode, 0, result.stderr)
            files1 = sorted(p.relative_to(root / 'pub1') for p in (root / 'pub1').rglob('*') if p.is_file())
            files2 = sorted(p.relative_to(root / 'pub2') for p in (root / 'pub2').rglob('*') if p.is_file())
            self.assertEqual(files1, files2)
            self.assertTrue(files1)
            for rel in files1:
                self.assertEqual((root / 'pub1' / rel).read_bytes(),
                                 (root / 'pub2' / rel).read_bytes(), rel)




class Portability(unittest.TestCase):
    """1.0 review axis 2 (JOURNAL-1.0.md §3): declared minimum Python 3.8,
    OS-independent output, and case-collision safety for Windows/macOS
    filesystems."""

    def test_source_parses_under_python_36_grammar(self):
        """The version guard can only explain itself on an old
        interpreter if the module still PARSES there — pin the grammar
        floor so a future edit doesn't silently break the guard."""
        import ast as ast_mod
        src = EXECUTABLE.read_text(encoding='utf-8')
        ast_mod.parse(src, feature_version=(3, 6))

    def test_version_guard_present_and_declares_38(self):
        src = EXECUTABLE.read_text(encoding='utf-8')
        self.assertIn('sys.version_info < (3, 8)', src)

    def test_readme_links_use_forward_slashes(self):
        md = (
            '<!-- lwp:meta -->\npage_title: Test\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k239\nkicker: T\n# Title\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            self.assertIn('(public/a.html)', readme)
            self.assertNotIn('\\', readme.split('## Articles')[1])

    def test_case_insensitive_page_dest_collision_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            for name in ('a.md', 'b.md'):
                (root / 'sources' / name).write_text(
                    '<!-- lwp:meta -->\npage_title: T\n---\n\n'
                    '<!-- lwp:slide:cover -->\nslug: k240\nkicker: T\n# T\nsummary: S.\n', encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_source': 'a.md', 'page_dest': 'Same.html'},
                {'page_source': 'b.md', 'page_dest': 'same.html'},
            ]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('case-insensitively', result.stderr)




class I18nParity(unittest.TestCase):
    """1.0 review axis 9 (JOURNAL-1.0.md §3): the built-in language packs
    must stay in lockstep — same string keys in fr and en, every key the
    code or templates reference present in both, no dead keys."""

    @staticmethod
    def _packs_and_source():
        src = EXECUTABLE.read_text(encoding='utf-8')
        fr = json.loads(re.search(r"LANG_FR = r\'\'\'(.*?)\'\'\'", src, re.DOTALL).group(1))
        en = json.loads(re.search(r"LANG_EN = r\'\'\'(.*?)\'\'\'", src, re.DOTALL).group(1))
        return fr, en, src

    def test_fr_and_en_have_identical_string_key_sets(self):
        fr, en, _ = self._packs_and_source()
        self.assertEqual(set(fr['strings']), set(en['strings']))

    def test_every_referenced_key_exists_in_both_packs_and_none_is_dead(self):
        fr, en, src = self._packs_and_source()
        used = set(re.findall(r"strings\.get\('([a-z_0-9]+)'", src))
        used |= set(re.findall(r"\{\{str_([a-z_0-9]+)\}\}", src))
        self.assertFalse(used - set(fr['strings']), 'referenced but missing from fr')
        self.assertFalse(used - set(en['strings']), 'referenced but missing from en')
        dead = set(fr['strings']) - used
        self.assertFalse(dead, 'dead keys (defined, never referenced)')

    def test_copy_feedback_tooltip_uses_the_language_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, (
                '<!-- lwp:meta -->\npage_title: T\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k241\nkicker: T\n# T\nsummary: S.\n'))
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn("btn.title = 'Link copied!'", html)


class NativeUtf8EndToEnd(unittest.TestCase):
    """Native UTF-8, end to end: accents, CJK, emoji, Cyrillic and RTL
    Arabic through every field AND in the page_source/page_dest filenames
    themselves — content, hrefs, README links and <meta> tags all intact."""

    def test_full_unicode_pipeline_including_accented_filenames(self):
        md = (
            '<!-- lwp:meta -->\npage_title: Café ☕ 日本語\nauthor: Zoë Müller\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k242\nkicker: Été\n# À 東京 🗼\nsummary: всё хорошо.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k243\nkicker: نص\n## عنوان عربي\nsummary: RTL.\nfact-label: Факт\n\nCorps 中文 🎉.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            (root / 'sources' / 'café-日本.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps(
                {'articles': [{'page_source': 'café-日本.md'}]}, ensure_ascii=False), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'café-日本.html').read_text(encoding='utf-8')
            for needle in ('<meta charset="UTF-8">', '東京 🗼', 'всё хорошо',
                           '<h2>عنوان عربي</h2>', 'Факт', '中文 🎉',
                           'name="author" content="Zoë Müller"'):
                self.assertIn(needle, html)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('href="café-日本.html"', index_html)
            readme = (root / 'README.md').read_text(encoding='utf-8')
            self.assertIn('café-日本.html', readme)




class ThemeEngineStaged(unittest.TestCase):
    """The property engine (§9 rewrite), wired through build. These pin the
    interface itself — one cascade for every property, references resolved by
    axis-fixed namespace, errors that name their key — under the full
    inventory that build/install/set-theme all compose from."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def resolve(self, *layers):
        return self.lwp.resolve_theme_properties(*layers)

    def test_later_layer_wins_and_bare_words_resolve_in_namespace(self):
        r = self.resolve({'color.ink': '#112233'},
                         {'summary.fg': 'ink-quiet'})
        self.assertEqual(r['color.ink'], '#112233FF')
        # summary.fg said a bare word: looked up in color.*, one hop.
        self.assertEqual(r['summary.fg'], r['color.ink-quiet'])

    def test_qualified_reference_reaches_another_component(self):
        r = self.resolve({'highlight.fg': 'summary.fg'})
        self.assertEqual(r['highlight.fg'], r['summary.fg'])

    def test_terminal_style_theme_is_fonts_plus_colours(self):
        # The catalogue's `terminal` in the new vocabulary: fixed pitch is
        # three lines. title1.font -> font.display -> font.text -> font.mono
        # is a 3-hop chain — an ordinary theme sitting exactly at the cap,
        # which is why the cap is three and not two.
        r = self.resolve({
            'color.page': '#0B0F0C', 'color.ink': '#D7FFE0',
            'font.text': 'mono', 'font.display': 'mono', 'font.ui': 'mono',
            'cover.fg': 'ink',
            # the green halo around the cover title: a shadow with no offset
            'title1.shadow.fg': '#33FF8880', 'title1.shadow.blur': '8px',
        })
        self.assertIn('monospace', r['page.font'])
        self.assertIn('monospace', r['title1.font'])
        self.assertIn('monospace', r['kicker.font'])
        # title1.fg -> cover.fg -> color.ink, an ordinary 2-hop chain.
        self.assertEqual(r['title1.fg'], '#D7FFE0FF')
        self.assertEqual(r['title1.shadow.fg'], '#33FF8880')

    def test_a_halo_at_its_default_is_not_emitted_at_all(self):
        """Not an optimisation, and the difference is the whole of B20.
        `text-shadow` is INHERITED, so emitting it at its default does not
        paint nothing — it BLOCKS the halo the page set. With thirty-two
        components carrying axes, emitting the default everywhere would
        have taken the atmosphere off every one of them on the nine themes
        that set `page.shadow`. Saying nothing is the only way to say
        `inherit`."""
        css = self.lwp.emit_theme_css(self.resolve({}))
        self.assertNotIn('text-shadow', css,
                         'a halo nobody asked for is blocking inheritance')

    def test_a_halo_a_theme_asks_for_is_emitted_on_its_own_selector(self):
        css = self.lwp.emit_theme_css(self.resolve({
            'title2.shadow.fg': '#33FF8880', 'title2.shadow.blur': '0.2em'}))
        self.assertIn('text-shadow: var(--title2-shadow-dx) '
                      'var(--title2-shadow-dy) var(--title2-shadow-blur) '
                      'var(--title2-shadow-fg);', css)
        # And only that one: the twenty-nine others asked for nothing.
        self.assertEqual(css.count('text-shadow'), 1, css.count('text-shadow'))

    # Every component that sets `color` or `font-size` and has NO halo
    # axes, with the reason. Two kinds, and the distinction is the whole
    # rule: a CONTAINER would pass its halo to everything inside it, which
    # is a different instrument rather than a finer grain, and three
    # painters where a halo is a measured bad idea.
    NO_HALO = {
        'fact': 'container: reaches the code, tables and calls inside it',
        'footer': 'container: byline and licence line, each its own component',
        'cover': 'container: its h1, kicker, summary and number have their own',
        'quote': 'container: the paragraphs of the quotation',
        'note': 'container: its items, numbers and back-links',
        'note.local': 'container: the block that holds the list',
        'note.page': 'container: the end-of-page notes section',
        'table': 'container: heads, verdicts and cells have their own',
        'article': 'container: the long-form prose, its headings and code',
        'refs': 'container: the reference paragraphs it holds',
        'share': 'container: the popover, ink spread over four selectors',
        'intro': 'container: the paragraphs of the introduction',
        'code': 'fixed pitch at 0.88em: 2px of bleed on 1px stems',
        'footnote-call': 'the smallest glyph, and its job is to be findable',
    }

    def test_every_component_that_paints_glyphs_can_carry_a_halo(self):
        """The coverage statement B20 asked for, read off the registry
        rather than off a list written twice. A component that paints text
        either carries the axes or is named above with why — so a
        component added tomorrow lands in one column or fails here, and an
        exclusion outliving its component fails too."""
        haloed = {k.rsplit('.shadow.', 1)[0]
                  for k in self.lwp.PROPERTY_REGISTRY if '.shadow.' in k}
        painters = {c.key for c in self.lwp.THEME_COMPONENTS
                    if any(p.css in ('color', 'font-size') for p in c.props)}
        self.assertEqual(sorted(painters - haloed), sorted(self.NO_HALO),
                         'a component paints glyphs, carries no halo, and '
                         'nothing here says why')
        self.assertEqual(sorted(set(self.NO_HALO) - painters), [],
                         'an exclusion outlived the component it excused')
        for key, why in self.NO_HALO.items():
            self.assertGreaterEqual(len(why.split()), 4,
                                    f'{key}: the reason is not a reason')

    def test_the_worst_served_heading_is_the_one_that_gained_axes(self):
        """B20's own measurement, and why coverage was the gap rather than
        expressiveness: `page.shadow` is inherited, so its `em` resolves
        ONCE at the root and propagates as an absolute length — 0.13em is
        the same 2.1px on a 42px slide heading as on a 13px kicker. Blur
        over rendered size came out at 0.05 for the slide heading against
        0.26 for `h1`, worst of the whole table, and it is a heading. A
        halo is proportional to its glyph only where the component
        declares its own."""
        for key in ('title2.shadow.fg', 'title2.shadow.blur',
                    'title2.shadow.dx', 'title2.shadow.dy'):
            self.assertIn(key, self.lwp.PROPERTY_REGISTRY,
                          'the slide heading is the case B20 names')

    def test_a_composite_reads_a_hyphenated_key_back_exactly(self):
        """The var name a composite writes has to come back as the key that
        owns it, and turning hyphens into dots cannot do that: a key segment
        may itself contain a hyphen. `--nav-btn-shadow-fg` is
        `nav-btn.shadow.fg`, not `nav.btn.shadow.fg`, and the difference is
        not cosmetic — a key that misses the registry is a key whose default
        is never compared, and `omit_when_default` decides on that
        comparison."""
        reads = self.lwp.Composite(
            'text-shadow',
            'var(--nav-btn-shadow-dx) var(--highlight-caption-shadow-dy) '
            'var(--title2-shadow-fg)').reads()
        self.assertEqual(reads, ['nav-btn.shadow.dx',
                                 'highlight-caption.shadow.dy',
                                 'title2.shadow.fg'])
        for key in reads:
            self.assertIn(key, self.lwp.PROPERTY_REGISTRY)

    def test_every_composite_in_the_registry_reads_keys_that_exist(self):
        """Read off the shipped components rather than a sample: a composite
        whose value names a var nothing declares is a declaration built on a
        name, and nothing else would say so."""
        unresolved = [(c.key, comp.cssprop, key)
                      for c in self.lwp.THEME_COMPONENTS
                      for comp in c.composite
                      for key in comp.reads()
                      if key not in self.lwp.PROPERTY_REGISTRY]
        self.assertEqual(unresolved, [])

    def test_a_halo_asked_for_on_a_hyphenated_component_is_emitted(self):
        """What the exact reverse map buys, said in rendered CSS. Nine
        components carry a hyphen in the first segment of their key —
        `fact-label`, `nav-btn`, `series-nav.title` and six others — and for
        each of them a mistranslated var name would have made the halo
        unreachable: asked for in the theme, present in the :root block,
        and never once written into a rule."""
        for key in ('fact-label', 'nav-btn', 'series-nav.title',
                    'highlight-caption', 'body-heading', 'version-tag'):
            css = self.lwp.emit_theme_css(self.resolve({
                f'{key}.shadow.fg': '#33FF8880',
                f'{key}.shadow.blur': '0.2em'}))
            var = '--' + key.replace('.', '-') + '-shadow-fg'
            self.assertIn(f'text-shadow: var(', css, key)
            self.assertIn(f'{var});', css, f'{key}: halo asked for, not painted')

    def test_a_key_the_registry_does_not_know_is_never_at_its_default(self):
        """The failure direction that matters. `all()` over an empty set is
        True, so a name that resolves to nothing would report "everything is
        at its default" and drop the declaration — silently, and precisely
        where the code understood the least. Not knowing must mean emit."""
        resolved = self.resolve({})
        self.assertTrue(self.lwp._all_at_default(resolved,
                                                 ['title2.shadow.fg']))
        self.assertFalse(self.lwp._all_at_default(resolved, []))
        self.assertFalse(self.lwp._all_at_default(
            resolved, ['title2.shadow.fg', '--not-a-property']))

    def test_no_fixed_elevation_is_left_in_the_skeleton(self):
        """B12's coverage statement, and the one that cannot be satisfied
        by a list: the skeleton must not declare a `box-shadow` at all. A
        shadow left there is black at an alpha chosen against a white page,
        which on half the catalogue is not a shadow but nothing at all, and
        no theme can reach it. `transition: ... box-shadow ...` names the
        property without declaring it and stays.

        Every occurrence, not every line that starts with one: the
        skeleton is largely one-line rules — `.nav-btn:active`,
        `.tag-menu.open`, `h1` — so a shadow put back inside a brace would
        walk past a line-leading test untouched. Each occurrence is taken
        back to its enclosing declaration and has to be a transition."""
        skeleton = self.lwp.TEMPLATE_SKELETON
        found = []
        for m in re.finditer(r'box-shadow\s*:', skeleton):
            head = re.split(r'[;{}]', skeleton[:m.start()])[-1]
            if not head.lstrip().startswith('transition'):
                found.append(skeleton[m.start():m.start() + 60])
        self.assertEqual(found, [])

    # The thirteen declarations as the skeleton wrote them, transcribed
    # from the sheet before they moved (B12): selector, then offset-x,
    # offset-y, blur and the `rgba()` alpha. Written down here rather than
    # derived, because this is the one table in the change that must NOT
    # come from the code — it is the record of what the page used to
    # paint, and the whole claim of the migration is that nothing but the
    # alpha notation moved.
    ELEVATION_AS_THE_SHEET_WROTE_IT = {
        'fact.elevation':                    ('0', '1px', '8px',  0.06),
        'card.elevation':                    ('0', '1px', '8px',  0.06),
        'card.elevation-hover':              ('0', '4px', '16px', 0.10),
        'series-nav.link.elevation':         ('0', '2px', '12px', 0.08),
        'series-nav.link.elevation-hover':   ('0', '4px', '16px', 0.12),
        'nav-btn.elevation':                 ('0', '2px', '8px',  0.10),
        'nav-btn.elevation-hover':           ('0', '4px', '14px', 0.15),
        'slide-counter.elevation':           ('0', '1px', '6px',  0.10),
        'tag-menu.elevation':                ('0', '4px', '18px', 0.18),
        'share.elevation':                   ('0', '8px', '32px', 0.18),
        'presenter-panel.elevation':         ('0', '-4px', '22px', 0.20),
        'help-card.elevation':               ('0', '8px', '40px', 0.25),
        'share.qr.elevation':                ('0', '8px', '32px', 0.25),
    }

    def test_every_migrated_elevation_still_paints_what_it_painted(self):
        """The statement the render guard cannot make. It names the
        `--*-elevation-*` lines as added, and `strip_added()` runs over
        both pages, so their VALUES are invisible to it: every one of the
        thirteen could be changed to anything at all and the whole suite
        would stay green. Found by mutating all ten components to garbage
        and watching 868 tests pass.

        Geometry byte for byte, alpha through the conversion the migration
        claims — `rgba(0,0,0,a)` to eight-digit hex, rounding half up as
        the rest of the registry rounds. `round()` is banker's rounding
        and would give 76 where the house gives 77, so the arithmetic is
        written out rather than borrowed."""
        resolved = self.resolve({})
        for key, (dx, dy, blur, alpha) in \
                self.ELEVATION_AS_THE_SHEET_WROTE_IT.items():
            self.assertEqual(resolved[f'{key}.dx'], dx, key)
            self.assertEqual(resolved[f'{key}.dy'], dy, key)
            self.assertEqual(resolved[f'{key}.blur'], blur, key)
            self.assertEqual(resolved[f'{key}.spread'], '0', key)
            byte = int(alpha * 255 + 0.5)
            self.assertEqual(resolved[f'{key}.fg'],
                             '#000000%02X' % byte, key)

    def test_the_migrated_table_covers_every_elevation_and_no_more(self):
        """So the table above cannot quietly stop covering a component,
        which is how a transcription record turns into decoration."""
        declared = {f'{k}.{g}'
                    for k, (_rest, hover) in
                    self.lwp.ELEVATION_COMPONENTS.items()
                    for g in (('elevation', 'elevation-hover') if hover
                              else ('elevation',))}
        self.assertEqual(sorted(self.ELEVATION_AS_THE_SHEET_WROTE_IT),
                         sorted(declared))

    def test_every_elevation_carries_all_five_axes(self):
        """Five, not the three the sheet used. `dx` because a shadow could
        only be cast downward, which nobody decided, and `spread` because a
        ring or a soft lift is not expressible without it — both default to
        `0`, so the neutral elevation is still the one the sheet drew."""
        for key, (_rest, hover) in self.lwp.ELEVATION_COMPONENTS.items():
            groups = ['elevation'] + (['elevation-hover'] if hover else [])
            for group in groups:
                for axis in ('fg', 'blur', 'dx', 'dy', 'spread'):
                    self.assertIn(f'{key}.{group}.{axis}',
                                  self.lwp.PROPERTY_REGISTRY)

    def test_an_elevation_is_emitted_even_when_nobody_asked_for_one(self):
        """The halo's opposite, and the reason `omit_when_default` is not
        set here. `text-shadow` is inherited, so emitting it at its default
        blocks what the page set; `box-shadow` is not, so emitting it at
        its default paints nothing and blocks nothing. Always emitting is
        what puts the declaration at a stable specificity for `custom.css`
        to override."""
        css = self.lwp.emit_theme_css(self.resolve({}))
        self.assertEqual(
            css.count('box-shadow: var('), 13,
            'the thirteen elevations are not all in the sheet')

    def test_a_theme_can_lift_a_card_and_the_sheet_says_so(self):
        css = self.lwp.emit_theme_css(self.resolve({
            'card.elevation.fg': '#123456AA',
            'card.elevation.spread': '3px'}))
        self.assertIn('--card-elevation-fg: #123456AA;', css)
        self.assertIn('--card-elevation-spread: 3px;', css)
        self.assertIn('box-shadow: var(--card-elevation-dx) '
                      'var(--card-elevation-dy) var(--card-elevation-blur) '
                      'var(--card-elevation-spread) '
                      'var(--card-elevation-fg);', css)

    # Every elevation and the selector it must land on, read off the sheet
    # the skeleton used to carry. The whole table rather than a sample,
    # because the render guard cannot make this statement: a declaration
    # named as moving takes its braces with it, so a rule the engine opens
    # for one elevation alone can change selector there unnoticed.
    ELEVATION_SELECTORS = {
        'fact.elevation': '.fact-box',
        'card.elevation': '.article-card',
        'card.elevation-hover': '.article-card:hover',
        'series-nav.link.elevation': '.series-link',
        # The whole state, not half of it: `.series-link` lifts on focus as
        # well as on hover, and losing that would be a keyboard regression
        # dressed as a refactor.
        'series-nav.link.elevation-hover':
            '.series-link:hover, .series-link:focus-visible',
        'nav-btn.elevation': '.nav-btn',
        'nav-btn.elevation-hover': '.nav-btn:hover',
        'slide-counter.elevation': '.slide-counter',
        'tag-menu.elevation': '.tag-menu',
        'share.elevation': '.share-popover',
        'presenter-panel.elevation': '.presenter-panel',
        'help-card.elevation': '.help-card',
        'share.qr.elevation': '.share-qr-modal-content',
    }

    def test_every_elevation_lands_on_the_selector_it_belongs_to(self):
        css = self.lwp.emit_theme_css(self.resolve({}))
        rules = {}
        for block in css.split('}'):
            if '{' not in block:
                continue
            selector, body = block.rsplit('{', 1)
            rules.setdefault(selector.strip().split('\n')[-1].strip(),
                             []).extend(body.strip().split('\n'))
        found = {}
        for selector, decls in rules.items():
            for decl in decls:
                m = re.match(r'box-shadow: var\(--(.+?)-dx\)', decl.strip())
                if m:
                    found[m.group(1)] = selector
        self.assertEqual(
            found,
            {self.lwp.PROPERTY_REGISTRY[f'{k}.dx'].var[2:-3]: sel
             for k, sel in self.ELEVATION_SELECTORS.items()})

    def test_selector_overrides_land_on_their_own_selector(self):
        # One component, several selectors: the fact ground on .fact-box, its
        # ink on .fact-content; states and contexts likewise.
        css = self.lwp.emit_theme_css(self.resolve({}))
        self.assertIn('.fact-content {\n  color: var(--fact-fg);', css)
        self.assertIn('.nav-dots a.active {\n  background: var(--nav-dot-bg-active);', css)
        self.assertIn('.slide-cover h1 {\n  color: var(--title1-fg);', css)

    def test_flat_fill_is_a_gradient_with_equal_stops(self):
        r = self.resolve({})
        self.assertEqual(r['cover.bg.from'], r['cover.bg.to'])

    def test_unknown_key_is_a_named_error_with_a_suggestion(self):
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve({'summary.color': '#000000'})
        self.assertIn('summary.color', str(ctx.exception))

    def test_weight_beyond_normal_and_bold_is_rejected_with_the_reason(self):
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve({'kicker.weight': '600'})
        self.assertIn('normal|bold', str(ctx.exception))
        self.assertIn('generic', str(ctx.exception))

    def test_font_stack_must_end_on_a_generic(self):
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve({'font.text': '"Helvetica Neue", Helvetica'})
        self.assertIn('generic family', str(ctx.exception))

    def test_line_height_rejects_a_length(self):
        # 1.5 inherits as a factor; 1.5rem inherits as a fixed length and
        # breaks when a child changes font-size. The type says so.
        with self.assertRaises(self.lwp.PropertyError):
            self.resolve({'summary.leading': '1.5rem'})

    def test_reference_cycle_is_named_with_its_chain(self):
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve({'kicker.fg': 'summary.fg', 'summary.fg': 'kicker.fg'})
        self.assertIn('cycle', str(ctx.exception))
        self.assertIn('kicker.fg -> summary.fg -> kicker.fg', str(ctx.exception))

    def test_reference_chain_capped_at_three_hops(self):
        layer = {'kicker.fg': 'summary.fg', 'summary.fg': 'highlight.fg',
                 'highlight.fg': 'ink-quiet', 'color.ink-quiet': 'ink'}
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve(layer)
        self.assertIn('3 hops', str(ctx.exception))

    def test_colours_normalise_to_argb(self):
        r = self.resolve({'color.page': '#abc',
                          'summary.fg': '#11223344',
                          'kicker.fg': 'transparent'})
        self.assertEqual(r['color.page'], '#AABBCCFF')
        self.assertEqual(r['summary.fg'], '#11223344')
        self.assertEqual(r['kicker.fg'], '#00000000')

    def test_emitted_rules_read_only_component_properties(self):
        # G1: outside :root, no rule touches a shared value directly — the
        # 61 direct palette bindings are what this forbids.
        css = self.lwp.emit_theme_css(self.resolve({}))
        rules = css[css.index('}') + 1:]
        self.assertNotIn('var(--color-', rules)
        self.assertNotIn('var(--font-', rules)

    def test_every_catalogue_theme_resolves_and_emits(self):
        # The whole catalogue goes through the converter, the cascade and
        # emission without an error — every theme, no exception is the test.
        for slug in self.lwp.THEMES:
            layer = self.lwp.theme_property_layer(slug)
            self.lwp.emit_theme_css(self.resolve(layer))

    def test_dark_theme_inverts_furniture_light_theme_keeps_defaults(self):
        # What dark_background switched behind the theme's back, the layer
        # now says: white veils on terminal, registry defaults on nord.
        dark = self.resolve(self.lwp.theme_property_layer('terminal'))
        light = self.resolve(self.lwp.theme_property_layer('nord'))
        self.assertEqual(dark['fact.bg'], '#FFFFFF0E')
        self.assertEqual(light['fact.bg'], '#FFFFFFB8')
        self.assertEqual(dark['cover.fg'], dark['color.ink'])
        self.assertEqual(light['cover.fg'], light['color.page'])
        # the measured 0.78 follows the actual palette on both polarities
        self.assertEqual(dark['cover.summary.fg'], dark['color.ink'][:7] + 'C7')
        self.assertEqual(light['cover.summary.fg'], light['color.page'][:7] + 'C7')

    def test_terminal_port_carries_register_and_halo(self):
        r = self.resolve(self.lwp.theme_property_layer('terminal'))
        self.assertIn('monospace', r['page.font'])
        self.assertIn('monospace', r['title1.font'])
        self.assertEqual(r['title1.shadow.fg'], '#33FF8866')
        # bold on the bright mark ground takes the dark page ink
        self.assertEqual(r['fact.strong.fg'], r['color.page'])

    def test_the_skeleton_references_only_the_measure(self):
        # The completeness rule made mechanical. It used to run at every
        # extraction, on a sheet derived from a constant; the skeleton is
        # now the constant, so the same rule is a plain read of it. A
        # var() here other than the measure is a visual decision the
        # registry does not expose — B14 step 2 keeps this guard precisely
        # because the dynamic one went away.
        #
        # Stronger than it was: the measure used to be --content-max, a
        # variable the skeleton declared for itself and no layer could
        # reach (B13's "the one themeless variable"). It is now an ordinary
        # length property, so this test can also insist the one var it
        # tolerates is BACKED by the registry — a typo would previously
        # have produced a silently unset width.
        # Two layout tokens, and only two: the prose measure and the width
        # of the boxes that are not prose. Both must be registry-backed —
        # before B13 the skeleton declared its own, which no layer could
        # reach and no audit could see retire.
        allowed = {'--page-content-max', '--page-block-max'}
        for line in self.lwp.TEMPLATE_SKELETON.splitlines():
            for var in re.findall(r'var\((--[a-z-]+)', line):
                self.assertIn(var, allowed, f'skeleton references {var}')
        for key in ('page.content-max', 'page.block-max'):
            self.assertIn(key, self.lwp.PROPERTY_REGISTRY)
            self.assertIn(self.lwp.PROPERTY_REGISTRY[key].var, allowed)
            # And declared nowhere in the skeleton: the engine owns them.
            self.assertNotIn(self.lwp.PROPERTY_REGISTRY[key].var + ':',
                             self.lwp.TEMPLATE_SKELETON)

    def test_the_skeleton_carries_no_content_colour(self):
        # Second half of the old gap check. Layout may paint depth (the
        # rgba box-shadows); a colour that content is read against would
        # survive theming, which is the whole defect the registry kills.
        css = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_SKELETON, flags=re.S)
        self.assertEqual(re.findall(r'#[0-9a-fA-F]{3,8}\b', css), [])
        for decl in re.findall(r'(?<![-\w])(?:color|background)'
                               r'(?:-color)?\s*:\s*([^;}]+)', css):
            self.assertIn(decl.strip(), ('inherit', 'none'), decl)

    def test_the_skeleton_and_the_registry_never_drive_the_same_thing(self):
        # The collision check that replaces extraction. Extraction removed
        # driven declarations mechanically, so a duplicate was impossible
        # by construction; the skeleton is hand-edited now, and a literal
        # re-added on a driven (selector, property) pair would fight the
        # engine across the cascade — the engine's rule comes FIRST, so at
        # equal specificity the stale literal silently wins.
        driven = set()
        for comp in self.lwp.THEME_COMPONENTS:
            for c in comp.composite:
                for sel in (c.selector or comp.selector).split(','):
                    driven.add((sel.strip(), c.cssprop))
            for prop in comp.props:
                if prop.css:
                    for sel in (prop.selector or comp.selector).split(','):
                        driven.add((sel.strip(), prop.css))
            if any(p.key.endswith('.mark') for p in comp.props):
                driven.add((comp.selector.strip() + '::before', 'content'))
        css = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_SKELETON, flags=re.S)
        collisions = []
        for block in re.finditer(r'([^{}@]+)\{([^{}]*)\}', css):
            selectors = [s.strip() for s in block.group(1).split(',')]
            for decl in block.group(2).split(';'):
                if ':' not in decl:
                    continue
                prop = decl.split(':', 1)[0].strip()
                for sel in selectors:
                    if (sel, prop) in driven:
                        collisions.append(f'{sel} {{ {prop} }}')
        self.assertEqual(collisions, [],
                         'the skeleton restates a declaration the engine drives')

    def test_skeleton_keeps_media_overrides_and_shorthand_styles(self):
        skeleton = self.lwp.TEMPLATE_SKELETON
        self.assertIn('@media (max-width: 600px)', skeleton)
        # border shorthands lost colour and width to the engine but keep
        # their style token, or every rule would silently vanish
        self.assertIn('border-bottom-style: solid', skeleton)
        self.assertIn('outline-style: solid', skeleton)

    def test_composed_sheet_is_engine_then_skeleton(self):
        # Order is load-bearing: the skeleton's @media overrides share
        # specificity with the engine's base values and must win by coming
        # later.
        full = self.lwp.compose_stylesheet(self.resolve({}))
        self.assertLess(full.index(':root'), full.index('@media'))
        self.assertLess(full.index('--kicker-fg:'), full.index('@media'))

    def test_emission_consumes_every_registered_component_property(self):
        # Completeness is structural: everything with a css= target appears
        # exactly as a var() consumer in the rules.
        resolved = self.resolve({})
        css = self.lwp.emit_theme_css(resolved)
        for comp in self.lwp.THEME_COMPONENTS:
            for prop in comp.props:
                if prop.css:
                    self.assertIn(f'var({prop.var})', css,
                                  f'{prop.key} declared but never consumed')


class AlignmentAxes(unittest.TestCase):
    """B7. Alignment is a property of a BLOCK, which is the whole reason it
    could not simply copy the font tags: an inline <span> cannot carry
    text-align. Layers 1-4 are identical to every other axis; only the
    instance layer differs, and it differs in syntax, not in principle."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def _sheet(self, **over):
        lwp = self.lwp
        return lwp.compose_stylesheet(lwp.resolve_theme_properties(
            lwp.theme_property_layer('nord'), over))

    def _emitted(self, **over):
        # The engine's own rules only. The skeleton's .align-justify class
        # carries hyphens unconditionally, which is correct there and would
        # mask what the registry did or did not emit.
        lwp = self.lwp
        return lwp.emit_theme_css(lwp.resolve_theme_properties(
            lwp.theme_property_layer('nord'), over))

    def test_the_layout_by_fiat_moved_into_the_registry(self):
        # These four were hard-coded in the sheet with no recourse: the key
        # figure centred (B4), table cells left, the caption centred. If a
        # future edit puts text-align back in the skeleton, the collision
        # test fires; this one checks the registry really took them over.
        for key, default in [('highlight.align', 'center'),
                             ('table.cell.align', 'left'),
                             ('table.head.align', 'left'),
                             ('caption.align', 'center')]:
            self.assertEqual(self.lwp.PROPERTY_REGISTRY[key].default, default)

    def test_the_key_figure_realigns_from_a_settings_layer(self):
        # B4's acceptance case, per series rather than per figure.
        self.assertIn('--highlight-align: right', self._sheet(**{
            'highlight.align': 'right'}))

    def test_alignment_sets_alignment_and_nothing_else(self):
        # `justify` used to drag `hyphens: auto` along. Breaking words at end
        # of line is a typographic decision of its own; it must not arrive as
        # a side effect of choosing an alignment.
        sheet = self._emitted(**{'article.align': 'justify'})
        block = sheet[sheet.index('.full-article p, .full-article ul'):]
        block = block[:block.index('}')]
        self.assertIn('text-align: var(--article-align);', block)
        self.assertNotIn('hyphens', block)

    def test_a_misspelt_alignment_is_a_named_build_error(self):
        with self.assertRaises(self.lwp.PropertyError) as cm:
            self._sheet(**{'summary.align': 'centre'})
        self.assertIn('summary.align', str(cm.exception))
        self.assertIn('centre', str(cm.exception))

    def test_the_block_tag_wraps_whole_paragraphs(self):
        html = self.lwp.convert_markdown(
            'Before.\n\n{align:center}\nOne.\n\nTwo.\n{/align}\n\nAfter.\n')
        self.assertIn('<div class="align-center">', html)
        self.assertIn('</div>', html)
        # Both paragraphs inside, neither of the outer ones.
        inside = html[html.index('align-center'):html.index('</div>')]
        self.assertIn('<p>One.</p>', inside)
        self.assertIn('<p>Two.</p>', inside)
        self.assertNotIn('Before.', inside)
        self.assertNotIn('After.', inside)

    def test_the_closer_is_not_swallowed_by_the_paragraph_above_it(self):
        # Found by rendering: a bare line break does not end a paragraph, so
        # the closer was absorbed as continuation text and the <div> never
        # closed. The regression is silent — valid-looking output, wrong
        # container — so it gets its own test.
        html = self.lwp.convert_markdown('{align:right}\nOnly line.\n{/align}\n')
        self.assertNotIn('{/align}', html)
        self.assertIn('</div>', html)

    def test_an_unknown_alignment_in_the_text_is_a_named_build_error(self):
        with self.assertRaises(self.lwp.PropertyError) as cm:
            self.lwp.convert_markdown('{align:middle}\nx\n{/align}\n')
        self.assertIn('block tag {align:middle}', str(cm.exception))

    def test_a_stray_closer_stays_literal_like_an_unclosed_inline_tag(self):
        html = self.lwp.convert_markdown('{/align}\n')
        self.assertIn('{/align}', html)
        self.assertNotIn('</div>', html)

    def test_the_block_classes_reach_the_children(self):
        # text-align is inherited, but a component that declares its own
        # beats what it inherits — so an author's local choice could never
        # win over the theme without the descendant selector. Whether that
        # selector actually WINS is AlignmentReachesWhatItWraps' job; this
        # only checks the arm exists at all.
        sheet = self._sheet()
        self.assertIn('.align-center.align-center *', sheet)
        self.assertIn('text-align: center;',
                      sheet[sheet.index('.align-center,'):])


class EverySixTypeRejectsWhatItMustReject(unittest.TestCase):
    """Every property type's rejection branch, exercised. Three of the six
    had none, and this is not a hypothetical gap: with the colour branch
    neutered the whole suite stays green, and two of the five unguarded
    types (font stack, length) turned out to be genuinely exploitable —
    both shipped stored XSS until they were closed. Two thirds of the
    registry is colour-typed; nothing pinned it."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_the_rejection_branch_of_every_type_is_load_bearing(self):
        lwp = self.lwp
        # One escape attempt per type, all shaped the same way: close the
        # declaration, close the sheet, open a script.
        ESCAPE = '} </style><script>alert(1)</script><style>x{'
        cases = [
            (lwp.PROP_COLOR,   '#000' + ESCAPE),
            (lwp.PROP_COLOR,   'rgb(0,0,0)'),
            (lwp.PROP_COLOR,   '#12345'),
            (lwp.PROP_ANGLE,   '0deg' + ESCAPE),
            (lwp.PROP_ANGLE,   '90'),
            (lwp.PROP_LENGTH,  '1px' + ESCAPE),
            (lwp.PROP_LENGTH,  '10furlong'),
            (lwp.PROP_RATIO,   '1.5px'),
            (lwp.PROP_WEIGHT,  '600'),
            (lwp.PROP_FONT,    'serif' + ESCAPE),
            (lwp.PROP_TEXT,    '"a' + ESCAPE),
        ]
        for prop, bad in cases:
            with self.assertRaises(lwp.PropertyError,
                                   msg=f'{prop.name} accepted {bad!r}'):
                prop.check('some.key', bad)

    def test_a_neutered_colour_check_would_ship_a_script(self):
        # States what the guard above is actually protecting, so a future
        # reader knows the cost of weakening it: the article layer reaches
        # the inlined <style>, and colour is what most of it is made of.
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp,
                '<!-- lwp:meta -->\npage_title: A\n'
                'style.color.mark: #000} </style><script>alert(1)</script>'
                '<style> x{\n---\n\nslug: r200\n# Cover\n\nsummary: s\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / 'public' / 'a.html').exists())


class EveryAttributeSinkEscapes(unittest.TestCase):
    """Four sinks share one threat — a value reaching an HTML attribute —
    and only two had a test. All four escapes are load-bearing on the real
    executable; the two untested ones survived mutation."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_a_quote_in_page_desc_cannot_leave_the_meta_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n'
                                 'page_desc: D" onx="1\n---\n\n'
                                 'slug: r227\n# Cover\n\nsummary: s\n')
            self.assertEqual(
                run('build', str(root), '--output', str(root / 'public')
                    ).returncode, 0)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('content="D&quot; onx=&quot;1"', html)

    def test_a_quote_in_a_code_fence_language_cannot_leave_the_class(self):
        # _CODE_FENCE_RE is ^```(\S*)$, so a quote does reach the attribute.
        html = self.lwp.convert_markdown('```py"onload="alert(1)\nx\n```\n')
        self.assertIn('class="language-py&quot;onload=&quot;alert(1)"', html)
        self.assertNotIn('onload="alert', html)


class TheGuideBuildsWithTheToolItDescribes(unittest.TestCase):
    """The guide describes a tool for making card decks backed by a
    long-form article, so it is one. Running the build here is what stops
    its examples from rotting: the long-form file IS GUIDE.md, assembled at
    build time rather than copied, so there is no second version to drift.

    It also means the guide exercises the components it names, which is
    how the deck's own `source:` line was found published as literal text —
    it sat after prose, tripping the one-way switch the guide documents two
    sections earlier."""

    def test_the_committed_guide_is_the_guide_the_tool_makes(self):
        """The guard `themes-gallery.html` has had all along and this
        did not. Both are generated artefacts committed to the repo;
        only one of them was compared to a fresh build, so `generated/guide/`
        drifted 184 CSS declarations behind the stylesheet — the halo
        and the elevation — while the whole suite stayed green. A dated
        audit even recorded that both were checked byte for byte, which
        was the sentence that made the drift invisible.

        The build is deterministic: two runs of `build_guide.py` produce
        identical bytes, which is what makes a byte comparison the right
        instrument rather than a flaky one."""
        root = Path(__file__).resolve().parent.parent
        script = root / 'tools' / 'build_guide.py'
        committed = root / 'generated' / 'guide'
        if not script.exists() or not committed.is_dir():
            self.skipTest('no build_guide.py or generated/guide in this checkout')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'guide'
            r = subprocess.run([sys.executable, str(script), '--output', str(out)],
                               capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for name in sorted(p.name for p in out.iterdir() if p.is_file()):
                self.assertEqual(
                    (committed / name).read_bytes(), (out / name).read_bytes(),
                    f'generated/guide/{name} is stale: re-run '
                    f'`python3 tools/build_guide.py`')

    def test_the_guide_builds_and_shows_what_it_names(self):
        root = Path(__file__).resolve().parent.parent
        script = root / 'tools' / 'build_guide.py'
        if not script.exists():
            self.skipTest('no build_guide.py in this checkout')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'guide'
            r = subprocess.run([sys.executable, str(script), '--output', str(out)],
                               capture_output=True, text=True, timeout=180)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            html = (out / 'guide.html').read_text(encoding='utf-8')

        # Every component the guide's own anatomy section names.
        for cls in ('slide slide-cover', 'slide full-article', 'fact-box',
                    'fact-label', 'highlight-figure', 'highlight-caption',
                    'source', 'series-list', 'comparison-table'):
            self.assertIn(f'class="{cls}"', html, f'{cls} missing from the guide')
        # And no field line published as prose, which is what a slide with
        # its fields after the text looks like.
        for field in ('source:', 'fact-label:', 'highlight:'):
            self.assertNotIn(f'<p>{field}', html,
                             f'{field} rendered as literal text')


class TheGalleryPanelStaysOnTheDecksOwnSideOfItsBreakpoint(unittest.TestCase):
    """A gallery panel is a real viewport with the real sheet in it, and
    the sheet turns at a width of its own. The panel used to be a fixed
    340px, safely below it; it now grows with the window so the gallery
    can use a wide screen instead of sitting in a 1474px column. That
    makes the two numbers a pair, and nothing but this test says so.

    Past the turn the gallery would still look fine -- which is the
    danger. Half the panels would render the desktop layout and half the
    mobile one, in the same page, and a gallery whose whole job is
    comparison would be comparing two different renderings."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_the_panel_never_grows_past_the_sheets_own_turn(self):
        head = self.lwp.TEMPLATE_THEMES_GALLERY_HEAD
        clamp = re.search(r'--gal-panel:\s*clamp\(([^;]+)\);', head)
        self.assertTrue(clamp, 'the panel width is no longer a clamp()')
        floor, _, ceiling = [p.strip() for p in
                             re.split(r',(?![^()]*\))', clamp.group(1))]
        turns = sorted(int(w) for w in re.findall(
            r'@media \(max-width:\s*(\d+)px\)', self.lwp.TEMPLATE_SKELETON))
        self.assertTrue(turns, 'the sheet has no width breakpoint -- wrong store')
        self.assertLess(int(ceiling.rstrip('px')), turns[0],
                        f'a panel of {ceiling} renders the desktop layout '
                        f'while a narrower one renders the mobile layout')
        # And the floor is the width the panels were composed against:
        # below it the note falls out of the card, which is the one thing
        # that panel exists to show.
        self.assertEqual(floor, '340px')

    def test_the_row_is_as_wide_as_the_four_panels_it_holds(self):
        """The wrap's max-width was the constant 1474px against a real sum
        of 1496px, so the fourth panel sat 22px behind a horizontal scroll
        on every row at every window size. Derived now, and the arithmetic
        has to keep agreeing with the boxes it adds up."""
        head = self.lwp.TEMPLATE_THEMES_GALLERY_HEAD

        def px(pattern):
            m = re.search(pattern, head, re.DOTALL)
            self.assertTrue(m, pattern)
            return [int(v) for v in re.findall(r'(\d+)px', m.group(1))]

        wrap_pad = px(r'\.wrap \{.*?padding:\s*([^;]+);')
        panels_pad = px(r'\.panels \{.*?padding:\s*([^;]+);')
        gap = px(r'\.panels \{.*?gap:\s*([^;]+);')[0]
        border = px(r'\.theme-row \{.*?border:\s*([^;]+)\s')[0]
        # padding: top sides bottom  ->  the sides are the second value.
        expected = (wrap_pad[1] * 2 + panels_pad[1] * 2 + border * 2 + gap * 3)
        stated = int(re.search(
            r'max-width:\s*calc\(var\(--gal-panel\) \* 4 \+ (\d+)px\)',
            head).group(1))
        self.assertEqual(stated, expected,
                         'the wrap does not add up to the four panels, the '
                         'three gutters and the two boxes around them')


class TheGalleryInTheRepoIsTheGalleryTheToolMakes(unittest.TestCase):
    """README says the gallery "can never drift from what install --theme
    actually applies". That is true of the generator and was not true of
    the committed copy, which is regenerated by hand — it happened to be
    in sync, and nothing kept it so."""

    def test_the_committed_gallery_is_byte_identical_to_a_fresh_one(self):
        repo_copy = (Path(__file__).resolve().parent.parent
                     / 'generated' / 'themes-gallery.html')
        if not repo_copy.exists():
            self.skipTest('no committed gallery in this checkout')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            self.assertEqual(
                out.read_bytes(), repo_copy.read_bytes(),
                'generated/themes-gallery.html is stale: re-run '
                '`lightwebpres theme gallery generated/themes-gallery.html`')


class TypedSurfaceCannotLeaveItsDeclaration(unittest.TestCase):
    """§9 claims the CSS-string axis is "the only one whose value travels
    untransformed, so the only one that must guard itself". That was false:
    two other types passed values through verbatim, and both reached the
    page's inlined <style> from an ARTICLE's meta block — the trust level
    the rewrite hardened everywhere else."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_no_diagnostic_is_printed_instead_of_logged(self):
        """B26. §2.4.1 puts error, warning, info and debug on stderr and
        the command's ANSWER on stdout, and `audit` ignored it for 26
        sites — every warning it raised itself.

        Survivable while audit was the only thing talking. It stopped
        being survivable in v0.37.0, when the rendering pass began
        raising warnings through `log()`, which obeys the rule: one run
        then split its findings across both streams, the editorial ones
        on stdout and the render-borne ones on stderr, with nothing
        saying so. Someone grepping stderr got half of them.

        Guarded on the SOURCE rather than on an output, because the
        defect is the site and not the run: a `print()` of a diagnostic
        added tomorrow is caught tomorrow, on any code path, including
        ones no test exercises. `log()` is the funnel and the only way
        out."""
        source = (Path(__file__).resolve().parent.parent
                  / 'lightwebpres').read_text(encoding='utf-8')
        tags = ('[WARNING]', '[ERROR]', '[INFO]', '[DEBUG]')
        offenders = []
        for i, line in enumerate(source.split('\n'), 1):
            stripped = line.strip()
            if not stripped.startswith(('print(', "print(f'", 'print("')):
                continue
            if any(tag in line for tag in tags):
                offenders.append(f'{i}: {stripped[:78]}')
        self.assertEqual(
            offenders, [],
            'a diagnostic printed instead of logged — it lands on stdout, '
            'where §2.4.1 puts the command\'s answer, and the collector '
            'that feeds `--strict` never sees it:\n' + '\n'.join(offenders))

    def test_auto_is_refused_on_every_length_because_it_fits_none_of_them(self):
        """B31. `auto` validated, resolved and emitted, and no browser
        parses what came out.

        `card.elevation.dx: auto` produced `box-shadow: auto 1px 8px 0
        #0000000F`, an unparseable declaration, so the card lost its
        shadow entirely — no build error, no `audit` warning, nothing in
        `theme show`. A value that survives every check the tool makes
        and dies in the renderer is the failure mode typing exists to
        prevent, on the one axis where nothing was checking.

        The entry expected a narrower type for the axes where `auto` is
        meaningless. Swept, the registry says there are no others: all
        212 length properties reach a CSS context that refuses it —
        shadow offsets, blurs and spreads, font sizes, border and ring
        widths, tracking, padding, and the two max-widths, whose keyword
        is `none`. Nothing defaulted to it and no built-in theme resolved
        to it. So it is not a type that was missing, it is one value that
        never belonged.

        Asserted over the WHOLE registry rather than on a sample: the
        entry's own history is that the hole was found on one axis and
        was open on sixty-five."""
        lengths = [k for k, p in self.lwp.PROPERTY_REGISTRY.items()
                   if p.type.name == 'length']
        self.assertGreater(len(lengths), 100, 'the sweep found no lengths')
        for key in lengths:
            with self.assertRaises(self.lwp.PropertyError, msg=key):
                self.lwp.resolve_theme_properties({key: 'auto'})
        # And the message says why, because someone wrote it on purpose.
        with self.assertRaises(self.lwp.PropertyError) as caught:
            self.lwp.resolve_theme_properties({'card.elevation.dx': 'auto'})
        self.assertIn('`auto` is not a length here', str(caught.exception))
        self.assertIn('Write `0` for none', str(caught.exception))
        # What a length legitimately is still passes, on the same axes.
        self.lwp.resolve_theme_properties({
            'card.elevation.dx': '0', 'title1.shadow.blur': '0.2em',
            'page.content-max': 'clamp(20rem, 60vw, 50ch)',
            'kicker.tracking': '2.5px'})

    def test_a_font_stack_cannot_carry_anything_but_family_names(self):
        # Checking only the LAST component let a payload ending on a generic
        # through: `</style><script>x</script><style>y, sans-serif`.
        for bad in ('</style><script>alert(1)</script><style>x, sans-serif',
                    'Charter, "Bad;Font", serif',
                    'a{}, serif',
                    'a/*, serif'):
            with self.assertRaises(self.lwp.PropertyError, msg=bad):
                self.lwp.PROP_FONT.check('font.text', bad)

    def test_a_length_function_body_is_validated_not_just_its_prefix(self):
        # Inspecting the five-character prefix let `calc(0px)} </style>…` out
        # of the declaration and out of the sheet.
        for bad in ('calc(0px)} </style><script>x</script><style>z{q:r',
                    'clamp(1px, 2vw"3px)',
                    'min(1px'):
            with self.assertRaises(self.lwp.PropertyError, msg=bad):
                self.lwp.PROP_LENGTH.check('page.content-max', bad)

    def test_the_values_the_engine_itself_ships_still_pass(self):
        # A guard that rejects the defaults would be caught by every other
        # test; a guard that rejects an author's legitimate stack would not.
        for good in ("Charter, 'Bitstream Charter', Georgia, serif",
                     'ui-monospace, Menlo, monospace', 'serif'):
            self.assertEqual(self.lwp.PROP_FONT.check('font.text', good), good)
        for good in ('clamp(28px, 4.5vmin, 52px)', 'min(84vw, 1100px)', '50ch'):
            self.assertEqual(self.lwp.PROP_LENGTH.check('x', good), good)

    def test_a_poisoned_article_property_stops_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp,
                '<!-- lwp:meta -->\npage_title: A\n'
                'style.font.text: </style><script>alert(1)</script>'
                '<style>x, sans-serif\n---\n\nslug: r201\n# Cover\n\nsummary: s\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / 'public' / 'a.html').exists())


class QuadraticInputIsNotAcceptedAsSlow(unittest.TestCase):
    """Three patterns fed by article text were O(n²) — measured 4x per
    doubling, 16s on 60kB, and in the browser GUI that freezes the tab. The
    meta one billed its cost BEFORE deciding the file was invalid."""

    BUDGET = 2.0   # generous: the fixed versions run in milliseconds

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def _under_budget(self, fn, label):
        start = time.time()
        fn()
        elapsed = time.time() - start
        self.assertLess(elapsed, self.BUDGET, f'{label}: {elapsed:.1f}s')

    def test_unterminated_image_openers(self):
        self._under_budget(lambda: self.lwp.md_inline('![a](x' * 10000),
                           'inline image')

    def test_unterminated_link_openers(self):
        self._under_budget(lambda: self.lwp.md_inline('[a](https://' * 10000),
                           'markdown link')

    def test_repeated_meta_markers_with_no_terminator(self):
        text = '<!-- lwp:meta -->\n' * 4000 + 'x' * 160000
        self._under_budget(
            lambda: self.lwp.parse_markdown_extended(text), 'meta block')


class TemplatesAndSourcesStayInsideTheSeries(unittest.TestCase):
    """A symlink is not a path traversal, and the name-shape check does not
    see it. custom.css is published verbatim into every page, so a link
    there turns a build into a read primitive on anything the build user can
    open — a CI env file, an ssh key, .git-credentials."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_a_symlinked_custom_css_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / 'hostsecret.txt'
            secret.write_text('HOSTSECRET=hunter2', encoding='utf-8')
            run('init', tmp, '--force')
            root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                                 '# Cover\n\nsummary: s\n')
            custom = root / 'templates' / 'custom.css'
            custom.unlink(missing_ok=True)
            custom.symlink_to(secret)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertIn('custom.css', result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_a_symlinked_page_source_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / 'outside'
            outside.mkdir()
            (outside / 'secret.md').write_text(
                '<!-- lwp:meta -->\npage_title: S\n---\n\n'
                '# Cover\n\nsummary: sk-live-LEAKED\n', encoding='utf-8')
            run('init', tmp, '--force')
            root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                                 '# Cover\n\nsummary: s\n')
            (root / 'sources' / 'leak.md').symlink_to(outside / 'secret.md')
            data = json.loads((root / 'series.json').read_text())
            data['articles'].append({'page_dest': 'leak.html',
                                     'page_source': 'leak.md',
                                     'nav_title': 'L', 'nav_desc': 'L'})
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / 'public' / 'leak.html').exists())


class ANotePropertyMustReachTheNotesItNames(unittest.TestCase):
    """A theme axis that is emitted but loses is worse than one that does
    not exist: `settings.conf` lists it, `audit` counts it, and it does
    nothing.

    `note.size` shipped exactly that way. `article.size` drives
    `.full-article ol` at (0,1,1), which beat a plain `.note-body` at
    (0,1,0), so the axis was inert on the notes at the foot of the
    long-form article — where the DEFAULT placement puts them. Declared
    14px, computed 15px, and the same rule was giving the block a 24px
    indent it never asked for.

    Whether one selector beats another is only answerable against real
    markup — `.fact-content h2` outranks `.note-back` on paper and can
    never select it — so the "does it land" half of this lives in
    tests/test_web.py, where a browser resolves it. What stays here is
    the SCALE, which is a decision rather than a resolution."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_a_note_at_the_foot_of_a_unit_is_smaller_than_one_in_its_own_section(self):
        # The measured scale a card already has: body 15px, `source` and
        # `fact-label` 12px. A note at `note.size` came out at 93% of the
        # body it annotates, and larger than the `.refs` block that is the
        # same role three lines below it in the same article. Both now sit
        # at 12px, which is the FLOOR of the whole design -- nothing among
        # the 244 properties is smaller -- so this also pins that nobody
        # goes below it looking for room.
        reg = self.lwp.PROPERTY_REGISTRY
        local = _floor_px(reg['note.local.size'].default)
        section = _floor_px(reg['note.size'].default)
        refs = _floor_px(reg['refs.size'].default)
        body = _floor_px(reg['article.size'].default)
        self.assertLess(local, section, 'a foot-of-unit note is not apparatus')
        self.assertEqual(local, refs,
                         'the two foot-of-unit apparatus blocks are two sizes')
        # The two blocks are one role: a theme that quietens its notes has
        # said it about its references too, rather than saying it twice.
        self.assertEqual(reg['refs.fg'].default, 'note.fg')
        self.assertLess(local, body)
        floor = min(_floor_px(p.default)
                    for p in reg.values()
                    if p.css == 'font-size' and isinstance(p.default, str)
                    and _floor_px(p.default) is not None)
        self.assertEqual(local, floor,
                         'a foot-of-unit note is at the design floor, not below it')
        # The ordering has to hold at both ends of the scale, not just at
        # the floor. Sizes read `max(floor, N vmin)`: a change that raises
        # one coefficient and not the other inverts the ranking on any
        # screen large enough for the coefficient to win, which is every
        # screen this is presented on.
        self.assertLess(_coefficient(reg['note.local.size'].default),
                        _coefficient(reg['note.size'].default),
                        'the ordering holds at the floor and inverts above it')

    def test_no_property_sets_a_size_below_the_twelve_pixel_floor(self):
        """12px is the design floor, and the test above only ties the
        foot-of-unit note to whatever the MINIMUM happens to be. If every
        size in the registry drifted down together the minimum would
        follow and that check would stay green while the floor was gone.
        This one states the number.

        Below 12px the reference -- the one thing this tool exists to make
        reachable -- becomes the smallest element on a card, under the card
        number and under the label. The floor is a decision, so it belongs
        somewhere a decision can fail rather than in a sentence."""
        reg = self.lwp.PROPERTY_REGISTRY
        sizes = {name: _floor_px(p.default)
                 for name, p in reg.items()
                 if p.css == 'font-size' and isinstance(p.default, str)
                 and _floor_px(p.default) is not None}
        # An empty measurement would make the assertion below vacuous, and
        # `css == 'font-size'` is exactly the kind of predicate a refactor
        # renames out from under a test.
        self.assertGreater(len(sizes), 20,
                           'no sized properties found -- the scan is broken, '
                           'not the design')
        below = {n: px for n, px in sizes.items() if px < 12}
        self.assertEqual(below, {},
                         'a property sets a size below the 12px design floor')

    def test_a_theme_that_resizes_its_notes_resizes_both(self):
        # high-contrast states a bigger note; its foot-of-unit note has to
        # follow, or the theme's one intent is honoured in one place only.
        seen = 0
        for slug, props in self.lwp.THEME_NOTE_PROPS.items():
            if 'note.size' in props:
                seen += 1
                self.assertIn('note.local.size', props,
                              f'{slug} resizes note.size but not note.local.size')
                self.assertLess(_floor_px(props['note.local.size']),
                                _floor_px(props['note.size']), slug)
                # A theme that restates a size restates a SCALE. Written in
                # bare px it pinned the note at 16px on a 4K screen whose
                # body text had reached 58px -- the theme's one intent,
                # a bigger note, inverted by the screen it was shown on.
                self.assertLess(_coefficient(props['note.local.size']),
                                _coefficient(props['note.size']), slug)
        # One theme resizes its notes, so the loop runs once; drop that one
        # pair of keys and the body never executes and the test still
        # passes. The counter is what makes the loop an assertion.
        self.assertGreater(seen, 0, 'no theme resizes its notes -- wrong store')

    def test_speaker_note_field_is_hidden_and_only_for_the_presenter(self):
        # A `note:` field is a SPEAKER note, distinct from a `[^x]` source
        # footnote: it is parsed but withheld from the slide the reader sees,
        # and only the presenter panel (key N) reads it back from the DOM.
        deck = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k244\nkicker: T\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide -->\nslug: k245\nkicker: One\n## First\n'
            'note: Say the 2020 figure aloud.\n\n'
            'A visible claim[^kwh].\n\n[^kwh]: Measured at 230 V.\n'
        )
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('<div class="speaker-note" hidden>Say the 2020 figure aloud.</div>', html)
        # Withheld from the slide: the speaker text appears exactly once,
        # inside the hidden .speaker-note, never double-rendered visibly:
        self.assertEqual(html.count('Say the 2020 figure aloud.'), 1)
        # Reader-facing source footnotes still render independently:
        self.assertIn('class="notes-local"', html)

    def test_speaker_note_field_supports_multiline(self):
        # `note:` may span several indented continuation lines, with an
        # indented blank line marking a paragraph break. The whole block is
        # one speaker note, withheld from the slide, shown only in the panel.
        deck = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k246\nkicker: One\n## First\n'
            'note: First line, spoken aloud.\n'
            '  Second line, on its own.\n'
            '  \n'
            '  Third line, after a paragraph break.\n'
            'A visible claim.\n'
        )
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn(
            '<div class="speaker-note" hidden>First line, spoken aloud.\n'
            'Second line, on its own.\n\n'
            'Third line, after a paragraph break.</div>', html)
        # The note text appears exactly once, only inside the hidden div:
        self.assertEqual(html.count('First line, spoken aloud.'), 1)
        self.assertEqual(html.count('Third line, after a paragraph break.'), 1)
        # And it is NOT part of the visible slide body:
        body = html.split('class="slide-body"', 1)[1]
        visible = re.sub(r'<div class="speaker-note" hidden>.*?</div>', '',
                         body, flags=re.S)
        self.assertNotIn('First line, spoken aloud.', visible)
        self.assertIn('A visible claim.', visible)

    def test_comment_field_supports_multiline_and_stays_hidden(self):
        # `comment:` (review note, GLOSSARY.md) also accepts indented
        # continuation; like always it is parsed but rendered nowhere.
        deck = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nslug: k247\nkicker: One\n## First\n'
            'comment: Review point one.\n  Review point two.\n'
            'A visible claim.\n'
        )
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        # Never reaches the page, no matter how many continuation lines:
        self.assertNotIn('Review point one.', html)
        self.assertNotIn('Review point two.', html)


class AlignmentReachesWhatItWraps(unittest.TestCase):
    """The instance layer has to WIN, not merely be emitted. Shipped once
    with a losing selector: the tag was inert on long-form prose -- the one
    place it exists for -- while its hyphens companion still landed, so a
    paragraph came out left-aligned and hyphenated. Measured in a browser."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()
        cls.sheet = cls.lwp.compose_stylesheet(
            cls.lwp.resolve_theme_properties(cls.lwp.theme_property_layer('nord')))

    @staticmethod
    def _specificity(selector):
        """(ids, classes+attrs+pseudo-classes, elements) — enough for this
        sheet, which uses no ids and no pseudo-elements in these rules."""
        ids = selector.count('#')
        classes = selector.count('.') + selector.count('[') + selector.count(':')
        elements = len([p for p in re.split(r'[\s>+~]+', selector.strip())
                        if p and not p[0] in '.#[:'])
        return (ids, classes, elements)

    def test_the_instance_arm_outranks_every_engine_rule_it_must_beat(self):
        # The engine's rules come first, so ties go to the skeleton -- but
        # `.full-article p` is (0,1,1) and beat a plain `.align-x *` at
        # (0,1,0). Compare against every selector the registry drives
        # text-align on, so a new align axis on a compound selector cannot
        # silently re-open the hole.
        driven = [p.selector or c.selector
                  for c in self.lwp.THEME_COMPONENTS for p in c.props
                  if p.css == 'text-align']
        self.assertTrue(driven)
        arm = self._specificity('.align-center.align-center *')
        for sel in driven:
            for simple in sel.split(','):
                self.assertGreater(
                    arm, self._specificity(simple),
                    f'.align-* would lose to {simple.strip()}')

    def test_no_arm_touches_hyphenation(self):
        # Re-aligning a block must not change whether its words break: that
        # is page.hyphens' business, and it is off unless asked for.
        for value in ('left', 'center', 'right', 'justify'):
            block = self.sheet[self.sheet.index(f'.align-{value},'):]
            self.assertNotIn('hyphens', block[:block.index('}')])


class WordsAreNeverBrokenUnlessAsked(unittest.TestCase):
    """Breaking words at end of line is off unless a layer names it. It
    shipped once tied to `justify`, so choosing an alignment silently turned
    it on — a typographic decision arriving as the side effect of another."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_no_theme_at_any_alignment_turns_word_breaking_on(self):
        # Swept over the whole catalogue rather than spot-checked: the defect
        # was that ONE value of ONE axis enabled it, which a spot check on
        # the defaults would never have seen.
        lwp = self.lwp
        for key in list(lwp.THEMES) + [None]:
            base = lwp.theme_property_layer(key) if key else {}
            for axis in ('article.align', 'summary.align', 'title1.align',
                         'highlight.align', 'table.cell.align'):
                sheet = lwp.compose_stylesheet(
                    lwp.resolve_theme_properties(base, {axis: 'justify'}))
                self.assertNotIn('hyphens: auto', sheet,
                                 f'{key or "defaults"} / {axis}')

    def test_the_axis_defaults_to_off_and_is_reachable(self):
        lwp = self.lwp
        self.assertEqual(lwp.PROPERTY_REGISTRY['page.hyphens'].default, 'manual')
        sheet = lwp.compose_stylesheet(
            lwp.resolve_theme_properties({}, {'page.hyphens': 'auto'}))
        self.assertIn('--page-hyphens: auto;', sheet)
        self.assertIn('hyphens: var(--page-hyphens);', sheet)

    def test_a_bad_value_is_a_named_error(self):
        with self.assertRaises(self.lwp.PropertyError) as cm:
            self.lwp.resolve_theme_properties({}, {'page.hyphens': 'oui'})
        self.assertIn('page.hyphens', str(cm.exception))


class BlockWidthIsNotAMeasure(unittest.TestCase):
    """A table, a code block or a figure is sized by what it holds, not by a
    count of characters in its own font. Pointing all seventeen consumers at
    the measure put a five-column table in 350px on a 1440px desktop."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def _rule(self, selector):
        sk = self.lwp.TEMPLATE_SKELETON
        i = sk.index(selector + ' {')
        return sk[i:sk.index('}', i)]

    def test_boxes_read_the_block_width_and_prose_reads_the_measure(self):
        self.assertEqual(
            self.lwp.PROPERTY_REGISTRY['page.block-max'].default,
            'min(84vw, max(1100px, 102vmin))')
        for box in ('pre', '.comparison-table', '.figure',
                    '.full-article table'):
            self.assertIn('var(--page-block-max)', self._rule(box), box)
        for prose in ('.summary', '.full-article p', '.intro'):
            self.assertIn('var(--page-content-max)', self._rule(prose), prose)

    def test_the_block_width_is_a_floor_and_not_a_ceiling(self):
        """1100px flat put a table with 41px text in 26 characters a line
        at 3840, once the type scales lost their own ceilings. The `max`
        is what keeps the box growing with the text inside it; a bare
        `min(84vw, 1100px)` is the shape this replaced."""
        d = self.lwp.PROPERTY_REGISTRY['page.block-max'].default
        self.assertIn('max(', d, 'the block width has a ceiling again')
        self.assertIn('vmin', d)

    def test_the_key_figure_is_centred_on_the_same_thing_as_the_text(self):
        """.highlight was the ONE centred box reading the block width, so
        its centre sat 256px left of every other component's at 1920 and
        1063px left at 3840 -- measured in a browser. A left-aligned box
        can be narrower and still share the column's left edge; a centred
        one cannot. It is also not a flex column any more: `align-items:
        center` made highlight.align inert, and setting it to `left`
        moved the figure by zero pixels."""
        rule = self._rule('.highlight')
        self.assertIn('var(--page-content-max)', rule)
        self.assertNotIn('var(--page-block-max)', rule)
        self.assertNotIn('display: flex', rule)
        self.assertNotIn('align-items', rule)


class EveryTypeSizeScalesWithTheScreen(unittest.TestCase):
    """A deck is presented full screen, so a size that does not scale
    shrinks -- relative to everything around it -- the bigger the screen
    gets. Eight sizes were given a scale and twenty-seven were not, which
    left the tag, the fact label, the key figure's caption and the slide
    number at their 1080p pixel values on a 4K display whose body text
    had more than doubled. Measured: tag/summary was 0.556 by design and
    had fallen to 0.206 at 3840."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()
        cls.sizes = {n: p.default for n, p in cls.lwp.PROPERTY_REGISTRY.items()
                     if getattr(p, 'css', None) == 'font-size'}

    def test_no_size_is_pinned_to_pixels(self):
        stuck = {n: d for n, d in self.sizes.items()
                 if 'vmin' not in d and not d.endswith('em')}
        self.assertEqual(stuck, {},
                         'these sizes stay put while the screen grows')
        self.assertGreater(len(self.sizes), 30, 'the size list moved')

    def test_a_theme_that_restates_a_size_restates_a_scale(self):
        """high-contrast is the only theme that resizes anything, and it
        did it in bare px -- so under that theme the notes it deliberately
        enlarges were the one part of the page that did not grow."""
        seen = 0
        for slug, props in self.lwp.THEME_NOTE_PROPS.items():
            for key, value in props.items():
                if key.endswith('.size'):
                    seen += 1
                    self.assertIn('vmin', value, f'{slug} {key}')
        self.assertGreater(seen, 0, 'no theme restates a size -- wrong store')

    def test_a_halo_is_drawn_against_the_glyph_it_surrounds(self):
        """A glow and a marker box are both sized by the text they sit
        on, so both scale with it. terminal is the one theme with a glow
        and it stated 10px flat -- around a 51px title at 1080p and the
        same 10px around a 132px one at 3840, which is the theme's single
        visual idea gone on the screen a deck is shown on.

        Both halo lengths are checked, not just the blur. `dy` was used by
        no theme at all when this guard was written, so it could be added
        later as a flat px and the guard would not have noticed -- and the
        two light-family themes that carry a drop shadow rather than a glow
        are exactly the ones whose offset is the visible part.

        `em` counts as well as `vmin`, and is the better of the two: it
        resolves against the glyph's OWN size rather than the viewport's,
        so one declaration gives every title the same ratio. Written in
        viewport units the same declaration gave the two h1 of one page
        0.70 and 1.21 of blur relative to their size; in `em` both read
        0.26."""
        seen = 0
        for store in (self.lwp.THEME_PROPERTY_OVERRIDES,
                      self.lwp.THEME_NOTE_PROPS,
                      self.lwp.DARK_FURNITURE_PROPS):
            for slug, props in store.items():
                if not isinstance(props, dict):
                    continue
                for key, value in props.items():
                    # `.shadow.` and not `.elevation.`: a text halo is
                    # drawn against the glyph and wants a length the glyph
                    # decides, while a box shadow is drawn against the box
                    # and stays in px. `dx` joined the axes with B20 and is
                    # here from the start, so it cannot repeat `dy`'s
                    # history — that one was used by no theme at all when
                    # this guard was written, and was added to it late.
                    if not any(key.endswith(f'.shadow.{axis}')
                               for axis in ('blur', 'dx', 'dy')):
                        continue
                    if str(value) in ('0', '0px'):
                        continue
                    seen += 1
                    self.assertTrue(
                        'vmin' in value or value.rstrip().endswith('em'),
                        f'{slug} {key}: {value!r} is a length the glyph '
                        f'does not decide')
        # A test that iterates the wrong store passes on an empty set. The
        # first version of this one read THEMES, which holds a theme's
        # label and palette rather than its property overrides, so it went
        # green against a glow still written as a flat 10px.
        self.assertGreater(seen, 0, 'no glow found -- wrong store')

    def test_the_marker_box_grows_with_the_run_it_marks(self):
        """The underline thickness, its offset and the mark's corner
        radius all scale with the type: they were measured against the
        descenders, the mark's lower edge and the glyph's edge, and a
        ratio measured once is only kept by scaling every side of it.
        The side padding is a pinnable property (fact.strong.pad),
        emitted by the engine — what stays in the skeleton is the
        radius and the two underline lengths."""
        sk = self.lwp.TEMPLATE_SKELETON
        i = sk.index('.fact-content strong {')
        rule = sk[i:sk.index('}', i)]
        for decl in ('border-radius',
                     'text-decoration-thickness', 'text-underline-offset'):
            line = [l for l in rule.splitlines() if l.strip().startswith(decl + ':')]
            self.assertTrue(line, decl)
            self.assertIn('vmin', line[0], decl)
            self.assertIn('max(', line[0], decl)

    def test_the_navigation_list_is_as_wide_as_the_card(self):
        """A flat 680px put the series-nav list at 42% of the column at
        1920 and 21% at 3840, against the left edge of a card whose
        heading ran the full width. That heading is the only other thing
        on the slide, so any narrower width is also a second centre."""
        sk = self.lwp.TEMPLATE_SKELETON
        i = sk.index('.series-list {')
        rule = sk[i:sk.index('}', i)]
        self.assertIn('var(--page-content-max)', rule)
        self.assertNotIn('680px', rule)

    def test_every_size_keeps_a_floor(self):
        """The floor is what leaves a phone untouched: below a smaller
        dimension of about 800px it wins, so a 375x667 screen renders as
        it did before any of this."""
        for name, d in self.sizes.items():
            if d.endswith('em'):
                continue
            self.assertIsNotNone(_floor_px(d), f'{name} = {d}')
            self.assertGreaterEqual(_floor_px(d), 12, name)


class BlockTagErrorContract(unittest.TestCase):
    """A well-formed tag with a bad value names itself; an unclosed one names
    itself too, because unlike an inline tag it leaves invalid HTML behind."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_the_type_decides_the_value_not_the_regex(self):
        # Matching only [a-z]+ made {align:CENTER} fail to match at all, so it
        # rendered as literal text instead of naming itself — the opposite of
        # what the inline tags do with a bad value.
        with self.assertRaises(self.lwp.PropertyError) as cm:
            self.lwp.convert_markdown('{align:CENTER}\nx\n{/align}\n')
        self.assertIn('CENTER', str(cm.exception))

    def test_surrounding_space_in_the_value_is_tolerated(self):
        html = self.lwp.convert_markdown('{align: center }\nx\n{/align}\n')
        self.assertIn('<div class="align-center">', html)

    def test_an_unclosed_opener_names_the_real_cause(self):
        # The §13 balance check does catch it, but it reports a mismatched
        # <div> to an author who wrote no raw HTML at all.
        with self.assertRaises(self.lwp.PropertyError) as cm:
            self.lwp.convert_markdown('{align:center}\nx\n')
        self.assertIn('unclosed', str(cm.exception))
        self.assertIn('{/align}', str(cm.exception))

    def test_the_length_type_accepts_the_units_the_engine_ships(self):
        # The defaults use vmin and svh; a type rejecting its own defaults'
        # units traps the first author who restates one.
        for unit in ('4vmin', '3vmax', '100svh', '50dvh'):
            self.assertEqual(self.lwp.PROP_LENGTH.check('title1.size', unit),
                             unit)


class ContentMeasure(unittest.TestCase):
    """B13. The measure is an ordinary length property, and the skeleton
    consumes it at every prose site. Numbers verified in a browser across
    fifteen viewports — see ETUDE-VIEWPORT.md."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_the_content_width_follows_the_display_area(self):
        # PROPORTIONAL, and with no ceiling: a built page is a deck, every
        # card is `min-height: 100vh`, and a deck shown full screen has to
        # use the screen. Measured at 3840px under the old 1100px ceiling:
        # the column was 29% of the width, with 22px body text.
        #
        # A `ch` cap was tried before that and reverted for a different
        # reason: a ch length inside a custom property resolves against the
        # CONSUMING element, so one declared value became a different pixel
        # width per component — about 800px on a 32px title, about 450px on
        # 18px body text — and the card lost its inner edge.
        default = self.lwp.PROPERTY_REGISTRY['page.content-max'].default
        self.assertEqual(default, '84vw')

    def test_the_type_scale_has_no_ceiling_either(self):
        # The column and the type have to be uncapped TOGETHER. Capping one
        # is what produces a bad page: a wider column alone lengthens every
        # line, bigger type alone shortens them. Only both moving by the same
        # factor leaves the characters per line where they were — measured
        # invariant from 1080p to 4K.
        #
        # The FLOOR stays: it is what governs a phone, where the cards are
        # already tight vertically (ETUDE-VIEWPORT.md §7 counted the ones
        # that overflow), and where a 35% larger type would put more of them
        # over. Measured at 375x667: byte for byte what it was.
        for key in ('title1.size', 'title2.size', 'summary.size', 'fact.size',
                    'header.title.size', 'header.subtitle.size',
                    'highlight.size', 'table.size'):
            default = self.lwp.PROPERTY_REGISTRY[key].default
            self.assertNotIn('clamp(', default,
                             f'{key} is capped again, so it stops growing on '
                             f'the screen this scale exists for')
            self.assertIn('vmin', default,
                          f'{key} has to answer to the smaller dimension, or '
                          f'rotating a phone changes the type size')

    def test_the_column_is_centred_in_the_card(self):
        # Measured at 1920px before this was fixed: 154px of margin on the
        # left of the card and 666px on the right. A source assertion, and
        # said to be one — what it can catch is a revert to a fixed `8vw`
        # pair, which is the shape the defect had.
        #
        # It reads --page-content-max on purpose: the padding that centres
        # the column has to be derived from the column's own width, or an
        # author who pins a different one gets it centred around the wrong
        # number. Pinning that here is what stops the two drifting apart.
        # Comments stripped first. This scanned the raw text and so read
        # the prose too, which is a trap this file has sprung before, on
        # the docstring that quotes `log('warning', ...)` as the mistake
        # to avoid: the rule that records a defect names the defect, and
        # a textual guard fails on the very sentence written to prevent
        # it. The declaration is what is under test, never the account of
        # it — the same reason the log-level scan walks the AST.
        skeleton = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_SKELETON,
                          flags=re.DOTALL)
        self.assertNotIn('padding: 60px 8vw;', skeleton,
                         'the card is back to a fixed side padding, which '
                         'leaves the column against the left edge on any '
                         'screen wider than the column')
        self.assertIn('(100% - var(--page-content-max)) / 2', skeleton,
                      'the centring must be computed from the column width, '
                      'not from a number repeated beside it')

    def test_the_prose_cap_resolves_to_one_width_for_every_component(self):
        # The regression this pins is not "a wrong number" — it is a cap in a
        # unit that resolves per element, which is invisible in the source and
        # obvious on screen. Any font-relative unit reintroduces it.
        default = self.lwp.PROPERTY_REGISTRY['page.content-max'].default
        for relative in ('ch', 'em', 'ex', 'cap', 'ic', 'lh'):
            self.assertNotRegex(
                default, rf'\d{relative}\b',
                f'{relative} resolves against the element that reads the '
                f'variable, so the title and the paragraph under it would get '
                f'different widths from one declared value')

    def test_every_prose_cap_reads_the_measure(self):
        # The article's own 800px cap was the worst offender and was not
        # even governed by the old variable.
        skeleton = self.lwp.TEMPLATE_SKELETON
        for stale in ('800px', '480px', '700px', '1100px'):
            self.assertNotIn(f'max-width: {stale}', skeleton)
        # WHICH selectors read which cap is BlockWidthIsNotAMeasure's job.
        # A bare count would let two prose caps migrate to the block width
        # and still pass — a proxy that can only produce a false green.
        self.assertIn('var(--page-content-max)', skeleton)

    def test_the_type_scale_follows_the_constraining_dimension(self):
        # On vw, rotating a phone shortens the viewport and simultaneously
        # ENLARGES the type. In portrait vmin is vw, so this changes nothing
        # there and only bites where it should.
        for key in ('title1.size', 'title2.size', 'summary.size',
                    'fact.size', 'table.size', 'highlight.size'):
            default = self.lwp.PROPERTY_REGISTRY[key].default
            self.assertIn('vmin', default, key)
            self.assertNotIn('vw', default, key)

    def test_a_height_breakpoint_exists_and_comes_last(self):
        # Every other breakpoint keys on width, which is why landscape went
        # unnoticed. And it must sit AFTER the rules it overrides: at equal
        # specificity the later rule wins, which is exactly how the share
        # popover's mobile overrides became dead (B15).
        skeleton = self.lwp.TEMPLATE_SKELETON
        at = skeleton.index('@media (max-height: 520px)')
        for base in ('.slide {', '.highlight {', '.fact-box {'):
            self.assertGreater(at, skeleton.index(base), base)
        # And genuinely last, stated as the invariant rather than checked
        # against the three characters that happened to follow it: any
        # later @media overrides it at equal specificity, which is exactly
        # how the share popover's mobile rules died (B15).
        self.assertEqual(at, skeleton.rindex('@media'))

    def test_the_small_screen_override_of_the_measure_is_gone(self):
        # It existed to claw characters back on a narrow screen; a measure
        # the 8vw padding already bounds does not need it.
        self.assertNotIn('calc(100vw - 48px)', self.lwp.TEMPLATE_SKELETON)


class ArticleStyleLayer(unittest.TestCase):
    """style.* meta keys — the article layer of the cascade (§9). One page
    recomposes over the same series layers; every other page and the index
    keep the series sheet. Same vocabulary, same types, same errors as
    settings.conf, named with the file they came from."""

    ARTICLE = ('<!-- lwp:meta -->\n'
               'page_title: A\n'
               '{style_lines}'
               '---\n\n'
               'slug: r220\n# Cover\n\nsummary: s\n')

    def _series(self, tmp, style_lines=''):
        # install first: it writes its own empty series.json, which would
        # bury the scaffold's article list if run second.
        run('init', tmp, '--force')
        return scaffold(tmp, self.ARTICLE.format(style_lines=style_lines))

    def test_style_meta_restyles_its_page_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'style.verdict.partial.fg: #8A4B00\n')
            self.assertEqual(run('build', str(root)).returncode, 0)
            page = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            index = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('--verdict-partial-fg: #8A4B00FF;', page)
            self.assertNotIn('#8A4B00', index)

    def test_page_layer_sits_on_top_of_theme_and_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'style.color.mark: #101010\n')
            run('series', 'theme', 'set', str(root), '--theme', 'nord')
            self.assertEqual(run('build', str(root)).returncode, 0)
            page = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # the page pins the mark; everything else is still nord
            self.assertIn('--color-mark: #101010FF;', page)
            self.assertIn('--color-page: #ECEFF4FF;', page)

    def test_a_bad_value_is_a_build_error_naming_the_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'style.kicker.weight: 600\n')
            result = run('build', str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn('a.md', result.stderr)
            self.assertIn('normal|bold', result.stderr)

    def test_an_unknown_property_is_a_build_error_naming_the_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, 'style.tag.color: #000000\n')
            result = run('build', str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn('a.md', result.stderr)
            self.assertIn('unknown property', result.stderr)


class InstanceTags(unittest.TestCase):
    """The fifth layer of the cascade: format-defined tags in article text,
    instance-scoped, same types as everywhere else. The compiler sees them,
    so a bad value is a named build error and audit can enumerate them —
    the visibility that makes literals acceptable at all."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_colour_literal_normalises_to_argb_inline(self):
        html = self.lwp.md_inline('a {color:#e8a33d}word{/color} b')
        self.assertIn('<span style="color:#E8A33DFF">word</span>', html)

    def test_bare_word_references_emit_the_guaranteed_var(self):
        html = self.lwp.md_inline('{color:mark}x{/color} {font:mono}y{/font}')
        self.assertIn('<span style="color:var(--color-mark)">x</span>', html)
        self.assertIn('<span style="font-family:var(--font-mono)">y</span>', html)

    def test_valueless_tags_cover_the_non_composing_axes(self):
        html = self.lwp.md_inline('{sc}a{/sc} {strike}b{/strike} {u}c{/u} {mono}d{/mono}')
        self.assertIn('font-variant:small-caps', html)
        self.assertIn('text-decoration:line-through', html)
        self.assertIn('text-decoration:underline', html)
        self.assertIn('font-family:var(--font-mono)', html)

    def test_tags_nest_and_keep_markdown_inside(self):
        html = self.lwp.md_inline('{color:call}**bold** and {sc}caps{/sc}{/color}')
        self.assertIn('<strong>bold</strong>', html)
        self.assertIn('font-variant:small-caps', html)
        self.assertIn('color:var(--color-call)', html)

    def test_a_bad_literal_is_a_named_error(self):
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.lwp.md_inline('{color:dark-grey}x{/color}')
        self.assertIn('{color:dark-grey}', str(ctx.exception))
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.lwp.md_inline('{font:Comic Sans}x{/font}')
        self.assertIn('generic', str(ctx.exception))

    def test_an_unclosed_tag_stays_visible_literal_text(self):
        html = self.lwp.md_inline('a {color:#fff}forgot to close')
        self.assertIn('{color:#fff}', html)
        self.assertNotIn('<span', html)

    def test_a_code_span_is_never_a_tag(self):
        html = self.lwp.md_inline('`{color:#fff}not a tag{/color}`')
        self.assertNotIn('<span', html)

    def test_a_bad_tag_in_a_real_article_names_its_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                                 'slug: r224\n# Cover\n\nsummary: s\n\n---\n\n'
                                 'slug: r225\n## S\n\nfact-label: F\n\n'
                                 'Un fait {color:rouge}mal{/color} balisé.\n')
            result = run('build', str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn('a.md', result.stderr)
            self.assertIn('{color:rouge}', result.stderr)

    def _series_with_long_form(self, tmp, article_body):
        """A deck whose full-article slide pulls in a long-form file — the
        surface both guards below used to miss."""
        run('init', tmp, '--force')
        root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                             'slug: r226\n# Cover\n\nsummary: s\n\n---\n\n'
                             '<!-- lwp:slide:full-article -->\nslug: k248\n'
                             'article: a_article.md\n')
        (root / 'sources' / 'a_article.md').write_text(
            article_body, encoding='utf-8')
        return root

    def test_a_bad_tag_in_the_long_form_file_names_that_file(self):
        # The deck path already named its source; the long-form file did not,
        # and it is where most of the prose lives. A bad tag there surfaced as
        # a bare Python traceback naming nothing the author could open.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_long_form(
                tmp, '## H\n\n{align:centre}\nx\n{/align}\n')
            result = run('build', str(root))
            self.assertEqual(result.returncode, 1)
            self.assertNotIn('Traceback', result.stderr)
            self.assertIn('a_article.md', result.stderr)
            self.assertIn('{align:centre}', result.stderr)

    def test_the_census_counts_the_long_form_file_and_the_align_tag(self):
        # Two holes, one cause: the census read page_source only, and its
        # alternation omitted `align`. Its stated purpose is telling an author
        # changing themes where to look, so both omissions defeated it.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_long_form(
                tmp, '## H\n\n{align:center}\nx\n{/align}\n\n'
                     'Un {sc}mot{/sc} et {color:mark}un autre{/color}.\n')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('3 instance tag(s)', result.stdout)
            self.assertIn('1 align', result.stdout)

    def test_audit_enumerates_instance_tags_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n---\n\n'
                                 '# Cover\n\nsummary: {color:#333}s{/color} '
                                 'et {sc}x{/sc}\n')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[NOTE] a.md: 2 instance tag(s)', result.stdout)


class InstanceAndArticleLayerSecurity(unittest.TestCase):
    """The audit's boundary findings, pinned. The article style.* layer and
    the instance tags are the one trust level the rewrite hardened; a value
    must never escape the inlined <style> or the href it sits in."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def _build(self, tmp, body='', meta_extra=''):
        run('init', tmp, '--force')
        scaffold(tmp, '<!-- lwp:meta -->\npage_title: A\n' + meta_extra +
                 '---\n\nslug: r202\n# Cover\n\nsummary: s\n\n---\n\n'
                 'slug: r202b\n## S\n\nfact-label: F\n\n' + body + '\n')
        return run('build', tmp)

    def test_a_verdict_mark_cannot_escape_the_inlined_style(self):
        # The only untyped axis was FreeTextType; a style.* meta key reached
        # it and shipped a raw </style><script> into the page.
        with tempfile.TemporaryDirectory() as tmp:
            r = self._build(tmp, meta_extra=(
                'style.verdict.yes.mark: "\\25CF"; } </style><script>'
                'alert(1)</script><style>{\n'))
            self.assertEqual(r.returncode, 1)
            self.assertIn('is not a CSS string', r.stderr)

    def test_a_well_formed_mark_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._build(tmp, meta_extra='style.verdict.yes.mark: "\\2714"\n')
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('--verdict-yes-mark: "\\2714";', page)

    def test_a_settings_mark_is_validated_too(self):
        r = self.lwp.PROP_TEXT
        with self.assertRaises(self.lwp.PropertyError):
            r.check('verdict.yes.mark', '"x"; } body { display: none } "')
        self.assertEqual(r.check('verdict.yes.mark', '"\\25CF"'), '"\\25CF"')
        self.assertEqual(r.check('verdict.yes.mark', 'none'), 'none')

    def test_an_instance_tag_in_a_link_url_cannot_inject_an_attribute(self):
        # The opening <a> is placeholder-protected, so a tag inside the URL
        # stays literal in the quoted href instead of becoming a <span> that
        # closes the attribute.
        with tempfile.TemporaryDirectory() as tmp:
            r = self._build(tmp, 'A [x](https://e.com/{color:#FFF} '
                                 'onload=alert(1) y{/color}) here.')
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            anchor = page.split('<a ')[1].split('</a>')[0]
            # the tag stays literal inside the quoted href — no span closing
            # the attribute, no onload leaking out as its own attribute
            self.assertNotIn('<span', anchor)
            self.assertNotIn('onload="', anchor)

    def test_a_tag_in_link_text_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._build(tmp, 'A [{sc}styled{/sc} label](https://e.com/p).')
            self.assertEqual(r.returncode, 0, r.stderr)
            page = (Path(tmp) / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('font-variant:small-caps', page)

    def test_a_pathological_tag_run_does_not_hang(self):
        # Brace-free content classes plus the depth cap bound what was a
        # measured 29 s on 40k unclosed openers.
        html = self.lwp.md_inline('{sc}' * 5000 + ' end')
        self.assertIn('{sc}', html)          # leftovers stay literal
        deep = self.lwp.md_inline('{color:call}' * 40 + 'x' + '{/color}' * 40)
        self.assertIn('x', deep)


class FactVariant(unittest.TestCase):
    """fact-variant names a MEANING in the source; what it looks like is the
    theme's or the author's to define (a .fact--<name> rule in custom.css),
    so a theme change carries the variant with it — the same contract as
    class="yes" on a table cell."""

    ARTICLE = ('<!-- lwp:meta -->\npage_title: A\n---\n\n'
               'slug: r222\n# Cover\n\nsummary: s\n\n---\n\n'
               'slug: r223\n## S\n\nfact-label: F\nfact-variant: {variant}\n\nBody.\n')

    def test_variant_becomes_a_class_hook(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp, self.ARTICLE.format(variant='warning'))
            self.assertEqual(run('build', str(root)).returncode, 0)
            page = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('class="fact-box fact--warning"', page)

    def test_an_invalid_variant_name_is_a_named_build_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            run('init', tmp, '--force')
            root = scaffold(tmp, self.ARTICLE.format(variant='Bad Name!'))
            result = run('build', str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn('a.md', result.stderr)
            self.assertIn('fact-variant', result.stderr)


class ANoteIsReachableOrItIsNotANote(unittest.TestCase):
    """What shipped under the name "footnotes" before this was a literal
    marker: `[^1]` became `<sup>[^1]</sup>` and the body became a
    paragraph starting with the same literal. No anchor, no link, no
    numbering. For a tool whose central use is the sourced article, a
    reference the reader cannot reach is a defect, so every test here is
    about REACHABILITY, not about looks."""

    DECK = (
        '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
        'nav_title: A\nnav_desc: A\n{extra}---\n\n'
        '<!-- lwp:slide:cover -->\nslug: k249\nkicker: T\n# Title\nsummary: S.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nslug: k250\nkicker: One\n## First\n\nfact-label: L\n\n'
        'A claim[^kwh] and the same source again[^kwh].\n\n'
        'A different one[^b].\n\n'
        '[^kwh]: Measured at 230 V.\n[^b]: A second body.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nslug: k251\nkicker: Two\n## Second\n\nfact-label: L\n\n'
        'A claim in the next card[^z].\n\n[^z]: Its own body.\n\n'
        '---\n\n'
        '<!-- lwp:slide:full-article -->\nslug: k252\narticle: art.md\n'
    )
    ARTICLE = ('# Long form\n\nOne[^p] and two[^q].\n\n'
               '[^p]: First.\n[^q]: Second.\n')

    def _build(self, extra='', article=None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, self.DECK.format(extra=extra))
        (root / 'sources' / 'art.md').write_text(
            self.ARTICLE if article is None else article, encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def _card_ids(self, html):
        """The cards' own ids, in document order.

        A note's locality is the card's IDENTITY (§12.1.1), not its rank,
        so these tests ask the page what its cards are called rather than
        assuming `sN`. That assumption is the very thing the identity work
        removed: inserting a card ahead of another used to move every note
        anchor after it, and a test that hard-codes the rank would go on
        passing through exactly that breakage."""
        return re.findall(r'<section class="[^"]*" id="([^"]+)"', html)

    def test_the_call_and_the_body_point_at_each_other(self):
        html = self._build()
        two = self._card_ids(html)[1]
        self.assertIn(f'<a id="noteref-{two}-1" href="#note-{two}-1" '
                      'role="doc-noteref">1</a>', html)
        self.assertIn(f'<li id="note-{two}-1" role="doc-footnote">', html)
        self.assertIn(f'href="#noteref-{two}-1" role="doc-backlink"', html)

    def test_the_authors_label_never_reaches_the_page(self):
        # The label is a key, not content: it can be anything, and
        # numbering is therefore not a rewrite of what the author wrote.
        html = self._build()
        for label in ('[^kwh]', '[^b]', '[^z]', '[^p]', '[^q]'):
            self.assertNotIn(label, html)

    def test_numbering_restarts_in_each_card_and_runs_on_in_the_article(self):
        # A card is individually shareable, so a reader can arrive at card
        # 5 having seen nothing else; a note numbered 7 there would send
        # them looking for six they will never find (specifications.md §6.5.2).
        html = self._build()
        two, three = self._card_ids(html)[1], self._card_ids(html)[2]
        self.assertIn(f'id="note-{two}-1"', html)
        self.assertIn(f'id="note-{two}-2"', html)
        self.assertIn(f'id="note-{three}-1"', html)   # next card, back to 1
        self.assertIn('id="note-article-1"', html)
        self.assertIn('id="note-article-2"', html)

    def test_every_id_in_the_page_is_unique(self):
        # This is the whole reason the displayed number is not the anchor
        # id. Two cards each carrying one note would otherwise emit two
        # id="note-1", and every return link would land on the wrong one.
        html = self._build()
        ids = re.findall(r'\bid="([^"]+)"', html)
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(dupes, [], f'duplicate ids: {dupes}')

    def test_one_label_called_twice_is_one_body_with_two_return_links(self):
        # Duplicating the body would give two numbers to one reference.
        html = self._build()
        two = self._card_ids(html)[1]
        self.assertEqual(html.count(f'id="note-{two}-1"'), 1)
        self.assertIn(f'href="#noteref-{two}-1" role="doc-backlink"', html)
        self.assertIn(f'href="#noteref-{two}-1-2" role="doc-backlink"', html)

    def test_local_is_the_default_and_bodies_stay_with_their_card(self):
        html = self._build()
        self.assertIn('class="notes-local"', html)
        self.assertNotIn('class="slide notes-section"', html)
        # The card's own block, inside the card's own section.
        two, three = self._card_ids(html)[1], self._card_ids(html)[2]
        card = html.split(f'id="{two}"', 1)[1].split('<section', 1)[0]
        self.assertIn(f'id="note-{two}-1"', card)
        self.assertIn(f'id="note-{two}-2"', card)
        self.assertNotIn(f'id="note-{three}-1"', card)

    def test_page_placement_collects_into_one_section_of_the_page(self):
        html = self._build(extra='notes_placement: page\n')
        self.assertIn('<section class="slide notes-section" id="notes" '
                      'role="doc-endnotes">', html)
        self.assertNotIn('class="notes-local"', html)
        # Continuous across the whole page, and endnotes rather than
        # footnotes now that they have been collected.
        for n in range(1, 6):
            self.assertIn(f'id="note-p-{n}"', html)
        self.assertIn('role="doc-endnote"', html)

    def test_a_call_can_precede_the_card_that_defines_its_body(self):
        # Only possible because a page-wide scope is numbered once the
        # whole page has been converted, not card by card.
        deck = self.DECK.format(extra='notes_placement: page\n').replace(
            '[^z]: Its own body.', '[^late]: Defined after it was called.')
        deck = deck.replace('A claim in the next card[^z].',
                            'A claim in the next card[^late].')
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        (root / 'sources' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('href="#note-p-3" role="doc-noteref"', html)
        self.assertIn('id="note-p-3"', html)

    def test_the_tooltip_is_off_by_default_and_is_never_the_only_carrier(self):
        # A tooltip does not exist on a touch screen, does not exist in
        # print, and is not in the reading order. The body is always in
        # the document; the tooltip only ever saves a jump.
        plain = self._build()
        self.assertNotIn('title="Measured at 230 V."', plain)
        withtip = self._build(extra='notes_tooltip: on\n')
        self.assertIn('title="Measured at 230 V."', withtip)
        self.assertIn(f'<li id="note-{self._card_ids(withtip)[1]}-1"', withtip)

    def test_placement_cascades_from_series_meta_and_the_article_wins(self):
        for meta_line, expected_section in (('', True), ('notes_placement: local\n', False)):
            tmp = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, tmp, True)
            root = scaffold(tmp, self.DECK.format(extra=meta_line))
            (root / 'sources' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data = {'series_meta': {'notes_placement': 'page'},
                    'articles': data['articles']}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertEqual('class="slide notes-section"' in html,
                             expected_section, meta_line or '(series only)')

    def test_an_unknown_placement_is_a_build_error_naming_the_article(self):
        # Falling back to the default would leave an author reading a page
        # that ignores what they asked for, with nothing to say why.
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, self.DECK.format(extra='notes_placement: sidebar\n'))
        (root / 'sources' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('a.md', result.stderr)
        self.assertIn('notes_placement', result.stderr)

    def test_a_call_inside_a_code_span_stays_literal(self):
        html = self._build(article='Write `[^1]` to call a note.\n')
        self.assertIn('<code>[^1]</code>', html)

    def test_a_source_cannot_forge_a_call_with_a_control_character(self):
        # md_inline() owns U+0000 and U+0002 as internal placeholders. A
        # source carrying one must not be able to mint a note that has no
        # body, nor to reach into the code-span table.
        deck = ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k253\nkicker: T\n# Title\nsummary: S.\n\n'
                '---\n\n<!-- lwp:slide:full-article -->\nslug: k254\narticle: art.md\n')
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        (root / 'sources' / 'art.md').write_text(
            'Text \x02kwh\x02 and \x001\x00 more.\n', encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
        # 'note-call' on its own is in the composed stylesheet of every
        # page; what must not appear is a rendered call.
        self.assertNotIn('<sup class="note-call">', html)
        self.assertIn('Text kwh and 1 more.', html)


class AResponsiveOverrideMustActuallyOverride(unittest.TestCase):
    """CSS breaks ties by source order, so a `@media` rule declared ABOVE
    the base rule it means to override loses at equal specificity and does
    nothing at all — silently, on the one viewport nobody develops at.

    `.share-popover`'s three phone declarations sat in that position and
    were dead: measured in Chromium at 375px the popover resolved to the
    desktop bottom/right/max-width, ignoring every value the media block
    asked for. The skeleton's own comment warned about source order; a
    comment is not a guard, so this is one."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    def test_no_media_declaration_is_overruled_by_a_later_base_rule(self):
        # Comments are blanked FIRST, in place, so offsets stay aligned:
        # the skeleton's own commentary says "@media" more than once, and
        # matching one of those mentions blanks a span of real rules and
        # makes this test pass by seeing nothing. (It did, until the fix
        # below was mutation-tested.)
        css = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)),
                     self.lwp.TEMPLATE_SKELETON, flags=re.S)
        # (selector, property) -> offset, for every declaration inside a
        # media block and every one outside it.
        in_media, base = [], []
        for m in re.finditer(r'@media[^{]*\{(.*?)\n\}', css, re.S):
            for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', m.group(1)):
                for sel in rule.group(1).split(','):
                    for decl in rule.group(2).split(';'):
                        if ':' in decl:
                            in_media.append((sel.strip(),
                                             decl.split(':', 1)[0].strip(),
                                             m.start()))
        # Everything that is NOT inside a media block, with its offset.
        stripped = re.sub(r'@media[^{]*\{.*?\n\}',
                          lambda m: ' ' * len(m.group(0)), css, flags=re.S)
        for rule in re.finditer(r'([^{}]+)\{([^{}]*)\}', stripped):
            for sel in rule.group(1).split(','):
                for decl in rule.group(2).split(';'):
                    if ':' in decl:
                        base.append((sel.strip(),
                                     decl.split(':', 1)[0].strip(),
                                     rule.start()))
        self.assertTrue(in_media, 'no media declarations found — the parse is wrong')
        dead = [(sel, prop) for sel, prop, at in in_media
                for bsel, bprop, bat in base
                if bsel == sel and bprop == prop and bat > at]
        self.assertEqual(sorted(set(dead)), [],
                         'declared in a @media block but overruled by a later '
                         'base rule of equal specificity: ' + repr(sorted(set(dead))))


class EveryNoteSurfaceIsMeasuredOnEveryThemeItShipsWith(unittest.TestCase):
    """Ten contrast constraints × every theme, measured from the RESOLVED
    sheet rather than from the intent.

    Two things this catches that a cheaper test would not. Membership in
    `DARK_FURNITURE_PROPS` is not enough — the notes plate and its rules
    were left out of it and shipped a near-opaque white slab carrying pale
    ink on all 18 dark themes, but a membership test would also pass the
    day someone adds a key with a value that does not work. And a call does
    not always sit on the card's ground: inside a highlighted run and on a
    cover it sits on two other ones, which is where `call` measured 1.00:1
    on tokyo-night — the number painted exactly its own background."""

    # EMPTY on purpose, and it stays as the only door an exemption may come
    # through. The set is exact rather than a floor: a new entry is a
    # regression, and a MISSING one means a palette was fixed and its
    # exemption has to leave with it. That is what happened to the last
    # occupant — catppuccin's `fact.strong.fg` at 3.05:1 on its own
    # highlight ground, which the palette's `color.mark` now clears at
    # 4.51:1 — and the mechanism is what pushed it out.
    KNOWN_PALETTE_FAILURES = set()

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    @staticmethod
    def _rgba(value):
        h = value.lstrip('#')
        h = h + 'FF' if len(h) == 6 else h
        return [int(h[i:i + 2], 16) for i in (0, 2, 4, 6)]

    @classmethod
    def _over(cls, fg, bg):
        a = fg[3] / 255
        return [round(fg[i] * a + bg[i] * (1 - a)) for i in range(3)] + [255]

    @staticmethod
    def _ratio(a, b):
        def lum(c):
            def ch(v):
                v /= 255
                return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
            return .2126 * ch(c[0]) + .7152 * ch(c[1]) + .0722 * ch(c[2])
        la, lb = lum(a), lum(b)
        return (max(la, lb) + .05) / (min(la, lb) + .05)

    def _checks(self, slug):
        """(name, foreground, grounds it may land on, floor) for one theme."""
        r = self.lwp.resolve_theme_properties(
            self.lwp.theme_property_layer(slug), {})
        page = self._rgba(r['color.page'])
        # A standard card has no ground of its own — getComputedStyle on
        # section.slide returns rgba(0,0,0,0) — so a note in a card sits
        # directly on color.page. Three grounds a body can land on, not two.
        card = page
        article = self._over(self._rgba(r['article.bg']), page)
        notes = self._over(self._rgba(r['note.page.bg']), page)
        marked = self._over(self._rgba(r['fact.strong.bg']),
                            self._over(self._rgba(r['fact.bg']), page))
        cover = self._over(self._rgba(r['cover.bg.from']), page)
        body = [card, article, notes]
        return r, page, [
            ('note.fg',               self._rgba(r['note.fg']),               body,     4.5),
            ('note.marker.fg',        self._rgba(r['note.marker.fg']),        body,     4.5),
            ('note.back.fg',          self._rgba(r['note.back.fg']),          body,     4.5),
            ('note.page.title.fg',    self._rgba(r['note.page.title.fg']),    [notes],  4.5),
            # `.refs` is the same role at the same size on the same page,
            # and it had never been measured: `ink-quiet` there was below
            # AA on 12 of 33 themes (solarized 2.61:1) before it was made
            # to track `note.fg`.
            ('refs.fg',               self._rgba(r['refs.fg']),               [article], 4.5),
            ('footnote-call.fg',      self._rgba(r['footnote-call.fg']),      [card, article], 4.5),
            ('footnote-call.fg-marked', self._rgba(r['footnote-call.fg-marked']), [marked], 4.5),
            ('footnote-call.fg-cover',  self._rgba(r['footnote-call.fg-cover']),  [cover],  4.5),
            ('note.local.rule-fg', self._over(self._rgba(r['note.local.rule-fg']), page), [page], 3.0),
            ('note.page.rule-fg',  self._over(self._rgba(r['note.page.rule-fg']),  page), [page], 3.0),
        ]

    def test_every_note_ink_clears_aa_and_every_rule_clears_three_to_one(self):
        failures = set()
        for slug in self.lwp.THEMES:
            _, _, checks = self._checks(slug)
            for name, fg, grounds, floor in checks:
                low = min(self._ratio(fg, g) for g in grounds)
                if round(low, 2) < floor:
                    failures.add((slug, name))
        self.assertEqual(
            failures, self.KNOWN_PALETTE_FAILURES,
            'the measured failures changed. New entries are regressions; a '
            'MISSING one means the palette was fixed and its exemption must '
            'go with it.')

    def test_a_dark_theme_never_paints_the_notes_plate_pale(self):
        # The plate departs from the page in the direction that has
        # headroom. On a dark theme that is upward, and it must stay a
        # raised ground rather than becoming a light slab in the middle.
        for slug, theme in self.lwp.THEMES.items():
            if not theme.get('dark_background'):
                continue
            r, page, _ = self._checks(slug)
            plate = self._over(self._rgba(r['note.page.bg']), page)
            self.assertLessEqual(self._ratio(plate, page), 2.0,
                                 f'{slug}: the notes plate reads as a light slab')

    def test_the_notes_plate_is_a_ground_and_not_nothing(self):
        # The other direction: a plate that does not depart from the page
        # at all is not a section, it is a rule with text under it.
        for slug in self.lwp.THEMES:
            r, page, _ = self._checks(slug)
            plate = self._over(self._rgba(r['note.page.bg']), page)
            self.assertGreater(self._ratio(plate, page), 1.10,
                               f'{slug}: the notes plate is invisible against its page')

    def test_the_dot_that_says_where_you_are_can_be_seen(self):
        """`nav-dot.bg-active` and `table.col-snap.rule-fg` both default to
        `mark`, and on most palettes `mark` is a highlighter -- a wash pale
        enough for text to survive on top of it. As a solid dot on the page
        it therefore vanishes: eighteen themes measured below 3:1 and four
        below 1.10:1, vaporwave's dot at 1.007:1 being its own ground and
        high-contrast, the theme whose whole claim is contrast, at 1.022:1.

        Not a report but a floor, because the dot is the only thing that
        says which slide of the deck is open. Both grounds are measured:
        the page, and the veiled rail the row of dots sits in. Measured
        with every override removed, the rail is the binding one on every
        theme that fails -- nord's dot reads 1.355:1 on its page and
        1.064:1 on its rail -- and the page stays in the check so the
        guard does not rest on that continuing to hold.

        `theme show` reports this too, and the report is per theme and
        advisory: §11.9.1 lets a theme miss AA deliberately, so a reader who
        chooses one accepts what they were shown. Nobody chooses an
        invisible dot, which is why this one is a test."""
        for slug in self.lwp.THEMES:
            r, page, _ = self._checks(slug)
            rail = self._over(self._rgba(r['nav-dot.bg']), page)
            snap = self._over(self._rgba(r['table.col-snap.bg']),
                              self._over(self._rgba(r['fact.bg']), page))
            for name, grounds in (('nav-dot.bg-active', (page, rail)),
                                  ('table.col-snap.rule-fg', (snap,))):
                fg = self._rgba(r[name])
                low = min(self._ratio(fg, g) for g in grounds)
                self.assertGreaterEqual(
                    round(low, 2), 3.0,
                    f'{slug} {name} at {low:.3f}:1 -- the reader cannot see '
                    f'where they are in the deck')

    def test_the_two_extra_call_axes_default_to_the_tone_of_their_ground(self):
        # The defaults keep the call structurally consistent with no
        # per-theme value: each names the tone the theme already chose for
        # text on that ground. If a future edit pins a literal instead, the
        # call stops tracking its palette; contrast remains a separate report.
        reg = self.lwp.PROPERTY_REGISTRY
        self.assertEqual(reg['footnote-call.fg-marked'].default, 'fact.strong.fg')
        self.assertEqual(reg['footnote-call.fg-cover'].default, 'cover.fg')


class AuditNamesTheThreeWaysANoteBreaks(unittest.TestCase):
    """None of them is fatal — the input contract does not break over an
    editorial slip — so `audit` is where they have to surface."""

    DECK = (
        '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
        'nav_title: A\nnav_desc: A\n{extra}---\n\n'
        '<!-- lwp:slide:cover -->\nslug: k255\nkicker: T\n# Title\nsummary: S.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nslug: k256\nkicker: One\n## First\n\nfact-label: L\n\n'
        'A body defined here[^here].\n\n[^here]: Present.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nslug: k257\nkicker: Two\n## Second\n\nfact-label: L\n\n'
        'A call to it from the next card[^here].\n\n'
        '---\n\n'
        '<!-- lwp:slide:full-article -->\nslug: k258\narticle: art.md\n'
    )
    ARTICLE = (
        '# Long form\n\nOne[^p].\n\n[^p]: First.\n\n'
        '[^never]: Nothing calls this.\n\n'
        '<div class="refs">\n\n[^raw]: Inside raw HTML.\n\n</div>\n'
    )

    def _audit(self, extra=''):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        run('init', tmp, '--force')
        root = scaffold(tmp, self.DECK.format(extra=extra))
        (root / 'sources' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
        result = run('audit', str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        # Warnings are diagnostics and go to stderr (§2.4.1). stdout
        # carries the command's answer, which here is the count line.
        return result.stderr

    def test_a_body_nothing_calls_and_a_call_with_no_body_are_both_named(self):
        out = self._audit()
        self.assertIn('[^never]', out)
        self.assertIn('nothing calls', out)

    def test_a_definition_inside_raw_html_is_named(self):
        # Raw HTML is passed through verbatim by design, which is how the
        # combination of `.refs` and notes shipped broken output at exit 0.
        out = self._audit()
        self.assertIn('[^raw]', out)
        self.assertIn('raw HTML', out)

    def test_the_report_follows_the_placement_in_force(self):
        # A call in card 3 to a body in card 2 is a defect under `local`
        # and perfectly fine under `page`. A report blind to that would be
        # wrong in one direction or the other, every time.
        self.assertIn('[^here]', self._audit())
        self.assertNotIn('[^here]', self._audit(extra='notes_placement: page\n'))


class LicenseTextsTravelWithTheExecutable(unittest.TestCase):
    """The executable embeds the GPL and the Output Exception rather than
    reading them from files beside it, because `install` copies the program
    into a series and GPL section 4 requires the License to travel with it
    -- and a release publishes the executable ALONE, with no COPYING nearby,
    so a repository-relative lookup would fail in exactly the case that
    matters. Embedding buys that at the cost of a duplicated text, so the
    duplicate is guarded here rather than by good intentions."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()
        self.root = EXECUTABLE.parent

    def test_embedded_texts_match_the_files_at_the_repository_root(self):
        for filename, constant in (
            ('COPYING', 'LICENSE_GPL_TEXT'),
            ('COPYING.EXCEPTION', 'LICENSE_EXCEPTION_TEXT'),
        ):
            with self.subTest(filename):
                self.assertEqual(
                    getattr(self.lwp, constant),
                    (self.root / filename).read_text(encoding='utf-8'),
                    f'{constant} has drifted from {filename}. Change both together: '
                    f'the copy inside the executable is the one users actually '
                    f'receive, so a stale constant hands out terms that are not '
                    f'the ones this repository publishes.')

    def test_the_gpl_text_is_whole(self):
        # A truncated license is worse than no license: it looks like
        # compliance. Cheap to check, and the failure it catches (a bad
        # copy-paste, a stray editor truncation) is silent otherwise.
        text = self.lwp.LICENSE_GPL_TEXT
        self.assertIn('GNU GENERAL PUBLIC LICENSE', text)
        self.assertIn('Version 3, 29 June 2007', text)
        self.assertIn('END OF TERMS AND CONDITIONS', text)

    def test_install_writes_both_licenses_beside_the_copied_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            subprocess.run([sys.executable, str(EXECUTABLE), 'init', str(root)],
                           check=True, capture_output=True, text=True)
            self.assertTrue((root / 'lightwebpres').is_file(),
                            'install no longer copies the executable')
            for filename in ('COPYING', 'COPYING.EXCEPTION'):
                path = root / filename
                self.assertTrue(
                    path.is_file(),
                    f'install copied the program but not {filename}: anyone '
                    f'publishing this series would be conveying GPL code without '
                    f'its license, through no fault of their own')
                self.assertEqual(path.read_text(encoding='utf-8'),
                                 (self.root / filename).read_text(encoding='utf-8'))


class TestNamingConvention(unittest.TestCase):
    """§20.0: a name's shape says what level it is set at — kebab-case for a
    slide field, snake_case for an article/series field, dotted for a theme
    property.

    The rule is load-bearing, not cosmetic. Putting a field at the wrong
    level produces no error (it is simply ignored), and `resolve` picks
    which cascade to interrogate from the shape of the name alone. It is
    also the rule most likely to be broken by accident: four article-level
    fields were once named in kebab-case purely because they sat next to
    `highlight-caption` and looked like CSS. Nothing checked, so the
    resemblance won. This is the thing that checks."""

    SNAKE = re.compile(r'^[a-z][a-z0-9]*(_[a-z0-9]+)*$')
    KEBAB = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')

    def setUp(self):
        self.source = EXECUTABLE.read_text(encoding='utf-8')
        self.lwp = load_lightwebpres_module()

    def _article_level_names(self):
        """Every name the engine treats as article- or series-level.

        Two sources on purpose. The tuples are the registries `resolve`
        and `series-info` are driven by, so they are what a new field is
        added to; the source scan catches a field that is read from a
        meta block and registered nowhere, which is exactly the kind that
        would slip past a registry-only check. Neither is asked for a
        specific name — a canary naming a field would fire on the very
        rename this test exists to report, and bury the real message."""
        names = set(self.lwp._ARTICLE_LEVEL_NAMES)
        names |= set(self.lwp._SERIES_META_STRING_FIELDS)
        names |= set(self.lwp._SERIES_STRING_FIELDS)
        names |= set(re.findall(r"(?:meta|series_meta)\.get\('([^']+)'", self.source))
        names |= set(re.findall(r"\bpick\('([^']+)'", self.source))
        self.assertGreater(len(names), 15, 'the field registries have gone empty')
        return names

    def test_every_slide_field_is_kebab_case(self):
        self.assertTrue(self.lwp.SLIDE_FIELD_NAMES, 'the slide field list has gone empty')
        for name in self.lwp.SLIDE_FIELD_NAMES:
            with self.subTest(name):
                self.assertNotIn(
                    '_', name,
                    f'{name!r} is a slide field written in snake_case: its shape '
                    f'now claims it belongs in the meta block instead (§20.0)')
                self.assertRegex(name, self.KEBAB, f'{name!r} is not kebab-case')

    def test_every_article_level_field_is_snake_case(self):
        for name in sorted(self._article_level_names()):
            with self.subTest(name):
                self.assertNotIn(
                    '-', name,
                    f'{name!r} is an article-level field written in kebab-case: its '
                    f'shape claims it belongs in a slide header, and `resolve` would '
                    f'send it to the wrong cascade (§20.0)')
                self.assertRegex(name, self.SNAKE, f'{name!r} is not snake_case')

    def test_a_name_at_both_levels_is_one_resolve_refuses(self):
        """A bare word has no shape to read, so a name living at BOTH
        levels makes the rule say two things at once — and `resolve` has
        to pick a cascade from it. One such name exists: `comment`, which
        every level parses and no renderer reads.

        The invariant is therefore not "no overlap" but "no SILENT
        overlap": anything at both levels must be in the list of names
        `resolve` refuses, with a reason. A new one added quietly would
        make `resolve` answer about one level while the reader asked
        about the other."""
        overlap = self._article_level_names() & set(self.lwp.SLIDE_FIELD_NAMES)
        unacknowledged = overlap - set(self.lwp._UNRESOLVABLE_NAMES)
        self.assertEqual(
            unacknowledged, set(),
            f'{sorted(unacknowledged)} is read at both the slide and the '
            f'article level, and `resolve` would silently pick one of them')

    def test_every_theme_property_is_dotted(self):
        registry = self.lwp.PROPERTY_REGISTRY
        self.assertTrue(registry, 'the property registry has gone empty')
        for key in registry:
            with self.subTest(key):
                self.assertIn(
                    '.', key,
                    f'{key!r} is a theme property with no dot: nothing tells it '
                    f'apart from a field name (§20.0)')
                for segment in key.split('.'):
                    self.assertRegex(
                        segment, self.KEBAB,
                        f'{key!r} has a segment that is not kebab-case')


class SeriesInfoReportsTheCascadeTheBuildUses(unittest.TestCase):
    """§11.11. `series-info` says what is in a series without building
    it: the articles in series.json's order, each field RESOLVED the way
    a build resolves it (§20.3.1), and which level of the cascade each
    value came from.

    The point of the command is that there is ONE cascade in this
    program. So the load-bearing tests here do not compare the report
    against an expectation written in this file — they compare it
    against a real build's output. A second implementation that drifted
    would still satisfy a hand-written expectation; it cannot satisfy
    the page the build actually wrote.

    Every string used below is deliberately free of the punctuation the
    typography engine touches (no colon, no question mark, no
    guillemets): the build applies non-breaking spaces to what it
    renders and `series-info` reports the resolved value, so a title
    carrying any of them would differ for a reason that is not a bug."""

    # A cover slide is all an article needs for the content level of the
    # cascade to have something to give (its heading and its summary).
    ARTICLE = ('<!-- lwp:meta -->\n{meta}---\n\n'
               '<!-- lwp:slide:cover -->\nslug: k259\nkicker: Tag\n# {heading}\n'
               'summary: {summary}\n')
    NAV_SLIDE = '\n---\n\n<!-- lwp:slide:series-nav -->\nslug: k260\n'

    def _series(self, tmp, entries, sources, series_meta=None):
        """A series directory: `entries` go into series.json verbatim,
        `sources` maps a filename to its .md text."""
        root = Path(tmp)
        (root / 'sources').mkdir(parents=True, exist_ok=True)
        for name, text in sources.items():
            (root / 'sources' / name).write_text(text, encoding='utf-8')
        data = {'articles': entries}
        if series_meta is not None:
            data['series_meta'] = series_meta
        (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        return root

    def setUp(self):
        # The status vocabulary is read from the executable, not restated
        # here: a value added upstream would otherwise pass unnoticed.
        self.lwp = load_lightwebpres_module()

    def _report(self, root):
        result = run('status', str(root), '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def _field(self, article, name):
        return article['fields'][name]['value'], article['fields'][name]['source']

    # ------------------------------------------------------------------
    # Against a real build, not against an expectation written here
    # ------------------------------------------------------------------

    def test_a_minimal_series_reports_the_titles_the_build_produces(self):
        """Two entries carrying nothing but `page_source` — so every
        field is derived — checked against the pages a build wrote:
        <title>, <meta name="description">, the index cards, and the
        nav card one article renders for the OTHER one."""
        sources = {
            'intro.md': self.ARTICLE.format(
                meta='', heading='Where it begins',
                summary='A first look at the whole thing.') + self.NAV_SLIDE,
            'next.md': self.ARTICLE.format(
                meta='', heading='What comes after',
                summary='The second half of the story.') + self.NAV_SLIDE,
        }
        entries = [{'page_source': 'intro.md'}, {'page_source': 'next.md'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            report = self._report(root)
            out = root / 'public'
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            index = (out / 'index.html').read_text(encoding='utf-8')

            for article in report['articles']:
                page_dest, _ = self._field(article, 'page_dest')
                page = (out / page_dest).read_text(encoding='utf-8')
                page_title, _ = self._field(article, 'page_title')
                page_desc, _ = self._field(article, 'page_desc')
                card_title, _ = self._field(article, 'card_title')
                card_desc, _ = self._field(article, 'card_desc')
                nav_title, _ = self._field(article, 'nav_title')

                self.assertIn(f'<title>{page_title}</title>', page)
                self.assertIn(f'<meta name="description" content="{page_desc}">',
                              page)
                self.assertIn(f'<div class="article-title">{card_title}</div>',
                              index)
                self.assertIn(f'<div class="article-desc">{card_desc}</div>',
                              index)
                # The nav card this article gets on the OTHER article's
                # page — the reason every entry is resolved up front.
                other = next(a for a in report['articles'] if a is not article)
                other_page = (out / other['fields']['page_dest']['value']
                              ).read_text(encoding='utf-8')
                self.assertIn(f'<div class="series-title">{nav_title}</div>',
                              other_page)

    def test_the_order_is_series_json_s_order_and_the_build_agrees(self):
        """The order IS data: it fixes cross-article navigation. Named so
        that alphabetical order would be a different answer."""
        names = ['zulu.md', 'alpha.md', 'mike.md']
        sources = {name: self.ARTICLE.format(
            meta='', heading=name[:-3].title(), summary='A summary.')
            for name in names}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': n} for n in names], sources)
            report = self._report(root)
            self.assertEqual([a['page_source'] for a in report['articles']], names)

            out = root / 'public'
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            index = (out / 'index.html').read_text(encoding='utf-8')
            positions = [index.index(f'>{n[:-3].title()}<') for n in names]
            self.assertEqual(positions, sorted(positions),
                             'the report is not in the order the index uses')

    # ------------------------------------------------------------------
    # The cascade, level by level
    # ------------------------------------------------------------------

    def test_series_json_wins_over_the_meta_block_wins_over_the_content(self):
        """The same field, at the three levels an author can write it,
        one article per level — value AND provenance."""
        sources = {
            'all.md': self.ARTICLE.format(
                meta='page_title: From the meta block\n',
                heading='From the content', summary='A summary.'),
            'meta.md': self.ARTICLE.format(
                meta='page_title: From the meta block\n',
                heading='From the content', summary='A summary.'),
            'content.md': self.ARTICLE.format(
                meta='', heading='From the content', summary='A summary.'),
        }
        entries = [
            {'page_source': 'all.md', 'page_title': 'From series json'},
            {'page_source': 'meta.md'},
            {'page_source': 'content.md'},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            report = self._report(root)
            self.assertEqual(
                [self._field(a, 'page_title') for a in report['articles']],
                [('From series json', 'series'),
                 ('From the meta block', 'article'),
                 ('From the content', 'content')])

            # And the build agrees about the value that won.
            out = root / 'public'
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            self.assertIn('<title>From series json</title>',
                          (out / 'all.html').read_text(encoding='utf-8'))
            self.assertIn('<title>From the meta block</title>',
                          (out / 'meta.html').read_text(encoding='utf-8'))
            self.assertIn('<title>From the content</title>',
                          (out / 'content.html').read_text(encoding='utf-8'))

    def test_every_level_of_the_cascade_names_itself(self):
        """All five provenances at once, including the two a hand-written
        expectation would get wrong: a value chained off another resolved
        field is `derived`, and a field that legitimately resolves to
        nothing still has a provenance (`default`) instead of
        disappearing."""
        sources = {'a.md': self.ARTICLE.format(
            meta='card_desc: From the meta block\n',
            heading='From the content', summary='A summary.')}
        entries = [{'page_source': 'a.md', 'card_label': 'From series json'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            article = self._report(root)['articles'][0]

            self.assertEqual(self._field(article, 'card_label'),
                             ('From series json', 'series'))
            self.assertEqual(self._field(article, 'card_desc'),
                             ('From the meta block', 'article'))
            self.assertEqual(self._field(article, 'page_title'),
                             ('From the content', 'content'))
            # page_dest from page_source, card_title from page_title,
            # nav_desc from card_desc: computed from another field.
            self.assertEqual(self._field(article, 'page_dest'),
                             ('a.html', 'derived'))
            self.assertEqual(self._field(article, 'card_title'),
                             ('From the content', 'derived'))
            self.assertEqual(self._field(article, 'nav_desc'),
                             ('From the meta block', 'derived'))
            self.assertEqual(article['status'], {'value': 'active',
                                                 'source': 'default'})

        # card_label with nothing anywhere: empty, and still says where
        # the emptiness comes from.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md'}], sources)
            article = self._report(root)['articles'][0]
            self.assertEqual(self._field(article, 'card_label'), ('', 'default'))

    def test_a_derived_page_dest_and_an_explicit_one_are_told_apart(self):
        sources = {'a.md': self.ARTICLE.format(meta='page_dest: from-meta.html\n',
                                               heading='H', summary='S.'),
                   'b.md': self.ARTICLE.format(meta='', heading='H', summary='S.')}
        entries = [{'page_source': 'a.md'},
                   {'page_source': 'b.md', 'page_dest': 'from-series.html'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            report = self._report(root)
            self.assertEqual(self._field(report['articles'][0], 'page_dest'),
                             ('from-meta.html', 'article'))
            self.assertEqual(self._field(report['articles'][1], 'page_dest'),
                             ('from-series.html', 'series'))

    # ------------------------------------------------------------------
    # Drafts
    # ------------------------------------------------------------------

    def test_drafts_are_listed_reported_and_counted_apart(self):
        """A draft is excluded from the build but is still in the series:
        it must be reported, marked, and counted separately — not made to
        vanish, which is what reading the build's output would do."""
        sources = {
            'live.md': self.ARTICLE.format(meta='', heading='Live',
                                           summary='A summary.'),
            'hidden.md': self.ARTICLE.format(meta='', heading='Hidden',
                                             summary='A summary.'),
            'quiet.md': self.ARTICLE.format(meta='status: draft\n', heading='Quiet',
                                            summary='A summary.'),
            'gone.md': self.ARTICLE.format(meta='', heading='Gone',
                                           summary='A summary.'),
        }
        entries = [{'page_source': 'live.md'},
                   {'page_source': 'hidden.md', 'status': 'draft'},
                   {'page_source': 'quiet.md'},
                   {'page_source': 'gone.md', 'status': 'ignored'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            report = self._report(root)
            self.assertEqual(report['counts'],
                             {'active': 1, 'draft': 2, 'ignored': 1})
            self.assertEqual([a['status'] for a in report['articles']],
                             [{'value': 'active', 'source': 'default'},
                              {'value': 'draft', 'source': 'series'},
                              {'value': 'draft', 'source': 'article'},
                              {'value': 'ignored', 'source': 'series'}])
            # An ignored article is STILL LISTED. It is out of the chain,
            # not out of the series file, and a report that dropped it
            # would leave a consumer unable to show it or bring it back.
            self.assertEqual([a['page_source'] for a in report['articles']],
                             ['live.md', 'hidden.md', 'quiet.md', 'gone.md'])

            # Evidence that these really are the build's statuses: the
            # build writes exactly the one the report calls active.
            out = root / 'public'
            self.assertEqual(run('build', str(root), '--output', str(out))
                             .returncode, 0)
            self.assertTrue((out / 'live.html').exists())
            for skipped in ('hidden.html', 'quiet.html', 'gone.html'):
                self.assertFalse((out / skipped).exists(), skipped)

    def test_series_json_beats_the_meta_block_for_the_status_too(self):
        """§20.6, and the case that used to need a rule of its own: an
        article declaring itself a draft, put back into the series from
        series.json. `active` is a value like any other, so this is the
        ordinary cascade rather than a presence-versus-truth exception."""
        sources = {'a.md': self.ARTICLE.format(meta='status: draft\n', heading='H',
                                               summary='S.')}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md', 'status': 'active'}],
                                sources)
            article = self._report(root)['articles'][0]
            self.assertEqual(article['status'], {'value': 'active',
                                                 'source': 'series'})

    # ------------------------------------------------------------------
    # The JSON surface itself (§1.2: renaming a key breaks the GUI)
    # ------------------------------------------------------------------

    ORIGINS = {'series', 'article', 'content', 'derived', 'default'}
    FIELDS = ('page_dest', 'page_title', 'page_desc', 'card_title',
              'card_desc', 'card_label', 'nav_title', 'nav_desc')

    def test_the_json_parses_and_carries_the_documented_keys(self):
        sources = {'a.md': self.ARTICLE.format(meta='', heading='H',
                                               summary='S.')}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md'}], sources,
                                series_meta={'title': 'A series',
                                             'author': 'Fade78'})
            report = self._report(root)

        # /2, not /1: `draft` disappeared and `counts` changed meaning.
        # The promise is that the number moves for exactly that, and
        # never for a key merely being added.
        self.assertEqual(report['schema'], 'lightwebpres.series-info/2')
        version = run('--help').stdout.split('LightWebPres v', 1)[1].split(' ', 1)[0]
        self.assertEqual(report['lightwebpres_version'], version)
        self.assertEqual(set(report), {'schema', 'lightwebpres_version',
                                       'target', 'series_meta', 'counts',
                                       'articles'})
        self.assertEqual(set(report['target']), {'kind', 'directory', 'theme'})
        self.assertEqual(report['target']['kind'], 'series')
        self.assertEqual(report['target']['directory'], str(Path(root).resolve()))
        self.assertIsNone(report['target']['theme'])
        self.assertEqual(set(report['series_meta']),
                         {'title', 'subtitle', 'version', 'intro', 'author',
                          'license'})
        self.assertEqual(report['series_meta']['title'], 'A series')
        self.assertIsNone(report['series_meta']['subtitle'])
        self.assertEqual(set(report['counts']), {'active', 'draft', 'ignored'})

        article = report['articles'][0]
        self.assertEqual(set(article),
                         {'page_source', 'source_read', 'status', 'fields'})
        self.assertIs(article['source_read'], True)
        self.assertEqual(tuple(article['fields']), self.FIELDS)
        for name, field in article['fields'].items():
            self.assertEqual(set(field), {'value', 'source'}, name)
            self.assertIsInstance(field['value'], str, name)
            self.assertIn(field['source'], self.ORIGINS, name)
        self.assertEqual(set(article['status']), {'value', 'source'})
        self.assertIn(article['status']['value'], self.lwp.ARTICLE_STATUSES)

    def test_the_theme_in_force_is_the_one_settings_conf_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            self.assertEqual(run('init', str(root), '--theme', 'evergreen')
                             .returncode, 0)
            self.assertEqual(self._report(root)['target']['theme'], 'evergreen')
            self.assertEqual(run('series', 'theme', 'set', str(root), '--theme', 'nord')
                             .returncode, 0)
            self.assertEqual(self._report(root)['target']['theme'], 'nord')

    # ------------------------------------------------------------------
    # What it must not do
    # ------------------------------------------------------------------

    def test_an_unreadable_article_does_not_cost_the_rest_of_the_answer(self):
        """A missing or undecodable page_source is a `build` error and
        stays one — this command is not a second `check`. It still
        answers: the entry is listed with source_read false and its
        fields fallen back, the other articles are intact, the notice
        goes to stderr so stdout stays one JSON document, and the exit
        code is 0."""
        sources = {'good.md': self.ARTICLE.format(meta='', heading='Good one',
                                                  summary='A summary.')}
        entries = [{'page_source': 'good.md'},
                   {'page_source': 'gone.md'},
                   {'page_source': 'binary.md'}]
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, entries, sources)
            (root / 'sources' / 'binary.md').write_bytes(
                b'<!-- lwp:meta -->\npage_title: T \xff\xfe\n---\n')
            result = run('status', str(root), '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)

            self.assertEqual([a['source_read'] for a in report['articles']],
                             [True, False, False])
            self.assertEqual(self._field(report['articles'][0], 'page_title'),
                             ('Good one', 'content'))
            # Nothing to read means nothing to fall back on but the
            # filename the entry itself carries.
            self.assertEqual(self._field(report['articles'][1], 'page_title'),
                             ('gone.html', 'derived'))
            self.assertEqual(self._field(report['articles'][2], 'page_desc'),
                             ('', 'default'))
            self.assertIn('gone.md', result.stderr)
            self.assertIn('binary.md', result.stderr)
            self.assertNotIn('gone.md', result.stdout.split('"articles"')[0])

            # And the build's verdict on the same series is unchanged.
            build = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(build.returncode, 0)
            self.assertIn('Source not found', build.stderr)
            self.assertNotIn('Traceback', build.stderr)

    def test_it_writes_nothing_at_all(self):
        sources = {'a.md': self.ARTICLE.format(meta='', heading='H',
                                               summary='S.')}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md'}], sources)

            def snapshot():
                return {str(p.relative_to(root)): p.stat().st_mtime_ns
                        for p in sorted(root.rglob('*')) if p.is_file()}

            before = snapshot()
            for fmt in ('text', 'json'):
                self.assertEqual(run('status', str(root), '--format', fmt)
                                 .returncode, 0)
            self.assertEqual(snapshot(), before)
            self.assertFalse((root / 'public').exists())
            self.assertFalse((root / 'README.md').exists())

    def test_an_unknown_format_is_a_fatal_error(self):
        sources = {'a.md': self.ARTICLE.format(meta='', heading='H',
                                               summary='S.')}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md'}], sources)
            result = run('status', str(root), '--format', 'yaml')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('--format', result.stderr)

    def test_the_text_format_names_the_provenance_of_every_field(self):
        sources = {'a.md': self.ARTICLE.format(meta='', heading='A heading',
                                               summary='A summary.')}
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, [{'page_source': 'a.md'}], sources)
            text = run('status', str(root)).stdout
        for name in self.FIELDS:
            self.assertRegex(text, rf'{name}\s+\[(?:{"|".join(self.ORIGINS)})\]',
                             f'{name} is reported without its provenance')
        self.assertIn('A heading', text)

    # ------------------------------------------------------------------
    # One cascade, not two
    # ------------------------------------------------------------------

    # The command reports what resolve_article_fields RETURNED while it
    # resolved. If any of these functions ever parses an article itself,
    # a second cascade has been born — the exact thing §11.11 exists to
    # prevent, and the kind of copy that drifts silently because both
    # halves keep passing their own tests.
    SERIES_INFO_SURFACE = {'series_info_report', 'print_series_info_text',
                           'cmd_series_info', 'series_theme'}
    RESOLUTION_PRIMITIVES = {'parse_markdown_extended', 'parse_metadata_block',
                             '_find_cover_slide', '_read_article_source'}

    def test_series_info_does_not_resolve_anything_a_second_time(self):
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        seen = set()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in self.SERIES_INFO_SURFACE:
                continue
            seen.add(node.name)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id in self.RESOLUTION_PRIMITIVES:
                    self.fail(f'{node.name} reaches {sub.id}: series-info is '
                              f'resolving fields itself instead of reporting '
                              f'what resolve_article_fields resolved')
        self.assertEqual(seen, self.SERIES_INFO_SURFACE,
                         'a series-info function was renamed or removed; this '
                         'guard now watches nothing')

    def test_the_command_goes_through_the_build_s_own_resolver(self):
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        command = next(n for n in tree.body
                       if isinstance(n, ast.FunctionDef) and n.name == 'cmd_series_info')
        called = {sub.id for sub in ast.walk(command) if isinstance(sub, ast.Name)}
        self.assertIn('resolve_article_fields', called)


class ResolveAnswersOneNameAndShowsWhoLost(unittest.TestCase):
    """§11.12. `resolve` takes one name and says what it is worth here,
    which level decided it, and — the part that makes it worth having —
    what every other level held.

    A value alone never explains why the line an author just wrote
    changed nothing. So the tests that matter here are the ones about the
    LOSERS: a settings pin that beats the theme must leave the theme in
    the chain, and a commented-out line must show as a level holding
    nothing rather than vanish. A report that only ever showed the winner
    would pass a naive test and be useless for the one job it has.

    Values are cross-checked against a real build wherever a build can
    produce them: an expectation written in this file would be satisfied
    by a second cascade that drifted, and the page the build wrote would
    not."""

    ARTICLE = ('<!-- lwp:meta -->\n{meta}---\n\n'
               '<!-- lwp:slide:cover -->\nslug: k261\nkicker: Tag\n# {heading}\n'
               'summary: {summary}\n')

    def _series(self, tmp, entries, sources, series_meta=None, settings=None):
        root = Path(tmp)
        (root / 'sources').mkdir(parents=True, exist_ok=True)
        for name, text in sources.items():
            (root / 'sources' / name).write_text(text, encoding='utf-8')
        data = {'articles': entries}
        if series_meta is not None:
            data['series_meta'] = series_meta
        (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        if settings is not None:
            (root / 'templates').mkdir(exist_ok=True)
            (root / 'templates' / 'settings.conf').write_text(
                settings, encoding='utf-8')
        return root

    def _one_article(self, tmp, meta='', entry=None, **kwargs):
        sources = {'intro.md': self.ARTICLE.format(
            meta=meta, heading='Where it begins',
            summary='A first look at the whole thing.')}
        return self._series(tmp, [dict({'page_source': 'intro.md'},
                                       **(entry or {}))], sources, **kwargs)

    def _resolve(self, root, *args):
        result = run('resolve', str(root), *args, '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def _levels(self, report):
        return {link['level']: link for link in report['resolution']['chain']}

    def setUp(self):
        self.lwp = load_lightwebpres_module()

    # ------------------------------------------------------------------
    # The shape of the name picks the cascade (§20.0)
    # ------------------------------------------------------------------

    def test_the_shape_of_the_name_picks_the_cascade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            for name, kind, extra in (
                ('kicker.fg', 'theme-property', ()),
                ('page_title', 'article-field', ('--article', 'intro.md')),
                ('fact-label', 'slide-field', ()),
                ('title', 'series-field', ()),
            ):
                with self.subTest(name):
                    report = self._resolve(root, name, *extra)
                    self.assertEqual(report['query']['kind'], kind)

    # ------------------------------------------------------------------
    # Against a real build, not against an expectation written here
    # ------------------------------------------------------------------

    def test_a_theme_property_reports_the_colour_the_build_paints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'series'
            subprocess.run([sys.executable, str(EXECUTABLE), 'init',
                            str(root), '--theme', 'nord'],
                           check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(EXECUTABLE), 'demo', str(root)],
                           check=True, capture_output=True, text=True)
            build = run('build', str(root))
            self.assertEqual(build.returncode, 0, build.stderr)

            value = self._resolve(root, 'kicker.fg')['resolution']['value']
            page = next((root / 'public').glob('*.html')).read_text(encoding='utf-8')
            self.assertIn(
                value, page,
                f'resolve says kicker.fg is {value}, and no built page contains '
                f'it: the report and the stylesheet disagree, which is the '
                f'second cascade this command exists not to be')

    def test_an_article_field_reports_the_title_the_build_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            build = run('build', str(root))
            self.assertEqual(build.returncode, 0, build.stderr)
            report = self._resolve(root, 'page_title', '--article', 'intro.md')
            page = (root / 'public' / 'intro.html').read_text(encoding='utf-8')
            self.assertIn(f'<title>{report["resolution"]["value"]}</title>', page)
            self.assertEqual(report['resolution']['source'], 'content')

    # ------------------------------------------------------------------
    # The losers, which are the point
    # ------------------------------------------------------------------

    def test_a_settings_pin_wins_and_the_theme_stays_in_the_chain(self):
        """`note.fg` on purpose: nord overrides it, so the theme level
        holds a real value that the pin then beats. A property no theme
        touches would leave that level empty, and the test would pass
        while proving nothing about losing levels."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(
                tmp, settings='theme: nord\nnote.fg: call\n')
            levels = self._levels(self._resolve(root, 'note.fg'))
            self.assertTrue(levels['settings']['winner'])
            self.assertEqual(levels['settings']['value'], 'call')
            self.assertTrue(
                levels['theme']['present'],
                'the level that lost was dropped from the report, which is '
                'the half of the answer that explains why')
            self.assertEqual(levels['theme']['value'],
                             self.lwp.theme_property_layer('nord')['note.fg'])
            self.assertFalse(levels['theme']['winner'])
            self.assertTrue(levels['default']['present'],
                            'the registry default always holds something')
            self.assertFalse(levels['default']['winner'])

    def test_a_commented_out_line_is_a_level_holding_nothing(self):
        """The exact mistake this command exists for: the line is in the
        file, the author can see it, and it does nothing."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(
                tmp, settings='theme: nord\n# kicker.fg: call\n')
            report = self._resolve(root, 'kicker.fg')
            levels = self._levels(report)
            self.assertFalse(levels['settings']['present'])
            self.assertIsNone(levels['settings']['value'])
            self.assertNotEqual(report['resolution']['source'], 'settings')

    def test_an_instance_tag_is_named_in_the_chain_and_never_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp, settings='theme: nord\n')
            instance = self._levels(self._resolve(root, 'kicker.fg'))['instance']
            self.assertFalse(instance['winner'])
            self.assertFalse(instance['present'])
            self.assertIn('note', instance,
                          'a level that can never win has to say why, or it '
                          'reads as one nobody set')

    def test_the_article_layer_is_absent_until_article_is_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(
                tmp, meta='style.kicker.fg: #123456\n', settings='theme: nord\n')

            without = self._levels(self._resolve(root, 'kicker.fg'))['article']
            self.assertFalse(without['present'])
            self.assertIn('--article', without.get('note', ''),
                          'a layer that was not consulted must say so, not '
                          'look like one nobody wrote')

            report = self._resolve(root, 'kicker.fg', '--article', 'intro.md')
            self.assertEqual(report['resolution']['source'], 'article')
            self.assertEqual(self._levels(report)['article']['value'], '#123456')
            self.assertTrue(report['resolution']['value'].startswith('#123456'))

    def test_a_reference_is_followed_and_the_hops_are_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(
                tmp, settings='theme: nord\nkicker.fg: call\n')
            resolution = self._resolve(root, 'kicker.fg')['resolution']
            self.assertEqual(resolution['hops'], ['color.call'],
                             'a bare word is a reference (§9.2); showing only '
                             'the final colour hides where it came from')
            palette = self._resolve(root, 'color.call')['resolution']['value']
            self.assertEqual(resolution['value'], palette)

    def test_a_series_wide_default_is_told_apart_from_a_series_json_line(self):
        """`author` reaches a level the display fields do not have. It
        needed its own word before it could be reported at all, and the
        whole point of that word is that it is NOT `series`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp, series_meta={'author': 'The series'})
            report = self._resolve(root, 'author', '--article', 'intro.md')
            self.assertEqual(report['resolution']['source'], 'series-default')
            self.assertEqual(report['resolution']['value'], 'The series')
            self.assertFalse(self._levels(report)['series']['present'])

        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp, entry={'author': 'This article'},
                                     series_meta={'author': 'The series'})
            report = self._resolve(root, 'author', '--article', 'intro.md')
            self.assertEqual(report['resolution']['source'], 'series')
            levels = self._levels(report)
            self.assertEqual(levels['series-default']['value'], 'The series')
            self.assertFalse(levels['series-default']['winner'])

    def test_every_level_of_the_article_cascade_can_win(self):
        cases = [
            ({}, '', 'content', 'Where it begins'),
            ({}, 'page_title: From the meta block\n', 'article',
             'From the meta block'),
            ({'page_title': 'From series json'}, 'page_title: ignored\n',
             'series', 'From series json'),
        ]
        for entry, meta, source, value in cases:
            with self.subTest(source), tempfile.TemporaryDirectory() as tmp:
                root = self._one_article(tmp, meta=meta, entry=entry)
                resolution = self._resolve(
                    root, 'page_title', '--article', 'intro.md')['resolution']
                self.assertEqual(resolution['source'], source)
                self.assertEqual(resolution['value'], value)

    def test_the_chain_is_ordered_strongest_first(self):
        """And carries every level, not only the ones holding something:
        the empty rungs are what tell an author where they could have
        written the value they are looking for."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            for name, expected in (
                ('page_title',
                 ['series', 'article', 'content', 'derived', 'default']),
                ('card_label', ['series', 'article', 'default']),
                ('author',
                 ['series', 'article', 'series-default', 'default']),
                ('kicker.fg',
                 ['instance', 'article', 'settings', 'theme', 'default']),
            ):
                with self.subTest(name):
                    chain = self._resolve(
                        root, name, '--article',
                        'intro.md')['resolution']['chain']
                    self.assertEqual([link['level'] for link in chain], expected)

    def test_a_series_field_still_names_the_level_it_fell_back_to(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            report = self._resolve(root, 'subtitle')
            self.assertEqual([link['level']
                              for link in report['resolution']['chain']],
                             ['series', 'default'])
            self.assertEqual(report['resolution']['source'], 'default')

    # ------------------------------------------------------------------
    # A slide field has no cascade, and the report says so by shape
    # ------------------------------------------------------------------

    def test_a_slide_field_is_reported_as_sites_not_as_one_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = {
                'a.md': self.ARTICLE.format(meta='', heading='A', summary='s')
                        + '\n---\n\n<!-- lwp:slide -->\nslug: k262\n## First\n'
                          'fact-label: On A\n\nbody\n',
                'b.md': self.ARTICLE.format(meta='', heading='B', summary='s')
                        + '\n---\n\n<!-- lwp:slide -->\nslug: k263\n## Second\n'
                          'fact-label: On B\n\nbody\n',
            }
            root = self._series(tmp, [{'page_source': 'a.md'},
                                      {'page_source': 'b.md'}], sources)

            report = self._resolve(root, 'fact-label')
            self.assertNotIn('value', report['resolution'],
                             'a slide field has no winner to report: slides '
                             'that never competed cannot have one')
            sites = report['resolution']['sites']
            self.assertEqual([(s['article'], s['value']) for s in sites],
                             [('a.md', 'On A'), ('b.md', 'On B')])
            self.assertEqual(sites[0]['slide'], 2)
            self.assertEqual(sites[0]['slide_title'], 'First')

            only = self._resolve(root, 'fact-label', '--article', 'b.md')
            self.assertEqual([s['article'] for s in only['resolution']['sites']],
                             ['b.md'])

    def test_a_slide_field_set_nowhere_is_an_empty_survey_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            self.assertEqual(
                self._resolve(root, 'highlight-caption')['resolution']['sites'], [])

    # ------------------------------------------------------------------
    # Refusals, each with the reason
    # ------------------------------------------------------------------

    def test_a_name_that_never_resolves_is_refused_with_its_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            for name, expected in (('comment', 'review note'),
                                   ('slide_title', '`##`')):
                with self.subTest(name):
                    result = run('resolve', str(root), name)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(expected, result.stderr)

    def test_an_unknown_name_names_the_reading_that_was_made(self):
        """The likeliest mistake is writing the wrong SHAPE, so the error
        has to say which cascade it went to before saying it found
        nothing there."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            for name, expected in (('fact-lable', 'slide field'),
                                   ('page_titel', 'article-level field'),
                                   ('tag.foreground', 'unknown theme property')):
                with self.subTest(name):
                    result = run('resolve', str(root), name)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(expected, result.stderr)

    def test_a_per_article_field_without_article_lists_the_articles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            result = run('resolve', str(root), 'card_label')
            self.assertEqual(result.returncode, 1)
            self.assertIn('--article', result.stderr)
            self.assertIn('intro.md', result.stderr,
                          'the fix is a copy-paste; the error should hand '
                          'over the string, not point at the file')

    def test_an_unknown_article_lists_the_ones_that_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            result = run('resolve', str(root), 'page_title',
                         '--article', 'nope.md')
            self.assertEqual(result.returncode, 1)
            self.assertIn('intro.md', result.stderr)

    def test_a_missing_name_and_an_unknown_format_are_both_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            self.assertEqual(run('resolve').returncode, 1)
            result = run('resolve', str(root), 'page_title',
                         '--article', 'intro.md', '--format', 'yaml')
            self.assertEqual(result.returncode, 1)
            self.assertIn('text, json', result.stderr)

    # ------------------------------------------------------------------
    # What it must not do
    # ------------------------------------------------------------------

    def test_it_writes_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp, settings='theme: nord\n')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            for args in (('kicker.fg',), ('fact-label',),
                         ('page_title', '--article', 'intro.md')):
                self._resolve(root, *args)
            after = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertFalse((root / 'public').exists(),
                             'resolve built something, and it must not')

    def test_an_unreadable_article_warns_and_still_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(tmp)
            (root / 'sources' / 'intro.md').unlink()
            result = run('resolve', str(root), 'page_title',
                         '--article', 'intro.md', '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARNING]', result.stderr)
            self.assertNotIn('[ERROR]', result.stderr, result.stderr)
            self.assertEqual(
                json.loads(result.stdout)['resolution']['source'], 'derived')

    def test_the_command_goes_through_the_builds_own_resolvers(self):
        """Same rule as `series-info`, for the same reason: exposing a
        cascade by rewriting it installs the divergent copy the command
        exists to prevent."""
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        wanted = {'resolve_article_field': 'resolve_article_fields',
                  'resolve_theme_property': 'resolve_theme_properties'}
        found = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                found[node.name] = {sub.id for sub in ast.walk(node)
                                    if isinstance(sub, ast.Name)}
        for caller, callee in wanted.items():
            with self.subTest(caller):
                self.assertIn(caller, found, f'{caller} is gone')
                if caller == 'resolve_article_field':
                    # It does not call the resolver — cmd_resolve does, and
                    # hands it what that call recorded. What matters is that
                    # nothing here re-parses an article.
                    self.assertNotIn('parse_markdown_extended', found[caller])
                else:
                    self.assertIn(callee, found[caller])

    def test_the_text_format_shows_the_losing_levels_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._one_article(
                tmp, settings='theme: nord\nkicker.fg: call\n')
            result = run('resolve', str(root), 'kicker.fg')
            self.assertEqual(result.returncode, 0, result.stderr)
            for level in ('instance', 'article', 'settings', 'theme', 'default'):
                self.assertIn(level, result.stdout, level)
            self.assertIn('> settings', result.stdout,
                          'the human format has to mark the winner, or the '
                          'chain is a list of values with no verdict')


class RegressionFixes(unittest.TestCase):
    """Black-box regression tests for definite bugs that were fixed.

    Each test asserts the CORRECT (post-fix) behaviour. They were written
    after confirming the bug was reproducible (the buggy code failed the
    assertion); they now pass and must never break again."""

    def _series(self, tmp, articles, md_for):
        root = Path(tmp)
        (root / 'sources').mkdir(parents=True, exist_ok=True)
        series = []
        for name, md in md_for.items():
            dest = name.replace('.md', '.html')
            (root / 'sources' / name).write_text(md, encoding='utf-8')
            series.append({'page_dest': dest, 'page_source': name,
                           'nav_title': name[0].upper(), 'nav_desc': name[0]})
        (root / 'series.json').write_text(
            json.dumps({'articles': series}), encoding='utf-8')
        return root

    def _build_html(self, tmp, md=None, extra=None):
        root = scaffold(tmp, md or (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\nslug: r203\n# A\n'))
        if extra:
            extra(root)
        r = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(r.returncode, 0, r.stderr)
        return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    # --- A1: main() crash on global-options-only invocation ---
    def test_a1_global_options_only_no_crash(self):
        for opt in (['--quiet'], ['--lang', 'fr'], ['--dry-run']):
            with self.subTest(opt=opt):
                result = run(*opt)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
                self.assertNotIn('IndexError', result.stderr)
                self.assertIn('command', result.stderr.lower())

    # --- A2: --drafts-only manifest undercount ---
    def test_a2_drafts_only_manifest_keeps_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'active.md': ('<!-- lwp:meta -->\npage_dest: active.html\n'
                              'page_title: T\nnav_title: A\nnav_desc: A\n'
                              'status: active\n---\n\nslug: r204\n# A\n'),
                'draft.md': ('<!-- lwp:meta -->\npage_dest: draft.html\n'
                             'page_title: T\nnav_title: D\nnav_desc: D\n'
                             'status: draft\n---\n\nslug: r205\n# D\n'),
            })
            r1 = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertTrue((root / 'public' / 'active.html').exists())
            r2 = run('build', str(root), '--drafts-only',
                     '--output', str(root / 'public'))
            self.assertEqual(r2.returncode, 0, r2.stderr)
            r3 = run('clean', str(root), '--force')
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertTrue(
                (root / 'public' / 'active.html').exists(),
                'active.html was wrongly deleted as an orphan by clean --force')

    # --- B2: GFM trailing-pipe must not add an empty column ---
    def test_b2_table_trailing_pipe_no_extra_column(self):
        md = ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
              'nav_title: A\nnav_desc: A\n---\n\nslug: r206\n# T\n\n'
              '| H1 | H2 | H3 |\n| --- | --- | --- |\n'
              '| a | b | c |\n| d | e | f |\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            r = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(r.returncode, 0, r.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            m = re.search(r'<table[^>]*>.*?</table>', html, re.DOTALL)
            self.assertIsNotNone(m, 'no table in output')
            tbl = m.group(0)
            self.assertEqual(tbl.count('<th>'), 3,
                             f'header column count = {tbl.count("<th>")}')
            self.assertEqual(tbl.count('<td>'), 6,
                             f'body cell count = {tbl.count("<td>")}')

    # --- B3: multi-dot numbers rejected by length/ratio/angle types ---
    def test_b3_multi_dot_numbers_rejected(self):
        cases = [
            ('title1.size', '1.2.3rem', 'length'),
            ('page.leading', '1.2.3', 'ratio'),
            ('cover.bg.angle', '1.2.3deg', 'angle'),
        ]
        for prop, bad, kind in cases:
            with self.subTest(prop=prop, bad=bad):
                with tempfile.TemporaryDirectory() as tmp:
                    root = scaffold(tmp, (
                        '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                        'nav_title: A\nnav_desc: A\n---\n\nslug: r207\n# A\n'))
                    (root / 'templates').mkdir(exist_ok=True)
                    (root / 'templates' / 'settings.conf').write_text(
                        f'{prop}: {bad}\n', encoding='utf-8')
                    r = run('build', str(root), '--output', str(root / 'public'))
                    self.assertNotEqual(
                        r.returncode, 0,
                        f'{kind} {bad!r} should be rejected')
                    self.assertNotIn('Traceback', r.stderr)
                    out = ((root / 'public' / 'a.html').read_text()
                            if (root / 'public' / 'a.html').exists() else '')
                    self.assertNotIn(bad, out,
                                     f'{bad!r} leaked into the output HTML')

    # --- B4: corner click on .nav-buttons must not advance slide ---
    def test_b4_nav_buttons_in_is_interactive(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            i = html.find('isInteractive')
            self.assertNotEqual(i, -1)
            seg = html[i:i + 250]
            self.assertIn('.nav-buttons', seg)

    # --- B5: wake lock released on webkitfullscreenchange ---
    def test_b5_webkit_release_wake_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            i = html.find('webkitfullscreenchange')
            self.assertNotEqual(i, -1)
            seg = html[i:i + 850]
            self.assertIn('releaseWakeLock', seg)

    # --- B6: releaseWakeLock() must have a .catch() ---
    def test_b6_release_wakelock_catch(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            self.assertIn('release().catch', html)

    # --- B8: the generated <script> must be syntactically valid JS ---
    # A single bad character (e.g. an unescaped apostrophe inside a
    # single-quoted JS string literal) makes the whole script fail to parse,
    # silently killing fullscreen, the presenter panel and every nav handler.
    # Naive HTML-level assertions never catch this, so validate the script
    # for real when a JS engine is available.
    def test_b8_generated_script_is_valid_javascript(self):
        lwp = load_lightwebpres_module()
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            ok, detail = lwp.validate_page_scripts(html)
            self.assertTrue(ok, detail)

    def test_apply_strings_escapes_quotes_in_string_literals(self):
        # Root cause of the fullscreen break: a locale string holding an
        # apostrophe (or a quote, or a backslash) must not break the JS/HTML
        # string literal it is substituted into. apply_strings must escape it
        # quote/backslash-aware, so the placeholder can never again kill the
        # whole <script>.
        lwp = load_lightwebpres_module()
        value = "l'index \"quote\" \\ back"
        strings = {'weird': value}
        for q in ("'", '"'):
            tmpl = 'var s = ' + q + '{{str_weird}}' + q + ';'
            out = lwp.apply_strings(tmpl, strings)
            self.assertNotIn('{{str_weird}}', out)
            escaped = value.replace('\\', '\\\\').replace(q, '\\' + q)
            self.assertEqual(out, 'var s = ' + q + escaped + q + ';')
            ok, detail = lwp.validate_page_scripts('<script>' + out + '</script>')
            self.assertTrue(ok, detail)
        # Bare (unquoted, HTML text) placeholder is substituted verbatim:
        self.assertEqual(
            lwp.apply_strings('<p>{{str_weird}}</p>', strings),
            '<p>' + value + '</p>')

    # --- B7: contextmenu handler clears the pending left-click timer ---
    def test_b7_contextmenu_clears_timer(self):
        """A window of 400 characters after the listener's name used to
        stand in for "inside the handler". It is not the same thing:
        adding a paragraph of comment to that handler pushed
        `clearTimeout` out of the window and failed a guard about
        behaviour that had not changed. The window now ends where the
        handler does — at the `});` that closes it — so a comment can grow
        and a moved call still fails.

        The timer the handler used to clear is gone: the left click
        became instant in 0.43.7 (no 250 ms guess; the glide is a
        200 ms animation of the deck's own, and a click during the
        glide jumps straight to its target), so the contextmenu
        handler has nothing left to cancel. What it must still do is
        step back a card — the mirror of the left button, glide
        included: the guard pins that, and the absence of any
        `clearTimeout` is asserted as part of it: a timer that comes
        back must come back with its own guard, not inside this one."""
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            i = html.find("'contextmenu'")
            self.assertNotEqual(i, -1)
            end = html.find('\n  });', i)
            self.assertNotEqual(end, -1, 'the contextmenu handler has no end')
            handler = html[i:end]
            self.assertIn('goTo(base - 1, isScrolling)', handler)
            self.assertNotIn('clearTimeout', handler)

    # --- B9: audit must not false-positive a retired name as a prefix ---
    def test_b9_audit_no_false_retired_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\nslug: r208\n# A\n'),
            })
            (root / 'templates').mkdir(exist_ok=True)
            # --page-content-max is current; --content-max is retired and must
            # NOT be flagged just because its name is a substring.
            (root / 'templates' / 'custom.css').write_text(
                'x { --page-content-max: 40rem; }\n', encoding='utf-8')
            r = run('audit', str(root))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('--content-max', r.stdout + r.stderr)
            # Sanity: a genuine retired variable is still flagged.
            (root / 'templates' / 'custom.css').write_text(
                'x { --ink: #111; }\n', encoding='utf-8')
            r2 = run('audit', str(root))
            self.assertIn('--ink', r2.stdout + r2.stderr)

    # --- B10: a bad property reference surfaces a clean error, no traceback ---
    def test_b10_bad_reference_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\nslug: r209\n# A\n'),
            })
            (root / 'templates').mkdir(exist_ok=True)
            (root / 'templates' / 'settings.conf').write_text(
                'kicker.fg: notacolor\n', encoding='utf-8')
            r = run('resolve', str(root), 'kicker.fg')
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn('Traceback', r.stderr)
            self.assertNotIn('KeyError', r.stderr)

    # --- B18: check must honor --no-nav (else spurious [DRIFT]) ---
    def test_b18_check_honors_no_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\n'
                         '<!-- lwp:slide:cover -->\nslug: k264\nkicker: T\n# Title\n'
                         'summary: S.\n\n---\n\n'
                         '<!-- lwp:slide:series-nav -->\nslug: k265\n'),
                'b.md': ('<!-- lwp:meta -->\npage_dest: b.html\npage_title: T\n'
                         'nav_title: B\nnav_desc: B\n---\n\nslug: r210\n# B\n'),
            })
            r1 = run('build', str(root), '--no-nav',
                     '--output', str(root / 'public'))
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = run('verify', str(root), '--no-nav',
                     '--output', str(root / 'public'))
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotIn('[DRIFT]', r2.stdout + r2.stderr)

    # --- B21: copy_images must refuse a self-referential symlink ---
    def test_b21_self_referential_symlink(self):
        import subprocess as _sp
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\nslug: r211\n# A\n'),
            })
            img = root / 'sources' / 'img'
            img.mkdir()
            # Self-referential: img/loop -> img/  (would recurse forever).
            (img / 'loop').symlink_to(img)
            try:
                proc = _sp.run(
                    [sys.executable, str(EXECUTABLE), 'build', str(root),
                     '--output', str(root / 'public')],
                    capture_output=True, text=True, timeout=30)
            except _sp.TimeoutExpired:
                self.fail('build hung on self-referential symlink '
                          '(infinite recursion)')
            self.assertEqual(proc.returncode, 0, proc.stderr)


    def test_audit_templates_restricts_to_presentation(self):
        # --templates (DECISION-CLI.md §3) restricts `audit` to the
        # presentation/template layer and skips per-article editorial checks.
        md = ('<!-- lwp:meta -->\npage_dest: a.html\npage_source: a.md\n'
              'nav_title: A\nnav_desc: A\n---\n\n'
              '<!-- lwp:slide:standard -->\nslug: k266\n# Title\nsummary: S.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md, source_name='a.md', file_name='a.html')
            full = run('audit', str(root))
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertIn('no cover slide', full.stderr,
                          'editorial check should fire without --templates')
            tmpl = run('audit', str(root), '--templates')
            self.assertEqual(tmpl.returncode, 0, tmpl.stderr)
            self.assertNotIn('no cover slide', tmpl.stdout,
                             '--templates must skip editorial checks')

class AuditKeepsItsPromiseWhenTheSeriesFightsBack(unittest.TestCase):
    """`audit` promises, in §11.5 and in the guide, to report and exit 0
    whatever it finds. An adversarial pass over the delivered lot found
    four places where it did not, and each of the four is the same shape:
    a fault the render can see, on a path the report never reaches.

    These are not hypotheticals. Every case here was measured on the
    delivered executable before the repair, and the measurement is in the
    docstring of the test that pins it."""

    def _series(self, tmp):
        root = str(Path(tmp) / 's')
        self.assertEqual(run('init', root).returncode, 0)
        self.assertEqual(run('demo', root).returncode, 0)
        return root

    def _mark_draft(self, root, index=1):
        path = Path(root) / 'series.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data.get('articles', data) if isinstance(data, dict) else data
        entries[index]['status'] = 'draft'
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return entries[index]['page_source']

    def test_a_draft_is_audited_like_any_other_article(self):
        """The gate's worst case: `--strict` green on a series whose fault
        is sitting in the article still being worked on. Measured before
        the repair, on one article and one fault, changing only `status`:
        active gave one warning and `--strict` exit 1, draft gave
        `No warnings` and exit 0 — while `build --include-drafts` printed
        the warning plainly. §20.6 says nothing is excluded from an audit,
        and `audit` has no `--include-drafts` to reach it with."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            source = self._mark_draft(root)
            article = Path(root) / 'sources' / source
            article.write_text(
                article.read_text(encoding='utf-8').replace(
                    '<!-- lwp:slide:cover -->',
                    '<!-- lwp:slide:cover -->\nslug: k267\nfact-label: X', 1),
                encoding='utf-8')
            plain = run('audit', root)
            self.assertIn('never rendered', plain.stderr,
                          'the draft was rendered out of the audit:\n'
                          + plain.stdout + plain.stderr)
            self.assertEqual(plain.returncode, 0)
            self.assertEqual(run('audit', root, '--strict').returncode, 1,
                             '--strict passed on a fault in a draft')

    def test_a_source_that_is_not_text_is_a_finding_not_a_stop(self):
        """Measured before the repair: one article saved in the wrong
        encoding took `audit` down at exit 1, with no summary line at all,
        on the same run where the guide promises exit 0 whatever it finds.
        `read_text_file` refusing and exiting is right for a build, which
        has nothing to produce from it, and wrong for a report."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (Path(root) / 'sources' / 'first_article.md').write_bytes(
                b'<!-- lwp:meta -->\npage_title: X\n---\n\n'
                b'<!-- lwp:slide:cover -->\nslug: k268\n# T\nsummary: \xff not utf-8\n')
            plain = run('audit', root)
            self.assertEqual(plain.returncode, 0,
                             'audit stopped on a file it could not read:\n'
                             + plain.stdout + plain.stderr)
            self.assertIn('warning(s)', plain.stdout,
                          'audit ended without a summary')
            self.assertEqual(run('audit', root, '--strict').returncode, 1)

    def test_the_unreadable_memo_does_not_outlive_the_run(self):
        """The memo is a module global, and the executable is loaded as a
        MODULE by the web interface, where the process outlives a command.
        A memo that survived would keep calling a file unreadable after its
        author had fixed it and asked again — a report that cannot be
        corrected, which is worse than the repeated line the memo exists to
        avoid. Measured on the module: without the clear, the second read
        of a repaired file still came back None."""
        lwp = load_lightwebpres_module()
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'bad.md'
            bad.write_bytes(b'\xff not utf-8')
            self.assertIsNone(lwp.audit_read(bad))
            bad.write_text('readable now\n', encoding='utf-8')
            self.assertIsNone(lwp.audit_read(bad),
                              'the memo is not holding within a run, so the '
                              'file would be named once per pass')
            lwp._AUDIT_UNREADABLE.clear()
            self.assertEqual(lwp.audit_read(bad), 'readable now\n',
                             'a repaired file stayed unreadable across runs')

    def test_a_run_clears_the_memo_before_it_reads_anything(self):
        """The clear has to be in cmd_audit, not left to the caller: a
        long-lived process is exactly the one that never thinks to."""
        source = EXECUTABLE.read_text(encoding='utf-8')
        body = source[source.index('def cmd_audit('):]
        self.assertIn('_AUDIT_UNREADABLE.clear()',
                      body[:body.index('\n    for entry in articles:')],
                      'cmd_audit reads articles before clearing the memo')

    def test_an_unreadable_file_is_named_once_per_run_not_once_per_pass(self):
        """Three passes reach for the same article — the syntax pass, the
        judgement pass, the render — so one unreadable file used to print
        three identical [ERROR] lines. Two remain by construction: audit's
        own read, and the build path's refusal during the render, which is
        not audit's to silence."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (Path(root) / 'sources' / 'first_article.md').write_bytes(
                b'<!-- lwp:meta -->\npage_title: X\n---\n\n'
                b'<!-- lwp:slide:cover -->\nslug: k269\n# T\nsummary: \xff not utf-8\n')
            stderr = run('audit', root).stderr
            self.assertLessEqual(stderr.count('not valid UTF-8'), 2,
                                 'one file named once per pass:\n' + stderr)

    def test_a_missing_source_is_counted_not_only_logged(self):
        """The summary-contradicting-stderr defect, still alive twenty
        lines above the finding written to kill it. Reachable through an
        `ignored` article, whose missing source never reaches the render
        either: audit printed an [ERROR], then `No warnings`, and exited 0
        under `--strict`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            path = Path(root) / 'series.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            entries = (data.get('articles', data)
                       if isinstance(data, dict) else data)
            entries[1]['status'] = 'ignored'
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
            (Path(root) / 'sources' / entries[1]['page_source']).unlink()
            plain = run('audit', root)
            self.assertIn('page_source not found', plain.stderr)
            self.assertNotIn('No warnings', plain.stdout,
                             'audit called a series clean while printing an '
                             '[ERROR] about it:\n' + plain.stdout)
            self.assertEqual(plain.returncode, 0)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)

    def test_one_legacy_stylesheet_is_one_finding(self):
        """`judge_resolved_theme` keeps the one-mistake-one-finding rule
        inside a pass — "eight warnings for one typo is how a report stops
        being read" — and rendering broke it between passes. A legacy
        `templates/style.css` was reported by audit_presentation, which
        also names every retired variable it still references, and again
        by the build path, whose own message defers to that one and then
        repeats it. Two lines, two counts, one file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (Path(root) / 'templates' / 'style.css').write_text(
                '/* legacy */ .x { color: var(--marker); }\n',
                encoding='utf-8')
            plain = run('audit', root)
            report = plain.stdout + plain.stderr
            named = [line for line in report.splitlines()
                     if line.startswith('[WARNING]') and 'style.css' in line]
            self.assertEqual(len(named), 1,
                             'one file, two findings:\n' + '\n'.join(named))
            self.assertIn('--marker', report,
                          'the surviving message is the poorer of the two: '
                          'it no longer names the retired variables')
            counted = re.search(r'(\d+) warning\(s\)', plain.stdout)
            self.assertEqual(counted.group(1), '1', plain.stdout)

    def test_build_progress_does_not_leak_into_the_report(self):
        """Since the render pass calls load_build_context, its progress
        lines print in the middle of audit's report — and they were bare
        print() calls, so `--quiet` could not see them. That is the exact
        defect log()'s own comment describes: "progress went out through
        bare print() calls the flag could not see".

        On an `ignored` article rather than a draft, and mutation is why:
        audit now renders WITH drafts, so the `[draft]` line it used to
        leak is no longer reachable from here at all and a test written on
        it passes whatever the print does. `ignored` stays filtered — it
        is out of the chain by definition — so it is the case that still
        exercises the flag."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            path = Path(root) / 'series.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            entries = (data.get('articles', data)
                       if isinstance(data, dict) else data)
            entries[1]['status'] = 'ignored'
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
            loud = run('audit', root)
            self.assertIn('[ignored]', loud.stdout,
                          'the premise changed: this line is what --quiet '
                          'has to be able to suppress')
            quiet = run('audit', root, '--quiet')
            self.assertNotIn('[ignored]', quiet.stdout,
                             'build progress survived --quiet inside the '
                             'audit report:\n' + quiet.stdout)
            self.assertIn('No warnings', quiet.stdout,
                          'the summary is the command answer and must stay')

    def test_a_draft_cannot_take_the_series_index_out_of_the_audit(self):
        """The regression the draft repair introduced, and the worst kind:
        a fix that reopens the defect it was part of closing. Rendering
        with drafts is right, but `resolve_index_claim` then let a DRAFT
        named index.html claim the index — so `build_index`, and
        `templates/index_extra.html` with it, were never rendered at all.
        Measured: a fatal in that file, `build` exit 1, audit reporting
        `No warnings` and exit 0 under --strict. The claim is resolved
        against what a build would ship, not against what audit renders."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / 's')
            self.assertEqual(run('init', root).returncode, 0)
            (Path(root) / 'sources').mkdir(exist_ok=True)
            (Path(root) / 'sources' / 'index.md').write_text(
                '<!-- lwp:meta -->\npage_title: Solo\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: k270\n# Solo\nsummary: One.\n',
                encoding='utf-8')
            path = Path(root) / 'series.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['articles'] = [{'page_source': 'index.md', 'status': 'draft'}]
            path.write_text(json.dumps(data, indent=2), encoding='utf-8')
            (Path(root) / 'templates' / 'index_extra.html').write_bytes(
                b'<div>\xff not utf-8</div>\n')
            self.assertEqual(run('build', root).returncode, 1,
                             'the premise changed: this still has to be fatal')
            plain = run('audit', root)
            self.assertIn('index does not build', plain.stderr,
                          'a draft claimed the index and took it out of the '
                          'audit:\n' + plain.stdout + plain.stderr)
            self.assertEqual(plain.returncode, 0)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)

    def test_a_fatal_draft_does_not_claim_the_series_is_broken(self):
        """Rendering drafts makes a draft's fatal reachable, and the
        series-wide sentence became false with it: `build` produces every
        other page and exits 0. A finding that is false is worse than one
        that is missing, so the draft gets its own sentence."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            source = self._mark_draft(root)
            article = Path(root) / 'sources' / source
            article.write_text(
                article.read_text(encoding='utf-8') + '\n<div>\n',
                encoding='utf-8')
            self.assertEqual(run('build', root).returncode, 0,
                             'the premise changed: a build without drafts '
                             'still has to succeed here')
            plain = run('audit', root)
            self.assertIn('this draft does not render', plain.stderr,
                          plain.stdout + plain.stderr)
            self.assertNotIn('the series does not build', plain.stdout,
                             'audit called the series broken while build '
                             'exits 0:\n' + plain.stdout)

    def test_an_unreadable_custom_css_is_counted_under_templates(self):
        """`--templates` does not render, and the render was the only pass
        that caught this file. Measured before the repair: `[ERROR]` on
        stderr, `No warnings` on stdout, `--strict` exit 0, on a series
        `build` refuses — the summary contradicting the message two lines
        above it, which is the defect this whole lot exists to remove."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (Path(root) / 'templates' / 'custom.css').write_bytes(
                b'/* mine */ .x { color: \xff\xfe; }\n')
            self.assertEqual(run('build', root).returncode, 1,
                             'the premise changed: this still has to be fatal')
            plain = run('audit', root, '--templates')
            self.assertNotIn('No warnings', plain.stdout,
                             'audit called a series clean that build '
                             'refuses:\n' + plain.stdout)
            self.assertEqual(plain.returncode, 0)
            self.assertEqual(
                run('audit', root, '--templates', '--strict').returncode, 1,
                '--strict passed on a stylesheet the build refuses')

    def test_a_missing_source_is_counted_once_not_once_per_pass(self):
        """The count is what --strict gates on, and the render fails on the
        very cause the syntax pass has already named. `already_said` covers
        warnings; a fatal arrives through the other door, so the caller
        tells the render it has named the cause itself."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            path = Path(root) / 'series.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            entries = (data.get('articles', data)
                       if isinstance(data, dict) else data)
            (Path(root) / 'sources' / entries[1]['page_source']).unlink()
            plain = run('audit', root)
            counted = re.search(r'(\d+) warning\(s\)', plain.stdout)
            self.assertIsNotNone(counted, plain.stdout)
            self.assertEqual(counted.group(1), '1',
                             'one missing file, one finding:\n'
                             + plain.stdout + plain.stderr)
            self.assertEqual(run('audit', root, '--strict').returncode, 1)


class TheReadabilityFloorReadsCssFunctionsCorrectly(unittest.TestCase):
    """`clamp`, `min` and `max` are three different questions, and were
    answered as one: take the first argument of whichever appears. That is
    right for `clamp(a, b, c)`, whose floor is `a`, and wrong both ways for
    the other two — measured on the delivered executable, `max(9px, 1rem)`
    renders at 16px and warned, `min(20px, 4vw)` can render at 8px and said
    nothing."""

    def _px(self, value):
        return load_lightwebpres_module()._absolute_size_px(value)

    def test_clamp_is_judged_on_its_floor(self):
        self.assertEqual(self._px('clamp(9px, 2vw, 20px)'), 9.0)

    def test_a_max_is_judged_on_its_largest_argument(self):
        """The false positive: this renders at 16px and cannot go below."""
        self.assertEqual(self._px('max(9px, 1rem)'), 16.0)

    def test_a_min_is_judged_on_its_smallest_argument(self):
        self.assertEqual(self._px('min(10px, 20px)'), 10.0)

    def test_a_relative_term_inside_a_max_floors_at_zero(self):
        """`max(12px, 1.5vmin)` is the catalogue's own idiom, and it really
        can render at 12px: a viewport can be arbitrarily small, so the
        relative term contributes zero and the floor is the largest of the
        absolute ones. A repair once had `max` refuse whenever an argument
        was relative, on the reasoning that an unknown might lift the
        render above the floor — which confuses the rendered value with the
        floor, and measured, turned the guard off for 1,856 of the
        catalogue's 2,030 size readings."""
        self.assertEqual(self._px('max(8px, 6.1vmin)'), 8.0)
        self.assertEqual(self._px('max(12px, 1.5vmin)'), 12.0)
        self.assertEqual(self._px('max(8px, 0.5em)'), 8.0)

    def test_a_relative_term_inside_a_min_leaves_it_unjudged(self):
        """The other direction, and it is not symmetric: a relative term
        inside a `min` puts the floor at zero, so every such value would
        warn. Nothing useful is left to say."""
        self.assertIsNone(self._px('min(20px, 4vw)'))

    def test_a_nested_function_is_split_on_its_own_commas(self):
        """Splitting on every comma reads `min(10px` as an argument and
        drops the rest, which is how a nested value silently becomes a
        different value."""
        self.assertEqual(self._px('max(1rem, min(10px, 20px))'), 16.0)
        self.assertEqual(self._px('clamp(min(9px, 11px), 2vw, 3rem)'), 9.0)

    def test_a_function_with_no_arguments_does_not_take_audit_down(self):
        """`LengthType.check` only asks for balanced parentheses and a body
        without dangerous punctuation, so `min()` reaches this function
        intact from a settings.conf. Reducing it over an empty sequence
        raised ValueError, and audit — whose whole contract is to report
        and exit 0 — died at exit 1 with no summary, on a series `build`
        compiled without complaint. `clamp` had the guard; its two
        neighbours did not."""
        for value in ('min()', 'max()', 'clamp()', 'max( , )', 'min(,)'):
            self.assertIsNone(self._px(value), value)

    def test_a_series_pinning_an_empty_function_is_reported_not_fatal(self):
        """The unit above proves the function; this proves the promise it
        broke, at the command."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / 's')
            self.assertEqual(run('init', root).returncode, 0)
            self.assertEqual(run('demo', root).returncode, 0)
            conf = Path(root) / 'templates' / 'settings.conf'
            conf.write_text(conf.read_text(encoding='utf-8')
                            + '\ntitle1.size: min()\n', encoding='utf-8')
            plain = run('audit', root)
            self.assertEqual(plain.returncode, 0,
                             'audit died on a value build accepts:\n'
                             + plain.stdout + plain.stderr)
            self.assertNotIn('internal error', plain.stderr)

    def test_the_floor_still_fires_on_what_it_was_written_for(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / 's')
            self.assertEqual(run('init', root).returncode, 0)
            self.assertEqual(run('demo', root).returncode, 0)
            conf = Path(root) / 'templates' / 'settings.conf'
            conf.write_text(conf.read_text(encoding='utf-8')
                            + '\nnote.size: min(20px, 3px)\n', encoding='utf-8')
            report = run('audit', root)
            self.assertIn('note.size', report.stdout + report.stderr)


class TheWarningLevelIsSpeltWhereContributorsWillReadIt(unittest.TestCase):
    """The whole collector rests on every warning going through
    log('warn', ...). log()'s own docstring said there was no warning
    level and to route anything meaning one through 'info' with a
    [WARNING] tag — six lines above the branch implementing 'warn'.

    A warning written that way prints, is silenced by --quiet, and is
    never counted by audit. The advice outlived the level it denied, and
    the lot that made the collector load-bearing is the one that had to
    kill it."""

    def test_no_source_comment_still_denies_the_warn_level(self):
        source = EXECUTABLE.read_text(encoding='utf-8')
        for claim in ("there is no 'warning'\n    level",
                      "There is no 'warn'",
                      'no warn level in log()'):
            self.assertNotIn(claim, source,
                             f'a comment still denies the level the '
                             f'collector hooks: {claim!r}')

    def test_a_warning_routed_the_old_way_would_not_be_collected(self):
        """Asserted rather than argued: this is what the removed advice
        produced, and why the advice was a trap and not a style note."""
        lwp = load_lightwebpres_module()
        with lwp.collect_warnings() as sink:
            lwp.log('info', '[WARNING] written the way the docstring said')
            lwp.log('warn', 'written the way the docstring says now')
        self.assertEqual(sink.messages,
                         ['written the way the docstring says now'])

    def test_the_collector_can_declare_what_was_already_said(self):
        lwp = load_lightwebpres_module()
        with lwp.collect_warnings(already_said=('seen this',)) as sink:
            lwp.log('warn', 'seen this one before')
            lwp.log('warn', 'but not this one')
        self.assertEqual(sink.messages, ['but not this one'])
        self.assertIsNone(lwp._WARN_SINK)


class AListItemKeepsTheLinesThatContinueIt(unittest.TestCase):
    """Reported from a 28-article corpus, where `build`, `verify` and
    `audit` were all green and 73 Markdown markers were visible on screen.

    An item used to be exactly one line. The continuation did not merely
    lose its wrapping: it became a paragraph of its own, emitted AFTER the
    list closed, so a list whose items wrapped came out as several
    one-item lists with paragraphs between them. Three losses, not one —
    the reading order, the structure a screen reader announces, and any
    emphasis spanning the two lines, which shipped as literal `**`."""

    def _render(self, body):
        lwp = load_lightwebpres_module()
        html = lwp.convert_markdown(body)
        return re.sub(r'\s+', ' ', html).strip()

    def test_an_indented_continuation_belongs_to_its_item(self):
        html = self._render('- Puce avec un **gras coupé\n'
                            '  par un retour à la ligne**.\n')
        self.assertIn('<strong>gras coupé par un retour à la ligne',
                      html, html)
        self.assertNotIn('**', html, 'markup shipped to the reader:\n' + html)

    def test_a_lazy_continuation_belongs_to_its_item(self):
        """CommonMark takes an unindented continuation too, and the corpus
        had both — a long item wraps wherever the editor wrapped it."""
        html = self._render('- Item deux, en continuation paresseuse\n'
                            'non indentée du tout.\n')
        self.assertIn('<li>Item deux, en continuation paresseuse non '
                      'indentée du tout.</li>', html, html)

    def test_a_wrapped_list_stays_one_list(self):
        """The structural half, and the one a reader with a screen reader
        pays for: three items used to become three one-item lists."""
        html = self._render('- Un, coupé\n  sur deux lignes.\n'
                            '- Deux, coupé\n  aussi.\n'
                            '- Trois simple.\n')
        self.assertEqual(html.count('<ul>'), 1, html)
        self.assertEqual(html.count('<li>'), 3, html)
        self.assertNotIn('</ul> <p>', html,
                         'a continuation was ejected after the list:\n' + html)

    def test_a_new_block_still_ends_the_item(self):
        """The other direction, and what stops this absorbing the file: the
        rule is _is_paragraph_continuation, shared with paragraphs rather
        than restated, so a heading, a fence, a table, a note body or the
        next item all close the item exactly as they close a paragraph."""
        html = self._render('- Un item.\n'
                            '\n'
                            'Un paragraphe séparé par une ligne vide.\n')
        self.assertIn('<p>Un paragraphe séparé', html, html)
        self.assertNotIn('<li>Un item. Un paragraphe', html, html)
        html = self._render('- Un item.\n### Un titre\n')
        self.assertIn('<h3', html, html)
        self.assertNotIn('<li>Un item. ### ', html, html)

    def test_an_ordered_list_wraps_the_same_way(self):
        html = self._render('1. Un numéroté coupé\n   sur deux lignes.\n'
                            '2. Un autre.\n')
        self.assertEqual(html.count('<ol>'), 1, html)
        self.assertIn('<li>Un numéroté coupé sur deux lignes.</li>', html, html)


class AFieldSaysWhenItIsCarryingMarkupItWillNotRender(unittest.TestCase):
    """A field is a value — one physical line, taken verbatim — and the
    free text beside it is Markdown, with nothing in the file marking the
    border. The border is not where an author would guess either: a field
    passes raw HTML straight through (`page_title: A<br>B` is in the
    README), so someone who finds markup "works" there generalises.

    Measured on the reporting corpus: 32 fields had accumulated it across
    16 pages, `source:` lines among them — the exact place a reader
    checking a claim looks."""

    def _series(self, tmp, body):
        root = str(Path(tmp) / 's')
        self.assertEqual(run('init', root).returncode, 0)
        self.assertEqual(run('demo', root).returncode, 0)
        (Path(root) / 'sources' / 't.md').write_text(body, encoding='utf-8')
        path = Path(root) / 'series.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        entries = data.get('articles', data) if isinstance(data, dict) else data
        entries.append({'page_source': 't.md'})
        path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return root

    HEAD = ('<!-- lwp:meta -->\npage_title: T\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: k271\n# T\nsummary: s\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: k272\n')

    def test_every_field_that_ships_markup_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.HEAD + (
                '## Un **gras** dans un titre\n'
                'summary: Un **gras** dans un summary\n'
                'highlight-caption: un `code` dans une légende\n'
                'fact-label: Le fait\n'
                'source: Voir [la source](https://example.org)\n\n'
                'Le corps, lui, rend **le gras** correctement.\n'))
            report = run('audit', root).stderr
            for field in ('## title', 'summary', 'highlight-caption', 'source'):
                self.assertIn(f'`{field}` contains', report,
                              f'{field} ships its markup unnamed:\n' + report)
            # And the page really does carry it, which is the whole point.
            self.assertEqual(run('build', root).returncode, 0)
            page = (Path(root) / 'public' / 't.html').read_text(encoding='utf-8')
            self.assertIn('<h2>Un **gras** dans un titre</h2>', page)

    def test_free_text_beside_the_field_is_not_touched(self):
        """The guard has to know which side of the border an occurrence
        fell on, which is why it reads the PARSED slide and not the source
        — the same `**` two lines down is a real emphasis."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.HEAD + (
                '## Un titre propre\nfact-label: Le fait\n\n'
                'Le corps avec **du gras**, de l\'`inline code` et un '
                '[lien](https://example.org).\n'))
            self.assertNotIn('contains', run('audit', root).stdout)

    def test_an_unpaired_marker_is_not_a_lost_emphasis(self):
        """`2 ** 8` is arithmetic and `**kwargs` is Python. Warning on them
        is the noise that gets a check switched off, so only PAIRED
        markers count — measured against a caption documenting Python."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, self.HEAD + (
                '## Un titre propre\n'
                'highlight: 2 ** 8\n'
                'highlight-caption: ce que **kwargs déballe\n'
                'fact-label: Le fait\n\nDu corps.\n'))
            self.assertNotIn('contains', run('audit', root).stdout)

    def test_the_delivered_demo_raises_none_of_this(self):
        """The guard that keeps the check honest: a warning on our own
        example content would mean the rule is wrong, not the content."""
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / 's')
            self.assertEqual(run('init', root).returncode, 0)
            self.assertEqual(run('demo', root).returncode, 0)
            self.assertIn('No warnings', run('audit', root).stdout)

if __name__ == '__main__':
    unittest.main()
