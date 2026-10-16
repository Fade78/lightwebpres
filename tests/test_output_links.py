"""Filesystem output names become URLs only at the link boundary."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from urllib.parse import quote, unquote, urlsplit

if __package__:
    from .test_lightwebpres import run
else:
    from test_lightwebpres import run

ROOT = Path(__file__).resolve().parents[1]


class _Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.links.append((attrs.get('class', ''), attrs['href']))


class OutputLinks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='output-links-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'public output'
        self.env = {'LWP_THEMES_DIR': str(self.root / 'themes'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons')}
        (self.root / 'sources').mkdir()
        self.names = ['simple space.html', 'literal%20.html', 'literal .html',
                      'name#hash.html', 'name(paren).html', "it's!.html", 'été.html',
                      'café-日本.html']
        if os.name != 'nt':
            self.names += ['name?query.html', 'name:colon.html', 'quote".html']
        entries = []
        for index, name in enumerate(self.names):
            source = 'source ' + str(index) + '.md'
            entries.append({'page_source': source, 'page_dest': name})
            (self.root / 'sources' / source).write_text(
                '<!-- lwp:meta -->\n---\n\n<!-- lwp:slide:cover -->\nslug: cover\n'
                '# Page ' + str(index) + '\nsummary: Example.\n\n---\n\n'
                '<!-- lwp:slide:full-article -->\nslug: body\narticle: long article.md\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: navigation\n', encoding='utf-8')
        (self.root / 'sources/long article.md').write_text('# Long article\n\nIncluded text.\n', encoding='utf-8')
        (self.root / 'series.json').write_text(json.dumps({'articles': entries}), encoding='utf-8')

    def cli(self, command, *options):
        result = run(command, str(self.root), '--output', str(self.output),
                     '--lang', 'en', *options, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_index_and_navigation_urls_reach_the_actual_output_names(self):
        self.cli('build')
        index = _Links((self.output / 'index.html').read_text(encoding='utf-8'))
        urls = [href for css, href in index.links if css == 'article-card']
        self.assertEqual(urls, [quote(name, safe='') for name in self.names])
        for url, name in zip(urls, self.names):
            self.assertFalse(urlsplit(url).query or urlsplit(url).fragment)
            self.assertEqual(unquote(urlsplit(url).path), name)
            self.assertIn('Included text.', (self.output / name).read_text(encoding='utf-8'))
        article = _Links((self.output / self.names[0]).read_text(encoding='utf-8'))
        self.assertEqual([href for css, href in article.links if 'series-link' in css],
                         [quote(name, safe='') for name in self.names[1:]] + ['index.html'])
        self.cli('verify')

    def test_readme_encodes_output_paths_but_keeps_route_keys_separate(self):
        for options, filename in (((), None), (('--single-html', 'my series.html'), 'my series.html')):
            with self.subTest(options=options):
                self.cli('build', *options)
                readme = (self.root / 'README.md').read_text(encoding='utf-8')
                links = re.findall(r'^\d+\. \[[^\]]+\]\(([^\s)]+)\)', readme, re.M)
                expected = [quote('public output/' + (filename or name), safe='/')
                            + ('#lwp/a/' + quote(name, safe='') if filename else '')
                            for name in self.names]
                self.assertEqual(links, expected)
                self.cli('verify', *options)

    def test_combined_views_keep_raw_filename_keys(self):
        self.cli('build', '--single-html', 'series.html')
        html = (self.output / 'series.html').read_text(encoding='utf-8')
        payload = re.search(r'<script id="lwp-series-data" type="application/json">(.*?)</script>', html, re.S)
        data = json.loads(payload[1])
        self.assertEqual(data['order'], self.names)
        self.assertEqual([view['key'] for view in data['views']], ['', *self.names])

    def test_native_browser_links_remap_without_filename_aliases(self):
        self.cli('build')
        self.cli('build', '--single-html', 'my series.html')
        try:
            checked = subprocess.run(
                ['node', str(ROOT / 'tests/output_links_e2e.cjs'),
                 (self.output / 'index.html').as_uri(),
                 (self.output / 'my series.html').as_uri(), json.dumps(self.names)],
                cwd=ROOT, env={**os.environ, 'TMPDIR': str(ROOT / 'work/tmp')},
                text=True, capture_output=True, timeout=120)
        except FileNotFoundError:
            self.skipTest('Node unavailable in supplied environment')
        if checked.returncode == 77:
            self.skipTest(checked.stderr.strip())
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        for name in ('chromium', 'firefox'):
            self.assertIn(name + ': output links preserve filename identities', checked.stdout)
