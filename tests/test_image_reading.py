"""Image reading layout from a real build, with controlled CSS geometry."""
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


class ImageReadingRuntime(unittest.TestCase):
    def test_responsive_images_follow_fit_and_manual_zoom(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        with tempfile.TemporaryDirectory(dir=scratch, prefix='image-reading-') as temp:
            root = Path(temp)
            (root / 'sources').mkdir()
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'Responsive images'},
                'articles': [{'page_source': 'images.md'}],
            }), encoding='utf-8')
            (root / 'sources' / 'img').mkdir()
            (root / 'sources' / 'img' / 'image.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" '
                'height="2000"><rect width="1000" height="2000"/></svg>',
                encoding='utf-8')
            (root / 'sources' / 'images.md').write_text(
                '<!-- lwp:meta -->\npage_title: Responsive images\n---\n\n'
                '<!-- lwp:slide -->\nslug: image\n## Image\n\n'
                '![Responsive image](img/image.svg)\n', encoding='utf-8')
            output = root / 'public'
            built = run('build', root, '--output', output, env=env, cwd=ROOT)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            try:
                check = subprocess.run(
                    ['node', str(ROOT / 'tests' / 'image_reading_runtime.cjs'),
                     str(output / 'images.html')], cwd=ROOT, env=env,
                    capture_output=True, text=True, timeout=30)
            except FileNotFoundError:
                self.skipTest('Node unavailable in the supplied environment')
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertIn('Image reading runtime checks passed', check.stdout)

            browser = subprocess.run(
                ['node', str(ROOT / 'tests' / 'image_reading_browser.cjs'),
                 (output / 'images.html').as_uri()], cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=90)
            if browser.returncode == 77:
                self.skipTest(browser.stderr.strip())
            self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
            for engine in ('chromium', 'firefox'):
                self.assertIn(engine + ': responsive image controls passed', browser.stdout)
