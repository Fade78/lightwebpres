"""End-to-end test for web/index.html (the Pyodide-in-the-browser build).

Real browser, real Pyodide, real zip upload/download — this exercises the
actual deliverable, not a simulation. Requires Node.js with the `playwright`
package (and its Chromium browser) available; skips cleanly if either is
missing, since this is a heavier dependency than the rest of the suite (the
core lightwebpres tool itself stays stdlib-only, see specifications.md §13.4
— only this optional browser wrapper depends on Node/Playwright/Pyodide).

Run with: python3 tests/run_tests.py
"""

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_E2E_SCRIPT = Path(__file__).resolve().parent / 'web_e2e.cjs'
FILE_PROTOCOL_GUARD_SCRIPT = Path(__file__).resolve().parent / 'file_protocol_guard_e2e.cjs'
STORAGE_UNAVAILABLE_SCRIPT = Path(__file__).resolve().parent / 'storage_unavailable_e2e.cjs'
LWP_LOOKUP_SCRIPT = Path(__file__).resolve().parent / 'lightwebpres_lookup_e2e.cjs'
GALLERY_FACETS_SCRIPT = Path(__file__).resolve().parent / 'themes_gallery_facets_e2e.cjs'
GALLERY_PANELS_SCRIPT = Path(__file__).resolve().parent / 'gallery_panels_e2e.cjs'
NOTE_PROPERTIES_SCRIPT = Path(__file__).resolve().parent / 'note_properties_e2e.cjs'
SLIDE_TAGS_SCRIPT = Path(__file__).resolve().parent / 'slide_tags_e2e.cjs'
ARTICLE_TAGS_SCRIPT = Path(__file__).resolve().parent / 'article_tags_e2e.cjs'
TAG_REPORT_SCRIPT = Path(__file__).resolve().parent / 'tag_report_e2e.cjs'


def _node_playwright_available():
    if shutil.which('node') is None:
        return False, 'node not found on PATH'
    npm_root = subprocess.run(
        ['npm', 'root', '-g'], capture_output=True, text=True,
    ).stdout.strip()
    check = subprocess.run(
        ['node', '-e', "require('playwright')"],
        capture_output=True, text=True,
        env={**__import__('os').environ, 'NODE_PATH': npm_root},
    )
    if check.returncode != 0:
        return False, 'playwright not resolvable via npm root -g'
    return True, npm_root


AVAILABLE, NPM_ROOT_OR_REASON = _node_playwright_available()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def _make_test_zip(zip_path):
    """A minimal but complete series: one article, one full-article body."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'sources').mkdir()
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}],
        }), encoding='utf-8')
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Web test\n'
            'nav_title: A\nnav_desc: A\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: c1\nkicker: T\n# Web build test\n'
            'summary: Built entirely in the browser.\n\n---\n\n'
            '<!-- lwp:slide:full-article -->\nslug: c2\narticle: a_article.md\n',
            encoding='utf-8',
        )
        (root / 'sources' / 'a_article.md').write_text(
            '# Full article\n\nBuilt via Pyodide, in-browser.\n',
            encoding='utf-8',
        )
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in root.rglob('*'):
                if f.is_file():
                    zf.write(f, f.relative_to(root))


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class WebBuild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(REPO_ROOT)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)

    def _build(self, lang):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / 'series.zip'
            out_path = Path(tmp) / 'public.zip'
            _make_test_zip(zip_path)

            result = subprocess.run(
                ['node', str(WEB_E2E_SCRIPT), 'http://127.0.0.1:%d' % self.port,
                 str(zip_path), lang, str(out_path)],
                capture_output=True, text=True,
                env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(out_path.exists(), 'no file was downloaded')

            with zipfile.ZipFile(out_path) as zf:
                names = zf.namelist()
                self.assertIn('a.html', names)
                self.assertIn('index.html', names)
                html = zf.read('a.html').decode('utf-8')
            return html

    def test_build_in_browser_french(self):
        html = self._build('fr')
        self.assertIn('Built entirely in the browser.', html)
        self.assertIn('Planche précédente', html)

    def test_build_in_browser_english(self):
        html = self._build('en')
        self.assertIn('Built entirely in the browser.', html)
        self.assertIn('Previous slide', html)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class WebStorageResilience(unittest.TestCase):
    """Storage policy failures must not prevent the page from booting."""

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *a: _QuietHandler(*a, directory=str(REPO_ROOT)),
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)

    def test_page_boots_when_storage_access_throws(self):
        result = subprocess.run(
            ['node', str(STORAGE_UNAVAILABLE_SCRIPT),
             'http://127.0.0.1:%d' % self.port],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'Connection data cleared.')
        self.assertFalse(report['zipDisabled'])
        self.assertFalse(report['pullDisabled'])
        self.assertEqual(report['errors'], [])


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class SlideTagsRuntime(unittest.TestCase):
    """The tag menu must change the visible slide subset and persist it."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name)
        (root / 'sources').mkdir()
        (root / 'series.json').write_text(json.dumps({
            'articles': [{'page_source': 'a.md'}],
        }), encoding='utf-8')
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Slide tags\n'
            'nav_title: Tags\nnav_desc: Runtime tags\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: c3\nkicker: Shared\n# Shared\n'
            'summary: Shared cover.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: c4\ntags: en\nkicker: English\n'
            '## English\nsummary: English variant.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: c5\ntags: fr\nkicker: Français\n'
            '## Français\nsummary: French variant.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: c6\nkicker: Common\n## Common\n'
            'summary: Shared content.\n',
            encoding='utf-8',
        )
        output_dir = root / 'public'
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / 'lightwebpres'), 'build',
             str(root), '--output', str(output_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        cls.httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *a: _QuietHandler(*a, directory=str(output_dir)),
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_menu_switches_and_persists_variant(self):
        result = subprocess.run(
            ['node', str(SLIDE_TAGS_SCRIPT),
             'http://127.0.0.1:%d/a.html' % self.port],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class ArticleTagsRuntime(unittest.TestCase):
    """Article gates and slide availability must agree on index and nav."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        root = Path(cls.tmpdir.name)
        (root / 'sources').mkdir()
        (root / 'series.json').write_text(json.dumps({
            'series_meta': {'default_tag': 'fr'},
            'articles': [
                {'page_source': 'a.md', 'page_dest': 'a.html',
                 'nav_title': 'A', 'nav_desc': 'French'},
                {'page_source': 'b.md', 'page_dest': 'b.html',
                 'nav_title': 'B', 'nav_desc': 'English'},
                {'page_source': 'c.md', 'page_dest': 'c.html',
                 'nav_title': 'C', 'nav_desc': 'Shared'},
            ],
        }), encoding='utf-8')
        (root / 'sources' / 'a.md').write_text(
            '<!-- lwp:meta -->\ntags: fr\npage_title: A\n'
            'nav_title: A\nnav_desc: French\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: a-cover\ntags: fr\n# A\n'
            'summary: French.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: a-nav\ntags: fr\n',
            encoding='utf-8')
        (root / 'sources' / 'b.md').write_text(
            '<!-- lwp:meta -->\ntags: en\npage_title: B\n'
            'nav_title: B\nnav_desc: English\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: b-cover\ntags: en\n# B\n'
            'summary: English.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: b-nav\ntags: en\n',
            encoding='utf-8')
        (root / 'sources' / 'c.md').write_text(
            '<!-- lwp:meta -->\npage_title: C\nnav_title: C\nnav_desc: Shared\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: c-cover\ntags: fr\n# C\nsummary: Shared.\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: c-nav\ntags: fr\n',
            encoding='utf-8')
        output_dir = root / 'public'
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / 'lightwebpres'), 'build',
             str(root), '--output', str(output_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        cls.httpd = HTTPServer(
            ('127.0.0.1', 0),
            lambda *a: _QuietHandler(*a, directory=str(output_dir)),
        )
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_article_and_slide_tags_filter_index_and_nav(self):
        result = subprocess.run(
            ['node', str(ARTICLE_TAGS_SCRIPT),
             'http://127.0.0.1:%d/index.html' % self.port,
             'http://127.0.0.1:%d/a.html' % self.port],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        report = subprocess.run(
            [sys.executable, str(REPO_ROOT / 'lightwebpres'), 'series', 'tags',
             str(Path(self.tmpdir.name)), '--format', 'json'],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
        report_json = json.loads(report.stdout)
        article_urls = [
            'http://127.0.0.1:%d/%s.html' % (self.port, slug)
            for slug in ('a', 'b', 'c')
        ]
        result = subprocess.run(
            ['node', str(TAG_REPORT_SCRIPT),
             'http://127.0.0.1:%d/index.html' % self.port,
             json.dumps(report_json['tags']), *article_urls],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class FileProtocolGuard(unittest.TestCase):
    """§23.6: opening index.html as a local file:// page (the natural
    thing to do with a self-contained static page) can never actually
    load Pyodide — browsers block its module/asset fetches under the
    file:// origin. init() must detect this up front and show a clear,
    actionable, one-click-copyable command instead of letting Pyodide fail
    with a raw, confusing browser error."""

    def test_index_html_shows_guard_when_opened_as_local_file(self):
        # The expected command pins down the exact, complete, copyable
        # command — naming the real repo root computed from the file's own
        # path, not a vague "serve this directory" that would silently
        # serve whatever directory happens to be the shell's cwd (e.g. a
        # cluttered Downloads folder) instead of the one that actually has
        # the sibling files this page needs. The driver script also clicks
        # the Copy button and reads the clipboard back, so this exercises
        # copyability end to end, not just that the text is present.
        file_url = 'file://' + str(REPO_ROOT / 'web' / 'index.html')
        expected = 'python3 -m http.server 8000 --bind 127.0.0.1 --directory "%s"' % REPO_ROOT
        result = subprocess.run(
            ['node', str(FILE_PROTOCOL_GUARD_SCRIPT), file_url, expected],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class MissingSiblingExecutableGuard(unittest.TestCase):
    """§23.4/§23.8: the page looks for the lightwebpres executable in two
    conventional spots relative to itself, in order: ./lightwebpres
     (alongside the contents of web/, so a site can serve web/ itself as its
    URL root with no extra path segment) and ../lightwebpres (the repo's
    own layout, for a deployment that's just a duplicate of the repo
     as-is). If neither exists — a real mistake, e.g. copying the contents of web/
    into a flat target folder without the executable at all — both fetches
    404. The page must explain the real cause instead of showing a bare
    "Failed to fetch ../lightwebpres: 404"."""

    @classmethod
    def setUpClass(cls):
        # Serve ONLY web/ as the HTTP root, so neither ./lightwebpres nor
        # ../lightwebpres is reachable within the served tree —
        # reproducing exactly what happens when the contents of web/ are
        # deployed without the executable anywhere nearby.
        web_dir = str(REPO_ROOT / 'web')
        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=web_dir))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)

    def test_index_html_explains_missing_lightwebpres(self):
        url = 'http://127.0.0.1:%d/index.html' % self.port
        result = subprocess.run(
            ['node', str(LWP_LOOKUP_SCRIPT), url,
             'either of its two conventional locations'],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright unavailable: %s' % NPM_ROOT_OR_REASON)
class FlatDeploymentFindsCurrentDirExecutable(unittest.TestCase):
    """§23.8: when lightwebpres is copied alongside the contents of web/
    (the "flat" layout, so a site can serve web/ itself as its own URL
    root — no unrelated parent directory needed just to hold the
    executable) — with NO copy one level up either — the page must still
    reach Ready., proving ./lightwebpres is genuinely tried and used, not
    just documented. index.html loads both tabs' glue scripts up front, so
    reaching Ready. here also proves app.py and git_sync.py coexist in the
    shared Pyodide namespace without colliding (§23.1)."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        flat_dir = Path(cls.tmpdir.name)
        for item in (REPO_ROOT / 'web').iterdir():
            dest = flat_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        shutil.copy2(REPO_ROOT / 'lightwebpres', flat_dir / 'lightwebpres')

        cls.httpd = HTTPServer(('127.0.0.1', 0), lambda *a: _QuietHandler(*a, directory=str(flat_dir)))
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=5)
        cls.tmpdir.cleanup()

    def test_index_html_reaches_ready(self):
        url = 'http://127.0.0.1:%d/index.html' % self.port
        result = subprocess.run(
            ['node', str(LWP_LOOKUP_SCRIPT), url, 'Ready.'],
            capture_output=True, text=True,
            env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class ThemesGalleryFacets(unittest.TestCase):
    """§11.7/§9.5.3: the gallery's facet filters, measured against real
    layout in a real browser.

    This needs a browser because the failure it guards against is
    invisible to everything cheaper. The script hides a card by setting
    its `hidden` property, which relies on the browser default
    [hidden] { display: none } — and a class rule carrying a `display` of
    its own outranks that UA default. When that happened the counter read
    "14 palettes" and the dead-end facets greyed out correctly, while all
    cards were still on screen. Asserting on the attribute,
    or on the counter, would have passed."""

    def test_facets_actually_hide_and_restore_the_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            gallery = Path(tmp) / 'themes-gallery.html'
            generated = subprocess.run(
                [sys.executable, str(REPO_ROOT / 'lightwebpres'),
                 'theme', 'gallery', str(gallery)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(generated.returncode, 0,
                             generated.stdout + generated.stderr)
            result = subprocess.run(
                ['node', str(GALLERY_FACETS_SCRIPT), 'file://%s' % gallery],
                capture_output=True, text=True,
                env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class GalleryPanelsShowWhatTheyName(unittest.TestCase):
    """§11.7: each row is four panels, and each panel is an iframe with a
    real viewport at scale 1.0.

    This needs a browser for the same reason the facet test does: the
    claim is about LAYOUT. "The card panel shows a note at its foot" is
    not provable from the markup — the card is taller than the panel and
    the overflow is hidden, so the note can be perfectly present in the
    document and entirely off-screen. Shrinking the panel back to the
    height it had before notes existed left every offline test green with
    the note out of frame."""

    def test_the_note_is_inside_the_card_panel_and_the_rule_inside_the_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            gallery = Path(tmp) / 'themes-gallery.html'
            generated = subprocess.run(
                [sys.executable, str(REPO_ROOT / 'lightwebpres'),
                 'theme', 'gallery', str(gallery)],
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(generated.returncode, 0,
                             generated.stdout + generated.stderr)
            result = subprocess.run(
                ['node', str(GALLERY_PANELS_SCRIPT), 'file://%s' % gallery],
                capture_output=True, text=True,
                env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(AVAILABLE, 'node/playwright not available: %s' % NPM_ROOT_OR_REASON)
class EveryNoteAxisLandsWhereItIsAimed(unittest.TestCase):
    """§9/§6.5: an axis that is emitted but loses is worse than one that
    does not exist — `settings.conf` lists it, `audit` counts it, and it
    does nothing.

    `note.size` shipped that way: `article.size` drives `.full-article ol`
    at (0,1,1), which beat `.note-body` at (0,1,0), so the axis was inert
    on the notes at the foot of the long-form article, where the default
    placement puts them. Declared 14px, computed 15px.

    This needs a browser because it cannot be settled on paper.
    Specificity alone says `.fact-content h2` outranks `.note-back`, which
    is true and irrelevant: it can never select one. Only real markup
    answers the question, so the check is the sound one — resolve the
    declared value, resolve the computed value, compare."""

    def test_every_note_axis_lands_in_a_card_an_article_and_a_section(self):
        # The executable has no .py suffix, so spec_from_file_location
        # cannot pick a loader for it — name one explicitly, as the main
        # suite's load_lightwebpres_module() does.
        import importlib.util
        from importlib.machinery import SourceFileLoader
        loader = SourceFileLoader('lwp_under_test',
                                  str(REPO_ROOT / 'lightwebpres'))
        lwp = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(lwp)
        with tempfile.TemporaryDirectory() as tmp:
            urls = []
            for panel in ('card', 'article', 'notes'):
                path = Path(tmp) / f'{panel}.html'
                path.write_text(
                    lwp.build_theme_preview_document('newsprint', panel),
                    encoding='utf-8')
                urls.append('file://%s' % path)
            # The two keyword axes default to `normal`, which is also
            # what an element inherits — so a declared-vs-computed check
            # passes on them whether or not any rule consumes the
            # variable, and detaching their selector left it green. The
            # provoked copy sets them to values nothing inherits.
            provoked = Path(tmp) / 'provoked.html'
            provoked.write_text(
                lwp.build_theme_preview_document('newsprint', 'card')
                   .replace('--note-weight: normal', '--note-weight: bold')
                   .replace('--note-style: normal', '--note-style: italic'),
                encoding='utf-8')
            urls.append('file://%s' % provoked)
            result = subprocess.run(
                ['node', str(NOTE_PROPERTIES_SCRIPT), *urls],
                capture_output=True, text=True,
                env={**__import__('os').environ, 'NODE_PATH': NPM_ROOT_OR_REASON},
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class WebSourceHardening(unittest.TestCase):
    """Static guards for web fixes that do not require a browser run."""

    def test_local_server_hint_is_loopback_only(self):
        html = (REPO_ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('--bind 127.0.0.1 --directory', html)

    def test_pyodide_proxies_are_destroyed_after_each_call(self):
        html = (REPO_ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('function destroyPyProxy(proxy)', html)
        for name in ('buildFn', 'pullFn', 'pushFn'):
            self.assertIn(f'destroyPyProxy({name})', html)
        self.assertIn('destroyPyProxy(resultProxy)', html)

    def test_zip_guards_reject_ambiguous_members_in_both_glues(self):
        for filename in ('app.py', 'git_sync.py'):
            source = (REPO_ROOT / 'web' / filename).read_text(encoding='utf-8')
            self.assertIn('infolist()', source)
            self.assertIn('canonical in seen', source)
            self.assertIn(r"'\x00' in name", source)
            self.assertIn('ZIP_MAX_ENTRIES', source)
            self.assertIn('ZIP_MAX_COMPRESSED_BYTES', source)
            self.assertIn('ZIP_MAX_UNCOMPRESSED_BYTES', source)

    def test_archive_limits_are_owned_by_the_page_and_injected_before_glues(self):
        html = (REPO_ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('const ZIP_MAX_ENTRIES = 4096;', html)
        self.assertIn(
            'const ZIP_MAX_COMPRESSED_BYTES = 500 * 1024 * 1024;', html)
        self.assertIn(
            'const ZIP_MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024;', html)

        injection = html.index(
            "pyodide.globals.set('ZIP_MAX_COMPRESSED_BYTES'")
        app_load = html.index("const appSource = await fetchText('./app.py');")
        git_load = html.index(
            "const gitSyncSource = await fetchText('./git_sync.py');")
        self.assertLess(injection, app_load)
        self.assertLess(injection, git_load)
        self.assertLess(
            html.index('file.size > ZIP_MAX_COMPRESSED_BYTES'),
            html.index('file.arrayBuffer()'))

        git_sync = (REPO_ROOT / 'web' / 'git_sync.py').read_text(encoding='utf-8')
        self.assertIn("resp.headers.get('content-length')", git_sync)
        self.assertLess(
            git_sync.index("resp.headers.get('content-length')"),
            git_sync.index('await resp.bytes()'))


class TheZipGuardCapsWhatItExtractsIntoMemory(unittest.TestCase):
    """web/ extracts archives into Pyodide's in-memory filesystem: without
    limits, a hostile or oversized zip exhausts the tab instead of failing
    with an explicit error. The caps live inside the shared guard, so the
    upload tab and the GitLab pull get them from one rule. Exercised here
    at reduced values: what matters is the mechanism, not the numbers."""

    def _load_guard(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'lwp_web_app_guard_under_test', REPO_ROOT / 'web' / 'app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _real_zip(self, names_and_payloads):
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for name, payload in names_and_payloads:
                zf.writestr(name, payload)
        return zipfile.ZipFile(io.BytesIO(buf.getvalue()))

    def test_a_normal_series_zip_passes_the_guard(self):
        guard = self._load_guard()
        zf = self._real_zip([
            ('series.json', '{"articles": []}'),
            ('sources/a.md', '# A\n'),
        ])
        self.assertIsNone(guard._validate_zip_members(zf))

    def test_an_archive_beyond_the_byte_cap_is_refused(self):
        guard = self._load_guard()
        guard.ZIP_MAX_UNCOMPRESSED_BYTES = 16
        zf = self._real_zip([('sources/a.md', 'x' * 64)])
        with self.assertRaises(RuntimeError) as raised:
            guard._validate_zip_members(zf)
        self.assertIn('decompresses to more than', str(raised.exception))

    def test_an_input_beyond_the_compressed_cap_is_refused_before_loading(self):
        guard = self._load_guard()
        guard.ZIP_MAX_COMPRESSED_BYTES = 16
        result = guard.build_from_zip_bytes(b'x' * 17)
        self.assertIsNone(result[0])
        self.assertEqual(result[1], '')
        self.assertIn('compressed-size limit', result[2])

    def test_an_archive_beyond_the_entry_cap_is_refused(self):
        guard = self._load_guard()
        guard.ZIP_MAX_ENTRIES = 2
        zf = self._real_zip([
            ('series.json', '{}'),
            ('sources/a.md', '# A\n'),
            ('sources/b.md', '# B\n'),
        ])
        with self.assertRaises(RuntimeError) as raised:
            guard._validate_zip_members(zf)
        self.assertIn('entry limit', str(raised.exception))


if __name__ == '__main__':
    unittest.main()


class TheSharedZipGuardIsOneRuleInTwoPlaces(unittest.TestCase):
    """B25 / §23.1: `_validate_zip_members` is defined at module level in
    BOTH `web/app.py` and `web/git_sync.py`, and that sharing is
    deliberate rather than an accident.

    `index.html` runs the two glue scripts one after the other into the
    same Python namespace, so the second loaded wins — for both call
    sites, including the one in the file whose definition was replaced.
    It is a path-traversal guard on zip members. Two copies that drifted
    apart would leave the surviving one governing an extraction the other
    file believes it is protecting, and nothing would say so: same name,
    same signature, no error, no warning, a build that works.

    §23.1 states the rule and said, until this existed, that nothing
    checked it.

    Compared by AST with docstrings stripped, because the docstrings
    legitimately differ — one explains the defence, the other points at
    it — and because comparing source text would fail on a reflowed line
    and pass on a changed constant. What has to match is the RULE."""

    FILES = ('app.py', 'git_sync.py')
    NAME = '_validate_zip_members'

    def _rule(self, filename):
        import ast
        source = (REPO_ROOT / 'web' / filename).read_text(encoding='utf-8')
        tree = ast.parse(source, filename=filename)
        found = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef) and n.name == self.NAME]
        self.assertEqual(
            len(found), 1,
            f'web/{filename} defines {self.NAME} {len(found)} times at '
            f'module level; §23.1 says exactly one, in each of the two')
        fn = found[0]
        body = fn.body
        # Drop a leading docstring: it is prose about the rule, not the rule.
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        return ast.dump(ast.Module(body=body, type_ignores=[]))

    def test_the_two_bodies_are_the_same_rule(self):
        first = self._rule('app.py')
        second = self._rule('git_sync.py')
        self.assertEqual(
            first, second,
            'web/app.py and web/git_sync.py disagree about '
            f'{self.NAME}. They share one namespace and the second loaded '
            'wins for both call sites, so the difference would apply '
            'silently — to an extraction the other file thinks it is '
            'guarding. Either make them identical or stop sharing the '
            'name (§23.1)')

    def test_both_files_still_carry_it(self):
        """The pair is the point. One file losing the definition leaves
        the survivor governing both extractions by accident rather than
        by the decision §23.1 records — which happens to work, and works
        for no stated reason."""
        import ast
        for filename in self.FILES:
            source = (REPO_ROOT / 'web' / filename).read_text(encoding='utf-8')
            names = [n.name for n in ast.parse(source).body
                     if isinstance(n, ast.FunctionDef)]
            self.assertIn(
                self.NAME, names,
                f'web/{filename} no longer defines {self.NAME}; §23.1 says '
                f'both files carry it and both bodies stay identical')
