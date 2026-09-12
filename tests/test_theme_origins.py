"""Uniform theme slugs and loader provenance across catalogue consumers."""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest import mock

if __package__:
    from .test_lightwebpres import EXECUTABLE, load_lightwebpres_module, run
else:
    from test_lightwebpres import EXECUTABLE, load_lightwebpres_module, run


class ThemeOrigins(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lwp = load_lightwebpres_module()
        self.env = {'LWP_THEMES_DIR': str(self.root / 'user-themes'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons')}
        environment = mock.patch.dict(os.environ, self.env)
        environment.start()
        self.addCleanup(environment.stop)

    def theme(self, directory, slug, label):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (slug + '.conf')
        path.write_text(self.lwp.theme_file_text(slug,
            {'label': label, 'family': 'desk', 'source': 'palette-credit'},
            self.lwp.resolve_theme_properties(self.lwp.theme_property_layer('nord'))), encoding='utf-8')
        return path

    def series(self):
        path = self.root / 'series'
        result = run('init', str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        return path

    def test_every_shipped_theme_has_a_bare_slug_and_the_same_origin(self):
        catalog = self.lwp.ThemeCatalog()
        self.assertEqual(catalog.theme_ids[0], 'light')
        self.assertTrue(all(':' not in slug for slug in catalog.theme_ids))
        for slug in catalog.theme_ids:
            self.assertEqual(catalog.resolve(slug).origin, 'builtin')
            self.assertEqual(catalog.layer(slug), catalog.layer('builtin:' + slug))
        listed = run('theme', 'list')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn('  light  [light/neutral]  desk  origin=builtin', listed.stdout)
        self.assertIn('  nord  [light/neutral]  ported  origin=builtin', listed.stdout)
        self.assertNotIn('  builtin:light ', listed.stdout)

    def test_precedence_is_enforced_by_the_catalogue_not_call_order(self):
        catalog = self.lwp.ThemeCatalog()
        props = self.lwp.resolve_theme_properties()
        for origin in ('series', 'user', 'installed'):
            catalog.add_local('light', {'label': origin}, props,
                              self.root / origin / 'light.conf', origin, origin)
        self.assertEqual(catalog.resolve('light').origin, 'series')
        self.assertEqual(catalog.entry('light')['label'], 'series')
        self.assertEqual(catalog.entry('builtin:light')['label'], 'Light')
        self.assertEqual(catalog.layer('builtin:light')['page.bg'], 'page')

    def test_origin_filter_uses_effective_entries_and_never_palette_credits(self):
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'light', 'User Light')
        listed = run('theme', 'list', '--origin', 'user')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn('User Light', listed.stdout)
        self.assertIn('origin=user', listed.stdout)
        self.assertNotIn('  nord ', listed.stdout)
        builtins = run('theme', 'list', '--origin', 'builtin')
        self.assertEqual(builtins.returncode, 0, builtins.stderr)
        self.assertNotRegex(builtins.stdout, r'(?m)^  light  \[')
        invalid = run('theme', 'list', '--origin', 'palette-credit')
        self.assertEqual(invalid.returncode, 1)
        self.assertIn('Unknown --origin', invalid.stderr)
        report = json.loads(run('theme', 'show', 'light', '--format', 'json').stdout)
        self.assertEqual(report['origin'], 'user')
        self.assertEqual(report['source'], 'palette-credit')

    def test_series_override_and_forced_builtin_have_distinct_origins(self):
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'light', 'User Light')
        series = self.series()
        self.theme(series / 'templates/themes', 'light', 'Series Light')
        for selector, origin, label in [('light', 'series', 'Series Light'),
                                         ('builtin:light', 'builtin', 'Light')]:
            chosen = run('series', 'theme', 'set', str(series), '--theme', selector)
            self.assertEqual(chosen.returncode, 0, chosen.stderr)
            report = run('series', 'theme', str(series), '--format', 'json')
            self.assertEqual(report.returncode, 0, report.stderr)
            data = json.loads(report.stdout)
            self.assertEqual((data['origin'], data['label']), (origin, label))

    def test_installed_user_and_series_layers_resolve_the_same_slug(self):
        installation = self.root / 'installation'
        installation.mkdir()
        shutil.copy2(EXECUTABLE, installation / 'lightwebpres')
        self.theme(installation / 'themes', 'light', 'Installed Light')
        import subprocess
        import sys

        def inspect():
            result = subprocess.run([sys.executable, str(installation / 'lightwebpres'),
                                     'theme', 'show', 'light', '--format', 'json'],
                                    env={**os.environ, **self.env}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        self.assertEqual(inspect()['origin'], 'installed')
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'light', 'User Light')
        self.assertEqual(inspect()['origin'], 'user')

    def test_runtime_deduplicates_bare_and_forced_references_to_one_resource(self):
        series = self.series()
        for selector in ('light', 'builtin:light', 'nord'):
            chosen = run('series', 'theme', 'set', str(series), '--theme', selector)
            self.assertEqual(chosen.returncode, 0, chosen.stderr)
            result = run('build', str(series), '--themes', 'all,builtin:light,builtin:nord')
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (series / 'public/index.html').read_text()
            runtime = json.loads(re.search(
                r'<script id="lwp-theme-data" type="application/json">(.*?)</script>', html, re.S)[1])
            self.assertEqual(len([theme for theme in runtime['themes'] if theme['label'] == 'Light']), 1)
            self.assertEqual(len([theme for theme in runtime['themes'] if theme['label'] == 'Nord']), 1)
            self.assertTrue(all(theme['origin'] == 'builtin' for theme in runtime['themes']))

    def test_commons_theme_origin_is_not_its_descriptor_origin(self):
        series = self.series()
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'light', 'User Light')
        descriptors = series / 'templates/commons/presets'
        descriptors.mkdir(parents=True)
        (descriptors / 'paper.json').write_text(json.dumps({
            'schema': 'lightwebpres.commons-preset/1', 'id': 'paper', 'label': 'Paper',
            'description': 'Series descriptor using a user theme', 'theme': 'light'}))
        data = json.loads((series / 'series.json').read_text())
        data.setdefault('series_meta', {})['presentation_preset'] = 'commons/paper'
        (series / 'series.json').write_text(json.dumps(data))
        report = run('series', 'theme', str(series), '--format', 'json')
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)['origin'], 'user')
        self.assertEqual(json.loads(report.stdout)['source'], 'palette-credit')

    def test_native_vendor_is_a_noop_for_bare_or_forced_selection(self):
        series = self.series()
        for selector in ('light', 'builtin:light'):
            result = run('theme', 'vendor', str(series), '--themes', selector)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((series / 'templates/themes').exists())
        local = self.theme(Path(self.env['LWP_THEMES_DIR']), 'light', 'User Light')
        result = run('theme', 'vendor', str(series), '--themes', 'light')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((series / 'templates/themes/light.conf').read_bytes(), local.read_bytes())

    def test_implicit_runtime_default_does_not_duplicate_native_light(self):
        data = self.lwp.build_theme_runtime('all', None)
        native = [theme for theme in data['themes'] if theme.get('identity') == 'builtin']
        self.assertEqual([theme['slug'] for theme in native], ['default'])

    def test_vendor_refuses_two_origins_for_one_filename_before_any_write(self):
        series = self.series()
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'nord', 'User Nord')
        for force in ((), ('--force',)):
            result = run('theme', 'vendor', str(series), '--themes', 'dracula,nord,builtin:nord', *force)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertFalse((series / 'templates/themes').exists())

    def test_vendor_cannot_replace_a_selected_series_resource_with_another_origin(self):
        series = self.series()
        local = self.theme(series / 'templates/themes', 'nord', 'Series Nord')
        original = local.read_bytes()
        result = run('theme', 'vendor', str(series), '--themes', 'dracula,nord,builtin:nord', '--force')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(local.read_bytes(), original)
        self.assertEqual([path.name for path in local.parent.iterdir()], ['nord.conf'])

    def test_standalone_scaffold_parser_and_report_share_the_full_catalogue(self):
        for reference in ('light', 'builtin:light', 'nord', 'builtin:nord'):
            with self.subTest(reference=reference):
                text = self.lwp.build_settings_scaffold(reference)
                theme, pins = self.lwp.parse_settings_text(text)
                self.assertEqual(theme, reference)
                self.assertEqual(pins, {})
                report = self.lwp.theme_info_report('series', reference, None,
                                                    [self.lwp.theme_property_layer(reference)])
                self.assertEqual(report['origin'], 'builtin')
                self.assertEqual(report['facets']['family'], 'desk' if 'light' in reference else 'ported')

    def test_property_only_runtime_does_not_invent_loader_provenance(self):
        data = self.lwp.build_theme_runtime('nord', None,
            preset_props={'color.ink': '#123456'}, preset_selector='example/paper')
        self.assertEqual(data['primary'], 'presentation:example/paper')
        self.assertIsNone(data['themes'][0]['origin'])
        self.assertEqual(data['themes'][1]['origin'], 'builtin')

    def test_a_known_theme_wins_over_a_same_named_directory(self):
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'mine', 'User palette')
        for slug in ('light', 'nord', 'mine'):
            (self.root / slug).mkdir()
            report = run('theme', 'show', slug, '--format', 'json', cwd=self.root)
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertEqual(json.loads(report.stdout)['target']['theme'], slug)
        (self.root / 'not-a-theme').mkdir()
        rejected = run('theme', 'show', 'not-a-theme', cwd=self.root)
        self.assertEqual(rejected.returncode, 1)
        self.assertIn('series theme', rejected.stderr)

    def test_commons_can_force_any_builtin_without_vendoring_the_shadow(self):
        self.theme(Path(self.env['LWP_THEMES_DIR']), 'nord', 'User Nord')
        descriptors = Path(self.env['LWP_COMMONS_DIR']) / 'presets'
        descriptors.mkdir(parents=True)
        (descriptors / 'forced.json').write_text(json.dumps({
            'schema': 'lightwebpres.commons-preset/1', 'id': 'forced', 'label': 'Forced',
            'description': 'Built-in Nord', 'theme': 'builtin:nord'}))
        series = self.root / 'forced-series'
        result = run('init', str(series), '--preset', 'commons/forced')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((series / 'templates/themes').exists())
        report = run('series', 'theme', str(series), '--format', 'json')
        self.assertEqual(report.returncode, 0, report.stderr)
        data = json.loads(report.stdout)
        self.assertEqual((data['label'], data['origin']), ('Nord', 'builtin'))
        self.assertEqual(run('build', str(series)).returncode, 0)
