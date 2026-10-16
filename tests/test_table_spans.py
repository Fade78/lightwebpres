"""Only DokuWiki-style merge operators extend the existing LWP table grammar."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from random import Random
import re
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run

ROOT = Path(__file__).resolve().parents[1]
HEADER = '| A | B | C |\n| --- | --- | --- |\n'


class TableMarkup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tables, self.table, self.row, self.cell = [], None, None, None
        self.group = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table' and attrs.get('class') == 'comparison-table':
            self.table = []
            self.tables.append(self.table)
        elif self.table is not None:
            if tag in ('thead', 'tbody'):
                self.group = tag
            elif tag == 'tr':
                self.row = {'group': self.group, 'cells': []}
                self.table.append(self.row)
            elif tag in ('th', 'td') and self.row is not None:
                self.cell = {'tag': tag, 'text': '', 'colspan': int(attrs.get('colspan', 1)),
                             'rowspan': int(attrs.get('rowspan', 1)), 'attrs': attrs}
                self.row['cells'].append(self.cell)

    def handle_endtag(self, tag):
        if tag in ('th', 'td'):
            self.cell = None
        elif tag == 'tr':
            self.row = None
        elif tag == 'table':
            self.table = self.row = self.cell = None
        elif tag in ('thead', 'tbody'):
            self.group = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['text'] += data


class TableSpansCli(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='table-spans-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.number = 0

    def series(self, body, full=False):
        self.number += 1
        root = self.root / str(self.number)
        (root / 'sources').mkdir(parents=True)
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
        source = '<!-- lwp:meta -->\npage_title: Table spans\n---\n\n'
        if full:
            source += '<!-- lwp:slide:full-article -->\nslug: table\narticle: text.md\n'
            (root / 'sources/text.md').write_text('# Long form\n\n' + body, encoding='utf-8')
        else:
            source += '<!-- lwp:slide -->\nslug: table\n## Table spans\nfact-label: Grid\n\n' + body
        (root / 'sources/a.md').write_text(source, encoding='utf-8')
        env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
               'LWP_THEMES_DIR': str(root / 'themes'), 'LWP_COMMONS_DIR': str(root / 'commons'),
               'LWP_IDENTITY_KITS_DIR': str(root / 'kits')}
        return root, env

    def render(self, body, combined=False, full=False):
        root, env = self.series(body, full)
        options = ('--single-html', 'series.html') if combined else ()
        for command in ('build', 'verify'):
            result = run(command, root, '--lang', 'en', *options, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        html = (root / 'public' / ('series.html' if combined else 'a.html')).read_text(encoding='utf-8')
        if combined:
            payload = re.search(r'<script id="lwp-series-data" type="application/json">(.*?)</script>', html, re.S)
            self.assertIsNotNone(payload)
            html = next(view['content'] for view in json.loads(payload[1])['views'] if view['key'] == 'a.html')
        return html, TableMarkup(html).tables

    @staticmethod
    def cells(table, group='tbody'):
        return [[(cell['text'], cell['colspan'], cell['rowspan']) for cell in row['cells']]
                for row in table if row['group'] == group]

    def test_horizontal_spans_do_not_consume_spaced_empty_cells(self):
        html, tables = self.render(HEADER + '| Merge || Tail |\n| Left | | Right |\n| Last |||\n|| Middle | End |')
        self.assertEqual(self.cells(tables[0]), [
            [('Merge', 2, 1), ('Tail', 1, 1)],
            [('Left', 1, 1), ('', 1, 1), ('Right', 1, 1)],
            [('Last', 3, 1)], [('', 1, 1), ('Middle', 1, 1), ('End', 1, 1)]])
        self.assertNotIn('colspan="1"', html)
        self.assertNotIn('rowspan="1"', html)

    def test_merged_partial_and_empty_headers_keep_their_existing_roles(self):
        _, tables = self.render('| Group || Final |\n|---|---|---|\n| A | B | C |')
        self.assertEqual(self.cells(tables[0], 'thead'), [[('Group', 2, 1), ('Final', 1, 1)]])
        _, tables = self.render('| | | |\n|---|---|---|\n| All |||')
        self.assertEqual(self.cells(tables[0], 'thead'), [])
        self.assertEqual(self.cells(tables[0]), [[('All', 3, 1)]])
        _, tables = self.render('| A | | C |\n|---|---|---|\n| All |||')
        self.assertEqual(len(self.cells(tables[0], 'thead')[0]), 3)

    def test_vertical_chains_render_the_original_content_once(self):
        _, tables = self.render('| A | B |\n|---|---|\n| Group | b1 |\n| ::: | b2 |\n| ::: | b3 |\n| Other | b4 |')
        self.assertEqual(self.cells(tables[0]), [
            [('Group', 1, 3), ('b1', 1, 1)], [('b2', 1, 1)], [('b3', 1, 1)],
            [('Other', 1, 1), ('b4', 1, 1)]])

    def test_combined_rectangles_accept_compact_and_repeated_continuations(self):
        _, tables = self.render(HEADER + '| Group || X |\n| ::: || ::: |\n| ::: | ::: | Z |')
        self.assertEqual(self.cells(tables[0]), [
            [('Group', 2, 3), ('X', 1, 2)], [], [('Z', 1, 1)]])

    def test_literal_operators_use_existing_inline_code_and_punctuation_escapes(self):
        html, tables = self.render('| A | B |\n|---|---|\n'
                                   '| `:::` | A\\|\\|B |\n| \\:\\:\\: | C |\n| prefix::: | D |')
        self.assertEqual(self.cells(tables[0]), [
            [(':::', 1, 1), ('A||B', 1, 1)], [(':::', 1, 1), ('C', 1, 1)],
            [('prefix:::', 1, 1), ('D', 1, 1)]])
        self.assertIn('<code>:::</code>', html)

    def test_nonmerged_ragged_tables_code_and_raw_html_are_unchanged(self):
        raw = '<table><tbody><tr><td colspan="2">Raw</td></tr></tbody></table>'
        source = ('```\n' + HEADER + '| A || B |\n```\n\n' + raw
                  + '\n\n^ Not a DokuWiki header ^\n\n'
                  '| A | B |\n|:---|---:|\n| Short |\n| Many | Cells | Stay |')
        html, tables = self.render(source)
        self.assertEqual(len(tables), 1)
        self.assertEqual(self.cells(tables[0]), [[('Short', 1, 1)],
                                               [('Many', 1, 1), ('Cells', 1, 1), ('Stay', 1, 1)]])
        self.assertIn(raw, html)
        self.assertNotIn('text-align:', html.split('<table class="comparison-table">')[1].split('</table>')[0])
        html, tables = self.render('| Group || C |\n|:---|---:|:---:|\n| Data || D |')
        self.assertEqual(self.cells(tables[0]), [[('Data', 2, 1), ('D', 1, 1)]])
        self.assertNotIn('text-align:', html.split('<table class="comparison-table">')[1].split('</table>')[0])

    def test_inline_content_and_full_articles_work_in_both_output_topologies(self):
        for combined in (False, True):
            for full in (False, True):
                with self.subTest(combined=combined, full_article=full):
                    html, tables = self.render('| A | B |\n|---|---|\n| **Bold** ||\n| ::: ||', combined, full)
                    self.assertEqual(self.cells(tables[0]), [[('Bold', 2, 2)], []])
                    self.assertIn('<strong>Bold</strong>', html)

    def test_invalid_merges_fail_before_replacing_publication_or_caches(self):
        invalid = (
            HEADER + '| ::: | B | C |',
            '| ::: | B |\n|---|---|\n| A | B |',
            '| Group ||\n|---|---|\n| ::: ||',
            HEADER + '| Group || X |\n| ::: | Replacement | Y |',
            HEADER + '| A | B | X |\n| ::: || Y |',
            HEADER + '| Group || X |\n| Replacement | ::: | Y |',
            HEADER + '| Too short ||',
            '| Too | Wide | Header |\n|---|---|\n| Data ||',
            '| A | B |\n|---||\n| Data ||',
        )
        for index, source in enumerate(invalid):
            with self.subTest(case=index):
                root, env = self.series(HEADER + '| A | B | C |')
                result = run('build', root, env=env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                (root / 'public/manual.txt').write_text('Keep', encoding='utf-8')
                path = root / 'sources/a.md'
                path.write_text(path.read_text().split('Grid\n\n')[0] + 'Grid\n\n' + source, encoding='utf-8')
                before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
                for command, options in (('build', ()), ('verify', ()), ('build', ('--incremental', 'a.md'))):
                    result = run(command, root, *options, env=env)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertIn('table', result.stderr.lower())
                    self.assertIn('a.md', result.stderr)
                    self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}, before)

    def test_colspan_beyond_the_native_html_limit_is_refused(self):
        count = 1001
        source = ('|' + '|'.join(['H'] * count) + '|\n|'
                  + '|'.join(['---'] * count) + '|\n| Wide ' + '|' * count)
        root, env = self.series(source)
        result = run('build', root, env=env)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('colspan', result.stderr)
        self.assertIn('1000', result.stderr)
        self.assertFalse((root / 'public').exists())

    def test_audit_reports_invalid_merges_without_writing_and_keeps_strict_optional(self):
        root, env = self.series(HEADER + '| Group || X |\n| ::: | Incomplete | Y |')
        before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        for options, code in [((), 0), (('--strict',), 1)]:
            result = run('audit', root, *options, env=env)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            self.assertIn('a.md', result.stdout + result.stderr)
            self.assertIn('table', (result.stdout + result.stderr).lower())
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual({p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}, before)

    def test_markdown_image_spans_resize_zoom_fullscreen_and_restore_after_print(self):
        images = ('| ![Wide](img/wide.svg) {width=100%; height=auto} || '
                  '![Portrait](img/portrait.svg) {width=100%; height=auto} |\n'
                  '| ::: || ::: |\n| Landscape || Portrait |')
        root, env = self.series('| | | |\n|---|---|---|\n' + images)
        source = root / 'sources/a.md'
        text = source.read_text(encoding='utf-8').replace('slug: table', 'slug: auto')
        text += ('\n---\n\n<!-- lwp:slide -->\nslug: fixed\n## Fixed-layout spans\n'
                 'fact-label: Grid\n\n| Pictures || Portrait |\n|---|---|---|\n' + images)
        source.write_text(text, encoding='utf-8')
        (root / 'sources/img').mkdir()
        for name, width, height in [('wide', 2400, 900), ('portrait', 900, 1600)]:
            (root / 'sources/img' / (name + '.svg')).write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
                f'<rect width="{width}" height="{height}"/></svg>', encoding='utf-8')
        (root / 'templates').mkdir()
        (root / 'templates/custom.css').write_text(
            '#fixed .comparison-table {width:100%;table-layout:fixed}', encoding='utf-8')
        data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
        data['series_meta'] = {'scroll_duration': 0}
        (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        for output, options in [('public', ()), ('combined', ('--single-html', 'series.html'))]:
            for command in ('build', 'verify'):
                result = run(command, root, '--output', root / output, '--lang', 'en',
                             *options, env=env, cwd=ROOT)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        try:
            browser = subprocess.run(
                ['node', str(ROOT / 'tests/table_spans_e2e.cjs'),
                 (root / 'public/a.html').as_uri(), (root / 'combined/series.html').as_uri()],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        except FileNotFoundError:
            self.skipTest('Node unavailable in supplied environment')
        if browser.returncode == 77:
            self.skipTest(browser.stderr.strip())
        self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
        for name in ('chromium', 'firefox'):
            self.assertIn(name + ': Markdown table spans passed', browser.stdout)


class TableSpanGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def compile(self, source):
        header, separator, *body = source.splitlines()
        return self.lwp._compile_markdown_table(header, separator, body)

    def test_audit_candidates_are_the_same_resolved_grid_as_the_converter(self):
        candidates = []
        html = self.lwp.convert_markdown(HEADER + '| Group || X |\n| ::: || Y |\n| ::: | ::: | Z |', table_candidates=candidates)
        table = candidates[0]
        self.assertEqual(table.columns, 3)
        self.assertTrue(table.has_header)
        self.assertEqual([(cell.text, cell.column, cell.colspan, cell.rowspan) for cell in table.rows[1]],
                         [('Group', 0, 2, 3), ('X', 2, 1, 1)])
        self.assertEqual([cell.text for cell in table.rows[2]], ['Y'])
        self.assertIn('<td colspan="2" rowspan="3">Group</td>', html)

    def test_independent_rectangular_tilings_match_compact_and_repeated_source(self):
        rng = Random(71)
        for sample in range(50):
            height, width = rng.randrange(1, 6), rng.randrange(1, 6)
            grid = [[None] * width for _ in range(height)]
            expected = []
            for row in range(height):
                for col in range(width):
                    if grid[row][col] is not None:
                        continue
                    choices = [(h, w) for h in range(1, height - row + 1)
                               for w in range(1, width - col + 1)
                               if all(grid[r][c] is None for r in range(row, row + h)
                                      for c in range(col, col + w))]
                    h, w = rng.choice(choices)
                    owner = ('Cell' + str(len(expected)), row, col, h, w)
                    expected.append(owner)
                    for r in range(row, row + h):
                        for c in range(col, col + w):
                            grid[r][c] = owner
            for compact in (False, True):
                body = []
                for row in range(height):
                    fields = []
                    for col in range(width):
                        label, r, c, h, w = grid[row][col]
                        fields.append(label if r == row and c == col else
                                      ('' if r == row or (compact and c != col) else ':::'))
                    body.append('|' + '|'.join(fields) + '|')
                table = self.lwp._compile_markdown_table(
                    '|' + '|'.join(['H'] * width) + '|', '|' + '|'.join(['---'] * width) + '|', body)
                actual = [(cell.text, row - 1, cell.column, cell.rowspan, cell.colspan)
                          for row, cells in enumerate(table.rows) if row for cell in cells]
                self.assertEqual(actual, expected, (sample, compact, body))

    def test_colspan_estimates_charge_one_cell_not_every_covered_column(self):
        resolved = self.lwp.resolve_theme_properties({
            'table.size': '200px', 'table.head.size': '200px', 'table.head.tracking': '0px'})
        merged = self.compile('| LongHeading |||\n|---|---|---|\n| MuchLongerBody |||')
        single = self.compile('| LongHeading |\n|---|\n| MuchLongerBody |')
        self.assertEqual(self.lwp.estimate_table_widths(merged, resolved),
                         self.lwp.estimate_table_widths(single, resolved))
        self.assertEqual(len(self.lwp.estimate_table_widths(merged, resolved)), 4)

    def test_overlapping_width_constraints_do_not_depend_on_row_order(self):
        resolved = self.lwp.resolve_theme_properties({
            'table.size': '200px', 'table.head.size': '200px', 'table.head.tracking': '0px'})
        a, b = '| SameLongCell || |', '| | SameLongCell ||'
        prefix = '| | | |\n|---|---|---|\n'
        first = self.compile(prefix + a + '\n' + b)
        second = self.compile(prefix + b + '\n' + a)
        findings = self.lwp.estimate_table_widths(first, resolved)
        self.assertEqual(findings, self.lwp.estimate_table_widths(second, resolved))
        # With outer columns each >=32px, the shared middle column satisfies
        # both 1,232px spans at once: 32 + 1,200 + 32, not two padded copies.
        self.assertEqual([(finding[0], finding[3]) for finding in findings],
                         [(name, 1264.0) for name in ('landscape', 'portrait', '16:9')])

    def test_rowspan_limits_match_native_html_without_serializing_huge_output(self):
        table = self.lwp._compile_markdown_table('| H |', '|---|', ['| Value |'] + ['| ::: |'] * 65533)
        self.assertEqual(table.rows[1][0].rowspan, 65534)
        with self.assertRaisesRegex(self.lwp.PropertyError, 'rowspan.*65534'):
            self.lwp._compile_markdown_table('| H |', '|---|', ['| Value |'] + ['| ::: |'] * 65534)

    def test_escaped_pipes_keep_cell_boundaries_and_literal_backslashes(self):
        table = self.compile('| A | B |\n|---|---|\n| Trailing\\| | Last\\|\n| Slash\\\\| End |')
        self.assertEqual([[cell.text for cell in row] for row in table.rows[1:]],
                         [['Trailing\\|', 'Last\\|'], ['Slash\\\\', 'End']])
        self.assertEqual([[cell.column for cell in row] for row in table.rows[1:]], [[0, 1], [0, 1]])
