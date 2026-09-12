"""Identity boundaries, native resource references and Commons dependencies."""

import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

if __package__:
    from . import test_lightwebpres as fixtures
else:
    import test_lightwebpres as fixtures


class IdentityKits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = fixtures.load_lightwebpres_module()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = mock.patch.dict(os.environ, {
            'LWP_IDENTITY_KITS_DIR': str(self.root / 'library' / 'kits'),
            'LWP_COMMONS_DIR': str(self.root / 'library' / 'commons'),
            'LWP_THEMES_DIR': str(self.root / 'library' / 'themes'),
        })
        environment.start()
        self.addCleanup(environment.stop)

    def _kit(self, **changes):
        manifest = {
            'schema': 'lightwebpres.identity-kit/1',
            'id': 'studio', 'version': '1.0.0', 'label': 'Studio',
            'layouts': {
                kind: {'default': 'builtin:standard'}
                for kind in self.lwp._PRESENTATION_SLIDE_TYPES
            },
            'themes': {'paper': 'builtin:light'},
            'presets': {
                'brief': {
                    'label': 'Brief', 'description': 'A studio brief.',
                    'theme': 'paper',
                    'slide_layouts': {
                        kind: 'default' for kind in self.lwp._PRESENTATION_SLIDE_TYPES
                    },
                    'slide_chrome': {'all': {'footer': 'Studio footer'}},
                },
            },
        }
        manifest['layouts']['index'] = 'builtin:standard'
        manifest.update(changes)
        root = (self.root / 'templates' / 'kits' / manifest['id']
                / manifest['version'])
        root.mkdir(parents=True, exist_ok=True)
        path = root / 'manifest.json'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        return root, manifest

    def _commons(self, root=None, **changes):
        descriptor = {
            'schema': 'lightwebpres.commons-preset/1', 'id': 'night',
            'label': 'Night', 'description': 'Native slides with a dark theme.',
            'theme': 'dracula',
        }
        descriptor.update(changes)
        root = root or self.root / 'templates' / 'commons'
        path = root / 'presets' / f'{descriptor["id"]}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(descriptor), encoding='utf-8')
        return path

    def test_native_selector_is_explicit_and_catalogued_once(self):
        catalog = self.lwp.load_identity_catalog(self.root / 'templates')
        preset = catalog.resolve_preset(None, 'test')
        self.assertIs(preset, catalog.resolve_preset('builtin/standard', 'test'))
        self.assertEqual(preset.selector, 'builtin/standard')
        self.assertEqual(preset.identity_kit.id, 'builtin')
        self.assertEqual(preset.resource_collection, 'builtin')
        self.assertEqual(preset.theme_meta['label'], 'Light')
        self.assertEqual(list(preset.identity_kit.themes), ['light'])
        self.assertEqual(self.lwp.resolve_theme_properties(preset.theme_props),
                         self.lwp.resolve_theme_properties())
        self.assertEqual([p.selector for p in catalog.presets()].count(preset.selector), 1)
        listed = fixtures.run('preset', 'list', '--format', 'json')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        selectors = [p['selector'] for p in json.loads(listed.stdout)['presets']]
        self.assertEqual(selectors.count('builtin/standard'), 1)

    def test_native_theme_has_a_canonical_catalogue_id_without_flattening(self):
        catalog = self.lwp.ThemeCatalog()
        self.assertIn('light', catalog.theme_ids)
        self.assertNotIn('builtin:light', catalog.theme_ids)
        self.assertTrue(catalog.has('builtin:light'))
        self.assertEqual(catalog.entry('builtin:light')['label'], 'Light')
        self.assertEqual(catalog.entry('builtin:light')['source'], 'builtin')
        self.assertEqual(
            catalog.layer('builtin:light'),
            self.lwp.BUILTIN_STANDARD_PRESET.theme_props)
        self.assertEqual(
            self.lwp.resolve_theme_properties(catalog.layer('builtin:light'))['page.bg'],
            self.lwp.resolve_theme_properties()['page.bg'])
        self.assertEqual(catalog.layer('builtin:light')['page.bg'], 'page')
        self.assertEqual(
            self.lwp.theme_property_layer('builtin:light')['page.bg'],
            'page')
        self.assertEqual(
            self.lwp.theme_property_layer('builtin:nord'),
            self.lwp.theme_property_layer('nord'))
        listed = fixtures.run('theme', 'list')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn('light  [light/neutral]  desk  origin=builtin', listed.stdout)
        shown = fixtures.run('theme', 'show', 'builtin:light', '--format', 'json')
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(json.loads(shown.stdout)['target']['theme'], 'builtin:light')

    def test_local_light_snapshot_shadows_bare_but_not_forced_native_light(self):
        themes = self.root / 'library' / 'themes'
        themes.mkdir(parents=True)
        local = themes / 'light.conf'
        local.write_text(self.lwp.theme_file_text(
            'light', {'label': 'Local Light', 'family': 'desk'},
            self.lwp.resolve_theme_properties(
                self.lwp.theme_property_layer('nord'))), encoding='utf-8')
        catalog = self.lwp.load_theme_catalog()
        self.assertEqual(catalog.theme_ids[0], 'light')
        self.assertIn('light', catalog.theme_ids)
        self.assertEqual(catalog.entry('light')['label'], 'Local Light')
        self.assertEqual(catalog.entry('builtin:light')['label'], 'Light')
        self.assertNotEqual(catalog.layer('light')['color.page'],
                            catalog.layer('builtin:light')['color.page'])
        shown = fixtures.run('theme', 'show', 'builtin:light', '--format', 'json')
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(json.loads(shown.stdout)['label'], 'Light')

    def test_selector_grammar_has_no_native_aliases(self):
        for value in ('default', 'builtin', 'builtin/default',
                      'builtin@1.0.0/standard', 'commons@1.0.0/brief',
                      'commons/a/b', 'commons/', 'studio/brief',
                      'studio@1.0.0-beta.1/brief', 'studio@1.0.0+build.1/brief'):
            with self.subTest(value=value), self.assertRaises(self.lwp.PropertyError):
                self.lwp.parse_presentation_preset_selector(value, 'test')
        result = fixtures.run('preset', 'show', 'default')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('builtin/standard', result.stderr)

    def test_help_names_current_identity_catalogues_and_native_selection(self):
        result = fixtures.run('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        help_text = ' '.join(result.stdout.split())
        environment = result.stdout.split('ENVIRONMENT VARIABLES', 1)[1].split(
            'SERIES DIRECTORY', 1)[0]
        for variable in ('LWP_IDENTITY_KITS_DIR', 'LWP_COMMONS_DIR'):
            self.assertIn(variable, environment)
        for text in ('<platform-data>/lightwebpres/kits',
                     '<platform-data>/lightwebpres/commons'):
            self.assertIn(text, environment)
        for text in ('templates/kits/<id>/<version>',
                     'templates/commons/presets/<id>.json',
                     'lightwebpres.commons-preset/1',
                     'Native Standard (builtin/standard)'):
            self.assertIn(text, help_text)
        for text in ('LWP_PRESENTATION_PACKAGES_DIR', 'presentation package',
                     'presentation-package', 'virtual default',
                     'layouts/<id>/<version>'):
            self.assertNotIn(text, help_text)

    def test_preset_inspection_reports_preferred_preset_and_loader_scope(self):
        root, manifest = self._kit(default_preset='second')
        manifest['presets']['second'] = copy.deepcopy(manifest['presets']['brief'])
        manifest['presets']['second']['label'] = 'Second'
        manifest['themes']['paper'] = 'themes/paper.conf'
        (root / 'themes').mkdir()
        (root / 'themes' / 'paper.conf').write_text(self.lwp.theme_file_text(
            'paper', {'label': 'Paper', 'family': 'desk', 'source': 'installed'},
            self.lwp.resolve_theme_properties()), encoding='utf-8')
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        result = fixtures.run('preset', 'show', 'studio@1.0.0/brief',
                              '--format', 'json', env={
                                  'LWP_IDENTITY_KITS_DIR': str(root.parent.parent)})
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['schema'], 'lightwebpres.presentation-preset/3')
        self.assertFalse(report['native_renderer'])
        self.assertNotIn('default', report)
        self.assertEqual(report['selector'], 'studio@1.0.0/brief')
        self.assertEqual(report['identity']['default_preset'], 'second')
        self.assertEqual(report['identity']['label'], 'Studio')
        self.assertEqual(report['scope'], 'user')
        self.assertEqual(report['identity']['scope'], 'user')

    def test_native_fragments_keep_kit_chrome_and_scope(self):
        root, _manifest = self._kit()
        identity_kit = self.lwp._load_identity_kit(root, 'series')
        preset = identity_kit.presets['brief']
        self.assertFalse(preset.default)
        self.assertEqual(identity_kit.label, 'Studio')
        self.assertEqual(identity_kit.default_preset, 'brief')
        self.assertEqual(preset.scope, 'series')
        self.assertEqual(preset.resource_collection, 'kit')
        self.assertEqual(identity_kit.themes['paper']['source_identity'], 'builtin')
        self.assertEqual(identity_kit.themes['paper']['scope'], 'builtin')
        self.assertEqual(identity_kit.themes['paper']['meta']['label'], 'Light')
        self.assertEqual(identity_kit.index_layout, '{{content}}')
        self.assertEqual(identity_kit.dependency_paths, (root / 'manifest.json',))
        series = fixtures.scaffold(self.root, fixtures.IdentityKitFixtures._article())
        data_path = series / 'series.json'
        data = json.loads(data_path.read_text(encoding='utf-8'))
        data['series_meta'] = {'presentation_preset': preset.selector}
        data_path.write_text(json.dumps(data), encoding='utf-8')
        built = fixtures.run('build', str(series), '--no-essential-theme')
        self.assertEqual(built.returncode, 0, built.stderr)
        html = (series / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertIn('Studio footer', html)
        self.assertIn('class="lwp-presentation--studio"', html)

    def test_kit_label_default_preset_and_reserved_ids_are_validated(self):
        for changes in ({'label': ''}, {'label': None}, {'label': '  '},
                        {'default_preset': 'missing'}, {'default_preset': None},
                        {'default_preset': 'builtin/standard'},
                        {'id': 'builtin'}, {'id': 'commons'},
                        {'schema': 'lightwebpres.presentation-package/1'}):
            with self.subTest(changes=changes):
                root, _ = self._kit(**changes)
                with self.assertRaises(self.lwp.PropertyError):
                    self.lwp._load_identity_kit(root, 'series')
        root, manifest = self._kit()
        second = copy.deepcopy(manifest['presets']['brief'])
        manifest['presets']['second'] = second
        for declared in (None, 'second'):
            if declared is not None:
                manifest['default_preset'] = declared
            (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            identity_kit = self.lwp._load_identity_kit(root, 'series')
            self.assertEqual(identity_kit.default_preset, declared or 'brief')

    def test_resource_origins_cannot_be_declared(self):
        for key in ('origin', 'scope', 'resource_collection', 'extends',
                    'provenance', 'filiation', 'trust'):
            with self.subTest(key=key):
                root, _ = self._kit(**{key: 'builtin'})
                with self.assertRaisesRegex(self.lwp.PropertyError, 'unknown manifest key'):
                        self.lwp._load_identity_kit(root, 'series')
                path = self._commons(**{key: 'builtin'})
                with self.assertRaisesRegex(self.lwp.PropertyError, 'unknown Commons preset key'):
                    self.lwp._load_commons_preset(path, 'user', self.lwp.ThemeCatalog())

    def test_kits_reject_foreign_resource_references(self):
        for reference in ('commons:dracula', 'other:paper', 'builtin:dracula',
                          'other@1.0.0:paper'):
            for field in ('theme', 'slide', 'index'):
                with self.subTest(reference=reference, field=field):
                    root, manifest = self._kit()
                    if field == 'theme':
                        manifest['themes']['paper'] = reference
                    elif field == 'slide':
                        manifest['layouts']['standard']['default'] = reference
                    else:
                        manifest['layouts']['index'] = reference
                    (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                    with self.assertRaises(self.lwp.PropertyError):
                        self.lwp._load_identity_kit(root, 'series')

    def test_commons_identity_scope_and_dependencies_are_independent(self):
        path = self._commons()
        catalog = self.lwp.load_identity_catalog(self.root / 'templates')
        preset = catalog.resolve_preset('commons/night', 'test')
        self.assertIs(preset.identity_kit, self.lwp.BUILTIN_IDENTITY_KIT)
        self.assertTrue(preset.default)
        self.assertEqual(preset.resource_collection, 'commons')
        self.assertEqual(preset.scope, 'series')
        self.assertEqual(preset.dependency_paths, (path,))
        self.assertEqual(preset.identity_kit.dependency_paths, ())
        self.assertEqual(preset.identity_kit.digest, '')
        self.assertTrue(preset.digest)
        self.assertEqual(preset.slide_chrome, {})
        self.assertIsNone(preset.starter)
        candidates = self.lwp._presentation_runtime_presets(catalog, preset, None, 'test')
        self.assertEqual([p.selector for p in candidates],
                         ['commons/night', 'builtin/standard'])

    def test_public_native_renderer_does_not_mean_initial_selection(self):
        self._commons(root=self.root / 'library' / 'commons')
        listed = fixtures.run('preset', 'list', '--format', 'json')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        listing = json.loads(listed.stdout)
        self.assertEqual(listing['schema'], 'lightwebpres.preset-list/3')
        reports = {report['selector']: report for report in listing['presets']}
        for selector in ('builtin/standard', 'commons/night'):
            shown = fixtures.run('preset', 'show', selector, '--format', 'json')
            self.assertEqual(shown.returncode, 0, shown.stderr)
            report = json.loads(shown.stdout)
            self.assertEqual(report, reports[selector])
            self.assertEqual(report['schema'], 'lightwebpres.presentation-preset/3')
            self.assertIs(report['native_renderer'], True)
            self.assertNotIn('default', report)
        self.assertNotEqual(reports['commons/night']['id'],
                            reports['commons/night']['identity']['default_preset'])

    def test_commons_theme_is_not_dropped_by_native_renderer_flag(self):
        self._commons()
        templates = self.root / 'templates'
        catalog = self.lwp.load_identity_catalog(templates)
        preset = catalog.resolve_preset('commons/night', 'test')
        layers, _ = self.lwp.series_style_context(templates, preset_theme=preset.theme_props)
        expected = self.lwp.resolve_theme_properties(preset.theme_props)
        self.assertEqual(self.lwp.resolve_theme_properties(*layers), expected)
        self.assertNotEqual(expected, self.lwp.resolve_theme_properties())
        (templates / 'settings.conf').write_text('color.page: #123456FF\n', encoding='utf-8')
        layers, _ = self.lwp.series_style_context(templates, preset_theme=preset.theme_props)
        resolved = self.lwp.resolve_theme_properties(*layers)
        self.assertEqual(resolved['color.page'], '#123456FF')
        self.assertEqual(resolved['page.bg'], '#123456FF')
        self.assertEqual(resolved['color.ink'], expected['color.ink'])
        (templates / 'settings.conf').write_text('theme: nord\n', encoding='utf-8')
        layers, _ = self.lwp.series_style_context(templates, preset_theme=preset.theme_props)
        self.assertEqual(self.lwp.resolve_theme_properties(*layers),
                         self.lwp.resolve_theme_properties(self.lwp.theme_property_layer('nord')))

    def test_native_standard_keeps_registry_references_for_author_pins(self):
        templates = self.root / 'templates'
        templates.mkdir()
        (templates / 'settings.conf').write_text('color.page: #123456FF\n', encoding='utf-8')
        preset = self.lwp.BUILTIN_STANDARD_PRESET
        layers, _ = self.lwp.series_style_context(templates, preset_theme=preset.theme_props)
        resolved = self.lwp.resolve_theme_properties(*layers)
        self.assertEqual(resolved['color.page'], '#123456FF')
        self.assertEqual(resolved['page.bg'], '#123456FF')

    def test_commons_descriptor_and_theme_changes_invalidate_digest(self):
        path = self._commons(theme='brand')
        themes = self.root / 'templates' / 'themes'
        themes.mkdir(parents=True)
        theme_path = themes / 'brand.conf'
        props = self.lwp.resolve_theme_properties(self.lwp.theme_property_layer('dracula'))
        theme_path.write_text(self.lwp.theme_file_text(
            'brand', {'label': 'Brand', 'family': 'desk',
                      'source': 'palette-credit', 'note': 'Palette note.'},
            props), encoding='utf-8')
        before = self.lwp.load_identity_catalog(self.root / 'templates').resolve_preset('commons/night', 'test')
        self.assertEqual(before.dependency_paths, (path, theme_path))
        self.assertEqual(before.theme_meta['source'], 'palette-credit')
        self.assertEqual(before.theme_meta['note'], 'Palette note.')
        report = self.lwp.theme_info_report(
            'series', None, None, [before.theme_props],
            presentation_preset=before)
        self.assertEqual(report['source'], 'palette-credit')
        self.assertEqual(report['note'], 'Palette note.')
        props['color.page'] = '#123456FF'
        theme_path.write_text(self.lwp.theme_file_text(
            'brand', {'label': 'Brand', 'family': 'desk'}, props), encoding='utf-8')
        after = self.lwp.load_identity_catalog(self.root / 'templates').resolve_preset('commons/night', 'test')
        self.assertNotEqual(before.digest, after.digest)
        self.assertEqual(after.theme_props['color.page'], '#123456FF')
        self._commons(theme='brand', description='Changed description.')
        renamed = self.lwp.load_identity_catalog(self.root / 'templates').resolve_preset('commons/night', 'test')
        self.assertNotEqual(after.digest, renamed.digest)
        self.assertEqual(after.identity_kit.digest, renamed.identity_kit.digest)

    def test_commons_builtin_light_and_foreign_theme_rejection(self):
        path = self._commons(theme='builtin:light')
        preset = self.lwp._load_commons_preset(path, 'installed', self.lwp.ThemeCatalog())
        self.assertEqual(self.lwp.resolve_theme_properties(preset.theme_props),
                         self.lwp.resolve_theme_properties())
        self.assertEqual(preset.theme_meta['label'], 'Light')
        for theme in ('builtin:missing', 'studio:paper', 'studio@1.0.0/paper',
                      'commons:dracula', 'missing'):
            with self.subTest(theme=theme):
                path = self._commons(theme=theme)
                with self.assertRaises(self.lwp.PropertyError):
                    self.lwp._load_commons_preset(path, 'series', self.lwp.ThemeCatalog())

    def test_commons_precedence_catalogue_and_watch(self):
        installed = self.root / 'installed'
        user_root = Path(os.environ['LWP_COMMONS_DIR'])
        self._commons(installed / 'commons', label='Installed')
        user_path = self._commons(user_root, label='User')
        with mock.patch.object(self.lwp, '_installed_presentation_roots', return_value=[installed / 'kits']):
            catalog = self.lwp.load_identity_catalog(self.root / 'templates')
            self.assertEqual(catalog.resolve_preset('commons/night', 'test').label, 'User')
            self.assertEqual(catalog.resolve_preset('commons/night', 'test').scope, 'user')
            series_path = self._commons(label='Series')
            catalog = self.lwp.load_identity_catalog(self.root / 'templates')
            preset = catalog.resolve_preset('commons/night', 'test')
            self.assertEqual(preset.label, 'Series')
            self.assertEqual(preset.scope, 'series')
            self.assertEqual([p.selector for p in catalog.presets()].count('commons/night'), 1)
            watched = self.lwp._watch_paths(self.root, {})
            self.assertIn(user_path, watched)
            self.assertIn(series_path, watched)
        listed = fixtures.run('preset', 'list', '--format', 'json')
        self.assertEqual(listed.returncode, 0, listed.stderr)
        report = next(p for p in json.loads(listed.stdout)['presets']
                      if p['selector'] == 'commons/night')
        self.assertEqual(report['resource_collection'], 'commons')
        self.assertEqual(report['scope'], 'user')
        self.assertEqual(report['identity']['id'], 'builtin')

    def test_commons_build_verify_and_only_cache_track_descriptor_changes(self):
        descriptor = self._commons()
        series = fixtures.scaffold(self.root, fixtures.IdentityKitFixtures._article())
        data_path = series / 'series.json'
        data = json.loads(data_path.read_text(encoding='utf-8'))
        data['series_meta'] = {'presentation_preset': 'commons/night'}
        data_path.write_text(json.dumps(data), encoding='utf-8')
        cache = series / '.lwp-cache' / 'commons.json'
        args = ('--no-essential-theme', '--nav-cache', str(cache))
        built = fixtures.run('build', str(series), *args)
        self.assertEqual(built.returncode, 0, built.stderr)
        html = (series / 'public' / 'a.html').read_text(encoding='utf-8')
        expected = self.lwp.resolve_theme_properties(self.lwp.theme_property_layer('dracula'))
        self.assertIn(f'--color-page: {expected["color.page"]};', html)
        report = json.loads((series / 'public' / '.lwp-manifest.json').read_text(encoding='utf-8'))
        commons = next(p for p in report['presentation_presets'] if p['selector'] == 'commons/night')
        self.assertTrue(commons['preset_digest'])
        self.assertEqual(commons['identity_digest'], '')
        value = json.loads(descriptor.read_text(encoding='utf-8'))
        value['description'] = 'A changed description without any kit changes.'
        descriptor.write_text(json.dumps(value), encoding='utf-8')
        verified = fixtures.run('verify', str(series), '--no-essential-theme')
        self.assertNotEqual(verified.returncode, 0)
        self.assertIn('[DRIFT] a.html', verified.stdout)
        only = fixtures.run('build', str(series), *args, '--only', 'a.html')
        self.assertEqual(only.returncode, 0, only.stderr)
        self.assertIn('--only requested but not safe', only.stdout + only.stderr)

    def test_commons_descriptors_cannot_escape_their_root(self):
        outside = self.root / 'outside'
        descriptor = self._commons(outside)
        commons = self.root / 'templates' / 'commons'
        commons.mkdir(parents=True)
        (commons / 'presets').symlink_to(descriptor.parent, target_is_directory=True)
        with self.assertRaisesRegex(self.lwp.PropertyError, 'through a symlink'):
            self.lwp.load_identity_catalog(self.root / 'templates')

    def _external_commons(self):
        descriptor = self._commons(Path(os.environ['LWP_COMMONS_DIR']), theme='brand')
        themes = Path(os.environ['LWP_THEMES_DIR'])
        themes.mkdir(parents=True)
        props = self.lwp.resolve_theme_properties(self.lwp.theme_property_layer('dracula'))
        theme = themes / 'brand.conf'
        theme.write_text(self.lwp.theme_file_text(
            'brand', {'label': 'Brand', 'family': 'desk'}, props), encoding='utf-8')
        return descriptor, theme, props

    def test_commons_init_and_set_vendor_only_selected_dependencies_for_isolated_builds(self):
        descriptor, theme, props = self._external_commons()
        self._commons(Path(os.environ['LWP_COMMONS_DIR']), id='unused')
        descriptor_text, theme_text = descriptor.read_bytes(), theme.read_bytes()
        series_roots = []
        for command in ('init', 'set'):
            series = self.root / command
            args = ('--preset', 'commons/night') if command == 'init' else ()
            result = fixtures.run('init', str(series), *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            if command == 'set':
                result = fixtures.run('series', 'preset', 'set', str(series),
                                      '--preset', 'commons/night')
                self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads((series / 'series.json').read_text(encoding='utf-8'))
            self.assertEqual(data['series_meta']['presentation_preset'], 'commons/night')
            data['articles'] = [{'page_source': 'a.md'}]
            (series / 'series.json').write_text(json.dumps(data), encoding='utf-8')
            (series / 'sources' / 'a.md').write_text(
                fixtures.IdentityKitFixtures._article(), encoding='utf-8')
            templates = series / 'templates'
            self.assertEqual((templates / 'commons/presets/night.json').read_bytes(), descriptor_text)
            self.assertEqual((templates / 'themes/brand.conf').read_bytes(), theme_text)
            self.assertFalse((templates / 'commons/presets/unused.json').exists())
            self.assertFalse((templates / 'kits').exists())
            self.assertFalse((templates / 'layouts').exists())
            series_roots.append(series)
        shutil.rmtree(self.root / 'library')

        for series in series_roots:
            with self.subTest(series=series.name):
                shown = fixtures.run('series', 'preset', str(series), '--format', 'json')
                self.assertEqual(shown.returncode, 0, shown.stderr)
                preset = json.loads(shown.stdout)['preset']
                self.assertEqual(preset['selector'], 'commons/night')
                self.assertEqual(preset['scope'], 'series')
                self.assertEqual(preset['theme']['label'], 'Brand')
                report = fixtures.run('series', 'theme', str(series), '--format', 'json')
                self.assertEqual(report.returncode, 0, report.stderr)
                report = json.loads(report.stdout)
                self.assertEqual(report['label'], 'Brand')
                self.assertEqual(report['palette']['page'], props['color.page'])

                settings = series / 'templates/settings.conf'
                settings.write_text('color.page: #123456FF\n', encoding='utf-8')
                refreshed = fixtures.run('template', 'update', str(series), '--scaffold')
                self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
                self.assertIn('# scaffold-for: commons/night', settings.read_text())
                self.assertIn('color.page: #123456FF', settings.read_text())
                self.assertIn(f'# color.ink: {props["color.ink"]}', settings.read_text())
                settings.unlink()
                refreshed = fixtures.run('template', 'update', str(series))
                self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
                self.assertIn('# scaffold-for: commons/night', settings.read_text())
                self.assertIn(f'# color.page: {props["color.page"]}', settings.read_text())
                audit = fixtures.run('audit', str(series), '--templates', '--strict')
                self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
                built = fixtures.run('build', str(series), '--no-essential-theme')
                self.assertEqual(built.returncode, 0, built.stderr)
                self.assertIn(f'--color-page: {props["color.page"]};',
                              (series / 'public/a.html').read_text())
                verified = fixtures.run('verify', str(series), '--no-essential-theme')
                self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

    def test_explicit_native_init_and_commons_to_native_set_keep_the_selector(self):
        series = self.root / 'series'
        initialized = fixtures.run('init', str(series), '--preset', 'builtin/standard')
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        series_path = series / 'series.json'
        self.assertEqual(json.loads(series_path.read_text())['series_meta']['presentation_preset'],
                         'builtin/standard')
        self.assertIn('# scaffold-for: builtin/standard',
                      (series / 'templates/settings.conf').read_text())
        self.assertFalse((series / 'templates/kits').exists())
        theme = fixtures.run('series', 'theme', str(series), '--format', 'json')
        self.assertEqual(theme.returncode, 0, theme.stderr)
        report = json.loads(theme.stdout)
        self.assertEqual(report['label'], 'Light')
        self.assertEqual(report['source'], 'builtin')
        self._commons(Path(os.environ['LWP_COMMONS_DIR']))
        for selector in ('commons/night', 'builtin/standard'):
            selected = fixtures.run('series', 'preset', 'set', str(series), '--preset', selector)
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(json.loads(series_path.read_text())['series_meta']['presentation_preset'],
                             selector)

    def test_commons_init_and_set_dry_run_leave_dependencies_and_series_untouched(self):
        self._external_commons()
        series = self.root / 'series'
        initialized = fixtures.run('init', str(series), '--preset', 'commons/night', '--dry-run')
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertFalse(series.exists())
        self.assertEqual(fixtures.run('init', str(series)).returncode, 0)
        before = {path.relative_to(series): path.read_bytes()
                  for path in series.rglob('*') if path.is_file()}
        selected = fixtures.run('series', 'preset', 'set', str(series),
                                '--preset', 'commons/night', '--dry-run')
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertEqual(before, {path.relative_to(series): path.read_bytes()
                                  for path in series.rglob('*') if path.is_file()})
        self.assertFalse((series / 'templates/commons').exists())
        self.assertFalse((series / 'templates/themes').exists())

    def test_commons_set_rolls_back_dependencies_if_series_write_fails(self):
        self._external_commons()
        series = self.root / 'series'
        self.assertEqual(fixtures.run('init', str(series)).returncode, 0)
        series_path = series / 'series.json'
        settings = series / 'templates/settings.conf'
        settings.write_text('theme: nord\ncolor.page: #123456FF\n', encoding='utf-8')
        before_series, before_settings = series_path.read_bytes(), settings.read_bytes()
        write_file = self.lwp._write_file

        def fail_series_write(path, text, **kwargs):
            if Path(path) == series_path:
                raise OSError('injected series write failure')
            return write_file(path, text, **kwargs)

        with mock.patch.object(self.lwp, '_write_file', side_effect=fail_series_write):
            with self.assertRaises(SystemExit):
                self.lwp.cmd_set_presentation_preset(series, {
                    '--preset': 'commons/night', '--use-preset-theme': True})
        self.assertEqual(series_path.read_bytes(), before_series)
        self.assertEqual(settings.read_bytes(), before_settings)
        self.assertFalse((series / 'templates/commons').exists())
        self.assertFalse((series / 'templates/themes').exists())

    def test_commons_schema_label_and_filename_are_validated(self):
        for changes in ({'schema': 'other/1'}, {'id': 'Bad'},
                        {'label': ''}, {'description': ' '}, {'theme': None},
                        {'starter': 'seed'}):
            with self.subTest(changes=changes):
                path = self._commons(**changes)
                with self.assertRaises(self.lwp.PropertyError):
                    self.lwp._load_commons_preset(path, 'series', self.lwp.ThemeCatalog())
        path = self._commons()
        renamed = path.with_name('different.json')
        path.rename(renamed)
        with self.assertRaisesRegex(self.lwp.PropertyError, 'match the filename'):
            self.lwp._load_commons_preset(renamed, 'series', self.lwp.ThemeCatalog())


if __name__ == '__main__':
    unittest.main()
