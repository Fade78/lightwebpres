"""Snapshot consistency at the real GitLab glue boundary, with no network."""
import base64
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
from urllib.parse import unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class GitSnapshotConsistency(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        http = types.ModuleType('pyodide.http')
        http.pyfetch = None
        spec = importlib.util.spec_from_file_location('git_snapshot_test', ROOT / 'web/git_sync.py')
        self.glue = importlib.util.module_from_spec(spec)
        with mock.patch.dict('sys.modules', {'pyodide.http': http}):
            spec.loader.exec_module(self.glue)
        self.glue.GIT_WORK_DIR = self.root / 'pull'
        self.head = 'pull-revision'
        self.files = {'series.json': json.dumps({'articles': []}).encode(),
                      'sources/a.md': b'Pulled source', 'sources/old.md': b'Keep me'}
        self.last = {name: 'older-file-revision' for name in self.files}
        self.revisions = {self.head: (dict(self.files), dict(self.last))}
        self.requests = []
        self.commits = []
        self.race = None
        self.fail_chunk = None
        self.glue._request = self.request

    def remote_edit(self, name, content):
        self.head = 'external-' + str(len(self.revisions))
        self.files[name] = content
        self.last[name] = self.head
        self.revisions[self.head] = (dict(self.files), dict(self.last))

    async def request(self, base, token, method, path, params=None, body=None, **kwargs):
        self.requests.append((method, path, params, body))
        if method == 'GET' and '/commits/' in path:
            return {'id': self.head}
        if method == 'GET' and path.endswith('/archive.zip'):
            files, _ = self.revisions[self.head if params['sha'] == 'main' else params['sha']]
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as zf:
                for name, content in files.items():
                    zf.writestr('project/' + name, content)
            return archive.getvalue()
        if method == 'GET' and path.endswith('/tree'):
            files, _ = self.revisions[self.head if params['ref'] == 'main' else params['ref']]
            return [{'path': name, 'type': 'blob'} for name in files]
        if method == 'GET' and '/files/' in path:
            files, revisions = self.revisions[params['ref']]
            name = unquote(path.split('/files/')[1])
            return {'last_commit_id': revisions[name],
                    'content_sha256': hashlib.sha256(files[name]).hexdigest()}
        if method == 'POST':
            if self.race:
                race, self.race = self.race, None
                race()
            if self.fail_chunk == len(self.commits) + 1:
                raise RuntimeError('injected request failure')
            # Model GitLab's create and update preconditions atomically per commit.
            for action in body['actions']:
                name = action['file_path']
                if action['action'] == 'create':
                    if name in self.files:
                        raise RuntimeError('file already exists')
                elif (name not in self.files or ('last_commit_id' in action
                      and action['last_commit_id'] != self.last[name])):
                    raise RuntimeError('file changed since last_commit_id')
            parent = self.head
            self.head = 'commit-' + str(len(self.commits) + 1)
            for action in body['actions']:
                name = action['file_path']
                self.files[name] = base64.b64decode(action['content'])
                self.last[name] = self.head
            self.revisions[self.head] = (dict(self.files), dict(self.last))
            self.commits.append(body)
            return {'id': self.head, 'parent_ids': [parent]}
        raise AssertionError((method, path))

    async def pull(self):
        directory, error = await self.glue.pull('https://example.invalid', 'fake', 'team/project', 'main')
        self.assertIsNone(error)
        self.local = Path(directory)
        return directory

    async def push(self, **changes):
        options = dict(base_url='https://example.invalid', token='fake', project_id='team/project',
                       branch='main', series_dir=str(self.local), commit_message='Update')
        options.update(changes)
        return await self.glue.push(**options)

    async def test_pull_downloads_the_resolved_revision_not_the_moving_branch(self):
        await self.pull()
        archive = next(request for request in self.requests if request[1].endswith('archive.zip'))
        self.assertEqual(archive[2], {'sha': 'pull-revision'})

    async def test_external_commit_after_pull_is_refused_before_any_write(self):
        await self.pull()
        self.remote_edit('sources/a.md', b'New contribution')
        ok, message = await self.push()
        self.assertFalse(ok)
        self.assertIn('Pull again', message)
        self.assertEqual(self.files['sources/a.md'], b'New contribution')
        self.assertEqual(self.commits, [])

    async def test_race_after_preflight_cannot_overwrite_a_new_contribution(self):
        await self.pull()
        (self.local / 'sources/a.md').write_text('Local edit')
        self.race = lambda: self.remote_edit('sources/a.md', b'Concurrent edit')
        ok, message = await self.push()
        self.assertFalse(ok)
        self.assertIn('Pull again', message)
        self.assertEqual(self.files['sources/a.md'], b'Concurrent edit')
        self.assertEqual(self.commits, [])

    async def test_create_race_is_not_retried_as_an_update(self):
        await self.pull()
        (self.local / 'new.md').write_text('Local new file')
        self.race = lambda: self.remote_edit('new.md', b'Remote new file')
        self.assertFalse((await self.push())[0])
        self.assertEqual(self.files['new.md'], b'Remote new file')
        self.assertEqual(self.commits, [])

    async def test_unchanged_branch_uses_file_revisions_and_advances_the_snapshot(self):
        await self.pull()
        (self.local / 'sources/a.md').write_text('Edited locally')
        (self.local / 'sources/old.md').unlink()
        self.assertTrue((await self.push())[0])
        actions = {action['file_path']: action for action in self.commits[0]['actions']}
        self.assertEqual(actions['sources/a.md']['last_commit_id'], 'older-file-revision')
        self.assertNotIn('sources/old.md', actions)
        self.assertEqual(self.files['sources/old.md'], b'Keep me')
        (self.local / 'sources/a.md').write_text('Second local edit')
        self.assertTrue((await self.push())[0])
        self.assertEqual(self.files['sources/a.md'], b'Second local edit')

    async def test_destination_and_directory_are_part_of_the_snapshot(self):
        await self.pull()
        for change in ({'project_id': 'other'}, {'branch': 'other'},
                       {'base_url': 'https://other.invalid'}, {'series_dir': str(self.root)}):
            before = len(self.requests)
            self.assertFalse((await self.push(**change))[0])
            self.assertEqual(len(self.requests), before)
        self.assertEqual(self.commits, [])

    async def test_partial_chunk_failure_reports_progress_and_requires_a_new_pull(self):
        await self.pull()
        for name in self.files:
            (self.local / name).write_text('Changed ' + name)
        self.glue.PUSH_CHUNK_SIZE = 1
        self.fail_chunk = 2
        ok, message = await self.push()
        self.assertFalse(ok)
        self.assertIn('1 commit', message)
        self.assertIn('Pull again', message)
        self.assertEqual(len(self.commits), 1)
        before = len(self.requests)
        self.assertFalse((await self.push())[0])
        self.assertEqual(len(self.requests), before)

    async def test_successful_chunks_recheck_the_last_confirmed_revision(self):
        await self.pull()
        for name in self.files:
            (self.local / name).write_text('Changed ' + name)
        self.glue.PUSH_CHUNK_SIZE = 1
        self.assertTrue((await self.push())[0])
        self.assertEqual(len(self.commits), len(self.files))

    async def test_unchanged_files_cannot_form_an_empty_chunk_before_changed_files(self):
        await self.pull()
        self.glue.PUSH_CHUNK_SIZE = 1
        (self.local / 'z-new.md').write_text('New content')
        self.assertTrue((await self.push())[0])
        self.assertEqual(len(self.commits), 1)
        self.assertEqual(self.commits[0]['actions'][0]['file_path'], 'z-new.md')
        self.assertTrue((await self.push())[0])
        self.assertEqual(len(self.commits), 1)

    async def test_later_chunk_cannot_adopt_a_racing_edit_to_a_completed_chunk(self):
        await self.pull()
        for name in self.files:
            (self.local / name).write_text('Local ' + name)
        self.glue.PUSH_CHUNK_SIZE = 1
        request = self.glue._request

        async def race_on_second_chunk(*args, **kwargs):
            if args[2] == 'POST' and len(self.commits) == 1:
                self.remote_edit('series.json', b'Concurrent contribution')
            return await request(*args, **kwargs)

        self.glue._request = race_on_second_chunk
        ok, message = await self.push()
        self.assertFalse(ok)
        self.assertIn('2 commit(s) confirmed', message)
        self.assertIn('unexpected parent', message)
        self.assertFalse((await self.push())[0])
        self.assertEqual(self.files['series.json'], b'Concurrent contribution')

    async def test_failed_replacement_pull_invalidates_the_previous_snapshot(self):
        await self.pull()
        request = self.glue._request
        self.glue._request = mock.AsyncMock(side_effect=RuntimeError('offline'))
        directory, error = await self.glue.pull('https://example.invalid', 'fake', 'team/project', 'main')
        self.assertIsNone(directory)
        self.assertIn('offline', error)
        self.glue._request = request
        self.assertFalse((await self.push())[0])
        self.assertEqual(self.commits, [])
