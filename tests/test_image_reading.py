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
            (root / 'sources' / 'img' / 'medium.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" '
                'height="900"><rect width="1000" height="900"/></svg>',
                encoding='utf-8')
            (root / 'sources' / 'img' / 'giant.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1000" '
                'height="20000"><rect width="1000" height="20000"/></svg>',
                encoding='utf-8')
            (root / 'sources' / 'img' / 'wide.svg').write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="3840" '
                'height="2160"><rect width="3840" height="2160"/></svg>',
                encoding='utf-8')
            (root / 'sources' / 'images.md').write_text(
                '<!-- lwp:meta -->\npage_title: Responsive images\n---\n\n'
                '<!-- lwp:slide -->\nslug: image\n## Image\n\n'
                '![Responsive image](img/image.svg)\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: medium\n## Medium image\n'
                'slide-header: A visible header takes room above the title.\n'
                'summary: A visible heading and summary.\n'
                'slide-footer: A footer stays readable.\n\n'
                '![Medium image](img/medium.svg "A legible caption")\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: chrome-tall\n'
                'slide-header: Header above a large image.\n'
                'slide-footer: Footer below the same image.\n'
                '## A substantial title\n'
                'summary: This description shares the image’s slide.\n\n'
                '![Large image](img/image.svg "Its caption also needs space")\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: ratio\n'
                'slide-header: A short header.\n'
                'slide-footer: A short footer.\n'
                '## Wide image on a slide\n'
                'summary: The heading and summary need room above the image.\n'
                'fact-label: A fact box around the image.\n\n'
                'One paragraph in the box.\n\n'
                '![Wide image](img/wide.svg)\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: giant\n## Giant image\n\n'
                '![Giant image](img/giant.svg)\n\n---\n\n'
                '<!-- lwp:slide -->\nslug: impossible\n## Long text and an image\n\n'
                + ('A paragraph that takes its own line.\n\n' * 45)
                + '![Image after long text](img/medium.svg)\n', encoding='utf-8')
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

            config = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            config['appearance'] = {'presets': ['lightwebpres-docs@0.1.0/docs']}
            (root / 'series.json').write_text(json.dumps(config), encoding='utf-8')
            docs_output = root / 'docs'
            docs_env = {**env, 'LWP_IDENTITY_KITS_DIR': str(ROOT / 'examples' / 'kits')}
            built = run('build', root, '--output', docs_output, env=docs_env, cwd=ROOT)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            for variant, page in (('standard', output), ('docs preset', docs_output)):
                with self.subTest(variant=variant):
                    browser = subprocess.run(
                        ['node', str(ROOT / 'tests' / 'image_reading_browser.cjs'),
                         (page / 'images.html').as_uri()], cwd=ROOT, env=env,
                        capture_output=True, text=True, timeout=90)
                    if browser.returncode == 77:
                        self.skipTest(browser.stderr.strip())
                    self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
                    for engine in ('chromium', 'firefox'):
                        self.assertIn(engine + ': responsive image controls passed', browser.stdout)
