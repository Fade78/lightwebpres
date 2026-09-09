"""Browser-level reading controls and gesture isolation, using real builds.

Only browser emulation is exercised, not a physical phone. Playwright must
already be resolvable through the supplied environment; nothing is installed.
"""

import functools
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = Path(__file__).resolve().parent.parent


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class ReadingControls(unittest.TestCase):
    def test_menu_keyboard_nested_scroll_and_native_pinch(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        try:
            probe = subprocess.run(
                ['node', '-e', "require('playwright')"], env=env,
                capture_output=True, text=True, timeout=30)
        except OSError as exc:
            self.skipTest(str(exc))
        if probe.returncode:
            self.skipTest('Playwright unavailable in the supplied environment')
        with tempfile.TemporaryDirectory(dir=scratch, prefix='reading-controls-') as tmp:
            root = Path(tmp)
            (root / 'sources').mkdir()
            shutil.copytree(ROOT / 'examples' / 'kits' / 'lightwebpres-docs' / '0.1.0',
                            root / 'templates' / 'kits' / 'lightwebpres-docs' / '0.1.0')
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'default_tag': 'main'},
                'presentation_presets': ['lightwebpres-docs@0.1.0/docs'],
                'articles': [{'page_dest': 'controls.html', 'page_source': 'controls.md',
                              'nav_title': 'Reading', 'nav_desc': 'Reading controls'}],
            }), encoding='utf-8')
            table = ('| ' + ' | '.join('LongUnbreakableColumnHeading%d' % i for i in range(8))
                     + ' |\n| ' + ' | '.join(['---'] * 8) + ' |\n'
                     + '\n'.join('| ' + ' | '.join('Measured text %d %d' % (i, j)
                                                    for i in range(8)) + ' |'
                                 for j in range(5)))
            (root / 'sources' / 'long.md').write_text(
                '# Long reading\n\nA claim with a source[^source].\n\n'
                + '\n\n'.join('## Section %d\n\n' % i
                              + 'Reading position must survive zoom and browser chrome. ' * 8
                              for i in range(30))
                + '\n\n[^source]: The source at the end of the long article.\n',
                encoding='utf-8')
            (root / 'sources' / 'controls.md').write_text(
                '<!-- lwp:meta -->\npage_dest: controls.html\npage_title: Reading controls\n'
                'nav_title: Reading\nnav_desc: Controls\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: cover\ntags: main brief\n# Reading controls\n'
                'summary: A cover to make accidental navigation observable.\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: wide\ntags: main\n## Wide table and text\n'
                'summary: Keep this text readable independently of the table.\n\n'
                + table + '\n\n---\n\n'
                '<!-- lwp:slide:full-article -->\nslug: long\ntags: main solo double\narticle: long.md\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: after\ntags: main\n## After reading\n'
                'summary: Reached only by intentional navigation.\n'
                'note: Speaker notes remain readable without shrinking the chosen type size.\n\n---\n\n'
                '<!-- lwp:slide:full-article -->\nslug: other-long\ntags: double\narticle: long.md\n',
                encoding='utf-8')
            built = root / 'public'
            build = subprocess.run(
                ['python3', str(ROOT / 'lightwebpres'), 'build', str(root)],
                env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            handler = functools.partial(_QuietHandler, directory=str(built))
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                check = subprocess.run(
                    ['node', str(ROOT / 'tests' / 'reading_controls_e2e.cjs'),
                     'http://127.0.0.1:%d/controls.html' % server.server_port],
                    env=env, capture_output=True, text=True, timeout=180)
                if check.returncode == 77:
                    self.skipTest(check.stderr.strip())
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                self.assertIn('390 mobile', check.stdout)
                self.assertIn('768 desktop', check.stdout)
            finally:
                server.shutdown()
                thread.join()
                server.server_close()
