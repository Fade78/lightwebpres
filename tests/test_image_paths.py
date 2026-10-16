"""Image URLs and filesystem inventories keep distinct, single-decoded names."""
import base64
import hashlib
from html import escape
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run


ROOT = Path(__file__).resolve().parents[1]
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="4"><rect width="8" height="4"/></svg>'


class ImageUrlPaths(unittest.TestCase):
    def test_inventory_decodes_urls_once_without_decoding_html_entities_twice(self):
        lwp = load_lightwebpres_module()
        for url, filename in (
                ('img/my%20photo.svg?v=2#detail', 'img/my photo.svg'),
                ('./img/nested%20dir/%C3%A9t%C3%A9.svg', 'img/nested dir/été.svg'),
                ('img/%64iagram.svg', 'img/diagram.svg'),
                ('img/100%25.svg', 'img/100%.svg'),
                ('img/literal%2520.svg', 'img/literal%20.svg'),
                ('img/a%23b%3Fc.svg?v=2#detail', 'img/a#b?c.svg'),
                ('img/%252e%252e/private.svg', 'img/%2e%2e/private.svg'),
                ('img/chart&copy;.svg', 'img/chart&copy;.svg')):
            with self.subTest(url=url):
                markup = '<img src="' + escape(url, quote=True) + '">'
                self.assertEqual(lwp.image_inventory_from_html([markup]),
                                 {filename: {'inline': 1, 'figure': 0}})

    def test_inventory_rejects_nonlocal_and_unsafe_decoded_urls(self):
        lwp = load_lightwebpres_module()
        for url in (None, '', 'https://example.invalid/a.svg', '//example.invalid/a.svg',
                    'file:///img/a.svg', '/img/a.svg', 'C:/img/a.svg',
                    '%2Fimg/a.svg', '%2F%2Fexample.invalid/a.svg',
                    'img/%2e%2e/private.svg', 'img/%2E%2E%2Fprivate.svg',
                    'img/%5Cprivate.svg', 'img/private.svg%00',
                    'img/private.svg#%0A', 'img/%FF.svg', 'img/a\nb.svg',
                    'img/./a.svg', 'img//a.svg', 'img/../a.svg'):
            with self.subTest(url=url):
                self.assertIsNone(lwp._local_image_path(url))

    def test_image_cache_validates_filesystem_paths_without_reinterpreting_urls(self):
        lwp = load_lightwebpres_module()
        with tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp') as temporary:
            root = Path(temporary)
            cache = root / 'images.json'
            paths = ['img/my photo.svg', 'img/literal%20.svg',
                     'img/a#b?c.svg', 'img/chart&copy;.svg']
            entry = {'sha256': 'a' * 64, 'images': paths}
            data = {'schema': lwp._IMAGE_CACHE_SCHEMA,
                    'output_dir': str(root), 'pages': {'a.html': entry}}
            cache.write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(lwp.load_image_cache(cache, root), {'a.html': entry})
            data['schema'] = 'lightwebpres.image-cache/1'
            cache.write_text(json.dumps(data), encoding='utf-8')
            self.assertIsNone(lwp.load_image_cache(cache, root))
            data['schema'] = lwp._IMAGE_CACHE_SCHEMA
            for unsafe in ('img/../private.svg', '/img/private.svg',
                           'img\\private.svg', 'img/private.svg\x00'):
                with self.subTest(unsafe=unsafe):
                    entry['images'] = [unsafe]
                    cache.write_text(json.dumps(data), encoding='utf-8')
                    self.assertIsNone(lwp.load_image_cache(cache, root))


class ImageUrlPublication(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp',
                                                prefix='image-url-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = {'LWP_THEMES_DIR': str(self.root / 'themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits')}
        self.sources = self.root / 'sources'
        self.sources.mkdir()
        (self.root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}],
        }), encoding='utf-8')
        for name in ('a', 'b'):
            (self.sources / (name + '.md')).write_text(
                '<!-- lwp:meta -->\n---\n\n<!-- lwp:slide:cover -->\n'
                'slug: cover\n# Article ' + name + '\nsummary: Example.\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: body\n## Body\nOriginal prose.\n',
                encoding='utf-8')

    def cli(self, command, *options, code=0):
        result = run(command, str(self.root), '--lang', 'en',
                     *map(str, options), env=self.env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def image(self, name):
        path = self.sources / 'img' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(SVG)
        return 'img/' + quote(name, safe='/')

    def append(self, name, text):
        path = self.sources / name
        path.write_text(path.read_text(encoding='utf-8') + '\n' + text + '\n',
                        encoding='utf-8')

    def test_encoded_images_are_copied_in_markdown_raw_html_and_long_form(self):
        names = ['my photo.svg', 'nested dir/été.svg', '100% chart.svg',
                 'a#b.svg', 'literal%20.svg', 'chart&copy;.svg']
        urls = [self.image(name) + '?v=2&mode=light#detail' for name in names]
        self.append('b.md', '\n'.join([
            '![Standalone](' + urls[0] + ')', '',
            'Inline ![Nested](' + urls[1] + ') here.', '',
            '<img src="' + escape(urls[2], quote=True) + '" alt="Raw">',
            '', '![Reserved](' + urls[3] + ')', '',
            '![Percent](' + urls[4] + ')', '',
            '![Entity](' + urls[5] + ')', '',
            '---', '', '<!-- lwp:slide:full-article -->',
            'slug: long-form', 'article: long.md',
        ]))
        (self.sources / 'long.md').write_text(
            '# Long form\n\n![Included](' + urls[0] + ')\n', encoding='utf-8')
        for mode, options in (('multi', ()), ('combined', ('--single-html', 'all.html'))):
            with self.subTest(mode=mode):
                output = self.root / mode
                self.cli('build', '--output', output, *options)
                for name in names:
                    self.assertEqual((output / 'img' / name).read_bytes(), SVG)
                manifest = json.loads((output / '.lwp-manifest.json').read_text())
                self.assertEqual(sorted(name for name in manifest['files']
                                        if name.startswith('img/')),
                                 sorted('img/' + name for name in names))
                self.cli('verify', '--output', output, *options)
        audited = self.cli('audit')
        self.assertNotIn('missing from sources/img/', audited.stdout + audited.stderr)
        self.assertNotIn('NEVER referenced', audited.stdout)
        for name in names:
            self.assertIn('img/' + name + ': referenced', audited.stdout)

    def test_verify_detects_missing_and_changed_encoded_images(self):
        url = self.image('my photo.svg')
        self.append('b.md', '![Photo](' + url + ')')
        for mode, options in (('multi', ()), ('combined', ('--single-html', 'all.html'))):
            with self.subTest(mode=mode):
                output = self.root / mode
                self.cli('build', '--output', output, *options)
                published = output / 'img/my photo.svg'
                published.unlink()
                missing = self.cli('verify', '--output', output, *options, code=1)
                self.assertIn('[NEW] img/my photo.svg', missing.stdout)
                self.cli('build', '--output', output, *options)
                published.write_bytes(b'Changed output')
                changed = self.cli('verify', '--output', output, *options, code=1)
                self.assertIn('[DRIFT] img/my photo.svg', changed.stdout)

    def test_incremental_retains_decoded_paths_in_cache_and_manifest(self):
        names = ['literal%20.svg', 'a#b.svg', 'my photo.svg']
        for name in names:
            self.append('b.md', '![Photo](' + self.image(name) + ')')
        self.cli('build')
        output = self.root / 'public'
        retained = (output / 'b.html').read_bytes()
        cache_path = self.root / '.lwp-cache/images.json'
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        expected = sorted('img/' + name for name in names)
        self.assertEqual(cache['pages']['b.html']['images'], expected)
        self.assertEqual(load_lightwebpres_module().load_image_cache(
            cache_path, output)['b.html']['images'], expected)
        for name in names:
            (self.sources / 'img' / name).write_bytes(SVG + b'\n')
        self.append('a.md', 'Changed prose.')
        built = self.cli('build', '--incremental', 'a.md')
        self.assertIn('Incremental build', built.stdout)
        self.assertEqual((output / 'b.html').read_bytes(), retained)
        for name in names:
            self.assertEqual((output / 'img' / name).read_bytes(), SVG + b'\n')
        manifest = json.loads((output / '.lwp-manifest.json').read_text())
        self.assertEqual(sorted(name for name in manifest['files']
                                if name.startswith('img/')), expected)
        self.cli('verify')

    def test_old_url_spelling_cache_is_discarded_for_retained_pages(self):
        url = self.image('my photo.svg')
        self.append('b.md', '![Photo](' + url + ')')
        self.cli('build')
        output = self.root / 'public'
        retained = (output / 'b.html').read_bytes()
        cache_path = self.root / '.lwp-cache/images.json'
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        cache['schema'] = 'lightwebpres.image-cache/1'
        cache['pages']['b.html'] = {
            'sha256': hashlib.sha256(retained).hexdigest(), 'images': [url]}
        cache_path.write_text(json.dumps(cache), encoding='utf-8')
        self.append('a.md', 'Changed prose.')
        built = self.cli('build', '--incremental', 'a.md')
        self.assertIn('Incremental build', built.stdout)
        self.assertEqual((output / 'b.html').read_bytes(), retained)
        self.assertEqual((output / 'img/my photo.svg').read_bytes(), SVG)
        fresh = json.loads(cache_path.read_text(encoding='utf-8'))
        self.assertEqual(fresh['pages']['b.html']['images'], ['img/my photo.svg'])

    def test_inline_decodes_once_preserves_fragments_and_does_not_copy_images(self):
        for name in ('my photo.svg', 'literal%20.svg', 'a#b.svg', 'chart&copy;.svg'):
            url = self.image(name)
            self.append('b.md', '![Photo](' + url + '?v=2#detail)')
        self.cli('build', '--inline-images')
        html = (self.root / 'public/b.html').read_text(encoding='utf-8')
        self.assertIn('data:image/svg+xml;base64,'
                      + base64.b64encode(SVG).decode('ascii') + '#detail', html)
        self.assertNotIn('src="img/', html)
        self.assertFalse((self.root / 'public/img').exists())
        self.cli('verify', '--inline-images')

    def test_decoded_traversal_in_raw_html_never_enters_the_copy_plan(self):
        (self.sources / 'private.svg').write_bytes(SVG)
        self.image('private.svg')
        for url in ('img/%2e%2e/private.svg', 'img/%2E%2E%2Fprivate.svg',
                    '%2Fimg/private.svg', 'img/%5Cprivate.svg',
                    'img/private.svg%00', 'img/%FF.svg'):
            self.append('b.md', '<img src="' + url + '" alt="Invalid">')
        self.cli('build')
        output = self.root / 'public'
        manifest = json.loads((output / '.lwp-manifest.json').read_text())
        self.assertFalse(any(name.startswith('img/') for name in manifest['files']))
        self.assertFalse((output / 'img').exists())


if __name__ == '__main__':
    unittest.main()
