# Demonstration Identity Kits

`lightwebpres-docs@0.1.0/docs` is a presentation preset shipped as a
repository example. Its Identity Kit is used by `tools/build_guide.py`, so the
official guide is also a live example of a portable kit with layouts,
chrome, constrained structural CSS, an asset, and a preset-declared starter.

Inspect it from the repository root:

```bash
LWP_IDENTITY_KITS_DIR="$PWD/examples/kits" ./lightwebpres preset show lightwebpres-docs@0.1.0/docs
```

Use it in a new series:

```bash
LWP_IDENTITY_KITS_DIR="$PWD/examples/kits" ./lightwebpres init my-series --preset lightwebpres-docs@0.1.0/docs
```

`init --preset` applies the preset's declared starter by default; add
`--no-starter` to leave it out. For an existing series, use
`series preset set my-series --preset lightwebpres-docs@0.1.0/docs` and choose
`--keep-theme` or `--use-preset-theme` if `settings.conf` has an explicit
`theme:`.

The kit's `lightwebpres.identity-kit/1` manifest gives it a fixed identity
`label` and named presets; `default_preset`, or the first preset in manifest
order, selects its default without changing the identity's name. Its references
are local files or native layouts/themes, never dependencies on another kit.

The kit is deliberately not installed into the user's catalogue. Keeping
its physical `kits/<id>/<version>/` namespace here makes the example
inspectable, versioned and available to the guide build without changing a
user's global environment.

For the user workflow, follow
[Design and compose identities](../../GUIDE.md#3-design-and-compose-identities).
For explicit assembly from several independent kits, use the
[Field Notes composition example](../kit-composition/README.md). The
[presentation glossary](../../GLOSSARY.md#presentation-vocabulary) distinguishes
identity ownership, resource collection and loading origin: Commons is a shared
collection, not another identity.
