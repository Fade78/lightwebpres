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

import json
import os
import inspect
import re
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            result = run('check', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('up to date', result.stdout)

    def test_install_refuses_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'dummy.txt').write_text('x', encoding='utf-8')
            result = run('install', str(root))
            self.assertNotEqual(result.returncode, 0)

    def test_typography_nbsp_before_double_punctuation(self):
        # This one intentionally uses French content: it tests the French
        # typography engine's own rule (nbsp before "?").
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Une question ?\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('question\xa0?', html)


class ParagraphHandling(unittest.TestCase):
    """Spec §4.1/§6.1: one line = one field, but real Markdown paragraphs
    (separated by a blank line) must be respected, and a paragraph broken
    without a blank line must be re-joined."""

    def test_two_real_paragraphs_in_factbox_stay_separate(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n\n---\n\n<!-- lwp:slide:full-article -->\n'
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
        md = '---\n\n<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            result = run('install', str(root), '--force')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'series.json').exists())


class AuditCommand(unittest.TestCase):
    """The audit command (§11.5): never blocking, warns about editorial
    conventions that are not respected."""

    def test_audit_clean_series_no_warnings(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No warnings', result.stdout)

    def test_audit_warns_when_no_cover(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stdout)

    def test_audit_warns_when_cover_not_first(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T2\n# Cover title\n'
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
            self.assertEqual(run('install', tmp, '--theme', 'nord').returncode, 0)
            self.assertEqual(run('demo', tmp).returncode, 0)
            clean = run('audit', tmp)
            self.assertNotIn('scaffold', clean.stdout.lower())

            self.assertEqual(run('set-theme', tmp, '--theme', 'evergreen').returncode, 0)
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
            self.assertEqual(run('install', tmp).returncode, 0)
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nhighlight: 42 %\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nsummary: No highlight here.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="highlight"', html)


_MINIMAL_MD = (
    '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
    '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## S\nfact-label: F\n'
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
            self.assertNotIn('--marker', title)
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
    """§3.3/§12.3: every slide carries a zero-padded 'NN / NN' counter —
    completely unasserted before axis 4 (a broken counter would ship on
    every page unnoticed)."""

    def test_counter_is_zero_padded_with_correct_total(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Two\nsummary: S.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Three\nsummary: S.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<span class="slide-num">01 / 03</span>', html)
            self.assertIn('<span class="slide-num">02 / 03</span>', html)
            self.assertIn('<span class="slide-num">03 / 03</span>', html)


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
            {'page_source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B', 'draft': True},
        ]}), encoding='utf-8')
        return root

    def test_check_include_drafts_is_green_after_matching_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_draft(tmp)
            result = run('build', str(root), '--output', str(root / 'public'),
                         '--include-drafts')
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run('check', str(root), '--output', str(root / 'public'),
                         '--include-drafts')
            self.assertEqual(result.returncode, 0,
                             result.stdout + result.stderr)
            self.assertIn('[OK] b.html', result.stdout)

    def test_plain_check_after_drafts_build_reports_index_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_draft(tmp)
            run('build', str(root), '--output', str(root / 'public'),
                '--include-drafts')
            result = run('check', str(root), '--output', str(root / 'public'))
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Magnifique !\n'
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

    def test_h4_stays_literal_paragraph_text(self):
        html = self._html('#### Not a heading\n')
        self.assertIn('<p>#### Not a heading</p>', html)
        self.assertNotIn('<h4>', html)

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
        for command in ('install', 'demo', 'build', 'check', 'audit',
                        'refresh-templates', 'themes-gallery'):
            self.assertIn(command, result.stdout)

    def test_demo_without_install_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run('demo', tmp)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('install', result.stderr)

    def test_demo_writes_svg_and_editorial_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            run('install', str(root), '--lang', 'en')
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
            result = run('check', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 1)
            self.assertTrue(any(line.strip().startswith('+') and 'Changed.' in line
                                for line in result.stdout.splitlines()))

    def test_audit_numeric_summary_and_drafts_audited(self):
        # A draft article with no cover: audit must still inspect it and
        # count its warning — audit never excludes drafts (§11.5).
        md_no_cover = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            'page_desc: Has one.\ndraft: true\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Standard only\nsummary: S.\n'
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
            self.assertIn('[INFO]', result.stdout)

    def test_gitlab_ci_content_pins_image_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            result = run('install', str(root), '--gitlab-ci')
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
            result = run('install', str(root), '--gitlab-ci', '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            ci = (root / '.gitlab-ci.yml').read_text(encoding='utf-8')
            self.assertIn('build . --lang en', ci)

    def test_demo_lang_produces_english_ui(self):
        # The README quickstart passes --lang to demo (not install, where
        # it is inert for local builds) — the UI chrome must be English.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            self.assertEqual(run('install', str(root)).returncode, 0)
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

    def test_draft_string_true_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD, series_extra={'draft': 'TRUE'})
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n\n---\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: Base tag\ntag: Override tag\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n'
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
            result = run('check', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT] index.html', result.stdout)

    def test_readme_drift_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, _MINIMAL_MD)
            run('build', str(root), '--output', str(root / 'public'))
            (root / 'README.md').write_text('Hand-edited.', encoding='utf-8')
            result = run('check', str(root), '--output', str(root / 'public'))
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n'
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


class SeriesNavFullArticleStrictContent(unittest.TestCase):
    """§22.8/§22.9: series-nav and full-article slides render none of
    their own content beyond their directives — unrecognized lines are
    fatal (they used to vanish silently). comment: is recognized on
    every slide type, these two included."""

    def _build(self, tmp, slide_block, extra_files=None):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n\n---\n\n'
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
                tmp, '<!-- lwp:slide:full-article -->\narticle: art.md\ntag: Oops\n',
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
            '<!-- lwp:slide -->\ntag: T\n## Slide\nfact-label: FACT\n'
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
            result = run('install', str(root), '--lang', 'en')
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
            result = run('install', str(root), '--lang', 'en')
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
            '<!-- lwp:slide -->\ntag: T\n## Slide\nsummary: S.\nhighlight: 42 %\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n\n---\n\n'
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
        self.assertNotIn(' ![', html)

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
        # Spec §6 (line 414-415): footnotes are a visual marker, not a real
        # anchor link — [^N] -> <sup>[^N]</sup>, not a clickable #fn1 link.
        html = self._build_article_html(
            'A claim with a footnote[^1].\n\n[^1]: Some source, 2020.\n'
        )
        self.assertIn('A claim with a footnote<sup>[^1]</sup>.', html)
        self.assertIn('<p><sup>[^1]</sup>: Some source, 2020.</p>', html)

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
            '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\n'
            'nav_title: Question ? Titre\nnav_desc: Alerte !\ncard_label: Numéro :\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
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
            self.assertIn('no usable cache found', result.stdout)
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide -->\ntag: New\n## A brand-new slide\nsummary: New body content.\n\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md_a2, encoding='utf-8')
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'][0]['nav_title'] = 'Article A Renamed'
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')

            result = run('build', str(root), '--output', str(root / 'public'), '--only', 'a.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('nav/index-affecting metadata changed', result.stdout)
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Article C\nsummary: Summary C.\n\n---\n\n'
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
            self.assertIn('nav/index-affecting metadata changed', result.stdout)
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
            install_result = run('install', str(root))
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
            result = run('install', str(root))
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Original summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            changed_md = md.replace('Original summary.', 'Changed summary.')
            (root / 'articles' / 'a.md').write_text(changed_md, encoding='utf-8')
            result = run('check', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('[DRIFT]', result.stdout)


class RemainingTypographyRules(unittest.TestCase):
    """§7.2: the two French rules not already covered by
    test_typography_nbsp_before_double_punctuation."""

    def test_typography_nbsp_after_opening_quote(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: « Une citation.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('«\xa0Une citation.', html)

    def test_typography_nbsp_before_percent(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nhighlight: 50 %\nhighlight-caption: half\n'
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
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: {summary}\n'
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
            f'<!-- lwp:slide:cover -->\ntag: {w("Tag")}\n# {w("Titre")}\nsummary: {w("Résumé")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<span class="slide-tag">(.*?)</span>', html).group(1))
            self._both_ends(re.search(r'<h1>(.*?)</h1>', html).group(1))
            self._both_ends(re.search(r'<p class="summary">(.*?)</p>', html).group(1))

    def test_standard_slide_all_fields(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\n'
            f'tag: {w("Tag")}\n'
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
            self._both_ends(re.search(r'<span class="slide-tag">(.*?)</span>', html).group(1))
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
            f'<!-- lwp:slide -->\ntag: T\n## Titre\nsummary:{self.NBSP}Résumé\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            summary = re.search(r'<p class="summary">(.*?)</p>', html).group(1)
            self.assertTrue(summary.startswith(self.NBSP), repr(summary))

    def test_page_title_survives(self):
        md = (
            f'<!-- lwp:meta -->\npage_dest: a.html\npage_title: {self._wrap("Titre de page")}\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
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
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: {self._wrap("Description")}\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n\n'
            '---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: a_article.md\n'
        )
        article_md = f'Un appel[^1].\n\n[^1]:{self.NBSP}Corps de la note.\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md, extra_articles={'a_article.md': article_md})
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            m = re.search(r'<sup>\[\^1\]</sup>: (.*?)</p>', html)
            self.assertIsNotNone(m, html)
            self.assertTrue(m.group(1).startswith(self.NBSP), repr(m.group(1)))

    def test_index_series_meta_and_card_fields_survive(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n'
            f'card_title: {w("Carte titre")}\ncard_desc: {w("Carte desc")}\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
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


class TypographyDisableSwitches(unittest.TestCase):
    """§4.5/§19.6: typo-units/typo-thousands/typo meta fields and
    --no-typography each turn off part or all of the typography engine,
    scoped exactly as documented — per-rule, per-article, or global."""

    def _two_article_series(self, tmp, meta_extra_b=''):
        root = Path(tmp)
        (root / 'articles').mkdir(parents=True, exist_ok=True)
        summary = 'Environ ≈ 5 $ pour 170 000 000 vues, × 4 la dose, 170 millions de gens, 20 dollars.'
        md_a = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre A\nsummary: {summary}\n'
        )
        md_b = (
            '<!-- lwp:meta -->\npage_dest: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            f'{meta_extra_b}---\n\n'
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre B\nsummary: {summary}\n'
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
            root = self._two_article_series(tmp, meta_extra_b='typo-units: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertIn('170\xa0millions', a)
            self.assertIn('170 millions', b)
            # Thousands separator is untouched by typo-units: off.
            self.assertIn('170\xa0000\xa0000', b)

    def test_typo_thousands_off_disables_only_thousands_for_that_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._two_article_series(tmp, meta_extra_b='typo-thousands: off\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            a = self._summary_of(root, 'public', 'a.html')
            b = self._summary_of(root, 'public', 'b.html')
            self.assertIn('170\xa0000\xa0000', a)
            self.assertIn('170 000 000', b)
            # Units rule is untouched by typo-thousands: off.
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
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
            result = run('check', str(root), '--no-typography')
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            result = run('refresh-templates', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('install', result.stderr.lower())

    def test_reports_up_to_date_when_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            before = {name: (root / 'templates' / name).read_text(encoding='utf-8')
                      for name in ('settings.conf', 'custom.css', 'nav.js')}
            result = run('refresh-templates', str(root))
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
            self.assertEqual(run('install', str(root)).returncode, 0)
            (root / 'templates' / 'settings.conf').unlink()
            (root / 'templates' / 'custom.css').unlink()

            result = run('refresh-templates', str(root))
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
            self.assertEqual(run('install', str(root), '--theme', 'nord').returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            edited = settings.read_text(encoding='utf-8').replace(
                '# color.mark: #EBCB8B', 'color.mark: #EBCB8B', 1,
            ) + '# my own note\n'
            settings.write_text(edited, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_text(encoding='utf-8'), edited)

    def test_a_legacy_style_css_warns_but_never_fails(self):
        """The pre-rewrite exit-1-without-marker path is gone: a leftover
        style.css is the author's file holding the author's values, so it
        is reported (it is silently unread otherwise) and left exactly in
        place — refresh must still succeed at its own job."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            legacy = '/* old scaffold */\n.old-custom { color: blue; }\n'
            style_path = root / 'templates' / 'style.css'
            style_path.write_text(legacy, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('[WARN]', result.stderr)
            self.assertIn('style.css is no longer read', result.stderr)
            self.assertEqual(style_path.read_text(encoding='utf-8'), legacy)

    def test_nav_js_is_replaced_and_previous_version_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            nav_path = root / 'templates' / 'nav.js'
            old_nav = nav_path.read_text(encoding='utf-8') + '\n// OLD-CUSTOM-NAV\n'
            nav_path.write_text(old_nav, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

            refreshed = nav_path.read_text(encoding='utf-8')
            self.assertNotIn('OLD-CUSTOM-NAV', refreshed)
            backup = root / 'templates' / 'nav.js.bak'
            self.assertTrue(backup.exists())
            self.assertIn('OLD-CUSTOM-NAV', backup.read_text(encoding='utf-8'))


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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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

            check_result = run('check', str(root), '--output', str(root / 'public'))
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
                '<!-- lwp:slide:cover -->\ntag: T\n# B\nsummary: Summary.\n',
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
            check_result = run('check', str(root), '--output', str(root / 'public'))
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
            self.assertEqual(run('install', str(root)).returncode, 0)
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
            result = run('install', str(root), '--theme', 'nord')
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
            result = run('install', str(root), '--theme', 'not-a-real-theme')
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
            self.assertEqual(run('install', str(root), '--theme', 'dracula').returncode, 0)
            settings_path = root / 'templates' / 'settings.conf'
            before = settings_path.read_text(encoding='utf-8')
            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings_path.read_text(encoding='utf-8'), before)

    def test_themes_gallery_default_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('themes-gallery', cwd=str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            gallery = root / 'themes-gallery.html'
            self.assertTrue(gallery.exists())

    def test_themes_gallery_explicit_path_documents_every_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'gallery.html'
            result = run('themes-gallery', str(out))
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
            self.assertIn('lightwebpres install my-series --theme nord', html)
            # One card per theme, whatever the count — asserting a literal
            # number here just means editing the test every time a palette
            # is added, which tests nothing.
            expected = len(load_lightwebpres_module().THEMES)
            # Prefix, not the exact tag: cards carry data-* facet
            # attributes (§9.5.3), so an exact-string count silently
            # dropped to zero when those were added.
            open_tags = html.count('<article class="theme-card"')
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
            self.assertEqual(run('install', str(root), '--theme', 'nord').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            result = run('build', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            for page in ('a.html', 'index.html'):
                html = (root / 'public' / page).read_text(encoding='utf-8')
                self.assertIn('--color-mark: #EBCB8BFF;', html, page)


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
        dark_items = self.lwp.DARK_FURNITURE_PROPS.items()
        for slug, theme in self.lwp.THEMES.items():
            layer = self.lwp.theme_property_layer(slug)
            if theme.get('dark_background'):
                self.assertTrue(dark_items <= layer.items(),
                                f'{slug} is dark but its layer lacks the dark furniture')
            else:
                for key in self.lwp.DARK_FURNITURE_PROPS:
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
            self.assertEqual(run('install', str(root), '--theme', 'terminal').returncode, 0)
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
            self.assertEqual(run('install', str(root), '--theme', 'nord').returncode, 0)
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
        dark_items = self.lwp.DARK_FURNITURE_PROPS.items()
        for key, theme in self.lwp.THEMES.items():
            dark_facet = self.lwp.theme_facets(theme)['polarity'] == 'dark'
            dark_css = dark_items <= self.lwp.theme_property_layer(key).items()
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

    EMPHASIS_VARS = ('--fact-strong-weight', '--fact-strong-style',
                     '--fact-strong-highlight', '--fact-strong-ink',
                     '--fact-strong-decoration', '--fact-strong-decoration-color')

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
        """Byte-for-byte the renderer's own output, for every slide of
        the mock — which is itself written in the real article format and
        goes through the real parser."""
        _, slides, _, _ = self.lwp.parse_markdown_extended(
            self.lwp.TEMPLATE_THEMES_GALLERY_MOCK)
        self.assertGreaterEqual(len(slides), 2, 'the mock lost its slides')
        pack = self.lwp.load_language(None, 'en')
        engine = self.lwp.TypoEngine(pack)
        doc = self.lwp.build_theme_preview_document('nord')
        for i, slide in enumerate(slides, 1):
            rendered = self.lwp.render_slide(slide, i, len(slides), engine,
                                             pack.get('strings', {}))
            self.assertIn(rendered, doc, f'slide {i}')

    def test_the_mock_exercises_the_parts_a_theme_actually_changes(self):
        """A preview that shows no fact-box says nothing about the
        emphasis axes; one with no verdict cell says nothing about the
        shape markers."""
        doc = self.lwp.build_theme_preview_document('nord')
        self.assertIn('class="slide slide-cover"', doc)
        for cls in ('slide-tag', 'summary', 'highlight-figure',
                    'highlight-caption', 'fact-box', 'fact-label',
                    'comparison-table'):
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
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        self.assertEqual(html.count('<iframe class="preview"'), len(self.lwp.THEMES))
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
        axes = ('weight', 'style', 'bg', 'fg', 'decoration', 'decoration-color')
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

    def test_underline_is_a_fourth_independent_axis(self):
        props = self.lwp.theme_fact_properties
        self.assertEqual(props({})['decoration'], 'none')
        self.assertEqual(props({})['decoration-color'], 'currentColor')
        instead = props({'fact_highlight': None, 'fact_decoration': 'underline',
                         'fact_decoration_color': 'marker'})
        self.assertEqual(instead['highlight'], 'transparent')
        self.assertEqual(instead['decoration-color'], 'var(--marker)')
        as_well = props({'fact_highlight': 'marker', 'fact_decoration': 'underline'})
        self.assertEqual(as_well['highlight'], 'var(--marker)')
        self.assertEqual(as_well['decoration'], 'underline')

    def test_the_catalogue_demonstrates_both_ways_of_using_the_underline(self):
        instead, as_well = [], []
        for slug, theme in self.lwp.THEMES.items():
            props = self.lwp.theme_fact_properties(theme)
            if props['decoration'] != 'underline':
                continue
            (instead if props['highlight'] == 'transparent' else as_well).append(slug)
        self.assertTrue(instead, 'no theme shows an underline replacing the marker')
        self.assertTrue(as_well, 'no theme shows an underline alongside the marker')
        for slug in instead + as_well:
            theme = self.lwp.THEMES[slug]
            colour = theme.get('fact_decoration_color')
            if colour is None:
                continue
            self.assertGreaterEqual(
                contrast_ratio(theme[colour], theme['page']), 3.0,
                f'{slug}: the underline is too faint against the page')

    def test_the_default_highlight_role_names_a_role_that_exists(self):
        default = self.lwp.theme_fact_properties({})['highlight']
        self.assertIn(default[6:-1], self.lwp.PALETTE_ROLES, default)

    def test_each_swatch_names_the_role_before_the_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
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
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
        stated = re.findall(r'class="fact-treatment"><span>[^<]*</span>(.*?)</p>', html)
        self.assertEqual(len(stated), len(self.lwp.THEMES))
        for slug, theme in self.lwp.THEMES.items():
            label = self.lwp.fact_treatment_label(theme)
            self.assertIn(label, stated, slug)
            props = self.lwp.theme_fact_properties(theme)
            self.assertEqual('underlined' in label, props['decoration'] == 'underline', slug)
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
        source = inspect.getsource(self.lwp.parse_markdown_extended)
        names = re.search(r"\^\(([a-z|-]+)\):", source).group(1).split('|')
        self.assertIn('highlight-caption', names, 'the field regex moved')
        for field in names:
            self.assertIn(field, self.skill, field)

    def test_every_article_level_field_is_named(self):
        for field in self.lwp._SERIES_STRING_FIELDS:
            self.assertIn(field, self.skill, field)
        for field in self.lwp._SERIES_META_STRING_FIELDS:
            self.assertIn(field, self.skill, f'series_meta.{field}')
        # Not just the word: --include-drafts contains it, which is
        # how a first version of this line survived its own mutation.
        # `true` is the only value that marks a draft, so that is what
        # the skill has to show.
        self.assertIn('draft: true', self.skill)

    def test_every_styling_hook_reachable_only_by_hand_is_named(self):
        """A class the stylesheet defines and the Markdown cannot
        produce is reachable only if the skill says it exists."""
        css = self.lwp.TEMPLATE_STYLE
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

    def _cover_ground(self, theme):
        """What the cover slide actually paints under its own text: the
        ink itself on a light theme, the #00000073 veil (the measured 45%
        black, as the layer's explicit ARGB) over the page on a dark
        one."""
        if theme.get('dark_background'):
            return self._over((0, 0, 0), 0x73 / 255, self._rgb(theme['page']))
        return self._rgb(theme['ink'])

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
            ground = self._cover_ground(theme)
            ratio = self._ratio(self._over(fg, alpha, ground), ground)
            self.assertGreaterEqual(round(ratio, 2), 4.5, f'{slug}: {ratio:.2f}:1')

    # A text rule may fade itself only if the faded result has been
    # measured against the ground it actually sits on. Each entry names
    # what that ground is; the test below computes the worst case across
    # all 33 themes and fails if it ever drops under AA, so an allowance
    # cannot quietly rot into the defect it was carved out of.
    MEASURED_FADES = {'.slide-cover .summary': 'cover'}

    def test_a_text_rule_fades_itself_only_where_it_was_measured(self):
        """The two worst failures in the render sweep were both an
        `opacity` on a block of text: the 'currently reading' card at
        1.62:1 on 33/33 themes, and the 'no' verdict at 1.99:1 on 32/33.
        Both read as a style choice and were a contrast failure. An
        opacity on a text-bearing rule now has to be justified here."""
        css = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_STYLE, flags=re.DOTALL)
        offenders = []
        for block in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            selector, body = block.group(1).strip(), block.group(2)
            m = re.search(r'(?<![-\w])opacity:\s*([\d.]+)', body)
            if not m or float(m.group(1)) >= 1:
                continue
            if not re.search(r'(?<![-\w])(color|font-size|font-weight):', body):
                continue          # paints a ground or a glyph, not running text
            if selector in self.MEASURED_FADES:
                continue
            offenders.append(f'{selector} (opacity {m.group(1)})')
        self.assertEqual(offenders, [], 'a text rule may not fade itself unmeasured')

    def test_every_allowed_fade_still_clears_aa_on_every_theme(self):
        """Guards the exemption above. The cover summary paints
        --cover-fg at 78% over the cover ground; that is fine today
        (worst 5.05:1, catppuccin) and would stop being fine if either
        the alpha or a palette moved."""
        css = re.sub(r'/\*.*?\*/', '', self.lwp.TEMPLATE_STYLE, flags=re.DOTALL)
        for selector, ground_kind in self.MEASURED_FADES.items():
            self.assertEqual(ground_kind, 'cover')
            block = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', css)
            self.assertIsNotNone(block, selector)
            alpha = float(re.search(r'opacity:\s*([\d.]+)', block.group(1)).group(1))
            for slug, theme in self.lwp.THEMES.items():
                ground = self._cover_ground(theme)
                # --cover-fg is the page colour on a light theme, the ink
                # on a dark one (§9.5.2) — the cover inverts the page.
                fg = self._rgb(theme['page'] if not theme.get('dark_background')
                               else theme['ink'])
                ratio = self._ratio(self._over(fg, alpha, ground), ground)
                self.assertGreaterEqual(round(ratio, 2), 4.5,
                                        f'{selector} on {slug}: {ratio:.2f}:1')

    def test_a_body_link_keeps_the_ink_around_it(self):
        """§9.1/BACKLOG B3. The link had no rule at all and took the
        browser blue, measured at 1.03:1 on pop-violet and below AA on
        fifteen themes. Ink-on-page is the pair every theme is admitted
        on, so inheriting is the only treatment that cannot fail."""
        css = self.lwp.TEMPLATE_STYLE
        block = re.search(r'\.fact-content a,\s*\.full-article a \{([^}]*)\}', css)
        self.assertIsNotNone(block, 'the body-link rule is gone')
        body = block.group(1)
        self.assertRegex(body, r'color:\s*inherit')
        self.assertRegex(body, r'text-decoration:\s*underline')
        self.assertIn('var(--link-decoration-color)', body)
        self.assertIn('--link-decoration-color: currentColor;', css)

    def test_the_link_rule_never_reaches_navigation(self):
        """Underlining every <a> would have underlined the series-nav
        cards, the index cards and the slide-progress dots. The rule is
        scoped to the two containers the Markdown converter writes into,
        and nothing else."""
        css = self.lwp.TEMPLATE_STYLE
        # Comments first: a comment sitting above the rule lands inside
        # any [^{}]* that reaches back for the selector.
        selector = re.search(r'([^{}]*)\{[^}]*text-decoration-color: var\(--link-decoration-color\)',
                             re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)).group(1)
        # Checked part by part, not by looking for names that must be
        # absent: a bare `a` reaches every one of those containers
        # without naming any of them, which is how the first version of
        # this guard passed its own mutation.
        parts = [p.strip() for p in selector.strip().split(',') if p.strip()]
        self.assertTrue(parts)
        allowed = ('.fact-content ', '.full-article ')
        for part in parts:
            self.assertTrue(part.startswith(allowed),
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
            self.assertEqual(run('install', tmp).returncode, 0)
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
            self.assertEqual(run('install', tmp).returncode, 0)
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
            self.assertEqual(run('install', tmp).returncode, 0)
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
        result = run('themes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotRegex(result.stdout, r'&[a-zA-Z]+;|&#\d+;')
        self.assertNotIn('<code>', result.stdout)
        # The property names a note quotes must survive, or stripping the
        # markup would have taken the content with it.
        self.assertIn('color.page', result.stdout)

    def test_the_gallery_still_gets_the_markup_the_page_needs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'g.html'
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
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
        result = run('themes')
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

        result = run('themes', '--polarity', 'dark')
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
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')

        cards = re.findall(
            r'data-polarity="([^"]*)" data-intensity="([^"]*)" data-hue="([^"]*)" '
            r'data-name="(\S+) ', html)
        self.assertEqual(len(cards), len(self.lwp.THEMES))

        for polarity, intensity, hue in {(c[0], c[1], c[2]) for c in cards}:
            from_gallery = sorted(c[3] for c in cards
                                  if (c[0], c[1], c[2]) == (polarity, intensity, hue))
            result = run('themes', '--polarity', polarity,
                         '--intensity', intensity, '--hue', hue)
            self.assertEqual(result.returncode, 0, result.stderr)
            from_cli = sorted(re.findall(r'^  (\S+)  \[', result.stdout, re.MULTILINE))
            self.assertEqual(from_cli, from_gallery, (polarity, intensity, hue))

    def test_an_unknown_facet_value_is_a_fatal_error_that_lists_the_valid_ones(self):
        """Not an empty result: 'rouge' is a typo for 'red', and quietly
        answering "no theme is like that" would send the reader looking
        for a theme that is right there."""
        result = run('themes', '--hue', 'rouge')
        self.assertEqual(result.returncode, 1)
        self.assertIn('Unknown --hue', result.stderr)
        self.assertIn('red', result.stderr)

    def test_an_empty_but_legitimate_combination_says_so_and_succeeds(self):
        result = run('themes', '--polarity', 'dark', '--hue', 'orange')
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
        self.assertIn('lightwebpres themes', result.stdout)


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
            self.assertEqual(run('install', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            self._uncomment(settings, '# color.mark: #EBCB8B', 'color.mark: #EBCB8B')
            before = settings.read_text(encoding='utf-8').splitlines()

            result = run('set-theme', tmp, '--theme', 'evergreen')
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
            self.assertEqual(run('install', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            before_text = settings.read_text(encoding='utf-8')
            before_mtime = settings.stat().st_mtime_ns
            result = run('set-theme', tmp, '--theme', 'nord')
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
            self.assertEqual(run('install', tmp, '--theme', 'nord').returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            original = settings.read_text(encoding='utf-8')
            for slug in ('synthwave', 'crimson', 'sage', 'nord'):
                result = run('set-theme', tmp, '--theme', slug)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(settings.read_text(encoding='utf-8'), original)

    def test_a_series_that_was_never_installed_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run('set-theme', tmp, '--theme', 'nord')
            self.assertEqual(result.returncode, 1)
            self.assertIn('Run install first', result.stderr)

    def test_templates_without_settings_gets_a_fresh_scaffold(self):
        """A series installed before the rewrite has templates/ but no
        settings.conf: nothing to preserve, so a full scaffold for the
        chosen theme is written — the same file install --theme writes."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'templates').mkdir()
            result = run('set-theme', tmp, '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('fresh settings.conf written', result.stdout)
            written = (Path(tmp) / 'templates' / 'settings.conf').read_text(encoding='utf-8')
            self.assertEqual(written, self.lwp.build_settings_scaffold('nord'))

    def test_a_missing_theme_option_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('install', tmp).returncode, 0)
            missing = run('set-theme', tmp)
            self.assertEqual(missing.returncode, 1)
            self.assertIn('requires --theme', missing.stderr)

    def test_an_unknown_slug_is_fatal_and_names_the_catalogue_count(self):
        """The count is derived from THEMES (G6): an error message that
        says how many valid slugs exist cannot drift from the table."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('install', tmp).returncode, 0)
            unknown = run('set-theme', tmp, '--theme', 'nope')
            self.assertEqual(unknown.returncode, 1)
            self.assertIn('Unknown theme', unknown.stderr)
            self.assertIn(f'{len(self.lwp.THEMES)} valid slugs', unknown.stderr)

    def test_the_default_theme_is_named_default_in_that_message(self):
        """A file with no theme line is on the default theme, which is an
        answer to "replaced by what" — not a missing value to elide."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run('install', tmp).returncode, 0)
            result = run('set-theme', tmp, '--theme', 'crimson')
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
            self.assertEqual(run('install', tmp).returncode, 0)
            settings = Path(tmp) / 'templates' / 'settings.conf'
            before = settings.read_text(encoding='utf-8').splitlines()
            self.assertEqual(run('set-theme', tmp, '--theme', 'crimson').returncode, 0)
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
            self.assertEqual(run('install', str(root), '--theme', 'nord').returncode, 0)
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('set-theme', tmp, '--theme', 'gruvbox').returncode, 0)
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
            self.assertEqual(run('install', str(root), '--theme', 'dracula').returncode, 0)
            settings = root / 'templates' / 'settings.conf'
            self._uncomment(settings, '# color.mark: #F1FA8C', 'color.mark: #F1FA8C')
            scaffold(tmp, _MINIMAL_MD)
            self.assertEqual(run('set-theme', tmp, '--theme', 'nord').returncode, 0)
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
            self.assertEqual(run('install', tmp, '--theme', 'nord').returncode, 0)
            result = run('set-theme', tmp, '--theme', 'evergreen')
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
        skeleton = re.sub(r'/\*.*?\*/', '', self.lwp.extract_skeleton(), flags=re.S)
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
            self.assertEqual(run('install', str(root)).returncode, 0)
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
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_succeeds_with_multiple_covers(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T1\n# First cover\nsummary: S1.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T2\n# Second cover\nsummary: S2.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T2\n# Cover title\nsummary: S.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n',
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n',
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
    """§20.3.1: file/page_title/card_title/card_desc/card_label/nav_title/
    nav_desc all resolve as series.json entry > article's own meta block
    field of the same name > a content-derived fallback, most specific to
    least specific:

      file        : derived from `source` (.md -> .html)
      page_title  : the cover slide's own h1 -> the resolved `file`
      card_title  : page_title (resolved)
      card_desc   : the cover slide's own summary
      card_label  : '' (nothing to extrapolate)
      nav_title   : card_title (resolved)
      nav_desc    : card_desc (resolved)

    Nothing in this chain is fatal if absent everywhere — every field
    always resolves to SOMETHING, down to the article's own file name in
    the worst case. `source` is the only field series.json still requires."""

    def _build(self, tmp, meta_extra, series_entry_extra, cover_extra=''):
        root = Path(tmp)
        (root / 'articles').mkdir()
        md = (
            '<!-- lwp:meta -->\n' + meta_extra + '\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Cover H1\n' + cover_extra + '\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Cover H1\n' + cover_extra + '\n\n---\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            self.assertEqual(run('install', str(root)).returncode, 0)
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
        for needle in ('typo-units', 'typo-thousands', '--no-typography'):
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Original.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            clean = run('check', str(root), '--output', str(root / 'public'))
            # 3 files: the article page, index.html and README.md (§11.4)
            self.assertIn('3 file(s) OK, 0 file(s) different.', clean.stdout)

            changed_md = md.replace('Original.', 'Changed.')
            (root / 'articles' / 'a.md').write_text(changed_md, encoding='utf-8')
            drifted = run('check', str(root), '--output', str(root / 'public'))
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
            result = run('install', str(root))
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
                'nav_desc: Desc A\n---\n\n<!-- lwp:slide:cover -->\ntag: T\n# A\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n', encoding='utf-8')
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n', encoding='utf-8')
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
            '<!-- lwp:slide:cover -->\ntag: T\n# A\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# A\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
            'A first paragraph starts free text.\n\n'
            'tag: this looks like a field but is not one.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('this looks like a field but is not one', html)


class OptionalFieldOmission(unittest.TestCase):
    """§22.3/§22.4: a slide without tag: or a cover without summary: must
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
            self.assertNotIn('class="slide-tag"', html)
            self.assertIn('Title without a tag', html)

    def test_cover_without_summary_builds_successfully(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Cover without summary\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\nsource: Some Author, 2024.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
                f'nav_desc: D\n---\n\n<!-- lwp:slide:cover -->\ntag: T\n# {name}\n'
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
            '<!-- lwp:slide -->\ntag: T\nh2: Title via field\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\nh1: Title via field\nsummary: Summary.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The takeaway\nContent with a fact-label.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent without a fact-label.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nFirst paragraph.\n\nSecond paragraph.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Slide title\n# Body heading\n\nBody.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: Source\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('check', str(root), '--output', str(root / 'public'))
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n\n---\n\n'
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
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n\n---\n\n'
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
            result = run('install', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / '.gitlab-ci.yml').exists())

    def test_install_with_flag_creates_gitlab_ci_yml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('install', str(root), '--gitlab-ci')
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\ncomment: COVER-SECRET\n'
            '# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T2\ncomment: STANDARD-SECRET\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\ncomment: a note\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_comment_on_standard_slide_does_not_become_fact_box_content(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\ncomment: a note\n## Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Real title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide -->\ntag: T\n## The real slide title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# The real cover title\nsummary: Summary.\n\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Real title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
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
            f'<!-- lwp:slide:cover -->\ntag: T\n# Title\n{summary_line}'
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


class DraftArticles(unittest.TestCase):
    """§20.3.1/GLOSSARY.md: draft: true excludes an article from the
    build entirely (no page, no index card, no nav entry) unless
    --include-drafts, which builds it with a centered banner."""

    def _series(self, tmp, b_meta_extra='', b_entry_extra=None):
        root = Path(tmp)
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Live article\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Live\nsummary: Live summary.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n', encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(
            f'<!-- lwp:meta -->\npage_title: Draft article\n{b_meta_extra}---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Draft\nsummary: Draft summary.\n', encoding='utf-8')
        entry_b = {'page_source': 'b.md'}
        entry_b.update(b_entry_extra or {})
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}, entry_b],
        }), encoding='utf-8')
        return root

    def test_draft_excluded_from_page_index_and_nav_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='draft: true\n')
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
            root = self._series(tmp, b_meta_extra='draft: true\n')
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

    def test_series_json_false_overrides_meta_block_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='draft: true\n',
                                b_entry_extra={'draft': False})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'b.html').exists())
            html_b = (root / 'public' / 'b.html').read_text(encoding='utf-8')
            self.assertNotIn('draft-banner', html_b)

    def test_non_true_values_are_not_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series(tmp, b_meta_extra='draft: soon\n')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'b.html').exists())


class LegacyFieldMigrationErrors(unittest.TestCase):
    """v1.0 freeze (JOURNAL-1.0.md §2.1): the retired series.json keys
    `source`/`file` produce an explicit renamed-in-v1.0 error, not a
    mystifying missing-required-field one."""

    def _series_with_keys(self, tmp, entry):
        root = Path(tmp)
        (root / 'articles').mkdir()
        (root / 'articles' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: T\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# T\nsummary: S.\n', encoding='utf-8')
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_legacy_source_key_gets_migration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_keys(tmp, {'source': 'a.md'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('renamed to "page_source" in v1.0', result.stderr)

    def test_legacy_file_key_gets_migration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_keys(tmp, {'page_source': 'a.md', 'file': 'a.html'})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('renamed to "page_dest" in v1.0', result.stderr)


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
          '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n')

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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: T2\n## Second\nsummary: S2.\nfact-label: F\n\nBody.\n'
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
                b'<!-- lwp:slide:cover -->\ntag: T\n# Broken \xff\xfe\nsummary: S.\n')
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
                    f'<!-- lwp:slide:cover -->\ntag: T\n# Article {name}\nsummary: Résumé : test.\n\n---\n\n'
                    f'<!-- lwp:slide -->\ntag: F\n## Fiche\nsummary: S.\nfact-label: Fait\n\nCorps **gras**.\n\n---\n\n'
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
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: S.\n'
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
                    '<!-- lwp:slide:cover -->\ntag: T\n# T\nsummary: S.\n', encoding='utf-8')
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
                '<!-- lwp:slide:cover -->\ntag: T\n# T\nsummary: S.\n'))
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
            '<!-- lwp:slide:cover -->\ntag: Été\n# À 東京 🗼\nsummary: всё хорошо.\n\n---\n\n'
            '<!-- lwp:slide -->\ntag: نص\n## عنوان عربي\nsummary: RTL.\nfact-label: Факт\n\nCorps 中文 🎉.\n'
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
    """The property engine (§9 rewrite), staged in the executable but not yet
    wired into build. These pin the interface itself — one cascade for every
    property, references resolved by axis-fixed namespace, errors that name
    their key — before the full inventory lands on top of it."""

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
        self.assertIn('monospace', r['tag.font'])
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
            self.resolve({'tag.weight': '600'})
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
            self.resolve({'tag.fg': 'summary.fg', 'summary.fg': 'tag.fg'})
        self.assertIn('cycle', str(ctx.exception))
        self.assertIn('tag.fg -> summary.fg -> tag.fg', str(ctx.exception))

    def test_reference_chain_capped_at_three_hops(self):
        layer = {'tag.fg': 'summary.fg', 'summary.fg': 'highlight.fg',
                 'highlight.fg': 'ink-quiet', 'color.ink-quiet': 'ink'}
        with self.assertRaises(self.lwp.PropertyError) as ctx:
            self.resolve(layer)
        self.assertIn('3 hops', str(ctx.exception))

    def test_colours_normalise_to_argb(self):
        r = self.resolve({'color.page': '#abc',
                          'summary.fg': '#11223344',
                          'tag.fg': 'transparent'})
        self.assertEqual(r['color.page'], '#AABBCCFF')
        self.assertEqual(r['summary.fg'], '#11223344')
        self.assertEqual(r['tag.fg'], '#00000000')

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

    def test_skeleton_extraction_leaves_no_variable_behind(self):
        # The gap check is the completeness rule made mechanical: after the
        # driven declarations are removed, any surviving var() is a visual
        # decision the registry does not expose. It found four real registry
        # gaps on its first run; this pins that it now finds none.
        skeleton = self.lwp.extract_skeleton()
        for line in skeleton.splitlines():
            for var in re.findall(r'var\((--[a-z-]+)', line):
                self.assertEqual(var, '--content-max',
                                 f'skeleton still references {var}')

    def test_skeleton_keeps_media_overrides_and_shorthand_styles(self):
        skeleton = self.lwp.extract_skeleton()
        self.assertIn('@media (max-width: 600px)', skeleton)
        # border shorthands lose colour and width to the engine but keep
        # their style token, or every rule would silently vanish
        self.assertIn('border-bottom-style: solid', skeleton)
        self.assertIn('outline-style: solid', skeleton)

    def test_composed_sheet_is_engine_then_skeleton(self):
        # Order is load-bearing: the skeleton's @media overrides share
        # specificity with the engine's base values and must win by coming
        # later.
        full = self.lwp.compose_stylesheet(self.resolve({}))
        self.assertLess(full.index(':root'), full.index('@media'))
        self.assertLess(full.index('--tag-fg:'), full.index('@media'))

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


if __name__ == '__main__':
    unittest.main()
