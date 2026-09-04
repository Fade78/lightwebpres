# Demonstration presentation packages

`lightwebpres-docs@0.1.0/docs` is the first presentation preset shipped as a
repository example. Its package is used by `tools/build_guide.py`, so the
official guide is also a live example of a portable package with layouts,
chrome, constrained structural CSS, an asset, and a preset-declared starter.

Inspect it from the repository root:

```bash
LWP_PRESENTATION_PACKAGES_DIR="$PWD/examples/layouts" ./lightwebpres preset show lightwebpres-docs@0.1.0/docs
```

Use it in a new series:

```bash
LWP_PRESENTATION_PACKAGES_DIR="$PWD/examples/layouts" ./lightwebpres init my-series --preset lightwebpres-docs@0.1.0/docs
```

`init --preset` applies the preset's declared starter by default; add
`--no-starter` to leave it out. For an existing series, use
`series preset set my-series --preset lightwebpres-docs@0.1.0/docs` and choose
`--keep-theme` or `--use-preset-theme` if `settings.conf` has an explicit
`theme:`.

The package is deliberately not installed into the user's catalogue. Keeping
its physical `layouts/<id>/<version>/` namespace here makes the example
inspectable, versioned and available to the guide build without changing a
user's global environment.
