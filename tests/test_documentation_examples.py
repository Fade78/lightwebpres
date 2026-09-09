"""Executable source examples, exercised without the author's installed kits."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / 'examples/kit-composition'
FIRST_ARTICLE = ROOT / 'examples/first-article'
SELECTOR = 'field-notes@1.0.0/brief'


class KitCompositionExample(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.catalogue = self.root / 'kits'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('LWP_')}
        self.env.update(
            HOME=str(self.root), XDG_DATA_HOME=str(self.root / 'data'),
            XDG_CONFIG_HOME=str(self.root / 'config'), APPDATA=str(self.root / 'data'),
            LWP_IDENTITY_KITS_DIR=str(self.catalogue),
            LWP_COMMONS_DIR=str(self.root / 'commons'),
            LWP_THEMES_DIR=str(self.root / 'themes'))

    def cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'lightwebpres'), *map(str, args)],
            cwd=self.root, env=self.env, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def first_article(self, series, selector, *options):
        self.cli('init', series, '--preset', selector, *options)
        shutil.copyfile(FIRST_ARTICLE / 'series.json', series / 'series.json')
        shutil.copyfile(FIRST_ARTICLE / 'sources/first-page.md',
                        series / 'sources/first-page.md')
        self.cli('series', 'preset', 'set', series, '--preset', selector,
                 '--keep-theme' if options else '--use-preset-theme')
        self.cli('build', series, '--lang', 'en')
        self.cli('verify', series, '--lang', 'en')
        return (series / 'public/first-page.html').read_text(encoding='utf-8')

    def test_composed_example_builds_after_recipe_and_sources_are_removed(self):
        inputs = self.root / 'example'
        shutil.copytree(EXAMPLE, inputs)
        recipe_path = inputs / 'recipe.json'
        recipe = json.loads(recipe_path.read_text(encoding='utf-8'))
        self.assertEqual(set(recipe['sources']), {'frames', 'marks', 'ink'})
        before = {p.relative_to(inputs): p.read_bytes()
                  for p in inputs.rglob('*') if p.is_file()}
        self.cli('kit', 'compose', recipe_path, '--output', self.catalogue, '--dry-run')
        self.assertFalse(self.catalogue.exists())
        self.cli('kit', 'compose', recipe_path, '--output', self.catalogue)
        self.assertEqual(before, {p.relative_to(inputs): p.read_bytes()
                                  for p in inputs.rglob('*') if p.is_file()})
        kit = self.catalogue / 'field-notes/1.0.0'
        self.assertEqual(json.loads((kit / 'manifest.json').read_text()), recipe['manifest'])
        self.assertEqual({p.relative_to(kit).as_posix()
                          for p in kit.rglob('*') if p.is_file()},
                         set(recipe['files']) | {'manifest.json'})
        for destination, descriptor in recipe['files'].items():
            original = inputs / recipe['sources'][descriptor['source']] / descriptor['path']
            expected = original.read_bytes()
            if destination == 'structure.css':
                expected = expected.replace(b'.lwp-presentation--field-frames',
                                            b'.lwp-presentation--field-notes')
            self.assertEqual((kit / destination).read_bytes(), expected)
        self.assertTrue((inputs / recipe['sources']['marks'] / 'assets/trail.svg').is_file())
        self.assertFalse((kit / 'assets/trail.svg').exists())
        shutil.rmtree(inputs)

        shown = json.loads(self.cli('preset', 'show', SELECTOR, '--format', 'json'))
        self.assertEqual(shown['selector'], SELECTOR)
        self.assertEqual(shown['label'], 'Field Notes Brief')
        self.assertEqual(shown['theme']['id'], 'paper')
        self.assertEqual(shown['theme']['label'], 'Field Notes Paper')
        series = self.root / 'first-article'
        html = self.first_article(series, SELECTOR)
        self.assertIn('class="field-sheet"', html)
        self.assertIn('class="field-sheet-content"', html)
        self.assertIn('.lwp-presentation--field-notes .field-sheet', html)
        self.assertIn('border-left: 7px double var(--color-ink)', html)
        self.assertIn('FIELD NOTES', html)
        self.assertIn('OBSERVE / RECORD / SHARE', html)
        self.assertIn('<span class="slide-chrome-label">Compass rose</span>', html)
        asset = 'assets/presentations/field-notes/1.0.0/compass.svg'
        self.assertIn(asset, html)
        self.assertEqual((series / 'public' / asset).read_bytes(),
                         (kit / 'assets/compass.svg').read_bytes())
        self.assertIn('id="travels-with-the-page"', html)
        self.assertIn('--color-ink: #111111', html)
        self.assertIn('--font-text: \'Nimbus Mono PS\'', html)
        self.assertIn('first-page.html', (series / 'public/index.html').read_text())
        for directory in (kit, series / 'public'):
            for path in directory.rglob('*'):
                if path.is_file():
                    with self.subTest(path=path.relative_to(directory)):
                        content = path.read_text(encoding='utf-8')
                        for forbidden in ('field-frames', 'field-marks', 'field-ink',
                                          'trail.svg', 'presentation:trail', str(inputs)):
                            self.assertNotIn(forbidden, content)

        theme = json.loads(self.cli('series', 'theme', series, '--format', 'json'))
        self.assertIsNone(theme['target']['theme'])
        self.assertEqual(theme['target']['presentation_preset'], SELECTOR)
        self.assertEqual(theme['label'], 'Field Notes Paper')
        self.assertEqual(theme['palette']['page'], '#FFFFFFFF')
        self.assertEqual(theme['palette']['ink'], '#111111FF')

        self.cli('series', 'theme', 'set', series, '--theme', 'nord')
        self.cli('build', series, '--lang', 'en')
        pinned = json.loads(self.cli('series', 'theme', series, '--format', 'json'))
        self.assertEqual(pinned['target']['theme'], 'nord')
        self.assertEqual(pinned['target']['presentation_preset'], SELECTOR)

        # No Markdown overrides: the tool can also offer the native presentation.
        match = re.search(r'<script id="lwp-presentation-data" type="application/json">'
                          r'(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match)
        runtime = json.loads(match.group(1))
        self.assertEqual(runtime['primary'], SELECTOR)
        self.assertEqual([preset['selector'] for preset in runtime['presets']],
                         [SELECTOR, 'builtin/standard'])
        self.assertIn('class="field-sheet"',
                      runtime['variants'][SELECTOR]['sections']['first-page'])
        self.assertNotIn('class="field-sheet"',
                         runtime['variants']['builtin/standard']['sections']['first-page'])
        self.cli('series', 'preset', 'set', series, '--preset', 'builtin/standard',
                 '--use-preset-theme')
        self.cli('build', series, '--lang', 'en')
        self.cli('verify', series, '--lang', 'en')
        self.assertNotIn('class="field-sheet"',
                         (series / 'public/first-page.html').read_text())

        overridden = self.root / 'override'
        override_html = self.first_article(overridden, SELECTOR, '--theme', 'nord')
        theme = json.loads(self.cli('series', 'theme', overridden, '--format', 'json'))
        self.assertEqual(theme['target']['theme'], 'nord')
        self.assertEqual(theme['target']['presentation_preset'], SELECTOR)
        self.assertIn('class="field-sheet"', override_html)
        self.assertIn(asset, override_html)
        self.cli('series', 'preset', 'set', overridden, '--preset', SELECTOR,
                 '--use-preset-theme')
        restored = json.loads(self.cli('series', 'theme', overridden, '--format', 'json'))
        self.assertIsNone(restored['target']['theme'])
        self.assertEqual(restored['label'], 'Field Notes Paper')

        demo = self.root / 'demo'
        self.cli('init', demo, '--preset', SELECTOR)
        self.cli('demo', demo, '--lang', 'en')
        self.cli('build', demo, '--lang', 'en')
        self.cli('verify', demo, '--lang', 'en')

    def test_each_source_is_a_usable_kit_without_its_siblings(self):
        for kit_id, preset in (('field-frames', 'sheet'), ('field-marks', 'compass'),
                               ('field-ink', 'paper')):
            with self.subTest(kit=kit_id):
                shutil.copytree(EXAMPLE / 'sources' / kit_id, self.catalogue / kit_id)
                html = self.first_article(self.root / kit_id, f'{kit_id}@1.0.0/{preset}')
                self.assertEqual('class="field-sheet"' in html, kit_id == 'field-frames')
                self.assertEqual('Compass rose' in html, kit_id == 'field-marks')
                for sibling in ('field-frames', 'field-marks', 'field-ink'):
                    if sibling != kit_id:
                        self.assertNotIn(sibling, html)
                shutil.rmtree(self.catalogue)

    def test_paper_is_a_complete_typed_snapshot_with_explicit_metadata(self):
        path = EXAMPLE / 'sources/field-ink/1.0.0/themes/paper.conf'
        properties = dict(line.split(': ', 1) for line in path.read_text().splitlines()
                          if line and not line.startswith('#'))
        self.assertEqual(properties['schema'], 'lightwebpres.theme/1')
        self.assertEqual(properties['label'], 'Field Notes Paper')
        self.assertEqual(properties['family'], 'print')
        self.assertEqual(properties['source'], 'lightwebpres')
        self.assertIn('snapshot', properties['note'])
        reference = self.root / 'reference.conf'
        self.cli('theme', 'create', 'reference', '--from', 'print-oldpress',
                 '--output', reference)
        exported = dict(line.split(': ', 1) for line in reference.read_text().splitlines()
                        if line and not line.startswith('#'))
        self.assertEqual(properties.keys(), exported.keys())
        self.assertNotIn('theme', properties)
        self.assertEqual(properties['color.ink'], '#111111FF')
        self.assertIn('monospace', properties['font.text'])

    def test_documentation_capture_inputs_images_and_dimensions_are_fresh(self):
        import hashlib

        manifest = json.loads((ROOT / 'generated/documentation-captures.json').read_text())
        inputs = {'lightwebpres', 'tools/screenshot-documentation.cjs'}
        for directory in ('examples/first-article', 'examples/kits/lightwebpres-docs',
                          'examples/kit-composition'):
            inputs.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*')
                          if p.is_file() and p.name != 'README.md')
        self.assertEqual(set(manifest['inputs']), inputs)
        for name, expected in manifest['inputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected,
                             f'{name}: run node tools/screenshot-documentation.cjs')
        outputs = {'generated/appearance-choices.png': (1600, 1440),
                   'generated/identity-composition.png': (1600, 1080)}
        self.assertEqual(len(manifest['captures']), len(outputs))
        self.assertEqual({c['file'] for c in manifest['captures']}, set(outputs))
        for capture in manifest['captures']:
            data = (ROOT / capture['file']).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(data[12:16], b'IHDR')
            dimensions = (int.from_bytes(data[16:20], 'big'),
                          int.from_bytes(data[20:24], 'big'))
            self.assertEqual(dimensions, outputs[capture['file']])
            self.assertEqual(dimensions, (capture['width'], capture['height']))
            self.assertEqual(hashlib.sha256(data).hexdigest(), capture['sha256'])


if __name__ == '__main__':
    unittest.main()
