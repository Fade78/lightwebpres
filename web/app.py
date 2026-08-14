"""Browser glue for LightWebPres.

Loaded into Pyodide after lightwebpres itself (see index.html), which
defines cmd_build() as a global in this same Python namespace. This module
never modifies or duplicates lightwebpres — it only wires a zip upload/zip
download flow around the existing, unmodified build() entry point.

Everything here runs against Pyodide's in-memory virtual filesystem: the
uploaded zip never leaves the browser tab.
"""

import contextlib
import io
import shutil
import zipfile
from pathlib import Path

ZIP_WORK_DIR = Path('/lwp_web_work')


def _validate_zip_members(zf):
    """Rejects hostile member names before extraction (zip-slip).

    The vendored runtime's zipfile already sanitizes `..` and absolute
    paths, but that is one layer; the defence-in-depth check here makes
    the intent explicit and keeps the glue safe on any runtime.
    """
    for name in zf.namelist():
        parts = Path(name.replace('\\', '/')).parts
        if name.startswith(('/', '\\')) or '..' in parts:
            raise RuntimeError(
                'archive contains a path outside the extraction root: %r' % name)


def _find_series_dir_in_zip(root):
    """Locates the series directory inside the extracted zip.

    Accepts either a zip whose root already contains series.json, or a zip
    with a single top-level folder containing series.json (the common shape
    produced by "Compress" / "Send to > zip" on most operating systems).
    """
    if (root / 'series.json').exists():
        return root
    subdirs = [p for p in root.iterdir() if p.is_dir()]
    if len(subdirs) == 1 and (subdirs[0] / 'series.json').exists():
        return subdirs[0]
    raise RuntimeError(
        'series.json not found at the root of the zip, nor inside a single '
        'top-level folder.'
    )


def build_from_zip_bytes(data, lang='fr'):
    """Builds a series from an uploaded zip's bytes.

    Returns (result_zip_bytes_or_None, log_text, error_text_or_None).
    On success, error_text is None and result_zip_bytes holds the zipped
    public/ output. On failure, result_zip_bytes is None and error_text
    describes what went wrong; log_text always holds whatever build/verify
    printed, for troubleshooting either way.
    """
    log = io.StringIO()

    if ZIP_WORK_DIR.exists():
        shutil.rmtree(ZIP_WORK_DIR)
    ZIP_WORK_DIR.mkdir()

    try:
        with zipfile.ZipFile(io.BytesIO(bytes(data))) as zf:
            _validate_zip_members(zf)
            zf.extractall(ZIP_WORK_DIR)

        series_dir = _find_series_dir_in_zip(ZIP_WORK_DIR)
        output_dir = series_dir / 'public'

        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            cmd_build(str(series_dir), {'--output': str(output_dir), '--lang': lang})  # noqa: F821

        if not output_dir.exists() or not any(output_dir.iterdir()):
            return None, log.getvalue(), 'Build produced no output — see the log above.'

        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(output_dir.rglob('*')):
                if f.is_file():
                    zf.write(f, f.relative_to(output_dir))

        return result.getvalue(), log.getvalue(), None

    except SystemExit as e:
        return None, log.getvalue(), 'Build stopped (exit code %s) — see the log above.' % e.code
    except Exception as e:
        return None, log.getvalue(), '%s: %s' % (type(e).__name__, e)
    finally:
        shutil.rmtree(ZIP_WORK_DIR, ignore_errors=True)
