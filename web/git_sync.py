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

Three independent steps, each callable on its own from the page:
  - pull(): downloads the repository archive for a branch and extracts it
    into the work directory.
  - build(): runs the unmodified cmd_build() against the pulled directory.
  - push(): diffs the work directory (sources + the public/ that build()
    just produced) against the remote repository tree and commits
    create/update actions for changed or new files in one commit (chunked
    if large). Never deletes: a file that disappeared locally but still
    exists remotely is left untouched — deletions go through GitLab
    directly, not through this page (specifications.md §23.12).
"""

import base64
import contextlib
import io
import json
import shutil
import zipfile
from pathlib import Path
from urllib.parse import quote, urlencode

from pyodide.http import pyfetch

GIT_WORK_DIR = Path('/lwp_git_work')

PUSH_CHUNK_SIZE = 100


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
    return await resp.bytes()


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
    """Downloads the repository archive for `branch` and extracts it.

    Returns (series_dir_str_or_None, error_text_or_None).
    """
    if GIT_WORK_DIR.exists():
        shutil.rmtree(GIT_WORK_DIR)
    GIT_WORK_DIR.mkdir(parents=True)

    try:
        pid = quote(str(project_id), safe='')
        archive = await _request(
            base_url, token, 'GET', f'/projects/{pid}/repository/archive.zip',
            params={'sha': branch}, want_json=False,
        )
        with zipfile.ZipFile(io.BytesIO(bytes(archive))) as zf:
            zf.extractall(GIT_WORK_DIR)
        series_dir = _find_series_dir_in_archive(GIT_WORK_DIR)
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


async def _remote_paths(base_url, token, project_id, branch):
    """Full set of file paths that currently exist in the remote tree, so
    push() can tell create from update. Existence only — no content is
    fetched, so an update is issued even when the content already matches
    (a same-content commit, harmless but not skipped; see §23.12)."""
    pid = quote(str(project_id), safe='')
    paths = set()
    page = 1
    while True:
        items = await _request(
            base_url, token, 'GET', f'/projects/{pid}/repository/tree',
            params={'ref': branch, 'recursive': 'true', 'per_page': 100, 'page': page},
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


async def push(base_url, token, project_id, branch, series_dir, commit_message):
    """Commits every file under series_dir (sources + public/) that is new
    or differs by path from what's remote. Returns (ok, summary_text).
    """
    pid = quote(str(project_id), safe='')
    remote_paths = await _remote_paths(base_url, token, project_id, branch)

    root = Path(series_dir)
    actions = []
    for f in sorted(root.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(root).as_posix()
        action = 'update' if rel in remote_paths else 'create'
        actions.append({
            'action': action,
            'file_path': rel,
            'content': base64.b64encode(f.read_bytes()).decode('ascii'),
            'encoding': 'base64',
        })

    if not actions:
        return False, 'Nothing to push: the work directory is empty.'

    commit_count = 0
    for i in range(0, len(actions), PUSH_CHUNK_SIZE):
        chunk = actions[i:i + PUSH_CHUNK_SIZE]
        message = commit_message
        if len(actions) > PUSH_CHUNK_SIZE:
            message = f'{commit_message} (part {commit_count + 1})'
        await _request(
            base_url, token, 'POST', f'/projects/{pid}/repository/commits',
            body={'branch': branch, 'commit_message': message, 'actions': chunk},
        )
        commit_count += 1

    return True, f'Pushed {len(actions)} file(s) in {commit_count} commit(s).'
