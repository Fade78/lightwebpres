"""End-to-end coverage for the runtime theme picker and menu."""

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
        settings = root / 'templates' / 'settings.conf'
        settings.write_text(
            settings.read_text(encoding='utf-8') + 'color.ink: #123456\n',
            encoding='utf-8',
        )
        (root / 'templates' / 'custom.css').write_text(
            ':root { --color-mark: #ABCDEF; }\n', encoding='utf-8')
        build = subprocess.run(
            ['python3', str(LWP), 'build', str(root),
             '--no-essential-theme', '--themes', 'print-ink'],
            capture_output=True, text=True, timeout=60,
        )
        assert build.returncode == 0, build.stdout + build.stderr

        output = root / 'public'
        cls.httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *args: _QuietHandler(*args, directory=str(output)),
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

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
        cls.static_httpd.shutdown()
        cls.static_thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_picker_menu_and_session_theme_are_real_browser_behaviour(self):
        base = 'http://127.0.0.1:%d' % self.port
        result = subprocess.run(
            ['node', str(SCRIPT), base,
             'http://127.0.0.1:%d' % self.static_port],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
