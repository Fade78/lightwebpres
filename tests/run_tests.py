#!/usr/bin/env python3
"""Runs the LightWebPres regression test battery.

Usage: python3 tests/run_tests.py
       python3 tests/run_tests.py --workers 8
       python3 tests/run_tests.py --no-nice
The default worker count is the process's available CPU count — every
core, with the runner niced one step below the desktop (nice +5, see
--no-nice) so the machine stays responsive under the battery.
`--workers N` overrides the count explicitly.
Non-zero exit if a test fails unexpectedly (a regression), or if a test
marked as a known bug starts passing without its @unittest.expectedFailure
decorator having been removed.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TESTS = Path(__file__).resolve().parent


def _cache_path():
    """The durations cache lives with the user, not the repository.

    The XDG cache directory is the standard home (falls back to
    ~/.cache), under a `lightwebpres/` subdirectory. Keeping it out of
    the repo is the point: durations are properties of the machine that
    measured them, and a committed list of "slow tests" would rot as
    silently as the guess it replaces.
    """
    base = os.environ.get('XDG_CACHE_HOME')
    if not base:
        base = str(Path.home() / '.cache')
    return Path(base) / 'lightwebpres' / 'test-durations.json'


def _load_durations():
    """What the last runs measured, per class, in wall-clock seconds.

    Absent or unreadable means "no information yet": the first run of a
    fresh machine (or a fresh user) orders by case count, and the cache
    is written when that run is done.
    """
    try:
        data = json.loads(_cache_path().read_text(encoding='utf-8'))
        return {name: float(sec) for name, sec in data.items()
                if isinstance(sec, (int, float)) and sec >= 0}
    except (OSError, ValueError):
        return {}


def _save_durations(durations):
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        tmp.write_text(json.dumps(durations, indent=1, sort_keys=True),
                       encoding='utf-8')
        os.replace(tmp, path)
    except OSError:
        pass


def _iter_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_cases(item)
        else:
            yield item


def _default_workers():
    """One worker per CPU available to this process.

    The battery used to leave two cores for the desktop; on this
    machine's NVMe the measured cost was the difference between 142 s
    and 181 s of wall-clock for the same suite. Every core is now the
    default, and the interference that used to justify the margin is
    handled by priority instead: the runner nices itself below the
    desktop (see _yield_priority), so the interactive work keeps its
    room without the suite losing its cores. Affinity reports the CPUs
    this process can actually schedule on; platforms without
    sched_getaffinity fall back to the portable CPU count.
    """
    try:
        available = len(os.sched_getaffinity(0))
    except AttributeError:
        available = os.cpu_count() or 1
    return max(1, available)


def _yield_priority():
    """Run the battery one step below the desktop (nice +5).

    Using every core is only polite while the machine's interactive
    work still gets the room it wants, so the whole battery — the
    parent, and every worker subprocess it spawns — lowers its
    priority. +5 is a small step: tests are background work, not a
    halt. Relative to the current value, so a runner already launched
    niced goes a little deeper instead of coming back up. Never fails:
    a restricted environment may refuse to lower itself, and that is
    fine — it only means the suite keeps the priority it was given.
    """
    try:
        os.nice(5)
    except OSError:
        pass


def _class_groups(suite):
    """Return importable test classes with their case counts.

    Classes, rather than individual methods, are the unit of work: a
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


# A class's WALL-CLOCK is the only weight that matters here: a browser
# class waits for most of its run — it drives a real Chromium (or a
# real server) and spends the run in waits, not in CPU — while a unit
# class of 37 cases is, by wall-clock, tiny and computes the whole way.
#
# The queue order decides the machine's CPU profile: put all the long
# classes first and the four workers run browsers together while the
# unit work waits; put all the short ones first and the workers burn
# their CPUs together in a burst, then sit idle while the long classes
# drain one by one — the measured shape of the run this ordering exists
# to fix. The long classes are the natural gap-fillers: they yield the
# machine while they wait, and the short work fills the gaps around
# them.
def _task_order(groups, known):
    """Order the classes: longest first, short work interleaved.

    Wall-clock measured by the LAST run is the weight (absent a
    measurement, the case count is the stand-in — a class's first run
    is a blind draw, and the cache is written when it is done). The
    queue is the schedule: the pool hands a task to the first free
    worker, so the order of the queue is the profile of the run. Two
    halves, interleaved — one long, one short, then the next long:
    the long classes (mostly browser runs, which WAIT) yield the
    machine while the short ones (mostly unit runs, which compute) fill
    the gaps, so no moment of the run is all long (CPU idle) and no
    moment is all short (CPU burst).
    """
    ordered = sorted(groups.items(), key=lambda item: (known.get(item[0], 0.0), item[1]), reverse=True)
    half = (len(ordered) + 1) // 2
    long_, short = ordered[:half], ordered[half:]
    out = []
    for i in range(half):
        out.append(long_[i])
        if i < len(short):
            out.append(short[i])
    return out


def _run_class(task):
    """Run one test class in its own Python process; the caller gives the
    next task as soon as this one returns. The class — not a batch of
    classes — is the unit of work, so a worker that draws a long class
    gets the next short one right after, and a worker whose classes all
    finished early is never idle while work remains."""
    name, count = task
    started = time.monotonic()
    clock = time.strftime('%H:%M:%S')
    result = subprocess.run(
        [sys.executable, '-m', 'unittest', '-q', name],
        cwd=ROOT, capture_output=True, text=True,
    )
    elapsed = time.monotonic() - started
    return name, count, result, elapsed, clock


def _run_parallel(suite, workers):
    groups = _class_groups(suite)
    known = _load_durations()
    tasks = _task_order(groups, known)
    total = sum(count for count in groups.values())
    run_started = time.monotonic()
    print(f'Parallel run: {total} tests, {len(tasks)} classes, '
          f'{workers} workers.')

    # One task per class, handed out to the worker that becomes free —
    # never a round-robin, never a fixed batch: a worker draws its next
    # task the moment it returns from the previous one. The queue ORDER
    # is what _task_order shapes above, and it is the whole of the
    # scheduling: the pool hands out to the first free worker, so the
    # profile of the run is the profile of the queue.
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_class, task) for task in tasks]
        for future in futures:
            name, count, result, elapsed, clock = future.result()
            results[name] = (count, result, elapsed, clock)
            # Written as each class lands, not at the end of the run: a
            # run interrupted halfway leaves the measurements it did
            # make, and the next run orders by what it has.
            _save_durations({n: results[n][2] for n in results})

    failed = False
    print()
    for name in sorted(results):
        count, result, elapsed, clock = results[name]
        print(f'{clock} {name}: {count} tests, {elapsed:.1f}s')
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        if result.returncode:
            failed = True

    # The benchmark: the classes that own the wall-clock, in order.
    wall = time.monotonic() - run_started
    slowest = sorted(results.items(), key=lambda kv: kv[1][2], reverse=True)
    print(f'\nSlowest (wall {wall:.0f}s, {len(results)} classes):')
    for name, (count, _, sec, _) in slowest[:15]:
        share = 100.0 * sec / wall
        print(f'{sec:8.1f}s {share:4.1f}%  {name}')
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
                             '(default: available CPU count, minimum 1)')
    parser.add_argument('--no-nice', action='store_true',
                        help='do not lower the runner below the desktop '
                             'priority (default: nice +5)')
    args = parser.parse_args()
    workers = _default_workers() if args.workers is None else args.workers
    if workers < 1:
        parser.error('--workers must be at least 1')
    if not args.no_nice:
        _yield_priority()

    suite = unittest.TestLoader().discover(
        start_dir=str(TESTS),
        pattern='test_*.py',
    )
    if workers > 1:
        sys.exit(_run_parallel(suite, workers))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
