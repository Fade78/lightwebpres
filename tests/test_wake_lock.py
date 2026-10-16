"""Screen wake locks follow fullscreen and visibility, including delayed replies."""
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


class WakeLockLifecycle(unittest.TestCase):
    def test_emitted_runtime_owns_pending_active_and_released_screen_locks(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='wake-lock-') as temporary:
            root = Path(temporary)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({
                'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            (root / 'sources/a.md').write_text(
                '<!-- lwp:meta -->\n---\n\n<!-- lwp:slide:cover -->\nslug: cover\n# Wake lock\n', encoding='utf-8')
            env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
                   'LWP_THEMES_DIR': str(root / 'themes'),
                   'LWP_COMMONS_DIR': str(root / 'commons'),
                   'LWP_IDENTITY_KITS_DIR': str(root / 'kits')}
            built = run('build', root, env=env)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            try:
                checked = subprocess.run(
                    ['node', str(ROOT / 'tests/wake_lock_runtime.cjs'), str(root / 'public/a.html')],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
            except FileNotFoundError:
                self.skipTest('Node unavailable in supplied environment')
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn('Screen wake lock lifecycle checks passed', checked.stdout)
