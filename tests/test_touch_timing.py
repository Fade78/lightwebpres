"""Touch gesture duration follows input occurrence, not delayed handler execution."""
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


class TouchEventTiming(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='touch-timing-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'sources').mkdir()
        (self.root / 'sources/a.md').write_text(
            '<!-- lwp:meta -->\n---\n\n' + '\n\n---\n\n'.join(
                '<!-- lwp:slide -->\nslug: c' + str(index)
                + '\n## Native touch\nsummary: A queued gesture.\n'
                for index in range(1, 4)), encoding='utf-8')
        (self.root / 'series.json').write_text(json.dumps({
            'build': {'index': True},
            'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
        self.env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
                    'LWP_THEMES_DIR': str(self.root / 'themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits')}
        built = run('build', self.root, env=self.env)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)

    def node(self, script, *arguments):
        try:
            checked = subprocess.run(
                ['node', str(ROOT / 'tests' / script), *map(str, arguments)],
                cwd=ROOT, env=self.env, text=True, capture_output=True, timeout=90)
        except FileNotFoundError:
            self.skipTest('Node unavailable in supplied environment')
        if checked.returncode == 77:
            self.skipTest(checked.stderr.strip())
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        return checked.stdout

    def test_emitted_touch_recognizer_uses_event_time_and_keeps_click_quarantine(self):
        self.assertIn('Touch event clock checks passed', self.node(
            'touch_timing_runtime.cjs', self.root / 'public/a.html'))

    def test_queued_native_taps_restore_position_and_toggle_chrome(self):
        built = run('build', self.root, '--single-html', 'series.html',
                    '--output', self.root / 'combined', env=self.env)
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        self.assertIn('Queued native touch checks passed', self.node(
            'touch_timing_e2e.cjs', (self.root / 'public/a.html').as_uri(),
            (self.root / 'combined/series.html').as_uri()))
