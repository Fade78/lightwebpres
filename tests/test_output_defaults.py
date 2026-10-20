"""Automatic series contents/navigation and explicit output-policy overrides."""

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'work/tmp'


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sections = []
        self.links = []
        self.body = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'body':
            self.body = attrs
        if tag == 'section' and 'slide' in attrs.get('class', '').split():
            self.sections.append(attrs)
        if tag == 'a':
            self.links.append(attrs)


class OutputDefaults(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=SCRATCH, prefix='output-defaults-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'public'
        (self.root / 'sources').mkdir()
        self.env = {'TMPDIR': str(SCRATCH),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'unused-kits'),
                    'LWP_THEMES_DIR': str(self.root / 'unused-themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'unused-commons')}
        self.data = {'series_meta': {'title': 'A collection', 'scroll_duration': 0},
                     'articles': [{'page_source': 'a.md'}]}
        for name in ('a', 'b'):
            (self.root / 'sources' / (name + '.md')).write_text(
                '<!-- lwp:meta -->\npage_title: Unit ' + name + '\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: intro\n# Unit ' + name + '\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: collection\ntags: nav-only\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: detail\n## Detail ' + name + '\n\nBody.\n\n---\n\n'
                '<!-- lwp:slide:unit-index -->\nslug: contents\n', encoding='utf-8')
        self.save()

    def save(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')

    def cli(self, command, *options, success=True):
        result = run(command, str(self.root), '--lang', 'en', *options,
                     env=self.env, cwd=ROOT)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def build(self, *options):
        self.save()
        result = self.cli('build', *options)
        verify_options = list(options)
        if '--incremental' in verify_options:
            position = verify_options.index('--incremental')
            del verify_options[position:position + 2]
        self.cli('verify', *verify_options)
        return result

    def page(self, name='a.html'):
        return (self.output / name).read_text(encoding='utf-8')

    def snapshot(self):
        return {str(path.relative_to(self.root)): (path.stat().st_mtime_ns, path.read_bytes())
                for path in self.root.rglob('*') if path.is_file()}

    def test_one_unit_omits_contents_and_the_whole_nav_slide(self):
        self.build('--slides-page-numbers', 'on')
        self.assertFalse((self.output / 'index.html').exists())
        html = self.page()
        markup = Markup(html)
        self.assertEqual([section['id'] for section in markup.sections],
                         ['intro', 'detail', 'contents'])
        self.assertNotIn('href="#collection"', html)
        self.assertNotIn('nav-only', markup.body['data-lwp-series-tags'])
        self.assertNotIn('collection', markup.body['data-lwp-tag-preview'])
        self.assertEqual(markup.body['data-lwp-series-home'], 'a.html')
        self.assertIn('data-lwp-i18n="menu_series_start"', html)
        self.assertIn('slide-unit-index', html)
        self.assertEqual(re.findall(r'<span class="slide-num">([^<]+)</span>', html),
                         ['01 / 03', '02 / 03', '03 / 03'])
        self.assertEqual(json.loads((self.output / '.lwp-manifest.json').read_text())['files'],
                         ['a.html'])

    def test_multiple_units_keep_index_and_navigation(self):
        self.data['articles'].append({'page_source': 'b.md'})
        self.build()
        self.assertTrue((self.output / 'index.html').is_file())
        markup = Markup(self.page())
        self.assertIn('collection', [section['id'] for section in markup.sections])
        self.assertTrue(any(link.get('href') == 'b.html' for link in markup.links))
        self.assertTrue(any(link.get('href') == 'index.html' for link in markup.links))
        self.assertEqual(markup.body['data-lwp-series-home'], 'index.html')

    def test_tag_report_keeps_source_inventory_but_counts_actual_default_output(self):
        for enabled in (False, True):
            self.data['build'] = {'nav': enabled}
            self.save()
            result = run('series', 'tags', str(self.root), '--format', 'json', env=self.env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['totals']['slides']['non_excluded'], 4)
            nav = next(tag for tag in report['tags'] if tag['tag'] == 'nav-only')
            self.assertEqual(nav['slides'], 4, 'source shared/default slides stay in inventory')
            self.assertEqual(nav['output']['slides'], 4 if enabled else 3)

    def test_cli_switches_are_independent_and_override_json(self):
        for index, nav in ((True, False), (False, True), (True, True), (False, False)):
            with self.subTest(index=index, nav=nav):
                self.data['build'] = {'index': not index, 'nav': not nav}
                directory = self.root / ('combination-%s-%s' % (index, nav))
                options = ('--output', str(directory),
                           '--make-index' if index else '--no-index',
                           '--make-nav' if nav else '--no-nav')
                self.build(*options)
                self.assertEqual((directory / 'index.html').exists(), index)
                html = (directory / 'a.html').read_text(encoding='utf-8')
                markup = Markup(html)
                self.assertEqual(any(section['id'] == 'collection'
                                     for section in markup.sections), nav)
                self.assertEqual(any(link.get('href') == 'index.html'
                                     for link in markup.links), index and nav)

    def test_json_booleans_force_both_directions(self):
        for count, enabled in ((1, True), (2, False)):
            with self.subTest(count=count, enabled=enabled):
                self.data['articles'] = [{'page_source': name + '.md'}
                                         for name in ('a', 'b')[:count]]
                self.data['build'] = {'index': enabled, 'nav': enabled}
                directory = self.root / ('json-' + str(count))
                self.build('--output', str(directory))
                self.assertEqual((directory / 'index.html').exists(), enabled)
                markup = Markup((directory / 'a.html').read_text(encoding='utf-8'))
                self.assertEqual(any(section['id'] == 'collection'
                                     for section in markup.sections), enabled)

    def test_opposite_switches_refuse_in_both_orders_before_any_writes(self):
        before = self.snapshot()
        for command in ('build', 'verify', 'watch'):
            for positive, negative in (('--make-index', '--no-index'),
                                       ('--make-nav', '--no-nav')):
                for options in ((positive, negative), (negative, positive)):
                    with self.subTest(command=command, options=options):
                        result = self.cli(command, *options, success=False)
                        self.assertIn(positive, result.stderr)
                        self.assertIn(negative, result.stderr)
                        self.assertEqual(self.snapshot(), before)

    def test_only_json_booleans_are_accepted_even_when_cli_overrides(self):
        for key in ('index', 'nav'):
            for value in (None, 0, 1, 'true', 'auto', [], {}):
                self.data['build'] = {key: value}
                self.save()
                before = self.snapshot()
                with self.subTest(key=key, value=value):
                    result = self.cli('build', '--make-' + key, success=False)
                    self.assertIn('build.' + key, result.stderr)
                    self.assertIn('boolean', result.stderr)
                    self.assertEqual(self.snapshot(), before)

    def test_count_uses_effective_status_and_draft_flags(self):
        for status in ('draft', 'ignored'):
            self.data['articles'] = [{'page_source': 'a.md'},
                                     {'page_source': 'b.md', 'status': status}]
            self.build('--output', str(self.root / status))
            self.assertFalse((self.root / status / 'index.html').exists())
        self.data['articles'][1]['status'] = 'draft'
        self.build('--include-drafts')
        self.assertTrue((self.output / 'index.html').is_file())
        self.assertTrue((self.output / 'b.html').is_file())
        self.data['articles'][1].pop('status')
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace('page_title:', 'status: draft\npage_title:'))
        self.build('--output', str(self.root / 'meta-draft'))
        self.assertFalse((self.root / 'meta-draft/index.html').exists())
        self.data['articles'][1]['status'] = 'active'
        self.build('--output', str(self.root / 'json-active'))
        self.assertTrue((self.root / 'json-active/index.html').is_file())

    def test_drafts_only_keeps_its_navigation_universe(self):
        self.data['articles'].append({'page_source': 'b.md', 'status': 'draft'})
        self.save()
        self.cli('build', '--drafts-only')
        self.assertTrue((self.output / 'index.html').is_file())
        self.assertFalse((self.output / 'a.html').exists())
        self.assertIn('collection', [section['id'] for section in Markup(self.page('b.html')).sections])
        lwp = load_lightwebpres_module()
        with mock.patch.dict(os.environ, self.env), mock.patch('webbrowser.open') as opened:
            self.assertEqual(lwp.cmd_build(str(self.root),
                             {'--drafts-only': True, '--no-index': True, '--open': True}), 'b.html')
        opened.assert_called_once_with((self.output / 'b.html').as_uri())

    def test_empty_collection_keeps_an_empty_index_unless_explicitly_disabled(self):
        self.data['articles'] = []
        self.build()
        self.assertTrue((self.output / 'index.html').is_file())
        directory = self.root / 'empty-no-index'
        self.build('--output', str(directory), '--no-index')
        self.assertEqual(list(directory.glob('*.html')), [])

    def test_make_nav_never_inserts_a_slide_absent_from_sources(self):
        source = self.root / 'sources/a.md'
        source.write_text(re.sub(r'<!-- lwp:slide:series-nav -->.*?---\n\n', '',
                                 source.read_text(), flags=re.S))
        self.build('--make-nav')
        self.assertNotIn('collection', [section['id'] for section in Markup(self.page()).sections])

    def test_suppressed_nav_still_reserves_and_validates_source_slugs(self):
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text().replace('slug: collection', 'slug: intro'))
        before = self.snapshot()
        self.cli('build', success=False)
        self.assertEqual(self.snapshot(), before)

    def test_disabled_navigation_has_no_selected_graphic_plan_or_payload(self):
        self.data['resources'] = {
            'assets': [{'id': 'badge', 'kind': 'html', 'format': 'plain',
                        'content': 'NAVIGATION-ONLY'}],
            'layers': [{'id': 'nav-decoration', 'selector': 'type:series-nav',
                        'elements': [{'id': 'badge', 'asset': 'badge',
                                      'place': {'target': {'ref': 'slide', 'anchor': 'top-right'},
                                                'self_anchor': 'top-right'}}]}]}
        self.build()
        self.assertNotIn('class="lwp-graphic-assets"', self.page())
        self.assertNotIn('data-lwp-graphics=', self.page())
        self.build('--make-nav')
        self.assertIn('class="lwp-graphic-assets"', self.page())
        self.assertIn('NAVIGATION-ONLY', self.page())

    def test_help_and_completion_expose_inverse_switches_on_all_three_commands(self):
        for command in ('build', 'verify', 'watch'):
            result = run(command, '--help')
            self.assertEqual(result.returncode, 0, result.stderr)
            for flag in ('--make-index', '--no-index', '--make-nav', '--no-nav'):
                self.assertIn(flag, result.stdout)
        for shell in ('bash', 'zsh'):
            result = run('completion', '--shell', shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--make-index', result.stdout)
            self.assertIn('--make-nav', result.stdout)

    def test_forced_index_cannot_silently_yield_to_an_article(self):
        for filename in ('index.html', 'Index.html'):
            self.data['articles'][0]['page_dest'] = filename
            for settings, flags in (({}, ('--make-index',)), ({'index': True}, ())):
                self.data['build'] = settings
                self.save()
                before = self.snapshot()
                for command in ('build', 'verify', 'watch'):
                    with self.subTest(filename=filename, command=command, settings=settings):
                        result = self.cli(command, *flags, success=False)
                        self.assertIn('collides with the series index', result.stderr)
                        self.assertEqual(self.snapshot(), before)

    def test_single_article_home_preserves_exact_destination_and_encoding(self):
        lwp = load_lightwebpres_module()
        for filename, href in (('Index.html', 'Index.html'),
                               ('unit #%.html', 'unit%20%23%25.html')):
            self.data['articles'][0]['page_dest'] = filename
            self.save()
            with mock.patch.dict(os.environ, self.env), mock.patch('webbrowser.open') as opened:
                self.assertEqual(lwp.cmd_build(str(self.root), {'--open': True}), filename)
            opened.assert_called_once_with((self.output / filename).as_uri())
            self.assertEqual(Markup(self.page(filename)).body['data-lwp-series-home'], href)

    def test_combined_default_counts_logical_units_not_physical_files(self):
        for count in (1, 2):
            self.data['articles'] = [{'page_source': name + '.md'} for name in ('a', 'b')[:count]]
            directory = self.root / ('combined-' + str(count))
            self.build('--output', str(directory), '--single-html', 'combined.html')
            html = (directory / 'combined.html').read_text(encoding='utf-8')
            payload = json.loads(re.search(r'<script id="lwp-series-data"[^>]*>(.*?)</script>',
                                          html, re.S)[1])
            self.assertEqual(len(payload['views']), count + (count > 1))
            if count == 1:
                self.assertEqual(payload['home'], 'a.html')
                self.assertNotIn('id="collection"', html)
            else:
                self.assertNotIn('home', payload)
            self.assertEqual(len(list(directory.glob('*.html'))), 1)

    def test_incremental_invalidates_other_pages_when_index_policy_changes(self):
        self.data['articles'].append({'page_source': 'b.md'})
        self.build()
        for flag in ('--no-index', '--make-index'):
            result = self.build(flag, '--incremental', 'a.md')
            self.assertNotIn('Incremental build:', result.stdout)
            markup = Markup(self.page('b.html'))
            self.assertEqual(any(link.get('href') == 'index.html' for link in markup.links),
                             flag == '--make-index')

    def test_watch_recomputes_auto_and_json_options_without_mutating_caller(self):
        lwp = load_lightwebpres_module()
        options = {'--lang': 'en', '--open': True}
        def changes(*args, **kwargs):
            self.data['articles'].append({'page_source': 'b.md'})
            self.save()
            yield [self.root / 'series.json']
            self.assertTrue((self.output / 'index.html').is_file())
            self.assertIn('collection', [s['id'] for s in Markup(self.page()).sections])
            self.data['build'] = {'index': False, 'nav': False}
            self.save()
            yield [self.root / 'series.json']
            self.assertNotIn('collection', [s['id'] for s in Markup(self.page()).sections])
            manifest = json.loads((self.output / '.lwp-manifest.json').read_text())
            self.assertNotIn('index.html', manifest['files'])
            raise KeyboardInterrupt
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(lwp, '_cmd_watch_poll', changes), \
                mock.patch('webbrowser.open') as opened:
            self.assertEqual(lwp.cmd_watch(str(self.root), options), 0)
        self.assertEqual(options, {'--lang': 'en', '--open': True})
        opened.assert_called_once_with((self.output / 'a.html').as_uri())

    def test_watch_serves_the_actual_single_article_entry(self):
        lwp = load_lightwebpres_module()
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(lwp, '_cmd_watch_poll', side_effect=KeyboardInterrupt), \
                mock.patch('http.server.HTTPServer') as server, \
                mock.patch('webbrowser.open') as opened:
            server.return_value.serve_forever = mock.Mock()
            self.assertEqual(lwp.cmd_watch(str(self.root),
                             {'--serve': True, '--open': True, '--port': '8123'}), 0)
        opened.assert_called_once_with('http://127.0.0.1:8123/a.html')

    def test_empty_no_index_watch_does_not_invent_an_index_url(self):
        self.data['articles'] = []
        self.data['build'] = {'index': False}
        self.save()
        lwp = load_lightwebpres_module()
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(lwp, '_cmd_watch_poll', side_effect=KeyboardInterrupt), \
                mock.patch('http.server.HTTPServer') as server, \
                mock.patch('webbrowser.open') as opened:
            server.return_value.serve_forever = mock.Mock()
            self.assertEqual(lwp.cmd_watch(str(self.root),
                             {'--serve': True, '--open': True, '--port': '8123'}), 0)
        opened.assert_called_once_with('http://127.0.0.1:8123/')
        self.assertEqual(list(self.output.glob('*.html')), [])

    def test_old_index_becomes_an_orphan_without_deleting_unowned_files(self):
        self.build('--make-index')
        previous = (self.output / 'index.html').read_bytes()
        (self.output / 'owner.txt').write_text('Not generated')
        self.build()
        manifest = json.loads((self.output / '.lwp-manifest.json').read_text())
        self.assertNotIn('index.html', manifest['files'])
        self.assertIn('index.html', manifest['previous'])
        self.assertEqual((self.output / 'index.html').read_bytes(), previous)
        result = self.cli('clean')
        self.assertIn('index.html', result.stdout)
        self.assertNotIn('owner.txt', result.stdout)
        self.cli('clean', '--force')
        self.assertFalse((self.output / 'index.html').exists())
        self.assertEqual((self.output / 'owner.txt').read_text(), 'Not generated')


class OutputDefaultsBrowser(unittest.TestCase):
    def test_reader_home_sharing_and_omitted_slides_in_both_topologies(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/output_defaults_e2e.cjs')], cwd=ROOT,
            env={**os.environ, 'TMPDIR': str(SCRATCH), 'PYTHON': sys.executable},
            capture_output=True, text=True, timeout=180)
        if result.returncode == 77:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Output defaults browser checks passed', result.stdout)
