"""Reading policy, lossless table markup and explicitly approximate audit advice."""

import contextlib
import copy
import io
import json
import re
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run, scaffold
else:
    from test_lightwebpres import load_lightwebpres_module, run, scaffold


DEFAULTS = {
    'table_mode': 'clip', 'text_fit': 'fixed',
    'table_shrink': False, 'object_shrink': False,
    'min_text_scale': 0.75, 'min_table_scale': 0.85,
    'min_object_scale': 0.85,
}
ARTICLE = (
    '<!-- lwp:meta -->\npage_dest: a.html\npage_title: Reading\n'
    'nav_title: Reading\nnav_desc: Reading policy.\n---\n\n'
    '<!-- lwp:slide:cover -->\nslug: cover\n# Reading\n'
    'summary: Reading policy.\n\n---\n\n'
    '<!-- lwp:slide -->\nslug: comparison\n## Comparison\n'
    'fact-label: Comparison\n\n{table}\n'
)
NORMAL_TABLE = '| Name | Result |\n| --- | --- |\n| Alpha | Works |'


class ReadingSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_defaults_are_resolved_without_changing_the_author_object(self):
        for meta in ({}, {'reading': {}}, {'reading': {'text_fit': 'uniform'}}):
            with self.subTest(meta=meta):
                data = {'series_meta': copy.deepcopy(meta), 'articles': []}
                before = copy.deepcopy(data)
                loaded = self.lwp.series_meta_of(data)
                resolved = self.lwp.resolve_reading_settings(loaded)
                self.assertEqual(resolved, {**DEFAULTS, **meta.get('reading', {})})
                resolved['table_mode'] = 'scroll'
                self.assertEqual(data, before)
                self.assertEqual(self.lwp.DEFAULT_READING_SETTINGS, DEFAULTS)

    def test_each_enum_and_boundary_is_accepted(self):
        for mode in ('clip', 'overflow', 'scroll'):
            for fit in ('fixed', 'uniform', 'per-slide'):
                reading = {
                    'table_mode': mode, 'text_fit': fit,
                    'table_shrink': True, 'object_shrink': True,
                    'min_text_scale': 0.5, 'min_table_scale': 1,
                    'min_object_scale': 1.0,
                }
                self.assertEqual(self.lwp.resolve_reading_settings(
                    {'reading': reading}), reading)

    def test_invalid_shapes_values_unknown_keys_and_nonfinite_scales_fail(self):
        invalid = [None, False, [], 'scroll', 1, {'unknown': True}]
        for key in ('table_mode', 'text_fit'):
            invalid.extend({key: value} for value in
                           (None, True, 1, [], {}, 'auto', ' FIXED '))
        for key in ('table_shrink', 'object_shrink'):
            invalid.extend({key: value} for value in
                           (None, 0, 1, 'true', 'false', [], {}))
        for key in ('min_text_scale', 'min_table_scale', 'min_object_scale'):
            invalid.extend({key: value} for value in
                           (None, True, False, '0.75', 0.49, 1.01, [], {},
                            float('nan'), float('inf'), -float('inf')))
        for reading in invalid:
            with self.subTest(reading=reading):
                with self.assertRaises(self.lwp.PropertyError):
                    self.lwp.resolve_reading_settings({'reading': reading})

    def test_audit_can_report_bad_settings_and_continue(self):
        errors = []
        with contextlib.redirect_stderr(io.StringIO()):
            meta = self.lwp.series_meta_of(
                {'series_meta': {'reading': {'table_shrink': 1}, 'title': 'T'}},
                tolerate_invalid=True, errors=errors)
        self.assertEqual(len(errors), 1)
        self.assertIn('series_meta.reading.table_shrink', errors[0])
        self.assertEqual(meta['title'], 'T')
        self.assertEqual(self.lwp.resolve_reading_settings(meta), DEFAULTS)

    def test_runtime_json_escapes_script_terminators_and_round_trips(self):
        reading = {**DEFAULTS, 'probe': '</script><script>alert(1)</script>'}
        markup = self.lwp.reading_runtime_markup(reading)
        payload = markup.split('>', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('<', payload)
        self.assertEqual(json.loads(payload), reading)
        self.assertEqual(markup.count('</script>'), 1)


class ReadingCLI(unittest.TestCase):
    def make_series(self, tmp, reading=None, table=NORMAL_TABLE):
        root = scaffold(tmp, ARTICLE.format(table=table))
        if reading is not None:
            data = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            data['series_meta'] = {'reading': reading}
            (root / 'series.json').write_text(json.dumps(data), encoding='utf-8')
        return root

    def test_article_and_index_receive_defaults_and_all_configured_modes(self):
        for reading in (None, {}, {'table_mode': 'overflow'}, {
                'table_mode': 'scroll', 'text_fit': 'per-slide',
                'table_shrink': True, 'object_shrink': True,
                'min_text_scale': 0.6, 'min_table_scale': 0.7,
                'min_object_scale': 0.8}):
            with self.subTest(reading=reading), tempfile.TemporaryDirectory() as tmp:
                root = self.make_series(tmp, reading)
                original = (root / 'series.json').read_bytes()
                result = run('build', str(root))
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in ('a.html', 'index.html'):
                    html = (root / 'public' / name).read_text(encoding='utf-8')
                    expected = {**DEFAULTS, **(reading or {})}
                    payload = re.findall(
                        r'<script id="lwp-reading-data" type="application/json">'
                        r'(.*?)</script>', html, re.S)
                    self.assertEqual(len(payload), 1)
                    self.assertEqual(json.loads(payload[0]), expected)
                    self.assertIn('data-lwp-table-mode="' +
                                  expected['table_mode'] + '"', html)
                self.assertEqual((root / 'series.json').read_bytes(), original)

    def test_bad_reading_is_a_build_error_and_an_audit_finding(self):
        for reading, field in (({'min_text_scale': True}, 'min_text_scale'),
                               ({'min_table_scale': float('inf')}, 'min_table_scale'),
                               ({'table_shrink': 'yes'}, 'table_shrink'),
                               ({'table_mode': 'wide'}, 'table_mode'),
                               ({'text_fit': 'auto'}, 'text_fit'),
                               ({'oops': 1}, 'oops')):
            with self.subTest(reading=reading), tempfile.TemporaryDirectory() as tmp:
                root = self.make_series(tmp, reading)
                result = run('build', str(root))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('series_meta.reading', result.stderr)
                self.assertIn(field, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                result = run('audit', str(root), '--strict')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(field, result.stdout + result.stderr)

    def test_pathological_table_is_lossless_and_warns_for_every_reference_format(self):
        token = 'LongToken' * 100
        table = '| Label | Value |\n| --- | --- |\n| Alpha | ' + token + ' |'
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_series(tmp, table=table)
            result = run('build', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertRegex(html, r'<div class="lwp-table-viewport">\s*'
                                   r'<table class="comparison-table">')
            self.assertIn('<td>' + token + '</td>', html)
            self.assertIn('<thead>', html)
            self.assertIn('<th>Value</th>', html)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = result.stdout + result.stderr
            self.assertIn('a.md: slide 2 (comparison), table 1: ESTIMATE', report)
            for viewport in ('landscape 1024x768', 'portrait 768x1024',
                             '16:9 1280x720', '21:9 1680x720'):
                self.assertIn(viewport, report)
            self.assertIn('not a precise font measurement', report)
            self.assertEqual(run('audit', str(root), '--strict').returncode, 1)

    def test_normal_wrappable_prose_is_not_mistaken_for_one_long_token(self):
        table = NORMAL_TABLE + '\n| Beta | ' + ('short words ' * 100) + ' |'
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_series(tmp, table=table)
            result = run('audit', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('ESTIMATE', result.stdout + result.stderr)

    def test_included_article_tables_are_wrapped_and_located(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_series(tmp)
            (root / 'sources' / 'body.md').write_text(
                NORMAL_TABLE + '\n| Beta | ' + 'W' * 1000 + ' |', encoding='utf-8')
            with (root / 'sources' / 'a.md').open('a', encoding='utf-8') as output:
                output.write('\n---\n\n<!-- lwp:slide:full-article -->\nslug: full\n'
                             'article: body.md\n')
            result = run('build', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (root / 'public' / 'a.html').read_text(encoding='utf-8')
            self.assertEqual(len(re.findall(
                r'<div class="lwp-table-viewport">\s*<table', html)), 2)
            result = run('audit', str(root))
            self.assertIn('slide 3 (full), table 1 (body.md): ESTIMATE',
                          result.stdout + result.stderr)

    def test_audit_uses_series_and_article_table_size_pins(self):
        for where in ('series', 'article'):
            with self.subTest(where=where), tempfile.TemporaryDirectory() as tmp:
                root = self.make_series(tmp)
                if where == 'series':
                    (root / 'templates').mkdir()
                    (root / 'templates' / 'settings.conf').write_text(
                        'table.size: 200px\n', encoding='utf-8')
                else:
                    source = root / 'sources' / 'a.md'
                    source.write_text(source.read_text(encoding='utf-8').replace(
                        'page_title: Reading',
                        'page_title: Reading\nstyle.table.size: 200px'),
                        encoding='utf-8')
                result = run('audit', str(root))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('table 1: ESTIMATE', result.stdout + result.stderr)


class TableEstimates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def test_viewport_lengths_resolve_functions_and_inherited_em(self):
        px = self.lwp.reading_length_px
        self.assertAlmostEqual(px('max(13px, 1.9vmin)', 1024, 768), 14.592)
        self.assertEqual(px('min(84vw, max(1100px, 102vmin))', 1680, 720), 1100)
        self.assertEqual(px('clamp(12px, 2vw, 24px)', 1000, 700), 20)
        self.assertEqual(px('0.8em', 1000, 700, 20), 16)
        self.assertIsNone(px('calc(100vw - 20px)', 1000, 700))

    def test_estimate_uses_resolved_size_pins_and_discloses_fallbacks(self):
        rows = [['Name', 'Value'], ['Alpha', 'MediumLengthToken']]
        normal = self.lwp.resolve_theme_properties()
        self.assertFalse(self.lwp.estimate_table_widths(rows, normal))
        large = self.lwp.resolve_theme_properties({'table.size': '200px'})
        self.assertEqual(len(self.lwp.estimate_table_widths(rows, large)), 4)
        fallback = self.lwp.resolve_theme_properties(
            {'table.size': 'calc(10px + 1vw)'})
        findings = self.lwp.estimate_table_widths([['W' * 1000]], fallback)
        self.assertEqual(len(findings), 4)
        self.assertIn('table.size', findings[0][5])

    def test_converter_collects_only_markdown_tables_not_code_or_raw_html(self):
        candidates = []
        raw = '<table><tr><td>Raw</td></tr></table>'
        html = self.lwp.convert_markdown(
            '```\n' + NORMAL_TABLE + '\n```\n\n' + raw + '\n\n' + NORMAL_TABLE,
            table_candidates=candidates)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], [['Name', 'Result'], ['Alpha', 'Works']])
        self.assertEqual(html.count('<div class="lwp-table-viewport">'), 1)
        self.assertIn(raw, html)

    def test_many_short_columns_warn_from_their_combined_width(self):
        resolved = self.lwp.resolve_theme_properties()
        self.assertEqual(len(self.lwp.estimate_table_widths(
            [['A'] * 60, ['B'] * 60], resolved)), 4)


if __name__ == '__main__':
    unittest.main()
