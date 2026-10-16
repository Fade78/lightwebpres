"""Inert kit HTML-insertion checks: no browser, code payload or network."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

if __package__:
    from .test_lightwebpres import run
else:
    from test_lightwebpres import run

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('cover', 'standard', 'series-nav', 'full-article')
SLOTS = '{{slide_header}}{{content}}{{slide_footer}}'
VALID_LAYOUT = '<div class="card">' + SLOTS + '</div>'
COMMENT_LAYOUT = '<div>{{slide_header}}<!-- {{content}} -->{{slide_footer}}</div>'


class KitLayoutInsertionContexts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / 'work/tmp', prefix='kit-slot-contexts-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @staticmethod
    def manifest(kit_id):
        return {
            'schema': 'lightwebpres.identity-kit/1', 'id': kit_id,
            'version': '1.0.0', 'label': 'Insertion fixture', 'default_preset': 'standard',
            'layouts': {**{kind: {'default': 'card.html'} for kind in KINDS},
                        'index': 'index.html'},
            'themes': {'plain': 'builtin:light'},
            'presets': {'standard': {
                'label': 'Standard fixture', 'description': 'An inert layout fixture.', 'theme': 'plain',
                'slide_layouts': {kind: 'default' for kind in KINDS}, 'slide_chrome': {},
            }},
        }

    def kit(self, catalogue, kit_id='fixture'):
        kit = catalogue / kit_id / '1.0.0'
        kit.mkdir(parents=True)
        (kit / 'manifest.json').write_text(json.dumps(self.manifest(kit_id)), encoding='utf-8')
        (kit / 'card.html').write_text(VALID_LAYOUT, encoding='utf-8')
        (kit / 'index.html').write_text('<main>{{content}}</main>', encoding='utf-8')
        return kit

    def series(self, name, external=False):
        root = self.root / name
        (root / 'sources').mkdir(parents=True)
        catalogue = root / ('catalogue' if external else 'templates/kits')
        kit = self.kit(catalogue)
        (root / 'series.json').write_text(json.dumps({
            'appearance': {'presets': ['fixture@1.0.0/standard']},
            'articles': [{'page_source': 'a.md'}]}), encoding='utf-8')
        (root / 'sources/a.md').write_text(
            '<!-- lwp:meta -->\npage_title: Slot fixture\n---\n\n'
            '<!-- lwp:slide:cover -->\nslug: cover\n# Visible title\nsummary: Visible summary.\n\n---\n\n'
            '<!-- lwp:slide -->\nslug: body\n## Visible details\n\n'
            '<aside>Literal {{content}} remains.</aside>\n\n---\n\n'
            '<!-- lwp:slide:series-nav -->\nslug: navigation\n', encoding='utf-8')
        env = {**os.environ, 'TMPDIR': str(ROOT / 'work/tmp'),
               'LWP_THEMES_DIR': str(root / 'empty-themes'),
               'LWP_COMMONS_DIR': str(root / 'empty-commons'),
               'LWP_IDENTITY_KITS_DIR': str(catalogue if external else root / 'empty-kits')}
        return root, kit, env

    def cli(self, root, env, command, *options):
        return run(command, root, '--lang', 'en', *options, env=env)

    def assert_refused(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn(message, result.stderr)

    @staticmethod
    def files(root):
        return {path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    def test_slots_must_be_html_insertions_not_markup_comments_or_inert_data(self):
        cases = {
            'comment': COMMENT_LAYOUT,
            'quoted attribute': '<div title="{{content}}">{{slide_header}}{{slide_footer}}</div>',
            'unquoted attribute': '<div title={{content}}>{{slide_header}}{{slide_footer}}</div>',
            'closing tag': '<div>{{slide_header}}{{slide_footer}}</div {{content}}>',
            'declaration': '<!DOCTYPE fixture "{{content}}">{{slide_header}}{{slide_footer}}',
            'processing instruction': '<?fixture {{content}}?>{{slide_header}}{{slide_footer}}',
            'self-closing template': '<template/>{{content}}{{slide_header}}{{slide_footer}}',
            'nested template': '<template><template>Example</template>{{content}}</template>{{slide_header}}{{slide_footer}}',
            'plaintext has no end tag': '<plaintext></plaintext>{{content}}{{slide_header}}{{slide_footer}}',
        }
        for tag in ('template', 'textarea', 'title', 'xmp', 'noembed', 'noframes',
                    'noscript', 'plaintext', 'select', 'option', 'optgroup', 'datalist'):
            cases[tag] = '<' + tag + '>{{content}}</' + tag + '>{{slide_header}}{{slide_footer}}'
        for index, (name, layout) in enumerate(cases.items()):
            with self.subTest(context=name):
                root, kit, env = self.series('context-' + str(index))
                (kit / 'card.html').write_text(layout, encoding='utf-8')
                result = self.cli(root, env, 'build')
                self.assert_refused(result, 'normal HTML content')
                self.assertIn('card.html', result.stderr)
                self.assertFalse((root / 'public').exists())

    def test_incomplete_layout_markup_is_rejected_before_slot_expansion(self):
        for index, layout in enumerate((
                '<div title="Unfinished ' + SLOTS,
                SLOTS + '<div title="Unfinished',
                SLOTS + '<!-- unfinished',
                SLOTS + '</div')):
            with self.subTest(layout=layout):
                root, kit, env = self.series('unfinished-' + str(index))
                (kit / 'card.html').write_text(layout, encoding='utf-8')
                result = self.cli(root, env, 'build')
                self.assert_refused(result, 'incomplete markup')
                self.assertIn('card.html', result.stderr)
                self.assertFalse((root / 'public').exists())

    def test_a_fragment_cannot_leave_a_later_insertion_in_an_open_inert_context(self):
        for index, suffix in enumerate(('<template/>', '<template><span>Example</span>',
                                        '<textarea>', '<select>', '<plaintext></plaintext>')):
            with self.subTest(suffix=suffix):
                root, kit, env = self.series('open-inert-' + str(index))
                (kit / 'card.html').write_text(SLOTS + suffix, encoding='utf-8')
                result = self.cli(root, env, 'build')
                self.assert_refused(result, 'unclosed HTML insertion context')
                self.assertIn('card.html', result.stderr)
                self.assertFalse((root / 'public').exists())

    def test_literal_markers_and_decorative_inert_nodes_do_not_become_slots(self):
        literal = '&#123;&#123;content&#125;&#125;'
        layout = ('<!-- Decorative note: ' + literal + ' -->'
                  '<template><span>' + literal + '</span></template>'
                  '<textarea>' + literal + '</textarea>'
                  '<div data-example="' + literal + '">'
                  '{{slide_header}}<hr/>{{content}}<br/>{{slide_footer}}</div>')
        for name, options, output in (
                ('multi', (), 'a.html'),
                ('combined', ('--single-html', 'series.html'), 'series.html')):
            with self.subTest(topology=name):
                root, kit, env = self.series('literal-' + name)
                (kit / 'card.html').write_text(layout, encoding='utf-8')
                for command in ('build', 'verify'):
                    result = self.cli(root, env, command, *options)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                html = (root / 'public' / output).read_text(encoding='utf-8')
                if options:
                    payload = re.search(r'<script id="lwp-series-data" type="application/json">(.*?)</script>', html, re.S)
                    self.assertIsNotNone(payload)
                    html = next(view['content'] for view in json.loads(payload[1])['views']
                                if view['key'] == 'a.html')
                self.assertIn('Visible title', html)
                self.assertIn('Literal {{content}} remains.', html)
                self.assertIn('data-example="' + literal + '"', html)

    def test_rejected_local_and_catalogue_layouts_preserve_existing_publication(self):
        for external in (False, True):
            for combined in (False, True):
                with self.subTest(catalogue=external, combined=combined):
                    root, kit, env = self.series('retained-' + str(external) + str(combined), external)
                    options = ('--single-html', 'series.html') if combined else ()
                    result = self.cli(root, env, 'build', *options)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    (root / 'public/manual.txt').write_text('Manual sidecar', encoding='utf-8')
                    (kit / 'card.html').write_text(COMMENT_LAYOUT, encoding='utf-8')
                    before = self.files(root)
                    for command, extra in (('build', ()), ('verify', ()),
                                           ('build', ('--incremental', 'a.md'))):
                        result = self.cli(root, env, command, *options, *extra)
                        self.assert_refused(result, 'normal HTML content')
                        self.assertEqual(self.files(root), before,
                                         'rejection must preserve output, sidecars, sources, README and caches')

    def test_an_unused_index_fragment_in_an_alternative_kit_is_still_validated(self):
        root, kit, env = self.series('alternative')
        other = self.kit(kit.parents[1], 'other')
        config = json.loads((root / 'series.json').read_text(encoding='utf-8'))
        config['appearance']['presets'].append('other@1.0.0/standard')
        (root / 'series.json').write_text(json.dumps(config), encoding='utf-8')
        options = ('--single-html', 'series.html', '--no-index')
        result = self.cli(root, env, 'build', *options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (other / 'index.html').write_text('<!-- {{content}} -->', encoding='utf-8')
        before = self.files(root)
        result = self.cli(root, env, 'build', *options)
        self.assert_refused(result, 'normal HTML content')
        self.assertIn('index.html', result.stderr)
        self.assertEqual(self.files(root), before)

    def test_composition_refuses_invalid_source_and_final_slots_without_publication(self):
        for source_case in (True, False):
            with self.subTest(source_validation=source_case):
                root = self.root / ('compose-source' if source_case else 'compose-result')
                root.mkdir()
                output = root / 'result'
                output.mkdir()
                (output / 'manual.txt').write_text('Keep this catalogue sidecar', encoding='utf-8')
                recipe = {'schema': 'lightwebpres.kit-composition/1', 'sources': {},
                          'manifest': self.manifest('composed'), 'files': {}}
                if source_case:
                    kit = self.kit(root / 'inputs')
                    (kit / 'card.html').write_text(COMMENT_LAYOUT, encoding='utf-8')
                    recipe['sources']['frame'] = kit.relative_to(root).as_posix()
                    recipe['files'] = {name: {'source': 'frame', 'path': name}
                                       for name in ('card.html', 'index.html')}
                else:
                    recipe['files'] = {'card.html': {'text': COMMENT_LAYOUT},
                                       'index.html': {'text': '<main>{{content}}</main>'}}
                recipe_path = root / 'recipe.json'
                recipe_path.write_text(json.dumps(recipe), encoding='utf-8')
                before = self.files(root)
                for options in (('--dry-run',), ()):
                    result = run('kit', 'compose', recipe_path, '--output', output,
                                 *options, env={'TMPDIR': str(ROOT / 'work/tmp')})
                    self.assert_refused(result, 'normal HTML content')
                    self.assertFalse((output / 'composed/1.0.0').exists())
                    self.assertEqual(self.files(root), before)
