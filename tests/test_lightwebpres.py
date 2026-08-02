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
    entry = {'file': file_name, 'source': source_name, 'nav_title': 'A', 'nav_desc': 'A'}
    if series_extra:
        entry.update(series_extra)
    (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
    return root


class BuildGoldenPath(unittest.TestCase):
    """Behaviors that already work — must never regress."""

    def test_build_smoke(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
            'First paragraph.\n\nSecond paragraph, clearly distinct.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<p class="fact-content">First paragraph.</p>', html)
            self.assertIn('<p class="fact-content">Second paragraph, clearly distinct.</p>', html)

    def test_hardwrap_without_blank_line_is_joined_into_one_paragraph(self):
        # Standard Markdown rule (spec §6.1): consecutive lines with no
        # blank line between them merge into a single paragraph.
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
            'A sentence broken\nby mistake across two physical lines.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn(
                '<p class="fact-content">A sentence broken by mistake across two physical lines.</p>',
                html,
            )


class FatalErrorCases(unittest.TestCase):
    """Spec §22: cases that must make the build fail (non-zero exit code),
    not produce a corrupted or silently wrong result."""

    def test_full_article_missing_article_field_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n\n---\n\n<!-- lwp:slide:full-article -->\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_duplicate_full_article_slides_is_fatal(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
        md = '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n'
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_cover_with_unexpected_trailing_content_is_fatal(self):
        # Spec §22.12: a cover slide has no fact-box, so unexpected
        # content after its fields must be rejected, not silently dropped.
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
            )
            (root / 'articles' / 'a1.md').write_text(md, encoding='utf-8')
            (root / 'articles' / 'a2.md').write_text(md, encoding='utf-8')
            series = {'articles': [
                {'file': 'a.html', 'source': 'a1.md', 'nav_title': 'A1', 'nav_desc': 'A1'},
                {'file': 'a.html', 'source': 'a2.md', 'nav_title': 'A2', 'nav_desc': 'A2'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)


class LanguageStrings(unittest.TestCase):
    """§7.3/§7.4: interface strings follow --lang, and a language/{lang}.json
    override only needs to define the keys it wants to change."""

    def _series(self, tmp):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('No warnings', result.stdout)

    def test_audit_warns_when_no_cover(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('no cover slide', result.stdout)

    def test_audit_warns_when_cover_not_first(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T2\n# Cover title\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('is not a cover', result.stdout)


class HighlightField(unittest.TestCase):
    """§4.3: the highlight/highlight-caption fields (renamed from the former
    'mesure' naming) must actually render, and must be omitted when absent."""

    def test_highlight_renders_figure_and_caption(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nsummary: No highlight here.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertNotIn('class="highlight"', html)


class MarkdownConversion(unittest.TestCase):
    """§3.2/§6: the full-article body goes through convert_markdown() and
    must support standard Markdown, not just paragraphs."""

    def _build_article_html(self, article_body):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\nfile: b.html\npage_title: Article B\nnav_title: Article B\n'
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
                {'file': 'a.html', 'source': 'a.md', 'nav_title': 'Article A',
                 'nav_desc': 'Desc A', 'card_label': 'Article 1',
                 'card_title': 'Custom card title A', 'card_desc': 'Custom card desc A'},
                {'file': 'b.html', 'source': 'b.md', 'nav_title': 'Article B',
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


class IncrementalBuildOnly(unittest.TestCase):
    """§11.3.1: `build --only <file>` rebuilds a single article instead of
    the whole series, but only when nothing that affects index.html/
    series-nav changed since the last build — checked via a fingerprint
    cache (--nav-cache, default .lwp-cache/nav.json)."""

    def _build_series(self, tmp):
        root = Path(tmp)
        (root / 'articles').mkdir()
        md_a = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Article A\nnav_title: Article A\n'
            'nav_desc: Desc A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article A\nsummary: Summary A.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        md_b = (
            '<!-- lwp:meta -->\nfile: b.html\npage_title: Article B\nnav_title: Article B\n'
            'nav_desc: Desc B\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Article B\nsummary: Summary B.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
        series = {
            'series_meta': {'title': 'The series', 'subtitle': '', 'intro': ''},
            'articles': [
                {'file': 'a.html', 'source': 'a.md', 'nav_title': 'Article A', 'nav_desc': 'Desc A'},
                {'file': 'b.html', 'source': 'b.md', 'nav_title': 'Article B', 'nav_desc': 'Desc B'},
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Article A\nnav_title: Article A\n'
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Article A\nnav_title: Article A Renamed\n'
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
                '<!-- lwp:meta -->\nfile: c.html\npage_title: Article C\nnav_title: Article C\n'
                'nav_desc: Desc C\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Article C\nsummary: Summary C.\n\n---\n\n'
            )
            (root / 'articles' / 'c.md').write_text(md_c, encoding='utf-8')
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'].append({'file': 'c.html', 'source': 'c.md',
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: « Une citation.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('«\xa0Une citation.', html)

    def test_typography_nbsp_before_percent(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            self._both_ends(re.search(r'<p class="fact-content">(.*?)</p>', html).group(1))

    def test_leading_nbsp_in_field_value_is_not_swallowed_by_regex(self):
        """Regression: the field regex used `key:\\s*(.*)`, and \\s
        matches U+00A0 exactly like str.strip() does — a leading nbsp
        right after the colon was silently dropped even after strip_ws()
        started protecting the rest of the pipeline."""
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide -->\ntag: T\n## Titre\nsummary:{self.NBSP}Résumé\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, md)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            summary = re.search(r'<p class="summary">(.*?)</p>', html).group(1)
            self.assertTrue(summary.startswith(self.NBSP), repr(summary))

    def test_page_title_survives(self):
        md = (
            f'<!-- lwp:meta -->\nfile: a.html\npage_title: {self._wrap("Titre de page")}\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\n---\n\n'
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: {self._wrap("Description")}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir(parents=True, exist_ok=True)
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': 'a.html', 'source': 'a.md'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            index_html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self._both_ends(re.search(r'<div class="article-desc">(.*?)</div>', index_html).group(1))

    def test_full_article_headings_paragraph_table_and_footnote(self):
        w = self._wrap
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre A\nsummary: {summary}\n'
        )
        md_b = (
            '<!-- lwp:meta -->\nfile: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n'
            f'{meta_extra_b}---\n\n'
            f'<!-- lwp:slide:cover -->\ntag: T\n# Titre B\nsummary: {summary}\n'
        )
        (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
        (root / 'articles' / 'b.md').write_text(md_b, encoding='utf-8')
        entries = [
            {'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
            {'file': 'b.html', 'source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B'},
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Titre à 50 % fini\nnav_title: A\n'
                'nav_desc: A\ntypo: off\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Titre\nsummary: Résumé.\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
                '<!-- lwp:meta -->\nfile: b.html\npage_title: B\nnav_title: B\nnav_desc: B\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# B\nsummary: Summary.\n',
                encoding='utf-8',
            )
            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['articles'].append({'file': 'b.html', 'source': 'b.md', 'nav_title': 'B', 'nav_desc': 'B'})
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nContent.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_succeeds_with_multiple_covers(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
        del entry[field]
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_missing_file_field_derives_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_missing_field(tmp, 'file')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'a.html').exists())

    def test_missing_source_field_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_missing_field(tmp, 'source')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_nonexistent_source_file_is_a_warning_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            series = {'articles': [
                {'file': 'a.html', 'source': 'missing.md', 'nav_title': 'A', 'nav_desc': 'A'},
            ]}
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'public' / 'a.html').exists())


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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n',
            encoding='utf-8',
        )
        series = {'articles': [
            {'file': file_value, 'source': source_value, 'nav_title': 'A', 'nav_desc': 'A'},
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n',
                encoding='utf-8',
            )
            series = {'articles': [
                {'file': 'a.html', 'source': 'a.MD', 'nav_title': 'A', 'nav_desc': 'A'},
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
        entry = {'source': 'a.md'}
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
            root = self._build(tmp, 'file: renamed.html\npage_title: Test', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / 'public' / 'renamed.html').exists())
            self.assertFalse((root / 'public' / 'a.html').exists())

    def test_series_json_file_overrides_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(
                tmp, 'file: from-meta.html\npage_title: Test',
                {'file': 'from-series-json.html'},
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
        with tempfile.TemporaryDirectory() as tmp:
            root = self._build(tmp, 'page_title: Page title', {})
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'index.html').read_text(encoding='utf-8')
            self.assertIn('<div class="article-number"></div>', html)

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
        entry = {'source': 'a.md'}
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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


class TypographyTagProtection(unittest.TestCase):
    """§P2/§19.3: typography rules must never be able to corrupt HTML tag
    syntax in already-assembled HTML (fact-box content, full articles),
    regardless of what a language/*.json override file's rules do."""

    def test_custom_rule_does_not_corrupt_link_tag_attribute(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\nsummary: Original.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            run('build', str(root), '--output', str(root / 'public'))
            clean = run('check', str(root), '--output', str(root / 'public'))
            self.assertIn('1 file(s) OK, 0 file(s) different.', clean.stdout)

            changed_md = md.replace('Original.', 'Changed.')
            (root / 'articles' / 'a.md').write_text(changed_md, encoding='utf-8')
            drifted = run('check', str(root), '--output', str(root / 'public'))
            self.assertIn('0 file(s) OK, 1 file(s) different.', drifted.stdout)


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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: A\nnav_title: Article A\n'
                'nav_desc: Desc A\n---\n\n<!-- lwp:slide:cover -->\ntag: T\n# A\n'
            )
            (root / 'articles' / 'a.md').write_text(md_a, encoding='utf-8')
            series = {
                'series_meta': {'title': 'My Series', 'subtitle': 'A subtitle'},
                'articles': [
                    {'file': 'a.html', 'source': 'a.md', 'nav_title': 'Article A', 'nav_desc': 'Desc A'},
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
        entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
        entry[field] = value
        (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
        return root

    def test_absolute_file_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_file_value(tmp, 'file', '/tmp/evil.html')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)

    def test_traversal_source_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._series_with_file_value(tmp, 'source', '../../etc/passwd')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)

    def test_traversal_article_field_is_rejected(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:full-article -->\narticle: ../../../etc/passwd\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unsafe', result.stderr)


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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\ntag: T\n# A\n'
        )
        (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
        series = {
            'series_meta': {'title': malicious_title},
            'articles': [{'file': 'a.html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}],
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
                '<!-- lwp:meta -->\nfile: a".html\npage_title: A\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# A\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            series = {'articles': [
                {'file': 'a".html', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'},
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
                f'<!-- lwp:meta -->\nfile: {name}.html\npage_title: {name}\nnav_title: {name}\n'
                f'nav_desc: D\n---\n\n<!-- lwp:slide:cover -->\ntag: T\n# {name}\n'
            )
            (root / 'articles' / f'{name}.md').write_text(md, encoding='utf-8')
            entries.append({'file': f'{name}.html', 'source': f'{name}.md',
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


class H2FieldForm(unittest.TestCase):
    """§4.3: h2: as a key-value field is equivalent to a Markdown ## Title
    heading — only the ## form is exercised elsewhere in this suite."""

    def test_h2_field_form_renders_like_markdown_heading(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\nh2: Title via field\nsummary: Summary.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<h2>Title via field</h2>', html)


class FactLabelOptional(unittest.TestCase):
    """§4.3: free text after a standard slide's fields goes into the
    fact-box when fact-label: is present, or a bare <p> paragraph
    (no fact-box wrapper) when it's absent."""

    def test_fact_label_present_produces_fact_box(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The takeaway\nContent with a fact-label.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'), '--lang', 'en')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertIn('<div class="fact-box">', html)
            self.assertIn('<div class="fact-label">The takeaway</div>', html)
            self.assertIn('<p class="fact-content">Content with a fact-label.</p>', html)

    def test_fact_label_absent_produces_bare_paragraph(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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


class FactBoxBlockquoteAndCode(unittest.TestCase):
    """§6.3: fact-box free text shares convert_markdown() with the
    full-article body, so blockquotes and code must work there too, not
    just in a full-article file."""

    def test_fact_box_supports_blockquote_and_inline_code(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': '', 'source': 'a.md', 'nav_title': 'A', 'nav_desc': 'A'}
            (root / 'series.json').write_text(json.dumps({'articles': [entry]}), encoding='utf-8')
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertNotEqual(result.returncode, 0)

    def test_empty_string_nav_title_falls_back_to_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'articles').mkdir()
            md = (
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: Meta title\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': '', 'nav_desc': 'A'}
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
                '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_desc: A\n---\n\n'
                '<!-- lwp:slide:cover -->\ntag: T\n# Title\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\n'
            )
            (root / 'articles' / 'a.md').write_text(md, encoding='utf-8')
            entry = {'file': 'a.html', 'source': 'a.md', 'nav_title': '', 'nav_desc': 'A'}
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide -->\ntag: T\n## Title\nfact-label: The fact\n'
            'A line<br>with a break, then <hr> and '
            '<script>if (1 < 2 && 3 > 2) { void 0; }</script> inline.\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = scaffold(tmp, md)
            result = run('build', str(root), '--output', str(root / 'public'))
            self.assertEqual(result.returncode, 0, result.stderr)


class HeadingInBodyIsContentNotRetitle(unittest.TestCase):
    """§22.2: the field->free-text switch applies to # / ## lines exactly
    like key: value fields — a heading appearing after body content has
    already started is fact-box content (rendered as a real heading by
    convert_markdown), not a silent overwrite of the slide's own h1/h2."""

    def test_heading_after_body_content_does_not_overwrite_slide_h2(self):
        md = (
            '<!-- lwp:meta -->\nfile: a.html\npage_title: Test\nnav_title: A\nnav_desc: A\n---\n\n'
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
                '<p class="fact-content">First paragraph of body text.</p>',
                html,
            )
            self.assertIn('<h2>This looks like a heading in the body</h2>', html)
            # Only one <h2> may be the slide title; the second is nested
            # inside the fact-box, not a sibling slide title.
            self.assertEqual(html.count('<h2>'), 2)


if __name__ == '__main__':
    unittest.main()
