"""The entry point, tutorial and illustrations remain usable together."""
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent


class TheDocumentationDeliversItsExamples(unittest.TestCase):
    def test_compiled_chapter_links_move_the_reader_not_just_the_hash(self):
        env = os.environ.copy()
        try:
            npm = subprocess.run(['npm', 'root', '-g'], capture_output=True,
                                 text=True, timeout=30)
            if npm.returncode == 0:
                env['NODE_PATH'] = npm.stdout.strip()
            result = subprocess.run(['node', str(ROOT / 'tests/documentation_e2e.cjs')],
                                    env=env, capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest('Node/npm unavailable')
        if result.returncode == 77 or "Executable doesn't exist" in result.stderr:
            self.skipTest('Playwright/Chromium unavailable')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_personal_article_extends_the_quickstart_and_verifies(self):
        guide = (ROOT / 'GUIDE.md').read_text(encoding='utf-8')
        guide = guide.split('## 2. Make your first personal article\n', 1)[1].split(
            '## 3. Understand page anatomy\n', 1)[0]
        source = re.search(r'```markdown\n(<!-- lwp:meta -->.*?)\n```',
                           guide, re.S).group(1) + '\n'
        example = ROOT / 'examples/first-article'
        self.assertEqual(source, (example / 'sources/first-page.md').read_text())
        json_blocks = [json.loads(block) for block in
                       re.findall(r'```json\n(.*?)\n```', guide, re.S)]
        entry = {'page_source': 'first-page.md'}
        self.assertIn(entry, json_blocks)
        self.assertIn(json.loads((example / 'series.json').read_text()), json_blocks)
        env = {k: v for k, v in os.environ.items() if not k.startswith('LWP_')}
        with tempfile.TemporaryDirectory() as tmp:
            series = Path(tmp) / 'my-series'

            def run(*args):
                result = subprocess.run(
                    [sys.executable, str(ROOT / 'lightwebpres'), *args],
                    cwd=tmp, env=env, text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result

            run('init', str(series))
            run('demo', str(series), '--lang', 'en')
            self.assertTrue((series / 'public/index.html').is_file())
            config = json.loads((series / 'series.json').read_text())
            self.assertEqual(len(config['articles']), 3)
            config['articles'].append(entry)
            (series / 'series.json').write_text(json.dumps(config))
            (series / 'sources/first-page.md').write_text(source, encoding='utf-8')
            run('build', str(series), '--lang', 'en')
            run('audit', str(series), '--lang', 'en')
            run('verify', str(series), '--lang', 'en')
            index = (series / 'public/index.html').read_text()
            article = (series / 'public/first-page.html').read_text()
            self.assertIn('first-page.html', index)
            self.assertIn('id="travels-with-the-page"', article)
            for demo in config['articles'][:3]:
                self.assertIn(demo.get('page_dest', demo['page_source'][:-3] + '.html'),
                              article)

    def test_product_capture_inputs_and_images_have_not_changed(self):
        manifest = json.loads((ROOT / 'generated/product-captures.json').read_text())
        expected_inputs = {
            'lightwebpres', 'tools/screenshot-product.cjs',
            'examples/first-article/series.json',
        }
        for directory in ('sources', 'templates'):
            expected_inputs.update(p.relative_to(ROOT).as_posix() for p in
                                   (ROOT / 'examples/first-article' / directory).rglob('*')
                                   if p.is_file())
        self.assertEqual(set(manifest['inputs']), expected_inputs)
        for name, expected in manifest['inputs'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                             expected, f'{name}: regenerate product captures')
        self.assertEqual([c['name'] for c in manifest['captures']], ['responsive'])
        capture = manifest['captures'][0]
        image = (ROOT / capture['file']).read_bytes()
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', image[16:24]), (1280, 760))
        self.assertEqual((capture['width'], capture['height']), (1280, 760))
        self.assertEqual(hashlib.sha256(image).hexdigest(), capture['sha256'])
        self.assertEqual(
            [(view['name'], view['width'], view['height'], view['isMobile'],
              view['hasTouch'], view['deviceScaleFactor'])
             for view in capture['viewports']],
            [('landscape', 960, 540, False, False, 1),
             ('mobile', 390, 844, True, True, 1)])

    def test_document_links_reach_files_and_real_headings(self):
        for name in ('README.md', 'GUIDE.md', 'examples/first-article/README.md'):
            document = ROOT / name
            text = re.sub(r'^```[^\n]*\n.*?^```\s*$', '',
                          document.read_text(encoding='utf-8'), flags=re.M | re.S)
            text = re.sub(r'`[^`\n]+`', '', text)
            targets = re.findall(r'\]\(([^\s)]+)\)', text)
            targets += re.findall(r'(?:src|href)="([^"]+)"', text)
            for target in targets:
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue
                dest = document.parent / unquote(url.path) if url.path else document
                self.assertTrue(dest.exists(), f'{name}: missing {target}')
                if url.fragment and dest.suffix == '.md':
                    body = re.sub(r'^```[^\n]*\n.*?^```\s*$', '',
                                  dest.read_text(encoding='utf-8'), flags=re.M | re.S)
                    anchors = [re.sub(r'[^\w -]', '', title.lower()).replace(' ', '-')
                               for title in re.findall(r'^#{1,6} (.+)$', body, re.M)]
                    self.assertIn(url.fragment, anchors, f'{name}: missing {target}')

    def test_compiled_guide_has_chapter_targets_and_packaged_images(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids, self.links, self.images = set(), [], []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'id' in attrs:
                    self.ids.add(attrs['id'])
                if tag == 'a':
                    self.links.append(attrs.get('href', ''))
                if tag == 'img':
                    self.images.append(attrs.get('src', ''))

        parser = Links()
        output = ROOT / 'generated/guide'
        parser.feed((output / 'guide.html').read_text(encoding='utf-8'))
        chapters = [link[1:] for link in parser.links if re.match(r'^#\d+-', link)]
        self.assertEqual(len(chapters), 11)
        for chapter in chapters:
            self.assertIn(chapter, parser.ids)
        for name in ('product-responsive.png',):
            self.assertIn('img/' + name, parser.images)
            self.assertEqual((output / 'img' / name).read_bytes(),
                             (ROOT / 'generated' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
