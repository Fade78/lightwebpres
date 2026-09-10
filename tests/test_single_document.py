"""Single-document publication contracts exercised through the real CLI."""

import base64
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from urllib.parse import quote

if __package__:
    from . import test_lightwebpres as fixtures
else:
    import test_lightwebpres as fixtures


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'work' / 'tmp'
PAYLOAD = re.compile(r'<script\b[^>]*\bid="lwp-series-data"[^>]*>(.*?)</script>', re.S)


class _Markup(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class SingleDocument(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=SCRATCH, prefix='single-document-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'public'
        self.env = {
            'TMPDIR': str(SCRATCH), 'PYTHONDONTWRITEBYTECODE': '1',
            'LWP_IDENTITY_KITS_DIR': str(self.root / 'unused-kits'),
            'LWP_COMMONS_DIR': str(self.root / 'unused-commons'),
            'LWP_THEMES_DIR': str(self.root / 'unused-themes'),
        }
        (self.root / 'sources' / 'img').mkdir(parents=True)
        (self.root / 'templates').mkdir()
        self.svg = self.root / 'sources' / 'img' / 'mark.svg'
        self.svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12">'
            '<rect width="12" height="12" fill="red"/></svg>', encoding='utf-8')
        self.data = {'series_meta': {'title': 'Bundled series'}, 'articles': []}
        for name in ('a', 'b', 'draft'):
            self.data['articles'].append({
                'page_source': name + '.md', 'page_dest': name + '.html',
                'nav_title': 'Article ' + name, 'nav_desc': 'Description ' + name,
                **({'status': 'draft'} if name == 'draft' else {}),
            })
            (self.root / 'sources' / (name + '.md')).write_text(
                '<!-- lwp:meta -->\npage_title: Article ' + name + '\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: intro\n# Article ' + name + '\n'
                'summary: Unique body ' + name + '.\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: detail\n## Detail\n'
                '![Static mark](img/mark.svg)\n\n'
                '[Local](#intro) [Other](b.html#detail)\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: collection\n', encoding='utf-8')
        self.save_series()

    def save_series(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')

    def cli(self, command, *options, success=True):
        result = fixtures.run(command, str(self.root), '--output', str(self.output),
                              *options, env=self.env, cwd=ROOT)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def bundle(self, *options, filename='series.html'):
        self.cli('build', '--single-html', filename, *options)
        html = (self.output / filename).read_text(encoding='utf-8')
        matches = PAYLOAD.findall(html)
        self.assertEqual(len(matches), 1, 'Exactly one inert series payload is required')
        return html, json.loads(matches[0])

    def snapshot(self):
        return {str(path.relative_to(self.root)): (path.stat().st_mtime_ns, path.read_bytes())
                for path in self.root.rglob('*') if path.is_file()}

    def test_removed_option_is_unknown_without_legacy_handling(self):
        before = self.snapshot()
        result = self.cli('build', '--single-' + 'page', 'old.html', success=False)
        self.assertIn('Unknown option:', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_default_remains_multipage_and_output_remains_a_directory(self):
        self.output = self.root / 'output.html'
        self.cli('build')
        self.assertTrue(self.output.is_dir())
        self.assertEqual({p.name for p in self.output.glob('*.html')},
                         {'index.html', 'a.html', 'b.html'})
        self.assertNotIn('id="lwp-series-data"',
                         (self.output / 'a.html').read_text(encoding='utf-8'))
        self.cli('verify')

    def test_payload_is_inert_and_local_ids_are_not_globally_renamed(self):
        html, payload = self.bundle()
        self.assertEqual(payload['version'], 1)
        self.assertEqual(payload['order'], ['a.html', 'b.html'])
        views = {view['key']: view for view in payload['views']}
        self.assertEqual(len(payload['views']), 3)
        self.assertEqual(set(views), {'', 'a.html', 'b.html'})
        required = {'key', 'title', 'bodyClass', 'articleTags', 'content',
                    'pageCss', 'themePins', 'presentationPins', 'variants'}
        for key, view in views.items():
            self.assertTrue(required <= view.keys(), key)
        elements = _Markup(html).elements
        self.assertEqual(sum(tag == 'div' and attrs.get('id') == 'lwp-series-view'
                             for tag, attrs in elements), 1)
        self.assertEqual(sum(attrs.get('id') == 'lwp-presentation-index'
                             for _, attrs in elements), 1)
        self.assertFalse(any(tag == 'section' and 'slide' in attrs.get('class', '').split()
                             for tag, attrs in elements))
        self.assertFalse(any(attrs.get('id') in ('intro', 'detail') for _, attrs in elements))
        self.assertTrue(any(tag == 'script' and attrs.get('id') == 'lwp-series-data'
                            and attrs.get('type') == 'application/json' for tag, attrs in elements))
        scripts = [attrs for tag, attrs in elements
                   if tag == 'script' and attrs.get('type') != 'application/json']
        self.assertEqual(len(scripts), 1, 'The mounted document owns one shared runtime')
        self.assertNotIn('src', scripts[0])
        for key in payload['order']:
            ids = [attrs.get('id') for _, attrs in _Markup(views[key]['content']).elements]
            self.assertEqual(ids.count('intro'), 1)
            self.assertEqual(ids.count('detail'), 1)
        self.assertEqual({p.name for p in self.output.glob('*.html')}, {'series.html'})
        self.cli('verify', '--single-html', 'series.html')

    def test_invalid_filename_and_unsupported_combinations_refuse_before_writes(self):
        invalid = [('--single-html', name) for name in
                    ('', '../escape.html', 'nested/file.html', 'nested\\file.htm',
                     str(self.root / 'absolute.html'), 'series.txt', 'series.html#intro',
                     'series.html?x=1')]
        invalid += [('--single-html', 'series.html', flag)
                    for flag in ('--no-index', '--drafts-only')]
        before = self.snapshot()
        for command in ('build', 'verify', 'watch'):
            for options in invalid:
                with self.subTest(command=command, options=options):
                    result = self.cli(command, *options, success=False)
                    self.assertIn('--single-html', result.stderr)
                    self.assertNotIn('Unknown option', result.stderr)
                    self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.output.exists())

    def test_omitted_filename_uses_the_series_title_with_build_verify_parity(self):
        self.data['series_meta']['title'] = '<b>\u00c9nergie</b> & Soci\u00e9t\u00e9 / 2026'
        self.save_series()
        self.cli('build', '--single-html', '--inline-images')
        filename = 'energie-societe-2026.html'
        self.assertTrue((self.output / filename).is_file())
        self.assertIn(filename + '#lwp/a/a.html', (self.root / 'README.md').read_text())
        manifest = json.loads((self.output / '.lwp-manifest.json').read_text())
        self.assertEqual(manifest['files'], [filename])
        self.cli('verify', '--single-html', '--inline-images')
        self.bundle('--inline-images', filename='explicit.htm')
        self.cli('verify', '--single-html=explicit.htm', '--inline-images')

    def test_bare_option_does_not_consume_the_series_directory(self):
        for options in (['--single-html', str(self.root)],
                        ['--single-html', '--inline-images', str(self.root)],
                        ['--single-html', '--', str(self.root)]):
            with self.subTest(options=options):
                result = fixtures.run('build', *options, env=self.env, cwd=ROOT)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((self.output / 'bundled-series.html').is_file())
        result = fixtures.run('build', '--single-html', env=self.env, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_derived_name_handles_empty_unicode_reserved_and_long_titles(self):
        lwp = fixtures.load_lightwebpres_module()
        fallback = re.sub(r'[\W_]+', '-', self.root.name).strip('-') + '.html'
        for title, expected in (('', fallback),
                                ('!!!', fallback),
                                ('\u65e5\u672c\u8a9e', '\u65e5\u672c\u8a9e.html'),
                                ('\u65e5' * 500, '\u65e5' * 66 + '.html'),
                                ('CON', 'series-con.html'),
                                ('A' * 500, 'a' * 100 + '.html')):
            with self.subTest(title=title):
                self.data['series_meta']['title'] = title
                self.save_series()
                args = {'--single-html': True}
                ctx = lwp.load_build_context(str(self.root), args)
                self.assertEqual(ctx.args['--single-html'], expected)
                self.assertIs(args['--single-html'], True, 'watch must retain automatic naming')

    def test_watch_opens_the_derived_name_and_recomputes_it_after_a_title_change(self):
        lwp = fixtures.load_lightwebpres_module()
        def changes(*args, **kwargs):
            self.data['series_meta']['title'] = 'Renamed series'
            self.save_series()
            yield [self.root / 'series.json']
            raise KeyboardInterrupt
        with mock.patch.object(lwp, '_cmd_watch_poll', changes), \
                mock.patch('webbrowser.open') as opened:
            self.assertEqual(lwp.cmd_watch(str(self.root), {'--single-html': True, '--open': True}), 0)
        opened.assert_called_once_with((self.output / 'bundled-series.html').as_uri())
        self.assertTrue((self.output / 'renamed-series.html').is_file())
        self.cli('verify', '--single-html')

    def test_include_drafts_no_nav_no_readme_and_htm_filename(self):
        html, payload = self.bundle('--include-drafts', '--no-nav', '--no-readme',
                                    filename='collection.htm')
        self.assertEqual(payload['order'], ['a.html', 'b.html', 'draft.html'])
        self.assertEqual({v['key'] for v in payload['views']},
                         {'', 'a.html', 'b.html', 'draft.html'})
        self.assertTrue(any(attrs.get('id') == 'navMenu' for _, attrs in _Markup(html).elements))
        for view in payload['views'][1:]:
            self.assertNotIn('class="series-item', view['content'])
            self.assertIn('class="series-list"', view['content'])
        self.assertFalse((self.root / 'README.md').exists())
        self.cli('verify', '--single-html', 'collection.htm', '--include-drafts',
                 '--no-nav', '--no-readme')

    def test_only_validates_selection_but_rebuilds_the_entire_bundle(self):
        self.bundle()
        source = self.root / 'sources' / 'b.md'
        source.write_text(source.read_text(encoding='utf-8').replace(
            'Unique body b.', 'Changed unselected article.'), encoding='utf-8')
        _, payload = self.bundle('--only', 'a.md')
        self.assertEqual(payload['order'], ['a.html', 'b.html'])
        self.assertIn('Changed unselected article.',
                      next(v['content'] for v in payload['views'] if v['key'] == 'b.html'))
        self.cli('verify', '--single-html', 'series.html')
        before = self.snapshot()
        for selected in ('missing.html', 'draft.html'):
            with self.subTest(selected=selected):
                self.cli('build', '--single-html', 'series.html', '--only', selected, success=False)
                self.assertEqual(self.snapshot(), before)

    def test_manifest_owns_physical_bundle_and_images_and_clean_removes_old_pages(self):
        self.cli('build')
        old = {name: (self.output / name).read_bytes()
               for name in ('index.html', 'a.html', 'b.html')}
        self.bundle()
        manifest = json.loads((self.output / '.lwp-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(manifest['files']), {'series.html', 'img/mark.svg'})
        self.assertTrue(set(old) <= set(manifest['previous']))
        for name, content in old.items():
            self.assertEqual((self.output / name).read_bytes(), content)
        self.assertEqual((self.output / 'img/mark.svg').read_bytes(), self.svg.read_bytes())
        readme = (self.root / 'README.md').read_text(encoding='utf-8')
        for key in ('a.html', 'b.html'):
            self.assertIn('series.html#lwp/a/' + quote(key, safe=''), readme)
        self.cli('clean', '--force')
        for name in old:
            self.assertFalse((self.output / name).exists())
        self.assertTrue((self.output / 'series.html').is_file())
        self.assertTrue((self.output / 'img/mark.svg').is_file())
        self.cli('verify', '--single-html', 'series.html')

    def test_inline_svg_images_include_alternate_identity_variants(self):
        if __package__:
            from .test_resource_factoring import image_sources, runtime_data
        else:
            from test_resource_factoring import image_sources, runtime_data
        kit = self.root / 'templates' / 'kits' / 'lightwebpres-docs' / '0.1.0'
        shutil.copytree(ROOT / 'examples' / 'kits' / 'lightwebpres-docs' / '0.1.0', kit)
        selector = 'lightwebpres-docs@0.1.0/docs'
        self.data['presentation_presets'] = [selector]
        self.save_series()
        html, payload = self.bundle('--inline-images')
        resources = runtime_data(html)
        view = next(v for v in payload['views'] if v['key'] == 'a.html')
        native_images = image_sources(view['content'], resources)
        self.assertIn('data:image/svg+xml;base64,' + base64.b64encode(
            self.svg.read_bytes()).decode('ascii'), native_images)
        variant = view['variants'][selector]
        variant_text = variant if isinstance(variant, str) else json.dumps(variant)
        variant_images = [src for section in variant['sections'].values()
                          for src in image_sources(section, resources)]
        self.assertTrue(variant_images)
        self.assertTrue(all(src.startswith('data:image/svg+xml;base64,')
                            for src in variant_images))
        self.assertNotIn('assets/presentations/', variant_text)
        manifest = json.loads((self.output / '.lwp-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['files'], ['series.html'])
        self.cli('verify', '--single-html', 'series.html', '--inline-images')
        mark = kit / 'assets' / 'lightwebpres-mark.svg'
        mark.write_text(mark.read_text(encoding='utf-8').replace('</svg>',
                       '<!-- changed alternate SVG -->\n</svg>'), encoding='utf-8')
        result = self.cli('verify', '--single-html', 'series.html', '--inline-images', success=False)
        self.assertIn('series.html', result.stdout + result.stderr)

    def test_verify_detects_article_and_svg_drift_without_writing(self):
        for inline in (False, True):
            options = ('--inline-images',) if inline else ()
            with self.subTest(inline=inline):
                self.bundle(*options)
                source = self.root / 'sources' / 'b.md'
                original = source.read_text(encoding='utf-8')
                source.write_text(original.replace('Unique body b.', 'Content drift.'), encoding='utf-8')
                before = self.snapshot()
                result = self.cli('verify', '--single-html', 'series.html', *options, success=False)
                self.assertIn('series.html', result.stdout + result.stderr)
                self.assertEqual(self.snapshot(), before)
                source.write_text(original, encoding='utf-8')
                svg = self.svg.read_text(encoding='utf-8')
                self.svg.write_text(svg.replace('red', 'blue'), encoding='utf-8')
                before = self.snapshot()
                self.cli('verify', '--single-html', 'series.html', *options, success=False)
                self.assertEqual(self.snapshot(), before)
                self.svg.write_text(svg, encoding='utf-8')

    def test_verify_ignores_stamps_in_json_but_not_article_content(self):
        html, payload = self.bundle('--build-stamp')
        self.assertIn('Compiled at ', json.dumps(payload))
        changed, count = re.subn(r'Compiled at \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                                'Compiled at 2001-01-01 00:00:00', html)
        self.assertGreater(count, 0)
        bundle = self.output / 'series.html'
        bundle.write_text(changed, encoding='utf-8')
        for options in ((), ('--build-stamp',)):
            self.cli('verify', '--single-html', 'series.html', *options)
        self.assertIn('Unique body b.', changed)
        bundle.write_text(changed.replace('Unique body b.', 'Tampered body b.'), encoding='utf-8')
        self.cli('verify', '--single-html', 'series.html', success=False)

    def test_dry_run_and_custom_navigation_refusal_do_not_write(self):
        before = self.snapshot()
        self.cli('build', '--single-html', 'series.html', '--inline-images', '--dry-run')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.output.exists())
        nav = self.root / 'templates' / 'nav.js'
        nav.write_text('// Custom navigation\n', encoding='utf-8')
        before = self.snapshot()
        result = self.cli('build', '--single-html', 'series.html', success=False)
        self.assertIn('nav.js', result.stderr)
        self.assertEqual(self.snapshot(), before)
        nav.write_text(fixtures.load_lightwebpres_module().TEMPLATE_NAV_JS, encoding='utf-8')
        self.bundle()
        before = self.snapshot()
        self.cli('build', '--single-html', 'series.html', '--inline-images', '--dry-run')
        self.assertEqual(self.snapshot(), before)

    def test_index_named_article_and_contents_have_distinct_routes(self):
        self.data['articles'][0]['page_dest'] = 'index.html'
        self.save_series()
        _, payload = self.bundle()
        self.assertEqual(payload['order'], ['index.html', 'b.html'])
        for view in payload['views'][1:]:
            self.assertIn('href="#lwp/index"', view['content'])
        self.cli('verify', '--single-html', 'series.html')

    def test_index_extensions_are_refused_without_changes(self):
        (self.root / 'templates' / 'index_extra.html').write_text('<p>Custom extension</p>', encoding='utf-8')
        before = self.snapshot()
        result = self.cli('build', '--single-html', 'series.html', success=False)
        self.assertIn('index_extra.html', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_watch_builds_and_rebuilds_the_inline_bundle(self):
        env = {**os.environ, **self.env}
        process = subprocess.Popen(
            [sys.executable, '-u', str(ROOT / 'lightwebpres'), 'watch', str(self.root),
             '--output', str(self.output), '--single-html', '--inline-images'],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        observed = False
        try:
            deadline = time.monotonic() + 15
            bundle = self.output / 'bundled-series.html'
            while process.poll() is None and time.monotonic() < deadline:
                if bundle.exists() and PAYLOAD.search(bundle.read_text(encoding='utf-8')):
                    source = self.root / 'sources' / 'b.md'
                    # Let watch finish taking its initial input snapshot.
                    time.sleep(1)
                    source.write_text(source.read_text(encoding='utf-8').replace(
                        'Unique body b.', 'Watch rebuilt article.'), encoding='utf-8')
                    break
                time.sleep(0.1)
            while process.poll() is None and time.monotonic() < deadline:
                if bundle.exists() and 'Watch rebuilt article.' in bundle.read_text(encoding='utf-8'):
                    observed = True
                    break
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
        self.assertTrue(observed, stdout + stderr)
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.cli('verify', '--single-html', '--inline-images')


class SingleDocumentBrowser(unittest.TestCase):
    def test_single_document_runtime(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(SCRATCH), 'PYTHON': sys.executable,
               'PYTHONDONTWRITEBYTECODE': '1'}
        # Resolve the supplied browser before the script isolates XDG_CACHE_HOME.
        try:
            probe = subprocess.run(
                ['node', '-e', "process.stdout.write(require('playwright').chromium.executablePath())"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        except OSError as exc:
            self.skipTest('Browser check blocked: ' + str(exc))
        if probe.returncode:
            self.skipTest('Playwright unavailable in the supplied environment: ' + probe.stderr.strip())
        env.setdefault('PW_CHROMIUM_PATH', probe.stdout.strip())
        check = subprocess.run(['node', str(ROOT / 'tests' / 'single_document_e2e.cjs')],
                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
        if check.returncode == 77:
            self.skipTest(check.stderr.strip())
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn('Single-document runtime:', check.stdout)
