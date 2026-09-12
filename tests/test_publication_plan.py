"""One publication universe and output inventory, across render topologies."""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest import mock

if __package__:
    from .test_lightwebpres import load_lightwebpres_module, run
else:
    from test_lightwebpres import load_lightwebpres_module, run

ROOT = Path(__file__).resolve().parents[1]


class PublicationPlanning(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.env = {'LWP_THEMES_DIR': str(self.root / 'themes'),
                    'LWP_COMMONS_DIR': str(self.root / 'commons'),
                    'LWP_IDENTITY_KITS_DIR': str(self.root / 'kits')}
        (self.root / 'sources').mkdir()
        (self.root / 'templates').mkdir()
        self.data = {'articles': [{'page_source': 'a.md'}, {'page_source': 'b.md'}]}
        for name in ('a', 'b'):
            (self.root / 'sources' / (name + '.md')).write_text(
                '<!-- lwp:meta -->\n---\n<!-- lwp:slide:cover -->\n'
                f'slug: cover\n# Article {name}\nsummary: Example.\n\n---\n'
                '<!-- lwp:slide:standard -->\nslug: body\n## Content\nOriginal body.\n',
                encoding='utf-8')
        self.save()

    def save(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')

    def cli(self, command, *options, code=0):
        result = run(command, str(self.root), *options, env=self.env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def kit(self):
        shutil.copytree(ROOT / 'examples/kits/lightwebpres-docs/0.1.0',
                        self.root / 'templates/kits/lightwebpres-docs/0.1.0')
        self.data['series_meta'] = {'presentation_preset': 'lightwebpres-docs@0.1.0/docs'}
        self.save()

    def presets(self):
        html = (self.root / 'public/a.html').read_text(encoding='utf-8')
        data = json.loads(re.search(
            r'<script id="lwp-presentation-data" type="application/json">(.*?)</script>', html, re.S)[1])
        return [item['selector'] for item in data['presets']]

    def snapshot(self):
        files = [self.root / 'README.md', self.root / '.lwp-cache/nav.json']
        files += list((self.root / 'public').rglob('*'))
        return {str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in files if path.is_file()}

    def test_ignored_and_omitted_draft_units_do_not_remove_published_presets(self):
        self.kit()
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace('slug: cover', 'slug: cover\nslide-layout: hero'))
        for status in ('ignored', 'draft'):
            with self.subTest(status=status):
                self.data['articles'][1]['status'] = status
                self.save()
                result = self.cli('build')
                self.assertNotIn('presentation is unavailable', result.stderr)
                self.assertIn('builtin/standard', self.presets())
        self.cli('build', '--include-drafts')
        self.assertNotIn('builtin/standard', self.presets())

    def test_excluded_slides_do_not_constrain_runtime_compatibility(self):
        self.kit()
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace(
            'slug: cover', 'slug: cover\ntags: excluded\nslide-layout: hero'))
        self.cli('build', '--presentation-presets', 'builtin/standard')
        self.assertIn('builtin/standard', self.presets())
        source.write_text(source.read_text().replace('tags: excluded\n', ''))
        self.cli('build', '--presentation-presets', 'builtin/standard', code=1)

    def test_ignored_kit_metadata_does_not_block_a_native_build_but_audit_sees_it(self):
        self.data['articles'][1]['status'] = 'ignored'
        self.save()
        source = self.root / 'sources/b.md'
        source.write_text(source.read_text().replace('slug: cover', 'slug: cover\nslide-layout: hero'))
        self.cli('build')
        result = run('audit', str(self.root), env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('b.md', result.stdout + result.stderr)

    def test_copied_image_freshness_is_independent_of_output_topology(self):
        image = self.root / 'sources/img/nested/logo.svg'
        image.parent.mkdir(parents=True)
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text() + '\n![Logo](img/nested/logo.svg)\n')
        for options in ((), ('--single-html', 'all.html')):
            with self.subTest(options=options):
                image.write_text('<svg xmlns="http://www.w3.org/2000/svg"><title>Before</title></svg>')
                self.cli('build', *options)
                image.write_text(image.read_text().replace('Before', 'After'))
                before = self.snapshot()
                result = self.cli('verify', *options, code=1)
                self.assertIn('[DRIFT] img/nested/logo.svg', result.stdout)
                self.assertEqual(self.snapshot(), before)
                self.cli('build', *options)
                (self.root / 'public/img/nested/logo.svg').unlink()
                result = self.cli('verify', *options, code=1)
                self.assertIn('[NEW] img/nested/logo.svg', result.stdout)

    def test_late_article_error_preserves_every_previous_output(self):
        a, b = [self.root / 'sources' / (name + '.md') for name in ('a', 'b')]
        originals = a.read_text(), b.read_text()
        for options in ((), ('--single-html', 'all.html')):
            with self.subTest(options=options):
                a.write_text(originals[0])
                b.write_text(originals[1])
                self.cli('build', *options)
                (self.root / 'public/CNAME').write_text('example.invalid')
                before = self.snapshot()
                a.write_text(originals[0].replace('Original body.', 'New body.'))
                b.write_text(originals[1].replace('slug: body', 'slug: cover'))
                self.cli('build', *options, code=1)
                self.assertEqual(self.snapshot(), before)

    def test_invalid_index_extension_fails_before_article_replacement(self):
        self.cli('build')
        before = self.snapshot()
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text().replace('Original body.', 'New body.'))
        (self.root / 'templates/index_extra.html').write_text('<script>function ( broken</script>')
        self.cli('build', code=1)
        self.assertEqual(self.snapshot(), before)

    def test_destination_conflict_is_detected_before_any_output_is_replaced(self):
        self.cli('build')
        destination = self.root / 'public/index.html'
        destination.unlink()
        destination.mkdir()
        before = self.snapshot()
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text().replace('Original body.', 'New body.'))
        self.cli('build', code=1)
        self.assertEqual(self.snapshot(), before)

    def test_metadata_planning_failure_preserves_previous_outputs(self):
        self.cli('build')
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text().replace('Original body.', 'New body.'))
        for invalid in ('[]', '{broken', '{"files":[{}]}', '{"previous":1}'):
            with self.subTest(invalid=invalid):
                (self.root / 'public/.lwp-manifest.json').write_text(invalid)
                before = self.snapshot()
                self.cli('build', code=1)
                self.assertEqual(self.snapshot(), before)

    def test_cache_cannot_claim_an_html_file_through_a_directory_alias(self):
        self.cli('build')
        (self.root / 'public/alias').symlink_to(self.root / 'public', target_is_directory=True)
        before = self.snapshot()
        self.cli('build', '--nav-cache', str(self.root / 'public/alias/a.html'), code=1)
        self.assertEqual(self.snapshot(), before)

    def test_planned_files_cannot_be_parents_of_other_outputs(self):
        self.cli('build')
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text().replace('Original body.', 'New body.'))
        (self.root / 'sources/c.md').write_text(source.read_text())
        self.data['articles'].append({'page_source': 'c.md'})
        self.save()
        before = self.snapshot()
        self.cli('build', '--nav-cache', str(self.root / 'public/c.html/nav.json'), code=1)
        self.assertEqual(self.snapshot(), before)

    def test_parsed_units_are_reused_but_render_mutations_are_isolated(self):
        self.kit()
        self.data['articles'] = self.data['articles'][:1]
        self.save()
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text() + '\n---\n<!-- lwp:slide:unit-index -->\nslug: contents\n')
        lwp = load_lightwebpres_module()
        with mock.patch.dict(os.environ, self.env), \
                mock.patch.object(lwp, 'parse_markdown_extended', wraps=lwp.parse_markdown_extended) as parse, \
                mock.patch.object(lwp, 'compile_selector', wraps=lwp.compile_selector) as compile_query:
            ctx = lwp.load_build_context(self.root, {})
            first = lwp._render_article(ctx, ctx.articles[0], source)
            second = lwp._render_article(ctx, ctx.articles[0], source)
            self.assertEqual(first, second)
            self.assertEqual(parse.call_count, 1)
            self.assertEqual(compile_query.call_count, 1)

    def test_local_light_and_native_light_keep_distinct_runtime_identities(self):
        result = run('theme', 'create', 'light', '--from', 'nord', '--label', 'Local Light', env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.cli('build', '--themes', 'all,builtin:light')
        html = (self.root / 'public/a.html').read_text(encoding='utf-8')
        data = json.loads(re.search(
            r'<script id="lwp-theme-data" type="application/json">(.*?)</script>', html, re.S)[1])
        ids = [item['slug'] for item in data['themes']]
        self.assertEqual(len(ids), len(set(ids)))
        native = [item for item in data['themes'] if item['label'] == 'Light']
        self.assertEqual([item['slug'] for item in native], ['builtin:light'])
        local = next(item for item in data['themes'] if item['slug'] == 'light')
        self.assertEqual(local['label'], 'Local Light')
        self.assertIsNone(local['identity'])

    def test_asset_read_failure_during_planning_leaves_all_outputs_intact(self):
        image = self.root / 'sources/img/logo.svg'
        image.parent.mkdir()
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        source = self.root / 'sources/a.md'
        source.write_text(source.read_text() + '\n![Logo](img/logo.svg)\n')
        self.cli('build')
        before = self.snapshot()
        source.write_text(source.read_text().replace('Original body.', 'Changed body.'))
        lwp = load_lightwebpres_module()
        original_stage = lwp._stage_file

        def fail_asset(path, content=None, source=None):
            if source == image:
                raise OSError('injected asset read failure')
            return original_stage(path, content=content, source=source)

        with mock.patch.dict(os.environ, self.env), mock.patch.object(lwp, '_stage_file', side_effect=fail_asset):
            with self.assertRaisesRegex(OSError, 'injected asset read failure'):
                lwp.cmd_build(self.root, {})
        self.assertEqual(self.snapshot(), before)
