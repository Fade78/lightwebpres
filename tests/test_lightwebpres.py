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
import json
import os
import inspect
import re
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
    (root / 'articles').mkdir(parents=True, exist_ok=True)
    (root / 'articles' / source_name).write_text(article_md, encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Une question ?\n'
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
            '<!-- lwp:slide:cover -->\nkicker: Shared\n# Shared\n'
            'summary: Common content.\n\n---\n\n'
            '<!-- lwp:slide -->\ntags: EN Français_v2\n'
            'kicker: English\n## Variant\nsummary: Variant content.\n\n---\n\n'
            '<!-- lwp:slide -->\ntags: excluded\n## Removed\n'
            'summary: This must never be emitted.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\ntags: EXCLUDED\n'
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
        self.assertIn('id="s1"', html)
        self.assertIn('id="s2"', html)
        self.assertNotIn('id="s3"', html)

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

    def test_lang_tag_selects_a_different_typography_pack_per_slide(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Tags\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\n# Cover\nsummary: English.\n\n---\n\n'
            '<!-- lwp:slide -->\ntags: EN\n## English\nsummary: English.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n\n---\n\n<!-- lwp:slide:full-article -->\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_duplicate_full_article_slides_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: art1.md\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: art2.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art1.md').write_text('CONTENT ONE\n', encoding='utf-8')
            (root / 'articles' / 'art2.md').write_text('CONTENT TWO\n', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_duplicate_series_nav_slides_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n\n---\n\n<!-- lwp:slide:series-nav -->\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_md_must_start_with_meta_block(self):
        md = '---\n\n<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
            'This text should never appear nor be silently ignored.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_series_json_rejects_duplicate_file_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
            )
            (root / 'articles' / 'a1.md').write_text(md, encoding='utf-8')
            (root / 'articles' / 'a2.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No warnings', result.stdout)

    def test_audit_warns_when_no_cover(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stdout)

    def test_audit_warns_when_cover_not_first(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T2\n# Cover title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('is not a cover', result.stdout)

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
            self.assertIn("generated for theme 'nord'", result.stdout)
            self.assertIn("declares 'evergreen'", result.stdout)

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
            self.assertIn('summary.color', result.stdout)
            self.assertIn('unknown property', result.stdout)

    def test_audit_does_not_crash_when_series_json_omits_file(self):
        """§20.3.1: series.json needs only `source` — audit must resolve
        `file` (resolve_article_fields()) before reading entry['file'],
        not assume it's always explicitly present like pre-v0.5.0. Uses a
        cover-less article so the warning path (the one that actually
        reads entry['file']) is exercised, not just the "no warnings" one
        where it's never dereferenced."""
        md = (
            '<!-- lwp:meta -->\npage_title: Test\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir(parents=True)
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            (root / 'series.json').write_text(
                json.dumps({'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('a.html', result.stdout)
            self.assertIn('no cover slide', result.stdout)


class HighlightField(unittest.TestCase):
    """§4.3: the highlight/highlight-caption fields (renamed from the former
    'mesure' naming) must actually render, and must be omitted when absent."""

    def test_highlight_renders_figure_and_caption(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nhighlight: 42 %\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nsummary: No highlight here.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="highlight"', html)


_MINIMAL_MD = (
    '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
    '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n'
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
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(_MINIMAL_MD, encoding='utf-8')
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
            (root / 'articles').mkdir()
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
            '<!-- lwp:slide -->\nkicker: T\n## S\nfact-label: F\n'
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
        '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
        '<!-- lwp:slide -->\nkicker: T\n## Two\nsummary: S.\n\n---\n\n'
        '<!-- lwp:slide -->\nkicker: T\n## Three\nsummary: S.\n'
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
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(_MINIMAL_MD, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Magnifique !\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: ' + body + '\n'
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
            '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art.md').write_text(body, encoding='utf-8')
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
            self.assertTrue((root / 'articles' / 'img' / 'demo-figure.svg').exists())
            first = (root / 'articles' / 'first.md').read_text(encoding='utf-8')
            self.assertIn('date:', first)
            self.assertIn('comment:', first)
            self.assertIn('Demo site generated in public/', result.stdout)

    def test_check_exit_code_is_exactly_one_with_diff_hunk(self):
        md = _MINIMAL_MD.replace('Summary.', 'Original.')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            (root / 'articles' / 'a.md').write_text(
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
            '<!-- lwp:slide -->\nkicker: T\n## Standard only\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            (root / 'articles' / 'b.md').write_text(md_no_cover, encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({'articles': [
                {'page_source': 'b.md'},
            ]}), encoding='utf-8')
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stdout)
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
            (root / 'articles').mkdir()
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

    def test_no_share_button_on_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            index = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('id="navShare"', index)

    def test_series_nav_status_strings_reach_output(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
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
            '<!-- lwp:slide:cover -->\nkicker: Base tag\nkicker: Override tag\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n'
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
    """§9.2.1: the share matrix's slide scope is disabled by slide TYPE
    (cover, series-nav), not by position — slide order is free (§4.4)."""

    def test_nav_js_tests_cover_class_not_first_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn("classList.contains('slide-cover')", html)
            self.assertNotIn("s.id === 's1'", html)


class CoverIgnoredFieldsWarn(unittest.TestCase):
    """A cover renders only tag/#/summary(+comment). The other standard
    fields are accepted with a WARNING, not an error: toggling a slide
    between standard and cover while drafting is a normal workflow."""

    def test_standard_fields_on_cover_warn_but_build(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n'
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
            '<!-- lwp:slide:cover -->\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide:covre -->\n## Second\n'
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
            '<!-- lwp:slide:cover -->\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide -->\n## Standard\nFree text.\n\n'
            '---\n\n'
            '<!-- lwp:slide:series-nav -->\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: a_article.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'a_article.md').write_text(
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


class SeriesNavFullArticleStrictContent(unittest.TestCase):
    """§22.8/§22.9: series-nav and full-article slides render none of
    their own content beyond their directives — unrecognized lines are
    fatal (they used to vanish silently). comment: is recognized on
    every slide type, these two included."""

    def _build(self, tmp, slide_block, extra_files=None):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            + slide_block
        )
        root = scaffold(tmp, md)
        for name, content in (extra_files or {}).items():
            (root / 'articles' / name).write_text(content, encoding='utf-8')
        return root, run('build', str(root), '--output', str(root / 'public'))

    def test_stray_text_in_series_nav_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(tmp, '<!-- lwp:slide:series-nav -->\nSome stray text.\n')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('never renders', result.stderr)
            self.assertIn('Some stray text.', result.stderr)

    def test_stray_field_in_full_article_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(
                tmp, '<!-- lwp:slide:full-article -->\narticle: art.md\nkicker: Oops\n',
                extra_files={'art.md': '# Art\n\nBody.\n'})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('never renders', result.stderr)

    def test_article_directive_on_series_nav_is_fatal(self):
        # article: only means something on a full-article slide.
        with tempfile.TemporaryDirectory() as tmp:
            _, result = self._build(tmp, '<!-- lwp:slide:series-nav -->\narticle: art.md\n')
            self.assertNotEqual(result.returncode, 0)

    def test_comment_is_recognized_and_never_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, result = self._build(
                tmp,
                '<!-- lwp:slide:series-nav -->\ncomment: nav review note\n\n---\n\n'
                '<!-- lwp:slide:full-article -->\narticle: art.md\ncomment: article review note\n',
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
            '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        )
        root = scaffold(tmp, md)
        (root / 'articles' / 'art.md').write_text('# T\n\n' + body, encoding='utf-8')
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
            '<!-- lwp:slide -->\nkicker: T\n## Slide\nfact-label: FACT\n'
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
        result = run('--version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LightWebPres v', result.stdout)
        # Version is not buried in help: --version prints only the version.
        self.assertNotIn('COMMANDS', result.stdout)

    def test_help_contains_version_in_header(self):
        result = run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LightWebPres v', result.stdout)

    def test_legacy_install_emits_warn_and_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / 's')
            result = run('install', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARN]', result.stderr)
            self.assertIn('deprecated', result.stderr)
            self.assertIn('init', result.stderr)

    def test_legacy_check_emits_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            # Build once so check has something to compare.
            run('build', str(root), '--output', str(root / 'public'))
            result = run('check', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARN]', result.stderr)
            self.assertIn('verify', result.stderr)

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

    def test_verbose_is_accepted(self):
        # --verbose is accepted globally (Phase 2 wires it; verbose messages
        # are added as the codebase grows).
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            result = run('--verbose', 'build', str(root),
                         '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_strict_audit_fails_on_warnings(self):
        # --strict makes audit exit 1 when warnings are emitted (DECISION §1
        # Phase 2). A series with no cover slide triggers a warning.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_source: a.md\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:standard -->\n# Title\nsummary: S.\n'
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
        # --no-nav (DECISION §4): the placeholder is replaced by an empty
        # string, the container (<h2> + <div class="series-list">) stays.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_source: a.md\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md, source_name='a.md', file_name='a.html')
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--no-nav')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            # The container stays (the <div class="series-list"> is in the
            # HTML body, not just the CSS).
            self.assertIn('class="series-list"', html)
            # No actual nav links: <a class="series-link" ...> elements are
            # gone (the CSS still mentions .series-link, but no <a> uses it).
            self.assertNotIn('<a href', html.split('series-list', 1)[1].split('</div>', 1)[0]
                             if 'series-list' in html else '')

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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title A\nsummary: S.\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_source: b.md\n'
            'nav_title: B\nnav_desc: B\nstatus: draft\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title B\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
            (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
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
        # --open (DECISION §1 Phase 3): opens the browser on the result.
        # We mock webbrowser.open via the LWP_BROWSER env var to avoid
        # actually opening a window in CI.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            # Point webbrowser at a no-op by setting BROWSER to /bin/true
            # (webbrowser.open falls back to the BROWSER env var on POSIX).
            env = {'BROWSER': '/bin/true'}
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--open', env=env)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_inline_images_embeds_base64_and_skips_img_dir(self):
        # --inline-images: images are embedded as base64 data URIs, and
        # the img/ directory is not copied to the output.
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: F\n## Fiche\nfact-label: L\n\n'
            'Inline ![red](img/red.png) and standalone:\n\n'
            '![Red](img/red.png "Cap")\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            # Create a minimal 1x1 PNG in articles/img/.
            (root / 'articles' / 'img').mkdir()
            (root / 'articles' / 'img' / 'red.png').write_bytes(
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

    def test_inline_images_off_by_default(self):
        # Without --inline-images: images stay as relative paths and
        # img/ is copied to the output (the standard behaviour).
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: F\n## Fiche\nfact-label: L\n\n'
            'Inline ![red](img/red.png) in text.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'img').mkdir()
            (root / 'articles' / 'img' / 'red.png').write_bytes(
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

    def test_clean_dry_run_lists_orphans(self):
        # `clean` (DECISION §3): dry-run by default, lists orphans.
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            # Drop an orphan file into public/.
            (root / 'public' / 'orphan.html').write_text('stale', encoding='utf-8')
            result = run('clean', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('orphan.html', result.stdout)
            self.assertIn('would be removed', result.stdout)
            # Dry-run: the orphan is still there.
            self.assertTrue((root / 'public' / 'orphan.html').exists())

    def test_clean_force_removes_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            (root / 'public' / 'orphan.html').write_text('stale', encoding='utf-8')
            result = run('clean', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'public' / 'orphan.html').exists())

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

    def test_watch_is_a_known_command(self):
        # `watch` is recognized and builds once before polling. We can't
        # test the infinite loop in CI, but we can check the initial build
        # runs by sending SIGINT immediately after.
        import signal
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            import subprocess as sp
            proc = sp.Popen([sys.executable, str(EXECUTABLE), 'watch',
                             str(root), '--output', str(root / 'public')],
                            stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            # Give it time to build once.
            import time as _time
            _time.sleep(1.5)
            proc.send_signal(signal.SIGINT)
            out, err = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, err)
            self.assertIn('[watch]', out)
            # The initial build wrote the page.
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_no_bare_filesystem_write_outside_helpers(self):
        """--dry-run relies on every filesystem write going through the
        _write_file/_mkdir/_copy/_copytree helpers. This AST test guards
        that no bare .write_text()/.mkdir()/shutil.copy* exists outside
        those four helpers in the executable (PLAN-CLI.md Phase 3).

        Uses a parent-tracking walk so the check is by function name, not
        by line number — robust against the helpers moving in the file."""
        import ast
        tree = ast.parse(EXECUTABLE.read_text(encoding='utf-8'))
        HELPER_NAMES = {'_write_file', '_mkdir', '_copy', '_copytree'}
        # The one allowed bare print to stderr is inside log() itself.
        ALLOWED_IN = HELPER_NAMES | {'log'}
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
                    if func.attr in ('write_text', 'mkdir'):
                        if enclosing not in ALLOWED_IN:
                            violations.append(
                                f'line {node.lineno}: .{func.attr}() in {enclosing}')
                    elif func.attr in ('copy', 'copy2', 'copyfile', 'copytree'):
                        if isinstance(func.value, ast.Name) and func.value.id == 'shutil':
                            if enclosing not in ALLOWED_IN:
                                violations.append(
                                    f'line {node.lineno}: shutil.{func.attr}() in {enclosing}')
        walk_with_scope(tree, None)
        self.assertFalse(violations,
                         f'Bare filesystem writes outside helpers found:\n'
                         + '\n'.join(violations))

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
        result = run('completion', '--shell', 'zsh')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('_lightwebpres_completion', result.stdout)
        self.assertIn('compdef _lightwebpres_completion lightwebpres',
                     result.stdout)

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
        _LEGACY_ALIASES, _SERIES_VERBS, _THEME_VERBS, and
        _COMMAND_OPTIONS. If a command or option is added to those
        tables but not to the completion script, this test fails —
        so an evolution of the CLI does not silently break completion."""
        lwp = load_lightwebpres_module()
        script = run('completion', '--shell', 'bash').stdout
        # Every shortcut and legacy alias must appear in the root list.
        for name in set(lwp._SHORTCUTS) | set(lwp._LEGACY_ALIASES):
            self.assertIn(name, script,
                           f'completion script missing root command {name!r}')
        # Every series verb must appear in the series list.
        for verb in lwp._SERIES_VERBS:
            self.assertIn(verb, script,
                           f'completion script missing series verb {verb!r}')
        # Every theme verb must appear in the theme list.
        for verb in lwp._THEME_VERBS:
            self.assertIn(verb, script,
                           f'completion script missing theme verb {verb!r}')
        # Every option from every command must appear in the options list.
        all_opts = set()
        for opts in lwp._COMMAND_OPTIONS.values():
            all_opts |= opts
        all_opts |= lwp._GLOBAL_OPTIONS
        all_opts |= lwp._VALUE_OPTIONS
        for opt in all_opts:
            self.assertIn(opt, script,
                           f'completion script missing option {opt!r}')

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
            '<!-- lwp:slide:full-article -->\narticle: missing_article.md\n'
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
            (root / 'articles' / 'mine.md').write_text(_MINIMAL_MD, encoding='utf-8')
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
            '<!-- lwp:slide -->\nkicker: T\n## Slide\nsummary: S.\nhighlight: 42 %\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
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
        slide = slide_body or '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            + slide
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art.md').write_text(article_body or '', encoding='utf-8')
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
        slide = ('<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n\n'
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
                '<!-- lwp:slide -->\n## Card\nfact-label: FACT\n'
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
            slide_body='<!-- lwp:slide:full-article -->\narticle: art.md\n')
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
            '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art.md').write_text(article_body, encoding='utf-8')
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
            '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art.md').write_text('```\nnever closed\n', encoding='utf-8')
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
        (root / 'articles').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
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
               '<!-- lwp:slide:cover -->\nkicker: T\n# {title}\n'
               'summary: Summary of {title}.\n')

    def series(self, tmp, entries):
        """entries: list of (page_source, page_dest[, extra dict])."""
        root = Path(tmp)
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        articles = []
        for source, dest, *rest in entries:
            title = source[:-3].upper()
            (root / 'articles' / source).write_text(
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
        (root / 'articles').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            f'nav_desc: Desc A\n{article_a_extra_meta}---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\n'
            'nav_title: Question ? Titre\nnav_desc: Alerte !\ncard_label: Numéro :\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
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
        (root / 'articles').mkdir()
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
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
                '<!-- lwp:slide:cover -->\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide -->\nkicker: New\n## A brand-new slide\nsummary: New body content.\n\n'
                '---\n\n<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md_a2, encoding='utf-8')

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
                '<!-- lwp:slide:cover -->\nkicker: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md_a2, encoding='utf-8')
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
                '<!-- lwp:slide:cover -->\nkicker: T\n# Article C\nsummary: Summary C.\n\n---\n\n'
            )
            (root / 'articles' / 'c.md').write_text(md_c, encoding='utf-8')
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
            self.assertTrue((root / 'articles').is_dir())
            # The author surface: values, rules, behaviour. No style.css —
            # the stylesheet is composed at build time and owns no file.
            self.assertTrue((root / 'templates' / 'settings.conf').exists())
            self.assertTrue((root / 'templates' / 'custom.css').exists())
            self.assertTrue((root / 'templates' / 'nav.js').exists())
            self.assertFalse((root / 'templates' / 'style.css').exists())
            self.assertTrue((root / 'language' / 'fr.json').exists())
            self.assertTrue((root / 'language' / 'en.json').exists())
            fr_pack = json.loads((root / 'language' / 'fr.json').read_text(encoding='utf-8'))
            self.assertIn('rules', fr_pack)
            self.assertIn('strings', fr_pack)
            en_pack = json.loads((root / 'language' / 'en.json').read_text(encoding='utf-8'))
            self.assertIn('rules', en_pack)
            self.assertIn('strings', en_pack)


class CheckDrift(unittest.TestCase):
    """§11.3: check must actually detect drift, not just report its absence."""

    def test_check_reports_drift_after_source_change(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Original summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            changed_md = md.replace('Original summary.', 'Changed summary.')
            (root / 'articles' / 'a.md').write_text(changed_md, encoding='utf-8')
            result = run('verify', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT]', result.stdout)


class RemainingTypographyRules(unittest.TestCase):
    """§7.2: the two French rules not already covered by
    test_typography_nbsp_before_double_punctuation."""

    def test_typography_nbsp_after_opening_quote(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: « Une citation.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('«\xa0Une citation.', html)

    def test_typography_nbsp_before_percent(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nhighlight: 50 %\nhighlight-caption: half\n'
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
            f'<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: {summary}\n'
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
                (root / 'articles' / name).write_text(content, encoding='utf-8')
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
            f'<!-- lwp:slide:cover -->\nkicker: {w("Tag")}\n# {w("Titre")}\nsummary: {w("Résumé")}\n'
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
            '<!-- lwp:slide -->\n'
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
            f'<!-- lwp:slide -->\nkicker: T\n## Titre\nsummary:{self.NBSP}Résumé\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            summary = re.search(r'<p class="summary">(.*?)</p>', html).group(1)
            self.assertTrue(summary.startswith(self.NBSP), repr(summary))

    def test_page_title_survives(self):
        md = (
            f'<!-- lwp:meta -->\npage_dest: a.html\npage_title: {self._wrap("Titre de page")}\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n'
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
            f'<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: {self._wrap("Description")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir(parents=True, exist_ok=True)
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: a_article.md\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: a_article.md\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n'
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

    def _two_article_series(self, tmp, meta_extra_b=''):
        root = Path(tmp)
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        summary = 'Environ ≈ 5 $ pour 170 000 000 vues, × 4 la dose, 170 millions de gens, 20 dollars.'
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\nkicker: T\n# Titre A\nsummary: {summary}\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            f'{meta_extra_b}---\n\n'
            f'<!-- lwp:slide:cover -->\nkicker: T\n# Titre B\nsummary: {summary}\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
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
            (root / 'articles').mkdir(parents=True, exist_ok=True)
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Titre à 50 % fini\nnav_title: A\n'
                'nav_desc: A\ntypo: off\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            (root / 'articles').mkdir(parents=True, exist_ok=True)
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
    templates/custom.css, behaviour through templates/nav.js. The old
    whole-file style.css override is gone (the sheet is composed in
    memory); its guarantee splits into the two tests below, one per
    author file."""

    def test_custom_css_rules_are_appended_after_the_composed_sheet(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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

    def test_settings_conf_values_reach_the_page(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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

    def test_index_extra_html_is_inserted_before_body_close(self):
        """§9.3: templates/index_extra.html, if present, is inserted as-is
        just before </body> on the index page only (not article pages)."""
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('</script>\n\n\n</body>', index_html)


class RefreshTemplates(unittest.TestCase):
    """§11.6 under the §9 rewrite: only nav.js is a tool-owned file on
    disk that an upgrade can refresh — the stylesheet is composed at
    build time, so it is always fresh by construction, and the author's
    settings.conf / custom.css are never the tool's to touch. The marker
    machinery (and its [SKIP]/exit-1 paths) is gone with the shared
    file that required it."""

    def test_requires_install_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('template', 'update', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('init', result.stderr.lower())

    def test_reports_up_to_date_when_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            before = {name: (root / 'templates' / name).read_text(encoding='utf-8')
                      for name in ('settings.conf', 'custom.css', 'nav.js')}
            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Already up to date', result.stdout)
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
            self.assertIn('[WARN]', result.stderr)
            self.assertIn('style.css is no longer read', result.stderr)
            self.assertEqual(style_path.read_text(encoding='utf-8'), legacy)

    def test_nav_js_is_replaced_and_previous_version_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('init', str(root)).returncode, 0)
            nav_path = root / 'templates' / 'nav.js'
            old_nav = nav_path.read_text(encoding='utf-8') + '\n// OLD-CUSTOM-NAV\n'
            nav_path.write_text(old_nav, encoding='utf-8')

            result = run('template', 'update', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

            refreshed = nav_path.read_text(encoding='utf-8')
            self.assertNotIn('OLD-CUSTOM-NAV', refreshed)
            backup = root / 'templates' / 'nav.js.bak'
            self.assertTrue(backup.exists())
            self.assertIn('OLD-CUSTOM-NAV', backup.read_text(encoding='utf-8'))


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
                          '# Cover\n\nsummary: s\n')
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
                          '# Cover\n\nsummary: s\n')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            (root / 'articles' / 'b.md').write_text(
                '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# B\nsummary: Summary.\n',
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
            for facet in ('data-polarity=', 'data-intensity=', 'data-hue='):
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
    ordinary component colours. The guarantee is unchanged: a white
    surface veil turns a card into an unreadable pale block over a dark
    page, which is exactly what a green-on-black candidate produced
    before the mechanism existed."""

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

        All 33 themes, both polarities, because stated this way the
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

    def test_every_theme_declares_its_intensity_rather_than_defaulting(self):
        """Intensity is the one facet that cannot be derived, so a silent
        default is a silent lie. The nine editor palettes omitted the key
        and all fell to `sober` — which put Monokai's card at
        [light/sober/neutral] directly above its own note, "among the most
        vivid of the lot"."""
        for slug, theme in self.lwp.THEMES.items():
            self.assertIn('intensity', theme, f'{slug} relies on the default')

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

    def test_every_theme_carries_the_three_facets(self):
        for key, theme in self.lwp.THEMES.items():
            facets = self.lwp.theme_facets(theme)
            self.assertIn(facets['polarity'], ('light', 'dark'), key)
            self.assertIn(facets['intensity'], ('sober', 'vivid', 'mono'), key)
            self.assertIsInstance(facets['hue'], str)

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
        for i, (slide, panel) in enumerate(zip(slides, ('cover', 'card')), 1):
            rendered = self.lwp.render_slide(slide, i, len(slides), engine,
                                             pack.get('strings', {}),
                                             absorb_punct=absorb,
                                             show_slide_num=True)
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
        on .preview means the notes became unreadable again."""
        head = self.lwp.TEMPLATE_THEMES_GALLERY_HEAD
        preview = head.split('.preview {', 1)[1].split('}', 1)[0]
        self.assertNotIn('transform', preview)
        self.assertIn('width: 340px', preview)

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
        self.assertEqual(len(roles), 6 * len(self.lwp.THEMES))
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

    def test_the_skill_does_not_promise_that_nothing_is_fatal(self):
        """It said so twice, and page_dest has three fatal paths."""
        self.assertNotIn('Nothing in this chain is fatal', self.skill)
        self.assertNotIn('Nothing here is ever a fatal build error', self.skill)

    def test_the_skill_names_no_field_the_parser_does_not_know(self):
        """The frontmatter advertised a `slide_title:` field that has
        never existed; an agent that skims only the description emits it,
        and free text on a cover slide is fatal."""
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
    """Every one of these was found by rendering real pages under all 33
    themes and MEASURING, after two earlier defects survived a check that
    looked at the gallery preview instead. They are grouped here because
    they share one cause: a rule that dims text — by an opacity, or by a
    fixed alpha nobody re-measured — reads as a style choice and is a
    contrast failure. Each test pins the value at its source, not its
    rendering, because the rendering is the consequence."""

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
        all 33 themes AND on the default palette. 'Faint' is a look, not
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
    # all 33 themes. The dict stays as the only door a future fade may
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

    def test_bold_fact_text_clears_aa_on_its_own_highlight_on_every_theme(self):
        """`fact.strong.bg` is the palette's `mark` and `fact.strong.fg`
        is the tone the theme chose for text on it, so the pair is the
        theme's own decision and nothing derives it right. catppuccin's
        measured 3.05:1 — Latte Yellow under a slate-blue ink — for every
        bold run in every fact box, with or without a note in it. All 33
        clear AA, so this is a floor and not a pinned set."""
        for slug in self.lwp.THEMES:
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


class ThemeInfoMeasuresRatherThanDeclares(unittest.TestCase):
    """§11.9.1. The accessibility level of a theme is COMPUTED from the
    property registry, never written into a THEMES entry. A hand-written
    label is right on the day it is typed and silent about every palette
    tweak afterwards, because nothing connects it to the colour it claims
    to qualify.

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
        """theme-info's JSON, through the CLI, as the GUI would get it."""
        result = run('theme-info', *args, '--format', 'json')
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
        """The whole claim, on all 33 themes at once: for the pair the
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
    # graphite is the reference for "clears AA everywhere"; nord is a
    # borrowed palette whose green accent sits at 1.79:1 on its own
    # near-white card, which §9.5.2 already records in its own words.
    PINNED_LEVELS = {
        'graphite': ('AA', 'AAA', 'pass'),
        'nord': ('fail', 'AAA', 'fail'),
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
        text = run('theme-info', 'nord')
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
        the intensity facet — the one that is declared and cannot be
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
            self.assertIsNone(report['facets']['intensity'])
            self.assertIsNone(report['label'])
            self.assertIn(report['facets']['polarity'], ('light', 'dark'))

    def test_custom_css_is_reported_as_unmeasured_only_once_it_has_rules(self):
        """custom.css is free CSS, outside the typed surface, so it is
        not measured — and saying nothing about that would be the
        hand-written label all over again. `install` writes the file with
        only its explanatory comment in it, so existence alone must not
        raise the flag or it would be raised on every series."""
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
            self.assertIn('NOT', run('theme-info', str(root)).stdout)

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
        self.assertEqual(report['schema'], 'lightwebpres.theme-info/1')
        self.assertEqual(report['lightwebpres_version'],
                         self.lwp.VERSION)
        self.assertEqual(set(report), self.ROOT_KEYS)
        self.assertEqual(set(report['target']), self.TARGET_KEYS)
        self.assertEqual(set(report['facets']),
                         {'polarity', 'intensity', 'hue'})
        self.assertEqual(set(report['palette']),
                         {'page', 'ink', 'ink-quiet', 'mark', 'call', 'affirm'})
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
        printed = dict(re.findall(r'^  (\S+)  \[(\S+)\]$', listing.stdout,
                                  re.MULTILINE))
        self.assertEqual(len(printed), len(self.lwp.THEMES))
        for slug in ('nord', 'graphite', 'terminal', 'pop-fuchsia'):
            facets = self._report(slug)['facets']
            self.assertEqual(
                '/'.join(facets[k] for k in ('polarity', 'intensity', 'hue')),
                printed[slug], slug)

    # --- errors ---

    def test_an_unknown_slug_is_a_named_error_listing_the_valid_ones(self):
        """The `themes` idiom for an unknown facet value: name what was
        rejected and list what is accepted. Answering "no such theme" and
        stopping would send a reader hunting for something that exists, a
        typo away."""
        result = run('theme-info', 'nrod')
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
            result = run('theme-info', tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn('init', result.stderr)

    def test_an_unknown_format_is_a_named_error(self):
        result = run('theme-info', 'nord', '--format', 'yaml')
        self.assertEqual(result.returncode, 1)
        self.assertIn('text', result.stderr)
        self.assertIn('json', result.stderr)

    def test_the_command_takes_no_option_it_does_not_own(self):
        result = run('theme-info', 'nord', '--theme', 'graphite')
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
                        'cmd_theme_info', 'cmd_series_theme'}

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

    @unittest.expectedFailure
    def test_a_built_page_is_byte_identical_to_the_previous_version_s(self):
        """The direct evidence, not a word list: the same series built
        by the executable as it stood at the last tagged release (v0.26.0),
        and by this one, compared byte for byte. --build-stamp is off by
        default, so there is no timestamp to excuse a difference.

        Expected to fail until v0.26.1 is tagged: the presenter pack
        refinements (right-click to go back, double-click for fullscreen,
        cursor hide in fullscreen, nav.js auto-update warning) change the
        nav.js and the page template. Once v0.26.1 is tagged, repoint
        this test at v0.26.1 and drop the @unittest.expectedFailure.

        Skipped, loudly, when the previous version cannot be reached --
        outside a git checkout there is nothing to compare against, and
        a comparison with nothing is not a pass."""
        previous = subprocess.run(
            ['git', 'show', 'v0.26.0:lightwebpres'], capture_output=True,
            cwd=str(EXECUTABLE.parent))
        if previous.returncode != 0:
            self.skipTest('no v0.26.0 tag to read the previous version from')
        with tempfile.TemporaryDirectory() as tmp:
            before_exe = Path(tmp) / 'lightwebpres-before'
            before_exe.write_bytes(previous.stdout)
            outputs = []
            for name, executable in (('before', before_exe),
                                     ('after', EXECUTABLE)):
                root = Path(tmp) / name
                for step in (['install', str(root), '--theme', 'pop-lemon'],
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
            for name in outputs[0]:
                self.assertEqual(outputs[0][name], outputs[1][name],
                                 f'{name} is not the page it was')

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
    """§9.1: the six palette variables are named for what they DO. Until
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
        meta_keys = {'label', 'source', 'note', 'note_good', 'intensity',
                     'dark_background'}
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
        """The sheet a page gets declares the six --color-* roles and not
        one of the retired names. Substring traps abound here: --page: is
        a suffix of --color-page:, so absence is asserted on the start of
        a declaration line (regex anchored MULTILINE), and consumption on
        the exact var(--old) form."""
        css = self.lwp.compose_stylesheet(self.lwp.resolve_theme_properties({}))
        for new in ('--color-page', '--color-ink', '--color-ink-quiet',
                    '--color-mark', '--color-call', '--color-affirm'):
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
            self.assertIn('no longer read', result.stdout)
            self.assertIn('--marker -> --color-mark', result.stdout)


class ThemesCommand(unittest.TestCase):
    """§11.9: the facets have to be reachable from the terminal, not only
    from the generated gallery page. lightwebpres is a standalone tool —
    if choosing a theme requires opening a browser, the CLI cannot do its
    own job."""

    def setUp(self):
        self.lwp = load_lightwebpres_module()

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
            trio = '/'.join((facets['polarity'], facets['intensity'], facets['hue']))
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
            r'data-polarity="([^"]*)" data-intensity="([^"]*)" data-hue="([^"]*)" '
            r'data-name="(\S+) ', html)
        self.assertEqual(len(cards), len(self.lwp.THEMES))

        for polarity, intensity, hue in {(c[0], c[1], c[2]) for c in cards}:
            from_gallery = sorted(c[3] for c in cards
                                  if (c[0], c[1], c[2]) == (polarity, intensity, hue))
            result = run('theme', 'list', '--polarity', polarity,
                         '--intensity', intensity, '--hue', hue)
            self.assertEqual(result.returncode, 0, result.stderr)
            from_cli = sorted(re.findall(r'^  (\S+)  \[', result.stdout, re.MULTILINE))
            self.assertEqual(from_cli, from_gallery, (polarity, intensity, hue))

    def test_an_unknown_facet_value_is_a_fatal_error_that_lists_the_valid_ones(self):
        """Not an empty result: 'rouge' is a typo for 'red', and quietly
        answering "no theme is like that" would send the reader looking
        for a theme that is right there."""
        result = run('theme', 'list', '--hue', 'rouge')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Unknown --hue', result.stderr)
        self.assertIn('red', result.stderr)

    def test_an_empty_but_legitimate_combination_says_so_and_succeeds(self):
        result = run('theme', 'list', '--polarity', 'dark', '--hue', 'orange')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No theme matches', result.stdout)

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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_succeeds_with_multiple_covers(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T1\n# First cover\nsummary: S1.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T2\n# Second cover\nsummary: S2.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T2\n# Cover title\nsummary: S.\n'
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
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            (root / 'articles').mkdir()
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
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n',
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
            (root / 'articles').mkdir()
            (root / 'articles' / 'a.MD').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n',
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
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\n' + meta_extra + '\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Cover H1\n' + cover_extra + '\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\n' + meta_extra + '\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Cover H1\n' + cover_extra + '\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'img').mkdir()
            (root / 'articles' / 'img' / 'photo.jpg').write_bytes(b'fake-photo')
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
        self.assertIn('## Title', result.stdout)


class TypographyTagProtection(unittest.TestCase):
    """§P2/§19.3: typography rules must never be able to corrupt HTML tag
    syntax in already-assembled HTML (fact-box content, full articles),
    regardless of what a language/*.json override file's rules do."""

    def test_custom_rule_does_not_corrupt_link_tag_attribute(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Original.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            clean = run('verify', str(root), '--output', str(root / 'public'))
            # 3 files: the article page, index.html and README.md (§11.4)
            self.assertIn('3 file(s) OK, 0 file(s) different.', clean.stdout)

            changed_md = md.replace('Original.', 'Changed.')
            (root / 'articles' / 'a.md').write_text(changed_md, encoding='utf-8')
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
            (root / 'articles').mkdir()
            md_a = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: Article A\n'
                'nav_desc: Desc A\n---\n\n<!-- lwp:slide:cover -->\nkicker: T\n# A\n'
            )
            (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
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
    outside articles/public (Path(dir) / '/etc/passwd' == '/etc/passwd')."""

    def _series_with_file_value(self, tmp, field, value):
        root = Path(tmp)
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide:full-article -->\narticle: ../../../etc/passwd\n'
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
            '<!-- lwp:slide:full-article -->\narticle: ..\n'
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
            (root / 'articles').mkdir(parents=True)
            (root / 'articles' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:full-article -->\narticle: leak.md\n', encoding='utf-8')
            (root / 'articles' / 'leak.md').symlink_to(secret)
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
            (root / 'articles' / 'img').mkdir(parents=True)
            (root / 'articles' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n', encoding='utf-8')
            (root / 'articles' / 'img' / 'leak.png').symlink_to(secret)
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
            (root / 'articles' / 'img').mkdir(parents=True)
            (root / 'articles' / 'img' / 'real.png').write_text('PNGDATA', encoding='utf-8')
            (root / 'articles' / 'img' / 'alias.png').symlink_to(
                root / 'articles' / 'img' / 'real.png')
            (root / 'articles' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                'nav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n', encoding='utf-8')
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
            '<!-- lwp:slide:full-article -->\narticle: art.md\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'articles' / 'art.md').write_text(body, encoding='utf-8')
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
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# A\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a".html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# A\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            (root / 'articles').mkdir()
            (root / 'series.json').write_text('{not valid json', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_articles_not_a_list_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            (root / 'series.json').write_text(json.dumps({'articles': 'oops'}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[ERROR]', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_invalid_json_language_file_is_a_clean_error(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
            'Before the break.\n\n---\n\nAfter the break.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\n## Title without a tag\nsummary: Summary here.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Cover without summary\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
        (root / 'articles').mkdir()
        entries = []
        for name in order:
            md = (
                f'<!-- lwp:meta -->\npage_dest: {name}.html\npage_title: {name}\nnav_title: {name}\n'
                f'nav_desc: D\n---\n\n<!-- lwp:slide:cover -->\nkicker: T\n# {name}\n'
            )
            (root / 'articles' / f'{name}.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide -->\nkicker: T\nh2: Title via field\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\nh1: Title via field\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)


class FactLabelOptional(unittest.TestCase):
    """§4.3: free text after a standard slide's fields goes into the
    fact-box when fact-label: is present, or a bare <p> paragraph
    (no fact-box wrapper) when it's absent."""

    def test_fact_label_present_produces_fact_box(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The takeaway\nContent with a fact-label.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nContent without a fact-label.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nFirst paragraph.\n\nSecond paragraph.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Slide title\n# Body heading\n\nBody.\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: Source\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
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
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'page_dest': '', 'page_source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_empty_string_nav_title_falls_back_to_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: Meta title\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\ncomment: COVER-SECRET\n'
            '# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T2\ncomment: STANDARD-SECRET\n'
            '## Standard title\nsummary: Summary 2.\nfact-label: The fact\n'
            'Body text.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\ncomment: a note\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_comment_on_standard_slide_does_not_become_fact_box_content(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\ncomment: a note\n## Title\nsummary: Summary.\n'
            'fact-label: The fact\nReal fact-box body.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('Real fact-box body.', html)
            self.assertNotIn('a note', html)


class HeadingInBodyIsContentNotRetitle(unittest.TestCase):
    """§22.2: the field->free-text switch applies to # / ## lines exactly
    like key: value fields — a heading appearing after body content has
    already started is fact-box content (rendered as a real heading by
    convert_markdown), not a silent overwrite of the slide's own h1/h2."""

    def test_heading_after_body_content_does_not_overwrite_slide_h2(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T\n## Real title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## The real slide title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# The real cover title\nsummary: Summary.\n\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Real title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide -->\nkicker: T\n## Title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
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
        (root / 'articles').mkdir()
        md = (
            f'<!-- lwp:meta -->\npage_title: Test\n{meta_extra}---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
        (root / 'articles').mkdir()
        summary_line = f'summary: {summary}\n' if summary else ''
        md = (
            f'<!-- lwp:meta -->\npage_title: Test\n{meta_extra}---\n\n'
            f'<!-- lwp:slide:cover -->\nkicker: T\n# Title\n{summary_line}'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
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
            self.assertIn('no description anywhere', result.stdout)


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
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Live article\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Live\nsummary: Live summary.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n', encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(
            f'<!-- lwp:meta -->\npage_title: Draft article\n{b_meta_extra}---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Draft\nsummary: Draft summary.\n', encoding='utf-8')
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
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: T\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# T\nsummary: S.\n', encoding='utf-8')
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
        (root / 'articles').mkdir()
        (root / 'series.json').write_text(
            json.dumps({'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
        return root

    MD = ('<!-- lwp:meta -->\npage_title: Test\n---\n\n'
          '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n')

    def test_bom_in_series_json_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'articles' / 'a.md').write_text(self.MD, encoding='utf-8')
            raw = (root / 'series.json').read_bytes()
            (root / 'series.json').write_bytes(b'\xef\xbb\xbf' + raw)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_bom_in_full_article_does_not_leak_or_break_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'articles' / 'a.md').write_text(
                self.MD + '\n---\n\n<!-- lwp:slide:full-article -->\narticle: a_article.md\n',
                encoding='utf-8')
            (root / 'articles' / 'a_article.md').write_bytes(
                b'\xef\xbb\xbf# Full article heading\n\nBody.\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h1>Full article heading</h1>', html)
            self.assertNotIn('\ufeff', html)

    def test_crlf_article_parses_identically(self):
        crlf_md = (
            '<!-- lwp:meta -->\npage_title: Test\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: T2\n## Second\nsummary: S2.\nfact-label: F\n\nBody.\n'
        ).replace('\n', '\r\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'articles' / 'a.md').write_bytes(crlf_md.encode('utf-8'))
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h1>Title</h1>', html)
            self.assertIn('<h2>Second</h2>', html)
            self.assertEqual(html.count('<section class="slide'), 2)

    def test_invalid_utf8_article_gets_clean_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'articles' / 'a.md').write_bytes(
                b'<!-- lwp:meta -->\npage_title: T\n---\n\n'
                b'<!-- lwp:slide:cover -->\nkicker: T\n# Broken \xff\xfe\nsummary: S.\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not valid UTF-8', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_empty_article_file_gets_clean_meta_block_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp)
            (root / 'articles' / 'a.md').write_text('', encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('must start with a <!-- lwp:meta --> block', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_empty_articles_array_builds_an_empty_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
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
            (root / 'articles').mkdir()
            for name in ('a', 'b'):
                (root / 'articles' / f'{name}.md').write_text(
                    f'<!-- lwp:meta -->\npage_title: Article {name}\ndate: 2026\n---\n\n'
                    f'<!-- lwp:slide:cover -->\nkicker: T\n# Article {name}\nsummary: Résumé : test.\n\n---\n\n'
                    f'<!-- lwp:slide -->\nkicker: F\n## Fiche\nsummary: S.\nfact-label: Fait\n\nCorps **gras**.\n\n---\n\n'
                    f'<!-- lwp:slide:series-nav -->\n', encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n'
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
            (root / 'articles').mkdir()
            for name in ('a.md', 'b.md'):
                (root / 'articles' / name).write_text(
                    '<!-- lwp:meta -->\npage_title: T\n---\n\n'
                    '<!-- lwp:slide:cover -->\nkicker: T\n# T\nsummary: S.\n', encoding='utf-8')
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
        self.assertFalse(set(fr['strings']) - used, 'dead keys (defined, never referenced)')

    def test_copy_feedback_tooltip_uses_the_language_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, (
                '<!-- lwp:meta -->\npage_title: T\n---\n\n'
                '<!-- lwp:slide:cover -->\nkicker: T\n# T\nsummary: S.\n'))
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
            '<!-- lwp:slide:cover -->\nkicker: Été\n# À 東京 🗼\nsummary: всё хорошо.\n\n---\n\n'
            '<!-- lwp:slide -->\nkicker: نص\n## عنوان عربي\nsummary: RTL.\nfact-label: Факт\n\nCorps 中文 🎉.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            (root / 'articles' / 'café-日本.md').write_text(md, encoding='utf-8')
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

    def test_shadow_defaults_are_invisible_and_emitted_once(self):
        # A halo is a shadow with no offset; the transparent default means
        # the composite is present but paints nothing until a theme asks.
        r = self.resolve({})
        self.assertEqual(r['page.shadow.fg'], '#00000000')
        css = self.lwp.emit_theme_css(r)
        self.assertIn('text-shadow: 0 var(--page-shadow-dy) '
                      'var(--page-shadow-blur) var(--page-shadow-fg);', css)

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
        # emission without an error — 33 themes, no exception is the test.
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
            for cssprop, _value in comp.composite:
                for sel in comp.selector.split(','):
                    driven.add((sel.strip(), cssprop))
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
                '<style> x{\n---\n\n# Cover\n\nsummary: s\n')
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
                                 '# Cover\n\nsummary: s\n')
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


class TheGalleryInTheRepoIsTheGalleryTheToolMakes(unittest.TestCase):
    """README says the gallery "can never drift from what install --theme
    actually applies". That is true of the generator and was not true of
    the committed copy, which is regenerated by hand — it happened to be
    in sync, and nothing kept it so."""

    def test_the_committed_gallery_is_byte_identical_to_a_fresh_one(self):
        repo_copy = Path(__file__).resolve().parent.parent / 'themes-gallery.html'
        if not repo_copy.exists():
            self.skipTest('no committed gallery in this checkout')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('theme', 'gallery', str(out)).returncode, 0)
            self.assertEqual(
                out.read_bytes(), repo_copy.read_bytes(),
                'themes-gallery.html is stale: re-run '
                '`lightwebpres theme gallery themes-gallery.html`')


class TypedSurfaceCannotLeaveItsDeclaration(unittest.TestCase):
    """§9 claims the CSS-string axis is "the only one whose value travels
    untransformed, so the only one that must guard itself". That was false:
    two other types passed values through verbatim, and both reached the
    page's inlined <style> from an ARTICLE's meta block — the trust level
    the rewrite hardened everywhere else."""

    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

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
                '<style>x, sans-serif\n---\n\n# Cover\n\nsummary: s\n')
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
            (root / 'articles' / 'leak.md').symlink_to(outside / 'secret.md')
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

    def test_a_theme_that_resizes_its_notes_resizes_both(self):
        # high-contrast states a bigger note; its foot-of-unit note has to
        # follow, or the theme's one intent is honoured in one place only.
        for slug, props in self.lwp.THEME_NOTE_PROPS.items():
            if 'note.size' in props:
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

    def test_speaker_note_field_is_hidden_and_only_for_the_presenter(self):
        # A `note:` field is a SPEAKER note, distinct from a `[^x]` source
        # footnote: it is parsed but withheld from the slide the reader sees,
        # and only the presenter panel (key N) reads it back from the DOM.
        deck = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n'
            '---\n\n'
            '<!-- lwp:slide -->\nkicker: One\n## First\n'
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
            '<!-- lwp:slide -->\nkicker: One\n## First\n'
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
            '<!-- lwp:slide -->\nkicker: One\n## First\n'
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
        for slug, props in self.lwp.THEME_NOTE_PROPS.items():
            for key, value in props.items():
                if key.endswith('.size'):
                    self.assertIn('vmin', value, f'{slug} {key}')

    def test_a_halo_is_drawn_against_the_glyph_it_surrounds(self):
        """A glow and a marker box are both sized by the text they sit
        on, so both scale with it. terminal is the one theme with a glow
        and it stated 10px flat -- around a 51px title at 1080p and the
        same 10px around a 132px one at 3840, which is the theme's single
        visual idea gone on the screen a deck is shown on."""
        seen = 0
        for store in (self.lwp.THEME_PROPERTY_OVERRIDES,
                      self.lwp.THEME_NOTE_PROPS,
                      self.lwp.DARK_FURNITURE_PROPS):
            for slug, props in store.items():
                if not isinstance(props, dict):
                    continue
                for key, value in props.items():
                    if not key.endswith('.shadow.blur'):
                        continue
                    if str(value) in ('0', '0px'):
                        continue
                    seen += 1
                    self.assertIn('vmin', value, f'{slug} {key}')
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
        skeleton = self.lwp.TEMPLATE_SKELETON
        slide_rule = self._rule('.slide') if hasattr(self, '_rule') else skeleton
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
               '# Cover\n\nsummary: s\n')

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
                                 '# Cover\n\nsummary: s\n\n---\n\n'
                                 '## S\n\nfact-label: F\n\n'
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
                             '# Cover\n\nsummary: s\n\n---\n\n'
                             '<!-- lwp:slide:full-article -->\n'
                             'article: a_article.md\n')
        (root / 'articles' / 'a_article.md').write_text(
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
                 '---\n\n# Cover\n\nsummary: s\n\n---\n\n'
                 '## S\n\nfact-label: F\n\n' + body + '\n')
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
               '# Cover\n\nsummary: s\n\n---\n\n'
               '## S\n\nfact-label: F\nfact-variant: {variant}\n\nBody.\n')

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
        '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nkicker: One\n## First\n\nfact-label: L\n\n'
        'A claim[^kwh] and the same source again[^kwh].\n\n'
        'A different one[^b].\n\n'
        '[^kwh]: Measured at 230 V.\n[^b]: A second body.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nkicker: Two\n## Second\n\nfact-label: L\n\n'
        'A claim in the next card[^z].\n\n[^z]: Its own body.\n\n'
        '---\n\n'
        '<!-- lwp:slide:full-article -->\narticle: art.md\n'
    )
    ARTICLE = ('# Long form\n\nOne[^p] and two[^q].\n\n'
               '[^p]: First.\n[^q]: Second.\n')

    def _build(self, extra='', article=None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, self.DECK.format(extra=extra))
        (root / 'articles' / 'art.md').write_text(
            self.ARTICLE if article is None else article, encoding='utf-8')
        result = run('build', str(root), '--output', str(root / 'public'))
        self.assertEqual(result.returncode, 0, result.stderr)
        return (root / 'public' / 'a.html').read_text(encoding='utf-8')

    def test_the_call_and_the_body_point_at_each_other(self):
        html = self._build()
        self.assertIn('<a id="noteref-s2-1" href="#note-s2-1" '
                      'role="doc-noteref">1</a>', html)
        self.assertIn('<li id="note-s2-1" role="doc-footnote">', html)
        self.assertIn('href="#noteref-s2-1" role="doc-backlink"', html)

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
        self.assertIn('id="note-s2-1"', html)
        self.assertIn('id="note-s2-2"', html)
        self.assertIn('id="note-s3-1"', html)   # next card, back to 1
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
        self.assertEqual(html.count('id="note-s2-1"'), 1)
        self.assertIn('href="#noteref-s2-1" role="doc-backlink"', html)
        self.assertIn('href="#noteref-s2-1-2" role="doc-backlink"', html)

    def test_local_is_the_default_and_bodies_stay_with_their_card(self):
        html = self._build()
        self.assertIn('class="notes-local"', html)
        self.assertNotIn('class="slide notes-section"', html)
        # The card's own block, inside the card's own section.
        card = html.split('id="s2"', 1)[1].split('<section', 1)[0]
        self.assertIn('id="note-s2-1"', card)
        self.assertIn('id="note-s2-2"', card)
        self.assertNotIn('id="note-s3-1"', card)

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
        (root / 'articles' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
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
        self.assertIn('<li id="note-s2-1"', withtip)

    def test_placement_cascades_from_series_meta_and_the_article_wins(self):
        for meta_line, expected_section in (('', True), ('notes_placement: local\n', False)):
            tmp = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, tmp, True)
            root = scaffold(tmp, self.DECK.format(extra=meta_line))
            (root / 'articles' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
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
        (root / 'articles' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
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
                '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n'
                '---\n\n<!-- lwp:slide:full-article -->\narticle: art.md\n')
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = scaffold(tmp, deck)
        (root / 'articles' / 'art.md').write_text(
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
    """Ten contrast constraints × 33 themes, measured from the RESOLVED
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

    def test_the_two_extra_call_axes_default_to_the_tone_of_their_ground(self):
        # The defaults are what make this right by construction with no
        # per-theme value: each names the tone the theme ALREADY chose for
        # text on that ground. If a future edit pins a literal instead, 33
        # themes silently stop tracking their own palettes.
        reg = self.lwp.PROPERTY_REGISTRY
        self.assertEqual(reg['footnote-call.fg-marked'].default, 'fact.strong.fg')
        self.assertEqual(reg['footnote-call.fg-cover'].default, 'cover.fg')


class AuditNamesTheThreeWaysANoteBreaks(unittest.TestCase):
    """None of them is fatal — the input contract does not break over an
    editorial slip — so `audit` is where they have to surface."""

    DECK = (
        '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\n'
        'nav_title: A\nnav_desc: A\n{extra}---\n\n'
        '<!-- lwp:slide:cover -->\nkicker: T\n# Title\nsummary: S.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nkicker: One\n## First\n\nfact-label: L\n\n'
        'A body defined here[^here].\n\n[^here]: Present.\n\n'
        '---\n\n'
        '<!-- lwp:slide -->\nkicker: Two\n## Second\n\nfact-label: L\n\n'
        'A call to it from the next card[^here].\n\n'
        '---\n\n'
        '<!-- lwp:slide:full-article -->\narticle: art.md\n'
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
        (root / 'articles' / 'art.md').write_text(self.ARTICLE, encoding='utf-8')
        result = run('audit', str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

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
               '<!-- lwp:slide:cover -->\nkicker: Tag\n# {heading}\n'
               'summary: {summary}\n')
    NAV_SLIDE = '\n---\n\n<!-- lwp:slide:series-nav -->\n'

    def _series(self, tmp, entries, sources, series_meta=None):
        """A series directory: `entries` go into series.json verbatim,
        `sources` maps a filename to its .md text."""
        root = Path(tmp)
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        for name, text in sources.items():
            (root / 'articles' / name).write_text(text, encoding='utf-8')
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
            (root / 'articles' / 'binary.md').write_bytes(
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
               '<!-- lwp:slide:cover -->\nkicker: Tag\n# {heading}\n'
               'summary: {summary}\n')

    def _series(self, tmp, entries, sources, series_meta=None, settings=None):
        root = Path(tmp)
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        for name, text in sources.items():
            (root / 'articles' / name).write_text(text, encoding='utf-8')
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
                        + '\n---\n\n<!-- lwp:slide -->\n## First\n'
                          'fact-label: On A\n\nbody\n',
                'b.md': self.ARTICLE.format(meta='', heading='B', summary='s')
                        + '\n---\n\n<!-- lwp:slide -->\n## Second\n'
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
            (root / 'articles' / 'intro.md').unlink()
            result = run('resolve', str(root), 'page_title',
                         '--article', 'intro.md', '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARN]', result.stderr)
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
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        series = []
        for name, md in md_for.items():
            dest = name.replace('.md', '.html')
            (root / 'articles' / name).write_text(md, encoding='utf-8')
            series.append({'page_dest': dest, 'page_source': name,
                           'nav_title': name[0].upper(), 'nav_desc': name[0]})
        (root / 'series.json').write_text(
            json.dumps({'articles': series}), encoding='utf-8')
        return root

    def _build_html(self, tmp, md=None, extra=None):
        root = scaffold(tmp, md or (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
            'nav_title: A\nnav_desc: A\n---\n\n# A\n'))
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
                              'status: active\n---\n\n# A\n'),
                'draft.md': ('<!-- lwp:meta -->\npage_dest: draft.html\n'
                             'page_title: T\nnav_title: D\nnav_desc: D\n'
                             'status: draft\n---\n\n# D\n'),
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
              'nav_title: A\nnav_desc: A\n---\n\n# T\n\n'
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
                        'nav_title: A\nnav_desc: A\n---\n\n# A\n'))
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
        with tempfile.TemporaryDirectory() as tmp:
            html = self._build_html(tmp)
            i = html.find("'contextmenu'")
            self.assertNotEqual(i, -1)
            seg = html[i:i + 400]
            self.assertIn('clearTimeout', seg)

    # --- B9: audit must not false-positive a retired name as a prefix ---
    def test_b9_audit_no_false_retired_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\n# A\n'),
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
                         'nav_title: A\nnav_desc: A\n---\n\n# A\n'),
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
                         '<!-- lwp:slide:cover -->\nkicker: T\n# Title\n'
                         'summary: S.\n\n---\n\n'
                         '<!-- lwp:slide:series-nav -->\n'),
                'b.md': ('<!-- lwp:meta -->\npage_dest: b.html\npage_title: T\n'
                         'nav_title: B\nnav_desc: B\n---\n\n# B\n'),
            })
            r1 = run('build', str(root), '--no-nav',
                     '--output', str(root / 'public'))
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = run('check', str(root), '--no-nav',
                     '--output', str(root / 'public'))
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotIn('[DRIFT]', r2.stdout + r2.stderr)

    # --- B21: copy_images must refuse a self-referential symlink ---
    def test_b21_self_referential_symlink(self):
        import subprocess as _sp
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, None, {
                'a.md': ('<!-- lwp:meta -->\npage_dest: a.html\npage_title: T\n'
                         'nav_title: A\nnav_desc: A\n---\n\n# A\n'),
            })
            img = root / 'articles' / 'img'
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
              '<!-- lwp:slide:standard -->\n# Title\nsummary: S.\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md, source_name='a.md', file_name='a.html')
            full = run('audit', str(root))
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertIn('no cover slide', full.stdout,
                          'editorial check should fire without --templates')
            tmpl = run('audit', str(root), '--templates')
            self.assertEqual(tmpl.returncode, 0, tmpl.stderr)
            self.assertNotIn('no cover slide', tmpl.stdout,
                             '--templates must skip editorial checks')

if __name__ == '__main__':
    unittest.main()
