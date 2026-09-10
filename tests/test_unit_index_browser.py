"""Real CLI unit-index layouts and navigation in the supplied browser.

Every invocation owns a unique repository-local scratch directory, including
browser profiles and captures, so the parallel runner can use eight workers.
"""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UnitIndexBrowser(unittest.TestCase):
    def test_responsive_indexes_navigation_locales_and_print(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ['node', str(ROOT / 'tests' / 'unit_index_e2e.cjs')],
                cwd=ROOT,
                env={**os.environ, 'TMPDIR': str(scratch), 'PYTHON': sys.executable},
                capture_output=True, text=True, timeout=240)
        except FileNotFoundError:
            self.skipTest('Node unavailable in the supplied environment')
        if result.returncode == 77:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('unit-index browser checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
