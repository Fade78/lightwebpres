"""Mouse grammar and capture lifecycle, plus native browser integration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import run
else:
    from test_lightwebpres import run

ROOT = Path(__file__).resolve().parents[1]


class MouseCommands(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=scratch, prefix='mouse-commands-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources').mkdir()
        self.env = {**os.environ, 'TMPDIR': str(scratch)}
        (self.root / 'series.json').write_text(json.dumps({
            'series_meta': {'title': 'Mouse commands', 'scroll_duration': 0},
            'articles': [{'page_source': name + '.md', 'page_dest': name + '.html'}
                         for name in ['a', 'b']],
        }), encoding='utf-8')
        for name in ['a', 'b']:
            (self.root / 'sources' / (name + '.md')).write_text(
                '<!-- lwp:meta -->\npage_title: Mouse ' + name + '\n---\n\n'
                '<!-- lwp:slide -->\nslug: start\n## Start\n'
                + ('A long first slide.\n\n' * 80)
                + '<input aria-label="Native input">\n'
                '[Other article](b.html#start)\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: second\n## Second\nText.\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: third\n## Third\nText.\n', encoding='utf-8')
        self.output = self.root / 'public'
        result = run('build', self.root, '--lang', 'en', '--output', self.output,
                     env=self.env, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def node(self, script, *arguments):
        try:
            result = subprocess.run(['node', str(ROOT / 'tests' / script),
                                     *map(str, arguments)], cwd=ROOT, env=self.env,
                                    text=True, capture_output=True, timeout=120)
        except FileNotFoundError:
            self.skipTest('Node unavailable in the supplied environment')
        if result.returncode == 77:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_generated_runtime_grammar_capture_and_event_ownership(self):
        self.assertIn('Mouse command runtime checks passed', self.node(
            'mouse_commands_runtime.cjs', self.output / 'a.html'))

    def browser(self, engine):
        bundle = self.root / 'combined'
        result = run('build', self.root, '--lang', 'en', '--single-html', 'series.html',
                     '--output', bundle, env=self.env, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Mouse command browser checks passed', self.node(
            'mouse_commands_e2e.cjs', engine,
            (self.output / 'a.html').as_uri(), (bundle / 'series.html').as_uri()))

    def test_chromium_native_gestures_and_capture(self):
        self.browser('chromium')

    def test_firefox_native_gestures_and_capture(self):
        self.browser('firefox')
