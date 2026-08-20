#!/usr/bin/env python3
"""Runs the LightWebPres regression test battery.

Usage: python3 tests/run_tests.py
       python3 tests/run_tests.py --workers 8
The default worker count is the process's available CPU count minus two,
with a minimum of one. `--workers N` overrides it explicitly.
Non-zero exit if a test fails unexpectedly (a regression), or if a test
marked as a known bug starts passing without its @unittest.expectedFailure
decorator having been removed.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
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


def _default_workers():
    """Leave two CPU slots for the test harness and the desktop.

    Affinity is more useful than os.cpu_count() in a container or CI runner:
    it reports the CPUs this process can actually schedule on. Platforms
    without sched_getaffinity fall back to the portable CPU count.
    """
    try:
        available = len(os.sched_getaffinity(0))
    except AttributeError:
        available = os.cpu_count() or 1
    return max(1, available - 2)


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


def _fetch_tags():
    """Bring the remote's tags in, best effort, before anything runs.

    One test compares VERSION against the newest tag reachable from HEAD
    (`test_the_number_the_tool_says_is_the_number_it_was_released_as`). It
    reads LOCAL refs on purpose — a network call inside a unit test fails
    where there is no network — and its docstring records the blind spot
    that follows: a clone that has not fetched cannot see a tag just
    pushed, and the guard stays silent for exactly as long as that lasts.

    Measured twice, a day apart, in this repository: v0.42.1 was cut and
    the tree kept announcing 0.42.1 through six further commits with a
    green suite, and v0.43.1 was cut and three further commits went out
    the same way. Both times the clone had never fetched the tag. Telling
    people to remember `git fetch --tags` did not work, which is the usual
    fate of that instruction.

    So the RUNNER fetches and the test still reads local refs. The trade
    the test makes is kept — it passes offline, in a container, on a
    checkout with no remote — and the case it cannot see is closed one
    level up, where a network call is allowed to fail quietly. Five
    seconds, no output, and any failure is ignored: not fetching is
    exactly the state we were already in.
    """
    try:
        subprocess.run(['git', '-C', str(ROOT), 'fetch', '--tags', '--quiet'],
                       capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


if __name__ == '__main__':
    _fetch_tags()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=None,
                        help='run test classes in N isolated workers '
                             '(default: available CPUs - 2, minimum 1)')
    args = parser.parse_args()
    workers = _default_workers() if args.workers is None else args.workers
    if workers < 1:
        parser.error('--workers must be at least 1')

    suite = unittest.TestLoader().discover(
        start_dir=str(TESTS),
        pattern='test_*.py',
    )
    if workers > 1:
        sys.exit(_run_parallel(suite, workers))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
