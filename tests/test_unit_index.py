"""Unit indexes use source provenance and the final published slide universe."""

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

if __package__:
    from . import test_lightwebpres as support
else:
    import test_lightwebpres as support


class IndexHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.sections = []
        self.indexes = {}
        self.section = None
        self.index = None
        self.link = None
        self.text_field = None
        self.template_depth = 0
        self.preview = None
        self.cards = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'template':
            self.template_depth += 1
        if self.template_depth:
            return
        classes = attrs.get('class', '').split()
        if 'data-lwp-tag-preview' in attrs:
            self.preview = json.loads(attrs['data-lwp-tag-preview'])
        if attrs.get('data-lwp-article-card') == 'true':
            self.cards.append(attrs)
        if tag == 'section' and 'slide' in classes:
            self.section = attrs['id']
            self.sections.append(self.section)
        if tag == 'nav' and 'lwp-unit-index' in classes:
            self.index = {'attrs': attrs, 'links': [], 'empty': False}
            self.indexes[self.section] = self.index
        if self.index is not None and tag == 'a':
            self.link = {'attrs': attrs, 'title': '', 'number': ''}
            self.index['links'].append(self.link)
        if 'lwp-unit-index-empty' in classes and self.index is not None:
            self.index['empty'] = True
        for field in ('title', 'number'):
            if f'lwp-unit-index-{field}' in classes:
                self.text_field = field

    def handle_endtag(self, tag):
        if tag == 'template':
            self.template_depth -= 1
            return
        if self.template_depth:
            return
        if tag == 'nav':
            self.index = None
        if tag == 'a':
            self.link = None
        if tag == 'span':
            self.text_field = None

    def handle_data(self, data):
        if self.link is not None and self.text_field:
            self.link[self.text_field] += data


META = '<!-- lwp:meta -->\npage_dest: a.html\n{meta}---\n\n'
COVER = '<!-- lwp:slide:cover -->\nslug: cover\n# Opening\n'
STANDARD = '<!-- lwp:slide -->\nslug: detail\ntags: Focus\n## Detail\n'
INDEX = '<!-- lwp:slide:unit-index -->\nslug: contents\n{fields}'


class UnitIndexSource(unittest.TestCase):
    def setUp(self):
        self.lwp = support.load_lightwebpres_module()

    def test_draft_v2_exposes_fields_cardinality_and_empty_rules(self):
        contract = self.lwp.slide_draft_contract()
        self.assertEqual(contract['schema'], 'lightwebpres.slide-draft/2')
        descriptor = next(item for item in contract['types']
                          if item['name'] == 'unit-index')
        self.assertEqual(descriptor['required_fields'], ['slug'])
        self.assertEqual(descriptor['cardinality'], {'min': 0, 'max': None})
        self.assertIsNone(descriptor['free_text'])
        for field in ('index-max-columns', 'index-selector'):
            self.assertIn(field, descriptor['fields'])
            self.assertIn('unit-index.' + field, contract['empty_rules'])
        source = META.format(meta='') + descriptor['draft']['source']
        _, slides, has_meta, before = self.lwp.parse_markdown_extended(source)
        # Presentation fields deliberately need an author choice or omission.
        for field in self.lwp._PRESENTATION_SLIDE_FIELDS:
            slides[0].raw_meta.pop(field, None)
        self.lwp.validate_slides(slides, 'test.md', has_meta, before)
        self.assertEqual(slides[0].index_max_columns, 1)
        self.assertEqual(slides[0].index_selector, '*')

    def test_source_capture_keeps_unit_authority_and_not_series_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = META.format(meta='status: active\ntags: Focus\n') + COVER
            root = support.scaffold(tmp, source, {'status': 'draft'})
            data = json.loads((root / 'series.json').read_text())
            entry = data['articles'][0]
            self.lwp.resolve_article_fields(
                data['articles'], root / 'sources', {'author': 'Series author'},
                build_args={'--unit-index': 'on'})
            sources = entry['_lwp_selection_sources']
            self.assertEqual([item['source'] for item in sources],
                             ['series-entry', 'unit-meta', 'derived'])
            self.assertEqual([item['priority'] for item in sources], [20, 10, 0])
            self.assertEqual(sources[0]['values']['status'], 'draft')
            self.assertEqual(sources[1]['values']['status'], 'active')
            self.assertNotIn('author', sources[0]['values'])
            self.assertNotIn('author', sources[2]['values'])
            self.assertEqual(sources[2]['values']['page_title'], 'Opening')
            self.assertEqual(entry['author'], 'Series author')
            self.assertEqual([item['type'] for item in entry['_lwp_tag_slides']],
                             ['cover', 'unit-index'])
            # Audit resolves its preliminary inventory again for rendering.
            self.lwp.resolve_article_fields(
                data['articles'], root / 'sources', {'author': 'Series author'})
            self.assertNotIn('author', entry['_lwp_selection_sources'][0]['values'])
            self.assertNotIn('author', entry['_lwp_selection_sources'][2]['values'])

    def test_endnotes_probe_is_resource_free_and_metadata_errors_stay_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = support.scaffold(tmp, META.format(meta='notes_placement: page\n')
                                    + STANDARD + '\n[^1]: ![mark](img/mark.svg)\n')
            with mock.patch.object(self.lwp, '_encode_inline_image',
                                   side_effect=AssertionError('resource read')), \
                    mock.patch.object(self.lwp, 'log') as logged:
                for body, expected in (
                        ('[^1]: ![mark](img/mark.svg)\n', True),
                        ('[^1]: Definition\n{align:invalid}\n', False)):
                    text = META.format(meta='notes_placement: page\n') + STANDARD + '\n' + body
                    (root / 'sources' / 'a.md').write_text(text, encoding='utf-8')
                    entries = [{'page_source': 'a.md'}]
                    self.lwp.resolve_article_fields(
                        entries, root / 'sources',
                        build_strings={'notes_section_title': 'References'})
                    details = entries[0]['_lwp_tag_slides']
                    self.assertEqual(any(slide['type'] == 'notes' for slide in details), expected)
                    if expected:
                        self.assertEqual(details[-1], {'title': 'References', 'type': 'notes',
                                                     'tags': ['default'], 'untagged': False})
                logged.assert_not_called()

    def test_endnotes_probe_honors_placement_and_unavailable_full_articles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = support.scaffold(tmp, META.format(meta='') + STANDARD)
            _, slides, _, _ = self.lwp.parse_markdown_extended(
                STANDARD + '\n[^1]: Definition\n')
            with mock.patch.object(self.lwp, 'convert_markdown') as converted, \
                    mock.patch.object(self.lwp, 'log') as logged:
                for meta, series in (({}, {}), ({'notes_placement': 'local'},
                                               {'notes_placement': 'page'}),
                                     ({'notes_placement': 'invalid'}, {})):
                    self.assertFalse(self.lwp._unit_has_page_endnotes(
                        slides, meta, series, root / 'sources'))
                converted.assert_not_called()
                logged.assert_not_called()
            for field in ('', 'missing.md', '../outside.md'):
                text = (META.format(meta='notes_placement: page\n')
                        + '<!-- lwp:slide:full-article -->\nslug: full\n'
                        + f'article: {field}\n')
                (root / 'sources' / 'a.md').write_text(text, encoding='utf-8')
                entries = [{'page_source': 'a.md'}]
                self.lwp.resolve_article_fields(entries, root / 'sources')
                self.assertFalse(any(slide['type'] == 'notes'
                                     for slide in entries[0]['_lwp_tag_slides']))


class UnitIndexBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, slides, meta='', series_meta=None, entry=None):
        text = META.format(meta=meta) + '\n---\n\n'.join(slides)
        support.scaffold(self.root, text, entry)
        path = self.root / 'series.json'
        data = json.loads(path.read_text())
        if series_meta:
            data['series_meta'] = series_meta
        path.write_text(json.dumps(data), encoding='utf-8')
        return text

    def build(self, *args):
        result = support.run('build', str(self.root), '--lang', 'en', *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        html = (self.root / 'public' / 'a.html').read_text(encoding='utf-8')
        self.assertNotIn('UNIT_INDEX_PLACEHOLDER', html)
        return html, IndexHTML(html)

    def targets(self, parsed, slug='contents'):
        return [link['attrs']['data-lwp-index-target']
                for link in parsed.indexes[slug]['links']]

    def test_explicit_multiple_indexes_have_independent_selectors_and_columns(self):
        self.fixture([COVER, INDEX.format(fields='## Everything\n'), STANDARD,
                      INDEX.replace('contents', 'focused').format(
                          fields='index-selector: tag:focus\nindex-max-columns: 3\n')])
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), ['cover', 'contents', 'detail', 'focused'])
        self.assertEqual(self.targets(parsed, 'focused'), ['detail'])
        self.assertEqual(parsed.indexes['contents']['attrs']['data-lwp-index-columns'], '1')
        self.assertEqual(parsed.indexes['focused']['attrs']['style'], '--lwp-index-columns:3')
        self.assertEqual(parsed.indexes['focused']['links'][0]['number'], '3')
        self.assertEqual(parsed.indexes['focused']['links'][0]['attrs']['data-lwp-target-tags'],
                         'focus')

    def test_wildcard_contains_self_other_indexes_cover_and_generated_notes(self):
        self.fixture([COVER, INDEX.format(fields=''),
                      STANDARD + '\nText[^1].\n\n[^1]: A note body.\n',
                      '<!-- lwp:slide -->\nslug: omitted\ntags: excluded\n## Hidden\n',
                      '<!-- lwp:slide:full-article -->\nslug: unfinished\narticle:\n',
                      INDEX.replace('contents', 'another').format(fields='')],
                     meta='notes_placement: page\n')
        _, parsed = self.build()
        expected = ['cover', 'contents', 'detail', 'another', 'notes']
        self.assertEqual(parsed.sections, expected)
        self.assertEqual(self.targets(parsed), expected)
        self.assertEqual(self.targets(parsed, 'another'), expected)

    def test_generated_notes_make_default_visibility_counts_and_cards_match_output(self):
        self.fixture([STANDARD.replace('Focus', 'expert-en')
                      + '\nText[^1].\n\n[^1]: Endnote.\n'],
                     meta='notes_placement: page\n')
        built = support.run('build', str(self.root), '--lang', 'en')
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertNotIn("tag 'default' selects no displayable slide", built.stderr)
        article = IndexHTML((self.root / 'public' / 'a.html').read_text())
        self.assertEqual(article.sections, ['detail', 'notes'])
        self.assertEqual(article.preview['articles'][0]['slides'][-1],
                         {'title': 'Notes', 'type': 'notes', 'tags': ['default']})
        index = IndexHTML((self.root / 'public' / 'index.html').read_text())
        self.assertEqual(index.cards[0]['data-lwp-slide-tags'], 'expert-en default')
        report = support.run('series', 'tags', str(self.root), '--format', 'json')
        status = support.run('status', str(self.root), '--format', 'json')
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(status.returncode, 0, status.stderr)
        tags = json.loads(report.stdout)
        self.assertEqual(tags['totals']['slides'], {'non_excluded': 2, 'untagged': 0})
        self.assertEqual(tags['default_output'],
                         {'tag': 'default', 'articles': 1, 'slides': 1, 'empty': False})
        self.assertEqual(json.loads(status.stdout)['tags']['default_output'],
                         tags['default_output'])
        audited = support.run('audit', str(self.root), '--lang', 'en')
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertNotIn("tag 'default' selects no displayable slide", audited.stderr)

    def test_literal_definitions_and_orphan_calls_do_not_create_inventory_notes(self):
        for body in ('```\n[^1]: Literal code\n```\n',
                     '<div>\n[^1]: Raw HTML\n</div>\n',
                     '`[^1]: Inline code`\n', '> [^1]: Quoted text\n',
                     '| Text |\n| --- |\n| [^1]: Table cell |\n',
                     'A call without a body[^missing].\n'):
            with self.subTest(body=body):
                self.fixture([STANDARD + '\n' + body], meta='notes_placement: page\n')
                _, parsed = self.build()
                self.assertEqual(parsed.sections, ['detail'])
                self.assertEqual([slide['type'] for slide in parsed.preview['articles'][0]['slides']],
                                 ['standard'])

    def test_endnotes_include_unreferenced_and_long_form_bodies_but_not_excluded_sources(self):
        full = '<!-- lwp:slide:full-article -->\nslug: prose\narticle: body.md\ntags: expert-en\n'
        for slide in (STANDARD + '\n[^1]: Unreferenced.\n', full):
            with self.subTest(slide=slide):
                self.fixture([slide], series_meta={'notes_placement': 'page'})
                (self.root / 'sources' / 'body.md').write_text(
                    '# Prose\n\n[^1]: Unreferenced long-form body.\n', encoding='utf-8')
                _, parsed = self.build()
                self.assertIn('notes', parsed.sections)
                self.assertEqual(parsed.preview['articles'][0]['slides'][-1]['type'], 'notes')
        self.fixture([STANDARD, full.replace('expert-en', 'excluded'),
                      STANDARD.replace('slug: detail', 'slug: omitted').replace('Focus', 'excluded')
                      + '\n[^1]: Omitted.\n'], meta='notes_placement: page\n')
        _, parsed = self.build()
        self.assertEqual(parsed.sections, ['detail'])
        self.assertEqual(len(parsed.preview['articles'][0]['slides']), 1)

    def test_endnotes_obey_unit_gates_and_report_status_publication_counts(self):
        self.fixture([STANDARD + '\n[^1]: Body.\n'], meta='notes_placement: page\n')
        path = self.root / 'series.json'
        data = json.loads(path.read_text())
        for status in ('draft', 'ignored'):
            source = self.root / 'sources' / f'{status}.md'
            source.write_text((self.root / 'sources' / 'a.md').read_text().replace(
                'page_dest: a.html', f'page_dest: {status}.html'), encoding='utf-8')
            data['articles'].append({'page_source': source.name, 'status': status})
        path.write_text(json.dumps(data), encoding='utf-8')
        result = support.run('series', 'tags', str(self.root), '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        default = next(item for item in report['tags'] if item['tag'] == 'default')
        self.assertEqual(default['articles'], {'active': 1, 'draft': 1, 'ignored': 1, 'total': 3})
        self.assertEqual(default['slides'], 3)
        self.assertEqual(default['output'], {'articles': 1, 'slides': 1})
        self.fixture([STANDARD + '\n[^1]: Body.\n'],
                     meta='notes_placement: page\ntags: focus\n')
        result = support.run('series', 'tags', str(self.root), '--format', 'json')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['default_output']['empty'])
        focus = next(item for item in report['tags'] if item['tag'] == 'focus')
        self.assertEqual(focus['output'], {'articles': 1, 'slides': 2})

    def test_queries_read_scoped_source_fields_regex_and_unit_status(self):
        for query in ('unit:status:draft slide:type:standard',
                      'series:author:Shared unit:author:Local title:/Detail/',
                      'unit:page_source:a.md tag:focus',
                      'slide:title:/^Det/ -slide:type:unit-index'):
            with self.subTest(query=query):
                self.fixture([COVER, INDEX.format(fields=f'index-selector: {query}\n'),
                              STANDARD], meta='status: active\nauthor: Meta\n',
                             series_meta={'author': 'Shared'},
                             entry={'status': 'draft', 'author': 'Local'})
                _, parsed = self.build('--include-drafts')
                self.assertEqual(self.targets(parsed), ['detail'])

    def test_comment_is_not_selection_data_and_empty_results_are_explicit(self):
        self.fixture([INDEX.format(fields=('index-selector: slide:comment:private '
                                           '| unit:comment:private | series:comment:private\n')),
                      STANDARD + 'comment: private\n'], meta='comment: private\n',
                      series_meta={'comment': 'private'})
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), [])
        self.assertTrue(parsed.indexes['contents']['empty'])

    def test_unit_tags_and_default_status_are_distinct_from_slide_tags(self):
        self.fixture([COVER, INDEX.format(fields=(
            'index-selector: unit:tags:audience status:active tag:focus\n')), STANDARD],
            meta='tags: Audience\n')
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), ['detail'])

    def test_jsonpath_and_boolean_queries_share_the_published_universe(self):
        for query in ('slide:type:cover | tag:focus',
                      '$[?(@.slide.type == "cover" || @.slide.slug == "detail")]',
                      '-slide:type:unit-index'):
            with self.subTest(query=query):
                self.fixture([COVER, INDEX.format(fields=f'index-selector: {query}\n'),
                              STANDARD])
                _, parsed = self.build()
                self.assertEqual(self.targets(parsed), ['cover', 'detail'])

    def test_invalid_selector_is_a_diagnostic_not_a_traceback_or_wildcard(self):
        self.fixture([INDEX.format(fields='index-selector: title:/[/\n'), STANDARD])
        result = support.run('build', str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('index-selector', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_title_queries_precede_typography_and_skip_markup_only_titles(self):
        self.fixture([INDEX.format(fields='index-selector: title:"Pourquoi ?"\n'),
                      '<!-- lwp:slide:full-article -->\nslug: background\narticle: background.md\n'])
        (self.root / 'sources' / 'background.md').write_text('# Pourquoi ?\n\nText.\n', encoding='utf-8')
        for options in (('--lang', 'fr'), ('--lang', 'fr', '--no-typography')):
            with self.subTest(options=options):
                _, parsed = self.build(*options)
                self.assertEqual(self.targets(parsed), ['background'])
                self.assertIn(parsed.indexes['contents']['links'][0]['title'],
                              ('Pourquoi ?', 'Pourquoi\u00a0?'))
        self.fixture([INDEX.format(fields=''),
                      STANDARD.replace('## Detail', 'kicker: Fallback\n## <span></span>'),
                      '<!-- lwp:slide -->\nslug: unnamed\n## <span></span>\n'])
        _, parsed = self.build()
        self.assertEqual([link['title'] for link in parsed.indexes['contents']['links']],
                         ['Contents', 'Fallback', 'unnamed'])

    def test_missing_summary_and_unknown_metadata_are_not_invented_fields(self):
        self.fixture([INDEX.format(fields='index-selector: $[? @.slide.summary]\n'),
                      STANDARD, STANDARD.replace('detail', 'other') + 'summary: Present\n'],
                     meta='unrecognized: Not queryable\n', series_meta={'status': 'draft'})
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), ['other'])
        source = self.root / 'sources' / 'a.md'
        source.write_text(source.read_text().replace('$[? @.slide.summary]',
                          'series:status:draft | unit:unrecognized:"Not queryable"'), encoding='utf-8')
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), [])

    def test_heading_note_calls_never_leak_into_index_labels_or_queries(self):
        for placement in ('local', 'page'):
            with self.subTest(placement=placement):
                self.fixture([INDEX.format(fields='index-selector: title:Evidence\n'),
                              '<!-- lwp:slide:full-article -->\nslug: background\narticle: background.md\n'],
                             meta='notes_placement: ' + placement + '\n')
                (self.root / 'sources' / 'background.md').write_text(
                    '# Evidence[^n]\n\nThe supporting text.\n\n[^n]: Source.\n', encoding='utf-8')
                html, parsed = self.build()
                self.assertEqual(self.targets(parsed), ['background'])
                self.assertEqual(parsed.indexes['contents']['links'][0]['title'], 'Evidence')
                self.assertNotIn('\x02', html)

    def test_long_form_target_uses_its_rendered_heading(self):
        self.fixture([INDEX.format(fields='index-selector: slide:type:full-article\n'),
                      '<!-- lwp:slide:full-article -->\nslug: prose\narticle: body.md\n'])
        (self.root / 'sources' / 'body.md').write_text(
            '## An <a href="https://example.test">explanation</a>\n\nText.\n',
            encoding='utf-8')
        _, parsed = self.build()
        self.assertEqual(self.targets(parsed), ['prose'])
        self.assertEqual(parsed.indexes['contents']['links'][0]['title'], 'An explanation')

    def test_automatic_meta_insertion_is_in_memory_prefixed_and_visible_in_previews(self):
        text = self.fixture([COVER, STANDARD],
                            meta='unit_index: yes\nslug_prefix: demo-\n')
        html, parsed = self.build()
        self.assertEqual(parsed.sections, ['demo-cover', 'demo-lwp-index', 'demo-detail'])
        self.assertEqual(self.targets(parsed, 'demo-lwp-index'), parsed.sections)
        self.assertEqual((self.root / 'sources' / 'a.md').read_text(), text)
        self.assertIn('&quot;type&quot;:&quot;unit-index&quot;', html)

    def test_automatic_settings_cascade_meta_cli_series_and_default(self):
        cases = [
            ('', {}, (), False, None),
            ('', {'unit_index': True, 'unit_index_max_columns': 2}, (), True, '2'),
            ('unit_index: off\n', {'unit_index': True}, ('--unit-index', 'on'), False, None),
            ('unit_index_max_columns: 4\n', {'unit_index': False},
             ('--unit-index', 'on', '--unit-index-max-columns', '3'), True, '4'),
            ('', {'unit_index': True}, ('--unit-index', 'off'), False, None),
        ]
        for meta, series, args, present, columns in cases:
            with self.subTest(meta=meta, series=series, args=args):
                self.fixture([COVER, STANDARD], meta=meta, series_meta=series)
                _, parsed = self.build(*args)
                self.assertEqual('lwp-index' in parsed.indexes, present)
                if present:
                    self.assertEqual(parsed.indexes['lwp-index']['attrs']['data-lwp-index-columns'],
                                     columns)

    def test_automatic_selector_cascade_and_cli_preview(self):
        self.fixture([COVER, STANDARD], series_meta={'unit_index_selector': 'tag:missing'})
        html, parsed = self.build('--unit-index', 'on', '--unit-index-selector', 'tag:focus')
        self.assertEqual(self.targets(parsed, 'lwp-index'), ['detail'])
        self.assertIn('&quot;type&quot;:&quot;unit-index&quot;', html)
        self.fixture([COVER, STANDARD], meta='unit_index_selector: slide:type:cover\n')
        _, parsed = self.build('--unit-index', 'on', '--unit-index-selector', 'tag:focus')
        self.assertEqual(self.targets(parsed, 'lwp-index'), ['cover'])

    def test_placement_skips_excluded_cover_and_explicit_indexes_suppress_auto(self):
        self.fixture([COVER.replace('slug: cover', 'slug: hidden\ntags: excluded'),
                      STANDARD, COVER], meta='unit_index: on\n')
        _, parsed = self.build()
        self.assertEqual(parsed.sections, ['detail', 'cover', 'lwp-index'])
        self.fixture([STANDARD], meta='unit_index: on\n')
        _, parsed = self.build()
        self.assertEqual(parsed.sections, ['lwp-index', 'detail'])
        self.fixture([INDEX.format(fields=''), STANDARD], meta='unit_index: on\n')
        _, parsed = self.build()
        self.assertEqual(parsed.sections, ['contents', 'detail'])

    def test_generated_identity_collision_is_fatal_even_with_prefix(self):
        self.fixture([COVER.replace('slug: cover', 'slug: lwp-index')],
                     meta='unit_index: on\nslug_prefix: unit-\n')
        result = support.run('build', str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unit-lwp-index', result.stderr)
        self.assertIn('already used', result.stderr)

    def test_auto_does_not_conceal_empty_or_invalid_source(self):
        for slides in ([], ['<!-- lwp:slide:typo -->\nslug: bad\n']):
            with self.subTest(slides=slides):
                self.fixture(slides, meta='unit_index: on\n')
                result = support.run('build', str(self.root))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_invalid_index_fields_values_and_missing_slug_fail_cleanly(self):
        invalid = ['index-max-columns: 0\n', 'index-max-columns: -2\n',
                   'index-max-columns: 1.5\n', 'index-max-columns: true\n',
                   'Unexpected free body.\n', 'highlight: invisible\n',
                   '# Wrong heading\n']
        for fields in invalid:
            with self.subTest(fields=fields):
                self.fixture([INDEX.format(fields=fields)])
                result = support.run('build', str(self.root))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('unit-index' if 'columns' not in fields else 'positive integer',
                              result.stderr)
                self.assertNotIn('Traceback', result.stderr)
        self.fixture([INDEX.replace('slug: contents\n', '').format(fields='')])
        result = support.run('build', str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('slug:', result.stderr)

    def test_index_fields_are_not_silently_accepted_on_other_types(self):
        for slide in (COVER, STANDARD,
                      '<!-- lwp:slide:series-nav -->\nslug: nav\n',
                      '<!-- lwp:slide:full-article -->\nslug: full\narticle: body.md\n'):
            for field in ('index-selector: *\n', 'index-max-columns:\n'):
                with self.subTest(slide=slide, field=field):
                    self.fixture([slide + field])
                    result = support.run('build', str(self.root))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('Traceback', result.stderr)

    def test_plain_link_labels_and_speaker_notes_preserve_editorial_footer(self):
        self.fixture([COVER.replace('Opening', '<a href="https://example.test">A &amp; B</a>'),
                      INDEX.format(fields='kicker: Read\nsummary: Choose a slide.\n'
                                          'note: Speak softly.\ncomment: Private review.\n')],
                     meta='author: Writer\nlicense: CC0\n')
        html, parsed = self.build()
        self.assertEqual(parsed.indexes['contents']['links'][0]['title'], 'A & B')
        self.assertIn('<div class="speaker-note" hidden>Speak softly.</div>', html)
        self.assertNotIn('Private review.', html)
        self.assertIn('Choose a slide.', html)
        self.assertIn('Writer', html)
        self.assertIn('CC0', html)

    def test_existing_kit_standard_layout_and_chrome_are_used_without_manifest_change(self):
        self.fixture([COVER, INDEX.format(fields='')],
                      series_meta={'presentation_preset': support.IdentityKitFixtures.SELECTOR})
        fixture = support.IdentityKitFixtures()
        identity_kit = fixture._write_identity_kit(self.root / 'templates' / 'kits')
        manifest_path = identity_kit / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        preset = manifest['presets']['brief']
        preset['slide_chrome']['standard'] = {'header': 'Standard header'}
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        before = manifest_path.read_bytes()
        html, parsed = self.build()
        self.assertEqual(self.targets(parsed), ['cover', 'contents'])
        index_section = html.split('id="contents"', 1)[1].split('</section>', 1)[0]
        self.assertIn('presentation-studio-standard', index_section)
        self.assertIn('Standard header', index_section)
        self.assertIn('Kit footer', index_section)
        self.assertEqual(manifest_path.read_bytes(), before)

    def test_dedicated_kit_index_layout_and_chrome_override_standard_fallback(self):
        self.fixture([INDEX.format(fields='')],
                      series_meta={'presentation_preset': support.IdentityKitFixtures.SELECTOR})
        fixture = support.IdentityKitFixtures()
        identity_kit = fixture._write_identity_kit(self.root / 'templates' / 'kits')
        path = identity_kit / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['layouts']['unit-index'] = {'default': 'layouts/cover.html'}
        manifest['presets']['brief']['slide_chrome']['unit-index'] = {'header': 'Dedicated header'}
        path.write_text(json.dumps(manifest), encoding='utf-8')
        html, _ = self.build()
        index_section = html.split('id="contents"', 1)[1].split('</section>', 1)[0]
        self.assertIn('presentation-studio-cover', index_section)
        self.assertIn('Dedicated header', index_section)

    def test_preset_variants_keep_identical_index_targets_and_ordinals(self):
        fixture = support.IdentityKitFixtures()
        root, _, _, _, _ = fixture._runtime_series(self.root)
        source = root / 'sources' / 'a.md'
        source.write_text(source.read_text() + '\n---\n\n'
                          + INDEX.format(fields='index-selector: slide:type:cover\n'),
                          encoding='utf-8')
        html, parsed = self.build()
        expected = parsed.indexes['contents']['links']
        variants = fixture._presentation_data(html)['variants']
        self.assertGreater(len(variants), 1)
        for selector, variant in variants.items():
            with self.subTest(selector=selector):
                markup = ('<section class="slide" id="contents">'
                          + variant['sections']['contents'] + '</section>')
                self.assertEqual(IndexHTML(markup).indexes['contents']['links'], expected)

    def test_invalid_automatic_values_fail_cleanly(self):
        for config in ({'unit_index': 'maybe'}, {'unit_index_max_columns': True},
                       {'unit_index_max_columns': 0}, {'unit_index_selector': []}):
            with self.subTest(config=config):
                self.fixture([COVER], series_meta=config)
                result = support.run('build', str(self.root))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_resolve_reports_unit_index_defaults_and_unit_overrides(self):
        self.fixture([COVER], meta='unit_index: off\nunit_index_max_columns: 3\n',
                     series_meta={'unit_index': 'on', 'unit_index_max_columns': 2})
        for field, expected in (('unit_index', False), ('unit_index_max_columns', 3),
                                ('unit_index_selector', '*')):
            result = support.run('resolve', str(self.root), field, '--article', 'a.md', '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr)
            resolution = json.loads(result.stdout)['resolution']
            self.assertEqual(resolution['value'], expected)
            self.assertEqual(resolution['source'], 'default' if field == 'unit_index_selector' else 'article')
        text = support.run('resolve', str(self.root), 'unit_index', '--article', 'a.md')
        self.assertIn('value: False', text.stdout)
        self.assertNotIn('value: (empty)', text.stdout)
        self.build()

    def test_verify_uses_the_same_in_memory_index_settings(self):
        self.fixture([COVER, STANDARD])
        self.build('--unit-index', 'on')
        verified = support.run('verify', str(self.root), '--lang', 'en', '--unit-index', 'on')
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_audit_recognizes_index_metadata_and_reports_invalid_settings_without_blocking(self):
        self.fixture([COVER, STANDARD], meta='unit_index: on\nunit_index_max_columns: 2\n')
        audited = support.run('audit', str(self.root), '--lang', 'en')
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertNotIn('not a meta field', audited.stderr)
        self.assertNotIn('Traceback', audited.stderr)
        self.fixture([COVER], meta='unit_index_max_columns: invalid\n')
        audited = support.run('audit', str(self.root), '--lang', 'en')
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertIn('positive integer', audited.stderr)
        self.assertNotIn('Traceback', audited.stderr)


if __name__ == '__main__':
    unittest.main()
