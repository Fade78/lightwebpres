"""Native DPI scaling can make 100vh fractional while clientHeight is integral."""
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


class FractionalViewportFit(unittest.TestCase):
    def test_native_fractional_windows_fit_images_before_and_after_fullscreen(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='fractional-viewport-') as temporary:
            root = Path(temporary)
            (root / 'sources/img').mkdir(parents=True)
            for name, width, height in [('wide', 3840, 2160), ('portrait', 900, 1600)]:
                (root / 'sources/img' / (name + '.svg')).write_text(
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
                    f'<rect width="{width}" height="{height}"/></svg>', encoding='utf-8')
            slides = []
            for name, body in (
                    ('figure', '![Wide](img/wide.svg "A readable caption")'),
                    ('auto', '| | |\n| --- | --- |\n| ![Wide](img/wide.svg){width=100% height=auto}'
                     ' | ![Portrait](img/portrait.svg){width=100% height=auto} |'),
                    ('fixed', '<table style="width:100%;table-layout:fixed"><tbody><tr>'
                     '<td><img src="img/wide.svg" alt="Wide" style="width:100%;height:auto"></td>'
                     '<td><img src="img/portrait.svg" alt="Portrait" style="width:100%;height:auto"></td>'
                     '</tr></tbody></table>')):
                slides.append('<!-- lwp:slide -->\nslug: ' + name
                              + '\nslide-header: Header remains visible.\n'
                              'slide-footer: Footer remains visible.\n## A complete image slide\n'
                              'summary: Preserve image ratio and chrome.\nfact-label: Images\n\n' + body)
            (root / 'sources/a.md').write_text(
                '<!-- lwp:meta -->\npage_title: Fractional viewport\n---\n\n'
                + '\n\n---\n\n'.join(slides), encoding='utf-8')
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'scroll_duration': 0},
                'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
            env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
                   'LWP_THEMES_DIR': str(root / 'themes'),
                   'LWP_IDENTITY_KITS_DIR': str(root / 'kits'),
                   'LWP_COMMONS_DIR': str(root / 'commons')}
            for output, options in [('multi', ()), ('combined', ('--single-html', 'series.html'))]:
                built = run('build', root, '--output', root / output, *options, env=env)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            try:
                checked = subprocess.run(
                    ['node', str(ROOT / 'tests/fractional_viewport_fit_e2e.cjs'),
                     (root / 'multi/a.html').as_uri(), (root / 'combined/series.html').as_uri()],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=150)
            except FileNotFoundError:
                self.skipTest('Node unavailable in supplied environment')
            if checked.returncode == 77:
                self.skipTest(checked.stderr.strip())
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            for engine in ('chromium', 'firefox'):
                self.assertIn(engine + ': native fractional viewport fitting passed', checked.stdout)
