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
import re
import subprocess
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
            self.assertNotIn('--yellow', title)
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


class RefreshTemplatesDuplicateMarker(unittest.TestCase):
    """A second copy of the customization marker pasted into the author's
    own CSS must not cause refresh-templates to drop the author rules
    between the two markers (rfind -> find)."""

    def test_author_css_between_duplicate_markers_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 's'
            self.assertEqual(run('install', str(root), '--lang', 'en').returncode, 0)
            marker = ('/* === Personnalisations locales : refresh-templates '
                      'conserve tout ce qui suit cette ligne === */')
            style = root / 'templates' / 'style.css'
            style.write_text(style.read_text(encoding='utf-8') +
                             f'\n/*BLOCK_A*/\n{marker}\n/*BLOCK_B*/\n', encoding='utf-8')
            self.assertEqual(run('refresh-templates', str(root)).returncode, 0)
            kept = style.read_text(encoding='utf-8')
            self.assertIn('BLOCK_A', kept)
            self.assertIn('BLOCK_B', kept)


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
        html = self._build_article_html('![p](img/p.png "Cap")\n')
        self.assertIn('.figure-caption', html)
        self.assertIn('color: var(--grey)', html)


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
            self.assertTrue((root / 'templates' / 'style.css').exists())
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
    """§12/§18: a templates/style.css or templates/nav.js placed by the
    author must be used instead of the built-in default."""

    def test_custom_style_css_is_used(self):
        md = (
            '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            (root / 'templates').mkdir()
            (root / 'templates' / 'style.css').write_text(
                '/* CUSTOM-MARKER-CSS */', encoding='utf-8',
            )
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('/* CUSTOM-MARKER-CSS */', html)

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
    """§9.4/§11.6: refresh-templates updates the built-in portion of
    templates/style.css and templates/nav.js after an executable upgrade,
    without discarding local customizations."""

    MARKER = '/* === Personnalisations locales : refresh-templates conserve tout ce qui suit cette ligne === */'

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
            before_style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            before_nav = (root / 'templates' / 'nav.js').read_text(encoding='utf-8')
            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('up to date', result.stdout.lower())
            self.assertEqual((root / 'templates' / 'style.css').read_text(encoding='utf-8'), before_style)
            self.assertEqual((root / 'templates' / 'nav.js').read_text(encoding='utf-8'), before_nav)

    def test_style_css_refreshes_builtin_part_and_keeps_customization_after_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            style_path = root / 'templates' / 'style.css'
            stale = style_path.read_text(encoding='utf-8').replace(
                ':root {', '/* STALE-BUILTIN-RULE */\n:root {', 1,
            )
            stale += '\n  .my-custom { color: red; }\n'
            style_path.write_text(stale, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

            refreshed = style_path.read_text(encoding='utf-8')
            self.assertNotIn('STALE-BUILTIN-RULE', refreshed)
            self.assertIn('.my-custom { color: red; }', refreshed)
            self.assertIn(self.MARKER, refreshed)

    def test_style_css_without_marker_is_skipped_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            style_path = root / 'templates' / 'style.css'
            legacy = '/* old scaffold, predates the marker */\n.old-custom { color: blue; }\n'
            style_path.write_text(legacy, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(self.MARKER, result.stderr)
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
    """§9.5/§11.1/§11.6/§11.7: install --theme substitutes the six palette
    variables from THEMES, records which theme was applied in a marker
    refresh-templates can read back, and themes-gallery documents every
    entry purely from that same table."""

    THEME_MARKER_RE = re.compile(r'^/\* lightwebpres-theme: (\S+) \*/$', re.MULTILINE)

    def test_install_without_theme_uses_default_and_no_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--yellow: #FFFC00;', style)
            self.assertIsNone(self.THEME_MARKER_RE.search(style))

    def test_install_with_valid_theme_substitutes_colors_and_records_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('install', str(root), '--theme', 'nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Nord', result.stdout)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--yellow: #EBCB8B;', style)
            self.assertIn('--dark: #2E3440;', style)
            self.assertNotIn('#FFFC00', style)
            m = self.THEME_MARKER_RE.search(style)
            self.assertIsNotNone(m)
            self.assertEqual(m.group(1), 'nord')

    def test_install_with_valid_theme_keeps_the_personalization_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'dracula').returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn(RefreshTemplates.MARKER, style)

    def test_install_with_unknown_theme_is_a_fatal_error_listing_valid_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run('install', str(root), '--theme', 'not-a-real-theme')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('not-a-real-theme', result.stderr)
            self.assertIn('nord', result.stderr)
            self.assertFalse((root / 'templates').exists())

    def test_refresh_templates_reapplies_known_theme_after_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'dracula').returncode, 0)
            style_path = root / 'templates' / 'style.css'
            stale = style_path.read_text(encoding='utf-8').replace(
                '--yellow: #F1FA8C;', '--yellow: #F1FA8C;\n  /* STALE-BUILTIN-RULE */', 1,
            )
            style_path.write_text(stale, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

            refreshed = style_path.read_text(encoding='utf-8')
            self.assertNotIn('STALE-BUILTIN-RULE', refreshed)
            self.assertIn('--yellow: #F1FA8C;', refreshed)
            self.assertIn('--dark: #282A36;', refreshed)
            m = self.THEME_MARKER_RE.search(refreshed)
            self.assertIsNotNone(m)
            self.assertEqual(m.group(1), 'dracula')

    def test_refresh_templates_falls_back_to_default_with_warning_for_unknown_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'nord').returncode, 0)
            style_path = root / 'templates' / 'style.css'
            edited = style_path.read_text(encoding='utf-8').replace(
                '/* lightwebpres-theme: nord */', '/* lightwebpres-theme: retired-theme */', 1,
            )
            style_path.write_text(edited, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('retired-theme', result.stderr)

            refreshed = style_path.read_text(encoding='utf-8')
            self.assertIn('--yellow: #FFFC00;', refreshed)
            self.assertIsNone(self.THEME_MARKER_RE.search(refreshed))

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
            self.assertIn('--yellow:#EBCB8B', html)
            self.assertIn('lightwebpres install my-series --theme nord', html)
            open_tags = html.count('<article class="theme-card">')
            close_tags = html.count('</article>')
            self.assertEqual(open_tags, 9)
            self.assertEqual(open_tags, close_tags)

    def test_themed_build_actually_uses_the_substituted_colors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'gruvbox').returncode, 0)
            self.assertEqual(run('demo', str(root)).returncode, 0)
            self.assertEqual(run('build', str(root)).returncode, 0)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('--yellow: #D79921;', index_html)


class FactStrongEmphasis(unittest.TestCase):
    """§9.1/§9.5: --fact-strong-weight/--fact-strong-style/--fact-strong-
    highlight independently control a fact-box's Markdown **bold**
    rendering (weight, italic, and mark-style background), decoupled
    from each other and from the semantic <strong> markup itself."""

    def test_default_install_has_the_three_properties_matching_prior_look(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--fact-strong-weight: bold;', style)
            self.assertIn('--fact-strong-style: normal;', style)
            self.assertIn('--fact-strong-highlight: var(--yellow);', style)

    def test_themes_set_distinct_fact_strong_treatments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'solarized').returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--fact-strong-weight: bold;', style)
            self.assertIn('--fact-strong-style: italic;', style)
            self.assertIn('--fact-strong-highlight: transparent;', style)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'dracula').returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--fact-strong-highlight: var(--green);', style)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'catppuccin').returncode, 0)
            style = (root / 'templates' / 'style.css').read_text(encoding='utf-8')
            self.assertIn('--fact-strong-weight: normal;', style)
            self.assertIn('--fact-strong-style: italic;', style)

    def test_refresh_templates_reapplies_fact_strong_properties_for_a_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root), '--theme', 'solarized').returncode, 0)
            style_path = root / 'templates' / 'style.css'
            stale = style_path.read_text(encoding='utf-8').replace(
                '--fact-strong-style: italic;', '--fact-strong-style: italic; /* STALE */', 1,
            )
            style_path.write_text(stale, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)

            refreshed = style_path.read_text(encoding='utf-8')
            self.assertNotIn('STALE', refreshed)
            self.assertIn('--fact-strong-style: italic;', refreshed)
            self.assertIn('--fact-strong-highlight: transparent;', refreshed)

    def test_user_can_keep_highlight_and_drop_bold_via_override(self):
        """The exact motivating use case: highlight kept, bold dropped,
        without hand-writing a full replacement rule."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(run('install', str(root)).returncode, 0)
            style_path = root / 'templates' / 'style.css'
            custom = (style_path.read_text(encoding='utf-8') + '\n'
                      ':root { --fact-strong-weight: normal; }\n')
            style_path.write_text(custom, encoding='utf-8')

            result = run('refresh-templates', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            refreshed = style_path.read_text(encoding='utf-8')
            self.assertIn(':root { --fact-strong-weight: normal; }', refreshed)
            self.assertIn('--fact-strong-highlight: var(--yellow);', refreshed)

    def test_themes_gallery_shows_a_bolded_word_styled_per_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'gallery.html'
            self.assertEqual(run('themes-gallery', str(out)).returncode, 0)
            html = out.read_text(encoding='utf-8')
            self.assertIn('<strong>', html)
            self.assertIn('--fact-strong-weight:normal;--fact-strong-style:italic;'
                           '--fact-strong-highlight:transparent;', html)


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




if __name__ == '__main__':
    unittest.main()
