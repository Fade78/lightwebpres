"""Explicit, independent Identity Kit recomposition through the public CLI."""

import copy
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SLIDE_TYPES = ('cover', 'standard', 'series-nav', 'full-article')
EXECUTABLE = Path(__file__).resolve().parent.parent / 'lightwebpres'


def run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(EXECUTABLE), *args], capture_output=True,
        text=True, env={**os.environ, **(env or {})}, timeout=120)


class KitCompose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loader = importlib.machinery.SourceFileLoader('kit_compose_tests', str(EXECUTABLE))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.lwp = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.lwp)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'result'
        self.destination = self.output / 'combined' / '1.2.3'
        self.recipe_path = self.root / 'recipe.json'
        self.recipe = {
            'schema': 'lightwebpres.kit-composition/1',
            'sources': {},
            'manifest': self.manifest('combined', '1.2.3'),
            'files': {},
        }

    @staticmethod
    def manifest(kit_id, version='1.0.0'):
        return {
            'schema': 'lightwebpres.identity-kit/1',
            'id': kit_id, 'version': version, 'label': 'Complete Identity Kit',
            'layouts': {kind: {'default': 'builtin:standard'} for kind in SLIDE_TYPES},
            'themes': {'palette': 'builtin:light'},
            'presets': {'brief': {
                'label': 'Brief', 'description': 'An explicit presentation.',
                'theme': 'palette',
                'slide_layouts': {kind: 'default' for kind in SLIDE_TYPES},
                'slide_chrome': {},
            }},
        }

    def source(self, kit_id):
        root = self.root / 'inputs' / kit_id / '1.0.0'
        root.mkdir(parents=True)
        manifest = self.manifest(kit_id)
        manifest['layouts']['cover']['default'] = 'cover.html'
        (root / 'cover.html').write_text(
            '<div class="selected-cover">{{slide_header}}{{content}}'
            '{{slide_footer}}</div>\n', encoding='utf-8')
        manifest['structure_css'] = 'structure.css'
        (root / 'structure.css').write_text(
            f'.lwp-presentation--{kit_id} .lwp-presentation--{kit_id}-child '
            '{ display: grid; }\n', encoding='utf-8')
        (root / 'assets').mkdir()
        (root / 'assets' / 'mark.png').write_bytes(b'\x89PNG\r\n\x1a\n\xff')
        manifest['assets'] = {'mark': {'path': 'assets/mark.png', 'kind': 'image'}}
        manifest['chrome'] = 'chrome.json'
        (root / 'chrome.json').write_text(json.dumps({'models': {
            'masthead': {'slot': 'header', 'items': [
                {'kind': 'image', 'asset': 'presentation:mark', 'alt': 'Mark'}]},
        }}), encoding='utf-8')
        (root / 'junk.txt').write_text('not a declared dependency', encoding='utf-8')
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        self.recipe['sources'][kit_id] = root.relative_to(self.root).as_posix()
        return root

    def compose(self, *args):
        self.recipe_path.write_text(json.dumps(self.recipe), encoding='utf-8')
        return run('kit', 'compose', str(self.recipe_path),
                   '--output', str(self.output), *args)

    def assert_refused(self, result, message=None):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn('internal error', result.stderr)
        if message:
            self.assertIn(message, result.stderr)

    def test_three_sources_produce_a_standalone_kit_with_explicit_names(self):
        frame = self.source('frame')
        brand = self.source('brand')
        palette = self.source('palette')
        (palette / 'themes').mkdir()
        created = run('theme', 'create', 'selected', '--from', 'dracula',
                      '--output', str(palette / 'themes' / 'selected.conf'))
        self.assertEqual(created.returncode, 0, created.stderr)
        manifest_path = palette / 'manifest.json'
        palette_manifest = json.loads(manifest_path.read_text())
        palette_manifest['themes']['palette'] = 'themes/selected.conf'
        manifest_path.write_text(json.dumps(palette_manifest), encoding='utf-8')
        target = self.recipe['manifest']
        target['layouts']['cover']['default'] = 'layouts/cover.html'
        target['themes'] = {'selected': 'themes/colors.conf'}
        target['presets']['brief']['theme'] = 'selected'
        target['presets']['brief']['slide_chrome'] = {
            'cover': {'header': {'model': 'masthead'}}}
        target['assets'] = {'mark': {'path': 'assets/mark.png', 'kind': 'image'}}
        target['chrome'] = 'chrome.json'
        target['structure_css'] = 'structure.css'
        self.recipe['files'] = {
            'layouts/cover.html': {'source': 'frame', 'path': 'cover.html'},
            'themes/colors.conf': {'source': 'palette', 'path': 'themes/selected.conf'},
            'chrome.json': {'source': 'brand', 'path': 'chrome.json'},
            'assets/mark.png': {'source': 'brand', 'path': 'assets/mark.png'},
            'structure.css': {'parts': [
                {'source': 'frame', 'path': 'structure.css'},
                {'source': 'brand', 'path': 'structure.css'},
                {'text': '.lwp-presentation--combined .local { display: flex; }'},
            ]},
        }
        expected_asset = (brand / 'assets' / 'mark.png').read_bytes()
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.destination / 'manifest.json').read_text()), target)
        self.assertEqual((self.destination / 'assets' / 'mark.png').read_bytes(), expected_asset)
        css = (self.destination / 'structure.css').read_text()
        self.assertIn('.lwp-presentation--combined .lwp-presentation--frame-child', css)
        self.assertIn('.lwp-presentation--combined .lwp-presentation--brand-child', css)
        self.assertEqual({p.relative_to(self.destination).as_posix()
                          for p in self.destination.rglob('*') if p.is_file()},
                         set(self.recipe['files']) | {'manifest.json'})
        # Removing the recipe and every input cannot affect the installed result.
        shutil.rmtree(frame.parent.parent)
        self.recipe_path.unlink()
        shown = run('preset', 'show', 'combined@1.2.3/brief', '--format', 'json',
                    env={'LWP_IDENTITY_KITS_DIR': str(self.output)})
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(json.loads(shown.stdout)['theme']['id'], 'selected')

    def test_local_files_and_inline_text_can_add_new_resources(self):
        (self.root / 'local.bin').write_bytes(b'\x00\xfflocal')
        self.recipe['manifest']['assets'] = {
            'local': {'path': 'assets/local.bin', 'kind': 'icon'}}
        self.recipe['manifest']['layouts']['standard']['default'] = 'standard.html'
        self.recipe['files'] = {
            'assets/local.bin': {'file': 'local.bin'},
            'standard.html': {'text': '<div>{{slide_header}}{{content}}{{slide_footer}}</div>'},
        }
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / 'assets' / 'local.bin').read_bytes(), b'\x00\xfflocal')

    def test_direct_source_css_is_rebound_without_pruning_or_prefix_rewrites(self):
        source = self.source('frame')
        with (source / 'structure.css').open('a', encoding='utf-8') as css:
            css.write('.lwp-presentation--frame .escaped\\.lwp-presentation--frame '
                      '{ display: flex; }\n')
        self.recipe['manifest']['structure_css'] = 'renamed.css'
        self.recipe['files']['renamed.css'] = {'source': 'frame', 'path': 'structure.css'}
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / 'renamed.css').read_text(),
                         '.lwp-presentation--combined .lwp-presentation--frame-child '
                         '{ display: grid; }\n'
                         '.lwp-presentation--combined .escaped\\.lwp-presentation--frame '
                         '{ display: flex; }\n')

    def test_source_aliases_are_local_names_not_kit_identifiers(self):
        self.source('frame')
        self.recipe['sources']['Layout source'] = self.recipe['sources'].pop('frame')
        self.recipe['manifest']['layouts']['cover']['default'] = 'cover.html'
        self.recipe['files']['cover.html'] = {'source': 'Layout source', 'path': 'cover.html'}
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_css_rebinding_changes_only_class_tokens_in_selectors(self):
        source = self.source('frame')
        css = (
            '/* .lwp-presentation--frame { [ " */\n'
            '@media (min-width: 1px) {\n'
            '  .lwp-presentation--frame [data-token=".lwp-presentation--frame"],\n'
            "  .lwp-presentation--frame [data-token='.lwp-presentation--frame'] {\n"
            '    content: ".lwp-presentation--frame";\n'
            "    other: '.lwp-presentation--frame';\n"
            '  }\n'
            '  /* } .lwp-presentation--frame */\n'
            '  @media (max-width: 999px) {\n'
            '    .lwp-presentation--frame :is(.lwp-presentation--frame, .other) { display: grid; }\n'
            '  }\n'
            '}\n'
            '/* trailing .lwp-presentation--frame */\n'
        )
        (source / 'structure.css').write_text(css, encoding='utf-8')
        self.recipe['manifest']['structure_css'] = 'structure.css'
        self.recipe['files']['structure.css'] = {'source': 'frame', 'path': 'structure.css'}
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = css.replace('  .lwp-presentation--frame [', '  .lwp-presentation--combined [')
        expected = expected.replace(
            '.lwp-presentation--frame :is(.lwp-presentation--frame,',
            '.lwp-presentation--combined :is(.lwp-presentation--combined,')
        self.assertEqual((self.destination / 'structure.css').read_text(), expected)

    def test_css_rebinding_decodes_class_identifier_escapes_not_literal_values(self):
        source = self.source('frame')
        css = (
            r'.lwp-presentation--\66 rame .label { display: grid; }' '\n'
            r'.lwp-presentation--fra\6d e .label { display: flex; }' '\n'
            r'.lwp-presentation--\000066rame .label { display: block; }' '\n'
            r'.lwp-presentation--fra\me .escaped\.lwp-presentation--frame { display: grid; }' '\n'
            r'.lwp-presentation--frame .lwp-presentation--frame\2d child { display: grid; }' '\n'
        )
        (source / 'structure.css').write_text(css, encoding='utf-8')
        self.recipe['manifest']['structure_css'] = 'structure.css'
        self.recipe['files']['structure.css'] = {'parts': [
            {'source': 'frame', 'path': 'structure.css'}]}
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = (
            '.lwp-presentation--combined .label { display: grid; }\n'
            '.lwp-presentation--combined .label { display: flex; }\n'
            '.lwp-presentation--combined .label { display: block; }\n'
            r'.lwp-presentation--combined .escaped\.lwp-presentation--frame { display: grid; }' '\n'
            r'.lwp-presentation--combined .lwp-presentation--frame\2d child { display: grid; }' '\n'
        )
        self.assertEqual((self.destination / 'structure.css').read_text(), expected)

    def test_direct_structural_css_selection_uses_manifest_role_not_extension(self):
        source = self.source('frame')
        css = (source / 'structure.css').read_text()
        (source / 'structure.txt').write_text(css, encoding='utf-8')
        manifest_path = source / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['structure_css'] = 'structure.txt'
        manifest['assets']['css-file'] = {'path': 'assets/unrelated.css', 'kind': 'icon'}
        (source / 'assets/unrelated.css').write_text('literal .lwp-presentation--frame', encoding='utf-8')
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        self.recipe['manifest']['structure_css'] = 'selected.txt'
        self.recipe['manifest']['assets'] = {
            'css-file': {'path': 'assets/unrelated.css', 'kind': 'icon'}}
        self.recipe['files'] = {
            'selected.txt': {'source': 'frame', 'path': 'structure.txt'},
            'assets/unrelated.css': {'source': 'frame', 'path': 'assets/unrelated.css'},
        }
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / 'selected.txt').read_text(),
                         css.replace('.lwp-presentation--frame ', '.lwp-presentation--combined '))
        self.assertEqual((self.destination / 'assets/unrelated.css').read_text(),
                         'literal .lwp-presentation--frame')

    def test_css_parts_still_require_css_extension_for_structural_resources(self):
        source = self.source('frame')
        (source / 'structure.txt').write_text((source / 'structure.css').read_text(), encoding='utf-8')
        path = source / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['structure_css'] = 'structure.txt'
        path.write_text(json.dumps(manifest), encoding='utf-8')
        self.recipe['files']['structure.css'] = {'parts': [
            {'source': 'frame', 'path': 'structure.txt'}]}
        self.assert_refused(self.compose(), 'only textual .css files')

    def test_catalogue_read_during_publication_sees_only_old_kits_and_failure_cleans_up(self):
        for existing_version in (False, True):
            for fail in (False, True):
                with self.subTest(existing_version=existing_version, fail=fail):
                    output = self.root / f'catalogue-{existing_version}-{fail}'
                    output.mkdir()
                    if existing_version:
                        old = output / 'combined/0.9.0'
                        old.mkdir(parents=True)
                        (old / 'manifest.json').write_text(
                            json.dumps(self.manifest('combined', '0.9.0')), encoding='utf-8')
                    env = {'LWP_IDENTITY_KITS_DIR': str(output),
                           'LWP_COMMONS_DIR': str(self.root / 'no-commons'),
                           'LWP_THEMES_DIR': str(self.root / 'no-themes')}
                    before = run('preset', 'list', '--format', 'json', env=env)
                    self.assertEqual(before.returncode, 0, before.stderr)
                    old_tree = sorted(p.relative_to(output) for p in output.rglob('*'))
                    self.recipe_path.write_text(json.dumps(self.recipe), encoding='utf-8')
                    staged = []
                    replace_tree = self.lwp._replace_tree

                    def observe(source, destination):
                        staged.append(source.parent.parent)
                        during = run('preset', 'list', '--format', 'json', env=env)
                        self.assertEqual(during.returncode, 0, during.stderr)
                        self.assertEqual(json.loads(during.stdout), json.loads(before.stdout))
                        self.assertNotIn(output, source.parents)
                        self.assertEqual(source.stat().st_dev, destination.parent.stat().st_dev)
                        if fail:
                            raise OSError('injected publication failure')
                        return replace_tree(source, destination)

                    with mock.patch.object(self.lwp, '_replace_tree', side_effect=observe):
                        with mock.patch.dict(self.lwp._LOG_STATE, {'quiet': True}):
                            if fail:
                                with self.assertRaises(SystemExit):
                                    self.lwp.cmd_kit_compose(self.recipe_path, {'--output': str(output)})
                            else:
                                self.lwp.cmd_kit_compose(self.recipe_path, {'--output': str(output)})
                    self.assertEqual(len(staged), 1)
                    self.assertFalse(staged[0].exists())
                    self.assertEqual((output / 'combined/1.2.3').exists(), not fail)
                    if fail:
                        self.assertEqual(sorted(p.relative_to(output) for p in output.rglob('*')), old_tree)
                    after = run('preset', 'list', '--format', 'json', env=env)
                    self.assertEqual(after.returncode, 0, after.stderr)

    def test_mount_boundary_is_refused_before_creating_a_stage_or_output_files(self):
        self.output.mkdir()
        self.recipe_path.write_text(json.dumps(self.recipe), encoding='utf-8')
        stat = Path.stat

        def mounted_stat(path, *args, **kwargs):
            result = stat(path, *args, **kwargs)
            if path == self.output or self.output in path.parents:
                fields = list(result)
                fields[2] += 1
                return os.stat_result(fields)
            return result

        with mock.patch.object(Path, 'stat', new=mounted_stat):
            with mock.patch.object(tempfile, 'TemporaryDirectory') as stage:
                with mock.patch.object(self.lwp, 'log') as log:
                    with self.assertRaises(SystemExit):
                        self.lwp.cmd_kit_compose(self.recipe_path, {'--output': str(self.output)})
                    self.assertIn('same filesystem', log.call_args.args[1])
                stage.assert_not_called()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_failed_publication_removes_new_output_parents_and_stage(self):
        self.recipe_path.write_text(json.dumps(self.recipe), encoding='utf-8')
        with mock.patch.object(self.lwp, '_replace_tree', side_effect=OSError('publish failed')):
            with self.assertRaises(SystemExit):
                self.lwp.cmd_kit_compose(self.recipe_path, {'--output': str(self.output)})
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.lwp-kit-compose-*')))

    def test_local_css_parts_are_concatenated_in_order(self):
        css = '.lwp-presentation--combined .a { display: grid; }'
        (self.root / 'local.css').write_text(css, encoding='utf-8')
        self.recipe['manifest']['structure_css'] = 'structure.css'
        self.recipe['files']['structure.css'] = {'parts': [
            {'text': '/* first */'}, {'file': 'local.css'}, {'text': '/* last */'}]}
        result = self.compose()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.destination / 'structure.css').read_text(),
                         '/* first */\n' + css + '\n/* last */')

    def test_full_target_validation_happens_before_any_output_is_created(self):
        original = copy.deepcopy(self.recipe)
        for field, value in (
                ('label', ''), ('schema', 'lightwebpres.presentation-package/1'),
                ('layouts', {}), ('themes', {}), ('presets', {}),
                ('structure_css', 'missing.css'), ('chrome', 'missing.json'),
                ('lineage', []), ('origin', 'anything')):
            with self.subTest(field=field):
                self.recipe = copy.deepcopy(original)
                self.recipe['manifest'][field] = value
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())
                self.assertFalse(list(self.root.glob('.lwp-kit-compose-*')))

    def test_source_must_be_a_complete_valid_kit_even_if_unselected(self):
        source = self.source('broken')
        (source / 'cover.html').write_text('<script>bad</script>', encoding='utf-8')
        self.assert_refused(self.compose(), 'layout fragment')
        self.assertFalse(self.output.exists())

    def test_source_junk_cannot_be_selected(self):
        self.source('frame')
        self.recipe['files']['junk.txt'] = {'source': 'frame', 'path': 'junk.txt'}
        self.assert_refused(self.compose(), 'not declared')
        self.assertFalse(self.output.exists())

    def test_missing_explicit_asset_is_not_inferred_from_chrome(self):
        self.source('brand')
        self.recipe['manifest']['chrome'] = 'chrome.json'
        self.recipe['files']['chrome.json'] = {'source': 'brand', 'path': 'chrome.json'}
        self.assert_refused(self.compose(), 'asset')
        self.assertFalse(self.output.exists())

    def test_css_parts_are_strict_and_only_textual_css(self):
        (self.root / 'other.txt').write_text('/* CSS-looking text */', encoding='utf-8')
        (self.root / 'binary.css').write_bytes(b'\xff')
        for destination, descriptor in (
                ('other.txt', {'parts': [{'text': 'text'}]}),
                ('other.css', {'parts': []}),
                ('other.css', {'parts': {}}),
                ('other.css', {'parts': [{'file': 'other.txt'}]}),
                ('other.css', {'parts': [{'file': 'binary.css'}]}),
                ('other.css', {'parts': [{'parts': [{'text': 'nested'}]}]})):
            with self.subTest(descriptor=descriptor):
                self.recipe['files'] = {destination: descriptor}
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())

    def test_descriptors_reject_unknown_mixed_and_invalid_values(self):
        for descriptor in (None, [], {}, {'text': 7}, {'source': [], 'path': 'x'},
                           {'source': 'missing', 'path': 'x'}, {'text': 'x', 'file': 'x'},
                           {'file': 'x', 'extra': True}, {'text': '\ud800'}):
            with self.subTest(descriptor=descriptor):
                self.recipe['files'] = {'x': descriptor}
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())

    def test_paths_reject_traversal_absolute_and_ambiguous_spellings(self):
        self.source('frame')
        for path in ('../outside', '/absolute', 'a/../x', './x', 'a//x',
                     'a\\x', 'C:/x', 'x/', '', 'a\x00x'):
            for location in ('destination', 'local', 'source', 'root'):
                with self.subTest(path=path, location=location):
                    recipe = copy.deepcopy(self.recipe)
                    if location == 'destination':
                        self.recipe['files'] = {path: {'text': 'x'}}
                    elif location == 'root':
                        self.recipe['sources'] = {'frame': path}
                    else:
                        descriptor = ({'file': path} if location == 'local' else
                                      {'source': 'frame', 'path': path})
                        self.recipe['files'] = {'x': descriptor}
                    self.assert_refused(self.compose())
                    self.assertFalse(self.output.exists())
                    self.recipe = recipe

    def test_symlink_escapes_in_local_files_source_roots_and_source_files(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside)
            (external / 'secret').write_text('private', encoding='utf-8')
            (self.root / 'link').symlink_to(external, target_is_directory=True)
            self.recipe['files'] = {'x': {'file': 'link/secret'}}
            self.assert_refused(self.compose(), 'symlink')
            self.recipe['files'] = {}
            self.recipe['sources'] = {'outside': 'link'}
            self.assert_refused(self.compose(), 'escapes')
            self.recipe['sources'] = {}
            source = self.source('frame')
            (source / 'junk-link').symlink_to(external / 'secret')
            self.assert_refused(self.compose(), 'symlink')
            self.assertFalse(self.output.exists())

    def test_reserved_manifest_and_file_directory_conflicts(self):
        for files in ({'manifest.json': {'text': '{}'}},
                      {'manifest.json/x': {'text': 'x'}},
                      {'x': {'text': 'x'}, 'x/y': {'text': 'y'}}):
            with self.subTest(files=files):
                self.recipe['files'] = files
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())

    def test_duplicate_json_keys_are_rejected_at_every_depth(self):
        valid = json.dumps(self.recipe)
        for text in ('{"schema":1,"schema":2}',
                     valid.replace('"files": {}', '"files":{"x":{"text":"a"},"x":{"text":"b"}}'),
                     valid.replace('"files": {}', '"files":{"x":{"text":"a","text":"b"}}'),
                     valid.replace('"id": "combined"', '"id":"combined","id":"other"')):
            with self.subTest(text=text):
                self.recipe_path.write_text(text, encoding='utf-8')
                self.assert_refused(run('kit', 'compose', str(self.recipe_path),
                                        '--output', str(self.output)), 'duplicate JSON key')
                self.assertFalse(self.output.exists())

    def test_recipe_shape_schema_and_non_json_constants_are_strict(self):
        original = copy.deepcopy(self.recipe)
        for recipe in ([], {}, {**original, 'extra': True},
                       {**original, 'schema': 'other'}, {**original, 'sources': []},
                       {**original, 'manifest': []}, {**original, 'files': []}):
            with self.subTest(recipe=recipe):
                self.recipe = recipe
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())
        self.recipe_path.write_text('{"schema":NaN}', encoding='utf-8')
        self.assert_refused(run('kit', 'compose', str(self.recipe_path),
                                '--output', str(self.output)), 'invalid JSON constant')

    def test_id_and_exact_version_are_checked_before_staging(self):
        for field, value in (('id', 'builtin'), ('id', 'commons'), ('id', '../escape'),
                             ('version', 'latest'), ('version', '1.2'), ('version', '../x')):
            with self.subTest(field=field, value=value):
                self.recipe['manifest'] = self.manifest('combined', '1.2.3')
                self.recipe['manifest'][field] = value
                self.assert_refused(self.compose())
                self.assertFalse(self.output.exists())

    def test_output_never_clobbers_even_empty_directory_or_dangling_symlink(self):
        self.destination.parent.mkdir(parents=True)
        for kind in ('empty', 'file', 'symlink'):
            with self.subTest(kind=kind):
                if kind == 'empty':
                    self.destination.mkdir()
                elif kind == 'file':
                    self.destination.write_text('keep', encoding='utf-8')
                else:
                    self.destination.symlink_to(self.root / 'missing')
                self.assert_refused(self.compose(), 'output')
                self.assert_refused(self.compose('--dry-run'), 'output')
                if kind == 'empty':
                    self.assertEqual(list(self.destination.iterdir()), [])
                    self.destination.rmdir()
                else:
                    if kind == 'file':
                        self.assertEqual(self.destination.read_text(), 'keep')
                    else:
                        self.assertTrue(self.destination.is_symlink())
                    self.destination.unlink()

    def test_output_cannot_be_inside_a_source_or_traverse_a_symlink(self):
        source = self.source('frame')
        self.output = source / 'nested'
        self.assert_refused(self.compose(), 'inside a source kit')
        self.assertFalse(self.output.exists())
        self.output = self.root / 'output-link'
        self.output.symlink_to(source, target_is_directory=True)
        self.assert_refused(self.compose(), 'symlink')
        self.assertFalse((source / 'combined').exists())

    def test_dry_run_validates_the_final_kit_without_creating_output(self):
        self.source('frame')
        self.recipe['manifest']['structure_css'] = 'structure.css'
        self.recipe['files']['structure.css'] = {'source': 'frame', 'path': 'structure.css'}
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.compose('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('would replace tree', result.stderr)
        self.assertFalse(self.output.exists())
        for path, contents in before.items():
            self.assertEqual(Path(path).read_bytes(), contents)
        self.assertFalse(list(self.root.glob('.lwp-kit-compose-*')))
        self.recipe['files']['structure.css'] = {'text': 'body { display: grid; }'}
        self.assert_refused(self.compose('--dry-run'), 'structure_css')
        self.assertFalse(self.output.exists())

    def test_help_completion_and_required_arguments(self):
        for args in (('kit', '--help'), ('kit', 'compose', '--help'), ('--help',)):
            result = run(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('kit compose', result.stdout)
        for args in (('kit',), ('kit', 'unknown'), ('kit', 'compose'),
                     ('kit', 'compose', 'recipe.json'),
                     ('kit', 'compose', 'recipe.json', '--force'),
                     ('kit', 'compose', 'a', 'b', '--output', str(self.output))):
            self.assert_refused(run(*args))
        for shell in ('bash', 'zsh'):
            result = run('completion', '--shell', shell)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"kit compose") opts=', result.stdout)
        script = run('completion', '--shell', 'bash').stdout
        for words, expected in ((['lightwebpres', 'ki'], {'kit'}),
                                (['lightwebpres', 'kit', ''], {'compose'}),
                                (['lightwebpres', 'kit', 'compose', '--'], {'--output', '--dry-run'})):
            program = (script + '\nCOMP_WORDS=(' + ' '.join(map(shlex.quote, words))
                       + f')\nCOMP_CWORD={len(words) - 1}\n_lightwebpres_completion\n'
                       + 'printf "%s\\n" "${COMPREPLY[@]}"\n')
            completed = subprocess.run(['bash', '-c', program], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            offered = set(completed.stdout.splitlines())
            self.assertTrue(expected <= offered, offered)
            self.assertNotIn('--force', offered)


if __name__ == '__main__':
    unittest.main()
