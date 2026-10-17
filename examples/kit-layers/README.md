# Kit-owned graphic layers

Requires LightWebPres 0.73.0 or newer. This is a tracked **source example**, not
a directory to build in place. It demonstrates both the kit designer's files
and an author's independent source choices. No custom slide HTML or structural
CSS is required: the kit deliberately reuses native layouts.

## Build a disposable copy

From the repository root:

```bash
mkdir -p work/tmp
demo="$(mktemp -d "$PWD/work/tmp/kit-layers-demo.XXXXXX")"
cp -a examples/kit-layers/. "$demo/"
python3 lightwebpres build "$demo" --lang en
python3 lightwebpres verify "$demo" --lang en
```

Open `$demo/public/kit-layers.html#inherited`, then use **C** to change presets.
The optional combined/embedded output uses matching build/verify flags:

```bash
python3 lightwebpres build "$demo" --lang en --single-html series.html --inline-images
python3 lightwebpres verify "$demo" --lang en --single-html series.html --inline-images
```

The README beside the series is build-owned and reflects the last output mode;
verify immediately with the same flags rather than checking an older mode's
README after building another one.

## Follow the two ownership paths

| Owner | Declaration | Purpose |
|---|---|---|
| Kit | `templates/kits/signal-notes/1.0.0/manifest.json` → `resources` | Registers two graphic assets and two compositions |
| Preset | The same manifest's `presets` | Supplies ordered choices before documentary overrides |
| Series | Root `series.json.resources` | Registers the independent SOURCE marker |
| Unit | `sources/kit-layers.md`, `lwp:meta.layers` | Adds SOURCE after every preset/type choice |
| Slide | The `local` and `disabled` headers | Replaces or clears the inherited selection |

These are resource ownership and resolution sources, not four new logical
scopes. The documentary scopes remain series, unit and slide.

The corner mark is an image asset, not chrome. Its literal `file` value is
`signal mark.svg`; no URL encoding belongs in that descriptor. Its instance
uses the current theme's kicker ink as a tint. The DRAFT text is a separate
static HTML asset. The source marker is not hidden in the kit and is never
implicitly rewritten when the identity/preset changes.

## Exercise every preset and exception

- **Marked:** adds `brand`; cover and generated notes opt out at preset scope.
- **Review:** changes the mark's rotation and adds `draft` underneath content;
  full articles remove only `draft` in their preset type choice.
- **Clean:** chooses `[]` at preset scope. The later unit addition still adds
  SOURCE; Clean is not a higher-authority ban on author choices.
- **Local card:** an array containing `kit/brand` replaces all inherited layers
  and explicitly overrides the image instance's rotation/opacity.
- **Disabled card:** slide-local `[]` cancels kit and author layers together.

Review is a presentation choice, not publication status: the DRAFT graphic
does not set article `status`, change tags or modify publication membership.

`auto` resets to tag/selector matching, not to the preset's explicit list.
Manifest fields use actual JSON arrays/objects, not strings containing encoded
JSON; Markdown metadata is where the one-line textual JSON form belongs.
Arrays replace; `{ "add": [...] }` is the right form for a preset that should
augment automatic matching. `{ "remove": [...] }` removes effective instance
IDs; `{use, as, overrides}` addresses an element by its declared ID, not index.

An unqualified source reference resolves unit → series → active kit. `kit/id`
explicitly uses the active kit. A kit composition binds its **own** assets,
even when an author declares a source asset with the same name. Kits cannot
capture another kit's or a document's resources as dependencies.

## Publish compatible alternatives

Every declared appearance alternative is validated before files are replaced.
This example publishes three presets from the same kit, all of which expose
`brand`, including Clean. Its explicit `kit/brand` card therefore remains valid.

To add `builtin/standard`, first remove that card's explicit kit reference or
replace it with a source-owned composition. Native Built-in has no `brand`
resource. The other cards can then follow the native/kit identity choice while
SOURCE remains independent. A palette-only change changes ink, not the selected
composition or resource catalogue. Menus remain above graphics; decorative
images do not intercept gestures.

The series deliberately lists Monochrome Night as an explicit palette, so that
author choice remains fixed while presets change compositions. To start from
the kit's Paper theme instead, change `appearance.themes` to
`["preset","essential"]` and rebuild. Listing `preset` before an explicit
palette does not make that palette stop being an author override.

Kit choices apply to the five authored card types and generated notes. The
separate series contents HTML is not a card; its logo/chrome uses the existing
Identity Kit layout contract, not an implicit graphical-slide policy.

## Inspect before editing

```bash
LWP_IDENTITY_KITS_DIR="$demo/templates/kits" python3 lightwebpres kit show signal-notes@1.0.0 --format json
python3 lightwebpres series preset "$demo" --format json
python3 lightwebpres resolve "$demo" resources --article kit-layers.md --format json
python3 lightwebpres resolve "$demo" layers --article kit-layers.md --format json
```

Kit reports list graphic resource IDs separately from chrome assets. Preset
reports include declared `layers` / `layers_by_type`. Layer resolution keeps
the primary `sites` view and exposes every published plan in `presets`, keyed
by the full preset selector. Origins are computed by loaders, not asserted by
the manifest. The resource schemas and live kit/cascade contract are under
`contract.graphics`.

## Compose and move the kit

`compose.json` explicitly copies all five declared descriptor/payload files and
supplies the final independent manifest:

```bash
python3 lightwebpres kit compose "$demo/compose.json" --output "$demo/composed-kits"
LWP_IDENTITY_KITS_DIR="$demo/composed-kits" python3 lightwebpres kit show signal-notes-composed@1.0.0 --format json
```

The composed kit does not extend `signal-notes` or need its files at runtime.
Native layout/theme references are supported engine resources, not another kit
dependency. Installing either kit with `init --preset` or `series preset set`
copies its graphic descriptors and payloads with the kit; a starter is optional
source content, not the mechanism that makes kit layers work.

Changes to declared graphic JSON or payloads affect the kit digest and build
fingerprints. `watch` observes kit files; `verify` detects stale output. Both
output modes publish the media needed by inactive alternatives too, but do not
publish an unused asset merely because it was registered. Normal manifest and
sidecar ownership rules still govern `clean`.

For print, the mark uses the complete logical card, not a captured screen
fragment. Screen/viewport-based elements need an explicit print override or
screen-only media. Inspect the real print/PDF output as well as a screen-media
preview. The example's SVG and text are original repository sources under the
project's licensing terms; it includes no third-party image or font.
