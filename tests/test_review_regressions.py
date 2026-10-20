"""Independent review reproductions exercise emitted tag and physical-home contracts."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run

ROOT = Path(__file__).resolve().parents[1]


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class IndependentReviewRegressions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='review-regressions-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources').mkdir()
        self.env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
                    'LWP_THEMES_DIR': str(self.root / 'themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits')}

    def series(self, entries):
        registered = []
        for entry, tags in entries:
            registered.append(entry)
            tag_field = 'tags: ' + tags + '\n' if tags else ''
            (self.root / 'sources' / entry['page_source']).write_text(
                '<!-- lwp:meta -->\n---\n\n<!-- lwp:slide:cover -->\nslug: cover\n'
                + tag_field + '# Review fixture\nsummary: Readable content.\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: navigation\n' + tag_field,
                encoding='utf-8')
        (self.root / 'series.json').write_text(json.dumps({
            'series_meta': {'scroll_duration': 0}, 'articles': registered}), encoding='utf-8')

    def cli(self, command, *options):
        result = run(command, self.root, '--lang', 'en', *options, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def browser(self, mode, paths):
        handler = functools.partial(_QuietHandler, directory=str(self.root))
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port) + '/'
            try:
                checked = subprocess.run(
                    ['node', str(ROOT / 'tests/review_regressions_e2e.cjs'), mode,
                     *[base + path for path in paths]], cwd=ROOT, env=self.env,
                    capture_output=True, text=True, timeout=120)
            except FileNotFoundError:
                self.skipTest('Node unavailable in supplied environment')
            if checked.returncode == 77:
                self.skipTest(checked.stderr.strip())
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn('chromium: ' + mode + ' regression passed', checked.stdout)
            self.assertIn('firefox: ' + mode + ' regression passed', checked.stdout)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_constructor_tag_is_available_and_falls_back_in_both_topologies(self):
        self.series([({'page_source': 'a.md'}, ''), ({'page_source': 'b.md'}, 'constructor')])
        self.cli('build', '--output', self.root / 'multi')
        self.cli('verify', '--output', self.root / 'multi')
        self.cli('build', '--output', self.root / 'combined', '--single-html', 'series.html')
        self.cli('verify', '--output', self.root / 'combined', '--single-html', 'series.html')
        self.browser('tags', ['multi/b.html', 'combined/series.html#lwp/a/b.html/cover'])

    def test_mixed_case_index_home_links_sharing_and_shortcut_reach_real_home(self):
        self.series([({'page_source': 'a.md', 'page_dest': 'Index.html'}, '')])
        self.cli('build', '--output', self.root / 'multi', '--make-nav')
        self.cli('verify', '--output', self.root / 'multi', '--make-nav')
        self.assertTrue((self.root / 'multi/Index.html').is_file())
        if os.name != 'nt':
            self.assertFalse((self.root / 'multi/index.html').exists())
        self.cli('build', '--output', self.root / 'combined', '--single-html', 'series.html',
                 '--make-index', '--make-nav')
        self.cli('verify', '--output', self.root / 'combined', '--single-html', 'series.html',
                 '--make-index', '--make-nav')
        self.browser('home', ['multi/Index.html', 'combined/series.html#lwp/a/Index.html/cover'])

    def test_build_open_uses_the_exact_claimant_spelling(self):
        self.series([({'page_source': 'a.md', 'page_dest': 'Index.html'}, '')])
        recorder = self.root / 'browser.py'
        opened = self.root / 'opened.txt'
        recorder.write_text('import pathlib,sys\npathlib.Path(sys.argv[1]).write_text(sys.argv[2])\n')
        self.env['BROWSER'] = ' '.join(map(shlex.quote,
            [sys.executable, str(recorder), str(opened)])) + ' %s'
        self.cli('build', '--open')
        self.assertEqual(opened.read_text(), (self.root / 'public/Index.html').as_uri())

    def test_watch_open_uses_the_entrypoint_returned_by_its_real_build(self):
        self.series([({'page_source': 'a.md', 'page_dest': 'Index.html'}, '')])
        lwp = load_lightwebpres_module()
        with mock.patch.dict(os.environ, self.env), mock.patch.object(
                lwp, '_cmd_watch_poll', return_value=iter(())), mock.patch('webbrowser.open') as opened:
            lwp.cmd_watch(str(self.root), {'--open': True})
        opened.assert_called_once_with((self.root / 'public/Index.html').as_uri())
