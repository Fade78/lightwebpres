#!/usr/bin/env python3
"""Runs the LightWebPres regression test battery.

Usage: python3 tests/run_tests.py
       python3 tests/run_tests.py --workers 8
Non-zero exit if a test fails unexpectedly (a regression), or if a test
marked as a known bug starts passing without its @unittest.expectedFailure
decorator having been removed.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent


def _iter_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_cases(item)
        else:
            yield item


def _class_groups(suite):
    """Return importable test classes with their case counts.

    Classes, rather than individual methods, are the unit of sharding: a
    class's setUpClass/tearDownClass remains together and each worker gets a
    fresh Python process. The subprocess boundary also keeps the black-box
    tests' temporary fixtures and imported module state isolated.
    """
    groups = {}
    for case in _iter_cases(suite):
        cls = type(case)
        module = cls.__module__
        if module.startswith('test_'):
            module = f'tests.{module}'
        name = f'{module}.{cls.__name__}'
        groups[name] = groups.get(name, 0) + 1
    return groups


def _shards(groups, workers):
    shards = [[] for _ in range(workers)]
    loads = [0] * workers
    # Greedy balancing keeps the large classes from all landing in one shard.
    for name, count in sorted(groups.items(), key=lambda item: item[1],
                              reverse=True):
        index = min(range(workers), key=loads.__getitem__)
        shards[index].append(name)
        loads[index] += count
    return [(index, names, loads[index])
            for index, names in enumerate(shards) if names]


def _run_shard(shard):
    index, names, count = shard
    result = subprocess.run(
        [sys.executable, '-m', 'unittest', '-q', *names],
        cwd=ROOT, capture_output=True, text=True,
    )
    return index, names, count, result


def _run_parallel(suite, workers):
    groups = _class_groups(suite)
    shards = _shards(groups, workers)
    total = sum(count for count in groups.values())
    print(f'Parallel run: {total} tests, {len(shards)} workers.')

    with ThreadPoolExecutor(max_workers=len(shards)) as pool:
        results = list(pool.map(_run_shard, shards))

    failed = False
    for index, names, count, result in sorted(results):
        print(f'\n--- worker {index + 1}: {count} tests, '
              f'{len(names)} classes ---')
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode:
            failed = True
    return 1 if failed else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=1,
                        help='run test classes in N isolated workers')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be at least 1')

    suite = unittest.TestLoader().discover(
        start_dir=str(TESTS),
        pattern='test_*.py',
    )
    if args.workers > 1:
        sys.exit(_run_parallel(suite, args.workers))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
