"""Slide headings/summaries use inline formatting; empty table headers disappear."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import run
else:
    from test_lightwebpres import run

ROOT = Path(__file__).resolve().parents[1]


class InlineSlideFields(unittest.TestCase):
    def build(self, source, options=()):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch, prefix='inline-fields-') as temporary:
            root = Path(temporary)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'Inline fields'},
                'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}],
            }), encoding='utf-8')
            (root / 'sources' / 'a.md').write_text(source, encoding='utf-8')
            (root / 'sources' / 'b.md').write_text(
                '<!-- lwp:meta -->\n---\n<!-- lwp:slide:cover -->\nslug: b\n# Other\n', encoding='utf-8')
            env = {**os.environ, 'TMPDIR': str(scratch)}
            built = run('build', root, '--lang', 'en', *options, env=env, cwd=ROOT)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            html = (root / 'public' / ('series.html' if options else 'a.html')).read_text(encoding='utf-8')
            audited = run('audit', root, '--lang', 'en', env=env, cwd=ROOT)
            return html, audited.stdout + audited.stderr

    def test_headings_and_summaries_render_supported_inline_markup(self):
        source = ('<!-- lwp:meta -->\n---\n\n'
                  '<!-- lwp:slide:cover -->\nslug: cover\n'
                  '# A **bold** and *italic* [title](https://example.org)\n'
                  'summary: A {u}line{/u} and `code` with **strength**.\n\n---\n\n'
                  '<!-- lwp:slide -->\nslug: detail\n'
                  '## Another **heading**\nsummary: *Short* [summary](https://example.org).\n'
                  '\n---\n\n<!-- lwp:slide:unit-index -->\nslug: contents\n'
                  '## **Contents**\nsummary: *Read here*.\n')
        for options in ((),):
            with self.subTest(options=options):
                html, audit = self.build(source, options)
                self.assertIn('<strong>bold</strong>', html)
                self.assertIn('<em>italic</em>', html)
                self.assertIn('<span style="text-decoration:underline">line</span>', html)
                self.assertIn('<code>code</code>', html)
                self.assertIn('<h2>Another <strong>heading</strong></h2>', html)
                self.assertIn('<h2><strong>Contents</strong></h2>', html)
                self.assertIn('A bold and italic title</title>', html)
                self.assertIn('<span class="lwp-unit-index-title">Another heading</span>', html)
                self.assertNotIn('`summary:` contains Markdown', audit)

    def test_escapes_code_and_html_attributes_keep_literal_delimiters(self):
        source = ('<!-- lwp:meta -->\npage_title: Literals\n---\n\n'
                  '<!-- lwp:slide -->\nslug: literals\n'
                  '## \\*literal\\* and `**code**`\n'
                  'summary: \\[not a link](https://example.org) and \\{u}no underline{/u}.\n\n'
                  '<span data-note="\\*attribute\\*">Body **bold**</span>\n')
        html, _ = self.build(source)
        self.assertIn('<h2>*literal* and <code>**code**</code></h2>', html)
        self.assertIn('[not a link](https://example.org) and {u}no underline{/u}', html)
        self.assertIn('data-note="\\*attribute\\*"', html)
        self.assertIn('Body <strong>bold</strong>', html)

    def test_other_structural_fields_remain_literal(self):
        source = ('<!-- lwp:meta -->\npage_title: Literal fields\n---\n\n'
                  '<!-- lwp:slide -->\nslug: other\nkicker: **Literal kicker**\n'
                  '## A formatted **title**\nfact-label: **Literal label**\n\nBody.\n')
        html, _ = self.build(source)
        self.assertIn('<span class="slide-kicker">**Literal kicker**</span>', html)
        self.assertIn('<div class="fact-label">**Literal label**</div>', html)

    def test_derived_metadata_keeps_literal_code_angles_and_ampersands(self):
        html, _ = self.build('<!-- lwp:meta -->\n---\n\n'
                             '<!-- lwp:slide:cover -->\nslug: cover\n'
                             '# **Fish** & `<chips>`\nsummary: A `<value>` example.\n\n'
                             '---\n\n<!-- lwp:slide:unit-index -->\nslug: contents\n## Contents\n')
        self.assertIn('Fish &amp; &lt;chips&gt;</title>', html)
        self.assertIn('content="A &lt;value&gt; example."', html)
        self.assertIn('Fish &amp; &lt;chips&gt;</span>', html)

    def test_index_labels_match_literal_entities_rendered_in_headings(self):
        html, _ = self.build('<!-- lwp:meta -->\n---\n\n'
                             '<!-- lwp:slide:cover -->\nslug: cover\n'
                             '# <a href="https://example.org">A &amp; B</a>\n\n'
                             '---\n\n<!-- lwp:slide:unit-index -->\nslug: contents\n## Contents\n')
        self.assertIn('>A &amp;amp; B</a></h1>', html)
        self.assertIn('<span class="lwp-unit-index-title">A &amp;amp; B</span>', html)

    def test_escaped_url_delimiters_do_not_leave_private_tokens(self):
        html, _ = self.build('<!-- lwp:meta -->\npage_title: Links\n---\n\n'
                             '<!-- lwp:slide -->\nslug: link\n'
                             '## [A link](https://example.org/a\\(b\\))\nsummary: Literal \\* marker.\n')
        self.assertIn('href="https://example.org/a(b)"', html)
        self.assertNotIn('\x00', html)

    def test_empty_headers_are_omitted_but_partial_headers_remain(self):
        source = ('<!-- lwp:meta -->\npage_title: Headers\n---\n\n'
                  '<!-- lwp:slide -->\nslug: blank\n## Layout\n\n'
                  '| |   |\n| --- | --- |\n| Left | Right |\n\n---\n\n'
                  '<!-- lwp:slide -->\nslug: partial\n## Data\n\n'
                  '| Label | |\n| --- | --- |\n| A | B |\n')
        html, _ = self.build(source)
        blank = re.search(r'<section [^>]*id="blank"[^>]*>(.*?)</section>', html, re.S).group(1)
        partial = re.search(r'<section [^>]*id="partial"[^>]*>(.*?)</section>', html, re.S).group(1)
        self.assertNotIn('<thead>', blank)
        self.assertIn('<tbody>', blank)
        self.assertEqual(blank.count('<td>'), 2)
        self.assertIn('<thead>', partial)
        self.assertEqual(partial.count('<th>'), 2)
