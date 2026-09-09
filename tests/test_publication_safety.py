"""CLI regressions for publication ownership and output-local cache validity."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


EXECUTABLE = Path(__file__).resolve().parents[1] / 'lightwebpres'


class PublicationSafety(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='publication-safety-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('LWP_')}
        self.env.update({
            'LWP_IDENTITY_KITS_DIR': str(self.root / 'unused-kits'),
            'LWP_COMMONS_DIR': str(self.root / 'unused-commons'),
            'LWP_THEMES_DIR': str(self.root / 'unused-themes'),
            'PYTHONDONTWRITEBYTECODE': '1',
        })
        (self.root / 'sources').mkdir()
        (self.root / 'templates').mkdir()
        self.data = {'series_meta': {'title': 'Publication safety'}, 'articles': []}
        for name in ('a', 'b'):
            (self.root / 'sources' / (name + '.md')).write_text(
                '<!-- lwp:meta -->\npage_title: Article ' + name + '\n---\n\n'
                '<!-- lwp:slide:cover -->\nslug: cover-' + name + '\n'
                '# Article ' + name + '\nsummary: Example.\n\n---\n\n'
                '<!-- lwp:slide:series-nav -->\nslug: navigation-' + name + '\n',
                encoding='utf-8')
            self.data['articles'].append({'page_source': name + '.md'})
        self.save_series()

    def save_series(self):
        (self.root / 'series.json').write_text(json.dumps(self.data), encoding='utf-8')

    def cli(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, str(EXECUTABLE), *map(str, args)],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result

    def snapshot(self, root=None):
        snapshot = {}
        for path in (root or self.root).rglob('*'):
            stat = path.lstat()
            content = (os.readlink(path) if path.is_symlink() else
                       path.read_bytes() if path.is_file() else None)
            snapshot[str(path.relative_to(root or self.root))] = (
                stat.st_mode, stat.st_mtime_ns, content)
        return snapshot

    def assert_full_build(self, result, output):
        self.assertNotIn('Incremental build', result.stdout)
        self.assertIn('Build complete: 2 articles', result.stdout)
        self.assertTrue((output / 'a.html').is_file())
        self.assertTrue((output / 'b.html').is_file())
        self.cli('verify', self.root, '--output', output)

    def test_backslashes_in_filenames_are_rejected_before_build_writes(self):
        for field in ('page_dest', 'page_source'):
            with self.subTest(field=field):
                original = dict(self.data['articles'][0])
                self.data['articles'][0][field] = 'manual\\a.' + (
                    'html' if field == 'page_dest' else 'md')
                self.save_series()
                before = self.snapshot()
                result = self.cli('build', self.root, code=1)
                self.assertIn('unsafe', result.stderr)
                self.assertEqual(self.snapshot(), before)
                self.data['articles'][0] = original

    def test_backslashes_in_article_front_matter_and_includes_are_rejected(self):
        source = self.root / 'sources' / 'a.md'
        original = source.read_text(encoding='utf-8')
        public = self.root / 'public'
        public.mkdir()
        (public / 'manual.html').write_bytes(b'Never generated')
        for text in (
            original.replace('page_title:', 'page_dest: manual\\a.html\npage_title:', 1),
            original + '\n---\n\n<!-- lwp:slide:full-article -->\n'
            'slug: body\narticle: manual\\body.md\n',
        ):
            with self.subTest(text=text):
                source.write_text(text, encoding='utf-8')
                before = self.snapshot()
                result = self.cli('build', self.root, code=1)
                self.assertIn('safe', result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_clean_refuses_every_unsafe_entry_before_removing_any_orphan(self):
        public = self.root / 'public'
        (public / 'manual').mkdir(parents=True)
        (public / 'manual' / 'a.html').write_bytes(b'Never generated')
        (public / 'orphan.html').write_bytes(b'Previously generated')
        for key in ('files', 'previous'):
            for value in ('manual\\a.html', '../a.html', '/a.html', 'C:/a.html',
                          'a\x00.html', '.', 'manual/./a.html', 'manual//a.html',
                          'manual/', None, {'path': 'a.html'}):
                with self.subTest(key=key, value=value):
                    manifest = {'files': [], 'previous': ['orphan.html']}
                    manifest[key].append(value)
                    (public / '.lwp-manifest.json').write_text(
                        json.dumps(manifest), encoding='utf-8')
                    before = self.snapshot()
                    result = self.cli('clean', self.root, '--force', code=1)
                    self.assertIn('unsafe path', result.stderr)
                    self.assertEqual(self.snapshot(), before)

    def test_old_backslash_manifest_survives_rebuild_without_alias_deletion(self):
        public = self.root / 'public'
        (public / 'manual').mkdir(parents=True)
        sidecar = public / 'manual' / 'a.html'
        sidecar.write_bytes(b'Handwritten deployment page')
        literal = public / 'manual\\a.html'
        if os.name != 'nt':
            literal.write_bytes(b'Old Linux output')
        (public / '.lwp-manifest.json').write_text(json.dumps({
            'files': ['manual\\a.html'], 'previous': [],
        }), encoding='utf-8')
        self.cli('build', self.root)
        before = self.snapshot()
        for options in ((), ('--dry-run',)):
            self.cli(*options, 'clean', self.root, '--force', code=1)
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(sidecar.read_bytes(), b'Handwritten deployment page')
        if os.name != 'nt':
            self.assertEqual(literal.read_bytes(), b'Old Linux output')

    def test_clean_accepts_nested_posix_assets_and_preserves_manual_files(self):
        public = self.root / 'public'
        assets = ('img/nested/old.svg',
                  'assets/presentations/example/1.0.0/icons/old.svg')
        for name in (*assets, 'img/nested/manual.svg'):
            path = public / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode('ascii'))
        (public / '.lwp-manifest.json').write_text(json.dumps({
            'files': [], 'previous': list(assets),
        }), encoding='utf-8')
        before = self.snapshot()
        self.cli('--dry-run', 'clean', self.root, '--force')
        self.assertEqual(self.snapshot(), before)
        self.cli('clean', self.root, '--force')
        for name in assets:
            self.assertFalse((public / name).exists())
        self.assertEqual((public / 'img/nested/manual.svg').read_bytes(),
                         b'img/nested/manual.svg')

    def test_second_template_update_preserves_both_customizations(self):
        nav = self.root / 'templates' / 'nav.js'
        backup = nav.with_name('nav.js.bak')
        first = b'// Custom navigation A\r\n'
        second = b'// Custom navigation B\n'
        nav.write_bytes(first)
        self.cli('template', 'update', self.root)
        self.assertEqual(backup.read_bytes(), first)
        self.assertFalse(nav.exists())
        nav.write_bytes(second)
        before = self.snapshot()
        result = self.cli('template', 'update', self.root, code=1)
        self.assertIn('protected backup', result.stderr)
        self.assertIn('Move the backup', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_backup_collisions_refuse_before_missing_scaffolds_are_created(self):
        templates = self.root / 'templates'
        nav = templates / 'nav.js'
        backup = templates / 'nav.js.bak'
        nav.write_bytes(b'// active\n')
        target = self.root / 'preserved-backup'
        target.write_bytes(nav.read_bytes())
        for kind in ('different', 'directory', 'symlink', 'dangling-symlink'):
            with self.subTest(kind=kind):
                if kind == 'different':
                    backup.write_bytes(b'// earlier customization\n')
                elif kind == 'directory':
                    backup.mkdir()
                else:
                    backup.symlink_to(target if kind == 'symlink' else
                                      self.root / 'absent-backup')
                before = self.snapshot()
                for options in ((), ('--dry-run',)):
                    result = self.cli(*options, 'template', 'update', self.root, code=1)
                    self.assertIn('protected backup', result.stderr)
                    self.assertEqual(self.snapshot(), before)
                self.assertFalse((templates / 'settings.conf').exists())
                self.assertFalse((templates / 'custom.css').exists())
                if kind == 'directory':
                    backup.rmdir()
                else:
                    backup.unlink()

    def test_identical_backup_is_reused_without_rewriting_it(self):
        nav = self.root / 'templates' / 'nav.js'
        backup = nav.with_name('nav.js.bak')
        nav.write_bytes(b'// active\r\n')
        backup.write_bytes(nav.read_bytes())
        before = self.snapshot()
        self.cli('--dry-run', 'template', 'update', self.root)
        self.assertEqual(self.snapshot(), before)
        self.cli('template', 'update', self.root)
        self.assertFalse(nav.exists())
        self.assertEqual(self.snapshot()['templates/nav.js.bak'],
                         before['templates/nav.js.bak'])

    def test_new_backup_dry_run_preserves_all_files(self):
        (self.root / 'templates' / 'nav.js').write_bytes(b'// active\n')
        before = self.snapshot()
        self.cli('--dry-run', 'template', 'update', self.root)
        self.assertEqual(self.snapshot(), before)

    def test_builtin_nav_removal_does_not_touch_an_unneeded_backup(self):
        self.cli('template', 'write', 'nav.js', self.root)
        backup = self.root / 'templates' / 'nav.js.bak'
        backup.write_bytes(b'// Earlier customization\n')
        before = self.snapshot()['templates/nav.js.bak']
        self.cli('template', 'update', self.root)
        self.assertFalse((self.root / 'templates' / 'nav.js').exists())
        self.assertEqual(self.snapshot()['templates/nav.js.bak'], before)

    def test_new_output_invalidates_shared_cache_without_touching_first_output(self):
        self.cli('build', self.root)
        public = self.root / 'public'
        before = self.snapshot(public)
        preview = self.root / 'preview'
        result = self.cli('build', self.root, '--only', 'a.md', '--output', preview)
        self.assert_full_build(result, preview)
        self.assertEqual(self.snapshot(public), before)

    def test_metadata_change_in_second_output_cannot_leave_first_output_stale(self):
        self.cli('build', self.root)
        public = self.root / 'public'
        old_b = (public / 'b.html').read_bytes()
        self.data['series_meta']['title'] = 'New series title'
        self.data['articles'][0]['nav_title'] = 'Renamed navigation A'
        self.save_series()
        preview = self.root / 'preview'
        self.cli('build', self.root, '--output', preview)
        before = self.snapshot(preview)
        result = self.cli('build', self.root, '--only', 'a.md')
        self.assert_full_build(result, public)
        self.assertNotEqual((public / 'b.html').read_bytes(), old_b)
        self.assertIn(b'Renamed navigation A', (public / 'b.html').read_bytes())
        self.assertEqual(self.snapshot(preview), before)

    def test_missing_retained_page_falls_back_to_full_build(self):
        self.cli('build', self.root)
        public = self.root / 'public'
        sidecar = public / 'manual.html'
        sidecar.write_bytes(b'Never generated')
        (public / 'b.html').unlink()
        before = self.snapshot()
        self.cli('--dry-run', 'build', self.root, '--only', 'a.md')
        self.assertEqual(self.snapshot(), before)
        result = self.cli('build', self.root, '--only', 'a.md')
        self.assert_full_build(result, public)
        self.assertIn('retained pages/assets', result.stderr)
        self.assertEqual(sidecar.read_bytes(), b'Never generated')

    def test_missing_published_asset_falls_back_and_restores_nested_image(self):
        image = self.root / 'sources' / 'img' / 'nested' / 'photo.svg'
        image.parent.mkdir(parents=True)
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
        source = self.root / 'sources' / 'b.md'
        source.write_text(source.read_text(encoding='utf-8')
                          + '\n---\n\n<!-- lwp:slide -->\nslug: picture\n'
                          '## Image\n![Photo](img/nested/photo.svg)\n', encoding='utf-8')
        self.cli('build', self.root)
        public = self.root / 'public'
        published = public / 'img' / 'nested' / 'photo.svg'
        self.assertEqual(published.read_bytes(), image.read_bytes())
        published.unlink()
        result = self.cli('build', self.root, '--only', 'a.md')
        self.assert_full_build(result, public)
        self.assertEqual(published.read_bytes(), image.read_bytes())

    def test_missing_manifest_is_not_evidence_of_complete_output(self):
        self.cli('build', self.root)
        public = self.root / 'public'
        (public / '.lwp-manifest.json').unlink()
        result = self.cli('build', self.root, '--only', 'a.md')
        self.assert_full_build(result, public)

    def test_same_absolute_output_retains_fast_path_and_recreates_selected_page(self):
        self.cli('build', self.root, '--output', 'public')
        public = self.root / 'public'
        before = self.snapshot(public)['b.html']
        (public / 'a.html').unlink()
        result = self.cli('build', self.root, '--only', 'a.md', '--output', public)
        self.assertIn('Incremental build', result.stdout)
        self.assertEqual(self.snapshot(public)['b.html'], before)
        self.cli('verify', self.root)


if __name__ == '__main__':
    unittest.main()
