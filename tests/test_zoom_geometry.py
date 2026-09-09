"""Manual zoom keeps the actual shipped identity frames at responsive size."""
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent


class ZoomGeometryBrowser(unittest.TestCase):
    def test_content_zoom_preserves_real_native_and_kit_frames(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        try:
            probe = subprocess.run(['node', '-e', "require('playwright')"], env=env,
                                   capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            self.skipTest('Node/Playwright unavailable on supplied PATH: ' + str(exc))
        if probe.returncode:
            self.skipTest('Playwright unavailable in supplied environment: ' + probe.stderr)
        result = subprocess.run(['node', str(ROOT / 'tests/zoom_geometry_e2e.cjs')],
                                env=env, capture_output=True, text=True, timeout=180)
        if result.returncode == 77:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
