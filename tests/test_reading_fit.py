"""Real-browser reading layout checks; all fixture and browser scratch stays local."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class ReadingFitBrowser(unittest.TestCase):
    def test_reading_layout_in_a_real_build(self):
        scratch = ROOT / 'work' / 'tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, 'TMPDIR': str(scratch)}
        try:
            probe = subprocess.run(
                ['node', '-e', "require('playwright')"], env=env,
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            self.skipTest('Node/Playwright unavailable on supplied PATH: ' + str(exc))
        if probe.returncode:
            self.skipTest('Playwright unavailable in supplied environment: ' + probe.stderr)

        with tempfile.TemporaryDirectory(prefix='reading-fit-', dir=scratch) as temp:
            root = Path(temp) / 'series'

            def cli(*args):
                done = subprocess.run([sys.executable, str(ROOT / 'lightwebpres'), *args],
                                      env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                return done.stdout

            cli('init', str(root))
            (root / 'series.json').write_text(json.dumps({
                'series_meta': {'title': 'Reading fixture'},
                'presentation_presets': ['commons/roomy'],
                'articles': [{'page_source': 'reading.md'}],
            }), encoding='utf-8')
            presets = root / 'templates' / 'commons' / 'presets'
            presets.mkdir(parents=True, exist_ok=True)
            (presets / 'roomy.json').write_text(json.dumps({
                'schema': 'lightwebpres.commons-preset/1', 'id': 'roomy',
                'label': 'Roomy', 'description': 'Alternate runtime presentation',
                'theme': 'print-oldpress',
            }), encoding='utf-8')
            article = '''<!-- lwp:meta -->
page_title: Reading fixture
---
<!-- lwp:slide -->
slug: short
## Short heading

<p class="probe-text">Short text with <strong>relative emphasis</strong>.</p>

---
<!-- lwp:slide -->
slug: dense
## Dense heading

<p class="probe-text">DENSE</p>

---
<!-- lwp:slide -->
slug: tables
## Local table scrolling

<table id="raw-table"><caption>Wide measurements</caption><tbody><tr><td><a id="table-link" href="#short">Preserved link</a></td><td>Other column</td></tr></tbody></table>

| Semantic | Table |
| --- | --- |
| A | B |

---
<!-- lwp:slide -->
slug: objects
## Authored image geometry

<figure id="author-figure"><img id="author-image" width="1000" height="700" style="zoom: 1.2; width: 1000px; height: 700px" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1000' height='700'%3E%3Crect width='1000' height='700' fill='gray'/%3E%3C/svg%3E" alt="Fixture"><figcaption>Authored caption</figcaption></figure>

<iframe id="author-player" title="Player" style="zoom: 1.1" src="about:blank"></iframe>

---
<!-- lwp:slide -->
slug: inherited
tags: regression

<p id="inherited-container" style="font-size: 40px; line-height: 60px; margin: 0"><strong>INHERITED</strong></p>

<div hidden><span id="hidden-type">Hidden text</span></div>

<svg width="20" height="20" style="position: absolute"><text id="svg-type" style="font-size: 14px">SVG</text></svg>

---
<!-- lwp:slide -->
slug: paired
tags: regression

<div id="paired-images"><img alt="First" width="100" height="300" style="display: block; width: 100px; height: 300px; zoom: 1" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='300'/%3E"><img alt="Second" width="100" height="300" style="display: block; width: 100px; height: 300px; zoom: 1" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='300'/%3E"></div>

---
<!-- lwp:slide:full-article -->
slug: impossible
tags: long
article: long.md
'''
            article = article.replace('DENSE', '<br>'.join(['A measured line of text.'] * 16))
            article = article.replace('INHERITED', '<br>'.join(['Emphasized line.'] * 11))
            (root / 'sources' / 'long.md').write_text(
                '# Long article\n\n' + '\n\n'.join(['Paragraph of long-form prose.'] * 55),
                encoding='utf-8')
            (root / 'sources' / 'reading.md').write_text(article, encoding='utf-8')
            (root / 'templates' / 'custom.css').write_text(
                '.probe-text { font-size: 30px; line-height: 36px; }\n'
                '.probe-text strong { font-size: 1.2em; }\n'
                '#raw-table, .comparison-table { min-width: 1600px; }\n', encoding='utf-8')
            cli('build', str(root), '--themes', 'print-ink,dracula', '--scroll-duration', '0')
            config = json.loads((root / 'series.json').read_text(encoding='utf-8'))
            config['series_meta']['reading'] = {
                'text_fit': 'uniform', 'table_mode': 'scroll',
                'table_shrink': True, 'object_shrink': True,
                'min_text_scale': .9, 'min_table_scale': .93, 'min_object_scale': .94,
            }
            (root / 'series.json').write_text(json.dumps(config), encoding='utf-8')
            cli('build', str(root), '--output', str(root / 'public' / 'configured'))
            config['series_meta']['reading']['table_mode'] = 'overflow'
            (root / 'series.json').write_text(json.dumps(config), encoding='utf-8')
            cli('build', str(root), '--output', str(root / 'public' / 'overflow'))
            handler = partial(QuietHandler, directory=str(root / 'public'))
            with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    result = subprocess.run(
                        ['node', str(ROOT / 'tests' / 'reading_fit_e2e.cjs'),
                         'http://127.0.0.1:%s/reading.html' % server.server_port,
                         'http://127.0.0.1:%s/configured/reading.html' % server.server_port,
                         'http://127.0.0.1:%s/overflow/reading.html' % server.server_port],
                        env=env, capture_output=True, text=True, timeout=180)
                finally:
                    server.shutdown()
                    thread.join()
            if result.returncode == 77:
                self.skipTest(result.stderr.strip())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertGreaterEqual(len(report['checks']), 12, report)
            self.assertEqual([sample['factor'] for sample in report['imageUnits']], [.5, 1, 2])
            for sample in report['imageUnits']:
                images = {image['id']: image for image in sample['images']}
                for image_id, width, height in [('unit-em', 80, 40), ('unit-authored-zoom', 64, 32)]:
                    self.assertEqual(images[image_id]['width'], width * sample['factor'])
                    self.assertEqual(images[image_id]['height'], height * sample['factor'])


if __name__ == '__main__':
    unittest.main()
