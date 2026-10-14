"""Mixed ratios must use their own space and remain visible across fullscreen."""
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


class TableImageLayout(unittest.TestCase):
    def test_mixed_images_fit_independently_through_resize_fullscreen_and_print(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        with tempfile.TemporaryDirectory(dir=scratch, prefix='table-image-layout-') as temporary:
            root = Path(temporary)
            (root / 'sources' / 'img').mkdir(parents=True)
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'Mixed table images', 'scroll_duration': 0},
                'articles': [{'page_source': 'a.md'}],
            }), encoding='utf-8')
            for name, width, height in [('wide', 2400, 900), ('portrait', 900, 1600),
                                        ('square', 1200, 1200)]:
                (root / 'sources' / 'img' / (name + '.svg')).write_text(
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
                    f'<rect width="{width}" height="{height}"/></svg>', encoding='utf-8')
            slides = []
            for slug in ('fixed', 'natural', 'percent'):
                if slug == 'fixed':
                    body = ('<table style="width:100%;table-layout:fixed"><tbody><tr>'
                            '<td><img alt="Wide" src="img/wide.svg" style="width:100%;height:auto"></td>'
                            '<td><img alt="Portrait" src="img/portrait.svg" style="width:100%;height:auto"></td>'
                            '</tr></tbody></table>')
                else:
                    suffix = ' {width=100%; height=auto}' if slug == 'percent' else ''
                    body = ('| | |\n| --- | --- |\n'
                            f'| ![Wide](img/wide.svg){suffix} | ![Square](img/square.svg){suffix} |')
                slides.append(f'<!-- lwp:slide -->\nslug: {slug}\n## **Mixed** images\n'
                              f'summary: Two *ratios* share a row.\nfact-label: Pictures\n\n{body}\n')
            slides.append('<!-- lwp:slide -->\nslug: raw-headers\n## Raw headers\n\n'
                          '<table id="raw-blank"><thead><tr><th> </th><th><span></span></th></tr></thead>'
                          '<tbody><tr><td>Left</td><td>Right</td></tr></tbody></table>\n\n'
                          '<table id="raw-labelled"><thead><tr><th aria-label="Label"> </th></tr></thead>'
                          '<tbody><tr><td>Data</td></tr></tbody></table>\n')
            (root / 'sources' / 'a.md').write_text(
                '<!-- lwp:meta -->\npage_title: Mixed table images\n---\n\n'
                + '\n---\n\n'.join(slides), encoding='utf-8')
            for output, options in [('public', ()), ('combined', ('--single-html', 'series.html'))]:
                built = run('build', root, '--output', root / output, *options, env=env, cwd=ROOT)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            try:
                browser = subprocess.run(
                    ['node', str(ROOT / 'tests' / 'table_image_layout_e2e.cjs'),
                     (root / 'public' / 'a.html').as_uri(),
                     (root / 'combined' / 'series.html').as_uri()],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
            except FileNotFoundError:
                self.skipTest('Node unavailable in supplied environment')
            if browser.returncode == 77:
                self.skipTest(browser.stderr.strip())
            self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
            for name in ('chromium', 'firefox'):
                self.assertIn(name + ': independent table image checks passed', browser.stdout)
