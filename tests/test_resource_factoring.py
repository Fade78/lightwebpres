"""Per-file inert resources: CLI publication and private serialization contracts."""
import base64
import copy
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

if __package__:
    from . import test_lightwebpres as fixtures
else:
    import test_lightwebpres as fixtures

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'work/tmp'

# The same cases exercise Python's source parser and the real browser hydrator.
OPAQUE_CONTEXTS = [
    (tag, '<' + tag + '>', '</' + tag + '>')
    for tag in ('pre', 'code', 'textarea', 'title', 'xmp', 'picture', 'template',
                'noscript', 'iframe', 'object', 'audio', 'video')
] + [
    ('svg', '<svg><foreignObject>', '</foreignObject></svg>'),
    ('math', '<math><mtext>', '</mtext></math>'),
    ('custom element', '<probe-widget><div>', '</div></probe-widget>'),
    ('customized built-in', '<div is="probe-widget"><div>', '</div></div>'),
    ('nested opaque', '<pre><code><span>', '</span></code></pre>'),
]


def runtime_data(html):
    return {name: json.loads(body) for name, body in re.findall(
        r'<script id="(lwp-(?:resource|series|presentation)-data)" type="application/json">(.*?)</script>',
        html, re.S)}


def image_sources(fragment, data):
    """Inspect actual img elements, resolving the published pool rather than text matches."""
    class Images(HTMLParser):
        def __init__(self):
            super().__init__()
            self.sources = []

        def handle_starttag(self, tag, attrs):
            if tag == 'img':
                attrs = dict(attrs)
                src = attrs.get('src')
                if src is None:
                    src = data['lwp-resource-data']['images'][attrs['data-lwp-image']]
                    src += attrs.get('data-lwp-image-fragment', '')
                self.sources.append(src)
    parser = Images()
    parser.feed(fragment)
    return parser.sources


class ResourceFactoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = fixtures.load_lightwebpres_module()

    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.TemporaryDirectory(prefix='resource-pool-', dir=SCRATCH)
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.env = {**os.environ, 'TMPDIR': str(self.root), 'PYTHONDONTWRITEBYTECODE': '1',
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'unused-kits'),
                    'LWP_COMMONS_DIR': str(self.root / 'unused-commons'),
                    'LWP_THEMES_DIR': str(self.root / 'unused-themes')}
        (self.root / 'sources/img').mkdir(parents=True)
        (self.root / 'templates').mkdir()
        rng = random.Random(20260910)
        pixels = b''.join(b'\0' + bytes(rng.randrange(256) for _ in range(384)) for _ in range(96))
        def chunk(kind, value):
            return struct.pack('!I', len(value)) + kind + value + struct.pack('!I', zlib.crc32(kind + value))
        self.png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 128, 96, 8, 2, 0, 0, 0))
                    + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b''))
        self.uri = 'data:image/png;base64,' + base64.b64encode(self.png).decode()
        for name in ('repeat.png', 'same.png'):
            (self.root / 'sources/img' / name).write_bytes(self.png)
        self.series = {'series_meta': {'title': 'Resource pool'}, 'articles': []}
        for name in ('a', 'b'):
            self.series['articles'].append({'page_source': name + '.md', 'page_dest': name + '.html'})
            text = '<!-- lwp:meta -->\npage_title: Unit ' + name + '\n---\n\n'
            for number in range(3):
                text += ('<!-- lwp:slide -->\nslug: s' + str(number) + '\n## Images\n\n'
                         '![First](img/repeat.png "Caption")\n\n![Second](img/same.png)\n\n---\n\n')
            (self.root / 'sources' / (name + '.md')).write_text(text, encoding='utf-8')
        self.save()

    def save(self):
        (self.root / 'series.json').write_text(json.dumps(self.series), encoding='utf-8')

    def kit(self):
        identity_kit = self.root / 'templates/kits/lightwebpres-docs/0.1.0'
        shutil.copytree(ROOT / 'examples/kits/lightwebpres-docs/0.1.0', identity_kit)
        manifest = json.loads((identity_kit / 'manifest.json').read_text())
        manifest['presets']['compact'] = copy.deepcopy(manifest['presets']['docs'])
        manifest['presets']['compact']['label'] = 'Compact'
        manifest['presets']['compact']['slide_layouts']['cover'] = 'hero'
        (identity_kit / 'manifest.json').write_text(json.dumps(manifest))
        self.series['series_meta']['presentation_preset'] = 'lightwebpres-docs@0.1.0/docs'
        self.series['presentation_presets'] = ['lightwebpres-docs@0.1.0/compact', 'builtin/standard']
        self.save()

    def cli(self, command, output, *options):
        result = fixtures.run(command, str(self.root), '--output', str(output), '--no-readme',
                              '--no-essential-theme', '--lang', 'en', *options, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_cli_topologies_inline_linked_and_primary_images(self):
        self.kit()
        for single in (False, True):
            for inline in (False, True):
                with self.subTest(single=single, inline=inline):
                    output = self.root / ('out-%s-%s' % (single, inline))
                    options = (['--single-html', 'series.html'] if single else []) + (['--inline-images'] if inline else [])
                    self.cli('build', output, *options)
                    paths = list(output.glob('*.html'))
                    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
                    self.cli('verify', output, *options)
                    self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
                    for path in paths:
                        html = path.read_text()
                        data = runtime_data(html)
                        self.lwp._runtime_resource_data(html)
                        if inline and path.name != 'index.html':
                            self.assertEqual(html.count(self.uri), 1 if single else 7)
                            self.assertEqual(len(data['lwp-resource-data']['images']), 2)
                            if not single:
                                # The live primary DOM is not rewritten; it works without JavaScript.
                                self.assertEqual(image_sources(html, data).count(self.uri), 6)
                            else:
                                views = data['lwp-series-data']['views']
                                for view in views[1:]:
                                    self.assertEqual(image_sources(view['content'], data).count(self.uri), 6)
                                    self.assertEqual(len(view['variants']), 3)
                                self.assertEqual(len(data['lwp-resource-data']['css']), 2)
                        if not inline:
                            self.assertEqual((output / 'img/repeat.png').read_bytes(), self.png)
                            self.assertEqual((output / 'img/same.png').read_bytes(), self.png)
                        else:
                            self.assertFalse((output / 'img').exists())
                    self.cli('build', output, *options, '--only', 'a.md')
                    self.cli('verify', output, *options)

    def test_single_image_per_unit_pool_and_independent_builds(self):
        for unit in ('a', 'b'):
            path = self.root / 'sources' / (unit + '.md')
            path.write_text('<!-- lwp:meta -->\npage_title: Unit\n---\n\n'
                            '<!-- lwp:slide -->\nslug: s\n## One\n\n![One](img/repeat.png)\n')
        output = self.root / 'public'
        self.cli('build', output, '--single-html', 'series.html', '--inline-images', '--build-stamp')
        html = (output / 'series.html').read_text()
        self.assertEqual(html.count(self.uri), 1)
        self.cli('verify', output, '--single-html', 'series.html', '--inline-images')
        self.cli('build', output, '--inline-images')
        for unit in ('a', 'b'):
            html = (output / (unit + '.html')).read_text()
            self.assertEqual(html.count(self.uri), 1)
            self.assertNotIn('lwp-resource-data', runtime_data(html))

    def page(self, fragment, css=''):
        data = {'version': 1, 'views': [{'key': 'a.html', 'content': fragment, 'pageCss': css, 'variants': {}}]}
        return ('<p>Primary stays intact</p><script id="lwp-series-data" type="application/json">'
                + json.dumps(data).replace('<', '\\u003c') + '</script>')

    def test_exact_attributes_mime_fragments_and_opaque_text(self):
        uri = 'data:image/svg+xml;base64,' + base64.b64encode(b'<svg>' + b' ' * 600 + b'</svg>').decode()
        other = uri.replace('image/svg+xml', 'image/png')
        image = '<IMG alt="src=not-an-attribute &amp; more" width="21" height="34" title="Title" loading="lazy" src=\'%s\'/>'
        left, right = image % (uri + '#left'), image % (uri + '#right')
        untouched = ('<code>&lt;img src="' + uri + '"&gt;</code><script>var text = \'<img src="' + uri + '">\';</script>'
                     '<img srcset="x 2x" src="' + uri + '"><textarea><img src="' + uri + '"></textarea>'
                     '<probe-widget><img src="' + uri + '"></probe-widget>'
                     '<img src="' + uri + '" onload="window.authored=true"><img src><img>')
        original = self.page(left + right + (image % other) * 2 + untouched)
        factored = self.lwp._factor_runtime_resources(original)
        data = runtime_data(factored)
        self.assertEqual(len(data['lwp-resource-data']['images']), 2)
        fragment = data['lwp-series-data']['views'][0]['content']
        self.assertIn(untouched, fragment)
        self.assertIn('data-lwp-image-fragment="#left"', fragment)
        self.assertIn('data-lwp-image-fragment="#right"', fragment)
        for attribute in ('alt="src=not-an-attribute &amp; more"', 'width="21"', 'height="34"', 'loading="lazy"', 'title="Title"'):
            self.assertEqual(fragment.count(attribute), 4)
        self.assertTrue(fragment.startswith('<IMG '))
        self.assertIn('/>', fragment)
        self.assertLess(len(factored), len(original))
        self.assertEqual(self.lwp._factor_runtime_resources(factored), factored)
        self.lwp.validate_html(factored, 'probe')

    def test_single_use_small_duplicates_and_unrelated_json_do_not_grow(self):
        for uri, count in [(self.uri, 1), ('data:image/png;base64,AA==', 6)]:
            html = self.page(('<img src="' + uri + '">') * count)
            self.assertEqual(self.lwp._factor_runtime_resources(html), html)
        html = '<script id="private" type="application/json">' + json.dumps({'content': self.uri * 4}) + '</script>'
        self.assertEqual(self.lwp._factor_runtime_resources(html), html)

    def test_opaque_contexts_preserve_resources_and_ignore_foreign_markers(self):
        image = '<img src="' + self.uri + '" alt="Authored">'
        fake = '<img data-lwp-image="foreign-reference" alt="Foreign marker">'
        for name, opening, closing in OPAQUE_CONTEXTS:
            with self.subTest(context=name):
                opaque = opening + image * 2 + fake + closing
                html = self.lwp._factor_runtime_resources(self.page(opaque + image * 2))
                self.lwp.validate_html(html, name)
                data = runtime_data(html)
                fragment = data['lwp-series-data']['views'][0]['content']
                self.assertTrue(fragment.startswith(opaque))
                self.assertEqual(fragment[len(opaque):].count('data-lwp-image='), 2)
                self.assertEqual(len(data['lwp-resource-data']['images']), 1)
        with self.assertRaises(SystemExit):
            self.lwp.validate_html(self.page(fake), 'eligible missing reference')

    def test_missing_or_corrupt_pool_references_fail_validation(self):
        html = self.lwp._factor_runtime_resources(self.page(('<img src="' + self.uri + '">') * 6))
        data = runtime_data(html)
        key = next(iter(data['lwp-resource-data']['images']))
        broken = re.sub(r'<script id="lwp-resource-data".*?</script>\n', '', html, flags=re.S)
        for value in (broken, html.replace('data-lwp-image=\\"' + key, 'data-lwp-image=\\"missing'),
                      html.replace(self.uri, self.uri + 'bad')):
            with self.subTest(value=value[:50]), self.assertRaises(SystemExit):
                self.lwp.validate_html(value, 'broken')
        css = self.page('', '<style>' + '.a{color:red}' * 100 + '</style>')
        payload = runtime_data(css)['lwp-series-data']
        payload['views'].append(copy.deepcopy(payload['views'][0]))
        css = '<script id="lwp-series-data" type="application/json">' + json.dumps(payload) + '</script>'
        factored = self.lwp._factor_runtime_resources(css)
        missing = re.sub(r'<script id="lwp-resource-data".*?</script>\n', '', factored, flags=re.S)
        with self.assertRaises(SystemExit):
            self.lwp.validate_html(missing, 'missing CSS')

    def test_unit_css_ownership_and_private_navigation(self):
        self.kit()
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace('page_title: Unit b', 'page_title: Unit b\nstyle.page.bg: #eeeeee'))
        output = self.root / 'public'
        self.cli('build', output, '--single-html', 'series.html')
        data = runtime_data((output / 'series.html').read_text())
        views = data['lwp-series-data']['views']
        self.assertEqual(views[0]['pageCss'], views[1]['pageCss'])
        self.assertNotEqual(views[1]['pageCss'], views[2]['pageCss'])
        self.assertIsInstance(views[2]['pageCss'], str)
        (self.root / 'templates/nav.js').write_text('// Private navigation\n')
        self.cli('build', output, '--inline-images')
        html = (output / 'a.html').read_text()
        self.assertNotIn('lwp-resource-data', runtime_data(html))
        self.assertEqual(html.count(self.uri), 24)

    def test_cli_same_bytes_different_mime_and_raw_inline_guard(self):
        (self.root / 'sources/img/same.jpg').write_bytes(self.png)
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace('img/same.png', 'img/same.jpg'))
        output = self.root / 'public'
        self.cli('build', output, '--single-html', 'series.html', '--inline-images')
        pool = runtime_data((output / 'series.html').read_text())['lwp-resource-data']['images']
        self.assertEqual(set(pool.values()), {self.uri, self.uri.replace('image/png', 'image/jpeg')})
        self.assertEqual(len(pool), 2)
        source.write_text(source.read_text().replace('![Second](img/same.jpg)', '<img src="img/same.jpg" alt="Raw">'))
        failed = fixtures.run('build', str(self.root), '--output', str(output), '--single-html', 'series.html',
                              '--inline-images', env=self.env)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('pointing outside', failed.stderr)

    def test_browser_offline_primary_and_inert_resources(self):
        try:
            probe = subprocess.run(['node', '-e', "process.stdout.write(require('playwright').chromium.executablePath())"],
                                   cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=30)
        except OSError as exc:
            self.skipTest('Browser check blocked: ' + str(exc))
        if probe.returncode:
            self.skipTest('Playwright unavailable: ' + probe.stderr)
        self.kit()
        identity_kit = self.root / 'templates/kits/lightwebpres-docs/0.1.0'
        theme = (identity_kit / 'themes/docs.conf').read_text().replace('\ncaption.fg: #5A7184FF\n', '\ncaption.fg: #116633\n')
        (identity_kit / 'themes/docs.conf').write_text(theme)
        (identity_kit / 'themes/compact.conf').write_text(theme.replace('#116633', '#aa2255'))
        manifest = json.loads((identity_kit / 'manifest.json').read_text())
        manifest['themes']['compact'] = 'themes/compact.conf'
        manifest['presets']['compact']['theme'] = 'compact'
        (identity_kit / 'manifest.json').write_text(json.dumps(manifest))
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="96">'
               '<view id="left" viewBox="0 0 64 96"/><view id="right" viewBox="64 0 64 96"/>'
               '<rect width="64" height="96" fill="red"/><rect x="64" width="64" height="96" fill="blue"/></svg>')
        (self.root / 'sources/img/views.svg').write_text(svg)
        for name in ('a', 'b'):
            source = self.root / 'sources' / (name + '.md')
            background, ink = ('#ffeedd', '#123456') if name == 'a' else ('#ddeeff', '#654321')
            text = source.read_text().replace('page_title: Unit ' + name,
                'page_title: Unit ' + name + '\nstyle.page.bg: ' + background
                + '\nstyle.page.fg: ' + ink + '\nstyle.color.ink: ' + ink)
            source.write_text(text.replace('## Images', '## Images\n\n![Left](img/views.svg#left)\n\n'
                                          '![Right](img/views.svg#right)', 1))
        (self.root / 'sources/c.md').write_text((self.root / 'sources/a.md').read_text().replace('Unit a', 'Unit c'))
        self.series['articles'].append({'page_source': 'c.md', 'page_dest': 'c.html'})
        self.save()
        self.cli('build', self.root / 'multi', '--inline-images')
        self.cli('build', self.root / 'single', '--single-html', 'series.html', '--inline-images')
        data = runtime_data((self.root / 'single/series.html').read_text())
        views = {view['key']: view for view in data['lwp-series-data']['views']}
        self.assertIsInstance(views['a.html']['pageCss'], dict)
        self.assertEqual(views['a.html']['pageCss'], views['c.html']['pageCss'])
        self.assertNotEqual(views['a.html']['pageCss'], views['b.html']['pageCss'])
        (self.root / 'opaque-contexts.json').write_text(json.dumps(OPAQUE_CONTEXTS))
        (self.root / 'copied').mkdir()
        shutil.copyfile(self.root / 'single/series.html', self.root / 'copied/renamed.html')
        env = {**self.env, 'PW_CHROMIUM_PATH': self.env.get('PW_CHROMIUM_PATH') or probe.stdout.strip()}
        result = subprocess.run(['node', str(ROOT / 'tests/resource_factoring_e2e.cjs'), str(self.root)],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        if result.returncode == 77:
            sys.stderr.write(result.stderr)
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Resource factoring:', result.stdout)


if __name__ == '__main__':
    unittest.main()
