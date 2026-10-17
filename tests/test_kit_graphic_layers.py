"""Kits own graphic resources; presets select them without taking source ownership."""
import copy
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('cover', 'standard', 'series-nav', 'full-article', 'unit-index')


class Plans(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.plans = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section' and 'slide' in attrs.get('class', '').split():
            self.plans[attrs['id']] = json.loads(attrs.get('data-lwp-graphics', '{"layers":[]}'))


class KitGraphicLayers(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch, prefix='kit-graphics-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources').mkdir()
        self.data = {'series_meta': {'scroll_duration': 0},
                     'appearance': {'presets': ['red@1.0.0/decorated']},
                     'articles': [{'page_source': 'a.md'}]}
        self.source = ('<!-- lwp:meta -->\npage_title: Kit graphics\n---\n\n'
                       '<!-- lwp:slide:cover -->\nslug: cover\n# Cover\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: detail\ntags: evidence\n## Detail\n\nBody.\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: disabled\nlayers: []\n## Disabled\n')
        self.env = {**os.environ, 'TMPDIR': str(scratch),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'no-kits'),
                    'LWP_THEMES_DIR': str(self.root / 'no-themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'no-commons')}
        self.kits = {}
        self.kit('red', 'RED')

    def kit(self, name, label):
        path = self.root / 'templates/kits' / name / '1.0.0'
        (path / 'graphics/label').mkdir(parents=True)
        (path / 'graphics/label/label.txt').write_text(label, encoding='utf-8')
        (path / 'graphics/label/asset.json').write_text(json.dumps({
            'id': 'mark', 'kind': 'html', 'format': 'plain', 'file': 'label.txt',
            'style': {'font_size': '20px', 'color': {'theme': 'kicker.fg'}}}), encoding='utf-8')
        (path / 'graphics/frame.json').write_text(json.dumps({
            'id': 'frame', 'elements': [{'id': 'stamp', 'asset': 'mark',
                'rotate': '-10deg', 'size': {'width': '80px'},
                'place': {'target': {'ref': 'slide', 'anchor': 'top-right'},
                          'self_anchor': 'top-right', 'offset': ['-20px', '20px']}}]}), encoding='utf-8')
        preset = {'label': 'Decorated', 'description': 'Kit-owned graphic defaults', 'theme': 'paper',
                  'slide_layouts': {kind: 'default' for kind in KINDS}, 'slide_chrome': {},
                  'layers': {'add': ['frame']}, 'layers_by_type': {'cover': []}}
        manifest = {'schema': 'lightwebpres.identity-kit/1', 'id': name, 'version': '1.0.0',
                    'label': label, 'layouts': {kind: {'default': 'builtin:standard'} for kind in KINDS},
                    'themes': {'paper': 'builtin:light'}, 'resources': {
                        'assets': ['graphics/label/asset.json'], 'layers': ['graphics/frame.json']},
                    'presets': {'decorated': preset,
                                'plain': {**copy.deepcopy(preset), 'label': 'Plain', 'layers': [], 'layers_by_type': {}}}}
        self.kits[name] = (path, manifest)
        self.write_kit(name)
        return path, manifest

    def write_kit(self, name):
        path, manifest = self.kits[name]
        (path / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    def write(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')
        (self.root / 'sources/a.md').write_text(self.source, encoding='utf-8')

    def cli(self, *args):
        return run(*args, env=self.env, cwd=ROOT)

    def build(self, *options):
        self.write()
        result = self.cli('build', self.root, '--lang', 'en', *options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli('verify', self.root, '--lang', 'en', *options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = Path(options[options.index('--output') + 1]) if '--output' in options else self.root / 'public'
        name = options[options.index('--single-html') + 1] if '--single-html' in options else 'a.html'
        return (output / name).read_text(encoding='utf-8')

    def test_preset_defaults_type_choices_and_slide_clear(self):
        html = self.build()
        plans = Plans(html).plans
        self.assertEqual(plans['cover']['layers'], [])
        self.assertEqual(plans['disabled']['layers'], [])
        self.assertEqual([layer['id'] for layer in plans['detail']['layers']], ['frame'])
        self.assertEqual(plans['detail']['layers'][0]['definition']['scope'], 'kit/red@1.0.0')
        self.assertEqual(plans['detail']['trace'][-1]['source'], 'preset')

    def test_source_scopes_override_and_explicit_kit_lookup_keeps_asset_binding(self):
        self.data['resources'] = {'assets': [{'id': 'mark', 'kind': 'html', 'format': 'plain', 'content': 'SOURCE'}]}
        self.source = self.source.replace('page_title: Kit graphics', 'page_title: Kit graphics\nlayers: ["kit/frame"]')
        html = self.build()
        plan = Plans(html).plans['detail']
        self.assertEqual([layer['id'] for layer in plan['layers']], ['frame'])
        self.assertEqual(plan['trace'][-1]['source'], 'unit')
        assets = {}
        for payload in re.findall(r'<script type="application/json" class="lwp-graphic-assets">(.*?)</script>', html, re.S):
            assets.update(json.loads(payload))
        bound = assets[plan['layers'][0]['elements'][0]['asset']]['html']
        self.assertIn('RED', bound)
        self.assertNotIn('SOURCE', bound)
        self.source = self.source.replace('layers: ["kit/frame"]',
            'layers: [{"use":"kit/frame","overrides":{"stamp":{"asset":"series/mark"}}}]')
        html = self.build()
        plan = Plans(html).plans['detail']
        assets = {}
        for payload in re.findall(r'<script type="application/json" class="lwp-graphic-assets">(.*?)</script>', html, re.S):
            assets.update(json.loads(payload))
        bound = assets[plan['layers'][0]['elements'][0]['asset']]['html']
        self.assertIn('SOURCE', bound, 'an explicit author asset override uses caller scope')
        self.assertNotIn('RED', bound)

    def test_series_remove_and_unit_add_can_override_a_kit_instance(self):
        self.data['series_meta']['layers'] = {'remove': ['frame']}
        self.source = self.source.replace('page_title: Kit graphics',
            'page_title: Kit graphics\nlayers: {"add":[{"use":"kit/frame","as":"local","overrides":{"stamp":{"rotate":22}}}]}')
        plans = Plans(self.build()).plans
        layer = plans['detail']['layers'][0]
        self.assertEqual(layer['id'], 'local')
        self.assertEqual(layer['elements'][0]['rotate'], 22)

    def test_alternatives_have_distinct_plans_and_assets_with_same_resource_ids(self):
        self.kit('blue', 'BLUE')
        self.data['appearance']['presets'] = ['builtin/standard', 'red@1.0.0/decorated',
                                               'red@1.0.0/plain', 'blue@1.0.0/decorated']
        html = self.build()
        self.assertEqual(Plans(html).plans['detail']['layers'], [])
        runtime = json.loads(re.search(r'<script id="lwp-presentation-data" type="application/json">(.*?)</script>', html, re.S)[1])
        variants = runtime['variants']
        self.assertEqual(variants['red@1.0.0/plain']['graphics'], {})
        red = variants['red@1.0.0/decorated']['graphics']['detail']['layers'][0]
        blue = variants['blue@1.0.0/decorated']['graphics']['detail']['layers'][0]
        self.assertNotEqual(red['elements'][0]['asset'], blue['elements'][0]['asset'])
        self.assertIn('RED', html)
        self.assertIn('BLUE', html)
        self.assertIn('LWP anchored graphic compositions', html, 'the initially empty native view still loads the runtime')

    def test_kit_and_preset_reports_expose_owned_resources_and_defaults(self):
        self.write()
        kit = run('kit', 'show', 'red@1.0.0', '--format', 'json', cwd=ROOT,
                  env={**self.env, 'LWP_IDENTITY_KITS_DIR': str(self.root / 'templates/kits')})
        self.assertEqual(kit.returncode, 0, kit.stdout + kit.stderr)
        report = json.loads(kit.stdout)
        self.assertEqual(report['resources'], {'assets': ['mark'], 'layers': ['frame']})
        preset = self.cli('series', 'preset', self.root, '--format', 'json')
        self.assertEqual(preset.returncode, 0, preset.stdout + preset.stderr)
        self.assertEqual(json.loads(preset.stdout)['preset']['layers'], {'add': ['frame']})

    def test_resolve_exposes_primary_and_alternative_preset_plans(self):
        self.data['appearance']['presets'] = ['red@1.0.0/decorated', 'red@1.0.0/plain']
        self.write()
        result = self.cli('resolve', self.root, 'layers', '--article', 'a.md', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        resolution = json.loads(result.stdout)['resolution']
        self.assertIn('red@1.0.0/plain', resolution['presets'])
        self.assertTrue(all(not site['value'] for site in resolution['presets']['red@1.0.0/plain']))
        result = self.cli('resolve', self.root, 'resources', '--article', 'a.md', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('kit/red@1.0.0', json.loads(result.stdout)['resolution']['value'])

    def test_registered_graphic_dependencies_affect_digest_watch_and_verify(self):
        self.build()
        lwp = load_lightwebpres_module()
        kit = self.kits['red'][0]
        before = lwp._load_identity_kit(kit, 'series')
        label = kit / 'graphics/label/label.txt'
        self.assertIn(label, before.dependency_paths)
        self.assertIn(label, lwp._watch_paths(self.root, {}))
        label.write_text('CHANGED', encoding='utf-8')
        self.assertNotEqual(before.digest, lwp._load_identity_kit(kit, 'series').digest)
        self.assertNotEqual(self.cli('verify', self.root, '--lang', 'en').returncode, 0)
        self.write()
        result = self.cli('build', self.root, '--lang', 'en', '--incremental', 'a.md')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli('verify', self.root, '--lang', 'en')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invalid_unused_alternative_is_refused_without_touching_publication(self):
        self.build()
        (self.root / 'public/manual.txt').write_text('KEEP', encoding='utf-8')
        self.kit('blue', 'BLUE')
        path, manifest = self.kits['blue']
        manifest['resources']['assets'].append({'id': 'missing', 'kind': 'image', 'alt': '', 'file': 'missing.svg'})
        self.write_kit('blue')
        self.data['appearance']['presets'].append('blue@1.0.0/plain')
        self.write()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        for command, options in [('build', ()), ('verify', ()), ('build', ('--incremental', 'a.md'))]:
            result = self.cli(command, self.root, '--lang', 'en', *options)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
            self.assertIn('missing.svg', result.stderr)
            self.assertEqual({p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}, before)

    def test_kit_definitions_cannot_capture_documentary_resources(self):
        path, _manifest = self.kits['red']
        layer = json.loads((path / 'graphics/frame.json').read_text())
        layer['elements'][0]['asset'] = 'series/mark'
        (path / 'graphics/frame.json').write_text(json.dumps(layer))
        self.data['resources'] = {'assets': [{'id': 'mark', 'kind': 'html', 'content': 'SOURCE'}]}
        self.write()
        result = self.cli('build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, 'kit.*(?:source|series)|(?:source|series).*kit')
        self.assertFalse((self.root / 'public').exists())

    def test_kit_compose_copies_declared_graphics_as_standalone_resources(self):
        path, manifest = self.kits['red']
        destination_manifest = copy.deepcopy(manifest)
        destination_manifest.update(id='composed', label='Composed')
        declared = ['graphics/label/asset.json', 'graphics/label/label.txt', 'graphics/frame.json']
        recipe = {'schema': 'lightwebpres.kit-composition/1', 'sources': {'red': str(path.relative_to(self.root))},
                  'manifest': destination_manifest, 'files': {name: {'source': 'red', 'path': name} for name in declared}}
        recipe_path = self.root / 'recipe.json'
        recipe_path.write_text(json.dumps(recipe), encoding='utf-8')
        result = self.cli('kit', 'compose', recipe_path, '--output', self.root / 'composed-kits')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        composed = self.root / 'composed-kits/composed/1.0.0'
        for name in declared:
            self.assertEqual((composed / name).read_bytes(), (path / name).read_bytes())
        shutil.move(str(path), str(self.root / 'original-kit'))
        self.env['LWP_IDENTITY_KITS_DIR'] = str(self.root / 'composed-kits')
        self.data['appearance']['presets'] = ['composed@1.0.0/decorated']
        self.assertEqual(Plans(self.build()).plans['detail']['layers'][0]['definition']['scope'], 'kit/composed@1.0.0')

    def test_alternative_image_media_are_published_once_and_unused_files_are_not(self):
        path, manifest = self.kits['red']
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40"><rect width="80" height="40"/></svg>'
        (path / 'graphics/picture %20.svg').write_bytes(svg)
        (path / 'graphics/unused.svg').write_bytes(svg.replace(b'80', b'81'))
        manifest['resources']['assets'] += [
            {'id': 'picture', 'kind': 'image', 'file': 'graphics/picture %20.svg', 'alt': ''},
            {'id': 'unused', 'kind': 'image', 'file': 'graphics/unused.svg', 'alt': ''}]
        manifest['presets']['decorated']['layers'] = [{
            'use': 'frame', 'overrides': {'stamp': {'asset': {
                'kind': 'image', 'file': 'graphics/picture %20.svg', 'alt': ''}}}}]
        self.write_kit('red')
        self.data['appearance']['presets'] = ['builtin/standard', 'red@1.0.0/decorated']
        for combined in (False, True):
            for inline in (False, True):
                with self.subTest(combined=combined, inline=inline):
                    output = self.root / f'media-{combined}-{inline}'
                    options = ['--output', output]
                    if combined: options += ['--single-html', 'series.html']
                    if inline: options.append('--inline-images')
                    self.build(*options)
                    files = list((output / 'assets/graphics').glob('*.svg'))
                    self.assertEqual(len(files), 0 if inline else 1)
                    if files:self.assertEqual(files[0].read_bytes(), svg)

    def test_init_vendors_graphic_descriptors_and_payloads_without_the_user_catalogue(self):
        fresh = self.root / 'fresh'
        env = {**self.env, 'LWP_IDENTITY_KITS_DIR': str(self.root / 'templates/kits')}
        result = run('init', fresh, '--preset', 'red@1.0.0/decorated', '--no-starter', env=env, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        copied = fresh / 'templates/kits/red/1.0.0/graphics/label/label.txt'
        self.assertEqual(copied.read_text(), 'RED')
        for command in ('demo', 'build', 'verify'):
            options = ('--lang', 'en') if command in ('build', 'verify') else ()
            result = self.cli(command, fresh, *options)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(any('RED' in path.read_text() for path in (fresh / 'public').glob('*.html')))

    def test_identity_preset_switching_preserves_source_layers_in_real_browsers(self):
        self.kit('blue', 'BLUE')
        image_hashes = {}
        for name, colour in [('red', '#cc2233'), ('blue', '#2255cc')]:
            path, manifest = self.kits[name]
            image = (f'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
                     f'<rect width="80" height="40" fill="{colour}"/></svg>').encode()
            (path / 'graphics/picture %20.svg').write_bytes(image)
            image_hashes[name.upper()] = hashlib.sha256(image).hexdigest()[:24]
            manifest['resources']['assets'].append({'id': 'picture', 'kind': 'image',
                'file': 'graphics/picture %20.svg', 'alt': ''})
            layer = json.loads((path / 'graphics/frame.json').read_text())
            layer['elements'].append({'id': 'picture', 'asset': 'picture', 'size': {'width': '40px'},
                'place': {'target': {'ref': 'slide', 'anchor': 'bottom-right'},
                          'self_anchor': 'bottom-right', 'offset': ['-20px', '-20px']}})
            (path / 'graphics/frame.json').write_text(json.dumps(layer))
            self.write_kit(name)
        self.data['appearance']['presets'] = ['builtin/standard', 'red@1.0.0/decorated',
                                               'red@1.0.0/plain', 'blue@1.0.0/decorated']
        self.data['resources'] = {'assets': [{'id': 'author-label', 'kind': 'html', 'format': 'plain',
                                             'content': 'AUTHOR', 'style': {'font_size': '16px'}}],
                                 'layers': [{'id': 'author', 'elements': [{'id': 'note', 'asset': 'author-label',
                                    'place': {'target': {'ref': 'slide', 'anchor': 'bottom-left'},
                                              'self_anchor': 'bottom-left', 'offset': ['20px', '-20px']}}]}]}
        self.data['articles'].append({'page_source': 'b.md'})
        (self.root / 'sources/b.md').write_text(
            '<!-- lwp:meta -->\npage_title: Author layers\nlayers: {"add":["author"]}\n---\n\n'
            '<!-- lwp:slide -->\nslug: author-card\n## Source-owned graphics\n\nBody.\n', encoding='utf-8')
        self.build()
        bundle = self.root / 'bundle'
        self.build('--single-html', 'series.html', '--inline-images', '--output', bundle)
        result = subprocess.run(['node', str(ROOT / 'tests/kit_graphic_layers_e2e.cjs'),
            (self.root / 'public/a.html').as_uri(), (self.root / 'public/b.html').as_uri(),
            (bundle / 'series.html').as_uri(), json.dumps(image_hashes)],
            cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=240)
        if result.returncode == 77:self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for browser in ('chromium', 'firefox'):
            self.assertIn(browser + ': kit graphic layers passed', result.stdout)

    def test_automatic_kit_rules_and_source_auto_reset_use_the_active_catalogue(self):
        path, manifest = self.kits['red']
        layer = json.loads((path / 'graphics/frame.json').read_text())
        layer['tags'] = ['evidence']
        (path / 'graphics/frame.json').write_text(json.dumps(layer))
        manifest['presets']['decorated'].pop('layers')
        manifest['presets']['decorated'].pop('layers_by_type')
        self.write_kit('red')
        plans = Plans(self.build()).plans
        self.assertEqual([item['id'] for item in plans['detail']['layers']], ['frame'])
        self.assertEqual(plans['cover']['layers'], [])
        self.data['appearance']['presets'] = ['red@1.0.0/plain']
        self.assertEqual(Plans(self.build()).plans['detail']['layers'], [])
        self.source = self.source.replace('page_title: Kit graphics', 'page_title: Kit graphics\nlayers: auto')
        self.assertEqual([item['id'] for item in Plans(self.build()).plans['detail']['layers']], ['frame'])

    def test_invalid_choices_in_unpublished_kit_presets_are_rejected(self):
        path, manifest = self.kits['red']
        original = copy.deepcopy(manifest['presets']['plain'])
        for bad in ({'layers': None}, {'layers_by_type': None}, {'layers': ['frame', 'frame']},
                    {'layers': ['missing']}, {'layers_by_type': {'unknown-type': []}},
                    {'layers': '["frame"]'}, {'layers_by_type': '{"cover":[]}'},
                    {'layers_by_type': {'standard': '["frame"]'}}):
            with self.subTest(choice=bad):
                manifest['presets']['plain'] = {**copy.deepcopy(original), **bad}
                self.write_kit('red')
                self.write()
                result = self.cli('build', self.root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('presets.plain', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse((self.root / 'public').exists())

    def test_manifest_graphic_catalogue_is_an_actual_json_object(self):
        _path, manifest = self.kits['red']
        for value in (None, [], '{"assets":[],"layers":[]}'):
            with self.subTest(value=value):
                manifest['resources'] = value
                self.write_kit('red')
                self.write()
                result = self.cli('build', self.root)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('resources', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse((self.root / 'public').exists())

    def test_explicit_source_kit_reference_requires_every_published_identity(self):
        self.data['appearance']['presets'].append('builtin/standard')
        self.source = self.source.replace('page_title: Kit graphics', 'page_title: Kit graphics\nlayers: ["kit/frame"]')
        self.write()
        result = self.cli('build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('builtin/standard', result.stderr)
        self.assertIn('kit/frame', result.stderr)
        self.assertFalse((self.root / 'public').exists())

    def test_build_reuses_the_validated_kit_resource_snapshot(self):
        self.write()
        lwp = load_lightwebpres_module()
        path, _manifest = self.kits['red']
        kit = lwp._load_identity_kit(path, 'series')
        (path / 'graphics/label/label.txt').write_text('CHANGED AFTER LOAD', encoding='utf-8')
        preset = kit.presets['decorated']
        graphics = lwp.GraphicCatalog(self.root, self.root / 'sources', self.data, presets=[preset])
        plan = graphics.plan_unit('a.md', lwp.ParsedUnit(self.source), self.data['series_meta'])
        asset = graphics.assets[plan['detail']['layers'][0]['elements'][0]['asset']]
        self.assertIn('RED', asset['html'])
        self.assertNotIn('CHANGED AFTER LOAD', asset['html'])

    def test_tracked_kit_example_builds_embeds_and_composes_without_mock_resources(self):
        example = self.root / 'example'
        shutil.copytree(ROOT / 'examples/kit-layers', example)
        for options in [(), ('--single-html', 'series.html', '--inline-images')]:
            for command in ('build', 'verify'):
                result = self.cli(command, example, '--lang', 'en', *options)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.cli('kit', 'compose', example / 'compose.json', '--output', example / 'composed-kits')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads((example / 'series.json').read_text())
        data['appearance']['presets'] = ['signal-notes-composed@1.0.0/review']
        (example / 'series.json').write_text(json.dumps(data))
        shutil.move(str(example / 'templates/kits/signal-notes'), str(self.root / 'original-example-kit'))
        env = {**self.env, 'LWP_IDENTITY_KITS_DIR': str(example / 'composed-kits')}
        for command in ('build', 'verify'):
            result = run(command, example, '--lang', 'en', env=env, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
