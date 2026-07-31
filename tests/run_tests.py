#!/usr/bin/env python3
"""Runs the LightWebPres regression test battery.

Usage: python3 tests/run_tests.py
Non-zero exit if a test fails unexpectedly (a regression), or if a test
marked as a known bug starts passing without its @unittest.expectedFailure
decorator having been removed.
"""

import sys
import unittest
from pathlib import Path

if __name__ == '__main__':
    suite = unittest.TestLoader().discover(
        start_dir=str(Path(__file__).resolve().parent),
        pattern='test_*.py',
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
