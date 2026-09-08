"""End-to-end coverage for the runtime theme picker and menu."""

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LWP = REPO_ROOT / 'lightwebpres'
SCRIPT = Path(__file__).resolve().parent / 'runtime_themes_e2e.cjs'


def _node_playwright_available():
    if shutil.which('node') is None:
        return False, 'node not found on PATH'
    npm_root = subprocess.run(
        ['npm', 'root', '-g'], capture_output=True, text=True,
    ).stdout.strip()
    check = subprocess.run(
        ['node', '-e', "require('playwright')"],
        capture_output=True, text=True,
        env={**os.environ, 'NODE_PATH': npm_root},
    )
    if check.returncode != 0:
        return False, 'playwright not resolvable via npm root -g'
    return True, npm_root


AVAILABLE, NPM_ROOT_OR_REASON = _node_playwright_available()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


class RuntimeIdentityMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_lightwebpres import load_lightwebpres_module
        cls.lwp = load_lightwebpres_module()

    def test_single_preset_retains_identity_and_standard_metadata(self):
        preset = self.lwp.DEFAULT_PRESENTATION_PRESET
        data = self.lwp._presentation_runtime_context(
            [preset], ([preset.theme_props, {}], ''), None, None)
        self.assertEqual(data['primary'], 'builtin/standard')
        self.assertEqual(data['identities'], [{
            'selector': 'builtin', 'label': 'LightWebPres', 'origin': 'builtin',
        }])
        self.assertEqual(data['presets'][0]['label'], 'Standard')
        self.assertEqual(data['presets'][0]['identity'], 'builtin')
        self.assertIn('identityOptions', self.lwp._presentation_picker_markup({}, data))
        self.assertIsNone(self.lwp.build_theme_runtime(None, None, presets=[preset]))

    def test_native_commons_keeps_its_theme_origin_and_independent_digest(self):
        native = self.lwp.DEFAULT_PRESENTATION_PRESET
        commons = self.lwp.PresentationPreset(
            native.package, 'ink', 'Commons ink', 'Ink preset',
            theme_props={'color.ink': '#123456'}, default=True,
            resource_collection='commons', scope='series', digest='first')
        context = ([native.theme_props, {}], '')
        data = self.lwp._presentation_runtime_context(
            [native, commons], context, None, None)
        descriptor = data['presets'][1]
        self.assertEqual(descriptor['selector'], 'commons/ink')
        self.assertEqual(descriptor['identity'], 'builtin')
        self.assertEqual(descriptor['collection'], 'commons')
        self.assertEqual(descriptor['origin'], 'series')
        self.assertEqual(descriptor['label'], 'Commons ink')
        ink = data['vars'].index('--color-ink')
        self.assertEqual(dict(descriptor['theme_values'])[ink], '#123456FF')
        commons._digest = 'second'
        changed = self.lwp._presentation_runtime_context(
            [native, commons], context, None, None)
        self.assertNotEqual(data['catalog_digest'], changed['catalog_digest'])

    def test_all_selected_kit_themes_are_qualified_independent_choices(self):
        kit = self.lwp.PresentationPackage(
            'brand', '1.0.0', label='A brand', scope='series', digest='kit-v1',
            themes={name: {
                'props': {'color.ink': ink},
                'meta': {'label': name.title(), 'family': 'brand'},
            } for name, ink in [('main', '#123456'), ('secondary', '#654321')]})
        preset = self.lwp.PresentationPreset(
            kit, 'slides', 'Slides', 'Brand slides', theme_id='main',
            theme_props=kit.themes['main']['props'])
        data = self.lwp.build_theme_runtime(
            'print-ink', None, preset_props=preset.theme_props,
            preset_selector=preset.selector, presets=[preset])
        self.assertEqual(data['primary'], 'kit:brand@1.0.0/main')
        themes = {theme['slug']: theme for theme in data['themes']}
        self.assertEqual(set(themes), {
            'kit:brand@1.0.0/main', 'kit:brand@1.0.0/secondary', 'print-ink',
        })
        secondary = themes['kit:brand@1.0.0/secondary']
        self.assertEqual(secondary['identity'], 'brand@1.0.0')
        self.assertEqual(secondary['identity_label'], 'A brand')
        self.assertEqual(secondary['origin'], 'series')
        ink = data['vars'].index('--color-ink')
        self.assertEqual(dict(secondary['values'])[ink], '#654321FF')
        self.assertEqual(themes['print-ink']['collection'], 'Commons')
        self.assertEqual(themes['print-ink']['origin'], 'embedded')
        kit_only = self.lwp.build_theme_runtime(
            None, None, preset_props=preset.theme_props,
            preset_selector=preset.selector, presets=[preset])
        self.assertEqual(len(kit_only['themes']), 2)
        kit.digest = 'kit-v2'
        changed = self.lwp.build_theme_runtime(
            'print-ink', None, preset_props=preset.theme_props,
            preset_selector=preset.selector, presets=[preset])
        self.assertNotEqual(data['catalog_digest'], changed['catalog_digest'])

    def test_commons_theme_origin_comes_from_catalog_not_authored_source(self):
        catalog = self.lwp.ThemeCatalog()
        catalog.add_local('print-ink', self.lwp.THEMES['print-ink'],
                          catalog.layer('print-ink'), LWP, 'series', 'fixture')
        data = self.lwp.build_theme_runtime('print-ink', 'print-ink', catalog=catalog)
        self.assertEqual(data['themes'][0]['origin'], 'series')
        self.assertEqual(data['themes'][0]['collection'], 'Commons')

    def test_commons_primary_is_a_global_theme_not_a_native_identity_theme(self):
        catalog = self.lwp.ThemeCatalog()
        native = self.lwp.DEFAULT_PRESENTATION_PACKAGE
        preset = self.lwp.PresentationPreset(
            native, 'paper', 'Paper', 'Commons paper', theme_id='print-ink',
            theme_props=catalog.layer('print-ink'), default=True,
            resource_collection='commons', scope='user', digest='paper-v1')
        data = self.lwp.build_theme_runtime(
            'print-ink', None, catalog=catalog, preset_props=preset.theme_props,
            preset_selector=preset.selector, presets=[preset])
        self.assertEqual(data['primary'], 'print-ink')
        self.assertEqual(data['themes'][0]['collection'], 'Commons')
        self.assertIsNone(data['themes'][0]['identity'])
        self.assertEqual(data['themes'][1]['slug'], 'kit:builtin/light')

    def test_theme_deltas_use_the_static_cascade_without_flattening_references(self):
        catalog = self.lwp.ThemeCatalog()
        native = self.lwp.DEFAULT_PRESENTATION_PRESET
        commons = self.lwp.PresentationPreset(
            native.package, 'night', 'Night', 'Commons night', theme_id='dracula',
            theme_props=catalog.layer('dracula'), default=True,
            resource_collection='commons')
        snapshot = self.lwp.resolve_theme_properties(catalog.layer('dracula'))
        kit = self.lwp.PresentationPackage(
            'snapshot', '1.0.0', label='Snapshot', themes={'night': {
                'props': snapshot, 'meta': {'label': 'Night', 'family': 'desk'},
            }})
        kit_preset = self.lwp.PresentationPreset(
            kit, 'slides', 'Slides', 'Literal snapshot', theme_id='night',
            theme_props=snapshot)
        pins = {'color.page': '#123456FF'}
        _variables, keys = self.lwp._theme_runtime_variables()
        for preset, raw_id in [(native, 'kit:builtin/light'), (commons, 'dracula'),
                               (kit_preset, 'kit:snapshot@1.0.0/night')]:
            with self.subTest(preset=preset.selector):
                static = self.lwp.resolve_theme_properties(preset.theme_props, pins)
                raw = self.lwp.resolve_theme_properties(preset.theme_props)
                self.assertEqual(static['page.bg'], snapshot['page.bg']
                                 if preset is kit_preset else pins['color.page'])
                data = self.lwp.build_theme_runtime(
                    'print-ink', None, catalog=catalog, settings_props=pins,
                    preset_props=preset.theme_props, presets=[preset])
                self.assertEqual(data['themes'][0]['preview']['background'], static['page.bg'])
                for slug, expected in [(raw_id, raw), ('print-ink',
                        self.lwp._theme_runtime_resolved('print-ink', catalog))]:
                    theme = next(theme for theme in data['themes'] if theme['slug'] == slug)
                    applied = dict(static)
                    applied.update((keys[index], value) for index, value in theme['values'])
                    self.assertEqual(applied, expected, slug)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s'
                     % NPM_ROOT_OR_REASON)
class RuntimeThemesBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name) / 'series'
        init = subprocess.run(
            ['python3', str(LWP), 'init', str(root), '--theme', 'print-oldpress'],
            capture_output=True, text=True, timeout=60,
        )
        assert init.returncode == 0, init.stdout + init.stderr
        demo = subprocess.run(
            ['python3', str(LWP), 'demo', str(root)],
            capture_output=True, text=True, timeout=60,
        )
        assert demo.returncode == 0, demo.stdout + demo.stderr
        package_source = REPO_ROOT / 'examples' / 'kits' / 'lightwebpres-docs' / '0.1.0'
        package_destination = (root / 'templates' / 'kits'
                               / 'lightwebpres-docs' / '0.1.0')
        shutil.copytree(package_source, package_destination)
        series_path = root / 'series.json'
        series = json.loads(series_path.read_text(encoding='utf-8'))
        series.setdefault('series_meta', {})['presentation_preset'] = \
            'lightwebpres-docs@0.1.0/docs'
        series_path.write_text(json.dumps(series), encoding='utf-8')
        settings = root / 'templates' / 'settings.conf'
        settings.write_text(
            settings.read_text(encoding='utf-8')
            + 'color.ink: #123456\n'
            + 'nav-btn.size: 36px\n',
            encoding='utf-8',
        )
        (root / 'templates' / 'custom.css').write_text(
            ':root { --color-mark: #ABCDEF; }\n', encoding='utf-8')
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(root),
             '--no-essential-theme', '--themes', 'print-ink',
             '--scroll-duration', '350'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr

        output = root / 'public'
        zero_output = output / 'zero-duration'
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(root),
             '--output', str(zero_output), '--scroll-duration', '0'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        cls.httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *args: _QuietHandler(*args, directory=str(output)),
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

        presentation_root = Path(cls.tmpdir.name) / 'presentation-series'
        init = subprocess.run(
            ['python3', str(LWP), 'init', str(presentation_root)],
            capture_output=True, text=True, timeout=60,
        )
        assert init.returncode == 0, init.stdout + init.stderr
        demo = subprocess.run(
            ['python3', str(LWP), 'demo', str(presentation_root)],
            capture_output=True, text=True, timeout=60,
        )
        assert demo.returncode == 0, demo.stdout + demo.stderr
        presentation_package = (presentation_root / 'templates' / 'kits'
                                / 'lightwebpres-docs' / '0.1.0')
        shutil.copytree(package_source, presentation_package)
        presentation_manifest_path = presentation_package / 'manifest.json'
        presentation_manifest = json.loads(
            presentation_manifest_path.read_text(encoding='utf-8'))
        compact_theme = subprocess.run(
            ['python3', str(LWP), 'theme', 'create', 'compact', '--from', 'nord',
             '--output', str(presentation_package / 'themes' / 'compact.conf')],
            capture_output=True, text=True, timeout=60,
        )
        assert compact_theme.returncode == 0, compact_theme.stdout + compact_theme.stderr
        presentation_manifest['themes']['compact'] = 'themes/compact.conf'
        presentation_manifest['presets']['compact'] = {
            'label': 'Compact documentation',
            'description': 'A denser presentation for the same content.',
            'theme': 'compact',
            'slide_layouts': {
                'cover': 'hero', 'standard': 'default',
                'series-nav': 'default', 'full-article': 'default',
            },
            'slide_chrome': {'all': {'footer': ''}},
        }
        presentation_manifest_path.write_text(
            json.dumps(presentation_manifest), encoding='utf-8')
        presentation_series_path = presentation_root / 'series.json'
        presentation_series = json.loads(
            presentation_series_path.read_text(encoding='utf-8'))
        presentation_series.setdefault('series_meta', {})[
            'presentation_preset'] = 'lightwebpres-docs@0.1.0/docs'
        presentation_series['presentation_presets'] = [
            'lightwebpres-docs@0.1.0/compact',
        ]
        presentation_series_path.write_text(
            json.dumps(presentation_series), encoding='utf-8')
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(presentation_root),
             '--no-essential-theme', '--themes', 'print-ink'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        presentation_output = presentation_root / 'public'
        other_output = presentation_output / 'other-deck'
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(presentation_root),
             '--output', str(other_output), '--no-essential-theme',
             '--themes', 'print-ink'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        cls.presentation_httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *args: _QuietHandler(*args, directory=str(presentation_output)),
        )
        cls.presentation_port = cls.presentation_httpd.server_address[1]
        cls.presentation_thread = threading.Thread(
            target=cls.presentation_httpd.serve_forever, daemon=True)
        cls.presentation_thread.start()

        static_root = Path(cls.tmpdir.name) / 'static-series'
        init = subprocess.run(
            ['python3', str(LWP), 'init', str(static_root), '--theme', 'print-oldpress'],
            capture_output=True, text=True, timeout=60,
        )
        assert init.returncode == 0, init.stdout + init.stderr
        demo = subprocess.run(
            ['python3', str(LWP), 'demo', str(static_root)],
            capture_output=True, text=True, timeout=60,
        )
        assert demo.returncode == 0, demo.stdout + demo.stderr
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(static_root),
             '--no-essential-theme'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        static_output = static_root / 'public'
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(static_root),
             '--output', str(static_output / 'single-preset'),
             '--no-essential-theme', '--themes', 'print-ink'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        cls.static_httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *args: _QuietHandler(*args, directory=str(static_output)),
        )
        cls.static_port = cls.static_httpd.server_address[1]
        cls.static_thread = threading.Thread(
            target=cls.static_httpd.serve_forever, daemon=True)
        cls.static_thread.start()

        pinned_root = Path(cls.tmpdir.name) / 'pinned-series'
        for command in ('init', 'demo'):
            result = subprocess.run(
                ['python3', str(LWP), command, str(pinned_root)],
                capture_output=True, text=True, timeout=60,
            )
            assert result.returncode == 0, result.stdout + result.stderr
        commons_dir = pinned_root / 'templates' / 'commons' / 'presets'
        commons_dir.mkdir(parents=True)
        (commons_dir / 'night.json').write_text(json.dumps({
            'schema': 'lightwebpres.commons-preset/1', 'id': 'night',
            'label': 'Night', 'description': 'Reference-aware Commons theme',
            'theme': 'dracula',
        }), encoding='utf-8')
        series_path = pinned_root / 'series.json'
        series = json.loads(series_path.read_text(encoding='utf-8'))
        for name, selector in [('native', 'builtin/standard'), ('commons', 'commons/night')]:
            series['series_meta']['presentation_preset'] = selector
            series_path.write_text(json.dumps(series), encoding='utf-8')
            for variant, settings in [('pinned', 'color.page: #123456FF\n'), ('raw', '')]:
                (pinned_root / 'templates' / 'settings.conf').write_text(settings, encoding='utf-8')
                result = subprocess.run(
                    ['python3', str(LWP), 'build', str(pinned_root), '--no-essential-theme',
                     '--themes', 'print-ink', '--output', str(static_output / (name + '-' + variant))],
                    capture_output=True, text=True, timeout=60,
                )
                assert result.returncode == 0, result.stdout + result.stderr

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.presentation_httpd.shutdown()
        cls.presentation_thread.join(timeout=5)
        cls.static_httpd.shutdown()
        cls.static_thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_picker_menu_and_session_theme_are_real_browser_behaviour(self):
        base = 'http://127.0.0.1:%d' % self.port
        result = subprocess.run(
            ['node', str(SCRIPT), base,
             'http://127.0.0.1:%d' % self.static_port,
             base + '/zero-duration',
             'http://127.0.0.1:%d' % self.presentation_port],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
