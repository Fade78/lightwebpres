"""Kicker placement is independent from its text and follows owned defaults."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / 'work' / 'tmp'
KINDS = ('cover', 'standard', 'series-nav', 'full-article', 'unit-index')


class KickerPosition(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=SCRATCH, prefix='kicker-position-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources').mkdir()
        self.env = {**os.environ, 'TMPDIR': str(SCRATCH),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'library' / 'kits'),
                    'LWP_COMMONS_DIR': str(self.root / 'library' / 'commons'),
                    'LWP_THEMES_DIR': str(self.root / 'library' / 'themes')}
        self.data = {'series_meta': {'title': 'Kicker placement', 'scroll_duration': 0},
                     'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}],
                     'chrome': {'header': 'Shared header', 'footer': 'Shared footer'}}
        self.source = ('<!-- lwp:meta -->\npage_title: Kicker placement\n---\n\n'
                       '<!-- lwp:slide -->\nslug: inherited\nkicker: Label\n'
                       '## Inherited position\nsummary: Short content.\n')
        (self.root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\npage_title: Second article\nkicker_position: before-title\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: second\nkicker: Unit override\n# Another article\n', encoding='utf-8')

    def write(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')
        (self.root / 'sources' / 'a.md').write_text(self.source, encoding='utf-8')

    def cli(self, *args):
        return run(*args, env=self.env, cwd=ROOT)

    def build(self, *args):
        self.write()
        result = self.cli('build', self.root, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return (self.root / 'public' / 'a.html').read_text(encoding='utf-8')

    def section(self, html, slug='inherited'):
        found = re.search(r'<section [^>]*id="' + re.escape(slug) + r'"[^>]*>(.*?)</section>',
                          html, re.S)
        self.assertIsNotNone(found, slug)
        return found.group(1)

    def kit(self, position=None, placement='edge'):
        root = self.root / 'templates' / 'kits' / 'kicker-test' / '1.0.0'
        (root / 'slides').mkdir(parents=True, exist_ok=True)
        (root / 'slides' / 'default.html').write_text(
            '<div class="kicker-test-frame">{{slide_header}}\n'
            '<div class="kicker-test-content">{{content}}</div>\n'
            '{{slide_footer}}</div>', encoding='utf-8')
        preset = {'label': 'Placement', 'description': 'Kicker placement fixture.',
                  'theme': 'paper', 'slide_layouts': {kind: 'default' for kind in KINDS},
                  'slide_chrome': {}, 'slide_chrome_placement': placement}
        if position is not None:
            preset['kicker_position'] = position
        manifest = {'schema': 'lightwebpres.identity-kit/1', 'id': 'kicker-test',
                    'version': '1.0.0', 'label': 'Kicker fixture',
                    'layouts': {kind: {'default': 'slides/default.html'} for kind in KINDS},
                    'themes': {'paper': 'builtin:light'}, 'presets': {'test': preset}}
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return root, manifest

    def test_default_and_each_cascade_level(self):
        self.assertNotIn('class="slide-header-region"', self.section(self.build()))
        self.kit('after-header')
        self.data['appearance'] = {'presets': ['kicker-test@1.0.0/test']}
        self.assertIn('class="slide-header-region"', self.section(self.build()))
        self.data['series_meta']['kicker_position'] = 'before-title'
        self.assertNotIn('class="slide-header-region"', self.section(self.build()))
        self.source = self.source.replace('page_title:', 'kicker_position: after-header\npage_title:')
        self.assertIn('class="slide-header-region"', self.section(self.build()))
        self.source = self.source.replace('kicker: Label', 'kicker: Label\nkicker-position: before-title')
        self.assertNotIn('class="slide-header-region"', self.section(self.build()))
        self.source = self.source.replace('kicker-position: before-title', 'kicker-position: after-header')
        section = self.section(self.build())
        self.assertEqual(section.count('class="slide-kicker"'), 1)
        self.assertLess(section.index('Shared header'), section.index('Label'))
        self.assertLess(section.index('Label'), section.index('<h2>'))

    def test_all_types_missing_header_and_absent_kicker(self):
        self.data['series_meta']['kicker_position'] = 'after-header'
        self.source = ('<!-- lwp:meta -->\npage_title: All types\n---\n\n'
                       '<!-- lwp:slide:cover -->\nslug: cover\nkicker: Cover label\n# Cover\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: inherited\nkicker: Label\n## Standard\n\n---\n\n'
                       '<!-- lwp:slide:unit-index -->\nslug: contents\nkicker: Contents label\n'
                       '## Contents\nindex-selector: $[? @.slide.slug == "cover"]\n\n---\n\n'
                       '<!-- lwp:slide:full-article -->\nslug: long\narticle: long.md\n\n---\n\n'
                       '<!-- lwp:slide:series-nav -->\nslug: navigation\n'
                       'kicker-position: after-header\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: no-header\nkicker: No header label\n'
                       'slide-header: ""\n## Header removed\n\n---\n\n'
                       '<!-- lwp:slide -->\nslug: no-kicker\n## No label\n')
        (self.root / 'sources' / 'long.md').write_text('# Long article\n\nText.\n', encoding='utf-8')
        html = self.build()
        for slug in ('cover', 'inherited', 'contents', 'long', 'no-header'):
            with self.subTest(slug=slug):
                section = self.section(html, slug)
                self.assertEqual(section.count('class="slide-kicker"'), 1)
                self.assertIn('class="slide-header-region"', section)
        self.assertNotIn('slide-chrome-header', self.section(html, 'no-header'))
        for slug in ('navigation', 'no-kicker'):
            self.assertNotIn('class="slide-kicker"', self.section(html, slug))
            self.assertNotIn('class="slide-header-region"', self.section(html, slug))

    def test_invalid_values_fail_before_any_output_even_when_overridden(self):
        original = self.source
        for scope in ('series', 'article', 'slide', 'preset'):
            for value in ('above', '', '""', 'After-header', None, False, {}):
                if scope in ('article', 'slide') and not isinstance(value, str):
                    continue
                with self.subTest(scope=scope, value=value):
                    self.data['series_meta'].pop('kicker_position', None)
                    self.data.pop('appearance', None)
                    self.source = original
                    output = self.root / f'bad-{scope}-{len(str(value))}-{type(value).__name__}'
                    if scope == 'series':
                        self.data['series_meta']['kicker_position'] = value
                        self.source = self.source.replace('kicker: Label',
                                                          'kicker: Label\nkicker-position: before-title')
                    elif scope == 'article':
                        self.source = self.source.replace('page_title:',
                                                          f'kicker_position: {value}\npage_title:')
                    elif scope == 'slide':
                        self.source = self.source.replace('kicker: Label',
                                                          f'kicker: Label\nkicker-position: {value}')
                    else:
                        kit, manifest = self.kit()
                        manifest['presets']['test']['kicker_position'] = value
                        (kit / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                        self.data['appearance'] = {'presets': ['kicker-test@1.0.0/test']}
                    self.write()
                    result = self.cli('build', self.root, '--output', output)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertRegex(result.stderr, r'kicker[-_]position')
                    self.assertFalse(output.exists())

    def test_contract_and_resolution_report_describe_the_live_cascade(self):
        self.data['series_meta']['kicker_position'] = 'after-header'
        self.source = self.source.replace('kicker: Label', 'kicker: Label\nkicker-position: before-title')
        self.write()
        contract = self.cli('contract', '--format', 'json')
        self.assertEqual(contract.returncode, 0, contract.stderr)
        draft = json.loads(contract.stdout)
        for kind in draft['types']:
            self.assertIn('kicker-position', kind['fields'])
        self.assertIn('invalid', draft['empty_rules']['kicker-position'])
        self.assertEqual(draft['value_sets']['kicker-position'], ['before-title', 'after-header'])
        report = self.cli('resolve', self.root, 'kicker-position', '--article', 'a.md', '--format', 'json')
        self.assertEqual(report.returncode, 0, report.stderr)
        site = json.loads(report.stdout)['resolution']['sites'][0]
        self.assertEqual(site['value'], 'before-title')
        self.assertEqual(site['source'], 'slide')
        self.assertEqual([link['level'] for link in site['chain']],
                         ['slide', 'article', 'series', 'preset', 'default'])
        metadata = self.cli('resolve', self.root, 'kicker_position', '--article', 'a.md', '--format', 'json')
        self.assertEqual(metadata.returncode, 0, metadata.stderr)
        self.assertEqual(json.loads(metadata.stdout)['resolution']['value'], 'after-header')

    def test_native_default_field_does_not_change_existing_markup(self):
        old = self.section(self.build())
        self.source = self.source.replace('kicker: Label', 'kicker: Label\nkicker-position: before-title')
        self.assertEqual(self.section(self.build()), old)
        lwp = load_lightwebpres_module()
        self.assertEqual(lwp.BUILTIN_STANDARD_PRESET.kicker_position, 'before-title')

    def test_body_kickers_and_field_like_text_are_not_relocated(self):
        self.data['series_meta']['kicker_position'] = 'after-header'
        self.source = self.source.replace('kicker: Label\n', '')
        self.source += ('\nBody content.\n\n'
                        '<span class="slide-kicker">Authored body label</span>\n\n'
                        'kicker-position: before-title\n')
        section = self.section(self.build())
        self.assertNotIn('class="slide-header-region"', section)
        self.assertIn('Authored body label', section)
        self.assertIn('kicker-position: before-title', section)
        self.assertLess(section.index('Body content.'), section.index('Authored body label'))

    def test_selectors_see_the_resolved_position_and_owned_source_values(self):
        self.kit('after-header')
        self.data['appearance'] = {'presets': ['kicker-test@1.0.0/test']}
        self.source += ('\n---\n\n<!-- lwp:slide -->\nslug: local\nkicker: Local label\n'
                        'kicker-position: before-title\n## Local\n\n---\n\n'
                        '<!-- lwp:slide:unit-index -->\nslug: selected\n## Selected\n'
                        'index-selector: $[? @.effective.kicker_position == "after-header"]\n')
        html = self.build()
        contents = self.section(html, 'selected')
        self.assertIn('data-lwp-index-target="inherited"', contents)
        self.assertNotIn('data-lwp-index-target="local"', contents)
        self.data['series_meta']['kicker_position'] = 'before-title'
        self.source = self.source.replace('page_title:', 'kicker_position: after-header\npage_title:')
        self.source = self.source.replace('@.effective.kicker_position == "after-header"',
                                          '@.general.kicker_position == "before-title"')
        contents = self.section(self.build(), 'selected')
        self.assertIn('data-lwp-index-target="inherited"', contents)
        self.assertIn('data-lwp-index-target="local"', contents)

    def test_browser_placement_print_and_runtime_presets(self):
        self.kit('after-header')
        self.data['appearance'] = {'presets': ['builtin/standard', 'kicker-test@1.0.0/test']}
        self.source += ('\n---\n\n<!-- lwp:slide -->\nslug: pinned\nkicker: Fixed label\n'
                        'kicker-position: before-title\n## Pinned to title\nsummary: Content.\n'
                        '\n---\n\n<!-- lwp:slide -->\nslug: no-header\nkicker: Standalone label\n'
                        'slide-header: ""\n## No header\nsummary: Content.\n'
                        '\n---\n\n<!-- lwp:slide:cover -->\nslug: cover\nkicker: Cover label\n'
                        '# Cover title\nsummary: A short summary.\n'
                        '\n---\n\n<!-- lwp:slide:unit-index -->\nslug: contents\n'
                        'kicker: Contents label\n## Contents title\nindex-selector: type:cover\n'
                        '\n---\n\n<!-- lwp:slide:full-article -->\nslug: long\narticle: long.md\n')
        (self.root / 'sources' / 'long.md').write_text('# Long title\n\nShort text.\n', encoding='utf-8')
        self.build()
        for placement in ('edge', 'content'):
            _kit, manifest = self.kit('after-header', placement)
            (_kit / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            output = self.root / placement
            result = self.cli('build', self.root, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            combined = self.root / (placement + '-combined')
            result = self.cli('build', self.root, '--output', combined,
                              '--single-html', 'series.html')
            self.assertEqual(result.returncode, 0, result.stderr)
            try:
                browser = subprocess.run(
                    ['node', str(ROOT / 'tests' / 'kicker_position_e2e.cjs'),
                     (output / 'a.html').as_uri(), (combined / 'series.html').as_uri(), placement],
                    cwd=ROOT, env=self.env, capture_output=True, text=True, timeout=180)
            except FileNotFoundError:
                self.skipTest('Node unavailable in the supplied environment')
            if browser.returncode == 77:
                self.skipTest(browser.stderr.strip())
            self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
            for name in ('chromium', 'firefox'):
                self.assertIn(name + ': kicker placement checks passed', browser.stdout)
