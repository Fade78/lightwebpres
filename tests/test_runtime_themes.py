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
        package_source = REPO_ROOT / 'examples' / 'layouts' / 'lightwebpres-docs' / '0.1.0'
        package_destination = (root / 'templates' / 'layouts'
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
        presentation_package = (presentation_root / 'templates' / 'layouts'
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
        cls.static_httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *args: _QuietHandler(*args, directory=str(static_output)),
        )
        cls.static_port = cls.static_httpd.server_address[1]
        cls.static_thread = threading.Thread(
            target=cls.static_httpd.serve_forever, daemon=True)
        cls.static_thread.start()

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
