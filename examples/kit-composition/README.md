# Field Notes: compose three independent kits

This source example combines a ruled notebook frame, a compass masthead and a
monochrome typewriter theme into **Field Notes**, preset **Field Notes Brief**
(`field-notes@1.0.0/brief`). It contains no built site. The `.html` source is a
layout fragment with slots, not a generated page.

## What the recipe selects

| Alias | Independent source kit | Selected resources |
| --- | --- | --- |
| `frames` | `sources/field-frames/1.0.0` | `layouts/sheet.html`, renamed to `layouts/notebook.html`; `structure.css` |
| `marks` | `sources/field-marks/1.0.0` | `chrome.json` and `assets/compass.svg` |
| `ink` | `sources/field-ink/1.0.0` | The complete typed theme `themes/paper.conf` |

Each source has its own valid `lightwebpres.identity-kit/1` manifest and usable
preset. Frames supplies no chrome; Marks supplies no layout files; Ink supplies
only its theme. They use `builtin:standard` for native layouts and, where no
custom theme is needed, `builtin:light`. These built-ins belong to the tool;
they are not dependencies on another kit.

`recipe.json` uses `lightwebpres.kit-composition/1`. Its `manifest` is the
**complete final manifest**, not a patch or an inheritance declaration. Its
`files` map names every selected destination. The composer rebinds the structural
CSS scope from `.lwp-presentation--field-frames` to
`.lwp-presentation--field-notes`. It does not rename references inside HTML,
chrome or theme files, and does not infer missing dependencies.

The target explicitly declares the local theme name `paper`, chrome model
`masthead` and asset name `compass`. The copied chrome's `presentation:compass`
resolves to the target's own `assets.compass`, not to the Marks kit. The final
cover and standard layouts reference `layouts/notebook.html`; navigation,
full-article and index layouts remain native.

Marks also declares `assets/trail.svg`. It is deliberately absent from both the
recipe's file selection and the final manifest. Composition leaves the source
kits unchanged, but does not copy everything they contain. Once composed, the
result needs neither these source kits nor the recipe.

## Compose and inspect

Run these Bash commands **from the repository root**. `repo` records that root;
all subsequent commands use explicit paths and can run from any directory in
the same shell. Python 3.8+ is sufficient; no package installation is needed.

```bash
repo="$PWD"
mkdir -p "$repo/work/tmp"
export TMPDIR="$repo/work/tmp"
work="$(mktemp -d "$TMPDIR/lwp-field-notes.XXXXXX")"
export LWP_IDENTITY_KITS_DIR="$work/kits"

python3 "$repo/lightwebpres" kit compose \
  "$repo/examples/kit-composition/recipe.json" \
  --output "$LWP_IDENTITY_KITS_DIR" --dry-run

python3 "$repo/lightwebpres" kit compose \
  "$repo/examples/kit-composition/recipe.json" \
  --output "$LWP_IDENTITY_KITS_DIR"

python3 "$repo/lightwebpres" preset show field-notes@1.0.0/brief --format json
```

The dry run validates all three sources and the complete result without creating
the output kit. The second command creates
`$work/kits/field-notes/1.0.0/`. Composition refuses an existing destination:
use a fresh `work` directory to repeat the walkthrough. For a persistent install,
choose an absolute directory you own for `LWP_IDENTITY_KITS_DIR` before composing;
keep that variable set when inspecting, initializing or building a series.

## Build the same first article

This uses the exact Markdown and series metadata from `examples/first-article`.
It deliberately does **not** copy that example's `templates/settings.conf`,
which pins `nebula` and would override the preset theme.

```bash
python3 "$repo/lightwebpres" init "$work/first-article" \
  --preset field-notes@1.0.0/brief
cp "$repo/examples/first-article/sources/first-page.md" \
  "$work/first-article/sources/first-page.md"
cp "$repo/examples/first-article/series.json" "$work/first-article/series.json"
python3 "$repo/lightwebpres" series preset set "$work/first-article" \
  --preset field-notes@1.0.0/brief --use-preset-theme
python3 "$repo/lightwebpres" build "$work/first-article" --lang en
python3 "$repo/lightwebpres" verify "$work/first-article" --lang en
```

Copying `series.json` replaces the selection written by `init`, so the explicit
`series preset set` restores it. Open
`$work/first-article/public/first-page.html` for the presentation, or
`$work/first-article/public/index.html` for its index. The article filename is
**`first-page.html`**, not `first-article.html`.

The cover and standard slide show a double-ruled frame, the compass and an
editorial masthead. The paper theme uses white, black and quiet gray with system
monospace fonts. The wrapper shrinks its padding on small screens. No fonts are
downloaded. This article has no layout or chrome overrides, so the runtime can
also offer `builtin/standard` as its native alternative.

The published compass is
`public/assets/presentations/field-notes/1.0.0/compass.svg`.
Publish the whole `public/` directory. There is no published trail icon.

## Try the built-in demo

Use a separate series to keep the first article comparison unchanged:

```bash
python3 "$repo/lightwebpres" init "$work/demo" --preset field-notes@1.0.0/brief
python3 "$repo/lightwebpres" demo "$work/demo" --lang en
python3 "$repo/lightwebpres" build "$work/demo" --lang en
python3 "$repo/lightwebpres" verify "$work/demo" --lang en
```

`demo` writes and builds its sample articles; the explicit `build` also shows
the command to run after editing them. Open `$work/demo/public/index.html`.
The composed kit has no starter and does not inherit one from a source.

## Preset theme versus explicit override

`init --preset field-notes@1.0.0/brief` leaves the typed theme under the preset's
control. `init --preset field-notes@1.0.0/brief --theme nord` instead pins `nord`
in the new series' settings. The frame, masthead and kit selection remain Field
Notes; only the typed theme base changes. `--theme` is not a `build` option.

For an existing series, try the override and then restore the preset theme:

```bash
python3 "$repo/lightwebpres" series theme set "$work/first-article" --theme nord
python3 "$repo/lightwebpres" build "$work/first-article" --lang en
python3 "$repo/lightwebpres" series theme "$work/first-article" --format json

python3 "$repo/lightwebpres" series preset set "$work/first-article" \
  --preset field-notes@1.0.0/brief --use-preset-theme
python3 "$repo/lightwebpres" build "$work/first-article" --lang en
```

The compass is an authored black-and-white SVG with its own white ground; a
typed theme does not recolor its pixels. `--use-preset-theme` clears the explicit
theme selection, not arbitrary property pins or custom CSS you may have added.

## Inspect a source on its own

Point the catalogue at the example's sources, rather than the composed output:

```bash
LWP_IDENTITY_KITS_DIR="$repo/examples/kit-composition/sources" \
  python3 "$repo/lightwebpres" preset show field-frames@1.0.0/sheet
LWP_IDENTITY_KITS_DIR="$repo/examples/kit-composition/sources" \
  python3 "$repo/lightwebpres" preset show field-marks@1.0.0/compass
LWP_IDENTITY_KITS_DIR="$repo/examples/kit-composition/sources" \
  python3 "$repo/lightwebpres" preset show field-ink@1.0.0/paper
```

These command-local assignments leave the composed catalogue selected for later
commands. Each source also works if its siblings are removed: the example test
installs and builds them one at a time, then builds the composed result after
deleting its copied recipe and sources.

## Theme provenance and licenses

`sources/field-ink/1.0.0/themes/paper.conf` is a committed, complete snapshot of
the tool's `print-oldpress` theme, not a reference to a globally installed theme.
Its metadata is `schema: lightwebpres.theme/1`, `label: Field Notes Paper`,
`family: print`, `source: lightwebpres`. This repo-root command regenerates that
source snapshot intentionally; it is not needed to use the example:

```bash
python3 "$repo/lightwebpres" theme create paper --from print-oldpress \
  --family print --label "Field Notes Paper" --source lightwebpres \
  --note "Complete Print Old Press snapshot for the Field Notes composition example." \
  --output "$repo/examples/kit-composition/sources/field-ink/1.0.0/themes/paper.conf" \
  --force
```

The recipe, layouts, structural CSS and typed theme use the repository's GPLv3
license and applicable Output Exception; see `COPYING` and `COPYING.EXCEPTION`
at the repository root. The compass and trail icons are original, symbolic,
nonbrand artwork for this example, separately licensed under MIT in
`LICENSE-SVG.txt`. Their notices also travel inside the SVGs. No third-party
fonts or assets are bundled.

Run the source-example tests from the repository root:

```bash
python3 -m unittest tests.test_documentation_examples -v
```
