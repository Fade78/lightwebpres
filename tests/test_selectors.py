"""Owned-field resolution and the bounded, publication-neutral selector core."""

import ast
import itertools
import json
import re
import tempfile
import time
import unittest
from unittest import mock

if __package__:
    from . import test_lightwebpres as support
else:
    import test_lightwebpres as support
load_lightwebpres_module = support.load_lightwebpres_module


class Selectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lwp = load_lightwebpres_module()

    def record(self, tags=None, status=None, **fields):
        unit = {} if status is None else {'status': status}
        slide = dict(fields, tags=tags or [])
        return self.lwp.make_selector_record({}, [
            {'source': 'meta', 'priority': 10, 'values': unit}], slide)

    def query(self, record, expression, selectors=None):
        return self.lwp.compile_selector(expression, selectors)(record)

    def test_scopes_and_both_directions_preserve_source_authority(self):
        scope = self.lwp.LogicalScope
        self.assertEqual([int(level) for level in scope], [0, 1, 2])
        declarations = [
            {'scope': scope.UNIT, 'source': 'meta', 'priority': 10, 'value': 'meta'},
            {'scope': scope.UNIT, 'source': 'json', 'priority': 20, 'value': 'json'},
            {'scope': scope.UNIT, 'source': 'derived', 'priority': 0, 'value': 'derived'},
        ]
        for policy in ('specific-first', 'general-first', 'source-order'):
            with self.subTest(policy=policy):
                result = self.lwp.resolve_scoped(declarations, policy)
                self.assertEqual((result['value'], result['scope'], result['source']),
                                 ('json', 1, 'json'))
                self.assertEqual([item['source'] for item in result['candidates']],
                                 ['json', 'meta', 'derived', 'default'])
        declarations.append({'scope': scope.SERIES, 'source': 'series',
                             'priority': 100, 'value': 'series'})
        declarations.append({'scope': scope.SLIDE, 'source': 'slide',
                             'priority': 0, 'value': 'slide'})
        self.assertEqual(self.lwp.resolve_scoped(declarations)['value'], 'slide')
        for policy in ('general-first', 'source-order'):
            self.assertEqual(self.lwp.resolve_scoped(declarations, policy)['value'], 'series')
        self.assertNotIn('present', declarations[0])

    def test_fallbacks_absence_false_clear_and_field_specific_accept(self):
        candidates = [
            {'scope': None, 'source': 'registry', 'priority': 999, 'value': 'registry'},
            {'scope': 2, 'source': 'absent', 'value': 'absent', 'present': False},
            {'scope': 2, 'source': 'noncontributing', 'value': 1, 'contributes': False},
            {'scope': 1, 'source': 'unit', 'value': False},
            {'scope': 0, 'source': 'series', 'value': True},
        ]
        self.assertIs(self.lwp.resolve_scoped(candidates)['value'], False)
        self.assertIs(self.lwp.resolve_scoped(candidates, 'general-first')['value'], True)
        self.assertEqual(self.lwp.resolve_scoped(candidates[:3])['source'], 'registry')
        for value in ('', None, [], {}):
            with self.subTest(value=value):
                candidates[3]['value'] = value
                self.assertEqual(self.lwp.resolve_scoped(candidates)['value'], value)
                self.assertIs(self.lwp.resolve_scoped(candidates, accept=bool)['value'], True)
        self.assertEqual(self.lwp.resolve_scoped([], default='last')['value'], 'last')
        self.assertEqual(self.lwp.resolve_scoped([], default='last', accept=lambda v: False)['value'], 'last')

    def test_stable_ties_and_invalid_resolution_requests(self):
        candidates = [{'scope': 1, 'source': 'first', 'value': 1},
                      {'scope': 1, 'source': 'second', 'value': 2}]
        self.assertEqual(self.lwp.resolve_scoped(candidates)['value'], 1)
        with self.assertRaises(ValueError):
            self.lwp.resolve_scoped([], 'ascending')
        for scope in (-1, 3, 'unit', True):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                self.lwp.resolve_scoped([{'scope': scope, 'value': 1}])
        with self.assertRaises(ValueError):
            self.lwp.resolve_scoped([{'scope': 1, 'priority': '20', 'value': 1}])

    def test_source_order_accepts_unscoped_cli_authority_but_not_as_a_parent(self):
        candidates = [
            {'scope': 1, 'source': 'unit-meta', 'priority': 30, 'value': 'unit'},
            {'scope': None, 'fallback': False, 'source': 'command line',
             'priority': 20, 'value': False},
            {'scope': 0, 'source': 'series', 'priority': 10, 'value': 'series'},
            {'scope': None, 'source': 'registry', 'priority': 0, 'value': 'registry'},
        ]
        for index, expected in enumerate(('unit', False, 'series', 'registry')):
            result = self.lwp.resolve_scoped(candidates, 'source-order', default='last')
            self.assertEqual(result['value'], expected)
            self.assertEqual(result['source'], candidates[index]['source'])
            if index == 1:
                self.assertIsNone(result['scope'])
                self.assertFalse(result['candidates'][1]['fallback'])
            candidates[index]['present'] = False
        self.assertEqual(self.lwp.resolve_scoped(candidates, 'source-order', default='last')['value'], 'last')
        for policy in ('specific-first', 'general-first'):
            with self.subTest(policy=policy), self.assertRaisesRegex(ValueError, 'require source-order'):
                self.lwp.resolve_scoped(candidates, policy)
        # Fallback is independent of both source authority and logical rank.
        candidates[0]['present'] = True
        candidates[3].update(scope=2, fallback=True, present=True, priority=999)
        self.assertEqual(self.lwp.resolve_scoped(candidates, 'source-order')['value'], 'unit')
        for flag in (0, 1, None, 'false'):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, 'must be a boolean'):
                self.lwp.resolve_scoped([{'scope': None, 'fallback': flag}], 'source-order')

    def test_resolve_before_matching_does_not_resurrect_masked_metadata(self):
        record = self.lwp.make_selector_record({}, [
            {'source': 'json', 'priority': 20, 'values': {'status': 'draft', 'author': ' '}},
            {'source': 'meta', 'priority': 10, 'values': {'status': 'active', 'author': 'Meta'}},
        ], {'tags': ['default']})
        self.assertTrue(self.query(record, 'status:draft'))
        for query in ('status:active', 'unit:status:active', 'general:status:active'):
            self.assertFalse(self.query(record, query))
        self.assertEqual(record['effective']['author'], ' ')
        origin = record['origin']['status']
        self.assertEqual((origin['source'], origin['scope']), ('json', 1))
        self.assertEqual(len(origin['candidates']), 3)
        self.assertTrue(self.query(record, '$[? @.origin.status.source == "json" && @.origin.status.scope == 1]'))
        self.assertTrue(self.query(record, '$[? @.origin.status.candidates[? @.source == "meta" && @.value == "active"]]'))

    def test_qualified_effective_specific_general_and_missing_scopes(self):
        record = self.lwp.make_selector_record({'author': 'Series'}, [
            {'source': 'meta', 'priority': 10, 'values': {'author': 'Unit'}}],
            {'author': 'Slide'})
        for query in ('author:Slide', 'specific:author:Slide', 'general:author:Series',
                      'unit:author:Unit', 'series:author:Series', 'slide:author:Slide'):
            self.assertTrue(self.query(record, query), query)
        self.assertFalse(self.query(record, 'unit:author:Slide'))
        self.assertFalse(self.query(record, 'series:status:active'))
        self.assertNotIn('status', record['unit'])
        self.assertNotIn('status', record['series'])
        self.assertNotIn('status', record['slide'])
        self.assertTrue(self.query(record, 'status:active'))
        simulation = self.lwp.make_selector_record({'status': 'draft'}, [], {'status': 'ignored'})
        self.assertTrue(self.query(simulation, 'status:ignored general:status:draft'))

    def test_explicit_empty_status_is_not_an_active_fallback(self):
        record = self.record(status='')
        self.assertFalse(self.query(record, 'status:active'))
        self.assertTrue(self.query(record, 'status:""'))

    def test_metadata_profile_applies_before_every_view_without_dropping_trace(self):
        policies = self.lwp._article_selector_field_policies()
        sources = [
            {'source': 'series-entry', 'priority': 20,
             'values': {'status': '', 'author': ''}},
            {'source': 'unit-meta', 'priority': 10,
             'values': {'status': 'draft', 'author': '', 'notes_placement': ' \t ',
                        'enabled': False, 'tags': []}},
        ]
        series = {'author': 'Shared', 'notes_placement': 'page',
                  'tags': ['series'], 'slide-header': 'Inherited'}
        slide = {'slide-header': '', 'tags': []}
        record = self.lwp.make_selector_record(series, sources, slide, field_policies=policies)
        for query in ('status:draft', 'unit:status:draft', 'specific:status:draft',
                      'general:status:draft', 'author:Shared', 'general:author:Shared',
                      'notes_placement:page', 'slide:slide-header:""', 'slide-header:""',
                      '$[? @.specific.enabled == false]'):
            self.assertTrue(self.query(record, query), query)
        self.assertNotIn('author', record['unit'])
        self.assertNotIn('notes_placement', record['unit'])
        self.assertNotIn('status', record['series'])
        self.assertNotIn('status', record['slide'])
        self.assertEqual(record['unit']['tags'], [])
        self.assertEqual(record['effective']['tags'], [])
        for field, source, raw in (('status', 'series-entry', ''),
                                   ('author', 'series-entry', ''),
                                   ('author', 'unit-meta', ''),
                                   ('notes_placement', 'unit-meta', ' \t ')):
            candidate = next(item for item in record['origin'][field]['candidates']
                             if item['source'] == source)
            self.assertEqual(candidate['value'], raw)
            self.assertTrue(candidate['present'])
            self.assertFalse(candidate['contributes'])
        # Opt-in profile: simulated fields and unprofiled records retain clears.
        raw = self.lwp.make_selector_record(series, sources, slide)
        self.assertEqual(raw['effective']['status'], '')
        self.assertEqual(raw['effective']['author'], '')
        self.assertEqual(raw['unit']['notes_placement'], ' \t ')
        self.assertNotIn('contributes', sources[0]['values'])

    def test_metadata_profile_preserves_whitespace_author_and_normal_status_fallback(self):
        sources = [{'source': 'series-entry', 'priority': 20,
                    'values': {'author': ' ', 'status': ''}},
                   {'source': 'unit-meta', 'priority': 10, 'values': {'author': 'Meta'}}]
        record = self.lwp.make_selector_record({'author': 'Shared'}, sources, {},
                                               self.lwp._article_selector_field_policies())
        self.assertEqual(record['effective']['author'], ' ')
        self.assertEqual(record['unit']['author'], ' ')
        self.assertEqual(record['effective']['status'], 'active')
        self.assertNotIn('status', record['unit'])
        self.assertIsNone(record['origin']['status']['scope'])
        self.assertEqual(record['origin']['status']['source'], 'default')

    def test_caller_field_policy_does_not_become_a_global_blank_rule(self):
        record = self.lwp.make_selector_record({'summary': 'Inherited'}, [],
                                               {'summary': '', 'status': False, 'title': ''},
                                               {'summary': bool})
        self.assertEqual(record['effective']['summary'], 'Inherited')
        self.assertNotIn('summary', record['slide'])
        self.assertEqual(record['slide']['title'], '')
        self.assertIs(record['effective']['status'], False)

    def test_notes_and_numbering_helpers_use_the_core_without_changing_valid_values(self):
        notes_cases = (
            ({}, {}, ('local', False)),
            ({'notes_placement': 'local'}, {'notes_placement': 'page', 'notes_tooltip': 'on'}, ('local', True)),
            ({'notes_placement': ' \t ', 'notes_tooltip': ''},
             {'notes_placement': 'page', 'notes_tooltip': 'on'}, ('page', True)),
            ({'notes_placement': ' PAGE ', 'notes_tooltip': ' OFF '},
             {'notes_placement': 'invalid', 'notes_tooltip': 'invalid'}, ('page', False)),
        )
        with mock.patch.object(self.lwp, 'resolve_scoped', wraps=self.lwp.resolve_scoped) as resolver:
            with mock.patch.object(self.lwp, 'log') as log:
                for meta, series, expected in notes_cases:
                    with self.subTest(meta=meta, series=series):
                        self.assertEqual(self.lwp.resolve_notes_settings(meta, series, 'unit.md'), expected)
                log.assert_not_called()
            self.assertEqual(resolver.call_count, 2 * len(notes_cases))
            self.assertTrue(all(call.kwargs['policy'] == 'specific-first' for call in resolver.call_args_list))

        numbering_cases = (
            ({}, {}, {}, False),
            ({'slide_page_numbers': False}, {'slide_page_numbers': True},
             {'--slides-page-numbers': 'on'}, False),
            ({'slide_page_numbers': ' \t '}, {'slide_page_numbers': True},
             {'--slides-page-numbers': 'off'}, False),
            ({}, {'slide_page_numbers': True}, {}, True),
            ({}, {'slide_page_numbers': True}, {'--slides-page-numbers': None}, True),
            ({'slide_page_numbers': ' YES '}, {'slide_page_numbers': 'invalid'},
             {'--slides-page-numbers': 'invalid'}, True),
            ({}, {'slide_page_numbers': 'invalid'}, {'--slides-page-numbers': False}, False),
        )
        with mock.patch.object(self.lwp, 'resolve_scoped', wraps=self.lwp.resolve_scoped) as resolver:
            with mock.patch.object(self.lwp, 'log') as log:
                for meta, series, args, expected in numbering_cases:
                    with self.subTest(meta=meta, series=series, args=args):
                        self.assertIs(self.lwp.resolve_slide_page_numbers(meta, series, 'unit.md', args), expected)
                log.assert_not_called()
            self.assertEqual(resolver.call_count, len(numbering_cases))
            self.assertTrue(all(call.kwargs['policy'] == 'source-order' for call in resolver.call_args_list))
            candidates = resolver.call_args.args[0]
            cli = next(item for item in candidates if item['source'] == 'command line')
            self.assertIsNone(cli['scope'])
            self.assertFalse(cli['fallback'])

    def test_notes_error_recovery_reports_only_invalid_winners_in_original_order(self):
        errors = []
        with mock.patch.object(self.lwp, 'log') as log:
            result = self.lwp.resolve_notes_settings(
                {'notes_placement': 'SIDEWAYS', 'notes_tooltip': False},
                {'notes_placement': 'OTHER', 'notes_tooltip': 'on'}, 'unit.md', errors)
        self.assertEqual(result, ('local', True))
        self.assertEqual(errors, ['notes_placement', 'notes_placement', 'notes_tooltip'])
        self.assertEqual(log.call_args_list, [
            mock.call('error', "unit.md: notes_placement: 'sideways' is not a valid value (local | page)."),
            mock.call('error', "series.json: notes_placement: 'other' is not a valid value (local | page)."),
            mock.call('error', "unit.md: notes_tooltip: 'false' is not a valid value (off | on)."),
        ])
        # None is not an empty string in this existing structural resolver.
        with mock.patch.object(self.lwp, 'log') as log, self.assertRaises(SystemExit) as raised:
            self.lwp.resolve_notes_settings({'notes_placement': None}, {'notes_placement': 'page'}, 'unit.md')
        self.assertEqual(raised.exception.code, 1)
        log.assert_called_once_with('error', "unit.md: notes_placement: 'none' is not a valid value (local | page).")

    def test_numbering_preserves_cli_blank_errors_and_origin_labels(self):
        for meta, series, args, origin, value in (
                ({'slide_page_numbers': None}, {'slide_page_numbers': True}, {}, 'unit.md', None),
                ({}, {'slide_page_numbers': True}, {'--slides-page-numbers': ''}, 'command line', ''),
                ({}, {'slide_page_numbers': True}, {'--slides-page-numbers': ' '}, 'command line', ' '),
                ({'slide_page_numbers': ''}, {'slide_page_numbers': 'bad'}, {}, 'series.json', 'bad')):
            with self.subTest(origin=origin, value=value):
                with mock.patch.object(self.lwp, 'log') as log, self.assertRaises(SystemExit) as raised:
                    self.lwp.resolve_slide_page_numbers(meta, series, 'unit.md', args)
                self.assertEqual(raised.exception.code, 1)
                log.assert_called_once_with('error', '%s: slide_page_numbers: %r is not a valid value (on | off).' % (origin, value))
        report = self.lwp.resolve_notes_field('notes_tooltip', {'notes_tooltip': 'on'}, {'notes_tooltip': 'off'})
        self.assertEqual((report['value'], report['source']), ('off', 'article'))
        self.assertEqual([link['level'] for link in report['chain']], ['article', 'series-default', 'default'])

    def test_slide_tags_do_not_absorb_the_unit_gate_or_default_visibility(self):
        record = self.lwp.make_selector_record({'tags': ['series']}, [
            {'source': 'json', 'priority': 20, 'values': {'tags': ['red']}}],
            {'tags': ['blue', 'default']})
        self.assertFalse(self.query(record, 'red'))
        self.assertTrue(self.query(record, 'blue unit:tag:red series:tag:series'))
        self.assertFalse(self.query(record, 'series'))
        self.assertFalse(self.query(record, 'unrelated'))
        self.assertTrue(self.query(record, 'default'))
        record = self.lwp.make_selector_record({}, [
            {'source': 'json', 'priority': 20, 'values': {'tags': ['red']}}], {})
        self.assertFalse(self.query(record, 'red'))
        self.assertTrue(self.query(record, 'unit:tag:red'))
        self.assertEqual(record['effective']['tags'], [])

    def test_star_is_entire_input_in_order_with_identity_deduplication(self):
        records = [self.record(status=status, type=kind) for status, kind in
                   [('draft', 'unit-index'), ('ignored', 'full-article'), ('active', 'cover')]]
        for expression in ('*', '$[*]', '* | status:draft'):
            selected = self.lwp.select_records(records + records, expression)
            self.assertEqual(len(selected), 3)
            self.assertTrue(all(left is right for left, right in zip(selected, records)))
        self.assertEqual(self.lwp.select_records(records[2:], '*'), records[2:])
        self.assertEqual(self.lwp.select_records([{}, {}], '*'), [{}, {}])

    def test_record_generators_do_not_lose_items_to_recycled_object_ids(self):
        def records():
            for index in range(200):
                yield {'effective': {'tags': ['keep'] if index % 4 == 0 else []},
                       'ordinal': index}
        selected = self.lwp.select_records(records(), 'keep')
        self.assertEqual([record['ordinal'] for record in selected], list(range(0, 200, 4)))

    def test_compact_boolean_precedence_literal_words_and_negative_tags(self):
        record = self.record(['expert-en', 'AND', 'OR', 'NOT', '-literal'])
        for expression in ('expert-en', 'tag:expert-en', 'AND OR NOT', 'tag:-literal',
                           '-absent expert-en', 'absent | expert-en AND',
                           '(expert-en | absent) -missing', '-(missing | other)',
                           '"-literal"', 'tag:"AND"', '-literal'):
            self.assertTrue(self.query(record, expression), expression)
        for expression in ('-expert-en', 'expert-en missing | other',
                           'expert-en -(AND | missing)'):
            self.assertFalse(self.query(record, expression), expression)

    def test_compact_tag_literals_follow_existing_casefolding(self):
        record = self.record(['expert-en', 'strasse'])
        for expression in ('EXPERT-EN', 'tag:Expert-En', 'slide:tags:EXPERT-EN', 'tag:Stra\u00dfe'):
            self.assertTrue(self.query(record, expression), expression)
        self.assertFalse(self.query(record, '-tag:EXPERT-EN'))
        self.assertFalse(self.query(record, '$[? @.slide.tags[? @ == "EXPERT-EN"]]'))

    def test_quoted_punctuation_escaping_and_unicode(self):
        record = self.record(['a:b (c)|d', 'line\nbreak', 'caf\u00e9', '\U0001f642', 'quote"slash\\'])
        for expression in ('tag:"a:b (c)|d"', 'tag:"line\\nbreak"',
                           'tag:"caf\\u00e9"', 'caf\u00e9', '"\\ud83d\\ude42"',
                           r'tag:"quote\"slash\\"'):
            self.assertTrue(self.query(record, expression), expression)
        self.assertTrue(self.query(record, '$[? @.slide.tags[? @ == "caf\\u00e9"]]'))
        self.assertTrue(self.query(self.record(summary='a/b'), r'summary:/a\/b/'))

    def test_named_selectors_compile_as_shared_predicates(self):
        from types import MappingProxyType
        names = {'english': 'expert-en -status:draft',
                 'content': 'selector:english | summary:/summary$/',
                 'json': '$[? @.effective.status == "active"]'}
        predicate = self.lwp.compile_selector('selector:content selector:json', names)
        self.assertTrue(predicate(self.record(['expert-en'])))
        self.assertTrue(self.query(self.record(['expert-en']), 'selector:english',
                                   MappingProxyType(names)))
        self.assertFalse(predicate(self.record(['expert-en'], status='draft')))
        self.assertTrue(predicate(self.record(summary='A summary')))
        self.assertFalse(self.query(self.record(['english']), 'selector:english', names))
        self.assertTrue(self.query(self.record(['english']), 'english', names))
        names['english'] = 'missing'
        self.assertTrue(predicate(self.record(['expert-en'])))

    def test_named_errors_even_in_unreachable_boolean_branches(self):
        for expression, names in (
                ('* | selector:missing', {}),
                ('selector:a', {'a': 'selector:a'}),
                ('selector:a', {'a': 'selector:b', 'b': 'selector:a'}),
                ('selector:a', {'a': '$..*'}),
                ('selector:a', {'a': 3})):
            with self.subTest(expression=expression, names=names), self.assertRaises(self.lwp.SelectorError):
                self.lwp.compile_selector(expression, names)
        self.assertTrue(self.query({}, '*', {'unused': 'selector:unknown'}))

    def test_jsonpath_profile_boolean_scalar_comparisons_and_existence(self):
        record = self.record(status='draft', score=3, enabled=False, clear=None, blank='')
        for expression in (
                '$[*]', '$[?(@.effective.status == "draft")]',
                '$[? @.slide.score >= 3 && @.slide.score < 4]',
                '$[? @.slide.enabled == false && @.slide.enabled != 0]',
                '$[? @.slide.clear == null && @.slide.clear]',
                '$[? @.slide.enabled && @.slide.blank]',
                '$[? !@.slide.missing]',
                '$[? @.slide.score == 3.0 || @.slide.missing]',
                '$[? !(@.slide.score > 4 || @.slide.score <= 2)]'):
            self.assertTrue(self.query(record, expression), expression)
        for expression in ('$[? @.slide.missing == null]', '$[? @.slide.missing != null]',
                           '$[? @.slide.missing != @.slide.other]',
                           '$[? @.slide.enabled == 0]', '$[? @.slide.enabled < true]',
                           '$[? @.slide.score == "3"]', '$[? @.slide.tags == null]'):
            self.assertFalse(self.query(record, expression), expression)

    def test_jsonpath_quoted_fields_and_nested_array_filter_existence(self):
        record = self.record(['expert-en', 'expert-fr'], **{'fact-label': 'Evidence',
                             'groups': [{'tags': ['red']}, {'tags': ['blue']}]})
        for expression in (
                "$[? @['slide']['fact-label'] == 'Evidence']",
                '$[? @.slide.tags[? @ == "expert-en"]]',
                '$[? @.slide.tags[? match(@, "expert-[a-z]{2}")]]',
                '$[? @.slide.groups[? @.tags[? @ == "blue"]]]'):
            self.assertTrue(self.query(record, expression), expression)
        self.assertFalse(self.query(record, '$[? @.slide.tags[? @ == "red"]]'))
        self.assertFalse(self.query(record, '$[? @.slide.missing[? @ == "red"]]'))

    def test_regex_search_full_match_anchors_classes_and_quantifiers(self):
        cases = [
            ('summary:/.*summary$/', 'Useful summary', True),
            ('summary:/summary/', 'Useful summary today', True),
            ('summary:/^summary$/', 'Useful summary', False),
            ('summary:/^summary$/', 'summary\n', False),
            ('summary:/^caf\u00e9 [a-z]+[0-9]?$/', 'caf\u00e9 abc2', True),
            ('summary:/^[^0-9]{2,4}$/', '\u00e9\u03bb', True),
            ('summary:/^[^0-9]{2,4}$/', 'ab3', False),
            ('summary:/^a{2,}b?$/', 'aaa', True),
            ('summary:/^a{0}b$/', 'b', True),
            ('summary:/^a*b+c?$/', 'bb', True),
            ('summary:/^a*b+c?$/', 'ac', False),
            ('summary:/^a*b*$/', 'ba', False),
            ('summary:/^a*b*$/', 'aabb', True),
            ('summary:/^[-a]+$/', '--a', True),
            (r'summary:/^a\+b$/', 'a+b', True),
            ('summary:/^.$/', '\n', False),
            (r'summary:/^\n$/', '\n', True),
            ('$[? search(@.slide.summary, "summary")]', 'A summary here', True),
            ('$[? match(@.slide.summary, "summary")]', 'A summary here', False),
            ('$[? match(@.slide.summary, "summary")]', 'summary', True),
            ('summary://', '', True),
        ]
        for expression, value, expected in cases:
            with self.subTest(expression=expression, value=value):
                self.assertEqual(self.query(self.record(summary=value), expression), expected)
        self.assertFalse(self.query(self.record(score=3), '$[? search(@.slide.score, "3")]'))

    def test_nfa_agrees_with_reference_on_small_supported_languages(self):
        # Python re is only a test oracle on tiny, generated, nonhostile inputs.
        texts = [''.join(chars) for size in range(5)
                 for chars in itertools.product('ab\n', repeat=size)]
        for first, second in itertools.product(('a', 'b', '.', '[ab]', '[^a]'), repeat=2):
            for left, right in itertools.product(('', '*', '+', '?', '{0,2}'), repeat=2):
                pattern = first + left + second + right
                compiled = self.lwp._SelectorRegex(pattern)
                reference = re.compile(pattern)
                for text in texts:
                    self.assertEqual(compiled.test(text), reference.search(text) is not None,
                                     (pattern, text, 'search'))
                    self.assertEqual(compiled.test(text, full=True), reference.fullmatch(text) is not None,
                                     (pattern, text, 'match'))

    def test_unsupported_regex_is_fatal_not_a_python_backtracking_fallback(self):
        for pattern in ('(a+)+$', '(?=a)', '(a)\\1', 'a|b', r'\d+', r'\w', r'\p{L}',
                        'a*?', 'a++', '[z-a]', '[]', '[abc', 'a{2,1}', 'a{65}',
                        'a{,3}', 'a{2', 'a^b', 'a$b', 'a\\'):
            with self.subTest(pattern=pattern), self.assertRaises(self.lwp.SelectorError):
                self.lwp.compile_selector('* | summary:/' + pattern + '/')

    def test_syntax_errors_and_unknown_scopes_are_never_wildcards(self):
        for expression in ('', ' ', '| x', 'x |', '(x', 'x)', 'x || y', 'x & y',
                           'planet:status:draft', 'tag: x', 'unit: status:draft',
                           'unit:status :draft', 'tag:', 'tag:"x', 'tag:"\\q"',
                           'tag:"\\ud800"', 'summary:/x/i', '*junk',
                           '$..*', '$[0]', '$[? @.planet.status == "draft"]',
                           '$[? @.status == "draft"]', '$[? true]',
                           '$[? @.slide.score + 1 == 2]', '$[? @.slide.tags[0]]',
                           '$[? @.slide.*]', '$[? @.slide.score =~ "x"]',
                           '$[? search(@.slide.summary, @.slide.pattern)]',
                           '$[? length(@.slide.tags) > 0]', '$[? @.slide.score == 1e9999]'):
            with self.subTest(expression=expression), self.assertRaises(self.lwp.SelectorError):
                self.lwp.compile_selector(expression)

    def test_resource_limits_fail_clearly(self):
        for expression in ('x' * 4097, '(' * 33 + 'x' + ')' * 33,
                           '-' * 33 + 'x', ' '.join(['x'] * 130),
                           'summary:/' + 'x' * 513 + '/',
                           'summary:/' + 'x' * 256 + '/'):
            with self.subTest(expression=expression[:60]), self.assertRaises(self.lwp.SelectorError):
                self.lwp.compile_selector(expression)
        with self.assertRaises(self.lwp.SelectorError):
            self.query(self.record(summary='x' * 8193), 'summary:/x/')
        for expression in ('x', '$[? @.slide.tags[? @ == "x"]]'):
            with self.assertRaises(self.lwp.SelectorError):
                self.query(self.record(['x'] * 1025), expression)
        names = {'n%d' % i: 'selector:n%d' % (i + 1) for i in range(33)}
        names['n33'] = '*'
        with self.assertRaises(self.lwp.SelectorError):
            self.lwp.compile_selector('selector:n0', names)
        # The nesting budget spans named definitions, rather than resetting.
        names = {'a': '(' * 20 + 'selector:b' + ')' * 20,
                 'b': '(' * 20 + '*' + ')' * 20}
        with self.assertRaises(self.lwp.SelectorError):
            self.lwp.compile_selector('selector:a', names)
        names = {'n%d' % i: '*' for i in range(65)}
        with self.assertRaises(self.lwp.SelectorError):
            self.lwp.compile_selector(' | '.join('selector:n%d' % i for i in range(65)), names)

    def test_aggregate_regex_and_nested_filter_work_limits(self):
        expression = 'tag:/^' + 'a*' * 80 + 'b$/'
        with self.assertRaisesRegex(self.lwp.SelectorError, 'regex work'):
            self.query(self.record(['a' * 8192] * 3), expression)
        groups = [{'values': list(range(1000, 1100))} for unused in range(100)]
        with self.assertRaisesRegex(self.lwp.SelectorError, 'step limit'):
            self.query(self.record(groups=groups),
                       '$[? @.slide.groups[? @.values[? @ == -1]]]')

    def test_hostile_supported_regex_is_bounded_and_compiled_once(self):
        predicate = self.lwp.compile_selector('summary:/^' + 'a*' * 80 + 'b$/')
        record = self.record(summary='a' * 8192 + '')
        start = time.monotonic()
        self.assertFalse(predicate(record))
        self.assertLess(time.monotonic() - start, 5.0)
        # Reuse must not parse the regex or carry matches from the previous item.
        old = self.lwp._SelectorRegex.__init__
        def forbid_compile(*args):
            self.fail('Regex recompiled while evaluating a record')
        self.lwp._SelectorRegex.__init__ = forbid_compile
        try:
            self.assertTrue(predicate(self.record(summary='ab')))
            self.assertFalse(predicate(self.record(summary='ac')))
        finally:
            self.lwp._SelectorRegex.__init__ = old

    def test_shared_named_ast_does_not_expand_exponentially(self):
        names = {'n0': 'missing'}
        for index in range(1, 25):
            names['n%d' % index] = 'selector:n%d | selector:n%d' % (index - 1, index - 1)
        start = time.monotonic()
        self.assertFalse(self.query(self.record(), 'selector:n24', names))
        self.assertLess(time.monotonic() - start, 1.0)

    def test_new_core_uses_python38_syntax_without_eval_or_exec(self):
        import inspect
        source = inspect.getsource(self.lwp).split(
            '# Logical selection is independent of physical output and publication policy.\n', 1)[1]
        source = source.split('\nclass SlideType:', 1)[0]
        tree = ast.parse(source, feature_version=(3, 8))
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id in ('eval', 'exec') for node in ast.walk(tree)))


class SelectorMetadataBuild(unittest.TestCase):
    def targets(self, query, meta='', entry=None, notes=False):
        from tests import test_unit_index as index_support
        with tempfile.TemporaryDirectory(dir=support.EXECUTABLE.parent / 'work' / 'tmp') as tmp:
            slide = index_support.STANDARD
            if notes:
                slide += '\nText[^1].\n\n[^1]: A note body.\n'
                meta += 'notes_placement: page\n'
            text = index_support.META.format(meta=meta) + '\n---\n\n'.join((
                index_support.COVER,
                index_support.INDEX.format(fields='index-selector: ' + query + '\n'), slide))
            root = support.scaffold(tmp, text, entry)
            path = root / 'series.json'
            data = json.loads(path.read_text(encoding='utf-8'))
            data['series_meta'] = {'author': 'Shared'}
            path.write_text(json.dumps(data), encoding='utf-8')
            result = support.run('build', str(root), '--lang', 'en', '--include-drafts')
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = index_support.IndexHTML((root / 'public' / 'a.html').read_text(encoding='utf-8'))
            return [link['attrs']['data-lwp-index-target'] for link in parsed.indexes['contents']['links']]

    def test_empty_json_status_falls_through_to_meta_before_querying(self):
        for query in ('status:draft unit:status:draft general:status:draft slide:slug:detail',
                      '$[? @.effective.status == "draft" && @.slide.slug == "detail" && '
                      '@.origin.status.candidates[? @.source == "series-entry" && '
                      '@.value == "" && @.present == true && @.contributes == false]]'):
            with self.subTest(query=query):
                self.assertEqual(self.targets(query, meta='status: DRAFT\n', entry={'status': ''}), ['detail'])

    def test_empty_unit_authors_fall_through_to_series_without_inheriting_into_unit(self):
        for query in ('author:Shared general:author:Shared -unit:author:Shared slide:slug:detail',
                      '$[? @.effective.author == "Shared" && !@.unit.author && '
                      '@.origin.author.scope == 0 && @.slide.slug == "detail"]'):
            with self.subTest(query=query):
                self.assertEqual(self.targets(query, meta='author:\n', entry={'author': ''}), ['detail'])
        self.assertEqual(self.targets('author:Shared -unit:author:Shared type:notes',
                                      meta='author:\n', entry={'author': ''}, notes=True), ['notes'])

    def test_whitespace_json_author_still_masks_meta_and_series(self):
        self.assertEqual(self.targets('unit:author:" " author:" " slide:slug:detail',
                                      meta='author: Meta\n', entry={'author': ' '}), ['detail'])


if __name__ == '__main__':
    unittest.main()
