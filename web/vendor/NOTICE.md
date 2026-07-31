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
- `LICENSE` — upstream license text (MPL-2.0)

## Updating

```
curl -sL "$(curl -s https://registry.npmjs.org/pyodide/latest | python3 -c 'import json,sys;print(json.load(sys.stdin)["dist"]["tarball"])')" -o pyodide.tgz
tar xzf pyodide.tgz package/pyodide.js package/pyodide.asm.mjs package/pyodide.asm.wasm package/python_stdlib.zip package/pyodide-lock.json
cp package/{pyodide.js,pyodide.asm.mjs,pyodide.asm.wasm,python_stdlib.zip,pyodide-lock.json} web/vendor/pyodide/
```

Then re-run `python3 tests/run_tests.py` — the web E2E test will catch any
incompatibility introduced by a newer Pyodide/CPython version.
