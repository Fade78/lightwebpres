# Vendored third-party code

`pyodide/` contains an unmodified copy of the [Pyodide](https://pyodide.org)
runtime (CPython compiled to WebAssembly + the Python standard library),
used to run `lightwebpres` directly in the browser for `web/index.html`.

- Source: `pyodide` npm package, version `314.0.3`
  (https://registry.npmjs.org/pyodide/-/pyodide-314.0.3.tgz)
- License: Mozilla Public License 2.0 — see `pyodide/LICENSE`
- Upstream project: https://github.com/pyodide/pyodide

This is not part of the `lightwebpres` executable itself, which remains
Python-standard-library-only (specifications.md §13.4). It is an optional
dependency of the separate, additive browser build page only.

## Files

- `pyodide.js` — loader (classic script, exposes `loadPyodide`)
- `pyodide.asm.mjs`, `pyodide.asm.wasm` — the compiled interpreter
- `python_stdlib.zip` — the Python standard library
- `pyodide-lock.json` — package manifest read by the loader
- `SHA256SUMS` — integrity checksums for the five files above
- `LICENSE` — upstream license text (MPL-2.0)

## Integrity

`pyodide/SHA256SUMS` records the SHA-256 of every served runtime file.
These assets run the code that handles a user's series (and, on the
GitLab tab, their token), so a tampered vendored file compromises the
whole page. The files are committed to git — any change is reviewable in
the diff — and served same-origin (no runtime CDN). Verify at any time
with:

```
( cd web/vendor/pyodide && sha256sum -c SHA256SUMS )
```

## Updating

Pin an **exact** version (never `latest`), download it, **verify the
upstream-published hash before copying**, then record the new local
checksums. Set `VER` and paste the `dist.integrity` (or `dist.shasum`)
npm publishes for that version:

```
VER=314.0.3
curl -sL "https://registry.npmjs.org/pyodide/-/pyodide-${VER}.tgz" -o pyodide.tgz
# Verify the tarball against npm's published integrity BEFORE trusting it:
EXPECTED=$(curl -s "https://registry.npmjs.org/pyodide/${VER}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["dist"]["shasum"])')
echo "${EXPECTED}  pyodide.tgz" | sha1sum -c - || { echo "TARBALL HASH MISMATCH — abort"; exit 1; }
tar xzf pyodide.tgz package/pyodide.js package/pyodide.asm.mjs package/pyodide.asm.wasm package/python_stdlib.zip package/pyodide-lock.json
cp package/{pyodide.js,pyodide.asm.mjs,pyodide.asm.wasm,python_stdlib.zip,pyodide-lock.json} web/vendor/pyodide/
# Record the new checksums and update the version string above:
( cd web/vendor/pyodide && sha256sum pyodide.js pyodide.asm.mjs pyodide.asm.wasm python_stdlib.zip pyodide-lock.json > SHA256SUMS )
```

Then re-run `python3 tests/run_tests.py` — the web E2E test will catch any
incompatibility introduced by a newer Pyodide/CPython version.
