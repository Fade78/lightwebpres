# Anchored graphic compositions

Status: integrated for unreleased 0.72.0 (DECISIONS.md B98).
The implementation originally lived in the uncommitted `feature/layers`
worktree and announced 0.71.0 locally; main's separately committed 0.71.0
contains table merges and reader corrections, not graphics. The original
branch's B85/B86 entries are preserved here as B98/B99 to avoid main's IDs.
The initial runs retained the baseline Pointer Lock test intermittence;
their qualified results remain below. B99 records the subsequent complete green run.
Owner-authorized implementation branch: `feature/layers`, based on v0.70.0.
The owner explicitly requested this branch as an exception to the normal
main-only contribution workflow, and delegated remaining design choices.
The original commission did not imply publication, release or merge into main.
The owner later authorized a commit, the `v0.71.0` tag and a push to `origin`;
that historical authorization is not evidence that a commit or tag was made.
On 2026-10-16 the owner authorized integration after table-only 0.71.0 was
committed/pushed. The original worktree remains intact. No 0.72.0 tag, push or
GitHub release is implied by this integration request.
The finalized normative contract is `specifications.md` §9.10. This feature
retains the commissioning choices, scope and verification record.

Follow-up B99 expands the guide/example into explicit free-image, background,
foreground and theme-driven decoration cases, and adds typed inline field
styles. The original run counts below describe this feature's first increment;
the follow-up has its own final verification record.

## Purpose and vocabulary

- An **asset** is reusable image or static HTML content. HTML can be authored
  as plain text, inline Markdown, block Markdown or a static HTML fragment.
- An **element** is a named asset instance with layout, size, rotation,
  attachment, effects and optional overrides.
- A **layer** is an ordered composition of elements, not a flattened image.
- **Application** selects compositions for series, units and slides.
- A **screen / écran** is the geometrically visible portion of one slide in
  the reader at a given instant: its rectangle intersected with the visual
  viewport. Two partially visible slides have separate screens. This is not a
  new logical scope, URL identity, discrete page or publication filter.
- The **viewport** is the full reader window; the **slide** is the complete
  logical card, potentially taller than the viewport. Overlay dialogs do not
  change the geometric screen rectangle.

## Authoring and resource ownership

External JSON descriptors use `lightwebpres.asset/1` and `lightwebpres.layer/1`.
`resources.assets` and `resources.layers` accept descriptor paths. Series root
declarations own series resources; article metadata imports and inline blocks
own unit resources. Import paths are relative to the series root. Payload files
are relative to their descriptor (or the unit's sources directory for inline
definitions), inside the authorized resource root. URLs and file paths remain
distinct, and spaces/non-ASCII names are encoded rather than renamed.

Image `src` values inside HTML/Markdown assets use URL encoding: decoding
happens once before contained file lookup, with SVG fragments kept on the
published/embedded URL. Descriptor `file` values are literal filesystem paths,
not URLs. This distinction also preserves percent signs and encoded filename
punctuation without double-decoding or renaming source files.

Examples:

```json
{
  "resources": {
    "assets": ["templates/assets/draft-label/asset.json"],
    "layers": ["templates/layers/draft/layer.json"]
  }
}
```

```json
{
  "schema": "lightwebpres.asset/1",
  "id": "draft-label",
  "kind": "html",
  "format": "markdown-inline",
  "content": "**DRAFT**",
  "style": {
    "font": {"theme": "kicker.font"},
    "font_size": "28px",
    "color": {"theme": "kicker.fg"}
  }
}
```

Image assets use `kind: image` and `file`. HTML assets use exactly one of `file`
and `content`; their format is `plain`, `markdown-inline`, `markdown` or `html`.
Media and descriptors are immutable inputs during one build operation.

Inline resource fences (`lwp-asset`, `lwp-layer`, at least three backticks)
contain the same JSON descriptor. An HTML asset may instead put literal content
after a whole-line `---` following its JSON header. Use a longer outer fence
when quoting code fences. These declarations live in the unit resource prologue
after `lwp:meta` and before the first slide. They are extracted before slide
splitting, never interpreted inside ordinary code fences, and retain original
file/line diagnostics. Forward references are allowed.

Definitions do not render at the declaration location. Inline objects may also
define an asset inside an element, or a composition inside a `layers` choice.
Duplicate IDs in one scope fail. Unqualified lookup searches the definition's
own scope then the series; `series/id` and `unit/id` explicitly qualify names.
Using a series composition from a unit does not dynamically rebind its assets.
Instance overrides are explicit. Named copies use `as`; source origins are
computed, not asserted by a resource.

## Composition and selection

```json
{
  "schema": "lightwebpres.layer/1",
  "id": "draft",
  "tags": ["draft"],
  "plane": "over-content",
  "elements": [{
    "id": "stamp",
    "asset": "draft-label",
    "place": {
      "target": {"ref": "slide", "anchor": "top-left"},
      "self_anchor": "top-left",
      "offset": ["24px", "24px"]
    },
    "screen": {"place": {"target": {"ref": "screen", "anchor": "top-left"},
      "self_anchor": "top-left", "offset": ["24px", "24px"]}},
    "rotate": "-12deg",
    "opacity": 0.28
  }]
}
```

Only registered resources participate. Automatic application matches literal
normalized slide tags (OR), not shared-default reader visibility or inferred
roles. No tags/selector means explicit use only. An optional selector reuses
the bounded selector core and cannot depend on the result of layer selection.
A graphical DRAFT mark does not change publication status.

`layers` is accepted in series metadata, unit metadata and all five slide types:

| Value | Meaning |
|---|---|
| omitted | inherit |
| `auto` | reset to automatic matching |
| list | replace selection, in painting order |
| `[]` | no layers, including automatic matches |
| `{ "add": [...], "remove": [...] }` | modify inherited selection |

`layers_by_type` at series/unit scope provides type-specific choices after that
scope's general choice. Unit scope wins over series, slide scope wins last.
Choices may be resource IDs, `{use, as, overrides}` instances, or inline layer
objects. Overrides address element IDs, not array indices. Scalars replace;
structured layout/size/place/effects replace their complete value. Unknown or
duplicate effective instance IDs fail. Generated notes receive the unit policy;
the separate series contents view is not silently treated as a slide.

## Geometric references

Native semantic references include slide, screen, viewport, main, header,
header-group, footer, kicker, title, summary, highlight, highlight-caption,
fact, fact-label, fact-content, body, source, slide-number and rendered notes.
Availability is explicit per slide type. Metadata-only and hidden speaker-note
fields do not acquire geometry. Assets cannot impersonate native components.

- `box` measures the border rectangle, without margins or effects.
- `content` measures visible text/child-content bounds instead of an allocated
  empty box. Main and header-group are semantic aggregates.
- Anchors are the nine physical rectangle points; x increases rightward,
  y downward, positive angles clockwise, independent of text direction.
- Placement aligns a post-rotation self anchor to a target anchor plus offset.
- `element:id` references an instance in the current composition;
  `layer:instance/id` references another selected composition instance.
- `on_missing` supports `hide`, `error` and a named fallback reference.
  Unknown names are errors; offscreen is not missing. Screens with no visible
  area hide their dependent elements without a diagnostic storm.

Lengths are CSS px (numeric or `px`), physical CSS units where supported,
viewport units, or `{percent, of}` with an explicit reference dimension such
as `screen.width`, `summary.height` or `element:logo.width`. No arbitrary eval.
`size.measure` is `before-rotation` or `after-rotation` (default latter), using
the image/layout rectangle, including transparent source margins, excluding
shadows/glow. Aspect ratios are preserved. A width/height box uses contain or
explicit cover, not distortion.

Regions derive left/right/top/bottom boundaries from references and offsets.
Inverted/empty regions follow the missing-reference policy, never move native
content. Region references, size and placement all enter the dependency graph.
Cycles are errors with a readable chain. Native roots cannot depend on layers.

## Text layout, style and interaction

Typography and geometric scaling are separate. `layout.width` wraps HTML before
measurement; an explicit `size` uniformly scales that frozen layout. Line
wrapping does not change within a rotated-size calculation.

Style properties accept typed literals or `{theme: property}` references.
References follow resolved theme/settings/unit pins but not accidental native
CSS classes or content-fit multipliers. Fixed values stay theme-independent;
browser zoom remains browser zoom. Theme-linked and fixed properties may mix.
There is no implicit role/style-copy mode: authors name the typed property
references they want, including font family, size, colour and spacing.

Static HTML is isolated from document styles (Shadow DOM with a local reset),
and cannot become a native heading/kicker/reference. Scripts, event handlers,
forms, embedded browsing contexts and unsafe URLs are rejected; this does not
turn the existing trusted raw-HTML body grammar into a sanitizer. IDs are local
to instances. Links require explicit `interaction: links`; ordinary layers
pass pointer gestures through and add no unexpected keyboard stops. Images
require explicit alternative text (empty means decorative). HTML text retains
meaningful accessible content. B81's image-click zoom remains separate.

Opacity, alpha-contour shadow/glow, tint and bounded basic filters are typed.
Shadow offsets use screen axes after rotation. Under-content layers paint above
the slide background and below its content; over-content layers never cover
reader controls/dialogs. Composition/element order is deterministic. The layer
host is isolated and clipped; it cannot alter content scroll metrics, fitting,
zoom, notes, counts, native links or navigation. Optional debug outlines reveal
reference and transformed bounds.

## Media and lifecycle choices

Base element geometry applies to both media. Optional `screen` and `print`
overrides replace complete geometric fields. Print uses the full logical slide
and native print components, not the currently visible screen fragment. A base
screen/viewport-dependent element must provide a print override or explicitly
limit its media to screen. Screen-only dependencies in a screen override do not
pollute the base print geometry. Print restores screen composition afterwards.
Printing repeats per logical slide; physical-paper-page repetition requires a
separate pagination feature and is not falsely promised.

Body fitting finishes first. Geometry then follows native boxes, font/image
loads, themes, presets, resizing, native fullscreen and scroll. VisualViewport
updates repaint screen-based graphics without forcing native pinch reanchoring.
HTML-combined view/preset replacement remounts graphics from retained plans.
Only visible slides need dynamic geometry work; payloads/media are deduplicated.

Build/verify share asset inventory, inline-image embedding, manifest ownership
and pre-write validation. Watch and incremental fingerprints include descriptor
and payload dependencies. Clean does not delete unrelated files. Inspection and
the machine contract expose schemas, native references and effective plans.

## Delivery checklist

- [x] Parser extraction, scoped catalogs, external/inline equivalence.
- [x] Selection, type overrides, tag/selector defaults, provenance.
- [x] Static HTML validation, typed styling and media lifecycle.
- [x] Native/instance/region references, DAG validation and geometry.
- [x] Independent rendering, effects, fitting/gesture isolation.
- [x] Asset publication, inline images, watch/verify/clean/incremental paths.
- [x] Native/kit/combined runtime, screen/viewport distinction, printing.
- [x] Contract, inspection, examples and permanent documentation.
- [x] Chromium/Firefox regression matrix and full six-worker runs, with the
  baseline Pointer Lock intermittence reported rather than hidden.

Animations, arbitrary executable HTML and recursive resource composition are
not part of this static composition feature. B81/B82 remain explicitly deferred.

## Baseline evidence

Before changes, v0.70.0 at aa49553 ran 1,554 tests / 241 classes with six
workers in this worktree. A pre-existing Chromium pointer-lock timeout occurred
in `mouse_commands_e2e.cjs:296`; all other classes passed. Preserve that log in
`work/tmp/layers-baseline-sixworkers.log` rather than attributing the failure to
the new feature. Final validation must report the actual final run separately.

## Integration verification

The first full feature run exposed four regression classes: a VM image-runtime
fixture lacked the new layout-event primitive, and three guards needed their
accepted-field/documented-field inventories updated. The failing classes pass
after the fixture/contract updates; no browser failure was attributed to this
feature in that run.

Additional regression cases preserve resource prologues and quoted markers
byte-for-byte during slug assignment, reset screen-only styles on print,
exercise small-caps, verify shared inline-image payloads in combined HTML,
track missing payload creation and preserve unrelated sidecars during clean.
Real Chromium/Firefox tests cover every native reference on all five slide
types plus generated notes, two simultaneous screen fragments, wrapping and
both rotation measurements, cross-layer dependencies, regions, tint, themes,
preset/view replacement, fullscreen and print restoration.

### Final verification — 2026-10-15

- All **26 graphic-layer tests pass**, including real Chromium and Firefox
  checks. Local scroll capture also keeps an asset attached to an authored
  anchor inside a scrollable native body, not just during document scroll.
- The complete suite runs **1,580 tests / 242 classes / six workers**. An earlier
  complete feature run passed (`work/tmp/layers-final-full-sixworkers.log`).
  After the final local-scroll correction, both full runs passed every class
  except `MouseCommands.test_chromium_native_gestures_and_capture`: the same
  30-second Pointer Lock wait at `mouse_commands_e2e.cjs:296` observed on the
  untouched baseline. The test passes isolated in 9.3 seconds. No mouse
  navigation workaround was added to disguise that existing intermittence.
- Final frozen-source logs: `work/tmp/layers-validated-full-sixworkers.log`,
  `work/tmp/layers-final-confirmed-sixworkers.log` and
  `work/tmp/layers-final-mouse-isolated.log`. The bounded complete-suite retry
  reproduced the same failure; it was not retried indefinitely to obtain green.
- Compilation, reference checking and diff-whitespace checking pass. The guide's
  complete inline example builds and verifies as self-contained combined HTML;
  the tracked external/inline example is covered by the regression suite.
- Native desktop, mobile and actual Chromium PDF output were inspected using
  the real example. Local captures are under
  `work/tmp/layers-final-preview-qq60d48b/`; they are inspection evidence, not
  shipped sources. Generated guide/gallery/golden outputs and capture manifests
  were regenerated through their owning tools, not edited by hand.

At the end of that original implementation, no commit, merge, push, tag or
release had been made. Those statements are historical, not a claim about
main's later table-only commit or this current integration. B78's
physical Firefox investigation and the deferred B81/B82 requests remain outside
this feature.

## Integration follow-up — 2026-10-16

Main's 0.71.0 table/URL/kit corrections and mouse acknowledgement-state fix are
retained. Image src values inside HTML/Markdown assets now use the same single
URL-decoding boundary while descriptor file values stay literal. The native
combined regression exercises table spans inside and outside a graphic asset,
encoded filenames, automatic tags, MD/MG cycles, zoom and print restoration.
Its first full run passed; a later full run exposed B100's separate dispatch
clock defect. That defect now has a failing-before/passing-after runtime guard
and native input tracing. Historical run counts above are not substituted for
the current integration's final acceptance results.
