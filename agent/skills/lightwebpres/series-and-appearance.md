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
`slug_prefix`, `presentation_preset`, `reading`, `selectors`, `unit_index`,
`unit_index_max_columns`, `unit_index_selector`. The first four drive the generated
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

## Scoped Selectors

`unit-index` is the current consumer of the common build-time selector core.
Do not invent `build --select` or replace publication status/flags with an
index expression. A selector cannot restore an item excluded from its input.

Compact syntax: `*` selects all supplied records; `expert-en` means literal
`tag:expert-en` (also `tags:expert-en`), with no shared-default rule. Tags are
user names, not implicit editorial/language roles. Whitespace is AND, `|` OR,
leading `-` NOT; parentheses group, quotes preserve spaces/punctuation. NOT
binds before AND, then OR. `AND`, `OR`, `NOT` are ordinary literal tags.
`field:value` reads effective fields; `view:field:value` reads that view only.
Colons have no surrounding whitespace. `/regex/` values perform search.

Views are `series`, `unit`, `slide`, `effective`, `specific`, `general` and
`origin`. Logical ranks are series 0, unit 1, slide 2. The JSON article entry
and Markdown meta both own unit values; source authority, not rank, makes JSON
win for supported fields. `specific` is specific-first and `general` is
general-first, preserving within-scope authority. Effective tags remain
slide-owned, not a union with the unit gate. Scoped reads never inherit another
scope. Effective status defaults to active, but `unit:status:active` requires
an eligible declaration. Blank metadata can be ineligible; Boolean false is
preserved where the field requires it. `origin` retains rejected candidates.

Record fields are registered parsed source values, not unknown metadata or
`comment`. Slide records also expose `type`, plain computed `title`, authored
`slug`, prefixed `id`, normalized `tags`; source fields such as `summary` remain
separate. Do not select by display-only typography. Generated endnotes have
`type:notes`, but are not another authored slide type.

```text
index-selector: (expert-fr | expert-en) -type:unit-index
index-selector: series:author:"Editorial team" slide:title:/^Evidence/
index-selector: $[? @.slide.type == "standard" && @.slide.tags[? @ == "expert-en"]]
index-selector: $[? search(@.slide.title, "Evidence")]
```

These are alternative lines. Repeating the field retains only the last one.
The JSONPath **filter profile** accepts `$[*]`, `$[? ...]`, scalar comparisons
`== != < <= > >=`, `&& || !`, parentheses, scoped dot/bracket paths, existence,
nested array-filter existence with relative `@`, and `match` (full string) /
`search` with constant regexes. Missing operands make every comparison false,
including `!=`; false/null/empty values still exist. Not full RFC 9535 or
I-Regexp: no projection, array indexing, recursion, arithmetic or dynamic regex.

Name queries in `series_meta.selectors`, a mapping of nonempty names to strings:

```json
{"selectors": {"evidence": "type:standard", "english": "$[? @.slide.tags[? @ == \"expert-en\"]]", "english-evidence": "selector:evidence selector:english"}}
```

Use `index-selector: selector:english-evidence`. References compose shared ASTs,
never textual substitution. Mapping shape is checked; only reachable expressions
are compiled. Unknown reachable names, cycles and exhausted budgets are errors,
not fallback to `*` or truncated results.

Regex uses a case-sensitive Unicode NFA, not backtracking or Python `re`:
literals, dot except LF, classes/ranges/negation, absolute `^`/`$`, `* + ?`,
`{m}`, `{m,n}`, `{m,}`, punctuation escapes and `\n \r \t`. No groups,
alternation, shorthand classes, lookarounds, backreferences or flags. Limits:
query 4096 characters per expression, depth 32, AST 256 nodes, 64 reachable
names, regex 512 characters, NFA 256 states, repeat bound 64, regex input 8192
characters, evaluated array 1024 items, 16384 evaluation steps and 4000000
aggregate regex work units per record. String/array limits apply when evaluated.
Both syntaxes use the same Python core in CPython and Pyodide, never `eval`.
See specifications.md §3.4 for the complete profile.

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

**Menu > Display settings** (**Affichage** in French) opens the dedicated
`readingMenu` submenu with zoom, modes and independent table/image shrink
switches. Back or Escape returns focus to the main menu's Display settings
item; clicking outside closes the submenu. **-**, **+**, **=** reduce, enlarge
and reset presentation zoom;
**O** cycles table modes and **A** text modes in the order above. `clip` hides
overflow visually, not cells in HTML; `scroll` contains navigation gestures
inside the table. `fixed` keeps native responsive sizes without content fitting.
`uniform` measures all tag-visible slides in the current article by default
and applies one shared factor. Combined-HTML output shows **Uniform fit scope**
only while this mode is selected: **Current article** (default) or **Entire
series**. Series scope measures tag-eligible slides across all articles using
their actual geometry, styles, presets and settings pins, then shares the
smallest factor. Long-form and series-navigation slides participate even when
they remain too large at the minimum and can shrink the whole group.
`per-slide` measures each slide separately without propagating its factor;
`fixed` performs no content fitting. Multipage output is unaffected by scope.
Browser layout is remeasured after resize, theme/preset/tag changes and
font/image loading. Factors never exceed `1`;
text originally at least 12 CSS pixels also keeps a 12-pixel floor. Smaller
authored text is not enlarged. An unfit slide remains available to scroll at
the floor, not hidden.

`object_shrink` supports images/figures, not arbitrary iframes, players or
buttons. Presentation zoom scales content fonts, line heights and images,
not the page root or frame widths, padding, borders, minimum heights or UI.
At 100%, native responsive sizing remains in effect. Fitting is solved at
100% before the manual factor, so it cannot cancel magnification; long content
can still grow or scroll. Native pinch remains browser zoom, not a custom LWP
gesture. Browser emulation is not a physical-device guarantee.

Reading preferences use `localStorage` under `lwp-reading:<output-directory-path>`
on the same origin, shared across articles, the index and reloads. The strict
version-1 record contains `v: 1`, `table_mode`, `text_fit`, `table_shrink`,
`object_shrink` and `presentationZoom` (a finite number from `0.5` to `2`).
It never stores authored minimum limits or writes `series.json`. Invalid or
inaccessible stored data leaves author defaults and 100% zoom in effect;
controls still work if saving is blocked. Browser storage availability and
`file:` handling vary; do not promise the same persistence as served HTTP(S).
This does not change Appearance's session-storage contract. Print clears
runtime scales and expands table viewports without screen clipping.

Combined-HTML uniform scope stores `article` or `series` separately at
`readingPreferenceKey + ':fit-scope'`, that is,
`lwp-reading:<output-directory-path>:fit-scope`. Missing/invalid values or
blocked reads fall back to `article`; failed writes leave the control usable.
This is not a new field in the version-1 reading record or `series_meta.reading`.
See specifications.md §9.3.9 for the complete contract.

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
origins; no declared provenance or authenticity is implied. The `unit-index`
layout is optional: an existing kit falls back to its standard layout with
chrome, without a manifest rewrite. A dedicated layout uses `default` unless
the preset selects a variant.

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
index carries primary HTML plus inert fragments for alternatives. Available
reader presentation choices apply across the series, stay in browser session
storage and never rewrite source files.

**C** offers **Identity**, **Preset**, **Theme** only when a real Identity Kit
is published; selecting native `builtin/standard` does not remove those axes.
Without a published kit, even with Commons presets, it offers only **Theme**
with theme-specific labels/help, no Identity/Preset axes and no Follow preset.
Preset metadata alone does not expose those axes, and hidden Commons preset
choices are not restored from session storage. The actual theme is selected;
choosing the primary theme restores the author's base appearance.

Applicable / Current identity / All narrow published choices, not brand
approval. Applicable means typed compatibility. For native `builtin`, Current
identity includes published Commons/global themes, Light and native custom
variants, excluding foreign kit themes. For a real kit, it includes only its
own qualified themes and custom variants, excluding unowned global themes and
other kits. Commons availability to native LightWebPres is not declared kit
membership. All themes of selected kits are published with kit-qualified names;
no cross-product is generated. Identity labels name ownership, while default
markers name initial choices.

An explicit `theme:` in `settings.conf` stays fixed when presentation changes.
Without it, the preset's theme follows the selected presentation until the
reader chooses an explicit runtime theme. In kit-aware mode, **Follow preset**
clears that override; in theme-only mode, select the primary theme instead.
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
