"""Graphic resources are scoped, declarative and independent of body layout."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import quote

if __package__:
    from .test_lightwebpres import run, load_lightwebpres_module
else:
    from test_lightwebpres import run, load_lightwebpres_module

ROOT = Path(__file__).resolve().parents[1]


class GraphicLayers(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch, prefix='graphics-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources' / 'img').mkdir(parents=True)
        (self.root / 'sources' / 'img' / 'stamp image.svg').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="140">'
            '<rect width="600" height="140" fill="black"/></svg>', encoding='utf-8')
        self.env = {**os.environ, 'TMPDIR': str(scratch)}
        self.data = {'series_meta': {'title': 'Layers', 'scroll_duration': 0},
                     'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}]}
        (self.root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\npage_title: B\n---\n'
            '<!-- lwp:slide -->\nslug: other\n## Other\n', encoding='utf-8')
        self.source = ('<!-- lwp:meta -->\npage_title: Graphics\nlayers: ["draft"]\n'
                       'layers_by_type: {"cover": []}\n---\n\n'
                       '<!-- lwp:slide:cover -->\nslug: cover\n# Cover\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: detail\nkicker: Evidence\n## Native title\n'
                       'summary: Native summary\n\nShort body.\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: disabled\nlayers: []\n## No layers\n')
        self.asset = {'schema': 'lightwebpres.asset/1', 'id': 'label', 'kind': 'html',
                      'format': 'markdown-inline', 'content': '**DRAFT**',
                      'style': {'font_size': '28px', 'color': {'theme': 'kicker.fg'}}}
        self.layer = {'schema': 'lightwebpres.layer/1', 'id': 'draft', 'tags': ['draft'],
                      'elements': [{'id': 'stamp', 'asset': 'label', 'rotate': '-12deg',
                                    'place': {'target': {'ref': 'kicker', 'bounds': 'content',
                                                        'anchor': 'right-center'},
                                              'self_anchor': 'left-center', 'offset': ['8px', '0px']}}]}

    def write(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')
        (self.root / 'sources' / 'a.md').write_text(self.source, encoding='utf-8')

    def external(self):
        directory = self.root / 'templates' / 'graphics'
        directory.mkdir(parents=True, exist_ok=True)
        for name, value in [('asset', self.asset), ('layer', self.layer)]:
            (directory / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
        self.data['resources'] = {'assets': ['templates/graphics/asset.json'],
                                  'layers': ['templates/graphics/layer.json']}

    def cli(self, *arguments):
        return run(*arguments, env=self.env, cwd=ROOT)

    def build(self, *options):
        self.write()
        result = self.cli('build', self.root, '--lang', 'en', *options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_external_resources_and_explicit_empty_type_overrides(self):
        self.external()
        self.build()
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('data-lwp-graphics=', html)
        self.assertIn('lwp-graphic-assets', html)
        checked = self.cli('verify', self.root, '--lang', 'en')
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        other = (self.root / 'public' / 'b.html').read_text(encoding='utf-8')
        self.assertNotIn('data-lwp-graphics=', other)

    def test_inline_declarations_are_not_slides_or_body_text(self):
        self.source = self.source.replace('---\n\n<!-- lwp:slide:cover -->',
            '---\n\n````lwp-asset\n' + json.dumps({key: value for key, value in self.asset.items()
                                                  if key != 'content'})
            + '\n---\n**DRAFT**\n````\n\n````lwp-layer\n'
            + json.dumps(self.layer) + '\n````\n\n<!-- lwp:slide:cover -->', 1)
        self.build()
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('data-lwp-graphics=', html)
        self.assertNotIn('class="language-lwp-asset"', html)
        self.assertIn('Native title', html)

    def test_unknown_reference_and_dependency_cycles_fail_before_writes(self):
        self.external()
        for reference in ('not-a-native-reference', 'element:stamp'):
            self.layer['elements'][0]['place']['target']['ref'] = reference
            self.external()
            self.write()
            output = self.root / ('bad-' + reference.replace(':', '-'))
            result = self.cli('build', self.root, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('internal error', result.stderr)
            self.assertRegex(result.stderr, 'unknown|cycle')
            self.assertFalse(output.exists())

    def test_duplicate_and_unsafe_html_resources_fail(self):
        self.external()
        for content in ('<script>alert(1)</script>', '<span onclick="x()">bad</span>'):
            self.asset['format'] = 'html'
            self.asset['content'] = content
            self.external()
            self.write()
            result = self.cli('build', self.root)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('internal error', result.stderr)
            self.assertFalse((self.root / 'public').exists())

    def test_geometry_contract_exposes_screen_and_typed_resources(self):
        lwp = load_lightwebpres_module()
        contract = lwp.slide_draft_contract()
        self.assertEqual(contract['graphics']['schemas']['asset'], 'lightwebpres.asset/1')
        self.assertIn('screen', contract['graphics']['references'])
        self.assertIn('layers', contract['types'][0]['fields'])

    def plans(self, name='a.html', output='public'):
        from html import unescape
        html = (self.root / output / name).read_text(encoding='utf-8')
        return {slug: json.loads(unescape(plan)) for slug, plan in re.findall(
            r'<section\b[^>]*id="([^"]+)"[^>]*data-lwp-graphics="([^"]+)"', html)}

    def test_auto_tags_local_shadowing_and_owned_asset_binding(self):
        self.external()
        self.source = self.source.replace('layers: ["draft"]', 'layers: auto').replace(
            'slug: detail', 'slug: detail\ntags: draft')
        local_asset = {**self.asset, 'content': 'UNIT, NOT SERIES'}
        self.source = self.source.replace('<!-- lwp:slide:cover -->',
            '```lwp-asset\n' + json.dumps(local_asset) + '\n```\n\n<!-- lwp:slide:cover -->')
        self.build()
        plans = self.plans()
        self.assertEqual(list(plans), ['detail'])
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('DRAFT', html)
        self.assertNotIn('UNIT, NOT SERIES', html)

    def test_selection_cascade_add_remove_and_named_instances(self):
        self.external()
        self.data['series_meta']['layers'] = ['draft']
        self.source = self.source.replace('layers: ["draft"]',
            'layers: {"add": [{"use": "draft", "as": "other", '
            '"overrides": {"stamp": {"rotate": "32deg"}}}], "remove": ["draft"]}')
        self.build()
        plans = self.plans()
        self.assertEqual(list(plans), ['detail'])
        self.assertEqual(plans['detail']['layers'][0]['id'], 'other')
        self.assertEqual(plans['detail']['layers'][0]['elements'][0]['rotate'], 32)

    def test_image_ownership_inline_embedding_watch_and_incremental(self):
        self.asset = {**self.asset, 'kind': 'image', 'file': 'stamp image.svg', 'alt': 'Draft'}
        self.asset.pop('content')
        self.external()
        image = self.root / 'templates' / 'graphics' / 'stamp image.svg'
        image.write_bytes((self.root / 'sources' / 'img' / 'stamp image.svg').read_bytes())
        self.build()
        media = list((self.root / 'public' / 'assets' / 'graphics').glob('*.svg'))
        self.assertEqual(len(media), 1)
        checked = self.cli('verify', self.root, '--lang', 'en')
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        image.write_text(image.read_text().replace('black', 'red'), encoding='utf-8')
        checked = self.cli('verify', self.root, '--lang', 'en')
        self.assertNotEqual(checked.returncode, 0)
        self.build('--incremental', 'a.md')
        lwp = load_lightwebpres_module()
        self.assertIn(image, lwp._watch_paths(self.root, {}))
        self.build('--inline-images', '--single-html', 'all.html', '--output', self.root / 'inline')
        html = (self.root / 'inline' / 'all.html').read_text(encoding='utf-8')
        self.assertIn('data:image/svg+xml;base64,', html)
        self.assertFalse((self.root / 'inline' / 'assets' / 'graphics').exists())

    def test_html_image_urls_decode_once_but_descriptor_files_stay_literal(self):
        self.external()
        names = ('image one.svg', 'image%20one.svg', 'image &copy; #?.svg')
        media_dir = self.root / 'templates/graphics'
        for index, name in enumerate(names):
            (media_dir / name).write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{600 + index}" height="140">'
                '<rect width="600" height="140" fill="black"/></svg>', encoding='utf-8')
        self.layer['elements'].append({'id': 'literal-file',
            'asset': {'kind': 'image', 'file': names[1], 'alt': 'Literal percent filename'},
            'place': {'target': {'ref': 'slide'}}})
        for format_ in ('html', 'markdown'):
            urls = [quote(name, safe='/') + '#shape' for name in names]
            content = ('\n'.join(f'<img src="{url}" alt="Image {index}">' for index, url in enumerate(urls))
                       if format_ == 'html' else
                       '\n\n'.join(f'![Image {index}]({url})' for index, url in enumerate(urls)))
            self.asset.update(format=format_, content=content)
            self.external()
            for combined in (False, True):
                for inline in (False, True):
                    with self.subTest(format=format_, combined=combined, inline=inline):
                        output = self.root / f'{format_}-{combined}-{inline}'
                        options = ['--output', str(output)]
                        if combined:
                            options += ['--single-html', 'series.html']
                        if inline:
                            options.append('--inline-images')
                        self.build(*options)
                        checked = self.cli('verify', self.root, '--lang', 'en', *options)
                        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                        media = list((output / 'assets/graphics').glob('*.svg'))
                        self.assertEqual(len(media), 0 if inline else len(names))
                        if media:
                            self.assertEqual({path.read_bytes() for path in media},
                                             {(media_dir / name).read_bytes() for name in names})
                        html = (output / ('series.html' if combined else 'a.html')).read_text(encoding='utf-8')
                        self.assertIn('.svg#shape' if not inline else 'data:image/svg+xml;base64,', html)
        watched = load_lightwebpres_module()._watch_paths(self.root, {})
        for name in names:
            self.assertIn(media_dir / name, watched)

    def test_graphics_keep_table_merges_encoded_paths_and_mouse_acknowledgements(self):
        destination = 'Deck %20.html'
        self.data['articles'][0]['page_dest'] = destination
        self.source = ('<!-- lwp:meta -->\npage_title: Integrated graphics\n---\n\n'
                       '<!-- lwp:slide -->\nslug: grid\ntags: constructor\n'
                       '## Layers and cells\nfact-label: Pictures\n\n'
                       '| | | |\n|---|---|---|\n'
                       '| ![Wide](img/cell%20%2520.svg) {width=100%; height=auto} || '
                       '![Portrait](img/portrait.svg) {width=100%; height=auto} |\n'
                       '| ::: || ::: |\n| Landscape || Portrait |')
        image = (self.root / 'sources/img/stamp image.svg').read_bytes()
        (self.root / 'sources/img/cell %20.svg').write_bytes(image)
        (self.root / 'sources/img/portrait.svg').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="300">'
            '<rect width="120" height="300"/></svg>', encoding='utf-8')
        self.layer = {'id': 'draft', 'tags': ['constructor'], 'elements': [
            {'id': 'mark', 'asset': {'kind': 'image', 'file': 'mark %20.svg', 'alt': ''},
             'rotate': '25deg', 'size': {'width': '64px'},
             'place': {'target': {'ref': 'slide', 'anchor': 'right-center'},
                       'self_anchor': 'right-center', 'offset': ['-20px', '0px']}},
            {'id': 'assettable', 'asset': {'kind': 'html', 'format': 'markdown',
                 'content': '| | |\n|---|---|\n| ![HTML asset](mark%20%2520.svg) ||\n| ::: ||'},
             'size': {'width': '80px'},
             'place': {'target': {'ref': 'slide'}, 'offset': ['24px', '24px']}}]}
        self.external()
        (self.root / 'templates/graphics/mark %20.svg').write_bytes(image)
        bundle = self.root / 'bundle'
        for options in [(), ('--single-html', 'series.html', '--inline-images', '--output', bundle)]:
            self.build(*options)
            result = self.cli('verify', self.root, '--lang', 'en', *options)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run(['node', str(ROOT / 'tests/graphic_integration_e2e.cjs'),
                                 (self.root / 'public' / destination).as_uri(),
                                 (bundle / 'series.html').as_uri(), destination],
                                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=180)
        if result.returncode == 77:
            self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ('chromium', 'firefox'):
            self.assertIn(name + ': graphic/table/reader integration passed', result.stdout)

    def test_media_graphs_allow_disjoint_dependencies_but_require_print_geometry(self):
        self.external()
        element = self.layer['elements'][0]
        element['place']['target']['ref'] = 'screen'
        self.external()
        self.write()
        result = self.cli('build', self.root, '--output', self.root / 'bad-media')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('print', result.stderr)
        element['print'] = {'place': {'target': {'ref': 'slide'}}}
        self.external()
        self.build()

    def test_forward_inline_references_quoted_examples_and_original_line_numbers(self):
        lwp = load_lightwebpres_module()
        body = ('<!-- lwp:meta -->\npage_title: Inline\n---\n\n'
                '```lwp-layer\n' + json.dumps(self.layer) + '\n```\n'
                '```lwp-asset\n' + json.dumps(self.asset) + '\n```\n\n'
                '<!-- lwp:slide -->\nslug: only\n## An example\n\n'
                '````markdown\n```lwp-asset\n{"id": "not-active"}\n---\n'
                '<!-- lwp:slide:cover -->\n# Not a slide\n```\n````\n')
        parsed = lwp.ParsedUnit(body)
        self.assertEqual(len(parsed.parsed[1]), 1)
        self.assertEqual(parsed.resources[0]['line'], 5)
        self.assertEqual([entry['data']['id'] for entry in parsed.resources], ['draft', 'label'])
        self.source = body.replace('page_title: Inline', 'page_title: Inline\nlayers: ["draft"]')
        self.build()
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('&lt;!-- lwp:slide:cover --&gt;', html)
        self.assertIn('not-active', html)

    def test_missing_duplicate_and_misplaced_declarations_fail(self):
        self.external()
        self.source += '\n```lwp-asset\n' + json.dumps(self.asset) + '\n```\n'
        self.write()
        result = self.cli('build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('before the first slide', result.stderr)
        self.source = '<!-- lwp:meta -->\n---\n\n'
        definition = '```lwp-asset\n' + json.dumps(self.asset) + '\n```\n'
        self.source += definition + definition + '<!-- lwp:slide -->\nslug: a\n## A\n'
        self.write()
        result = self.cli('build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate', result.stderr)
        self.assertNotIn('internal error', result.stderr)

    def test_audit_keeps_graphic_parse_failures_advisory_unless_strict(self):
        self.source = self.source.replace('<!-- lwp:slide:cover -->',
            '```lwp-asset\n{"id": invalid-json}\n```\n\n<!-- lwp:slide:cover -->')
        self.write()
        ordinary = self.cli('audit', self.root)
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout + ordinary.stderr)
        self.assertIn('graphic declarations', ordinary.stderr)
        strict = self.cli('audit', self.root, '--strict')
        self.assertNotEqual(strict.returncode, 0)
        self.assertNotIn('internal error', strict.stderr)
        self.assertFalse((self.root / 'public').exists())

    def test_selector_uses_bounded_core_and_resolve_exposes_effective_plans(self):
        self.layer.pop('tags')
        self.layer['selector'] = '$[? @.slide.slug == "detail"]'
        self.source = self.source.replace('layers: ["draft"]\n', '')
        self.external()
        self.build()
        self.assertEqual(list(self.plans()), ['detail'])
        result = self.cli('resolve', self.root, 'layers', '--article', 'a.md', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        sites = json.loads(result.stdout)['resolution']['sites']
        self.assertEqual([site['value'] for site in sites], [[], ['draft'], []])
        self.assertIn('order', sites[1]['plan'])
        resources = self.cli('resolve', self.root, 'resources', '--article', 'a.md', '--format', 'json')
        self.assertEqual(resources.returncode, 0, resources.stderr)
        self.assertIn('draft', json.loads(resources.stdout)['resolution']['value']['series']['layers'])

    def test_generated_notes_receive_the_unit_policy(self):
        self.external()
        self.source = self.source.replace('page_title:', 'notes_placement: page\npage_title:')
        self.source = self.source.replace('Short body.', 'Short body.[^n]\n\n[^n]: A documented note.')
        self.build()
        self.assertIn('notes', self.plans())

    def test_variant_graphs_do_not_invent_cycles_between_disjoint_media(self):
        self.layer['elements'] = [
            {'id': 'a', 'asset': 'label', 'place': {'target': {'ref': 'slide'}},
             'screen': {'place': {'target': {'ref': 'element:b'}}}},
            {'id': 'b', 'asset': 'label', 'place': {'target': {'ref': 'slide'}},
             'print': {'place': {'target': {'ref': 'element:a'}}}},
        ]
        self.external()
        self.build()
        self.layer['elements'][1]['screen'] = {'place': {'target': {'ref': 'element:a'}}}
        self.external()
        self.write()
        result = self.cli('build', self.root, '--output', self.root / 'cyclic')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cycle', result.stderr)

    def test_unreferenced_media_is_validated_but_not_published(self):
        self.external()
        self.data['resources']['assets'].append({'id': 'spare', 'kind': 'image',
            'file': 'sources/img/stamp image.svg', 'alt': ''})
        self.build()
        self.assertFalse((self.root / 'public' / 'assets' / 'graphics').exists())

    def test_descriptors_and_payloads_are_watched_outside_templates(self):
        directory = self.root / 'artwork'
        directory.mkdir()
        (directory / 'asset.json').write_text(json.dumps(self.asset), encoding='utf-8')
        (directory / 'layer.json').write_text(json.dumps(self.layer), encoding='utf-8')
        self.data['resources'] = {'assets': ['artwork/asset.json'], 'layers': ['artwork/layer.json']}
        self.build()
        paths = load_lightwebpres_module()._watch_paths(self.root, {})
        self.assertIn(directory / 'asset.json', paths)
        self.assertIn(directory / 'layer.json', paths)

    def test_complete_tracked_example_builds_verifies_and_embeds(self):
        example = self.root / 'example'
        shutil.copytree(ROOT / 'examples' / 'graphic-layers', example)
        for options in ([], ['--single-html', 'series.html', '--inline-images']):
            for command in ('build', 'verify'):
                result = self.cli(command, example, '--lang', 'en', *options)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_slug_assignment_preserves_prologue_and_quoted_markers_byte_for_byte(self):
        example = self.root / 'slug-example'
        shutil.copytree(ROOT / 'examples' / 'graphic-layers', example)
        path = example / 'sources' / 'compositions.md'
        text = path.read_text(encoding='utf-8').replace('slug: attached\n', '')
        text = text.replace('Open the appearance menu',
            '````markdown\n```lwp-asset\n---\n<!-- lwp:slide:cover -->\nslug: quoted\n```\n````\n\n'
            'Open the appearance menu')
        path.write_text(text, encoding='utf-8')
        result = self.cli('series', 'slug', 'set', example)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        updated = path.read_text(encoding='utf-8')
        slides = load_lightwebpres_module().parse_markdown_extended(updated)[1]
        self.assertEqual(len(slides), 8)
        assigned = next(slide.slug for slide in slides if slide.h2 == 'Content and decoration stay independent')
        self.assertNotEqual(assigned, 'quoted')
        self.assertEqual(updated.replace('slug: ' + assigned + '\n', ''), text)
        report = self.cli('series', 'slug', example, '--format', 'json')
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(len(json.loads(report.stdout)['articles'][0]['slides']), 8)

    def test_clean_retires_only_owned_graphic_media(self):
        self.asset = {'id': 'label', 'kind': 'image', 'file': 'stamp.svg', 'alt': ''}
        self.external()
        (self.root / 'templates' / 'graphics' / 'stamp.svg').write_bytes(
            (self.root / 'sources' / 'img' / 'stamp image.svg').read_bytes())
        self.build()
        old = next((self.root / 'public' / 'assets' / 'graphics').glob('*.svg'))
        sidecar = old.parent / 'owner-file.txt'
        sidecar.write_text('Not produced by the build.', encoding='utf-8')
        self.source = self.source.replace('layers: ["draft"]', 'layers: []')
        self.build()
        result = self.cli('clean', self.root, '--force')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(old.exists())
        self.assertTrue(sidecar.exists())

    def test_watch_tracks_a_missing_nested_graphic_payload(self):
        self.asset.pop('content')
        self.asset['file'] = 'nested/missing.md'
        self.external()
        self.write()
        missing = self.root / 'templates' / 'graphics' / 'nested' / 'missing.md'
        watched = load_lightwebpres_module()._watch_paths(self.root, {})
        self.assertIn(missing, watched)
        self.assertIn(missing.parent, watched)

    def test_combined_html_owns_one_deduplicated_asset_payload(self):
        self.asset = {'id': 'label', 'kind': 'image', 'file': 'stamp.svg', 'alt': ''}
        self.external()
        (self.root / 'templates' / 'graphics' / 'stamp.svg').write_bytes(
            (self.root / 'sources' / 'img' / 'stamp image.svg').read_bytes())
        (self.root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\nlayers: ["draft"]\n---\n<!-- lwp:slide -->\nslug: b\n## B\n', encoding='utf-8')
        self.build('--single-html', 'all.html', '--inline-images')
        html = (self.root / 'public' / 'all.html').read_text(encoding='utf-8')
        payloads = re.findall(r'<script type="application/json" class="lwp-graphic-assets">([^<]+)</script>', html)
        self.assertEqual(len(payloads), 1)
        asset = next(iter(json.loads(payloads[0]).values()))
        self.assertTrue(asset['url'].startswith('data:image/svg+xml;base64,'))
        self.assertEqual(html.count(asset['url']), 1)

    def test_wrong_policy_scopes_and_empty_series_resources_do_not_fail_silently(self):
        self.external()
        for field in ('layers', 'layers_by_type', 'resources'):
            with self.subTest(field=field):
                self.data['articles'][0][field] = []
                self.write()
                result = self.cli('build', self.root, '--output', self.root / ('wrong-' + field))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('not articles[]', result.stderr)
                self.data['articles'][0].pop(field)
        self.data['articles'] = []
        self.asset['content'] = '<script>not static</script>'
        self.asset['format'] = 'html'
        self.external()
        self.write()
        result = self.cli('build', self.root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('static HTML', result.stderr)
        self.assertNotIn('internal error', result.stderr)

    def test_native_reference_registry_matches_all_rendered_slide_types(self):
        lwp = load_lightwebpres_module()
        self.asset.update(format='plain', content='X')
        self.layer = {'id': 'refs', 'media': ['screen'], 'elements': [
            {'id': name.replace('.', '-'), 'asset': 'label', 'size': {'width': '12px'},
             'place': {'target': {'ref': name, 'anchor': 'center'}, 'self_anchor': 'center'}}
            for name in lwp.GRAPHIC_REFERENCES]}
        self.layer['elements'].append({'id': 'strict', 'asset': 'label',
            'place': {'target': {'ref': 'header.image'}, 'on_missing': 'error'}})
        self.layer['elements'].append({'id': 'local', 'asset': 'label',
            'size': {'width': '12px'}, 'place': {'target': {'ref': 'anchor:local-target'}}})
        self.source = ('<!-- lwp:meta -->\npage_title: Native references\nstatus: draft\n'
                       'author: Example author\nlicense: Example licence\n'
                       'notes_placement: page\nlayers: ["refs"]\n---\n\n'
                       '<!-- lwp:slide:cover -->\nslug: cover\nkicker: Cover\n# Cover title\nsummary: A summary.\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: fact\nkicker: Fact\n## Fact title\nsummary: A summary.\n'
                       'highlight: 42\nhighlight-caption: A caption\nfact-label: Evidence\nsource: A source\n\n'
                       'Body with a note.[^n]\n\n[^n]: A note body.\n\n'
                       '<div id="local-scroller" style="height:180px;overflow:auto">'
                       '<div style="height:30px"></div><span id="local-target">Local target</span>'
                       '<div style="height:600px"></div></div>\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: body\n## Free body\n\nSome free body.\n\n---\n\n'
                       '<!-- lwp:slide:unit-index -->\nslug: index\n## Contents\nsummary: Choose a card.\n\n---\n\n'
                       '<!-- lwp:slide:series-nav -->\nslug: series\n\n---\n\n'
                       '<!-- lwp:slide:full-article -->\nslug: article\narticle: long.md\n')
        (self.root / 'sources' / 'long.md').write_text('# Long title\n\nLong body.\n', encoding='utf-8')
        self.data['chrome'] = {'header': 'Header', 'footer': 'Footer'}
        self.data['series_meta']['slide_page_numbers'] = True
        self.external()
        self.build('--include-drafts', '--build-stamp')
        result = subprocess.run(['node', str(ROOT / 'tests' / 'graphic_refs_e2e.cjs'),
                                 (self.root / 'public' / 'a.html').as_uri()],
                                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=150)
        if result.returncode == 77:
            self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_background_and_foreground_images_cover_the_slide_without_changing_layout(self):
        self.asset = {'id': 'label', 'kind': 'image', 'file': 'background.svg', 'alt': ''}
        self.layer = {'id': 'backdrop', 'plane': 'under-content', 'elements': [{
            'id': 'background', 'asset': 'label',
            'size': {'width': {'percent': 100, 'of': 'slide.width'},
                     'height': {'percent': 100, 'of': 'slide.height'}, 'fit': 'cover'},
            'place': {'target': {'ref': 'slide', 'anchor': 'center'}, 'self_anchor': 'center'},
        }]}
        self.source = self.source.replace('layers: ["draft"]', 'layers: ["backdrop", "foreground"]')
        self.source = self.source.replace('layers_by_type: {"cover": []}\n', '')
        self.external()
        directory = self.root / 'templates' / 'graphics'
        (directory / 'background.svg').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="140">'
            '<rect width="600" height="140" fill="#dbefff"/></svg>', encoding='utf-8')
        (directory / 'front.svg').write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
            '<rect width="100" height="100" fill="#c02030"/></svg>', encoding='utf-8')
        self.data['resources']['assets'].append({'id': 'front', 'kind': 'image',
            'file': 'templates/graphics/front.svg', 'alt': ''})
        self.data['resources']['layers'].append({'id': 'foreground', 'plane': 'over-content', 'elements': [{
            'id': 'front', 'asset': 'front', 'size': {'width': '60px'},
            'tint': {'theme': 'color.call'},
            'place': {'target': {'ref': 'slide', 'anchor': 'center'}, 'self_anchor': 'center'},
        }]})
        self.source = self.source.replace('page_title:', 'style.color.call: #c02030\npage_title:', 1)
        self.build()
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        payload = json.loads(re.search(r'class="lwp-graphic-assets">([^<]+)</script>', html).group(1))
        self.assertTrue(any(asset.get('url', '').startswith('data:image/svg+xml;base64,')
                            for asset in payload.values()))
        self.assertEqual(len(list((self.root / 'public' / 'assets' / 'graphics').glob('*.svg'))), 1)
        result = subprocess.run(['node', str(ROOT / 'tests' / 'graphic_backgrounds_e2e.cjs'),
                                 (self.root / 'public' / 'a.html').as_uri()],
                                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=150)
        if result.returncode == 77:
            self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_values_are_diagnostics_not_internal_errors(self):
        self.external()
        cases = [({'style': {'color': {'theme': []}}}, 'asset'),
                 ({'elements': [False]}, 'layer'),
                 ({'elements': [{'id': 'a', 'asset': 'label', 'rotate': False}]}, 'layer'),
                 ({'elements': [{'id': 'a', 'asset': 'label', 'media': [False]}]}, 'layer'),
                 ({'elements': [{'id': 'a', 'asset': 'label', 'size': {'width': '-20px'}}]}, 'layer'),
                 ({'elements': [{'id': 'a', 'asset': 'label', 'place': {'target': {'ref': []}}}]}, 'layer')]
        original_asset, original_layer = self.asset, self.layer
        for number, (patch, kind) in enumerate(cases):
            with self.subTest(kind=kind, patch=patch):
                self.asset, self.layer = dict(original_asset), dict(original_layer)
                (self.asset if kind == 'asset' else self.layer).update(patch)
                self.external()
                self.write()
                result = self.cli('build', self.root, '--output', self.root / ('bad-' + str(number)))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('internal error', result.stderr)

    def test_browser_anchors_media_isolation_and_runtime_replacement(self):
        self.external()
        self.asset.update(format='html', content='<h2 class="slide-kicker" id="spoof">DRAFT</h2>')
        self.layer['elements'] = [
            {**self.layer['elements'][0], 'size': {'width': '120px'},
             'effects': [{'kind': 'shadow', 'x': '2px', 'y': '3px', 'blur': '3px', 'color': '#00000066'}]},
            {'id': 'screen', 'asset': {'kind': 'image', 'file': 'img/stamp image.svg', 'alt': ''},
             'size': {'width': {'percent': 20, 'of': 'screen.width'}},
             'place': {'target': {'ref': 'screen', 'anchor': 'bottom-right'},
                       'self_anchor': 'bottom-right', 'offset': ['-10px', '-10px']},
             'print': {'size': {'width': {'percent': 20, 'of': 'slide.width'}},
                       'place': {'target': {'ref': 'slide', 'anchor': 'bottom-right'},
                                 'self_anchor': 'bottom-right', 'offset': ['-10px', '-10px']}}},
            {'id': 'viewport', 'asset': 'label', 'media': ['screen'],
             'size': {'height': {'percent': 10, 'of': 'viewport.height'}},
             'place': {'target': {'ref': 'viewport', 'anchor': 'top-left'}, 'offset': ['10px', '10px']}},
            {'id': 'dependent', 'asset': 'label', 'size': {'width': '70px'},
             'place': {'target': {'ref': 'element:stamp', 'anchor': 'bottom-left'},
                       'offset': ['0px', '6px']}},
            {'id': 'fixed', 'asset': {'kind': 'html', 'format': 'plain', 'content': 'FIXED',
                                     'style': {'font_size': '22px', 'color': '#123456'}},
             'place': {'target': {'ref': 'slide'}, 'offset': ['20px', '160px']}},
            {'id': 'before', 'asset': {'kind': 'image', 'file': 'img/stamp image.svg', 'alt': 'Before rotation'},
             'rotate': '45deg', 'tint': '#ff0000', 'size': {'width': '120px', 'measure': 'before-rotation'},
             'place': {'target': {'ref': 'slide'}, 'offset': ['20px', '210px']}},
            {'id': 'wrapped', 'asset': {'kind': 'html', 'format': 'markdown',
                'content': 'Several words that must wrap on multiple lines.', 'style': {'font_size': '16px'}},
             'layout': {'width': '90px'}, 'size': {'width': '180px', 'measure': 'before-rotation'},
             'place': {'target': {'ref': 'slide'}, 'offset': ['20px', '340px']}},
            {'id': 'region', 'asset': 'label', 'size': {'width': '45px'}, 'debug': True,
             'place': {'target': {'ref': 'region:gap', 'anchor': 'center'}, 'self_anchor': 'center'}},
            {'id': 'link', 'asset': {'kind': 'html', 'format': 'html',
                'content': '<a href="#local">Jump locally</a><span id="local"> target</span>'},
             'interaction': 'links', 'place': {'target': {'ref': 'slide'}, 'offset': ['200px', '14px']}},
            {'id': 'fragment', 'asset': 'label', 'media': ['screen'],
             'size': {'height': {'percent': 20, 'of': 'screen.height'}},
             'place': {'target': {'ref': 'screen'}, 'offset': ['0px', '0px']}},
            {'id': 'variant', 'asset': {'kind': 'html', 'format': 'plain', 'content': 'Mixed Case',
                                       'style': {'font_size': '22px'}},
             'screen': {'style': {'color': '#ff0000', 'transform': 'small-caps'}},
             'place': {'target': {'ref': 'slide', 'anchor': 'top-right'},
                       'self_anchor': 'top-right', 'offset': ['-100px', '100px']}},
        ]
        self.layer['regions'] = {'gap': {
            'left': {'ref': 'title', 'edge': 'left'}, 'right': {'ref': 'summary', 'edge': 'right'},
            'top': {'ref': 'title', 'edge': 'bottom'}, 'bottom': {'ref': 'summary', 'edge': 'top'}}}
        # Inline assets in an external composition resolve relative to that
        # composition, not its caller. Keep this source image local to it.
        media_dir = self.root / 'templates' / 'graphics' / 'img'
        media_dir.mkdir()
        (media_dir / 'stamp image.svg').write_bytes((self.root / 'sources' / 'img' / 'stamp image.svg').read_bytes())
        kit, manifest = self.kit()
        self.data['appearance'] = {'presets': ['builtin/standard', 'graphics-test@1.0.0/test'],
                                   'themes': ['light', 'monochrome-night']}
        self.data['chrome'] = {'header': 'Native header', 'footer': 'Native footer'}
        self.source = self.source.replace('<!-- lwp:slide -->\nslug: disabled',
            '<!-- lwp:slide -->\nslug: edge\nkicker: Second fragment\n## Edge\n\n'
            'Another short card.\n\n---\n\n<!-- lwp:slide -->\nslug: disabled')
        self.source += ('\n---\n\n<!-- lwp:slide -->\nslug: tall\nkicker: Tall label\n'
                        '## Long slide\n\n' + '\n\n'.join('A paragraph of content.' for _ in range(75)))
        (self.root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\npage_title: B\nlayers: ["draft"]\n---\n'
            '<!-- lwp:slide -->\nslug: other\nkicker: Second\n## Other\n', encoding='utf-8')
        self.external()
        self.data['resources']['layers'].append({'id': 'followers', 'plane': 'under-content',
            'elements': [{'id': 'cross', 'asset': 'label', 'size': {'width': '36px'},
                          'place': {'target': {'ref': 'layer:draft/dependent', 'anchor': 'bottom-right'},
                                    'offset': ['4px', '4px']}}]})
        self.source = self.source.replace('layers: ["draft"]', 'layers: ["followers", "draft"]', 1)
        self.build()
        bundle = self.root / 'bundle'
        self.build('--single-html', 'series.html', '--inline-images', '--output', bundle)
        result = subprocess.run(['node', str(ROOT / 'tests' / 'graphic_layers_e2e.cjs'),
                                 (self.root / 'public' / 'a.html').as_uri(),
                                 (bundle / 'series.html').as_uri()],
                                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=240)
        if result.returncode == 77:
            self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('graphic checks passed', result.stdout)

    def kit(self):
        kit = self.root / 'templates' / 'kits' / 'graphics-test' / '1.0.0'
        (kit / 'slides').mkdir(parents=True)
        (kit / 'slides' / 'default.html').write_text(
            '<div class="graphic-test-layout">{{slide_header}}\n'
            '<div class="graphic-test-main">{{content}}</div>\n{{slide_footer}}</div>', encoding='utf-8')
        kinds = ('cover', 'standard', 'series-nav', 'full-article', 'unit-index')
        manifest = {'schema': 'lightwebpres.identity-kit/1', 'id': 'graphics-test', 'version': '1.0.0',
                    'label': 'Graphics fixture', 'layouts': {kind: {'default': 'slides/default.html'} for kind in kinds},
                    'themes': {'paper': 'builtin:light'},
                    'presets': {'test': {'label': 'Anchors', 'description': 'Graphic reference geometry.',
                                         'theme': 'paper', 'slide_layouts': {kind: 'default' for kind in kinds},
                                         'slide_chrome': {}, 'slide_chrome_placement': 'edge',
                                         'kicker_position': 'after-header'}}}
        (kit / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return kit, manifest
