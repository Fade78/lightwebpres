"""The entry point, tutorial and illustrations remain usable together."""
import hashlib
import importlib.util
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
_builder_spec = importlib.util.spec_from_file_location(
    'lwp_guide_builder', ROOT / 'tools' / 'build_guide.py')
_builder = importlib.util.module_from_spec(_builder_spec)
_builder_spec.loader.exec_module(_builder)
GUIDE_IMAGES = _builder.GUIDE_IMAGES
heading_slug = _builder.heading_slug
markdown_lines = _builder.markdown_lines
prepare_article = _builder.prepare_article
ROUTES = [
    '1. Create content',
    '2. Organize a documentary collection',
    '3. Design and compose identities',
    '4. Read, present and share',
    '5. Publish and maintain',
    '6. Integrate and automate',
]


class DocumentHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.images, self.headings = [], [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
            if re.fullmatch(r'h[1-6]', tag):
                self.headings.append((tag, attrs['id']))
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if tag == 'img':
            self.images.append(attrs.get('src', ''))
        if tag in ('img', 'source') and attrs.get('srcset'):
            self.images.extend(part.strip().split()[0]
                               for part in attrs['srcset'].split(',') if part.strip())


def markdown_headings(text):
    return [(len(match[1]), match[2]) for line, protected in markdown_lines(text)
            if not protected for match in [re.match(r'^(#{1,6}) (.+)$', line)] if match]


class TheDocumentationDeliversItsExamples(unittest.TestCase):
    def test_compiled_chapter_links_move_the_reader_not_just_the_hash(self):
        env = os.environ.copy()
        try:
            npm = subprocess.run(['npm', 'root', '-g'], capture_output=True,
                                 text=True, timeout=30)
            if npm.returncode == 0:
                env['NODE_PATH'] = npm.stdout.strip()
            result = subprocess.run(['node', str(ROOT / 'tests/documentation_e2e.cjs')],
                                    env=env, capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            self.skipTest('Node/npm unavailable')
        if result.returncode == 77 or "Executable doesn't exist" in result.stderr:
            self.skipTest('Playwright/Chromium unavailable')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_personal_article_extends_the_quickstart_and_verifies(self):
        guide = (ROOT / 'GUIDE.md').read_text(encoding='utf-8')
        start, end = '<!-- example:first-article -->', '<!-- /example:first-article -->'
        self.assertEqual(guide.count(start), 1)
        self.assertEqual(guide.count(end), 1)
        self.assertLess(guide.index(start), guide.index(end))
        guide = guide.split(start, 1)[1].split(end, 1)[0]
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

    def test_native_selection_is_implicit_only_when_not_written(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('LWP_')}
        with tempfile.TemporaryDirectory() as tmp:
            env.update(XDG_DATA_HOME=tmp, APPDATA=tmp)

            def run(*args):
                result = subprocess.run(
                    [sys.executable, str(ROOT / 'lightwebpres'), *map(str, args)],
                    cwd=tmp, env=env, text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            for explicit in (False, True):
                with self.subTest(explicit=explicit):
                    series = Path(tmp) / ('explicit' if explicit else 'implicit')
                    run('init', series, *(['--preset', 'builtin/standard'] if explicit else []))
                    meta = json.loads((series / 'series.json').read_text())['series_meta']
                    if explicit:
                        self.assertEqual(meta['presentation_preset'], 'builtin/standard')
                    else:
                        self.assertNotIn('presentation_preset', meta)
                    report = json.loads(run('series', 'preset', series, '--format', 'json'))
                    self.assertEqual(report['schema'], 'lightwebpres.series-preset/2')
                    self.assertEqual(report['preset']['schema'], 'lightwebpres.presentation-preset/2')
                    self.assertTrue(report['preset']['native_renderer'])
                    self.assertNotIn('default', report['preset'])
                    self.assertEqual(report['preset']['selector'], 'builtin/standard')
                    self.assertEqual(report['preset']['theme']['id'], 'light')
                    self.assertEqual(report['preset']['theme']['label'], 'Light')
                    theme = json.loads(run('series', 'theme', series, '--format', 'json'))
                    self.assertEqual(theme['schema'], 'lightwebpres.theme-info/6')
                    self.assertIsNone(theme['target']['theme'])
                    self.assertEqual(theme['target']['presentation_preset'], 'builtin/standard')
                    self.assertEqual((theme['label'], theme['source']), ('Light', 'builtin'))
                    run('series', 'preset', 'set', series, '--preset', 'builtin/standard')
                    meta = json.loads((series / 'series.json').read_text())['series_meta']
                    self.assertEqual(meta['presentation_preset'], 'builtin/standard')
                    for resource in ('kits', 'commons', 'themes'):
                        self.assertFalse((series / 'templates' / resource).exists())

    def test_documented_composition_and_commons_json_build(self):
        for document in ('GUIDE.md', 'specifications.md'):
            with self.subTest(document=document), tempfile.TemporaryDirectory() as tmp:
                blocks = re.findall(r'```json\n(.*?)\n```',
                                    (ROOT / document).read_text(encoding='utf-8'), re.S)
                examples = {}
                for schema in ('lightwebpres.kit-composition/1',
                               'lightwebpres.commons-preset/1'):
                    matches = [json.loads(block) for block in blocks
                               if re.search(r'"schema"\s*:\s*"' + re.escape(schema) + '"', block)]
                    self.assertEqual(len(matches), 1, f'{document}: expected one {schema} example')
                    examples[schema] = matches[0]
                recipe = examples['lightwebpres.kit-composition/1']
                commons = examples['lightwebpres.commons-preset/1']
                root = Path(tmp)
                env = {k: v for k, v in os.environ.items() if not k.startswith('LWP_')}
                env.update(XDG_DATA_HOME=tmp, APPDATA=tmp,
                           LWP_IDENTITY_KITS_DIR=str(root / 'kits'),
                           LWP_COMMONS_DIR=str(root / 'commons'))

                def run(*args):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / 'lightwebpres'), *map(str, args)],
                        cwd=tmp, env=env, text=True, capture_output=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return result.stdout

                def add_article(target):
                    config_path = target / 'series.json'
                    config = json.loads(config_path.read_text())
                    config['articles'] = [{'page_source': 'first-page.md'}]
                    config_path.write_text(json.dumps(config), encoding='utf-8')
                    source = ROOT / 'examples/first-article/sources/first-page.md'
                    (target / 'sources/first-page.md').write_text(
                        source.read_text(encoding='utf-8'), encoding='utf-8')

                recipe_path = root / 'recipe.json'
                recipe_path.write_text(json.dumps(recipe), encoding='utf-8')
                run('kit', 'compose', recipe_path, '--output', 'kits', '--dry-run')
                self.assertFalse((root / 'kits').exists())
                run('kit', 'compose', recipe_path, '--output', 'kits')
                manifest = recipe['manifest']
                kit = root / 'kits' / manifest['id'] / manifest['version']
                self.assertEqual(json.loads((kit / 'manifest.json').read_text()), manifest)
                selector = f"{manifest['id']}@{manifest['version']}/{manifest['default_preset']}"
                report = json.loads(run('preset', 'show', selector, '--format', 'json'))
                self.assertEqual(report['selector'], selector)
                series = root / 'my-brief'
                run('init', series, '--preset', selector)
                add_article(series)
                run('build', series, '--lang', 'en')
                run('verify', series, '--lang', 'en')
                self.assertIn('class="lwp-presentation--brief"',
                              (series / 'public/first-page.html').read_text())

                descriptor = root / 'commons' / 'presets' / f"{commons['id']}.json"
                descriptor.parent.mkdir(parents=True)
                descriptor.write_text(json.dumps(commons), encoding='utf-8')
                commons_selector = f"commons/{commons['id']}"
                commons_series = root / 'my-commons'
                run('init', commons_series, '--preset', commons_selector)
                run('series', 'preset', 'set', series, '--preset', commons_selector)
                for target in (commons_series, series):
                    vendored = target / 'templates/commons/presets' / descriptor.name
                    self.assertEqual(json.loads(vendored.read_text()), commons)
                    self.assertFalse((target / 'templates/themes').exists())
                self.assertFalse((commons_series / 'templates/kits').exists())

                env['LWP_COMMONS_DIR'] = str(root / 'empty-commons')
                env['LWP_IDENTITY_KITS_DIR'] = str(root / 'empty-kits')
                add_article(commons_series)
                run('build', commons_series, '--lang', 'en')
                run('build', series, '--lang', 'en')
                for target in (commons_series, series):
                    report = json.loads(run('series', 'preset', target, '--format', 'json'))
                    self.assertEqual(report['preset']['selector'], commons_selector)
                    self.assertEqual(report['preset']['resource_collection'], 'commons')
                    self.assertIsNone(report['preset']['starter'])
                    run('verify', target, '--lang', 'en')

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
        documents = {ROOT / 'README.md', ROOT / 'GUIDE.md'}
        documents.update((ROOT / 'examples').rglob('README.md'))
        documents.update((ROOT / 'agent').rglob('*.md'))
        for document in sorted(documents):
            name = document.relative_to(ROOT).as_posix()
            text = '\n'.join(line for line, protected in markdown_lines(
                document.read_text(encoding='utf-8')) if not protected)
            text = re.sub(r'`[^`\n]+`', '', text)
            targets = re.findall(r'\]\(<?([^\s)>]+)>?(?:\s+"[^"]*")?\)', text)
            targets += re.findall(r'^ {0,3}\[[^\]^]+\]:\s*<?([^\s>]+)', text, re.M)
            parser = DocumentHTML()
            parser.feed(text)
            targets += parser.links + parser.images
            for target in targets:
                with self.subTest(document=name, target=target):
                    url = urlsplit(target)
                    if url.scheme or url.netloc:
                        continue
                    dest = document.parent / unquote(url.path) if url.path else document
                    self.assertTrue(dest.exists(), f'{name}: missing {target}')
                    if url.fragment and dest.suffix.lower() in ('.md', '.html', '.htm'):
                        body = dest.read_text(encoding='utf-8')
                        anchors = []
                        if dest.suffix.lower() == '.md':
                            anchors = [heading_slug(title) for _, title in markdown_headings(body)]
                            body = '\n'.join(line for line, protected in markdown_lines(body)
                                             if not protected)
                        parser = DocumentHTML()
                        parser.feed(body)
                        self.assertIn(unquote(url.fragment), anchors + parser.ids,
                                      f'{name}: missing {target}')

    def test_guide_adaptation_preserves_examples_and_maps_only_known_images(self):
        for fence in ('```', '````', '~~~'):
            with self.subTest(fence=fence):
                example = (f'{fence}markdown\n## Not a chapter\n```\n'
                           '### Not a subsection\n[example](#not-a-target)\n'
                           '![example](generated/not-a-real-image.png)\n'
                           f'{fence}\n') if fence != '```' else (
                               '```markdown\n## Not a chapter\n'
                               '![example](generated/not-a-real-image.png)\n```\n')
                text = '## 1. Create content\n### Read, then build!\n' + example
                text += '`![Inline example](img/not-a-real-image.png)`\n'
                text += '[Read](#read-then-build)\n'
                for source in GUIDE_IMAGES:
                    text += f'![A real image]({source} "Caption")\n'
                text += '<img src="generated/product-responsive.png" alt="Browser capture">\n'
                article, images = prepare_article(text)
                self.assertIn(example, article)
                self.assertIn('`![Inline example](img/not-a-real-image.png)`', article)
                self.assertEqual(markdown_headings(text), [
                    (2, '1. Create content'), (3, 'Read, then build!')])
                self.assertIn('<h3 id="read-then-build" tabindex="-1">', article)
                self.assertIn('<a href="#read-then-build">Read</a>', article)
                self.assertEqual(images, set(GUIDE_IMAGES))
                for target in GUIDE_IMAGES.values():
                    self.assertIn(target, article)
        for unknown in ('generated/product-unknown.png', 'img/unknown.png'):
            for markup in (f'![Unknown]({unknown})', f"<img src='{unknown}'>"):
                with self.subTest(markup=markup), self.assertRaisesRegex(
                        ValueError, 'unknown guide image'):
                    prepare_article(markup)
        article, images = prepare_article('![Remote](https://example.org/image.png)\n')
        self.assertEqual(images, set())
        self.assertIn('https://example.org/image.png', article)
        _, images = prepare_article((ROOT / 'GUIDE.md').read_text(encoding='utf-8'))
        self.assertEqual(images, set(GUIDE_IMAGES))

    def test_compiled_guide_has_chapter_targets_and_packaged_images(self):
        headings = markdown_headings((ROOT / 'GUIDE.md').read_text(encoding='utf-8'))
        self.assertEqual([title for level, title in headings if level == 2], ROUTES)
        expected_chapters = {heading_slug(title) for title in ROUTES}
        deck = (ROOT / 'tools/guide-deck.md').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'^source: (.+)$', deck, re.M), [
            f'<a href="#{heading_slug(title)}">Guide, route {title.replace(". ", ": ", 1)}</a>'
            for title in ROUTES])
        parser = DocumentHTML()
        output = ROOT / 'generated/guide'
        parser.feed((output / 'guide.html').read_text(encoding='utf-8'))
        chapters = {link[1:] for link in parser.links if re.match(r'^#\d+-', link)}
        self.assertEqual(len(chapters), 6)
        self.assertEqual(chapters, expected_chapters)
        self.assertEqual(parser.headings, [(f'h{level}', heading_slug(title))
                                           for level, title in headings])
        self.assertEqual(len(parser.ids), len(set(parser.ids)), 'duplicate HTML IDs')
        for link in parser.links:
            if link.startswith('#'):
                self.assertIn(unquote(link[1:]), parser.ids)
        self.assertIn('#guide-complet', parser.links)
        self.assertEqual(set(GUIDE_IMAGES), {
            'generated/product-responsive.png', 'generated/appearance-choices.png',
            'generated/identity-composition.png',
        })
        for source, target in GUIDE_IMAGES.items():
            self.assertIn(target, parser.images)
            self.assertEqual((output / target).read_bytes(), (ROOT / source).read_bytes())

    def test_theme_contact_sheet_pins_equal_outer_tracks(self):
        script = (ROOT / 'tools/screenshot-gallery.cjs').read_text(encoding='utf-8')
        fixed_tracks = 'grid-template-columns: repeat(${COLUMNS}, ${ROW}px) !important;'
        self.assertEqual(script.count(fixed_tracks), 2)
        self.assertNotIn(
            'grid-template-columns: repeat(${COLUMNS}, max-content) !important;', script)


if __name__ == '__main__':
    unittest.main()
