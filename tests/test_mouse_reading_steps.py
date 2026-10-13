"""Real browser mouse reading steps on a tall slide with a table image."""

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


class MouseReadingSteps(unittest.TestCase):
    def test_plain_table_images_and_background_follow_the_reading_screen(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        with tempfile.TemporaryDirectory(dir=scratch, prefix='mouse-steps-') as tmp:
            root = Path(tmp)
            (root / 'sources' / 'img').mkdir(parents=True)
            (root / 'sources' / 'img' / 'photo.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="600" '
                'height="360"><rect width="600" height="360"/></svg>', encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'Mouse steps', 'scroll_duration': 0},
                'articles': [{'page_source': 'a.md', 'page_dest': 'a.html'},
                             {'page_source': 'b.md', 'page_dest': 'b.html'}],
            }), encoding='utf-8')
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_title: Mouse steps\n---\n\n'
                '<!-- lwp:slide -->\nslug: tall\n## A tall slide with a fact\n'
                'fact-label: An image beside text.\n\n'
                '<table id="image-table"><tbody><tr>'
                '<td><img id="plain-table-image" alt="Plain" src="img/photo.svg" '
                'width="160" height="96"></td><td>One fact alongside the image.</td>'
                '</tr><tr><td><a id="linked-image" href="https://example.invalid/">'
                '<img alt="Linked" src="img/photo.svg" width="48" height="28">'
                '</a></td><td>A linked image keeps its action.</td></tr>'
                '</tbody></table>\n\n'
                + ('A paragraph in the remaining slide.\n\n' * 55)
                + '---\n\n<!-- lwp:slide -->\nslug: after\n## Following slide\n\n'
                '---\n\n<!-- lwp:slide -->\nslug: last\n## Last slide\n', encoding='utf-8')
            (root / 'sources' / 'b.md').write_text(
                '<!-- lwp:meta -->\npage_title: Second article\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: cover\n# Other article\n', encoding='utf-8')
            for output, extra in (('public', ()), ('combined', ('--single-html', 'series.html'))):
                built = run('build', root, '--output', root / output, *extra, env=env, cwd=ROOT)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            try:
                browser = subprocess.run(
                    ['node', str(ROOT / 'tests' / 'mouse_reading_steps_e2e.cjs'),
                     (root / 'public' / 'a.html').as_uri(),
                     (root / 'combined' / 'series.html').as_uri()],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=150)
            except FileNotFoundError:
                self.skipTest('Node unavailable in the supplied environment')
            if browser.returncode == 77:
                self.skipTest(browser.stderr.strip())
            self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
            for name in ('chromium', 'firefox'):
                self.assertIn(name + ': bounded mouse reading checks passed', browser.stdout)

            series = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            series['series_meta']['scroll_duration'] = 200
            (root / 'series.json').write_text(json.dumps(series), encoding='utf-8')
            for output, extra in (('animated', ()),
                                  ('animated-combined', ('--single-html', 'series.html'))):
                built = run('build', root, '--output', root / output, *extra,
                            env=env, cwd=ROOT)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            animated = subprocess.run(
                ['node', str(ROOT / 'tests' / 'mouse_reading_animation_e2e.cjs'),
                 (root / 'animated' / 'a.html').as_uri(),
                 (root / 'animated-combined' / 'series.html').as_uri()],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
            self.assertEqual(animated.returncode, 0, animated.stdout + animated.stderr)
            for name in ('chromium', 'firefox'):
                self.assertIn(name + ': timed mouse reading checks passed', animated.stdout)
