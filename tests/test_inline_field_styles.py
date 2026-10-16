"""Typed inline roles for native slide titles and summaries, not body CSS."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run

ROOT = Path(__file__).resolve().parents[1]
SURFACES = ('title1', 'title2', 'summary', 'cover.summary')
ROLES = ('strong', 'em', 'code', 'link')


class InlineFieldStyles(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix='inline-styles-', dir=scratch)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'sources').mkdir()
        (self.root / 'templates' / 'themes').mkdir(parents=True)
        self.env = {**os.environ, 'TMPDIR': str(scratch),
                    'LWP_THEMES_DIR': str(self.root / 'library' / 'themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'library' / 'commons'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'library' / 'kits')}
        self.data = {'series_meta': {'title': 'Inline style roles', 'scroll_duration': 0},
                     'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}]}
        text = '**Strong** *Emphasis* `code` [Link](https://example.org)'
        self.source = ('<!-- lwp:meta -->\npage_title: Inline styles\n---\n\n'
                       '<!-- lwp:slide:cover -->\nslug: cover\n# ' + text + '\nsummary: ' + text + '\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: detail\n## ' + text + '\nsummary: ' + text + '\n'
                       'fact-label: Body is independent\n\nBody **strong**, *emphasis* and `code`.\n\n---\n\n'
                       '<!-- lwp:slide:unit-index -->\nslug: contents\n## **Contents**\nsummary: *Choose* a card.\n')
        (self.root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\npage_title: Other\n---\n\n<!-- lwp:slide -->\nslug: second\n'
            '## **Second** title\nsummary: A **summary**.\n', encoding='utf-8')

    def cli(self, *args):
        return run(*args, cwd=ROOT, env=self.env)

    def write(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')
        (self.root / 'sources' / 'a.md').write_text(self.source, encoding='utf-8')

    def build(self, *args):
        self.write()
        result = self.cli('build', self.root, '--lang', 'en', *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_live_registry_exposes_each_inline_role_and_typed_axes(self):
        lwp = load_lightwebpres_module()
        properties = {prop['key'] for prop in lwp.theme_registry_contract()['properties']}
        for surface in SURFACES:
            for role in ROLES:
                for axis in ('fg', 'bg', 'font', 'size', 'weight', 'style', 'decoration',
                             'decoration-color', 'pad-inline', 'pad-block', 'radius',
                             'shadow.fg', 'shadow.blur', 'shadow.dx', 'shadow.dy'):
                    key = f'{surface}.{role}.{axis}'
                    self.assertIn(key, set(lwp.PROPERTY_REGISTRY))
                    self.assertIn(key, properties)

    def test_settings_article_pins_and_resolution_share_the_live_registry(self):
        (self.root / 'templates' / 'settings.conf').write_text(
            'title2.strong.fg: #123456\nsummary.em.style: normal\nsummary.strong.bg: #fff0aa\n', encoding='utf-8')
        self.source = self.source.replace('page_title:', 'style.title2.strong.fg: #654321\npage_title:')
        self.build()
        result = self.cli('resolve', self.root, 'title2.strong.fg', '--article', 'a.md', '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        resolution = json.loads(result.stdout)['resolution']
        self.assertEqual(resolution['value'], '#654321FF')
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('--title2-strong-fg: #654321FF', html)
        self.assertIn('--summary-em-style: normal', html)

    def test_invalid_inline_options_fail_before_output(self):
        for number, (key, value) in enumerate((('summary.strong.fg', 'not-a-colour'),
                ('title2.em.style', 'oblique'), ('title1.code.font', 'Arial'),
                ('summary.link.decoration', 'blink'))):
            with self.subTest(key=key):
                (self.root / 'templates' / 'settings.conf').write_text(f'{key}: {value}\n', encoding='utf-8')
                self.write()
                output = self.root / f'bad-{number}'
                result = self.cli('build', self.root, '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)
                self.assertFalse(output.exists())

    def test_new_roles_do_not_invalidate_previous_complete_theme_snapshots(self):
        self.data['appearance'] = {'presets': ['lightwebpres-docs@0.1.0/docs']}
        import shutil
        shutil.copytree(ROOT / 'examples' / 'kits' / 'lightwebpres-docs',
                        self.root / 'templates' / 'kits' / 'lightwebpres-docs')
        self.build()

    def test_new_role_reference_chains_stay_bounded(self):
        lwp = load_lightwebpres_module()
        resolved = lwp.resolve_theme_properties()
        self.assertEqual(resolved['title1.strong.decoration-color'], resolved['title1.fg'])
        for slug in lwp.THEMES:
            values = lwp.resolve_theme_properties(lwp.theme_property_layer(slug))
            self.assertEqual(values['summary.strong.font'], values['page.font'], slug)
            self.assertEqual(values['cover.summary.em.fg'], values['cover.summary.fg'], slug)

    def theme(self, name, colour):
        lwp = load_lightwebpres_module()
        pins = {f'{surface}.{role}.fg': colour for surface in SURFACES for role in ROLES}
        pins.update({'summary.strong.bg': '#fff0aa', 'title2.strong.weight': 'normal',
                     'title2.strong.style': 'italic', 'summary.em.style': 'normal',
                     'summary.link.decoration': 'line-through', 'title2.code.size': '0.7em',
                     'summary.strong.pad-inline': '4px', 'summary.strong.radius': '3px'})
        meta = dict(lwp._native_theme_catalog_entry(), label='Inline ' + name)
        text = lwp.theme_file_text(name, meta, lwp.resolve_theme_properties(pins))
        (self.root / 'templates' / 'themes' / (name + '.conf')).write_text(text, encoding='utf-8')

    def test_real_browsers_apply_roles_theme_switching_zoom_and_print(self):
        self.theme('inline-a', '#123456')
        self.theme('inline-b', '#654321')
        import shutil
        shutil.copytree(ROOT / 'examples' / 'kits' / 'lightwebpres-docs',
                        self.root / 'templates' / 'kits' / 'lightwebpres-docs')
        self.data['appearance'] = {'themes': ['inline-a', 'inline-b'],
                                   'presets': ['builtin/standard', 'lightwebpres-docs@0.1.0/docs']}
        self.source = self.source.replace('page_title:', 'style.title2.link.fg: #abcdef\npage_title:')
        self.build()
        self.build('--single-html', 'all.html', '--inline-images', '--output', self.root / 'bundle')
        result = subprocess.run(['node', str(ROOT / 'tests' / 'inline_field_styles_e2e.cjs'),
                                 (self.root / 'public' / 'a.html').as_uri(),
                                 (self.root / 'bundle' / 'all.html').as_uri()],
                                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=180)
        if result.returncode == 77:
            self.skipTest('Playwright unavailable in supplied environment')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('inline field styles passed', result.stdout)
