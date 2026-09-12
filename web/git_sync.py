"""GitLab sync glue for LightWebPres (browser), loaded into Pyodide after
lightwebpres itself (see index.html), which defines cmd_build() as a
global in this same Python namespace.

Talks to a GitLab instance's REST API v4 directly from the browser via
pyodide.http.pyfetch — a thin wrapper over the browser's own fetch(), so
the same-origin/CORS rules a browser enforces still apply. Nothing is
proxied through a third party: every request goes straight from this tab
to the GitLab instance the user configured. If that instance does not send
Access-Control-Allow-Origin on its API responses, every call here fails —
that is a server-side setting to fix, not something this page can work
around (see index.html's GitLab tab setup note).

Three explicit steps share a revision-bound snapshot:
  - pull(): resolves a branch and downloads that commit's repository archive
    into the work directory.
  - build(): runs the unmodified cmd_build() against the pulled directory.
  - push(): diffs the work directory (sources + the public/ that build()
    just produced, except build bookkeeping) against the remote repository
    tree and commits
    create/update actions for changed or new files in one commit (chunked
    if large). Never deletes: a file that disappeared locally but still
    exists remotely is left untouched — deletions go through GitLab
    directly, not through this page (specifications.md §23.12).
"""

import base64
import contextlib
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlencode

from pyodide.http import pyfetch

GIT_WORK_DIR = Path('/lwp_git_work')

PUSH_CHUNK_SIZE = 100


class GitSnapshot:
    """One pulled revision and destination; advances only after confirmed commits."""

    def __init__(self, base_url, project_id, branch, directory, revision):
        self.target = (base_url.rstrip('/'), str(project_id), branch)
        self.directory = Path(directory)
        self.revision = revision
        self.usable = True

    def matches(self, base_url, project_id, branch, directory):
        return (self.usable and self.directory == Path(directory)
                and self.target == (base_url.rstrip('/'), str(project_id), branch))


_git_snapshot = None

# index.html injects the page-owned values before loading this glue. These
# defaults keep the module testable in isolation; the deployment values live
# in the static page so both browser tabs use the same limits.
ZIP_MAX_ENTRIES = int(globals().get('ZIP_MAX_ENTRIES', 4096))
ZIP_MAX_COMPRESSED_BYTES = int(
    globals().get('ZIP_MAX_COMPRESSED_BYTES', 500 * 1024 * 1024))
ZIP_MAX_UNCOMPRESSED_BYTES = int(
    globals().get('ZIP_MAX_UNCOMPRESSED_BYTES', 500 * 1024 * 1024))


def _validate_zip_members(zf):
    """Rejects hostile, oversized or ambiguous members before extraction.

    This is the same defence-in-depth rule as web/app.py. Duplicate names
    are rejected too: otherwise the later entry silently replaces the
    earlier one, and slash/dot variants can disagree across runtimes.
    Size is capped as well: extraction goes into an in-memory filesystem,
    so a decompression bomb would exhaust the tab instead of erroring.
    """
    seen = set()
    total_bytes = 0
    if len(zf.infolist()) > ZIP_MAX_ENTRIES:
        raise RuntimeError(
            'archive declares %d entries — more than the %d-entry limit.'
            % (len(zf.infolist()), ZIP_MAX_ENTRIES))
    for info in zf.infolist():
        name = info.filename
        normalized = name.replace('\\', '/')
        parts = PurePosixPath(normalized).parts
        canonical = '/'.join(parts)
        if (not name or '\x00' in name
                or normalized.startswith('/')
                or (len(normalized) >= 2 and normalized[1] == ':')
                or '..' in parts or not canonical or canonical in seen):
            raise RuntimeError(
                'archive contains an invalid or duplicate member name: %r' % name)
        seen.add(canonical)
        total_bytes += info.file_size
        if total_bytes > ZIP_MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError(
                'archive decompresses to more than %d bytes — refusing to '
                'extract it.' % ZIP_MAX_UNCOMPRESSED_BYTES)


def _api_url(base_url, path, params=None):
    url = base_url.rstrip('/') + '/api/v4' + path
    if params:
        url += '?' + urlencode(params)
    return url


async def _request(base_url, token, method, path, params=None, body=None, want_json=True):
    url = _api_url(base_url, path, params)
    headers = {'PRIVATE-TOKEN': token}
    # redirect='error' instead of the fetch default ('follow'): PRIVATE-TOKEN
    # is a custom header, so it is NOT one of the small set (Authorization,
    # Cookie, Proxy-Authorization) the fetch spec strips on a cross-origin
    # redirect — a silently-followed redirect would resend the token to
    # whatever host the response points at. Failing loudly here is safer
    # than leaking it, even at the cost of breaking a legitimate redirect.
    kwargs = {'method': method, 'headers': headers, 'redirect': 'error'}
    if body is not None:
        headers['Content-Type'] = 'application/json'
        kwargs['body'] = json.dumps(body)
    try:
        resp = await pyfetch(url, **kwargs)
    except Exception as e:
        raise RuntimeError(
            f'{method} {path} -> request failed (possibly a blocked redirect): {e}'
        )
    if not resp.ok:
        text = await resp.string()
        raise RuntimeError(f'{method} {path} -> HTTP {resp.status}: {text[:500]}')
    if want_json:
        return await resp.json()

    # Content-Length lets us refuse an archive before pyfetch allocates its
    # response bytes. The length check after bytes() is the fallback for
    # servers that omit or hide that header from the browser.
    content_length = resp.headers.get('content-length')
    if content_length is not None:
        try:
            content_length = int(content_length)
        except (TypeError, ValueError):
            raise RuntimeError(
                f'{method} {path} -> invalid Content-Length header')
        if content_length > ZIP_MAX_COMPRESSED_BYTES:
            raise RuntimeError(
                f'{method} {path} -> archive exceeds the '
                f'{ZIP_MAX_COMPRESSED_BYTES}-byte compressed-size limit.')

    data = await resp.bytes()
    if len(data) > ZIP_MAX_COMPRESSED_BYTES:
        raise RuntimeError(
            f'{method} {path} -> archive exceeds the '
            f'{ZIP_MAX_COMPRESSED_BYTES}-byte compressed-size limit.')
    return data


def _find_series_dir_in_archive(root):
    """Same acceptance rule as app.py's build flow: series.json at the
    zip root, or inside a single top-level folder — which is exactly the
    shape GitLab's archive.zip produces (it wraps everything in a
    {project}-{ref}-{sha}/ folder)."""
    if (root / 'series.json').exists():
        return root
    subdirs = [p for p in root.iterdir() if p.is_dir()]
    if len(subdirs) == 1 and (subdirs[0] / 'series.json').exists():
        return subdirs[0]
    raise RuntimeError(
        'series.json not found at the root of the repository archive, nor '
        'inside a single top-level folder.'
    )


async def pull(base_url, token, project_id, branch):
    """Resolve a branch once, then download and bind that immutable revision.

    Returns (series_dir_str_or_None, error_text_or_None).
    """
    global _git_snapshot
    _git_snapshot = None
    if GIT_WORK_DIR.exists():
        shutil.rmtree(GIT_WORK_DIR)
    GIT_WORK_DIR.mkdir(parents=True)

    try:
        pid = quote(str(project_id), safe='')
        revision = await _remote_revision(base_url, token, project_id, branch)
        archive = await _request(
            base_url, token, 'GET', f'/projects/{pid}/repository/archive.zip',
            params={'sha': revision}, want_json=False,
        )
        with zipfile.ZipFile(io.BytesIO(bytes(archive))) as zf:
            _validate_zip_members(zf)
            zf.extractall(GIT_WORK_DIR)
        series_dir = _find_series_dir_in_archive(GIT_WORK_DIR)
        _git_snapshot = GitSnapshot(base_url, project_id, branch, series_dir, revision)
        return str(series_dir), None
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'


def build(series_dir, lang='fr'):
    """Runs the unmodified cmd_build() against a directory pull() prepared.

    Returns (ok, log_text, error_text_or_None).
    """
    log = io.StringIO()
    try:
        output_dir = Path(series_dir) / 'public'
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            cmd_build(series_dir, {'--output': str(output_dir), '--lang': lang})  # noqa: F821
        if not output_dir.exists() or not any(output_dir.iterdir()):
            return False, log.getvalue(), 'Build produced no output — see the log above.'
        return True, log.getvalue(), None
    except SystemExit as e:
        return False, log.getvalue(), f'Build stopped (exit code {e.code}) — see the log above.'
    except Exception as e:
        return False, log.getvalue(), f'{type(e).__name__}: {e}'


async def _remote_revision(base_url, token, project_id, branch):
    pid, ref = quote(str(project_id), safe=''), quote(branch, safe='')
    commit = await _request(base_url, token, 'GET',
                            f'/projects/{pid}/repository/commits/{ref}')
    return _commit_revision(commit)


def _commit_revision(commit):
    revision = commit.get('id') if isinstance(commit, dict) else None
    if not isinstance(revision, str) or not revision:
        raise RuntimeError('GitLab returned no commit revision')
    return revision


async def _remote_paths(base_url, token, project_id, revision):
    """File paths at one pinned revision, used to distinguish create from update.

    Push separately reads file revisions and checksums at this same revision.
    """
    pid = quote(str(project_id), safe='')
    paths = set()
    page = 1
    while True:
        items = await _request(
            base_url, token, 'GET', f'/projects/{pid}/repository/tree',
            params={'ref': revision, 'recursive': 'true', 'per_page': 100, 'page': page},
        )
        if not items:
            break
        for item in items:
            if item.get('type') == 'blob':
                paths.add(item['path'])
        if len(items) < 100:
            break
        page += 1
    return paths


# Mirrors default_nav_cache_path() in the generator. Declared rather than
# imported: under Pyodide the generator is a loaded script, not a package.
BUILD_CACHE_DIR = '.lwp-cache'
BUILD_MANIFEST_NAME = '.lwp-manifest.json'


async def push(base_url, token, project_id, branch, series_dir, commit_message):
    """Plan against the pulled revision and guard each update at the server.

    Branch checks detect earlier edits; file preconditions close the race after
    checking. Creates never become updates on a conflict. Any failed/uncertain
    attempt invalidates the snapshot; completed chunks remain reported and a
    new Pull is required before retrying. Returns (ok, summary_text).
    """
    snapshot = _git_snapshot
    if snapshot is None or not snapshot.matches(base_url, project_id, branch, series_dir):
        return False, 'No matching usable GitLab snapshot. Pull again before Build or Push.'
    pid = quote(str(project_id), safe='')
    commit_count = 0
    pending_request = False

    async def check_revision():
        if _git_snapshot is not snapshot or not snapshot.usable:
            raise RuntimeError('The loaded snapshot changed during Push')
        if await _remote_revision(base_url, token, project_id, branch) != snapshot.revision:
            raise RuntimeError('The remote branch changed since Pull or the last confirmed commit')

    try:
        await check_revision()
        remote_paths = await _remote_paths(base_url, token, project_id, snapshot.revision)
        actions = []
        for f in sorted(snapshot.directory.rglob('*')):
            if not f.is_file():
                continue
            relative = f.relative_to(snapshot.directory)
            if BUILD_CACHE_DIR in relative.parts or f.name == BUILD_MANIFEST_NAME:
                continue
            rel = relative.as_posix()
            content = f.read_bytes()
            action = {'action': 'update' if rel in remote_paths else 'create',
                      'file_path': rel, 'encoding': 'base64',
                      'content': base64.b64encode(content).decode('ascii')}
            if action['action'] == 'update':
                metadata = await _request(
                    base_url, token, 'GET', f'/projects/{pid}/repository/files/{quote(rel, safe="")}',
                    params={'ref': snapshot.revision})
                revision = metadata.get('last_commit_id') if isinstance(metadata, dict) else None
                if not isinstance(revision, str) or not revision:
                    raise RuntimeError(f'GitLab returned no file revision for {rel}')
                checksum = metadata.get('content_sha256')
                if not isinstance(checksum, str) or len(checksum) != 64:
                    raise RuntimeError(f'GitLab returned no content checksum for {rel}')
                if hashlib.sha256(content).hexdigest() == checksum:
                    continue
                action['last_commit_id'] = revision
            actions.append(action)
        if not actions:
            return True, 'Nothing to push: no new or changed files.'
        for i in range(0, len(actions), PUSH_CHUNK_SIZE):
            await check_revision()
            message = (f'{commit_message} (part {commit_count + 1})'
                       if len(actions) > PUSH_CHUNK_SIZE else commit_message)
            pending_request = True
            result = await _request(
                base_url, token, 'POST', f'/projects/{pid}/repository/commits',
                body={'branch': branch, 'commit_message': message,
                      'actions': actions[i:i + PUSH_CHUNK_SIZE]})
            commit_count += 1
            pending_request = False
            # A successful later chunk can incorporate a concurrent edit to a
            # file from an earlier chunk. Do not adopt that unseen content as
            # the baseline authorizing a future Push of stale local bytes.
            if result.get('parent_ids') != [snapshot.revision]:
                raise RuntimeError('The confirmed commit has an unexpected parent revision')
            snapshot.revision = _commit_revision(result)
    except Exception as exc:
        snapshot.usable = False
        return False, (f'Push stopped after {commit_count} commit(s) confirmed: {exc}. '
                       'Pull again before Build or Push.'
                       + (' An unconfirmed request may have reached GitLab.' if pending_request else ''))

    return True, f'Pushed {len(actions)} file(s) in {commit_count} commit(s).'
