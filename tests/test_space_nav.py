"""Space follows the existing deck journey without stealing control activation."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SpaceNavigation(unittest.TestCase):
    def test_geometry_card_journeys_and_key_ownership(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ['node', str(ROOT / 'tests' / 'space_nav_e2e.cjs')],
                cwd=ROOT,
                env={**os.environ, 'TMPDIR': str(scratch), 'PYTHON': sys.executable},
                capture_output=True, text=True, timeout=240)
        except FileNotFoundError:
            self.skipTest('Node unavailable in the supplied environment')
        if result.returncode == 77:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Space navigation checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
