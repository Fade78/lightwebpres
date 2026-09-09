# Series And Appearance

Read this for article registration, order, visibility, languages, identities
and runtime choices. [Article Format](article-format.md) owns metadata
cascades and slide fields; [Text and Style](text-and-style.md) owns text
conversion and local styling. [Operations](operations.md) covers authorized
changes, kit composition and validation without duplicating CLI schemas.

## Register Articles

Every article that should appear in navigation/index needs an entry in
`series.json`'s `articles` array, at minimum:

```json
{"page_source": "apple-pie.md"}
```

`page_source` is the only required field in an entry. It must be a bare
filename, not `sources/x.md`, an absolute path or `..`, must end in `.md`,
and must exist in `sources/`. Array order is navigation/index order.
The pre-v1.0 `source`/`file` names are rejected with a migration error.
`page_dest` is also a bare filename if specified; otherwise it derives from
`page_source`. Article Format describes the complete fallback chain.

Other entry fields are `page_dest`, `page_title`, `page_desc`, `card_title`,
`card_desc`, `card_label`, `nav_title`, `nav_desc`, `author`, `license`,
`date`, `status` and `comment`. Repeat one only to override the article's
own metadata or content-derived fallback:

```json
{"page_source": "apple-pie.md", "card_label": "Article 3 (corrected)"}
```

Non-string values for these fields are fatal. An explicit destination must
end in `.html`/`.htm`; case-insensitive output collisions are fatal.
A `full-article` slide's `article:` target must also be a bare filename that
exists under `sources/`. The tool follows symlinks; `audit` reports those
that leave their logical root. Filename validation is not a symlink sandbox.

`series_meta`, beside `articles`, holds series-wide `title`, `subtitle`,
`version`, `intro`, `author`, `license`, `default_tag`, `scroll_duration`,
`lang_tags`, `notes_placement`, `notes_tooltip`, `slide_page_numbers`,
`slug_prefix`, `presentation_preset`, `reading`. The first four drive the generated
index and README; `author`/`license` provide article fallbacks. `comment`
also works here, or on an article entry, and is never read or rendered.

No `articles[]` entry or `lwp:meta` block selects or refines a presentation
preset. That choice belongs only to `series_meta.presentation_preset`.
The optional root `presentation_presets` list declares build-time runtime
alternatives, not a persisted reader selection. The root `themes` list does
the same for extra runtime themes; neither list is an article field.

## Tags And Visibility

Article-level `tags:` goes in `lwp:meta`. If present, a selected tag must
match that gate **and** at least one non-excluded slide must accept it for
the article's index/nav card to remain visible. Without this field there is
no article-level gate. `series tags` counts only effective intersections.

On slides, `tags:` is separate from that gate and from inline styling tags.
Use one physical line of space-separated names. Names normalize
case-insensitively and accept Unicode word characters, digits, `-`, `_`,
except a name cannot begin with `_`.

- Absent or empty slide `tags:` assigns `default`, the shared slide tag.
- `tags: excluded` removes a slide after type validation but before other slide validation, numbering and anchor generation.
- Other values become `data-tags="..."` on the slide section.
- A non-`default` selection keeps its own slides plus `default` slides. Selecting `default` keeps only `default` slides.
- Article gates require exact matches; the slide-level shared-default rule does not make an article gate shared.

Press **L** in generated pages to choose a tag when at least two exist.
The choice persists in `localStorage['lwp-active-tag']`. The menu names the
active tag, counts visible articles/slides and lists titles; an empty
selection is announced on the page.

`series_meta.default_tag` chooses the initial tag on a fresh page, defaulting
to `default`. It must occur on an article or a non-excluded slide selected
for the build. A valid persisted reader choice wins over it. `build` and
`audit` warn if the chosen tag or another selectable tag has no effective
slide after gates and exclusions.

```bash
lightwebpres series tags <series-dir> --format json
lightwebpres series tags <series-dir> --tag fr
lightwebpres status <series-dir> --format json
```

These are read-only reports, not builds or approval checks. `series tags`
exposes the stable vocabulary, `default_output`, per-tag status totals and
slide counts. `status` embeds the same report under `tags`. `output` counts
active articles only; drafts and ignored entries stay in inventory without
making normal output appear visible. Compare the intersections, not just
the presence of tag names. Status is participation, not factual or editorial
approval. A documentary collection may span multiple series; LWP has no
cross-series corpus database or corpus command. Inventory each series
explicitly and keep any collection-wide editorial index outside this schema.

## Languages And Scrolling

When tags select languages, declare typography packs in `series.json`:

```json
{
  "series_meta": {
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "articles": [{"page_source": "guide.md"}]
}
```

The first mapped language tag on a slide selects its typography pack.
Slides without one use build-wide `--lang`/`LWP_LANG`. Built-in `fr` and
`en` are always available; another pack resolves to `typography/<name>.json`,
then legacy `language/<name>.json`. `audit` warns about malformed slide tags
and missing mapped packs; plain audit does not block. Language tags choose
typography, not automatic translation. Text and Style lists the rules.

`series_meta.scroll_duration` is a non-negative integer in milliseconds,
default `200`. `0` makes slide navigation jump rather than glide.
`build`, `verify`, `watch` accept `--scroll-duration` as a one-run override.
The presenter's Scroll action or **I** toggles between that duration and
`0`, displaying the active value.

## Reading Choices And Fitting

Set initial reader choices only in `series_meta.reading`, not an article,
theme or preset. This fragment keeps tables locally scrollable and fits text
independently per slide; merge it without replacing other metadata:

```json
{
  "series_meta": {
    "reading": {"table_mode": "scroll", "text_fit": "per-slide"}
  }
}
```

The object is strict. Omission or `{}` uses all defaults; partial objects fill
omitted keys. Unknown keys and invalid values are fatal.

| Key | Values | Default |
|---|---|---|
| `table_mode` | `clip`, `overflow`, `scroll` | `clip` |
| `text_fit` | `fixed`, `uniform`, `per-slide` | `fixed` |
| `table_shrink` | JSON boolean | `false` |
| `object_shrink` | JSON boolean | `false` |
| `min_text_scale` | Finite JSON number from `0.5` to `1`, inclusive | `0.75` |
| `min_table_scale` | Finite JSON number from `0.5` to `1`, inclusive | `0.85` |
| `min_object_scale` | Finite JSON number from `0.5` to `1`, inclusive | `0.85` |

**Menu** exposes the modes and independent table/image shrink switches;
**O** cycles table modes and **A** text modes in the order above. `clip` hides
overflow visually, not cells in HTML; `scroll` contains navigation gestures
inside the table. `fixed` keeps native responsive sizes without content fitting.
`uniform` measures all currently visible slides under the active tag, including
a visible long-form article, and applies one shared factor; `per-slide`
measures each separately. Browser layout is remeasured after resize,
theme/preset/tag changes and font/image loading. Factors never exceed `1`;
text originally at least 12 CSS pixels also keeps a 12-pixel floor. Smaller
authored text is not enlarged. An unfit slide remains available to scroll at
the floor, not hidden.

`object_shrink` supports images/figures, not arbitrary iframes, players or
buttons. Presentation zoom is independent magnification that can cause
overflow; native browser pinch is not a custom presentation-zoom gesture.
Reading choices and zoom survive closing/reopening Menu in the loaded page,
not page navigation or reloads. They do not use the Appearance session-storage
contract. Print clears runtime scales and expands table viewports without
screen clipping. See specifications.md §9.3.9 for the complete contract.

## Identities, Presets And Themes

An Identity Kit owns inner layouts, chrome, assets, typed themes and
constrained structural CSS. LWP owns `<head>`, `<body>`, navigation,
JavaScript and each slide's `<section>`. A kit lives at
`kits/<id>/<version>/`; a vendored copy at `templates/kits/<id>/<version>/`.
`LWP_IDENTITY_KITS_DIR` selects the user catalogue. Published assets go to
`public/assets/presentations/<id>/<version>/...`. The complete manifest,
fragment, asset and validation contract is specifications.md §9.9.

Only `series_meta.presentation_preset` persists the initial choice:
`builtin/standard`, `commons/<id>` or `id@MAJOR.MINOR.PATCH/preset`.
Identity is inferred from it and applies to the entire series and index.
Omission implicitly selects `builtin/standard`. `init --preset builtin/standard`
and `series preset set --preset builtin/standard` persist the explicit
reference; plain `init` leaves it absent. Neither native choice vendors resources.

```json
{
  "series_meta": {
    "presentation_preset": "corporate@1.0.0/brief"
  }
}
```

The `lightwebpres.identity-kit/1` manifest requires `id`, `version` and an
identity `label`. Optional `default_preset` names a local preset; otherwise
the first in manifest order is used. The label stays fixed regardless of
that choice. `slide_layouts` and `slide_chrome` declare defaults **in the
manifest only**. References are local files or native `builtin:standard`
layouts and `builtin:light` themes. Native layouts in a kit keep its chrome.
Kits neither extend nor depend on other kits or Commons. Loaders compute
origins; no declared provenance or authenticity is implied.

Commons themes live under `themes/` and `templates/themes/`, with
`LWP_THEMES_DIR` for the user catalogue. Commons presets live under
`commons/presets/<id>.json`: installed, user (`LWP_COMMONS_DIR`) or
series-local (`templates/commons/presets/`). Their strict
`lightwebpres.commons-preset/1` schema has `schema`, `id`, `label`,
`description`, `theme`; the theme is a global slug or `builtin:light`.
They bind native layouts to a theme with no starter. Native Standard uses
minimal Light. `kit compose` creates an autonomous kit from explicit final
references; follow the guide route in Operations for manifest and recipe
examples, not an invented inheritance scheme.

Every slide type accepts these per-slide overrides:

```text
slide-layout: hero
slide-header: Internal brand
slide-footer: ""
```

`slide-layout` must match `[a-z][a-z0-9-]*`; empty is fatal.
`slide-header` and `slide-footer` take text, a JSON object model or exactly `""`
to suppress inherited chrome; unquoted empty is fatal. These are slide
overrides, not an article-entry JSON cascade. The typed style order is
base preset theme < `settings.conf` pins < article `style.*` < instance styles,
then advanced final CSS in `templates/custom.css`.

## Runtime Presentation Alternatives

A kit or Commons primary also exposes compatible native Standard.
Additional choices are declared at the root of `series.json`:

```json
{
  "series_meta": {
    "presentation_preset": "corporate@1.0.0/brief"
  },
  "presentation_presets": ["builtin/standard"]
}
```

`build`, `verify`, `watch` accept `--presentation-presets selector[,selector...]`
to override that root list. Alternatives add to, not replace, the primary.
The effective list keeps the primary first and removes duplicates.
Missing/unknown selectors fail before writing output. Each article and
index carries primary HTML plus inert fragments for alternatives. **C**
opens Appearance; the reader's presentation choice applies across the series,
stays in browser session storage and never rewrites source files.

The picker offers **Identity**, **Preset**, **Theme**. Applicable / Current
identity / All filter published choices by typed compatibility or ownership,
not brand approval. All themes of selected kits are published with
kit-qualified names; no cross-product is generated. Identity labels name
ownership, while default markers name initial choices.

An explicit `theme:` in `settings.conf` stays fixed when presentation changes.
Without it, the preset's theme follows the selected presentation until the
reader chooses an explicit runtime theme, which lasts until **Follow preset**.
Kit-only slide overrides may make implicit native Standard incompatible;
it is then omitted with a warning. Explicit incompatible requests fail.

## Runtime Themes

The root `themes` list contains strings from the effective series catalogue,
including complete snapshots under `templates/themes/`:

```json
{
  "series_meta": {
    "title": "My series",
    "intro": "What it is about.",
    "default_tag": "fr",
    "lang_tags": {"fr": "fr", "en": "en"}
  },
  "themes": ["essential", "family:terrain"],
  "articles": [{"page_source": "apple-pie.md"}]
}
```

Each item is a theme slug, `all`, `essential`, or a facet selector such as
`background:light`, `fam:terrain`, `bgh:red`. Several items add their matches;
an explicit CLI `--themes` overrides the list. `essential` means Monochrome,
Monochrome Night and Print Ink; it ships by default and this list only adds
to it. `--no-essential-theme` opts out. If a local file shadows a slug,
`builtin:<slug>` selects the embedded version.

With property pins in `settings.conf`, the runtime's first variant is
`custom(<theme>)` and it also includes the raw base theme; pins affect only
the custom variant. A local snapshot is a complete
`templates/themes/<slug>.conf`; `series.json` names it but never contains
its typed properties. Theme measurements are per-category WCAG information,
not approval, and the tool neither designs an accessible palette nor rejects
a theme for its appearance. Check actual content in the browser.
